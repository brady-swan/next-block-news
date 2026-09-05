"""Freeze registry-selected source rows into immutable, time-bounded model packets."""
from __future__ import annotations

import ast
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .core import EvaluationError, digest, leaf_paths, validate_corpus

NEWS_DESK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 25,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "candidate_id": {"type": "string", "minLength": 1},
                    "disposition": {
                        "type": "string",
                        "enum": ["publish", "update", "research", "hold", "pass"],
                    },
                    "reason": {"type": "string", "minLength": 1, "maxLength": 600},
                    "post": {"type": "string", "maxLength": 8000},
                    "selected_receipt_id": {"type": "string", "maxLength": 120},
                    "material_claims": {
                        "type": "array",
                        "maxItems": 16,
                        "items": {"type": "string", "maxLength": 500},
                    },
                },
                "required": [
                    "candidate_id",
                    "disposition",
                    "reason",
                    "post",
                    "selected_receipt_id",
                    "material_claims",
                ],
            },
        },
        "run_note": {"type": "string", "maxLength": 1000},
    },
    "required": ["decisions", "run_note"],
}

INTAKE_PREP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 30,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "candidate_id": {"type": "string"},
                    "route": {"type": "string", "enum": ["priority", "candidate", "background"]},
                    "category": {"type": "string", "enum": [
                        "bitcoin_direct", "protocol_mining", "custody_security",
                        "policy_regulation", "monetary_macro", "treasury_company",
                        "industry_business", "unrelated",
                    ]},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 240},
                },
                "required": ["candidate_id", "route", "category", "reason"],
            },
        },
    },
    "required": ["decisions"],
}

ASSIGNMENT_PREP_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 30,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "candidate_id": {"type": "string"},
                    "route": {"type": "string", "enum": ["advance", "background"]},
                    "event_summary": {"type": "string", "maxLength": 400},
                    "bitcoin_relevance": {"type": "string", "maxLength": 300},
                    "freshness_note": {"type": "string", "maxLength": 240},
                    "research_objective": {"type": "string", "maxLength": 400},
                    "source_leads": {"type": "array", "maxItems": 8,
                                     "items": {"type": "string", "maxLength": 300}},
                    "related_keys": {"type": "array", "maxItems": 8,
                                     "items": {"type": "string", "maxLength": 200}},
                    "related_storyline_keys": {"type": "array", "maxItems": 2,
                                                "items": {"type": "string", "maxLength": 200}},
                    "event_group": {"type": "string", "minLength": 1, "maxLength": 80},
                },
                "required": [
                    "candidate_id", "route", "event_summary", "bitcoin_relevance",
                    "freshness_note", "research_objective", "source_leads", "related_keys",
                    "related_storyline_keys", "event_group",
                ],
            },
        },
    },
    "required": ["decisions"],
}

EDITOR_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "minItems": 1,
            "maxItems": 12,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "story_id": {"type": "string", "minLength": 1},
                    "verdict": {
                        "type": "string", "enum": ["publish", "revise", "draft", "drop"]
                    },
                    "post": {"type": "string", "maxLength": 8000},
                    "reason": {"type": "string", "minLength": 1, "maxLength": 600},
                },
                "required": ["story_id", "verdict", "post", "reason"],
            },
        },
    },
    "required": ["decisions"],
}


EVAL_DESK_INSTRUCTIONS = """This is a frozen, read-only NBN model evaluation. Make one final
news judgment for every candidate on the desk. Use publish for genuinely fresh first coverage,
update only for a material new development to an event in recent coverage, research or hold for
a worthwhile lead that the supplied evidence cannot yet support, and pass for everything else.

The receipt cards are the only inspected evidence in this exercise. An original lead or guide
post remains a tip unless its card explicitly says it is an inspected first-party statement or
data release. Do not browse or claim that you browsed. A publish/update decision must include
publication-ready X copy and the selected receipt_id. Other decisions must use an empty post and
receipt ID. Account for every candidate exactly once. Write for the scan: put the news first, use
single-sentence or two-sentence short paragraphs with blank lines between each, and stop when the
reader has the change and why it matters."""


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EvaluationError(f"{path} must contain a JSON object")
    return value


