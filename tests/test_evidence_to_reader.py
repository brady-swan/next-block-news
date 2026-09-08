"""Plan 0065: completed research survives the editor and memory boundaries."""
import json
import time
import unittest
from contextlib import ExitStack
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from nbn import brain, config, editor, main, newsroom, publisher, source_policy, sources, store, writer_memory
from tests.support import item, temporary_store
from tests.test_editorial_v2 import inspected, materialization_fixture
from tests.test_reporter_writer import session


def answer(decisions):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"decisions": decisions}))],
        usage=SimpleNamespace(input_tokens=100, output_tokens=30, cache_creation_input_tokens=0,
                              cache_read_input_tokens=0, cache_creation=None), stop_reason="end_turn")


def card(key="s1", evidence=()):
    rows = list(evidence)
    return {"story_id": key, "post": "Useful Bitcoin context.", "inspected_evidence": rows,
            "selected_receipt": {"fetch_id": rows[0]["fetch_id"]} if rows else {}}


class EvidenceToReaderTests(unittest.TestCase):
    def research(self, text=None, fid="blog"):
        return editor.receipt_card(inspected(fid, "https://opensats.org/blog/" + fid,
            "OpenSats", text or ("Operating funds are raised separately. " + "context " * 600)))

    def test_appendix_is_clipped_unassigned_and_yields_to_baseline(self):
        research = self.research()
        baseline, _ = editor._batch_editor_payload([card()], [])
        payload, deferred = editor._batch_editor_payload([card()], [], research=[research] * 2)
        self.assertFalse(deferred)
        self.assertEqual(payload["candidates"], baseline["candidates"])
        self.assertEqual(payload["evidence_catalog"], [])
        receipt = payload["unassigned_run_research"]["receipts"][0]
        self.assertEqual(len(receipt["text"]), 2000)
        self.assertTrue(receipt["text_truncated"])
        self.assertEqual(receipt["content_fingerprint"], source_policy.content_fingerprint(receipt["text"]))
        self.assertEqual(receipt["original_content_fingerprint"], research["content_fingerprint"])
        self.assertIn("unseen remainder", receipt["excerpt_note"])
        with patch.object(editor, "EDITOR_PAYLOAD_MAX_BYTES", editor._payload_bytes(baseline) + 1):
            tight, deferred = editor._batch_editor_payload([card()], [], research=[research])
        self.assertEqual(tight, baseline)
        self.assertFalse(deferred)

    def test_appendix_record_byte_and_selected_evidence_limits(self):
        rows = [self.research(fid=str(i)) for i in range(20)]
        payload, _ = editor._batch_editor_payload([card(evidence=[rows[0]])], [], research=rows)
        appendix = payload["unassigned_run_research"]
        self.assertLessEqual(len(appendix["receipts"]), 8)
        self.assertEqual(len(appendix["receipts"]) + appendix["omitted"], 19)
        self.assertNotIn("0", [r["fetch_id"] for r in appendix["receipts"]])
        self.assertLessEqual(editor._payload_bytes(appendix), editor.EDITOR_RESEARCH_MAX_BYTES)
        self.assertLessEqual(editor._payload_bytes(payload), editor.EDITOR_PAYLOAD_MAX_BYTES)

    def test_full_source_caveats_survive_excerpt_clipping(self):
        raw = {**self.research(), "retrieval_kind": "provider_reported_extract",
               "limitations": "Native paraphrase. " + "Caveat. " * 50 + "Not independently confirmed."}
        payload, _ = editor._batch_editor_payload([card()], [], research=[raw])
        shown = payload["unassigned_run_research"]["receipts"][0]
        self.assertEqual(shown["limitations"], raw["limitations"])
        self.assertTrue(shown["text_truncated"])

    def test_invalid_refs_are_atomic_and_total_evidence_cap_counts_captures(self):
        payload, _ = editor._batch_editor_payload([card()], [], research=[self.research()])
        c = payload["candidates"][0]
        ref = payload["unassigned_run_research"]["receipts"][0]["evidence_ref"]
        valid = {"verdict": "revise", "post": "Useful.", "additional_evidence_refs": [ref]}
        self.assertEqual(editor._editor_decision(valid, payload, c, "initial")["additional_evidence_refs"], [ref])
        for bad in ([ref, "unseen"], "not-list", [None], [ref] * 9):
            with self.subTest(bad=bad):
                self.assertIsNone(editor._editor_decision({**valid, "additional_evidence_refs": bad}, payload, c, "initial"))
        self.assertIsNone(editor._editor_decision(valid, payload, {**c, "evidence_records_used": 8}, "initial"))
        legacy = editor._editor_decision({"verdict": "publish", "post": "Useful."}, payload, c, "initial")
        self.assertEqual(legacy["additional_evidence"], [])
        self.assertIsNone(editor._editor_decision({**valid, "verdict": []}, payload, c, "initial"))

    def test_invalid_first_pass_recovers_only_omitted_with_same_excerpt(self):
        sent = []
        def create(_model, _system, raw, **_kwargs):
            p = json.loads(raw)
            sent.append(p)
            if len(sent) == 1:
                return answer([{"story_id": "s1", "verdict": "publish", "post": "First."},
                    {"story_id": "s2", "verdict": "revise", "post": "Bad ref.", "additional_evidence_refs": ["unknown"]}])
            ref = p["unassigned_run_research"]["receipts"][0]["evidence_ref"]
            return answer([{"story_id": "s2", "verdict": "revise", "post": "Recovered.", "additional_evidence_refs": [ref]}])
        with temporary_store() as con, patch.object(brain, "_create", side_effect=create):
            result = editor.review_newsroom_batch([card("s1"), card("s2")], con,
                run_id="test:recovery", research=[self.research()])
        self.assertEqual(len(sent), 2)
        self.assertEqual([r["story_id"] for r in sent[1]["candidates"]], ["s2"])
        self.assertEqual(sent[1]["unassigned_run_research"], sent[0]["unassigned_run_research"])
        self.assertEqual(result["decisions"]["s1"]["post"], "First.")
        self.assertEqual(len(result["decisions"]["s2"]["additional_evidence"]), 1)

    def test_recovery_never_overflows_payload_or_selects_removed_excerpt(self):
        base, _ = editor._batch_editor_payload([card()], [])
        research = self.research("Small inspected original source. 日本語 €")
        roomy, _ = editor._batch_editor_payload([card()], [], research=[research])
        sent = []
        def create(_model, _system, raw, **_kwargs):
            p = json.loads(raw)
            sent.append(p)
            self.assertEqual(len(raw.encode()), editor._payload_bytes(p))
            return answer([{"story_id": "s1", "verdict": "revise", "post": "Unknown.",
                            "additional_evidence_refs": ["not-shown"]}])
        with temporary_store() as con, patch.object(editor, "EDITOR_PAYLOAD_MAX_BYTES", editor._payload_bytes(roomy)), \
                patch.object(brain, "_create", side_effect=create):
            result = editor.review_newsroom_batch([card()], con, run_id="recovery:tight", research=[research])
        self.assertEqual(len(sent), 2)
        self.assertTrue(all(editor._payload_bytes(p) <= editor._payload_bytes(roomy) for p in sent))
        self.assertFalse(result["decisions"])
        self.assertEqual(sent[1]["candidates"], base["candidates"])

    def test_malformed_verdict_does_not_discard_valid_sibling(self):
        first = answer([{"story_id": "s1", "verdict": "publish", "post": "Keep me."},
                        {"story_id": "s2", "verdict": [], "post": "Malformed."}])
        second = answer([{"story_id": "s2", "verdict": "drop", "post": None}])
        with temporary_store() as con, patch.object(brain, "_create", side_effect=[first, second]) as create:
            result = editor.review_newsroom_batch([card("s1"), card("s2")], con, run_id="malformed:sibling")
            self.assertTrue(result["ok"])
            self.assertEqual(result["decisions"]["s1"]["post"], "Keep me.")
            self.assertEqual([r["story_id"] for r in json.loads(create.call_args_list[1].args[2])["candidates"]], ["s2"])

    def _materialize(self, *, quote_beyond_excerpt=False, invalid_refs=False, native=False):
        with temporary_store() as con, ExitStack() as stack:
            run_id = "run:evidence-to-reader"
            row, selected, _draft, fake = materialization_fixture(con, run_id)
            outcome = fake.conduct.return_value
            text = "Operating funds are raised separately. " + "Context. " * 260 + "Only the invisible remainder says this."
            blog = inspected("blog", "https://opensats.org/blog/operations", "OpenSats", text)
            if native:
                blog = replace(blog, retrieval_kind="provider_reported_extract", limitations="Native paraphrase, not verbatim.")
            unrelated = inspected("unrelated", "https://www.sec.gov/other", "SEC", "Other event.")
            historical = replace(unrelated, fetch_id="memory_old", adapter_provenance="newsroom_story_memory")
            outcome.fetches.update({r.fetch_id: r for r in (blog, unrelated, historical)})
            writer_memory.save(con, run_id, "blog", "receipt", {"fetch_id": "blog", "text": text}, title="Blog")
            sent = []
            def create(_model, _system, raw, **_kwargs):
                p = json.loads(raw)
                sent.append(p)
                entries = p["unassigned_run_research"]["receipts"]
                receipt = next(r for r in entries if r["fetch_id"] == "blog")
                post = ('The SEC announced a Bitcoin policy update.\n\n"Only the invisible remainder says this."'
                        if quote_beyond_excerpt else 'The SEC announced a Bitcoin policy update.\n\nOperating funds are raised separately.'
                        if native else 'The SEC announced a Bitcoin policy update.\n\n"Operating funds are raised separately."')
                return answer([{"story_id": "sec", "verdict": "revise", "post": post, "reason": "Useful original context.",
                    "additional_evidence_refs": ["invalid"] if invalid_refs else [receipt["evidence_ref"]]}])
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="test"))
            stack.enter_context(patch.object(brain, "_create", side_effect=create))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=fake))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", False))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            publish = stack.enter_context(patch.object(publisher, "publish", return_value=("DRAFT", "test-draft")))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            result = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id=run_id,
                inventory=[row], pending=[row], result={k: 0 for k in ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")},
                theme_snapshot=[], overrides={}, run_started=time.time())
            self.assertNotIn("memory_old", json.dumps(sent))
            pool = json.loads(con.execute("SELECT evidence_pool_json FROM newsroom_story_memory").fetchone()[0])
            if invalid_refs:
                self.assertEqual(len(sent), 2)
                self.assertEqual(result["drafted"], 1)
                self.assertTrue(publish.call_args.kwargs["force_draft"])
                self.assertNotIn("Operating funds", str(publish.call_args))
                self.assertNotIn(blog.final_url, json.dumps(pool))
                return
            self.assertNotIn(unrelated.final_url, json.dumps(pool))
            retained = next(r for r in pool if r["final_url"] == blog.final_url)
            self.assertEqual(len(retained["text"]), 2000)
            self.assertTrue(retained["truncated"])
            self.assertEqual(retained["original_content_fingerprint"], blog.content_fingerprint)
            self.assertEqual(retained["retrieval_kind"], blog.retrieval_kind)
            if native:
                self.assertIn("Native paraphrase", retained["limitations"])
            with patch.object(newsroom, "_cached_url_is_public", return_value=True):
                next_desk = session(con)
            restored = next(r for r in next_desk.fetches.values() if r.final_url == blog.final_url)
            self.assertEqual(restored.text, retained["text"])
            self.assertEqual(restored.original_content_fingerprint, blog.content_fingerprint)
            self.assertTrue(restored.text_truncated)
            self.assertEqual(restored.retrieval_kind, blog.retrieval_kind)
            if native:
                self.assertFalse(restored.direct_primary)
                self.assertFalse(restored.independent_report)
            self.assertEqual(con.execute("SELECT canonical_key FROM writer_artifacts").fetchone()[0], "sec-bitcoin-policy")
            if quote_beyond_excerpt:
                publish.assert_not_called()
                self.assertGreater(result["held"], 0)
            else:
                self.assertEqual(result["drafted"], 1)
                self.assertIn("Operating funds", str(publish.call_args))
                self.assertIn(selected.final_url, str(publish.call_args))
                self.assertNotIn(blog.final_url, str(publish.call_args))

    def test_opensats_omitted_blog_survives_editor_and_memory(self):
        self._materialize()

    def test_native_appendix_does_not_become_direct_evidence(self):
        self._materialize(native=True)

    def test_quote_in_unseen_remainder_is_not_supported(self):
        self._materialize(quote_beyond_excerpt=True)

    def test_unresolved_invalid_refs_stage_only_original_with_zero_additions(self):
        self._materialize(invalid_refs=True)

    def test_mempool_shell_is_not_a_receipt_but_short_real_page_is(self):
        for text, valid in (("mempool - Bitcoin Explorer", False), ("Bitcoin block explorer maintenance starts Tuesday.", True)):
            url = "https://mempool.space/tx/test"
            response = httpx.Response(200, text=f"<title>{text}</title>", request=httpx.Request("GET", url))
            with self.subTest(text=text), temporary_store() as con, patch.object(sources, "_assert_public_http_url"), \
                    patch.object(sources.httpx, "Client") as client:
                client.return_value.__enter__.return_value.get.return_value = response
                desk = session(con)
                result = desk._fetch(url)
                self.assertEqual(result["ok"], valid)
                self.assertEqual(bool(desk.fetches), valid)

    def test_bitcoin_magazine_blank_and_ambiguous_bodies_keep_fallback(self):
        for bodies in ('<div class="td-post-content"></div>',
                       '<div class="td-post-content">First.</div><div class="td-post-content">Second.</div>'):
            html = "<p>Whole page introduction.</p>" + bodies
            self.assertEqual(sources._article_markup(html), html)

    def _storyline(self, con):
        saved = store.upsert_new_items(con, [item()])[0]
        key = saved["url_hash"]
        store.apply_newsroom_storyline_updates(con, run_id="original-run", allowed_existing_keys=set(), updates=[{
            "storyline_key": "inflation-outlook", "base_revision": None, "title": "Inflation outlook",
            "lifecycle": "open", "state_summary": "Writer proposed inflation background.", "watch_for": [],
            "relationship": "new_storyline", "candidate_ids": [key], "candidate_dispositions": {key: "publish"},
            "candidate_event_keys": {key: "oil-outlook"}, "update_reason": "Possible context."}])
        return saved

    def test_storyline_index_card_catalog_show_current_editor_drop_without_rewriting(self):
        with temporary_store() as con:
            self._storyline(con)
            now = time.time()
            store.save_newsroom_story_attempt(con, "oil-outlook", "editor_feedback", {"proposed_post": "Writer idea."}, now=now - 30)
            store.save_newsroom_editor_feedback(con, "oil-outlook", verdict="drop", post=None,
                reason="Expectations are not realized inflation; routine macro.", now=now)
            before = tuple(con.execute("SELECT * FROM newsroom_storylines").fetchone())
            changes = con.total_changes
            index = store.newsroom_storyline_index(con)[0]
            full = store.newsroom_storyline_cards(con, ["inflation-outlook"])[0]
            catalog = next(r for r in writer_memory.catalog(con)["rows"] if r["kind"] == "storyline")
            for view in (index, full, catalog):
                self.assertEqual(view["outcome_caveats"][0]["editor"]["verdict"], "drop")
                self.assertIn("not_editor_approved", view["summary_status"])
            event = full["recent_events"][0]
            self.assertEqual(event["disposition"], "publish")
            self.assertEqual(event["current_event_outcome"]["editor"]["at"], round(now, 3))
            self.assertIn("not_original_run", event["current_event_outcome"]["scope"])
            self.assertEqual(tuple(con.execute("SELECT * FROM newsroom_storylines").fetchone()), before)
            self.assertEqual(con.total_changes, changes)
            self.assertLess(editor._payload_bytes(full), 16 * 1024)
            con.execute("UPDATE newsroom_story_memory SET expires_at=?", (now - 1,))
            expired = store.newsroom_storyline_index(con)[0]["outcome_caveats"][0]
            self.assertEqual(expired["state"], "unknown")
            self.assertIsNone(expired["editor"])

    def test_confirmed_alias_publication_and_newer_draft_are_separate(self):
        with temporary_store() as con:
            self._storyline(con)
            now = time.time()
            con.execute("INSERT INTO story_key_aliases VALUES (?,?,?,?,?)", ("old-oil-key", "oil-outlook", "same event", now, now))
            for key, body, created, status, confirmed in (
                    ("old-oil-key", "Published account.", now - 50, "published", now - 30),
                    ("oil-outlook", "New draft.", now, "draft", None)):
                con.execute("INSERT INTO posts(created,class,body,mode,story_key,storyline_key,publisher_status,confirmed_at) VALUES (?,?,?,?,?,?,?,?)",
                            (created, "secondary", body, "DRAFT", key, "inflation-outlook", status, confirmed))
            con.commit()
            for outcome in (store.newsroom_event_outcome(con, "old-oil-key"),
                            store.newsroom_storyline_cards(con, ["inflation-outlook"])[0]["output_state"]):
                self.assertTrue(outcome["reader_covered"])
                self.assertTrue(outcome["open_draft"])
                self.assertEqual(outcome["confirmed_at"], now - 30)


if __name__ == "__main__":
    unittest.main()
