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
- 5 to 9 posts. Post 1 is a LINK-FREE INDEX that opens the thread, headed EXACTLY:
  "{window_title} Block - {date}

  Top stories:
  • <story one, a few words>
  • <story two>
  • <story three>

  More inside ➡️"
  Use 3-5 index bullets naming the biggest stories, no numbers needed there, receipt null.
  The "More inside ➡️" signoff is the house convention — the one emoji the wire uses,
  exactly there and nowhere else.
- Each following post covers one story or data point from the brief, numbers verbatim
  from the brief text, in the same order as the index where possible.
- The brief was written for a company called Swan. REMOVE every reference to Swan, its
  products, partners-as-Swan's, or its people. Rewrite such sentences neutrally or drop them.
- Mention only X handles from the verified list, max 2 in the whole thread.
- You never write URLs. For each post, if the brief cites a source URL for its story, put
  that URL (copied exactly from the brief) in the separate "receipt" field; the system
  appends receipts. Only URLs that appear in the brief are allowed.
- HARD SCOPE: Bitcoin only. Never name or price any non-Bitcoin token (no ETH, XRP, etc.),
  no "altcoins", no crypto-industry stories — drop those sentences from the brief entirely.
  "Crypto" may appear only inside the quoted title of an official document.
- If "wire_items" is provided: those are stories this wire itself covered since the last
  briefing. Fold in the ones the brief does NOT already cover (one post each, receipt =
  that item's url); skip duplicates of brief stories.
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


def build_thread(brief_payload: dict, window_title: str, wire_items: list = None):
    """Returns [{'text':..., 'receipt':...}] or None."""
    from . import brain  # late import to avoid cycle
    wire_items = wire_items or []
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
    if wire_items:
        source_text += "\n\nWire items:\n" + "\n".join(
            f"- {w['title']} ({w['source']}) {w['url']}" for w in wire_items)
    allowed_urls = _brief_urls(source_text)
    today = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "window_title": window_title,
        "date": f"{today:%B %-d, %Y}",
        "verified_handles": lint.verified_handles(),
        "brief": source_text[:12000],
        "wire_items": [{"title": w["title"], "source": w["source"], "url": w["url"]}
                       for w in wire_items[:10]],
    }
    out = None
    for attempt in range(2):
        request = dict(payload)
        if attempt:
            request["retry_instruction"] = (
                "The previous response was empty, truncated, or invalid JSON. Return a compact "
                "complete JSON object with 5-7 concise posts; close every string and array."
            )
        resp = brain._create(config.ANTHROPIC_MODEL, BRIEFING_PROMPT, json.dumps(request),
                             max_tokens=8000)
        try:
            candidate = brain._json_from(resp)
        except ValueError as exc:
            log.warning("briefing JSON attempt %d failed: %s", attempt + 1, exc)
            continue
        if isinstance(candidate, dict):
            out = candidate
            break
        log.warning("briefing JSON attempt %d returned %s", attempt + 1,
                    type(candidate).__name__)
    if out is None:
        log.error("briefing generation failed after two attempts")
        return None
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
        # A wider catch-up window survives deploys and a slow news cycle. The story key
        # remains the once-per-window guard, so repeated checks cannot duplicate a Block.
        if not (fire <= now < fire + datetime.timedelta(minutes=60)):
            continue
        key = f"briefing:{now:%Y-%m-%d}:{title.lower()}"
        if store.story_produced(con, key):
            continue
        payload = fetch_brief()
        if not payload:
            log.warning("no brief available for %s window", title)
            continue
        since = store.last_briefing_ts(con) or (now.timestamp() - 18 * 3600)
        posts = build_thread(payload, title, store.wire_items_since(con, since))
        if not posts:
            continue
        from . import publisher
        # Post 1 is the link-free index (algo-safe opener); every later post carries its
        # own receipt link so the card renders on the relevant tweet (Brady 2026-08-29).
        # The model never writes URLs; we append verified ones, never to post 1.
        receipts = [p["receipt"] for p in posts if p.get("receipt")]
        texts = [
            p["text"] if i == 0 or not p.get("receipt") else f"{p['text']}\n\n{p['receipt']}"
            for i, p in enumerate(posts)
        ]
        publisher_backend = publisher.backend_name()
        mode, ref = publisher.publish_thread(texts, klass="briefing")
        store.log_post(con, key, None, "briefing", "\n\n".join(texts), receipts[0] if receipts else "",
                       mode, ref, publisher_backend=publisher_backend)
        log.info("briefing %s window: %s (%s)", title, mode, ref)
        return True
    return False
