"""The loop: poll -> triage -> draft -> gate -> publish. Plus a /health endpoint."""
import datetime
import json
import logging
import threading
import time
import uuid
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import (
    brain,
    briefing,
    config,
    guide_context,
    lint,
    node_discovery,
    publisher,
    source_policy,
    sources,
    store,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("nbn.main")

STATE = {"started": time.time(), "cycles": 0, "last_cycle": None, "last_error": None}


def _timestamp_quality(items: list[dict]) -> dict[str, int]:
    import email.utils
    counts = {"parseable": 0, "unknown": 0, "unparseable": 0}
    for item in items:
        value = str(item.get("published") or "").strip()
        if not value:
            counts["unknown"] += 1
            continue
        try:
            email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError):
            try:
                datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                counts["unparseable"] += 1
                continue
        counts["parseable"] += 1
    return counts


def _key_hashes(items: list[dict]) -> set[str]:
    return {
        store.url_hash(store.canonical_discovery_key(item.get("url", "")))
        for item in items if item.get("url")
    }


def _record_source_overlap(con, run_id: str, perception_items: list[dict],
                           x_items: list[dict], now: float) -> None:
    raw = store.kv_get(con, "node:latest_pulse")
    try:
        pulse = json.loads(raw) if raw else {}
        generated = datetime.datetime.fromisoformat(
            str(pulse.get("generated_at") or "").replace("Z", "+00:00")
        ).timestamp()
    except (TypeError, ValueError):
        pulse, generated = {}, 0
    fresh = bool(generated and -300 <= now - generated <= config.NODE_PULSE_MAX_AGE_SECONDS)
    all_refs = set(pulse.get("all_key_hashes") or []) if fresh else set()
    primary_refs = set(pulse.get("primary_key_hashes") or []) if fresh else set()
    detector_items = [
        item for item in x_items if str(item.get("source") or "").startswith(
            ("X detector", "X guide")
        )
    ]

    def lane(items: list[dict]) -> dict:
        keys = _key_hashes(items)
        return {
            "items": len(items),
            "url_keys": len(keys),
            "any_ref_overlap": len(keys & all_refs),
            "primary_ref_overlap": len(keys & primary_refs),
            "timestamps": _timestamp_quality(items),
        }

    metadata = {
        "metric": "latest_pulse_url_overlap",
        "definition": "URL overlap with latest fresh pulse; not story coverage completeness",
        "pulse": {
            "fresh": fresh,
            "run_id": pulse.get("run_id") if fresh else None,
            "status": pulse.get("status") if fresh else None,
            "age_seconds": int(max(0, now - generated)) if fresh else None,
            "candidate_count": pulse.get("candidate_count") if fresh else 0,
            "all_ref_keys": len(all_refs),
            "primary_ref_keys": len(primary_refs),
            "timestamps": pulse.get("timestamp_counts") if fresh else {},
        },
        "direct_perception": lane(perception_items),
        "broad_detector_x": lane(detector_items),
    }
    store.record_pipeline_event(
        con, run_id, f"overlap:{run_id}", "source_overlap", None,
        "latest_pulse_url_overlap", metadata,
    )


def _record_node_story_key_hint(con, item: dict) -> None:
    if not item.get("story_key"):
        return
    try:
        context = json.loads(item.get("discovery_context") or "")
    except (TypeError, ValueError):
        return
    if not isinstance(context, dict) or context.get("schema_version") != "wire-pulse-v2":
        return
    hint = str(context.get("event_key_hint") or "")[:180]
    if not hint:
        return
    store.record_pipeline_event(
        con, item.get("_run_id", ""), item["url_hash"], "node_event_key_mapped",
        item["story_key"], "discovery", {
            "event_key_hint": hint,
            "event_key_version": str(context.get("event_key_version") or "")[:40],
        },
    )


def _action_ids(item) -> list[int]:
    ids = item.get("_operator_action_ids") or []
    if item.get("_operator_action_id"):
        ids = [*ids, item["_operator_action_id"]]
    return list(dict.fromkeys(ids))


def _override_allows(item, gate: str) -> bool:
    gates = set(item.get("_operator_gates") or [])
    if item.get("_operator_gate"):
        gates.add(item["_operator_gate"])
    return gate in gates


def _finish_actions(con, item, state: str, result: str) -> None:
    for action_id in _action_ids(item):
        store.finish_operator_action(con, action_id, state, result)


def _hold(con, item, result, note):
    store.set_status(con, item["url_hash"], "held", item.get("story_key"), note[:300])
    store.finish_research_job(con, item["url_hash"])
    _finish_actions(con, item, "blocked", note)
    result["held"] += 1


def _defer_research(con, item, result, stage: str, kind: str, message: str):
    budget = "hourly call budget exhausted" in str(message).lower()
    state = store.defer_research_job(
        con, item["url_hash"], stage, kind or "infrastructure", message,
        delay_seconds=300, consume_attempt=not budget,
    )
    store.record_pipeline_event(
        con, item.get("_run_id", ""), item["url_hash"], "research_deferred",
        item.get("story_key"), "infrastructure", {"stage": stage, "error_kind": kind},
    )
    _record_research_failure(con, item, stage, kind, state)
    _finish_actions(con, item, "blocked", f"research retry failed: {message}")
    item["_research_deferred"] = True
    result["held"] += 1


def _record_research_failure(con, item: dict, stage: str, kind: str, state: str) -> None:
    allowed = {"support_assessment_timeout", "search_timeout", "source_fetch", "exhausted"}
    typed = "source_fetch" if stage == "source_fetch" else str(kind or "unknown")
    if typed not in allowed:
        typed = "unknown"
    store.record_pipeline_event(
        con, item.get("_run_id", ""), item["url_hash"], f"research_failed:{typed}",
        item.get("story_key"), "infrastructure", {
            "stage": stage, "error_kind": typed, "state": state,
        },
    )


def _provider_matches(provider: str, selected_ref) -> bool:
    if not provider:
        return True
    provider_ref = source_policy.classify("", provider)
    return provider_ref.known and provider_ref.source_id == selected_ref.source_id


def _evidence_class(resolution) -> str:
    """Derive class from the final receipt; corroboration is added separately."""
    if (resolution.selected.official and resolution.supported
            and resolution.originality == "primary_artifact"):
        return "primary"
    return "secondary"


def _resolution_rank(resolution) -> tuple:
    originality = {
        "primary_artifact": 0, "original_research": 1, "technical_original": 2,
        "original_reporting": 3, "unknown": 4,
    }
    return (
        source_policy.TIER_RANK.get(resolution.selected.tier, 9),
        originality.get(resolution.originality, 9),
        resolution.selected.display_name.lower(), resolution.selected.url,
    )


