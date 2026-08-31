import unittest
import datetime
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from nbn import config, source_policy, store, verify
from scripts import backup_db
from tests.support import item, temporary_store


class StoreTests(unittest.TestCase):
    def test_url_deduplication(self):
        with temporary_store() as con:
            first = store.upsert_new_items(con, [item()])
            second = store.upsert_new_items(con, [item()])
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])

    def test_qualified_evidence_is_cross_cycle_fresh_and_independent(self):
        with temporary_store() as con:
            now = time.time()
            rows = [
                ("one", "owner-one", "artifact-a", "content-a", now),
                ("two", "owner-two", "artifact-b", "content-b", now + 1),
                # Same owner and same artifact cannot add a chain.
                ("two-copy", "owner-two", "artifact-a", "content-c", now + 2),
                # Expired independent evidence is ignored.
                ("old", "owner-old", "artifact-old", "content-old", now - 26 * 3600),
            ]
            for source_id, owner, artifact, content, observed in rows:
                con.execute(
                    "INSERT INTO source_evidence(item_hash,story_key,observed_at,url,source_id,"
                    "source_name,tier,category,independence_key,ownership_key,originality,"
                    "support_verdict,receipt_eligible,corroboration_eligible,"
                    "primary_artifact_fingerprint,content_fingerprint)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (source_id, "story", observed, f"https://{source_id}.example", source_id,
                     source_id, "t1", "reporting", owner, owner, "original_reporting",
                     1, 1, 1, artifact, content))
            con.commit()
            self.assertEqual(store.qualified_evidence_count(con, "story", 24), 2)

    def test_resolution_evidence_replacement_is_atomic_on_insert_failure(self):
        def resolution(url, evidence_urls):
            ref = source_policy.SourceRef(
                url.rsplit("/", 1)[-1], "Source", "t2", "reporting", url, url,
                "reporting", url, url.split("/")[2], "", "test")
            evidence = tuple(
                verify.EvidenceCandidate(
                    source_policy.SourceRef(
                        ev_url.rsplit("/", 1)[-1], "Evidence", "t2", "reporting",
                        ev_url, ev_url, "reporting", ev_url, ev_url.split("/")[2], "", "test"),
                    "original_reporting", True, True, True, "", f"fp-{index}")
                for index, ev_url in enumerate(evidence_urls)
            )
            return verify.ResolutionResult(
                "atomic-item", "atomic-story", "Original", ref, ref, "Bitcoin source",
                "selected", True, "original_reporting", True, True, "", "", "fp",
                None, "atomic test", evidence)

        with temporary_store() as con:
            prior = resolution("https://prior.example/story", ["https://prior.example/evidence"])
            store.persist_resolution(con, prior, "enforce")
            con.execute(
                "CREATE TRIGGER fail_second_evidence BEFORE INSERT ON source_evidence "
                "WHEN NEW.url LIKE '%fail-second%' BEGIN SELECT RAISE(ABORT, 'forced'); END"
            )
            replacement = resolution(
                "https://new.example/story",
                ["https://new.example/first", "https://new.example/fail-second"],
            )
            with self.assertRaises(sqlite3.IntegrityError):
                store.persist_resolution(con, replacement, "enforce")
            row = store.resolution_for_item(con, "atomic-item")
            evidence = store.evidence_for_item(con, "atomic-item")
            self.assertEqual(row["selected_url"], "https://prior.example/story")
            self.assertEqual([ev["url"] for ev in evidence], ["https://prior.example/evidence"])

    def test_near_copy_and_same_entity_x_evidence_collapse(self):
        body = ("Reuters reported that the Securities and Exchange Commission approved "
                "the Bitcoin exchange traded fund after commissioners voted on the "
                "proposed rule change. The order becomes effective immediately and "
                "applies to the named exchange.")
        wrapper = "Subscribe for updates. " + body + " Copyright Example Media."
        signatures = [source_policy.content_fingerprint(body),
                      source_policy.content_fingerprint(wrapper),
                      source_policy.content_fingerprint("Coinbase announced its own Bitcoin action")]
        owners = ["wire-owner-a", "wire-owner-b", "coinbase", "coinbase"]
        contents = [signatures[0], signatures[1], signatures[2],
                    source_policy.content_fingerprint("Different Coinbase website wording")]
        with temporary_store() as con:
            for index, (owner, content) in enumerate(zip(owners, contents)):
                con.execute(
                    "INSERT INTO source_evidence(item_hash,story_key,observed_at,url,source_id,"
                    "source_name,tier,category,independence_key,ownership_key,originality,"
                    "support_verdict,receipt_eligible,corroboration_eligible,"
                    "primary_artifact_fingerprint,content_fingerprint)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (f"item-{index}", "collapse", time.time() + index,
                     f"https://source-{index}.example", f"source-{index}", f"Source {index}",
                     "t2", "reporting", f"source-{index}", owner, "original_reporting",
                     1, 1, 1, "", content))
            con.commit()
            # Two wire wrappers are one chain; Coinbase X + site are one more chain.
            self.assertEqual(store.qualified_evidence_count(con, "collapse"), 2)

    def test_cycle_lease_is_cross_connection_owner_scoped_and_recoverable(self):
        with temporary_store() as first:
            second = store.connect()
            try:
                self.assertTrue(store.acquire_cycle_lease(first, "owner-a", now=100, ttl_seconds=10))
                self.assertFalse(store.acquire_cycle_lease(second, "owner-b", now=105, ttl_seconds=10))
                self.assertFalse(store.renew_cycle_lease(second, "owner-b", now=105))
                self.assertFalse(store.release_cycle_lease(second, "owner-b"))
                self.assertTrue(store.acquire_cycle_lease(second, "owner-b", now=111, ttl_seconds=10))
                self.assertFalse(store.release_cycle_lease(first, "owner-a"))
                self.assertTrue(store.release_cycle_lease(second, "owner-b"))
            finally:
                second.close()

    def test_legacy_database_migrates_additively(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            legacy = sqlite3.connect(path)
            legacy.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, created REAL, "
                           "story_key TEXT, item_hash TEXT, class TEXT, body TEXT, "
                           "receipt_url TEXT, mode TEXT, nuelink_id TEXT)")
            legacy.commit()
            legacy.close()
            with patch.object(config, "DATA_DIR", Path(directory)), \
                    patch.object(config, "DB_PATH", path):
                con = store.connect()
                try:
                    columns = {row["name"] for row in con.execute("PRAGMA table_info(posts)")}
                    self.assertTrue(set(store.POST_COLUMNS).issubset(columns))
                    self.assertIsNotNone(con.execute(
                        "SELECT name FROM sqlite_master WHERE name='idx_posts_publisher_ref'").fetchone())
                    self.assertIsNotNone(con.execute(
                        "SELECT name FROM sqlite_master WHERE name='source_resolutions'").fetchone())
                finally:
                    con.close()

    def test_online_backup_is_integrity_checked(self):
        with temporary_store() as con:
            store.upsert_new_items(con, [item()])
            target = backup_db.backup()
            self.assertTrue(target.exists())
            backed_up = sqlite3.connect(target)
            try:
                self.assertEqual(backed_up.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(backed_up.execute("SELECT COUNT(*) FROM items").fetchone()[0], 1)
            finally:
                backed_up.close()

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

    def test_recent_story_keys_uses_confirmed_publication_time(self):
        with temporary_store() as con:
            store.log_post(con, "published-late", None, "primary", "NEW: Test.",
                           "https://example.com", "IMMEDIATE")
            con.execute(
                "UPDATE posts SET created=?,confirmed_at=? WHERE story_key='published-late'",
                (time.time() - 10 * 86400, time.time()),
            )
            con.commit()
            self.assertIn("published-late", store.recent_story_keys(con, days=3))

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
            self.assertEqual(summary["outputs_created"], 5)

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