def _verified_snapshot(path: Path) -> dict:
    snapshot = _read_json(path)
    if snapshot.get("schema_version") != "nbn-eval-source-snapshot-v1":
        raise EvaluationError("unsupported source snapshot schema")
    claimed = str(snapshot.get("snapshot_hash") or "")
    unhashed = dict(snapshot)
    unhashed.pop("snapshot_hash", None)
    if digest(unhashed) != claimed:
        raise EvaluationError("source snapshot hash mismatch")
    return snapshot


def _orientation(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = "\n---\n"
    if marker not in text:
        raise EvaluationError("orientation brief lacks its separator")
    return text.split(marker, 1)[1].strip()


def _literal_assignment(path: Path, name: str) -> Any:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                return ast.literal_eval(node.value)
            except (TypeError, ValueError) as exc:
                raise EvaluationError(f"{path}:{name} is not a literal") from exc
    raise EvaluationError(f"{path} lacks literal {name}")


def _json_field(value: Any, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _latest_before(rows: list[dict], key: str, value: str, clock: float,
                   timestamp: str) -> dict | None:
    eligible = [row for row in rows if str(row.get(key) or "") == value
                and float(row.get(timestamp) or 0) <= clock]
    return max(eligible, key=lambda row: float(row.get(timestamp) or 0), default=None)


def _stamp_subtree(target: dict[str, float], prefix: str, value: Any, stamp: float) -> None:
    for path in leaf_paths(value, prefix):
        target[path] = float(stamp)


def _candidate_card(item: dict, preparations: list[dict], resolutions: list[dict],
                    clock: float) -> tuple[dict, list[dict], dict[str, float]]:
    item_hash = str(item["url_hash"])
    item_stamp = float(item.get("first_seen") or 0)
    prep = _latest_before(preparations, "item_hash", item_hash, clock, "prepared_at")
    resolution = _latest_before(resolutions, "item_hash", item_hash, clock, "resolved_at")
    card = {
        "candidate_id": item_hash,
        "source": str(item.get("source") or ""),
        "headline_or_post": str(item.get("title") or "")[:2000],
        "summary": str(item.get("summary") or "")[:3000],
        "published_at": str(item.get("published_at") or ""),
        "url": str(item.get("url") or ""),
        "discovery_origin": str(item.get("discovery_origin") or ""),
        "assignment_note": ({
            "route": prep.get("effective_route"),
            "event_summary": prep.get("event_summary"),
            "bitcoin_relevance": prep.get("bitcoin_relevance"),
            "freshness_note": prep.get("freshness_note"),
            "research_objective": prep.get("research_objective"),
            "source_leads": _json_field(prep.get("source_leads_json"), []),
        } if prep else None),
    }
    receipts: list[dict] = []
    stamps: dict[str, float] = {}
    _stamp_subtree(stamps, "", card, max(item_stamp, float(prep.get("prepared_at") or 0)
                                         if prep else item_stamp))
    if resolution and str(resolution.get("selected_text") or "").strip():
        receipts.append({
            "receipt_id": f"receipt-{item_hash[:12]}",
            "candidate_id": item_hash,
            "source": str(resolution.get("selected_source") or ""),
            "url": str(resolution.get("selected_url") or ""),
            "source_tier": str(resolution.get("selected_tier") or ""),
            "source_category": str(resolution.get("selected_category") or ""),
            "originality": str(resolution.get("originality") or ""),
            "support_verdict": bool(resolution.get("support_verdict")),
            "receipt_eligible": bool(resolution.get("receipt_eligible")),
            "text": str(resolution.get("selected_text") or "")[:16000],
        })
    return card, receipts, stamps


def _coverage_cards(posts: list[dict], clock: float) -> tuple[list[dict], dict[str, float]]:
    start = clock - 48 * 3600
    eligible = [row for row in posts if start <= float(row.get("created") or 0) <= clock]
    cards = []
    availability: dict[str, float] = {}
    for row in eligible[-36:]:
        card = {
            "event_key": str(row.get("story_key") or ""),
            "coverage_relation": str(row.get("coverage_relation") or ""),
            "published_or_staged_at": float(row.get("created") or 0),
            "post": str(row.get("body") or "")[:3000],
        }
        index = len(cards)
        cards.append(card)
        _stamp_subtree(availability, f"/input/recent_coverage_48h/{index}", card, clock)
    return cards, availability


def freeze_corpus(*, snapshot_path: Path, registry_path: Path, orientation_path: Path,
                  output_path: Path) -> dict:
    snapshot = _verified_snapshot(snapshot_path)
    registry = _read_json(registry_path)
    if registry.get("schema_version") != "nbn-eval-registry-v1":
        raise EvaluationError("unsupported registry schema")
    tables = snapshot.get("tables") or {}
    items = {str(row["url_hash"]): row for row in tables.get("items") or []}
    clock = float(snapshot["captured_at"])
    prompt_stamp = min(clock, float(orientation_path.stat().st_mtime))
    system = _orientation(orientation_path) + "\n\n" + EVAL_DESK_INSTRUCTIONS
    cases = []
    used: dict[str, str] = {}
    for packet_spec in registry.get("packets") or []:
        cards: list[dict] = []
        receipts: list[dict] = []
        adjudication = {
            "scored_dimensions": [
                "disposition", "evidence", "factual", "copy_style", "continuity",
                "schema", "reliability", "latency", "cost",
            ],
            "serious_error_triggers": {},
            "acceptable_dispositions": {},
            "clearly_wrong_dispositions": {},
            "required_facts": {},
            "supported_claims": {},
            "unsupported_claims": {},
            "canonical_event": {},
            "freshness_labels": {},
            "primary_strata": {},
        }
        event_ids: list[str] = []
        for spec in packet_spec.get("items") or []:
            item_hash = str(spec.get("item_hash") or "")
            if item_hash not in items:
                raise EvaluationError(f"registry item absent from snapshot: {item_hash}")
            event_id = str(spec.get("event_id") or "")
            prior = used.get(event_id)
            if prior and prior != str(packet_spec["split"]):
                raise EvaluationError(f"event {event_id} crosses corpus splits")
            used[event_id] = str(packet_spec["split"])
            card, found_receipts, _ = _candidate_card(
                items[item_hash], tables.get("desk_preparations") or [],
                tables.get("source_resolutions") or [], clock,
            )
            cards.append(card)
            receipts.extend(found_receipts)
            event_ids.append(event_id)
            adjudication["acceptable_dispositions"][item_hash] = spec[
                "acceptable_dispositions"
            ]
            adjudication["clearly_wrong_dispositions"][item_hash] = spec.get(
                "clearly_wrong_dispositions", []
            )
            adjudication["required_facts"][item_hash] = spec.get("required_facts", [])
            adjudication["supported_claims"][item_hash] = spec.get("supported_claims", [])
            adjudication["unsupported_claims"][item_hash] = spec.get("unsupported_claims", [])
            adjudication["canonical_event"][item_hash] = event_id
            adjudication["freshness_labels"][item_hash] = spec.get("freshness_labels", ["none"])
            adjudication["primary_strata"][item_hash] = spec.get("primary_stratum", "other")
            adjudication["serious_error_triggers"][item_hash] = spec.get(
                "serious_error_triggers", []
            )
        recent, recent_availability = _coverage_cards(tables.get("posts") or [], clock)
        packet = {
            "system": system,
            "input": {
                "desk_as_of_epoch": clock,
                "candidate_count": len(cards),
                "candidates": cards,
                "inspected_receipts": receipts,
                "recent_coverage_48h": recent,
            },
            "max_output_tokens": 5000,
        }
        availability = {path: clock for path in leaf_paths(packet)}
        _stamp_subtree(availability, "/system", packet["system"], prompt_stamp)
        availability.update(recent_availability)
        case = {
            "case_id": str(packet_spec["packet_id"]),
            "event_ids": event_ids,
            "lane": str(packet_spec["lane"]),
            "split": str(packet_spec["split"]),
            "editorial_clock": clock,
            "packet": packet,
            "availability": availability,
            "output_schema": NEWS_DESK_SCHEMA,
            "adjudication": adjudication,
            "training_contaminated": False,
            "source_snapshot_hash": snapshot["snapshot_hash"],
            "registry_hash": digest(registry),
        }
        case["case_hash"] = digest(case)
        cases.append(case)
    corpus = {
        "schema_version": "nbn-model-bakeoff-v1",
        "created_at": clock,
        "source_snapshot_hash": snapshot["snapshot_hash"],
        "registry_hash": digest(registry),
        "orientation_hash": digest(system),
        "prompt_development_event_ids": registry.get("prompt_development_event_ids") or [],
        "cases": cases,
    }
    corpus["corpus_hash"] = digest(corpus)
    validate_corpus(corpus)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return {
        "output": str(output_path),
        "corpus_hash": corpus["corpus_hash"],
        "cases": len(cases),
        "events": sum(len(case["event_ids"]) for case in cases),
        "source_snapshot_hash": snapshot["snapshot_hash"],
    }


def result_candidate_ids(case: Any, value: dict) -> list[str]:
    input_value = case.packet["input"]
    cards = input_value.get("candidates") or input_value.get("feed_cards") or []
    expected = [str(row["candidate_id"]) for row in cards]
    actual = [str(row.get("candidate_id") or "") for row in value.get("decisions") or []]
    if len(actual) != len(set(actual)):
        raise EvaluationError("result repeats a candidate_id")
    missing = sorted(set(expected) - set(actual))
    unknown = sorted(set(actual) - set(expected))
    if missing or unknown:
        raise EvaluationError(f"result candidate coverage mismatch missing={missing} unknown={unknown}")
    return actual


def objective_scores(case: Any, value: dict) -> dict:
    result_candidate_ids(case, value)
    acceptable = case.adjudication.get("acceptable_dispositions") or {}
    wrong = case.adjudication.get("clearly_wrong_dispositions") or {}
    decisions = {str(row["candidate_id"]): row for row in value["decisions"]}
    correct = 0
    serious = []
    rows = []
    for candidate_id, allowed in acceptable.items():
        disposition = str(decisions[candidate_id]["disposition"])
        is_correct = disposition in set(allowed)
        correct += int(is_correct)
        if disposition in set(wrong.get(candidate_id) or []):
            serious.append(candidate_id)
        rows.append({
            "candidate_id": candidate_id,
            "disposition": disposition,
            "acceptable": list(allowed),
            "correct": is_correct,
        })
    return {
        "disposition_correct": correct,
        "disposition_total": len(acceptable),
        "serious_disposition_cases": serious,
        "rows": rows,
    }


def editor_objective_scores(case: Any, value: dict) -> dict:
    result_story_ids(case, value)
    acceptable = case.adjudication.get("acceptable_verdicts") or {}
    decisions = {str(row["story_id"]): row for row in value["decisions"]}
    correct = 0
    rows = []
    for story_id, allowed in acceptable.items():
        verdict = str(decisions[story_id]["verdict"])
        is_correct = verdict in set(allowed)
        correct += int(is_correct)
        rows.append({
            "story_id": story_id, "verdict": verdict,
            "acceptable": list(allowed), "correct": is_correct,
        })
    return {"disposition_correct": correct, "disposition_total": len(acceptable),
            "serious_disposition_cases": [], "rows": rows}


def corpus_manifest(corpus_path: Path) -> dict:
    corpus = _read_json(corpus_path)
    cases = validate_corpus(corpus)
    strata: dict[str, int] = defaultdict(int)
    for case in cases:
        for value in (case.adjudication.get("primary_strata") or {}).values():
            strata[str(value)] += 1
    return {
        "corpus_hash": corpus.get("corpus_hash"),
        "cases": len(cases),
        "events": sum(len(case.event_ids) for case in cases),
        "splits": sorted({case.split for case in cases}),
        "lanes": sorted({case.lane for case in cases}),
        "strata": dict(sorted(strata.items())),
    }


def _prep_card(item: dict) -> dict:
    return {
        "candidate_id": str(item.get("url_hash") or "")[:64],
        "origin": str(item.get("discovery_origin") or "")[:40],
        "source": str(item.get("source") or "")[:120],
        "title": str(item.get("title") or "")[:300],
        "summary": str(item.get("summary") or "")[:500],
        "published": str(item.get("published_at") or "")[:100],
        "url": str(item.get("url") or "")[:1000],
    }


def _prep_cases(*, rows: list[dict], lane: str, split: str, system: str,
                output_schema: dict, clock: float, snapshot_hash: str,
                prompt_stamp: float, batch_size: int = 25) -> list[dict]:
    cases = []
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        packet = {
            "system": system,
            "input": {"feed_cards": [_prep_card(row) for row in batch]},
            "max_output_tokens": 6000,
        }
        availability = {path: clock for path in leaf_paths(packet)}
        _stamp_subtree(availability, "/system", system, prompt_stamp)
        adjudication = {
            "correctness_scored": False,
            "scored_dimensions": ["schema", "reliability", "latency", "cost"],
            "serious_error_triggers": [],
            "preserved_fields": [
                "candidate_id", "source", "title", "summary", "published", "url",
            ],
            "note": "Unadjudicated before output; route/category correctness is excluded. "
                    "Blind-review only disagreements before making a replacement decision.",
        }
        case = {
            "case_id": f"{lane}-{start // batch_size + 1:02d}",
            "event_ids": [f"raw-item:{row['url_hash']}" for row in batch],
            "lane": lane,
            "split": split,
            "editorial_clock": clock,
            "packet": packet,
            "availability": availability,
            "output_schema": output_schema,
            "adjudication": adjudication,
            "training_contaminated": False,
            "source_snapshot_hash": snapshot_hash,
        }
        case["case_hash"] = digest(case)
        cases.append(case)
    return cases


def freeze_preparation_corpus(*, snapshot_path: Path, intake_source_path: Path,
                              assignment_source_path: Path, output_path: Path,
                              item_count: int = 300) -> dict:
    snapshot = _verified_snapshot(snapshot_path)
    tables = snapshot.get("tables") or {}
    clock = float(snapshot["captured_at"])
    all_items = list(tables.get("items") or [])
    triaged_ids = {str(row.get("item_hash") or "") for row in tables.get("intake_triage") or []}
    prepared_ids = {
        str(row.get("item_hash") or "") for row in tables.get("desk_preparations") or []
    }
    by_id = {str(row.get("url_hash") or ""): row for row in all_items}
    intake_rows = [by_id[value] for value in sorted(triaged_ids) if value in by_id]
    assignment_rows = [by_id[value] for value in sorted(prepared_ids) if value in by_id]
    # Stable hash ordering prevents cherry-picking after any candidate output is observed.
    intake_rows.sort(key=lambda row: digest(f"intake-v1:{row['url_hash']}"))
    assignment_rows.sort(key=lambda row: digest(f"assignment-v1:{row['url_hash']}"))
    per_lane = max(1, int(item_count) // 2)
    intake_rows = intake_rows[:per_lane]
    assignment_rows = assignment_rows[:max(1, int(item_count) - len(intake_rows))]
    intake_system = str(_literal_assignment(intake_source_path, "SYSTEM"))
    assignment_system = str(_literal_assignment(assignment_source_path, "SYSTEM"))
    cases = _prep_cases(
        rows=intake_rows, lane="intake_prep", split="preparation",
        system=intake_system, output_schema=INTAKE_PREP_SCHEMA, clock=clock,
        snapshot_hash=snapshot["snapshot_hash"],
        prompt_stamp=min(clock, intake_source_path.stat().st_mtime),
    )
    cases.extend(_prep_cases(
        rows=assignment_rows, lane="assignment_prep", split="preparation",
        system=assignment_system, output_schema=ASSIGNMENT_PREP_SCHEMA, clock=clock,
        snapshot_hash=snapshot["snapshot_hash"],
        prompt_stamp=min(clock, assignment_source_path.stat().st_mtime),
    ))
    corpus = {
        "schema_version": "nbn-model-bakeoff-v1",
        "created_at": clock,
        "source_snapshot_hash": snapshot["snapshot_hash"],
        "prompt_development_event_ids": [],
        "cases": cases,
    }
    corpus["corpus_hash"] = digest(corpus)
    validate_corpus(corpus)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return {
        "output": str(output_path), "corpus_hash": corpus["corpus_hash"],
        "cases": len(cases), "intake_items": len(intake_rows),
        "assignment_items": len(assignment_rows), "source_snapshot_hash": snapshot["snapshot_hash"],
    }


def _editor_receipts(story: dict, resolutions: list[dict], clock: float) -> list[dict]:
    receipts = []
    for item_hash in story.get("member_candidate_ids") or []:
        row = _latest_before(resolutions, "item_hash", str(item_hash), clock, "resolved_at")
        if not row or not str(row.get("selected_text") or "").strip():
            continue
        receipts.append({
            "receipt_id": f"receipt-{str(item_hash)[:12]}",
            "source": str(row.get("selected_source") or ""),
            "url": str(row.get("selected_url") or ""),
            "source_tier": str(row.get("selected_tier") or ""),
            "originality": str(row.get("originality") or ""),
            "text": str(row.get("selected_text") or "")[:16000],
        })
    if not receipts and story.get("story_key"):
        eligible = [row for row in resolutions
                    if str(row.get("story_key") or "") == str(story["story_key"])
                    and float(row.get("resolved_at") or 0) <= clock
                    and str(row.get("selected_text") or "").strip()]
        for row in sorted(eligible, key=lambda value: float(value.get("resolved_at") or 0),
                          reverse=True)[:2]:
            receipts.append({
                "receipt_id": f"receipt-{str(row.get('item_hash') or '')[:12]}",
                "source": str(row.get("selected_source") or ""),
                "url": str(row.get("selected_url") or ""),
                "source_tier": str(row.get("selected_tier") or ""),
                "originality": str(row.get("originality") or ""),
                "text": str(row.get("selected_text") or "")[:16000],
            })
    return receipts[:8]


def freeze_editor_corpus(*, snapshot_path: Path, editor_source_path: Path,
                         orientation_path: Path, output_path: Path) -> dict:
    snapshot = _verified_snapshot(snapshot_path)
    tables = snapshot.get("tables") or {}
    clock = float(snapshot["captured_at"])
    runs = {str(row["run_id"]): row for row in tables.get("newsroom_runs") or []}
    pools: dict[str, list[dict]] = {"good": [], "salvageable": [], "reject": []}
    for commit in tables.get("newsroom_story_commits") or []:
        details = _json_field(commit.get("details_json"), {})
        editor = details.get("editor") if isinstance(details, dict) else None
        verdict = str((editor or {}).get("verdict") or "")
        category = {"publish": "good", "revise": "salvageable", "drop": "reject"}.get(verdict)
        if not category:
            continue
        run = runs.get(str(commit.get("run_id") or ""))
        if not run:
            continue
        dossier = _json_field(run.get("dossier_json"), {})
        story = next((row for row in dossier.get("stories") or []
                      if str(row.get("story_id") or "") == str(commit.get("story_id") or "")), None)
        if not story or not str(story.get("post") or "").strip():
            continue
        receipts = _editor_receipts(
            story, tables.get("source_resolutions") or [], clock
        )
        if not receipts:
            continue
        pools[category].append({
            "story_id": f"{commit['run_id']}::{commit['story_id']}",
            "story_key": str(story.get("story_key") or ""),
            "candidate_post": str(story.get("post") or "")[:8000],
            "reader_value": str(story.get("reader_value") or "")[:1000],
            "elevated_claim": bool(story.get("elevated_claim")),
            "inspected_receipts": receipts,
            "recent_coverage_event_keys": [
                str(row.get("story_key") or "") for row in tables.get("posts") or []
                if float(row.get("created") or 0) <= float(run.get("created_at") or clock)
            ][-36:],
            "hidden_baseline": {
                "class": category,
                "verdict": verdict,
                "reason": str((editor or {}).get("reason") or "")[:1000],
            },
        })
    owner_rejects = {
        "capital-b-adam-back-financing-bitcoin-treasury": (
            "Below the high treasury-company bar; transaction detail does not create importance."
        ),
        "waller-supports-holding-rates-steady-sept2026": (
            "Generic Fed beat reporting without a concrete Bitcoin development."
        ),
        "norway-nbim-treasury-allocation-cut-2026": (
            "A small macro allocation change without a direct, material Bitcoin connection."
        ),
        "druckenmiller-duquesne-bitcoin-miners-13f-q2-2026": (
            "Small indirect miner-equity positions do not clear the Bitcoin story bar."
        ),
        "sberbank-crypto-cross-border-settlements-launch": (
            "Generic cryptocurrency settlement service; the evidence does not establish Bitcoin use."
        ),
    }
    existing_story_keys = {
        row["story_key"] for values in pools.values() for row in values
    }
    resolutions = tables.get("source_resolutions") or []
    for post in tables.get("posts") or []:
        story_key = str(post.get("story_key") or "")
        if story_key not in owner_rejects or story_key in existing_story_keys:
            continue
        receipts = _editor_receipts(
            {"story_key": story_key, "member_candidate_ids": [post.get("item_hash")]},
            resolutions, clock,
        )
        if not receipts or not str(post.get("body") or "").strip():
            continue
        pools["reject"].append({
            "story_id": f"owner-post::{post['id']}",
            "story_key": story_key,
            "candidate_post": str(post.get("body") or "")[:8000],
            "reader_value": "",
            "elevated_claim": False,
            "inspected_receipts": receipts,
            "recent_coverage_event_keys": [],
            "hidden_baseline": {
                "class": "reject", "verdict": "drop", "reason": owner_rejects[story_key],
                "basis": "owner feedback recorded in orientation examples",
            },
        })
        existing_story_keys.add(story_key)
    selected = []
    for category in ("good", "salvageable", "reject"):
        ordered = sorted(
            pools[category], key=lambda row: digest(f"editor-v1:{row['story_id']}")
        )
        if len(ordered) < 8:
            raise EvaluationError(
                f"editor corpus lacks eight {category} examples; found "
                f"{len(ordered)} after evidence validation"
            )
        selected.extend(ordered[:8])
    prompt = str(_literal_assignment(editor_source_path, "BATCH_EDITOR_PROMPT"))
    system = (
        prompt + "\n\nSHARED EDITORIAL ORIENTATION\n" + _orientation(orientation_path)
        + "\n\nEVALUATION CONTRACT NOTE\nThe strict cross-provider schema uses an empty "
          "string, rather than null, in post when verdict is drop."
    )
    prompt_stamp = min(clock, editor_source_path.stat().st_mtime,
                       orientation_path.stat().st_mtime)
    cases = []
    for start in range(0, len(selected), 4):
        batch = selected[start:start + 4]
        visible = [{key: value for key, value in row.items() if key != "hidden_baseline"}
                   for row in batch]
        packet = {
            "system": system,
            "input": {"candidates": visible},
            "max_output_tokens": 8000,
        }
        availability = {path: clock for path in leaf_paths(packet)}
        _stamp_subtree(availability, "/system", system, prompt_stamp)
        adjudication = {
            "scored_dimensions": [
                "editor_verdict", "factual", "copy_style", "restraint", "schema",
                "reliability", "latency", "cost",
            ],
            "serious_error_triggers": {
                row["story_id"]: ["approve a hidden reject without removing its material defect"]
                for row in batch if row["hidden_baseline"]["class"] == "reject"
            },
            "acceptable_verdicts": {
                row["story_id"]: ({
                    "good": ["publish", "revise"],
                    "salvageable": ["revise", "draft"],
                    "reject": ["drop"],
                }[row["hidden_baseline"]["class"]]) for row in batch
            },
            "baseline_basis": {
                row["story_id"]: row["hidden_baseline"] for row in batch
            },
            "note": "Production editor outcome stratifies the fixed set; owner blind review "
                    "remains authoritative and may override it.",
        }
        case = {
            "case_id": f"editor-{start // 4 + 1:02d}",
            "event_ids": [f"editor-story:{row['story_id']}" for row in batch],
            "lane": "editor",
            "split": "editor",
            "editorial_clock": clock,
            "packet": packet,
            "availability": availability,
            "output_schema": EDITOR_SCHEMA,
            "adjudication": adjudication,
            "training_contaminated": False,
            "source_snapshot_hash": snapshot["snapshot_hash"],
        }
        case["case_hash"] = digest(case)
        cases.append(case)
    corpus = {
        "schema_version": "nbn-model-bakeoff-v1",
        "created_at": clock,
        "source_snapshot_hash": snapshot["snapshot_hash"],
        "prompt_development_event_ids": [],
        "cases": cases,
    }
    corpus["corpus_hash"] = digest(corpus)
    validate_corpus(corpus)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(corpus, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    return {
        "output": str(output_path), "corpus_hash": corpus["corpus_hash"],
        "cases": len(cases), "drafts": len(selected),
        "strata": {name: 8 for name in pools},
        "source_snapshot_hash": snapshot["snapshot_hash"],
    }


def result_story_ids(case: Any, value: dict) -> list[str]:
    expected = [str(row["story_id"]) for row in case.packet["input"]["candidates"]]
    actual = [str(row.get("story_id") or "") for row in value.get("decisions") or []]
    if len(actual) != len(set(actual)):
        raise EvaluationError("result repeats a story_id")
    missing = sorted(set(expected) - set(actual))
    unknown = sorted(set(actual) - set(expected))
    if missing or unknown:
        raise EvaluationError(f"result story coverage mismatch missing={missing} unknown={unknown}")
    return actual
