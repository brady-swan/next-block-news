"""Typefully API v2 backend: post + receipt reply as a 2-post X thread.

Why Typefully over Nuelink/direct X API (researched 2026-08-29):
- Long X posts (>280, note tweets) work through it; the direct X API has a
  documented history of 403s on long posts even for Premium accounts.
- Threads work via API (Nuelink's API cannot thread), so the receipt rides as
  the second post of a thread instead of a delayed comment.
- publish_at:"now" gives immediate publishing with a poll-to-confirm read-back
  (Nuelink has no single-post read-back at all).
- Direct X API is pay-per-use since Feb 2026 and charges $0.20 per post
  containing a link — our receipt replies would eat ~$100/mo at target cadence.

Schema verified live 2026-08-29 (the public docs are wrong/stale): threads are an
explicit array — platforms.x = {"enabled": true, "posts": [{"text": ...}, ...]}.
"""
import logging
import time

import httpx

from . import config

log = logging.getLogger("nbn.typefully")

BASE = "https://api.typefully.com/v2"


def _headers():
    return {"Authorization": f"Bearer {config.TYPEFULLY_API_KEY}"}


def upload_media(data: bytes, file_name: str) -> str:
    """Upload an image via the v2 media flow; returns media_id or '' (fail-safe).
    Flow (docs 2026-08-30): POST media/upload -> presigned PUT of raw bytes -> poll ready."""
    try:
        resp = httpx.post(
            f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/media/upload",
            json={"file_name": file_name}, headers=_headers(), timeout=30)
        resp.raise_for_status()
        j = resp.json()
        media_id, upload_url = j.get("media_id"), j.get("upload_url")
        if not (media_id and upload_url):
            log.warning("media upload: unexpected response %s", str(j)[:200])
            return ""
        put = httpx.put(upload_url, content=data, timeout=60)
        if put.status_code not in (200, 204):
            log.warning("media S3 PUT failed: %s", put.status_code)
            return ""
        for _ in range(15):
            st = httpx.get(
                f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/media/{media_id}",
                headers=_headers(), timeout=30)
            if st.status_code == 200 and st.json().get("status") == "ready":
                return media_id
            time.sleep(2)
        log.warning("media %s never became ready", media_id)
    except Exception as exc:  # noqa: BLE001 — an image must never block a post
        log.warning("media upload failed (%s): %s", file_name, exc)
    return ""


def publish(post: str, receipt_url: str, immediate: bool, image: tuple = None) -> tuple:
    """Create a 2-post X thread (post, receipt). Returns (ok, draft_id_or_error).
    image: optional (bytes, file_name) attached to the lead post (chart from the
    source page — FRED links preview poorly on X; Brady 2026-08-30)."""
    media_id = upload_media(*image) if image else ""
    return publish_thread([post, f"Source: {receipt_url}"], immediate,
                          lead_media_ids=[media_id] if media_id else None)


URL_RE = None  # set below


def publish_thread(texts: list, immediate: bool, lead_media_ids: list = None) -> tuple:
    """Create an N-post X thread. Returns (ok, draft_id_or_error).

    Typefully blocks publish-now for drafts containing URLs (X policy, learned live
    2026-08-30). Ladder: try as-is -> retry with links isolated in a trailing receipt
    post -> retry linkless -> stage as DRAFT with links intact for a human tap.
    """
    # Probed 2026-08-30: publish_at:"now" rejects any draft containing a URL (X policy,
    # draft-wide), but a SCHEDULED post carries links fine. So autonomous publishing is
    # "scheduled ~90s out" — links intact, autonomy intact, latency negligible.
    import re
    ok, ref = _create(texts, immediate, lead_media_ids)
    if ok or not immediate or "URLs is blocked" not in str(ref):
        return ok, ref
    # Policy changed on us? Last resorts: linkless now, then a staged linked draft.
    stripped = [t for t in (re.sub(r"\s*https?://\S+", "", t).rstrip() for t in texts) if t]
    ok, ref = _create(stripped, immediate, lead_media_ids)
    if ok:
        log.warning("published LINKLESS (URL policy hit even when scheduled)")
        return ok, ref
    ok, ref = _create(texts, immediate=False, lead_media_ids=lead_media_ids)
    log.warning("publishing blocked; staged linked DRAFT %s", ref)
    return ok, ref


def _create(texts: list, immediate: bool, lead_media_ids: list = None) -> tuple:
    import datetime
    posts = [{"text": t} for t in texts]
    if lead_media_ids:
        posts[0]["media_ids"] = lead_media_ids
    body = {
        "platforms": {"x": {"enabled": True, "posts": posts}},
        "draft_title": texts[0][:60],
    }
    if immediate:
        # "Immediate" = scheduled PUBLISH_DELAY seconds out: publish_at:"now" rejects
        # drafts containing URLs, scheduled posts don't (probed 2026-08-30).
        when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            seconds=config.PUBLISH_DELAY_SECONDS)
        body["publish_at"] = when.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    try:
        resp = httpx.post(
            f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
            json=body, headers=_headers(), timeout=30,
        )
        resp.raise_for_status()
        draft = resp.json()
        draft_id = str(draft.get("id", ""))
        if immediate:
            _confirm(draft_id)
        return True, draft_id
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        log.error("typefully publish failed: %s | body: %s", exc, body)
        return False, f"{exc.response.status_code}: {body}"[:200]
    except Exception as exc:  # noqa: BLE001
        log.error("typefully publish failed: %s", exc)
        return False, str(exc)[:200]


def _confirm(draft_id: str, attempts: int = 50):
    """Poll until publish_state is finished; log (never raise) on anything else."""
    for _ in range(attempts):
        try:
            resp = httpx.get(
                f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
                headers=_headers(), timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            state = data.get("publish_state")
            if state == "finished" or data.get("published_at"):
                log.info("typefully draft %s published", draft_id)
                return
            if state not in ("in_progress", "scheduled", None):
                log.error("typefully draft %s unexpected state: %s", draft_id, state)
                return
        except Exception as exc:  # noqa: BLE001
            log.warning("typefully confirm poll failed: %s", exc)
        time.sleep(3)
    log.error("typefully draft %s publish not confirmed after polling", draft_id)
