"""Output: Nuelink REST staging/publishing + the daily tape file (always written).

Policy:
- No Nuelink config      -> tape only ("TAPE" mode).
- Nuelink configured     -> stage as DRAFT.
- AUTOPOST_ENABLED and class in AUTOPOST_CLASSES -> publish IMMEDIATE with the
  receipt URL as the delayed first comment. Secondary class NEVER auto-publishes.
The Nuelink API has no update/delete: a published mistake is corrected with a
follow-up post, never removed. That is charter, not just API limitation.
"""
import datetime
import logging

import httpx

from . import config

log = logging.getLogger("nbn.publisher")


def _backend() -> str:
    if config.TYPEFULLY_API_KEY and config.TYPEFULLY_SOCIAL_SET_ID:
        return "typefully"
    if config.NUELINK_API_KEY and config.NUELINK_BRAND_ID and config.NUELINK_COLLECTION_ID:
        return "nuelink"
    return "tape"


def _mode_for(klass: str) -> str:
    if _backend() == "tape":
        return "TAPE"
    if config.AUTOPOST_ENABLED and klass in config.AUTOPOST_CLASSES:
        return "IMMEDIATE"
    return "DRAFT"


def publish(post: str, receipt_url: str, klass: str, image: tuple = None) -> tuple:
    """Returns (mode, post_id_or_None). image: optional (bytes, file_name) chart from
    the source page, attached to the lead post (FRED links preview poorly on X)."""
    mode = _mode_for(klass)
    tape(post, receipt_url, klass, mode)
    if mode == "TAPE":
        return mode, None

    if _backend() == "typefully":
        from . import publisher_typefully
        media_id = publisher_typefully.upload_media(*image) if image else ""
        # Link ON the post so the card renders and readers click through (Brady 2026-08-29).
        ok, ref = publisher_typefully.publish_thread(
            [f"{post}\n\n{receipt_url}"], immediate=(mode == "IMMEDIATE"),
            lead_media_ids=[media_id] if media_id else None)
        return (mode, ref) if ok else ("TAPE", None)
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
        return mode, post_id
    except Exception as exc:  # noqa: BLE001 - a posting failure must not kill the loop
        log.error("nuelink publish failed (%s): %s", mode, exc)
        return "TAPE", None


def publish_thread(texts: list, klass: str) -> tuple:
    """Publish/stage an N-post thread (briefing threads). Returns (mode, ref)."""
    mode = _mode_for(klass)
    tape("\n\n---\n\n".join(texts), "(thread)", klass, mode)
    if mode == "TAPE":
        return mode, None
    if _backend() == "typefully":
        from . import publisher_typefully
        ok, ref = publisher_typefully.publish_thread(texts, immediate=(mode == "IMMEDIATE"))
        return (mode, ref) if ok else ("TAPE", None)
    return "TAPE", None  # nuelink cannot thread


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
