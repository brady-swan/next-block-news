import json
import time
import unittest
from unittest.mock import patch

from nbn import brain, editor, store
from tests.support import temporary_store


class EditorTests(unittest.TestCase):
    def test_editor_failure_fails_open(self):
        with temporary_store() as con, \
                patch.object(brain, "_create", side_effect=RuntimeError("offline")):
            result = editor.review(
                "NEW: Bitcoin test.",
                {"class": "primary", "source": "Official", "title": "Test"}, con,
            )
        self.assertEqual(result["verdict"], "publish")
        self.assertEqual(result["post"], "NEW: Bitcoin test.")
        self.assertIn("editor error", result["reason"])

    def test_recent_feed_includes_only_relevant_lifecycle_modes(self):
        with temporary_store() as con:
            for mode in ("IMMEDIATE", "DRAFT", "UNCERTAIN", "FAILED", "TAPE"):
                store.log_post(con, mode.lower(), None, "primary", f"{mode} body",
                               "https://example.com", mode)

            captured = {}

            def fake_create(_model, _system, user, **_kwargs):
                captured.update(json.loads(user))
                return object()

            with patch.object(brain, "_create", side_effect=fake_create), \
                    patch.object(brain, "_json_from", return_value={
                        "verdict": "publish", "post": "NEW: Candidate.", "reason": "clean",
                    }):
                editor.review("NEW: Candidate.", {
                    "class": "primary", "source": "Official", "title": "Candidate",
                    "_coverage_action": "draft",
                }, con)

        modes = {entry["post"].split()[0] for entry in captured["recent_feed_newest_first"]}
        self.assertEqual(modes, {"IMMEDIATE", "DRAFT", "UNCERTAIN"})
        self.assertEqual(captured["coverage_action"], "draft")

    def test_recent_feed_orders_published_rows_by_confirmation_time(self):
        with temporary_store() as con:
            store.log_post(con, "published", None, "primary", "PUBLISHED body",
                           "https://example.com", "IMMEDIATE")
            store.log_post(con, "draft", None, "primary", "DRAFT body",
                           "https://example.com", "DRAFT")
            con.execute(
                "UPDATE posts SET created=?,confirmed_at=? WHERE story_key='published'",
                (time.time() - 86400, time.time()),
            )
            con.execute(
                "UPDATE posts SET created=? WHERE story_key='draft'", (time.time() - 60,))
            con.commit()
            captured = {}

            def fake_create(_model, _system, user, **_kwargs):
                captured.update(json.loads(user))
                return object()

            with patch.object(brain, "_create", side_effect=fake_create), \
                    patch.object(brain, "_json_from", return_value={
                        "verdict": "publish", "post": "NEW: Candidate.", "reason": "clean",
                    }):
                editor.review("NEW: Candidate.", {
                    "class": "primary", "source": "Official", "title": "Candidate",
                }, con)

            self.assertEqual(captured["recent_feed_newest_first"][0]["post"],
                             "PUBLISHED body")
            self.assertLess(captured["recent_feed_newest_first"][0]["hours_ago"], 0.1)


if __name__ == "__main__":
    unittest.main()
