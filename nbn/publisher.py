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
        stats["analytics"] = _refresh_analytics(con, publisher_typefully, store, now)
        log.info("Typefully publication sync: %s", stats)
        return stats
    except Exception as exc:  # noqa: BLE001 - reconciliation must never stop intake
        message = str(exc)[:200]
        store.kv_set(con, "publisher:last_error", message)
        log.warning("Typefully publication sync failed: %s", message)
        return {"error": message}


def reconcile_mutations(con) -> dict:
    """Bounded restart recovery for Typefully operations; never repeats a mutation."""
    if _backend() != "typefully":
        return {"disabled": 1}
    from . import publisher_typefully, store
    now = time.time()
    try:
        last = float(store.kv_get(con, "publisher:mutation_reconcile_last") or 0)
    except ValueError:
        last = 0
    if now - last < 300:
        return {"rate_limited": 1}
    store.kv_set(con, "publisher:mutation_reconcile_last", str(now))
    pending = [row for row in store.pending_publisher_mutations(con, limit=20)
               if row["state"] in {"prepared", "in_flight", "ambiguous"}]
    stats = {"checked": 0, "confirmed": 0, "review": 0, "failed": 0, "deferred": 0}
    if not pending:
        return stats
    create_rows = [row for row in pending if row["operation"] == "create"
                   and row["state"] != "prepared"]
    recent = []
    if create_rows:
        try:
            recent = publisher_typefully.list_recent_drafts(limit=50)
        except Exception as exc:  # noqa: BLE001 - keep intents protected for next run
            log.warning("Typefully mutation list reconciliation deferred: %s", exc)
            stats["deferred"] += len(create_rows)
    gets_left = 5
    for row in pending:
        stats["checked"] += 1
        token, version = row["owner_token"], int(row["version"])
        if row["state"] == "prepared":
            if store.transition_publisher_mutation(
                    con, row["mutation_id"], token, version, "definite_failure",
                    error_kind="crash_before_network", error_message="intent never entered flight"):
                stats["failed"] += 1
            continue
        if row["operation"] == "create":
            if not recent:
                stats["deferred"] += 1
                continue
            matches = []
            for raw in recent[:100]:
                created = publisher_typefully._timestamp(raw.get("created_at"))
                if created is None or abs(created - float(row["created_at"])) > 1800:
                    continue
                texts = publisher_typefully.draft_x_texts(raw)
                if texts and store.x_thread_fingerprint(texts) == row["desired_fingerprint"]:
                    matches.append(raw)
            if len(matches) == 1:
                remote = matches[0]
                ref = str(remote.get("id") or "")
                remote_status = str(remote.get("status") or "draft").casefold()
                mode = "DRAFT" if remote_status == "draft" \
                    and row["intended_mode"] == "DRAFT" else "IMMEDIATE"
                store.finalize_publisher_mutation(
                    con, row["mutation_id"], token, version, mode=mode,
                    provider_ref=ref, publisher_status=remote_status,
                )
                stats["confirmed"] += 1
            else:
                store.transition_publisher_mutation(
                    con, row["mutation_id"], token, version, "needs_owner_review",
                    error_kind="create_reconciliation_ambiguous",
                    error_message=f"exact matches: {len(matches)}",
                )
                stats["review"] += 1
            continue
        if gets_left <= 0:
            stats["deferred"] += 1
            continue
        gets_left -= 1
        try:
            remote = publisher_typefully.get_draft(str(row["target_draft_id"] or ""))
        except Exception as exc:  # noqa: BLE001
            log.warning("Typefully mutation GET reconciliation deferred: %s", exc)
            stats["deferred"] += 1
            continue
        status = str(remote.get("status") or "").casefold()
        if status == "deleted":
            store.transition_publisher_mutation(
                con, row["mutation_id"], token, version, "definite_failure",
                error_kind="remote_deleted", error_message="Typefully returned 404",
            )
            if row["target_post_id"]:
                con.execute(
                    "UPDATE posts SET publisher_status='deleted',publisher_synced_at=? WHERE id=?",
                    (time.time(), int(row["target_post_id"])),
                )
                con.commit()
            stats["failed"] += 1
            continue
        texts = publisher_typefully.draft_x_texts(remote)
        fingerprint = store.x_thread_fingerprint(texts) if texts else ""
        if fingerprint == row["desired_fingerprint"]:
            mode = "DRAFT" if status == "draft" else "IMMEDIATE"
            store.finalize_publisher_mutation(
                con, row["mutation_id"], token, version, mode=mode,
                provider_ref=str(row["target_draft_id"] or ""), publisher_status=status,
            )
            stats["confirmed"] += 1
        elif fingerprint == (row["prior_fingerprint"] or "") \
                and time.time() - float(row["updated_at"] or 0) >= 60:
            store.transition_publisher_mutation(
                con, row["mutation_id"], token, version, "definite_failure",
                error_kind="patch_not_applied", error_message="remote content remains prior",
            )
            stats["failed"] += 1
        elif fingerprint == (row["prior_fingerprint"] or ""):
            stats["deferred"] += 1
        else:
            store.transition_publisher_mutation(
                con, row["mutation_id"], token, version, "needs_owner_review",
                error_kind="remote_content_unrelated",
                error_message="remote content matches neither prior nor desired fingerprint",
            )
            stats["review"] += 1
    return stats