def _lease_run(con, scheduled: bool) -> dict:
    owner = str(uuid.uuid4())
    if not store.acquire_cycle_lease(con, owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
        log.warning("worker iteration skipped: another process owns the lease")
        return {"skipped_locked": 1}
    stop_heartbeat = threading.Event()
    heartbeat = threading.Thread(
        target=_renew_cycle_lease_until_stopped,
        args=(owner, stop_heartbeat),
        name="cycle-lease-heartbeat",
        daemon=True,
    )
    heartbeat.start()
    try:
        # Repair human-published Typefully drafts before any coverage/dedup decisions.
        publisher.reconcile_publications(con)
        result = _cycle_locked(con, owner)
        # The newsroom reservation belongs only to the one-off news cycle. Release any
        # remainder before independent scheduled Block/audit work asks for model capacity.
        brain.release_active_model_reservation()
        if scheduled:
            if config.NODE_READ_TOKEN:
                briefing.maybe_run(con)
            if config.AUDIT_UTC:
                from . import audit
                audit.maybe_run(con)
        return result
    finally:
        brain.release_active_model_reservation()
        stop_heartbeat.set()
        heartbeat.join(timeout=max(1, config.CYCLE_LEASE_HEARTBEAT_SECONDS + 1))
        store.release_cycle_lease(con, owner)


def _renew_cycle_lease_until_stopped(owner: str, stop: threading.Event) -> None:
    """Keep a live cycle's short lease valid using its own SQLite connection."""
    con = store.connect()
    try:
        while not stop.wait(config.CYCLE_LEASE_HEARTBEAT_SECONDS):
            try:
                renewed = store.renew_cycle_lease(
                    con, owner, ttl_seconds=config.CYCLE_LEASE_SECONDS
                )
            except Exception:  # noqa: BLE001 - the foreground stage checks remain authoritative
                log.exception("cycle lease heartbeat failed")
                continue
            if not renewed:
                log.error("cycle lease heartbeat lost ownership")
                return
    finally:
        con.close()


def cycle(con) -> dict:
    """Run one news cycle under the same lease used by the deployed worker."""
    return _lease_run(con, scheduled=False)


def worker_iteration(con) -> dict:
    """Run news, briefing, and audit as one cross-process critical section."""
    return _lease_run(con, scheduled=True)


def _retry_inventory(con, jobs: list[dict], pipeline_run_id: str,
                     *, materialize: bool) -> list[dict]:
    """Decode due research rows; newsroom survey mode leaves attempts untouched."""
    retry_verdicts = []
    for raw_job in jobs:
        job = raw_job
        if materialize:
            claimed = store.claim_research_job_for_materialization(con, job["item_hash"])
            if claimed:
                job = claimed
        try:
            retry = json.loads(job["context_json"])
        except (TypeError, ValueError):
            if materialize:
                store.defer_research_job(
                    con, job["item_hash"], "source_fetch", "invalid_context",
                    "saved research context is invalid")
            continue
        if not isinstance(retry, dict) or retry.get("url_hash") != job["item_hash"]:
            if materialize:
                store.defer_research_job(
                    con, job["item_hash"], "source_fetch", "invalid_context",
                    "saved research context does not match item")
            continue
        retry.update({
            "_research_retry": True,
            "_manual_draft_only": bool(job["manual_draft_only"]),
            "_run_id": pipeline_run_id,
        })
        action = store.pending_retry_action(con, retry["url_hash"])
        if action:
            if materialize:
                store.start_operator_action(con, action["id"])
            retry["_operator_action_id"] = action["id"]
            retry["_operator_gate"] = "research"
        retry_verdicts.append(retry)
    return retry_verdicts


def _run_editorial_v2(con, *, lease_owner: str, pipeline_run_id: str,
                      inventory: list[dict], pending: list[dict], result: dict,
                      theme_snapshot: list[dict], overrides: dict,
                      run_started: float) -> dict:
    """Materialize the practical v2 desk without touching any legacy terminal gates."""
    from . import editor, newsroom

    cluster_context = store.story_cluster_context(
        con, exclude_hashes={item["url_hash"] for item in inventory})
    reservation = brain.reserve_model_calls(config.RUN_NEWSROOM_MAX_ROUNDS * 2 + 1)
    if not reservation:
        note = "defer:model_budget_unavailable"
        verdicts = [{**item, "action": "hold", "reason": note} for item in inventory]
        for item in inventory:
            store.defer_item(con, item["url_hash"], note, delay_seconds=300,
                             category="technical_defer")
        result["held"] += len(inventory)
        result["newsroom"] = {"mode": config.RUN_NEWSROOM_MODE, "status": "deferred",
                              "error_kind": "budget_unavailable"}
        store.record_decision_run(con, pending, verdicts, result, run_started,
                                  theme_snapshot=theme_snapshot)
        return result

    brain.activate_model_reservation(reservation)
    store.start_newsroom_run(
        con, pipeline_run_id, config.RUN_NEWSROOM_MODE, config.ANTHROPIC_MODEL,
        newsroom.PROMPT_VERSION, [item["url_hash"] for item in inventory],
    )
    session = newsroom.start_session(
        run_id=pipeline_run_id, inventory=inventory, recent_clusters=cluster_context,
        theme_snapshot=theme_snapshot, handles=lint.verified_handles(), con=con,
        reservation=reservation,
    )
    try:
        outcome = session.conduct()
    except Exception as exc:  # one bounded clean retry; never enter legacy triage
        log.warning("v2 newsdesk failed, retrying once with a clean context: %s", exc)
        try:
            session = newsroom.start_session(
                run_id=pipeline_run_id, inventory=inventory, recent_clusters=cluster_context,
                theme_snapshot=theme_snapshot, handles=lint.verified_handles(), con=con,
                reservation=reservation,
            )
            outcome = session.conduct()
        except Exception as retry_exc:  # noqa: BLE001 - preserve inventory for next slot
            kind = getattr(retry_exc, "kind", type(retry_exc).__name__)
            message = f"{type(retry_exc).__name__}: {retry_exc}"[:500]
            counters = session.counters()
            store.set_newsroom_state(
                con, pipeline_run_id, "deferred", error_kind=kind,
                error_message=message, counters=counters,
            )
            verdicts = []
            for item in inventory:
                note = f"defer:newsdesk_unavailable:{kind}"[:300]
                store.defer_item(con, item["url_hash"], note, delay_seconds=300,
                                 story_key=item.get("story_key"),
                                 stage="newsdesk", category="technical_defer")
                verdicts.append({**item, "action": "hold", "reason": note})
            result["held"] += len(inventory)
            result["newsroom"] = {
                "mode": config.RUN_NEWSROOM_MODE, "status": "deferred",
                "prompt_version": newsroom.PROMPT_VERSION, "error_kind": kind,
                "error": message, **counters,
            }
            store.record_decision_run(con, pending, verdicts, result, run_started,
                                      theme_snapshot=theme_snapshot)
            return result

    result["newsroom"] = {
        "mode": config.RUN_NEWSROOM_MODE, "status": "validated",
        "prompt_version": newsroom.PROMPT_VERSION, **outcome.counters,
        "stories": len(outcome.dossier.get("stories") or []),
    }
    if config.RUN_NEWSROOM_MODE == "shadow":
        store.set_newsroom_state(con, pipeline_run_id, "completed", counters=outcome.counters)
        result["newsroom"]["status"] = "completed"
        store.record_decision_run(con, pending, outcome.verdicts, result, run_started,
                                  theme_snapshot=theme_snapshot)
        return result

    store.set_newsroom_state(con, pipeline_run_id, "materializing")
    valid_story_ids = sorted(set(outcome.story_ids.values()))
    store.init_newsroom_story_commits(con, pipeline_run_id, valid_story_ids, outcome.digest)

    # Completed editorial drops are terminal; defers remain in the next clean desk.
    for verdict in outcome.verdicts:
        action = verdict.get("action")
        if action == "skip":
            store.set_status(con, verdict["url_hash"], "skipped", verdict.get("story_key"),
                             verdict.get("reason"), stage="newsdesk", category="editorial_drop")
        elif action == "hold":
            store.defer_item(con, verdict["url_hash"], verdict.get("reason") or "defer",
                             story_key=verdict.get("story_key"), stage="newsdesk",
                             category="editorial_defer")
            result["held"] += 1

    by_story: dict[str, list[dict]] = {}
    for verdict in outcome.verdicts:
        story_id = outcome.story_ids.get(verdict["url_hash"])
        if story_id and verdict.get("action") == "draft":
            by_story.setdefault(story_id, []).append(verdict)

    candidates = []
    candidate_rows: dict[str, dict] = {}
    for story_id, members in by_story.items():
        anchor = members[0]
        resolution = outcome.resolutions[anchor["url_hash"]]
        draft = outcome.drafts[anchor["url_hash"]]
        post = str(draft.get("post") or "").strip()
        source_text = str(draft.get("_source_text") or resolution.selected_text or "")
        hard_errors = lint.check_v2(post, {"_source_text": source_text}, anchor)
        evidence_ids = list(draft.get("evidence_fetch_ids") or [])
        fetches = [outcome.fetches[value] for value in evidence_ids
                   if value in outcome.fetches]
        if not fetches:
            note = "defer:no_inspected_evidence_materialized"
            for member in members:
                store.defer_item(con, member["url_hash"], note,
                                 story_key=resolution.story_key, stage="research",
                                 category="technical_defer")
            result["held"] += len(members)
            store.set_newsroom_story_state(con, pipeline_run_id, story_id, "held")
            continue
        selected = outcome.fetches.get(str(draft.get("selected_fetch_id") or ""), fetches[0])
        if store.exact_output_exists(con, post, selected.final_url):
            for member in members:
                store.set_status(con, member["url_hash"], "skipped", resolution.story_key,
                                 "exact output or receipt already queued")
            store.set_newsroom_story_state(con, pipeline_run_id, story_id, "held")
            continue
        row = {
            "story_id": story_id, "post": post,
            "reader_value": draft.get("reader_value", ""),
            "selected_receipt": {"url": selected.final_url,
                                 "source": selected.source.display_name,
                                 "tier": selected.source.tier},
            "inspected_evidence": [{"fetch_id": record.fetch_id,
                                    "source": record.source.display_name,
                                    "tier": record.source.tier,
                                    "url": record.final_url,
                                    "text": record.text[:8000]} for record in fetches],
            "elevated_claim": bool(draft.get("needs_second_source")),
            "hard_rail_notes_for_revision": hard_errors,
        }
        candidates.append(row)
        candidate_rows[story_id] = {
            "members": members, "resolution": resolution, "draft": draft,
            "selected": selected, "fetches": fetches,
        }

    editorial = editor.review_newsroom_batch(
        candidates, con, run_id=pipeline_run_id, reservation=reservation,
    ) if candidates else {"ok": True, "decisions": {}}
    for story_id, candidate in candidate_rows.items():
        members = candidate["members"]
        resolution = candidate["resolution"]
        selected = candidate["selected"]
        decision = editorial["decisions"].get(story_id)
        if not editorial["ok"] or decision is None:
            verdict, post = "draft", candidate["draft"]["post"]
            reason = ("editor unavailable; staged for review" if not editorial["ok"]
                      else "editor omitted story; staged for review")
        else:
            verdict, post = decision["verdict"], decision.get("post")
            reason = decision.get("reason") or ""
        if verdict == "drop":
            for member in members:
                store.set_status(con, member["url_hash"], "skipped", resolution.story_key,
                                 f"editor dropped: {reason}"[:300], stage="editor",
                                 category="editorial_drop")
            store.set_newsroom_story_state(con, pipeline_run_id, story_id, "held")
            continue
        errors = lint.check_v2(str(post or ""),
                               {"_source_text": resolution.selected_text}, members[0])
        if errors:
            for member in members:
                store.defer_item(
                    con, member["url_hash"],
                    ("defer:editor_hard_rail:" + "; ".join(errors))[:300],
                    story_key=resolution.story_key, stage="hard_rail",
                    category="technical_defer",
                )
            result["held"] += len(members)
            store.set_newsroom_story_state(con, pipeline_run_id, story_id, "held")
            continue
        independent = {record.source.independence_key for record in candidate["fetches"]}
        klass = ("primary" if selected.source.official else
                 "corroborated" if len(independent) >= 2 else "secondary")
        for member in members:
            store.persist_resolution(con, outcome.resolutions[member["url_hash"]],
                                     config.SOURCE_POLICY_MODE)
        force_draft = (config.RUN_NEWSROOM_MODE == "draft" or verdict == "draft"
                       or any(_action_ids(member) for member in members))
        if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
            raise RuntimeError("cycle lease lost before v2 delivery")
        mode, publisher_ref = publisher.publish(
            str(post), selected.final_url, klass, force_draft=force_draft)
        lifecycle = {"IMMEDIATE": ("posted", "posted"), "DRAFT": ("drafted", "drafted"),
                     "UNCERTAIN": ("uncertain", "uncertain"), "FAILED": ("failed", "failed"),
                     "TAPE": ("taped", "taped")}
        status, counter = lifecycle.get(mode, ("failed", "failed"))
        for index, member in enumerate(members):
            store.set_status(con, member["url_hash"], status if index == 0 else "skipped",
                             resolution.story_key,
                             "" if index == 0 else "same story materialized from pooled evidence",
                             stage="delivery", category="output")
            _finish_actions(con, member, "completed", f"delivery result: {mode}")
        store.log_post(
            con, resolution.story_key, members[0]["url_hash"], klass, str(post),
            selected.final_url, mode, publisher_ref, editor_note=f"{verdict}: {reason}"[:300],
            resolution_id=members[0]["url_hash"], publisher_backend=publisher.backend_name(),
        )
        store.set_newsroom_story_state(
            con, pipeline_run_id, story_id,
            "delivered" if mode != "FAILED" else "held", publisher_ref or "")
        result[counter] += 1

    store.set_newsroom_state(con, pipeline_run_id, "completed", counters=outcome.counters)
    result["newsroom"]["status"] = "completed"
    store.record_decision_run(con, pending, outcome.verdicts, result, run_started,
                              theme_snapshot=theme_snapshot)
    return result


def _cycle_locked(con, lease_owner: str) -> dict:
    """Resolve and prepare complete story groups before choosing one final receipt."""
    from . import verify

    run_started = time.time()
    pipeline_run_id = f"cycle:{int(run_started)}:{lease_owner[:8]}"
    newsroom_recovery = store.recover_incomplete_newsroom_runs(con)
    if newsroom_recovery["runs"]:
        log.warning("recovered interrupted newsroom runs: %s", newsroom_recovery)
    node_result = node_discovery.ingest(con)
    rss_items = sources.fetch_feeds()
    edgar_items = sources.fetch_edgar()
    perception_items = sources.fetch_perception()
    x_items = sources.fetch_x(con)
    item_groups = (
        ("rss", rss_items),
        ("edgar", edgar_items),
        ("perception", perception_items),
        ("x", x_items),
    )
    items = []
    for origin, group in item_groups:
        items.extend({**item, "discovery_origin": origin} for item in group)
    _record_source_overlap(con, pipeline_run_id, perception_items, x_items, run_started)
    if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
        raise RuntimeError("cycle lease lost after fetch")
    inserted = store.upsert_new_items(con, items)
    summaries = {store.url_hash(i["url"]): i.get("summary", "") for i in items}
    pending = store.pending_items(con, config.MAX_ITEMS_PER_TRIAGE)
    overrides = {}
    for it in pending:
        action = store.pending_stage_action(con, it["url_hash"])
        if action:
            overrides[it["url_hash"]] = action
            it["_operator_action_id"] = action["id"]
            it["_operator_gate"] = action["gate"]
    fresh = []
    for it in pending:
        intake_age = (config.DESK_CANDIDATE_MAX_AGE_HOURS
                      if config.EDITORIAL_ENGINE == "v2" else None)
        if store.is_stale(it.get("published", ""), max_age_hours=intake_age) \
                and not _override_allows(it, "freshness"):
            note = "stale at intake"
            if _action_ids(it):
                store.set_status(con, it["url_hash"], "held", None, note)
                _finish_actions(con, it, "blocked", note)
            else:
                store.set_status(con, it["url_hash"], "skipped", None, note)
            continue
        if store.is_non_english(it.get("title", "")):
            store.set_status(con, it["url_hash"], "skipped", None, "non-English source")
            continue
        it["summary"] = summaries.get(it["url_hash"], it.get("summary", ""))
        it["_run_id"] = pipeline_run_id
        fresh.append(it)
    if config.RUN_NEWSROOM_MODE == "off":
        retry_jobs = store.claim_due_research_jobs(con, limit=2)
        retry_verdicts = _retry_inventory(
            con, retry_jobs, pipeline_run_id, materialize=True)
    else:
        retry_jobs = store.due_research_jobs_snapshot(con, limit=2)
        retry_verdicts = _retry_inventory(
            con, retry_jobs, pipeline_run_id, materialize=False)
    node_summary = {
        key: node_result[key] for key in (
            "attempted", "reason", "contract", "run_id", "consumed", "inserted",
            "deduped", "context_attached", "error", "v2_error"
        ) if key in node_result
    }
    result = {"fetched": len(items) + int(node_result.get("inserted", 0)),
              "new": len(inserted) + int(node_result.get("inserted", 0)),
              "node": node_summary, "considered": len(pending) + len(retry_verdicts),
              "pending": len(fresh) + len(retry_verdicts),
              "drafted": 0, "held": 0, "posted": 0, "uncertain": 0,
              "failed": 0, "taped": 0, "policy_held": 0}
    if newsroom_recovery["runs"]:
        result["newsroom_recovery"] = newsroom_recovery
    result["resolver_paths"] = {}
    result["resolver_outcomes"] = {}
    theme_snapshot = store.theme_coverage_snapshot(con, fresh)
    node_diagnostics = node_result.get("diagnostics") or {}
    for key in node_diagnostics.get("rejected_candidate_keys", [])[:24]:
        store.record_pipeline_event(
            con, pipeline_run_id, f"node-rejected:{key}", "node_packet_rejected",
            None, "discovery", {},
        )
    for key in node_diagnostics.get("dropped_candidate_keys", [])[:24]:
        store.record_pipeline_event(
            con, pipeline_run_id, f"node-dropped:{key}", "node_packet_dropped",
            None, "discovery", {},
        )
    store.record_pipeline_event(
        con, pipeline_run_id, f"themes:{pipeline_run_id}", "theme_context_summary",
        None, "discovery", {
            "theme_signals_parsed": int(node_diagnostics.get("theme_signals_parsed", 0)),
            "theme_candidates_rejected": int(
                node_diagnostics.get("theme_candidates_rejected", 0)),
            "snapshot_themes": len(theme_snapshot),
            "coverage_known": sum(bool(row.get("coverage_known")) for row in theme_snapshot),
            "coverage_unknown": sum(not bool(row.get("coverage_known"))
                                    for row in theme_snapshot),
            "open_drafts": sum(bool(row.get("open_draft")) for row in theme_snapshot),
            "published": sum(bool(row.get("last_published_at")) for row in theme_snapshot),
        },
    )

    if config.EDITORIAL_ENGINE == "v2" and config.RUN_NEWSROOM_MODE != "off":
        # Intake, publication reconciliation, health, Blocks, and audits still run each
        # minute. Only the expensive editorial seats are cadence-gated.
        force_desk = bool(overrides or retry_verdicts)
        due = store.editorial_run_due(con, now=run_started, force=force_desk)
        if not due:
            result["newsroom"] = {
                "mode": config.RUN_NEWSROOM_MODE, "status": "waiting",
                "prompt_version": "editorial-core-v2.0",
            }
            return result
        if not fresh and not retry_verdicts:
            result["newsroom"] = {
                "mode": config.RUN_NEWSROOM_MODE, "status": "empty",
                "prompt_version": "editorial-core-v2.0",
            }
            return result
        inventory = fresh + retry_verdicts
        result = _run_editorial_v2(
            con, lease_owner=lease_owner, pipeline_run_id=pipeline_run_id,
            inventory=inventory, pending=pending, result=result,
            theme_snapshot=theme_snapshot, overrides=overrides,
            run_started=run_started,
        )
        if len(store.pending_items(con, config.MAX_ITEMS_PER_TRIAGE + 1)) \
                > config.MAX_ITEMS_PER_TRIAGE:
            store.editorial_run_soon(con)
        return result

    if not fresh and not retry_verdicts:
        store.record_decision_run(
            con, pending, [], result, run_started, theme_snapshot=theme_snapshot)
        return result

    newsroom_outcome = None
    newsroom_error = ""
    newsroom_mode = config.RUN_NEWSROOM_MODE
    inventory = fresh + retry_verdicts
    handles = lint.verified_handles()
    cluster_context = store.story_cluster_context(
        con, exclude_hashes={item["url_hash"] for item in inventory})
    if newsroom_mode != "off":
        from . import newsroom
        reserve_count = config.RUN_NEWSROOM_MAX_ROUNDS + len(inventory)
        reservation = brain.reserve_model_calls(reserve_count)
        if reservation:
            brain.activate_model_reservation(reservation)
            store.start_newsroom_run(
                con, pipeline_run_id, newsroom_mode, config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [item["url_hash"] for item in inventory],
            )
            session = None
            try:
                session = newsroom.start_session(
                    run_id=pipeline_run_id, inventory=inventory,
                    recent_clusters=cluster_context, theme_snapshot=theme_snapshot,
                    handles=handles, con=con, reservation=reservation,
                )
                newsroom_outcome = session.conduct()
                result["newsroom"] = {
                    "mode": newsroom_mode, "prompt_version": newsroom.PROMPT_VERSION,
                    "status": "validated", **newsroom_outcome.counters,
                    "stories": len(newsroom_outcome.dossier.get("stories") or []),
                }
            except Exception as exc:  # noqa: BLE001 - whole-batch fallback is intentional
                newsroom_error = f"{type(exc).__name__}: {exc}"[:500]
                kind = getattr(exc, "kind", type(exc).__name__)
                counters = session.counters() if session else {}
                store.set_newsroom_state(
                    con, pipeline_run_id, "fallback", error_kind=kind,
                    error_message=newsroom_error, counters=counters,
                )
                result["newsroom"] = {
                    "mode": newsroom_mode, "status": "fallback",
                    "error_kind": kind, "error": newsroom_error, **counters,
                }
                log.warning("run newsroom fell back before materialization: %s", newsroom_error)
        else:
            newsroom_error = "model call budget reservation unavailable"
            result["newsroom"] = {
                "mode": newsroom_mode, "status": "fallback",
                "error_kind": "budget_unavailable", "error": newsroom_error,
            }

        if newsroom_outcome and newsroom_mode == "shadow":
            store.set_newsroom_state(
                con, pipeline_run_id, "completed", counters=newsroom_outcome.counters)
            result["newsroom"]["status"] = "completed"
            store.record_pipeline_event(
                con, pipeline_run_id, f"newsroom:{pipeline_run_id}",
                "newsroom_shadow_completed", None, "newsroom",
                result["newsroom"],
            )
            newsroom_outcome = None
        elif newsroom_outcome:
            store.set_newsroom_state(con, pipeline_run_id, "materializing")
            store.init_newsroom_story_commits(
                con, pipeline_run_id,
                [str(row.get("story_id") or "")
                 for row in newsroom_outcome.dossier.get("stories") or []],
                newsroom_outcome.digest,
            )
        elif config.RUN_NEWSROOM_FALLBACK == "hold" and newsroom_mode in {"draft", "live"}:
            verdicts = []
            for item in inventory:
                held = {**item, "action": "hold", "story_key": item.get("story_key"),
                        "class": "secondary", "reason": f"newsroom unavailable: {newsroom_error}"}
                verdicts.append(held)
                store.set_status(con, item["url_hash"], "held", held.get("story_key"),
                                 held["reason"][:300])
                result["held"] += 1
            store.record_decision_run(
                con, pending + retry_verdicts, verdicts, result, run_started,
                theme_snapshot=theme_snapshot)
            return result

    # Research retries were read-only during newsroom/shadow work. Claim them only when
    # an active dossier materializes or the identical inventory enters legacy fallback.
    if newsroom_mode != "off" and retry_jobs:
        retry_verdicts = _retry_inventory(
            con, retry_jobs, pipeline_run_id, materialize=True)
        retry_by_hash = {row["url_hash"]: row for row in retry_verdicts}
        inventory = [retry_by_hash.get(row["url_hash"], row) for row in inventory]

    if newsroom_outcome:
        verdicts = newsroom_outcome.verdicts
    else:
        if fresh:
            triage_args = (fresh, store.recent_story_keys(con), store.open_story_keys(con))
            verdicts = (brain.triage(*triage_args, theme_coverage=theme_snapshot)
                        if theme_snapshot else brain.triage(*triage_args))
        else:
            verdicts = []
        verdicts.extend(retry_verdicts)
    for item in verdicts:
        if item.get("story_key"):
            item["story_key"] = store.canonical_story_key(con, item["story_key"])
    for item in verdicts:
        _record_node_story_key_hint(con, item)
    for item in verdicts:
        action = overrides.get(item["url_hash"])
        if not action:
            continue
        store.start_operator_action(con, action["id"])
        item["_operator_action_id"] = action["id"]
        item["_operator_gate"] = action["gate"]
        item["action"] = "draft"
        item["story_key"] = action["story_key"] or item.get("story_key")
        item["reason"] = (f"owner requested Typefully draft; overriding {action['gate']} hold")
    resolutions = dict(newsroom_outcome.resolutions) if newsroom_outcome else {}
    original_texts = {
        item_hash: resolution.selected_text
        for item_hash, resolution in resolutions.items()
    }
    newsroom_drafts = dict(newsroom_outcome.drafts) if newsroom_outcome else {}

    # Persist exact keys, then resolve the complete actionable batch. An upsert moves
    # an item's evidence if triage corrects its key on a later cycle.
    for item in verdicts:
        if item.get("story_key"):
            store.set_status(con, item["url_hash"], "new", item["story_key"])
            # A retry may already have evidence under an earlier triage key. Move the
            # complete provenance record before handled/update short-circuits.
            store.move_resolution_story_key(con, item["url_hash"], item["story_key"])
    for item in verdicts:
        action, story_key = item.get("action", "skip"), item.get("story_key")
        if action not in ("draft", "update"):
            continue
        # A human-visible draft is not terminal: later independent outlets must still
        # enter the cluster so their evidence can corroborate it without another draft.
        if action == "draft" and store.story_reader_covered(con, story_key):
            continue
        if action == "update" and not store.story_reader_covered(con, story_key):
            continue
        item["_coverage_action"] = action
        if not item.get("_research_retry"):
            store.start_research_job(con, item, pipeline_run_id)
        store.record_pipeline_event(
            con, pipeline_run_id, item["url_hash"], "research_started", story_key,
            "infrastructure", {"retry": bool(item.get("_research_retry"))},
        )
        if guide_context.signal_from_context(item.get("discovery_context")):
            store.record_pipeline_event(
                con, pipeline_run_id, item["url_hash"], "guide_lead_advanced",
                story_key, "discovery", {},
            )
        if newsroom_outcome:
            resolution = resolutions.get(item["url_hash"])
            if resolution is None:
                _hold(con, item, result, "newsroom story lacks materializable receipt")
                continue
            result["resolver_paths"]["run_newsroom"] = (
                result["resolver_paths"].get("run_newsroom", 0) + 1
            )
            result["resolver_outcomes"]["selected"] = (
                result["resolver_outcomes"].get("selected", 0) + 1
            )
            store.persist_resolution(con, resolution, config.SOURCE_POLICY_MODE)
            store.record_pipeline_event(
                con, pipeline_run_id, item["url_hash"], "research_completed",
                item.get("story_key"), "research",
                {"status": resolution.status, "resolver_path": "run_newsroom"},
            )
            continue
        fetched = sources.fetch_article(item["url"])
        if fetched.get("outcome") == "infrastructure_retryable":
            result["resolver_paths"]["unknown"] = (
                result["resolver_paths"].get("unknown", 0) + 1
            )
            result["resolver_outcomes"]["source_fetch"] = (
                result["resolver_outcomes"].get("source_fetch", 0) + 1
            )
            _defer_research(
                con, item, result, "source_fetch", fetched.get("error_kind", ""),
                fetched.get("error_message") or "source fetch failed")
            continue
        text = fetched["text"]
        item["_final_url"] = fetched["final_url"]
        item["_canonical_url"] = fetched["canonical_url"]
        item["_byline"] = fetched["byline"]
        original_texts[item["url_hash"]] = text
        resolution = verify.resolve_source(
            item, text, con=con, use_persisted=not bool(_action_ids(item)),
            force_refresh=bool(_action_ids(item)))
        if resolution.outcome == "infrastructure_retryable":
            if resolution.retry_candidates:
                store.update_research_retry_candidates(
                    con, item["url_hash"], resolution.retry_candidates
                )
            path = resolution.resolver_path if resolution.resolver_path in {
                "direct", "node_ref", "guide_ref", "serpapi", "hosted_web"
            } else "unknown"
            outcome = resolution.error_kind if resolution.error_kind in {
                "support_assessment_timeout", "search_timeout", "source_fetch", "exhausted"
            } else "unknown"
            result["resolver_paths"][path] = result["resolver_paths"].get(path, 0) + 1
            result["resolver_outcomes"][outcome] = (
                result["resolver_outcomes"].get(outcome, 0) + 1
            )
            _defer_research(
                con, item, result, "source_resolution", resolution.error_kind,
                resolution.note)
            continue
        path = resolution.resolver_path if resolution.resolver_path in {
            "direct", "node_ref", "guide_ref", "serpapi", "hosted_web"
        } else "unknown"
        result["resolver_paths"][path] = result["resolver_paths"].get(path, 0) + 1
        resolution_outcome = "selected" if resolution.status == "selected" else "unknown"
        result["resolver_outcomes"][resolution_outcome] = (
            result["resolver_outcomes"].get(resolution_outcome, 0) + 1
        )
        resolutions[item["url_hash"]] = resolution
        store.persist_resolution(con, resolution, config.SOURCE_POLICY_MODE)
        store.record_pipeline_event(
            con, pipeline_run_id, item["url_hash"], "research_completed",
            item.get("story_key"), "research", {
                "status": resolution.status, "resolver_path": path,
            },
        )

    # Triage sees only headlines. Reconcile provisional keys after source fetch, using
    # article facts and a compact recent cluster catalog. A model failure is a no-op;
    # only high-confidence mappings to known keys are accepted by brain.py.
    cluster_items = []
    for item in verdicts:
        resolution = resolutions.get(item["url_hash"])
        if item.get("action") not in ("draft", "update") or resolution is None:
            continue
        enriched = dict(item)
        enriched["_selected_source"] = resolution.selected.display_name
        enriched["_selected_text"] = resolution.selected_text
        cluster_items.append(enriched)
    reconciled = ({
        row["url_hash"]: row
        for row in brain.reconcile_story_keys(cluster_items, cluster_context)
    } if cluster_items else {}) if not newsroom_outcome else {}
    for item in verdicts:
        match = reconciled.get(item["url_hash"])
        if not match:
            continue
        previous = item.get("story_key") or ""
        target = match.get("canonical_key") or previous
        if target != previous:
            target = store.register_story_alias(
                con, previous, target,
                f"{match.get('relationship', '')}: {match.get('reason', '')}",
            )
        item["story_key"] = store.canonical_story_key(con, target)
        item["_cluster_relationship"] = match.get("relationship") or "distinct"
        if item["story_key"] != previous:
            store.set_status(con, item["url_hash"], "new", item["story_key"])
            store.move_resolution_story_key(con, item["url_hash"], item["story_key"])
            store.record_pipeline_event(
                con, pipeline_run_id, item["url_hash"], "story_key_merged",
                item["story_key"], "identity", {
                    "alias_key": previous,
                    "relationship": item["_cluster_relationship"],
                    "confidence": match.get("confidence"),
                    "reason": match.get("reason"),
                },
            )
        if (item["_cluster_relationship"] == "new_development"
                and store.story_reader_covered(con, item["story_key"])):
            item["action"] = "update"
        elif (item["_cluster_relationship"] == "same_event"
              and store.story_reader_covered(con, item["story_key"])):
            item["action"] = "draft"

    # Resolve alias chains after all batch mappings are registered (A→B→C is valid).
    for item in verdicts:
        if item.get("story_key"):
            canonical = store.canonical_story_key(con, item["story_key"])
            if canonical != item["story_key"]:
                item["story_key"] = canonical
                store.set_status(con, item["url_hash"], "new", canonical)
                store.move_resolution_story_key(con, item["url_hash"], canonical)

    # An NBN-created Typefully draft remains an open evidence cluster. Later directly
    # supporting sources enrich it without another Writer/Editor/draft pass; two
    # independent chains (or a primary artifact) can schedule that approved copy.
    open_draft_groups = {}
    for item in verdicts:
        resolution = resolutions.get(item["url_hash"])
        story_key = item.get("story_key")
        if (item.get("action") not in ("draft", "update") or resolution is None
                or resolution.held or _action_ids(item)
                or store.story_reader_covered(con, story_key)):
            continue
        existing = store.open_typefully_draft(con, story_key)
        if existing:
            open_draft_groups.setdefault(story_key, {"draft": existing, "items": []})[
                "items"].append((item, resolution))
    for story_key, group in open_draft_groups.items():
        rows = group["items"]
        klass = "primary" if any(_evidence_class(res) == "primary" for _, res in rows) \
            else "secondary"
        evidence_count = store.qualified_evidence_count(
            con, story_key, max(config.SOURCE_EVIDENCE_LOOKBACK_HOURS,
                                config.max_event_age_hours()))
        if klass == "secondary" and evidence_count >= 2:
            klass = "corroborated"
        mode, _ = publisher.promote_draft(group["draft"]["nuelink_id"], klass)
        if mode in ("IMMEDIATE", "UNCERTAIN"):
            store.record_draft_promotion(con, group["draft"]["id"], klass, mode)
            original_status = "posted" if mode == "IMMEDIATE" else "uncertain"
            if group["draft"]["item_hash"]:
                store.set_status(
                    con, group["draft"]["item_hash"], original_status, story_key,
                    "existing draft promoted by pooled evidence",
                )
            result["posted" if mode == "IMMEDIATE" else "uncertain"] += 1
        for item, _resolution in rows:
            item["_handled_by_open_draft"] = True
            note = ("pooled evidence promoted existing draft" if mode in (
                "IMMEDIATE", "UNCERTAIN") else "evidence pooled into existing draft")
            if mode == "FAILED":
                _hold(con, item, result, "existing Typefully draft promotion failed")
                continue
            store.set_status(con, item["url_hash"], "skipped", story_key, note)
            store.finish_research_job(con, item["url_hash"])
            _finish_actions(con, item, "completed", note)
            store.record_pipeline_event(
                con, pipeline_run_id, item["url_hash"],
                "existing_draft_promoted" if mode in ("IMMEDIATE", "UNCERTAIN")
                else "evidence_pooled_into_draft",
                story_key, "delivery", {"mode": mode,
                                         "draft_id": group["draft"]["nuelink_id"]},
            )
    if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
        raise RuntimeError("cycle lease lost after resolution")

    prepared: dict[str, list[dict]] = {}
    provider_cache = {}
    for item in verdicts:
        action, story_key = item.get("action", "skip"), item.get("story_key")
        if item.get("_research_deferred") or item.get("_handled_by_open_draft"):
            continue
        if action not in ("draft", "update"):
            status = "skipped" if action == "skip" else "held"
            store.set_status(con, item["url_hash"], status, story_key, item.get("reason"))
            if status == "held":
                result["held"] += 1
            continue
        if action == "draft" and store.story_reader_covered(con, story_key):
            store.set_status(con, item["url_hash"], "skipped", story_key, "story already handled")
            store.finish_research_job(con, item["url_hash"])
            _finish_actions(con, item, "blocked", "story already handled")
            continue
        if action == "update" and not store.story_reader_covered(con, story_key):
            _hold(con, item, result, "update lacks exact reader-covered story")
            continue

        resolution = resolutions[item["url_hash"]]
        if config.SOURCE_POLICY_MODE == "enforce" and resolution.held:
            _hold(con, item, result, f"source policy: {resolution.note}")
            result["policy_held"] += 1
            continue

        effective = dict(item)
        if not resolution.held:
            effective["url"] = resolution.selected.url
            effective["source"] = resolution.selected.display_name
            article_text = resolution.selected_text
        else:  # observe mode: record the would-be hold but preserve draft-only legacy flow
            article_text = original_texts.get(item["url_hash"], "")
        effective["_coverage_action"] = action

        # Model labels cannot set evidence class. It derives from the final receipt.
        klass = _evidence_class(resolution)
        effective["class"] = klass
        covered = [body.split("\n")[0][:200]
                   for body in store.recent_story_bodies(con, story_key, limit=2)]
        if newsroom_outcome:
            draft = newsroom_drafts.get(item["url_hash"])
            if not draft:
                _hold(con, item, result, "newsroom produced no draft for actionable story")
                continue
        else:
            try:
                draft = brain.draft(effective, article_text, handles, already_covered=covered)
            except Exception as exc:  # noqa: BLE001
                store.set_status(con, item["url_hash"], "error", story_key, str(exc)[:200])
                store.finish_research_job(con, item["url_hash"])
                _finish_actions(con, item, "blocked", f"writer error: {exc}")
                continue
        post = draft.get("post")
        if not post:
            _hold(con, item, result, "thin source")
            continue

        provider_resolution = None
        provider = draft.get("data_provider")
        pre_provider = None
        if (newsroom_outcome and provider
                and not _provider_matches(provider, resolution.selected)):
            _hold(con, item, result, "newsroom data-provider receipt mismatch")
            continue
        if provider and not _provider_matches(provider, resolution.selected):
            pre_provider = {
                "resolution": resolution, "effective": dict(effective),
                "article_text": article_text, "draft": draft, "post": post,
            }
            provider_key = (story_key, source_policy.normalize_alias(provider))
            if provider_key not in provider_cache:
                provider_cache[provider_key] = verify.resolve_data_provider(
                    effective, provider, con=con)
            provider_resolution = provider_cache[provider_key]
            provider_resolution = replace(
                provider_resolution,
                item_hash=resolution.item_hash,
                story_key=resolution.story_key,
                original_source_name=resolution.original_source_name,
                original=resolution.original,
            )
            if provider_resolution.held or not _provider_matches(provider, provider_resolution.selected):
                note = f"data provider source unresolved: {provider_resolution.note}"
                observed = replace(resolution, status="held", note=f"observe would hold: {note}"[:300])
                store.persist_resolution(con, observed, config.SOURCE_POLICY_MODE)
                if config.SOURCE_POLICY_MODE == "enforce":
                    _hold(con, item, result, note)
                    continue
                resolution = observed
                provider_resolution = None
            else:
                effective["url"] = provider_resolution.selected.url
                effective["source"] = provider_resolution.selected.display_name
                article_text = provider_resolution.selected_text
                store.persist_resolution(con, provider_resolution, config.SOURCE_POLICY_MODE)
                try:
                    provider_draft = brain.draft(
                        effective, article_text, handles, already_covered=covered)
                except Exception as exc:  # noqa: BLE001
                    provider_draft = None
                    provider_error = f"provider redraft failed: {exc}"
                else:
                    redraft_provider = provider_draft.get("data_provider")
                    provider_error = "" if provider_draft.get("post") and not (
                        redraft_provider and not _provider_matches(
                            redraft_provider, provider_resolution.selected)
                    ) else "provider redraft mismatch"
                if provider_error:
                    observed = replace(resolution, status="held",
                                       note=f"observe would hold: {provider_error}"[:300])
                    store.persist_resolution(con, observed, config.SOURCE_POLICY_MODE)
                    if config.SOURCE_POLICY_MODE == "enforce":
                        _hold(con, item, result, provider_error)
                        continue
                    resolution = observed
                    provider_resolution = None
                    effective = dict(item)
                    effective["url"] = resolution.selected.url
                    effective["source"] = resolution.selected.display_name
                    effective["_coverage_action"] = action
                    article_text = resolution.selected_text or original_texts.get(item["url_hash"], "")
                else:
                    draft, post, resolution = provider_draft, provider_draft["post"], provider_resolution

        effective["class"] = _evidence_class(resolution)
        prepared.setdefault(story_key, []).append({
            "item": item, "resolution": resolution, "effective": effective,
            "article_text": article_text, "draft": draft, "post": post,
            "covered": covered, "provider_resolution": provider_resolution,
            "pre_provider": pre_provider,
        })

    if newsroom_outcome:
        repair_requests = {}
        for rows in prepared.values():
            for candidate in rows:
                errors = lint.check(
                    candidate["post"],
                    {**candidate["draft"], "_source_text": candidate["article_text"]},
                    candidate["effective"],
                )
                story_id = candidate["draft"].get("newsroom_story_id")
                if errors and story_id and story_id not in repair_requests:
                    repair_requests[story_id] = {
                        "story_id": story_id, "errors": errors,
                        "current_post": candidate["post"],
                    }
        patches = {}
        if repair_requests:
            try:
                patches = newsroom_outcome.session.repair(list(repair_requests.values()))
            except Exception as exc:  # noqa: BLE001 - affected stories hold below
                log.warning("newsroom aggregate lint repair failed: %s", exc)
        for rows in prepared.values():
            for candidate in rows:
                story_id = candidate["draft"].get("newsroom_story_id")
                patch = patches.get(story_id)
                if not patch:
                    continue
                for key in (
                    "post", "event_date", "disclosure_date", "underlying_period_end",
                    "data_provider", "needs_second_source", "mentions_used", "numbers_used",
                ):
                    candidate["draft"][key] = patch.get(key)
                candidate["post"] = patch["post"]

    # Provider substitutions are now final for every candidate. Run terminal gates,
    # then rank each complete story group independently of feed order.
    for story_key in sorted(prepared):
        ready = []
        for candidate in prepared[story_key]:
            item, resolution = candidate["item"], candidate["resolution"]
            effective, article_text = candidate["effective"], candidate["article_text"]
            draft, post = candidate["draft"], candidate["post"]
            patched_provider = draft.get("data_provider")
            if (newsroom_outcome and patched_provider
                    and not _provider_matches(patched_provider, resolution.selected)):
                _hold(con, item, result, "newsroom patched data-provider receipt mismatch")
                continue
            freshness_date = draft.get("disclosure_date") or draft.get("event_date")
            if (store.event_is_stale(freshness_date, config.max_event_age_hours())
                    and not _override_allows(item, "freshness")):
                _hold(con, item, result, f"stale event: dated {freshness_date}, window "
                      f"{config.max_event_age_hours():g}h")
                continue
            if (store.event_is_stale(resolution.earliest_coverage_date,
                                     config.max_event_age_hours())
                    and not _override_allows(item, "freshness")):
                _hold(con, item, result,
                      f"stale event: earliest coverage {resolution.earliest_coverage_date}")
                continue
            errors = lint.check(post, {**draft, "_source_text": article_text}, effective)
            if errors and not newsroom_outcome:
                log.info("lint retry %s: %s", item["title"][:60], errors)
                try:
                    draft = brain.draft(
                        effective, article_text + "\n\n[Your previous draft was rejected by the "
                        f"style gate for: {'; '.join(errors)}. Rewrite avoiding exactly those violations.]",
                        handles, already_covered=candidate["covered"])
                    post = draft.get("post")
                    errors = lint.check(post, {**draft, "_source_text": article_text}, effective) \
                        if post else ["empty retry"]
                except Exception as exc:  # noqa: BLE001
                    errors = [f"retry failed: {exc}"]
            provider_resolution = candidate["provider_resolution"]
            if provider_resolution:
                final_provider = draft.get("data_provider")
                if final_provider and not _provider_matches(final_provider, provider_resolution.selected):
                    errors.append("provider mismatch after terminal redraft")
                support = verify.claims_supported(post, article_text) if post else {
                    "supported": False, "reason": "empty provider redraft"}
                if not support.get("supported"):
                    errors.append(f"provider claim support: {support.get('reason', 'ambiguous')}")
            if errors and provider_resolution and config.SOURCE_POLICY_MODE == "observe":
                # Observe records the terminal provider veto but stages the legacy,
                # pre-provider candidate. General lint still applies to that fallback.
                fallback = candidate["pre_provider"]
                note = "observe would hold: provider terminal gate: " + "; ".join(errors)
                resolution = replace(fallback["resolution"], status="held", note=note[:300])
                store.persist_resolution(con, resolution, config.SOURCE_POLICY_MODE)
                effective = dict(fallback["effective"])
                article_text = fallback["article_text"]
                draft, post = fallback["draft"], fallback["post"]
                provider_resolution = None
                errors = lint.check(post, {**draft, "_source_text": article_text}, effective)
                if errors:
                    try:
                        draft = brain.draft(
                            effective,
                            article_text + "\n\n[Your previous draft was rejected by the "
                            f"style gate for: {'; '.join(errors)}. Rewrite avoiding exactly "
                            "those violations.]",
                            handles, already_covered=candidate["covered"])
                        post = draft.get("post")
                        errors = lint.check(
                            post, {**draft, "_source_text": article_text}, effective
                        ) if post else ["empty retry"]
                    except Exception as exc:  # noqa: BLE001
                        errors = [f"retry failed: {exc}"]
            if errors:
                if _override_allows(item, "style"):
                    log.warning("owner override stages lint-held copy %s: %s",
                                item["title"][:60], errors)
                    errors = []
            if errors:
                _hold(con, item, result, "lint: " + "; ".join(errors)[:294])
                log.warning("lint held %s: %s", item["title"][:60], errors)
                continue
            candidate.update(
                draft=draft, post=post, resolution=resolution, effective=effective,
                article_text=article_text, provider_resolution=provider_resolution)
            ready.append(candidate)
        if not ready:
            continue

        ready.sort(key=lambda row: (_resolution_rank(row["resolution"]), row["item"]["url"]))
        chosen = ready[0]
        group_action_ids = [action_id for row in ready for action_id in _action_ids(row["item"])]
        group_gates = [gate for row in ready for gate in (
            [row["item"].get("_operator_gate")] if row["item"].get("_operator_gate") else [])]
        for superseded in ready[1:]:
            store.set_status(con, superseded["item"]["url_hash"], "skipped", story_key,
                             "stronger final receipt selected")
            store.finish_research_job(con, superseded["item"]["url_hash"])
        item, resolution = chosen["item"], chosen["resolution"]
        item["_operator_action_ids"] = group_action_ids
        item["_operator_gates"] = group_gates
        effective, article_text = chosen["effective"], chosen["article_text"]
        draft, post = chosen["draft"], chosen["post"]
        provider_resolution = chosen["provider_resolution"]
        klass = _evidence_class(resolution)
        evidence_count = store.qualified_evidence_count(
            con, story_key, max(config.SOURCE_EVIDENCE_LOOKBACK_HOURS,
                                config.max_event_age_hours()))
        if klass == "secondary" and evidence_count >= 2:
            klass = "corroborated"
        effective["class"] = klass
        if (draft.get("needs_second_source") and klass == "secondary"
                and not _override_allows(item, "corroboration")):
            _hold(con, item, result, f"needs second source ({resolution.note})")
            continue

        editor_note = None
        if config.SOURCE_POLICY_MODE == "enforce" or newsroom_outcome:
            from . import editor
            if newsroom_outcome:
                ed = editor.review_newsroom(
                    post, effective, con, source_text=article_text,
                    claims=draft.get("claims") or [],
                    provenance={
                        "url": resolution.selected.url,
                        "source": resolution.selected.display_name,
                        "source_id": resolution.selected.source_id,
                        "tier": resolution.selected.tier,
                        "originality": resolution.originality,
                        "content_fingerprint": resolution.content_fingerprint,
                    },
                )
            else:
                ed = editor.review(post, effective, con)
            editor_note = f"{ed['verdict']}: {ed['reason']}"[:300]
            if newsroom_outcome and ed.get("claims_supported") is not True:
                _hold(con, item, result, f"editor support failed: {ed['reason'][:210]}")
                continue
            if ed["verdict"] == "spike" and not _override_allows(item, "editor"):
                _hold(con, item, result, f"editor spiked: {ed['reason'][:220]}")
                continue
            if ed["verdict"] == "revise" and ed["post"] != post:
                revised_errors = lint.check(ed["post"], {**draft, "_source_text": article_text}, effective)
                if provider_resolution:
                    support = verify.claims_supported(ed["post"], article_text)
                    if not support.get("supported"):
                        revised_errors.append("editor revision unsupported by provider source")
                if not revised_errors:
                    post = ed["post"]
                elif newsroom_outcome:
                    _hold(con, item, result,
                          "newsroom editor revision failed deterministic gates")
                    continue
                else:
                    log.warning("editor revision failed final gates; original retained")

        receipt_url = effective["url"]
        if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
            raise RuntimeError("cycle lease lost before delivery")
        chart = sources.chart_image(receipt_url)
        publisher_backend = publisher.backend_name()
        newsroom_story_id = draft.get("newsroom_story_id")
        if newsroom_outcome and newsroom_story_id:
            store.set_newsroom_story_state(
                con, pipeline_run_id, newsroom_story_id, "materialized")
        mode, publisher_ref = publisher.publish(
            post, receipt_url, klass, image=chart,
            force_draft=bool(_action_ids(item)) or newsroom_mode == "draft")
        lifecycle = {
            "IMMEDIATE": ("posted", "posted"), "DRAFT": ("drafted", "drafted"),
            "UNCERTAIN": ("uncertain", "uncertain"), "FAILED": ("failed", "failed"),
            "TAPE": ("taped", "taped"),
        }
        item_status, counter = lifecycle.get(mode, ("failed", "failed"))
        store.set_status(con, item["url_hash"], item_status, story_key)
        store.log_post(con, story_key, item["url_hash"], klass, post, receipt_url, mode,
                       publisher_ref, editor_note=editor_note, resolution_id=item["url_hash"],
                       publisher_backend=publisher_backend)
        store.finish_research_job(con, item["url_hash"])
        _finish_actions(con, item, "completed", f"delivery result: {mode}")
        if newsroom_outcome and newsroom_story_id:
            store.set_newsroom_story_state(
                con, pipeline_run_id, newsroom_story_id,
                "delivered" if mode != "FAILED" else "held", publisher_ref or "")
        result[counter] += 1
    if newsroom_outcome:
        con.execute(
            "UPDATE newsroom_story_commits SET state='held',updated_at=?"
            " WHERE run_id=? AND state='pending'",
            (time.time(), pipeline_run_id),
        )
        con.commit()
        store.set_newsroom_state(
            con, pipeline_run_id, "completed", counters=newsroom_outcome.counters)
        result["newsroom"]["status"] = "completed"
    store.record_decision_run(
        con, pending + retry_verdicts, verdicts, result, run_started,
        theme_snapshot=theme_snapshot)
    return result


class Health(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(self.path)
        if parsed.path != "/item-action":
            self.send_response(404)
            self.end_headers()
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 4096)
        except ValueError:
            length = 0
        q = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
        token = (q.get("k") or [""])[0]
        if not config.REPORT_TOKEN or token != config.REPORT_TOKEN:
            self.send_response(403)
            self.end_headers()
            return
        item_hash = (q.get("id") or [""])[0]
        action = (q.get("action") or [""])[0]
        day = (q.get("d") or [""])[0]
        con = store.connect()
        try:
            outcome = store.request_operator_action(con, item_hash, action)
        finally:
            con.close()
        if not outcome["ok"]:
            self.send_response(409)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(outcome["reason"].encode())
            return
        self.send_response(303)
        self.send_header("Location", f"/report?k={token}" + (f"&d={day}" if day else ""))
        self.end_headers()

    def do_GET(self):  # noqa: N802
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(self.path)
        if parsed.path == "/dismiss":
            q = parse_qs(parsed.query)
            token = (q.get("k") or [""])[0]
            if not config.REPORT_TOKEN or token != config.REPORT_TOKEN:
                self.send_response(403)
                self.end_headers()
                return
            kind = (q.get("kind") or [""])[0]
            ref = (q.get("id") or [""])[0]
            day = (q.get("d") or [""])[0]
            if kind in ("post", "item", "audit") and ref:
                con = store.connect()
                store.kv_set(con, f"dismissed:{kind}:{ref}",
                             str(time.time()))
                con.close()
            self.send_response(302)
            self.send_header("Location", f"/report?k={token}" + (f"&d={day}" if day else ""))
            self.end_headers()
            return
        if parsed.path == "/report":
            token = (parse_qs(parsed.query).get("k") or [""])[0]
            if not config.REPORT_TOKEN or token != config.REPORT_TOKEN:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"forbidden")
                return
            from . import report
            day = (parse_qs(parsed.query).get("d") or [None])[0]
            con = store.connect()
            body = report.render(con, day=day).encode()
            con.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        con = store.connect()
        body = json.dumps({**STATE, "db": store.status_summary(con),
                           "autopost": config.AUTOPOST_ENABLED,
                           "source_policy_mode": config.SOURCE_POLICY_MODE,
                           "delivery_guard": "draft-only" if config.SOURCE_POLICY_MODE == "observe"
                                             else "normal"}).encode()
        con.close()
        stale = time.time() - STATE.get("last_cycle_ts", STATE["started"]) > 600
        self.send_response(500 if stale else 200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # quiet
        pass


def run():
    threading.Thread(
        target=lambda: ThreadingHTTPServer(("0.0.0.0", config.PORT), Health).serve_forever(),
        daemon=True,
    ).start()
    log.info("next-block-news worker up; autopost=%s source_policy=%s poll=%ss",
             config.AUTOPOST_ENABLED, config.SOURCE_POLICY_MODE, config.POLL_SECONDS)
    con = store.connect()
    while True:
        try:
            STATE["last_cycle"] = worker_iteration(con)
            STATE["cycles"] += 1
            if not STATE["last_cycle"].get("skipped_locked"):
                STATE["last_cycle_ts"] = time.time()
                STATE["last_error"] = None
                store.kv_set(con, "worker:last_success", str(STATE["last_cycle_ts"]))
                if config.HEARTBEAT_URL:
                    try:
                        import httpx
                        httpx.get(config.HEARTBEAT_URL, timeout=5)
                    except Exception:  # noqa: BLE001 - heartbeat failure never breaks news
                        pass
        except Exception as exc:  # noqa: BLE001 - the loop survives everything
            STATE["last_error"] = str(exc)[:300]
            log.exception("cycle failed")
        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    run()
