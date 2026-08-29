"""Morning/afternoon briefing thread, derived from the Marketing Node's Daily Intel brief.

The Node's read API (GET /api/daily-intel/latest, bearer read token) serves the
Brady-tuned brief: theme, body_md with inline citations, must_know, more_reads.
This module rewrites it into a wire-voice X thread. Hard requirements:
- STRIP every Swan reference (brand separation is the point of the handle).
- Facts and links only from the brief itself; the model never adds a URL.
- One thread per window per day (DB-guarded).
"""
import datetime
import json
import logging
import re

import httpx

from . import config, lint, store

log = logging.getLogger("nbn.briefing")

BRIEFING_PROMPT = """You turn a daily Bitcoin intelligence brief into an X thread for
Next Block News, a neutral Bitcoin news wire. Voice: facts stated flat, no adjectives of
magnitude, no forecasts, no buy/sell framing, no emoji, no hashtags, sentence case.

Rules:
- 5 to 9 posts. Post 1 opens the thread: "{window_title} Bitcoin briefing — {date}." then
  the single most important development in one sentence. Each following post covers one
  story or data point from the brief, numbers verbatim from the brief text.
- The brief was written for a company called Swan. REMOVE every reference to Swan, its
  products, partners-as-Swan's, or its people. Rewrite such sentences neutrally or drop them.
- Mention only X handles from the verified list, max 2 in the whole thread.
- You never write URLs. For each post, if the brief cites a source URL for its story, put
  that URL (copied exactly from the brief) in the separate "receipt" field; the system
  appends receipts. Only URLs that appear in the brief are allowed.
- Non-Bitcoin tokens may be named only as market fact, never as coverage.
- Final post: 1-2 sentence flat summary of what to watch next, only if the brief supports it.

Return ONLY JSON: {"posts": [{"text": "...", "receipt": "url-or-null"}, ...]}"""


def _node_headers():
    return {"Authorization": f"Bearer {config.NODE_READ_TOKEN}"}


def fetch_brief():
    try:
        resp = httpx.get(
            f"{config.NODE_BASE_URL}/api/daily-intel/latest",
            headers=_node_headers(), timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data if data.get("daily_brief") else None
    except Exception as exc:  # noqa: BLE001
        log.error("brief fetch failed: %s", exc)
        return None


def _brief_text(brief: dict) -> str:
    parts = [str(brief.get("theme", "")), str(brief.get("body_md", ""))]
    for mk in brief.get("must_know", []) or []:
        parts.append(f"{mk.get('title', '')} — {mk.get('summary', '')}")
    return "\n\n".join(p for p in parts if p)


def _brief_urls(text: str) -> set:
    return set(re.findall(r"https?://[^\s)\"']+", text))


def build_thread(brief_payload: dict, window_title: str):
    """Returns [{'text':..., 'receipt':...}] or None."""
    from . import brain  # late import to avoid cycle
    brief = brief_payload["daily_brief"]
    # The read API wraps strings as {"text":..., "truncated":...}; flatten.
    def flat(v):
        if isinstance(v, dict) and "text" in v:
            return v["text"]
        if isinstance(v, list):
            return [flat(x) for x in v]
        if isinstance(v, dict):
            return {k: flat(x) for k, x in v.items()}
        return v
    brief = flat(brief)
    source_text = _brief_text(brief)
    allowed_urls = _brief_urls(source_text)
    today = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "window_title": window_title,
        "date": f"{today:%B %-d, %Y}",
        "verified_handles": lint.verified_handles(),
        "brief": source_text[:12000],
    }
    resp = brain._create(config.ANTHROPIC_MODEL, BRIEFING_PROMPT, json.dumps(payload),
                         max_tokens=4000)
    out = brain._json_from(resp)
    posts = out.get("posts") or []
    if not (4 <= len(posts) <= 10):
        log.error("briefing thread wrong size: %d", len(posts))
        return None
    # Gates: lint each post; receipts must be URLs from the brief; no Swan leakage.
    for p in posts:
        text = p.get("text", "")
        errors = lint.check(text, {"_source_text": source_text}, {"class": "briefing"})
        errors = [e for e in errors if not e.startswith("news post must start")]
        if re.search(r"\bswan\b", text, re.I):
            errors.append("Swan reference leaked")
        r = p.get("receipt")
        if r and r not in allowed_urls:
            errors.append(f"receipt not in brief: {r}")
        if errors:
            log.warning("briefing post failed gates: %s | %s", errors, text[:80])
            return None
    return posts


def maybe_run(con) -> bool:
    """Fire at configured UTC times, once per window per day. Returns True if posted/staged."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() >= 5:  # the Node's intel runs Mon-Fri
        return False
    for hhmm, title in config.BRIEFING_SCHEDULE:
        h, m = hhmm.split(":")
        fire = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        # fire window: within 30 min after the scheduled time
        if not (fire <= now < fire + datetime.timedelta(minutes=30)):
            continue
        key = f"briefing:{now:%Y-%m-%d}:{title.lower()}"
        if store.story_already_posted(con, key):
            continue
        payload = fetch_brief()
        if not payload:
            log.warning("no brief available for %s window", title)
            continue
        posts = build_thread(payload, title)
        if not posts:
            continue
        from . import publisher
        # Assemble: post texts in order, then one receipts post at the end.
        receipts = [p["receipt"] for p in posts if p.get("receipt")]
        texts = [p["text"] for p in posts]
        if receipts:
            texts.append("Sources:\n" + "\n".join(receipts[:8]))
        mode, ref = publisher.publish_thread(texts, klass="briefing")
        store.log_post(con, key, None, "briefing", "\n\n".join(texts), receipts[0] if receipts else "",
                       mode, ref)
        log.info("briefing %s window: %s (%s)", title, mode, ref)
        return True
    return False
