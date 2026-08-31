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