def resolve_mutation(con, mutation_id: str, owner_token: str, version: int,
                     resolution: str, remote_draft_id: str = "") -> dict:
    """Desk-facing owner resolution; no branch retries a remote mutation."""
    from . import publisher_typefully, store
    row = store.publisher_mutation(con, mutation_id)
    if not row or row["owner_token"] != str(owner_token) or int(row["version"]) != int(version):
        return {"ok": False, "reason": "stale or unknown mutation"}
    if resolution != "bind_remote_draft":
        return store.owner_resolve_publisher_mutation(
            con, mutation_id, owner_token, version, resolution
        )
    if row["state"] not in {"ambiguous", "needs_owner_review"}:
        return {"ok": False, "reason": "mutation is not awaiting owner review"}
    if not remote_draft_id or _backend() != "typefully":
        return {"ok": False, "reason": "a Typefully draft ID is required"}
    try:
        remote = publisher_typefully.get_draft(str(remote_draft_id)[:200])
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "reason": f"Typefully lookup failed: {exc}"[:300]}
    if str(remote.get("social_set_id") or config.TYPEFULLY_SOCIAL_SET_ID) \
            != str(config.TYPEFULLY_SOCIAL_SET_ID):
        return {"ok": False, "reason": "draft belongs to another social set"}
    texts = publisher_typefully.draft_x_texts(remote)
    if not texts or store.x_thread_fingerprint(texts) != row["desired_fingerprint"]:
        return {"ok": False, "reason": "draft content does not match desired output"}
    status = str(remote.get("status") or "").casefold()
    if status not in {"draft", "planned", "scheduled", "publishing", "published"}:
        return {"ok": False, "reason": "remote draft has no bindable active status"}
    mode = "DRAFT" if status == "draft" and row["intended_mode"] == "DRAFT" else "IMMEDIATE"
    result = store.finalize_publisher_mutation(
        con, mutation_id, owner_token, version, mode=mode,
        provider_ref=str(remote_draft_id), publisher_status=status,
    )
    return {"ok": bool(result.get("ok")), "state": "confirmed",
            "post_id": result.get("post_id")}


