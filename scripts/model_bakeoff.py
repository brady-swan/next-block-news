"""Standalone CLI for Plan 0057's production-isolated model evaluation."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nbn.eval.budget import conservative_reservation, price_manifest
from nbn.eval.core import (
    EvaluationError,
    SecretRedactor,
    canonical_json,
    digest,
    load_corpus,
)
from nbn.eval.corpus import (
    corpus_manifest,
    freeze_corpus,
    freeze_editor_corpus,
    freeze_preparation_corpus,
)
from nbn.eval.providers import CONDITIONS, EVAL_KEY_ENV, discover_models, evaluation_key
from nbn.eval.reporting import build_report
from nbn.eval.runner import EvaluationRunner


def _conditions(value: str) -> list[str]:
    names = [part.strip() for part in value.split(",") if part.strip()]
    unknown = sorted(set(names) - set(CONDITIONS))
    if unknown:
        raise EvaluationError(f"unknown conditions: {unknown}")
    return names


def _runner(args) -> EvaluationRunner:
    return EvaluationRunner(Path(args.artifact_dir), cap_usd=float(args.cap_usd))


def command_validate(args) -> dict:
    document, cases = load_corpus(Path(args.corpus))
    return {"status": "valid", **corpus_manifest(Path(args.corpus)),
            "validated_cases": len(cases), "declared_hash": document.get("corpus_hash")}


def command_freeze(args) -> dict:
    return freeze_corpus(
        snapshot_path=Path(args.snapshot), registry_path=Path(args.registry),
        orientation_path=Path(args.orientation), output_path=Path(args.output),
    )


def command_freeze_prep(args) -> dict:
    return freeze_preparation_corpus(
        snapshot_path=Path(args.snapshot),
        intake_source_path=Path(args.intake_source),
        assignment_source_path=Path(args.assignment_source),
        output_path=Path(args.output), item_count=int(args.item_count),
    )


def command_freeze_editor(args) -> dict:
    return freeze_editor_corpus(
        snapshot_path=Path(args.snapshot), editor_source_path=Path(args.editor_source),
        orientation_path=Path(args.orientation), output_path=Path(args.output),
    )


def command_estimate(args) -> dict:
    _, cases = load_corpus(Path(args.corpus))
    conditions = _conditions(args.conditions)
    rows = []
    total = 0.0
    for case in cases:
        if args.lane and case.lane != args.lane:
            continue
        packet_bytes = len(canonical_json(case.packet).encode("utf-8"))
        maximum = int(case.packet.get("max_output_tokens") or 4000)
        for condition_name in conditions:
            condition = CONDITIONS[condition_name]
            amount = conservative_reservation(
                model=condition.model, input_bytes=packet_bytes,
                max_output_tokens=maximum,
                max_tool_calls={name: 3 for name in condition.native_tools},
            )
            amount *= int(args.repetitions)
            rows.append({"case_id": case.case_id, "condition": condition_name,
                         "repetitions": int(args.repetitions),
                         "reserved_usd": round(amount, 8)})
            total += amount
    return {"price_manifest": price_manifest(), "planned": rows,
            "conservative_total_usd": round(total, 8),
            "within_cap": total <= float(args.cap_usd)}


def command_probe(args) -> dict:
    runner = _runner(args)
    try:
        names = _conditions(args.conditions)
        results = runner.probe(names)
        return {"results": results, "summary": runner.summary()}
    finally:
        runner.close()


def command_run(args) -> dict:
    document, cases = load_corpus(Path(args.corpus))
    names = _conditions(args.conditions)
    runner = _runner(args)
    results = []
    try:
        for case in cases:
            if args.lane and case.lane != args.lane:
                continue
            for repetition in range(1, int(args.repetitions) + 1):
                ordered = sorted(
                    names,
                    key=lambda name: digest(
                        f"{args.seed}:{document.get('corpus_hash')}:{case.case_id}:"
                        f"{repetition}:{name}"
                    ),
                )
                for position, name in enumerate(ordered, start=1):
                    results.append(runner.invoke(
                        case, condition_name=name, repetition=repetition,
                        execution_position=position,
                    ))
        return {"results": results, "summary": runner.summary()}
    finally:
        runner.close()


def command_report(args) -> dict:
    runner = _runner(args)
    try:
        summary = runner.summary()
    finally:
        runner.close()
    if not args.corpus:
        return summary
    scored = build_report(
        corpus_path=Path(args.corpus),
        database_path=Path(args.artifact_dir) / "evaluation.sqlite",
        output_dir=Path(args.output_dir or args.artifact_dir),
        blind_seed=args.blind_seed,
    )
    return {"summary": summary, **scored}


def command_credentials(_args) -> dict:
    # Report only presence. Never emit values, lengths, prefixes, or suffixes.
    return {provider: {"environment": variable,
                       "available": bool(evaluation_key(os.environ, provider))}
            for provider, variable in EVAL_KEY_ENV.items()}


def command_discover(args) -> dict:
    providers = [value.strip() for value in args.providers.split(",") if value.strip()]
    unknown = sorted(set(providers) - {"anthropic", "openai", "xai"})
    if unknown:
        raise EvaluationError(f"unknown discovery providers: {unknown}")
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for provider in providers:
        key = evaluation_key(os.environ, provider)
        if not key:
            results.append({"provider": provider, "status": "skipped:no_isolated_credential"})
            continue
        try:
            redactor = SecretRedactor([key])
            result = discover_models(provider, api_key=key)
            results.append(redactor.value({"status": "ok", **result}))
        except Exception as exc:  # noqa: BLE001 - capability failures are reportable results
            results.append(SecretRedactor([key]).value({
                "provider": provider, "status": "error",
                "error": f"{type(exc).__name__}: {exc}"[:500],
            }))
    path = artifact_dir / "model-discovery.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return {"artifact": str(path), "results": results}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", default=".model-eval")
    parser.add_argument("--cap-usd", type=float, default=40.0)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("--corpus", required=True)
    validate.set_defaults(func=command_validate)

    freeze = sub.add_parser("freeze")
    freeze.add_argument("--snapshot", required=True)
    freeze.add_argument("--registry", default="eval/model-bakeoff-registry-v1.json")
    freeze.add_argument("--orientation", default="prompts/orientation-brief-v2.md")
    freeze.add_argument("--output", default=".model-eval/calibration-corpus.json")
    freeze.set_defaults(func=command_freeze)

    freeze_prep = sub.add_parser("freeze-prep")
    freeze_prep.add_argument("--snapshot", required=True)
    freeze_prep.add_argument("--intake-source", default="nbn/intake_triage.py")
    freeze_prep.add_argument("--assignment-source", default="nbn/desk_prep.py")
    freeze_prep.add_argument("--output", default=".model-eval/preparation-corpus.json")
    freeze_prep.add_argument("--item-count", type=int, default=300)
    freeze_prep.set_defaults(func=command_freeze_prep)

    freeze_editor = sub.add_parser("freeze-editor")
    freeze_editor.add_argument("--snapshot", required=True)
    freeze_editor.add_argument("--editor-source", default="nbn/editor.py")
    freeze_editor.add_argument("--orientation", default="prompts/orientation-brief-v2.md")
    freeze_editor.add_argument("--output", default=".model-eval/editor-corpus.json")
    freeze_editor.set_defaults(func=command_freeze_editor)

    estimate = sub.add_parser("estimate")
    estimate.add_argument("--corpus", required=True)
    estimate.add_argument("--conditions", required=True)
    estimate.add_argument("--lane")
    estimate.add_argument("--repetitions", type=int, default=1)
    estimate.set_defaults(func=command_estimate)

    probe = sub.add_parser("probe")
    probe.add_argument("--conditions", required=True)
    probe.set_defaults(func=command_probe)

    run = sub.add_parser("run")
    run.add_argument("--corpus", required=True)
    run.add_argument("--conditions", required=True)
    run.add_argument("--lane")
    run.add_argument("--repetitions", type=int, default=1)
    run.add_argument("--seed", default="nbn-model-bakeoff-v1")
    run.set_defaults(func=command_run)

    report = sub.add_parser("report")
    report.add_argument("--corpus")
    report.add_argument("--output-dir")
    report.add_argument("--blind-seed", default="nbn-owner-review-v1")
    report.set_defaults(func=command_report)

    credentials = sub.add_parser("credentials")
    credentials.set_defaults(func=command_credentials)

    discover = sub.add_parser("discover")
    discover.add_argument("--providers", default="anthropic,openai,xai")
    discover.set_defaults(func=command_discover)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        print(json.dumps(args.func(args), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (EvaluationError, OSError, json.JSONDecodeError) as exc:
        print(f"model-bakeoff: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
