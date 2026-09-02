import hashlib
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from nbn import brain, config, guide_context, main, report, store, verify
from tests.support import temporary_store


def response(text):
    return SimpleNamespace(
        stop_reason="end_turn", content=[SimpleNamespace(type="text", text=text)]
    )


def _node_context(url="https://example.com/story", filler=""):
    key = store.canonical_discovery_key(url)
    ref_id = hashlib.sha256(f"wire-ref-v1\n{key}".encode()).hexdigest()[:24]
    value = {
        "untrusted_discovery_context": True,
        "origin": "marketing_node_wire_pulse_v2",
        "schema_version": "wire-pulse-v2",
        "node_pulse_run_id": 1,
        "theme_ids": [],
        "theme_signal_version": None,
        "theme_signals": [],
        "source_refs": [{"rank": 1, "url": url, "ref_id": ref_id}],
    }
    if filler:
        value["filler"] = filler
    return json.dumps(value, separators=(",", ":"))


def _guide_context(url="https://x.com/BitcoinArchive/status/1"):
    signal = guide_context.build_signal(
        "BitcoinArchive", url,
        "Bitcoin ETF inflows rose 25% after the latest filing",
        {"likes": 20, "reposts": 3}, ["https://reuters.com/world/bitcoin"],
    )
    return json.dumps({
        "untrusted_discovery_context": True,
        "origin": "bitcoin_news_guide_account",
        "guide_signal": signal,
    }, separators=(",", ":"))


class GuideContextTests(unittest.TestCase):
    def test_node_then_guide_and_guide_then_node_preserve_both_namespaces(self):
        node = _node_context()
        guide = _guide_context()
        for first, second in ((node, guide), (guide, node)):
            merged = guide_context.merge_context(first, second)
            parsed = json.loads(merged)
            self.assertEqual(parsed["schema_version"], "wire-pulse-v2")
            self.assertEqual(parsed["source_refs"][0]["url"], "https://example.com/story")
            self.assertEqual(parsed["guide_signal"]["handle"], "BitcoinArchive")

    def test_oversize_guide_enrichment_returns_original_node_bytes(self):
        node = _node_context(filler="x" * 7850)
        self.assertLessEqual(len(node.encode()), 8192)
        merged = guide_context.merge_context(node, _guide_context())
        self.assertEqual(merged, node)

    def test_terminal_duplicate_is_not_enriched(self):
        with temporary_store() as con:
            first = {
                "source": "CoinDesk", "title": "Story", "url": "https://example.com/story",
                "published": "", "summary": "", "discovery_context": _node_context(),
            }
            row = store.upsert_new_items(con, [first])[0]
            store.set_status(con, row["url_hash"], "skipped", note="done")
            store.upsert_new_items(con, [{**first, "discovery_context": _guide_context()}])
            saved = con.execute(
                "SELECT discovery_context FROM items WHERE url_hash=?", (row["url_hash"],)
            ).fetchone()["discovery_context"]
            self.assertNotIn("guide_signal", saved)

    def test_valid_guide_wins_before_limit_but_malformed_lookalike_does_not(self):
        with temporary_store() as con:
            rows = [
                {"source": "CoinDesk", "title": "ordinary first",
                 "url": "https://example.com/first", "published": "", "summary": ""},
                {"source": "X guide @BitcoinArchive", "title": "malformed",
                 "url": "https://example.com/malformed", "published": "", "summary": "",
                 "discovery_context": '{"guide_signal":"lookalike"}'},
                {"source": "Reuters", "title": "ordinary second",
                 "url": "https://example.com/second", "published": "", "summary": ""},
                {"source": "X guide @BitcoinArchive", "title": "valid late",
                 "url": "https://x.com/BitcoinArchive/status/9", "published": "",
                 "summary": "", "discovery_context": _guide_context(
                     "https://x.com/BitcoinArchive/status/9")},
            ]
            store.upsert_new_items(con, rows)
            selected = store.pending_items(con, 2)
        self.assertEqual([row["title"] for row in selected], [
            "valid late", "ordinary first",
        ])


