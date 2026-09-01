import unittest
from unittest.mock import Mock, patch

import httpx

from nbn import publisher_typefully as tf


def response(payload):
    result = Mock()
    result.raise_for_status.return_value = None
    result.json.return_value = payload
    return result


class TypefullyTests(unittest.TestCase):
    @patch.object(tf.httpx, "get")
    def test_published_list_is_normalized_and_malformed_records_are_skipped(self, get):
        get.return_value = response({"results": [
            {"id": 42, "status": "published",
             "created_at": "2026-08-31T12:00:00Z",
             "published_at": "2026-08-31T12:05:00Z",
             "x_published_url": "https://x.com/nextblocknews_/status/42",
             "preview": "NEW: Bitcoin test.", "draft_title": "Bitcoin test"},
            {"id": 43, "status": "published", "published_at": "not-a-date"},
            {"id": 44, "status": "draft", "published_at": "2026-08-31T12:05:00Z"},
        ]})
        rows = tf.list_published()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "42")
        self.assertEqual(rows[0]["public_url"], "https://x.com/nextblocknews_/status/42")
        self.assertEqual(rows[0]["preview"], "NEW: Bitcoin test.")
        self.assertEqual(get.call_args.kwargs["params"]["status"], "published")

    def test_public_x_url_rejects_credentials_and_unrelated_hosts(self):
        self.assertEqual(tf._public_x_url("https://user:pass@x.com/status/1"), "")
        self.assertEqual(tf._public_x_url("https://x.com.evil.example/status/1"), "")
        self.assertEqual(tf._public_x_url("javascript:alert(1)"), "")

    @patch.object(tf.httpx, "post")
    def test_human_draft_is_staged(self, post):
        post.return_value = response({"id": "draft-1"})
        outcome, ref = tf._create(["copy"], immediate=False)
        self.assertIs(outcome, tf.PublishOutcome.STAGED)
        self.assertEqual(ref, "draft-1")

    @patch.object(tf, "_confirm", return_value=tf.PublishOutcome.CONFIRMED)
    @patch.object(tf.httpx, "post")
    def test_scheduled_post_requires_confirmation(self, post, confirm):
        post.return_value = response({"id": "draft-2"})
        outcome, ref = tf._create(["copy"], immediate=True)
        self.assertIs(outcome, tf.PublishOutcome.CONFIRMED)
        self.assertEqual(ref, "draft-2")
        confirm.assert_called_once_with("draft-2")

    @patch.object(tf.time, "sleep", return_value=None)
    @patch.object(tf.httpx, "get")
    def test_confirmation_timeout_is_uncertain(self, get, _sleep):
        get.return_value = response({"publish_state": "scheduled"})
        self.assertIs(tf._confirm("draft-3", attempts=2), tf.PublishOutcome.UNCERTAIN)
        self.assertEqual(get.call_count, 2)

    @patch.object(tf.time, "sleep", return_value=None)
    @patch.object(tf.httpx, "get")
    def test_explicit_terminal_state_is_failed(self, get, _sleep):
        get.return_value = response({"publish_state": "failed"})
        self.assertIs(tf._confirm("draft-4", attempts=2), tf.PublishOutcome.FAILED)
        self.assertEqual(get.call_count, 1)

    @patch.object(tf, "_create", return_value=(tf.PublishOutcome.UNCERTAIN, "draft-5"))
    def test_uncertain_create_never_retries(self, create):
        outcome, ref = tf.publish_thread(["copy https://example.com"], immediate=True)
        self.assertIs(outcome, tf.PublishOutcome.UNCERTAIN)
        self.assertEqual(ref, "draft-5")
        self.assertEqual(create.call_count, 1)

    @patch.object(tf, "_create")
    def test_url_policy_fallback_requires_definitive_rejection(self, create):
        create.side_effect = [
            (tf.PublishOutcome.FAILED, "403: Adding URLs is blocked"),
            (tf.PublishOutcome.CONFIRMED, "draft-6"),
        ]
        outcome, ref = tf.publish_thread(["copy https://example.com"], immediate=True)
        self.assertIs(outcome, tf.PublishOutcome.CONFIRMED)
        self.assertEqual(ref, "draft-6")
        self.assertEqual(create.call_count, 2)
        self.assertNotIn("https://", create.call_args_list[1].args[0][0])

    @patch.object(tf.httpx, "post", side_effect=TimeoutError("response lost"))
    def test_transport_failure_during_create_is_uncertain(self, post):
        outcome, ref = tf._create(["copy"], immediate=True)
        self.assertIs(outcome, tf.PublishOutcome.UNCERTAIN)
        self.assertIn("response lost", ref)
        self.assertEqual(post.call_count, 1)

    @patch.object(tf.httpx, "post")
    def test_server_error_during_create_is_uncertain(self, post):
        request = httpx.Request("POST", "https://api.typefully.com/v2/drafts")
        response_ = httpx.Response(503, request=request, text="temporary failure")
        post.return_value = response_
        outcome, ref = tf._create(["copy"], immediate=True)
        self.assertIs(outcome, tf.PublishOutcome.UNCERTAIN)
        self.assertIn("503", ref)

    @patch.object(tf, "_confirm", return_value=tf.PublishOutcome.CONFIRMED)
    @patch.object(tf.httpx, "patch")
    def test_existing_draft_is_scheduled_in_place(self, patch_, confirm):
        patch_.return_value = response({"id": "draft-7", "status": "scheduled"})
        outcome = tf.schedule_draft("draft-7")
        self.assertIs(outcome, tf.PublishOutcome.CONFIRMED)
        self.assertIn("publish_at", patch_.call_args.kwargs["json"])
        confirm.assert_called_once_with("draft-7")

    @patch.object(tf.httpx, "delete")
    def test_delete_draft_accepts_deleted_and_already_missing(self, delete):
        deleted = response({})
        deleted.status_code = 204
        missing = response({})
        missing.status_code = 404
        delete.side_effect = [deleted, missing]
        self.assertTrue(tf.delete_draft("draft-8"))
        self.assertTrue(tf.delete_draft("draft-8"))


if __name__ == "__main__":
    unittest.main()
