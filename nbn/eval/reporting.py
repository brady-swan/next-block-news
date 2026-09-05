"""Objective scorecards and blinded copy-review artifacts for model evaluation."""
from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .core import EvaluationError, blinded_order, canonical_json, load_corpus
from .corpus import editor_objective_scores, objective_scores


def _style(post: str) -> dict:
    text = str(post or "").strip()
    if not text:
        return {"words": 0, "paragraphs": 0, "sentences": 0,
                "mean_sentence_words": 0.0, "long_sentences": 0}
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text)
                 if part.strip()]
    sentence_words = [len(re.findall(r"\b[\w’'-]+\b", sentence))
                      for sentence in sentences]
    return {
        "words": len(re.findall(r"\b[\w’'-]+\b", text)),
        "paragraphs": len(paragraphs),
        "sentences": len(sentences),
        "mean_sentence_words": round(mean(sentence_words), 2) if sentence_words else 0.0,
        "long_sentences": sum(value > 30 for value in sentence_words),
    }


def build_report(*, corpus_path: Path, database_path: Path, output_dir: Path,
                 blind_seed: str = "nbn-owner-review-v1") -> dict:
    _document, cases = load_corpus(corpus_path)
    by_case = {case.case_id: case for case in cases}
    con = sqlite3.connect(database_path)
    con.row_factory = sqlite3.Row
    rows = [dict(row) for row in con.execute(
        "SELECT * FROM eval_outputs WHERE lane!='probe' ORDER BY case_id,repetition,"
        "execution_position,condition"
    ) if str(row["case_id"]) in by_case]
    con.close()
    aggregate: dict[str, dict] = defaultdict(lambda: {
        "attempts": 0, "ok": 0, "invalid_or_error": 0,
        "disposition_correct": 0, "disposition_total": 0,
        "serious_disposition_case_ids": set(), "cost_usd": 0.0,
        "latencies_ms": [], "style": [],
    })
    conditions_by_case: dict[str, set[str]] = defaultdict(set)
    parsed_rows = []
    for row in rows:
        case = by_case.get(str(row["case_id"]))
        if case is None:
            raise EvaluationError(f"output references unknown case {row['case_id']}")
        bucket = aggregate[str(row["condition"])]
        bucket["attempts"] += 1
        bucket["cost_usd"] += float(row.get("actual_cost_usd") or 0)
        bucket["latencies_ms"].append(int(row.get("latency_ms") or 0))
        conditions_by_case[case.case_id].add(str(row["condition"]))
        parsed = json.loads(row.get("parsed_json") or "{}")
        objective = None
        if row["status"] == "ok":
            bucket["ok"] += 1
            if case.lane in {"calibration", "newsdesk", "research_judgment"}:
                objective = objective_scores(case, parsed)
            elif case.lane == "editor":
                objective = editor_objective_scores(case, parsed)
            if objective:
                bucket["disposition_correct"] += objective["disposition_correct"]
                bucket["disposition_total"] += objective["disposition_total"]
                bucket["serious_disposition_case_ids"].update(
                    f"{case.case_id}:{candidate}" for candidate in
                    objective["serious_disposition_cases"]
                )
            for decision in parsed.get("decisions") or []:
                if (decision.get("disposition") in {"publish", "update"}
                        or decision.get("verdict") in {"publish", "revise", "draft"}):
                    bucket["style"].append(_style(decision.get("post") or ""))
        else:
            bucket["invalid_or_error"] += 1
        parsed_rows.append({**row, "parsed": parsed, "objective": objective})

    scorecards = {}
    for condition, bucket in sorted(aggregate.items()):
        styles = bucket.pop("style")
        latencies = bucket.pop("latencies_ms")
        serious = sorted(bucket.pop("serious_disposition_case_ids"))
        total = int(bucket["disposition_total"])
        scorecards[condition] = {
            **bucket,
            "cost_usd": round(float(bucket["cost_usd"]), 8),
            "disposition_accuracy": (round(bucket["disposition_correct"] / total, 4)
                                     if total else None),
            "serious_disposition_cases": serious,
            "mean_latency_ms": round(mean(latencies), 1) if latencies else None,
            "mean_post_words": round(mean(row["words"] for row in styles), 1)
            if styles else None,
            "mean_sentence_words": round(mean(row["mean_sentence_words"] for row in styles), 1)
            if styles else None,
            "mean_long_sentences": round(mean(row["long_sentences"] for row in styles), 2)
            if styles else None,
        }

    key: dict[str, dict[str, str]] = {}
    review_lines = [
        "# NBN model bake-off — blinded owner review",
        "",
        "Judge usefulness, lede, information order, clarity, restraint, and factual support ",
        "from the frozen receipts. Record a winner or tie per candidate before opening the key.",
        "",
    ]
    output_lookup = defaultdict(list)
    for row in parsed_rows:
        output_lookup[(row["case_id"], row["condition"])].append(row)
    for case in cases:
        order = blinded_order(case.case_id, conditions_by_case.get(case.case_id, set()), blind_seed)
        key[case.case_id] = {label: condition for label, condition in order}
        review_lines.extend([f"## {case.case_id}", ""])
        cards = (case.packet["input"].get("candidates")
                 or case.packet["input"].get("feed_cards") or [])
        id_key = "story_id" if case.lane == "editor" else "candidate_id"
        for card in cards:
            candidate_id = str(card[id_key])
            if case.lane in {"intake_prep", "assignment_prep"}:
                signatures = set()
                for _label, condition in order:
                    for result in output_lookup[(case.case_id, condition)]:
                        decision = next((item for item in result["parsed"].get("decisions") or []
                                         if item.get(id_key) == candidate_id), None)
                        if decision:
                            signatures.add((decision.get("route"), decision.get("category")))
                if len(signatures) <= 1:
                    continue
            review_lines.extend([
                (f"### {card.get('source') or card.get('story_key') or candidate_id}: "
                 f"{card.get('headline_or_post') or ''}"), "",
                f"Record `{candidate_id}`", "",
            ])
            for label, condition in order:
                for result in output_lookup[(case.case_id, condition)]:
                    decision = next((item for item in result["parsed"].get("decisions") or []
                                     if item.get(id_key) == candidate_id), None)
                    suffix = f" · repeat {result['repetition']}"
                    if result["status"] != "ok" or not decision:
                        review_lines.extend([f"**{label}{suffix}:** `{result['status']}`", ""])
                        continue
                    review_lines.extend([
                        (f"**{label}{suffix}:** `"
                         f"{decision.get('disposition') or decision.get('verdict') or decision.get('route')}` — "
                         f"{decision.get('reason')}"), "",
                    ])
                    if decision.get("post"):
                        review_lines.extend([str(decision["post"]), ""])
                    elif case.lane == "assignment_prep":
                        review_lines.extend([
                            f"Event: {decision.get('event_summary')}", "",
                            f"Bitcoin relevance: {decision.get('bitcoin_relevance')}", "",
                            f"Research objective: {decision.get('research_objective')}", "",
                        ])
            review_lines.extend(["Owner winner/tie: ", "", "Owner notes: ", ""])

    output_dir.mkdir(parents=True, exist_ok=True)
    scorecard_path = output_dir / "objective-scorecards.json"
    scorecard_path.write_text(json.dumps(scorecards, indent=2, sort_keys=True) + "\n")
    review_path = output_dir / "blind-review.md"
    review_path.write_text("\n".join(review_lines).rstrip() + "\n", encoding="utf-8")
    key_path = output_dir / "blind-key.json"
    key_path.write_text(canonical_json(key) + "\n", encoding="utf-8")
    return {
        "scorecards": scorecards,
        "blind_review": str(review_path),
        "blind_key": str(key_path),
        "scorecard_file": str(scorecard_path),
    }
