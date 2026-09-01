"""SQLite state: seen items, story-level dedup, post log."""
import hashlib
import json
import sqlite3
import time
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import config, source_policy

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS items (
  url_hash TEXT PRIMARY KEY,
  source TEXT, title TEXT, url TEXT, published_at TEXT,
  first_seen REAL, status TEXT DEFAULT 'new',
  -- new|skipped|held|drafted|posted|uncertain|failed|taped|error
  story_key TEXT, note TEXT,
  summary TEXT DEFAULT '',
  discovery_key TEXT,
  discovery_origin TEXT DEFAULT 'legacy',
  discovery_context TEXT DEFAULT '',
  discovery_candidate_id TEXT,
  decision_stage TEXT,
  decision_category TEXT
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created REAL, story_key TEXT, item_hash TEXT, class TEXT,
  body TEXT, receipt_url TEXT, mode TEXT, nuelink_id TEXT,
  editor_note TEXT, resolution_id TEXT,
  confirmed_at REAL, public_url TEXT, publisher_status TEXT,
  publisher_synced_at REAL, publisher_backend TEXT
);
CREATE TABLE IF NOT EXISTS source_resolutions (
  item_hash TEXT PRIMARY KEY,
  story_key TEXT NOT NULL,
  resolved_at REAL NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  original_url TEXT NOT NULL,
  original_source TEXT NOT NULL,
  original_source_id TEXT NOT NULL,
  original_tier TEXT NOT NULL,
  selected_url TEXT NOT NULL,
  selected_source TEXT NOT NULL,
  selected_source_id TEXT NOT NULL,
  selected_tier TEXT NOT NULL,
  selected_category TEXT NOT NULL,
  selected_independence_key TEXT NOT NULL,
  selected_ownership_key TEXT NOT NULL,
  originality TEXT NOT NULL,
  support_verdict INTEGER NOT NULL,
  receipt_eligible INTEGER NOT NULL,
  corroboration_eligible INTEGER NOT NULL,
  primary_artifact_url TEXT,
  primary_artifact_fingerprint TEXT,
  content_fingerprint TEXT,
  selected_text TEXT,
  earliest_coverage_date TEXT,
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_resolutions_story
  ON source_resolutions(story_key, resolved_at);
CREATE TABLE IF NOT EXISTS source_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_hash TEXT NOT NULL,
  story_key TEXT NOT NULL,
  observed_at REAL NOT NULL,
  url TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_name TEXT NOT NULL,
  tier TEXT NOT NULL,
  category TEXT NOT NULL,
  independence_key TEXT NOT NULL,
  ownership_key TEXT NOT NULL,
  originality TEXT NOT NULL,
  support_verdict INTEGER NOT NULL,
  receipt_eligible INTEGER NOT NULL,
  corroboration_eligible INTEGER NOT NULL,
  primary_artifact_fingerprint TEXT,
  content_fingerprint TEXT,
  UNIQUE(item_hash, url)
);
CREATE INDEX IF NOT EXISTS idx_evidence_story
  ON source_evidence(story_key, observed_at);
CREATE TABLE IF NOT EXISTS cycle_leases (
  name TEXT PRIMARY KEY,
  owner TEXT NOT NULL,
  expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS operator_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_hash TEXT NOT NULL,
  story_key TEXT,
  action TEXT NOT NULL,
  gate TEXT,
  requested_at REAL NOT NULL,
  completed_at REAL,
  state TEXT NOT NULL,
  original_status TEXT NOT NULL,
  original_note TEXT,
  result TEXT
);
CREATE INDEX IF NOT EXISTS idx_operator_actions_item
  ON operator_actions(item_hash, id DESC);
