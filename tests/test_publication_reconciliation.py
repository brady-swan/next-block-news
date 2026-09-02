import datetime
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from nbn import config, publisher, publisher_typefully, report, store
from tests.support import item, temporary_store


def published(ref, created, confirmed, text="NEW: Bitcoin publication reconciliation test.",
              url=None):
    return {
        "id": str(ref), "status": "published", "created_at": created,
        "published_at": confirmed,
        "public_url": url or f"https://x.com/nextblocknews_/status/{ref}",
        "preview": text, "draft_title": text[:60],
    }


class ReconciliationTests(unittest.TestCase):
    def test_analytics_attach_to_known_typefully_post_and_recent_feed(self):
        now = time.time()
        performance = {
            "impressions": 120, "likes": 4, "reposts": 3, "comments": 2,
            "quotes": 1, "saves": 1, "profile_clicks": 2,
            "link_clicks": None, "total_engagement": 9,
        }
        with temporary_store() as con:
            store.log_post(
                con, "measured", None, "secondary", "Bitcoin measured post.",
                "https://example.com", "IMMEDIATE", "draft-42",
                publisher_backend="typefully",
            )
            stats = store.reconcile_typefully_analytics(
                con, [{"draft_id": "draft-42", "performance": performance}],
                synced_at=now,
            )
            feed = store.recent_feed_posts(con)

        self.assertEqual(stats["matched"], 1)
        self.assertEqual(stats["updated"], 1)
        self.assertEqual(feed[0]["performance"], performance)
        self.assertEqual(feed[0]["performance_synced_at"], now)

    def test_authoritative_publish_promotes_supported_modes_and_updates_item(self):
        now = time.time()
        with temporary_store() as con:
            fresh = store.upsert_new_items(con, [item()])[0]
            for index, mode in enumerate(("DRAFT", "UNCERTAIN", "FAILED", "IMMEDIATE"), 1):
                item_hash = fresh["url_hash"] if mode == "DRAFT" else None
                store.log_post(
                    con, mode.lower(), item_hash, "primary",
                    "NEW: Bitcoin publication reconciliation test.",
                    "https://example.com", mode, str(index), publisher_backend="typefully")
                con.execute("UPDATE posts SET created=? WHERE nuelink_id=?", (now, str(index)))
            con.commit()
            records = [published(i, now, now + i) for i in range(1, 5)]

            stats = store.reconcile_typefully_publications(con, records, synced_at=now + 10)
            rows = con.execute(
                "SELECT mode,confirmed_at,public_url,publisher_status FROM posts ORDER BY id"
            ).fetchall()

            self.assertEqual(stats["promoted"], 3)
            self.assertEqual(stats["enriched"], 1)
            self.assertTrue(all(r["mode"] == "IMMEDIATE" for r in rows))
            self.assertTrue(all(r["publisher_status"] == "published" for r in rows))
            self.assertEqual(con.execute(
                "SELECT status FROM items WHERE url_hash=?", (fresh["url_hash"],)
            ).fetchone()["status"], "posted")

            again = store.reconcile_typefully_publications(con, records, synced_at=now + 20)
            self.assertEqual(again["promoted"], 0)
            self.assertEqual(again["enriched"], 4)

    def test_tape_duplicate_unknown_and_legacy_guard_are_safe(self):
        now = time.time()
        body = "NEW: Bitcoin publication reconciliation test with enough matching copy."
        with temporary_store() as con:
            store.log_post(con, "tape", None, "primary", body, "x", "TAPE", "tape-id",
                           publisher_backend="typefully")
            for _ in range(2):
                store.log_post(con, "dup", None, "primary", body, "x", "DRAFT", "dup-id",
                               publisher_backend="typefully")
            store.log_post(con, "legacy-good", None, "primary", body, "x", "DRAFT", "legacy-good")
            store.log_post(con, "legacy-bad", None, "primary", body, "x", "DRAFT", "legacy-bad")
            con.execute(
                "UPDATE posts SET created=? WHERE nuelink_id IN ('tape-id','dup-id','legacy-good','legacy-bad')",
                (now,))
            con.commit()
            records = [
                published("tape-id", now, now + 1, body),
                published("dup-id", now, now + 1, body),
                published("legacy-good", now, now + 1, body),
                published("legacy-bad", now, now + 1, "Completely different remote copy that does not match."),
                published("unknown", now, now + 1, body),
            ]
            stats = store.reconcile_typefully_publications(con, records, synced_at=now + 2)

            self.assertEqual(stats["tape_anomaly"], 1)
            self.assertEqual(stats["duplicates"], 1)
            self.assertEqual(stats["legacy_backfilled"], 1)
            self.assertEqual(stats["legacy_guard_failed"], 1)
            self.assertEqual(stats["unknown"], 1)
            tape = con.execute("SELECT * FROM posts WHERE nuelink_id='tape-id'").fetchone()
            self.assertEqual(tape["mode"], "TAPE")
            self.assertIsNone(tape["publisher_synced_at"])
            good = con.execute("SELECT * FROM posts WHERE nuelink_id='legacy-good'").fetchone()
            self.assertEqual((good["mode"], good["publisher_backend"]),
                             ("IMMEDIATE", "typefully"))
            bad = con.execute("SELECT * FROM posts WHERE nuelink_id='legacy-bad'").fetchone()
            self.assertEqual((bad["mode"], bad["publisher_backend"]), ("DRAFT", None))

    def test_legacy_guard_rejects_missing_short_and_mismatched_text(self):
        now = time.time()
        cases = [("missing", "", ""), ("short", "Short copy", "Short copy"),
                 ("mismatch", "A sufficiently long local Bitcoin report that has details.",
                  "A totally different remote publication with enough text to compare.")]
        with temporary_store() as con:
            records = []
            for ref, local, remote in cases:
                store.log_post(con, ref, None, "primary", local, "x", "DRAFT", ref)
                con.execute("UPDATE posts SET created=? WHERE nuelink_id=?", (now, ref))
                records.append(published(ref, now, now + 1, remote))
            con.commit()
            stats = store.reconcile_typefully_publications(con, records, synced_at=now + 2)
            self.assertEqual(stats["legacy_guard_failed"], 3)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) n FROM posts WHERE mode='DRAFT'"
            ).fetchone()["n"], 3)

    def test_confirmed_time_moves_publication_to_actual_central_day(self):
        central = ZoneInfo("America/Chicago")
        created = datetime.datetime(2026, 8, 30, 20, 0, tzinfo=central).timestamp()
        confirmed = datetime.datetime(2026, 8, 31, 8, 0, tzinfo=central).timestamp()
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "token"):
            store.log_post(con, "cross-day", None, "primary", "NEW: Cross-day test.",
                           "https://example.com", "IMMEDIATE", "cross",
                           publisher_backend="typefully")
            con.execute(
                "UPDATE posts SET created=?,confirmed_at=?,public_url=? WHERE nuelink_id='cross'",
                (created, confirmed, "https://x.com/nextblocknews_/status/cross"))
            con.commit()

            self.assertEqual(store.day_summary(con, "2026-08-30")["published"], 0)
            self.assertEqual(store.day_summary(con, "2026-08-31")["published"], 1)
            html = report.render(con, day="2026-08-31")
            self.assertIn("8:00 AM", html)
            self.assertIn("https://x.com/nextblocknews_/status/cross", html)

    def test_manual_publish_leaves_action_queue_and_freshness_is_visible(self):
        now = time.time()
        body = "NEW: Bitcoin manual publication reconciliation appears on the Desk."
        with temporary_store() as con, \
                patch.object(config, "REPORT_TOKEN", "token"), \
                patch.object(config, "TYPEFULLY_API_KEY", "key"), \
                patch.object(config, "TYPEFULLY_SOCIAL_SET_ID", "set"), \
                patch.object(report.time, "time", return_value=now + 2):
            store.log_post(con, "manual", None, "primary", body, "https://example.com",
                           "DRAFT", "manual", publisher_backend="typefully")
            con.execute("UPDATE posts SET created=? WHERE nuelink_id='manual'", (now,))
            con.commit()
            store.reconcile_typefully_publications(
                con, [published("manual", now, now + 1, body)], synced_at=now + 2)
            store.kv_set(con, "worker:last_success", str(now + 2))

            html = report.render(con)
            self.assertNotIn("AWAITING PUBLICATION", html)
            self.assertIn("1 published", html)
            self.assertIn("publisher sync just now", html)
            self.assertIn("cycle just now", html)
            self.assertIn("https://x.com/nextblocknews_/status/manual", html)

    def test_reconcile_failure_is_rate_limited_and_does_not_raise(self):
        with temporary_store() as con, \
                patch.object(config, "TYPEFULLY_API_KEY", "key"), \
                patch.object(config, "TYPEFULLY_SOCIAL_SET_ID", "set"), \
                patch.object(config, "PUBLISH_RECONCILE_SECONDS", 300), \
                patch.object(publisher.time, "time", return_value=1000), \
                patch.object(publisher_typefully, "list_published",
                             side_effect=RuntimeError("publisher offline")) as fetch:
            first = publisher.reconcile_publications(con)
            second = publisher.reconcile_publications(con)
            self.assertIn("publisher offline", first["error"])
            self.assertEqual(second, {"rate_limited": 1})
            self.assertEqual(fetch.call_count, 1)
            self.assertEqual(store.kv_get(con, "publisher:last_attempt"), "1000")

    def test_successful_publication_reconcile_refreshes_batched_analytics(self):
        now = time.time()
        with temporary_store() as con, \
                patch.object(config, "TYPEFULLY_API_KEY", "key"), \
                patch.object(config, "TYPEFULLY_SOCIAL_SET_ID", "set"), \
                patch.object(publisher.time, "time", return_value=now), \
                patch.object(publisher_typefully, "list_published", return_value=[]), \
                patch.object(publisher_typefully, "list_analytics_posts", return_value=[]) as analytics:
            result = publisher.reconcile_publications(con)
        analytics.assert_called_once_with()
        self.assertEqual(result["analytics"]["fetched"], 0)


class MigrationTests(unittest.TestCase):
    def test_partially_migrated_posts_table_is_completed_without_losing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.db"
            con = sqlite3.connect(path)
            con.execute(
                "CREATE TABLE posts (id INTEGER PRIMARY KEY,created REAL,story_key TEXT,"
                "item_hash TEXT,class TEXT,body TEXT,receipt_url TEXT,mode TEXT,nuelink_id TEXT,"
                "editor_note TEXT,confirmed_at REAL)"
            )
            con.execute(
                "INSERT INTO posts(created,story_key,body,mode,editor_note)"
                " VALUES (1,'kept','copy','DRAFT','existing')"
            )
            con.commit()
            con.close()
            with patch.object(config, "DATA_DIR", Path(directory)), \
                    patch.object(config, "DB_PATH", path):
                migrated = store.connect()
                try:
                    columns = {r["name"] for r in migrated.execute("PRAGMA table_info(posts)")}
                    self.assertTrue(set(store.POST_COLUMNS).issubset(columns))
                    row = migrated.execute("SELECT story_key,editor_note FROM posts").fetchone()
                    self.assertEqual((row["story_key"], row["editor_note"]), ("kept", "existing"))
                finally:
                    migrated.close()


if __name__ == "__main__":
    unittest.main()
