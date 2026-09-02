"""The Editor: last-mile judgment before an autonomous publish.

Runs AFTER every deterministic gate has passed. The gates check the post in isolation
(facts, numbers, scope, style); the editor checks it against the FEED — the two things
gates structurally cannot see: contextual duplication and craft. Born 2026-08-30 after
two live incidents (triple attribution, duplicate lede) that were exactly this class.

Powers: publish | revise (edit DOWNWARD only; re-linted, falls back to original on
failure) | spike (held, with the editor's reasoning in the Desk Report — during tuning
week Brady edits the editor).
"""
import json
import logging
import time

from . import config, lint, store

log = logging.getLogger("nbn.editor")

EDITOR_PROMPT = """You are the publishing editor of Next Block News, a Bitcoin news wire
on X. A post has passed all factual and style gates and is seconds from publishing. You
see the wire's recent feed exactly as a scrolling reader would. Decide:

1. READER VALUE: does this post tell the feed's reader something the feed has not already
   said? A rephrase of covered news, a non-story, or content-free filler gets spiked.
   When the source is itself an X post, the reader sees the original right under ours
   (quote/link) — a post that merely restates the original's copy adds nothing and gets
   spiked; our copy must extend it with material the original does not say.
2. FEED CONTEXT: given the recent posts, is the framing right? A follow-up must lead with
   what is new and reference earlier coverage in passing, never re-announce it.
3. COPY: can it be tightened? You may edit DOWNWARD ONLY — cut, reorder, merge, sharpen.
   You may not add any claim, number, name, or quote that is not already in the post.
   Keep the wire voice: flat, scannable short paragraphs, "NEW:" atom intact, attribution
   once, no hype, no forecasts.
4. PRICE DISCIPLINE: the wire reports prices and flows flat; it never speculates about
   why price sits at a level, never frames a metric-vs-price "tension" as the story,
   never asks questions. Spike or strip that framing.
5. SOURCE TIER: a number belongs to whoever measured it. If the copy attributes a
   second-tier aggregator whose only contribution is repackaging a data provider's
   figure, revise to credit the provider — and if the story is nothing BUT that
   repackaging, spike it (a weak link under our copy is our packaging too).
6. FINAL SMELL: anything a good editor would flinch at — wrong emphasis, buried lede,
   accidental editorializing, awkward wire cadence.

Be a real editor: most gate-passed posts should publish (possibly revised); spike only
with a reason you would say out loud to the newsroom. Do not spike for subjective taste
alone; do spike for redundancy, emptiness, or misframing.

Return ONLY JSON:
{"verdict": "publish" | "revise" | "spike",
 "post": "the final copy (original if publish, edited if revise, null if spike)",
 "reason": "one or two sentences you would say to the newsroom"}"""

NEWSROOM_EDITOR_PROMPT = EDITOR_PROMPT.rsplit("Return ONLY JSON:", 1)[0] + """

This candidate was produced by a run-scoped newsroom. You are also its independent,
fail-closed semantic support editor. The payload includes the exact selected receipt text
and code-owned provenance. Check every factual assertion in the final copy against ONLY
that receipt. A changed actor, reversed direction, negation, date mismatch, unsupported
paraphrase, inference, or fact found only in another source is unsupported. Search snippets,
outside knowledge, and the newsroom's own claim labels are not evidence.

You may revise only by cutting, reordering, merging, or sharpening material already in the
candidate. The revised post itself must remain completely supported by the selected receipt.

Return ONLY JSON:
{"verdict": "publish" | "revise" | "spike",
 "post": "final supported copy, or null if spike",
 "reason": "one or two newsroom sentences",
 "claims_supported": true | false,
 "unsupported_claims": ["specific unsupported assertion"]}
"""


