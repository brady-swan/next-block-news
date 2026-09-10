import json
import unittest

from nbn import store, writer_continuity as continuity, writer_memory
from tests.support import temporary_store


class HandoffOutputTests(unittest.TestCase):
    def deliver(self, con, run, story, key, ref, *, target=None):
        continuity.save_letter(con, run, "Unverified Writer summary", model="test", prompt_version="test")
        store.init_newsroom_story_commits(con, run, [{"story_id": story}], "digest")
        state = store.canonical_output_state(con, key)
        data = {"run_id": run, "story_id": story, "members": [], "body": "Accepted " + run,
                "receipt_url": "https://example.com/source", "klass": "secondary",
                "publisher_backend": "typefully", "coverage_relation": "same_event" if target else "distinct"}
        intent = store.prepare_publisher_mutation(
            con, story_key=key, operation="replace_draft" if target else "create", intended_mode="DRAFT",
            desired_thread=[data["body"]], materialization=data,
            expected_output_signature=state["signature"],
            **({"target_draft_id": ref, "target_post_id": target} if target else {}))
        self.assertTrue(intent["ok"], intent)
        result = store.finalize_publisher_mutation(con, intent["mutation_id"], intent["owner_token"], 1,
                                                 mode="DRAFT", provider_ref=ref, publisher_status="draft")
        self.assertTrue(result["ok"], result)
        return intent["mutation_id"]

    def artifact(self, con, run, key, number):
        con.execute("INSERT INTO writer_artifacts VALUES (?,?, 'receipt','[]',?,'receipt','{}','',1,9999999999)",
                    (f"artifact-{number:02}", run, key))
        con.commit()

    def test_delivered_outputs_survive_missing_or_sibling_tagged_receipts(self):
        with temporary_store() as con:
            self.deliver(con, "run", "dhs-proposal", "dhs-canonical", "dhs-draft")
            self.deliver(con, "run", "ionq", "ionq-canonical", "ionq-draft")
            self.artifact(con, "run", "liquid-wrong-sibling", 0)
            self.artifact(con, "run", "ionq-canonical", 1)
            out = continuity.handoff(con, "run")
            self.assertEqual({r["event_key"] for r in out["actual_outputs"]},
                             {"dhs-canonical", "ionq-canonical", "liquid-wrong-sibling"})
            live = {r["event_key"]: r["output"] for r in out["actual_outputs"]}
            self.assertIsNone(live["liquid-wrong-sibling"])
            self.assertEqual(live["dhs-canonical"]["mode"], "DRAFT")
            self.assertFalse(live["dhs-canonical"]["reader_covered"])
            self.assertNotIn("body", live["dhs-canonical"])
            self.assertEqual(out["body"], "Unverified Writer summary")

    def test_only_exact_confirmed_deliveries_supply_keys(self):
        changes = [
            ("UPDATE newsroom_story_commits SET state=?", "held"),
            ("UPDATE newsroom_story_commits SET delivery_ref=?", ""),
            ("UPDATE newsroom_story_commits SET delivery_ref=?", "wrong-ref"),
            ("UPDATE publisher_mutations SET state=?", "ambiguous"),
            ("UPDATE publisher_mutations SET state=?", "definite_failure"),
            ("UPDATE publisher_mutations SET materialization_json=?", "not-json"),
            ("UPDATE publisher_mutations SET materialization_json=?", "[]"),
            ("UPDATE publisher_mutations SET materialization_json=?", "{}"),
            ("UPDATE publisher_mutations SET materialization_json=?", json.dumps({"run_id": "other", "story_id": "story"})),
            ("UPDATE publisher_mutations SET materialization_json=?", json.dumps({"run_id": "run", "story_id": "other"})),
        ]
        for query, value in changes:
            with self.subTest(query=query, value=value), temporary_store() as con:
                self.deliver(con, "run", "story", "canonical", "shared-ref")
                con.execute(query, (value,))
                con.commit()
                self.assertEqual(continuity.handoff(con, "run")["actual_outputs"], [])

    def test_old_letter_keeps_current_output_after_replacement(self):
        with temporary_store() as con:
            original = self.deliver(con, "first", "old-story", "canonical", "same-draft")
            post = writer_memory.publication(con, "canonical")
            replacement = self.deliver(con, "second", "new-story", "canonical", "same-draft", target=post["id"])
            self.assertNotEqual(original, replacement)
            self.assertEqual(con.execute("SELECT mutation_id FROM posts WHERE id=?", (post["id"],)).fetchone()[0], replacement)
            for run in ("first", "second"):
                output = continuity.handoff(con, run)["actual_outputs"]
                self.assertEqual([r["event_key"] for r in output], ["canonical"])
                self.assertEqual(output[0]["output"]["id"], post["id"])
            self.assertEqual(writer_memory.publication(con, "canonical")["body"], "Accepted second")

    def test_deliveries_precede_artifacts_with_deterministic_dedup_and_bound(self):
        with temporary_store() as con:
            self.deliver(con, "run", "b-story", "b-key", "b-draft")
            self.deliver(con, "run", "a-story", "a-key", "a-draft")
            con.execute("UPDATE newsroom_story_commits SET updated_at=1")
            con.commit()
            for i, key in enumerate(["a-key", "a-key"] + [f"fallback-{i}" for i in range(10)]):
                self.artifact(con, "run", key, i)
            expected = ["a-key", "b-key"] + [f"fallback-{i}" for i in range(6)]
            for _ in range(2):
                self.assertEqual([r["event_key"] for r in continuity.handoff(con, "run")["actual_outputs"]], expected)

    def test_output_status_and_confirmed_body_use_existing_publication_semantics(self):
        with temporary_store() as con:
            self.deliver(con, "run", "story", "canonical", "draft")
            con.execute("UPDATE posts SET publisher_status='published',confirmed_at=2")
            con.commit()
            output = continuity.handoff(con, "run")["actual_outputs"][0]["output"]
            self.assertTrue(output["reader_covered"])
            self.assertNotIn("body", output)
            self.assertNotIn("body", output["confirmed_output"])
            for state in ("deleted", "inactive"):
                con.execute("UPDATE posts SET publisher_status=?", (state,))
                con.commit()
                self.assertIsNone(continuity.handoff(con, "run")["actual_outputs"][0]["output"])


if __name__ == "__main__":
    unittest.main()
