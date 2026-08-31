import json
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


if __name__ == "__main__":
    unittest.main()
