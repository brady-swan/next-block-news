"""EIC discovery intake and the legacy Marketing Node briefing-thread builder.

The Node's read API (GET /api/daily-intel/latest, bearer read token) serves the
Brady-tuned brief: theme, body_md with inline citations, must_know, more_reads.
Fresh cited reads normally enter the one-off newsroom. The opt-in legacy path rewrites the
brief into a wire-voice X thread with these hard requirements:
- STRIP every Swan reference (brand separation is the point of the handle).
- Facts and links only from the brief itself; the model never adds a URL.
- One thread per window per day (DB-guarded).
"""
import datetime
import json
import logging
import re
from zoneinfo import ZoneInfo

import httpx

from . import config, lint, sources, store

log = logging.getLogger("nbn.briefing")
EDITORIAL_TZ = ZoneInfo("America/Chicago")

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


def _as_utc(value) -> datetime.datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    return parsed.astimezone(datetime.timezone.utc)


def _freshness_issue(data: dict, window_title: str,
                     now: datetime.datetime | None = None) -> str | None:
    """Return why the Node payload cannot safely back this Block, or None."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.timezone.utc)
    now = now.astimezone(datetime.timezone.utc)
    run = data.get("run") if isinstance(data.get("run"), dict) else {}
    brief = data.get("daily_brief") if isinstance(data.get("daily_brief"), dict) else {}
    expected_date = now.astimezone(EDITORIAL_TZ).date().isoformat()
    expected_window = window_title.strip().lower()

    if str(run.get("selected_date") or "") != expected_date:
        return f"Daily Intel date is {run.get('selected_date')}, expected {expected_date}"
    if str(brief.get("date") or "") != expected_date:
        return f"EIC brief date is {brief.get('date')}, expected {expected_date}"
    if str(run.get("run_window") or "").lower() != expected_window:
        return f"Daily Intel window is {run.get('run_window')}, expected {expected_window}"

    latest_run_id = run.get("run_id")
    source_run_id = brief.get("source_daily_intel_run_id")
    if not latest_run_id or source_run_id != latest_run_id:
        return f"EIC brief used Daily Intel run {source_run_id}, latest is {latest_run_id}"
    if str(brief.get("source_daily_intel_run_window") or "").lower() != expected_window:
        return "EIC brief provenance does not match the requested window"

    generated_at = _as_utc(brief.get("generated_at"))
    source_received_at = _as_utc(brief.get("source_daily_intel_received_at"))
    run_received_at = _as_utc(run.get("received_at"))
    if generated_at is None or source_received_at is None or run_received_at is None:
        return "EIC brief freshness timestamps are missing or invalid"
    if source_received_at != run_received_at:
        return "EIC brief source timestamp does not match the latest Daily Intel run"
    if generated_at < source_received_at:
        return "EIC brief predates its source Daily Intel run"
    age = (now - generated_at).total_seconds()
    if age < -300:
        return "EIC brief timestamp is in the future"
    if age > config.BRIEFING_MAX_AGE_SECONDS:
        return f"EIC brief is stale ({int(age)}s old)"
    return None


def fetch_brief(window_title: str, now: datetime.datetime | None = None):
    try:
        resp = httpx.get(
            f"{config.NODE_BASE_URL}/api/daily-intel/latest",
            headers=_node_headers(), timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("daily_brief"):
            return None
        issue = _freshness_issue(data, window_title, now)
        if issue:
            log.warning("brief rejected for %s Block: %s", window_title, issue)
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        log.error("brief fetch failed: %s", exc)
        return None


def _brief_text(brief: dict) -> str:
    parts = [str(brief.get("theme", "")), str(brief.get("body_md", ""))]
    for mk in brief.get("must_know", []) or []:
        parts.append(f"{mk.get('title', '')} — {mk.get('summary', '')}")
    return "\n\n".join(p for p in parts if p)


def _flat(value):
    """Flatten the read API's bounded text wrappers."""
    if isinstance(value, dict) and "text" in value:
        return value["text"]
    if isinstance(value, list):
        return [_flat(item) for item in value]
    if isinstance(value, dict):
        return {key: _flat(item) for key, item in value.items()}
    return value


