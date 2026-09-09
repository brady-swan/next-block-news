import copy
import json
import time
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

from nbn import (brain, config, desk_prep, editor, main, memory_search, models, newsroom,
                 publisher, sources, store, writer_continuity as continuity, writer_memory)
from tests.support import temporary_store
from tests.test_editorial_v2 import inspected


def watch(con, key="incident", question="Have affected users recovered their funds?"):
    store.save_newsroom_story_attempt(con, key, "research_pending", {
        "members": [], "evidence": [], "objective": question, "headlines": [key]})
    value = {"followup_id": None, "base_revision": None, "context_id": "notebook:"+key,
        "question": question, "source_paths": ["https://www.sec.gov/newsroom/press-releases/test"],
        "next_check_minutes": 15, "state": "open", "result": "pending", "note": "Watch original statement."}
    continuity.apply_updates(con, "origin:"+key, [value], allowed_contexts={"notebook:"+key}, inventory=[])
    con.execute("UPDATE writer_followups SET next_check_at=0")
    con.commit()
    return continuity.active(con)[-1]


def desk_session(con, inventory, rid="cycle:continuity-test"):
    with patch.object(config, "NEWSROOM_MODEL", "grok-4.3"):
        session = newsroom.NewsroomSession(run_id=rid, inventory=inventory, recent_clusters=[],
            theme_snapshot=[], handles={}, con=con, reservation="test", prep_mode="off",
            research_mode="on", compact_enabled=True)
    store.start_newsroom_run(con, rid, "live", "grok-4.3", newsroom.PROMPT_VERSION,
                            [i["url_hash"] for i in inventory])
    return session