BATCH_EDITOR_PROMPT = """You are the independent publishing editor for Next Block News.
You receive all candidates from one run, their inspected evidence, and the recent feed.
The desk's goal is a useful automated Bitcoin account with good work flowing—not perfect,
unimpeachable copy and not a generic macro-stat feed.

For each candidate, use practical editorial judgment:
- publish useful, supported work; revise when a narrower or clearer version is better;
- draft only when the story is worthwhile but uncertainty makes autonomous publication
  unwise; drop true redundancy, unsupported material claims, non-stories, and bad framing;
- routine factual claims may rest on one credible inspected official/Tier 1/Tier 2 receipt;
  allegations, hacks, crime, disputed claims, or consequential legal assertions need a
  primary artifact or two credible independent reports;
- all supplied inspected receipts may support the post together. The selected receipt is the
  link readers get, not a demand that one page reproduce every harmless detail;
- judge rounding and numerical differences for materiality. Roughly 3% may describe 2.99%.
  Do not reject 159.95 versus 160.1 unless it changes the actual claim;
- use recent coverage to prevent genuine repetition while allowing useful later developments;
- if revision removes the actual new development and leaves only a static total or background
  fact, drop the story rather than publish a fact with no news peg;
- preserve or improve effective structure and length. Do not add facts absent from evidence.

Return ONLY JSON:
{"decisions":[{"story_id":"...","verdict":"publish|revise|draft|drop",
"post":"final copy or null","reason":"brief newsroom explanation"}]}"""


def review(post: str, item: dict, con) -> dict:
    """Returns {'verdict', 'post', 'reason'}; fails open to publish-as-is on errors."""
    from . import brain
    effective_ts = store.effective_post_ts_sql()
    recent = con.execute(
        f"SELECT body, class, {effective_ts} AS effective_at FROM posts"
        " WHERE mode IN ('IMMEDIATE','DRAFT','UNCERTAIN')"
        " ORDER BY effective_at DESC LIMIT 10").fetchall()
    feed = [{"hours_ago": round((time.time() - r["effective_at"]) / 3600, 1),
             "class": r["class"], "post": r["body"][:500]} for r in recent]
    payload = {
        "candidate_post": post,
        "class": item.get("class"),
        "coverage_action": item.get("_coverage_action", "draft"),
        "source": item.get("source"),
        # For X-sourced items the title IS the original post's text — the editor needs
        # it to judge whether our copy merely restates what the reader already sees.
        "source_item_text": (item.get("title") or "")[:600],
        "recent_feed_newest_first": feed,
    }
    try:
        resp = brain._create(config.EDITOR_MODEL, EDITOR_PROMPT, json.dumps(payload),
                             max_tokens=2000, effort=config.EDITOR_EFFORT)
        out = brain._json_from(resp)
    except Exception as exc:  # noqa: BLE001 — an editor outage must not block news
        log.warning("editor unavailable, publishing gate-passed post as-is: %s", exc)
        return {"verdict": "publish", "post": post, "reason": f"editor error: {exc}"[:150]}

    verdict = out.get("verdict", "publish")
    final = out.get("post") or post
    reason = (out.get("reason") or "")[:300]
    log.info("editor verdict: %s — %s", verdict, reason[:120])
    store.kv_set(con, "editor:last", json.dumps(
        {"verdict": verdict, "reason": reason, "at": time.time()}))
    return {"verdict": verdict, "post": final, "reason": reason}


def review_newsroom(post: str, item: dict, con, *, source_text: str,
                    claims: list[dict], provenance: dict) -> dict:
    """Independent semantic+craft review; any uncertainty fails closed."""
    from . import brain
    effective_ts = store.effective_post_ts_sql()
    recent = con.execute(
        f"SELECT body, class, {effective_ts} AS effective_at FROM posts"
        " WHERE mode IN ('IMMEDIATE','DRAFT','UNCERTAIN')"
        " ORDER BY effective_at DESC LIMIT 10").fetchall()
    feed = [{"hours_ago": round((time.time() - r["effective_at"]) / 3600, 1),
             "class": r["class"], "post": r["body"][:500]} for r in recent]
    payload = {
        "candidate_post": post,
        "declared_material_claims_untrusted": list(claims or [])[:24],
        "selected_receipt": {
            **dict(provenance or {}),
            "text": str(source_text or "")[:8000],
        },
        "class": item.get("class"),
        "coverage_action": item.get("_coverage_action", "draft"),
        "source_item_text": (item.get("title") or "")[:600],
        "recent_feed_newest_first": feed,
    }
    try:
        resp = brain._create(
            config.EDITOR_MODEL, NEWSROOM_EDITOR_PROMPT, json.dumps(payload),
            max_tokens=3000, effort=config.EDITOR_EFFORT,
        )
        out = brain._json_from(resp)
        verdict = out.get("verdict")
        supported = out.get("claims_supported") is True
        unsupported = out.get("unsupported_claims")
        if verdict not in {"publish", "revise", "spike"} or not isinstance(unsupported, list):
            raise ValueError("malformed newsroom editor verdict")
        if supported and unsupported:
            raise ValueError("inconsistent newsroom support verdict")
        if not supported:
            verdict = "spike"
        final = None if verdict == "spike" else out.get("post")
        if not final and verdict != "spike":
            raise ValueError("newsroom editor omitted final post")
        reason = str(out.get("reason") or "")[:300]
    except Exception as exc:  # noqa: BLE001 - newsroom support is deliberately fail closed
        log.warning("newsroom editor unavailable; holding candidate: %s", exc)
        return {
            "verdict": "spike", "post": None,
            "reason": f"newsroom editor unavailable: {exc}"[:300],
            "claims_supported": False, "unsupported_claims": ["support unknown"],
        }
    store.kv_set(con, "editor:last", json.dumps({
        "verdict": verdict, "reason": reason, "claims_supported": supported,
        "at": time.time(),
    }))
    return {
        "verdict": verdict, "post": final, "reason": reason,
        "claims_supported": supported,
        "unsupported_claims": [str(value)[:300] for value in unsupported[:12]],
    }


