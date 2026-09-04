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
import copy
import datetime
import logging
import re
import time
from enum import Enum
from urllib.parse import urlsplit

import httpx

from . import config

log = logging.getLogger("nbn.typefully")

BASE = "https://api.typefully.com/v2"
FEEDBACK_DRAFT_LIMIT = 30
FEEDBACK_PAGES_PER_DRAFT = 2
FEEDBACK_THREADS_PER_PAGE = 50
FEEDBACK_TOTAL_THREADS = 100
FEEDBACK_COMMENTS_PER_THREAD = 20
FEEDBACK_SELECTED_TEXT_CHARS = 1000
FEEDBACK_COMMENT_TEXT_CHARS = 2000
FEEDBACK_AUTHOR_CHARS = 120
FEEDBACK_DRAFT_TEXT_CHARS = 4000


class PublishOutcome(str, Enum):
    """What is known after a Typefully create/publish attempt."""

    CONFIRMED = "confirmed"
    STAGED = "staged"
    FAILED = "failed"
    UNCERTAIN = "uncertain"


def get_draft(draft_id: str) -> dict:
    """Return one exact Typefully object; 404 is represented, not retried."""
    resp = httpx.get(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
        headers=_headers(), timeout=30,
    )
    if resp.status_code == 404:
        return {"id": str(draft_id), "status": "deleted", "_http_status": 404}
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError("Typefully draft response is not an object")
    return data


def _feedback_draft_id(value) -> str:
    """Validate the numeric path component documented by Typefully's comments API."""
    draft_id = str(value or "").strip()
    if not re.fullmatch(r"[1-9][0-9]{0,19}", draft_id):
        raise ValueError("Typefully draft ID must be a positive integer")
    return draft_id


def get_draft_for_feedback(draft_id: str) -> dict:
    """Read one marker-free draft for display only; never use this object for PATCH."""
    draft_id = _feedback_draft_id(draft_id)
    resp = httpx.get(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
        params={"exclude_comment_markers": "true"}, headers=_headers(), timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict):
        raise TypeError("Typefully draft response is not an object")
    return data


