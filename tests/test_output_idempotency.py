import datetime
import unittest
from unittest.mock import patch

from nbn import publisher, publisher_typefully, store
from tests.support import item, temporary_store


class OutputIdempotencyTests(unittest.TestCase):
    def _post(self, con, story, mode, ref, *, relation="legacy", base=None,
              status="draft"):
        con.execute(
            "INSERT INTO posts(created,story_key,item_hash,class,body,receipt_url,mode,"
            "nuelink_id,publisher_backend,publisher_status,coverage_relation,base_post_id)"
            " VALUES (1,?,?,?,?,?,?,?,?,?,?,?)",
            (story, "item", "secondary", f"copy {ref}", f"https://example.com/{ref}",
             mode, ref, "typefully", status, relation, base),
        )
        con.commit()
        return con.execute("SELECT last_insert_rowid() id").fetchone()["id"]

    def test_reader_visible_precedes_newer_draft_and_dismissal_does_not_matter(self):
        with temporary_store() as con:
            visible = self._post(con, "event", "IMMEDIATE", "published", status="published")
            con.execute("UPDATE posts SET created=2 WHERE id=?", (visible,))
            self._post(con, "event", "DRAFT", "draft-newer")
            store.kv_set(con, "dismissed:post:1", "yes")
            state = store.canonical_output_state(con, "event")
            self.assertEqual(state["state"], "reader_visible")
            self.assertEqual(state["visible"]["id"], visible)
            self.assertEqual(len(state["drafts"]), 1)

    def test_deleted_draft_is_inactive_but_multiple_live_drafts_are_reported(self):
        with temporary_store() as con:
            self._post(con, "event", "DRAFT", "deleted", status="deleted")
            self.assertEqual(store.canonical_output_state(con, "event")["state"], "none")
            self._post(con, "event", "DRAFT", "one")
            self._post(con, "event", "DRAFT", "two")
            self.assertEqual(len(store.canonical_output_state(con, "event")["drafts"]), 2)

    def test_mutation_intent_fences_workers_and_finalizes_idempotently(self):
        with temporary_store() as con:
            saved = store.upsert_new_items(con, [item()])[0]
            state = store.canonical_output_state(con, "event")
            materialization = {
                "run_id": "run", "story_id": "story", "item_hash": saved["url_hash"],
                "members": [{"url_hash": saved["url_hash"], "story_key": "event"}],
                "klass": "secondary", "body": "Bitcoin event", "receipt_url": saved["url"],
                "editor_note": "publish: good", "resolution_id": saved["url_hash"],
                "publisher_backend": "typefully", "coverage_relation": "distinct",
                "base_post_id": None,
            }
            intent = store.prepare_publisher_mutation(
                con, story_key="event", operation="create", intended_mode="DRAFT",
                desired_thread=["Bitcoin event\n\nhttps://example.com/story"],
                materialization=materialization, expected_output_signature=state["signature"],
            )
            self.assertTrue(intent["ok"])
            blocked = store.prepare_publisher_mutation(
                con, story_key="event", operation="create", intended_mode="DRAFT",
                desired_thread=["duplicate"], materialization=materialization,
                expected_output_signature=state["signature"],
            )
            self.assertFalse(blocked["ok"])
            self.assertTrue(store.transition_publisher_mutation(
                con, intent["mutation_id"], intent["owner_token"], 1, "in_flight"
            ))
            finalized = store.finalize_publisher_mutation(
                con, intent["mutation_id"], intent["owner_token"], 2,
                mode="DRAFT", provider_ref="draft-1", publisher_status="draft",
            )
            again = store.finalize_publisher_mutation(
                con, intent["mutation_id"], intent["owner_token"], 2,
                mode="DRAFT", provider_ref="draft-1", publisher_status="draft",
            )
            self.assertTrue(finalized["ok"])
            self.assertTrue(again["already_finalized"])
            self.assertEqual(con.execute("SELECT COUNT(*) n FROM posts").fetchone()["n"], 1)
            self.assertEqual(con.execute(
                "SELECT status FROM items WHERE url_hash=?", (saved["url_hash"],)
            ).fetchone()["status"], "drafted")

    def test_owner_resolution_is_version_fenced_and_audited(self):
        with temporary_store() as con:
            state = store.canonical_output_state(con, "event")
            intent = store.prepare_publisher_mutation(
                con, story_key="event", operation="create", intended_mode="DRAFT",
                desired_thread=["copy"], materialization={"body": "copy", "members": []},
                expected_output_signature=state["signature"],
            )
            store.transition_publisher_mutation(
                con, intent["mutation_id"], intent["owner_token"], 1,
                "needs_owner_review", error_kind="zero_matches",
            )
            stale = store.owner_resolve_publisher_mutation(
                con, intent["mutation_id"], intent["owner_token"], 1, "confirmed_absent"
            )
            self.assertFalse(stale["ok"])
            resolved = store.owner_resolve_publisher_mutation(
                con, intent["mutation_id"], intent["owner_token"], 2, "keep_suppressed"
            )
            self.assertTrue(resolved["ok"])
            self.assertEqual(store.publisher_mutation(con, intent["mutation_id"])["state"],
                             "owner_suppressed")
            self.assertEqual(con.execute(
                "SELECT COUNT(*) n FROM pipeline_events WHERE event='publisher_owner_keep_suppressed'"
            ).fetchone()["n"], 1)

    def test_persisted_create_mutations_reconcile_from_stored_thread_fingerprint(self):
        shapes = [
            ["legacy copy\n\nhttps://example.com/story"],
            ["new copy", "Source: https://example.com/story"],
        ]
        for index, thread in enumerate(shapes):
            with self.subTest(thread=thread), temporary_store() as con:
                saved = store.upsert_new_items(con, [item(url=f"https://example.com/{index}")])[0]
                state = store.canonical_output_state(con, f"event-{index}")
                materialization = {
                    "run_id": "run", "story_id": "story",
                    "item_hash": saved["url_hash"],
                    "members": [{"url_hash": saved["url_hash"],
                                 "story_key": f"event-{index}"}],
                    "klass": "secondary", "body": "new copy",
                    "receipt_url": "https://example.com/story",
                    "editor_note": "publish: good", "resolution_id": saved["url_hash"],
                    "publisher_backend": "typefully", "coverage_relation": "distinct",
                    "base_post_id": None,
                }
                intent = store.prepare_publisher_mutation(
                    con, story_key=f"event-{index}", operation="create",
                    intended_mode="DRAFT", desired_thread=thread,
                    materialization=materialization,
                    expected_output_signature=state["signature"],
                )
                store.transition_publisher_mutation(
                    con, intent["mutation_id"], intent["owner_token"], 1, "in_flight"
                )
                persisted = store.publisher_mutation(con, intent["mutation_id"])
                remote = {
                    "id": f"draft-{index}", "status": "draft",
                    "created_at": datetime.datetime.fromtimestamp(
                        persisted["created_at"], datetime.timezone.utc
                    ).isoformat(),
                    "platforms": {"x": {"enabled": True,
                                         "posts": [{"text": text} for text in thread]}},
                }
                with patch.object(publisher, "_backend", return_value="typefully"), \
                        patch.object(publisher_typefully, "list_recent_drafts",
                                     return_value=[remote]), \
                        patch.object(publisher, "one_off_x_thread",
                                     side_effect=AssertionError("formatter must not run")):
                    result = publisher.reconcile_mutations(con)
                self.assertEqual(result["confirmed"], 1)
                self.assertEqual(con.execute("SELECT COUNT(*) n FROM posts").fetchone()["n"], 1)


if __name__ == "__main__":
    unittest.main()
