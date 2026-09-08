"""Plan 0069: crowded desks keep evidence and identity without a larger budget."""
import copy
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

from nbn import config, newsroom, source_policy, store, visual_tools, writer_memory
from tests.support import temporary_store
from tests.test_editorial_v2 import candidate, inspected


def crowded_desk(con, *, candidates=25, receipts=6):
    rows = [{**candidate(f"candidate-{i}"),
             "title": f"Bitcoin lead {i}: " + "Headline context " * 18,
             "url": f"https://www.sec.gov/newsroom/press-releases/lead-{i}",
             "summary": "Source context and disclosure dates. " * 20,
             "story_key": f"previous-event-{i}", "note": "Earlier held reason. " * 12,
             "decision_stage": "newsroom", "decision_category": "held",
             "_research_retry": True,
             "_owner_reconsider": {"requested_by": "Brady", "prior_skip": "Already covered"}}
            for i in range(candidates)]
    coverage = [{"canonical_key": f"covered-event-{i}", "draft_open": True,
                 "titles": ["Earlier report " * 20] * 3,
                 "draft_post_leads": ["Earlier accepted copy " * 15] * 2,
                 "aliases": [f"alias-{i}"], "sources": ["Source " * 20] * 3,
                 "updated_at": 1788870000 - i * 60}
                for i in range(8)]
    coverage[-1].update(canonical_key="strategy-weekly-treasury-2026-09-08",
                        draft_post_leads=["Strategy repurchased $176M of STRC. No Bitcoin bought or sold."])
    desk = newsroom.NewsroomSession(run_id="compact-repair", inventory=rows,
        recent_clusters=coverage, theme_snapshot=[], handles={}, con=con, reservation="r",
        prep_mode="off", research_mode="off", compact_enabled=True)
    # Fail-open intake can advance all 25 candidates even without useful prep summaries.
    for i in range(receipts):
        text = ("Bitcoin source evidence. " + "数値と日付。" * 12) * 40
        record = replace(inspected(f"receipt-{i}", rows[i % len(rows)]["url"], "SEC", text),
            adapter_provenance="desk_prefetch", published_at="2026-09-08",
            limitations="Text capture; source figures have not been visually inspected.",
            links=tuple({"text": f"Original source {j} " + "L" * 100,
                         "url": f"https://www.sec.gov/evidence/{i}/{j}"} for j in range(25)),
            image_candidates=tuple({"url": f"https://www.sec.gov/figure/{i}/{j}.png",
                "source_url": rows[i % len(rows)]["url"], "kind": "source_chart",
                "image_date": "2026-09-08", "alt": "A relevant figure " * 30}
                for j in range(3)))
        desk.fetches[record.fetch_id] = record
    return desk


