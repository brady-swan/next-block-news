"""0075 regressions: actor identity, native handoff, and real-controller replacement veto."""
import copy
import json
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from nbn import brain, config, editor, lead_material, main, models, newsroom, store, writer_memory
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate, inspected, materialization_fixture
from tests.test_evidence_to_reader import answer, card
from tests.test_reporter_writer import session, source


class SourceHandoffTests(unittest.TestCase):
    def test_immediate_original_precedes_its_outbound_and_keeps_actor_identity(self):
        parent = "https://x.com/EricSirion/status/2097722603720876477"
        outbound = "https://x.com/obi/status/2097700260910952790"
        raw = {"version": lead_material.VERSION, "post": {
            "id": "2097802161984024971", "handle": "gladstein", "text": "RT @EricSirion",
            "url": "https://x.com/gladstein/status/2097802161984024971"},
            "referenced_posts": [{"relation": "retweeted", "available": True, "post": {
                "id": "2097722603720876477", "handle": "EricSirion", "url": parent,
                "text": "Fedimint specification and funded independent implementations.", "linked_urls": [outbound]}}]}
        item = {**candidate(), "source_material": json.dumps(raw)}
        ranked = newsroom.NewsroomSession._reference_urls(item)
        self.assertEqual(ranked[0][1], parent)
        self.assertIn(outbound, [u for _, u in ranked])
        compact = lead_material.compact_preview(lead_material.preview(raw))
        self.assertEqual(compact["handle"], "gladstein")
        self.assertEqual(compact["quoted_sources"][0]["handle"], "EricSirion")
        self.assertEqual(compact["quoted_sources"][0]["relation"], "retweeted")
        with temporary_store() as con, patch.object(config, "DESK_PREFETCH_MAX_URLS", 1):
            desk = session(con)
            desk.inventory = [item]
            with patch.object(desk, "_fetch", return_value={"ok": True}) as fetch:
                desk.prefetch_prepared_receipts()
            self.assertEqual(fetch.call_args.args[0], parent)

    def test_ordinary_article_priority_is_unchanged(self):
        item = {**candidate(), "discovery_context": json.dumps({"source_refs": [
            {"url": "https://www.sec.gov/original", "publisher": "SEC"}]})}
        self.assertEqual(newsroom.NewsroomSession._reference_urls(item)[0][1], "https://www.sec.gov/original")

    def test_native_completion_preserves_work_and_only_adds_inspected_evidence(self):
        with temporary_store() as con:
            desk = session(con)
            desk.fetches = {fid: inspected(fid, "https://example.com/" + fid, "Example", "Evidence")
                            for fid in ("old", "new")}
            original = {"stories": [{"story_id": "s", "story_key": "same", "post": "Original copy.",
                "member_candidate_ids": ["c"], "selected_fetch_id": "old", "evidence_fetch_ids": ["old"],
                "visual": {"asset_id": "original"}}, {"story_id": "sibling", "post": "Keep."}],
                "decisions": [{"candidate_id": "c", "disposition": "publish"}], "shift_letter": "Keep this letter"}
            revised = {"stories": [{"story_id": "s", "story_key": "wrong", "post": "Changed!",
                "selected_fetch_id": "new", "evidence_fetch_ids": ["new", "invented"],
                "reporting_note": "Actual original added."}], "shift_letter": "Changed"}
            out = desk._complete_evidence_handoff(original, revised)
            self.assertEqual(out["stories"][0]["evidence_fetch_ids"], ["old", "new"])
            self.assertEqual(out["stories"][0]["selected_fetch_id"], "new")
            for field in ("post", "story_key", "member_candidate_ids", "visual"):
                self.assertEqual(out["stories"][0][field], original["stories"][0][field])
            self.assertEqual(out["stories"][1], original["stories"][1])
            self.assertEqual(out["shift_letter"], original["shift_letter"])
            self.assertEqual(out["decisions"], original["decisions"])

    def test_native_same_response_completion_and_fallbacks_stay_bounded(self):
        for mode in ("complete", "failed", "exhausted", "unused", "no_stories", "no_native", "wrong_tool", "mixed_tools"):
            with self.subTest(mode=mode), temporary_store() as con, ExitStack() as stack:
                desk = session(con)
                desk.fetches["old"] = inspected("old", candidate()["url"], "SEC", "Bitcoin policy changed.")
                data = {"decisions": [{"candidate_id": "candidate-1", "story_id": "s", "disposition": "publish"}],
                    "stories": [{"story_id": "s", "story_key": "s", "member_candidate_ids": ["candidate-1"],
                        "post": "Bitcoin policy changed.", "selected_fetch_id": "old", "evidence_fetch_ids": ["old"]}],
                    "native_sources": [], "shift_letter": "The policy story has fresh evidence; await Editor and delivery before calling it published."}
                if mode == "no_stories":
                    data["stories"] = []
                    data["decisions"][0]["disposition"] = "drop"
                calls = []
                def respond(**kwargs):
                    calls.append(kwargs)
                    desk.successful_newsdesk_calls += 1
                    if len(calls) == 2:
                        self.assertEqual(kwargs["tool_choice"], {"type": "tool", "name": "submit_editorial_dossier"})
                        self.assertEqual([t["name"] for t in kwargs["tools"]], ["submit_editorial_dossier"])
                        if mode == "failed":
                            raise TimeoutError("offline")
                    value = copy.deepcopy(data)
                    if len(calls) == 2 and mode != "unused":
                        value["native_sources"] = [source()]
                        value["stories"][0]["evidence_fetch_ids"].append(source()["url"])
                        value["stories"][0]["post"] = "Must not change the copy."
                        value["shift_letter"] = "Must not change the saved letter."
                    body = {"status": "completed", "citations": [source()["url"]], "usage": {
                        "server_side_tool_usage_details": {"web_search_calls": int(len(calls) == 1 and mode != "no_native")}},
                        "output": [{"type": "function_call", "call_id": f"c{len(calls)}",
                            "name": "submit_editorial_dossier", "arguments": json.dumps(value)}]}
                    if mode == "wrong_tool" and len(calls) == 2:
                        body["output"][0].update(name="fetch_source", arguments=json.dumps({"url": source()["url"]}))
                    if mode == "mixed_tools" and len(calls) == 2:
                        body["output"].append({"type": "function_call", "call_id": "extra",
                            "name": "fetch_source", "arguments": json.dumps({"url": source()["url"]})})
                    desk.native_urls.update(body["citations"])
                    return models.normalize(body, provider="xai", effort="medium")
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MAX_ROUNDS", 1 if mode == "exhausted" else 6))
                stack.enter_context(patch.object(desk, "prepare_desk"))
                stack.enter_context(patch.object(desk, "_initial_packet", return_value={}))
                stack.enter_context(patch.object(desk, "_call", side_effect=respond))
                stack.enter_context(patch.object(store, "validate_newsroom_run"))
                dispatch = stack.enter_context(patch.object(desk, "_dispatch"))
                result = desk.conduct_v2()
                dispatch.assert_not_called()
                self.assertEqual(len(calls), 1 if mode in {"exhausted", "no_stories", "no_native"} else 2)
                if mode != "no_stories":
                    draft = result.drafts["candidate-1"]
                    self.assertEqual(draft["post"], "Bitcoin policy changed.")
                    self.assertEqual(len(draft["evidence_fetch_ids"]), 2 if mode == "complete" else 1)
                self.assertEqual(con.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 0)
                letters = json.dumps([tuple(r) for r in con.execute("SELECT * FROM writer_handoffs")])
                self.assertNotIn("Must not change the saved letter", letters)


