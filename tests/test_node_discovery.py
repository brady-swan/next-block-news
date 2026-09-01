import hashlib
import json
import unittest
from unittest.mock import Mock, patch

from nbn import config, node_discovery, sources, store
from tests.support import temporary_store


def candidate_id(run_id, source_id, url):
    key = store.canonical_discovery_key(url)
    source = " ".join(str(source_id or "").split()) or "-"
    return hashlib.sha256(f"v1\n{run_id}\n{source}\n{key}".encode()).hexdigest()[:32]


def payload(url="https://example.com/story?utm_source=node&a=2&a=1"):
    run_id = 175618
    source_id = "card-1"
    return {
        "run": {"run_id": run_id, "status": "partial", "selected_date": "2026-08-31"},
        "context": {
            "theme": "Bitcoin policy and markets",
            "must_know_titles": ["A material Bitcoin development"],
            "limitations": ["One upstream feed was delayed"],
            "daily_brief_workflow_run_id": 175081,
            "daily_brief_date": "2026-08-31",
        },
        "candidates": [{
            "candidate_id": candidate_id(run_id, source_id, url),
            "order": 1,
            "title": "A material Bitcoin development",
            "publisher": "Primary Newsroom",
            "url": url,
            "source_id": source_id,
            "observed_at": "2026-08-31T17:00:00Z",
            "published_at": "2026-08-31T16:55:00Z",
            "origin": "daily_brief_more_reads",
        }],
        "diagnostics": {
            "refs_seen": 1, "invalid_refs": 0, "duplicate_refs": 0,
            "candidates_returned": 1,
        },
    }


def v2_payload(now=1788192000, urls=None, candidates=True):
    import datetime
    generated = datetime.datetime.fromtimestamp(now, datetime.timezone.utc)
    urls = urls or ["https://example.com/primary?utm_source=node", "https://sec.gov/release"]
    refs = []
    for rank, url in enumerate(urls, 1):
        key = store.canonical_discovery_key(url)
        ref_id = hashlib.sha256(f"wire-ref-v1\n{key}".encode()).hexdigest()[:24]
        refs.append({
            "ref_id": ref_id, "rank": rank, "source_id": None,
            "publisher": "Primary Source" if rank == 1 else "SEC",
            "title": "Primary source title" if rank == 1 else "Official release",
            "url": url, "published_at": generated.isoformat(), "observed_at": None,
            "source_tier": 1, "source_type": "article", "source_class": "official",
            "role_hint": "official",
        })
    rows = []
    if candidates:
        key = store.canonical_discovery_key(urls[0])
        material = (f"wire-pulse-v2\n501\nwire-event-v1\n{refs[0]['ref_id']}\n{key}")
        rows.append({
            "candidate_id": hashlib.sha256(material.encode()).hexdigest()[:32],
            "order": 1, "primary_ref_id": refs[0]["ref_id"], "source_refs": refs,
            "cluster_headline": "Context-only cluster headline",
            "cluster_summary": "Context-only cluster summary",
            "event_key_hint": "event:strategy-purchase:2026-08-31",
            "event_key_version": "wire-event-v1", "event_date": "2026-08-31",
            "disclosure_date": "2026-08-31", "reporting_period": None,
            "why_surfaced": "fresh official Bitcoin signal", "bitcoin_relevance": 0.9,
            "relevance_reasons": ["explicit Bitcoin signal"],
            "theme_ids": ["institutional-adoption"], "novelty_hint": "new",
            "confidence_hint": "high",
        })
    return {
        "schema_version": "wire-pulse-v2",
        "run": {
            "run_id": 501, "status": "partial", "received_at": generated.isoformat(),
            "completed_at": generated.isoformat(), "generated_at": generated.isoformat(),
        },
        "candidates": rows,
        "provider_diagnostics": [
            {"provider": "perception", "attempted": True, "success": True,
             "item_count": 3, "error_count": 0, "errors": []},
            {"provider": "rss", "attempted": True, "success": True,
             "item_count": 2, "error_count": 0, "errors": []},
            {"provider": "twitter", "attempted": True, "success": True,
             "item_count": 1, "error_count": 0, "errors": []},
        ],
        "source_items_seen": 6, "clusters_seen": 1, "candidates_filtered": 0,
    }


