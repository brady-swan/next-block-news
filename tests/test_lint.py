import unittest

from nbn import lint


def check(post, source="Bitcoin 100", **item_fields):
    item = {"class": "primary", **item_fields}
    return lint.check(post, {"_source_text": source}, item)


class LintTests(unittest.TestCase):
    def test_clean_wire_atom_passes(self):
        self.assertEqual(check("NEW: Bitcoin test reached 100."), [])

    def test_number_must_appear_in_source(self):
        errors = check("NEW: Bitcoin test reached 101.")
        self.assertTrue(any(error.startswith("number not in source text: 101")
                            for error in errors))

    def test_question_outside_quotes_is_rejected(self):
        self.assertIn("question in post (the wire states facts, it does not speculate)",
                      check("NEW: Why is Bitcoin at 100?"))

    def test_second_tier_data_attribution_is_rejected(self):
        errors = check("NEW: Bitcoin flows reached 100, per BeInCrypto.")
        self.assertTrue(any("second-tier aggregator" in error for error in errors))

    def test_unverified_mention_is_rejected(self):
        errors = check("NEW: Bitcoin test reached 100, per @notverified.")
        self.assertIn("unverified handle: @notverified", errors)

    def test_first_coverage_requires_new_prefix(self):
        errors = check("UPDATE: Bitcoin test reached 100.", _coverage_action="draft")
        self.assertIn("first-coverage news post must start with 'NEW:'", errors)

    def test_promoted_first_coverage_still_requires_new_prefix(self):
        errors = check("UPDATE: Bitcoin test reached 100.", _coverage_action="draft",
                       **{"class": "corroborated"})
        self.assertIn("first-coverage news post must start with 'NEW:'", errors)

    def test_exact_update_requires_update_prefix(self):
        errors = check("NEW: Bitcoin test reached 100.", _coverage_action="update")
        self.assertIn("covered-story update must start with 'UPDATE:'", errors)

    def test_correct_update_prefix_passes(self):
        self.assertEqual(check("UPDATE: Bitcoin test reached 100.",
                               _coverage_action="update"), [])


if __name__ == "__main__":
    unittest.main()
