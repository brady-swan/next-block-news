"""Typefully API v2 backend: post + receipt reply as a 2-post X thread.

Why Typefully over Nuelink/direct X API (researched 2026-08-29):
- Long X posts (>280, note tweets) work through it; the direct X API has a
  documented history of 403s on long posts even for Premium accounts.
- Threads work via API (Nuelink's API cannot thread), so the receipt rides as
  the second post of a thread instead of a delayed comment.
- Scheduled publishing supports receipt URLs and a poll-to-confirm read-back
  (Nuelink has no single-post read-back at all).
- Direct X API is pay-per-use since Feb 2026 and charges $0.20 per post
  containing a link — our receipt replies would eat ~$100/mo at target cadence.

Schema verified live 2026-08-29 (the public docs are wrong/stale): threads are an
explicit array — platforms.x = {"enabled": true, "posts": [{"text": ...}, ...]}.
"""
import datetime
import logging
import time
from enum import Enum
from urllib.parse import urlsplit

import httpx

from . import config

log = logging.getLogger("nbn.typefully")

BASE = "https://api.typefully.com/v2"


class PublishOutcome(str, Enum):
    """What is known after a Typefully create/publish attempt."""

    CONFIRMED = "confirmed"
    STAGED = "staged"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


def _headers():
    return {"Authorization": f"Bearer {config.TYPEFULLY_API_KEY}"}


def _timestamp(value):
    if not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.timestamp()


def _public_x_url(value) -> str:
    try:
        parsed = urlsplit(str(value or ""))
    except ValueError:
        return ""
    host = (parsed.hostname or "").lower().rstrip(".")
    if (parsed.scheme not in ("http", "https") or parsed.username or parsed.password
            or not (host in ("x.com", "twitter.com")
                    or host.endswith((".x.com", ".twitter.com")))):
        return ""
    return parsed.geturl()


def list_published(limit: int = 50) -> list[dict]:
    """Return normalized, definitively published Typefully drafts, newest first."""
    resp = httpx.get(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
        params={"status": "published", "sort": "-published_at", "limit": limit},
        headers=_headers(), timeout=30,
    )
    resp.raise_for_status()
    out = []
    for raw in resp.json().get("results", []):
        ref = str(raw.get("id") or "").strip()
        published_at = _timestamp(raw.get("published_at"))
        if raw.get("status") != "published" or not ref or published_at is None:
            log.warning("ignoring malformed Typefully published record id=%s", ref or "missing")
            continue
        out.append({
            "id": ref,
            "status": "published",
            "created_at": _timestamp(raw.get("created_at")),
            "published_at": published_at,
            "public_url": _public_x_url(raw.get("x_published_url")),
            "preview": str(raw.get("preview") or ""),
            "draft_title": str(raw.get("draft_title") or ""),
        })
    return out


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
    """Create a 2-post X thread. Returns (PublishOutcome, draft_id_or_error).
    image: optional (bytes, file_name) attached to the lead post (chart from the
    source page — FRED links preview poorly on X; Brady 2026-08-30)."""
    media_id = upload_media(*image) if image else ""
    return publish_thread([post, f"Source: {receipt_url}"], immediate,
                          lead_media_ids=[media_id] if media_id else None)


URL_RE = None  # set below


def publish_thread(texts: list, immediate: bool, lead_media_ids: list = None) -> tuple:
    """Create an N-post X thread. Returns (PublishOutcome, draft_id_or_error).

    Typefully blocks publish-now for drafts containing URLs (X policy, learned live
    2026-08-30). A definitive URL-policy rejection permits a linkless retry and then a
    linked human draft. An uncertain create/confirmation never permits another create.
    """
    # Probed 2026-08-30: publish_at:"now" rejects any draft containing a URL (X policy,
    # draft-wide), but a SCHEDULED post carries links fine. So autonomous publishing is
    # scheduled shortly ahead — links intact, autonomy intact, latency negligible.
    import re
    outcome, ref = _create(texts, immediate, lead_media_ids)
    if outcome is not PublishOutcome.FAILED or not immediate \
            or "URLs is blocked" not in str(ref):
        return outcome, ref
    # A definitive URL-policy rejection means no draft was created. Only then is a
    # second create safe. Ambiguous results never enter this fallback ladder.
    stripped = [t for t in (re.sub(r"\s*https?://\S+", "", t).rstrip() for t in texts) if t]
    outcome, ref = _create(stripped, immediate, lead_media_ids)
    if outcome in (PublishOutcome.CONFIRMED, PublishOutcome.UNCERTAIN):
        log.warning("published LINKLESS (URL policy hit even when scheduled)")
        return outcome, ref
    outcome, ref = _create(texts, immediate=False, lead_media_ids=lead_media_ids)
    log.warning("publishing blocked; staged linked DRAFT %s", ref)
    return outcome, ref


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
        if not draft_id:
            log.error("typefully create succeeded without a draft id")
            return PublishOutcome.UNCERTAIN, "missing draft id"
        if not immediate:
            return PublishOutcome.STAGED, draft_id
        return _confirm(draft_id), draft_id
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        log.error("typefully publish failed: %s | body: %s", exc, body)
        if exc.response.status_code >= 500:
            # A server-side error can still arrive after the create was accepted.
            return PublishOutcome.UNCERTAIN, f"{exc.response.status_code}: {body}"[:200]
        return PublishOutcome.FAILED, f"{exc.response.status_code}: {body}"[:200]
    except Exception as exc:  # noqa: BLE001
        # A transport failure during POST may happen after Typefully accepted the draft.
        # Retrying could duplicate a live scheduled post, so the outcome is uncertain.
        log.error("typefully create outcome uncertain: %s", exc)
        return PublishOutcome.UNCERTAIN, str(exc)[:200]


def schedule_draft(draft_id: str) -> PublishOutcome:
    """Promote one existing human-visible draft without creating a duplicate."""
    when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        seconds=config.PUBLISH_DELAY_SECONDS)
    try:
        resp = httpx.patch(
            f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
            json={"publish_at": when.strftime("%Y-%m-%dT%H:%M:%S+00:00")},
            headers=_headers(), timeout=30,
        )
        resp.raise_for_status()
        return _confirm(str(draft_id))
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        log.error("typefully draft promotion failed: %s | body: %s", exc, body)
        if exc.response.status_code >= 500:
            return PublishOutcome.UNCERTAIN
        return PublishOutcome.FAILED
    except Exception as exc:  # noqa: BLE001 - PATCH may have been accepted remotely
        log.error("typefully draft promotion outcome uncertain: %s", exc)
        return PublishOutcome.UNCERTAIN


def delete_draft(draft_id: str) -> bool:
    """Delete one precisely identified Typefully draft; 404 is already dismissed."""
    resp = httpx.delete(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
        headers=_headers(), timeout=30,
    )
    if resp.status_code == 404:
        return True
    resp.raise_for_status()
    return resp.status_code == 204


def _confirm(draft_id: str, attempts: int = 50):
    """Return a definitive or uncertain outcome without creating another draft."""
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
                return PublishOutcome.CONFIRMED
            if state not in ("in_progress", "scheduled", None):
                log.error("typefully draft %s unexpected state: %s", draft_id, state)
                return PublishOutcome.FAILED
        except Exception as exc:  # noqa: BLE001
            log.warning("typefully confirm poll failed: %s", exc)
        time.sleep(3)
    log.error("typefully draft %s publish not confirmed after polling", draft_id)
    return PublishOutcome.UNCERTAIN