class CompactDeskTests(unittest.TestCase):
    def test_crowded_packet_retains_candidates_receipts_hints_and_older_open_draft(self):
        self.assertIn("full candidate details via candidate_context_id", newsroom.NEWSROOM_V2_SYSTEM)
        self.assertIn("receipt text/link/image metadata via context_id", newsroom.NEWSROOM_V2_SYSTEM)
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con)
            visual = visual_tools.availability([{"source_url": "https://www.sec.gov/chart", "kind": "chart"}])
            correction = {"failure": "unknown_existing_cluster_key", "candidate_ids": ["candidate-0"],
                          "existing_cluster_key": "broad-storyline", "instruction": "Use an exact event key."}
            with patch.object(visual_tools, "source_images", return_value=[{"kind": "chart"}]), \
                    patch.object(visual_tools, "availability", return_value=visual), \
                    patch.object(writer_memory, "latest_identity_failure", return_value=correction):
                packet = desk._initial_packet()
            self.assertLessEqual(newsroom._json_bytes(packet), 65536)
            self.assertEqual(len(packet["intake_board"]), 25)
            self.assertEqual({r["candidate_id"] for r in packet["intake_board"]}, set(desk.by_hash))
            self.assertEqual(len(packet["prepared_evidence"]), 6)
            for row in packet["intake_board"]:
                self.assertTrue(row["research_retry"])
                self.assertEqual(row["identity_correction"], correction)
                self.assertEqual(row["owner_override"]["requested_by"], "Brady")
                self.assertEqual(row["prior_item_state_untrusted_context"]["decision_category"], "held")
                self.assertEqual(row["visual_available"]["count"], 1)
                self.assertIn(row["candidate_context_id"], desk.context_rows)
            drafts = packet["coverage_board"]["open_drafts"]
            self.assertEqual(len(drafts), 8)
            self.assertEqual(drafts[-1]["event_key"], "strategy-weekly-treasury-2026-09-08")
            self.assertIn("$176M", drafts[-1]["post_leads"][0])
            self.assertEqual(desk.context_rows[drafts[-1]["context_id"]]["known_aliases"], ["alias-7"])
            for row in packet["prepared_evidence"]:
                self.assertNotIn("links", row)
                self.assertNotIn("image_candidates", row)
                self.assertEqual(row["link_count"], 25)
                self.assertEqual(row["image_count"], 3)
                self.assertEqual(row["content_fingerprint"], source_policy.content_fingerprint(row["text"]))
                self.assertEqual(desk.context_rows[row["context_id"]]["text"], desk.fetches[row["fetch_id"]].text)
            opened = desk._read_desk_context([packet["intake_board"][0]["candidate_context_id"]])
            self.assertTrue(opened["ok"])
            self.assertEqual(opened["rows"][0]["what_arrived"], desk.inventory[0]["summary"][:600])
            self.assertEqual(opened["rows"][0]["identity_correction"], correction)
            self.assertEqual(len(opened["rows"][0]["references"]), 1)

    def test_exact_receipt_context_readback_including_sections_with_no_refetch(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con, candidates=1, receipts=1)
            with patch.object(newsroom.sources, "fetch_article") as fetch:
                packet = desk._initial_packet()
                row = packet["prepared_evidence"][0]
                expected = desk._fetch_payload(desk.fetches[row["fetch_id"]], cached=True)
                opened = desk._read_desk_context([row["context_id"]])["rows"][0]
                if "section_ids" in opened:
                    sections = []
                    ids = opened["section_ids"]
                    while ids:
                        result = desk._read_desk_context(ids[:config.COMPACT_DESK_RETRIEVAL_ROWS])
                        self.assertTrue(result["ok"])
                        self.assertTrue(result["rows"])
                        sections.extend(result["rows"])
                        read = {r["context_id"] for r in result["rows"]}
                        ids = [cid for cid in ids if cid not in read]
                    opened = json.loads("".join(s["text"] for s in sorted(sections, key=lambda x: x["part"])))
                for key, value in expected.items():
                    self.assertEqual(opened[key], value, key)
                fetch.assert_not_called()
                self.assertLessEqual(desk.context_retrieval_calls, config.COMPACT_DESK_RETRIEVAL_CALLS)
                self.assertLessEqual(desk.context_retrieval_bytes, config.COMPACT_DESK_RETRIEVAL_TOTAL_BYTES)

    def test_utf8_excerpt_preserves_capture_fingerprints_and_limits(self):
        text = "₿ 😀 日本語 " * 900
        payload = {"text": text, "content_fingerprint": source_policy.content_fingerprint(text),
                   "original_content_fingerprint": "upstream-fingerprint", "text_truncated": False,
                   "limitations": "Previously captured evidence.", "context_id": "ctx_example"}
        original = copy.deepcopy(payload)
        for limit in (4000, 2000, 1000, 500):
            payload = newsroom._evidence_excerpt(payload, limit)
            self.assertLessEqual(len(payload["text"].encode()), limit)
            self.assertTrue(text.startswith(payload["text"]))
            self.assertTrue(payload["text_truncated"])
            self.assertEqual(payload["content_fingerprint"], source_policy.content_fingerprint(payload["text"]))
            self.assertEqual(payload["excerpt_of_content_fingerprint"], original["content_fingerprint"])
            self.assertEqual(payload["original_content_fingerprint"], "upstream-fingerprint")
            self.assertEqual(payload["limitations"], original["limitations"])

    def test_small_receipt_remains_inline_and_full_record_is_not_mutated(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con, candidates=1, receipts=0)
            record = replace(inspected("small", candidate()["url"], "SEC", "The original statement."),
                             adapter_provenance="desk_prefetch", text_truncated=True,
                             links=({"text": "Source", "url": candidate()["url"]},))
            desk.fetches[record.fetch_id] = record
            packet = desk._initial_packet()
            row = packet["prepared_evidence"][0]
            self.assertEqual(row["text"], record.text)
            self.assertEqual(row["content_fingerprint"], record.content_fingerprint)
            self.assertEqual(row["links"], list(record.links))
            self.assertTrue(row["text_truncated"])
            self.assertNotIn("excerpt_of_content_fingerprint", row)
            self.assertIs(desk.fetches[record.fetch_id], record)

    def test_receipt_text_yields_before_irreducible_overflow(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con, candidates=1)
            with patch.object(config, "COMPACT_DESK_INITIAL_BYTES", 24000):
                packet = desk._initial_packet()
            self.assertLessEqual(newsroom._json_bytes(packet), 24000)
            self.assertEqual(len(packet["prepared_evidence"]), 6)
            self.assertTrue(all(len(r["text"].encode()) <= 2000 for r in packet["prepared_evidence"]))
            self.assertEqual(len(packet["coverage_board"]["open_drafts"]), 8)

    def test_irreducible_overflow_records_measurements_not_a_writer_handoff(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con, candidates=1, receipts=1)
            with patch.object(config, "COMPACT_DESK_INITIAL_BYTES", 100):
                with self.assertRaises(newsroom.NewsroomError) as raised:
                    desk._initial_packet()
            self.assertEqual(raised.exception.kind, "initial_context_overflow")
            observed = con.execute("SELECT kind,payload_json FROM run_observations WHERE run_id=?",
                                   (desk.run_id,)).fetchall()
            self.assertEqual([r["kind"] for r in observed], ["writer_packet_overflow"])
            data = json.loads(observed[0]["payload_json"])
            self.assertEqual(data["limit"], 100)
            self.assertGreater(data["bytes"], 100)
            self.assertEqual(data["candidate_count"], 1)
            self.assertGreater(data["section_bytes"]["prepared_evidence"], 0)


if __name__ == "__main__":
    unittest.main()
