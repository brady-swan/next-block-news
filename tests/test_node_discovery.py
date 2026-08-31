import hashlib
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


class NodeDiscoveryTests(unittest.TestCase):
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
