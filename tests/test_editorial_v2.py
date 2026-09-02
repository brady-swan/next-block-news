import time
import unittest
from unittest.mock import Mock, patch

from contextlib import ExitStack

from nbn import brain, config, editor, lint, main, newsroom, source_policy, sources, store
from tests.support import temporary_store


def candidate(item_hash="candidate-1"):
    return {
        "url_hash": item_hash, "source": "SEC", "title": "SEC updates Bitcoin policy",
        "url": "https://www.sec.gov/newsroom/press-releases/test", "published": "",
        "summary": "", "discovery_origin": "rss", "discovery_context": "",
    }


class EditorialV2Tests(unittest.TestCase):
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
