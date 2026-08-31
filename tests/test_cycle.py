import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from nbn import brain, config, editor, main, publisher, sources, store, verify
from tests.support import item, temporary_store


class CycleTests(unittest.TestCase):
    def run_cycle(self, con, raw_items, verdicts, drafts=None, mode="DRAFT", auto=False,
                  editor_result=None, verify_result=None, article_text="Bitcoin test source"):
        drafts = drafts or [{"post": "NEW: Bitcoin test.", "event_date": None,
                              "needs_second_source": False}]

        def triage(items, _recent, _open):
            return [{**row, **verdicts[index]} for index, row in enumerate(items)]

        draft = Mock(side_effect=drafts)
        publish = Mock(return_value=(mode, "publisher-ref"))
        review = Mock(return_value=editor_result or {
            "verdict": "publish", "post": drafts[-1].get("post"), "reason": "clean",
        })
        corroborate = Mock(return_value=verify_result or {
            "confirmed": False, "reason": "not confirmed", "earliest_coverage_date": None,
        })
        with ExitStack() as stack:
            stack.enter_context(patch.object(sources, "fetch_feeds", return_value=raw_items))
            stack.enter_context(patch.object(sources, "fetch_edgar", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_perception", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_x", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_article_text",
                                             return_value=article_text))
            stack.enter_context(patch.object(sources, "chart_image", return_value=None))
            stack.enter_context(patch.object(brain, "triage", side_effect=triage))
            stack.enter_context(patch.object(brain, "draft", draft))
            stack.enter_context(patch.object(publisher, "publish", publish))
            stack.enter_context(patch.object(editor, "review", review))
            stack.enter_context(patch.object(verify, "web_corroborate", corroborate))
            stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", auto))
            stack.enter_context(patch.object(config, "AUTOPOST_CLASSES",
                                             {"primary", "corroborated"}))
            result = main.cycle(con)
        return result, draft, publish, review, corroborate

    def test_each_publisher_mode_gets_explicit_status_and_counter(self):
        expected = {
            "IMMEDIATE": ("posted", "posted"),
            "DRAFT": ("drafted", "drafted"),
            "UNCERTAIN": ("uncertain", "uncertain"),
            "FAILED": ("failed", "failed"),
            "TAPE": ("taped", "taped"),
        }
        for mode, (status, counter) in expected.items():
            with self.subTest(mode=mode), temporary_store() as con:
                result, *_ = self.run_cycle(
                    con, [item(url=f"https://example.com/{mode.lower()}")],
                    [{"action": "draft", "story_key": mode.lower(), "class": "primary"}],
                    mode=mode,
                )
                row = con.execute("SELECT status FROM items").fetchone()
                self.assertEqual(row["status"], status)
                self.assertEqual(result[counter], 1)

    def test_secondary_never_reaches_editor_autopost_gate(self):
        with temporary_store() as con:
            result, _draft, _publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "secondary-story",
                  "class": "secondary"}],
                mode="DRAFT", auto=True,
            )
            self.assertEqual(result["drafted"], 1)
            review.assert_not_called()

    def test_ordinary_draft_for_handled_exact_key_is_skipped(self):
        with temporary_store() as con:
            store.log_post(con, "same-story", None, "secondary", "NEW: Earlier.",
                           "https://example.com/earlier", "DRAFT")
            result, draft, publish, *_ = self.run_cycle(
                con, [item(url="https://example.com/new-source")],
                [{"action": "draft", "story_key": "same-story", "class": "secondary"}],
            )
            self.assertEqual(result["posted"], 0)
            draft.assert_not_called()
            publish.assert_not_called()
            row = con.execute("SELECT status, note FROM items").fetchone()
            self.assertEqual(row["status"], "skipped")
            self.assertEqual(row["note"], "story already handled")

    def test_update_without_exact_reader_coverage_is_held(self):
        with temporary_store() as con:
            result, draft, publish, *_ = self.run_cycle(
                con, [item()],
                [{"action": "update", "story_key": "missing-story", "class": "primary"}],
            )
            self.assertEqual(result["held"], 1)
            draft.assert_not_called()
            publish.assert_not_called()

    def test_valid_update_receives_exact_prior_copy(self):
        with temporary_store() as con:
            store.log_post(con, "same-story", None, "primary", "NEW: Earlier fact.",
                           "https://example.com/earlier", "IMMEDIATE")
            result, draft, publish, *_ = self.run_cycle(
                con, [item(url="https://example.com/development")],
                [{"action": "update", "story_key": "same-story", "class": "primary"}],
                drafts=[{"post": "UPDATE: Bitcoin test.", "event_date": None,
                         "needs_second_source": False}],
            )
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_args.kwargs["already_covered"], ["NEW: Earlier fact."])
            publish.assert_called_once()

    def test_update_lint_retry_preserves_prior_coverage(self):
        with temporary_store() as con:
            store.log_post(con, "same-story", None, "primary", "NEW: Earlier fact.",
                           "https://example.com/earlier", "IMMEDIATE")
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False},
                {"post": "UPDATE: Bitcoin test.", "event_date": None,
                 "needs_second_source": False},
            ]
            result, draft, publish, *_ = self.run_cycle(
                con, [item(url="https://example.com/development")],
                [{"action": "update", "story_key": "same-story", "class": "primary"}],
                drafts=drafts,
            )
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 2)
            self.assertEqual(draft.call_args_list[1].kwargs["already_covered"],
                             ["NEW: Earlier fact."])
            publish.assert_called_once()

    def test_secondary_needing_verification_is_held_on_failure(self):
        with temporary_store() as con:
            result, _draft, publish, _review, corroborate = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "verify-me", "class": "secondary"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": None,
                         "needs_second_source": True}],
            )
            self.assertEqual(result["held"], 1)
            corroborate.assert_called_once()
            publish.assert_not_called()

    def test_stale_event_is_held(self):
        with temporary_store() as con:
            result, _draft, publish, *_ = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "stale", "class": "primary"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": "2020-01-01",
                         "needs_second_source": False}],
            )
            self.assertEqual(result["held"], 1)
            publish.assert_not_called()

    def test_editor_spike_holds_autonomous_candidate(self):
        with temporary_store() as con:
            result, _draft, publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "spike", "class": "primary"}],
                auto=True,
                editor_result={"verdict": "spike", "post": None, "reason": "duplicate"},
            )
            self.assertEqual(result["held"], 1)
            review.assert_called_once()
            publish.assert_not_called()

    def test_two_distinct_sources_promote_secondary_to_corroborated(self):
        with temporary_store() as con:
            raw = [item("https://one.example/story", source="Outlet One"),
                   item("https://two.example/story", source="Outlet Two")]
            verdicts = [
                {"action": "draft", "story_key": "two-source", "class": "secondary"},
                {"action": "draft", "story_key": "two-source", "class": "secondary"},
            ]
            result, _draft, publish, review, corroborate = self.run_cycle(
                con, raw, verdicts, mode="IMMEDIATE", auto=True,
                verify_result={"confirmed": False, "reason": "", "earliest_coverage_date": None},
            )
            self.assertEqual(result["posted"], 1)
            self.assertEqual(publish.call_args.args[2], "corroborated")
            review.assert_called_once()
            corroborate.assert_called_once()

    def test_lint_failure_after_retry_is_held(self):
        with temporary_store() as con:
            invalid = {"post": "UPDATE: Bitcoin test.", "event_date": None,
                       "needs_second_source": False}
            result, draft, publish, *_ = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "bad-copy", "class": "primary"}],
                drafts=[invalid, invalid],
            )
            self.assertEqual(result["held"], 1)
            self.assertEqual(draft.call_count, 2)
            publish.assert_not_called()

    def test_editor_revision_is_relinted_and_published(self):
        with temporary_store() as con:
            revised = "NEW: Bitcoin test, tightened."
            result, _draft, publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "revise", "class": "primary"}],
                mode="IMMEDIATE", auto=True,
                editor_result={"verdict": "revise", "post": revised, "reason": "tighter"},
            )
            self.assertEqual(result["posted"], 1)
            review.assert_called_once()
            self.assertEqual(publish.call_args.args[0], revised)


if __name__ == "__main__":
    unittest.main()
