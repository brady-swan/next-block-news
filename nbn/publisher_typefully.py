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


def publish(post: str, receipt_url: str, immediate: bool) -> tuple:
    """Create a 2-post X thread (post, receipt). Returns (ok, draft_id_or_error)."""
    return publish_thread([post, f"Source: {receipt_url}"], immediate)


URL_RE = None  # set below


def publish_thread(texts: list, immediate: bool) -> tuple:
    """Create an N-post X thread. Returns (ok, draft_id_or_error).

    Typefully blocks publish-now for drafts containing URLs (X policy, learned live
    2026-08-30). Ladder: try as-is -> retry with links isolated in a trailing receipt
    post -> retry linkless -> stage as DRAFT with links intact for a human tap.
    """
    import re
    ok, ref = _create(texts, immediate)
    if ok or not immediate or "URLs is blocked" not in str(ref):
        return ok, ref
    # Probed 2026-08-30: the URL block is DRAFT-WIDE (a link in any thread post 403s),
    # so the only autonomous rung is linkless. Receipt lives in the tape/Desk Report;
    # a human adds the link as a reply. Inline attempt stays first in case X relaxes.
    stripped = [t for t in (re.sub(r"\s*https?://\S+", "", t).rstrip() for t in texts) if t]
    ok, ref = _create(stripped, immediate)
    if ok:
        log.warning("published LINKLESS (X URL policy); receipt in tape - add as reply")
        return ok, ref
    ok, ref = _create(texts, immediate=False)
    log.warning("publish-now blocked; staged linked DRAFT %s", ref)
    return ok, ref


def _create(texts: list, immediate: bool) -> tuple:
    body = {
        "platforms": {"x": {"enabled": True, "posts": [{"text": t} for t in texts]}},
        "draft_title": texts[0][:60],
    }
    if immediate:
        body["publish_at"] = "now"
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


def _confirm(draft_id: str, attempts: int = 10):
    """Poll until publish_state is finished; log (never raise) on anything else."""
    for _ in range(attempts):
        try:
            resp = httpx.get(
                f"{BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{draft_id}",
                headers=_headers(), timeout=15,
            )
            resp.raise_for_status()
            state = resp.json().get("publish_state")
            if state == "finished":
                log.info("typefully draft %s published", draft_id)
                return
            if state not in ("in_progress", None):
                log.error("typefully draft %s unexpected state: %s", draft_id, state)
                return
        except Exception as exc:  # noqa: BLE001
            log.warning("typefully confirm poll failed: %s", exc)
        time.sleep(3)
    log.error("typefully draft %s publish not confirmed after polling", draft_id)