class NodeDiscoveryTests(unittest.TestCase):
    def test_valid_v2_uses_primary_ref_for_ordinary_item_and_context_only_for_hints(self):
        body = v2_payload()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = body
        client = Mock()
        client.get.return_value = response
        with temporary_store() as con, \
                patch.object(config, "NODE_READ_TOKEN", "read-token"), \
                patch.object(sources, "_assert_public_http_url", return_value=None):
            result = node_discovery.ingest(con, now=1788192000, client=client)
            row = con.execute("SELECT * FROM items").fetchone()
            self.assertEqual(result["contract"], "v2")
            self.assertEqual(row["title"], "Primary source title")
            self.assertEqual(row["source"], "Primary Source")
            self.assertEqual(row["summary"], "")
            context = json.loads(row["discovery_context"])
            self.assertEqual(context["cluster_headline"], "Context-only cluster headline")
            self.assertEqual(
                context["source_refs"][0]["ref_id"],
                body["candidates"][0]["primary_ref_id"],
            )
            self.assertEqual(store.kv_get(con, "node:last_pulse_run_id"), "501")

    def test_fresh_empty_v2_is_consumed_without_v1_fallback(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = v2_payload(candidates=False)
        client = Mock()
        client.get.return_value = response
        with temporary_store() as con, patch.object(config, "NODE_READ_TOKEN", "read-token"):
            result = node_discovery.ingest(con, now=1788192000, client=client)
            self.assertEqual(result["contract"], "v2")
            self.assertEqual(result["inserted"], 0)
            self.assertEqual(client.get.call_count, 1)
            self.assertEqual(con.execute(
                "SELECT COUNT(*) n FROM node_discovery_runs").fetchone()["n"], 1)

    def test_v2_context_trims_lowest_refs_but_retains_primary(self):
        urls = [f"https://example.com/story-{index}?q={'x' * 1500}" for index in range(6)]
        body = v2_payload(urls=urls)
        run, _context, _diag, items = node_discovery._parse_v2(body, now=1788192000)
        context = json.loads(items[0]["discovery_context"])
        self.assertLessEqual(len(items[0]["discovery_context"].encode()), 8192)
        self.assertEqual(context["source_refs"][0]["url"], urls[0])
        self.assertLess(len(context["source_refs"]), 6)
        self.assertEqual(run["run_id"], 501)

    def test_v2_primary_mismatch_is_rejected_inside_consumable_run(self):
        body = v2_payload()
        body["candidates"][0]["primary_ref_id"] = "0" * 24
        with patch.object(sources, "_assert_public_http_url", return_value=None):
            _run, _context, diagnostics, items = node_discovery._parse_v2(
                body, now=1788192000)
        self.assertEqual(items, [])
        self.assertEqual(diagnostics["nbn_rejected"], 1)

    def test_stale_v2_falls_back_to_v1(self):
        stale = v2_payload(now=1788192000 - config.NODE_PULSE_MAX_AGE_SECONDS - 1)
        v2_response = Mock()
        v2_response.raise_for_status.return_value = None
        v2_response.json.return_value = stale
        v1_response = Mock()
        v1_response.raise_for_status.return_value = None
        v1_response.json.return_value = payload()
        client = Mock()
        client.get.side_effect = [v2_response, v1_response]
        with temporary_store() as con, \
                patch.object(config, "NODE_READ_TOKEN", "read-token"), \
                patch.object(sources, "_assert_public_http_url", return_value=None):
            result = node_discovery.ingest(con, now=1788192000, client=client)
        self.assertEqual(result["contract"], "v1")
        self.assertIn("stale", result["v2_error"])
        self.assertEqual(client.get.call_count, 2)

    def test_v2_dedupe_attaches_context_only_to_new_row(self):
        body = v2_payload()
        with temporary_store() as con, patch.object(
                sources, "_assert_public_http_url", return_value=None):
            store.upsert_new_items(con, [{
                "source": "RSS", "title": "Original title",
                "url": "https://example.com/primary", "published": "", "summary": "original",
            }])
            run, context, diagnostics, items = node_discovery._parse_v2(body, now=1788192000)
            saved = store.ingest_node_discovery_run(
                con, run_id=run["run_id"], selected_date=run["selected_date"],
                status=run["status"], context=context, diagnostics=diagnostics, items=items)
            row = con.execute("SELECT * FROM items").fetchone()
            self.assertEqual(saved["context_attached"], 1)
            self.assertEqual(row["source"], "RSS")
            self.assertEqual(row["title"], "Original title")
            self.assertEqual(row["summary"], "original")
            self.assertIn("wire-pulse-v2", row["discovery_context"])

    def test_v2_dedupe_never_mutates_processed_row(self):
        body = v2_payload()
        with temporary_store() as con, patch.object(
                sources, "_assert_public_http_url", return_value=None):
            store.upsert_new_items(con, [{
                "source": "RSS", "title": "Processed title",
                "url": "https://example.com/primary", "published": "", "summary": "original",
            }])
            row = con.execute("SELECT url_hash FROM items").fetchone()
            store.set_status(con, row["url_hash"], "skipped", note="processed")
            run, context, diagnostics, items = node_discovery._parse_v2(body, now=1788192000)
            saved = store.ingest_node_discovery_run(
                con, run_id=run["run_id"], selected_date=run["selected_date"],
                status=run["status"], context=context, diagnostics=diagnostics, items=items)
            processed = con.execute("SELECT * FROM items").fetchone()
            self.assertEqual(saved["context_attached"], 0)
            self.assertEqual(processed["discovery_context"], "")
            self.assertEqual(processed["discovery_candidate_id"], None)

    def test_valid_run_is_consumed_once_and_context_is_not_summary(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload()
        client = Mock()
        client.get.return_value = response
        with temporary_store() as con, \
                patch.object(config, "NODE_READ_TOKEN", "read-token"), \
                patch.object(sources, "_assert_public_http_url", return_value=None):
            first = node_discovery.ingest(con, now=1788192000, client=client)
            # Clear only the throttle; the consumed run remains durable.
            store.kv_set(con, "node:last_attempt", "0")
            second = node_discovery.ingest(con, now=1788192301, client=client)
            self.assertEqual(first["inserted"], 1)
            self.assertTrue(second["consumed"])
            self.assertEqual(second["inserted"], 0)
            row = con.execute("SELECT * FROM items").fetchone()
            self.assertEqual(row["summary"], "")
            self.assertEqual(row["discovery_origin"], "marketing_node")
            self.assertIn("untrusted_discovery_context", row["discovery_context"])

    def test_attempt_is_persistently_throttled_before_request(self):
        client = Mock()
        with temporary_store() as con, patch.object(config, "NODE_READ_TOKEN", "read-token"):
            store.kv_set(con, "node:last_attempt", "1000")
            result = node_discovery.ingest(con, now=1100, client=client)
            self.assertEqual(result["reason"], "throttled")
            client.get.assert_not_called()

    def test_candidate_id_mismatch_skips_ref_but_consumes_valid_run(self):
        body = payload()
        body["candidates"][0]["candidate_id"] = "0" * 32
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = body
        client = Mock()
        client.get.return_value = response
        with temporary_store() as con, \
                patch.object(config, "NODE_READ_TOKEN", "read-token"), \
                patch.object(sources, "_assert_public_http_url", return_value=None):
            result = node_discovery.ingest(con, now=1788192000, client=client)
            self.assertEqual(result["inserted"], 0)
            self.assertEqual(result["diagnostics"]["nbn_rejected"], 1)
            self.assertEqual(con.execute("SELECT COUNT(*) n FROM node_discovery_runs").fetchone()["n"], 1)

    def test_invalid_envelope_is_not_consumed(self):
        body = payload()
        body["run"]["selected_date"] = "2026-08-30"
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = body
        client = Mock()
        client.get.return_value = response
        with temporary_store() as con, patch.object(config, "NODE_READ_TOKEN", "read-token"):
            result = node_discovery.ingest(con, now=1788192000, client=client)
            self.assertIn("error", result)
            self.assertEqual(con.execute("SELECT COUNT(*) n FROM node_discovery_runs").fetchone()["n"], 0)


if __name__ == "__main__":
    unittest.main()