CREATE TABLE IF NOT EXISTS node_discovery_runs (
  run_id INTEGER PRIMARY KEY,
  selected_date TEXT NOT NULL,
  status TEXT NOT NULL,
  ingested_at REAL NOT NULL,
  url_count INTEGER NOT NULL,
  invalid_count INTEGER NOT NULL DEFAULT 0,
  context_json TEXT NOT NULL DEFAULT '{}',
  diagnostics_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS research_jobs (
  item_hash TEXT PRIMARY KEY,
  story_key TEXT NOT NULL,
  triage_action TEXT NOT NULL,
  triage_class TEXT NOT NULL,
  triage_reason TEXT,
  stage TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at REAL,
  state TEXT NOT NULL,
  error_kind TEXT,
  error_message TEXT,
  manual_draft_only INTEGER NOT NULL DEFAULT 0,
  context_json TEXT NOT NULL,
  claim_token TEXT,
  claimed_at REAL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_research_jobs_due
  ON research_jobs(state, next_attempt_at);
CREATE TABLE IF NOT EXISTS pipeline_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  item_hash TEXT NOT NULL,
  story_key TEXT,
  event TEXT NOT NULL,
  category TEXT,
  at REAL NOT NULL,
  metadata TEXT,
  UNIQUE(item_hash, event)
);
CREATE INDEX IF NOT EXISTS idx_pipeline_events_at ON pipeline_events(at);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_posts_story ON posts(story_key);
"""

POST_COLUMNS = {
    "editor_note": "TEXT",
    "resolution_id": "TEXT",
    "confirmed_at": "REAL",
    "public_url": "TEXT",
    "publisher_status": "TEXT",
    "publisher_synced_at": "REAL",
    "publisher_backend": "TEXT",
}

ITEM_COLUMNS = {
    "summary": "TEXT DEFAULT ''",
    "discovery_key": "TEXT",
    "discovery_origin": "TEXT DEFAULT 'legacy'",
    "discovery_context": "TEXT DEFAULT ''",
    "discovery_candidate_id": "TEXT",
    "decision_stage": "TEXT",
    "decision_category": "TEXT",
}

NODE_RUN_COLUMNS = {
    "context_json": "TEXT NOT NULL DEFAULT '{}'",
    "diagnostics_json": "TEXT NOT NULL DEFAULT '{}'",
}


def _ensure_post_columns(con):
    """Apply additive post migrations without masking unexpected SQLite failures."""
    existing = {r["name"] for r in con.execute("PRAGMA table_info(posts)").fetchall()}
    for name, declaration in POST_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE posts ADD COLUMN {name} {declaration}")
    con.execute(
        "CREATE INDEX IF NOT EXISTS idx_posts_publisher_ref"
        " ON posts(publisher_backend, nuelink_id)"
    )
    con.commit()


def _ensure_item_columns(con):
    """Apply additive item migrations and backfill stable discovery identity."""
    existing = {r["name"] for r in con.execute("PRAGMA table_info(items)").fetchall()}
    for name, declaration in ITEM_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE items ADD COLUMN {name} {declaration}")
    rows = con.execute(
        "SELECT url_hash,url FROM items WHERE discovery_key IS NULL OR discovery_key=''"
    ).fetchall()
    for row in rows:
        con.execute(
            "UPDATE items SET discovery_key=?,discovery_origin=COALESCE(NULLIF(discovery_origin,''),'legacy')"
            " WHERE url_hash=?",
            (canonical_discovery_key(row["url"]), row["url_hash"]),
        )
    con.execute("CREATE INDEX IF NOT EXISTS idx_items_discovery_key ON items(discovery_key)")
    con.commit()


def _ensure_node_run_columns(con):
    existing = {
        r["name"] for r in con.execute("PRAGMA table_info(node_discovery_runs)").fetchall()
    }
    for name, declaration in NODE_RUN_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE node_discovery_runs ADD COLUMN {name} {declaration}")
    con.commit()


def kv_get(con, k: str) -> str:
    row = con.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return row["v"] if row else ""


def kv_set(con, k: str, v: str):
    con.execute("INSERT INTO kv(k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    con.commit()


def hold_gate(note: str) -> str:
    """Return the operator-facing gate for holds that can safely become a draft.

    Source and thin-source holds are intentionally excluded: they do not have enough
    reliable material to send through the Writer/Editor stack.
    """
    value = str(note or "").lower()
    if value.startswith("stale event:"):
        return "freshness"
    if value.startswith("needs second source"):
        return "corroboration"
    if value.startswith("editor spiked"):
        return "editor"
    if value.startswith("lint:"):
        return "style"
    return ""


def request_operator_action(con, item_hash: str, action: str) -> dict:
    """Apply a Desk disposition or queue one guarded, draft-only pipeline retry."""
    if action not in ("stage", "retry", "dismiss"):
        return {"ok": False, "reason": "unknown action"}
    try:
        con.execute("BEGIN IMMEDIATE")
        item = con.execute(
            "SELECT status,story_key,note FROM items WHERE url_hash=?", (item_hash,)
        ).fetchone()
        if not item:
            con.rollback()
            return {"ok": False, "reason": "item not found"}
        if item["status"] != "held":
            con.rollback()
            return {"ok": False, "reason": f"item is {item['status']}, not held"}
        gate = hold_gate(item["note"])
        if action == "stage" and not gate:
            con.rollback()
            return {"ok": False, "reason": "this hold needs more source material"}
        research = con.execute(
            "SELECT state,error_kind FROM research_jobs WHERE item_hash=?", (item_hash,)
        ).fetchone()
        if action == "retry" and (not research or research["state"] not in {"pending", "exhausted"}):
            con.rollback()
            return {"ok": False, "reason": "no retryable infrastructure research job"}
        now = time.time()
        state = "queued" if action in {"stage", "retry"} else "completed"
        cur = con.execute(
            "INSERT INTO operator_actions(item_hash,story_key,action,gate,requested_at,"
            "completed_at,state,original_status,original_note,result)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)",
            (item_hash, item["story_key"], action,
             ("research" if action == "retry" else gate or None), now,
             None if action in {"stage", "retry"} else now, state,
             item["status"], item["note"],
             None if action in {"stage", "retry"} else "owner dismissed"),
        )
        if action == "stage":
            con.execute("UPDATE items SET status='new' WHERE url_hash=?", (item_hash,))
        elif action == "retry":
            con.execute(
                "UPDATE research_jobs SET state='pending',next_attempt_at=?,manual_draft_only=1,"
                "claim_token=NULL,claimed_at=NULL,updated_at=? WHERE item_hash=?",
                (now, now, item_hash),
            )
        else:
            note = "owner dismissed"
            if item["note"]:
                note += f" · was: {item['note']}"
            con.execute(
                "UPDATE items SET status='skipped',note=? WHERE url_hash=?", (note[:300], item_hash)
            )
            con.execute(
                "UPDATE research_jobs SET state='dismissed',next_attempt_at=NULL,claim_token=NULL,"
                "claimed_at=NULL,updated_at=? WHERE item_hash=?", (now, item_hash)
            )
        con.commit()
        return {"ok": True, "id": cur.lastrowid, "state": state, "gate": gate}
    except Exception:
        con.rollback()
        raise


def pending_stage_action(con, item_hash: str):
    return con.execute(
        "SELECT * FROM operator_actions WHERE item_hash=? AND action='stage'"
        " AND state IN ('queued','processing') ORDER BY id DESC LIMIT 1", (item_hash,)
    ).fetchone()


def pending_retry_action(con, item_hash: str):
    return con.execute(
        "SELECT * FROM operator_actions WHERE item_hash=? AND action='retry'"
        " AND state IN ('queued','processing') ORDER BY id DESC LIMIT 1", (item_hash,)
    ).fetchone()


def latest_operator_action(con, item_hash: str):
    return con.execute(
        "SELECT * FROM operator_actions WHERE item_hash=? ORDER BY id DESC LIMIT 1", (item_hash,)
    ).fetchone()


def start_operator_action(con, action_id: int) -> None:
    con.execute(
        "UPDATE operator_actions SET state='processing' WHERE id=? AND state='queued'",
        (action_id,),
    )
    con.commit()


def finish_operator_action(con, action_id: int, state: str, result: str) -> None:
    if state not in ("completed", "blocked"):
        raise ValueError("invalid operator action state")
    con.execute(
        "UPDATE operator_actions SET state=?,completed_at=?,result=? WHERE id=?",
        (state, time.time(), str(result or "")[:300], action_id),
    )
    con.commit()


def record_decision_run(con, pending: list, verdicts: list, result: dict,
                        started_at: float) -> None:
    """Keep the last completed, non-empty intake decision run for Desk inspection."""
    if not pending:
        return
    by_hash = {row.get("url_hash"): row for row in verdicts}
    decisions = []
    for candidate in pending:
        item_hash = candidate["url_hash"]
        verdict = by_hash.get(item_hash, {})
        final = con.execute(
            "SELECT status, story_key, note FROM items WHERE url_hash=?", (item_hash,)
        ).fetchone()
        resolution = con.execute(
            "SELECT original_source, original_tier, selected_source, selected_tier,"
            " selected_url, status FROM source_resolutions WHERE item_hash=?", (item_hash,)
        ).fetchone()
        output = con.execute(
            "SELECT mode FROM posts WHERE item_hash=? ORDER BY id DESC LIMIT 1", (item_hash,)
        ).fetchone()
        decisions.append({
            "url_hash": item_hash,
            "source": str(candidate.get("source") or "")[:120],
            "title": str(candidate.get("title") or "")[:300],
            "url": str(candidate.get("url") or "")[:1000],
            "published": str(candidate.get("published") or "")[:100],
            "discovery_origin": str(candidate.get("discovery_origin") or "legacy")[:40],
            "triage_action": str(verdict.get("action") or "")[:40],
            "triage_reason": str(verdict.get("reason") or "")[:400],
            "story_key": (final["story_key"] if final else None) or verdict.get("story_key"),
            "final_status": final["status"] if final else "unknown",
            "final_note": (final["note"] if final else "") or "",
            "original_source": resolution["original_source"] if resolution else "",
            "original_tier": resolution["original_tier"] if resolution else "",
            "selected_source": resolution["selected_source"] if resolution else "",
            "selected_tier": resolution["selected_tier"] if resolution else "",
            "selected_url": resolution["selected_url"] if resolution else "",
            "resolution_status": resolution["status"] if resolution else "",
            "output_mode": output["mode"] if output else "",
        })
    payload = {
        "started": started_at,
        "completed": time.time(),
        "result": dict(result),
        "items": decisions,
    }
    kv_set(con, "desk:last_decision_run", json.dumps(payload, separators=(",", ":")))


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:24]


_TRACKING_QUERY_KEYS = {
    "fbclid", "gclid", "dclid", "msclkid", "mc_cid", "mc_eid", "igshid",
}


def canonical_discovery_key(value: str) -> str:
    """Stable URL identity for cross-feed discovery dedupe."""
    raw = str(value or "").strip()
    try:
        parts = urlsplit(raw)
        scheme = parts.scheme.lower()
        if scheme not in {"http", "https"} or not parts.hostname:
            return raw
        host = parts.hostname.rstrip(".").lower()
        try:
            port = parts.port
        except ValueError:
            return raw
        netloc = f"[{host}]" if ":" in host else host
        if port is not None and not ((scheme == "http" and port == 80)
                                    or (scheme == "https" and port == 443)):
            netloc = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
        query = []
        for key, val in parse_qsl(parts.query, keep_blank_values=True):
            lowered = key.lower()
            if lowered.startswith("utm_") or lowered in _TRACKING_QUERY_KEYS:
                continue
            query.append((key, val))
        query.sort(key=lambda pair: (pair[0], pair[1]))
        return urlunsplit((scheme, netloc, parts.path or "/",
                           urlencode(query, doseq=True), ""))
    except (TypeError, ValueError):
        return raw


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _ensure_post_columns(con)
    _ensure_item_columns(con)
    _ensure_node_run_columns(con)
    return con


def upsert_new_items(con, items) -> list:
    """Insert unseen items; return the newly inserted subset."""
    fresh = []
    for it in items:
        key = canonical_discovery_key(it["url"])
        existing = con.execute(
            "SELECT url_hash FROM items WHERE discovery_key=? ORDER BY first_seen LIMIT 1",
            (key,),
        ).fetchone()
        if existing:
            continue
        h = url_hash(key or it["url"])
        origin = str(it.get("discovery_origin") or "legacy")[:40]
        context = str(it.get("discovery_context") or "")[:8192]
        candidate_id = str(it.get("discovery_candidate_id") or "")[:32] or None
        cur = con.execute(
            "INSERT OR IGNORE INTO items(url_hash,source,title,url,published_at,first_seen,"
            "summary,discovery_key,discovery_origin,discovery_context,discovery_candidate_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (h, it["source"], it["title"], it["url"], it.get("published", ""),
             time.time(), str(it.get("summary") or "")[:600], key, origin, context,
             candidate_id),
        )
        if cur.rowcount:
            fresh.append({**it, "url_hash": h})
    con.commit()
    return fresh


def node_run_consumed(con, run_id: int) -> bool:
    return con.execute(
        "SELECT 1 FROM node_discovery_runs WHERE run_id=?", (run_id,)
    ).fetchone() is not None


def ingest_node_discovery_run(con, *, run_id: int, selected_date: str, status: str,
                              context: dict, diagnostics: dict, items: list[dict]) -> dict:
    """Atomically persist a valid Node run and all of its Node-first candidates."""
    context_json = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    if len(context_json.encode("utf-8")) > 16384:
        context_json = json.dumps({"context_omitted": "size"}, separators=(",", ":"))
    diagnostic = dict(diagnostics)
    inserted = deduped = context_attached = 0
    fresh = []
    try:
        con.execute("BEGIN IMMEDIATE")
        if con.execute("SELECT 1 FROM node_discovery_runs WHERE run_id=?", (run_id,)).fetchone():
            con.rollback()
            return {"consumed": True, "inserted": 0, "deduped": 0, "items": []}
        for it in items:
            key = canonical_discovery_key(it["url"])
            existing = con.execute(
                "SELECT url_hash,status FROM items WHERE discovery_key=? ORDER BY first_seen LIMIT 1",
                (key,),
            ).fetchone()
            if existing:
                deduped += 1
                context_value = str(it.get("discovery_context") or "")[:8192]
                if (existing["status"] == "new"
                        and '"schema_version":"wire-pulse-v2"' in context_value):
                    con.execute(
                        "UPDATE items SET discovery_context=?,discovery_candidate_id=?"
                        " WHERE url_hash=? AND status='new'",
                        (context_value,
                         str(it.get("discovery_candidate_id") or "")[:32] or None,
                         existing["url_hash"]),
                    )
                    context_attached += 1
                continue
            h = url_hash(key or it["url"])
            cur = con.execute(
                "INSERT OR IGNORE INTO items(url_hash,source,title,url,published_at,first_seen,"
                "summary,discovery_key,discovery_origin,discovery_context,discovery_candidate_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (h, it["source"], it["title"], it["url"], it.get("published", ""),
                 time.time(), "", key, "marketing_node",
                 str(it.get("discovery_context") or "")[:8192],
                 str(it.get("discovery_candidate_id") or "")[:32] or None),
            )
            if cur.rowcount:
                inserted += 1
                fresh.append({**it, "url_hash": h})
            else:
                deduped += 1
        diagnostic.update({
            "inserted": inserted, "deduped": deduped,
            "context_attached": context_attached,
        })
        diagnostics_json = json.dumps(
            diagnostic, separators=(",", ":"), ensure_ascii=False
        )
        if len(diagnostics_json.encode("utf-8")) > 4096:
            diagnostics_json = json.dumps({"diagnostics_omitted": "size"}, separators=(",", ":"))
        con.execute(
            "INSERT INTO node_discovery_runs(run_id,selected_date,status,ingested_at,"
            "url_count,invalid_count,context_json,diagnostics_json) VALUES (?,?,?,?,?,?,?,?)",
            (run_id, selected_date, status, time.time(), len(items),
             int(diagnostic.get("invalid_refs", 0)) + int(diagnostic.get("nbn_rejected", 0)),
             context_json, diagnostics_json),
        )
        con.commit()
        return {"consumed": False, "inserted": inserted, "deduped": deduped,
                "context_attached": context_attached,
                "items": fresh, "diagnostics": diagnostic}
    except Exception:
        con.rollback()
        raise


def record_pipeline_event(con, run_id: str, item_hash: str, event: str,
                          story_key: str = None, category: str = None,
                          metadata: dict = None) -> None:
    con.execute(
        "INSERT OR IGNORE INTO pipeline_events(run_id,item_hash,story_key,event,category,at,metadata)"
        " VALUES (?,?,?,?,?,?,?)",
        (run_id, item_hash, story_key, event, category, time.time(),
         json.dumps(metadata or {}, separators=(",", ":"))[:2000]),
    )
    con.commit()


def start_research_job(con, item: dict, run_id: str) -> dict:
    """Freeze and claim an actionable decision before its first external request."""
    now = time.time()
    context = {
        key: item.get(key) for key in (
            "url_hash", "source", "title", "url", "published", "summary", "story_key",
            "action", "class", "reason", "discovery_origin", "discovery_context",
            "discovery_candidate_id",
        )
    }
    encoded = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 32768:
        context["discovery_context"] = str(context.get("discovery_context") or "")[:4096]
        encoded = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 32768:
        context["discovery_context"] = ""
        context["summary"] = str(context.get("summary") or "")[:200]
        encoded = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    token = f"{run_id}:{item['url_hash']}:{int(now)}"
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT * FROM research_jobs WHERE item_hash=?", (item["url_hash"],)
        ).fetchone()
        if row and row["state"] in {"processing", "pending", "exhausted"}:
            con.rollback()
            return dict(row)
        con.execute(
            "INSERT INTO research_jobs(item_hash,story_key,triage_action,triage_class,"
            "triage_reason,stage,attempts,next_attempt_at,state,error_kind,error_message,"
            "manual_draft_only,context_json,claim_token,claimed_at,created_at,updated_at)"
            " VALUES (?,?,?,?,?,'source_fetch',1,NULL,'processing',NULL,NULL,0,?,?,?,?,?)"
            " ON CONFLICT(item_hash) DO UPDATE SET story_key=excluded.story_key,"
            "triage_action=excluded.triage_action,triage_class=excluded.triage_class,"
            "triage_reason=excluded.triage_reason,stage='source_fetch',attempts=1,"
            "next_attempt_at=NULL,state='processing',error_kind=NULL,error_message=NULL,"
            "manual_draft_only=0,context_json=excluded.context_json,"
            "claim_token=excluded.claim_token,claimed_at=excluded.claimed_at,"
            "updated_at=excluded.updated_at",
            (item["url_hash"], item.get("story_key") or "", item.get("action") or "draft",
             item.get("class") or "secondary", str(item.get("reason") or "")[:300],
             encoded, token, now, now, now),
        )
        con.execute(
            "UPDATE items SET status='researching',decision_stage='source_fetch',"
            "decision_category='infrastructure' WHERE url_hash=?", (item["url_hash"],)
        )
        con.commit()
        return dict(con.execute(
            "SELECT * FROM research_jobs WHERE item_hash=?", (item["url_hash"],)
        ).fetchone())
    except Exception:
        con.rollback()
        raise


def update_research_stage(con, item_hash: str, stage: str) -> None:
    con.execute(
        "UPDATE research_jobs SET stage=?,updated_at=? WHERE item_hash=? AND state='processing'",
        (stage, time.time(), item_hash),
    )
    con.commit()


def finish_research_job(con, item_hash: str) -> None:
    con.execute(
        "UPDATE research_jobs SET state='completed',claim_token=NULL,claimed_at=NULL,updated_at=?"
        " WHERE item_hash=?", (time.time(), item_hash)
    )
    con.commit()


def defer_research_job(con, item_hash: str, stage: str, error_kind: str,
                       message: str, delay_seconds: int = 300,
                       consume_attempt: bool = True) -> None:
    now = time.time()
    row = con.execute(
        "SELECT attempts,manual_draft_only FROM research_jobs WHERE item_hash=?", (item_hash,)
    ).fetchone()
    if row and not consume_attempt and row["attempts"] > 0:
        con.execute(
            "UPDATE research_jobs SET attempts=attempts-1 WHERE item_hash=?", (item_hash,)
        )
    effective_attempts = max(0, int(row["attempts"]) - (0 if consume_attempt else 1)) if row else 0
    exhausted = bool(row and (effective_attempts >= 2 or row["manual_draft_only"]))
    state = "exhausted" if exhausted else "pending"
    next_at = None if exhausted else now + max(1, delay_seconds)
    con.execute(
        "UPDATE research_jobs SET stage=?,state=?,next_attempt_at=?,error_kind=?,"
        "error_message=?,claim_token=NULL,claimed_at=NULL,updated_at=? WHERE item_hash=?",
        (stage, state, next_at, error_kind[:80], message[:300], now, item_hash),
    )
    con.execute(
        "UPDATE items SET status='held',note=?,decision_stage=?,decision_category='infrastructure'"
        " WHERE url_hash=?", (f"research {state}: {message}"[:300], stage, item_hash)
    )
    con.commit()


def claim_due_research_jobs(con, limit: int = 2, lease_ttl: int = 900,
                            now: float = None) -> list[dict]:
    current = time.time() if now is None else now
    try:
        con.execute("BEGIN IMMEDIATE")
        stale = con.execute(
            "SELECT item_hash,attempts,manual_draft_only FROM research_jobs"
            " WHERE state='processing' AND claimed_at<?", (current - lease_ttl,)
        ).fetchall()
        for row in stale:
            state = "exhausted" if row["attempts"] >= 2 or row["manual_draft_only"] else "pending"
            con.execute(
                "UPDATE research_jobs SET state=?,next_attempt_at=?,claim_token=NULL,claimed_at=NULL,"
                "updated_at=? WHERE item_hash=?",
                (state, current if state == "pending" else None, current, row["item_hash"]),
            )
        rows = con.execute(
            "SELECT * FROM research_jobs WHERE state='pending' AND next_attempt_at<=?"
            " ORDER BY next_attempt_at,item_hash LIMIT ?", (current, limit)
        ).fetchall()
        claimed = []
        for row in rows:
            token = f"retry:{row['item_hash']}:{int(current)}"
            con.execute(
                "UPDATE research_jobs SET state='processing',attempts=attempts+1,claim_token=?,"
                "claimed_at=?,updated_at=? WHERE item_hash=? AND state='pending'",
                (token, current, current, row["item_hash"]),
            )
            con.execute(
                "UPDATE items SET status='researching' WHERE url_hash=?", (row["item_hash"],)
            )
            claimed.append(dict(con.execute(
                "SELECT * FROM research_jobs WHERE item_hash=?", (row["item_hash"],)
            ).fetchone()))
        con.commit()
        return claimed
    except Exception:
        con.rollback()
        raise


def current_max_age_hours(now=None) -> float:
    """Freshness window tracks the news metabolism (Brady 2026-08-30): 2.5h during the
    weekday active cycle (7am-7pm ET), 6h overnight and on weekends. A fixed
    NBN_MAX_AGE_HOURS overrides the schedule entirely if set."""
    import datetime
    import os
    fixed = os.environ.get("NBN_MAX_AGE_HOURS")
    if fixed:
        return float(fixed)
    active = float(os.environ.get("NBN_MAX_AGE_HOURS_ACTIVE", "2.5"))
    quiet = float(os.environ.get("NBN_MAX_AGE_HOURS_QUIET", "6"))
    try:
        from zoneinfo import ZoneInfo
        now_et = (now.astimezone(ZoneInfo("America/New_York")) if now is not None
                  else datetime.datetime.now(ZoneInfo("America/New_York")))
    except Exception:  # noqa: BLE001 - missing tzdata must not kill intake
        return quiet
    if now_et.weekday() < 5 and 7 <= now_et.hour < 19:
        return active
    return quiet


def is_stale(published: str, max_age_hours: float = None, now=None) -> bool:
    """Deterministic freshness gate: a wire never posts old news as NEW.

    Unparseable dates pass through (triage judges them); parsed-and-old is skipped.
    """
    import datetime
    import email.utils
    if max_age_hours is None:
        max_age_hours = current_max_age_hours()
    if not published:
        return False
    dt = None
    try:
        dt = email.utils.parsedate_to_datetime(published)
    except (TypeError, ValueError):
        try:
            dt = datetime.datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    current = now or datetime.datetime.now(datetime.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=datetime.timezone.utc)
    age = current.astimezone(datetime.timezone.utc) - dt
    return age.total_seconds() > max_age_hours * 3600


def is_non_english(title: str) -> bool:
    """Deterministic language gate: the wire publishes in English; non-Latin-script
    items (Korean TokenPost via Perception, etc.) burn draft calls and fail JSON
    parsing. >30% of letters outside Latin ranges = skip at intake."""
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return False
    non_latin = sum(1 for c in letters if ord(c) > 0x024F)
    return non_latin / len(letters) > 0.3


def event_is_stale(date_str, max_hours: float, now=None) -> bool:
    """True when a model-extracted event/coverage date (YYYY-MM-DD) is older than the
    event window. Unparseable/null passes (the article-date gate already ran)."""
    import datetime
    if not date_str:
        return False
    try:
        d = datetime.date.fromisoformat(str(date_str)[:10])
    except ValueError:
        return False
    current = now or datetime.datetime.now(datetime.timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=datetime.timezone.utc)
    age = (current.astimezone(datetime.timezone.utc)
           - datetime.datetime(d.year, d.month, d.day, tzinfo=datetime.timezone.utc))
    # Date-only precision: measure from end of the event's day so a same-day or
    # yesterday event is never falsely stale.
    return age.total_seconds() - 86400 > max_hours * 3600


def pending_items(con, limit: int) -> list:
    """Items awaiting triage — includes anything stranded by a crash mid-cycle."""
    rows = con.execute(
        "SELECT url_hash, source, title, url, published_at AS published,"
        " summary,discovery_origin,discovery_context,discovery_candidate_id"
        " FROM items WHERE status='new' ORDER BY first_seen LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def effective_post_ts_sql(alias: str = "") -> str:
    """SQL expression for when a post became reader-visible (or might have)."""
    prefix = f"{alias}." if alias else ""
    return (f"CASE WHEN {prefix}mode='IMMEDIATE'"
            f" THEN COALESCE({prefix}confirmed_at,{prefix}created)"
            f" ELSE {prefix}created END")


def recent_story_keys(con, days: float = 3.0) -> list:
    """Story keys readers saw or may have seen (authorizes UPDATE handling)."""
    effective = effective_post_ts_sql()
    rows = con.execute(
        f"SELECT story_key, MAX({effective}) effective_at FROM posts"
        " WHERE mode IN ('IMMEDIATE','UNCERTAIN') GROUP BY story_key"
        f" HAVING MAX({effective}) > ? ORDER BY effective_at DESC LIMIT 100",
        (time.time() - days * 86400,),
    ).fetchall()
    return [r["story_key"] for r in rows if r["story_key"]]


def open_story_keys(con, days: float = 2.0) -> list:
    """Keys of stories seen but NOT posted (held/drafted/tracked). Triage must REUSE
    these for new items about the same event — key identity is what makes a second
    outlet's arrival trip the corroboration promotion."""
    rows = con.execute(
        "SELECT DISTINCT story_key FROM items WHERE story_key IS NOT NULL"
        " AND first_seen > ? LIMIT 150", (time.time() - days * 86400,),
    ).fetchall()
    posted = set(recent_story_keys(con, days))
    return [r["story_key"] for r in rows if r["story_key"] and r["story_key"] not in posted]


def wire_items_since(con, since_ts: float) -> list:
    """Stories the wire itself drafted/posted since a timestamp (for Block enrichment)."""
    rows = con.execute(
        "SELECT source, title, url, story_key, status FROM items"
        " WHERE status IN ('posted','drafted') AND first_seen > ? ORDER BY first_seen",
        (since_ts,),
    ).fetchall()
    return [dict(r) for r in rows]


def last_briefing_ts(con) -> float:
    row = con.execute(
        "SELECT MAX(created) t FROM posts WHERE class='briefing'"
    ).fetchone()
    return row["t"] or 0.0


def persist_resolution(con, result, mode: str):
    """Persist one immutable resolver result and its eligible evidence candidates."""
    now = time.time()
    original, selected = result.original, result.selected
    con.execute("SAVEPOINT persist_resolution")
    try:
        con.execute(
            "INSERT INTO source_resolutions("
        " item_hash, story_key, resolved_at, mode, status, original_url, original_source,"
        " original_source_id, original_tier, selected_url, selected_source,"
        " selected_source_id, selected_tier, selected_category,"
        " selected_independence_key, selected_ownership_key, originality,"
        " support_verdict, receipt_eligible, corroboration_eligible,"
        " primary_artifact_url, primary_artifact_fingerprint, content_fingerprint,"
        " selected_text, earliest_coverage_date, note)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(item_hash) DO UPDATE SET"
        " story_key=excluded.story_key, resolved_at=excluded.resolved_at, mode=excluded.mode,"
        " status=excluded.status, original_url=excluded.original_url,"
        " original_source=excluded.original_source, original_source_id=excluded.original_source_id,"
        " original_tier=excluded.original_tier, selected_url=excluded.selected_url,"
        " selected_source=excluded.selected_source, selected_source_id=excluded.selected_source_id,"
        " selected_tier=excluded.selected_tier, selected_category=excluded.selected_category,"
        " selected_independence_key=excluded.selected_independence_key,"
        " selected_ownership_key=excluded.selected_ownership_key, originality=excluded.originality,"
        " support_verdict=excluded.support_verdict, receipt_eligible=excluded.receipt_eligible,"
        " corroboration_eligible=excluded.corroboration_eligible,"
        " primary_artifact_url=excluded.primary_artifact_url,"
        " primary_artifact_fingerprint=excluded.primary_artifact_fingerprint,"
        " content_fingerprint=excluded.content_fingerprint, selected_text=excluded.selected_text,"
        " earliest_coverage_date=excluded.earliest_coverage_date, note=excluded.note",
            (result.item_hash, result.story_key, now, mode, result.status,
             original.url, result.original_source_name, original.source_id, original.tier,
             selected.url, selected.display_name, selected.source_id, selected.tier,
             selected.category, selected.independence_key, selected.ownership_key,
             result.originality, int(result.supported), int(result.receipt_eligible),
             int(result.corroboration_eligible), result.primary_artifact_url,
             result.primary_artifact_fingerprint, result.content_fingerprint,
             result.selected_text, result.earliest_coverage_date, result.note),
        )
        con.execute("DELETE FROM source_evidence WHERE item_hash=?", (result.item_hash,))
        for ev in result.evidence:
            con.execute(
                "INSERT INTO source_evidence("
                " item_hash, story_key, observed_at, url, source_id, source_name, tier, category,"
                " independence_key, ownership_key, originality, support_verdict, receipt_eligible,"
                " corroboration_eligible, primary_artifact_fingerprint, content_fingerprint)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (result.item_hash, result.story_key, now, ev.ref.url, ev.ref.source_id,
                 ev.ref.display_name, ev.ref.tier, ev.ref.category, ev.ref.independence_key,
                 ev.ref.ownership_key, ev.originality, int(ev.supported),
                 int(ev.receipt_eligible), int(ev.corroboration_eligible),
                 ev.primary_artifact_fingerprint, ev.content_fingerprint),
            )
        con.execute("RELEASE SAVEPOINT persist_resolution")
    except Exception:
        con.execute("ROLLBACK TO SAVEPOINT persist_resolution")
        con.execute("RELEASE SAVEPOINT persist_resolution")
        raise


