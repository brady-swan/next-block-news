import copy
import hashlib
import json
import time
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from nbn import brain, config, desk_prep, editor, main, models, newsroom, reporter, store, writer_memory
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate, inspected, materialization_fixture
from tests.test_reporter_writer import session


class ReportingFollowthroughTests(unittest.TestCase):
    def test_native_progress_is_current_work_not_citation_novelty_or_billing(self):
        bodies = [
            ({"output": [{"type": "web_search_call", "status": "completed"}],
              "usage": {"server_side_tool_usage_details": {"web_search_calls": 0}}}, True),
            ({"output": [{"type": "custom_tool_call", "name": "x_thread_fetch"}]}, True),
            ({"usage": {"server_side_tool_usage_details": {"x_search_calls": 1}}}, True),
            ({"citations": ["https://example.com/old"]}, False),
            ({}, False),
        ]
        for body, expected in bodies:
            with self.subTest(body=body):
                response = models.normalize({"status": "completed", **body}, provider="xai", effort="medium")
                self.assertEqual(reporter.native_activity(response), expected)

    def test_plain_completion_forces_next_dossier_but_native_work_continues(self):
        for native in (False, True):
            with self.subTest(native=native), temporary_store() as con:
                desk = session(con)
                desk.native_urls.add("https://example.com/prior")
                raw = {"status": "completed", "output": [
                    {"type": "reasoning", "encrypted_content": "opaque-test-state"},
                    {"type": "message", "content": [{"type": "output_text", "text": "Ready."}]}]}
                if native:
                    raw["output"].insert(0, {"type": "web_search_call", "status": "completed"})
                calls = []
                def respond(**kwargs):
                    calls.append(kwargs)
                    desk.successful_newsdesk_calls += 1
                    if len(calls) == 1:
                        return models.normalize(copy.deepcopy(raw), provider="xai", effort="medium")
                    return models.normalize({"status": "completed", "output": [{"type": "function_call",
                        "call_id": "final", "name": "submit_editorial_dossier",
                        "arguments": json.dumps({"decisions": [], "stories": [], "desk_feedback": None})}]},
                        provider="xai", effort="medium")
                with patch.object(desk, "prepare_desk"), patch.object(desk, "_initial_packet", return_value={"run_brief": {}}), \
                        patch.object(desk, "_call", side_effect=respond), patch("nbn.store.validate_newsroom_run"):
                    outcome = desk.conduct_v2()
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[1]["tool_choice"], None if native else
                                 {"type": "tool", "name": "submit_editorial_dossier"})
                self.assertEqual(outcome.verdicts[0]["action"], "hold")
                self.assertIn("opaque-test-state", json.dumps(models.response_input(desk.messages)))
                self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='writer_finalization'").fetchone()[0], int(not native))

    def test_early_finalization_keeps_one_dossier_only_receipt_repair(self):
        with temporary_store() as con:
            desk = session(con)
            desk.fetches["valid"] = inspected("valid", candidate()["url"], "SEC", "Bitcoin policy changed.")
            calls = []
            def respond(**kwargs):
                calls.append(kwargs)
                desk.successful_newsdesk_calls += 1
                if len(calls) == 1:
                    body = {"type": "message", "content": [{"type": "output_text", "text": "Done."}]}
                else:
                    fid = "bad-pointer" if len(calls) == 2 else "valid"
                    value = {"stories": [{"story_id": "s", "story_key": "policy", "member_candidate_ids": [candidate()["url_hash"]],
                        "post": "Bitcoin policy changed.", "selected_fetch_id": fid, "evidence_fetch_ids": [fid]}],
                        "decisions": [{"candidate_id": candidate()["url_hash"], "story_id": "s", "disposition": "publish"}]}
                    body = {"type": "function_call", "call_id": f"call-{len(calls)}",
                            "name": "submit_editorial_dossier", "arguments": json.dumps(value)}
                return models.normalize({"status": "completed", "output": [body]}, provider="xai", effort="medium")
            with patch.object(desk, "prepare_desk"), patch.object(desk, "_initial_packet", return_value={"run_brief": {}}), \
                    patch.object(desk, "_call", side_effect=respond), patch("nbn.store.validate_newsroom_run"):
                outcome = desk.conduct_v2()
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(call["tools"] == [newsroom.V2_DOSSIER_TOOL] for call in calls[1:]))
            self.assertEqual(outcome.verdicts[0]["action"], "draft")
            self.assertIn("Research is closed", json.dumps(desk.messages))
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='receipt_protocol_repair'").fetchone()[0], 1)

    def test_reporting_note_is_optional_bounded_context_not_evidence(self):
        schema = newsroom.V2_DOSSIER_TOOL["input_schema"]["properties"]["stories"]["items"]
        self.assertEqual(schema["properties"]["reporting_note"]["type"], ["string", "null"])
        for note in (None, {"bad": "value"}, "Origin checked. " * 200):
            with self.subTest(note=type(note)), temporary_store() as con:
                desk = session(con)
                row = candidate()
                rec = inspected("one", row["url"], "SEC", "Bitcoin policy changed.")
                desk.fetches["one"] = rec
                story = {"story_id": "s", "story_key": "policy", "member_candidate_ids": [row["url_hash"]],
                    "post": "Bitcoin policy changed.", "selected_fetch_id": "one", "evidence_fetch_ids": ["one"]}
                if note is not None:
                    story["reporting_note"] = note
                with patch("nbn.store.validate_newsroom_run"):
                    outcome = desk._validate_and_convert_v2({"stories": [story], "decisions": [
                        {"candidate_id": row["url_hash"], "story_id": "s", "disposition": "publish"}]})
                draft = outcome.drafts[row["url_hash"]]
                expected = note.strip()[:800].rstrip() if isinstance(note, str) else None
                self.assertEqual(draft["reporting_note"], expected)
                self.assertEqual(store._bounded_memory_attempt(outcome.story_attempts[0])["reporting_note"], expected)
                self.assertNotIn("Origin checked", draft["_source_text"])
                self.assertEqual(draft["evidence_fetch_ids"], ["one"])
                encoded = json.dumps(outcome.dossier, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                self.assertEqual(outcome.digest, hashlib.sha256(encoded.encode()).hexdigest())

    def test_editor_receipt_identity_preserves_url_author_date_and_body(self):
        first = {"fetch_id": "a", "url": "https://example.com/original", "text": "Identical report.",
                 "byline": "One", "retrieval_kind": "direct_fetch", "published_at": "yesterday",
                 "limitations": "", "content_fingerprint": "same"}
        variants = [first, {**first, "fetch_id": "b", "url": "https://other.example/copy"},
                    {**first, "fetch_id": "c", "byline": "Other"},
                    {**first, "fetch_id": "d", "published_at": "today"},
                    {**first, "fetch_id": "e", "limitations": "Paraphrase only"},
                    {**first, "fetch_id": "f", "retrieval_kind": "provider_reported_extract"},
                    {**first, "fetch_id": "g", "text": "Different actual content."}]
        candidates = [{"story_id": str(i), "post": "Report.", "reporting_note": "Check dates, not evidence.",
                       "selected_receipt": {"fetch_id": r["fetch_id"]}, "inspected_evidence": [r]}
                      for i, r in enumerate(variants)]
        candidates.append({**candidates[0], "story_id": "duplicate-capture",
                           "selected_receipt": {"fetch_id": "same-source-other-id"},
                           "inspected_evidence": [{**first, "fetch_id": "same-source-other-id"}]})
        payload, deferred = editor._batch_editor_payload(candidates, [])
        self.assertFalse(deferred)
        self.assertEqual(len(payload["evidence_catalog"]), 7)
        catalog = {r["evidence_ref"]: r for r in payload["evidence_catalog"]}
        for card, rec in zip(payload["candidates"], variants):
            actual = catalog[card["selected_evidence_ref"]]
            for key in ("url", "byline", "published_at", "limitations", "text", "retrieval_kind"):
                self.assertEqual(actual[key], rec[key])
            self.assertEqual(card["reporting_note"], "Check dates, not evidence.")

    def test_memory_catalog_keeps_event_and_confirmed_lede_not_new_draft(self):
        with temporary_store() as con:
            store.save_newsroom_story_attempt(con, "strategy-buy-august", "delivered", {"headlines": ["@Excellion"], "members": [], "evidence": []})
            con.execute("INSERT INTO posts(story_key,created,mode,publisher_status,confirmed_at,body) VALUES ('strategy-buy-august',1,'IMMEDIATE','published',1,'Prior purchase published')")
            con.execute("INSERT INTO posts(story_key,created,mode,publisher_status,body) VALUES ('strategy-buy-august',2,'DRAFT','draft','Wrong fresh purchase claim')")
            row = writer_memory.catalog(con)["rows"][0]
            self.assertEqual(row["event_key"], "strategy-buy-august")
            self.assertEqual(row["title"], "strategy-buy-august")
            self.assertEqual(row["confirmed_output"], {"post_lead": "Prior purchase published", "confirmed_at": 1})
            self.assertNotIn("Wrong fresh", json.dumps(row))

    def test_update_normalization_reaches_editor_fallback_and_final_rails(self):
        cases = [("missing", "publish", "The SEC announced a Bitcoin policy update."),
                 ("NEW: ", "revise", "NEW: The SEC announced a Bitcoin policy update."),
                 ("UPDATE: ", "drop", None), ("missing", "publish", None),
                 ("missing", "publish", ""), ("missing", "outage", None),
                 ("missing", "publish", "The SEC announced a Bitcoin policy update. https://example.com")]
        for prefix, verdict, final in cases:
            with self.subTest(prefix=prefix, verdict=verdict, final=final), temporary_store() as con, ExitStack() as stack:
                body = "The SEC announced a Bitcoin policy update."
                row, rec, draft, desk = materialization_fixture(con, "update-test", post=("" if prefix == "missing" else prefix) + body)
                draft.update(coverage_relation="material_update", reporting_note="Original checked; routine statement.")
                # A second, qualifying source must reach the real batch payload too.
                other = inspected("other", "https://www.sec.gov/other", "SEC", "No new rule enacted.")
                desk.conduct.return_value.fetches["other"] = other
                draft["evidence_fetch_ids"].append("other")
                state = store.canonical_output_state(con, "sec-bitcoin-policy")
                state.update(state="reader_visible", visible={"id": 99})
                stack.enter_context(patch.object(store, "canonical_output_state", return_value=state))
                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=desk))
                captured = []
                def review(cards, *_args, **_kwargs):
                    captured.append(editor._batch_editor_payload(cards, [])[0])
                    return {"ok": verdict != "outage", "decisions": {} if verdict == "outage" else
                            {"sec": {"verdict": verdict, "post": final, "reason": "test"}}}
                stack.enter_context(patch.object(editor, "review_newsroom_batch", side_effect=review))
                publish = stack.enter_context(patch.object(main.publisher, "publish", return_value=("DRAFT", "test-draft")))
                stack.enter_context(patch.object(main.publisher, "backend_name", return_value="typefully"))
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
                self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
                result = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id="update-test", inventory=[row], pending=[row],
                    result={k: 0 for k in ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                    theme_snapshot=[], overrides={}, run_started=time.time())
                card = captured[0]["candidates"][0]
                self.assertEqual(card["post"], "UPDATE: " + body)
                self.assertEqual(card["reporting_note"], draft["reporting_note"])
                self.assertEqual(len(card["inspected_evidence_refs"]), 2)
                if verdict == "drop" or (verdict != "outage" and (not final or "https:" in final)):
                    publish.assert_not_called()
                else:
                    self.assertEqual(publish.call_args.args[0], "UPDATE: " + body)
                    self.assertEqual(result["drafted"], 1)

    def test_update_repair_does_not_bypass_protection_or_relabel_open_drafts(self):
        for case in ("protected", "multiple", "same_event", "no_base", "open_draft"):
            with self.subTest(case=case), temporary_store() as con, ExitStack() as stack:
                body = "The SEC announced a Bitcoin policy update."
                row, _, draft, desk = materialization_fixture(con, "guards", post=body)
                draft["coverage_relation"] = "same_event" if case in {"same_event", "open_draft"} else "material_update"
                state = store.canonical_output_state(con, "sec-bitcoin-policy")
                if case != "no_base":
                    state.update(state="reader_visible", visible={"id": 99})
                if case == "protected":
                    state["protected_mutations"] = [{}]
                elif case == "multiple":
                    state["drafts"] = [{}, {}]
                elif case == "open_draft":
                    state.update(state="open_draft", visible=None, drafts=[{"nuelink_id": "old", "body": body,
                                                                          "receipt_url": row["url"]}])
                stack.enter_context(patch.object(store, "canonical_output_state", return_value=state))
                stack.enter_context(patch.object(config, "DRAFT_REPLACEMENT_ENABLED", True))
                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=desk))
                review = stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={"ok": True,
                    "decisions": {"sec": {"verdict": "drop", "post": None, "reason": "test"}}}))
                publish = stack.enter_context(patch.object(main.publisher, "publish"))
                replace = stack.enter_context(patch.object(main.publisher, "replace_draft"))
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
                self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
                main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id="guards", inventory=[row], pending=[row],
                    result={k: 0 for k in ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                    theme_snapshot=[], overrides={}, run_started=time.time())
                publish.assert_not_called()
                replace.assert_not_called()
                if case == "open_draft":
                    self.assertEqual(review.call_args.args[0][0]["post"], body)
                else:
                    review.assert_not_called()
                self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='update_label_normalized'").fetchone()[0], 0)

    def test_advisory_prompt_changes_preserve_scope_and_evidence_boundaries(self):
        self.assertIn("not a mandatory lookup", reporter.GUIDANCE)
        self.assertIn("editor sees those receipts", reporter.GUIDANCE)
        self.assertIn("not factual evidence", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("need not set a record", newsroom.NEWSROOM_V2_SYSTEM)
        self.assertIn("routine macro ticks", desk_prep.SYSTEM)
        self.assertIn("primary-only publication requirement", reporter.GUIDANCE)
        self.assertIn("viability, timing or scope of legislation", newsroom.ORIENTATION_BRIEF)

    def test_pending_update_draft_preserves_intake_for_decision_recording(self):
        for stale in (False, True):
            with self.subTest(stale=stale), temporary_store() as con, ExitStack() as stack:
                body = "UPDATE: The SEC announced a Bitcoin policy update."
                row, _, draft, desk = materialization_fixture(con, "pending-update", post=body)
                draft["coverage_relation"] = "material_update"
                store.log_post(con, "sec-bitcoin-policy", "prior-item", "primary",
                               "Prior announcement.", "https://www.sec.gov/prior", "IMMEDIATE",
                               "prior", publisher_backend="typefully")
                base_id = con.execute("SELECT MAX(id) FROM posts").fetchone()[0]
                store.log_post(con, "sec-bitcoin-policy", "draft-item", "primary",
                               "UPDATE: Prior draft.", "https://www.sec.gov/prior-update", "DRAFT",
                               "existing", publisher_backend="typefully", coverage_relation="material_update",
                               base_post_id=base_id + 1 if stale else base_id)
                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=desk))
                review = stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                    "ok": True, "decisions": {"sec": {"verdict": "publish", "post": body, "reason": "New fact."}}}))
                publish = stack.enter_context(patch.object(main.publisher, "publish"))
                replace = stack.enter_context(patch.object(main.publisher, "replace_draft", return_value=("DRAFT", "existing")))
                stack.enter_context(patch.object(main.publisher, "backend_name", return_value="typefully"))
                stack.enter_context(patch.object(main.publisher, "intended_mode", return_value="DRAFT"))
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
                self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
                result = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id="pending-update",
                    inventory=[row], pending=[row], result={k: 0 for k in
                    ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                    theme_snapshot=[], overrides={}, run_started=time.time())
                recorded = json.loads(store.kv_get(con, "desk:last_decision_run"))
                self.assertEqual([d["url_hash"] for d in recorded["items"]], [row["url_hash"]])
                publish.assert_not_called()
                if stale:
                    review.assert_not_called()
                    replace.assert_not_called()
                else:
                    replace.assert_called_once()
                    self.assertEqual(result["drafted"], 1)
                    self.assertEqual(con.execute("SELECT body FROM posts WHERE nuelink_id='existing'").fetchone()[0], body)
                    self.assertEqual(con.execute("SELECT state FROM publisher_mutations").fetchone()[0], "confirmed")

    def test_assignment_is_included_in_packet_byte_cap(self):
        with temporary_store() as con, patch.object(config, "EDITORIAL_ENGINE", "v2"):
            desk = session(con)
            packet = desk._initial_packet()
            self.assertEqual(packet["run_brief"]["assignment"], newsroom.V2_ASSIGNMENT)
            self.assertLessEqual(newsroom._json_bytes(packet), config.COMPACT_DESK_INITIAL_BYTES)
            with patch.object(config, "COMPACT_DESK_INITIAL_BYTES", 100):
                with self.assertRaises(newsroom.NewsroomError) as exc:
                    desk._initial_packet()
                self.assertEqual(exc.exception.kind, "initial_context_overflow")


if __name__ == "__main__":
    unittest.main()
