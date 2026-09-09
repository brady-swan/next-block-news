"""Plan 0069 and dense-packet follow-up: keep evidence within the same budget."""
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
    def test_real_preparation_and_shift_context_fit_without_losing_judgment(self):
        for count in (17, 25):
            with self.subTest(candidates=count), temporary_store() as con, \
                    patch.object(newsroom.anthropic, "Anthropic"):
                desk = crowded_desk(con, candidates=count, receipts=5)
                desk.recent_clusters = [{
                    "canonical_key": f"previous-event-{i}", "draft_open": True,
                    "draft_post_leads": ["Earlier accepted Bitcoin reporting with dates and attributed findings. " * 5],
                    "updated_at": 1788980000,
                } for i in range(40)]
                for index, item in enumerate(desk.inventory):
                    if index:
                        item.pop("_owner_reconsider")
                        item["note"] = "Earlier held: inspect original statement."
                    desk.preparations[item["url_hash"]] = {
                        "outcome": "model", "protection_reason": "guide_account",
                        "event_summary": "An important new development. " * 7,
                        "bitcoin_relevance": "Consequences for Bitcoin custody and monetary access. " * 3,
                        "research_objective": "Inspect the dated original statement, compare earlier coverage and preserve the announcement scope. " * 2,
                        "source_leads": [item["url"], "https://example.com/original-statement"],
                        "related_keys": [item["story_key"]],
                    }
                desk.incoming_handoff = {
                    "body": "Check the original statement; earlier copy is only a draft. " * 28,
                    "run_id": "previous-run", "written_at": 1788980000,
                    "actual_story_outcomes": [{"event_key": "previous-event-0", "editor_decision": "revise"}],
                    "actual_outputs": [{"event_key": "previous-event-0", "publisher_status": "draft", "confirmed_at": None}],
                }
                letter = copy.deepcopy(desk.incoming_handoff)
                output = {"id": 12, "body": "Earlier accepted copy with useful specifics. " * 70,
                          "mode": "draft", "publisher_status": "draft", "created": 1788980000,
                          "confirmed_at": None, "receipt_url": "https://example.com/original"}
                with patch.object(writer_memory, "publication", return_value=output):
                    packet = desk._initial_packet()
                self.assertLessEqual(newsroom._json_bytes(packet), config.COMPACT_DESK_INITIAL_BYTES)
                self.assertEqual(len(packet["intake_board"]), count)
                self.assertEqual(packet["incoming_shift_letter"], letter)
                self.assertEqual(len(packet["coverage_board"]["open_drafts"]), 40)
                self.assertEqual(len(packet["prepared_evidence"]), 5)
                for row in packet["intake_board"]:
                    self.assertIn("important new development", row["haiku_preparation"]["event_summary"])
                    self.assertIn("original statement", row["haiku_preparation"]["research_objective"])
                    self.assertTrue(row["research_retry"])
                self.assertEqual(packet["intake_board"][0]["owner_override"]["requested_by"], "Brady")
                accepted = packet["matching_accepted_output"][0]
                self.assertEqual(accepted["publisher_status"], "draft")
                self.assertIsNone(accepted["confirmed_at"])
                # Exercise the actual bounded retrieval tool for both full records.
                cid = packet["intake_board"][0]["candidate_context_id"]
                result = desk._read_desk_context([cid])
                self.assertTrue(result["ok"])
                for key, value in desk.preparations[desk.inventory[0]["url_hash"]].items():
                    self.assertEqual(result["rows"][0]["haiku_preparation"][key], value)
                result = desk._read_desk_context([accepted["context_id"]])
                self.assertTrue(result["ok"])
                self.assertEqual(result["rows"][0]["accepted_output"], output)

    def test_metadata_pressure_preserves_sources_controls_and_retrieval(self):
        from nbn import perception
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con)
            desk.recent_clusters = [{
                "canonical_key": f"covered-event-{i}", "draft_open": True,
                "draft_post_leads": ["Earlier accepted Bitcoin reporting. " * 10],
            } for i in range(50)]
            desk.continuity_cards = [{
                "event_key": f"earlier-event-{i}", "state": "deferred",
                "matches_current_item": False, "unresolved_gate": "Needs dated source.",
                "research_objective": "Check the original disclosure and prior accepted copy.",
            } for i in range(12)]
            for item in desk.inventory:
                item.pop("_owner_reconsider", None)
                item["story_key"] = None
                item["note"] = "defer:newsdesk_unavailable:initial_context_overflow"
                desk.preparations[item["url_hash"]] = {
                    "outcome": "batch_fail_open", "event_summary": item["title"],
                    "bitcoin_relevance": "Preparation unavailable; advanced to newsroom.",
                    "research_objective": "Let the Writer inspect and decide.",
                    "source_leads": [], "protection_reason": None,
                }
            desk.inventory[0]["_owner_reconsider"] = {"requested_by": "Brady", "prior_skip": "Already covered"}
            before_fetches = copy.deepcopy(desk.fetches)

            def hint(_con, url):
                return {"url": url, "artifact_id": "artifact_perception_" + "a" * 24,
                        "published_at": "2026-09-09T14:05:25+00:00", "captured_at": 1788965380.5,
                        "characters": 443, "completeness": "unknown",
                        "use": "Available dated text, not yet read in this session; use perception_article if useful."}

            with patch.object(perception, "candidate_hint", side_effect=hint):
                with patch.object(newsroom, "_compact_packet_repetition"), \
                        patch.object(newsroom, "_fit_optional_previews"):
                    with self.assertRaises(newsroom.NewsroomError) as raised:
                        desk._initial_packet()
                    self.assertEqual(raised.exception.kind, "initial_context_overflow")
                packet = desk._initial_packet()
            self.assertLessEqual(newsroom._json_bytes(packet), 65536)
            self.assertEqual(len(packet["intake_board"]), 25)
            self.assertEqual(len(packet["prepared_evidence"]), 6)
            self.assertEqual(len(packet["coverage_board"]["open_drafts"]), 50)
            self.assertEqual(len(packet["continuity_board"]["index"]), 12)
            self.assertNotIn("continuity", packet["retrievable_context_index"])
            defaults = packet["run_brief"]["compact_display_defaults"]
            self.assertIn("not yet read", defaults["available_perception_text.use"])
            self.assertIn("not_instruction", defaults["prior_item_state_untrusted_context.use"])
            for row in packet["intake_board"]:
                full = desk.context_rows[row["candidate_context_id"]]
                self.assertEqual(row["candidate_id"], full["candidate_id"])
                self.assertEqual(row.get("owner_override"), full.get("owner_override"))
                self.assertEqual(row["haiku_preparation"]["outcome"], "batch_fail_open")
                self.assertEqual(row["available_perception_text"]["artifact_id"],
                                 full["available_perception_text"]["artifact_id"])
                self.assertEqual(row["intake_url"], full["available_perception_text"]["url"])
                self.assertEqual(row["prior_item_state_untrusted_context"]["note"],
                                 full["prior_item_state_untrusted_context"]["note"])
            for row in packet["prepared_evidence"]:
                full = desk.context_rows[row["context_id"]]
                self.assertEqual(row["content_fingerprint"], source_policy.content_fingerprint(row["text"]))
                self.assertEqual(row["original_content_fingerprint"], full["original_content_fingerprint"])
                self.assertEqual(row["excerpt_of_content_fingerprint"], full["content_fingerprint"])
                self.assertEqual(row["limitations"], full["limitations"])
                self.assertEqual(row["inspectable_evidence"], full["inspectable_evidence"])
                self.assertEqual(row["visual_available"]["count"], full["visual_available"]["count"])
            self.assertEqual(desk.fetches, before_fetches)
            # Retrieval is still the full original, not the deduplicated display.
            cid = packet["prepared_evidence"][0]["context_id"]
            full = desk._read_desk_context([cid])["rows"][0]
            if "section_ids" in full:
                ids, sections = full["section_ids"], []
                while ids:
                    result = desk._read_desk_context(ids[:config.COMPACT_DESK_RETRIEVAL_ROWS])
                    self.assertTrue(result["ok"])
                    self.assertTrue(result["rows"])
                    sections.extend(result["rows"])
                    read = {row["context_id"] for row in result["rows"]}
                    ids = [value for value in ids if value not in read]
                full = json.loads("".join(row["text"] for row in sorted(sections, key=lambda row: row["part"])))
            self.assertIn("requested_url", full)
            self.assertIn("canonical_url", full)
            self.assertIn("redirect_chain", full)
            for key, value in desk._fetch_payload(next(iter(before_fetches.values())), cached=True).items():
                self.assertEqual(full[key], value, key)

    def test_metadata_dedup_is_exact_and_preserves_distinct_context(self):
        original = {
            "run_brief": {},
            "prepared_evidence": [{
                "fetch_id": "receipt", "final_url": "https://example.com/news",
                "requested_url": "https://example.com/news/", "canonical_url": "https://origin.example/report",
                "redirect_chain": ["https://example.com/news", "https://example.com/news"],
                "text": "Evidence", "content_fingerprint": "literal-fingerprint",
                "original_content_fingerprint": "distinct-original", "excerpt_of_content_fingerprint": "distinct-capture",
                "byline": "Reporter", "published_at": "2026-09-08", "limitations": "Partial capture",
                "official": False, "inspectable_evidence": False,
                "visual_available": {"count": 0, "tool": "different tool", "purpose": "different purpose"},
            }],
            "intake_board": [{"candidate_id": "c", "intake_url": "https://example.com/news",
                "available_perception_text": {"url": "https://example.com/news/", "use": "Distinct warning"},
                "prior_item_state_untrusted_context": {"story_key": "real-event", "use": "Distinct history"},
                "haiku_preparation": {"outcome": "model", "protection_reason": False},
                "research_retry": False, "first_seen_at": 0, "owner_override": {"by": "Brady"},
                "identity_correction": {"failure": "wrong event"}}],
            "continuity_board": {"index": [{"context_id": "a"}]},
            "retrievable_context_index": {"continuity": [{"context_id": "b"}]},
        }
        packet = copy.deepcopy(original)
        newsroom._compact_packet_repetition(packet)
        for key in ("prepared_evidence", "intake_board", "continuity_board", "retrievable_context_index"):
            self.assertEqual(packet[key], original[key])
        once = copy.deepcopy(packet)
        newsroom._compact_packet_repetition(packet)
        self.assertEqual(packet, once)

    def test_dense_fail_open_desk_removes_only_mechanical_repetition(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            desk = crowded_desk(con, receipts=5)
            for index, item in enumerate(desk.inventory):
                item["note"] = "defer:initial_context_overflow"
                if index:
                    item.pop("_owner_reconsider", None)
                desk.preparations[item["url_hash"]] = {
                    "outcome": "budget_fail_open", "event_summary": item["title"][:200],
                    "bitcoin_relevance": "Preparation was unavailable; advanced to newsroom.",
                    "research_objective": "Let Sonnet inspect and make the editorial call.",
                    "source_leads": [], "protection_reason": "guide_account",
                }
            desk.recent_clusters = [{
                "canonical_key": f"covered-event-{index}", "draft_open": index < 20,
                "reader_covered": index == 0, "titles": ["Existing exact event title " * 10],
                "draft_post_leads": ["An existing open draft lede " * 10],
                "reader_post_leads": ["Published post lede " * 10],
            } for index in range(50)]
            baseline = {}
            def unchanged(row, full):
                baseline[row["candidate_id"]] = copy.deepcopy(row)
                return row
            with patch.object(newsroom, "_compact_candidate_density", side_effect=unchanged), \
                    patch.object(newsroom, "_fit_optional_previews"):
                with self.assertRaises(newsroom.NewsroomError):
                    desk._initial_packet()
            packet = desk._initial_packet()
            self.assertLessEqual(newsroom._json_bytes(packet), 65536)
            self.assertEqual(len(packet["intake_board"]), 25)
            self.assertEqual(len(packet["prepared_evidence"]), 5)
            self.assertIn("no model judgment", packet["run_brief"]["compaction_note"])
            for row in packet["intake_board"]:
                self.assertEqual(row["haiku_preparation"], {
                    "outcome": "budget_fail_open", "protection_reason": "guide_account"})
                original = baseline[row["candidate_id"]]
                for key, value in original.items():
                    if key != "haiku_preparation" and value not in (None, "", [], {}):
                        self.assertEqual(row[key], value, key)
            drafts = packet["coverage_board"]["open_drafts"]
            self.assertEqual(len(drafts), 20)
            for row, original in zip(drafts, desk.recent_clusters[:20]):
                self.assertEqual(row["event_key"], original["canonical_key"])
                self.assertEqual(row["post_leads"], [original["draft_post_leads"][0][:260]])
            first = packet["intake_board"][0]
            full = desk._read_desk_context([first["candidate_context_id"]])["rows"][0]
            self.assertEqual(full["haiku_preparation"]["event_summary"],
                             desk.preparations[first["candidate_id"]]["event_summary"])
            self.assertEqual(full["haiku_preparation"]["outcome"], "budget_fail_open")
            self.assertEqual(first["owner_override"], full["owner_override"])
            self.assertEqual(first["prior_item_state_untrusted_context"],
                             full["prior_item_state_untrusted_context"])

    def test_density_tier_preserves_real_preparation_controls_false_and_zero(self):
        row = {
            "candidate_id": "c1", "research_retry": False, "first_seen_at": 0,
            "candidate_context_id": "ctx_full", "owner_override": {"note": "", "by": "Brady"},
            "identity_correction": {"failure": "wrong_key", "allowed_exact_event_keys": ["exact-1"]},
            "haiku_preparation": {"event_summary": "Useful actual judgment.",
                                  "source_leads": [{"url": "https://example.com/original"}]},
            "empty_optional": None, "empty_list": [], "empty_text": "", "empty_object": {},
        }
        original = copy.deepcopy(row)
        full = {**copy.deepcopy(row), "haiku_preparation": {
            **row["haiku_preparation"], "outcome": "model", "protection_reason": "guide_account"}}
        model = newsroom._compact_candidate_density(row, full)
        self.assertEqual(model["haiku_preparation"], original["haiku_preparation"])
        for key in ("research_retry", "first_seen_at", "owner_override", "identity_correction"):
            self.assertEqual(model[key], original[key])
        for key in ("empty_optional", "empty_list", "empty_text", "empty_object"):
            self.assertNotIn(key, model)
        for outcome in ("batch_fail_open", "budget_fail_open", "overflow_fail_open", "validation_fail_open"):
            with self.subTest(outcome=outcome):
                full["haiku_preparation"]["outcome"] = outcome
                fallback = newsroom._compact_candidate_density(row, full)
                self.assertEqual(fallback["haiku_preparation"], {
                    "outcome": outcome, "protection_reason": "guide_account"})
        for outcome in ("protected", "unrecognized_fail_open"):
            full["haiku_preparation"]["outcome"] = outcome
            self.assertEqual(newsroom._compact_candidate_density(row, full)["haiku_preparation"],
                             original["haiku_preparation"])
        self.assertEqual(row, original)
        self.assertEqual(full["haiku_preparation"]["event_summary"], "Useful actual judgment.")

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
