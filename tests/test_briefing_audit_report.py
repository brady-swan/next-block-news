import datetime
import json
import time
import unittest
from unittest.mock import patch

from nbn import audit, brain, briefing, config, publisher_typefully, report, store
from tests.support import temporary_store


def brief_payload():
    return {"daily_brief": {
        "theme": "Bitcoin policy",
        "body_md": "Official source https://example.com/source",
        "must_know": [],
    }}


def block_posts(text="Bitcoin policy update.", receipt="https://example.com/source"):
    return [
        {"text": "Morning Block - August thirty-first\n\nTop stories:\n• Bitcoin policy\n\nMore inside ➡️",
         "receipt": None},
        {"text": text, "receipt": receipt},
        {"text": "Bitcoin policy context.", "receipt": receipt},
        {"text": "Watch the official process.", "receipt": receipt},
    ]


class BriefingTests(unittest.TestCase):
    def build(self, posts):
        with patch.object(brain, "_create", return_value=object()), \
                patch.object(brain, "_json_from", return_value={"posts": posts}):
            return briefing.build_thread(brief_payload(), "Morning")

    def test_valid_receipts_pass(self):
        self.assertIsNotNone(self.build(block_posts()))

    def test_swan_reference_is_rejected(self):
        self.assertIsNone(self.build(block_posts(text="Swan policy update.")))

    def test_receipt_outside_brief_is_rejected(self):
        self.assertIsNone(self.build(block_posts(receipt="https://other.example/source")))

    def test_wrong_thread_size_is_rejected(self):
        self.assertIsNone(self.build(block_posts()[:3]))

    def test_truncated_json_gets_one_compact_retry_with_larger_budget(self):
        with patch.object(brain, "_create", side_effect=[object(), object()]) as create, \
                patch.object(brain, "_json_from", side_effect=[
                    ValueError("no JSON in response"), {"posts": block_posts()}
                ]):
            posts = briefing.build_thread(brief_payload(), "Afternoon")
        self.assertEqual(posts, block_posts())
        self.assertEqual(create.call_count, 2)
        self.assertEqual(create.call_args_list[0].kwargs["max_tokens"], 8000)
        retry_payload = json.loads(create.call_args_list[1].args[2])
        self.assertIn("compact", retry_payload["retry_instruction"])

    def test_two_invalid_json_responses_fail_cleanly(self):
        with patch.object(brain, "_create", side_effect=[object(), object()]), \
                patch.object(brain, "_json_from", side_effect=ValueError("truncated")):
            self.assertIsNone(briefing.build_thread(brief_payload(), "Afternoon"))

    def test_gate_failure_gets_one_feedback_retry(self):
        bad = block_posts(text="Bitcoin policy reached $99,999.")
        with patch.object(brain, "_create", side_effect=[object(), object()]) as create, \
                patch.object(brain, "_json_from", side_effect=[
                    {"posts": bad}, {"posts": block_posts()}
                ]):
            posts = briefing.build_thread(brief_payload(), "Afternoon")
        self.assertEqual(posts, block_posts())
        retry_payload = json.loads(create.call_args_list[1].args[2])
        self.assertIn("number not in source text", retry_payload["retry_instruction"])

    def test_triage_prompt_allows_factual_data_and_official_media_research(self):
        self.assertIn("Factual Bitcoin market-state reporting is eligible", brain.TRIAGE_SYSTEM)
        self.assertIn("Judge the factual payload", brain.TRIAGE_SYSTEM)
        self.assertIn("prepared remarks or a transcript", brain.TRIAGE_SYSTEM)
        self.assertNotIn("Typical batch yields 0-3 drafts", brain.TRIAGE_SYSTEM)


class AfternoonDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 31, 21, 55, tzinfo=datetime.timezone.utc)
        return value if tz else value.replace(tzinfo=None)


