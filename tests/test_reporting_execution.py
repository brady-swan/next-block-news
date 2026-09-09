"""Plan 0068: repaired handoffs, not lower editorial standards or bigger budgets."""
import copy
import json
import re
import unittest
import time
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nbn import brain, config, editor, main, models, newsroom, observations, publisher, source_policy, store, visual_tools, visual_render, writer_memory
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate, inspected, materialization_fixture
from tests.test_reporter_writer import session


def story(sid, cid, **changes):
    return {"story_id": sid, "story_key": sid, "member_candidate_ids": [cid],
        "coverage_relation": "distinct", "existing_cluster_key": None,
        "post": "Bitcoin policy changed.", "selected_fetch_id": "fetch-good",
        "evidence_fetch_ids": ["fetch-good"], **changes}


def response(value=None, *, text=None, stop="end_turn"):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text if text is not None else json.dumps(value))],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50), stop_reason=stop, stop_details=None)


class ReportingExecutionTests(unittest.TestCase):
    def test_identity_preview_is_pure_and_names_the_wrong_namespace(self):
        with temporary_store() as con:
            desk = session(con)
            desk.fetches["fetch-good"] = inspected("fetch-good", candidate()["url"], "SEC", "Bitcoin policy changed.")
            dossier = {"stories": [story("clarity-warning", "candidate-1",
                existing_cluster_key="clarity-act-market-structure-legislation", coverage_relation="material_update")],
                "decisions": [{"candidate_id": "candidate-1", "story_id": "clarity-warning", "disposition": "publish"}]}
            before = con.total_changes
            with patch.object(store, "validate_newsroom_run") as persist:
                out = desk._validate_and_convert_v2(dossier, persist=False)
            persist.assert_not_called()
            self.assertEqual(con.total_changes, before)
            self.assertFalse(out.story_attempts)
            self.assertFalse(out.drafts)
            error = desk._identity_repairs(dossier)[0]
            self.assertEqual(error["field"], "existing_cluster_key")
            self.assertEqual(error["current_output_state"], "no_output")
            self.assertNotIn("clarity-act-market-structure-legislation", error["allowed_exact_event_keys"])

    def test_identity_and_receipt_share_one_repair_and_preserve_siblings(self):
        for exhaust, fail in ((False, False), (True, False), (False, True)):
            with self.subTest(exhaust=exhaust, fail=fail), temporary_store() as con, \
                    patch.object(config, "RUN_NEWSROOM_MAX_ROUNDS", 1 if exhaust else 6):
                desk = session(con)
                desk.inventory = [candidate("good"), candidate("bad")]
                desk.by_hash = {r["url_hash"]: r for r in desk.inventory}
                desk.fetches["fetch-good"] = inspected("fetch-good", candidate()["url"], "SEC", "Bitcoin policy changed.")
                first = {"stories": [story("good", "good"), story("bad", "bad", existing_cluster_key="a-storyline", coverage_relation="material_update")],
                    "decisions": [{"candidate_id": k, "story_id": k, "disposition": "publish"} for k in ("good", "bad")]}
                revised = copy.deepcopy(first)
                revised["stories"][0]["post"] = "Sibling must not be rewritten."
                revised["stories"][1].update(existing_cluster_key=None, coverage_relation="distinct",
                                             selected_fetch_id="invented", evidence_fetch_ids=["invented"])
                calls = []
                def call(**kwargs):
                    calls.append(kwargs)
                    if fail and len(calls) == 2:
                        raise TimeoutError("repair unavailable")
                    desk.successful_newsdesk_calls += 1
                    return models.normalize({"status": "completed", "output": [{"type": "function_call",
                        "call_id": str(len(calls)), "name": "submit_editorial_dossier",
                        "arguments": json.dumps(first if len(calls) == 1 else revised)}]}, provider="xai", effort="medium")
                with patch.object(desk, "prepare_desk"), patch.object(desk, "_initial_packet", return_value={}), \
                        patch.object(desk, "_call", side_effect=call), patch.object(store, "validate_newsroom_run") as persist:
                    out = desk.conduct_v2()
                self.assertEqual(len(calls), 1 if exhaust else 2)
                persist.assert_called_once()
                self.assertEqual(out.drafts["good"]["post"], "Bitcoin policy changed.")
                self.assertNotIn("bad", out.drafts)
                if not exhaust:
                    self.assertEqual([t["name"] for t in calls[1]["tools"]], ["submit_editorial_dossier"])
                self.assertEqual(con.execute("SELECT COUNT(*) FROM story_key_aliases").fetchone()[0], 0)

    def test_failed_identity_is_candidate_memory_not_a_guessed_event(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [candidate()])[0]
            desk = session(con)
            desk.inventory = [row]; desk.by_hash = {row["url_hash"]: row}
            value = {"stories": [story("bit2me", row["url_hash"], existing_cluster_key="made-up", coverage_relation="same_event")],
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "bit2me", "disposition": "publish"}]}
            with patch.object(store, "validate_newsroom_run"):
                out = desk._validate_and_convert_v2(value)
            store.defer_item(con, row["url_hash"], out.verdicts[0]["reason"])
            remembered = writer_memory.latest_identity_failure(con, [row["url_hash"]])
            self.assertEqual(remembered["field"], "existing_cluster_key")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM newsroom_story_memory").fetchone()[0], 0)
            store.set_status(con, row["url_hash"], "skipped", "", "editorial drop")
            self.assertIsNone(writer_memory.latest_identity_failure(con, [row["url_hash"]]))

    def test_member_assignment_and_visible_base_have_different_repairs(self):
        with temporary_store() as con:
            desk = session(con)
            desk.by_hash["candidate-1"]["story_key"] = "bit2me-funding"
            err = desk._identity_repairs({"stories": [story("bit2me", "candidate-1")]})[0]
            self.assertEqual(err["failure"], "defer:incoherent_coverage_relation")
            self.assertIn("bit2me-funding", err["member_event_keys"])
            err = desk._identity_repairs({"stories": [story("bit2me", "candidate-1", coverage_relation="material_update")]})[0]
            self.assertEqual(err["failure"], "defer:material_update_has_no_visible_base")
            self.assertFalse(desk._identity_repairs({"stories": [story("bit2me", "candidate-1", coverage_relation="same_event")]}))

    def test_text_contract_reaches_actual_xai_request_without_visual_fields(self):
        prompt, schema = editor._batch_contract({"candidates": [{}]})
        self.assertNotIn("visual_verdict", prompt)
        http = Mock(); http.__enter__ = Mock(return_value=http); http.__exit__ = Mock()
        http.post.return_value = Mock(is_success=True)
        http.post.return_value.json.return_value = {"status": "completed", "output": [], "usage": {}}
        with patch.dict("os.environ", {"XAI_API_KEY": "test"}), patch.object(models.httpx, "Client", return_value=http):
            models.ResponsesClient("grok-4.5").create(model="grok-4.5", system=prompt, messages=[], max_tokens=100, schema=schema)
        actual = http.post.call_args.kwargs["json"]["text"]["format"]
        self.assertTrue(actual["strict"])
        props = actual["schema"]["properties"]["decisions"]["items"]["properties"]
        self.assertNotIn("visual_verdict", props)
        self.assertIn("reader_receipt_ref", props)
        # Mixed batch versus a recovery containing only text members.
        for cards, required in (([{"visual": {"asset_id": "v"}}, {}], True), ([{}], False)):
            p, s = editor._batch_contract({"candidates": cards})
            with patch.dict("os.environ", {"XAI_API_KEY": "test"}), patch.object(models.httpx, "Client", return_value=http):
                models.ResponsesClient("grok-4.5").create(model="grok-4.5", system=p, messages=[], max_tokens=100, schema=s)
            item = http.post.call_args.kwargs["json"]["text"]["format"]["schema"]["properties"]["decisions"]["items"]
            for key in ("visual_verdict", "visual_asset_id", "visual_content_hash", "text_fallback"):
                self.assertEqual(key in item["properties"], required)
                self.assertEqual(key in item["required"], required)

    def test_malformed_received_editor_response_recovers_but_outage_and_refusal_do_not(self):
        card = {"story_id": "treasury", "post": "A dated schedule.", "inspected_evidence": [], "selected_receipt": {}}
        for first, expected in ((response(text="Drop; old schedule."), 2), (RuntimeError("offline"), 1), (response(text="", stop="refusal"), 1)):
            with self.subTest(first=first), temporary_store() as con, patch("nbn.brain._create", side_effect=[first, response({"decisions": [
                    {"story_id": "treasury", "verdict": "drop", "post": None, "reason": "Old disclosure."}]})]) as create:
                result = editor.review_newsroom_batch([card], con, run_id="test")
                self.assertEqual(create.call_count, expected)
                if expected == 2:
                    self.assertEqual(result["decisions"]["treasury"]["verdict"], "drop")
                else:
                    self.assertFalse(result["ok"])

    def test_reader_source_can_be_own_evidence_or_explicit_appendix_only(self):
        records = [editor.receipt_card(inspected(fid, url, src, "Bitcoin policy changed.")) for fid, url, src in (
            ("tip", "https://x.com/Barchart/status/123", "Barchart"),
            ("official", "https://home.treasury.gov/statement", "Treasury"))]
        payload, _ = editor._batch_editor_payload([{"story_id": "s", "post": "Policy changed.",
            "selected_receipt": {"fetch_id": "tip"}, "inspected_evidence": records[:1]}], [], research=records[1:])
        card = payload["candidates"][0]
        ref = payload["unassigned_run_research"]["receipts"][0]["evidence_ref"]
        row = {"verdict": "publish", "post": "Policy changed.", "reason": "Good", "reader_receipt_ref": ref}
        self.assertIsNone(editor._editor_decision(row, payload, card, "initial"))
        row["additional_evidence_refs"] = [ref]
        result = editor._editor_decision(row, payload, card, "initial")
        self.assertEqual(result["reader_receipt"]["fetch_id"], "official")
        row["additional_evidence_refs"] = ["visual_verdict", "none", "visual_asset_id", "null"]
        self.assertIsNone(editor._editor_decision(row, payload, card, "initial"))
        row.update(additional_evidence_refs=[], reader_receipt_ref="https://invented.example")
        self.assertIsNone(editor._editor_decision(row, payload, card, "initial"))
        row["reader_receipt_ref"] = card["selected_evidence_ref"]
        self.assertEqual(editor._editor_decision(row, payload, card, "initial")["reader_receipt"]["fetch_id"], "tip")

    def test_shrunk_editor_receipt_keeps_exact_fingerprint(self):
        receipts = [editor.receipt_card(inspected(str(i), f"https://www.sec.gov/{i}", "SEC", str(i) + "x"*7800)) for i in range(2)]
        with patch.object(editor, "EDITOR_PAYLOAD_MAX_BYTES", 14000):
            payload, omitted = editor._batch_editor_payload([{"story_id": "s", "post": "News.", "selected_receipt": {"fetch_id": "0"}, "inspected_evidence": receipts}], [])
        self.assertFalse(omitted)
        small = next(r for r in payload["evidence_catalog"] if r["fetch_id"] == "1")
        self.assertEqual(len(small["text"]), 2000)
        self.assertTrue(small["text_truncated"])
        self.assertEqual(small["content_fingerprint"], source_policy.content_fingerprint(small["text"]))
        self.assertNotEqual(small["original_content_fingerprint"], small["content_fingerprint"])

    def test_editor_recovery_identifies_the_actual_bad_field(self):
        with temporary_store() as con, patch("nbn.brain._create", side_effect=[response({"decisions": [
                {"story_id": "gold", "verdict": "publish", "post": "Good copy.", "additional_evidence_refs": ["visual_verdict"]}]}),
                response({"decisions": [{"story_id": "gold", "verdict": "publish", "post": "Good copy.", "reader_receipt_ref": None, "additional_evidence_refs": []}]})]) as create:
            result = editor.review_newsroom_batch([{"story_id": "gold", "post": "Good copy.", "inspected_evidence": [], "selected_receipt": {}}], con, run_id="r")
            constraint = json.loads(create.call_args_list[1].args[2])["recovery_constraint"]
            self.assertIn('"field": "additional_evidence_refs"', constraint)
            self.assertIn('"visual_verdict"', constraint)
            self.assertEqual(result["decisions"]["gold"]["origin"], "recovery")

    def test_final_receipt_delivery_and_memory_agree_without_large_materialization(self):
        with temporary_store() as con, ExitStack() as stack:
            row, _, draft, fake = materialization_fixture(con, "receipt-handoff")
            out = fake.conduct.return_value
            originals = [inspected(str(i), f"https://home.treasury.gov/results-{i}", "Treasury", "界"*7900) for i in range(7)]
            out.fetches.update({r.fetch_id: r for r in originals})
            draft["evidence_fetch_ids"] += [r.fetch_id for r in originals]
            chosen = editor.receipt_card(originals[-1])
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="test"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=fake))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={"ok": True, "decisions": {
                "sec": {"verdict": "publish", "post": draft["post"], "reason": "Use original source", "reader_receipt": chosen}}}))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            stack.enter_context(patch.object(publisher, "publish", return_value=("DRAFT", "fixture-draft")))
            self.assertTrue(store.acquire_cycle_lease(con, "owner"))
            result = main._run_editorial_v2(con, lease_owner="owner", pipeline_run_id="receipt-handoff", inventory=[row], pending=[row],
                result={k: 0 for k in ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                theme_snapshot=[], overrides={}, run_started=time.time())
            self.assertEqual(result["drafted"], 1)
            post = dict(con.execute("SELECT * FROM posts").fetchone())
            self.assertEqual(post["receipt_url"], chosen["url"])
            self.assertEqual(store.resolution_for_item(con, row["url_hash"])["selected_url"], chosen["url"])
            self.assertEqual(writer_memory.publication(con, post["story_key"])["receipt_url"], chosen["url"])
            mutation = con.execute("SELECT materialization_json FROM publisher_mutations").fetchone()[0]
            self.assertLess(len(mutation.encode()), 12000)
            self.assertNotIn("reader_evidence", mutation)
            self.assertEqual(store.accepted_reader_context(con, post["id"])["reader_receipt"]["url"], chosen["url"])
            con.execute("UPDATE publisher_mutations SET state='uncertain'"); con.commit()
            self.assertFalse(store.accepted_reader_context(con, post["id"]))

    def test_missing_reader_choice_recovery_materializes_source_or_preserves_human_fallback(self):
        for recover in (True, False):
            with self.subTest(recover=recover), temporary_store() as con, ExitStack() as stack:
                run_id = "reader-choice-recovery"
                row, original, draft, fake = materialization_fixture(con, run_id)
                better = inspected("better", "https://www.sec.gov/original-policy", "SEC", draft["post"])
                fake.conduct.return_value.fetches[better.fetch_id] = better
                sent = []
                def create(_model, _system, raw, **kwargs):
                    payload = json.loads(raw)
                    sent.append(payload)
                    choice = {"story_id": "sec", "verdict": "publish", "post": draft["post"],
                        "reason": "Use the original source."}
                    if recover and len(sent) == 2:
                        ref = next(r["evidence_ref"] for r in payload["unassigned_run_research"]["receipts"]
                            if r["fetch_id"] == "better")
                        choice.update(reader_receipt_ref=ref, additional_evidence_refs=[ref])
                    return response({"decisions": [choice]})
                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="test"))
                stack.enter_context(patch.object(brain, "_create", side_effect=create))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=fake))
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
                stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", False))
                stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
                publish = stack.enter_context(patch.object(publisher, "publish", return_value=("DRAFT", "fixture-draft")))
                self.assertTrue(store.acquire_cycle_lease(con, "owner"))
                result = main._run_editorial_v2(con, lease_owner="owner", pipeline_run_id=run_id,
                    inventory=[row], pending=[row], result={k: 0 for k in
                        ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                    theme_snapshot=[], overrides={}, run_started=time.time())
                self.assertEqual(len(sent), 2)
                self.assertEqual(result["drafted"], 1)
                post = dict(con.execute("SELECT * FROM posts").fetchone())
                chosen = better.final_url if recover else original.final_url
                self.assertEqual(post["body"], draft["post"])
                self.assertEqual(post["receipt_url"], chosen)
                self.assertEqual(writer_memory.publication(con, post["story_key"])["receipt_url"], chosen)
                self.assertEqual(store.accepted_reader_context(con, post["id"])["reader_receipt"]["url"], chosen)
                if not recover:
                    self.assertTrue(publish.call_args.kwargs["force_draft"])

    def test_visual_examples_are_valid_and_source_media_outranks_avatar(self):
        examples = [json.JSONDecoder().raw_decode(visual_tools.GUIDANCE[m.end():])[0]
                    for m in re.finditer(r"spec_json=", visual_tools.GUIDANCE)]
        for kind, spec in zip(("bar", "line"), examples):
            validated = visual_render.validate(kind, spec, [{"fetch_id": "fetch_id_from_tool"}])
            self.assertEqual(validated["metric"], "none")
        self.assertEqual(len(examples), 2)
        receipt = SimpleNamespace(fetch_id="r", image_candidates=[
            {"url": "https://example.org/avatar.jpg"}, {"url": "https://example.org/chart.png"}, {"url": "https://example.org/chart.png"}])
        images = visual_tools.source_images({}, [receipt])
        self.assertEqual(len(images), 2)
        self.assertTrue(images[0]["url"].endswith("chart.png"))
        self.assertIn("inspect_visual", visual_tools.availability(images)["tool"])


if __name__ == "__main__":
    unittest.main()