def _discovery_items(brief_payload: dict, window_title: str) -> list[dict]:
    """Project cited EIC reads into ordinary, untrusted one-off candidates."""
    brief = _flat(brief_payload.get("daily_brief") or {})
    context = json.dumps({
        "untrusted_discovery_context": True,
        "origin": "marketing_node_eic_brief",
        "eic_window": window_title.lower(),
        "eic_brief_workflow_run_id": brief.get("workflow_run_id"),
        "source_daily_intel_run_id": brief.get("source_daily_intel_run_id"),
        "theme": str(brief.get("theme") or "")[:240] or None,
    }, separators=(",", ":"), ensure_ascii=False)
    items, seen = [], set()
    for raw in brief.get("more_reads") or []:
        row = raw if isinstance(raw, dict) else {"title": str(raw)}
        refs = row.get("source_refs") if isinstance(row.get("source_refs"), list) else []
        if row.get("url"):
            refs = [row, *refs]
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            url = str(ref.get("url") or ref.get("canonical_url") or "").strip()
            if not url:
                continue
            try:
                sources._assert_public_http_url(url)
            except sources.UnsafeSourceURL:
                continue
            key = store.canonical_discovery_key(url)
            if not key or key in seen:
                continue
            title = str(
                ref.get("title") or ref.get("headline") or row.get("title") or ""
            ).strip()
            publisher = str(
                ref.get("publisher") or ref.get("outlet") or ref.get("source")
                or "Marketing Node"
            ).strip()
            if not title:
                continue
            items.append({
                "source": publisher[:120],
                "title": " ".join(title.split())[:240],
                "url": url,
                "published": str(
                    ref.get("published_at") or ref.get("observed_at") or ""
                )[:100],
                "summary": "",
                "discovery_origin": "marketing_node",
                "discovery_context": context,
            })
            seen.add(key)
            if len(items) >= 12:
                return items
    return items


def maybe_ingest_discovery(con) -> bool:
    """Once per fresh EIC window, add its cited reads to the one-off intake."""
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() >= 5:
        return False
    for hhmm, title in config.EIC_DISCOVERY_SCHEDULE:
        h, m = hhmm.split(":")
        fire = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        if not (fire <= now < fire + datetime.timedelta(minutes=60)):
            continue
        key = f"node:eic_discovery:{now:%Y-%m-%d}:{title.lower()}"
        if store.kv_get(con, key):
            return False
        payload = fetch_brief(title, now=now)
        if not payload:
            return False
        items = _discovery_items(payload, title)
        inserted = store.upsert_new_items(con, items)
        store.kv_set(con, key, json.dumps({
            "seen": len(items), "inserted": len(inserted), "at": now.isoformat(),
        }, separators=(",", ":")))
        log.info("EIC %s discovery: %d cited reads, %d new", title, len(items), len(inserted))
        return True
    return False


def _brief_urls(text: str) -> set:
    return set(re.findall(r"https?://[^\s)\"']+", text))


def build_thread(brief_payload: dict, window_title: str, wire_items: list = None):
    """Returns [{'text':..., 'receipt':...}] or None."""
    from . import brain  # late import to avoid cycle
    wire_items = wire_items or []
    brief = brief_payload["daily_brief"]
    brief = _flat(brief)
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
    retry_reason = ""
    for attempt in range(2):
        request = dict(payload)
        if attempt:
            request["retry_instruction"] = (
                "The previous response failed. Return a compact complete JSON object with 5-7 "
                "concise posts; close every string and array. Do not add or alter any fact, "
                f"number, name, quote, or URL. Fix exactly this: {retry_reason[:1200]}"
            )
        resp = brain._create(config.ANTHROPIC_MODEL, BRIEFING_PROMPT, json.dumps(request),
                             max_tokens=8000)
        try:
            candidate = brain._json_from(resp)
        except ValueError as exc:
            log.warning("briefing JSON attempt %d failed: %s", attempt + 1, exc)
            retry_reason = str(exc)
            continue
        if not isinstance(candidate, dict):
            retry_reason = f"top-level response was {type(candidate).__name__}, not an object"
            log.warning("briefing JSON attempt %d %s", attempt + 1, retry_reason)
            continue
        posts = candidate.get("posts") or []
        if not (4 <= len(posts) <= 10):
            retry_reason = f"thread contained {len(posts)} posts; required 5-9"
            log.warning("briefing attempt %d: %s", attempt + 1, retry_reason)
            continue
        # Gates: lint each post; receipts must be URLs from the brief; no Swan leakage.
        gate_failures = []
        for index, p in enumerate(posts):
            text = p.get("text", "")
            errors = lint.check(text, {"_source_text": source_text}, {"class": "briefing"})
            errors = [e for e in errors if not e.startswith("news post must start")]
            if re.search(r"\bswan\b", text, re.I):
                errors.append("Swan reference leaked")
            r = p.get("receipt")
            if r and r not in allowed_urls:
                errors.append(f"receipt not in brief: {r}")
            if errors:
                gate_failures.append(f"post {index + 1}: {'; '.join(errors)}")
                log.warning("briefing post failed gates: %s | %s", errors, text[:80])
        if gate_failures:
            retry_reason = " | ".join(gate_failures)
            continue
        return posts
    log.error("briefing generation failed after two attempts: %s", retry_reason[:300])
    return None


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
        payload = fetch_brief(title, now=now)
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