def resolution_for_item(con, item_hash: str):
    return con.execute(
        "SELECT * FROM source_resolutions WHERE item_hash=?", (item_hash,)
    ).fetchone()


def evidence_for_item(con, item_hash: str) -> list:
    return con.execute(
        "SELECT * FROM source_evidence WHERE item_hash=? ORDER BY id", (item_hash,)
    ).fetchall()


def move_resolution_story_key(con, item_hash: str, story_key: str) -> None:
    """Move an existing resolution and all its evidence to one corrected exact key."""
    if not item_hash or not story_key:
        return
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "UPDATE source_resolutions SET story_key=? WHERE item_hash=?",
            (story_key, item_hash),
        )
        con.execute(
            "UPDATE source_evidence SET story_key=? WHERE item_hash=?",
            (story_key, item_hash),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise


def qualified_evidence(con, story_key: str, lookback_hours: float = 24.0) -> list:
    """Fresh, independent evidence chains for an exact story key.

    Same-owner publications, syndication copies, and evidence resolving to the same
    primary artifact or normalized content collapse to one chain.
    """
    if not story_key:
        return []
    rows = con.execute(
        "SELECT * FROM source_evidence WHERE story_key=? AND observed_at>=?"
        " AND support_verdict=1 AND corroboration_eligible=1"
        " ORDER BY observed_at, id",
        (story_key, time.time() - lookback_hours * 3600),
    ).fetchall()
    accepted, owners, artifacts, contents = [], set(), set(), set()
    for row in rows:
        owner = row["ownership_key"] or row["independence_key"]
        artifact = row["primary_artifact_fingerprint"] or ""
        content = row["content_fingerprint"] or ""
        near_copy = content and any(
            source_policy.content_fingerprints_match(content, prior) for prior in contents
        )
        if owner in owners or (artifact and artifact in artifacts) or near_copy:
            continue
        accepted.append(row)
        owners.add(owner)
        if artifact:
            artifacts.add(artifact)
        if content:
            contents.add(content)
    return accepted


def qualified_evidence_count(con, story_key: str, lookback_hours: float = 24.0) -> int:
    return len(qualified_evidence(con, story_key, lookback_hours))


def acquire_cycle_lease(con, owner: str, name: str = "worker", ttl_seconds: int = 900,
                        now: float = None) -> bool:
    """Acquire the cross-process cycle lease atomically; expired owners are recoverable."""
    current = time.time() if now is None else now
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT owner, expires_at FROM cycle_leases WHERE name=?", (name,)).fetchone()
        if row and row["owner"] != owner and row["expires_at"] > current:
            con.rollback()
            return False
        con.execute(
            "INSERT INTO cycle_leases(name, owner, expires_at) VALUES (?,?,?)"
            " ON CONFLICT(name) DO UPDATE SET owner=excluded.owner, expires_at=excluded.expires_at",
            (name, owner, current + ttl_seconds),
        )
        con.commit()
        return True
    except Exception:
        con.rollback()
        raise


def renew_cycle_lease(con, owner: str, name: str = "worker", ttl_seconds: int = 900,
                      now: float = None) -> bool:
    current = time.time() if now is None else now
    cur = con.execute(
        "UPDATE cycle_leases SET expires_at=? WHERE name=? AND owner=?",
        (current + ttl_seconds, name, owner),
    )
    con.commit()
    return bool(cur.rowcount)


def release_cycle_lease(con, owner: str, name: str = "worker") -> bool:
    cur = con.execute("DELETE FROM cycle_leases WHERE name=? AND owner=?", (name, owner))
    con.commit()
    return bool(cur.rowcount)


def story_reader_covered(con, story_key: str) -> bool:
    """True only when readers saw, or may have seen, this exact story."""
    if not story_key:
        return False
    return con.execute(
        "SELECT 1 FROM posts WHERE story_key=? AND mode IN ('IMMEDIATE','UNCERTAIN') LIMIT 1",
        (story_key,),
    ).fetchone() is not None


def story_handled(con, story_key: str) -> bool:
    """True when an exact story is already published, uncertain, or queued as a draft."""
    if not story_key:
        return False
    return con.execute(
        "SELECT 1 FROM posts WHERE story_key=?"
        " AND mode IN ('IMMEDIATE','DRAFT','UNCERTAIN') LIMIT 1", (story_key,)
    ).fetchone() is not None


def story_produced(con, story_key: str) -> bool:
    """True for any recorded output; used for one-shot jobs such as briefing windows."""
    if not story_key:
        return False
    return con.execute(
        "SELECT 1 FROM posts WHERE story_key=? LIMIT 1", (story_key,)
    ).fetchone() is not None


def set_status(con, url_hash_: str, status: str, story_key: str = None, note: str = None,
               stage: str = None, category: str = None):
    con.execute(
        "UPDATE items SET status=?,story_key=COALESCE(?,story_key),note=COALESCE(?,note),"
        "decision_stage=COALESCE(?,decision_stage),decision_category=COALESCE(?,decision_category)"
        " WHERE url_hash=?",
        (status, story_key, note, stage, category, url_hash_),
    )
    con.commit()


def log_post(con, story_key, item_hash, klass, body, receipt_url, mode, publisher_ref=None,
             editor_note=None, resolution_id=None, publisher_backend=None):
    """Record a produced post. nuelink_id is the legacy schema name for any backend ref."""
    con.execute(
        "INSERT INTO posts(created, story_key, item_hash, class, body, receipt_url, mode,"
        " nuelink_id, editor_note, resolution_id, publisher_backend)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (time.time(), story_key, item_hash, klass, body, receipt_url, mode, publisher_ref,
         editor_note, resolution_id, publisher_backend),
    )
    con.commit()


