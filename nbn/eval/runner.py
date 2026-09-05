"""Serialized evaluator: no production imports, cursors, tools, or mutations."""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .budget import BudgetLedger, conservative_reservation
from .core import (
    EvaluationError,
    SecretRedactor,
    ValidatedCase,
    append_jsonl,
    canonical_json,
    digest,
)
from .corpus import result_candidate_ids, result_story_ids
from .providers import CONDITIONS, evaluation_key, make_adapter


def _schema_errors(value: Any, schema: dict, path: str = "$") -> list[str]:
    """Validate the strict JSON subset used by evaluation contracts."""
    errors: list[str] = []
    expected = schema.get("type")
    type_ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)
    if not type_ok:
        return [f"{path}: expected {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value outside enum")
    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        for key in schema.get("required") or []:
            if key not in value:
                errors.append(f"{path}: missing {key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected {key}")
        for key, child in value.items():
            if key in properties:
                errors.extend(_schema_errors(child, properties[key], f"{path}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for index, child in enumerate(value):
            errors.extend(_schema_errors(child, schema["items"], f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{path}: below minLength")
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            errors.append(f"{path}: above maxLength")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{path}: below minItems")
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            errors.append(f"{path}: above maxItems")
    return errors


def _semantic_errors(case: ValidatedCase, value: dict) -> list[str]:
    covered_lanes = {
        "calibration", "newsdesk", "research_judgment", "intake_prep", "assignment_prep",
        "editor",
    }
    if case.lane not in covered_lanes:
        return []
    try:
        if case.lane == "editor":
            result_story_ids(case, value)
        else:
            result_candidate_ids(case, value)
    except EvaluationError as exc:
        return [str(exc)]
    if case.lane in {"intake_prep", "assignment_prep"}:
        return []
    errors: list[str] = []
    if case.lane == "editor":
        for row in value.get("decisions") or []:
            verdict = str(row.get("verdict") or "")
            post = str(row.get("post") or "").strip()
            story_id = str(row.get("story_id") or "")
            if verdict != "drop" and not post:
                errors.append(f"{story_id}: {verdict} lacks final post")
            if verdict == "drop" and post:
                errors.append(f"{story_id}: drop must return an empty post")
        return errors
    for row in value.get("decisions") or []:
        action = str(row.get("disposition") or "")
        post = str(row.get("post") or "").strip()
        receipt = str(row.get("selected_receipt_id") or "").strip()
        candidate = str(row.get("candidate_id") or "")
        if action in {"publish", "update"} and (not post or not receipt):
            errors.append(f"{candidate}: {action} lacks post or receipt")
        if action not in {"publish", "update"} and (post or receipt):
            errors.append(f"{candidate}: {action} must not carry post or receipt")
    return errors


class EvaluationRunner:
    def __init__(self, artifact_dir: Path, *, environment: dict[str, str] | None = None,
                 cap_usd: float = 40.0):
        self.artifact_dir = artifact_dir
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.environment = dict(os.environ if environment is None else environment)
        eval_names = (
            "NBN_EVAL_ANTHROPIC_API_KEY", "NBN_EVAL_OPENAI_API_KEY",
            "NBN_EVAL_XAI_API_KEY", "NBN_EVAL_SERPAPI_KEY",
        )
        self.redactor = SecretRedactor(self.environment.get(name, "") for name in eval_names)
        self.ledger = BudgetLedger(artifact_dir / "evaluation.sqlite", cap_usd=cap_usd)
        self.con = sqlite3.connect(artifact_dir / "evaluation.sqlite")
        self.con.row_factory = sqlite3.Row
        self.con.executescript("""
          CREATE TABLE IF NOT EXISTS eval_outputs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            case_hash TEXT NOT NULL,
            lane TEXT NOT NULL,
            condition TEXT NOT NULL,
            repetition INTEGER NOT NULL,
            execution_position INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            requested_model TEXT NOT NULL,
            returned_model TEXT NOT NULL DEFAULT '',
            effort TEXT,
            prompt_hash TEXT NOT NULL,
            contract_hash TEXT NOT NULL,
            normalized_input_hash TEXT NOT NULL,
            wire_payload_hash TEXT NOT NULL,
            parsed_json TEXT NOT NULL DEFAULT '{}',
            usage_json TEXT NOT NULL DEFAULT '{}',
            error_text TEXT NOT NULL DEFAULT '',
            stop_reason TEXT NOT NULL DEFAULT '',
            latency_ms INTEGER NOT NULL DEFAULT 0,
            actual_cost_usd REAL NOT NULL DEFAULT 0,
            request_id TEXT,
            created_at REAL NOT NULL,
            UNIQUE(case_id,condition,repetition)
          );
        """)
        columns = {row[1] for row in self.con.execute("PRAGMA table_info(eval_outputs)")}
        if "execution_position" not in columns:
            self.con.execute(
                "ALTER TABLE eval_outputs ADD COLUMN execution_position INTEGER NOT NULL DEFAULT 0"
            )
        run_row = self.con.execute(
            "SELECT value FROM eval_meta WHERE key='evaluation_run_id'"
        ).fetchone()
        if run_row:
            self.evaluation_run_id = str(run_row[0])
        else:
            self.evaluation_run_id = uuid.uuid4().hex
            self.con.execute(
                "INSERT INTO eval_meta(key,value) VALUES('evaluation_run_id',?)",
                (self.evaluation_run_id,),
            )
        self.con.commit()

    def close(self) -> None:
        self.con.close()
        self.ledger.close()

    def _record(self, value: dict) -> None:
        clean = self.redactor.value(value)
        columns = [
            "case_id", "case_hash", "lane", "condition", "repetition",
            "execution_position", "status",
            "requested_model", "returned_model", "effort", "prompt_hash",
            "contract_hash", "normalized_input_hash", "wire_payload_hash", "parsed_json",
            "usage_json", "error_text", "stop_reason", "latency_ms", "actual_cost_usd",
            "request_id", "created_at",
        ]
        row = dict(clean)
        for key in ("parsed_json", "usage_json"):
            if not isinstance(row.get(key), str):
                row[key] = canonical_json(row.get(key) or {})
        self.con.execute(
            f"INSERT OR REPLACE INTO eval_outputs({','.join(columns)})"
            f" VALUES({','.join('?' for _ in columns)})",
            tuple(row.get(column) for column in columns),
        )
        self.con.commit()
        append_jsonl(self.artifact_dir / "outputs.jsonl", clean, self.redactor)

    def existing(self, case_id: str, case_hash: str, condition: str, repetition: int) -> bool:
        row = self.con.execute(
            "SELECT status,case_hash FROM eval_outputs"
            " WHERE case_id=? AND condition=? AND repetition=?",
            (case_id, condition, int(repetition)),
        ).fetchone()
        if row and str(row["case_hash"]) != str(case_hash):
            raise EvaluationError(f"case {case_id} changed after an output was recorded")
        return bool(row and row["status"] != "skipped:no_isolated_credential")

    def invoke(self, case: ValidatedCase, *, condition_name: str, repetition: int,
               kind: str = "corpus", execution_position: int = 0) -> dict:
        condition = CONDITIONS.get(condition_name)
        if not condition:
            raise EvaluationError(f"unknown condition {condition_name}")
        if self.existing(case.case_id, case.case_hash, condition.name, repetition):
            return {"status": "existing", "case_id": case.case_id,
                    "condition": condition.name, "repetition": repetition}
        key = evaluation_key(self.environment, condition.provider)
        base = {
            "case_id": case.case_id, "case_hash": case.case_hash, "lane": case.lane,
            "condition": condition.name, "repetition": int(repetition),
            "execution_position": int(execution_position),
            "requested_model": condition.model, "returned_model": "",
            "effort": condition.effort, "prompt_hash": digest(case.packet.get("system", "")),
            "contract_hash": digest(case.output_schema),
            "normalized_input_hash": digest(case.packet), "wire_payload_hash": "",
            "parsed_json": {}, "usage_json": {}, "error_text": "", "stop_reason": "",
            "latency_ms": 0, "actual_cost_usd": 0.0, "request_id": None,
            "created_at": time.time(),
        }
        if not key:
            record = {**base, "status": "skipped:no_isolated_credential"}
            self._record(record)
            return record

        system = str(case.packet.get("system") or "")
        user_payload = case.packet.get("input")
        if not system or not isinstance(user_payload, dict):
            raise EvaluationError("packet requires system text and input object")
        output_name = f"nbn_{case.lane}_result".replace("-", "_")[:64]
        max_output = int(case.packet.get("max_output_tokens") or 4000)
        input_bytes = len(canonical_json(case.packet).encode("utf-8"))
        max_tools = {name: 3 for name in condition.native_tools}
        reserve_usd = conservative_reservation(
            model=condition.model, input_bytes=input_bytes,
            max_output_tokens=max_output, max_tool_calls=max_tools,
        )
        reservation = self.ledger.reserve(
            lane=case.lane, condition=condition.name, case_id=case.case_id,
            kind=kind, amount_usd=reserve_usd,
        )
        base["request_id"] = reservation.request_id
        adapter = None
        try:
            adapter = make_adapter(condition.provider, api_key=key)
            wire = adapter.wire_descriptor(
                condition=condition, system=system, user_payload=user_payload,
                output_schema=case.output_schema, output_name=output_name,
                max_output_tokens=max_output,
            )
            base["wire_payload_hash"] = digest(wire)
            result = adapter.invoke(
                condition=condition, system=system, user_payload=user_payload,
                output_schema=case.output_schema, output_name=output_name,
                max_output_tokens=max_output,
            )
            errors = _schema_errors(result.parsed, case.output_schema)
            if not errors:
                errors.extend(_semantic_errors(case, result.parsed))
            missing_tools = [
                name for name in case.adjudication.get("required_native_tools") or []
                if int((result.usage.get("native_tools") or {}).get(name) or 0) < 1
            ]
            errors.extend(f"required native tool was not used: {name}" for name in missing_tools)
            status = ("ok" if not errors else
                      "invalid_tool_use" if missing_tools else "invalid_schema")
            error_text = "; ".join(errors[:20])
            self.ledger.settle(
                reservation.request_id, actual_usd=result.actual_cost_usd,
                provider_usage=result.usage,
            )
            record = {
                **base, "status": status, "returned_model": result.returned_model,
                "parsed_json": result.parsed, "usage_json": result.usage,
                "error_text": error_text, "stop_reason": result.stop_reason,
                "latency_ms": result.latency_ms,
                "actual_cost_usd": result.actual_cost_usd,
            }
            self._record(record)
            append_jsonl(
                self.artifact_dir / "raw-responses.jsonl",
                {"case_id": case.case_id, "condition": condition.name,
                 "repetition": repetition, "response": result.raw_response},
                self.redactor,
            )
            return record
        except Exception as exc:  # noqa: BLE001 - all provider failures remain scored
            self.ledger.fail(reservation.request_id)
            record = {**base, "status": "error",
                      "error_text": self.redactor.text(f"{type(exc).__name__}: {exc}")}
            self._record(record)
            return record

    def probe(self, condition_names: Iterable[str]) -> list[dict]:
        now = time.time()
        ordinary_schema = {
            "type": "object", "additionalProperties": False,
            "properties": {"ok": {"type": "boolean"},
                           "echo": {"type": "string"}},
            "required": ["ok", "echo"],
        }
        results = []
        for index, name in enumerate(condition_names, start=1):
            condition = CONDITIONS[name]
            if condition.native_tools:
                schema = {
                    "type": "object", "additionalProperties": False,
                    "properties": {
                        "ok": {"type": "boolean"},
                        "finding": {"type": "string"},
                        "source_url": {"type": "string"},
                    },
                    "required": ["ok", "finding", "source_url"],
                }
                packet = {
                    "system": ("You are testing live retrieval. You must use the available "
                               "X search tool at least once, then return the required result."),
                    "input": {
                        "instruction": ("Find a recent Bitcoin news post on X from "
                                        "@BitcoinArchive. Summarize only what the post says and "
                                        "return its x.com URL; use empty strings if unavailable."),
                    },
                    "max_output_tokens": 512,
                }
                case_id = "capability-probe-native-x-search-v2"
                adjudication = {"required_native_tools": list(condition.native_tools)}
            else:
                schema = ordinary_schema
                packet = {
                    "system": "Return the required structured evaluation result.",
                    "input": {"instruction": "Set ok true and echo to nbn-eval-probe."},
                    "max_output_tokens": 256,
                }
                case_id = "capability-probe"
                adjudication = {}
            case = ValidatedCase(
                case_id=case_id, event_ids=(case_id,), lane="probe", split="probe",
                editorial_clock=now, packet=packet, output_schema=schema,
                adjudication=adjudication, training_contaminated=False,
                case_hash=digest({"packet": packet, "output_schema": schema}),
            )
            results.append(self.invoke(
                case, condition_name=name, repetition=1, kind="probe",
                execution_position=index,
            ))
        return results

    def summary(self) -> dict:
        rows = self.con.execute(
            "SELECT lane,condition,status,COUNT(*) calls,SUM(actual_cost_usd) cost,"
            "AVG(latency_ms) avg_latency_ms FROM eval_outputs"
            " GROUP BY lane,condition,status ORDER BY lane,condition,status"
        ).fetchall()
        return {"evaluation_run_id": self.evaluation_run_id,
                "budget": self.ledger.summary(), "outputs": [dict(row) for row in rows]}