class ResolverRecoveryTests(unittest.TestCase):
    def setUp(self):
        verify._url_cache.clear()
        verify._story_search_cache.clear()

    def test_handle_title_uses_substantive_summary_for_serpapi(self):
        item = {"title": "@BitcoinArchive", "summary": "Treasury yields rose to 4.80%",
                "story_key": "yield-move"}
        self.assertEqual(verify._serpapi_query(item), "Treasury yields rose to 4.80%")

    def test_external_x_pointer_to_fred_requires_semantic_assessment(self):
        item = {
            "url_hash": "fred-tip", "story_key": "treasury-yield",
            "source": "X guide @Barchart", "title": "@Barchart",
            "url": "https://fred.stlouisfed.org/graph/?g=abc",
            "summary": "U.S. 10-year Treasury yield rose to 4.80%",
        }
        verdict = {
            "directly_supports": False, "originality": "primary_artifact",
            "canonical_url": item["url"], "byline": "", "primary_artifact_url": None,
            "subject_is_actor": False, "reason": "graph does not prove interpretation",
        }
        with patch.object(verify, "_model_json", return_value=verdict) as assess:
            result = verify.resolve_source(item, "FRED data series (graph abc)\nDATE,VALUE")
        self.assertTrue(result.held)
        self.assertTrue(assess.called)
        self.assertIn("U.S. 10-year Treasury yield rose to 4.80%", assess.call_args.args[0])

    def test_node_item_labeled_fred_does_not_self_authenticate(self):
        item = {
            "url_hash": "node-fred", "story_key": "yield", "source": "FRED",
            "url": "https://fred.stlouisfed.org/graph/?g=abc", "title": "Yield rose",
            "summary": "Yield rose to 4.80%", "discovery_origin": "marketing_node",
        }
        verdict = {
            "directly_supports": False, "originality": "primary_artifact",
            "canonical_url": item["url"], "byline": "", "primary_artifact_url": None,
            "subject_is_actor": False, "reason": "ordinary assessment required",
        }
        with patch.object(verify, "_model_json", return_value=verdict) as assess:
            result = verify.resolve_source(item, "FRED data series (graph abc)\nDATE,VALUE")
        self.assertTrue(result.held)
        self.assertTrue(assess.called)

    def test_trusted_edgar_adapter_exact_artifact_self_authenticates(self):
        item = {
            "url_hash": "edgar", "story_key": "filing", "source": "SEC EDGAR",
            "url": "https://www.sec.gov/Archives/edgar/data/1/filing.htm",
            "title": "Company filed an 8-K", "summary": "",
            "discovery_origin": "edgar",
        }
        with patch.object(verify, "_model_json") as assess:
            result = verify.resolve_source(item, "Exact filing text")
        self.assertEqual(result.status, "selected")
        self.assertTrue(result.supported)
        assess.assert_not_called()

    def test_prepared_ref_assessor_receives_handle_summary_claim(self):
        signal = guide_context.build_signal(
            "BitcoinArchive", "https://x.com/BitcoinArchive/status/1",
            "U.S. 10-year Treasury yield rose to 4.80%", {}, [],
        )
        item = {
            "url_hash": "handle-tip", "story_key": "treasury-yield",
            "source": "X guide @BitcoinArchive", "title": "@BitcoinArchive",
            "url": "https://x.com/BitcoinArchive/status/1",
            "summary": "U.S. 10-year Treasury yield rose to 4.80%",
            "discovery_context": json.dumps({
                "untrusted_discovery_context": True,
                "origin": "bitcoin_news_guide_account", "guide_signal": signal,
            }),
        }
        fetched = {
            "outcome": "ok", "text": "The yield rose to 4.80 percent.",
            "final_url": "https://reuters.com/markets/yield",
            "canonical_url": "https://reuters.com/markets/yield", "byline": "Reporter",
        }
        verdict = {
            "directly_supports": True, "originality": "original_reporting",
            "canonical_url": fetched["final_url"], "byline": "Reporter",
            "primary_artifact_url": None, "subject_is_actor": True, "reason": "supports",
        }
        with patch("nbn.sources.fetch_article", return_value=fetched), \
                patch.object(verify, "_model_json", return_value=verdict) as assess:
            verify._try_prepared_refs(item, verify.source_policy.classify(
                item["url"], item["source"]), "tip", [{
                    "url": fetched["final_url"], "outlet": "Reuters", "rank": 1,
                }], "Guide")
        self.assertIn("U.S. 10-year Treasury yield rose to 4.80%", assess.call_args.args[0])

    def test_support_timeout_keeps_urls_but_grants_no_support(self):
        item = {
            "url_hash": "tip", "story_key": "bitcoin-policy", "source": "CryptoSlate",
            "title": "Bitcoin policy changed", "url": "https://cryptoslate.com/tip",
            "summary": "Bitcoin policy changed after a vote.",
        }
        fetched = {
            "outcome": "ok", "text": "Reuters reports the Bitcoin policy vote.",
            "final_url": "https://reuters.com/world/bitcoin-policy",
            "canonical_url": "https://reuters.com/world/bitcoin-policy", "byline": "Reporter",
        }
        with patch("nbn.search.google", return_value=[{
                "url": fetched["final_url"], "outlet": "Reuters", "rank": 1,
            }]), patch("nbn.sources.fetch_article", return_value=fetched), \
                patch.object(verify, "_model_json", side_effect=TimeoutError("timed out")):
            result = verify.resolve_source(item, "tip text")
        self.assertTrue(result.held)
        self.assertFalse(result.supported)
        self.assertFalse(result.receipt_eligible)
        self.assertEqual(result.error_kind, "support_assessment_timeout")
        self.assertEqual(result.resolver_path, "serpapi")
        self.assertEqual(len(result.retry_candidates), 1)

    def test_bounded_recovery_is_dry_run_first_and_excludes_stale(self):
        with temporary_store() as con:
            now = time.time()
            for suffix, published in (("fresh", "2099-01-01T00:00:00Z"),
                                      ("stale", "2020-01-01T00:00:00Z")):
                item = {
                    "source": "CryptoSlate", "title": suffix,
                    "url": f"https://example.com/{suffix}", "published": published,
                    "summary": "", "story_key": suffix, "action": "draft",
                    "class": "secondary", "reason": "test",
                }
                row = store.upsert_new_items(con, [item])[0]
                item["url_hash"] = row["url_hash"]
                store.start_research_job(con, item, "run")
                con.execute(
                    "UPDATE research_jobs SET state='exhausted',attempts=2,"
                    "stage='source_resolution',error_kind='support_assessment_timeout'"
                    " WHERE item_hash=?", (row["url_hash"],)
                )
                store.set_status(con, row["url_hash"], "held", suffix, "research exhausted")
            dry = store.recover_exhausted_timeouts(con, limit=10, apply=False, now=now)
            self.assertEqual(dry["eligible"], 1)
            self.assertEqual(dry["applied"], 0)
            applied = store.recover_exhausted_timeouts(con, limit=10, apply=True, now=now)
            self.assertEqual(applied["applied"], 1)
            states = {row["item_hash"]: row["state"] for row in con.execute(
                "SELECT item_hash,state FROM research_jobs"
            ).fetchall()}
            self.assertEqual(sorted(states.values()), ["exhausted", "pending"])


