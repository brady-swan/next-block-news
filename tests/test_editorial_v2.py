import time
import unittest
from unittest.mock import Mock, patch

from contextlib import ExitStack

from nbn import (
    brain, config, editor, lint, main, newsroom, publisher, source_policy, sources, store,
    verify,
)
from tests.support import temporary_store


def candidate(item_hash="candidate-1"):
    return {
        "url_hash": item_hash, "source": "SEC", "title": "SEC updates Bitcoin policy",
        "url": "https://www.sec.gov/newsroom/press-releases/test", "published": "",
        "summary": "", "discovery_origin": "rss", "discovery_context": "",
    }


def inspected(fetch_id, url, source, text, *, inspected_at=None):
    ref = source_policy.classify(url, source)
    return newsroom.FetchRecord(
        fetch_id=fetch_id, requested_url=url, final_url=url, canonical_url=url,
        redirect_chain=(url,), source=ref, byline="", text=text,
        content_fingerprint=source_policy.content_fingerprint(text), outcome="ok",
        inspected_at=inspected_at or time.time(),
    )


class EditorialV2Tests(unittest.TestCase):
    def test_v2_materialization_persists_editor_and_typefully_draft_lifecycle(self):
        with temporary_store() as con, ExitStack() as stack:
            saved = store.upsert_new_items(con, [{
                "source": "SEC", "title": "SEC updates Bitcoin policy",
                "url": "https://www.sec.gov/newsroom/press-releases/test",
                "published": "", "summary": "",
            }])[0]
            row = {**candidate(saved["url_hash"]), **saved}
            record = inspected(
                "fetch-sec", row["url"], "SEC",
                "The SEC announced a Bitcoin policy update.",
            )
            ev = verify.EvidenceCandidate(
                record.source, "primary_artifact", True, True, False,
                source_policy.artifact_fingerprint(record.final_url),
                record.content_fingerprint,
            )
            resolution = verify.ResolutionResult(
                row["url_hash"], "sec-bitcoin-policy", row["source"], record.source,
                record.source, record.text, "selected", True, "primary_artifact", True,
                False, record.final_url, ev.primary_artifact_fingerprint,
                record.content_fingerprint, None, "v2 test", (ev,),
                resolver_path="run_newsroom",
            )
            draft = {
                "post": "The SEC announced a Bitcoin policy update.",
                "reader_value": "Policy changed.", "needs_second_source": False,
                "selected_fetch_id": record.fetch_id,
                "evidence_fetch_ids": [record.fetch_id], "_source_text": record.text,
            }
            verdict = {
                **row, "action": "draft", "story_key": "sec-bitcoin-policy",
                "class": "secondary", "reason": "useful",
            }
            attempt = {
                "story_id": "sec", "canonical_key": "sec-bitcoin-policy",
                "identity_valid": True, "members": [row["url_hash"]],
                "headlines": [row["title"]], "submitted_story_key": "sec-policy-update",
                "existing_cluster_key": "", "proposed_post": draft["post"],
                "failure": "", "objective": "", "evidence": [{
                    "inspected_at": record.inspected_at, "requested_url": record.requested_url,
                    "final_url": record.final_url, "canonical_url": record.canonical_url,
                    "source_label": record.source.display_name,
                    "content_fingerprint": record.content_fingerprint, "text": record.text,
                }],
            }
            session = Mock()
            session.conduct.return_value = newsroom.NewsroomOutcome(
                "run:v2-success", {"stories": [{"story_id": "sec"}]}, "a" * 64,
                [verdict], {row["url_hash"]: resolution}, {row["url_hash"]: draft},
                {record.fetch_id: record}, {"rounds": 1}, session,
                {row["url_hash"]: "sec"}, [attempt],
            )
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": True, "decisions": {"sec": {
                    "verdict": "publish", "post": draft["post"], "reason": "clean",
                }},
            }))
            publish = stack.enter_context(patch.object(
                publisher, "publish", return_value=("DRAFT", "typefully-1")
            ))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            result = main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:v2-success",
                inventory=[row], pending=[row],
                result={"held": 0, "skipped": 0, "posted": 0, "drafted": 0,
                        "uncertain": 0, "failed": 0, "taped": 0},
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertEqual(result["drafted"], 1)
            publish.assert_called_once()
            memory = store.newsroom_story_memories(con)[0]
            self.assertEqual(memory["state"], "delivered")
            self.assertEqual(memory["editor"]["verdict"], "publish")
            self.assertEqual(memory["delivery"]["mode"], "DRAFT")
            self.assertFalse(memory["delivery"]["reader_covered"])
            self.assertEqual(store.canonical_story_key(con, "sec-policy-update"),
                             "sec-bitcoin-policy")

    def test_failed_elevated_story_retains_identity_draft_and_evidence(self):
        with temporary_store() as con:
            row = candidate()
            session = newsroom.NewsroomSession(
                run_id="continuity:first", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected(
                "fetch-tftc", "https://tftc.io/tether-lawsuit", "TFTC",
                "A lawsuit alleges Tether froze $42.4 million in USDT.",
            )
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "continuity:first", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"]],
            )
            post = "A lawsuit alleges Tether froze $42.4 million in USDT."
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "tether",
                               "disposition": "publish", "reason": "material allegation"}],
                "stories": [{"story_id": "tether", "story_key": "tether-freeze-lawsuit",
                             "existing_cluster_key": None,
                             "member_candidate_ids": [row["url_hash"]], "post": post,
                             "selected_fetch_id": record.fetch_id,
                             "evidence_fetch_ids": [record.fetch_id],
                             "elevated_claim": True, "reader_value": "Legal control risk.",
                             "reason": "material"}], "run_note": "recommended for delivery",
            })
            self.assertEqual(outcome.verdicts[0]["action"], "hold")
            self.assertEqual(outcome.verdicts[0]["story_key"], "tether-freeze-lawsuit")
            self.assertEqual(outcome.story_attempts[0]["proposed_post"], post)
            self.assertEqual(len(outcome.story_attempts[0]["evidence"]), 1)
            self.assertIn("independent", outcome.story_attempts[0]["objective"])

    def test_cached_evidence_rehydrates_and_one_new_independent_source_clears_gate(self):
        with temporary_store() as con:
            first_text = "A lawsuit alleges Tether froze $42.4 million in USDT."
            first = inspected(
                "fetch-old", "https://tftc.io/tether-lawsuit", "TFTC", first_text,
            )
            store.save_newsroom_story_attempt(con, "tether-freeze-lawsuit", "research_pending", {
                "story_id": "prior", "members": ["prior-hash"],
                "headlines": ["Tether freeze lawsuit"],
                "submitted_story_key": "tether-usdt-freeze-lawsuit",
                "proposed_post": first_text,
                "failure": "defer:elevated_claim_needs_primary_or_two_reports",
                "objective": "Find one independent second report.",
                "evidence": [{"inspected_at": first.inspected_at,
                              "requested_url": first.requested_url,
                              "final_url": first.final_url,
                              "canonical_url": first.canonical_url,
                              "source_label": first.source.display_name,
                              "content_fingerprint": first.content_fingerprint,
                              "text": first.text}],
            })
            row = candidate("new-url-hash")
            session = newsroom.NewsroomSession(
                run_id="continuity:second", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            memory_id = next(value for value in session.fetches if value.startswith("memory_"))
            second = inspected(
                "fetch-block", "https://www.theblock.co/post/tether-lawsuit", "The Block",
                "A court complaint says Tether froze $42.4 million tied to the plaintiff.",
            )
            session.fetches[second.fetch_id] = second
            store.start_newsroom_run(
                con, "continuity:second", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"]],
            )
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "tether",
                               "disposition": "publish", "reason": "now corroborated"}],
                "stories": [{"story_id": "tether", "story_key": "tether-42m-lawsuit",
                             "existing_cluster_key": "tether-freeze-lawsuit",
                             "member_candidate_ids": [row["url_hash"]],
                             "post": "A lawsuit alleges Tether froze $42.4 million in USDT.",
                             "selected_fetch_id": second.fetch_id,
                             "evidence_fetch_ids": [memory_id, second.fetch_id],
                             "elevated_claim": True, "reader_value": "Legal control risk.",
                             "reason": "corroborated"}], "run_note": "recommended for delivery",
            })
            self.assertEqual(outcome.verdicts[0]["action"], "draft")
            self.assertEqual(outcome.verdicts[0]["story_key"], "tether-freeze-lawsuit")
            self.assertNotEqual(memory_id, "fetch-old")

    def test_conflicting_member_families_hold_without_aliasing(self):
        with temporary_store() as con:
            rows = [candidate("one"), candidate("two")]
            rows[0]["story_key"], rows[1]["story_key"] = "event-one", "event-two"
            session = newsroom.NewsroomSession(
                run_id="identity:conflict", inventory=rows, recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected("fetch-good", rows[0]["url"], "SEC", "Bitcoin policy changed.")
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "identity:conflict", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"] for row in rows],
            )
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "merged",
                               "disposition": "publish", "reason": "same"} for row in rows],
                "stories": [{"story_id": "merged", "story_key": "new-merge",
                             "existing_cluster_key": None,
                             "member_candidate_ids": ["one", "two"], "post": "Bitcoin changed.",
                             "selected_fetch_id": record.fetch_id,
                             "evidence_fetch_ids": [record.fetch_id],
                             "elevated_claim": False, "reader_value": "change", "reason": ""}],
                "run_note": "recommended for delivery",
            })
            self.assertTrue(all(row["action"] == "hold" for row in outcome.verdicts))
            self.assertTrue(all(row["reason"] == "defer:identity_conflict"
                                for row in outcome.verdicts))
            self.assertEqual(outcome.story_attempts, [])
            self.assertEqual(store.canonical_story_key(con, "new-merge"), "new-merge")

    def test_expired_or_tampered_cached_evidence_is_not_citable(self):
        with temporary_store() as con:
            now = time.time()
            for key, inspected_at, fingerprint in (
                ("expired-event", now - newsroom.MEMORY_EVIDENCE_MAX_AGE_SECONDS - 1, ""),
                ("tampered-event", now, "not-the-text-fingerprint"),
            ):
                text = f"Bitcoin evidence for {key}."
                store.save_newsroom_story_attempt(con, key, "research_pending", {
                    "story_id": key, "members": [key], "headlines": [key],
                    "proposed_post": text, "failure": "defer:test", "objective": "test",
                    "evidence": [{
                        "inspected_at": inspected_at,
                        "final_url": f"https://example.com/{key}",
                        "content_fingerprint": (fingerprint or
                                                source_policy.content_fingerprint(text)),
                        "text": text,
                    }],
                }, now=now)
            session = newsroom.NewsroomSession(
                run_id="continuity:invalid-cache", inventory=[candidate("fresh")],
                recent_clusters=[], theme_snapshot=[], handles={}, con=con,
                reservation="token",
            )
            self.assertEqual(session.fetches, {})
            packet = session._initial_packet()
            self.assertEqual(sum(len(row["reusable_evidence"])
                                 for row in packet["continuity_board"]), 0)

    def test_editor_feedback_is_context_not_coverage_authority(self):
        with temporary_store() as con:
            store.save_newsroom_story_attempt(con, "facility-shutdown", "editor_feedback", {
                "story_id": "facility", "members": ["older-item"],
                "headlines": ["Company shuts Michigan mining facility"],
                "proposed_post": "The company shut its Michigan mining facility.",
                "evidence": [],
            })
            store.save_newsroom_editor_feedback(
                con, "facility-shutdown", verdict="drop",
                reason="Older general intent appeared to conflict.", post=None,
            )
            session = newsroom.NewsroomSession(
                run_id="continuity:editor", inventory=[candidate("new-related-item")],
                recent_clusters=[], theme_snapshot=[], handles={}, con=con,
                reservation="token",
            )
            packet = session._initial_packet()
            card = packet["continuity_board"][0]
            self.assertEqual(card["editor_feedback_untrusted_context"]["verdict"], "drop")
            clusters = store.story_cluster_context(con)
            cluster = next(row for row in clusters
                           if row["canonical_key"] == "facility-shutdown")
            self.assertFalse(cluster["reader_covered"])
            self.assertFalse(cluster["draft_open"])

    def test_editor_prompt_distinguishes_specific_current_fact_from_old_general_intent(self):
        self.assertIn("facility-specific action", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("older statement of general company", editor.BATCH_EDITOR_PROMPT)

    def test_persisted_cadence_survives_calls_and_can_be_forced(self):
        with temporary_store() as con, patch.object(config, "DESK_INTERVAL_SECONDS", 900):
            self.assertTrue(store.editorial_run_due(con, now=1000))
            self.assertFalse(store.editorial_run_due(con, now=1100))
            self.assertTrue(store.editorial_run_due(con, now=1100, force=True))
            self.assertAlmostEqual(float(store.kv_get(con, "editorial:next_run_at")), 2000)

    def test_small_numeric_presentation_difference_is_not_a_hard_veto(self):
        errors = lint.check_v2(
            "Japan's 10-year yield eased to roughly 3% while the yen traded near 160.",
            {"_source_text": "The 10-year yield was 2.99%. The yen was 159.95 per dollar."},
            {},
        )
        self.assertEqual(errors, [])

    def test_short_separate_quotes_are_checked_independently(self):
        errors = lint.check_v2(
            'Inflation "stalled" in 2025. The Fed can "take a bit more time."',
            {"_source_text": 'Inflation progress stalled in 2025. The Fed can take a bit more time.'},
            {},
        )
        self.assertEqual(errors, [])

    def test_one_bad_story_does_not_sink_valid_story_and_omissions_defer(self):
        with temporary_store() as con:
            rows = [candidate("candidate-1"), candidate("candidate-2"), candidate("candidate-3")]
            session = newsroom.NewsroomSession(
                run_id="cycle:v2", inventory=rows, recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            text = "The SEC announced a Bitcoin policy update."
            ref = source_policy.classify(rows[0]["url"], rows[0]["source"])
            record = newsroom.FetchRecord(
                fetch_id="fetch-good", requested_url=rows[0]["url"],
                final_url=rows[0]["url"], canonical_url=rows[0]["url"],
                redirect_chain=(rows[0]["url"],), source=ref, byline="", text=text,
                content_fingerprint=source_policy.content_fingerprint(text), outcome="ok",
            )
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "cycle:v2", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"] for row in rows],
            )
            dossier = {
                "decisions": [
                    {"candidate_id": "candidate-1", "story_id": "good",
                     "disposition": "publish", "reason": "useful"},
                    {"candidate_id": "candidate-2", "story_id": "bad",
                     "disposition": "publish", "reason": "useful"},
                ],
                "stories": [
                    {"story_id": "good", "story_key": "sec-bitcoin-policy",
                     "member_candidate_ids": ["candidate-1"],
                     "post": "The SEC announced a Bitcoin policy update.",
                     "selected_fetch_id": "fetch-good",
                     "evidence_fetch_ids": ["fetch-good"], "elevated_claim": False,
                     "reader_value": "Policy changed.", "reason": "useful"},
                    {"story_id": "bad", "story_key": "invented",
                     "member_candidate_ids": ["candidate-2"], "post": "Unsupported.",
                     "selected_fetch_id": "fetch-invented",
                     "evidence_fetch_ids": ["fetch-invented"], "elevated_claim": False,
                     "reader_value": "", "reason": ""},
                ], "run_note": "test",
            }
            outcome = session._validate_and_convert_v2(dossier)
            by_hash = {row["url_hash"]: row for row in outcome.verdicts}
            self.assertEqual(by_hash["candidate-1"]["action"], "draft")
            self.assertEqual(by_hash["candidate-2"]["action"], "hold")
            self.assertIn("uninspected", by_hash["candidate-2"]["reason"])
            self.assertEqual(by_hash["candidate-3"]["reason"], "defer:model_output_missing")

    def test_editor_outage_returns_draft_fallback_and_records_usage(self):
        with temporary_store() as con, patch("nbn.brain._create", side_effect=RuntimeError("offline")):
            result = editor.review_newsroom_batch([
                {"story_id": "s1", "post": "Bitcoin policy changed.",
                 "selected_receipt": {}, "inspected_evidence": []}
            ], con, run_id="cycle:editor")
            self.assertFalse(result["ok"])
            usage = store.model_usage_summary(con, time.time() - 60)
            self.assertEqual(usage["calls"], 1)

    def test_newsdesk_outage_never_calls_legacy_triage(self):
        raw = candidate()
        raw.pop("url_hash")
        failed = Mock()
        failed.conduct.side_effect = RuntimeError("offline")
        failed.counters.return_value = {"rounds": 1}
        with temporary_store() as con, ExitStack() as stack:
            stack.enter_context(patch.object(sources, "fetch_feeds", return_value=[raw]))
            stack.enter_context(patch.object(sources, "fetch_edgar", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_perception", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_x", return_value=[]))
            stack.enter_context(patch("nbn.node_discovery.ingest", return_value={"inserted": 0}))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=failed))
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            legacy = stack.enter_context(patch.object(brain, "triage"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            stack.enter_context(patch.object(config, "EDITORIAL_ENGINE", "v2"))
            result = main.cycle(con)
            saved = con.execute("SELECT status,note FROM items").fetchone()
        legacy.assert_not_called()
        self.assertEqual(result["newsroom"]["status"], "deferred")
        self.assertEqual(saved["status"], "new")
        self.assertIn("newsdesk_unavailable", saved["note"])


if __name__ == "__main__":
    unittest.main()