def _refresh_analytics(con, publisher_typefully, store, now: float) -> dict:
    """Refresh all recent post metrics in one Typefully request, independently cached."""
    try:
        last_attempt = float(store.kv_get(con, "publisher:analytics_last_attempt") or 0)
    except ValueError:
        last_attempt = 0
    if now - last_attempt < config.PUBLISH_ANALYTICS_SECONDS:
        return {"rate_limited": 1}
    store.kv_set(con, "publisher:analytics_last_attempt", str(now))
    try:
        records = publisher_typefully.list_analytics_posts()
        return store.reconcile_typefully_analytics(con, records, synced_at=time.time())
    except Exception as exc:  # analytics are context, never a publishing dependency
        message = str(exc)[:200]
        store.kv_set(con, "publisher:analytics_last_error", message)
        log.warning("Typefully analytics sync failed: %s", message)
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


def intended_mode(klass: str, *, force_draft: bool = False) -> str:
    mode = _mode_for(klass)
    return "DRAFT" if force_draft and mode != "TAPE" else mode


def one_off_x_thread(post: str, receipt_url: str) -> list[str]:
    """Exact Typefully payload shape for a one-off, used by mutation fingerprints."""
    return [str(post).strip(), f"Source: {str(receipt_url).strip()}"]


def legacy_one_off_x_thread(post: str, receipt_url: str) -> list[str]:
    """Exact one-post shape used before receipts moved into the first reply."""
    return [f"{post}\n\n{receipt_url}"]


def publish(post: str, receipt_url: str, klass: str, image: tuple = None,
            force_draft: bool = False, exact_payload: bool = False) -> tuple:
    """Returns (mode, post_id_or_None). image: optional (bytes, file_name) chart from
    the source page, attached to the lead post (FRED links preview poorly on X).
    Operator overrides use force_draft so they can never become autonomous posts."""
    mode = intended_mode(klass, force_draft=force_draft)
    if mode == "TAPE":
        tape(post, receipt_url, klass, mode)
        return mode, None

    if _backend() == "typefully":
        from . import publisher_typefully
        media_id = publisher_typefully.upload_media(*image) if image else ""
        # Keep the lead clean and place the verified receipt in the immediate first reply.
        outcome, ref = publisher_typefully.publish_thread(
            one_off_x_thread(post, receipt_url), immediate=(mode == "IMMEDIATE"),
            lead_media_ids=[media_id] if media_id else None,
            allow_url_fallback=not exact_payload)
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


def replace_draft(draft_id: str, prior_thread: list[str], desired_thread: list[str],
                  alternate_prior_threads: list[list[str]] | None = None) -> tuple:
    """Replace one verified Typefully draft without creating a fallback object."""
    if _backend() != "typefully":
        return "FAILED", "draft replacement requires Typefully"
    from . import publisher_typefully
    outcome, detail = publisher_typefully.replace_draft(
        str(draft_id), prior_thread, desired_thread,
        alternate_prior_threads=alternate_prior_threads,
    )
    actual = {
        publisher_typefully.PublishOutcome.CONFIRMED: "DRAFT",
        publisher_typefully.PublishOutcome.STAGED: "DRAFT",
        publisher_typefully.PublishOutcome.FAILED: "FAILED",
        publisher_typefully.PublishOutcome.UNCERTAIN: "UNCERTAIN",
    }[outcome]
    return actual, detail


def promote_draft(draft_id: str, klass: str) -> tuple:
    """Schedule an existing Typefully draft once pooled evidence clears autopost."""
    mode = _mode_for(klass)
    if mode != "IMMEDIATE":
        return "DRAFT", str(draft_id)
    if _backend() != "typefully":
        return "FAILED", "existing-draft promotion requires Typefully"
    from . import publisher_typefully
    outcome = publisher_typefully.schedule_draft(str(draft_id))
    actual = {
        publisher_typefully.PublishOutcome.CONFIRMED: "IMMEDIATE",
        publisher_typefully.PublishOutcome.STAGED: "DRAFT",
        publisher_typefully.PublishOutcome.FAILED: "FAILED",
        publisher_typefully.PublishOutcome.UNCERTAIN: "UNCERTAIN",
    }[outcome]
    return actual, str(draft_id)


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