def _publication_text_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join("".join(c if c.isalnum() else " " for c in normalized).split())


def _legacy_typefully_match(row, record: dict) -> bool:
    created_at = record.get("created_at")
    if created_at is None or abs(float(row["created"]) - float(created_at)) > 600:
        return False
    local = _publication_text_key(row["body"])
    if len(local) < 32:
        return False
    for field in ("preview", "draft_title"):
        remote = _publication_text_key(record.get(field, ""))
        if len(remote) >= 32 and (local.startswith(remote) or remote.startswith(local)):
            return True
    return False


def reconcile_typefully_publications(con, records: list, synced_at: float = None) -> dict:
    """Promote locally known Typefully drafts from authoritative published records.

    Unknown Typefully posts are intentionally not ingested: this increment repairs the
    Desk's lifecycle truth without turning it into a second content-management system.
    """
    synced_at = synced_at or time.time()
    stats = {
        "fetched": len(records), "matched": 0, "promoted": 0, "enriched": 0,
        "legacy_backfilled": 0, "unknown": 0, "duplicates": 0,
        "legacy_guard_failed": 0, "tape_anomaly": 0, "mode_anomaly": 0,
    }
    with con:
        for record in records:
            ref = str(record["id"])
            typed = con.execute(
                "SELECT * FROM posts WHERE publisher_backend='typefully' AND nuelink_id=?",
                (ref,),
            ).fetchall()
            if len(typed) > 1:
                stats["duplicates"] += 1
                continue
            legacy = False
            if typed:
                row = typed[0]
            else:
                candidates = con.execute(
                    "SELECT * FROM posts WHERE publisher_backend IS NULL AND nuelink_id=?",
                    (ref,),
                ).fetchall()
                if len(candidates) > 1:
                    stats["duplicates"] += 1
                    continue
                if not candidates:
                    stats["unknown"] += 1
                    continue
                row, legacy = candidates[0], True

            if row["mode"] == "TAPE":
                stats["tape_anomaly"] += 1
                continue
            if legacy and not _legacy_typefully_match(row, record):
                stats["legacy_guard_failed"] += 1
                continue
            if row["mode"] not in ("DRAFT", "UNCERTAIN", "FAILED", "IMMEDIATE"):
                stats["mode_anomaly"] += 1
                continue

            was_published = row["mode"] == "IMMEDIATE"
            con.execute(
                "UPDATE posts SET mode='IMMEDIATE', confirmed_at=?,"
                " public_url=COALESCE(NULLIF(?,''),public_url), publisher_status='published',"
                " publisher_synced_at=?, publisher_backend='typefully' WHERE id=?",
                (record["published_at"], record.get("public_url", ""), synced_at, row["id"]),
            )
            if row["item_hash"]:
                con.execute("UPDATE items SET status='posted' WHERE url_hash=?",
                            (row["item_hash"],))
            stats["matched"] += 1
            stats["enriched" if was_published else "promoted"] += 1
            if legacy:
                stats["legacy_backfilled"] += 1

        con.execute(
            "INSERT INTO kv(k,v) VALUES ('publisher:last_success',?)"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(synced_at),))
        con.execute(
            "INSERT INTO kv(k,v) VALUES ('publisher:last_error','')"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v")
        con.execute(
            "INSERT INTO kv(k,v) VALUES ('publisher:last_counts',?)"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (json.dumps(stats, sort_keys=True),))
    return stats


def day_bounds(day_str: str):
    """(start_ts, end_ts) for a YYYY-MM-DD day in America/Chicago (the desk's clock)."""
    import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/Chicago")
    d = datetime.date.fromisoformat(day_str)
    start = datetime.datetime(d.year, d.month, d.day, tzinfo=tz)
    return start.timestamp(), (start + datetime.timedelta(days=1)).timestamp()


def day_summary(con, day_str: str) -> dict:
    s, e = day_bounds(day_str)
    effective = effective_post_ts_sql()
    posts = con.execute(
        f"SELECT COUNT(*) n FROM posts WHERE {effective}>=? AND {effective}<?"
        " AND mode='IMMEDIATE'",
        (s, e)).fetchone()["n"]
    drafts = con.execute(
        "SELECT COUNT(*) n FROM posts WHERE created>=? AND created<? AND mode='DRAFT'",
        (s, e)).fetchone()["n"]
    uncertain = con.execute(
        "SELECT COUNT(*) n FROM posts WHERE created>=? AND created<? AND mode='UNCERTAIN'",
        (s, e)).fetchone()["n"]
    failed = con.execute(
        "SELECT COUNT(*) n FROM posts WHERE created>=? AND created<? AND mode='FAILED'",
        (s, e)).fetchone()["n"]
    tape = con.execute(
        "SELECT COUNT(*) n FROM posts WHERE created>=? AND created<? AND mode='TAPE'",
        (s, e)).fetchone()["n"]
    held = con.execute(
        "SELECT COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<? AND status='held'",
        (s, e)).fetchone()["n"]
    skipped = con.execute(
        "SELECT COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<? AND status='skipped'",
        (s, e)).fetchone()["n"]
    seen = con.execute(
        "SELECT COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<?", (s, e)).fetchone()["n"]
    evaluated = con.execute(
        "SELECT COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<?"
        " AND status!='new'", (s, e)).fetchone()["n"]
    outputs_created = con.execute(
        "SELECT COUNT(*) n FROM posts WHERE created>=? AND created<?", (s, e)).fetchone()["n"]
    return {"published": posts, "drafts": drafts, "uncertain": uncertain,
            "failed": failed, "tape": tape, "held": held, "skipped": skipped, "seen": seen,
            "evaluated": evaluated, "outputs_created": outputs_created}


def status_summary(con) -> dict:
    rows = con.execute("SELECT status, COUNT(*) n FROM items GROUP BY status").fetchall()
    posts = con.execute("SELECT COUNT(*) n FROM posts").fetchone()["n"]
    return {"items": {r["status"]: r["n"] for r in rows}, "posts": posts}