class IdentityGuardTests(unittest.TestCase):
    def _yield_case(self, relationship="same_event", candidate_value="4.80"):
        items = [{
            "url_hash": "yield", "source": "Bloomberg",
            "title": f"U.S. 10-year Treasury yield rose to {candidate_value}%",
            "summary": "", "published": "2026-09-01T12:00:00Z",
            "story_key": "yield-update-2026-09-01", "action": "draft",
            "_selected_text": "U.S. 10-year Treasury yield rose on 2026-09-01.",
        }]
        clusters = [{
            "canonical_key": "treasury-yield-2026-09-01",
            "titles": ["U.S. 10-year Treasury yield rose to 4.75% on 2026-09-01"],
        }]
        reply = response(json.dumps([{
            "url_hash": "yield", "canonical_key": "treasury-yield-2026-09-01",
            "relationship": relationship, "confidence": 0.96, "reason": "same move",
        }]))
        with patch.object(config, "YIELD_IDENTITY_NORMALIZER_ENABLED", True), \
                patch.object(brain, "_create", return_value=reply):
            return brain.reconcile_story_keys(items, clusters)[0]

    def test_clerk_valid_yield_same_event_is_accepted(self):
        result = self._yield_case()
        self.assertEqual(result["canonical_key"], "treasury-yield-2026-09-01")
        self.assertEqual(result["reason"], "identity-guard-v1:yield-same-event")

    def test_clerk_distinct_or_mismatched_yield_cannot_be_overridden(self):
        self.assertEqual(self._yield_case("distinct")["canonical_key"],
                         "yield-update-2026-09-01")
        self.assertEqual(self._yield_case(candidate_value="5.20")["canonical_key"],
                         "yield-update-2026-09-01")

    def test_conflicting_event_types_are_unknown(self):
        self.assertEqual(
            brain._event_type("Company filed an 8-K and announced a Bitcoin purchase"),
            "unknown",
        )

    def test_yield_identity_compares_material_final_reading(self):
        left = "U.S. 10-year Treasury yield rose from 4.0% to 4.5% on 2026-09-01"
        right = "U.S. 10-year Treasury yield rose from 4.0% to 5.0% on 2026-09-01"
        self.assertFalse(brain._yield_same_event(left, right))

    def test_yield_identity_ignores_shared_prior_close(self):
        left = (
            "U.S. 10-year Treasury yield rose to 4.80% on 2026-09-01; "
            "prior close 4.50%"
        )
        right = (
            "U.S. 10-year Treasury yield rose to 5.20% on 2026-09-01; "
            "prior close 4.50%"
        )
        self.assertFalse(brain._yield_same_event(left, right))