class BriefingScheduleTests(unittest.TestCase):
    def test_afternoon_block_has_sixty_minute_catch_up_window(self):
        with temporary_store() as con, \
                patch.object(briefing.datetime, "datetime", AfternoonDateTime), \
                patch.object(config, "BRIEFING_SCHEDULE", [("21:15", "Afternoon")]), \
                patch.object(briefing, "fetch_brief", return_value=brief_payload()), \
                patch.object(briefing, "build_thread", return_value=block_posts()), \
                patch("nbn.publisher.publish_thread", return_value=("DRAFT", "draft-block")):
            self.assertTrue(briefing.maybe_run(con))
            row = con.execute("SELECT story_key,mode FROM posts").fetchone()
        self.assertEqual(dict(row), {
            "story_key": "briefing:2026-08-31:afternoon", "mode": "DRAFT"
        })


class FixedDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 8, 31, 9, 10, tzinfo=datetime.timezone.utc)
        return value if tz else value.replace(tzinfo=None)


class AuditTests(unittest.TestCase):
    def test_audit_checks_only_published_or_possibly_published_modes(self):
        with temporary_store() as con:
            for mode in ("IMMEDIATE", "DRAFT", "UNCERTAIN", "FAILED", "TAPE"):
                store.log_post(con, mode.lower(), None, "primary", f"{mode} body",
                               "https://example.com", mode)
            checked = []

            def clean(row):
                checked.append(row["mode"])
                return {"verdict": "clean", "class_ok": True, "findings": [],
                        "source_drift": False}

            with patch.object(audit.datetime, "datetime", FixedDateTime), \
                    patch.object(audit, "_audit_one", side_effect=clean):
                self.assertTrue(audit.maybe_run(con))

            self.assertEqual(set(checked), {"IMMEDIATE", "UNCERTAIN"})
            saved = json.loads(store.kv_get(con, "audit:last"))
            self.assertEqual(saved["posts_checked"], 2)

    def test_material_correction_is_staged_never_immediate(self):
        row = {"id": 7}
        with patch.object(publisher_typefully, "publish_thread", return_value=(
                publisher_typefully.PublishOutcome.STAGED, "draft-7")) as publish:
            audit._stage_correction(row, "CORRECTION: Test.")
        self.assertFalse(publish.call_args.kwargs["immediate"])

    def test_audit_uses_confirmation_time_for_late_published_draft(self):
        with temporary_store() as con:
            store.log_post(con, "late", None, "primary", "NEW: Late publication.",
                           "https://example.com", "IMMEDIATE")
            con.execute(
                "UPDATE posts SET created=?,confirmed_at=? WHERE story_key='late'",
                (time.time() - 3 * 86400, time.time()),
            )
            con.commit()
            checked = []

            def clean(row):
                checked.append(row["story_key"])
                return {"verdict": "clean", "class_ok": True, "findings": [],
                        "source_drift": False}

            with patch.object(audit.datetime, "datetime", FixedDateTime), \
                    patch.object(audit, "_audit_one", side_effect=clean):
                self.assertTrue(audit.maybe_run(con))
            self.assertEqual(checked, ["late"])


