import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nbn.eval import budget
from nbn.eval.budget import BudgetLedger, conservative_reservation
from nbn.eval.core import (
    EvaluationError,
    blinded_order,
    digest,
    leaf_paths,
    load_corpus,
    validate_case,
    validate_corpus,
)
from nbn.eval.corpus import freeze_corpus
from nbn.eval.providers import (
    ProviderAdapter,
    ProviderResult,
    _native_tool_usage,
    evaluation_key,
)
from nbn.eval.reporting import build_report
from nbn.eval.runner import EvaluationRunner, _schema_errors, _semantic_errors

OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "candidate_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["draft", "pass", "hold"]},
                    "reason": {"type": "string"},
                },
                "required": ["candidate_id", "action", "reason"],
            },
        },
    },
    "required": ["decisions"],
}


def newsdesk_case(case_id="case-a", *, split="calibration", event_id="event-a",
                  clock=100.0, available=99.0, contaminated=False):
    packet = {
        "system": "You are an evaluation desk.",
        "input": {"candidates": [{"candidate_id": "a", "title": "Bitcoin event"}]},
        "max_output_tokens": 400,
    }
    case = {
        "case_id": case_id,
        "event_ids": [event_id],
        "lane": "calibration" if split == "calibration" else "newsdesk",
        "split": split,
        "editorial_clock": clock,
        "packet": packet,
        "availability": {path: available for path in leaf_paths(packet)},
        "output_schema": OUTPUT_SCHEMA,
        "training_contaminated": contaminated,
        "adjudication": {
            "scored_dimensions": ["copy_style"] if contaminated else ["disposition"],
            "serious_error_triggers": [],
            "acceptable_dispositions": {"a": ["draft"]},
            "required_facts": [],
            "supported_claims": [],
            "unsupported_claims": [],
            "canonical_event": event_id,
            "freshness_labels": ["none"],
        },
    }
    case["case_hash"] = digest(case)
    return case


class CorpusValidationTests(unittest.TestCase):
    def test_missing_case_hash_is_rejected(self):
        case = newsdesk_case()
        case.pop("case_hash")
        with self.assertRaisesRegex(EvaluationError, "case_hash"):
            validate_case(case)

    def test_every_visible_leaf_requires_historical_availability(self):
        case = newsdesk_case()
        case["availability"].pop("/input/candidates/0/title")
        case["case_hash"] = digest({key: value for key, value in case.items()
                                    if key != "case_hash"})
        with self.assertRaisesRegex(EvaluationError, "lack available_at"):
            validate_case(case)

    def test_future_field_rejects_case(self):
        case = newsdesk_case()
        case["availability"]["/input/candidates/0/title"] = 101
        case["case_hash"] = digest({key: value for key, value in case.items()
                                    if key != "case_hash"})
        with self.assertRaisesRegex(EvaluationError, "from the future"):
            validate_case(case)

    def test_contaminated_case_cannot_score_editorial_dimensions(self):
        case = newsdesk_case(contaminated=True)
        case["adjudication"]["scored_dimensions"] = ["disposition"]
        case["case_hash"] = digest({key: value for key, value in case.items()
                                    if key != "case_hash"})
        with self.assertRaisesRegex(EvaluationError, "contaminated"):
            validate_case(case)

    def test_calibration_and_holdout_must_be_disjoint(self):
        corpus = {
            "schema_version": "nbn-model-bakeoff-v1",
            "prompt_development_event_ids": [],
            "cases": [newsdesk_case(), newsdesk_case(
                "case-b", split="holdout", event_id="event-a"
            )],
        }
        corpus["corpus_hash"] = digest(corpus)
        with self.assertRaisesRegex(EvaluationError, "overlap"):
            validate_corpus(corpus)

    def test_prompt_development_event_cannot_enter_holdout(self):
        corpus = {
            "schema_version": "nbn-model-bakeoff-v1",
            "prompt_development_event_ids": ["event-b"],
            "cases": [newsdesk_case("case-b", split="holdout", event_id="event-b")],
        }
        corpus["corpus_hash"] = digest(corpus)
        with self.assertRaisesRegex(EvaluationError, "prompt-development"):
            validate_corpus(corpus)

    def test_prep_correctness_requires_full_labels(self):
        case = newsdesk_case()
        case["lane"] = "intake_prep"
        case["adjudication"] = {
            "correctness_scored": True, "scored_dimensions": ["route"],
            "serious_error_triggers": [], "acceptable_routes": ["candidate"],
        }
        case["case_hash"] = digest({key: value for key, value in case.items()
                                    if key != "case_hash"})
        with self.assertRaisesRegex(EvaluationError, "prep adjudication"):
            validate_case(case)

    def test_hash_and_blinding_are_stable(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))
        first = blinded_order("case", ["a", "b", "c"], "seed")
        self.assertEqual(first, blinded_order("case", ["c", "b", "a"], "seed"))
        self.assertEqual({condition for _, condition in first}, {"a", "b", "c"})


