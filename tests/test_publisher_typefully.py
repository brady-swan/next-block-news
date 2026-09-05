import unittest
from unittest.mock import Mock, patch

import httpx

from nbn import publisher_typefully as tf


def response(payload):
    result = Mock()
    result.status_code = 200
    result.raise_for_status.return_value = None
    result.json.return_value = payload
    return result


class TypefullyTests(unittest.TestCase):
    @patch.object(tf.httpx, "patch")
    @patch.object(tf, "get_draft")
    def test_replace_draft_changes_only_text_and_preserves_other_x_fields(self, get_draft,
                                                                         patch_http):
        prior = {
            "id": "42", "social_set_id": "set", "status": "draft",
            "platforms": {"x": {"enabled": True, "settings": {"reply": "all"},
                                "posts": [{"text": "old", "media_ids": ["m1"],
                                           "quote_post_url": "https://x.com/a/status/1",
                                           "subscribers_only": False,
                                           "paid_partnership": False,
                                           "made_with_ai": True,
                                           "hide_link_preview": True}]}},
        }
        desired = {**prior, "platforms": {"x": {**prior["platforms"]["x"],
                                                   "posts": [{**prior["platforms"]["x"]["posts"][0],
                                                              "text": "new"}]}}}
        get_draft.side_effect = [prior, desired]
        patch_http.return_value = response({"id": "42"})
        with patch.object(tf.config, "TYPEFULLY_SOCIAL_SET_ID", "set"):
            outcome, ref = tf.replace_draft("42", ["old"], ["new"])
        self.assertIs(outcome, tf.PublishOutcome.STAGED)
        self.assertEqual(ref, "42")
        body = patch_http.call_args.kwargs["json"]
        self.assertEqual(body["platforms"]["x"]["posts"][0]["media_ids"], ["m1"])
        self.assertFalse(body["platforms"]["x"]["posts"][0]["subscribers_only"])
        self.assertFalse(body["platforms"]["x"]["posts"][0]["paid_partnership"])
        self.assertTrue(body["platforms"]["x"]["posts"][0]["made_with_ai"])
        self.assertTrue(body["platforms"]["x"]["posts"][0]["hide_link_preview"])
        self.assertNotIn("draft_title", body)
        self.assertNotIn("force_overwrite_comments", body)

    @patch.object(tf.httpx, "patch")
    @patch.object(tf, "get_draft")
    def test_replace_draft_still_rejects_unknown_post_fields(self, get_draft,
                                                             patch_http):
        get_draft.return_value = {
            "id": "42", "social_set_id": "set", "status": "draft",
            "platforms": {"x": {"enabled": True, "posts": [
                {"text": "old", "future_unreviewed_field": True},
            ]}},
        }
        with patch.object(tf.config, "TYPEFULLY_SOCIAL_SET_ID", "set"):
            outcome, reason = tf.replace_draft("42", ["old"], ["new"])
        self.assertIs(outcome, tf.PublishOutcome.FAILED)
        self.assertEqual(reason, "unexpected_post_structure")
        patch_http.assert_not_called()

    @patch.object(tf.httpx, "patch")
    @patch.object(tf, "get_draft")
    def test_replace_draft_migrates_exact_legacy_one_post_to_source_reply(self, get_draft,
                                                                         patch_http):
        legacy = "old copy\n\nhttps://example.com/old"
        prior = {
            "id": "42", "social_set_id": "set", "status": "draft",
            "platforms": {"x": {"enabled": True, "settings": {"reply": "all"},
                                "posts": [{"text": legacy, "media_ids": ["m1"],
                                           "subscribers": False}]}},
        }
        desired_texts = ["updated copy", "Source: https://example.com/new"]
        confirmed = {
            **prior,
            "platforms": {"x": {
                **prior["platforms"]["x"],
                "posts": [
                    {"text": desired_texts[0], "media_ids": ["m1"],
                     "subscribers": False},
                    {"text": desired_texts[1]},
                ],
            }},
        }
        get_draft.side_effect = [prior, confirmed]
        patch_http.return_value = response({"id": "42"})
        with patch.object(tf.config, "TYPEFULLY_SOCIAL_SET_ID", "set"):
            outcome, ref = tf.replace_draft(
                "42", ["old copy", "Source: https://example.com/old"],
                desired_texts, alternate_prior_threads=[[legacy]],
            )
        self.assertIs(outcome, tf.PublishOutcome.STAGED)
        self.assertEqual(ref, "42")
        posts = patch_http.call_args.kwargs["json"]["platforms"]["x"]["posts"]
        self.assertEqual(posts, confirmed["platforms"]["x"]["posts"])

    @patch.object(tf.httpx, "patch")
    @patch.object(tf, "get_draft")
    def test_replace_draft_does_not_migrate_owner_edited_legacy_post(self, get_draft,
                                                                    patch_http):
        get_draft.return_value = {
            "id": "42", "social_set_id": "set", "status": "draft",
            "platforms": {"x": {"enabled": True,
                                  "posts": [{"text": "owner changed this"}]}},
        }
        with patch.object(tf.config, "TYPEFULLY_SOCIAL_SET_ID", "set"):
            outcome, reason = tf.replace_draft(
                "42", ["old copy", "Source: https://example.com/old"],
                ["new copy", "Source: https://example.com/new"],
                alternate_prior_threads=[[
                    "old copy\n\nhttps://example.com/old"
                ]],
            )
        self.assertIs(outcome, tf.PublishOutcome.FAILED)
        self.assertEqual(reason, "remote_modified")
        patch_http.assert_not_called()

    @patch.object(tf, "get_draft")
    def test_replace_draft_freezes_comment_marked_or_scheduled_output(self, get_draft):
        get_draft.return_value = {
            "id": "42", "status": "draft", "comments": [{"id": "c"}],
            "platforms": {"x": {"enabled": True, "posts": [{"text": "old"}]}},
        }
        outcome, reason = tf.replace_draft("42", ["old"], ["new"])
        self.assertIs(outcome, tf.PublishOutcome.FAILED)
        self.assertEqual(reason, "comment_marked")
        get_draft.return_value = {
            "id": "42", "status": "scheduled",
            "platforms": {"x": {"enabled": True, "posts": [{"text": "old"}]}},
        }
        outcome, reason = tf.replace_draft("42", ["old"], ["new"])
        self.assertIs(outcome, tf.PublishOutcome.FAILED)
        self.assertEqual(reason, "non_editable:scheduled")

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

    @patch.object(tf.httpx, "get")
    def test_analytics_posts_are_normalized_without_x_reads(self, get):
        get.return_value = response({"results": [{
            "draft_id": 42, "post_id": "2095",
            "created_at": "2026-09-02T12:00:00Z",
            "url": "https://x.com/nextblocknews_/status/2095",
            "metrics": {"impressions": 120, "engagement": {
                "total": 9, "likes": 4, "comments": 2, "shares": 3,
                "quotes": 1, "saves": 1, "profile_clicks": 2,
                "link_clicks": None,
            }},
        }]})
        rows = tf.list_analytics_posts()
        self.assertEqual(rows[0]["draft_id"], "42")
        self.assertEqual(rows[0]["performance"]["impressions"], 120)
        self.assertEqual(rows[0]["performance"]["likes"], 4)
        self.assertEqual(rows[0]["performance"]["reposts"], 3)
        self.assertIsNone(rows[0]["performance"]["link_clicks"])
        self.assertIn("/analytics/x/posts", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["params"]["include_replies"], "false")

    @patch.object(tf.httpx, "post")
    @patch.object(tf, "get_draft")
    def test_human_draft_is_staged_only_after_exact_content_readback(self, get_draft, post):
        post.return_value = response({"id": "draft-1"})
        get_draft.return_value = {
            "id": "draft-1", "status": "draft",
            "platforms": {"x": {"enabled": True, "posts": [
                {"text": "copy"}, {"text": "Source: https://example.com"},
            ]}},
        }
        outcome, ref = tf._create(
            ["copy", "Source: https://example.com"], immediate=False
        )
        self.assertIs(outcome, tf.PublishOutcome.STAGED)
        self.assertEqual(ref, "draft-1")
        get_draft.assert_called_once_with("draft-1")
        created_posts = post.call_args.kwargs["json"]["platforms"]["x"]["posts"]
        self.assertEqual(created_posts[0], {"text": "copy"})
        self.assertEqual(created_posts[1], {"text": "Source: https://example.com"})

    @patch.object(tf.httpx, "post")
    @patch.object(tf, "get_draft")
    def test_media_stays_on_lead_post_only(self, get_draft, post):
        post.return_value = response({"id": "draft-1"})
        get_draft.return_value = {
            "id": "draft-1", "status": "draft",
            "platforms": {"x": {"enabled": True, "posts": [
                {"text": "copy", "media_ids": ["media-1"]},
                {"text": "Source: https://example.com"},
            ]}},
        }
        outcome, _ = tf._create(
            ["copy", "Source: https://example.com"], immediate=False,
            lead_media_ids=["media-1"],
        )
        self.assertIs(outcome, tf.PublishOutcome.STAGED)
        created_posts = post.call_args.kwargs["json"]["platforms"]["x"]["posts"]
        self.assertEqual(created_posts[0]["media_ids"], ["media-1"])
        self.assertNotIn("media_ids", created_posts[1])

    @patch.object(tf.httpx, "post")
    @patch.object(tf, "get_draft")
    def test_human_draft_content_mismatch_is_uncertain(self, get_draft, post):
        post.return_value = response({"id": "draft-1"})
        get_draft.return_value = {
            "id": "draft-1", "status": "draft",
            "platforms": {"x": {"enabled": True, "posts": [{"text": "copy"}]}},
        }
        outcome, ref = tf._create(
            ["copy", "Source: https://example.com"], immediate=False
        )
        self.assertIs(outcome, tf.PublishOutcome.UNCERTAIN)
        self.assertEqual(ref, "draft-1")

    @patch.object(tf.httpx, "post")
    @patch.object(tf, "get_draft")
    def test_human_draft_readback_failure_after_create_is_uncertain(self, get_draft, post):
        post.return_value = response({"id": "draft-1"})
        request = httpx.Request("GET", "https://api.typefully.com/v2/drafts/draft-1")
        get_draft.side_effect = httpx.HTTPStatusError(
            "not yet visible", request=request,
            response=httpx.Response(404, request=request),
        )
        outcome, ref = tf._create(
            ["copy", "Source: https://example.com"], immediate=False
        )
        self.assertIs(outcome, tf.PublishOutcome.UNCERTAIN)
        self.assertEqual(ref, "draft-1")

    @patch.object(tf, "_confirm", return_value=tf.PublishOutcome.CONFIRMED)
    @patch.object(tf.httpx, "post")
    def test_scheduled_post_requires_confirmation(self, post, confirm):
        post.return_value = response({"id": "draft-2"})
        outcome, ref = tf._create(["copy"], immediate=True)
        self.assertIs(outcome, tf.PublishOutcome.CONFIRMED)
        self.assertEqual(ref, "draft-2")
        confirm.assert_called_once_with("draft-2", expected_texts=["copy"])

    @patch.object(tf.time, "sleep", return_value=None)
    @patch.object(tf.httpx, "get")
    def test_scheduled_confirmation_requires_exact_source_reply(self, get, _sleep):
        get.return_value = response({
            "publish_state": "scheduled",
            "platforms": {"x": {"enabled": True, "posts": [{"text": "copy"}]}},
        })
        outcome = tf._confirm(
            "draft-2", attempts=1,
            expected_texts=["copy", "Source: https://example.com"],
        )
        self.assertIs(outcome, tf.PublishOutcome.UNCERTAIN)
        self.assertEqual(get.call_count, 1)

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

    @patch.object(tf, "_create",
                  return_value=(tf.PublishOutcome.FAILED,
                                "403: Adding URLs is blocked"))
    def test_exact_payload_disables_content_changing_fallback(self, create):
        outcome, ref = tf.publish_thread(
            ["copy https://example.com"], immediate=True,
            allow_url_fallback=False,
        )
        self.assertIs(outcome, tf.PublishOutcome.FAILED)
        self.assertIn("URLs is blocked", ref)
        self.assertEqual(create.call_count, 1)

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

    @patch.object(tf.httpx, "get")
    def test_comment_page_is_get_only_normalized_and_hard_capped(self, get):
        comments = [{
            "id": f"c-{index}", "text": "x" * 2500,
            "created_at": "2026-09-04T12:00:00Z",
            "user": {"name": "a" * 200},
        } for index in range(25)]
        get.return_value = response({
            "results": [{
                "id": f"t-{index}", "platform": "x", "status": "unresolved",
                "selected_text": "s" * 1200, "comments": comments,
            } for index in range(60)],
            "next": "https://evil.example/steal",
        })
        with patch.object(tf.config, "TYPEFULLY_SOCIAL_SET_ID", "329191"):
            rows = tf.list_comment_threads("10626036", status="all", limit=999, offset=0)
        self.assertEqual(len(rows), tf.FEEDBACK_THREADS_PER_PAGE)
        self.assertEqual(len(rows[0]["comments"]), tf.FEEDBACK_COMMENTS_PER_THREAD)
        self.assertEqual(len(rows[0]["selected_text"]), tf.FEEDBACK_SELECTED_TEXT_CHARS)
        self.assertEqual(len(rows[0]["comments"][0]["text"]),
                         tf.FEEDBACK_COMMENT_TEXT_CHARS)
        self.assertEqual(len(rows[0]["comments"][0]["author"]), tf.FEEDBACK_AUTHOR_CHARS)
        self.assertEqual(get.call_count, 1)
        self.assertNotIn("evil.example", get.call_args.args[0])
        self.assertEqual(get.call_args.kwargs["params"], {
            "status": "all", "limit": 50, "offset": 0,
        })

    def test_comment_reader_rejects_untrusted_paths_and_pagination(self):
        for draft_id in ("../drafts/1", "1?next=https://evil.example", "0", ""):
            with self.subTest(draft_id=draft_id), self.assertRaises(ValueError):
                tf.list_comment_threads(draft_id)
        for kwargs in ({"status": "open"}, {"offset": "bad"}, {"limit": "bad"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                tf.list_comment_threads("10626036", **kwargs)

    @patch.object(tf.httpx, "get")
    def test_feedback_draft_read_excludes_markers_without_changing_get_draft(self, get):
        get.return_value = response({"id": 10626036})
        tf.get_draft_for_feedback("10626036")
        self.assertEqual(get.call_args.kwargs["params"], {
            "exclude_comment_markers": "true",
        })
        tf.get_draft("10626036")
        self.assertNotIn("params", get.call_args.kwargs)

    @patch.object(tf, "get_draft_for_feedback")
    @patch.object(tf, "list_comment_threads")
    @patch.object(tf, "list_recent_drafts")
    def test_feedback_collection_caps_drafts_pages_threads_and_display(
            self, recent, comments, display):
        recent.return_value = [{"id": str(index), "draft_title": "title"}
                               for index in range(1, 40)]
        comments.return_value = [{
            "id": "thread", "selected_text": "selected", "comments": [],
        }] * 50
        display.return_value = {
            "platforms": {"x": {"enabled": True, "posts": [{"text": "d" * 5000}]}},
        }
        rows = tf.collect_recent_feedback(status="unresolved", draft_limit=999)
        self.assertEqual(recent.call_args.kwargs["limit"], tf.FEEDBACK_DRAFT_LIMIT)
        self.assertEqual(len(rows), 1)
        self.assertEqual(sum(len(row["threads"]) for row in rows),
                         tf.FEEDBACK_TOTAL_THREADS)
        self.assertEqual(comments.call_count, tf.FEEDBACK_PAGES_PER_DRAFT)
        self.assertEqual(len(rows[0]["draft_text"]), tf.FEEDBACK_DRAFT_TEXT_CHARS)
        for call in comments.call_args_list:
            self.assertIn(call.kwargs["offset"], (0, tf.FEEDBACK_THREADS_PER_PAGE))


if __name__ == "__main__":
    unittest.main()
