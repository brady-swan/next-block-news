"""URL-level qualification storage must preserve selected capture provenance."""
import json
import time
import unittest
from contextlib import ExitStack
from dataclasses import replace
from unittest.mock import patch

from nbn import brain, config, main, newsroom, publisher, store, verify
from tests.support import temporary_store
from tests.test_editorial_v2 import inspected, materialization_fixture
from tests.test_evidence_to_reader import answer


def evidence(record):
    return verify.EvidenceCandidate(
        record.source, newsroom._record_originality(record), True, True,
        record.independent_report, content_fingerprint=record.content_fingerprint)


class EvidencePersistenceTests(unittest.TestCase):
    def test_writer_duplicates_prefer_selected_capture_in_both_orders(self):
        for same_text in (False, True):
            for selected_native in (False, True):
                for native_first in (False, True):
                    with self.subTest(same_text=same_text, selected_native=selected_native,
                                      native_first=native_first), temporary_store() as con:
                        row, record, _draft, session = materialization_fixture(con)
                        direct = evidence(record)
                        native = replace(direct, originality="unknown",
                            corroboration_eligible=False,
                            content_fingerprint=direct.content_fingerprint if same_text else "native-fp")
                        selected = native if selected_native else direct
                        captures = (native, direct) if native_first else (direct, native)
                        result = replace(session.conduct.return_value.resolutions[row["url_hash"]],
                            selected=selected.ref, originality=selected.originality,
                            supported=selected.supported, receipt_eligible=selected.receipt_eligible,
                            corroboration_eligible=selected.corroboration_eligible,
                            content_fingerprint=selected.content_fingerprint, evidence=captures)
                        store.persist_resolution(con, result, "enforce")
                        saved = store.evidence_for_item(con, row["url_hash"])
                        self.assertEqual(len(saved), 1)
                        self.assertEqual(saved[0]["originality"], selected.originality)
                        self.assertEqual(saved[0]["content_fingerprint"], selected.content_fingerprint)
                        self.assertEqual(saved[0]["corroboration_eligible"], selected.corroboration_eligible)
                        self.assertIs(result.evidence, captures)
                        self.assertEqual(result.selected_text, record.text)

    def test_nonselected_url_keeps_first_intact_not_combined_qualifications(self):
        with temporary_store() as con:
            row, record, _draft, session = materialization_fixture(con)
            direct = evidence(record)
            other = replace(direct, ref=replace(direct.ref, url=record.final_url + "-other"),
                            supported=False, receipt_eligible=False, content_fingerprint="first")
            later = replace(other, supported=True, receipt_eligible=True,
                            corroboration_eligible=True, content_fingerprint="later")
            result = replace(session.conduct.return_value.resolutions[row["url_hash"]],
                             evidence=(direct, other, later))
            store.persist_resolution(con, result, "enforce")
            saved = store.evidence_for_item(con, row["url_hash"])
            self.assertEqual(len(saved), 2)
            self.assertEqual(saved[1]["content_fingerprint"], "first")
            self.assertFalse(saved[1]["support_verdict"])
            self.assertFalse(saved[1]["receipt_eligible"])
            self.assertEqual(saved[1]["corroboration_eligible"], other.corroboration_eligible)

    def test_distinct_urls_with_identical_text_are_not_collapsed(self):
        with temporary_store() as con:
            row, record, _draft, session = materialization_fixture(con)
            direct = evidence(record)
            second = replace(direct, ref=replace(direct.ref, url=record.final_url + "/other"))
            result = replace(session.conduct.return_value.resolutions[row["url_hash"]],
                             evidence=(direct, second))
            store.persist_resolution(con, result, "enforce")
            self.assertEqual([e["url"] for e in store.evidence_for_item(con, row["url_hash"])],
                             [direct.ref.url, second.ref.url])

    def test_selected_source_metadata_matters_when_fingerprints_match(self):
        with temporary_store() as con:
            row, record, _draft, session = materialization_fixture(con)
            selected = evidence(record)
            other = replace(selected, ref=replace(selected.ref, source_id="other-attribution"))
            result = replace(session.conduct.return_value.resolutions[row["url_hash"]],
                             evidence=(other, selected))
            store.persist_resolution(con, result, "enforce")
            self.assertEqual(store.evidence_for_item(con, row["url_hash"])[0]["source_id"],
                             selected.ref.source_id)

    def test_full_materialization_retains_same_url_direct_and_native_captures(self):
        for native_reader in (False, True):
            with self.subTest(native_reader=native_reader), temporary_store() as con, ExitStack() as stack:
                run_id = "run:same-url-captures"
                row, primary, draft, fake = materialization_fixture(con, run_id)
                outcome = fake.conduct.return_value
                second = inspected("second", "https://www.coindesk.com/policy/bitcoin", "CoinDesk",
                                   "The SEC announced a Bitcoin policy update. More context.")
                native = replace(primary, fetch_id="native-primary", text=primary.text + " Native summary.",
                    content_fingerprint="native-primary-fp", retrieval_kind="provider_reported_extract",
                    limitations="Native source paraphrase, not a direct capture.")
                native_second = replace(second, fetch_id="native-second", text=second.text + " Native summary.",
                    content_fingerprint="native-second-fp", retrieval_kind="provider_reported_extract",
                    limitations="Native source paraphrase, not a direct capture.")
                outcome.fetches.update({r.fetch_id: r for r in (second, native, native_second)})
                outcome.resolutions[row["url_hash"]] = replace(outcome.resolutions[row["url_hash"]],
                    evidence=(evidence(primary), evidence(second)))
                draft["evidence_fetch_ids"] = [primary.fetch_id, second.fetch_id]
                outcome.story_attempts[0]["evidence"].append({
                    "inspected_at": second.inspected_at, "requested_url": second.requested_url,
                    "final_url": second.final_url, "canonical_url": second.canonical_url,
                    "source_label": second.source.display_name, "content_fingerprint": second.content_fingerprint,
                    "text": second.text, "retrieval_kind": second.retrieval_kind})
                sent = []

                def create(_model, _system, raw, **_kwargs):
                    payload = json.loads(raw)
                    sent.append(payload)
                    entries = payload["unassigned_run_research"]["receipts"]
                    refs = {e["fetch_id"]: e["evidence_ref"] for e in entries}
                    return answer([{"story_id": "sec", "verdict": "publish", "post": draft["post"],
                        "reason": "Same source captured directly and by native research.",
                        "additional_evidence_refs": [refs[native.fetch_id], refs[native_second.fetch_id]],
                        "reader_receipt_ref": refs[native.fetch_id] if native_reader else None}])

                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="test"))
                stack.enter_context(patch.object(brain, "_create", side_effect=create))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=fake))
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
                stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", False))
                stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
                publish = stack.enter_context(patch.object(publisher, "publish", return_value=("DRAFT", "test-draft")))
                self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
                counts = {k: 0 for k in ("held", "skipped", "posted", "drafted", "uncertain", "failed", "taped")}
                result = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id=run_id,
                    inventory=[row], pending=[row], result=counts, theme_snapshot=[], overrides={},
                    run_started=time.time())
                self.assertEqual(result["drafted"], 1)
                publish.assert_called_once()
                self.assertEqual(len(sent), 1)
                self.assertEqual(len(outcome.resolutions[row["url_hash"]].evidence), 4)
                saved = store.evidence_for_item(con, row["url_hash"])
                self.assertEqual(len(saved), 2)
                resolution = store.resolution_for_item(con, row["url_hash"])
                self.assertEqual(resolution["selected_url"], primary.source.url)
                selected = next(e for e in saved if e["url"] == primary.source.url)
                self.assertEqual(selected["content_fingerprint"], resolution["content_fingerprint"])
                self.assertEqual(selected["originality"], resolution["originality"])
                self.assertEqual(selected["corroboration_eligible"], resolution["corroboration_eligible"])
                self.assertIn("Native summary", resolution["selected_text"])
                pool = json.loads(con.execute("SELECT evidence_pool_json FROM newsroom_story_memory").fetchone()[0])
                self.assertEqual(len(pool), 4)
                for url in (primary.final_url, second.final_url):
                    self.assertEqual({r.get("retrieval_kind", "direct_fetch") for r in pool if r["final_url"] == url},
                                     {"direct_fetch", "provider_reported_extract"})


if __name__ == "__main__":
    unittest.main()
