import datetime
import json
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


class ReportTests(unittest.TestCase):
    def test_desk_uses_distinct_lifecycle_actions(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-token"):
            for mode in ("IMMEDIATE", "DRAFT", "UNCERTAIN", "FAILED", "TAPE"):
                store.log_post(con, mode.lower(), None, "primary", f"{mode} body",
                               "https://example.com", mode)
            html = report.render(con)

        self.assertEqual(html.count("TAP TO PUBLISH"), 1)
        self.assertEqual(html.count("VERIFY ON TYPEFULLY / X"), 1)
        self.assertEqual(html.count("PUBLISH FAILED"), 1)
        self.assertEqual(html.count("TAPE ONLY"), 1)
        self.assertNotIn("POST FAILED", html)
        self.assertIn("1 published", html)
        self.assertIn("1 uncertain", html)
        self.assertIn("1 failed", html)
        self.assertIn("1 tape", html)

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


if __name__ == "__main__":
    unittest.main()
