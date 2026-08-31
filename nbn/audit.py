"""Daily self-audit: re-verify yesterday's output against its own receipts.

Runs once daily (kv-guarded). For each post from the last 26h: refetch the receipt,
have the model check every claim and number against the source text, and audit the
class label (a press story classed `primary` is the one gate-proof failure).
Findings surface in the Desk Report; a MATERIAL finding stages a CORRECTION draft
per CORRECTIONS.md — corrections never auto-publish.
"""
import datetime
import json
import logging
import time

from . import config, sources, store

log = logging.getLogger("nbn.audit")

AUDIT_PROMPT = """You are the overnight fact-checker for a Bitcoin news wire. You receive
one published post and the CURRENT text of its cited source. Adversarially verify:

1. Every factual claim in the post is supported by the source text.
2. Every number in the post appears in the source (verbatim or trivially derived).
3. Quotes are verbatim.
4. CLASS check: the post was classed "{klass}". "primary" requires the source to BE an
   official artifact (regulator release, filing, company's own statement about itself) —
   press REPORTING about officials is not primary.

Note: the source page may have changed since publication; if the source text no longer
contains support but the post plausibly matched an earlier version, say so under
"source_drift" rather than calling the post wrong.

Verdicts: "clean" (all checks pass), "minor" (imprecision that does not mislead),
"material" (a reader believes something false), "unverifiable" (source text empty/blocked).

Return ONLY JSON:
{{"verdict": "...", "class_ok": true/false, "findings": ["..."], "source_drift": true/false,
  "correction_text": "only if material: a CORRECTION post per the house template, else null"}}"""


def _audit_one(post_row) -> dict:
    from . import brain
    src_text = sources.fetch_article_text(post_row["receipt_url"]) if (
        post_row["receipt_url"] or "").startswith("http") else ""
    if not src_text:
        return {"verdict": "unverifiable", "class_ok": True,
                "findings": ["source fetch failed or empty"], "source_drift": False}
    payload = {
        "post": post_row["body"],
        "class": post_row["class"],
        "source_url": post_row["receipt_url"],
        "source_text": src_text[:9000],
    }
    resp = brain._create(config.ANTHROPIC_MODEL,
                         AUDIT_PROMPT.format(klass=post_row["class"]),
                         json.dumps(payload), max_tokens=1500)
    return brain._json_from(resp)


def maybe_run(con) -> bool:
    """Fire once daily at NBN_AUDIT_UTC (default 09:00), kv-guarded."""
    now = datetime.datetime.now(datetime.timezone.utc)
    hh, mm = (config.AUDIT_UTC or "09:00").split(":")
    fire = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
    if not (fire <= now < fire + datetime.timedelta(minutes=45)):
        return False
    key = f"audit:{now:%Y-%m-%d}"
    if store.kv_get(con, key):
        return False
    store.kv_set(con, key, str(time.time()))

    posts = con.execute(
        "SELECT * FROM posts WHERE created > ? AND class != 'briefing'"
        " AND mode IN ('IMMEDIATE','UNCERTAIN') ORDER BY created",
        (time.time() - 26 * 3600,)).fetchall()
    results = []
    for p in posts:
        try:
            r = _audit_one(p)
        except Exception as exc:  # noqa: BLE001
            r = {"verdict": "unverifiable", "class_ok": True, "findings": [f"audit error: {exc}"[:150]]}
        results.append({
            "post_id": p["id"], "mode": p["mode"], "class": p["class"],
            "title": (p["body"] or "").split("\n")[0][:120],
            "verdict": r.get("verdict", "unverifiable"),
            "class_ok": bool(r.get("class_ok", True)),
            "findings": r.get("findings", [])[:5],
            "source_drift": bool(r.get("source_drift")),
        })
        if r.get("verdict") == "material" and r.get("correction_text"):
            _stage_correction(p, r["correction_text"])
        log.info("audit post %s: %s%s", p["id"], r.get("verdict"),
                 "" if r.get("class_ok", True) else " CLASS-SUSPECT")

    store.kv_set(con, "audit:last", json.dumps({
        "ran": f"{now:%Y-%m-%d %H:%M} UTC", "posts_checked": len(results),
        "results": results}))
    return True


def _stage_correction(post_row, correction_text: str):
    """Material finding -> staged CORRECTION draft (NEVER published; Brady taps)."""
    from . import publisher_typefully
    outcome, ref = publisher_typefully.publish_thread(
        [correction_text], immediate=False)
    log.warning("MATERIAL audit finding on post %s -> correction %s: %s",
                post_row["id"], outcome.value, ref)
