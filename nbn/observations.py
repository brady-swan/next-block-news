"""Best-effort run observations, never editorial state or provider reasoning.

One row <=384 KiB (the editor's 256 KiB packet fits). A run allows 80 ordinary
records / 1 MiB plus 40 critical handoffs / 2 MiB. Rich payloads expire after 14
days; small headers remain. Savepoints never commit/rollback a caller's work.
"""
from __future__ import annotations

import json
import logging
import re
import time

from . import config

log = logging.getLogger("nbn.observations")
ROW_BYTES = 384 * 1024
CRITICAL = {"writer_input", "writer_result", "editor_input", "editor_recovery_input",
            "editor_result", "editor_applied", "writer_feedback"}
PRIVATE = re.compile(r"(?:owner_token|probe_token|authorization|api_key|password|credential|encrypted|reasoning|thinking|raw_response|provider_response)", re.I)
QUERY_SECRET = re.compile(r"([?&](?:k|key|token|api_key|access_token|auth)=)[^\s&#\"']+", re.I)


def clean(value):
    """Sanitize only caller-selected business payloads, never whole API responses."""
    secrets = [v for k, v in vars(config).items() if isinstance(v, str) and len(v) >= 8
               and any(s in k for s in ("TOKEN", "API_KEY", "PASSWORD", "SECRET"))]
    changed = False

    def walk(v, depth=0):
        nonlocal changed
        if depth > 20:
            changed = True
            return "[depth limit]"
        if isinstance(v, dict):
            result = {}
            for k, x in list(v.items())[:500]:
                if PRIVATE.search(str(k)):
                    changed = True
                    continue
                result[str(k)[:120]] = walk(x, depth + 1)
            changed |= len(v) > 500
            return result
        if isinstance(v, (list, tuple)):
            changed |= len(v) > 500
            return [walk(x, depth + 1) for x in v[:500]]
        if isinstance(v, str):
            result = QUERY_SECRET.sub(r"\1[redacted]", v)
            for secret in secrets:
                result = result.replace(secret, "[redacted]")
            changed |= result != v or len(result) > 300000
            return result[:300000]
        if v is None or isinstance(v, (int, float, bool)):
            return v
        changed = True
        return str(v)[:300]
    return walk(value), changed


def record(con, run_id, kind, payload=None, *, ref="", phase=""):
    """Nonfatal, bounded, transactional recording of an already-existing handoff."""
    if con is None or not run_id:
        return
    opened = False
    try:
        safe, changed = clean(payload if payload is not None else {})
        encoded = json.dumps(safe, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        if len(encoded.encode()) > ROW_BYTES:
            changed = True
            encoded = json.dumps({"unavailable": "observation exceeds per-record bound",
                                  "original_bytes": len(encoded.encode())})
        con.execute("SAVEPOINT nbn_observation")
        opened = True
        slots = ",".join("?" for _ in CRITICAL)
        critical = kind in CRITICAL
        n, size = con.execute(
            f"SELECT COUNT(*),COALESCE(SUM(payload_bytes),0) FROM run_observations WHERE run_id=?"
            f" AND kind {'IN' if critical else 'NOT IN'} ({slots})", [run_id, *sorted(CRITICAL)]).fetchone()
        limit_n, limit_bytes = (40, 2 * 1024 * 1024) if critical else (80, 1024 * 1024)
        if n >= limit_n or size + len(encoded.encode()) > limit_bytes:
            if not con.execute("SELECT 1 FROM run_observations WHERE run_id=? AND kind='trace_limit' AND ref=?",
                               (run_id, "critical" if critical else "activity")).fetchone():
                con.execute("INSERT INTO run_observations(run_id,kind,ref,at,truncated) VALUES (?,'trace_limit',?,?,1)",
                            (run_id, "critical" if critical else "activity", time.time()))
        else:
            con.execute("INSERT INTO run_observations(run_id,kind,ref,phase,at,payload_json,payload_bytes,truncated) VALUES (?,?,?,?,?,?,?,?)",
                        (str(run_id)[:120], str(kind)[:60], str(ref)[:120], str(phase)[:40], time.time(), encoded, len(encoded.encode()), int(changed)))
        con.execute("RELEASE SAVEPOINT nbn_observation")
    except Exception as exc:
        if opened:
            try:
                con.execute("ROLLBACK TO SAVEPOINT nbn_observation")
                con.execute("RELEASE SAVEPOINT nbn_observation")
            except Exception:
                pass
        log.warning("observation not recorded (%s)", type(exc).__name__)


def source_poll(con, key, label, kind, *, count=None, error=""):
    if con is None:
        return
    opened = False
    try:
        con.execute("SAVEPOINT nbn_source_health")
        opened = True
        now = time.time()
        con.execute("INSERT INTO source_poll_health(source_key,label,kind,attempted_at,succeeded_at,outcome,result_count,error_kind) VALUES (?,?,?,?,?,?,?,?)"
                    " ON CONFLICT(source_key) DO UPDATE SET label=excluded.label,kind=excluded.kind,attempted_at=excluded.attempted_at,"
                    "succeeded_at=COALESCE(excluded.succeeded_at,source_poll_health.succeeded_at),outcome=excluded.outcome,result_count=excluded.result_count,error_kind=excluded.error_kind",
                    (key[:160], label[:160], kind[:40], now, None if error else now,
                     "error" if error else "ok", count, str(error)[:80]))
        con.execute("RELEASE SAVEPOINT nbn_source_health")
    except Exception as exc:
        if opened:
            try:
                con.execute("ROLLBACK TO SAVEPOINT nbn_source_health")
                con.execute("RELEASE SAVEPOINT nbn_source_health")
            except Exception:
                pass
        log.warning("source health not recorded (%s)", type(exc).__name__)


def prune(con):
    """Bounded worker maintenance, including abandoned runs; never a GET side effect."""
    try:
        con.execute("SAVEPOINT nbn_observation_prune")
        con.execute("UPDATE run_observations SET payload_json=NULL,payload_bytes=0,expired=1 WHERE id IN"
                    " (SELECT id FROM run_observations WHERE at<? AND expired=0 LIMIT 500)",
                    (time.time() - 14 * 86400,))
        con.execute("RELEASE SAVEPOINT nbn_observation_prune")
    except Exception:
        try:
            con.execute("ROLLBACK TO SAVEPOINT nbn_observation_prune")
            con.execute("RELEASE SAVEPOINT nbn_observation_prune")
        except Exception:
            pass
