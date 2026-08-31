"""Output router: Typefully preferred, legacy Nuelink fallback, tape always written.

Policy:
- No publishing backend -> tape only ("TAPE" mode).
- Backend configured    -> stage as DRAFT.
- AUTOPOST_ENABLED and class in AUTOPOST_CLASSES -> publish IMMEDIATE with the
  receipt URL attached by the system. Secondary class NEVER auto-publishes.
Typefully is the deployed backend. Nuelink remains as a compatibility fallback for
single posts, but cannot publish threads. UNCERTAIN is never retried automatically;
FAILED is distinct from tape-only operation. Corrections are staged for human review.
"""
import datetime
import logging
import time

import httpx

from . import config

log = logging.getLogger("nbn.publisher")


def _backend() -> str:
    if config.TYPEFULLY_API_KEY and config.TYPEFULLY_SOCIAL_SET_ID:
        return "typefully"
    if config.NUELINK_API_KEY and config.NUELINK_BRAND_ID and config.NUELINK_COLLECTION_ID:
        return "nuelink"
    return "tape"


def backend_name() -> str:
    """Stable public name for recording delivery provenance with the output row."""
    return _backend()


def reconcile_publications(con) -> dict:
    """Best-effort Typefully-to-local publication reconciliation, rate-limited."""
    if _backend() != "typefully":
        return {"disabled": 1}
    from . import publisher_typefully, store
    now = time.time()
    try:
        last_attempt = float(store.kv_get(con, "publisher:last_attempt") or 0)
    except ValueError:
        last_attempt = 0
    if now - last_attempt < config.PUBLISH_RECONCILE_SECONDS:
        return {"rate_limited": 1}
    # Commit the attempt before the request so an outage does not cause a retry storm.
    store.kv_set(con, "publisher:last_attempt", str(now))
    try:
        records = publisher_typefully.list_published()
        stats = store.reconcile_typefully_publications(con, records, synced_at=time.time())
        log.info("Typefully publication sync: %s", stats)
        return stats
    except Exception as exc:  # noqa: BLE001 - reconciliation must never stop intake
        message = str(exc)[:200]
        store.kv_set(con, "publisher:last_error", message)
        log.warning("Typefully publication sync failed: %s", message)
        return {"error": message}


def _mode_for(klass: str) -> str:
    if _backend() == "tape":
        return "TAPE"
    # Observe mode is an operational safety rail: even a stale Railway autopost env
    # cannot publish while source-policy decisions are being inspected.
    if config.SOURCE_POLICY_MODE == "observe":
        return "DRAFT"
    if config.AUTOPOST_ENABLED and klass in config.AUTOPOST_CLASSES:
        return "IMMEDIATE"
    return "DRAFT"


def publish(post: str, receipt_url: str, klass: str, image: tuple = None,
            force_draft: bool = False) -> tuple:
    """Returns (mode, post_id_or_None). image: optional (bytes, file_name) chart from
    the source page, attached to the lead post (FRED links preview poorly on X).
    Operator overrides use force_draft so they can never become autonomous posts."""
    mode = _mode_for(klass)
    if force_draft and mode != "TAPE":
        mode = "DRAFT"
    if mode == "TAPE":
        tape(post, receipt_url, klass, mode)
        return mode, None

    if _backend() == "typefully":
        from . import publisher_typefully
        media_id = publisher_typefully.upload_media(*image) if image else ""
        # Link ON the post so the card renders and readers click through (Brady 2026-08-29).
        outcome, ref = publisher_typefully.publish_thread(
            [f"{post}\n\n{receipt_url}"], immediate=(mode == "IMMEDIATE"),
            lead_media_ids=[media_id] if media_id else None)
        actual = {
            publisher_typefully.PublishOutcome.CONFIRMED: "IMMEDIATE",
            publisher_typefully.PublishOutcome.STAGED: "DRAFT",
            publisher_typefully.PublishOutcome.FAILED: "FAILED",
            publisher_typefully.PublishOutcome.UNCERTAIN: "UNCERTAIN",
        }[outcome]
        tape(post, receipt_url, klass, actual)
        return actual, ref
    body = {
        "publishMode": mode,
        "caption": post,
        "comment": {"delay": 1, "comment": f"Source: {receipt_url}"},
    }
    url = (f"{config.NUELINK_BASE}/brands/{config.NUELINK_BRAND_ID}"
           f"/collections/{config.NUELINK_COLLECTION_ID}/posts")
    try:
        resp = httpx.post(
            url, json=body, timeout=30,
            headers={"Authorization": f"Bearer {config.NUELINK_API_KEY}"},
        )
        resp.raise_for_status()
        post_id = str(resp.json().get("data", {}).get("id", ""))
        log.info("nuelink %s created id=%s", mode, post_id)
        tape(post, receipt_url, klass, mode)
        return mode, post_id
    except Exception as exc:  # noqa: BLE001 - a posting failure must not kill the loop
        log.error("nuelink publish failed (%s): %s", mode, exc)
        tape(post, receipt_url, klass, "FAILED")
        return "FAILED", str(exc)[:200]


def publish_thread(texts: list, klass: str) -> tuple:
    """Publish/stage an N-post thread (briefing threads). Returns (mode, ref)."""
    mode = _mode_for(klass)
    if mode == "TAPE":
        tape("\n\n---\n\n".join(texts), "(thread)", klass, mode)
        return mode, None
    if _backend() == "typefully":
        from . import publisher_typefully
        outcome, ref = publisher_typefully.publish_thread(
            texts, immediate=(mode == "IMMEDIATE"))
        actual = {
            publisher_typefully.PublishOutcome.CONFIRMED: "IMMEDIATE",
            publisher_typefully.PublishOutcome.STAGED: "DRAFT",
            publisher_typefully.PublishOutcome.FAILED: "FAILED",
            publisher_typefully.PublishOutcome.UNCERTAIN: "UNCERTAIN",
        }[outcome]
        tape("\n\n---\n\n".join(texts), "(thread)", klass, actual)
        return actual, ref
    tape("\n\n---\n\n".join(texts), "(thread)", klass, "FAILED")
    return "FAILED", "nuelink cannot publish threads"


def tape(post: str, receipt_url: str, klass: str, mode: str):
    """Append every produced post to the daily tape file (the audit trail)."""
    config.TAPE_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.datetime.now(datetime.timezone.utc)
    path = config.TAPE_DIR / f"tape-{now:%Y-%m-%d}.md"
    entry = (f"\n---\n**{now:%H:%M:%S} UTC · {klass} · {mode}**\n\n"
             f"{post}\n\n> receipt: {receipt_url}\n")
    if not path.exists():
        path.write_text(f"# Next Block News tape — {now:%Y-%m-%d}\n")
    with path.open("a") as f:
        f.write(entry)