class ReplacementTests(unittest.TestCase):
    def test_editor_requires_separate_replacement_decision_and_recovers_it(self):
        c = card()
        c["output_continuity"] = {"operation": "replace_draft"}
        payload, _ = editor._batch_editor_payload([c], [])
        for invalid in (None, "", "keep", [], {}):
            row = {"verdict": "revise", "post": "Keep copy.", "reader_receipt_ref": None,
                   "replacement_decision": invalid}
            errors = []
            self.assertIsNone(editor._editor_decision(row, payload, payload["candidates"][0], "initial", errors))
            self.assertEqual(errors[0]["field"], "replacement_decision")
        outputs = [answer([{"story_id": "s1", "verdict": "revise", "post": "Copy.", "reader_receipt_ref": None}]),
                   answer([{"story_id": "s1", "verdict": "revise", "post": "Copy.", "reader_receipt_ref": None,
                            "replacement_decision": "reject"}])]
        with temporary_store() as con, patch.object(brain, "_create", side_effect=outputs) as create:
            result = editor.review_newsroom_batch([c], con, run_id="replace-review")
        self.assertEqual(create.call_count, 2)
        self.assertEqual(result["decisions"]["s1"]["replacement_decision"], "reject")

    def test_controller_preserves_draft_and_identity_on_veto_or_missing_review(self):
        for case in ("reject", "missing", "outage", "capacity", "drop", "approve", "create_update", "visual_reject", "no_evidence", "exact_output", "failed_attempt"):
            with self.subTest(case=case), temporary_store() as con, ExitStack() as stack:
                row, receipt, draft, desk = materialization_fixture(con, "replacement-case")
                outcome = desk.conduct.return_value
                attempt = outcome.story_attempts[0]
                attempt["submitted_story_key"] = "distinct-new-event"
                if case == "failed_attempt":
                    real = session(con)
                    real.inventory = [row]
                    real.by_hash = {row["url_hash"]: row}
                    real.supplied_cluster_keys.add("sec-bitcoin-policy")
                    real.fetches[receipt.fetch_id] = receipt
                    outcome = real._validate_and_convert_v2({
                        "decisions": [{"candidate_id": row["url_hash"], "story_id": "sec", "disposition": "publish"}],
                        "stories": [{"story_id": "sec", "story_key": "distinct-new-event",
                            "existing_cluster_key": "sec-bitcoin-policy", "coverage_relation": "same_event",
                            "member_candidate_ids": [row["url_hash"]], "post": draft["post"],
                            "selected_fetch_id": "invented", "evidence_fetch_ids": [receipt.fetch_id, "invented"]}]}, persist=False)
                    desk.conduct.return_value = outcome
                    attempt = outcome.story_attempts[0]
                    self.assertTrue(attempt["identity_valid"])
                    self.assertEqual(attempt["failure"], "defer:uninspected_or_ineligible_receipt")
                draft["coverage_relation"] = "material_update" if case == "create_update" else "same_event"
                if case == "visual_reject":
                    draft["visual"] = {"asset_id": "never-queue", "reusable": True}
                if case == "no_evidence":
                    draft["evidence_fetch_ids"] = []
                if case == "exact_output":
                    stack.enter_context(patch.object(store, "exact_thread_output_exists", return_value=True))
                store.log_post(con, "sec-bitcoin-policy", "old-item", "primary", "Keep the accepted old story.",
                    "https://www.sec.gov/old", "IMMEDIATE" if case == "create_update" else "DRAFT",
                    "old-target", publisher_backend="typefully")
                old = dict(con.execute("SELECT * FROM posts").fetchone())
                writer_memory.save(con, "replacement-case", receipt.fetch_id, "receipt",
                    newsroom.NewsroomSession._fetch_payload(receipt, cached=False), candidate_ids=[row["url_hash"]])
                # A proposed alias must not exist before the Editor sees the candidate.
                def review(cards, *_args, **_kwargs):
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM story_key_aliases").fetchone()[0], int(case == "create_update"))
                    return {"ok": case != "outage", "payload_deferred": ["sec"] if case == "capacity" else [],
                        "decisions": {} if case in {"missing", "outage", "capacity"} else {"sec": {
                            "verdict": "drop" if case == "drop" else "revise", "post": draft["post"],
                            "reason": "Separate event, keep the existing draft." if case.endswith("reject") else "Review result.",
                            "replacement_decision": "reject" if case.endswith("reject") else case}}}
                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="test"))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=desk))
                stack.enter_context(patch.object(editor, "review_newsroom_batch", side_effect=review))
                for name, value in (("DRAFT_REPLACEMENT_ENABLED", True), ("RUN_NEWSROOM_MODE", "live")):
                    stack.enter_context(patch.object(config, name, value))
                publish = stack.enter_context(patch.object(main.publisher, "publish", return_value=("DRAFT", "new-target")))
                replace = stack.enter_context(patch.object(main.publisher, "replace_draft", return_value=("DRAFT", "old-target")))
                visual_queue = stack.enter_context(patch("nbn.publisher_visuals.queue"))
                stack.enter_context(patch.object(main.publisher, "backend_name", return_value="typefully"))
                stack.enter_context(patch.object(main.publisher, "intended_mode", return_value="DRAFT"))
                self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
                result = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id="replacement-case",
                    inventory=[row], pending=[row], result={k: 0 for k in
                    ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                    theme_snapshot=[], overrides={}, run_started=time.time())
                if case in {"approve", "create_update"}:
                    self.assertEqual(replace.call_count, int(case == "approve"))
                    self.assertEqual(publish.call_count, int(case == "create_update"))
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM story_key_aliases").fetchone()[0], 1)
                else:
                    replace.assert_not_called()
                    publish.assert_not_called()
                    visual_queue.assert_not_called()
                    self.assertEqual(dict(con.execute("SELECT * FROM posts").fetchone()), old)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM story_key_aliases").fetchone()[0], 0)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM newsroom_story_memory").fetchone()[0], 0)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM publisher_mutations").fetchone()[0], 0)
                    self.assertEqual(con.execute("SELECT COUNT(*) FROM writer_artifacts WHERE canonical_key<>''").fetchone()[0], 0)
                    item = con.execute("SELECT status,story_key FROM items WHERE url_hash=?", (row["url_hash"],)).fetchone()
                    self.assertFalse(item["story_key"])
                    self.assertEqual(item["status"], "skipped" if case in {"drop", "exact_output"} else "new")
                    failure = writer_memory.latest_identity_failure(con, [row["url_hash"]])
                    if case == "failed_attempt":
                        self.assertEqual(failure["failure"], attempt["failure"])
                    elif case not in {"drop", "no_evidence", "exact_output"}:
                        self.assertIn("replacement_identity_rejected" if case.endswith("reject") else "replacement_review_incomplete", failure["failure"])
                        self.assertEqual(result["held"], 1)


if __name__ == "__main__":
    unittest.main()