class ContinuityTests(unittest.TestCase):
    def test_due_assignment_identity_recovery_and_normal_cadence(self):
        with temporary_store() as con:
            watch(con)
            first = continuity.due_assignments(con)
            self.assertEqual(len(first), 1)
            self.assertFalse(first[0].get("story_key"))
            self.assertEqual(first[0]["published"], "")
            self.assertEqual(continuity.due_assignments(con)[0]["url_hash"], first[0]["url_hash"])
            self.assertEqual(store.pending_items(con, 25), [])
            self.assertEqual(desk_prep.protection_reason(first[0], set()), "scheduled_followup")
            desk = desk_session(con, first)
            self.assertIn("incident", desk.supplied_cluster_keys)
            packet = desk._initial_packet()
            self.assertEqual(packet["intake_board"][0]["reporting_assignment"]["followup_id"], first[0]["_followup"]["followup_id"])
            with patch.object(sources, "fetch_article") as fetch:
                desk.prefetch_prepared_receipts()
                fetch.assert_not_called()

    def test_no_change_preserves_signal_date_and_check_history(self):
        with temporary_store() as con:
            w = watch(con)
            rows = continuity.due_assignments(con)
            continuity.begin_assignments(con, "check:one", rows)
            value = {**w, "base_revision": w["revision"], "next_check_minutes": 120,
                     "result": "no_change", "note": "The original status page still reports investigation."}
            self.assertEqual(continuity.apply_updates(con, "check:one", [value],
                allowed_contexts=set(), inventory=rows)["accepted"], 1)
            continuity.finish_assignments(con, "check:one", rows)
            self.assertEqual(continuity.checks(con, "check:one")[0]["status"], "no_change")
            self.assertFalse(continuity.due_assignments(con))
            self.assertEqual(continuity.active(con)[0]["last_result"], "no_change")
            self.assertEqual(continuity.apply_updates(con, "check:one", [value],
                allowed_contexts=set(), inventory=rows)["accepted"], 0)
            # Internal checks are not new external signals for a storyline.
            con.execute("INSERT INTO newsroom_storylines VALUES (?,?,?,?,?,?,?,?,?,?)",
                ("security-watch", "Custody security", "Still investigating", "open", "[]", "watch", 1, 1, 123, 1))
            con.commit()
            update = {"storyline_key": "security-watch", "base_revision": 1, "title": "Custody security",
                "state_summary": "Still no change", "lifecycle": "open", "watch_for": ["Resolution"],
                "relationship": "continuing", "candidate_ids": [rows[0]["url_hash"]], "update_reason": "Checked"}
            result = store.apply_newsroom_storyline_updates(con, run_id="signal-check", updates=[update],
                allowed_existing_keys={"security-watch"})
            self.assertEqual(result["updated"], 1)
            self.assertEqual(con.execute("SELECT last_signal_at FROM newsroom_storylines").fetchone()[0], 123)
            update.update(base_revision=2, candidate_signal_times={rows[0]["url_hash"]: 456})
            store.apply_newsroom_storyline_updates(con, run_id="genuine-signal", updates=[update],
                allowed_existing_keys={"security-watch"})
            self.assertEqual(con.execute("SELECT last_signal_at FROM newsroom_storylines").fetchone()[0], 456)

    def test_missing_report_never_reopens_delivered_or_uncertain_item(self):
        for status in ("drafted", "posted", "uncertain", "held"):
            with self.subTest(status=status), temporary_store() as con:
                watch(con)
                rows = continuity.due_assignments(con)
                continuity.begin_assignments(con, "run:delivered", rows)
                con.execute("UPDATE items SET status=?,story_key='new-event'", (status,))
                con.commit()
                continuity.finish_assignments(con, "run:delivered", rows)
                self.assertEqual(con.execute("SELECT status FROM items").fetchone()[0], status)
                self.assertEqual(continuity.active(con)[0]["last_result"], "inconclusive")
                self.assertFalse(continuity.active(con)[0]["queued_assignment"])
                self.assertFalse(continuity.due_assignments(con))

    def test_backed_off_checks_do_not_starve_later_watches_or_erase_history(self):
        with temporary_store() as con:
            for i in range(3):
                watch(con, key=f"incident-{i}")
            first = continuity.due_assignments(con)
            continuity.begin_assignments(con, "check:one", first)
            continuity.finish_assignments(con, "check:one", first)
            later = continuity.due_assignments(con)
            self.assertEqual(len(later), 1)
            self.assertNotIn(later[0]["url_hash"], {r["url_hash"] for r in first})
            continuity.begin_assignments(con, "check:two", first)
            continuity.finish_assignments(con, "check:two", first)
            self.assertEqual(len(continuity.checks(con, "check:one")), 2)
            self.assertEqual(len(continuity.checks(con, "check:two")), 2)

    def test_due_only_new_development_reaches_normal_editor_and_draft(self):
        with temporary_store() as con, ExitStack() as stack:
            w = watch(con)
            rows = continuity.due_assignments(con)
            continuity.begin_assignments(con, "cycle:continuity-test", rows)
            desk = desk_session(con, rows)
            record = inspected("new-receipt", "https://www.sec.gov/newsroom/press-releases/new", "SEC",
                               "The SEC announced a new Bitcoin custody policy.")
            desk.fetches[record.fetch_id] = record
            letter = "A distinct custody-policy development emerged; the earlier incident remains unresolved."
            value = {"shift_letter": letter, "run_note": "New sourced development", "storyline_updates": [],
                "follow_up_updates": [{**w, "base_revision": w["revision"], "next_check_minutes": 180,
                    "result": "development", "note": "An original SEC announcement adds a new policy development."}],
                "decisions": [{"candidate_id": rows[0]["url_hash"], "story_id": "new", "disposition": "publish", "reason": "New policy"}],
                "stories": [{"story_id": "new", "story_key": "new-custody-policy", "existing_cluster_key": None,
                    "coverage_relation": "distinct", "member_candidate_ids": [rows[0]["url_hash"]],
                    "post": "The SEC announced a new Bitcoin custody policy.", "selected_fetch_id": record.fetch_id,
                    "evidence_fetch_ids": [record.fetch_id], "reader_value": "A consequential custody change", "elevated_claim": False}]}
            self.assertFalse(desk._identity_repairs(value))
            desk.messages = [{"role": "user", "content": "fixture"}]
            outcome = desk._validate_and_convert_v2(value)
            self.assertEqual(outcome.verdicts[0]["action"], "draft")
            stack.enter_context(patch.object(desk, "conduct", return_value=outcome))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=desk))
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="test"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            review = stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": True, "decisions": {"new": {"verdict": "publish", "post": value["stories"][0]["post"], "reason": "Supported"}}}))
            send = stack.enter_context(patch.object(publisher, "publish", return_value=("DRAFT", "test-draft")))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            store.acquire_cycle_lease(con, "test-owner")
            result = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id=desk.run_id,
                inventory=rows, pending=rows, result={k: 0 for k in ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                theme_snapshot=[], overrides={}, run_started=time.time())
            review.assert_called_once()
            send.assert_called_once()
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(continuity.handoff(con, desk.run_id)["body"], letter)
            self.assertEqual(continuity.checks(con, desk.run_id)[0]["status"], "development")

    def test_required_no_post_letter_uses_one_shared_correction_slot(self):
        with temporary_store() as con:
            watch(con)
            rows = continuity.due_assignments(con)
            desk = desk_session(con, rows)
            calls = []
            def respond(**kwargs):
                calls.append(kwargs)
                desk.successful_newsdesk_calls += 1
                value = {"decisions": [{"candidate_id": rows[0]["url_hash"], "disposition": "drop", "reason": "No change"}], "stories": []}
                if len(calls) == 2:
                    value["shift_letter"] = "The original notice remains unchanged; check the maintainer response tomorrow."
                return models.normalize({"status": "completed", "output": [{"type": "function_call",
                    "call_id": f"dossier-{len(calls)}", "name": "submit_editorial_dossier", "arguments": json.dumps(value)}]}, provider="xai", effort="medium")
            with patch.object(desk, "prepare_desk"), patch.object(desk, "_call", side_effect=respond):
                result = desk.conduct_v2()
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[-1]["tools"], [newsroom.V2_DOSSIER_TOOL])
            self.assertEqual(result.verdicts[0]["action"], "skip")
            self.assertIn("maintainer", continuity.handoff(con, desk.run_id)["body"])
            continuity.save_letter(con, desk.run_id, "Do not replace original", model="x", prompt_version="x")
            self.assertIn("maintainer", continuity.handoff(con, desk.run_id)["body"])

    def test_completed_development_with_deferred_output_reuses_same_candidate(self):
        with temporary_store() as con:
            w = watch(con)
            rows = continuity.due_assignments(con)
            continuity.begin_assignments(con, "research", rows)
            value = {**w, "base_revision": w["revision"], "next_check_minutes": 15,
                     "result": "development", "note": "A new official update warrants a story."}
            continuity.apply_updates(con, "research", [value], allowed_contexts=set(), inventory=rows)
            # Editor transport/capacity defers the story after research completed.
            con.execute("UPDATE items SET defer_until=?", (time.time()+3600,))
            con.execute("UPDATE writer_followups SET next_check_at=0")
            con.commit()
            self.assertFalse(continuity.due_assignments(con))
            con.execute("UPDATE items SET defer_until=0")
            con.commit()
            retry = continuity.due_assignments(con)
            self.assertEqual([i['url_hash'] for i in retry], [rows[0]['url_hash']])
            self.assertTrue(retry[0]['_followup']['completed_check_reporting_retry'])
            continuity.begin_assignments(con, "delivery-retry", retry)
            continuity.finish_assignments(con, "delivery-retry", retry)
            self.assertEqual(continuity.checks(con, "research")[0]['status'], 'development')
            self.assertEqual(continuity.checks(con, "delivery-retry")[0]['status'], 'reporting_retry')
            con.execute("UPDATE items SET status='drafted'")
            con.execute("UPDATE writer_followups SET next_check_at=?", (time.time()+3600,))
            con.commit()
            self.assertFalse(continuity.due_assignments(con))

    def test_handoff_includes_editor_drop_without_linked_artifacts(self):
        with temporary_store() as con:
            continuity.save_letter(con, "prior", "This looks ready, pending Editor.", model="test", prompt_version="test")
            store.start_newsroom_run(con, "prior", "live", "test", "test", [])
            store.init_newsroom_story_commits(con, "prior", [{"story_id": "s", "state": "pending", "details": {}}], "digest")
            store.set_newsroom_story_state(con, "prior", "s", "held", details={"editor": {"verdict": "drop", "reason": "Already covered"}})
            letter = continuity.handoff(con, "prior")
            self.assertEqual(letter["actual_story_outcomes"][0]["editor_reason"], "Already covered")
            self.assertEqual(letter["body"], "This looks ready, pending Editor.")

    def test_target_type_is_not_granted_by_reading_a_letter(self):
        with temporary_store() as con:
            row = watch(con)
            update = {**row, "followup_id": None, "context_id": "letter:read", "next_check_minutes": 60}
            self.assertEqual(continuity.apply_updates(con, "bad", [update],
                allowed_contexts={"letter:read"}, inventory=[])["ignored"], 1)