class DeskHealthTests(unittest.TestCase):
    def test_research_health_separates_backlog_activity_paths_and_outcomes(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "token"):
            now = time.time()
            store.kv_set(con, "desk:last_decision_run", json.dumps({
                "started": now - 1, "completed": now, "items": [],
                "result": {
                    "resolver_paths": {"serpapi": 2},
                    "resolver_outcomes": {"support_assessment_timeout": 1, "selected": 1},
                },
            }))
            store.record_pipeline_event(
                con, "run", "item", "research_started", category="infrastructure"
            )
            store.record_pipeline_event(
                con, "run", "item", "research_completed", category="research"
            )
            main._record_research_failure(
                con, {"_run_id": "run", "url_hash": "failed", "story_key": "story"},
                "source_resolution", "support_assessment_timeout", "pending",
            )
            store.record_pipeline_event(
                con, "run", "node:1", "node_packet_rejected", category="discovery"
            )
            store.record_pipeline_event(
                con, "run", "guide", "guide_lead_advanced", category="discovery"
            )
            store.record_pipeline_event(
                con, "run", "recovery", "research_recovery_requeued",
                category="infrastructure", metadata={"count": 3},
            )
            page = report.render(con)
            self.assertIn("Backlog now", page)
            self.assertIn("Selected CT day · distinct items", page)
            self.assertIn("SerpAPI 2", page)
            self.assertIn("support assessment timeout 1", page)
            self.assertIn("research completed 1", page)
            self.assertIn("Node packets rejected 1", page)
            self.assertIn("guide leads advanced 1", page)
            self.assertIn("recovery requeued 3", page)
            self.assertIn("Selected CT day · typed failures", page)

    def test_same_item_preserves_two_typed_failure_kinds_but_union_is_one(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "token"):
            item = {"_run_id": "run", "url_hash": "same", "story_key": "story"}
            main._record_research_failure(
                con, item, "source_resolution", "support_assessment_timeout", "pending"
            )
            main._record_research_failure(
                con, item, "source_resolution", "search_timeout", "exhausted"
            )
            events = con.execute(
                "SELECT event FROM pipeline_events WHERE item_hash='same' ORDER BY event"
            ).fetchall()
            page = report.render(con)
        self.assertEqual([row["event"] for row in events], [
            "research_failed:search_timeout",
            "research_failed:support_assessment_timeout",
        ])
        self.assertIn("research failed 1", page)
        self.assertIn("support assessment timeout 1", page)
        self.assertIn("search timeout 1", page)
