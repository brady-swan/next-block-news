import json
import unittest
from unittest.mock import patch

from nbn import store, verify
from tests.support import temporary_store


def story(url, source):
    return {"url_hash": "item-1", "story_key": "story", "url": url, "source": source,
            "title": "Bitcoin test story", "summary": "Bitcoin test source",
            "_canonical_url": url, "_byline": "Fetched Reporter"}


class VerifyTests(unittest.TestCase):
    def setUp(self):
        verify._url_cache.clear()
        verify._story_search_cache.clear()

    def test_tier_three_is_replaced_by_supporting_tier_one(self):
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": "https://cryptoslate.com/story", "byline": "A"},
            "candidates": [{"url": "https://reuters.com/world/story", "outlet": "Reuters",
                            "directly_supports": True, "originality": "original_reporting",
                            "canonical_url": "https://reuters.com/world/story", "byline": "B"}],
            "earliest_coverage_date": "2026-08-31", "reason": "Reuters confirms",
        }
        with patch.object(verify, "_model_json", return_value=verdict), \
                patch("nbn.sources.fetch_article", return_value={
                    "text": "Bitcoin test source", "final_url": "https://reuters.com/world/story",
                    "canonical_url": "https://reuters.com/world/story", "byline": "B"}):
            result = verify.resolve_source(
                story("https://cryptoslate.com/story", "CryptoSlate"), "Bitcoin test source")
        self.assertEqual(result.selected.source_id, "reuters")
        self.assertEqual(result.selected.tier, "t1")
        self.assertFalse(result.evidence[0].receipt_eligible)
        self.assertTrue(result.evidence[1].corroboration_eligible)

    def test_tier_three_holds_without_upgrade(self):
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": "https://cryptoslate.com/story", "byline": "A"},
            "candidates": [], "reason": "No independent source",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(
                story("https://cryptoslate.com/story", "CryptoSlate"), "Bitcoin test source")
        self.assertTrue(result.held)

    def test_node_ranked_refs_are_reclassified_and_capped_at_three(self):
        row = story("https://cryptoslate.com/tip", "CryptoSlate")
        row["discovery_context"] = json.dumps({
            "schema_version": "wire-pulse-v2",
            "untrusted_discovery_context": True,
            "source_refs": [
                {"rank": 1, "url": "https://unknown.example/one", "publisher": "SEC"},
                {"rank": 2, "url": "https://coindesk.com/two", "publisher": "Unknown"},
                {"rank": 3, "url": "https://reuters.com/three", "publisher": "Reuters"},
                {"rank": 4, "url": "https://sec.gov/newsroom/press-releases/four",
                 "publisher": "SEC"},
                {"rank": 5, "url": "https://theblock.co/five", "publisher": "The Block"},
            ],
        })
        refs = verify._node_ranked_refs(row)
        self.assertEqual([ref["rank"] for ref in refs], [2, 3, 4])
        self.assertEqual(len(refs), 3)

    def test_first_qualified_node_ref_stops_before_web_search(self):
        row = story("https://cryptoslate.com/tip", "CryptoSlate")
        row["discovery_context"] = json.dumps({
            "schema_version": "wire-pulse-v2",
            "untrusted_discovery_context": True,
            "source_refs": [
                {"rank": 1, "url": "https://coindesk.com/report", "publisher": "CoinDesk"},
                {"rank": 2, "url": "https://reuters.com/report", "publisher": "Reuters"},
            ],
        })
        verdict = {
            "directly_supports": True,
            "originality": "original_reporting",
            "subject_is_actor": False,
        }
        fetched = {
            "text": "Independent Bitcoin reporting",
            "final_url": "https://coindesk.com/report",
            "canonical_url": "https://coindesk.com/report",
            "byline": "Reporter",
            "outcome": "ok",
        }
        with patch.object(verify, "_model_json", return_value=verdict) as model, \
                patch("nbn.sources.fetch_article", return_value=fetched) as fetch:
            result = verify.resolve_source(row, "CryptoSlate detector text")
        self.assertFalse(result.held)
        self.assertEqual(result.selected.source_id, "coindesk")
        self.assertIn("Node ranked ref 1", result.note)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(fetch.call_count, 1)

    def test_first_qualified_guide_link_stops_before_web_search(self):
        row = story(
            "https://x.com/BitcoinArchive/status/1", "X guide @BitcoinArchive",
        )
        row["discovery_context"] = json.dumps({
            "untrusted_discovery_context": True,
            "guide_account_signal": True,
            "outbound_urls": [
                "https://news.bitcoin.com/relay",
                "https://reuters.com/world/bitcoin-policy",
            ],
        })
        self.assertEqual(
            [ref["url"] for ref in verify._guide_ranked_refs(row)],
            ["https://reuters.com/world/bitcoin-policy"],
        )
        verdict = {
            "directly_supports": True,
            "originality": "original_reporting",
            "subject_is_actor": False,
        }
        fetched = {
            "text": "Independent Bitcoin policy reporting",
            "final_url": "https://reuters.com/world/bitcoin-policy",
            "canonical_url": "https://reuters.com/world/bitcoin-policy",
            "byline": "Reporter",
            "outcome": "ok",
        }
        with patch.object(verify, "_model_json", return_value=verdict) as model, \
                patch("nbn.sources.fetch_article", return_value=fetched) as fetch:
            result = verify.resolve_source(row, "Bitcoin Archive tip")
        self.assertFalse(result.held)
        self.assertEqual(result.selected.source_id, "reuters")
        self.assertIn("Guide ranked ref 1", result.note)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(fetch.call_count, 1)

    def test_serpapi_query_removes_wire_prefix_url_and_caps_words(self):
        row = story("https://x.com/BitcoinArchive/status/1", "X guide @BitcoinArchive")
        row["title"] = "BREAKING: " + " ".join(f"word{i}" for i in range(40)) \
                       + " https://t.co/example"
        query = verify._serpapi_query(row)
        self.assertFalse(query.lower().startswith("breaking"))
        self.assertNotIn("https://", query)
        self.assertEqual(len(query.split()), 32)

    def test_serpapi_results_are_source_ranked_and_capped(self):
        row = story("https://cryptoslate.com/tip", "CryptoSlate")
        results = [
            {"rank": 1, "url": "https://news.bitcoin.com/relay", "outlet": "Bitcoin.com"},
            {"rank": 2, "url": "https://coindesk.com/report", "outlet": "CoinDesk"},
            {"rank": 3, "url": "https://reuters.com/report", "outlet": "Reuters"},
            {"rank": 4, "url": "https://sec.gov/newsroom/press-releases/test", "outlet": "SEC"},
            {"rank": 5, "url": "https://theblock.co/report", "outlet": "The Block"},
        ]
        with patch("nbn.search.google", return_value=results):
            refs = verify._serpapi_ranked_refs(row)
        self.assertEqual(
            [ref["url"] for ref in refs],
            [
                "https://sec.gov/newsroom/press-releases/test",
                "https://reuters.com/report",
                "https://coindesk.com/report",
            ],
        )

    def test_first_qualified_serpapi_ref_stops_before_hosted_search(self):
        row = story("https://cryptoslate.com/tip", "CryptoSlate")
        result_rows = [{
            "rank": 1,
            "url": "https://reuters.com/world/bitcoin-policy",
            "outlet": "Reuters",
        }]
        verdict = {
            "directly_supports": True,
            "originality": "original_reporting",
            "subject_is_actor": False,
        }
        fetched = {
            "text": "Independent Bitcoin policy reporting",
            "final_url": "https://reuters.com/world/bitcoin-policy",
            "canonical_url": "https://reuters.com/world/bitcoin-policy",
            "byline": "Reporter",
            "outcome": "ok",
        }
        with patch("nbn.search.google", return_value=result_rows) as search, \
                patch.object(verify, "_model_json", return_value=verdict) as model, \
                patch("nbn.sources.fetch_article", return_value=fetched) as fetch:
            result = verify.resolve_source(row, "CryptoSlate detector text")
        self.assertFalse(result.held)
        self.assertEqual(result.selected.source_id, "reuters")
        self.assertIn("SerpAPI ranked ref 1", result.note)
        self.assertEqual(search.call_count, 1)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(model.call_count, 1)
        self.assertFalse(model.call_args.kwargs["web"])

    def test_ineligible_model_candidate_is_rejected_before_fetch(self):
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": "https://cryptoslate.com/story", "byline": "A"},
            "candidates": [{"url": "http://127.0.0.1/admin", "outlet": "SEC",
                            "directly_supports": True, "originality": "primary_artifact"}],
            "reason": "untrusted candidate",
        }
        with patch.object(verify, "_model_json", return_value=verdict), \
                patch("nbn.sources.fetch_article") as fetch:
            result = verify.resolve_source(
                story("https://cryptoslate.com/story", "CryptoSlate"), "Bitcoin source")
        self.assertTrue(result.held)
        fetch.assert_not_called()

    def test_tier_two_original_reporting_fallback(self):
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": "https://coindesk.com/story", "byline": "Reporter"},
            "candidates": [], "reason": "Original CoinDesk reporting",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(
                story("https://coindesk.com/story", "CoinDesk"), "Bitcoin test source")
        self.assertFalse(result.held)
        self.assertEqual(result.selected.source_id, "coindesk")
        self.assertTrue(result.corroboration_eligible)

    def test_tier_two_unknown_originality_holds(self):
        verdict = {
            "original": {"directly_supports": True, "originality": "unknown",
                         "canonical_url": "https://coindesk.com/story", "byline": ""},
            "candidates": [], "reason": "Originality unclear",
        }
        row = story("https://coindesk.com/story", "CoinDesk")
        row["_byline"] = ""
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "Bitcoin test source")
        self.assertTrue(result.held)

    def test_final_redirect_url_is_reclassified(self):
        row = story("https://finance.yahoo.com/wrapper", "Yahoo Finance")
        row["_final_url"] = "https://reuters.com/world/story"
        result = verify.resolve_source(row, "Bitcoin test source")
        self.assertEqual(result.selected.source_id, "reuters")
        self.assertEqual(result.selected.tier, "t1")

    def test_story_cache_never_reuses_another_pages_originality_verdict(self):
        verdicts = [
            {"original": {"directly_supports": True, "originality": "original_reporting",
                          "canonical_url": "https://coindesk.com/one", "byline": "One"},
             "candidates": [], "reason": "first"},
            {"original": {"directly_supports": True, "originality": "original_reporting",
                          "canonical_url": "https://theblock.co/two", "byline": "Two"},
             "candidates": [], "reason": "second"},
        ]
        with patch.object(verify, "_model_json", side_effect=verdicts) as model:
            first = verify.resolve_source(
                story("https://coindesk.com/one", "CoinDesk"), "First original text")
            second_row = story("https://theblock.co/two", "The Block")
            second_row["url_hash"] = "item-2"
            second = verify.resolve_source(second_row, "Second original text")
        self.assertEqual(model.call_count, 2)
        self.assertEqual(first.selected.source_id, "coindesk")
        self.assertEqual(second.selected.source_id, "the-block")

    def test_redirected_wrappers_to_same_final_receipt_dedupe_before_persist(self):
        row = story("https://cryptoslate.com/tip", "CryptoSlate")
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": row["url"], "byline": "Tip"},
            "candidates": [
                {"url": "https://coindesk.com/wrapper-one", "outlet": "CoinDesk",
                 "directly_supports": True, "originality": "original_reporting"},
                {"url": "https://theblock.co/wrapper-two", "outlet": "The Block",
                 "directly_supports": True, "originality": "original_reporting"},
            ],
            "reason": "both wrappers locate Reuters",
        }
        fetched = {"text": "Reuters Bitcoin source",
                   "final_url": "https://reuters.com/world/final",
                   "canonical_url": "https://reuters.com/world/final", "byline": "Reporter"}
        with temporary_store() as con, \
                patch.object(verify, "_model_json", return_value=verdict), \
                patch("nbn.sources.fetch_article", return_value=fetched):
            result = verify.resolve_source(row, "CryptoSlate tip", con=con)
            store.persist_resolution(con, result, "enforce")
            evidence = store.evidence_for_item(con, row["url_hash"])
        self.assertEqual(len(result.evidence), 2)
        self.assertEqual(sum(ev.ref.source_id == "reuters" for ev in result.evidence), 1)
        self.assertEqual(len(evidence), 2)

    def test_candidate_redirecting_to_original_final_receipt_is_deduped(self):
        row = story("https://coindesk.com/original", "CoinDesk")
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting"},
            "candidates": [{"url": "https://theblock.co/wrapper", "outlet": "The Block",
                            "directly_supports": True, "originality": "original_reporting"}],
            "reason": "wrapper redirects to original",
        }
        fetched = {"text": "CoinDesk original Bitcoin source",
                   "final_url": row["url"], "canonical_url": row["url"],
                   "byline": "Fetched Reporter"}
        with patch.object(verify, "_model_json", return_value=verdict), \
                patch("nbn.sources.fetch_article", return_value=fetched):
            result = verify.resolve_source(row, "CoinDesk original Bitcoin source")
        self.assertEqual(len(result.evidence), 1)
        self.assertEqual(result.selected.source_id, "coindesk")

    def test_resolver_outage_holds_tier_three(self):
        with patch.object(verify, "_model_json", side_effect=RuntimeError("offline")):
            result = verify.resolve_source(
                story("https://cryptoslate.com/story", "CryptoSlate"), "Bitcoin test source")
        self.assertTrue(result.held)
        self.assertIn("offline", result.note)

    def test_known_discovery_source_cannot_be_model_promoted(self):
        raw = {"url": "https://cryptoslate.com/story", "outlet": "CryptoSlate",
               "directly_supports": True, "originality": "primary_artifact",
               "canonical_url": "https://cryptoslate.com/story", "byline": "Reporter"}
        candidate, _ = verify._candidate(raw, raw["url"], "CryptoSlate", "Bitcoin")
        self.assertFalse(candidate.receipt_eligible)
        self.assertFalse(candidate.corroboration_eligible)

    def test_privileged_alias_on_hostile_host_is_held(self):
        row = story("https://untrusted.example/story", "SEC")
        verdict = {
            "original": {"directly_supports": True, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "", "subject_is_actor": True},
            "candidates": [], "reason": "untrusted host",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "Official-looking but untrusted text")
        self.assertTrue(result.held)
        self.assertEqual(result.selected.tier, "unknown")

    def test_official_artifact_requires_support_and_role_verdict(self):
        row = story("https://sec.gov/newsroom/press-releases/test", "SEC")
        verdict = {
            "original": {"directly_supports": False, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "", "subject_is_actor": True},
            "candidates": [], "reason": "page does not support headline",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "A real SEC page with unrelated text")
        self.assertTrue(result.held)

    def test_official_artifact_requires_scoped_path(self):
        row = story("https://sec.gov/about/biography", "SEC")
        verdict = {
            "original": {"directly_supports": True, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "", "subject_is_actor": True},
            "candidates": [], "reason": "broad domain page",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "An SEC biography page")
        self.assertTrue(result.held)

    def test_supporting_official_release_passes_scoped_role_check(self):
        row = story("https://sec.gov/newsroom/press-releases/test", "SEC")
        verdict = {
            "original": {"directly_supports": True, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "", "subject_is_actor": True},
            "candidates": [], "reason": "official release supports story",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "SEC announces a Bitcoin order")
        self.assertFalse(result.held)
        self.assertTrue(result.selected.official)

    def test_fred_graph_route_passes_scoped_official_artifact_check(self):
        row = story("https://fred.stlouisfed.org/graph/?g=abc123", "FRED")
        verdict = {
            "original": {"directly_supports": True, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "", "subject_is_actor": True},
            "candidates": [], "reason": "official FRED series data",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "DATE,VALUE\n2026-08-31,100")
        self.assertFalse(result.held)
        self.assertEqual(result.selected.source_id, "federal-reserve")

    def test_official_x_is_primary_only_for_its_own_action(self):
        row = story("https://x.com/coinbase/status/1", "X @coinbase")
        verdict = {
            "original": {"directly_supports": True, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "",
                         "subject_is_actor": False},
            "candidates": [], "reason": "account comments on another entity",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "Coinbase comments on another company")
        self.assertTrue(result.held)

    def test_x_label_cannot_replace_url_identity_with_official_account(self):
        row = story("https://x.com/BitcoinArchive/status/1", "X @coinbase")
        verdict = {
            "original": {"directly_supports": True, "originality": "primary_artifact",
                         "canonical_url": row["url"], "byline": "",
                         "subject_is_actor": True},
            "candidates": [], "reason": "spoofed label",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "BitcoinArchive detector text")
        self.assertTrue(result.held)
        self.assertEqual(result.original.source_id, "bitcoin-archive")

    def test_fetched_metadata_overrides_favorable_model_metadata(self):
        row = story("https://coindesk.com/story", "CoinDesk")
        row["_canonical_url"] = "https://cryptoslate.com/copied-story"
        row["_byline"] = ""
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": row["url"], "byline": "Invented Reporter"},
            "candidates": [], "reason": "model claims original",
        }
        with patch.object(verify, "_model_json", return_value=verdict):
            result = verify.resolve_source(row, "Syndicated Bitcoin report")
        self.assertTrue(result.held)
        self.assertFalse(result.evidence[0].corroboration_eligible)

    def test_persisted_resolution_cache_survives_process_cache_clear(self):
        row = story("https://coindesk.com/cached", "CoinDesk")
        verdict = {
            "original": {"directly_supports": True, "originality": "original_reporting",
                         "canonical_url": row["url"], "byline": "Reporter"},
            "candidates": [], "reason": "original report",
        }
        with temporary_store() as con, patch.object(verify, "_model_json", return_value=verdict):
            first = verify.resolve_source(row, "Cached Bitcoin report", con=con)
            store.persist_resolution(con, first, "enforce")
            verify._url_cache.clear()
            with patch.object(verify, "_model_json", side_effect=AssertionError("paid search repeated")):
                second = verify.resolve_source(row, "Cached Bitcoin report", con=con)
        self.assertFalse(second.held)
        self.assertTrue(second.note.startswith("cached:"))

    def test_claim_support_is_fail_closed(self):
        with patch.object(verify, "_model_json", side_effect=RuntimeError("budget")):
            result = verify.claims_supported("NEW: Bitcoin test.", "Bitcoin test source")
        self.assertFalse(result["supported"])

    def test_exact_quote_must_exist(self):
        result = verify.claims_supported('NEW: "not in source".', "Bitcoin test source")
        self.assertFalse(result["supported"])
        self.assertIn("quote", result["reason"])


if __name__ == "__main__":
    unittest.main()
