import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from nbn import brain, config, intake_triage, report, store
from tests.support import item, temporary_store


def feed_item(url, title, origin="rss", source="Feed"):
    return {**item(url=url, title=title, source=source), "discovery_origin": origin}


def response_for(rows):
    decisions = [{
        "candidate_id": row["url_hash"],
        "route": "background" if "sports" in row["title"].lower() else "priority",
        "category": "unrelated" if "sports" in row["title"].lower()
        else "bitcoin_direct",
        "reason": "Unrelated sports item." if "sports" in row["title"].lower()
        else "Fresh direct Bitcoin development.",
    } for row in rows]
    block = SimpleNamespace(type="tool_use", name="submit_intake_triage",
                            input={"decisions": decisions})
    usage = SimpleNamespace(input_tokens=100, output_tokens=20,
                            cache_creation_input_tokens=0, cache_read_input_tokens=0)
    return SimpleNamespace(stop_reason="tool_use", content=[block], usage=usage)


class IntakeTriageTests(unittest.TestCase):
    def test_observe_persists_without_removing_background_from_desk(self):
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [
                feed_item("https://example.com/sports", "Sports results"),
            ])
            with patch.object(config, "INTAKE_TRIAGE_MODE", "observe"), \
                    patch.object(intake_triage.client.messages, "create",
                                 return_value=response_for(inserted)), \
                    patch.object(config, "RUN_NEWSROOM_MODE", "off"):
                result = intake_triage.route_cycle(con, inserted, run_id="run-1")
            row = con.execute(
                "SELECT t.route,t.applied_at,i.status FROM intake_triage t "
                "JOIN items i ON i.url_hash=t.item_hash"
            ).fetchone()
            self.assertEqual((row["route"], row["status"]), ("background", "new"))
            self.assertIsNone(row["applied_at"])
            self.assertEqual(result["saved"]["applied"], 0)

    def test_enforce_backgrounds_noise_and_priority_wakes_and_orders_desk(self):
        with temporary_store() as con:
            ordinary = store.upsert_new_items(con, [
                feed_item("https://example.com/ordinary", "Ordinary candidate"),
            ])[0]
            inserted = store.upsert_new_items(con, [
                feed_item("https://example.com/sports", "Sports results"),
                feed_item("https://example.com/bitcoin", "Bitcoin policy enacted"),
            ])
            with patch.object(config, "INTAKE_TRIAGE_MODE", "enforce"), \
                    patch.object(intake_triage.client.messages, "create",
                                 return_value=response_for(inserted)), \
                    patch.object(config, "RUN_NEWSROOM_MODE", "off"):
                result = intake_triage.route_cycle(con, inserted, run_id="run-2")
            rows = {row["url"]: dict(row) for row in con.execute(
                "SELECT i.url,i.status,t.route,t.applied_at FROM items i "
                "LEFT JOIN intake_triage t ON t.item_hash=i.url_hash"
            )}
            self.assertEqual(rows["https://example.com/sports"]["status"], "skipped")
            self.assertIsNotNone(rows["https://example.com/sports"]["applied_at"])
            self.assertEqual(result["saved"]["priority_wakes"], 1)
            self.assertLessEqual(float(store.kv_get(con, "editorial:next_run_at")), time.time())
            with patch.object(config, "INTAKE_TRIAGE_MODE", "enforce"):
                pending = store.pending_items(con, 1)
            self.assertEqual(pending[0]["url"], "https://example.com/bitcoin")
            self.assertNotEqual(pending[0]["url_hash"], ordinary["url_hash"])

    def test_invalid_model_record_fails_open_as_candidate(self):
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [
                feed_item("https://example.com/a", "Ambiguous filing", origin="edgar"),
            ])
            bad = SimpleNamespace(
                stop_reason="tool_use",
                content=[SimpleNamespace(type="tool_use", name="submit_intake_triage",
                                         input={"decisions": []})],
                usage=SimpleNamespace(input_tokens=30, output_tokens=4,
                                      cache_creation_input_tokens=0,
                                      cache_read_input_tokens=0),
            )
            with patch.object(config, "INTAKE_TRIAGE_MODE", "enforce"), \
                    patch.object(intake_triage.client.messages, "create", return_value=bad), \
                    patch.object(config, "RUN_NEWSROOM_MODE", "off"):
                intake_triage.route_cycle(con, inserted, run_id="run-3")
            row = con.execute("SELECT route,outcome FROM intake_triage").fetchone()
            self.assertEqual((row["route"], row["outcome"]),
                             ("candidate", "validation_fail_open"))
            self.assertEqual(con.execute("SELECT status FROM items").fetchone()["status"],
                             "new")

    def test_model_outage_and_budget_exhaustion_both_fail_open(self):
        for budget_available, expected_error in ((True, "RuntimeError"),
                                                 (False, "shared_budget")):
            with self.subTest(budget_available=budget_available), temporary_store() as con:
                inserted = store.upsert_new_items(con, [
                    feed_item(f"https://example.com/{budget_available}", "Bitcoin filing"),
                ])
                reserve = brain.reserve_model_calls if budget_available else lambda _count: None
                with patch.object(config, "INTAKE_TRIAGE_MODE", "enforce"), \
                        patch.object(config, "RUN_NEWSROOM_MODE", "off"), \
                        patch.object(brain, "reserve_model_calls", side_effect=reserve), \
                        patch.object(intake_triage.client.messages, "create",
                                     side_effect=RuntimeError("offline")):
                    intake_triage.route_cycle(con, inserted, run_id="run-4")
                row = con.execute(
                    "SELECT route,outcome,error_kind FROM intake_triage"
                ).fetchone()
                self.assertEqual(row["route"], "candidate")
                self.assertEqual(row["error_kind"], expected_error)

    def test_background_can_be_promoted_once_and_wakes_desk(self):
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [
                feed_item("https://example.com/background", "Sports results"),
            ])
            now = time.time()
            decision = intake_triage._decision(
                inserted[0], route="background", category="unrelated",
                reason="Unrelated.", outcome="model", error_kind="",
                batch_id="batch", now=now,
            )
            store.save_intake_triage(con, [decision], mode="enforce")
            promoted = store.request_operator_action(
                con, inserted[0]["url_hash"], "promote"
            )
            duplicate = store.request_operator_action(
                con, inserted[0]["url_hash"], "promote"
            )
            row = con.execute(
                "SELECT i.status,i.decision_category,t.promoted_at FROM items i "
                "JOIN intake_triage t ON t.item_hash=i.url_hash"
            ).fetchone()
            self.assertTrue(promoted["ok"])
            self.assertFalse(duplicate["ok"])
            self.assertEqual((row["status"], row["decision_category"]),
                             ("new", "promoted"))
            self.assertIsNotNone(row["promoted_at"])

    def test_observe_rows_reconcile_once_when_enforcement_starts(self):
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [
                feed_item("https://example.com/reconcile", "Sports results"),
            ])
            decision = intake_triage._decision(
                inserted[0], route="background", category="unrelated",
                reason="Unrelated.", outcome="model", error_kind="",
                batch_id="batch", now=time.time(),
            )
            store.save_intake_triage(con, [decision], mode="observe")
            first = store.reconcile_intake_triage(con)
            second = store.reconcile_intake_triage(con)
            self.assertEqual((first["applied"], second["seen"]), (1, 0))
            self.assertEqual(con.execute("SELECT status FROM items").fetchone()["status"],
                             "skipped")

    def test_report_exposes_bounded_background_and_promote_control_safely(self):
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [feed_item(
                "https://example.com/background", "Sports <script>alert(1)</script>",
                source="Bad & Feed",
            )])
            decision = intake_triage._decision(
                inserted[0], route="background", category="unrelated",
                reason="No Bitcoin <b>relevance</b>.", outcome="model", error_kind="",
                batch_id="batch", now=time.time(),
            )
            store.save_intake_triage(con, [decision], mode="enforce")
            with patch.object(config, "REPORT_TOKEN", "test-token"):
                html = report.render(con)
            self.assertIn("Intake mailroom", html)
            self.assertIn("SEND TO DESK", html)
            self.assertIn("Sports &lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertIn("No Bitcoin &lt;b&gt;relevance&lt;/b&gt;.", html)


if __name__ == "__main__":
    unittest.main()
