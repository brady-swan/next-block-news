import json
import os
import time
import unittest
from dataclasses import replace
from unittest.mock import Mock, patch

from nbn import config, desk_prep, editor, models, newsroom, research, store
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate, inspected
from tests.test_desk_prep import decision


def raw_response(output=None, **kwargs):
    return {"status": "completed", "model": "grok-4.3", "output": output or [],
            "usage": {"input_tokens": 1000, "output_tokens": 200,
                      "input_tokens_details": {"cached_tokens": 400},
                      "output_tokens_details": {"reasoning_tokens": 100}}, **kwargs}


def native_response(url="https://www.sec.gov/newsroom/test", author=""):
    data = {"what_happened": "A test policy changed.", "when": "today", "conflicts": "",
            "supportable_angle": "Policy", "remaining_gap": "", "sources": [{
                "url": url, "author": author, "source_summary": "A test policy changed.",
                "published_at": "today", "event_date": "today", "limitations": ""}]}
    body = raw_response([{"type": "message", "content": [{"type": "output_text",
        "text": json.dumps(data), "annotations": [{"type": "url_citation", "url": url}]}]}])
    body["usage"]["server_side_tool_usage_details"] = {"web_search_calls": 2, "x_search_calls": 1}
    return models.normalize(body, provider="xai", effort="medium")