class HybridMemoryTests(unittest.TestCase):
    def test_partial_keywords_run_ids_and_feedback_exclusion(self):
        with temporary_store() as con, patch.object(config, "MEMORY_EMBED_URL", ""):
            continuity.save_letter(con, "cycle:quiet", "Capital controls block family savings; watch the official decree.", model="test", prompt_version="test")
            self.assertTrue(writer_memory.catalog(con, query="currency repression capital") ["rows"])
            self.assertEqual(writer_memory.catalog(con, query="cycle:quiet")["rows"][0]["context_id"], "letter:cycle:quiet")
            self.assertEqual(memory_search.prose({"text": "safe", "desk_feedback": {"text": "private"}}), ["safe"])

    def test_version_changes_reembed_and_deleted_records_cannot_return(self):
        with temporary_store() as con, patch.object(config, "MEMORY_EMBED_URL", "http://local-test"), \
                patch.object(memory_search, "model_digest", return_value="a"*64), \
                patch.object(memory_search, "embed", side_effect=lambda texts, **k: [[1.0]+[0.0]*767 for _ in texts]) as emb:
            continuity.save_letter(con, "one", "Permissionless savings and capital controls.", model="test", prompt_version="test")
            memory_search.index_batch(con)
            self.assertEqual(emb.call_count, 1)
            memory_search.index_batch(con)
            self.assertEqual(emb.call_count, 1)
            with patch.object(memory_search, "VERSION", "changed-prefix-contract"):
                memory_search.index_batch(con)
            self.assertEqual(emb.call_count, 2)
            con.execute("DELETE FROM writer_handoffs")
            con.commit()
            self.assertFalse(writer_memory.catalog(con, query="capital")["rows"])

    def test_malformed_tags_and_timeout_fall_back(self):
        with temporary_store() as con, patch.object(config, "MEMORY_EMBED_URL", "http://local-test"):
            continuity.save_letter(con, "one", "Useful custody report", model="test", prompt_version="test")
            for body in ([], {"models": [None]}, {"models": {}}):
                with self.subTest(body=body), patch.object(memory_search.httpx, "get", return_value=httpx.Response(200, json=body, request=httpx.Request("GET", "http://local-test"))):
                    result = writer_memory.catalog(con, query="custody")
                    self.assertTrue(result["rows"])
                    self.assertIn("fallback", result["retrieval"]["mode"])
            with patch.object(memory_search.httpx, "post", return_value=httpx.Response(200, json=[], request=httpx.Request("POST", "http://local-test"))):
                with self.assertRaises(ValueError):
                    memory_search.embed(["test"])

    def test_expert_interaction_keeps_actor_and_parent_dates(self):
        tweet = {"id": "123", "author_id": "one", "text": "Important correction", "created_at": "2026-09-09",
            "referenced_tweets": [{"type": "replied_to", "id": "122"}],
            "entities": {"urls": [{"expanded_url": "https://example.org/statement"}]}}
        includes = {"users": [{"id": "one", "username": "lopp"}, {"id": "two", "username": "origin"}],
            "tweets": [{"id": "122", "author_id": "two", "text": "Original", "created_at": "2026-09-08"}]}
        item = sources._x_item(tweet, includes, sources.X_EXPERT_QUERIES[1], time.time())
        self.assertEqual(item["url"], "https://x.com/lopp/status/123")
        material = json.loads(item["source_material"])
        self.assertEqual(material["referenced_posts"][0]["post"]["published_at"], "2026-09-08")
        self.assertIn("expert_signal", json.loads(item["discovery_context"]))


if __name__ == "__main__":
    unittest.main()
