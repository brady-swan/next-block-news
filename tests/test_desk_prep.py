import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nbn import config, desk_prep, store
from tests.support import item, temporary_store


def response_for(decisions):
    block = SimpleNamespace(type="tool_use", name=desk_prep.TOOL["name"],
                            input={"decisions": decisions})
    usage = SimpleNamespace(input_tokens=100, output_tokens=20,
                            cache_creation_input_tokens=0,
                            cache_read_input_tokens=0, cache_creation=None)
    return SimpleNamespace(content=[block], usage=usage)


def decision(candidate_id, route="advance"):
    return {
        "candidate_id": candidate_id, "route": route,
        "event_summary": "A development happened.",
        "bitcoin_relevance": "Potentially relevant to Bitcoin readers.",
        "freshness_note": "Reported today.",
        "research_objective": "Find the most useful source.",
        "source_leads": ["official page"], "related_keys": [],
    }


class DeskPreparationTests(unittest.TestCase):
    @staticmethod
    def saved_item(con, *, url, source="Example", context=""):
        saved = store.upsert_new_items(con, [item(url=url, source=source)])[0]
        con.execute(
            "UPDATE items SET discovery_origin='rss',discovery_context=? WHERE url_hash=?",
            (context, saved["url_hash"]),
        )
        con.commit()
        return dict(con.execute("SELECT * FROM items WHERE url_hash=?",
                                (saved["url_hash"],)).fetchone())

    def test_enforce_backgrounds_ordinary_but_protects_official(self):
        with temporary_store() as con:
            ordinary = self.saved_item(con, url="https://example.com/story")
            official = self.saved_item(
                con, url="https://www.sec.gov/newsroom/press-releases/bitcoin",
                source="SEC",
            )
            api = Mock()
            api.messages.create.return_value = response_for([
                decision(ordinary["url_hash"], "background"),
                decision(official["url_hash"], "background"),
            ])
            with patch.object(desk_prep.anthropic, "Anthropic", return_value=api), \
                    patch.object(desk_prep.brain, "consume_model_call"):
                result = desk_prep.prepare(
                    con, run_id="run-1", inventory=[ordinary, official],
                    coverage_keys=[], continuity_ids=set(), reservation="r",
                    mode="enforce",
                )
            self.assertEqual(result.advanced_ids, (official["url_hash"],))
            statuses = {row["url_hash"]: row["status"] for row in
                        con.execute("SELECT url_hash,status FROM items")}
            self.assertEqual(statuses[ordinary["url_hash"]], "skipped")
            self.assertEqual(statuses[official["url_hash"]], "new")
            rows = store.latest_desk_preparations(
                con, [ordinary["url_hash"], official["url_hash"]]
            )
            self.assertEqual(rows[official["url_hash"]]["model_route"], "background")
            self.assertEqual(rows[official["url_hash"]]["effective_route"], "advance")
            self.assertEqual(rows[official["url_hash"]]["protection_reason"],
                             "official_primary")

    def test_observe_never_suppresses_or_reconciles_later(self):
        with temporary_store() as con:
            row = self.saved_item(con, url="https://example.com/observe")
            api = Mock()
            api.messages.create.return_value = response_for([
                decision(row["url_hash"], "background")
            ])
            with patch.object(desk_prep.anthropic, "Anthropic", return_value=api), \
                    patch.object(desk_prep.brain, "consume_model_call"):
                result = desk_prep.prepare(
                    con, run_id="observe-1", inventory=[row], coverage_keys=[],
                    continuity_ids=set(), reservation="r", mode="observe",
                )
            self.assertEqual(result.advanced_ids, (row["url_hash"],))
            self.assertEqual(con.execute("SELECT status FROM items").fetchone()["status"],
                             "new")
            with patch.object(config, "DESK_PREP_MODE", "enforce"):
                self.assertEqual(con.execute("SELECT status FROM items").fetchone()["status"],
                                 "new")

    def test_incomplete_model_output_fails_open_item_locally(self):
        with temporary_store() as con:
            first = self.saved_item(con, url="https://example.com/one")
            second = self.saved_item(con, url="https://example.com/two")
            api = Mock()
            api.messages.create.return_value = response_for([
                decision(first["url_hash"], "background")
            ])
            with patch.object(desk_prep.anthropic, "Anthropic", return_value=api), \
                    patch.object(desk_prep.brain, "consume_model_call"):
                result = desk_prep.prepare(
                    con, run_id="run-2", inventory=[first, second], coverage_keys=[],
                    continuity_ids=set(), reservation="r", mode="enforce",
                )
            self.assertEqual(result.advanced_ids, (second["url_hash"],))
            saved = store.latest_desk_preparations(con, [second["url_hash"]])
            self.assertEqual(saved[second["url_hash"]]["outcome"],
                             "validation_fail_open")

    def test_all_protected_skips_haiku_and_advances(self):
        with temporary_store() as con:
            row = self.saved_item(
                con, url="https://www.sec.gov/newsroom/press-releases/protected",
                source="SEC",
            )
            constructor = Mock()
            with patch.object(desk_prep.anthropic, "Anthropic", constructor):
                result = desk_prep.prepare(
                    con, run_id="run-protected", inventory=[row], coverage_keys=[],
                    continuity_ids=set(), reservation="r", mode="enforce",
                )
            constructor.assert_not_called()
            self.assertEqual(result.advanced_ids, (row["url_hash"],))
            self.assertFalse(result.diagnostics["called"])

    def test_operator_can_promote_assignment_background(self):
        with temporary_store() as con:
            row = self.saved_item(con, url="https://example.com/promote")
            prep = desk_prep._synthetic(
                row, run_id="run-promote", reason="Background.",
                outcome="model", model_route="background",
            )
            prep["effective_route"] = "background"
            store.save_desk_preparations(con, [prep], mode="enforce")
            result = store.request_operator_action(con, row["url_hash"], "promote")
            self.assertTrue(result["ok"])
            current = con.execute(
                "SELECT status,decision_stage,decision_category FROM items WHERE url_hash=?",
                (row["url_hash"],),
            ).fetchone()
            self.assertEqual(tuple(current), ("new", "operator", "promoted"))
            prepared = store.latest_desk_preparations(con, [row["url_hash"]])
            self.assertIsNotNone(prepared[row["url_hash"]]["promoted_at"])
            self.assertFalse(store.request_operator_action(
                con, row["url_hash"], "promote")["ok"])

    def test_enforcement_persistence_and_status_changes_are_atomic(self):
        with temporary_store() as con:
            first = self.saved_item(con, url="https://example.com/atomic-one")
            second = self.saved_item(con, url="https://example.com/atomic-two")
            rows = []
            for index, item_row in enumerate((first, second)):
                prep = desk_prep._synthetic(
                    item_row, run_id="atomic", reason="Background.",
                    outcome="model", model_route="background",
                )
                prep["effective_route"] = "background"
                prep["prepared_at"] += index
                rows.append(prep)
            con.execute(
                "CREATE TRIGGER fail_second_prep BEFORE INSERT ON desk_preparations "
                f"WHEN NEW.item_hash='{second['url_hash']}' BEGIN "
                "SELECT RAISE(ABORT, 'test rollback'); END"
            )
            with self.assertRaisesRegex(Exception, "test rollback"):
                store.save_desk_preparations(con, rows, mode="enforce")
            self.assertEqual(con.execute(
                "SELECT COUNT(*) n FROM desk_preparations").fetchone()["n"], 0)
            self.assertEqual({row["status"] for row in
                              con.execute("SELECT status FROM items")}, {"new"})


if __name__ == "__main__":
    unittest.main()
