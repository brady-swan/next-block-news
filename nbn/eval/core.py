"""Immutable corpus validation, hashing, redaction, and blinded ordering."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class EvaluationError(ValueError):
    """Raised before inference when an evaluation invariant is not satisfied."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_json(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def leaf_paths(value: Any, prefix: str = "") -> set[str]:
    """Return JSON Pointer paths for every model-visible scalar, including empty containers."""
    if isinstance(value, dict):
        if not value:
            return {prefix or "/"}
        paths: set[str] = set()
        for key, child in value.items():
            paths.update(leaf_paths(child, f"{prefix}/{_pointer_escape(str(key))}"))
        return paths
    if isinstance(value, list):
        if not value:
            return {prefix or "/"}
        paths = set()
        for index, child in enumerate(value):
            paths.update(leaf_paths(child, f"{prefix}/{index}"))
        return paths
    return {prefix or "/"}


@dataclass(frozen=True)
class ValidatedCase:
    case_id: str
    event_ids: tuple[str, ...]
    lane: str
    split: str
    editorial_clock: float
    packet: dict
    output_schema: dict
    adjudication: dict
    training_contaminated: bool
    case_hash: str


_SCORED_LANES = {"calibration", "newsdesk", "research_judgment", "editor",
                 "intake_prep", "assignment_prep"}
_PREP_LANES = {"intake_prep", "assignment_prep"}
_CONTAMINATED_ALLOWED = {"copy_style", "schema", "reliability", "latency", "cost"}


def _validate_adjudication(case: dict) -> None:
    adjudication = case.get("adjudication")
    if not isinstance(adjudication, dict):
        raise EvaluationError("missing adjudication")
    if case.get("lane") in _SCORED_LANES:
        required = {"scored_dimensions", "serious_error_triggers"}
        missing = required - set(adjudication)
        if missing:
            raise EvaluationError(f"adjudication missing {sorted(missing)}")
    if case.get("lane") in {"calibration", "newsdesk", "research_judgment"}:
        required = {"acceptable_dispositions", "required_facts", "supported_claims",
                    "unsupported_claims", "canonical_event", "freshness_labels"}
        missing = required - set(adjudication)
        if missing:
            raise EvaluationError(f"newsdesk adjudication missing {sorted(missing)}")
    if case.get("lane") in _PREP_LANES and adjudication.get("correctness_scored", True):
        required = {"acceptable_routes", "acceptable_categories", "event_group",
                    "source_leads", "storyline_keys", "preserved_fields"}
        missing = required - set(adjudication)
        if missing:
            raise EvaluationError(f"prep adjudication missing {sorted(missing)}")


def validate_case(case: dict) -> ValidatedCase:
    required = {"case_id", "event_ids", "lane", "split", "editorial_clock", "packet",
                "availability", "output_schema", "adjudication", "training_contaminated",
                "case_hash"}
    missing = required - set(case)
    if missing:
        raise EvaluationError(f"case missing {sorted(missing)}")
    if not isinstance(case["packet"], dict) or not isinstance(case["output_schema"], dict):
        raise EvaluationError("packet and output_schema must be objects")
    clock = float(case["editorial_clock"])
    availability = case["availability"]
    if not isinstance(availability, dict):
        raise EvaluationError("availability must be an object")
    leaves = leaf_paths(case["packet"])
    missing_times = sorted(leaves - set(availability))
    extra_times = sorted(set(availability) - leaves)
    if missing_times:
        raise EvaluationError(f"model-visible fields lack available_at: {missing_times[:5]}")
    if extra_times:
        raise EvaluationError(f"availability has unknown fields: {extra_times[:5]}")
    late = sorted(path for path, stamp in availability.items() if float(stamp) > clock)
    if late:
        raise EvaluationError(f"model-visible fields are from the future: {late[:5]}")
    _validate_adjudication(case)
    contaminated = bool(case["training_contaminated"])
    scored = set(case["adjudication"].get("scored_dimensions") or [])
    if contaminated and not scored.issubset(_CONTAMINATED_ALLOWED):
        raise EvaluationError("training-contaminated case scores editorial knowledge")
    event_ids = tuple(str(value) for value in case["event_ids"])
    if not event_ids or any(not value for value in event_ids):
        raise EvaluationError("event_ids must be nonempty")
    case_copy = dict(case)
    declared_hash = case_copy.pop("case_hash", None)
    computed_hash = digest(case_copy)
    if declared_hash != computed_hash:
        raise EvaluationError("case hash mismatch")
    return ValidatedCase(
        case_id=str(case["case_id"]), event_ids=event_ids, lane=str(case["lane"]),
        split=str(case["split"]), editorial_clock=clock, packet=case["packet"],
        output_schema=case["output_schema"], adjudication=case["adjudication"],
        training_contaminated=contaminated, case_hash=computed_hash,
    )


def validate_corpus(document: dict) -> list[ValidatedCase]:
    if document.get("schema_version") != "nbn-model-bakeoff-v1":
        raise EvaluationError("unsupported corpus schema")
    corpus_copy = dict(document)
    declared_hash = corpus_copy.pop("corpus_hash", None)
    if declared_hash != digest(corpus_copy):
        raise EvaluationError("corpus hash mismatch")
    cases = [validate_case(value) for value in document.get("cases") or []]
    if not cases:
        raise EvaluationError("corpus is empty")
    ids: set[str] = set()
    split_events: dict[str, set[str]] = {}
    for case in cases:
        if case.case_id in ids:
            raise EvaluationError(f"duplicate case_id {case.case_id}")
        ids.add(case.case_id)
        split_events.setdefault(case.split, set()).update(case.event_ids)
    calibration = split_events.get("calibration", set())
    holdout = split_events.get("holdout", set())
    overlap = sorted(calibration & holdout)
    if overlap:
        raise EvaluationError(f"calibration/holdout event overlap: {overlap[:5]}")
    excluded = set(document.get("prompt_development_event_ids") or [])
    contaminated_holdout = sorted(holdout & excluded)
    if contaminated_holdout:
        raise EvaluationError(f"prompt-development events in holdout: {contaminated_holdout[:5]}")
    return cases


def load_corpus(path: Path) -> tuple[dict, list[ValidatedCase]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return document, validate_corpus(document)


class SecretRedactor:
    """Remove explicitly supplied secrets before any artifact or log boundary."""

    def __init__(self, secrets: Iterable[str]):
        self._secrets = tuple(sorted({str(value) for value in secrets if value}, key=len,
                                     reverse=True))

    def text(self, value: Any) -> str:
        result = str(value)
        for secret in self._secrets:
            result = result.replace(secret, "[REDACTED]")
        return result

    def value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self.value(child) for key, child in value.items()}
        if isinstance(value, list):
            return [self.value(child) for child in value]
        if isinstance(value, tuple):
            return [self.value(child) for child in value]
        if isinstance(value, str):
            return self.text(value)
        return value


def blinded_order(case_id: str, conditions: Iterable[str], seed: str) -> list[tuple[str, str]]:
    ordered = sorted(set(conditions), key=lambda value: digest(f"{seed}:{case_id}:{value}"))
    return [(f"Model {chr(65 + index)}", condition) for index, condition in enumerate(ordered)]


def append_jsonl(path: Path, value: dict, redactor: SecretRedactor) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json(redactor.value(value))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