def review_newsroom_batch(candidates: list[dict], con, *, run_id: str,
                          reservation: str | None = None) -> dict:
    """One clean Sonnet editor call for the complete run; outage stages safe drafts."""
    from . import brain
    effective_ts = store.effective_post_ts_sql()
    recent = con.execute(
        f"SELECT body,class,{effective_ts} AS effective_at FROM posts"
        " WHERE mode IN ('IMMEDIATE','DRAFT','UNCERTAIN')"
        " ORDER BY effective_at DESC LIMIT 12"
    ).fetchall()
    payload = {
        "candidates": [{
            "story_id": row["story_id"], "post": row["post"],
            "reader_value": row.get("reader_value", ""),
            "selected_receipt": row.get("selected_receipt", {}),
            "inspected_evidence": row.get("inspected_evidence", [])[:8],
            "elevated_claim": bool(row.get("elevated_claim")),
            "code_notes_to_fix_before_delivery": row.get("hard_rail_notes_for_revision", []),
        } for row in candidates],
        "recent_feed_newest_first": [{
            "hours_ago": round((time.time() - r["effective_at"]) / 3600, 1),
            "class": r["class"], "post": r["body"][:1000],
        } for r in recent],
    }
    called_at = time.monotonic()
    try:
        resp = brain._create(
            config.EDITOR_MODEL, BATCH_EDITOR_PROMPT, json.dumps(payload),
            max_tokens=8000, effort=config.EDITOR_EFFORT, reservation=reservation,
        )
        store.record_model_usage(
            con, run_id=run_id, seat="editor", model=config.EDITOR_MODEL,
            round_number=1, response=resp,
            latency_ms=int((time.monotonic() - called_at) * 1000), outcome="ok",
        )
        out = brain._json_from(resp)
        rows = out.get("decisions")
        if not isinstance(rows, list):
            raise ValueError("editor omitted decisions")
        allowed = {row["story_id"] for row in candidates}
        decisions = {}
        for row in rows:
            story_id = str(row.get("story_id") or "")
            verdict = str(row.get("verdict") or "")
            if story_id not in allowed or story_id in decisions \
                    or verdict not in {"publish", "revise", "draft", "drop"}:
                continue
            final = row.get("post")
            if verdict in {"publish", "revise", "draft"} and not str(final or "").strip():
                continue
            decisions[story_id] = {
                "verdict": verdict, "post": final,
                "reason": str(row.get("reason") or "")[:300],
            }
        return {"ok": True, "decisions": decisions}
    except Exception as exc:  # noqa: BLE001 - preserve good desk work as drafts
        store.record_model_usage(
            con, run_id=run_id, seat="editor", model=config.EDITOR_MODEL,
            round_number=1, latency_ms=int((time.monotonic() - called_at) * 1000),
            outcome="error",
        )
        log.warning("batch editor unavailable; staging candidates as drafts: %s", exc)
        return {"ok": False, "error": str(exc)[:300], "decisions": {}}
