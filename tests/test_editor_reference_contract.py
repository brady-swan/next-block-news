"""Keep editor appendix selections inside the IDs exposed in each API request."""
import copy
import json
import unittest
from unittest.mock import Mock, patch

from nbn import brain, editor, models
from tests.support import temporary_store
from tests.test_editorial_v2 import inspected
from tests.test_evidence_to_reader import answer, card


def additions(schema):
    return schema["properties"]["decisions"]["items"]["properties"]["additional_evidence_refs"]


def research():
    return editor.receipt_card(inspected("official", "https://opensats.org/blog/test",
        "OpenSats", "Small inspected original source. 日本語 €"))


class EditorReferenceContractTests(unittest.TestCase):
    def test_absent_and_empty_appendix_allow_only_empty_array(self):
        for appendix in (None, {}, {"receipts": []}):
            payload = {"candidates": [card()]}
            if appendix is not None:
                payload["unassigned_run_research"] = appendix
            with self.subTest(appendix=appendix):
                _, schema = editor._batch_contract(payload)
                self.assertEqual(additions(schema)["maxItems"], 0)
                self.assertEqual(additions(schema)["items"], {"type": "string"})
                self.assertNotIn("additional_evidence_refs",
                    schema["properties"]["decisions"]["items"]["required"])

    def test_exact_ids_are_request_local_and_visual_contract_is_preserved(self):
        baseline = copy.deepcopy(editor.BATCH_EDITOR_SCHEMA)
        for cards in ([card()], [card(), {**card("v"), "visual": {"asset_id": "v1"}}]):
            payload = {"candidates": cards, "unassigned_run_research": {
                "receipts": [{"evidence_ref": "research_b"}, {"evidence_ref": "research_a"}]}}
            before = copy.deepcopy(payload)
            _, schema = editor._batch_contract(payload)
            self.assertEqual(additions(schema)["items"]["enum"], ["research_a", "research_b"])
            self.assertEqual(additions(schema)["maxItems"], 8)
            props = schema["properties"]["decisions"]["items"]["properties"]
            self.assertEqual("visual_verdict" in props, len(cards) == 2)
            self.assertNotIn("enum", props["reader_receipt_ref"])
            self.assertNotIn("enum", props["story_id"])
            self.assertEqual(payload, before)
        _, empty = editor._batch_contract({"candidates": [card()]})
        self.assertNotIn("enum", additions(empty)["items"])
        self.assertEqual(editor.BATCH_EDITOR_SCHEMA, baseline)

    def test_exact_ids_reach_strict_xai_http_request(self):
        prompt, schema = editor._batch_contract({"candidates": [card()],
            "unassigned_run_research": {"receipts": [{"evidence_ref": "research_abc"}]}})
        http = Mock()
        http.__enter__ = Mock(return_value=http)
        http.__exit__ = Mock()
        http.post.return_value = Mock(is_success=True)
        http.post.return_value.json.return_value = {"status": "completed", "output": [], "usage": {}}
        with patch.dict("os.environ", XAI_API_KEY="test"), patch.object(models.httpx, "Client", return_value=http):
            models.ResponsesClient("grok-4.5").create(model="grok-4.5", system=prompt,
                messages=[], max_tokens=100, schema=schema)
        actual = http.post.call_args.kwargs["json"]["text"]["format"]
        self.assertTrue(actual["strict"])
        allowed = additions(actual["schema"])["items"]["enum"]
        self.assertEqual(allowed, ["research_abc"])
        for invalid in ("research_abc],", "reader_receipt_ref", "reader_receipt_ref:", "visual_verdict"):
            self.assertNotIn(invalid, allowed)

    def test_recovery_contract_uses_only_post_pruning_appendix(self):
        receipt = research()
        roomy, _ = editor._batch_editor_payload([card()], [], research=[receipt])
        sent = []
        def create(_model, _system, raw, **kwargs):
            payload = json.loads(raw)
            sent.append(payload)
            shown = sorted(r["evidence_ref"] for r in
                (payload.get("unassigned_run_research") or {}).get("receipts", []))
            contract = additions(kwargs["schema"])
            if shown:
                self.assertEqual(contract["items"]["enum"], shown)
            else:
                self.assertEqual(contract["maxItems"], 0)
                self.assertNotIn("enum", contract["items"])
            return answer([{"story_id": "s1", "verdict": "revise", "post": "Unapplied.",
                "additional_evidence_refs": ["not-shown"]}])
        with temporary_store() as con, patch.object(editor, "EDITOR_PAYLOAD_MAX_BYTES", editor._payload_bytes(roomy)), \
                patch.object(brain, "_create", side_effect=create):
            result = editor.review_newsroom_batch([card()], con, run_id="refs:pruned", research=[receipt])
        self.assertEqual(len(sent), 2)
        self.assertTrue(sent[0]["unassigned_run_research"]["receipts"])
        self.assertFalse((sent[1].get("unassigned_run_research") or {}).get("receipts"))
        self.assertFalse(result["decisions"])

    def test_one_recovery_preserves_valid_sibling_and_validates_exact_refs(self):
        sent = []
        def create(_model, _system, raw, **kwargs):
            payload = json.loads(raw)
            sent.append(payload)
            ref = payload["unassigned_run_research"]["receipts"][0]["evidence_ref"]
            self.assertEqual(additions(kwargs["schema"])["items"]["enum"], [ref])
            if len(sent) == 1:
                return answer([{"story_id": "s1", "verdict": "drop", "post": None},
                    {"story_id": "s2", "verdict": "revise", "post": "Bad ref.",
                     "additional_evidence_refs": [ref + "],", "reader_receipt_ref"]}])
            return answer([{"story_id": "s2", "verdict": "revise", "post": "Shorter copy.",
                "additional_evidence_refs": [ref], "reader_receipt_ref": ref}])
        with temporary_store() as con, patch.object(brain, "_create", side_effect=create):
            result = editor.review_newsroom_batch([card("s1"), card("s2")], con,
                run_id="refs:siblings", research=[research()])
        self.assertEqual(len(sent), 2)
        self.assertEqual([r["story_id"] for r in sent[1]["candidates"]], ["s2"])
        self.assertEqual(result["decisions"]["s1"]["verdict"], "drop")
        self.assertEqual(result["decisions"]["s2"]["post"], "Shorter copy.")
        self.assertEqual(result["decisions"]["s2"]["origin"], "recovery")
        self.assertEqual(len(result["decisions"]["s2"]["additional_evidence"]), 1)
