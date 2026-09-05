"""Capture a read-only, detached production slice for the model bake-off.

This command invokes a fixed Python program through Railway SSH. The remote program opens
the production SQLite database in read-only/query-only mode, starts one read transaction,
and emits selected recent rows as JSON. It never imports NBN or inspects environment values.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

REMOTE_PROGRAM = r'''
import hashlib
import json
import sqlite3
import time

cutoff = float(__CUTOFF__)
con = sqlite3.connect("file:/data/nbn.db?mode=ro", uri=True)
con.row_factory = sqlite3.Row
con.execute("PRAGMA query_only=ON")
con.execute("BEGIN")

queries = {
    "newsroom_runs": (
        "SELECT * FROM newsroom_runs WHERE created_at>=? ORDER BY created_at,run_id", (cutoff,)
    ),
    "newsroom_story_commits": (
        "SELECT c.* FROM newsroom_story_commits c JOIN newsroom_runs r ON r.run_id=c.run_id "
        "WHERE r.created_at>=? ORDER BY c.updated_at,c.run_id,c.story_id", (cutoff,)
    ),
    "newsroom_story_memory": (
        "SELECT * FROM newsroom_story_memory WHERE updated_at>=? OR created_at>=? "
        "ORDER BY updated_at,canonical_key", (cutoff, cutoff)
    ),
    "desk_preparations": (
        "SELECT * FROM desk_preparations WHERE prepared_at>=? ORDER BY prepared_at,run_id,item_hash",
        (cutoff,),
    ),
    "source_evidence": (
        "SELECT * FROM source_evidence WHERE observed_at>=? ORDER BY observed_at,id", (cutoff,)
    ),
    "source_resolutions": (
        "SELECT * FROM source_resolutions WHERE resolved_at>=? ORDER BY resolved_at,item_hash",
        (cutoff,),
    ),
    "pipeline_events": (
        "SELECT * FROM pipeline_events WHERE at>=? ORDER BY at,id", (cutoff,)
    ),
    "intake_triage": (
        "SELECT * FROM intake_triage WHERE triaged_at>=? ORDER BY triaged_at,item_hash", (cutoff,)
    ),
    "items": (
        "SELECT * FROM items WHERE first_seen>=? ORDER BY first_seen,url_hash", (cutoff,)
    ),
    "posts": (
        "SELECT * FROM posts WHERE created>=? ORDER BY created,id", (cutoff,)
    ),
    "model_usage": (
        "SELECT * FROM model_usage WHERE created_at>=? ORDER BY created_at,id", (cutoff,)
    ),
}

tables = {}
table_fingerprints = {}
for name, (sql, params) in queries.items():
    rows = [dict(row) for row in con.execute(sql, params)]
    tables[name] = rows
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    table_fingerprints[name] = hashlib.sha256(encoded.encode()).hexdigest()

counts = {
    name: con.execute("SELECT COUNT(*) FROM " + name).fetchone()[0]
    for name in queries
}
captured_at = time.time()
payload = {
    "schema_version": "nbn-eval-source-snapshot-v1",
    "captured_at": captured_at,
    "cutoff": cutoff,
    "production_counts": counts,
    "table_fingerprints": table_fingerprints,
    "tables": tables,
}
encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
payload["snapshot_hash"] = hashlib.sha256(encoded.encode()).hexdigest()
print(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
con.rollback()
'''


def _remote_argument(program: str) -> str:
    # Railway currently reconstructs the remote argv through a shell. Escape Python's
    # syntactic parentheses and quotes so that the one compact -c argument remains intact.
    encoded = program.encode().hex()
    return f'exec\\(bytes.fromhex\\(\\"{encoded}\\"\\)\\)'


def capture(*, output: Path, days: float) -> dict:
    cutoff = time.time() - max(1.0, float(days)) * 86400
    program = REMOTE_PROGRAM.replace("__CUTOFF__", repr(cutoff))
    command = ["railway", "ssh", "--", "python", "-c", _remote_argument(program)]
    completed = subprocess.run(
        command, check=True, capture_output=True, text=True, timeout=180
    )
    payload = json.loads(completed.stdout)
    if payload.get("schema_version") != "nbn-eval-source-snapshot-v1":
        raise RuntimeError("unexpected source snapshot schema")
    claimed = str(payload.pop("snapshot_hash", ""))
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(encoded.encode()).hexdigest()
    if claimed != actual:
        raise RuntimeError("source snapshot hash mismatch")
    payload["snapshot_hash"] = claimed
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return {
        "output": str(output),
        "snapshot_hash": claimed,
        "captured_at": payload["captured_at"],
        "cutoff": payload["cutoff"],
        "rows": {name: len(rows) for name, rows in payload["tables"].items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".model-eval/source-snapshot.json")
    parser.add_argument("--days", type=float, default=10.0)
    args = parser.parse_args()
    print(json.dumps(capture(output=Path(args.output), days=args.days), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
