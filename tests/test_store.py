import unittest
import datetime

from nbn import store
from tests.support import item, temporary_store


class StoreTests(unittest.TestCase):
    def test_url_deduplication(self):
        with temporary_store() as con:
            first = store.upsert_new_items(con, [item()])
            second = store.upsert_new_items(con, [item()])
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])

    def test_story_corroboration_counts_distinct_publishers(self):
        with temporary_store() as con:
            rows = [
                item("https://one.example/story", source="Outlet One"),
                item("https://two.example/story", source="Outlet Two"),
                item("https://one.example/other", source="Outlet One"),
            ]
            inserted = store.upsert_new_items(con, rows)
            for row in inserted:
                store.set_status(con, row["url_hash"], "new", "same-story")
            self.assertEqual(store.corroboration_count(con, "same-story"), 2)

    def test_post_log_preserves_backend_reference_in_legacy_column(self):
        with temporary_store() as con:
            store.log_post(con, "story", None, "primary", "NEW: Test.",
                           "https://example.com", "TAPE", "backend-ref")
            row = con.execute("SELECT nuelink_id FROM posts").fetchone()
            self.assertEqual(row["nuelink_id"], "backend-ref")

    def test_coverage_predicates_separate_reader_handled_and_produced(self):
        expectations = {
            "IMMEDIATE": (True, True, True),
            "DRAFT": (False, True, True),
            "UNCERTAIN": (True, True, True),
            "FAILED": (False, False, True),
            "TAPE": (False, False, True),
        }
        with temporary_store() as con:
            for mode, expected in expectations.items():
                key = mode.lower()
                store.log_post(con, key, None, "primary", "NEW: Test.",
                               "https://example.com", mode)
                actual = (store.story_reader_covered(con, key),
                          store.story_handled(con, key),
                          store.story_produced(con, key))
                self.assertEqual(actual, expected, mode)

    def test_recent_story_keys_are_reader_coverage_only(self):
        with temporary_store() as con:
            for mode in ("IMMEDIATE", "DRAFT", "UNCERTAIN", "FAILED", "TAPE"):
                store.log_post(con, mode.lower(), None, "primary", "NEW: Test.",
                               "https://example.com", mode)
            self.assertEqual(set(store.recent_story_keys(con)), {"immediate", "uncertain"})

    def test_day_summary_exposes_every_output_mode(self):
        with temporary_store() as con:
            for mode in ("IMMEDIATE", "DRAFT", "UNCERTAIN", "FAILED", "TAPE"):
                store.log_post(con, mode.lower(), None, "primary", "NEW: Test.",
                               "https://example.com", mode)
            from zoneinfo import ZoneInfo
            day = datetime.datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")
            summary = store.day_summary(con, day)
            self.assertEqual(
                {k: summary[k] for k in ("published", "drafts", "uncertain", "failed", "tape")},
                {"published": 1, "drafts": 1, "uncertain": 1, "failed": 1, "tape": 1},
            )

    def test_time_boundaries_are_deterministic(self):
        utc = datetime.timezone.utc
        weekday_active = datetime.datetime(2026, 8, 31, 16, 0, tzinfo=utc)  # noon ET
        weekend = datetime.datetime(2026, 8, 30, 16, 0, tzinfo=utc)
        self.assertEqual(store.current_max_age_hours(weekday_active), 2.5)
        self.assertEqual(store.current_max_age_hours(weekend), 6)
        self.assertFalse(store.is_stale("2026-08-31T14:00:01Z", 2, weekday_active))
        self.assertTrue(store.is_stale("2026-08-31T13:59:59Z", 2, weekday_active))
        same_day = datetime.datetime(2026, 8, 31, 23, 59, tzinfo=utc)
        self.assertFalse(store.event_is_stale("2026-08-31", 2.5, same_day))
        next_day_late = datetime.datetime(2026, 9, 1, 3, 0, tzinfo=utc)
        self.assertTrue(store.event_is_stale("2026-08-31", 2.5, next_day_late))


if __name__ == "__main__":
    unittest.main()