def list_recent_drafts(limit: int = 50) -> list[dict]:
    """Bounded recent-object list used only for ambiguous-create reconciliation."""
    resp = httpx.get(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
        params={"sort": "-created_at", "limit": max(1, min(int(limit), 50))},
        headers=_headers(), timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json().get("results", [])
    return rows if isinstance(rows, list) else []


def list_comment_threads(draft_id: str, *, status: str = "unresolved",
                         limit: int = FEEDBACK_THREADS_PER_PAGE,
                         offset: int = 0) -> list[dict]:
    """Return one bounded, normalized comments page using GET requests only."""
    draft_id = _feedback_draft_id(draft_id)
    if status not in {"unresolved", "resolved", "all"}:
        raise ValueError("invalid Typefully comment status")
    try:
        safe_limit = max(1, min(int(limit), FEEDBACK_THREADS_PER_PAGE))
        safe_offset = max(0, int(offset))
    except (TypeError, ValueError) as exc:
        raise ValueError("comment pagination must use integers") from exc
    resp = httpx.get(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/"
        f"{draft_id}/comment-threads",
        params={"status": status, "limit": safe_limit, "offset": safe_offset},
        headers=_headers(), timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not isinstance(payload, dict):
        raise TypeError("Typefully comment response is not an object")
    rows = payload.get("results", [])
    if not isinstance(rows, list):
        raise TypeError("Typefully comment results are not a list")
    out = []
    for raw in rows[:safe_limit]:
        if not isinstance(raw, dict):
            continue
        comments = []
        raw_comments = raw.get("comments") or []
        if not isinstance(raw_comments, list):
            raw_comments = []
        for comment in raw_comments[:FEEDBACK_COMMENTS_PER_THREAD]:
            if not isinstance(comment, dict):
                continue
            user = comment.get("user") or {}
            if not isinstance(user, dict):
                user = {}
            comments.append({
                "id": str(comment.get("id") or "")[:128],
                "text": str(comment.get("text") or "")[:FEEDBACK_COMMENT_TEXT_CHARS],
                "created_at": str(comment.get("created_at") or "")[:64],
                "author": str(user.get("name") or "")[:FEEDBACK_AUTHOR_CHARS],
            })
        out.append({
            "id": str(raw.get("id") or "")[:128],
            "draft_id": draft_id,
            "platform": str(raw.get("platform") or "")[:32],
            "status": str(raw.get("status") or "")[:32],
            "selected_text": str(raw.get("selected_text") or "")[
                :FEEDBACK_SELECTED_TEXT_CHARS
            ],
            "comments": comments,
        })
    return out


def collect_recent_feedback(*, status: str = "unresolved",
                            draft_limit: int = FEEDBACK_DRAFT_LIMIT) -> list[dict]:
    """Collect a tightly bounded read-only view of comments on recent drafts."""
    if status not in {"unresolved", "resolved", "all"}:
        raise ValueError("invalid Typefully comment status")
    try:
        safe_draft_limit = max(1, min(int(draft_limit), FEEDBACK_DRAFT_LIMIT))
    except (TypeError, ValueError) as exc:
        raise ValueError("draft limit must be an integer") from exc
    drafts = list_recent_drafts(limit=safe_draft_limit)
    out = []
    threads_left = FEEDBACK_TOTAL_THREADS
    for raw_draft in drafts[:safe_draft_limit]:
        if threads_left <= 0:
            break
        try:
            draft_id = _feedback_draft_id(raw_draft.get("id"))
        except (AttributeError, ValueError):
            continue
        threads = []
        for page in range(FEEDBACK_PAGES_PER_DRAFT):
            page_limit = min(FEEDBACK_THREADS_PER_PAGE, threads_left)
            page_rows = list_comment_threads(
                draft_id, status=status, limit=page_limit,
                offset=page * FEEDBACK_THREADS_PER_PAGE,
            )
            threads.extend(page_rows[:threads_left])
            threads_left -= min(len(page_rows), threads_left)
            if len(page_rows) < page_limit or threads_left <= 0:
                break
        if not threads:
            continue
        display = get_draft_for_feedback(draft_id)
        texts = draft_x_texts(display) or []
        out.append({
            "draft_id": draft_id,
            "created_at": str(raw_draft.get("created_at") or "")[:64],
            "title": str(raw_draft.get("draft_title") or "")[:200],
            "draft_text": "\n\n---\n\n".join(texts)[:FEEDBACK_DRAFT_TEXT_CHARS],
            "threads": threads,
        })
    return out


def _has_comment_marker(value) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if "comment" in str(key).casefold() and bool(child):
                return True
            if _has_comment_marker(child):
                return True
    elif isinstance(value, list):
        return any(_has_comment_marker(child) for child in value)
    return False


def draft_x_texts(raw: dict) -> list[str] | None:
    try:
        x = raw["platforms"]["x"]
        posts = x["posts"]
    except (KeyError, TypeError):
        return None
    if not isinstance(x, dict) or x.get("enabled") is not True or not isinstance(posts, list):
        return None
    texts = []
    for post in posts:
        if not isinstance(post, dict) or not isinstance(post.get("text"), str):
            return None
        texts.append(post["text"])
    return texts


def replace_draft(draft_id: str, prior_texts: list[str], desired_texts: list[str]) -> tuple:
    """Edit only an untouched Typefully X draft; never retry an ambiguous PATCH."""
    try:
        raw = get_draft(str(draft_id))
        status = str(raw.get("status") or "").casefold()
        if status == "deleted":
            return PublishOutcome.FAILED, "deleted"
        if status != "draft":
            return PublishOutcome.FAILED, f"non_editable:{status or 'unknown'}"
        if str(raw.get("social_set_id") or config.TYPEFULLY_SOCIAL_SET_ID) \
                != str(config.TYPEFULLY_SOCIAL_SET_ID):
            return PublishOutcome.FAILED, "wrong_social_set"
        if _has_comment_marker(raw):
            return PublishOutcome.FAILED, "comment_marked"
        texts = draft_x_texts(raw)
        if texts is None or texts != [str(value) for value in prior_texts]:
            return PublishOutcome.FAILED, "remote_modified"
        x = raw.get("platforms", {}).get("x", {})
        if set(x) - {"enabled", "posts", "settings"}:
            return PublishOutcome.FAILED, "unexpected_x_structure"
        allowed_post = {"text", "media_ids", "quote_post_url", "subscribers"}
        posts = x.get("posts") or []
        if len(posts) != len(desired_texts) or any(set(post) - allowed_post for post in posts):
            return PublishOutcome.FAILED, "unexpected_post_structure"
        updated_x = copy.deepcopy(x)
        for post, text in zip(updated_x["posts"], desired_texts):
            post["text"] = str(text)
        resp = httpx.patch(
            f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
            json={"platforms": {"x": updated_x}}, headers=_headers(), timeout=30,
        )
        resp.raise_for_status()
        confirmed = get_draft(str(draft_id))
        if draft_x_texts(confirmed) == [str(value) for value in desired_texts] \
                and str(confirmed.get("status") or "").casefold() == "draft":
            return PublishOutcome.STAGED, str(draft_id)
        return PublishOutcome.UNCERTAIN, "patch_confirmation_mismatch"
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return PublishOutcome.FAILED, "deleted"
        if exc.response.status_code >= 500:
            return PublishOutcome.UNCERTAIN, f"{exc.response.status_code}: {exc.response.text[:200]}"
        return PublishOutcome.FAILED, f"{exc.response.status_code}: {exc.response.text[:200]}"
    except Exception as exc:  # noqa: BLE001 - PATCH may have reached Typefully
        log.error("typefully draft replacement outcome uncertain: %s", exc)
        return PublishOutcome.UNCERTAIN, str(exc)[:200]


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


def list_analytics_posts(lookback_days: int = 3, limit: int = 100) -> list[dict]:
    """Return normalized X performance supplied by Typefully's batched analytics API."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    start = today - datetime.timedelta(days=max(1, min(lookback_days, 30)))
    resp = httpx.get(
        f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/analytics/x/posts",
        params={
            "start_date": start.isoformat(), "end_date": today.isoformat(),
            "include_replies": "false", "limit": max(1, min(limit, 100)),
        },
        headers=_headers(), timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json().get("results", [])
    out = []

    def count(value):
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return None

    for raw in rows if isinstance(rows, list) else []:
        metrics = raw.get("metrics") or {}
        engagement = metrics.get("engagement") or {}
        draft_id = str(raw.get("draft_id") or "").strip()
        if not draft_id:
            continue
        out.append({
            "draft_id": draft_id,
            "post_id": str(raw.get("post_id") or "").strip(),
            "created_at": _timestamp(raw.get("created_at")),
            "public_url": _public_x_url(raw.get("url")),
            "performance": {
                "impressions": count(metrics.get("impressions")),
                "likes": count(engagement.get("likes")),
                "reposts": count(engagement.get("shares")),
                "comments": count(engagement.get("comments")),
                "quotes": count(engagement.get("quotes")),
                "saves": count(engagement.get("saves")),
                "profile_clicks": count(engagement.get("profile_clicks")),
                "link_clicks": count(engagement.get("link_clicks")),
                "total_engagement": count(engagement.get("total")),
            },
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


def publish_thread(texts: list, immediate: bool, lead_media_ids: list = None,
                   allow_url_fallback: bool = True) -> tuple:
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
    if outcome is not PublishOutcome.FAILED or not immediate or not allow_url_fallback \
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
            return _confirm_staged_create(draft_id, texts), draft_id
        return _confirm(draft_id, expected_texts=texts), draft_id
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


def _confirm_staged_create(draft_id: str, expected_texts: list[str]) -> PublishOutcome:
    """Read back a successful staged create; any doubt must suppress another create."""
    try:
        confirmed = get_draft(draft_id)
        if str(confirmed.get("status") or "").casefold() == "draft" \
                and draft_x_texts(confirmed) == [str(value) for value in expected_texts]:
            return PublishOutcome.STAGED
        log.error("typefully draft %s create content confirmation mismatch", draft_id)
    except Exception as exc:  # noqa: BLE001 - POST already returned a remote ID
        log.error("typefully draft %s create confirmation failed: %s", draft_id, exc)
    return PublishOutcome.UNCERTAIN


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


def _confirm(draft_id: str, attempts: int = 50,
             expected_texts: list[str] | None = None):
    """Return a definitive or uncertain outcome without creating another draft."""
    for _ in range(attempts):
        try:
            resp = httpx.get(
                f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
                headers=_headers(), timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if expected_texts is not None \
                    and draft_x_texts(data) != [str(value) for value in expected_texts]:
                log.error("typefully draft %s content confirmation mismatch", draft_id)
                return PublishOutcome.UNCERTAIN
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
