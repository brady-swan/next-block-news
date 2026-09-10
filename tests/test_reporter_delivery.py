import json
import time
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

import httpx

from nbn import config, reporter_delivery as delivery, reporter_store as rs, store
from tests.support import temporary_store


class ReporterDeliveryTests(unittest.TestCase):
    def test_source_must_bind_successful_evidence(self):
        with temporary_store() as con, self.stack():
            shift = self.begin(con)
            with patch.object(delivery.httpx, "post") as post:
                for evidence in ({"url":"https://example.com/different","text":"Source"},
                                 {"url":"https://example.com/news","text":""},
                                 {"url":"https://example.com/news","text":"Loading","outcome":"evidence_failed"}):
                    with con:
                        con.execute("UPDATE reporter_records SET payload_json=?", (json.dumps(evidence),))
                    with self.assertRaisesRegex(ValueError,"successfully inspected"):
                        delivery.submit(con,shift_id=shift["shift_id"],generation=shift["generation"],submission_id="bound",payload=self.payload())
                post.assert_not_called()

    def test_duplicate_manual_baseline_under_another_key(self):
        with temporary_store() as con, self.stack():
            shift=self.begin(con)
            with con:
                con.execute("INSERT INTO posts(created,story_key,body,receipt_url,mode) VALUES (0,'manual-baseline:123',?,?,'DRAFT')",
                            (self.payload()["body"],self.payload()["source_url"]))
            with self.assertRaisesRegex(ValueError,"exact post"):
                delivery.submit(con,shift_id=shift["shift_id"],generation=shift["generation"],submission_id="dup",payload=self.payload())

    def begin(self, con):
        shift = rs.start(con, worker_id="test-worker", shift_id="test-shift")
        rs.record(con, shift_id=shift["shift_id"], record_id="evidence:one", kind="evidence",
                  sender="system", payload={"url": "https://example.com/news", "text": "A source."})
        return shift

    def payload(self):
        return {"event_key": "test-event", "body": "NEW: Bitcoin test.",
                "source_url": "https://example.com/news", "evidence_ids": ["evidence:one"],
                "self_review": "Read source, checked current coverage and copy."}

    def raw(self, body=None):
        return {"id": 123, "status": "draft", "social_set_id": config.TYPEFULLY_SOCIAL_SET_ID,
                "created_at": "2026-09-10T12:00:00Z", "updated_at": None,
                "platforms": {"x": {"enabled": True, "posts": [
                    {"text": body or "NEW: Bitcoin test.", "media_ids": []},
                    {"text": "Source: https://example.com/news", "media_ids": []}]}}}

    def stack(self):
        stack = ExitStack()
        stack.enter_context(patch.object(config, "OPERATING_MODE", "infrastructure"))
        stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", False))
        stack.enter_context(patch.object(delivery.publisher, "tape"))
        return stack

    def test_same_stable_id_creates_exact_draft_only_once(self):
        with temporary_store() as con, self.stack():
            shift = self.begin(con)
            response = Mock(); response.json.return_value = self.raw()
            with patch.object(delivery.httpx, "post", return_value=response) as post, \
                    patch.object(delivery.tf, "get_draft", return_value=self.raw()):
                args = dict(shift_id=shift["shift_id"], generation=shift["generation"],
                            submission_id="test-submission", payload=self.payload())
                first = delivery.submit(con, **args)
                second = delivery.submit(con, **args)
            self.assertEqual(first["state"], "staged")
            self.assertEqual(second["provider_ref"], "123")
            self.assertEqual(post.call_count, 1)
            self.assertNotIn("publish_at", post.call_args.kwargs["json"])
            self.assertEqual(con.execute("SELECT count(*) FROM posts").fetchone()[0], 1)
            with self.assertRaisesRegex(ValueError, "different content"):
                delivery.submit(con, **{**args, "payload": {**self.payload(), "body": "changed"}})

    def test_timeout_protects_submission_and_event_without_retry(self):
        with temporary_store() as con, self.stack():
            shift = self.begin(con)
            args = dict(shift_id=shift["shift_id"], generation=shift["generation"],
                        submission_id="uncertain-submission", payload=self.payload())
            with patch.object(delivery.httpx, "post", side_effect=httpx.ReadTimeout("lost")) as post:
                self.assertEqual(delivery.submit(con, **args)["state"], "uncertain")
                self.assertEqual(delivery.submit(con, **args)["state"], "uncertain")
                with self.assertRaisesRegex(ValueError, "uncertain delivery"):
                    delivery.submit(con, **{**args, "submission_id": "another-id"})
                post.assert_called_once()

    def test_cutoff_rechecked_immediately_before_post(self):
        with temporary_store() as con, self.stack():
            shift = self.begin(con)
            with patch.object(delivery.rs, "assert_active", side_effect=[shift, shift, ValueError("cutoff")]), \
                    patch.object(delivery.httpx, "post") as post:
                output = delivery.submit(con, shift_id=shift["shift_id"], generation=shift["generation"],
                                         submission_id="expired", payload=self.payload())
            self.assertEqual(output["state"], "failed")
            post.assert_not_called()

    def test_matching_id_after_cutoff_returns_known_outcome_not_new_post(self):
        with temporary_store() as con, self.stack():
            shift = self.begin(con)
            args = dict(shift_id=shift["shift_id"], generation=shift["generation"],
                        submission_id="once", payload=self.payload())
            with patch.object(delivery.httpx, "post", side_effect=httpx.ReadTimeout("lost")) as post:
                delivery.submit(con, **args)
                rs.stop(con, shift["shift_id"])
                self.assertEqual(delivery.submit(con, **args)["state"], "uncertain")
                post.assert_called_once()

    def test_owner_edited_draft_is_not_overwritten_or_duplicated(self):
        with temporary_store() as con, self.stack():
            shift = self.begin(con)
            with con:
                con.execute("INSERT INTO posts(created,story_key,body,mode,publisher_status) "
                            "VALUES (?,?,?,'DRAFT','draft')", (time.time(), "test-event", "Owner's revised copy"))
            with patch.object(delivery.httpx, "post") as post:
                with self.assertRaisesRegex(ValueError, "open draft"):
                    delivery.submit(con, shift_id=shift["shift_id"], generation=shift["generation"],
                                    submission_id="blocked", payload=self.payload())
            post.assert_not_called()
            self.assertEqual(con.execute("SELECT body FROM posts").fetchone()[0], "Owner's revised copy")

    def test_shift_start_retry_does_not_extend_cutoff(self):
        with temporary_store() as con:
            first = rs.start(con, worker_id="worker", shift_id="shift", now=time.time())
            again = rs.start(con, worker_id="worker", shift_id="shift", now=time.time() + 3600)
            self.assertEqual(first["cutoff_at"], again["cutoff_at"])
            with self.assertRaisesRegex(ValueError, "another reporting shift"):
                rs.start(con, worker_id="other", shift_id="other")

    def test_record_retry_checks_sender_and_payload(self):
        with temporary_store() as con:
            args = dict(shift_id="shift", record_id="message:1", kind="message", sender="reporter", payload={"text": "hi"})
            self.assertEqual(rs.record(con, **args)["id"], rs.record(con, **args)["id"])
            with self.assertRaisesRegex(ValueError, "different content"):
                rs.record(con, **{**args, "sender": "owner"})