class BudgetTests(unittest.TestCase):
    def test_unknown_prices_reject_before_call(self):
        with self.assertRaisesRegex(EvaluationError, "unknown price"):
            conservative_reservation(
                model="imaginary", input_bytes=1, max_output_tokens=1
            )

    def test_hard_cap_reserves_before_call(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = BudgetLedger(Path(directory) / "eval.sqlite", cap_usd=0.10)
            ledger.reserve(lane="probe", condition="a", case_id="x", kind="probe",
                           amount_usd=0.08)
            with self.assertRaisesRegex(EvaluationError, "hard cost cap"):
                ledger.reserve(lane="probe", condition="b", case_id="y", kind="probe",
                               amount_usd=0.03)
            ledger.close()

    def test_unsettled_probe_reservation_survives_restart_as_charged(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eval.sqlite"
            first = BudgetLedger(path, cap_usd=1.0)
            first.reserve(lane="probe", condition="mini", case_id="probe", kind="probe",
                          amount_usd=0.37)
            first.close()
            reopened = BudgetLedger(path, cap_usd=1.0)
            self.assertAlmostEqual(reopened.charged(), 0.37)
            self.assertAlmostEqual(reopened.remaining(), 0.63)
            reopened.close()

    def test_append_only_model_price_update_preserves_existing_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eval.sqlite"
            current = budget.price_manifest()
            previous = json.loads(json.dumps(current))
            previous["version"] = "earlier"
            previous["per_million_tokens"].pop("grok-4.5")
            con = sqlite3.connect(path)
            con.executescript("""
              CREATE TABLE eval_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
              CREATE TABLE eval_requests(
                request_id TEXT PRIMARY KEY, lane TEXT, condition TEXT, case_id TEXT,
                kind TEXT, reserved_usd REAL, actual_usd REAL, charged_usd REAL,
                status TEXT, provider_usage_json TEXT, created_at REAL, settled_at REAL
              );
            """)
            con.execute("INSERT INTO eval_meta VALUES('price_manifest', ?)",
                        (budget.canonical_json(previous),))
            con.execute("INSERT INTO eval_meta VALUES('cap_usd', '40.0')")
            con.commit()
            con.close()

            ledger = BudgetLedger(path)
            stored = ledger.con.execute(
                "SELECT value FROM eval_meta WHERE key='price_manifest'"
            ).fetchone()[0]
            self.assertEqual(json.loads(stored), current)
            ledger.close()

    def test_existing_model_price_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "eval.sqlite"
            first = BudgetLedger(path)
            manifest = json.loads(first.con.execute(
                "SELECT value FROM eval_meta WHERE key='price_manifest'"
            ).fetchone()[0])
            manifest["per_million_tokens"]["grok-4.3"]["input"] = 99
            first.con.execute(
                "UPDATE eval_meta SET value=? WHERE key='price_manifest'",
                (budget.canonical_json(manifest),),
            )
            first.con.commit()
            first.close()
            with self.assertRaisesRegex(EvaluationError, "price manifest changed"):
                BudgetLedger(path)


class IsolationTests(unittest.TestCase):
    def test_adapters_require_explicit_key(self):
        with self.assertRaises(EvaluationError):
            ProviderAdapter(api_key="")

    def test_only_eval_namespace_is_read(self):
        environment = {
            "OPENAI_API_KEY": "prod-openai-canary",
            "NBN_EVAL_OPENAI_API_KEY": "eval-openai-canary",
        }
        self.assertEqual(evaluation_key(environment, "openai"), "eval-openai-canary")
        self.assertIsNone(evaluation_key({"OPENAI_API_KEY": "prod"}, "openai"))

    @patch("nbn.eval.runner.make_adapter")
    def test_production_credentials_never_construct_transport_or_persist(self, make_adapter):
        production = {
            "ANTHROPIC_API_KEY": "PROD-ANTHROPIC-CANARY-91",
            "OPENAI_API_KEY": "PROD-OPENAI-CANARY-82",
            "XAI_API_KEY": "PROD-XAI-CANARY-73",
            "SERPAPI_KEY": "PROD-SERP-CANARY-64",
        }
        case = validate_case(newsdesk_case())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = EvaluationRunner(root, environment=production)
            result = runner.invoke(case, condition_name="mini-low", repetition=1)
            runner.close()
            self.assertEqual(result["status"], "skipped:no_isolated_credential")
            make_adapter.assert_not_called()
            combined = b"".join(path.read_bytes() for path in root.iterdir() if path.is_file())
            for canary in production.values():
                self.assertNotIn(canary.encode(), combined)

    @patch("nbn.eval.runner.make_adapter")
    def test_eval_secret_is_redacted_from_error_database_and_artifacts(self, make_adapter):
        secrets = {
            "NBN_EVAL_ANTHROPIC_API_KEY": "EVAL-ANTHROPIC-CANARY-44",
            "NBN_EVAL_OPENAI_API_KEY": "EVAL-OPENAI-CANARY-55",
            "NBN_EVAL_XAI_API_KEY": "EVAL-XAI-CANARY-66",
            "NBN_EVAL_SERPAPI_KEY": "EVAL-SERP-CANARY-77",
        }

        class FailingAdapter:
            def wire_descriptor(self, **_kwargs):
                return {"safe": True}

            def invoke(self, **_kwargs):
                raise RuntimeError(
                    "transport failure accidentally mentioned " + " ".join(secrets.values())
                )

        make_adapter.return_value = FailingAdapter()
        case = validate_case(newsdesk_case())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = EvaluationRunner(
                root, environment=secrets, cap_usd=1.0
            )
            result = runner.invoke(case, condition_name="mini-low", repetition=1)
            runner.close()
            self.assertEqual(result["status"], "error")
            combined = b"".join(path.read_bytes() for path in root.iterdir() if path.is_file())
            for secret in secrets.values():
                self.assertNotIn(secret, result["error_text"])
                self.assertNotIn(secret.encode(), combined)

    def test_strict_schema_errors_remain_failures(self):
        value = {"decisions": [{"candidate_id": "a", "action": "invented", "reason": "x"}]}
        self.assertTrue(_schema_errors(value, OUTPUT_SCHEMA))

    def test_newsdesk_semantics_require_exact_candidate_coverage(self):
        case = validate_case(newsdesk_case())
        value = {"decisions": []}
        self.assertTrue(_semantic_errors(case, value))

    def test_native_tool_usage_uses_raw_response_when_usage_counter_is_absent(self):
        body = {"output": [{"type": "x_search_call"}, {"type": "message"}]}
        self.assertEqual(_native_tool_usage(body, {}), {"x_search": 1})

    def test_native_tool_usage_normalizes_xai_search_envelope(self):
        body = {
            "output": [
                {"type": "custom_tool_call", "name": "x_keyword_search"},
                {"type": "message"},
            ]
        }
        usage = {"server_side_tool_usage_details": {"x_search_calls": 1}}
        self.assertEqual(_native_tool_usage(body, usage), {"x_search": 1})

    def test_recorded_case_id_cannot_be_reused_with_changed_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = EvaluationRunner(Path(directory), environment={})
            runner.con.execute(
                "INSERT INTO eval_outputs(case_id,case_hash,lane,condition,repetition,status,"
                "requested_model,prompt_hash,contract_hash,normalized_input_hash,"
                "wire_payload_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                ("case-a", "old-hash", "calibration", "mini-low", 1, "ok",
                 "model", "p", "c", "n", "w", 1.0),
            )
            runner.con.commit()
            with self.assertRaisesRegex(EvaluationError, "changed"):
                runner.existing("case-a", "new-hash", "mini-low", 1)
            runner.close()


class FixturePipelineTests(unittest.TestCase):
    @patch("nbn.eval.runner.make_adapter")
    def test_freeze_run_and_blind_report_without_network(self, make_adapter):
        class FixtureAdapter:
            def wire_descriptor(self, **_kwargs):
                return {"safe": True}

            def invoke(self, **_kwargs):
                return ProviderResult(
                    parsed={
                        "decisions": [{
                            "candidate_id": "item-1", "disposition": "publish",
                            "reason": "Useful Bitcoin event.",
                            "post": "NEW: Bitcoin event happened.\n\nThe consequence matters.",
                            "selected_receipt_id": "receipt-item-1",
                            "material_claims": ["Bitcoin event happened"],
                        }],
                        "run_note": "One useful event.",
                    },
                    raw_response={"fixture": True},
                    usage={"input_tokens": 10, "output_tokens": 10},
                    actual_cost_usd=0.001, latency_ms=5,
                    returned_model="fixture-mini", stop_reason="completed",
                )

        make_adapter.return_value = FixtureAdapter()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = {
                "schema_version": "nbn-eval-source-snapshot-v1",
                "captured_at": 200.0,
                "cutoff": 0.0,
                "production_counts": {},
                "table_fingerprints": {},
                "tables": {
                    "items": [{
                        "url_hash": "item-1", "source": "Official", "title": "Bitcoin event",
                        "summary": "A supported event.", "published_at": "", "url": "https://x",
                        "discovery_origin": "fixture", "first_seen": 100.0,
                    }],
                    "desk_preparations": [],
                    "source_resolutions": [{
                        "item_hash": "item-1", "resolved_at": 150.0,
                        "selected_text": "Bitcoin event happened.", "selected_source": "Official",
                        "selected_url": "https://x", "selected_tier": "p0",
                        "selected_category": "official", "originality": "primary_artifact",
                        "support_verdict": 1, "receipt_eligible": 1,
                    }],
                    "posts": [],
                },
            }
            snapshot["snapshot_hash"] = digest(snapshot)
            snapshot_path = root / "snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot))
            registry = {
                "schema_version": "nbn-eval-registry-v1",
                "prompt_development_event_ids": [],
                "packets": [{
                    "packet_id": "desk-1", "split": "calibration", "lane": "calibration",
                    "items": [{
                        "item_hash": "item-1", "event_id": "event-1",
                        "primary_stratum": "primary_artifact",
                        "acceptable_dispositions": ["publish"],
                        "clearly_wrong_dispositions": ["pass"],
                        "required_facts": ["event"], "supported_claims": ["event"],
                        "unsupported_claims": [], "freshness_labels": ["NEW:"],
                        "serious_error_triggers": [],
                    }],
                }],
            }
            registry_path = root / "registry.json"
            registry_path.write_text(json.dumps(registry))
            orientation_path = root / "orientation.md"
            orientation_path.write_text("# Orientation\n\n---\n\nWrite useful Bitcoin news.\n")
            corpus_path = root / "corpus.json"
            freeze_corpus(
                snapshot_path=snapshot_path, registry_path=registry_path,
                orientation_path=orientation_path, output_path=corpus_path,
            )
            _, cases = load_corpus(corpus_path)
            artifacts = root / "artifacts"
            runner = EvaluationRunner(
                artifacts, environment={"NBN_EVAL_OPENAI_API_KEY": "fixture-key"}, cap_usd=1.0
            )
            result = runner.invoke(cases[0], condition_name="mini-low", repetition=1)
            runner.close()
            self.assertEqual(result["status"], "ok")
            con = sqlite3.connect(artifacts / "evaluation.sqlite")
            con.execute(
                "INSERT INTO eval_outputs(case_id,case_hash,lane,condition,repetition,status,"
                "requested_model,prompt_hash,contract_hash,normalized_input_hash,"
                "wire_payload_hash,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                ("foreign-case", "foreign-hash", "editor", "foreign-condition", 1, "ok",
                 "model", "p", "c", "n", "w", 1.0),
            )
            con.commit()
            con.close()
            report = build_report(
                corpus_path=corpus_path, database_path=artifacts / "evaluation.sqlite",
                output_dir=artifacts,
            )
            self.assertTrue(Path(report["blind_review"]).exists())
            self.assertEqual(report["scorecards"]["mini-low"]["disposition_accuracy"], 1.0)
            self.assertNotIn("foreign-condition", report["scorecards"])


if __name__ == "__main__":
    unittest.main()
