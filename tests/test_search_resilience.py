import json
import time
import unittest
import datetime
from unittest.mock import Mock, patch

from nbn import config, newsroom, report, search, sources, store
from scripts import search_smoke
from tests.support import item, temporary_store


def saved_candidate(con, suffix="one"):
    stored = store.upsert_new_items(con, [item(
        url=f"https://example.com/{suffix}",
        title=f"Bitcoin development {suffix}",
    )])[0]
    return dict(con.execute(
        "SELECT * FROM items WHERE url_hash=?", (stored["url_hash"],)
    ).fetchone())


def tool_block(query="Bitcoin policy", candidate_ids=None, block_id="search-1"):
    block = Mock()
    block.name = "search_web"
    block.input = {"query": query}
    if candidate_ids is not None:
        block.input["candidate_ids"] = candidate_ids
    block.id = block_id
    return block


def healthy_snapshot(remaining=4000):
    return {
        "provider": "serpapi", "state": "healthy", "plan_name": "Developer Plan",
        "plan_renewal_date": "2026-09-06", "searches_per_month": 5000,
        "this_month_usage": 1000, "total_searches_left": remaining,
        "this_hour_searches": 1, "last_hour_searches": 2,
        "account_rate_limit_per_hour": 1000,
    }


class SearchResilienceTests(unittest.TestCase):
    def test_search_tool_schema_uses_anthropic_supported_keywords(self):
        search_tool = next(tool for tool in newsroom.TOOLS if tool["name"] == "search_web")
        candidate_ids = search_tool["input_schema"]["properties"]["candidate_ids"]
        self.assertNotIn("maxItems", candidate_ids)

    def test_cache_identity_is_parameter_complete_and_unsafe_rows_do_not_persist(self):
        with temporary_store() as con:
            base = search.request_identity("  Bitcoin   policy ", max_results=5)
            different_limit = search.request_identity("Bitcoin policy", max_results=4)
            different_locale = search.request_identity(
                "Bitcoin policy", max_results=5, gl="gb"
            )
            self.assertNotEqual(base["cache_key"], different_limit["cache_key"])
            self.assertNotEqual(base["cache_key"], different_locale["cache_key"])
            stored = store.search_cache_put(con, base, [
                {"rank": 1, "url": "https://sec.gov/release", "outlet": "SEC",
                 "title": "Release", "snippet": "Details"},
                {"rank": 2, "url": "http://127.0.0.1/private", "outlet": "local"},
            ], ttl_seconds=3600, now=100)
            self.assertEqual(len(stored), 1)
            self.assertEqual(store.search_cache_get(con, base, now=101), stored)
            self.assertIsNone(store.search_cache_get(con, different_limit, now=101))
            self.assertIsNone(store.search_cache_get(con, different_locale, now=101))
            con.execute(
                "UPDATE search_query_cache SET results_json=? WHERE cache_key=?",
                ('[{"rank":"bad","url":"https://sec.gov/release"}]', base["cache_key"]),
            )
            con.commit()
            self.assertIsNone(store.search_cache_get(con, base, now=102))

    def test_cached_results_work_while_shared_quota_is_exhausted(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True):
            row = saved_candidate(con)
            identity = search.request_identity("Bitcoin policy", max_results=5)
            cached = store.search_cache_put(con, identity, [{
                "rank": 1, "url": "https://reuters.com/bitcoin", "outlet": "Reuters",
                "title": "Bitcoin report", "snippet": "Report",
            }], ttl_seconds=3600)
            store.record_search_account_status(con, healthy_snapshot(remaining=0))
            session = newsroom.NewsroomSession(
                run_id="cache:quota", inventory=[row], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            with patch.object(search, "google") as google:
                result = json.loads(session._dispatch(tool_block(
                    candidate_ids=[row["url_hash"]]
                ))["content"])
            self.assertTrue(result["ok"])
            self.assertTrue(result["cached"])
            self.assertEqual(result["results"], cached)
            google.assert_not_called()
            self.assertEqual(session.counters()["search_cache_hits"], 1)

    def test_zero_quota_is_checked_once_and_skips_provider_across_sessions(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True), \
                patch.object(search, "account_status", return_value=healthy_snapshot(0)) as status, \
                patch.object(search, "google") as google:
            row = saved_candidate(con)
            for index in range(2):
                session = newsroom.NewsroomSession(
                    run_id=f"quota:{index}", inventory=[row], recent_clusters=[],
                    theme_snapshot=[], handles={}, con=con, reservation="token",
                )
                result = json.loads(session._dispatch(tool_block(
                    query=f"Bitcoin policy {index}", candidate_ids=[row["url_hash"]],
                    block_id=f"search-{index}",
                ))["content"])
                self.assertEqual(result["reason"], "quota_exhausted")
            self.assertEqual(status.call_count, 1)
            google.assert_not_called()

    def test_account_refresh_preserves_search_endpoint_circuits(self):
        with temporary_store() as con:
            store.record_search_account_status(con, healthy_snapshot(), now=100)
            store.record_search_failure(
                con, "serpapi", "rate_limited", "hourly limit",
                retry_after_seconds=300, now=110,
            )
            store.record_search_account_status(con, healthy_snapshot(3999), now=120)
            state = store.search_provider_state(con)
            self.assertEqual(state["state"], "rate_limited")
            self.assertEqual(state["next_search_at"], 410)
            self.assertEqual(state["consecutive_failures"], 1)

            store.record_search_success(con, "serpapi", now=500)
            store.record_search_failure(
                con, "serpapi", "transport", "network one", now=510
            )
            store.record_search_failure(
                con, "serpapi", "transport", "network two", now=511
            )
            store.record_search_account_status(con, healthy_snapshot(3998), now=520)
            state = store.search_provider_state(con)
            self.assertEqual(state["state"], "degraded")
            self.assertEqual(state["next_search_at"], 811)
            self.assertEqual(state["consecutive_failures"], 2)

    def test_missing_capacity_does_not_cancel_known_quota_state(self):
        with temporary_store() as con:
            store.record_search_account_status(con, healthy_snapshot(0), now=100)
            before = store.search_provider_state(con)
            incomplete = healthy_snapshot()
            incomplete.pop("total_searches_left")
            incomplete["state"] = "unknown"
            store.record_search_account_status(con, incomplete, now=200)
            after = store.search_provider_state(con)
            self.assertEqual(after["state"], "quota_exhausted")
            self.assertEqual(after["next_search_at"], before["next_search_at"])
            self.assertEqual(after["total_searches_left"], 0)

    def test_missing_capacity_marks_healthy_snapshot_unknown_and_fails_open(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True):
            store.record_search_account_status(con, healthy_snapshot(), now=time.time() - 600)
            incomplete = healthy_snapshot()
            incomplete.pop("total_searches_left")
            incomplete["state"] = "unknown"
            store.record_search_account_status(con, incomplete, now=time.time() - 500)
            state = store.search_provider_state(con)
            self.assertEqual(state["state"], "unknown")
            self.assertEqual(state["total_searches_left"], 4000)

            row = saved_candidate(con)
            session = newsroom.NewsroomSession(
                run_id="capacity:unknown", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            with patch.object(search, "account_status", side_effect=search.SearchError(
                    "status unavailable", kind="transport")), \
                    patch.object(search, "google", return_value=[]) as google:
                result = json.loads(session._dispatch(tool_block(
                    query="Bitcoin unknown capacity", candidate_ids=[row["url_hash"]]
                ))["content"])
            self.assertTrue(result["ok"])
            google.assert_called_once()

    def test_quota_failure_uses_renewal_not_retry_after(self):
        renewal = datetime.datetime(2026, 9, 6, tzinfo=datetime.timezone.utc).timestamp()
        now = renewal - 86400
        with temporary_store() as con:
            store.record_search_account_status(con, healthy_snapshot(), now=now - 10)
            store.record_search_failure(
                con, "serpapi", "quota_exhausted", "no searches",
                retry_after_seconds=3600, now=now,
            )
            state = store.search_provider_state(con)
            self.assertEqual(state["state"], "quota_exhausted")
            self.assertEqual(state["next_search_at"], renewal)
            store.record_search_account_failure(
                con, "serpapi", "transport", "status unavailable", now=now + 60
            )
            self.assertEqual(
                store.search_provider_state(con)["next_search_at"], renewal
            )

    def test_account_upgrade_clears_known_zero_before_provider_search(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True):
            row = saved_candidate(con)
            store.record_search_account_status(con, healthy_snapshot(0), now=time.time() - 600)
            con.execute(
                "UPDATE search_provider_state SET last_status_attempt_at=? WHERE provider='serpapi'",
                (time.time() - 600,),
            )
            con.commit()
            results = [{"rank": 1, "url": "https://sec.gov/new", "outlet": "SEC",
                        "title": "New", "snippet": "New"}]
            session = newsroom.NewsroomSession(
                run_id="quota:upgrade", inventory=[row], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            with patch.object(search, "account_status", return_value=healthy_snapshot(4000)), \
                    patch.object(search, "google", return_value=results) as google:
                result = json.loads(session._dispatch(tool_block(
                    candidate_ids=[row["url_hash"]]
                ))["content"])
            self.assertTrue(result["ok"])
            google.assert_called_once()
            self.assertEqual(store.search_provider_state(con)["state"], "healthy")

    def test_expired_quota_half_open_probe_recovers_after_status_failure(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True):
            row = saved_candidate(con)
            store.record_search_account_status(con, healthy_snapshot(0))
            con.execute(
                "UPDATE search_provider_state SET next_search_at=?,last_status_attempt_at=?"
                " WHERE provider='serpapi'",
                (time.time() - 1, time.time() - 600),
            )
            con.commit()
            session = newsroom.NewsroomSession(
                run_id="quota:probe", inventory=[row], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            with patch.object(search, "account_status", side_effect=search.SearchError(
                    "status down", kind="transport")), \
                    patch.object(search, "google", return_value=[]):
                result = json.loads(session._dispatch(tool_block(
                    candidate_ids=[row["url_hash"]]
                ))["content"])
            self.assertTrue(result["ok"])
            state = store.search_provider_state(con)
            self.assertEqual(state["state"], "healthy")
            self.assertIsNone(state["probe_claim_token"])

    def test_half_open_claim_is_exclusive_and_abandoned_claim_expires(self):
        with temporary_store() as first:
            second = store.connect()
            try:
                store.record_search_account_status(first, healthy_snapshot(0), now=100)
                first.execute(
                    "UPDATE search_provider_state SET next_search_at=99,last_status_attempt_at=100"
                    " WHERE provider='serpapi'"
                )
                first.commit()
                token = store.claim_search_probe(first, "serpapi", lease_seconds=30, now=101)
                self.assertTrue(token)
                self.assertEqual(
                    store.claim_search_probe(second, "serpapi", lease_seconds=30, now=102), ""
                )
                replacement = store.claim_search_probe(
                    second, "serpapi", lease_seconds=30, now=132
                )
                self.assertTrue(replacement)
                self.assertNotEqual(replacement, token)
                self.assertFalse(store.record_search_success(
                    first, "serpapi", probe_token=token, now=133
                ))
                self.assertTrue(store.record_search_success(
                    second, "serpapi", probe_token=replacement, now=133
                ))
            finally:
                second.close()

    def test_status_refresh_and_half_open_probe_are_serialized(self):
        with temporary_store() as first:
            second = store.connect()
            try:
                now = time.time()
                store.record_search_account_status(first, healthy_snapshot(0), now=now - 600)
                first.execute(
                    "UPDATE search_provider_state SET next_search_at=?,last_status_attempt_at=?"
                    " WHERE provider='serpapi'",
                    (now - 1, now - 600),
                )
                first.commit()
                status_claim = store.claim_search_status_check(
                    first, "serpapi", ttl_seconds=300, lease_seconds=30, now=now
                )
                self.assertTrue(status_claim["token"])
                blocked = store.claim_search_status_check(
                    second, "serpapi", ttl_seconds=300, lease_seconds=30, now=now + 1
                )
                self.assertEqual(blocked["reason"], "in_progress")
                self.assertEqual(
                    store.claim_search_probe(
                        second, "serpapi", lease_seconds=30, now=now + 1
                    ),
                    "",
                )
                failure = store.fail_search_status_and_claim_probe(
                    first, "serpapi", "transport", "status down",
                    status_token=status_claim["token"], probe_lease_seconds=30,
                    now=now + 2,
                )
                self.assertTrue(failure["recorded"])
                self.assertTrue(failure["probe_token"])
                self.assertFalse(store.record_search_account_status(
                    second, healthy_snapshot(), status_token="stale", now=now + 3
                ))
                self.assertEqual(
                    store.search_provider_state(second)["probe_claim_token"],
                    failure["probe_token"],
                )
                self.assertTrue(store.record_search_success(
                    first, "serpapi", probe_token=failure["probe_token"], now=now + 4
                ))
            finally:
                second.close()

    def test_oversized_persisted_search_fields_fail_safely(self):
        with temporary_store() as con:
            identity = search.request_identity("Bitcoin policy", max_results=5)
            valid = {"rank": 1, "url": "https://sec.gov/release", "outlet": "SEC",
                     "title": "Release", "snippet": "Details"}
            for field, value in (
                ("url", "https://sec.gov/" + "x" * 2000),
                ("title", "x" * 301),
                ("snippet", "x" * 1201),
            ):
                row = {**valid, field: value}
                store.search_cache_put(con, identity, [valid], ttl_seconds=3600, now=100)
                con.execute(
                    "UPDATE search_query_cache SET results_json=? WHERE cache_key=?",
                    (json.dumps([row]), identity["cache_key"]),
                )
                con.commit()
                self.assertIsNone(store.search_cache_get(con, identity, now=101))
            con.execute(
                "INSERT INTO search_result_pointers(scope_type,scope_key,provider,url,"
                "outlet,title,snippet,observed_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)",
                ("candidate", "candidate-one", "serpapi", "https://sec.gov/" + "x" * 2000,
                 "SEC", "Release", "Details", 100, 1000),
            )
            con.commit()
            self.assertEqual(store.search_pointers_for_scopes(
                con, [("candidate", "candidate-one")], now=101
            ), [])

    def test_candidate_search_pointers_reappear_as_uninspected_references(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True), \
                patch.object(search, "account_status", return_value=healthy_snapshot()), \
                patch.object(search, "google", return_value=[{
                    "rank": 1, "url": "https://reuters.com/bitcoin-policy",
                    "outlet": "Reuters", "title": "Bitcoin policy",
                    "snippet": "A policy development.",
                }]):
            row = saved_candidate(con)
            first = newsroom.NewsroomSession(
                run_id="pointer:first", inventory=[row], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            result = json.loads(first._dispatch(tool_block(
                candidate_ids=[row["url_hash"]]
            ))["content"])
            self.assertTrue(result["ok"])
            second = newsroom.NewsroomSession(
                run_id="pointer:second", inventory=[row], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            packet = second._initial_packet()
            pointers = [value for value in packet["reference_board"]
                        if value["kind"] == "prior_search_result"]
            self.assertEqual(len(pointers), 1)
            self.assertEqual(pointers[0]["status"], "uninspected_pointer")
            self.assertEqual(packet["prepared_evidence"], [])
            self.assertEqual(second.counters()["search_pointer_reuse"], 1)

    def test_unknown_candidate_scope_is_rejected_before_provider_work(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True), \
                patch.object(search, "account_status") as status, \
                patch.object(search, "google") as google:
            row = saved_candidate(con)
            session = newsroom.NewsroomSession(
                run_id="scope:unknown", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            result = json.loads(session._dispatch(tool_block(
                candidate_ids=["not-on-this-desk"]
            ))["content"])
            self.assertEqual(result["kind"], "unknown_candidate_scope")
            status.assert_not_called()
            google.assert_not_called()

    def test_repeated_transport_failures_open_shared_cooldown(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True), \
                patch.object(search, "account_status", return_value=healthy_snapshot()), \
                patch.object(search, "google", side_effect=search.SearchError(
                    "network unavailable", kind="transport"
                )) as google:
            row = saved_candidate(con)
            session = newsroom.NewsroomSession(
                run_id="transport:twice", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            first = json.loads(session._dispatch(tool_block(
                query="Bitcoin policy one", candidate_ids=[row["url_hash"]],
            ))["content"])
            second = json.loads(session._dispatch(tool_block(
                query="Bitcoin policy two", candidate_ids=[row["url_hash"]],
                block_id="search-2",
            ))["content"])
            third = json.loads(session._dispatch(tool_block(
                query="Bitcoin policy three", candidate_ids=[row["url_hash"]],
                block_id="search-3",
            ))["content"])
            self.assertEqual(first["kind"], "search_retryable")
            self.assertEqual(second["kind"], "search_unavailable_for_run")
            self.assertEqual(third["kind"], "search_unavailable_for_run")
            self.assertEqual(google.call_count, 2)
            self.assertEqual(store.search_provider_state(con)["state"], "degraded")

    def test_report_exposes_safe_search_health_and_fetch_failures(self):
        with temporary_store() as con:
            store.record_search_account_status(con, healthy_snapshot())
            store.record_search_activity(con, "report:run", "provider_http_attempt")
            store.record_search_activity(con, "report:run", "cache_hit")
            html = report.render(con)
            self.assertIn("Search · shared account", html)
            self.assertIn("Developer Plan", html)
            self.assertIn("4000 / 5000 remaining", html)
            self.assertIn("provider HTTP 1", html)
            self.assertNotIn("api_key", html)

    def test_production_smoke_path_respects_quota_and_cooldown(self):
        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True), \
                patch.object(search, "account_status", return_value=healthy_snapshot(0)), \
                patch.object(search, "google") as google:
            with self.assertRaisesRegex(RuntimeError, "quota_exhausted"):
                search_smoke.run("Bitcoin quota smoke", con=con)
            google.assert_not_called()

        with temporary_store() as con, \
                patch.object(config, "SEARCH_RESILIENCE_ENABLED", True), \
                patch.object(search, "account_status", return_value=healthy_snapshot()), \
                patch.object(search, "google") as google:
            store.record_search_account_status(con, healthy_snapshot())
            store.record_search_failure(
                con, "serpapi", "rate_limited", "hourly limit",
                retry_after_seconds=300,
            )
            with self.assertRaisesRegex(RuntimeError, "rate_limited"):
                search_smoke.run("Bitcoin cooldown smoke", con=con)
            google.assert_not_called()

    def test_fetch_failure_kinds_separate_publisher_blocking(self):
        with temporary_store() as con:
            row = saved_candidate(con)
            session = newsroom.NewsroomSession(
                run_id="fetch:block", inventory=[row], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            with patch.object(sources, "fetch_article", return_value={
                "outcome": "http_error", "error_kind": "status_403",
                "error_message": "blocked",
            }):
                result = session._fetch(row["url"], intake=row)
            self.assertFalse(result["ok"])
            self.assertEqual(session.counters()["fetch_failure_kinds"], {"status_403": 1})


if __name__ == "__main__":
    unittest.main()
