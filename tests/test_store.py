import unittest
import datetime
import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from nbn import config, source_policy, store, verify
from scripts import backup_db
from tests.support import item, temporary_store


class StoreTests(unittest.TestCase):
    def test_guide_items_are_prioritized_for_triage(self):
        with temporary_store() as con:
            store.upsert_new_items(con, [item(url="https://example.com/ordinary")])
            store.upsert_new_items(con, [item(
                url="https://x.com/BitcoinArchive/status/1",
                source="X guide @BitcoinArchive",
            )])
            pending = store.pending_items(con, 1)
            self.assertEqual(pending[0]["source"], "X guide @BitcoinArchive")

    def test_url_deduplication(self):
        with temporary_store() as con:
            first = store.upsert_new_items(con, [item()])
            second = store.upsert_new_items(con, [item()])
            self.assertEqual(len(first), 1)
            self.assertEqual(second, [])

    def test_canonical_discovery_key_preserves_global_ipv6_syntax(self):
        self.assertEqual(
            store.canonical_discovery_key("https://[2606:4700:4700::1111]:443/a"),
            "https://[2606:4700:4700::1111]/a",
        )

    def test_connect_migrates_legacy_items_before_discovery_index(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            con = sqlite3.connect(path)
            con.execute(
                "CREATE TABLE items (url_hash TEXT PRIMARY KEY, source TEXT, title TEXT,"
                " url TEXT, published_at TEXT, first_seen REAL, status TEXT DEFAULT 'new',"
                " story_key TEXT, note TEXT)"
            )
            con.execute(
                "INSERT INTO items(url_hash,source,title,url,first_seen) VALUES (?,?,?,?,?)",
                ("legacy", "Legacy", "Old item", "https://example.com/a?utm_source=x", 1),
            )
            con.commit()
            con.close()
            with patch.object(config, "DATA_DIR", Path(directory)), \
                    patch.object(config, "DB_PATH", path):
                migrated = store.connect()
                try:
                    columns = {r["name"] for r in migrated.execute("PRAGMA table_info(items)")}
                    indexes = {r["name"] for r in migrated.execute("PRAGMA index_list(items)")}
                    row = migrated.execute(
                        "SELECT discovery_key FROM items WHERE url_hash='legacy'"
                    ).fetchone()
                    self.assertIn("discovery_key", columns)
                    self.assertIn("idx_items_discovery_key", indexes)
                    self.assertEqual(row["discovery_key"], "https://example.com/a")
                finally:
                    migrated.close()

    def test_research_job_gets_one_automatic_retry(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [item()])[0]
            decision = {**row, "story_key": "research-story", "action": "draft",
                        "class": "secondary", "reason": "material Bitcoin news"}
            first = store.start_research_job(con, decision, "run-1")
            self.assertEqual((first["state"], first["attempts"]), ("processing", 1))
            store.defer_research_job(
                con, row["url_hash"], "source_resolution", "timeout", "search timed out",
                delay_seconds=1)
            due = store.claim_due_research_jobs(con, now=time.time() + 2)
            self.assertEqual(len(due), 1)
            self.assertEqual((due[0]["state"], due[0]["attempts"]), ("processing", 2))
            store.defer_research_job(
                con, row["url_hash"], "source_resolution", "timeout", "search timed out")
            final = con.execute(
                "SELECT state,attempts FROM research_jobs WHERE item_hash=?", (row["url_hash"],)
            ).fetchone()
            self.assertEqual((final["state"], final["attempts"]), ("exhausted", 2))

    def test_budget_deferral_does_not_consume_research_attempt(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [item()])[0]
            decision = {**row, "story_key": "budget-story", "action": "draft",
                        "class": "secondary", "reason": "material Bitcoin news"}
            store.start_research_job(con, decision, "run-1")
            store.defer_research_job(
                con, row["url_hash"], "source_resolution", "budget", "budget exhausted",
                consume_attempt=False)
            saved = con.execute(
                "SELECT state,attempts FROM research_jobs WHERE item_hash=?", (row["url_hash"],)
            ).fetchone()
            self.assertEqual((saved["state"], saved["attempts"]), ("pending", 0))

    def test_owner_can_retry_only_infrastructure_job_and_forces_draft(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [item()])[0]
            decision = {**row, "story_key": "manual-research", "action": "draft",
                        "class": "secondary", "reason": "material Bitcoin news"}
            store.start_research_job(con, decision, "run-1")
            store.defer_research_job(
                con, row["url_hash"], "source_fetch", "timeout", "source timed out")
            outcome = store.request_operator_action(con, row["url_hash"], "retry")
            self.assertTrue(outcome["ok"])
            job = con.execute(
                "SELECT state,manual_draft_only FROM research_jobs WHERE item_hash=?",
                (row["url_hash"],),
            ).fetchone()
            self.assertEqual((job["state"], job["manual_draft_only"]), ("pending", 1))

    def test_operator_stage_is_guarded_and_audited(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [item()])[0]
            store.set_status(con, row["url_hash"], "held", "fresh-story",
                             "stale event: dated 2026-08-28, window 6h")
            result = store.request_operator_action(con, row["url_hash"], "stage")
            self.assertTrue(result["ok"])
            self.assertEqual(result["gate"], "freshness")
            current = con.execute(
                "SELECT status,note FROM items WHERE url_hash=?", (row["url_hash"],)
            ).fetchone()
            self.assertEqual(current["status"], "new")
            self.assertIn("stale event", current["note"])
            action = store.pending_stage_action(con, row["url_hash"])
            self.assertEqual((action["state"], action["original_status"]), ("queued", "held"))

    def test_operator_dismiss_records_disposition(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [item()])[0]
            store.set_status(con, row["url_hash"], "held", "dismiss-story",
                             "source policy: unresolved")
            result = store.request_operator_action(con, row["url_hash"], "dismiss")
            self.assertTrue(result["ok"])
            current = con.execute(
                "SELECT status,note FROM items WHERE url_hash=?", (row["url_hash"],)
            ).fetchone()
            self.assertEqual(current["status"], "skipped")
            self.assertIn("owner dismissed", current["note"])
            action = store.latest_operator_action(con, row["url_hash"])
            self.assertEqual((action["action"], action["state"]), ("dismiss", "completed"))

    def test_source_hold_cannot_be_forced_without_material(self):
        with temporary_store() as con:
            row = store.upsert_new_items(con, [item()])[0]
            store.set_status(con, row["url_hash"], "held", "source-story",
                             "source policy: selected receipt text unavailable")
            result = store.request_operator_action(con, row["url_hash"], "stage")
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason"], "this hold needs more source material")
            self.assertEqual(con.execute("SELECT status FROM items").fetchone()["status"], "held")

    def test_last_decision_run_keeps_final_state_and_survives_empty_poll(self):
        with temporary_store() as con:
            pending = store.upsert_new_items(con, [item(title="Decision candidate")])
            store.set_status(con, pending[0]["url_hash"], "held", "decision-story",
                             "needs second source")
            store.record_decision_run(
                con, pending,
                [{**pending[0], "action": "draft", "story_key": "decision-story",
                  "reason": "material Bitcoin story"}],
                {"fetched": 1, "new": 1, "considered": 1, "pending": 1}, 100.0,
            )
            saved = store.kv_get(con, "desk:last_decision_run")
            record = json.loads(saved)
            self.assertEqual(record["items"][0]["triage_action"], "draft")
            self.assertEqual(record["items"][0]["triage_reason"], "material Bitcoin story")
            self.assertEqual(record["items"][0]["final_status"], "held")
            self.assertEqual(record["items"][0]["final_note"], "needs second source")

            store.record_decision_run(con, [], [], {"fetched": 0}, 200.0)
            self.assertEqual(store.kv_get(con, "desk:last_decision_run"), saved)

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

    def test_story_alias_family_pools_cross_key_evidence_and_coverage(self):
        with temporary_store() as con:
            now = time.time()
            for key, source_id in (("global-yields", "cnbc"), ("g7-yields", "bloomberg")):
                con.execute(
                    "INSERT INTO source_evidence(item_hash,story_key,observed_at,url,source_id,"
                    "source_name,tier,category,independence_key,ownership_key,originality,"
                    "support_verdict,receipt_eligible,corroboration_eligible,"
                    "primary_artifact_fingerprint,content_fingerprint)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (source_id, key, now, f"https://{source_id}.example/story", source_id,
                     source_id, "t1", "reporting", source_id, source_id,
                     "original_reporting", 1, 1, 1, "", f"content-{source_id}"),
                )
            con.commit()
            store.log_post(
                con, "global-yields", None, "secondary", "NEW: Yields rose.",
                "https://cnbc.example/story", "DRAFT", "draft-id",
                publisher_backend="typefully",
            )
            canonical = store.register_story_alias(
                con, "g7-yields", "global-yields", "same dated event")
            self.assertEqual(canonical, "global-yields")
            self.assertEqual(store.story_key_family(con, "g7-yields"),
                             ["g7-yields", "global-yields"])
            self.assertEqual(store.qualified_evidence_count(con, "g7-yields"), 2)
            self.assertTrue(store.story_handled(con, "g7-yields"))
            self.assertFalse(store.story_reader_covered(con, "g7-yields"))
            self.assertEqual(store.open_typefully_draft(con, "g7-yields")["nuelink_id"],
                             "draft-id")
            con.execute(
                "UPDATE story_key_aliases SET updated_at=? WHERE alias_key='g7-yields'",
                (time.time() - 4 * 86400,),
            )
            con.commit()
            self.assertEqual(store.canonical_story_key(con, "g7-yields"), "g7-yields")

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

    def test_theme_coverage_snapshot_is_bounded_advisory_history(self):
        context = json.dumps({
            "untrusted_discovery_context": True,
            "schema_version": "wire-pulse-v2",
            "theme_ids": ["institutional-adoption"],
            "theme_signal_version": "node-theme-signal-v1",
            "theme_signals": [{
                "theme_id": "institutional-adoption",
                "name": "Institutional adoption",
                "trajectory": "building",
                "count_7d": 8,
                "count_14d": 12,
                "count_30d": 20,
                "last_evidence_at": "2026-09-01T12:00:00+00:00",
                "match_basis": "node-classifier-v1",
                "confidence": 0.91,
                "rank_eligible": True,
            }],
        })
        with temporary_store() as con:
            current = store.upsert_new_items(con, [{
                "source": "Node", "title": "Current", "url": "https://example.com/current",
                "published": "", "summary": "", "discovery_context": context,
            }])[0]
            unknown = store.theme_coverage_snapshot(con, [current])
            self.assertFalse(unknown[0]["coverage_known"])

            prior = store.upsert_new_items(con, [{
                "source": "Node", "title": "Prior", "url": "https://example.com/prior",
                "published": "", "summary": "", "discovery_context": context,
            }])[0]
            store.set_status(con, prior["url_hash"], "posted", "prior-event")
            store.log_post(
                con, "prior-event", prior["url_hash"], "primary", "NEW: Prior.",
                "https://example.com/prior", "IMMEDIATE", publisher_backend="typefully",
            )
            draft = store.upsert_new_items(con, [{
                "source": "Node", "title": "Draft", "url": "https://example.com/draft",
                "published": "", "summary": "", "discovery_context": context,
            }])[0]
            store.set_status(con, draft["url_hash"], "drafted", "draft-event")
            store.log_post(
                con, "draft-event", draft["url_hash"], "secondary", "NEW: Draft.",
                "https://example.com/draft", "DRAFT", "tf-1",
                publisher_backend="typefully",
            )
            snapshot = store.theme_coverage_snapshot(con, [current], key_limit=1)
            self.assertTrue(snapshot[0]["coverage_known"])
            self.assertTrue(snapshot[0]["open_draft"])
            self.assertIsNotNone(snapshot[0]["last_published_at"])
            self.assertEqual(len(snapshot[0]["recent_story_keys"]), 1)

    def test_theme_coverage_includes_uncertain_but_excludes_nonreader_lifecycles(self):
        def signal(theme_id):
            return {
                "theme_id": theme_id, "name": theme_id, "trajectory": "building",
                "count_7d": 1, "count_14d": 1, "count_30d": 1,
                "last_evidence_at": "2026-09-01T12:00:00+00:00",
                "match_basis": "node-classifier-v1", "confidence": 0.9,
                "rank_eligible": True,
            }

        def context(theme_id):
            return json.dumps({
                "untrusted_discovery_context": True,
                "schema_version": "wire-pulse-v2",
                "theme_ids": [theme_id],
                "theme_signal_version": "node-theme-signal-v1",
                "theme_signals": [signal(theme_id)],
            })

        with temporary_store() as con:
            current_context = json.loads(context("reader-theme"))
            current_context["theme_ids"].append("excluded-theme")
            current_context["theme_signals"].append(signal("excluded-theme"))
            current = store.upsert_new_items(con, [{
                "source": "Node", "title": "Current", "url": "https://example.com/current-2",
                "published": "", "summary": "",
                "discovery_context": json.dumps(current_context),
            }])[0]
            uncertain = store.upsert_new_items(con, [{
                "source": "Node", "title": "Uncertain", "url": "https://example.com/uncertain",
                "published": "", "summary": "", "discovery_context": context("reader-theme"),
            }])[0]
            store.log_post(
                con, "uncertain-event", uncertain["url_hash"], "primary", "NEW: Maybe live.",
                "https://example.com/uncertain", "UNCERTAIN", publisher_backend="typefully",
            )

            for index, mode in enumerate(("DISMISSED", "FAILED", "TAPE")):
                row = store.upsert_new_items(con, [{
                    "source": "Node", "title": mode,
                    "url": f"https://example.com/excluded-{index}", "published": "",
                    "summary": "", "discovery_context": context("excluded-theme"),
                }])[0]
                store.log_post(
                    con, f"excluded-{index}", row["url_hash"], "primary", f"{mode} body",
                    row["url"], mode, publisher_backend="typefully",
                )
            deleted = store.upsert_new_items(con, [{
                "source": "Node", "title": "Deleted", "url": "https://example.com/deleted",
                "published": "", "summary": "", "discovery_context": context("excluded-theme"),
            }])[0]
            store.log_post(
                con, "deleted-event", deleted["url_hash"], "secondary", "NEW: Deleted.",
                deleted["url"], "DRAFT", "tf-deleted", publisher_backend="typefully",
            )
            con.execute("UPDATE posts SET publisher_status='deleted' WHERE story_key='deleted-event'")
            for index, mode in enumerate(("IMMEDIATE", "UNCERTAIN"), 1):
                deleted_reader = store.upsert_new_items(con, [{
                    "source": "Node", "title": f"Deleted {mode}",
                    "url": f"https://example.com/deleted-reader-{index}", "published": "",
                    "summary": "", "discovery_context": context("excluded-theme"),
                }])[0]
                story_key = f"deleted-reader-{index}"
                store.log_post(
                    con, story_key, deleted_reader["url_hash"], "primary", "NEW: Deleted.",
                    deleted_reader["url"], mode, publisher_backend="typefully",
                )
                con.execute(
                    "UPDATE posts SET publisher_status='deleted' WHERE story_key=?",
                    (story_key,),
                )
            briefing = store.upsert_new_items(con, [{
                "source": "Node", "title": "Briefing", "url": "https://example.com/briefing",
                "published": "", "summary": "", "discovery_context": context("excluded-theme"),
            }])[0]
            store.log_post(
                con, "briefing-event", briefing["url_hash"], "briefing", "Block body",
                briefing["url"], "IMMEDIATE", publisher_backend="typefully",
            )
            con.commit()

            snapshot = {
                row["theme_id"]: row for row in store.theme_coverage_snapshot(con, [current])
            }
            self.assertTrue(snapshot["reader-theme"]["coverage_known"])
            self.assertIsNotNone(snapshot["reader-theme"]["last_published_at"])
            self.assertFalse(snapshot["excluded-theme"]["coverage_known"])
            self.assertFalse(snapshot["excluded-theme"]["open_draft"])

    def test_theme_coverage_falls_back_to_tagged_story_alias_family(self):
        context = json.dumps({
            "untrusted_discovery_context": True,
            "schema_version": "wire-pulse-v2",
            "theme_ids": ["policy-theme"],
            "theme_signal_version": "node-theme-signal-v1",
            "theme_signals": [{
                "theme_id": "policy-theme", "name": "Bitcoin policy",
                "trajectory": "building", "count_7d": 3, "count_14d": 5,
                "count_30d": 9, "last_evidence_at": "2026-09-01T12:00:00+00:00",
                "match_basis": "node-classifier-v1", "confidence": 0.94,
                "rank_eligible": True,
            }],
        })
        with temporary_store() as con:
            tagged = store.upsert_new_items(con, [{
                "source": "Node", "title": "Tagged alias",
                "url": "https://example.com/tagged-alias", "published": "", "summary": "",
                "discovery_context": context,
            }])[0]
            store.set_status(con, tagged["url_hash"], "held", "policy-vote-alias")
            untagged = store.upsert_new_items(con, [{
                "source": "RSS", "title": "Published canonical",
                "url": "https://example.com/published-canonical", "published": "",
                "summary": "",
            }])[0]
            store.set_status(con, untagged["url_hash"], "posted", "policy-vote")
            store.log_post(
                con, "policy-vote", untagged["url_hash"], "primary", "NEW: Vote passed.",
                untagged["url"], "IMMEDIATE", publisher_backend="typefully",
            )
            store.register_story_alias(
                con, "policy-vote-alias", "policy-vote", "same dated vote")
            current = store.upsert_new_items(con, [{
                "source": "Node", "title": "Current theme candidate",
                "url": "https://example.com/current-policy", "published": "", "summary": "",
                "discovery_context": context,
            }])[0]

            snapshot = store.theme_coverage_snapshot(con, [current])
            self.assertTrue(snapshot[0]["coverage_known"])
            self.assertIsNotNone(snapshot[0]["last_published_at"])
            self.assertEqual(snapshot[0]["recent_story_keys"], ["policy-vote"])

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
