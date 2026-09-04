import unittest
from unittest.mock import patch

from nbn import config, publisher, publisher_typefully as tf
from tests.support import temporary_store


class PublisherRouterTests(unittest.TestCase):
    def test_one_off_uses_clean_lead_and_source_reply(self):
        self.assertEqual(
            publisher.one_off_x_thread("  NEW: Test.  ", " https://example.com/story "),
            ["NEW: Test.", "Source: https://example.com/story"],
        )

    def test_no_backend_is_tape_not_failure(self):
        with temporary_store(), \
                patch.object(config, "TYPEFULLY_API_KEY", ""), \
                patch.object(config, "TYPEFULLY_SOCIAL_SET_ID", ""), \
                patch.object(config, "NUELINK_API_KEY", ""):
            mode, ref = publisher.publish(
                "NEW: Test.", "https://example.com", "primary")
        self.assertEqual((mode, ref), ("TAPE", None))

    def test_typefully_outcomes_map_to_lifecycle_modes(self):
        cases = {
            tf.PublishOutcome.CONFIRMED: "IMMEDIATE",
            tf.PublishOutcome.STAGED: "DRAFT",
            tf.PublishOutcome.FAILED: "FAILED",
            tf.PublishOutcome.UNCERTAIN: "UNCERTAIN",
        }
        for outcome, expected in cases.items():
            with self.subTest(outcome=outcome), temporary_store(), \
                    patch.object(config, "TYPEFULLY_API_KEY", "key"), \
                    patch.object(config, "TYPEFULLY_SOCIAL_SET_ID", "set"), \
                    patch.object(config, "AUTOPOST_ENABLED", True), \
                    patch.object(config, "AUTOPOST_CLASSES", {"primary"}), \
                    patch.object(tf, "publish_thread", return_value=(outcome, "ref")):
                mode, ref = publisher.publish(
                    "NEW: Test.", "https://example.com", "primary")
                self.assertEqual((mode, ref), (expected, "ref"))
                self.assertEqual(
                    tf.publish_thread.call_args.args[0],
                    ["NEW: Test.", "Source: https://example.com"],
                )

    def test_secondary_is_staged_even_when_autopost_is_enabled(self):
        with temporary_store(), \
                patch.object(config, "TYPEFULLY_API_KEY", "key"), \
                patch.object(config, "TYPEFULLY_SOCIAL_SET_ID", "set"), \
                patch.object(config, "AUTOPOST_ENABLED", True), \
                patch.object(config, "AUTOPOST_CLASSES", {"primary", "corroborated"}), \
                patch.object(tf, "publish_thread",
                             return_value=(tf.PublishOutcome.STAGED, "draft")):
            mode, _ = publisher.publish(
                "NEW: Test.", "https://example.com", "secondary")
            self.assertEqual(mode, "DRAFT")

    def test_observe_mode_forces_draft_even_for_primary_autopost(self):
        with patch.object(config, "SOURCE_POLICY_MODE", "observe"), \
                patch.object(config, "AUTOPOST_ENABLED", True), \
                patch.object(config, "AUTOPOST_CLASSES", {"primary"}), \
                patch.object(publisher, "_backend", return_value="typefully"), \
                patch.object(tf, "publish_thread", return_value=(
                    tf.PublishOutcome.STAGED, "draft-observe")) as publish:
            mode, _ = publisher.publish("NEW: Test.", "https://example.com", "primary")
            self.assertEqual(mode, "DRAFT")
            self.assertFalse(publish.call_args.kwargs["immediate"])
        self.assertFalse(publish.call_args.kwargs["immediate"])

    def test_operator_override_forces_draft_even_for_primary_autopost(self):
        with patch.object(config, "SOURCE_POLICY_MODE", "enforce"), \
                patch.object(config, "AUTOPOST_ENABLED", True), \
                patch.object(config, "AUTOPOST_CLASSES", {"primary"}), \
                patch.object(publisher, "_backend", return_value="typefully"), \
                patch.object(tf, "publish_thread", return_value=(
                    tf.PublishOutcome.STAGED, "draft-owner")) as publish:
            mode, _ = publisher.publish(
                "NEW: Test.", "https://example.com", "primary", force_draft=True)
        self.assertEqual(mode, "DRAFT")
        self.assertFalse(publish.call_args.kwargs["immediate"])

    def test_corroboration_promotes_existing_typefully_draft_in_place(self):
        with patch.object(config, "SOURCE_POLICY_MODE", "enforce"), \
                patch.object(config, "AUTOPOST_ENABLED", True), \
                patch.object(config, "AUTOPOST_CLASSES", {"primary", "corroborated"}), \
                patch.object(publisher, "_backend", return_value="typefully"), \
                patch.object(tf, "schedule_draft",
                             return_value=tf.PublishOutcome.CONFIRMED) as schedule:
            mode, ref = publisher.promote_draft("draft-9", "corroborated")
        self.assertEqual((mode, ref), ("IMMEDIATE", "draft-9"))
        schedule.assert_called_once_with("draft-9")


if __name__ == "__main__":
    unittest.main()
