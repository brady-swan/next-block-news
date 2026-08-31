"""The loop: poll -> triage -> draft -> gate -> publish. Plus a /health endpoint."""
import json
import logging
import threading
import time
import uuid
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import brain, briefing, config, lint, publisher, source_policy, sources, store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("nbn.main")

STATE = {"started": time.time(), "cycles": 0, "last_cycle": None, "last_error": None}


def _hold(con, item, result, note):
    store.set_status(con, item["url_hash"], "held", item.get("story_key"), note[:300])
    result["held"] += 1


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
    try:
        # Repair human-published Typefully drafts before any coverage/dedup decisions.
        publisher.reconcile_publications(con)
        result = _cycle_locked(con, owner)
        if scheduled:
            if config.NODE_READ_TOKEN:
                briefing.maybe_run(con)
            if config.AUDIT_UTC:
                from . import audit
                audit.maybe_run(con)
        return result
    finally:
        store.release_cycle_lease(con, owner)


def cycle(con) -> dict:
    """Run one news cycle under the same lease used by the deployed worker."""
    return _lease_run(con, scheduled=False)


def worker_iteration(con) -> dict:
    """Run news, briefing, and audit as one cross-process critical section."""
    return _lease_run(con, scheduled=True)


def _cycle_locked(con, lease_owner: str) -> dict:
    """Resolve and prepare complete story groups before choosing one final receipt."""
    from . import verify

    run_started = time.time()
    items = (sources.fetch_feeds() + sources.fetch_edgar()
             + sources.fetch_perception() + sources.fetch_x(con))
    if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
        raise RuntimeError("cycle lease lost after fetch")
    inserted = store.upsert_new_items(con, items)
    summaries = {store.url_hash(i["url"]): i.get("summary", "") for i in items}
    pending = store.pending_items(con, config.MAX_ITEMS_PER_TRIAGE)
    fresh = []
    for it in pending:
        if store.is_stale(it.get("published", "")):
            store.set_status(con, it["url_hash"], "skipped", None, "stale at intake")
            continue
        if store.is_non_english(it.get("title", "")):
            store.set_status(con, it["url_hash"], "skipped", None, "non-English source")
            continue
        it["summary"] = summaries.get(it["url_hash"], it.get("summary", ""))
        fresh.append(it)
    result = {"fetched": len(items), "new": len(inserted), "considered": len(pending),
              "pending": len(fresh),
              "drafted": 0, "held": 0, "posted": 0, "uncertain": 0,
              "failed": 0, "taped": 0, "policy_held": 0}
    if not fresh:
        store.record_decision_run(con, pending, [], result, run_started)
        return result

    verdicts = brain.triage(fresh, store.recent_story_keys(con), store.open_story_keys(con))
    handles = lint.verified_handles()
    resolutions, original_texts = {}, {}

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
        if action == "draft" and store.story_handled(con, story_key):
            continue
        if action == "update" and not store.story_reader_covered(con, story_key):
            continue
        item["_coverage_action"] = action
        fetched = sources.fetch_article(item["url"])
        text = fetched["text"]
        item["_final_url"] = fetched["final_url"]
        item["_canonical_url"] = fetched["canonical_url"]
        item["_byline"] = fetched["byline"]
        original_texts[item["url_hash"]] = text
        resolution = verify.resolve_source(item, text, con=con)
        resolutions[item["url_hash"]] = resolution
        store.persist_resolution(con, resolution, config.SOURCE_POLICY_MODE)
    if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
        raise RuntimeError("cycle lease lost after resolution")

    prepared: dict[str, list[dict]] = {}
    provider_cache = {}
    for item in verdicts:
        action, story_key = item.get("action", "skip"), item.get("story_key")
        if action not in ("draft", "update"):
            status = "skipped" if action == "skip" else "held"
            store.set_status(con, item["url_hash"], status, story_key, item.get("reason"))
            if status == "held":
                result["held"] += 1
            continue
        if action == "draft" and store.story_handled(con, story_key):
            store.set_status(con, item["url_hash"], "skipped", story_key, "story already handled")
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
        effective_ts = store.effective_post_ts_sql()
        covered = [row["body"].split("\n")[0][:200] for row in con.execute(
            "SELECT body FROM posts WHERE story_key=?"
            " AND mode IN ('IMMEDIATE','UNCERTAIN')"
            f" ORDER BY {effective_ts} DESC LIMIT 2",
            (story_key,)).fetchall()]
        try:
            draft = brain.draft(effective, article_text, handles, already_covered=covered)
        except Exception as exc:  # noqa: BLE001
            store.set_status(con, item["url_hash"], "error", story_key, str(exc)[:200])
            continue
        post = draft.get("post")
        if not post:
            _hold(con, item, result, "thin source")
            continue

        provider_resolution = None
        provider = draft.get("data_provider")
        pre_provider = None
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

    # Provider substitutions are now final for every candidate. Run terminal gates,
    # then rank each complete story group independently of feed order.
    for story_key in sorted(prepared):
        ready = []
        for candidate in prepared[story_key]:
            item, resolution = candidate["item"], candidate["resolution"]
            effective, article_text = candidate["effective"], candidate["article_text"]
            draft, post = candidate["draft"], candidate["post"]
            if store.event_is_stale(draft.get("event_date"), config.max_event_age_hours()):
                _hold(con, item, result, f"stale event: dated {draft['event_date']}, window "
                      f"{config.max_event_age_hours():g}h")
                continue
            if store.event_is_stale(resolution.earliest_coverage_date, config.max_event_age_hours()):
                _hold(con, item, result,
                      f"stale event: earliest coverage {resolution.earliest_coverage_date}")
                continue
            errors = lint.check(post, {**draft, "_source_text": article_text}, effective)
            if errors:
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
        for superseded in ready[1:]:
            store.set_status(con, superseded["item"]["url_hash"], "skipped", story_key,
                             "stronger final receipt selected")
        item, resolution = chosen["item"], chosen["resolution"]
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
        if draft.get("needs_second_source") and klass == "secondary":
            _hold(con, item, result, f"needs second source ({resolution.note})")
            continue

        editor_note = None
        if config.SOURCE_POLICY_MODE == "enforce":
            from . import editor
            ed = editor.review(post, effective, con)
            editor_note = f"{ed['verdict']}: {ed['reason']}"[:300]
            if ed["verdict"] == "spike":
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
                else:
                    log.warning("editor revision failed final gates; original retained")

        receipt_url = effective["url"]
        if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
            raise RuntimeError("cycle lease lost before delivery")
        chart = sources.chart_image(receipt_url)
        publisher_backend = publisher.backend_name()
        mode, publisher_ref = publisher.publish(post, receipt_url, klass, image=chart)
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
        result[counter] += 1
    store.record_decision_run(con, pending, verdicts, result, run_started)
    return result


class Health(BaseHTTPRequestHandler):
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