class ReportTests(unittest.TestCase):
    def test_desk_uses_distinct_lifecycle_actions(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            for mode in ("IMMEDIATE", "DRAFT", "UNCERTAIN", "FAILED", "TAPE"):
                store.log_post(con, mode.lower(), None, "primary", f"{mode} body",
                               "https://example.com", mode)
            html = report.render(con)

        self.assertEqual(html.count("AWAITING PUBLICATION"), 1)
        self.assertEqual(html.count("VERIFY ON TYPEFULLY / X"), 1)
        self.assertEqual(html.count("PUBLISH FAILED"), 1)
        self.assertEqual(html.count("TAPE ONLY"), 1)
        self.assertNotIn("POST FAILED", html)
        self.assertIn("1 published", html)
        self.assertIn("1 uncertain", html)
        self.assertIn("1 failed", html)
        self.assertIn("1 tape", html)
        self.assertIn("5</b><span>outputs created", html)

    def test_desk_shows_original_and_selected_source_metadata(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            con.execute(
                "INSERT INTO source_resolutions(item_hash,story_key,resolved_at,mode,status,"
                "original_url,original_source,original_source_id,original_tier,selected_url,"
                "selected_source,selected_source_id,selected_tier,selected_category,"
                "selected_independence_key,selected_ownership_key,originality,support_verdict,"
                "receipt_eligible,corroboration_eligible,primary_artifact_url,"
                "primary_artifact_fingerprint,content_fingerprint,selected_text,"
                "earliest_coverage_date,note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                ("item-1", "story", 1, "enforce", "selected",
                 "https://cryptoslate.com/a", "CryptoSlate", "cryptoslate", "t3",
                 "https://reuters.com/a", "Reuters", "reuters", "t1", "reporting",
                 "reuters", "reuters", "original_reporting", 1, 1, 1, "", "", "fp",
                 "Bitcoin source", None, "Reuters directly supports the story"))
            con.commit()
            store.log_post(con, "story", "item-1", "secondary", "NEW: Bitcoin source.",
                           "https://reuters.com/a", "DRAFT", resolution_id="item-1")
            html = report.render(con)
        self.assertIn("CryptoSlate", html)
        self.assertIn("Reuters", html)
        self.assertIn("t3", html)
        self.assertIn("t1", html)
        self.assertIn("selected", html)
        self.assertIn("Reuters directly supports the story", html)
        self.assertIn("eligible evidence: 0", html)

    def test_desk_shows_last_run_decisions_and_escapes_item_text(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            pending = store.upsert_new_items(con, [{
                "source": "Example", "title": "Bitcoin <script>alert(1)</script>",
                "url": "https://example.com/decision", "published": "", "summary": "",
            }])
            store.set_status(con, pending[0]["url_hash"], "skipped", "desk-test",
                             "outside charter")
            store.record_decision_run(
                con, pending,
                [{**pending[0], "action": "skip", "story_key": "desk-test",
                  "reason": "not material"}],
                {"fetched": 10, "new": 1, "considered": 1, "pending": 1}, time.time(),
            )
            html = report.render(con)
        self.assertIn("Last decision run", html)
        self.assertIn("triage · skip", html)
        self.assertIn("final · skipped", html)
        self.assertIn("Decision: not material", html)
        self.assertIn("Bitcoin &lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_held_freshness_item_has_specific_label_and_operator_controls(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            pending = store.upsert_new_items(con, [{
                "source": "Bitcoin Magazine", "title": "Strive buys bitcoin",
                "url": "https://example.com/strive", "published": "", "summary": "",
            }])
            store.set_status(con, pending[0]["url_hash"], "held", "strive-buy",
                             "stale event: dated 2026-08-28, window 6h")
            store.record_decision_run(
                con, pending,
                [{**pending[0], "action": "draft", "story_key": "strive-buy",
                  "reason": "material bitcoin treasury purchase news"}],
                {"fetched": 1, "new": 1, "considered": 1, "pending": 1}, time.time(),
            )
            html = report.render(con)
        self.assertIn("final · held · freshness", html)
        self.assertIn("STAGE DRAFT", html)
        self.assertIn("DISMISS", html)
        self.assertIn("method=post action='/item-action'", html)

    def test_source_hold_offers_dismiss_but_not_stage(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            row = store.upsert_new_items(con, [{
                "source": "Example", "title": "Thin item", "url": "https://example.com/thin",
                "published": "", "summary": "",
            }])[0]
            store.set_status(con, row["url_hash"], "held", "thin",
                             "source policy: selected receipt text unavailable")
            html = report.render(con)
        self.assertNotIn("STAGE DRAFT", html)
        self.assertIn("DISMISS", html)

    def test_skipped_headline_is_exact_when_reason_table_is_limited(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            for index in range(16):
                row = store.upsert_new_items(con, [{
                    "source": "Example", "title": f"Skipped {index}",
                    "url": f"https://example.com/skipped-{index}", "published": "",
                }])[0]
                store.set_status(con, row["url_hash"], "skipped", note=f"reason {index}")
            html = report.render(con)
        self.assertIn("16 skipped", html)
        self.assertIn("16 · top reasons", html)
        self.assertNotIn("= 16 seen", html)
        self.assertIn("intake: 16 seen · 16 evaluated", html)


if __name__ == "__main__":
    unittest.main()
