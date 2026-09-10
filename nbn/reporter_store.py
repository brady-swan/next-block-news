"""Durable Codex shifts and observable work; no model or provider calls."""
import hashlib
import json
import re
import time
import threading
import uuid

# Pause and the final create request share this fence; slow preparation does not.
dispatch_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS reporter_shifts (
 shift_id TEXT PRIMARY KEY, started_at REAL NOT NULL, cutoff_at REAL NOT NULL,
 status TEXT NOT NULL, generation TEXT NOT NULL, worker_id TEXT NOT NULL,
 lease_until REAL NOT NULL, thread_id TEXT, updated_at REAL NOT NULL,
 agenda_json TEXT NOT NULL DEFAULT '{}', letter TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reporter_records (
 id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT UNIQUE NOT NULL,
 shift_id TEXT NOT NULL, kind TEXT NOT NULL, sender TEXT NOT NULL,
 reply_to TEXT, at REAL NOT NULL, payload_json TEXT NOT NULL,
 delivered_turn TEXT, acknowledged_at REAL
);
CREATE INDEX IF NOT EXISTS reporter_records_shift ON reporter_records(shift_id,id);
CREATE TABLE IF NOT EXISTS reporter_submissions (
 submission_id TEXT PRIMARY KEY, shift_id TEXT NOT NULL, generation TEXT NOT NULL,
 canonical_key TEXT NOT NULL, payload_hash TEXT NOT NULL, payload_json TEXT NOT NULL,
 state TEXT NOT NULL, mutation_id TEXT, provider_ref TEXT, error TEXT,
 created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS reporter_submissions_story ON reporter_submissions(canonical_key,state);
CREATE TABLE IF NOT EXISTS reporter_remote_coverage (
 draft_id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at REAL,
 published_at REAL, synced_at REAL NOT NULL, payload_json TEXT NOT NULL
);
"""


def initialize(con):
    con.executescript(SCHEMA)


def encoded(payload, maximum=128 * 1024):
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(text.encode()) > maximum:
        raise ValueError("reporter payload too large; store a bounded artifact")
    return text


def digest(payload):
    return hashlib.sha256(encoded(payload).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,160}", value):
        raise ValueError("invalid stable identifier")
    return value


def shift(con, shift_id=None):
    row = con.execute("SELECT * FROM reporter_shifts " +
                      ("WHERE shift_id=?" if shift_id else "ORDER BY started_at DESC LIMIT 1"),
                      (shift_id,) if shift_id else ()).fetchone()
    if not row:
        return None
    out = dict(row)
    out["agenda"] = json.loads(out.pop("agenda_json"))
    out["expired"] = time.time() >= out["cutoff_at"]
    out["lease_alive"] = time.time() < out["lease_until"]
    return out


def start(con, *, worker_id, shift_id, now=None):
    """Only the control credential may call this. Retry never resets the cutoff."""
    identifier(worker_id)
    identifier(shift_id)
    stamp = time.time() if now is None else now
    with con:
        con.execute("BEGIN IMMEDIATE")
        old = shift(con, shift_id)
        if old:
            if old["worker_id"] != worker_id:
                raise ValueError("shift belongs to another supervisor")
            return old
        active = con.execute("SELECT shift_id FROM reporter_shifts WHERE status='active' AND cutoff_at>?",
                             (stamp,)).fetchone()
        if active:
            raise ValueError("another reporting shift is still active")
        con.execute("INSERT INTO reporter_shifts(shift_id,started_at,cutoff_at,status,generation,"
                    "worker_id,lease_until,updated_at) VALUES (?,?,?,'active',?,?,?,?)",
                    (shift_id, stamp, stamp + 7200, uuid.uuid4().hex, worker_id, stamp + 90, stamp))
    return shift(con, shift_id)


def assert_active(con, shift_id, generation, *, now=None):
    stamp = time.time() if now is None else now
    row = shift(con, identifier(shift_id))
    if not row or row["status"] != "active" or row["generation"] != generation:
        raise ValueError("reporter shift is paused, stopped or superseded")
    if stamp >= row["cutoff_at"] or stamp >= row["lease_until"]:
        raise ValueError("reporter cutoff or supervisor lease expired")
    return row


def heartbeat(con, *, shift_id, generation, worker_id, thread_id=None, now=None):
    stamp = time.time() if now is None else now
    with con:
        # A restarted supervisor can reclaim its SAME lease, never extend the shift.
        cur = con.execute("UPDATE reporter_shifts SET lease_until=?,updated_at=?,"
            "thread_id=COALESCE(?,thread_id) WHERE shift_id=? AND generation=? AND worker_id=? "
            "AND status='active' AND cutoff_at>?",
            (stamp + 90, stamp, thread_id, shift_id, generation, worker_id, stamp))
    if cur.rowcount != 1:
        raise ValueError("shift cannot be renewed")
    return shift(con, shift_id)


def stop(con, shift_id, *, status="paused"):
    if status not in {"paused", "completed", "failed"}:
        raise ValueError("invalid terminal shift status")
    with dispatch_lock, con:
        con.execute("UPDATE reporter_shifts SET status=?,generation=?,lease_until=0,updated_at=? "
                    "WHERE shift_id=?", (status, uuid.uuid4().hex, time.time(), identifier(shift_id)))
    return shift(con, shift_id)


def record(con, *, shift_id, record_id, kind, sender, payload, reply_to=None):
    identifier(record_id)
    if sender not in {"reporter", "owner", "main_assistant", "system", "typefully_comment"}:
        raise ValueError("invalid authenticated sender")
    text = encoded(payload)
    with con:
        old = con.execute("SELECT * FROM reporter_records WHERE record_id=?", (record_id,)).fetchone()
        if old:
            if (old["shift_id"], old["kind"], old["sender"], old["payload_json"], old["reply_to"]) != (
                    shift_id, kind, sender, text, reply_to):
                raise ValueError("record ID reused with different content")
            return dict(old)
        cur = con.execute("INSERT INTO reporter_records(record_id,shift_id,kind,sender,reply_to,at,payload_json) "
                          "VALUES (?,?,?,?,?,?,?)", (record_id, shift_id, kind, sender, reply_to, time.time(), text))
    return {"id": cur.lastrowid, "record_id": record_id}


def records(con, *, shift_id=None, after=0, kind=None, query="", limit=50):
    terms, values = ["id> ?"], [max(0, int(after))]
    if shift_id:
        terms.append("shift_id=?"); values.append(identifier(shift_id))
    if kind:
        terms.append("kind=?"); values.append(str(kind))
    if query:
        terms.append("lower(payload_json) LIKE ? ESCAPE '\\'")
        values.append("%" + str(query).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")[:200] + "%")
    limit = max(1, min(100, int(limit)))
    rows = [dict(r) for r in con.execute("SELECT * FROM reporter_records WHERE " + " AND ".join(terms) +
                                        " ORDER BY id LIMIT ?", (*values, limit + 1))]
    for row in rows:
        row["payload"] = json.loads(row.pop("payload_json"))
    return {"rows": rows[:limit], "next_after": rows[limit-1]["id"] if len(rows) > limit else None}


def save_handoff(con, *, shift_id, generation, letter, agenda, record_id):
    # Allow the final letter after cutoff, never renew a lease or permit delivery.
    row = shift(con, shift_id)
    if not row or row["generation"] != generation:
        raise ValueError("shift was superseded")
    if not isinstance(letter, str) or not 1 <= len(letter.strip()) <= 16000:
        raise ValueError("write a useful, bounded handoff letter")
    agenda_json = encoded(agenda, 16000)
    result = record(con, shift_id=shift_id, record_id=record_id, kind="handoff", sender="reporter",
                    payload={"letter": letter, "agenda": agenda})
    with con:
        con.execute("UPDATE reporter_shifts SET letter=?,agenda_json=?,updated_at=? WHERE shift_id=?",
                    (letter, agenda_json, time.time(), shift_id))
    return result
