import copy
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

from nbn import config, desk_api, models, newsroom, observations, reporter, research, source_policy, sources, store, writer_memory
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate, inspected


def session(con, **kwargs):
    with patch.object(config, "NEWSROOM_MODEL", "grok-4.3"):
        return newsroom.NewsroomSession(run_id="cycle:reporter-test", inventory=[candidate()],
            recent_clusters=[], theme_snapshot=[], handles={}, con=con, reservation="test",
            prep_mode="off", research_mode="on", compact_enabled=True, **kwargs)


def source(url="https://www.btcpolicy.org/report"):
    return {"url": url, "author": "BPI", "source_summary": "BPI published findings about Bitcoin adoption.",
            "published_at": "2026-09-06", "event_date": "2026-09-06", "limitations": "Research findings, not a causal proof."}


class ReporterWriterTests(unittest.TestCase):
    def test_unread_pdf_cannot_enter_receipts_or_reporting_memory(self):
        url = "https://example.com/circular.pdf"
        response = httpx.Response(200, content=b"%PDF-1.7\n1 0 obj\n<<>>\nendobj",
            headers={"content-type": "application/pdf"}, request=httpx.Request("GET", url))
        with temporary_store() as con:
            desk = session(con)
            with patch.object(sources, "_assert_public_http_url"), \
                    patch.object(sources.httpx, "Client") as client:
                client.return_value.__enter__.return_value.get.return_value = response
                result = desk._fetch(url, intake={"url_hash": "pdf-test", "title": "BSP proposal"})
            self.assertFalse(result["ok"])
            self.assertEqual(result["error_kind"], "unsupported_document")
            self.assertFalse(result["retry_same_call"])
            self.assertEqual(desk.fetches, {})
            self.assertEqual(desk.fetch_chars, 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM writer_artifacts WHERE kind='receipt'").fetchone()[0], 0)

    def test_native_and_custom_tools_are_combined(self):
        response = Mock(is_success=True)
        response.json.return_value = {"status": "completed", "output": [], "usage": {}}
        http = Mock()
        http.__enter__ = Mock(return_value=http)
        http.__exit__ = Mock()
        http.post.return_value = response
        with patch.dict("os.environ", {"XAI_API_KEY": "test-not-real"}), patch("nbn.models.httpx.Client", return_value=http):
            models.ResponsesClient("grok-4.3").create(model="grok-4.3", system="test", messages=[],
                max_tokens=100, native_tools=True, max_tool_calls=3, tools=[newsroom.V2_DOSSIER_TOOL])
        payload = http.post.call_args.kwargs["json"]
        self.assertEqual([t["type"] for t in payload["tools"]], ["function", "web_search", "x_search"])
        self.assertEqual(payload["max_tool_calls"], 3)

    def test_same_response_receipt_registered_and_invented_url_rejected(self):
        with temporary_store() as con:
            desk = session(con)
            url = source()["url"]
            desk.native_urls = {url}
            data = {"native_sources": [source(), source("https://invented.example/report")],
                    "stories": [{"selected_fetch_id": url, "evidence_fetch_ids": [url]}]}
            mapping = desk._register_native_sources(data)
            fid = mapping[url]
            self.assertEqual(len(mapping), 1)
            self.assertEqual(data["stories"][0]["selected_fetch_id"], fid)
            self.assertEqual(desk.fetches[fid].retrieval_kind, "provider_reported_extract")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM writer_artifacts").fetchone()[0], 1)
            self.assertIn("native_receipts", [r[0] for r in con.execute("SELECT kind FROM run_observations")])

    def test_native_x_does_not_guess_handle(self):
        with temporary_store() as con:
            desk = session(con)
            desk.native_urls = {"https://x.com/i/status/123456"}
            s = source("https://x.com/SenLummis/status/123456")
            s["author"] = "@SenLummis"
            mapping = desk._register_native_sources({"native_sources": [s]})
            record = desk.fetches[next(iter(mapping.values()))]
            self.assertEqual(record.final_url, "https://x.com/i/status/123456")
            self.assertEqual(record.byline, "")

    def test_exact_native_post_id_alias_is_not_an_invented_receipt(self):
        with temporary_store() as con:
            desk = session(con)
            desk.native_urls = {"https://x.com/i/status/123456"}
            data = {"native_sources": [source("https://x.com/SenLummis/status/123456")],
                "stories": [{"selected_fetch_id": "x-post-123456",
                    "evidence_fetch_ids": ["x-post-123456", "x-post-999999"]}]}
            mapping = desk._register_native_sources(data)
            self.assertEqual(data["stories"][0]["selected_fetch_id"], mapping["x-post-123456"])
            self.assertEqual(data["stories"][0]["evidence_fetch_ids"][1], "x-post-999999")
            self.assertEqual(reporter.SOURCE_SCHEMA["maxItems"], 8)

    def test_receipt_repair_once_preserves_mixed_stories_and_failure_fallback(self):
        for mode in ("repeat_bad", "request_failed", "exhausted"):
            with self.subTest(mode=mode), temporary_store() as con, patch.object(config, "RUN_NEWSROOM_MAX_ROUNDS", 1 if mode == "exhausted" else 6):
                desk = session(con)
                desk.inventory = [candidate("good"), candidate("bad")]
                desk.by_hash = {r["url_hash"]: r for r in desk.inventory}
                desk.fetches["fetch-good"] = inspected("fetch-good", candidate()["url"], "SEC", "Bitcoin policy changed.")
                value = {"decisions": [{"candidate_id": key, "story_id": key, "disposition": "publish"} for key in ("good", "bad")],
                    "stories": [{"story_id": key, "story_key": key, "member_candidate_ids": [key],
                        "post": "Bitcoin policy changed.", "selected_fetch_id": fid, "evidence_fetch_ids": [fid]}
                        for key, fid in (("good", "fetch-good"), ("bad", "pointer-invented"))],
                    "desk_feedback": {"what_helped": "private-feedback-marker", "what_hindered": "", "suggested_improvement": "", "references": []}}
                calls = []
                def respond(**kwargs):
                    calls.append(kwargs)
                    if mode == "request_failed" and len(calls) == 2:
                        raise TimeoutError("test repair failure")
                    desk.successful_newsdesk_calls += 1
                    return models.normalize({"status": "completed", "output": [{"type": "function_call",
                        "id": f"fc-{len(calls)}", "call_id": f"call-{len(calls)}", "name": "submit_editorial_dossier",
                        "arguments": json.dumps(value)}]}, provider="xai", effort="medium")
                with patch.object(desk, "prepare_desk"), patch.object(desk, "_initial_packet", return_value={"run_brief": {}}), \
                        patch.object(desk, "_call", side_effect=respond), patch("nbn.store.validate_newsroom_run"):
                    outcome = desk.conduct_v2()
                self.assertEqual(len(calls), 1 if mode == "exhausted" else 2)
                self.assertEqual({r["url_hash"]: r["action"] for r in outcome.verdicts}, {"good": "draft", "bad": "hold"})
                self.assertNotIn("private-feedback-marker", json.dumps(desk.messages))
                self.assertEqual(con.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 0)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM story_key_aliases").fetchone()[0], 0)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='receipt_protocol_repair'").fetchone()[0],
                                 0 if mode == "exhausted" else 1)

    def test_native_only_turn_can_continue_without_fake_tool_result(self):
        with temporary_store() as con:
            desk = session(con)
            response = models.normalize({"status": "completed", "output": [{"type": "message", "content":
                [{"type": "output_text", "text": "Found the statement."}]}]}, provider="xai", effort="medium")
            self.assertEqual(desk._append_assistant(response), [])
            self.assertIn("_responses_output", desk.messages[-1])

    def test_native_budget_is_aggregate_across_requests(self):
        with temporary_store() as con, patch.object(config, "NEWSROOM_MODEL", "grok-4.3"), patch("nbn.brain.consume_model_call"):
            desk = session(con)
            response = models.normalize({"status": "completed", "output": [], "usage": {
                "input_tokens": 10, "output_tokens": 10, "server_side_tool_usage_details": {
                    "web_search_calls": 3, "x_search_calls": 1}}}, provider="xai", effort="medium")
            desk.client.create = Mock(return_value=response)
            desk._call(max_tokens=100)
            desk._call(max_tokens=100)
            self.assertEqual(desk.native_calls, 8)
            self.assertEqual(desk.tool_calls, 8)
            self.assertEqual(desk.client.create.call_args.kwargs["max_tool_calls"], config.WRITER_NATIVE_MAX_TOOL_CALLS - 4)

    def test_feedback_is_optional_isolated_and_malformed_does_not_damage_dossier(self):
        with temporary_store() as con:
            for raw in (None, [], {"what_helped": []}, {"what_helped": "<script>test</script>",
                        "what_hindered": "", "suggested_improvement": "", "references": [1, "candidate-1"]}):
                dossier = {"stories": [], "decisions": [], "run_note": "Done", "desk_feedback": raw}
                reporter.take_feedback(con, "feedback-test", dossier, model="grok-4.3", effort="medium", prompt_version="test")
                self.assertNotIn("desk_feedback", dossier)
                self.assertEqual(dossier["run_note"], "Done")
            self.assertEqual(writer_memory.catalog(con)["total"], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM newsroom_story_memory").fetchone()[0], 0)
            record = con.execute("SELECT payload_json FROM run_observations ORDER BY id DESC LIMIT 1").fetchone()
            self.assertEqual(json.loads(record[0])["feedback"]["references"], ["candidate-1"])
            reporter.take_feedback(con, "feedback-test", {"desk_feedback": None}, model="grok-4.3", effort="medium", prompt_version="test")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE run_id='feedback-test'").fetchone()[0], 4)
            self.assertEqual(desk_api.feedback_card(None)["status"], "not_recorded")
            self.assertEqual(desk_api.feedback_card({"expired": True})["status"], "expired")

    def test_feedback_removed_from_response_history_and_validation(self):
        with temporary_store() as con:
            value = {"decisions": [], "stories": [], "desk_feedback": {"what_helped": "secret-self-report"}}
            response = SimpleNamespace(raw_output=[{"type": "function_call", "name": "submit_editorial_dossier",
                                                   "arguments": json.dumps(value)}])
            reporter.strip_feedback_history(response)
            self.assertNotIn("secret-self-report", json.dumps(response.raw_output))
            with patch("nbn.store.validate_newsroom_run"):
                outcome = session(con)._validate_and_convert_v2(value)
            self.assertNotIn("desk_feedback", outcome.dossier)

    def test_catalog_beyond_old_twelve_and_read_only_pagination(self):
        with temporary_store() as con:
            for i in range(49):
                store.save_newsroom_story_attempt(con, f"event-{i}", "research_pending",
                    {"headlines": ["Lummis statement" if i == 0 else "Another story"], "members": [f"old-{i}"], "evidence": []})
            con.execute("PRAGMA query_only=ON")
            catalog = writer_memory.catalog(con)
            self.assertEqual(catalog["total"], 49)
            self.assertEqual(catalog["next_offset"], 40)
            self.assertEqual(len(writer_memory.catalog(con, offset=40)["rows"]), 9)
            found = writer_memory.catalog(con, query="Lummis")["rows"][0]
            self.assertEqual(found["context_id"], "notebook:event-0")
            self.assertIsNotNone(writer_memory.read(con, found["context_id"]))
            con.execute("PRAGMA query_only=OFF")

    def test_skipped_original_intake_is_searchable_without_reopening(self):
        with temporary_store() as con:
            saved = store.upsert_new_items(con, [{"source": "X @SenLummis", "title": "CLARITY opportunity until 2030",
                "url": "https://x.com/SenLummis/status/123", "summary": "years of jobs investment", "published": "2026-09-06"}])[0]
            con.execute("UPDATE items SET status='skipped',note='advocacy' WHERE url_hash=?", (saved["url_hash"],))
            result = writer_memory.intake(con, "Lummis 2030")
            self.assertEqual(result["rows"][0]["status"], "skipped")
            self.assertEqual(result["rows"][0]["published_at"], "2026-09-06")
            self.assertEqual(result["hours"], 72)

    def test_receipt_survives_restart_with_historical_date_and_refresh(self):
        with temporary_store() as con:
            record = inspected("old", "https://example.com/balance", "Example", "The old balance was 4000 BTC.",
                               inspected_at=time.time() - 3 * 86400)
            aid = writer_memory.save(con, "prior-run", "old", "receipt", newsroom.NewsroomSession._fetch_payload(record, cached=False))
            other = store.connect()
            try:
                desk = session(other)
                opened = desk._read_desk_context([aid])
                fid = opened["rows"][0]["material"]["fetch_id"]
                self.assertEqual(desk.fetches[fid].inspected_at, record.inspected_at)
                fetched = {"outcome": "ok", "text": "New balance is 4100 BTC.", "final_url": record.final_url}
                with patch("nbn.sources._assert_public_http_url"), patch("nbn.sources.fetch_article", return_value=fetched) as fetch:
                    fresh = desk._fetch(record.final_url)
                fetch.assert_called_once()
                self.assertNotEqual(fresh["fetch_id"], fid)
                self.assertGreater(fresh["inspected_at"], record.inspected_at)
            finally:
                other.close()

    def test_current_output_overrides_old_delivery_and_resolved_failure(self):
        with temporary_store() as con:
            store.save_newsroom_story_attempt(con, "event", "research_pending", {"members": [], "failure": "old failure", "evidence": []})
            store.save_newsroom_story_attempt(con, "event", "editor_feedback", {"members": [], "failure": "", "evidence": []})
            con.execute("INSERT INTO posts(story_key,created,mode,publisher_status,confirmed_at,body) VALUES ('event',?,'IMMEDIATE','published',?,'Published copy')", (time.time(), time.time()))
            card = session(con).continuity_cards[0]
            self.assertIsNone(card["unresolved_gate"])
            self.assertEqual(card["state"], "delivered")
            con.execute("UPDATE posts SET publisher_status='publishing',confirmed_at=NULL")
            projection = writer_memory.publication(con, "event")
            self.assertFalse(projection["reader_covered"])
            self.assertTrue(projection["duplicate_risk"])

    def test_truncated_evidence_fingerprint_matches_retained_bytes(self):
        text = "Bitcoin policy. " * 1000
        row = store._bounded_memory_evidence({"text": text, "content_fingerprint": source_policy.content_fingerprint(text)})
        self.assertTrue(row["truncated"])
        self.assertEqual(row["content_fingerprint"], source_policy.content_fingerprint(row["text"]))

    def test_article_retains_source_anchor_and_shell_is_not_receipt(self):
        client = Mock()
        client.__enter__ = Mock(return_value=client)
        client.__exit__ = Mock()
        response = Mock(is_redirect=False, url="https://example.com/article")
        response.text = '<article><p>Senator said the bill matters.</p><a href="/statement">her statement</a></article>'
        client.get.return_value = response
        with patch("nbn.sources._assert_public_http_url"), patch("nbn.sources.httpx.Client", return_value=client):
            result = sources.fetch_article(str(response.url))
            self.assertIn({"text": "her statement", "url": "https://example.com/statement"}, result["links"])
            response.text = '<html><div>Data Loading...</div></html>'
            self.assertEqual(sources.fetch_article(str(response.url))["error_kind"], "dynamic_shell")

    def test_oversized_notebook_offers_readable_sections(self):
        with temporary_store() as con:
            desk = session(con)
            desk.context_rows["large"] = {"kind": "notebook", "text": "x" * 22000}
            result = desk._read_desk_context(["large"])
            ids = result["rows"][0]["section_ids"]
            self.assertGreater(len(ids), 1)
            next_result = desk._read_desk_context(ids[:2])
            self.assertEqual(len(next_result["rows"]), 2)
            self.assertLess(desk.context_retrieval_bytes, config.COMPACT_DESK_RETRIEVAL_TOTAL_BYTES)

    def test_eighth_native_source_is_not_silently_lost(self):
        with temporary_store() as con:
            desk = session(con)
            all_sources = [source(f"https://example.com/source-{i}") for i in range(8)]
            desk.native_urls = {s["url"] for s in all_sources}
            data = {"native_sources": all_sources, "stories": [{"selected_fetch_id": all_sources[-1]["url"],
                    "evidence_fetch_ids": [all_sources[-1]["url"]]}]}
            self.assertEqual(len(desk._register_native_sources(data)), 8)
            self.assertIn(data["stories"][0]["selected_fetch_id"], desk.fetches)

    def test_completed_native_thread_target_not_guessed_author(self):
        body = {"output": [{"type": "custom_tool_call", "name": "x_thread_fetch", "status": "completed",
                            "input": '{"post_id":"2096644344795246746"}'}]}
        self.assertEqual(research.cited_urls(body), {"https://x.com/i/status/2096644344795246746"})
        body["output"][0]["status"] = "failed"
        self.assertEqual(research.cited_urls(body), set())

    def test_new_draft_does_not_hide_old_publication_or_include_replay(self):
        with temporary_store() as con:
            con.execute("INSERT INTO posts(story_key,created,mode,publisher_status,confirmed_at,body) VALUES ('event',1,'IMMEDIATE','published',1,'Published')")
            con.execute("INSERT INTO posts(story_key,created,mode,publisher_status,body) VALUES ('event',2,'DRAFT','draft','New draft')")
            con.execute("INSERT INTO posts(story_key,created,mode,publisher_status,confirmed_at,class,body) VALUES ('event',3,'IMMEDIATE','published',3,'replay','Replay')")
            out = writer_memory.publication(con, "event")
            self.assertTrue(out["reader_covered"])
            self.assertTrue(out["duplicate_risk"])
            self.assertEqual(out["body"], "New draft")
            self.assertEqual(out["confirmed_output"]["body"], "Published")

    def test_artifact_volume_does_not_hide_notebooks(self):
        with temporary_store() as con:
            store.save_newsroom_story_attempt(con, "important", "research_pending", {"members": [], "evidence": []})
            for i in range(110):
                writer_memory.save(con, f"run-{i}", "step", "research_step", {"query": "Bitcoin"})
            rows = writer_memory.catalog(con, limit=100)["rows"]
            self.assertEqual(rows[0]["context_id"], "notebook:important")
            self.assertEqual(rows[1]["kind"], "reporting_run")
            self.assertEqual(writer_memory.catalog(con, query="Bitcoin")["total"], 110)

    def test_reserve_stops_queued_fetches_and_prefetch(self):
        with temporary_store() as con, patch("nbn.sources.fetch_article") as fetch:
            desk = session(con)
            desk.started = time.monotonic() - config.RUN_NEWSROOM_TIMEOUT_SECONDS + 44
            block = SimpleNamespace(id="fetch-last", name="fetch_source", input={"url": "https://example.com/report"})
            result = json.loads(desk._dispatch_inner(block)["content"])
            self.assertEqual(result["kind"], "finalization_reserve")
            desk.prefetch_prepared_receipts()
            fetch.assert_not_called()

    def test_native_only_work_survives_next_request_failure_and_restart(self):
        with temporary_store() as con, patch.object(config, "NEWSROOM_MODEL", "grok-4.3"), patch("nbn.brain.consume_model_call"):
            desk = session(con)
            response = models.normalize({"status": "completed", "output": [
                {"type": "reasoning", "encrypted_content": "MUST_NOT_STORE"},
                {"type": "message", "content": [{"type": "output_text", "text": "Located Lummis's original statement; check its date.",
                    "annotations": [{"type": "url_citation", "url": "https://x.com/i/status/123456"}]}]}],
                "usage": {"input_tokens": 10, "output_tokens": 10, "server_side_tool_usage_details": {"x_search_calls": 1}}},
                provider="xai", effort="medium")
            desk.client.create = Mock(side_effect=[response, RuntimeError("timeout"), RuntimeError("timeout")])
            desk._call(max_tokens=100)
            with self.assertRaises(RuntimeError):
                desk._call(max_tokens=100)
            other = store.connect()
            try:
                found = writer_memory.catalog(other, query="Lummis")["rows"][0]
                saved = writer_memory.read(other, found["context_id"])
                self.assertEqual(saved["kind"], "research_step")
                self.assertEqual(saved["material"]["kind"], "native_findings_not_evidence")
                self.assertNotIn("MUST_NOT_STORE", json.dumps(saved))
                self.assertNotIn("fetch_id", saved["material"])
            finally:
                other.close()
