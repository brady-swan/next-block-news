"""Owner skip reconsideration: durable delivery intent, never approval to publish."""
import io
import json
import time
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from nbn import config, desk_api, desk_prep, main, newsroom, store
from tests.support import temporary_store, item
from tests.test_desk_prep import decision, response_for
from tests.test_newsroom import tool_response


class ReconsiderTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(config, "EDITORIAL_ENGINE", "v2"))
        self.stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))

    def saved(self, con, suffix="story", stage="newsdesk"):
        row = store.upsert_new_items(con, [item(
            url=f"https://example.com/{suffix}", published="2026-01-01T00:00:00Z",
        )])[0]
        store.set_status(con, row["url_hash"], "skipped", "original-event", "Original skip reason",
                         stage=stage, category="editorial_drop")
        return row["url_hash"]

    def queue(self, con, h, version=0):
        return store.request_operator_action(con, h, "reconsider", expected_action_id=version)

    def test_request_is_atomic_idempotent_and_does_not_change_item_or_cadence(self):
        with temporary_store() as con:
            h = self.saved(con)
            store.kv_set(con, "editorial:next_run_at", "9999999999")
            before = dict(con.execute("SELECT * FROM items WHERE url_hash=?", (h,)).fetchone())
            first = self.queue(con, h)
            second = self.queue(con, h)
            self.assertTrue(first["ok"])
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(before, dict(con.execute("SELECT * FROM items WHERE url_hash=?", (h,)).fetchone()))
            self.assertEqual(store.kv_get(con, "editorial:next_run_at"), "9999999999")
            self.assertEqual(con.execute("SELECT COUNT(*) FROM operator_actions").fetchone()[0], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM posts").fetchone()[0], 0)
            action = store.latest_operator_action(con, h)
            self.assertEqual((action["original_note"], action["gate"]), ("Original skip reason", "newsdesk"))

    def test_delayed_post_needs_refreshed_action_version(self):
        with temporary_store() as con:
            h = self.saved(con)
            queued = self.queue(con, h)
            store.activate_reconsiderations(con)
            inventory = store.pending_items(con, 10)
            store.complete_reconsiderations(con, inventory, "cycle:test")
            store.set_status(con, h, "skipped", None, "Writer still declines")
            self.assertFalse(self.queue(con, h)["ok"])
            self.assertTrue(self.queue(con, h, queued["id"])["ok"])

    def test_state_transition_is_not_rewound_and_other_actions_block(self):
        with temporary_store() as con:
            for state in ("held", "drafted", "posted", "uncertain", "failed"):
                h = self.saved(con, suffix=state)
                self.queue(con, h)
                store.set_status(con, h, state, None, "Changed during current run")
                store.activate_reconsiderations(con)
                self.assertEqual(store.latest_operator_action(con, h)["state"], "blocked")
                self.assertEqual(con.execute("SELECT status FROM items WHERE url_hash=?", (h,)).fetchone()[0], state)
            h = self.saved(con, suffix="other-action")
            con.execute("INSERT INTO operator_actions(item_hash,action,requested_at,state,original_status) VALUES (?,'stage',?,'queued','held')", (h, time.time()))
            con.commit()
            self.assertFalse(self.queue(con, h)["ok"])

    def test_restart_activation_priority_and_existing_deferral(self):
        with temporary_store() as con:
            h = self.saved(con)
            self.queue(con, h)
            other = store.upsert_new_items(con, [item(url="https://example.com/other")])[0]
            restarted = store.connect()
            try:
                store.activate_reconsiderations(restarted)
                pending = store.pending_items(restarted, 1)
                self.assertEqual(pending[0]["url_hash"], h)
                self.assertEqual(pending[0]["published"], "2026-01-01T00:00:00Z")
                self.assertEqual(pending[0]["_owner_reconsider"]["requested_by"], "Brady")
                self.assertFalse(main._override_allows(pending[0], "freshness"))
                self.assertEqual(main._action_ids(pending[0]), [])
                store.defer_item(restarted, h, "defer:temporary failure", delay_seconds=300)
                due = restarted.execute("SELECT defer_until FROM items WHERE url_hash=?", (h,)).fetchone()[0]
                store.activate_reconsiderations(restarted)
                self.assertEqual(restarted.execute("SELECT defer_until FROM items WHERE url_hash=?", (h,)).fetchone()[0], due)
                self.assertEqual(store.pending_items(restarted, 1)[0]["url_hash"], other["url_hash"])
                self.assertEqual(store.latest_operator_action(restarted, h)["state"], "queued")
            finally:
                restarted.close()

    def test_background_prep_cannot_filter_owner_request(self):
        with temporary_store() as con:
            h = self.saved(con, stage="intake_triage")
            self.queue(con, h)
            store.activate_reconsiderations(con)
            inventory = store.pending_items(con, 10)
            api = Mock()
            api.messages.create.return_value = response_for([decision(h, "background")])
            with patch.object(desk_prep.anthropic, "Anthropic", return_value=api), patch.object(desk_prep.brain, "consume_model_call"):
                result = desk_prep.prepare(con, run_id="prep-owner", inventory=inventory,
                                          coverage_keys=[], continuity_ids=set(), reservation="r", mode="enforce")
            self.assertIn(h, result.advanced_ids)
            self.assertEqual(result.rows[0]["protection_reason"], "operator_requested")

    def session(self, con, inventory, compact=False):
        with patch.object(newsroom.anthropic, "Anthropic"):
            return newsroom.NewsroomSession(
                run_id="cycle:owner", inventory=inventory, recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="r", prep_mode="off", research_mode="off",
                compact_enabled=compact,
            )

    def test_owner_note_in_normal_and_forced_compact_packet(self):
        with temporary_store() as con:
            h = self.saved(con)
            self.queue(con, h)
            store.activate_reconsiderations(con)
            inventory = store.pending_items(con, 10)
            plain = self.session(con, inventory)._initial_packet()
            card = plain["intake_board"][0]
            self.assertIn("Brady overrode", card["owner_override"]["instruction"])
            self.assertEqual(card["owner_override"]["prior_skip_reason"], "Original skip reason")
            self.assertEqual(card["arrived_at"], "2026-01-01T00:00:00Z")
            self.assertIsNone(card["operator_gate"])
            session = self.session(con, inventory, compact=True)
            # Force optional context to overflow while retaining every candidate's owner note.
            session.storyline_cards = [{"title": "Long context" * 5000} for _ in range(8)]
            with patch.object(config, "COMPACT_DESK_INITIAL_BYTES", 12000):
                session.storyline_cards = []
                original_bytes = newsroom._json_bytes
                def force_compact(value):
                    if isinstance(value, dict) and value.get("intake_board"):
                        if "why_on_desk" in value["intake_board"][0]:
                            return 999999
                    return original_bytes(value)
                with patch.object(newsroom, "_json_bytes", side_effect=force_compact):
                    compact = session._initial_packet()
            compact_card = compact["intake_board"][0]
            self.assertNotIn("why_on_desk", compact_card)
            self.assertEqual(compact_card["owner_override"], card["owner_override"])

    def test_consume_only_valid_protocol_response_not_truncation_or_failure(self):
        with temporary_store() as con:
            h = self.saved(con)
            self.queue(con, h)
            store.activate_reconsiderations(con)
            inventory = store.pending_items(con, 10)
            for stop in ("max_tokens", "refusal", "invalid_response", "end_turn"):
                session = self.session(con, inventory)
                reply = SimpleNamespace(stop_reason=stop, content=[])
                with patch.object(session, "_call", return_value=reply), self.assertRaises(newsroom.NewsroomError):
                    session.conduct_v2()
                self.assertEqual(store.latest_operator_action(con, h)["state"], "queued")
            session = self.session(con, inventory)
            with patch.object(session, "_call", side_effect=TimeoutError), self.assertRaises(TimeoutError):
                session.conduct_v2()
            self.assertEqual(store.latest_operator_action(con, h)["state"], "queued")
            session = self.session(con, inventory)
            reply = tool_response("t1", "fetch_intake_item", {"candidate_id": h})
            with patch.object(session, "_call", return_value=reply), patch.object(session, "_dispatch", side_effect=TimeoutError), self.assertRaises(TimeoutError):
                session.conduct_v2()
            action = store.latest_operator_action(con, h)
            self.assertEqual(action["state"], "completed")
            self.assertIn("cycle:owner", action["result"])

    def test_old_skipped_lead_reaches_scheduled_desk_without_forcing_slot(self):
        with temporary_store() as con, ExitStack() as stack:
            h = self.saved(con)
            self.queue(con, h)
            for name in ("fetch_feeds", "fetch_edgar", "fetch_perception", "fetch_x"):
                stack.enter_context(patch.object(main.sources, name, return_value=[]))
            stack.enter_context(patch.object(main.publisher, "reconcile_mutations", return_value={}))
            stack.enter_context(patch.object(main.node_discovery, "ingest", return_value={}))
            stack.enter_context(patch.object(main.intake_triage, "route_cycle", return_value={}))
            desk = stack.enter_context(patch.object(main, "_run_editorial_v2", side_effect=lambda *a, **kw: kw["result"]))
            store.acquire_cycle_lease(con, "owner-test")
            store.kv_set(con, "editorial:next_run_at", str(time.time() + 900))
            result = main._cycle_locked(con, "owner-test")
            self.assertEqual(result["newsroom"]["status"], "waiting")
            desk.assert_not_called()
            store.kv_set(con, "editorial:next_run_at", "1")
            main._cycle_locked(con, "owner-test")
            inventory = desk.call_args.kwargs["inventory"]
            self.assertEqual([r["url_hash"] for r in inventory], [h])
            self.assertIn("_owner_reconsider", inventory[0])
            self.assertFalse(desk.call_args.kwargs["overrides"])

    def test_post_auth_json_route_restriction_and_snapshot_pending_status(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "test-owner"):
            h = self.saved(con)
            def post(**fields):
                handler = main.Health.__new__(main.Health)
                handler.path = "/desk/api/item-action"
                body = urlencode({"k": "test-owner", "id": h, "action": "reconsider", "expected_action_id": 0, **fields}).encode()
                handler.headers = {"Content-Length": str(len(body))}
                handler.rfile = io.BytesIO(body); handler.wfile = io.BytesIO()
                handler.send_response = Mock(); handler.send_header = Mock(); handler.end_headers = Mock()
                handler.do_POST()
                return handler.send_response.call_args.args[0], handler.wfile.getvalue()
            self.assertEqual(post(k="bad")[0], 403)
            self.assertEqual(post(action="dismiss")[0], 409)
            self.assertEqual(post(expected_action_id="bad")[0], 409)
            status, body = post()
            self.assertEqual(status, 200)
            self.assertTrue(json.loads(body)["ok"])
            snapshot = desk_api.snapshot(con, {"view": ["intake"]}, {})
            control = snapshot["items"][0]["reconsider"]
            self.assertFalse(control["eligible"])
            self.assertEqual(control["request"]["state"], "queued")
            self.assertNotIn("test-owner", json.dumps(snapshot))


if __name__ == "__main__":
    unittest.main()