class ModelsTests(unittest.TestCase):
    def test_preparation_schema_matches_existing_parser_list_limits(self):
        native = desk_prep.preparation_tool("gpt-5.6-luna")
        fields = native["input_schema"]["properties"]["decisions"]["items"]["properties"]
        for key, limit in (("source_leads", 3), ("related_keys", 3),
                           ("related_storyline_keys", 2)):
            self.assertEqual(fields[key]["maxItems"], limit)
        legacy = desk_prep.preparation_tool("claude-haiku-4-5")
        self.assertNotIn("maxItems", legacy["input_schema"]["properties"]["decisions"]
                         ["items"]["properties"]["source_leads"])
        self.assertEqual(legacy, desk_prep.TOOL)

    def test_responses_newsroom_requires_a_tool_but_preserves_forced_final_tool(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"), \
                patch.object(config, "NEWSROOM_MODEL", "grok-4.3"), \
                patch.object(newsroom.brain, "consume_model_call"):
            session = newsroom.NewsroomSession(run_id="required", inventory=[],
                recent_clusters=[], theme_snapshot=[], handles={}, con=con,
                reservation="r", prep_mode="off", research_mode="off", compact_enabled=True)
            response = models.normalize(raw_response(), provider="xai", effort="medium")
            with patch.object(session.client, "create", return_value=response) as call:
                session._call(max_tokens=100)
                self.assertEqual(call.call_args.kwargs["tool_choice"], {"type":"any"})
                final = {"type":"tool", "name":"submit_editorial_dossier"}
                session._call(max_tokens=100, tool_choice=final)
                self.assertEqual(call.call_args.kwargs["tool_choice"], final)

    def test_responses_tools_and_history_preserve_complete_output(self):
        raw = [{"type": "reasoning", "id": "r1", "encrypted_content": "opaque", "summary": []},
               {"type": "function_call", "call_id": "c1", "name": "fetch_source",
                "arguments": '{"url":"https://example.com"}'}]
        history = [{"role": "assistant", "content": [], "_responses_output": raw},
                   {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "c1",
                                                   "content": '{"ok":true}'}]}]
        inputs = models.response_input(history)
        self.assertEqual(inputs[:2], raw)
        self.assertEqual(inputs[2]["call_id"], "c1")
        transport = Mock()
        transport.post.return_value.is_success = True
        transport.post.return_value.json.return_value = raw_response(raw)
        with patch.dict(os.environ, XAI_API_KEY="test"), \
                patch.object(models.httpx, "Client") as factory:
            factory.return_value.__enter__.return_value = transport
            result = models.ResponsesClient("grok-4.3").create(
                model="grok-4.3", system="test", messages=history, max_tokens=100,
                tools=[newsroom.V2_DOSSIER_TOOL], output_config={"effort": "medium"},
                tool_choice={"type": "tool", "name": "submit_editorial_dossier"})
        payload = transport.post.call_args.kwargs["json"]
        self.assertEqual(payload["reasoning"], {"effort": "medium"})
        self.assertEqual(payload["tool_choice"], {"type": "function", "name": "submit_editorial_dossier"})
        self.assertFalse(payload["store"])
        self.assertEqual(result.content[0].id, "c1")
        self.assertEqual(result.stop_reason, "tool_use")

    def test_incomplete_or_invalid_calls_never_survive_as_decisions(self):
        valid = {"type": "function_call", "call_id": "1", "name": "submit", "arguments": '{}'}
        for body in (raw_response([valid], status="incomplete"),
                     raw_response([{**valid, "arguments": "broken"}]),
                     raw_response([valid], error={"code": "error"})):
            result = models.normalize(body, provider="xai", effort="medium")
            self.assertEqual(result.content, [])
            self.assertIn(result.stop_reason, {"invalid_response", "max_tokens"})

    def test_usage_counts_cached_once_and_provider_total_includes_tools(self):
        with temporary_store() as con:
            response = models.normalize(raw_response(), provider="openai", effort="low")
            store.record_model_usage(con, run_id="r", seat="desk_prep", model="gpt-5.6-luna",
                                     round_number=1, response=response)
            row = con.execute("SELECT * FROM model_usage").fetchone()
            self.assertAlmostEqual(row["estimated_cost_usd"], (600*.2 + 400*.02 + 200*1.2)/1e6)
            response.usage.cost_in_usd_ticks = 1230000000
            response.usage.native_web_calls = 5
            store.record_model_usage(con, run_id="r", seat="research_assistant", model="grok-4.3",
                                     round_number=1, response=response)
            row = con.execute("SELECT * FROM model_usage ORDER BY id DESC").fetchone()
            self.assertEqual(row["cost_source"], "provider_reported")
            self.assertAlmostEqual(row["estimated_cost_usd"], .123)
            self.assertEqual(row["reasoning_tokens"], 100)
            store.record_model_usage(con, run_id="r", seat="research_assistant", model="grok-4.3",
                                     round_number=2, outcome="error")
            self.assertEqual(store.model_usage_summary(con, 0)["unknown_cost_calls"], 1)

    def test_refusal_cannot_be_overwritten_by_a_tool_call(self):
        refusal = {"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}
        tool = {"type": "function_call", "call_id": "id", "name": "submit_editorial_dossier", "arguments": "{}"}
        for output in ([refusal, tool], [tool, refusal]):
            result = models.normalize(raw_response(output), provider="xai", effort="medium")
            self.assertEqual(result.stop_reason, "refusal")
            self.assertEqual(result.content, [])

    def test_luna_omissions_fail_open(self):
        inventory = [candidate("a"), candidate("b")]
        body = raw_response([{"type": "function_call", "name": desk_prep.TOOL["name"],
            "call_id": "prep", "arguments": json.dumps({"decisions": [decision("a")]})}])
        result = models.normalize(body, provider="openai", effort="low")
        rows = desk_prep._parse(result, inventory, run_id="r", protections={}, allowed_keys=set(),
                                allowed_storyline_keys=set())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["effective_route"], "advance")

    def test_native_sources_require_citations_and_do_not_guess_x_authors(self):
        response = native_response()
        self.assertEqual(len(research.extract_sources(response)[1]), 1)
        response.raw["output"][0]["content"][0]["annotations"] = []
        self.assertEqual(research.extract_sources(response)[1], [])
        response = native_response("https://x.com/bitcoinpolicy/status/123", "@wrong")
        self.assertEqual(research.extract_sources(response)[1], [])
        response = native_response("https://x.com/i/status/123", "@bitcoinpolicy")
        self.assertEqual(research.extract_sources(response)[1][0]["author"], "")
        self.assertEqual(research.extract_sources(native_response("https://x.com/grok/status/123"))[1], [])

    def test_native_research_creates_labeled_receipt_and_accounts_once(self):
        with temporary_store() as con, patch.object(config, "RESEARCH_MODEL", "grok-4.3"), \
                patch.object(newsroom.sources, "_assert_public_http_url"), \
                patch.object(research, "retrieve", return_value=native_response()) as retrieve, \
                patch.object(newsroom.brain, "consume_model_call"):
            session = newsroom.NewsroomSession(run_id="r", inventory=[candidate()], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="r", research_mode="on")
            with patch.object(session, "_fetch", return_value={"ok": False}):
                result = session._haiku_research({"candidate_ids": ["candidate-1"], "fetch_ids": [],
                                                   "objective": "Verify the test policy"})
            self.assertTrue(result["ok"], result)
            record = next(iter(session.fetches.values()))
            self.assertEqual(record.retrieval_kind, "provider_reported_extract")
            self.assertFalse(record.direct_primary)
            self.assertFalse(record.independent_report)
            self.assertEqual(newsroom._record_originality(record), "provider_reported_extract")
            self.assertEqual(session.haiku_tool_calls, 3)
            self.assertEqual(con.execute("SELECT count(*) FROM model_usage").fetchone()[0], 1)
            self.assertEqual(retrieve.call_args.kwargs["max_tool_calls"], 8)
            second = session._haiku_research({"candidate_ids": ["candidate-1"]})
            self.assertFalse(second["ok"])

    def test_native_provenance_survives_memory_restore_and_editor_dedup(self):
        with temporary_store() as con:
            record = replace(inspected("f", "https://www.sec.gov/newsroom/test", "SEC", "Policy."),
                             retrieval_kind="provider_reported_extract")
            receipt = {**newsroom.NewsroomSession._fetch_payload(record, cached=False),
                       "source_label": "SEC", "inspected_at": time.time()}
            direct = {**receipt, "fetch_id": "direct", "retrieval_kind": "direct_fetch"}
            store.save_newsroom_story_attempt(con, "test-policy", "research_pending", {
                "story_id": "s", "members": ["candidate-1"], "evidence": [receipt, direct], "failure": "gap"})
            with patch.object(newsroom, "_cached_url_is_public", return_value=True):
                session = newsroom.NewsroomSession(run_id="r", inventory=[candidate()], recent_clusters=[],
                    theme_snapshot=[], handles={}, con=con, reservation="r")
            self.assertEqual(len(session.fetches), 2)
            restored = next(r for r in session.fetches.values() if r.retrieval_kind == "provider_reported_extract")
            self.assertEqual(restored.evidence_capability, "provider_reported_extract")
            self.assertFalse(restored.direct_primary)
            payload, _ = editor._batch_editor_payload([{
                "story_id": "s", "post": "Policy", "inspected_evidence": [receipt, direct],
                "selected_receipt": {"fetch_id": "direct"}}], [])
            self.assertEqual(len(payload["evidence_catalog"]), 2)

    def test_successful_local_wrapper_does_not_discard_native_finding(self):
        with temporary_store() as con, patch.object(config, "RESEARCH_MODEL", "grok-4.3"), \
                patch.object(newsroom.sources, "_assert_public_http_url"), \
                patch.object(research, "retrieve", return_value=native_response()), \
                patch.object(newsroom.brain, "consume_model_call"), \
                patch.object(newsroom.sources, "fetch_article", return_value={
                    "outcome": "ok", "text": "Data Loading…"}):
            session = newsroom.NewsroomSession(run_id="r", inventory=[candidate()], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="r", research_mode="on")
            result = session._native_research({"candidate_ids": ["candidate-1"], "fetch_ids": [],
                                              "objective": "Verify"})
            self.assertTrue(result["ok"], result)
            kinds = {r["retrieval_kind"] for r in result["inspected_evidence"]}
            self.assertEqual(kinds, {"direct_fetch", "provider_reported_extract"})
            self.assertTrue(any("A test policy changed." in r["text"] for r in result["inspected_evidence"]))

    def test_editor_parse_failure_is_not_a_second_billable_call(self):
        with temporary_store() as con, patch("nbn.brain._create", return_value=models.normalize(
                raw_response([{"type": "message", "content": [{"type": "output_text", "text": "bad"}]}]),
                provider="xai", effort="medium")):
            result = editor.review_newsroom_batch([{"story_id": "s", "post": "Policy",
                "inspected_evidence": [], "selected_receipt": {}}], con, run_id="r")
            self.assertFalse(result["ok"])
            self.assertEqual(con.execute("SELECT count(*) FROM model_usage").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
