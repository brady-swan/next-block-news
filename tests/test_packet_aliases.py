"""Post-0074 natural overflow reconstruction; no provider calls or historical replay."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from nbn import config, newsroom
from tests.support import temporary_store
from tests.test_compact_desk import crowded_desk


def fixture(name="post0074-packet.json"):
    return json.loads((Path(__file__).parent / "fixtures" / name).read_text())


class PacketAliasTests(unittest.TestCase):
    def test_frozen_reconstruction_fits_without_changing_reporting_or_context(self):
        data = fixture()
        original = copy.deepcopy(data)
        packet = data["packet"]
        self.assertEqual(newsroom._json_bytes(packet), 71779)
        newsroom._compact_packet_aliases(packet)
        self.assertLessEqual(newsroom._json_bytes(packet), 65536)
        self.assertEqual(data["context_rows"], original["context_rows"])
        for key in ("incoming_shift_letter", "matching_accepted_output", "continuity_board",
                    "memory_catalog", "retrievable_context_index"):
            self.assertEqual(packet[key], original["packet"][key])
        for before, after in zip(original["packet"]["intake_board"], packet["intake_board"]):
            for key, value in before.items():
                if key not in {"expert_attention", "prior_item_state_untrusted_context"}:
                    self.assertEqual(after[key], value)
            self.assertIn(after["candidate_context_id"], data["context_rows"])
        for kind, rows in packet["coverage_board"].items():
            self.assertEqual(len(rows), len(original["packet"]["coverage_board"][kind]))
            for before, after in zip(original["packet"]["coverage_board"][kind], rows):
                self.assertEqual({**{"headlines": [], "post_leads": []}, **after}, before)
                self.assertIn(after["context_id"], data["context_rows"])
        for before, after in zip(original["packet"]["prepared_evidence"], packet["prepared_evidence"]):
            restored = dict(after)
            if restored.pop("prefetch_meta", False):
                legend = packet["run_brief"]["compact_display_defaults"]["prepared_evidence.prefetch_meta"]
                restored.update({key: value for key, value in legend.items() if key != "applies_when"})
            restored.setdefault("original_content_fingerprint", restored["excerpt_of_content_fingerprint"])
            if restored.pop("chain_pair", False):
                restored["redirect_chain"] = [restored["requested_url"], restored["final_url"]]
            self.assertEqual(restored, before)
            self.assertIn(after["context_id"], data["context_rows"])
        once = copy.deepcopy(packet)
        newsroom._compact_packet_aliases(packet)
        self.assertEqual(packet, once)
        # Extra preserved content probes margin; this is not an exact historic replay.
        packet["run_brief"]["assignment"] += "x" * 762
        self.assertLessEqual(newsroom._json_bytes(packet), 65536)

    def test_second_corrected_reconstruction_fits_with_dates_and_real_preparation(self):
        data = fixture("post0074-packet-second.json")
        before = copy.deepcopy(data)
        self.assertEqual(newsroom._json_bytes(data["packet"]), 72530)
        newsroom._compact_packet_aliases(data["packet"])
        self.assertLessEqual(newsroom._json_bytes(data["packet"]), 65536)
        self.assertEqual(data["context_rows"], before["context_rows"])
        for old, new in zip(before["packet"]["intake_board"], data["packet"]["intake_board"]):
            for key in ("candidate_id", "arrived_at", "haiku_preparation", "research_retry",
                        "candidate_context_id", "full_lead_context_id"):
                self.assertEqual(new.get(key), old.get(key))

    def test_prefetch_metadata_requires_all_exact_typed_values_and_roundtrips(self):
        metadata = {
            "ok": True, "cached": True, "adapter_provenance": "desk_prefetch",
            "inspectable_evidence": True, "evidence_capability": "inspected_social_statement",
            "independent_report": False, "retrieval_kind": "direct_fetch", "text_truncated": True,
        }
        rows = [{**metadata, "text": "Original excerpt", "fetch_id": "first"}]
        for key, value in metadata.items():
            missing = dict(metadata)
            del missing[key]
            rows.append(missing)
            for replacement in ([None, not value, int(value)] if isinstance(value, bool)
                                else [None, "distinct"]):
                rows.append({**metadata, key: replacement})
        original = copy.deepcopy(rows)
        packet = {"run_brief": {}, "prepared_evidence": rows}
        newsroom._compact_packet_aliases(packet)
        self.assertEqual(packet["prepared_evidence"][0], {
            "text": "Original excerpt", "fetch_id": "first", "prefetch_meta": True})
        self.assertEqual(packet["prepared_evidence"][1:], original[1:])
        legend = packet["run_brief"]["compact_display_defaults"]["prepared_evidence.prefetch_meta"]
        restored = copy.deepcopy(packet["prepared_evidence"])
        for row in restored:
            if row.pop("prefetch_meta", False):
                row.update({key: value for key, value in legend.items() if key != "applies_when"})
        self.assertEqual(restored, original)
        self.assertEqual(rows, original)
        once = copy.deepcopy(packet)
        newsroom._compact_packet_aliases(packet)
        self.assertEqual(packet, once)

    def test_mixed_technical_states_never_invent_missing_or_editorial_fields(self):
        state = {"note": "defer:newsdesk_unavailable:initial_context_overflow",
                 "decision_stage": "newsdesk", "decision_category": "technical_defer"}
        states = [state, {}, None, {**state, "story_key": "exact-event"},
                  {**state, "note": "Owner says keep the existing draft"},
                  {**state, "decision_category": None}, {**state, "extra": False},
                  {"note": state["note"]}]
        rows = [{"candidate_id": str(i), "prior_item_state_untrusted_context": copy.deepcopy(s)}
                for i, s in enumerate(states)] + [{"candidate_id": "absent"}]
        original = copy.deepcopy(rows)
        packet = {"run_brief": {}, "intake_board": rows}
        newsroom._compact_packet_aliases(packet)
        legend = packet["run_brief"]["compact_display_defaults"][
            "prior_item_state_untrusted_context.compact_default"]
        self.assertEqual(packet["intake_board"][0]["prior_item_state_untrusted_context"],
                         {"compact_default": True})
        restored = copy.deepcopy(packet["intake_board"])
        for row in restored:
            if row.get("prior_item_state_untrusted_context") == legend["applies_when"]:
                row["prior_item_state_untrusted_context"] = {
                    key: value for key, value in legend.items() if key != "applies_when"}
        self.assertEqual(restored, original)
        self.assertEqual(rows, original)

    def test_distinct_receipt_and_attention_metadata_stays_exact(self):
        receipts = [
            {"original_content_fingerprint": "source", "excerpt_of_content_fingerprint": "capture",
             "requested_url": "a", "final_url": "b", "redirect_chain": ["a", "hop", "b"]},
            {"original_content_fingerprint": "source", "text_truncated": True,
             "requested_url": "a", "final_url": "b", "redirect_chain": ["a", "a", "b"]},
            {"original_content_fingerprint": None, "excerpt_of_content_fingerprint": "",
             "requested_url": None, "final_url": "b", "redirect_chain": [None, "b"]},
        ]
        row = {"intake_url": "original", "expert_attention": {
            "post_url": "different", "instruction": "Distinct caution", "actor": "expert"}}
        packet = {"run_brief": {}, "prepared_evidence": copy.deepcopy(receipts),
                  "intake_board": [copy.deepcopy(row)]}
        newsroom._compact_packet_aliases(packet)
        self.assertEqual(packet["prepared_evidence"], receipts)
        self.assertEqual(packet["intake_board"], [row])

    def test_mixed_redirect_tiers_preserve_single_final_and_pair_meanings(self):
        receipts = [
            {"requested_url": "a", "final_url": "b", "redirect_chain": ["b"]},
            {"requested_url": "c", "final_url": "d", "redirect_chain": ["c", "d"]},
            {"requested_url": "e", "final_url": "f", "redirect_chain": ["e", "e", "f"]},
            {"requested_url": "g", "final_url": "g", "redirect_chain": ["g"]},
        ]
        packet = {"run_brief": {}, "prepared_evidence": copy.deepcopy(receipts)}
        newsroom._compact_packet_repetition(packet)
        prior_legend = packet["run_brief"]["compact_display_defaults"]["prepared_evidence.URLs"]
        newsroom._compact_packet_aliases(packet)
        self.assertEqual(packet["run_brief"]["compact_display_defaults"]["prepared_evidence.URLs"],
                         prior_legend)
        restored = []
        for after in packet["prepared_evidence"]:
            row = dict(after)
            row.setdefault("requested_url", row["final_url"])
            if row.pop("chain_pair", False):
                row["redirect_chain"] = [row["requested_url"], row["final_url"]]
            else:
                row.setdefault("redirect_chain", [row["final_url"]])
            restored.append(row)
        self.assertEqual(restored, receipts)

    def test_real_bounded_context_reads_preserve_candidate_coverage_and_receipt(self):
        data = fixture()
        packet = data["packet"]
        newsroom._compact_packet_aliases(packet)
        targets = [packet["intake_board"][0]["candidate_context_id"],
                   packet["matching_accepted_output"][0]["context_id"],
                   max(packet["prepared_evidence"], key=lambda r:
                       newsroom._json_bytes(data["context_rows"][r["context_id"]]))["context_id"]]
        # Each target is a separate legal retrieval choice, not a claim all fit together.
        for cid in targets:
            with self.subTest(cid=cid), temporary_store() as con, \
                    patch.object(newsroom.anthropic, "Anthropic"), \
                    patch.object(newsroom.sources, "fetch_article") as fetch:
                desk = crowded_desk(con, candidates=1, receipts=0)
                desk.context_rows = copy.deepcopy(data["context_rows"])
                expected = copy.deepcopy(desk.context_rows[cid])
                result = desk._read_desk_context([cid])
                self.assertTrue(result["ok"])
                opened = result["rows"][0]
                if "section_ids" in opened:
                    ids, sections = opened["section_ids"], []
                    while ids:
                        result = desk._read_desk_context(ids[:config.COMPACT_DESK_RETRIEVAL_ROWS])
                        self.assertTrue(result["ok"])
                        self.assertTrue(result["rows"])
                        sections.extend(result["rows"])
                        consumed = {r["context_id"] for r in result["rows"]}
                        ids = [value for value in ids if value not in consumed]
                    opened = json.loads("".join(s["text"] for s in sorted(sections, key=lambda s: s["part"])))
                for key, value in expected.items():
                    self.assertEqual(opened[key], value, key)
                self.assertLessEqual(desk.context_retrieval_calls, config.COMPACT_DESK_RETRIEVAL_CALLS)
                self.assertLessEqual(desk.context_retrieval_bytes, config.COMPACT_DESK_RETRIEVAL_TOTAL_BYTES)
                fetch.assert_not_called()

    def test_existing_fitting_packets_do_not_enter_alias_tier(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"), \
                patch.object(newsroom, "_compact_packet_aliases") as aliases:
            desk = crowded_desk(con, candidates=1, receipts=1)
            self.assertLessEqual(newsroom._json_bytes(desk._initial_packet()), 65536)
            aliases.assert_not_called()


if __name__ == "__main__":
    unittest.main()
