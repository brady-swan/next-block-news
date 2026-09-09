import copy
import datetime as dt
import json
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock

import httpx

from nbn import config, perception as p, newsroom, sources, store, writer_memory, desk_api, editor
from tests.support import temporary_store
from tests.test_reporter_writer import session

FIXTURE = json.loads((Path(__file__).parent / "fixtures/perception-2026-09-09.json").read_text())
NOW = 1788929000
URL = "https://bitcoinmagazine.com/news/lummis-blasts-democrats-on-clarity-act"


def article(now=NOW, text="Useful dated Bitcoin reporting."):
    return p.article_row({"Title": "Lummis CLARITY", "URL": URL, "Content": text,
                          "Date": "2026-09-08 20:56:30 UTC", "Outlet": "Bitcoin Magazine"}, now)


def transport(response):
    mock = Mock()
    mock.__enter__ = Mock(return_value=mock)
    mock.__exit__ = Mock(return_value=False)
    mock.stream.return_value.__enter__ = Mock(return_value=response)
    mock.stream.return_value.__exit__ = Mock(return_value=False)
    return mock


class PerceptionTests(unittest.TestCase):
    def test_rest_exhaustion_and_shared_minute_are_distinct(self):
        with temporary_store() as con:
            p.observe_quota(con, "rest", {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(NOW+3600)}, NOW)
            self.assertEqual(p.availability(con, "rest", "intake", NOW), "rest_reported_quota_exhausted")
            self.assertEqual(p.availability(con, "mcp", "writer", NOW), "")
            self.assertEqual(p.summary(con, NOW)["reported_rest_quota"]["remaining"], 0)
            p.observe_quota(con, "mcp", {"ratelimit-policy": "60;w=60", "ratelimit-remaining": "0"}, NOW)
            self.assertEqual(p.availability(con, "mcp", "writer", NOW), "shared_minute_limit")

    def test_stream_deadline_does_not_wait_for_unbounded_drip(self):
        client = transport(httpx.Response(200, text=FIXTURE["samples"][0]["body"]))
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(p.httpx, "Client", return_value=client), \
                patch.object(p.time, "monotonic", side_effect=[0, 21, 22]):
            result = p.request(con, "mcp", "coverage", {}, timeout=20)
            self.assertEqual(result["kind"], "request_deadline_exceeded")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM perception_cache").fetchone()[0], 0)

    def test_truncated_last_feed_page_stays_partial(self):
        result = {"ok": True, "rows": [], "pagination": {"hasNextPage": False, "truncated": True}}
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(config, "PERCEPTION_SURVEY_DAILY", 0), patch.object(p, "request", return_value=result):
            batch = p.collect(con)
            sources.acknowledge(con, batch)
            self.assertTrue(p.state(con, "feed")["partial"])
    def test_live_specialist_formats(self):
        samples = json.loads((Path(__file__).parent / "fixtures/perception-specialists-2026-09-09.json").read_text())
        for sample, operation, count in zip(samples, ["regulatory", "entity"], [1, 2]):
            parsed = p.parse_mcp(sample["body"], operation, sample["arguments"], NOW)
            self.assertEqual(len(parsed["rows"]), count)
            self.assertTrue(all(not row["text"] for row in parsed["rows"]))
            self.assertNotIn("Suggested next", p.encoded(parsed))

    def test_survey_attempt_is_once_per_slot_even_after_failure(self):
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(config, "PERCEPTION_SURVEY_DAILY", 8), patch.object(config, "PERCEPTION_TOOLS_ENABLED", True), \
                patch.object(p.time, "time", return_value=NOW), \
                patch.object(p, "request", return_value={"ok": False, "kind": "offline"}) as req:
            p.set_state(con, "feed", {"next_poll_at": NOW+4000})
            con.commit()
            p.collect(con)
            self.assertEqual(req.call_count, 1)
            p.collect(con)
            self.assertEqual(req.call_count, 1)
            self.assertEqual(p.state(con, "survey_attempt")["slot"], int(NOW//10800))

    def test_survey_pending_replays_without_network(self):
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(p.time, "time", return_value=NOW), patch.object(p, "request") as req:
            p.set_state(con, "feed", {"next_poll_at": NOW+4000})
            p.set_state(con, "survey_pending", {"ok": True, "rows": [article()], "retrieved_at": NOW-600})
            con.commit()
            batch = p.collect(con)
            self.assertEqual(len(batch), 1)
            req.assert_not_called()
            self.assertTrue(p.state(con, "survey_pending"))
            store.upsert_new_items(con, batch)
            sources.acknowledge(con, batch)
            self.assertEqual(p.state(con, "survey_pending"), {})

    def test_routing_split_is_soft_and_specialists_keep_remaining_allowance(self):
        with temporary_store() as con, patch.object(p.time, "time", return_value=NOW):
            for n in range(20):
                con.execute("INSERT INTO perception_requests VALUES(?,'mcp','coverage','writer',?,NULL,'ok',200,5,'{}')", (str(n), NOW))
            con.commit()
            args = {"q": "Lummis", "startDate": "2026-09-08", "endDate": "2026-09-09", "limit": 10}
            with patch.object(p, "request", return_value={"ok": True, "rows": []}) as req:
                p.coverage(con, "coverage", args, timeout=20)
                self.assertEqual(req.call_args.args[1], "rest")
                p.coverage(con, "coverage", {**args, "q": "Lummis CLARITY"}, timeout=20)
                self.assertEqual(req.call_args.args[1], "mcp")
                p.coverage(con, "entity", {**args, "company": "Block"}, timeout=20)
                self.assertEqual(req.call_args.args[1], "mcp")
            self.assertEqual(p.availability(con, "mcp", "writer", NOW), "")
            for n in range(4):
                con.execute("INSERT INTO perception_requests VALUES(?,'rest','feed','writer',?,NULL,'ok',200,5,'{}')", ("rest"+str(n), NOW))
            con.commit()
            self.assertEqual(p.availability(con, "mcp", "writer", NOW), "local_new_work_limit")
            self.assertEqual(p.availability(con, "rest", "intake", NOW), "")
    def test_live_search_and_article_sse_contracts(self):
        a, b = FIXTURE["samples"]
        search = p.parse_mcp(a["body"], "coverage", a["arguments"], NOW)
        self.assertEqual(len(search["rows"]), 3)
        self.assertTrue(search["partial"])
        self.assertEqual(search["total"], 5)
        self.assertEqual(search["rows"][0]["published_at"], "2026-09-08")
        self.assertEqual(search["rows"][0]["text"], "")
        body = p.parse_mcp(b["body"], "article", b["arguments"], NOW)["article"]
        self.assertEqual(body["url"], URL)
        self.assertEqual(body["completeness"], "unknown")
        self.assertEqual(body["byline"], "Mathew Di Salvo")
        self.assertNotIn("Try next", body["text"])
        self.assertNotIn("Prompt Library", body["text"])

    def test_error_or_unknown_format_is_not_empty(self):
        for raw in ([], {"error": {"code": -1}}, {"result": {"isError": True}},
                    {"result": {"content": ["bad"]}}, {"result": {"content": None}},
                    {"result": {"content": [{"type": "text", "text": "New format"}]}}):
            with self.assertRaises(ValueError):
                p.parse_mcp(json.dumps(raw), "coverage", {}, NOW)
        raw = {"result": {"content": [{"type": "text", "text": "No matching articles"}]}}
        self.assertEqual(p.parse_mcp(json.dumps(raw), "coverage", {}, NOW)["rows"], [])

    def test_json_and_wrong_article_identity(self):
        raw = p.rpc_payload(FIXTURE["samples"][1]["body"])
        wrapped = json.dumps({"result": raw})
        self.assertEqual(p.parse_mcp(wrapped, "article", {"url": URL}, NOW)["article"]["url"], URL)
        with self.assertRaises(ValueError):
            p.parse_mcp(wrapped, "article", {"url": "https://example.com/other"}, NOW)

    def test_dates_never_invent_midnight_or_wrong_year(self):
        self.assertEqual(p.publication("Sep 8"), ("", "unknown"))
        self.assertEqual(p.publication("Sep 8", {"startDate": "2025-01-01", "endDate": "2026-12-31"}), ("", "unknown"))
        self.assertEqual(p.publication("Sep 8, 2026"), ("2026-09-08", "day"))
        self.assertEqual(p.publication("2026-09-08T20:00:00Z")[1], "second")
        self.assertIsNone(p.article_row({"Title": "Unsafe", "URL": "http://127.0.0.1/x"}, NOW))

    def test_source_version_does_not_renew_or_commit(self):
        with temporary_store() as con:
            first = p.save_article(con, article(), "a")
            self.assertTrue(con.in_transaction)
            con.commit()
            second = p.save_article(con, article(NOW+600), "b")
            self.assertEqual(first, second)
            row = con.execute("SELECT * FROM writer_artifacts WHERE artifact_id=?", (first,)).fetchone()
            self.assertEqual(row["created_at"], NOW)
            self.assertEqual(row["expires_at"], NOW + writer_memory.TTL)
            self.assertEqual(json.loads(row["candidate_ids_json"]), ["a", "b"])
            third = p.save_article(con, article(NOW+700, "A materially different finding."))
            self.assertNotEqual(first, third)
            con.commit()
            self.assertEqual(p.retained_article(con, URL, NOW+800)["artifact_id"], third)

    def test_duplicate_enrichment_preserves_state_and_first_seen(self):
        with temporary_store() as con:
            raw = p.as_items([article()])
            fresh = store.upsert_new_items(con, raw)
            item_id = fresh[0]["url_hash"]
            con.execute("UPDATE items SET status='skipped',story_key='approved-existing-key',note='owner note' WHERE url_hash=?", (item_id,))
            con.commit()
            before = dict(con.execute("SELECT * FROM items WHERE url_hash=?", (item_id,)).fetchone())
            self.assertEqual(store.upsert_new_items(con, p.as_items([article(NOW+600, "New body")])), [])
            after = dict(con.execute("SELECT * FROM items WHERE url_hash=?", (item_id,)).fetchone())
            self.assertEqual(before, after)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM writer_artifacts").fetchone()[0], 2)

    def test_partial_storage_failure_replays_without_acknowledging(self):
        with temporary_store() as con:
            batch = sources.CollectedBatch()
            batch.extend(p.as_items([article()]))
            batch.checkpoints["perception:feed"] = p.encoded({"next_page": 2})
            with patch.object(p, "save_article", side_effect=RuntimeError("disk full")):
                with self.assertRaises(RuntimeError):
                    store.upsert_new_items(con, batch)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM items").fetchone()[0], 0)
            self.assertEqual(p.state(con, "feed"), {})
            store.upsert_new_items(con, batch)
            sources.acknowledge(con, batch)
            self.assertEqual(p.state(con, "feed")["next_page"], 2)

    def test_cache_is_transport_and_filter_specific_without_new_request(self):
        response = httpx.Response(200, text=FIXTURE["samples"][0]["body"])
        client = transport(response)
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(p.httpx, "Client", return_value=client), patch.object(p.time, "time", return_value=NOW):
            args = FIXTURE["samples"][0]["arguments"]
            first = p.request(con, "mcp", "coverage", args)
            second = p.request(con, "mcp", "coverage", args)
            self.assertTrue(first["ok"])
            self.assertTrue(second["cached"])
            self.assertEqual(client.stream.call_count, 1)
            self.assertEqual(sum(r["attempts"] for r in p.daily_counts(con, NOW)), 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM perception_cache").fetchone()[0], 1)
            with patch.object(p.time, "time", return_value=NOW+301):
                p.request(con, "mcp", "coverage", args)
            self.assertEqual(client.stream.call_count, 2)
            p.request(con, "mcp", "coverage", {**args, "outlet": "X"})
            self.assertEqual(client.stream.call_count, 3)

    def test_failure_reservation_survives_and_is_not_cached(self):
        client = transport(httpx.Response(429, json={"error": "rate limited"}, headers={"ratelimit-policy": "60;w=60"}))
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(p.httpx, "Client", return_value=client), patch.object(p.time, "time", return_value=NOW):
            result = p.request(con, "mcp", "coverage", {})
            self.assertFalse(result["ok"])
            self.assertEqual(con.execute("SELECT COUNT(*) FROM perception_cache").fetchone()[0], 0)
            self.assertTrue(p.availability(con, "rest", "intake", NOW))
            p.request(con, "mcp", "coverage", {})
            self.assertEqual(client.stream.call_count, 1)
            self.assertEqual(sum(r["attempts"] for r in p.daily_counts(con, NOW)), 1)
            self.assertEqual(p.state(con, "rest_daily"), {})  # minute quota is not daily capacity

    def test_local_new_work_cap_keeps_intake_available(self):
        with temporary_store() as con, patch.object(config, "PERCEPTION_NEW_WORK_DAILY", 0):
            self.assertEqual(p.availability(con, "mcp", "writer", NOW), "local_new_work_limit")
            self.assertEqual(p.availability(con, "rest", "intake", NOW), "")

    def test_collection_ack_and_backlog_newest_alternate(self):
        def response(*_args, **kwargs):
            return {"ok": True, "rows": [article()], "pagination": {"hasNextPage": True, "totalPages": 4}}
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(config, "PERCEPTION_SURVEY_DAILY", 0), patch.object(p, "request", side_effect=response) as req, \
                patch.object(p.time, "time", return_value=NOW):
            batch = p.collect(con)
            self.assertEqual(p.state(con, "feed"), {})
            store.upsert_new_items(con, batch)
            sources.acknowledge(con, batch)
            self.assertEqual(p.state(con, "feed")["next_page"], 2)
            self.assertEqual(len(p.collect(con)), 0)
            with patch.object(p.time, "time", return_value=NOW+901):
                batch = p.collect(con)
                self.assertEqual(req.call_args.args[3]["page"], 2)
                store.upsert_new_items(con, batch)
                sources.acknowledge(con, batch)
            with patch.object(p.time, "time", return_value=NOW+1802):
                p.collect(con)
                self.assertEqual(req.call_args.args[3]["page"], 1)

    def test_writer_retained_article_budget_memory_and_editor_identity(self):
        with temporary_store() as con, patch.object(config, "PERCEPTION_TOOLS_ENABLED", True):
            now = time.time()-100
            with con:
                p.save_article(con, article(now))
            desk = session(con)
            before = desk.context_retrieval_calls
            with patch.object(p, "request") as network:
                raw = desk._dispatch(SimpleNamespace(id="article1", name="perception_article", input={"url": URL}))
            result = json.loads(raw["content"])
            self.assertTrue(result["ok"])
            self.assertTrue(result["capture_reused"])
            self.assertEqual(result["inspected_at"], now)
            self.assertEqual(result["retrieval_kind"], "provider_captured_text")
            self.assertFalse(result["independent_report"])
            self.assertEqual(desk.context_retrieval_calls, before)
            self.assertEqual(desk.tool_calls, 1)
            self.assertEqual(desk.fetch_count, 1)
            network.assert_not_called()
            restored = desk._restore_receipt(result)
            self.assertEqual(restored["retrieval_kind"], "provider_captured_text")
            self.assertEqual(restored["final_url"], URL)
            self.assertEqual(restored["inspected_at"], now)
            self.assertNotIn(p.source_policy.normalize_url(URL), desk.fetch_by_url)
            receipt = editor.receipt_card(desk.fetches[result["fetch_id"]])
            payload, deferred = editor._batch_editor_payload([{
                "story_id": "story1", "post": "Lummis discussed the CLARITY Act.",
                "selected_receipt": receipt, "inspected_evidence": [receipt]}], [])
            self.assertEqual(deferred, [])
            actual = payload["evidence_catalog"][0]
            self.assertEqual(actual["url"], URL)
            self.assertEqual(actual["retrieval_kind"], "provider_captured_text")
            self.assertEqual(actual["evidence_capability"], "provider_captured_text")
            self.assertEqual(actual["inspected_at"], now)
            self.assertIn("completeness unknown", actual["limitations"])
            self.assertTrue(con.execute("SELECT 1 FROM writer_artifacts WHERE run_id=? AND kind='receipt'", (desk.run_id,)).fetchone())

    def test_optional_errors_and_finalization_do_not_end_writer(self):
        with temporary_store() as con, patch.object(config, "PERCEPTION_TOOLS_ENABLED", True):
            desk = session(con)
            bad = desk._dispatch(SimpleNamespace(id="bad", name="perception_coverage", input={"query": "Bitcoin", "start_date": "invalid"}))
            self.assertFalse(json.loads(bad["content"])["ok"])
            with patch.object(desk, "_research_seconds_left", return_value=1), patch.object(p, "request") as network:
                result = desk._dispatch(SimpleNamespace(id="late", name="perception_article", input={"url": URL}))
            self.assertFalse(json.loads(result["content"])["ok"])
            network.assert_not_called()

    def test_unicode_bodies_fit_artifact_bound(self):
        with temporary_store() as con:
            value = article(text="漢字" * 30000)
            self.assertTrue(value["text_truncated"])
            self.assertTrue(p.save_article(con, value))

    def test_desk_state_does_not_claim_shared_remaining(self):
        with temporary_store() as con:
            result = p.summary(con, NOW)
            self.assertIn("unknown", result["quota_scope"])
            self.assertEqual(result["today"], [])


if __name__ == "__main__":
    unittest.main()
