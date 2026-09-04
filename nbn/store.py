"""SQLite state: seen items, story-level dedup, post log."""
import datetime
import hashlib
import ipaddress
import json
import re
import sqlite3
import time
import unicodedata
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import config, guide_context, source_policy, theme_context

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
  decision_category TEXT,
  defer_until REAL
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created REAL, story_key TEXT, item_hash TEXT, class TEXT,
  body TEXT, receipt_url TEXT, mode TEXT, nuelink_id TEXT,
  editor_note TEXT, resolution_id TEXT,
  confirmed_at REAL, public_url TEXT, publisher_status TEXT,
  publisher_synced_at REAL, publisher_backend TEXT,
  performance_json TEXT, performance_synced_at REAL,
  coverage_relation TEXT NOT NULL DEFAULT 'legacy',
  base_post_id INTEGER,
  mutation_id TEXT
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
CREATE TABLE IF NOT EXISTS story_key_aliases (
  alias_key TEXT PRIMARY KEY,
  canonical_key TEXT NOT NULL,
  reason TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_story_alias_canonical
  ON story_key_aliases(canonical_key);
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
CREATE TABLE IF NOT EXISTS publisher_mutations (
  mutation_id TEXT PRIMARY KEY,
  canonical_key TEXT NOT NULL,
  operation TEXT NOT NULL,
  target_draft_id TEXT,
  target_post_id INTEGER,
  base_post_id INTEGER,
  desired_fingerprint TEXT NOT NULL,
  prior_fingerprint TEXT,
  owner_token TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  state TEXT NOT NULL,
  intended_mode TEXT NOT NULL,
  materialization_json TEXT NOT NULL,
  provider_ref TEXT,
  error_kind TEXT,
  error_message TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  resolved_at REAL
);
CREATE INDEX IF NOT EXISTS idx_publisher_mutations_family
  ON publisher_mutations(canonical_key, state, updated_at DESC);
CREATE TABLE IF NOT EXISTS newsroom_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  mode TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  inventory_fingerprint TEXT NOT NULL,
  inventory_json TEXT NOT NULL,
  survey_json TEXT,
  dossier_json TEXT,
  dossier_digest TEXT,
  counters_json TEXT NOT NULL DEFAULT '{}',
  error_kind TEXT,
  error_message TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  completed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_newsroom_runs_status_created
  ON newsroom_runs(status, created_at);
CREATE TABLE IF NOT EXISTS newsroom_story_commits (
  run_id TEXT NOT NULL,
  story_id TEXT NOT NULL,
  state TEXT NOT NULL,
  dossier_digest TEXT NOT NULL,
  delivery_ref TEXT,
  details_json TEXT NOT NULL DEFAULT '{}',
  updated_at REAL NOT NULL,
  PRIMARY KEY(run_id, story_id)
);
CREATE INDEX IF NOT EXISTS idx_newsroom_story_state
  ON newsroom_story_commits(state, updated_at);
CREATE TABLE IF NOT EXISTS newsroom_story_memory (
  canonical_key TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  attempts_json TEXT NOT NULL DEFAULT '[]',
  evidence_pool_json TEXT NOT NULL DEFAULT '[]',
  editor_json TEXT NOT NULL DEFAULT '{}',
  delivery_json TEXT NOT NULL DEFAULT '{}',
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_newsroom_story_memory_expiry
  ON newsroom_story_memory(expires_at);
CREATE TABLE IF NOT EXISTS newsroom_storylines (
  storyline_key TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  lifecycle TEXT NOT NULL,
  watch_for_json TEXT NOT NULL DEFAULT '[]',
  update_reason TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  last_signal_at REAL NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_newsroom_storylines_recent
  ON newsroom_storylines(lifecycle, updated_at DESC);
CREATE TABLE IF NOT EXISTS newsroom_storyline_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  storyline_key TEXT NOT NULL,
  item_hash TEXT NOT NULL,
  canonical_event_key TEXT,
  run_id TEXT NOT NULL,
  disposition TEXT NOT NULL,
  relationship TEXT NOT NULL,
  observed_at REAL NOT NULL,
  created_at REAL NOT NULL,
  UNIQUE(storyline_key, item_hash, run_id)
);
CREATE INDEX IF NOT EXISTS idx_newsroom_storyline_events_recent
  ON newsroom_storyline_events(storyline_key, observed_at DESC, id DESC);
CREATE TABLE IF NOT EXISTS model_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  seat TEXT NOT NULL,
  model TEXT NOT NULL,
  round INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cache_creation_input_tokens INTEGER NOT NULL DEFAULT 0,
  cache_creation_5m_input_tokens INTEGER NOT NULL DEFAULT 0,
  cache_creation_1h_input_tokens INTEGER NOT NULL DEFAULT 0,
  cache_read_input_tokens INTEGER NOT NULL DEFAULT 0,
  latency_ms INTEGER NOT NULL DEFAULT 0,
  outcome TEXT NOT NULL,
  estimated_cost_usd REAL NOT NULL DEFAULT 0,
  rate_version TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_model_usage_created ON model_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_model_usage_run ON model_usage(run_id, seat);
CREATE TABLE IF NOT EXISTS desk_preparations (
  run_id TEXT NOT NULL,
  item_hash TEXT NOT NULL,
  model_route TEXT NOT NULL,
  effective_route TEXT NOT NULL,
  event_summary TEXT NOT NULL DEFAULT '',
  bitcoin_relevance TEXT NOT NULL DEFAULT '',
  freshness_note TEXT NOT NULL DEFAULT '',
  research_objective TEXT NOT NULL DEFAULT '',
  source_leads_json TEXT NOT NULL DEFAULT '[]',
  related_keys_json TEXT NOT NULL DEFAULT '[]',
  related_storyline_keys_json TEXT NOT NULL DEFAULT '[]',
  event_group TEXT NOT NULL DEFAULT '',
  companion_anchor_hash TEXT,
  protection_reason TEXT,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  outcome TEXT NOT NULL,
  error_kind TEXT,
  mode TEXT NOT NULL,
  application_state TEXT NOT NULL,
  prepared_at REAL NOT NULL,
  applied_at REAL NOT NULL,
  promoted_at REAL,
  PRIMARY KEY(run_id, item_hash)
);
CREATE INDEX IF NOT EXISTS idx_desk_prep_item_time
  ON desk_preparations(item_hash, prepared_at DESC);
CREATE INDEX IF NOT EXISTS idx_desk_prep_route_time
  ON desk_preparations(effective_route, prepared_at DESC);
CREATE TABLE IF NOT EXISTS search_provider_state (
  provider TEXT PRIMARY KEY,
  state TEXT NOT NULL DEFAULT 'unknown',
  plan_name TEXT NOT NULL DEFAULT '',
  plan_renewal_date TEXT NOT NULL DEFAULT '',
  searches_per_month INTEGER,
  this_month_usage INTEGER,
  total_searches_left INTEGER,
  this_hour_searches INTEGER,
  last_hour_searches INTEGER,
  account_rate_limit_per_hour INTEGER,
  last_status_attempt_at REAL,
  last_status_success_at REAL,
  next_search_at REAL,
  last_search_success_at REAL,
  consecutive_failures INTEGER NOT NULL DEFAULT 0,
  error_kind TEXT,
  error_message TEXT,
  status_claim_token TEXT,
  status_claimed_at REAL,
  status_expires_at REAL,
  probe_claim_token TEXT,
  probe_claimed_at REAL,
  probe_expires_at REAL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS search_query_cache (
  cache_key TEXT PRIMARY KEY,
  provider TEXT NOT NULL,
  engine TEXT NOT NULL,
  normalized_query TEXT NOT NULL,
  locale_gl TEXT NOT NULL,
  locale_hl TEXT NOT NULL,
  result_limit INTEGER NOT NULL,
  page_start INTEGER NOT NULL,
  results_json TEXT NOT NULL,
  created_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  hit_count INTEGER NOT NULL DEFAULT 0,
  last_hit_at REAL
);
CREATE INDEX IF NOT EXISTS idx_search_cache_expiry
  ON search_query_cache(expires_at);
CREATE TABLE IF NOT EXISTS search_result_pointers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope_type TEXT NOT NULL,
  scope_key TEXT NOT NULL,
  provider TEXT NOT NULL,
  url TEXT NOT NULL,
  outlet TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  snippet TEXT NOT NULL DEFAULT '',
  observed_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  UNIQUE(scope_type, scope_key, provider, url)
);
CREATE INDEX IF NOT EXISTS idx_search_pointers_scope
  ON search_result_pointers(scope_type, scope_key, expires_at DESC);
CREATE TABLE IF NOT EXISTS search_activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  event TEXT NOT NULL,
  kind TEXT NOT NULL DEFAULT '',
  at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_search_activity_at ON search_activity(at);
CREATE TABLE IF NOT EXISTS intake_triage (
  item_hash TEXT PRIMARY KEY,
  route TEXT NOT NULL,
  category TEXT NOT NULL,
  reason TEXT NOT NULL,
  outcome TEXT NOT NULL,
  error_kind TEXT,
  origin TEXT NOT NULL,
  source TEXT NOT NULL,
  model TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  batch_id TEXT NOT NULL,
  triaged_at REAL NOT NULL,
  applied_at REAL,
  promoted_at REAL
);
CREATE INDEX IF NOT EXISTS idx_intake_triage_route_time
  ON intake_triage(route, triaged_at DESC);
CREATE INDEX IF NOT EXISTS idx_intake_triage_time
  ON intake_triage(triaged_at DESC);
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
    "performance_json": "TEXT",
    "performance_synced_at": "REAL",
    "coverage_relation": "TEXT NOT NULL DEFAULT 'legacy'",
    "base_post_id": "INTEGER",
    "mutation_id": "TEXT",
    "storyline_key": "TEXT",
}

ITEM_COLUMNS = {
    "summary": "TEXT DEFAULT ''",
    "discovery_key": "TEXT",
    "discovery_origin": "TEXT DEFAULT 'legacy'",
    "discovery_context": "TEXT DEFAULT ''",
    "discovery_candidate_id": "TEXT",
    "decision_stage": "TEXT",
    "decision_category": "TEXT",
    "defer_until": "REAL",
}

NODE_RUN_COLUMNS = {
    "context_json": "TEXT NOT NULL DEFAULT '{}'",
    "diagnostics_json": "TEXT NOT NULL DEFAULT '{}'",
}

NEWSROOM_COMMIT_COLUMNS = {
    "details_json": "TEXT NOT NULL DEFAULT '{}'",
}

NEWSROOM_MEMORY_COLUMNS = {
    "evidence_pool_json": "TEXT NOT NULL DEFAULT '[]'",
}

MODEL_USAGE_COLUMNS = {
    "cache_creation_5m_input_tokens": "INTEGER NOT NULL DEFAULT 0",
    "cache_creation_1h_input_tokens": "INTEGER NOT NULL DEFAULT 0",
}

DESK_PREPARATION_COLUMNS = {
    "event_group": "TEXT NOT NULL DEFAULT ''",
    "companion_anchor_hash": "TEXT",
    "related_storyline_keys_json": "TEXT NOT NULL DEFAULT '[]'",
}

SEARCH_PROVIDER_COLUMNS = {
    "status_claim_token": "TEXT",
    "status_claimed_at": "REAL",
    "status_expires_at": "REAL",
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
    con.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_mutation"
        " ON posts(mutation_id) WHERE mutation_id IS NOT NULL"
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


def _ensure_newsroom_columns(con):
    for table, columns in (
        ("newsroom_story_commits", NEWSROOM_COMMIT_COLUMNS),
        ("newsroom_story_memory", NEWSROOM_MEMORY_COLUMNS),
    ):
        existing = {r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, declaration in columns.items():
            if name not in existing:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {declaration}")
    con.commit()


def _ensure_model_usage_columns(con):
    existing = {r["name"] for r in con.execute("PRAGMA table_info(model_usage)").fetchall()}
    for name, declaration in MODEL_USAGE_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE model_usage ADD COLUMN {name} {declaration}")
    con.commit()


def _ensure_desk_preparation_columns(con):
    existing = {r["name"] for r in con.execute("PRAGMA table_info(desk_preparations)").fetchall()}
    for name, declaration in DESK_PREPARATION_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE desk_preparations ADD COLUMN {name} {declaration}")
    con.commit()


def _ensure_search_provider_columns(con):
    existing = {
        row["name"] for row in con.execute(
            "PRAGMA table_info(search_provider_state)"
        ).fetchall()
    }
    for name, declaration in SEARCH_PROVIDER_COLUMNS.items():
        if name not in existing:
            con.execute(
                f"ALTER TABLE search_provider_state ADD COLUMN {name} {declaration}"
            )
    con.commit()


def kv_get(con, k: str) -> str:
    row = con.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return row["v"] if row else ""


def kv_set(con, k: str, v: str):
    con.execute("INSERT INTO kv(k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    con.commit()


_SEARCH_CACHE_MAX_BYTES = 20 * 1024
_SEARCH_POINTER_MAX_AGE_SECONDS = 24 * 3600
_SEARCH_QUOTA_FALLBACK_SECONDS = 6 * 3600
_SEARCH_EVENTS = {
    "cache_hit", "cache_miss", "provider_http_attempt", "provider_skip",
    "provider_failure", "pointer_reuse", "account_status_success", "account_status_failure",
}


def _ensure_search_provider_row(con, provider: str, now: float | None = None) -> None:
    stamp = float(now if now is not None else time.time())
    con.execute(
        "INSERT OR IGNORE INTO search_provider_state(provider,state,updated_at)"
        " VALUES (?,'unknown',?)",
        (str(provider or "")[:40], stamp),
    )


def search_provider_state(con, provider: str = "serpapi") -> dict:
    row = con.execute(
        "SELECT * FROM search_provider_state WHERE provider=?", (str(provider)[:40],)
    ).fetchone()
    return dict(row) if row else {"provider": str(provider)[:40], "state": "unknown"}


def claim_search_status_check(con, provider: str, *, ttl_seconds: int,
                              lease_seconds: float = 30,
                              now: float | None = None) -> dict:
    """Claim one throttled account-status request across runs/processes."""
    stamp = float(now if now is not None else time.time())
    cutoff = stamp - max(30, min(int(ttl_seconds), 3600))
    token = uuid.uuid4().hex
    expiry = stamp + max(5.0, min(float(lease_seconds), 300.0))
    try:
        con.execute("BEGIN IMMEDIATE")
        _ensure_search_provider_row(con, provider, stamp)
        row = con.execute(
            "SELECT last_status_attempt_at,status_claim_token,status_expires_at,"
            "probe_claim_token,probe_expires_at FROM search_provider_state WHERE provider=?",
            (str(provider)[:40],),
        ).fetchone()
        status_active = bool(
            row and row["status_claim_token"]
            and float(row["status_expires_at"] or 0) > stamp
        )
        probe_active = bool(
            row and row["probe_claim_token"]
            and float(row["probe_expires_at"] or 0) > stamp
        )
        if status_active or probe_active:
            con.commit()
            return {"token": "", "reason": "in_progress"}
        due = not row or row["last_status_attempt_at"] is None \
            or float(row["last_status_attempt_at"]) <= cutoff
        if not due:
            con.commit()
            return {"token": "", "reason": "throttled"}
        con.execute(
            "UPDATE search_provider_state SET last_status_attempt_at=?,"
            "status_claim_token=?,status_claimed_at=?,status_expires_at=?,updated_at=?"
            " WHERE provider=?",
            (stamp, token, stamp, expiry, stamp, str(provider)[:40]),
        )
        con.commit()
        return {"token": token, "reason": "claimed"}
    except Exception:
        con.rollback()
        raise


def _renewal_epoch(value: str, now: float) -> float:
    try:
        parsed = datetime.datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)
        stamp = parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return now + _SEARCH_QUOTA_FALLBACK_SECONDS
    return stamp if stamp > now else now + _SEARCH_QUOTA_FALLBACK_SECONDS


def record_search_account_status(con, snapshot: dict, *, status_token: str = "",
                                 now: float | None = None) -> bool:
    """Persist only the allowlisted capacity fields from a successful free account check."""
    stamp = float(now if now is not None else time.time())
    provider = str(snapshot.get("provider") or "serpapi")[:40]

    def optional_int(name: str):
        value = snapshot.get(name)
        if value is None or isinstance(value, bool):
            return None
        try:
            return max(0, min(int(value), 1_000_000_000))
        except (TypeError, ValueError):
            return None

    try:
        con.execute("BEGIN IMMEDIATE")
        _ensure_search_provider_row(con, provider, stamp)
        current = con.execute(
            "SELECT * FROM search_provider_state WHERE provider=?", (provider,)
        ).fetchone()
        if status_token and (
            not current or current["status_claim_token"] != str(status_token)[:64]
        ):
            con.commit()
            return False
        if current and current["probe_claim_token"] \
                and float(current["probe_expires_at"] or 0) > stamp:
            con.commit()
            return False

        remaining = optional_int("total_searches_left")
        renewal = str(snapshot.get("plan_renewal_date") or "")[:40] or str(
            current["plan_renewal_date"] if current else ""
        )
        prior_state = str(current["state"] if current else "unknown")
        prior_next = current["next_search_at"] if current else None
        prior_failures = int(current["consecutive_failures"] if current else 0)
        if snapshot.get("state") == "unconfigured":
            state, next_search, failures = "unconfigured", None, prior_failures
        elif prior_state == "quota_exhausted" and remaining is None:
            state, next_search, failures = prior_state, prior_next, prior_failures
        elif remaining == 0:
            state = "quota_exhausted"
            next_search = _renewal_epoch(renewal, stamp)
            failures = prior_failures
        elif prior_state == "quota_exhausted" and remaining is not None and remaining > 0:
            state, next_search, failures = "healthy", None, 0
        elif prior_state in {"rate_limited", "degraded"}:
            state, next_search, failures = prior_state, prior_next, prior_failures
        elif remaining is not None:
            state, next_search, failures = "healthy", prior_next, prior_failures
        else:
            state, next_search, failures = "unknown", prior_next, prior_failures

        preserve_error = state in {"quota_exhausted", "rate_limited", "degraded"}
        error_kind = current["error_kind"] if current and preserve_error else None
        error_message = current["error_message"] if current and preserve_error else None

        def snapshot_or_prior(name: str):
            value = optional_int(name)
            return value if value is not None else (current[name] if current else None)

        status_where = "provider=?"
        status_values: tuple = (provider,)
        if status_token:
            status_where += " AND status_claim_token=?"
            status_values += (str(status_token)[:64],)
        cur = con.execute(
            "UPDATE search_provider_state SET state=?,plan_name=?,plan_renewal_date=?,"
            "searches_per_month=?,this_month_usage=?,total_searches_left=?,"
            "this_hour_searches=?,last_hour_searches=?,account_rate_limit_per_hour=?,"
            "last_status_success_at=?,next_search_at=?,consecutive_failures=?,error_kind=?,"
            "error_message=?,status_claim_token=?,status_claimed_at=?,status_expires_at=?,"
            f"updated_at=? WHERE {status_where}",
            (state, str(snapshot.get("plan_name") or "")[:80]
             or str(current["plan_name"] if current else ""), renewal,
             snapshot_or_prior("searches_per_month"),
             snapshot_or_prior("this_month_usage"),
             remaining if remaining is not None else (
                 current["total_searches_left"] if current else None
             ),
             snapshot_or_prior("this_hour_searches"),
             snapshot_or_prior("last_hour_searches"),
             snapshot_or_prior("account_rate_limit_per_hour"),
             stamp, next_search, failures, error_kind, error_message,
             None if status_token else current["status_claim_token"],
             None if status_token else current["status_claimed_at"],
             None if status_token else current["status_expires_at"],
             stamp, *status_values),
        )
        con.commit()
        return cur.rowcount == 1
    except Exception:
        con.rollback()
        raise


def record_search_account_failure(con, provider: str, kind: str, message: str,
                                  *, status_token: str = "",
                                  now: float | None = None) -> bool:
    """Record a failed status attempt without destroying the last good capacity snapshot."""
    stamp = float(now if now is not None else time.time())
    _ensure_search_provider_row(con, provider, stamp)
    where = "provider=?"
    values: tuple = (str(provider)[:40],)
    if status_token:
        where += " AND status_claim_token=?"
        values += (str(status_token)[:64],)
    release = int(bool(status_token))
    cur = con.execute(
        "UPDATE search_provider_state SET error_kind=?,error_message=?,"
        "status_claim_token=CASE WHEN ?=1 THEN NULL ELSE status_claim_token END,"
        "status_claimed_at=CASE WHEN ?=1 THEN NULL ELSE status_claimed_at END,"
        "status_expires_at=CASE WHEN ?=1 THEN NULL ELSE status_expires_at END,updated_at=?"
        f" WHERE {where}",
        (f"account_{str(kind or 'error')[:70]}", str(message or "")[:240],
         release, release, release, stamp, *values),
    )
    con.commit()
    return cur.rowcount == 1


def fail_search_status_and_claim_probe(
        con, provider: str, kind: str, message: str, *, status_token: str,
        probe_lease_seconds: float, now: float | None = None) -> dict:
    """Atomically finish a failed status check and, when due, own its quota probe."""
    stamp = float(now if now is not None else time.time())
    provider = str(provider)[:40]
    status_token = str(status_token)[:64]
    probe_token = uuid.uuid4().hex
    probe_expiry = stamp + max(5.0, min(float(probe_lease_seconds), 300.0))
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT state,next_search_at,status_claim_token,probe_claim_token,"
            "probe_claimed_at,probe_expires_at FROM search_provider_state WHERE provider=?",
            (provider,),
        ).fetchone()
        if not row or row["status_claim_token"] != status_token:
            con.commit()
            return {"recorded": False, "probe_token": ""}
        should_probe = bool(
            row["state"] == "quota_exhausted"
            and float(row["next_search_at"] or 0) <= stamp
            and (
                not row["probe_claim_token"]
                or float(row["probe_expires_at"] or 0) <= stamp
            )
        )
        con.execute(
            "UPDATE search_provider_state SET error_kind=?,error_message=?,"
            "status_claim_token=NULL,status_claimed_at=NULL,status_expires_at=NULL,"
            "probe_claim_token=?,probe_claimed_at=?,probe_expires_at=?,updated_at=?"
            " WHERE provider=? AND status_claim_token=?",
            (f"account_{str(kind or 'error')[:70]}", str(message or "")[:240],
             probe_token if should_probe else row["probe_claim_token"],
             stamp if should_probe else row["probe_claimed_at"],
             probe_expiry if should_probe else row["probe_expires_at"],
             stamp, provider, status_token),
        )
        con.commit()
        return {"recorded": True, "probe_token": probe_token if should_probe else ""}
    except Exception:
        con.rollback()
        raise


def claim_search_probe(con, provider: str, *, lease_seconds: float,
                       now: float | None = None) -> str:
    """Atomically claim or reclaim one half-open quota probe."""
    stamp = float(now if now is not None else time.time())
    token = uuid.uuid4().hex
    expiry = stamp + max(5.0, min(float(lease_seconds), 300.0))
    try:
        con.execute("BEGIN IMMEDIATE")
        _ensure_search_provider_row(con, provider, stamp)
        cur = con.execute(
            "UPDATE search_provider_state SET probe_claim_token=?,probe_claimed_at=?,"
            "probe_expires_at=?,updated_at=? WHERE provider=? AND state='quota_exhausted'"
            " AND COALESCE(next_search_at,0)<=?"
            " AND (status_claim_token IS NULL OR COALESCE(status_expires_at,0)<=?)"
            " AND (probe_claim_token IS NULL OR COALESCE(probe_expires_at,0)<=?)",
            (token, stamp, expiry, stamp, str(provider)[:40], stamp, stamp, stamp),
        )
        con.commit()
        return token if cur.rowcount == 1 else ""
    except Exception:
        con.rollback()
        raise


def record_search_success(con, provider: str, *, probe_token: str = "",
                          now: float | None = None) -> bool:
    stamp = float(now if now is not None else time.time())
    where = "provider=?"
    values: tuple = (str(provider)[:40],)
    if probe_token:
        where += " AND probe_claim_token=?"
        values += (str(probe_token)[:64],)
    else:
        where += " AND (probe_claim_token IS NULL OR COALESCE(probe_expires_at,0)<=?)"
        values += (stamp,)
    cur = con.execute(
        "UPDATE search_provider_state SET state='healthy',next_search_at=NULL,"
        "last_search_success_at=?,consecutive_failures=0,error_kind=NULL,error_message=NULL,"
        "probe_claim_token=NULL,probe_claimed_at=NULL,probe_expires_at=NULL,updated_at=?"
        f" WHERE {where}",
        (stamp, stamp, *values),
    )
    con.commit()
    return cur.rowcount == 1


def record_search_failure(con, provider: str, kind: str, message: str, *,
                          retry_after_seconds: int = 0, probe_token: str = "",
                          cooldown_seconds: int = 300,
                          now: float | None = None) -> bool:
    stamp = float(now if now is not None else time.time())
    provider = str(provider)[:40]
    _ensure_search_provider_row(con, provider, stamp)
    current = con.execute(
        "SELECT state,next_search_at,plan_renewal_date,consecutive_failures"
        " FROM search_provider_state"
        " WHERE provider=?", (provider,),
    ).fetchone()
    failure_kind = str(kind or "provider_error")[:80]
    if failure_kind == "quota_exhausted":
        state = "quota_exhausted"
        next_search = _renewal_epoch(
            current["plan_renewal_date"] if current else "", stamp
        )
    elif failure_kind == "rate_limited":
        state = "rate_limited"
        next_search = stamp + max(1, min(
            int(retry_after_seconds or cooldown_seconds), 3600
        ))
    else:
        failure_count = int(current["consecutive_failures"] if current else 0) + 1
        if probe_token or failure_count >= 2:
            state = "degraded"
            next_search = stamp + max(30, min(int(cooldown_seconds), 3600))
        else:
            prior_state = str(current["state"] if current else "unknown")
            state = prior_state if prior_state in {"healthy", "unknown"} else "unknown"
            next_search = current["next_search_at"] if current else None
    where = "provider=?"
    values: tuple = (provider,)
    if probe_token:
        where += " AND probe_claim_token=?"
        values += (str(probe_token)[:64],)
    else:
        where += " AND (probe_claim_token IS NULL OR COALESCE(probe_expires_at,0)<=?)"
        values += (stamp,)
    cur = con.execute(
        "UPDATE search_provider_state SET state=?,next_search_at=?,"
        "consecutive_failures=consecutive_failures+1,error_kind=?,error_message=?,"
        "probe_claim_token=NULL,probe_claimed_at=NULL,probe_expires_at=NULL,updated_at=?"
        f" WHERE {where}",
        (state, next_search, failure_kind, str(message or "")[:240], stamp, *values),
    )
    con.commit()
    return cur.rowcount == 1


def _valid_search_result(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    url = str(raw.get("url") or "").strip()
    outlet = str(raw.get("outlet") or "")
    title = str(raw.get("title") or "")
    snippet = str(raw.get("snippet") or "")
    if len(url) > 2000 or len(outlet) > 160 or len(title) > 300 or len(snippet) > 1200:
        return None
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").lower()
        if parts.scheme not in {"http", "https"} or not host or parts.username or parts.password:
            return None
        if host == "localhost" or host.endswith(".local"):
            return None
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return None
        except ValueError:
            pass
    except (TypeError, ValueError):
        return None
    try:
        rank = max(1, min(int(raw.get("rank") or 1), 100))
    except (TypeError, ValueError):
        return None
    return {
        "rank": rank,
        "url": url,
        "outlet": outlet,
        "title": title,
        "snippet": snippet,
    }


def search_cache_get(con, identity: dict, *, now: float | None = None) -> list[dict] | None:
    stamp = float(now if now is not None else time.time())
    row = con.execute(
        "SELECT * FROM search_query_cache WHERE cache_key=? AND expires_at>?",
        (str(identity.get("cache_key") or "")[:64], stamp),
    ).fetchone()
    if not row:
        return None
    expected = (
        str(identity.get("provider") or ""), str(identity.get("engine") or ""),
        str(identity.get("query") or ""), str(identity.get("gl") or ""),
        str(identity.get("hl") or ""), int(identity.get("limit") or 0),
        int(identity.get("start") or 0),
    )
    actual = (
        row["provider"], row["engine"], row["normalized_query"], row["locale_gl"],
        row["locale_hl"], int(row["result_limit"]), int(row["page_start"]),
    )
    try:
        encoded = str(row["results_json"] or "")
        parsed = json.loads(encoded)
    except (TypeError, ValueError):
        parsed, encoded = None, ""
    valid = [] if isinstance(parsed, list) else None
    if valid is not None:
        for raw in parsed[:8]:
            item = _valid_search_result(raw)
            if item:
                valid.append(item)
    if expected != actual or len(encoded.encode("utf-8")) > _SEARCH_CACHE_MAX_BYTES \
            or valid is None or len(valid) != len(parsed):
        con.execute("DELETE FROM search_query_cache WHERE cache_key=?", (row["cache_key"],))
        con.commit()
        return None
    con.execute(
        "UPDATE search_query_cache SET hit_count=hit_count+1,last_hit_at=? WHERE cache_key=?",
        (stamp, row["cache_key"]),
    )
    con.commit()
    return valid[:int(identity.get("limit") or 5)]


def search_cache_put(con, identity: dict, results: list[dict], *, ttl_seconds: int,
                     now: float | None = None) -> list[dict]:
    stamp = float(now if now is not None else time.time())
    bounded = []
    for raw in list(results or [])[:min(8, int(identity.get("limit") or 5))]:
        value = _valid_search_result(raw)
        if value:
            bounded.append(value)
    encoded = json.dumps(bounded, separators=(",", ":"), ensure_ascii=False)
    while bounded and len(encoded.encode("utf-8")) > _SEARCH_CACHE_MAX_BYTES:
        bounded.pop()
        encoded = json.dumps(bounded, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > _SEARCH_CACHE_MAX_BYTES:
        bounded, encoded = [], "[]"
    con.execute(
        "INSERT INTO search_query_cache(cache_key,provider,engine,normalized_query,locale_gl,"
        "locale_hl,result_limit,page_start,results_json,created_at,expires_at,hit_count,last_hit_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,0,NULL) ON CONFLICT(cache_key) DO UPDATE SET"
        " results_json=excluded.results_json,created_at=excluded.created_at,"
        "expires_at=excluded.expires_at,hit_count=0,last_hit_at=NULL",
        (str(identity.get("cache_key") or "")[:64], str(identity.get("provider") or "")[:40],
         str(identity.get("engine") or "")[:40], str(identity.get("query") or "")[:400],
         str(identity.get("gl") or "")[:10], str(identity.get("hl") or "")[:10],
         int(identity.get("limit") or 5), int(identity.get("start") or 0), encoded,
         stamp, stamp + max(60, min(int(ttl_seconds), 86400))),
    )
    con.commit()
    return bounded


def save_search_pointers(con, scopes: list[tuple[str, str]], results: list[dict], *,
                         provider: str = "serpapi", ttl_seconds: int = 21600,
                         now: float | None = None) -> int:
    stamp = float(now if now is not None else time.time())
    expiry = stamp + max(300, min(int(ttl_seconds), _SEARCH_POINTER_MAX_AGE_SECONDS))
    safe_scopes = list(dict.fromkeys(
        (str(kind)[:20], str(key)[:180]) for kind, key in scopes
        if kind in {"candidate", "story"} and str(key)
    ))[:16]
    bounded = [value for raw in list(results or [])[:5]
               if (value := _valid_search_result(raw))]
    inserted = 0
    for scope_type, scope_key in safe_scopes:
        for row in bounded:
            cur = con.execute(
                "INSERT INTO search_result_pointers(scope_type,scope_key,provider,url,outlet,"
                "title,snippet,observed_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(scope_type,scope_key,provider,url) DO UPDATE SET"
                " outlet=excluded.outlet,title=excluded.title,snippet=excluded.snippet,"
                "observed_at=excluded.observed_at,expires_at=excluded.expires_at",
                (scope_type, scope_key, str(provider)[:40], row["url"], row["outlet"],
                 row["title"], row["snippet"], stamp, expiry),
            )
            inserted += int(bool(cur.rowcount))
    con.commit()
    return inserted


def search_pointers_for_scopes(con, scopes: list[tuple[str, str]], *, limit: int = 12,
                               now: float | None = None) -> list[dict]:
    stamp = float(now if now is not None else time.time())
    rows, seen = [], set()
    for scope_type, scope_key in list(dict.fromkeys(scopes))[:16]:
        if scope_type not in {"candidate", "story"} or not scope_key:
            continue
        found = con.execute(
            "SELECT * FROM search_result_pointers WHERE scope_type=? AND scope_key=?"
            " AND expires_at>? ORDER BY observed_at DESC,id DESC LIMIT ?",
            (scope_type, str(scope_key)[:180], stamp, max(1, min(int(limit), 20))),
        ).fetchall()
        for raw in found:
            value = _valid_search_result(dict(raw))
            normalized = source_policy.normalize_url(value["url"]) if value else ""
            if not value or normalized in seen:
                continue
            seen.add(normalized)
            rows.append({**value, "provider": raw["provider"],
                         "observed_at": float(raw["observed_at"])})
            if len(rows) >= max(1, min(int(limit), 20)):
                return rows
    return rows


def record_search_activity(con, run_id: str, event: str, kind: str = "", *,
                           now: float | None = None) -> None:
    if event not in _SEARCH_EVENTS:
        return
    con.execute(
        "INSERT INTO search_activity(run_id,event,kind,at) VALUES (?,?,?,?)",
        (str(run_id or "")[:120], event, str(kind or "")[:80],
         float(now if now is not None else time.time())),
    )
    con.commit()


def search_health(con, *, since: float | None = None, now: float | None = None) -> dict:
    stamp = float(now if now is not None else time.time())
    start = float(since if since is not None else stamp - 86400)
    provider = search_provider_state(con)
    activity = {
        row["event"]: int(row["n"]) for row in con.execute(
            "SELECT event,COUNT(*) n FROM search_activity WHERE at>=? GROUP BY event", (start,)
        ).fetchall()
    }
    failures = {
        row["kind"] or "unknown": int(row["n"]) for row in con.execute(
            "SELECT kind,COUNT(*) n FROM search_activity"
            " WHERE at>=? AND event='provider_failure' GROUP BY kind", (start,)
        ).fetchall()
    }
    cache = con.execute(
        "SELECT COUNT(*) n FROM search_query_cache WHERE expires_at>?", (stamp,)
    ).fetchone()
    pointers = con.execute(
        "SELECT COUNT(*) n FROM search_result_pointers WHERE expires_at>?", (stamp,)
    ).fetchone()
    return {"provider": provider, "activity": activity, "failures": failures,
            "cache_entries": int(cache["n"] if cache else 0),
            "pointer_entries": int(pointers["n"] if pointers else 0)}


def prune_search_state(con, *, now: float | None = None, activity_days: int = 14) -> dict:
    stamp = float(now if now is not None else time.time())
    cache = con.execute("DELETE FROM search_query_cache WHERE expires_at<=?", (stamp,)).rowcount
    pointers = con.execute(
        "DELETE FROM search_result_pointers WHERE expires_at<=?", (stamp,)
    ).rowcount
    activity = con.execute(
        "DELETE FROM search_activity WHERE at<?",
        (stamp - max(1, min(int(activity_days), 90)) * 86400,),
    ).rowcount
    con.commit()
    return {"cache": int(cache), "pointers": int(pointers), "activity": int(activity)}


_MODEL_RATES = {
    # USD per million tokens. Prompt cache writes use Anthropic's default five-minute
    # 1.25x multiplier; cache hits use the documented 0.1x multiplier.
    "claude-sonnet-5": (2.0, 10.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-fable-5": (10.0, 50.0),
    "claude-fable-5-1": (10.0, 50.0),
    "claude-haiku-4-5": (1.0, 5.0),
}
MODEL_RATE_VERSION = "anthropic-public-2026-09-03-cache-ttl-v2"


def record_model_usage(con, *, run_id: str, seat: str, model: str, round_number: int,
                       response=None, latency_ms: int = 0, outcome: str = "ok") -> None:
    """Persist billing metadata only: never prompts, bodies, reasoning, or tool text."""
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    cache_create = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    cache_detail = getattr(usage, "cache_creation", None)
    cache_create_5m = int(
        getattr(cache_detail, "ephemeral_5m_input_tokens", 0) or 0
    )
    cache_create_1h = int(
        getattr(cache_detail, "ephemeral_1h_input_tokens", 0) or 0
    )
    if not cache_create_5m and not cache_create_1h:
        # Historical/current SDK responses without the detailed object used the
        # default five-minute cache duration.
        cache_create_5m = cache_create
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    input_rate, output_rate = _MODEL_RATES.get(str(model), (0.0, 0.0))
    estimated = ((input_tokens + cache_create_5m * 1.25 + cache_create_1h * 2.0
                  + cache_read * 0.1) * input_rate
                 + output_tokens * output_rate) / 1_000_000
    con.execute(
        "INSERT INTO model_usage(run_id,seat,model,round,input_tokens,output_tokens,"
        "cache_creation_input_tokens,cache_creation_5m_input_tokens,"
        "cache_creation_1h_input_tokens,cache_read_input_tokens,latency_ms,outcome,"
        "estimated_cost_usd,rate_version,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(run_id)[:120], str(seat)[:40], str(model)[:80], int(round_number),
         input_tokens, output_tokens, cache_create, cache_create_5m, cache_create_1h,
         cache_read, max(0, int(latency_ms)),
         str(outcome)[:40], estimated, MODEL_RATE_VERSION, time.time()),
    )
    con.commit()


def model_usage_summary(con, since: float) -> dict:
    row = con.execute(
        "SELECT COALESCE(SUM(input_tokens),0) AS input_tokens,"
        "COALESCE(SUM(output_tokens),0) AS output_tokens,"
        "COALESCE(SUM(cache_creation_input_tokens),0) AS cache_creation_input_tokens,"
        "COALESCE(SUM(cache_creation_5m_input_tokens),0) AS cache_creation_5m_input_tokens,"
        "COALESCE(SUM(cache_creation_1h_input_tokens),0) AS cache_creation_1h_input_tokens,"
        "COALESCE(SUM(cache_read_input_tokens),0) AS cache_read_input_tokens,"
        "COALESCE(SUM(estimated_cost_usd),0) AS estimated_cost_usd,"
        "COUNT(*) AS calls FROM model_usage WHERE created_at>=?", (float(since),),
    ).fetchone()
    return dict(row) if row else {}


def model_usage_seat_summary(con, *, seat: str, since: float, until: float) -> dict:
    row = con.execute(
        "SELECT COALESCE(SUM(input_tokens),0) AS input_tokens,"
        "COALESCE(SUM(output_tokens),0) AS output_tokens,"
        "COALESCE(SUM(estimated_cost_usd),0) AS estimated_cost_usd,COUNT(*) AS calls"
        " FROM model_usage WHERE seat=? AND created_at>=? AND created_at<?",
        (str(seat)[:40], float(since), float(until)),
    ).fetchone()
    return dict(row) if row else {}


def model_usage_calls(con, *, seat: str, since: float) -> int:
    row = con.execute(
        "SELECT COUNT(*) AS calls FROM model_usage WHERE seat=? AND created_at>=?",
        (str(seat)[:40], float(since)),
    ).fetchone()
    return int(row["calls"] if row else 0)


def save_desk_preparations(con, rows: list[dict], *, mode: str) -> dict:
    """Persist one run-scoped preparation batch and atomically apply enforcement."""
    if mode not in {"observe", "enforce"}:
        raise ValueError("desk preparation persistence requires observe or enforce mode")
    inserted = suppressed = advanced = 0
    now = time.time()
    try:
        con.execute("BEGIN IMMEDIATE")
        for value in rows:
            leads = json.dumps(list(value.get("source_leads") or [])[:3],
                               separators=(",", ":"), ensure_ascii=False)
            related = json.dumps(list(value.get("related_keys") or [])[:3],
                                 separators=(",", ":"), ensure_ascii=False)
            storylines = json.dumps(list(value.get("related_storyline_keys") or [])[:2],
                                   separators=(",", ":"), ensure_ascii=False)
            if (len(leads.encode("utf-8")) > 1800 or len(related.encode("utf-8")) > 800
                    or len(storylines.encode("utf-8")) > 400):
                raise ValueError("desk preparation row exceeds JSON bounds")
            effective = str(value.get("effective_route") or "advance")[:20]
            state = "observed" if mode == "observe" else "applied"
            cur = con.execute(
                "INSERT OR REPLACE INTO desk_preparations("
                "run_id,item_hash,model_route,effective_route,event_summary,"
                "bitcoin_relevance,freshness_note,research_objective,source_leads_json,"
                "related_keys_json,related_storyline_keys_json,event_group,companion_anchor_hash,"
                "protection_reason,model,prompt_version,outcome,error_kind,mode,application_state,"
                "prepared_at,applied_at,promoted_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                (str(value.get("run_id") or "")[:120],
                 str(value.get("item_hash") or "")[:64],
                 str(value.get("model_route") or "advance")[:20], effective,
                 str(value.get("event_summary") or "")[:400],
                 str(value.get("bitcoin_relevance") or "")[:300],
                 str(value.get("freshness_note") or "")[:240],
                 str(value.get("research_objective") or "")[:400], leads, related, storylines,
                 str(value.get("event_group") or "")[:80],
                 str(value.get("companion_anchor_hash") or "")[:64] or None,
                 str(value.get("protection_reason") or "")[:80] or None,
                 str(value.get("model") or "")[:80],
                 str(value.get("prompt_version") or "")[:80],
                 str(value.get("outcome") or "")[:40],
                 str(value.get("error_kind") or "")[:80] or None,
                 mode, state, float(value.get("prepared_at") or now), now),
            )
            inserted += int(bool(cur.rowcount))
            if effective == "advance":
                advanced += 1
            elif mode == "enforce" and effective == "background":
                changed = con.execute(
                    "UPDATE items SET status='skipped',note=?,decision_stage='desk_prep',"
                    "decision_category='background',defer_until=NULL"
                    " WHERE url_hash=? AND status='new'",
                    (("desk prep background: " + str(value.get("event_summary") or
                                                       value.get("bitcoin_relevance") or
                                                       "no NBN development"))[:300],
                     str(value.get("item_hash") or "")[:64]),
                ).rowcount
                suppressed += int(bool(changed))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"inserted": inserted, "advanced": advanced, "suppressed": suppressed,
            "mode": mode}


def latest_desk_preparations(con, item_hashes: list[str]) -> dict[str, dict]:
    """Return the latest preparation for supplied IDs without arbitrary DB enumeration."""
    values = [str(value)[:64] for value in item_hashes if str(value)]
    if not values:
        return {}
    marks = ",".join("?" for _ in values)
    rows = con.execute(
        "SELECT d.* FROM desk_preparations d JOIN ("
        " SELECT item_hash,MAX(prepared_at) prepared_at FROM desk_preparations"
        f" WHERE item_hash IN ({marks}) GROUP BY item_hash"
        ") latest ON latest.item_hash=d.item_hash AND latest.prepared_at=d.prepared_at",
        values,
    ).fetchall()
    result = {}
    for raw in rows:
        row = dict(raw)
        try:
            row["source_leads"] = json.loads(row.pop("source_leads_json") or "[]")
            row["related_keys"] = json.loads(row.pop("related_keys_json") or "[]")
            row["related_storyline_keys"] = json.loads(
                row.pop("related_storyline_keys_json") or "[]"
            )
        except (TypeError, ValueError):
            row["source_leads"], row["related_keys"] = [], []
            row["related_storyline_keys"] = []
        result[row["item_hash"]] = row
    return result


def desk_preparation_summary(con, start: float, end: float) -> dict:
    rows = con.execute(
        "SELECT effective_route,COUNT(*) n,SUM(outcome!='model') failures,"
        "SUM(protection_reason IS NOT NULL) protected FROM desk_preparations"
        " WHERE prepared_at>=? AND prepared_at<? GROUP BY effective_route",
        (float(start), float(end)),
    ).fetchall()
    result = {"advance": 0, "background": 0, "fail_open": 0, "protected": 0,
              "sonnet_wakes_suppressed": 0}
    for row in rows:
        route = str(row["effective_route"] or "")
        if route in result:
            result[route] = int(row["n"] or 0)
        result["fail_open"] += int(row["failures"] or 0)
        result["protected"] += int(row["protected"] or 0)
    suppressed = con.execute(
        "SELECT COUNT(DISTINCT run_id) n FROM desk_preparations d"
        " WHERE prepared_at>=? AND prepared_at<?"
        " AND NOT EXISTS (SELECT 1 FROM desk_preparations x WHERE x.run_id=d.run_id"
        "  AND x.effective_route='advance')",
        (float(start), float(end)),
    ).fetchone()
    result["sonnet_wakes_suppressed"] = int(suppressed["n"] if suppressed else 0)
    return result


def recent_desk_backgrounds(con, start: float, end: float, limit: int = 25) -> list[dict]:
    rows = con.execute(
        "SELECT d.*,i.source,i.title,i.url,i.status,i.decision_stage,i.decision_category"
        " FROM desk_preparations d JOIN items i ON i.url_hash=d.item_hash"
        " WHERE d.prepared_at>=? AND d.prepared_at<? AND d.effective_route='background'"
        " ORDER BY d.prepared_at DESC LIMIT ?",
        (float(start), float(end), max(0, min(int(limit), 100))),
    ).fetchall()
    return [dict(row) for row in rows]


def editorial_run_due(con, now: float | None = None, *, force: bool = False) -> bool:
    """Atomically claim the persisted 15-minute desk slot before calling a model."""
    now = float(now or time.time())
    try:
        due = float(kv_get(con, "editorial:next_run_at") or 0)
    except ValueError:
        due = 0
    if not force and due > now:
        return False
    kv_set(con, "editorial:next_run_at", str(now + config.DESK_INTERVAL_SECONDS))
    return True


def editorial_run_soon(con, now: float | None = None) -> None:
    """Let a remaining backlog drain on the next healthy one-minute worker cycle."""
    kv_set(con, "editorial:next_run_at", str(float(now or time.time())))


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
    if action not in ("stage", "retry", "dismiss", "promote"):
        return {"ok": False, "reason": "unknown action"}
    try:
        con.execute("BEGIN IMMEDIATE")
        item = con.execute(
            "SELECT status,story_key,note,decision_stage,decision_category"
            " FROM items WHERE url_hash=?", (item_hash,)
        ).fetchone()
        if not item:
            con.rollback()
            return {"ok": False, "reason": "item not found"}
        if action == "promote":
            triage = con.execute(
                "SELECT route,promoted_at FROM intake_triage WHERE item_hash=?", (item_hash,)
            ).fetchone()
            preparation = con.execute(
                "SELECT run_id,effective_route,promoted_at FROM desk_preparations"
                " WHERE item_hash=? ORDER BY prepared_at DESC LIMIT 1", (item_hash,)
            ).fetchone()
            active = con.execute(
                "SELECT 1 FROM operator_actions WHERE item_hash=?"
                " AND state IN ('queued','processing') LIMIT 1", (item_hash,),
            ).fetchone()
            intake_ok = bool(
                triage and triage["route"] == "background"
                and triage["promoted_at"] is None
                and item["decision_stage"] == "intake_triage"
            )
            prep_ok = bool(
                preparation and preparation["effective_route"] == "background"
                and preparation["promoted_at"] is None
                and item["decision_stage"] == "desk_prep"
            )
            if (not (intake_ok or prep_ok) or item["status"] != "skipped"
                    or item["decision_category"] != "background" or active):
                con.rollback()
                return {"ok": False, "reason": "item is not an eligible background"}
            now = time.time()
            gate = "intake_triage" if intake_ok else "desk_prep"
            cur = con.execute(
                "INSERT INTO operator_actions(item_hash,story_key,action,gate,requested_at,"
                "completed_at,state,original_status,original_note,result)"
                " VALUES (?,?,?,NULL,?,?,'completed',?,?,?)",
                (item_hash, item["story_key"], "promote", now, now,
                 item["status"], item["note"], "owner sent background to desk"),
            )
            if intake_ok:
                con.execute(
                    "UPDATE intake_triage SET promoted_at=?"
                    " WHERE item_hash=? AND promoted_at IS NULL", (now, item_hash),
                )
            else:
                con.execute(
                    "UPDATE desk_preparations SET promoted_at=?"
                    " WHERE run_id=? AND item_hash=? AND promoted_at IS NULL",
                    (now, preparation["run_id"], item_hash),
                )
            con.execute(
                "UPDATE items SET status='new',note='owner sent background to desk',"
                "defer_until=NULL,decision_stage='operator',decision_category='promoted'"
                " WHERE url_hash=?", (item_hash,),
            )
            con.execute(
                "INSERT INTO kv(k,v) VALUES ('editorial:next_run_at',?)"
                " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(now),),
            )
            con.commit()
            return {"ok": True, "id": cur.lastrowid, "state": "completed",
                    "gate": gate}
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
            con.execute("UPDATE items SET status='new',defer_until=NULL WHERE url_hash=?", (item_hash,))
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
                        started_at: float, theme_snapshot: list | None = None) -> None:
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
            "SELECT mode,storyline_key FROM posts WHERE item_hash=? ORDER BY id DESC LIMIT 1",
            (item_hash,),
        ).fetchone()
        packet = theme_context.parse_discovery_context(candidate.get("discovery_context"))
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
            "output_storyline_key": str(output["storyline_key"] or "")[:120]
            if output else "",
            "newsroom_story_id": str(verdict.get("_newsroom_story_id") or "")[:80],
            "newsroom_reader_value": str(
                verdict.get("_newsroom_reader_value") or "")[:800],
            "newsroom_unresolved": [str(value)[:300] for value in
                                    list(verdict.get("_newsroom_unresolved") or [])[:8]],
            "newsroom_storyline_suggestions": [str(value)[:120] for value in
                                                list(verdict.get(
                                                    "_newsroom_storyline_suggestions"
                                                ) or [])[:2]],
            "theme_ids": packet["theme_ids"],
            "theme_signals": packet["theme_signals"],
        })
    def safe_count(value) -> int:
        if isinstance(value, bool):
            return 0
        try:
            return max(0, min(int(value), 1000))
        except (TypeError, ValueError):
            return 0

    safe_result = dict(result)
    newsroom = result.get("newsroom") if isinstance(result, dict) else None
    if isinstance(newsroom, dict):
        raw_storylines = newsroom.get("storylines") or {}
        safe_storylines = {
            key: safe_count(raw_storylines.get(key, 0))
            for key in ("indexed", "haiku_selected", "initially_supplied", "retrieved")
        } if isinstance(raw_storylines, dict) else {}
        raw_persistence = newsroom.get("storyline_persistence") or {}
        safe_persistence = {
            key: safe_count(raw_persistence.get(key, 0))
            for key in ("created", "updated", "closed", "ignored", "events")
        } if isinstance(raw_persistence, dict) else {}
        if isinstance(raw_persistence, dict) and raw_persistence.get("error"):
            safe_persistence["error"] = str(raw_persistence["error"])[:80]
        if isinstance(raw_persistence, dict):
            safe_persistence["ignored_updates"] = [{
                "storyline_key": str(row.get("storyline_key") or "")[:120],
                "reason": str(row.get("reason") or "")[:160],
            } for row in list(raw_persistence.get("ignored_updates") or [])[:12]
                if isinstance(row, dict)]
        safe_result["newsroom"] = {
            "mode": str(newsroom.get("mode") or "")[:12],
            "status": str(newsroom.get("status") or "")[:24],
            "prompt_version": str(newsroom.get("prompt_version") or "")[:40],
            "error_kind": str(newsroom.get("error_kind") or "")[:80],
            "error": str(newsroom.get("error") or "")[:500],
            **{key: safe_count(newsroom.get(key, 0)) for key in (
                "rounds", "tool_calls", "searches", "search_http_attempts",
                "search_failures", "search_cache_hits", "search_cache_misses",
                "search_provider_skips", "search_pointer_reuse", "fetches", "fetch_chars",
                "duration_seconds", "stories", "successful_newsdesk_calls",
                "newsdesk_retry_used", "prefetch_attempts", "prefetch_successes",
                "prefetch_chars", "context_retrieval_calls", "context_retrieval_bytes",
                "haiku_assignments", "haiku_rounds", "haiku_tool_calls",
                "initial_packet_bytes")},
            "storylines": safe_storylines,
            "storyline_persistence": safe_persistence,
            "search_degraded": bool(newsroom.get("search_degraded")),
            "fetch_failure_kinds": {
                str(key)[:80]: safe_count(value) for key, value in
                dict(newsroom.get("fetch_failure_kinds") or {}).items()
                if safe_count(value) > 0
            },
        }
    for field, allowed in (
        ("resolver_paths", {"direct", "node_ref", "guide_ref", "serpapi", "hosted_web",
                            "run_newsroom", "unknown"}),
        ("resolver_outcomes", {"selected", "support_assessment_timeout", "search_timeout",
                               "source_fetch", "exhausted", "unknown"}),
    ):
        raw = result.get(field) or {}
        safe_result[field] = {
            key: safe_count(raw.get(key, 0))
            for key in sorted(allowed) if safe_count(raw.get(key, 0)) > 0
        } if isinstance(raw, dict) else {}
    payload = {
        "started": started_at,
        "completed": time.time(),
        "result": safe_result,
        "items": decisions,
        "theme_coverage_snapshot": list(theme_snapshot or []),
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
    _ensure_newsroom_columns(con)
    _ensure_model_usage_columns(con)
    _ensure_desk_preparation_columns(con)
    _ensure_search_provider_columns(con)
    return con


def upsert_new_items(con, items) -> list:
    """Insert unseen items; return the newly inserted subset."""
    fresh = []
    for it in items:
        key = canonical_discovery_key(it["url"])
        existing = con.execute(
            "SELECT url_hash,status,discovery_context FROM items"
            " WHERE discovery_key=? ORDER BY first_seen LIMIT 1",
            (key,),
        ).fetchone()
        if existing:
            if existing["status"] == "new":
                merged = guide_context.merge_context(
                    existing["discovery_context"], str(it.get("discovery_context") or "")
                )
                if merged and merged != (existing["discovery_context"] or ""):
                    con.execute(
                        "UPDATE items SET discovery_context=? WHERE url_hash=? AND status='new'",
                        (merged, existing["url_hash"]),
                    )
            continue
        h = url_hash(key or it["url"])
        origin = str(it.get("discovery_origin") or "legacy")[:40]
        context = guide_context.merge_context("", str(it.get("discovery_context") or ""))
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


def intake_triage_work(con, inserted: list[dict], *, recovery_limit: int,
                       recovery_hours: float) -> list[dict]:
    """Return new RSS/EDGAR rows without a mailroom record, newest inserts first."""
    work, seen = [], set()

    def eligible(row: dict) -> bool:
        item_hash = str(row.get("url_hash") or "")
        origin = str(row.get("discovery_origin") or "")
        if not item_hash or origin not in {"rss", "edgar"} or item_hash in seen:
            return False
        if con.execute(
            "SELECT 1 FROM intake_triage WHERE item_hash=?", (item_hash,)
        ).fetchone():
            return False
        if con.execute(
            "SELECT 1 FROM operator_actions WHERE item_hash=?"
            " AND state IN ('queued','processing') LIMIT 1", (item_hash,),
        ).fetchone():
            return False
        return True

    for raw in inserted:
        row = dict(raw)
        if eligible(row):
            seen.add(row["url_hash"])
            work.append(row)

    rows = con.execute(
        "SELECT i.url_hash,i.source,i.title,i.url,i.published_at AS published,"
        " i.summary,i.discovery_origin FROM items i"
        " LEFT JOIN intake_triage t ON t.item_hash=i.url_hash"
        " WHERE i.status='new' AND i.discovery_origin IN ('rss','edgar')"
        " AND i.first_seen>=? AND t.item_hash IS NULL"
        " AND NOT EXISTS (SELECT 1 FROM operator_actions a WHERE a.item_hash=i.url_hash"
        "  AND a.state IN ('queued','processing'))"
        " ORDER BY i.first_seen LIMIT ?",
        (time.time() - max(0.0, float(recovery_hours)) * 3600,
         max(0, int(recovery_limit))),
    ).fetchall()
    for raw in rows:
        row = dict(raw)
        if eligible(row):
            seen.add(row["url_hash"])
            work.append(row)
    return work


def _apply_intake_triage_row(con, row, now: float) -> bool:
    """Apply one persisted route inside the caller's transaction."""
    item_hash = row["item_hash"]
    if row["promoted_at"] is not None:
        con.execute(
            "UPDATE intake_triage SET applied_at=COALESCE(applied_at,?) WHERE item_hash=?",
            (now, item_hash),
        )
        return False
    item = con.execute(
        "SELECT status FROM items WHERE url_hash=?", (item_hash,)
    ).fetchone()
    if not item or item["status"] != "new":
        con.execute(
            "UPDATE intake_triage SET applied_at=COALESCE(applied_at,?) WHERE item_hash=?",
            (now, item_hash),
        )
        return False
    if row["route"] == "background":
        active = con.execute(
            "SELECT 1 FROM operator_actions WHERE item_hash=?"
            " AND state IN ('queued','processing') LIMIT 1", (item_hash,),
        ).fetchone()
        if active:
            return False
        note = ("intake background: " + str(row["reason"] or "no NBN relevance"))[:300]
        con.execute(
            "UPDATE items SET status='skipped',note=?,decision_stage='intake_triage',"
            "decision_category='background' WHERE url_hash=? AND status='new'",
            (note, item_hash),
        )
    elif row["route"] == "priority":
        con.execute(
            "INSERT INTO kv(k,v) VALUES ('editorial:next_run_at',?)"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(now),),
        )
    con.execute(
        "UPDATE intake_triage SET applied_at=COALESCE(applied_at,?) WHERE item_hash=?",
        (now, item_hash),
    )
    return row["route"] == "priority"


def save_intake_triage(con, decisions: list[dict], *, mode: str) -> dict:
    """Persist a batch and atomically apply it when enforcement is enabled."""
    now = time.time()
    inserted = applied = priority_wakes = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        for value in decisions:
            cur = con.execute(
                "INSERT OR IGNORE INTO intake_triage(item_hash,route,category,reason,outcome,"
                "error_kind,origin,source,model,prompt_version,batch_id,triaged_at,applied_at,"
                "promoted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)",
                (str(value["item_hash"])[:64], str(value["route"])[:20],
                 str(value["category"])[:40], str(value["reason"])[:240],
                 str(value["outcome"])[:40], str(value.get("error_kind") or "")[:80] or None,
                 str(value.get("origin") or "")[:40], str(value.get("source") or "")[:120],
                 str(value.get("model") or "")[:80],
                 str(value.get("prompt_version") or "")[:80],
                 str(value.get("batch_id") or "")[:120], float(value.get("triaged_at") or now)),
            )
            if not cur.rowcount:
                continue
            inserted += 1
            if mode == "enforce":
                row = con.execute(
                    "SELECT * FROM intake_triage WHERE item_hash=?", (value["item_hash"],)
                ).fetchone()
                woke = _apply_intake_triage_row(con, row, now)
                refreshed = con.execute(
                    "SELECT applied_at FROM intake_triage WHERE item_hash=?",
                    (value["item_hash"],),
                ).fetchone()
                applied += int(bool(refreshed and refreshed["applied_at"] is not None))
                priority_wakes += int(woke)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"inserted": inserted, "applied": applied, "priority_wakes": priority_wakes}


def reconcile_intake_triage(con, *, limit: int = 250) -> dict:
    """Apply persisted observe/crash rows once when enforcement is active."""
    now = time.time()
    applied = priority_wakes = protected = 0
    try:
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute(
            "SELECT * FROM intake_triage WHERE applied_at IS NULL AND promoted_at IS NULL"
            " ORDER BY triaged_at LIMIT ?", (max(0, int(limit)),),
        ).fetchall()
        for row in rows:
            before = row["applied_at"]
            woke = _apply_intake_triage_row(con, row, now)
            refreshed = con.execute(
                "SELECT applied_at FROM intake_triage WHERE item_hash=?", (row["item_hash"],)
            ).fetchone()
            if refreshed and refreshed["applied_at"] is not None and before is None:
                applied += 1
            else:
                protected += 1
            priority_wakes += int(woke)
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {"seen": len(rows), "applied": applied, "protected": protected,
            "priority_wakes": priority_wakes}


def intake_triage_summary(con, start: float, end: float) -> dict:
    counts = {"priority": 0, "candidate": 0, "background": 0, "promoted": 0,
              "fail_open": 0}
    rows = con.execute(
        "SELECT route,COUNT(*) n,SUM(promoted_at IS NOT NULL) promoted,"
        "SUM(outcome!='model') fail_open FROM intake_triage"
        " WHERE triaged_at>=? AND triaged_at<? GROUP BY route", (start, end),
    ).fetchall()
    for row in rows:
        if row["route"] in counts:
            counts[row["route"]] = int(row["n"] or 0)
        counts["promoted"] += int(row["promoted"] or 0)
        counts["fail_open"] += int(row["fail_open"] or 0)
    return counts


def intake_triage_source_summary(con, start: float, end: float, limit: int = 12) -> list[dict]:
    return [dict(row) for row in con.execute(
        "SELECT source,route,COUNT(*) n FROM intake_triage"
        " WHERE triaged_at>=? AND triaged_at<? GROUP BY source,route"
        " ORDER BY n DESC,source,route LIMIT ?", (start, end, max(0, int(limit))),
    ).fetchall()]


def intake_triage_background(con, start: float, end: float, limit: int = 25) -> list[dict]:
    return [dict(row) for row in con.execute(
        "SELECT t.*,i.title,i.url,i.status,i.decision_stage,i.decision_category"
        " FROM intake_triage t JOIN items i ON i.url_hash=t.item_hash"
        " WHERE t.route='background' AND t.triaged_at>=? AND t.triaged_at<?"
        " ORDER BY t.triaged_at DESC LIMIT ?", (start, end, max(0, int(limit))),
    ).fetchall()]


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
                "SELECT url_hash,status,discovery_context FROM items"
                " WHERE discovery_key=? ORDER BY first_seen LIMIT 1",
                (key,),
            ).fetchone()
            if existing:
                deduped += 1
                context_value = guide_context.merge_context(
                    existing["discovery_context"], str(it.get("discovery_context") or "")
                )
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
                 guide_context.merge_context("", str(it.get("discovery_context") or "")),
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


_NEWSROOM_STATES = {
    "surveying", "researching", "validated", "materializing", "completed", "fallback",
    "deferred",
}


def start_newsroom_run(con, run_id: str, mode: str, model: str, prompt_version: str,
                       inventory_hashes: list[str]) -> str:
    """Persist only the immutable inventory identity before the read-only model session."""
    ordered = [str(value)[:64] for value in inventory_hashes]
    encoded = json.dumps(ordered, separators=(",", ":"))
    fingerprint = hashlib.sha256(encoded.encode()).hexdigest()
    now = time.time()
    con.execute(
        "INSERT OR REPLACE INTO newsroom_runs(run_id,status,mode,model,prompt_version,"
        "inventory_fingerprint,inventory_json,counters_json,created_at,updated_at)"
        " VALUES (?,?,?,?,?,?,?,'{}',?,?)",
        (run_id, "surveying", mode[:12], model[:80], prompt_version[:40], fingerprint,
         encoded, now, now),
    )
    con.commit()
    return fingerprint


def checkpoint_newsroom_survey(con, run_id: str, survey: dict, counters: dict) -> None:
    encoded = json.dumps(survey, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode()) > 24576:
        raise ValueError("newsroom survey exceeds checkpoint bound")
    con.execute(
        "UPDATE newsroom_runs SET status='researching',survey_json=?,counters_json=?,"
        "updated_at=? WHERE run_id=? AND status='surveying'",
        (encoded, json.dumps(counters, separators=(",", ":"))[:4000], time.time(), run_id),
    )
    con.commit()


def validate_newsroom_run(con, run_id: str, dossier: dict, digest: str,
                          counters: dict) -> None:
    encoded = json.dumps(dossier, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode()) > 98304:
        raise ValueError("newsroom dossier exceeds checkpoint bound")
    cur = con.execute(
        "UPDATE newsroom_runs SET status='validated',dossier_json=?,dossier_digest=?,"
        "counters_json=?,updated_at=? WHERE run_id=? AND status IN ('surveying','researching')",
        (encoded, digest[:64], json.dumps(counters, separators=(",", ":"))[:4000],
         time.time(), run_id),
    )
    if cur.rowcount != 1:
        raise RuntimeError("newsroom run cannot transition to validated")
    con.commit()


def set_newsroom_state(con, run_id: str, status: str, *, error_kind: str = "",
                       error_message: str = "", counters: dict | None = None) -> None:
    if status not in _NEWSROOM_STATES:
        raise ValueError("invalid newsroom state")
    completed = time.time() if status in {"completed", "fallback", "deferred"} else None
    con.execute(
        "UPDATE newsroom_runs SET status=?,error_kind=?,error_message=?,"
        "counters_json=COALESCE(?,counters_json),updated_at=?,completed_at=? WHERE run_id=?",
        (status, str(error_kind or "")[:80], str(error_message or "")[:500],
         json.dumps(counters, separators=(",", ":"))[:4000] if counters is not None else None,
         time.time(), completed, run_id),
    )
    con.commit()


_NEWSROOM_STORY_STATES = {"pending", "materialized", "delivered", "held", "observed"}
_NEWSROOM_COMMIT_DETAILS_MAX_BYTES = 12 * 1024


def _bounded_commit_details(value: dict | None) -> str:
    payload = value if isinstance(value, dict) else {}
    encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) <= _NEWSROOM_COMMIT_DETAILS_MAX_BYTES:
        return encoded
    fallback = {
        "validation": str(payload.get("validation") or "")[:80],
        "reason": _utf8_prefix(payload.get("reason"), 1000),
        "warnings": [str(v)[:300] for v in list(payload.get("warnings") or [])[:8]],
        "editor": {
            "verdict": str((payload.get("editor") or {}).get("verdict") or "")[:40],
            "reason": _utf8_prefix((payload.get("editor") or {}).get("reason"), 1000),
        } if isinstance(payload.get("editor"), dict) else None,
        "delivery": payload.get("delivery") if isinstance(payload.get("delivery"), dict) else None,
    }
    encoded = json.dumps(fallback, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) <= _NEWSROOM_COMMIT_DETAILS_MAX_BYTES:
        return encoded
    # Never byte-slice serialized JSON: diagnostics must remain parseable even when an
    # upstream model returns pathologically large metadata.
    return json.dumps({
        "validation": fallback["validation"],
        "reason": _utf8_prefix(fallback["reason"], 500),
        "details_truncated": True,
    }, separators=(",", ":"), ensure_ascii=False)


def init_newsroom_story_commits(con, run_id: str, stories: list, digest: str) -> None:
    now = time.time()
    for raw in stories:
        if isinstance(raw, dict):
            story_id = str(raw.get("story_id") or "")[:80]
            state = str(raw.get("state") or "pending")
            details = _bounded_commit_details(raw.get("details"))
        else:
            story_id, state, details = str(raw or "")[:80], "pending", "{}"
        if not story_id:
            continue
        if state not in _NEWSROOM_STORY_STATES:
            raise ValueError("invalid newsroom story state")
        con.execute(
            "INSERT OR IGNORE INTO newsroom_story_commits(run_id,story_id,state,"
            "dossier_digest,details_json,updated_at) VALUES (?,?,?,?,?,?)",
            (run_id, story_id, state, digest[:64], details, now),
        )
    con.commit()


def set_newsroom_story_state(con, run_id: str, story_id: str, state: str,
                             delivery_ref: str = "", details: dict | None = None) -> None:
    if state not in _NEWSROOM_STORY_STATES:
        raise ValueError("invalid newsroom story state")
    row = con.execute(
        "SELECT details_json FROM newsroom_story_commits WHERE run_id=? AND story_id=?",
        (run_id, story_id),
    ).fetchone()
    current = _safe_json_object(row["details_json"]) if row else {}
    if isinstance(details, dict):
        current.update(details)
    con.execute(
        "UPDATE newsroom_story_commits SET state=?,delivery_ref=?,details_json=?,updated_at=?"
        " WHERE run_id=? AND story_id=?",
        (state, str(delivery_ref or "")[:200], _bounded_commit_details(current),
         time.time(), run_id, story_id),
    )
    con.commit()


def latest_newsroom_run(con):
    return con.execute(
        "SELECT * FROM newsroom_runs ORDER BY created_at DESC LIMIT 1"
    ).fetchone()


def prune_newsroom_runs(con, days: float = 14.0) -> None:
    cutoff = time.time() - max(1.0, days) * 86400
    con.execute(
        "UPDATE newsroom_runs SET inventory_json='[]',survey_json=NULL,dossier_json=NULL"
        " WHERE status IN ('completed','fallback','deferred') AND created_at<?",
        (cutoff,),
    )
    con.commit()


_STORY_MEMORY_STATES = {"research_pending", "editor_feedback", "delivered", "dropped"}
_STORY_MEMORY_TTL_SECONDS = 72 * 3600
_STORY_MEMORY_ATTEMPT_MAX_BYTES = 18 * 1024
_STORY_MEMORY_EVIDENCE_POOL_MAX_BYTES = 70 * 1024
_STORY_MEMORY_ROW_MAX_BYTES = 96 * 1024
_STORY_MEMORY_MAX_ATTEMPTS = 12
_STORY_MEMORY_MAX_EVIDENCE = 8


def _utf8_prefix(value, max_bytes: int) -> str:
    encoded = str(value or "").encode("utf-8")[:max(0, int(max_bytes))]
    return encoded.decode("utf-8", errors="ignore")


def _bounded_memory_attempt(raw: dict) -> dict:
    """Normalize one workbench attempt before it reaches durable state."""
    evidence = []
    for card in list(raw.get("evidence") or [])[:8]:
        if not isinstance(card, dict):
            continue
        evidence.append({
            "inspected_at": round(float(card.get("inspected_at") or time.time()), 3),
            "requested_url": str(card.get("requested_url") or "")[:2000],
            "final_url": str(card.get("final_url") or "")[:2000],
            "canonical_url": str(card.get("canonical_url") or "")[:2000],
            "source_label": str(card.get("source_label") or "")[:160],
            "byline": str(card.get("byline") or "")[:200],
            "content_fingerprint": str(card.get("content_fingerprint") or "")[:400],
            "text": _utf8_prefix(card.get("text"), 8192),
        })
    return {
        "at": round(float(raw.get("at") or time.time()), 3),
        "story_id": str(raw.get("story_id") or "")[:80],
        "members": [str(value)[:64] for value in list(raw.get("members") or [])[:25]],
        "headlines": [str(value)[:300] for value in list(raw.get("headlines") or [])[:3]],
        "submitted_story_key": str(raw.get("submitted_story_key") or "")[:180],
        "existing_cluster_key": str(raw.get("existing_cluster_key") or "")[:180],
        "coverage_relation": str(raw.get("coverage_relation") or "")[:30],
        "proposed_post": _utf8_prefix(raw.get("proposed_post"), 8192),
        "failure": str(raw.get("failure") or "")[:500],
        "objective": str(raw.get("objective") or "")[:500],
        "evidence": evidence,
    }


def _compact_memory_attempts(attempts: list[dict]) -> str:
    """Keep recent editorial history; full evidence text lives in the shared pool."""
    rows = [_bounded_memory_attempt(row) for row in attempts if isinstance(row, dict)]
    rows = rows[-_STORY_MEMORY_MAX_ATTEMPTS:]
    for row in rows:
        for evidence in row["evidence"]:
            evidence["text"] = ""

    def encoded() -> str:
        return json.dumps(rows, separators=(",", ":"), ensure_ascii=False)

    value = encoded()
    while rows and len(value.encode("utf-8")) > _STORY_MEMORY_ATTEMPT_MAX_BYTES:
        rows.pop(0)
        value = encoded()
    return value if len(value.encode("utf-8")) <= _STORY_MEMORY_ATTEMPT_MAX_BYTES else "[]"


def _bounded_memory_evidence(raw: dict) -> dict:
    return {
        "inspected_at": round(float(raw.get("inspected_at") or time.time()), 3),
        "requested_url": str(raw.get("requested_url") or "")[:2000],
        "final_url": str(raw.get("final_url") or "")[:2000],
        "canonical_url": str(raw.get("canonical_url") or raw.get("final_url") or "")[:2000],
        "source_label": str(raw.get("source_label") or "")[:160],
        "byline": str(raw.get("byline") or "")[:200],
        "content_fingerprint": str(raw.get("content_fingerprint") or "")[:400],
        "text": _utf8_prefix(raw.get("text"), 8192),
    }


def _merge_memory_evidence(*groups: list[dict]) -> str:
    """Merge newest evidence without allowing mirrors to create fake independence."""
    rows = []
    for group in groups:
        rows.extend(_bounded_memory_evidence(raw) for raw in group if isinstance(raw, dict))
    rows.sort(key=lambda row: float(row.get("inspected_at") or 0), reverse=True)
    kept = []
    seen_urls: set[str] = set()
    seen_fingerprints: set[str] = set()
    for row in rows:
        url = source_policy.normalize_url(row.get("canonical_url") or row.get("final_url") or "")
        fingerprint = str(row.get("content_fingerprint") or "")
        if not row.get("text") or not url or url in seen_urls:
            continue
        if fingerprint and fingerprint in seen_fingerprints:
            continue
        row["canonical_url"] = url
        seen_urls.add(url)
        if fingerprint:
            seen_fingerprints.add(fingerprint)
        kept.append(row)
        if len(kept) >= _STORY_MEMORY_MAX_EVIDENCE:
            break

    def encoded() -> str:
        return json.dumps(kept, separators=(",", ":"), ensure_ascii=False)

    value = encoded()
    # Preserve provenance cards and newest evidence longest; trim older bodies first.
    for limit in (4096, 2048, 1024, 0):
        if len(value.encode("utf-8")) <= _STORY_MEMORY_EVIDENCE_POOL_MAX_BYTES:
            break
        for row in reversed(kept[1:]):
            row["text"] = _utf8_prefix(row.get("text"), limit)
        value = encoded()
    while kept and len(value.encode("utf-8")) > _STORY_MEMORY_EVIDENCE_POOL_MAX_BYTES:
        kept.pop()
        value = encoded()
    return value if len(value.encode("utf-8")) <= _STORY_MEMORY_EVIDENCE_POOL_MAX_BYTES else "[]"


def _safe_json_object(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _safe_json_array(value: str) -> list:
    try:
        parsed = json.loads(value or "[]")
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _story_memory_size(key: str, state: str, attempts: str, evidence: str,
                       editor: str, delivery: str) -> int:
    return sum(len(str(value or "").encode("utf-8")) for value in (
        key, state, attempts, evidence, editor, delivery,
    ))


def _fit_story_memory_row(key: str, state: str, attempts_json: str,
                          evidence_json: str, editor_json: str,
                          delivery_json: str) -> tuple[str, str, str, str]:
    """Enforce the total durable-workbench ceiling without corrupting JSON.

    Attempt history is compacted before reusable evidence. If exceptional URL metadata
    still makes the row too large, older evidence bodies are shortened before cards are
    removed. The newest valid receipt is the last thing sacrificed.
    """
    attempts = _safe_json_array(attempts_json)
    evidence = _safe_json_array(evidence_json)
    editor = _safe_json_object(editor_json)
    delivery = _safe_json_object(delivery_json)

    def encode(value) -> str:
        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    def values() -> tuple[str, str, str, str]:
        return encode(attempts), encode(evidence), encode(editor), encode(delivery)

    def too_large() -> bool:
        current = values()
        return _story_memory_size(key, state, *current) > _STORY_MEMORY_ROW_MAX_BYTES

    while len(attempts) > 1 and too_large():
        attempts.pop(0)
    if too_large() and attempts:
        latest = attempts[-1]
        attempts[:] = [{
            "at": latest.get("at"), "story_id": latest.get("story_id", ""),
            "members": list(latest.get("members") or [])[:25],
            "submitted_story_key": latest.get("submitted_story_key", ""),
            "existing_cluster_key": latest.get("existing_cluster_key", ""),
            "coverage_relation": latest.get("coverage_relation", ""),
            "proposed_post": _utf8_prefix(latest.get("proposed_post"), 2048),
            "failure": str(latest.get("failure") or "")[:500],
            "objective": str(latest.get("objective") or "")[:500],
            "evidence": list(latest.get("evidence") or [])[:8],
        }]
    if too_large() and editor.get("post"):
        editor["post"] = _utf8_prefix(editor.get("post"), 2048)
        editor["post_truncated"] = True
    for limit in (2048, 1024, 0):
        if not too_large():
            break
        for row in reversed(evidence[1:]):
            if isinstance(row, dict):
                row["text"] = _utf8_prefix(row.get("text"), limit)
    while len(evidence) > 1 and too_large():
        evidence.pop()
    if too_large() and evidence and isinstance(evidence[0], dict):
        evidence[0]["text"] = _utf8_prefix(evidence[0].get("text"), 2048)
        evidence[0]["text_truncated_for_row_bound"] = True
    if too_large() and attempts:
        latest = attempts[-1]
        attempts[:] = [{
            "at": latest.get("at"), "story_id": latest.get("story_id", ""),
            "failure": latest.get("failure", ""),
            "objective": _utf8_prefix(latest.get("objective"), 300),
            "evidence": [], "details_truncated_for_row_bound": True,
        }]
    # The field-level bounds above make this final branch extraordinarily defensive.
    # Keep valid JSON and provenance rather than ever writing an oversized/corrupt row.
    if too_large():
        evidence = []
    return values()


def _enforce_story_memory_row_bound(con, canonical_key: str) -> None:
    row = con.execute(
        "SELECT canonical_key,state,attempts_json,evidence_pool_json,editor_json,delivery_json"
        " FROM newsroom_story_memory WHERE canonical_key=?",
        (canonical_key,),
    ).fetchone()
    if not row:
        return
    fields = _fit_story_memory_row(
        row["canonical_key"], row["state"], row["attempts_json"],
        row["evidence_pool_json"], row["editor_json"], row["delivery_json"],
    )
    con.execute(
        "UPDATE newsroom_story_memory SET attempts_json=?,evidence_pool_json=?,"
        "editor_json=?,delivery_json=? WHERE canonical_key=?",
        (*fields, canonical_key),
    )


def save_newsroom_story_attempt(con, canonical_key: str, state: str, attempt: dict,
                                *, now: float | None = None) -> None:
    """Append one bounded editorial attempt to an informational story workbench."""
    if state not in _STORY_MEMORY_STATES:
        raise ValueError("invalid newsroom story memory state")
    key = canonical_story_key(con, str(canonical_key or "")[:180])
    if not key:
        return
    current = con.execute(
        "SELECT attempts_json,evidence_pool_json,created_at FROM newsroom_story_memory"
        " WHERE canonical_key=?",
        (key,),
    ).fetchone()
    attempts = _safe_json_array(current["attempts_json"]) if current else []
    pool = _safe_json_array(current["evidence_pool_json"]) if current else []
    if not pool:
        pool = [
            evidence for prior in reversed(attempts) if isinstance(prior, dict)
            for evidence in list(prior.get("evidence") or []) if isinstance(evidence, dict)
        ]
    evidence_pool = _merge_memory_evidence(pool, list(attempt.get("evidence") or []))
    attempts.append(attempt)
    stamp = float(now if now is not None else time.time())
    con.execute(
        "INSERT INTO newsroom_story_memory(canonical_key,state,attempts_json,evidence_pool_json,"
        "editor_json,delivery_json,created_at,updated_at,expires_at)"
        " VALUES (?,?,?,?,'{}','{}',?,?,?)"
        " ON CONFLICT(canonical_key) DO UPDATE SET state=excluded.state,"
        "attempts_json=excluded.attempts_json,evidence_pool_json=excluded.evidence_pool_json,"
        "updated_at=excluded.updated_at,"
        "expires_at=excluded.expires_at",
        (key, state, _compact_memory_attempts(attempts), evidence_pool,
         float(current["created_at"]) if current else stamp, stamp,
         stamp + _STORY_MEMORY_TTL_SECONDS),
    )
    _enforce_story_memory_row_bound(con, key)
    con.commit()


def save_newsroom_editor_feedback(con, canonical_key: str, *, verdict: str, reason: str,
                                  post: str | None, now: float | None = None) -> None:
    """Attach the independent editor's bounded decision without making it a gate."""
    key = canonical_story_key(con, str(canonical_key or "")[:180])
    if not key:
        return
    stamp = float(now if now is not None else time.time())
    payload = json.dumps({
        "at": round(stamp, 3), "verdict": str(verdict or "")[:40],
        "reason": str(reason or "")[:500], "post": _utf8_prefix(post, 8192),
    }, separators=(",", ":"), ensure_ascii=False)
    state = "dropped" if verdict == "drop" else "editor_feedback"
    con.execute(
        "UPDATE newsroom_story_memory SET state=?,editor_json=?,updated_at=?,expires_at=?"
        " WHERE canonical_key=?",
        (state, payload, stamp, stamp + _STORY_MEMORY_TTL_SECONDS, key),
    )
    _enforce_story_memory_row_bound(con, key)
    con.commit()


_STORYLINE_KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+){0,15}$")
_STORYLINE_LIFECYCLES = {"open", "closed"}
_STORYLINE_RELATIONSHIPS = {
    "new_storyline", "continuing", "turn", "routine_signal", "closing",
}
_STORYLINE_DISPOSITIONS = {"publish", "drop", "defer"}


def valid_storyline_key(value: str) -> bool:
    key = str(value or "")
    return bool(len(key) <= 120 and _STORYLINE_KEY_RE.fullmatch(key))


def _storyline_watch_for(value) -> list[str]:
    if not isinstance(value, list) or len(value) > 3:
        return []
    return [str(row).strip()[:240] for row in value if str(row).strip()][:3]


def newsroom_storyline_index(con, *, limit: int = 80,
                             now: float | None = None) -> list[dict]:
    """Compact advisory index for Haiku; prose is never evidence."""
    stamp = float(now if now is not None else time.time())
    rows = con.execute(
        "SELECT * FROM newsroom_storylines WHERE lifecycle='open' OR updated_at>=?"
        " ORDER BY CASE lifecycle WHEN 'open' THEN 0 ELSE 1 END,updated_at DESC LIMIT ?",
        (stamp - 30 * 86400, max(0, min(int(limit), 80))),
    ).fetchall()
    out = []
    for raw in rows:
        row = dict(raw)
        if not valid_storyline_key(row.get("storyline_key")):
            continue
        events = con.execute(
            "SELECT canonical_event_key FROM newsroom_storyline_events"
            " WHERE storyline_key=? ORDER BY observed_at DESC,id DESC LIMIT 1",
            (row["storyline_key"],),
        ).fetchone()
        output = con.execute(
            "SELECT mode,body FROM posts WHERE storyline_key=?"
            " AND mode IN ('DRAFT','IMMEDIATE','UNCERTAIN')"
            " AND NOT (mode='DRAFT' AND COALESCE(publisher_status,'') IN ('deleted','inactive'))"
            " ORDER BY created DESC,id DESC LIMIT 1",
            (row["storyline_key"],),
        ).fetchone()
        out.append({
            "storyline_key": row["storyline_key"],
            "title": str(row.get("title") or "")[:160],
            "summary_excerpt": str(row.get("summary") or "")[:300],
            "lifecycle": row.get("lifecycle"),
            "revision": int(row.get("revision") or 1),
            "hours_since_signal": round(max(0, stamp - float(
                row.get("last_signal_at") or stamp)) / 3600, 1),
            "last_exact_event_key": str(events["canonical_event_key"] or "")[:180]
            if events else "",
            "open_draft": bool(output and output["mode"] == "DRAFT"),
            "reader_covered": bool(output and output["mode"] in {"IMMEDIATE", "UNCERTAIN"}),
        })
        if len(json.dumps(out, separators=(",", ":"), ensure_ascii=False).encode()) > 24 * 1024:
            out.pop()
            break
    return out


def newsroom_storyline_cards(con, keys: list[str], *, events_limit: int = 8) -> list[dict]:
    """Return full cards only for explicitly selected keys."""
    out = []
    for key in list(dict.fromkeys(str(value) for value in keys))[:24]:
        if not valid_storyline_key(key):
            continue
        raw = con.execute(
            "SELECT * FROM newsroom_storylines WHERE storyline_key=?", (key,)
        ).fetchone()
        if not raw:
            continue
        row = dict(raw)
        events = [dict(event) for event in con.execute(
            "SELECT e.storyline_key,e.item_hash,e.canonical_event_key,e.run_id,e.disposition,"
            "e.relationship,e.observed_at,i.title FROM newsroom_storyline_events e"
            " LEFT JOIN items i ON i.url_hash=e.item_hash WHERE e.storyline_key=?"
            " ORDER BY e.observed_at DESC,e.id DESC LIMIT ?",
            (key, max(1, min(int(events_limit), 8))),
        ).fetchall()]
        output = con.execute(
            "SELECT mode,body,created FROM posts WHERE storyline_key=?"
            " AND mode IN ('DRAFT','IMMEDIATE','UNCERTAIN')"
            " AND NOT (mode='DRAFT' AND COALESCE(publisher_status,'') IN ('deleted','inactive'))"
            " ORDER BY created DESC,id DESC LIMIT 1", (key,),
        ).fetchone()
        out.append({
            "storyline_key": key, "revision": int(row.get("revision") or 1),
            "title": str(row.get("title") or "")[:160],
            "state_summary": str(row.get("summary") or "")[:800],
            "lifecycle": row.get("lifecycle"),
            "watch_for": _storyline_watch_for(_safe_json_array(row.get("watch_for_json"))),
            "update_reason": str(row.get("update_reason") or "")[:400],
            "updated_at_epoch": float(row.get("updated_at") or 0),
            "last_signal_at_epoch": float(row.get("last_signal_at") or 0),
            "recent_events": [{
                "candidate_id": event.get("item_hash"),
                "exact_event_key": str(event.get("canonical_event_key") or "")[:180],
                "run_id": str(event.get("run_id") or "")[:120],
                "disposition": event.get("disposition"),
                "relationship": event.get("relationship"),
                "observed_at_epoch": float(event.get("observed_at") or 0),
                "headline": str(event.get("title") or "")[:300],
            } for event in events],
            "output_state": {
                "open_draft": bool(output and output["mode"] == "DRAFT"),
                "reader_covered": bool(output and output["mode"] in {"IMMEDIATE", "UNCERTAIN"}),
                "latest_output_lede": str(output["body"] or "").split("\n", 1)[0][:400]
                if output else "",
            },
            "status": "untrusted_editorial_memory_not_evidence",
        })
    return out


def apply_newsroom_storyline_updates(con, *, run_id: str, updates: list[dict],
                                     allowed_existing_keys: set[str]) -> dict:
    """Apply bounded advisory memory independently of publication materialization."""
    accepted: set[str] = set()
    ignored: list[dict] = []
    counts = {"created": 0, "updated": 0, "closed": 0, "ignored": 0,
              "events": 0}
    new_count = 0
    membership_count = 0
    used_members: set[str] = set()

    def reject(key: str, reason: str) -> None:
        counts["ignored"] += 1
        ignored.append({"storyline_key": str(key)[:120], "reason": reason[:160]})

    try:
        con.execute("BEGIN IMMEDIATE")
        for raw in list(updates or [])[:12]:
            if not isinstance(raw, dict):
                reject("", "invalid_update")
                continue
            key = str(raw.get("storyline_key") or "")
            if not valid_storyline_key(key):
                reject(key, "invalid_key")
                continue
            title = str(raw.get("title") or "").strip()[:160]
            summary = str(raw.get("state_summary") or "").strip()[:800]
            lifecycle = str(raw.get("lifecycle") or "")
            relationship = str(raw.get("relationship") or "")
            members = list(dict.fromkeys(
                str(value)[:64] for value in list(raw.get("candidate_ids") or []) if str(value)
            ))[:25]
            watch_for = _storyline_watch_for(raw.get("watch_for"))
            if (not title or not summary or lifecycle not in _STORYLINE_LIFECYCLES
                    or relationship not in _STORYLINE_RELATIONSHIPS or not members):
                reject(key, "invalid_fields")
                continue
            if membership_count + len(members) > 25 or used_members.intersection(members):
                reject(key, "candidate_membership_conflict")
                continue
            item_rows = con.execute(
                f"SELECT url_hash,story_key,first_seen FROM items WHERE url_hash IN "
                f"({','.join('?' for _ in members)})", members,
            ).fetchall()
            if len(item_rows) != len(members):
                reject(key, "unknown_candidate")
                continue
            existing = con.execute(
                "SELECT revision,created_at,last_signal_at FROM newsroom_storylines"
                " WHERE storyline_key=?", (key,),
            ).fetchone()
            signal_at = max(float(row["first_seen"] or 0) for row in item_rows)
            reason = str(raw.get("update_reason") or "")[:400]
            prior_same_run = con.execute(
                f"SELECT COUNT(DISTINCT item_hash) n FROM newsroom_storyline_events"
                f" WHERE storyline_key=? AND run_id=? AND item_hash IN "
                f"({','.join('?' for _ in members)})",
                (key, str(run_id)[:120], *members),
            ).fetchone()
            if existing and int(prior_same_run["n"] or 0) == len(members):
                accepted.add(key)
                continue
            if existing:
                if key not in allowed_existing_keys:
                    reject(key, "storyline_not_read")
                    continue
                try:
                    base_revision = int(raw.get("base_revision"))
                except (TypeError, ValueError):
                    reject(key, "missing_base_revision")
                    continue
                cur = con.execute(
                    "UPDATE newsroom_storylines SET title=?,summary=?,lifecycle=?,watch_for_json=?,"
                    "update_reason=?,updated_at=?,last_signal_at=MAX(last_signal_at,?),"
                    "revision=revision+1 WHERE storyline_key=? AND revision=?",
                    (title, summary, lifecycle, json.dumps(watch_for, separators=(",", ":"),
                     ensure_ascii=False), reason, time.time(), signal_at, key, base_revision),
                )
                if cur.rowcount != 1:
                    reject(key, "stale_revision")
                    continue
                counts["updated"] += 1
            else:
                if relationship != "new_storyline":
                    reject(key, "new_key_requires_new_storyline")
                    continue
                if new_count >= 3:
                    reject(key, "new_storyline_cap")
                    continue
                stamp = time.time()
                try:
                    con.execute(
                        "INSERT INTO newsroom_storylines(storyline_key,title,summary,lifecycle,"
                        "watch_for_json,update_reason,created_at,updated_at,last_signal_at,revision)"
                        " VALUES (?,?,?,?,?,?,?,?,?,1)",
                        (key, title, summary, lifecycle, json.dumps(watch_for,
                         separators=(",", ":"), ensure_ascii=False), reason, stamp, stamp,
                         signal_at),
                    )
                except sqlite3.IntegrityError:
                    reject(key, "concurrent_create")
                    continue
                new_count += 1
                counts["created"] += 1
            if lifecycle == "closed":
                counts["closed"] += 1
            accepted.add(key)
            membership_count += len(members)
            used_members.update(members)
            dispositions = raw.get("candidate_dispositions") or {}
            event_keys = raw.get("candidate_event_keys") or {}
            for item in item_rows:
                disposition = str(dispositions.get(item["url_hash"]) or "drop")
                if disposition not in _STORYLINE_DISPOSITIONS:
                    disposition = "drop"
                canonical = canonical_story_key(
                    con, str(event_keys.get(item["url_hash"]) or item["story_key"] or "")[:180]
                )
                cur = con.execute(
                    "INSERT OR IGNORE INTO newsroom_storyline_events(storyline_key,item_hash,"
                    "canonical_event_key,run_id,disposition,relationship,observed_at,created_at)"
                    " VALUES (?,?,?,?,?,?,?,?)",
                    (key, item["url_hash"], canonical or None, str(run_id)[:120], disposition,
                     relationship, float(item["first_seen"] or signal_at), time.time()),
                )
                counts["events"] += int(bool(cur.rowcount))
        con.commit()
    except Exception:
        con.rollback()
        raise
    return {
        "accepted_keys": sorted(accepted),
        "ignored_updates": ignored,
        **counts,
    }


def save_newsroom_delivery(con, canonical_key: str, *, mode: str, backend_ref: str = "",
                           delivered_at: float | None = None) -> None:
    """Record the actual publisher lifecycle; a DRAFT is not reader-covered."""
    key = canonical_story_key(con, str(canonical_key or "")[:180])
    if not key:
        return
    stamp = float(delivered_at if delivered_at is not None else time.time())
    payload = json.dumps({
        "at": round(stamp, 3), "mode": str(mode or "")[:40],
        "backend_ref": str(backend_ref or "")[:300],
        "reader_covered": mode in {"IMMEDIATE", "UNCERTAIN"},
    }, separators=(",", ":"), ensure_ascii=False)
    con.execute(
        "UPDATE newsroom_story_memory SET state='delivered',delivery_json=?,updated_at=?,"
        "expires_at=? WHERE canonical_key=?",
        (payload, stamp, stamp + _STORY_MEMORY_TTL_SECONDS, key),
    )
    _enforce_story_memory_row_bound(con, key)
    con.commit()


def newsroom_story_memories(con, *, limit: int = 12, now: float | None = None) -> list[dict]:
    """Return recent bounded workbenches; corrupt/expired state fails open."""
    stamp = float(now if now is not None else time.time())
    rows = con.execute(
        "SELECT * FROM newsroom_story_memory WHERE expires_at>?"
        " ORDER BY CASE state WHEN 'research_pending' THEN 0 WHEN 'editor_feedback' THEN 1"
        " ELSE 2 END,updated_at DESC LIMIT ?",
        (stamp, max(0, min(int(limit), 12))),
    ).fetchall()
    out = []
    for row in rows:
        if sum(len(str(row[field] or "").encode("utf-8")) for field in (
            "canonical_key", "state", "attempts_json", "evidence_pool_json",
            "editor_json", "delivery_json"
        )) > _STORY_MEMORY_ROW_MAX_BYTES:
            continue
        attempts = _safe_json_array(row["attempts_json"])
        if not attempts:
            continue
        pool = _safe_json_array(row["evidence_pool_json"])
        if not pool:
            # Lazy additive migration: seed old rows from every surviving attempt,
            # newest-first, while preserving original inspection timestamps.
            seeded = [
                evidence for prior in reversed(attempts) if isinstance(prior, dict)
                for evidence in list(prior.get("evidence") or []) if isinstance(evidence, dict)
            ]
            encoded = _merge_memory_evidence(seeded)
            pool = _safe_json_array(encoded)
            if pool:
                con.execute(
                    "UPDATE newsroom_story_memory SET evidence_pool_json=? WHERE canonical_key=?",
                    (encoded, row["canonical_key"]),
                )
        out.append({
            "canonical_key": row["canonical_key"], "state": row["state"],
            "attempts": attempts[-_STORY_MEMORY_MAX_ATTEMPTS:],
            "evidence_pool": pool[:_STORY_MEMORY_MAX_EVIDENCE],
            "editor": _safe_json_object(row["editor_json"]),
            "delivery": _safe_json_object(row["delivery_json"]),
            "created_at": float(row["created_at"]), "updated_at": float(row["updated_at"]),
            "expires_at": float(row["expires_at"]),
        })
    con.commit()
    return out


def prune_newsroom_story_memory(con, *, now: float | None = None) -> int:
    stamp = float(now if now is not None else time.time())
    cur = con.execute("DELETE FROM newsroom_story_memory WHERE expires_at<=?", (stamp,))
    con.commit()
    return int(cur.rowcount)


def recover_incomplete_newsroom_runs(con) -> dict:
    """Close interrupted runs without risking duplicate delivery.

    Survey/research/validated runs have not crossed the materialization boundary, so their
    untouched items remain available to a later cycle. Once materialization began, any
    story without a durable terminal item state is held for operator inspection. A post
    already recorded locally is treated as delivered; an unknown create outcome is never
    retried automatically.
    """
    rows = con.execute(
        "SELECT * FROM newsroom_runs WHERE status IN "
        "('surveying','researching','validated','materializing') ORDER BY created_at"
    ).fetchall()
    summary = {"runs": len(rows), "pre_materialization": 0,
               "materializing": 0, "items_held": 0, "stories_delivered": 0}
    if not rows:
        return summary
    now = time.time()
    try:
        con.execute("BEGIN IMMEDIATE")
        for run in rows:
            if run["status"] != "materializing":
                summary["pre_materialization"] += 1
                con.execute(
                    "UPDATE newsroom_runs SET status='fallback',error_kind=?,error_message=?,"
                    "updated_at=?,completed_at=? WHERE run_id=?",
                    ("interrupted_before_materialization",
                     "worker restarted before materialization; inventory left untouched",
                     now, now, run["run_id"]),
                )
                continue

            summary["materializing"] += 1
            try:
                dossier = json.loads(run["dossier_json"] or "{}")
            except (TypeError, ValueError):
                dossier = {}
            if not isinstance(dossier, dict):
                dossier = {}
            dossier_items = [
                row for row in dossier.get("items") or []
                if isinstance(row, dict) and row.get("url_hash")
            ]
            stories = {
                str(row.get("story_id") or ""): row
                for row in dossier.get("stories") or [] if isinstance(row, dict)
            }
            commit_rows = con.execute(
                "SELECT story_id,state FROM newsroom_story_commits WHERE run_id=?",
                (run["run_id"],),
            ).fetchall()
            commits = {row["story_id"]: row["state"] for row in commit_rows}
            item_rows = {
                row["url_hash"]: row for row in con.execute(
                    "SELECT url_hash,status FROM items WHERE url_hash IN ("
                    + ",".join("?" for _ in dossier_items) + ")",
                    tuple(str(row["url_hash"]) for row in dossier_items),
                ).fetchall()
            } if dossier_items else {}

            for story_id, story in stories.items():
                members = [str(value) for value in story.get("member_hashes") or []]
                states = {item_rows[value]["status"] for value in members if value in item_rows}
                recorded = bool(states & {"posted", "drafted", "uncertain", "taped"})
                commit_state = commits.get(story_id)
                if commit_state == "delivered" or recorded:
                    if commit_state != "delivered":
                        con.execute(
                            "UPDATE newsroom_story_commits SET state='delivered',updated_at=?"
                            " WHERE run_id=? AND story_id=?",
                            (now, run["run_id"], story_id),
                        )
                    summary["stories_delivered"] += 1
                    continue
                action = str(story.get("action") or "hold")
                for item_hash in members:
                    current = item_rows.get(item_hash)
                    if not current or current["status"] not in {"new", "researching"}:
                        continue
                    status = "skipped" if action == "skip" else "held"
                    note = ("newsroom recovery: interrupted after materialization began; "
                            "delivery outcome requires inspection")
                    con.execute(
                        "UPDATE items SET status=?,note=?,decision_stage='newsroom_recovery',"
                        "decision_category='infrastructure' WHERE url_hash=?",
                        (status, note[:300], item_hash),
                    )
                    con.execute(
                        "UPDATE research_jobs SET state='exhausted',next_attempt_at=NULL,"
                        "error_kind='newsroom_recovery',error_message=?,claim_token=NULL,"
                        "claimed_at=NULL,updated_at=? WHERE item_hash=?",
                        (note[:300], now, item_hash),
                    )
                    con.execute(
                        "UPDATE operator_actions SET state='blocked',completed_at=?,result=?"
                        " WHERE item_hash=? AND state IN ('queued','processing')",
                        (now, note[:300], item_hash),
                    )
                    summary["items_held"] += int(status == "held")
                if commit_state not in {"delivered", "held"}:
                    con.execute(
                        "UPDATE newsroom_story_commits SET state='held',updated_at=?"
                        " WHERE run_id=? AND story_id=?",
                        (now, run["run_id"], story_id),
                    )

            # Null-story skip/hold rows do not have commit records but still need a
            # terminal disposition if the worker stopped before reaching them.
            for item in dossier_items:
                if item.get("story_id") is not None:
                    continue
                item_hash = str(item.get("url_hash") or "")
                current = item_rows.get(item_hash)
                if not current or current["status"] not in {"new", "researching"}:
                    continue
                disposition = str(item.get("disposition") or "hold")
                status = "skipped" if disposition == "skip" else "held"
                con.execute(
                    "UPDATE items SET status=?,note='newsroom recovery: terminal disposition'"
                    " WHERE url_hash=?",
                    (status, item_hash),
                )
                summary["items_held"] += int(status == "held")

            con.execute(
                "UPDATE newsroom_runs SET status='completed',error_kind=?,error_message=?,"
                "updated_at=?,completed_at=? WHERE run_id=?",
                ("interrupted_materialization",
                 "worker restarted during materialization; unresolved stories held",
                 now, now, run["run_id"]),
            )
        con.commit()
    except Exception:
        con.rollback()
        raise
    return summary


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


def update_research_retry_candidates(con, item_hash: str, candidates) -> None:
    row = con.execute(
        "SELECT context_json FROM research_jobs WHERE item_hash=?", (item_hash,)
    ).fetchone()
    if not row:
        return
    try:
        context = json.loads(row["context_json"])
    except (TypeError, ValueError):
        return
    if not isinstance(context, dict):
        return
    bounded = []
    for raw in list(candidates or [])[:3]:
        if not isinstance(raw, dict):
            continue
        bounded.append({
            "url": str(raw.get("url") or "")[:2000],
            "outlet": str(raw.get("outlet") or "")[:120],
            "tier": str(raw.get("tier") or "")[:10],
            "path": str(raw.get("path") or "unknown")[:20],
        })
    context["_resolver_candidates"] = bounded
    encoded = json.dumps(context, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode()) > 32768:
        return
    con.execute(
        "UPDATE research_jobs SET context_json=?,updated_at=? WHERE item_hash=?",
        (encoded, time.time(), item_hash),
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
                       consume_attempt: bool = True) -> str:
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
    return state


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


def due_research_jobs_snapshot(con, limit: int = 2, now: float = None) -> list[dict]:
    """Read-only inventory for a newsroom; attempts are consumed only on materialization."""
    current = time.time() if now is None else now
    rows = con.execute(
        "SELECT * FROM research_jobs WHERE state='pending' AND next_attempt_at<=?"
        " ORDER BY next_attempt_at,item_hash LIMIT ?",
        (current, max(0, int(limit))),
    ).fetchall()
    return [dict(row) for row in rows]


def claim_research_job_for_materialization(con, item_hash: str, now: float = None):
    current = time.time() if now is None else now
    token = f"newsroom:{item_hash}:{int(current)}"
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT * FROM research_jobs WHERE item_hash=? AND state='pending'",
            (item_hash,),
        ).fetchone()
        if not row:
            con.rollback()
            return None
        con.execute(
            "UPDATE research_jobs SET state='processing',attempts=attempts+1,claim_token=?,"
            "claimed_at=?,updated_at=? WHERE item_hash=? AND state='pending'",
            (token, current, current, item_hash),
        )
        con.execute("UPDATE items SET status='researching' WHERE url_hash=?", (item_hash,))
        con.commit()
        return dict(con.execute(
            "SELECT * FROM research_jobs WHERE item_hash=?", (item_hash,)
        ).fetchone())
    except Exception:
        con.rollback()
        raise


def recover_exhausted_timeouts(con, limit: int = 20, apply: bool = False,
                               now: float = None) -> dict:
    """Explicit, capped one-time recovery for the repaired source-timeout path."""
    current = time.time() if now is None else now
    cap = max(1, min(int(limit), 100))
    rows = con.execute(
        "SELECT r.item_hash,r.error_kind,r.error_message,i.published_at,i.status"
        " FROM research_jobs r JOIN items i ON i.url_hash=r.item_hash"
        " WHERE r.state='exhausted' AND r.stage='source_resolution'"
        " AND i.status='held' ORDER BY r.updated_at,r.item_hash LIMIT ?",
        (cap * 4,),
    ).fetchall()
    eligible = []
    for row in rows:
        kind = str(row["error_kind"] or "")
        message = str(row["error_message"] or "").lower()
        repaired = kind in {"support_assessment_timeout", "search_timeout"} or (
            kind == "APITimeoutError" and (
                "timed out" in message or "timeout" in message or "interrupted" in message
            )
        )
        if repaired and not is_stale(row["published_at"], now=datetime.datetime.fromtimestamp(
                current, tz=datetime.timezone.utc)):
            eligible.append(row["item_hash"])
        if len(eligible) >= cap:
            break
    if apply and eligible:
        try:
            con.execute("BEGIN IMMEDIATE")
            for item_hash in eligible:
                con.execute(
                    "UPDATE research_jobs SET state='pending',attempts=1,next_attempt_at=?,"
                    "claim_token=NULL,claimed_at=NULL,updated_at=? WHERE item_hash=?"
                    " AND state='exhausted'",
                    (current, current, item_hash),
                )
            event_hash = f"recovery:{int(current)}"
            con.execute(
                "INSERT OR IGNORE INTO pipeline_events(run_id,item_hash,event,category,at,metadata)"
                " VALUES (?,?,?,?,?,?)",
                (event_hash, event_hash, "research_recovery_requeued", "infrastructure",
                 current, json.dumps({"count": len(eligible), "cap": cap}, separators=(",", ":"))),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return {"eligible": len(eligible), "applied": len(eligible) if apply else 0,
            "limit": cap, "dry_run": not apply}


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
        "SELECT i.url_hash,i.source,i.title,i.url,i.published_at AS published,"
        " i.summary,i.discovery_origin,i.discovery_context,i.discovery_candidate_id,"
        " i.story_key,i.note,i.decision_stage,i.decision_category,"
        " t.route AS intake_route,t.promoted_at AS intake_promoted_at"
        " FROM items i LEFT JOIN intake_triage t ON t.item_hash=i.url_hash"
        " WHERE i.status='new' AND COALESCE(i.defer_until,0)<=?"
        " ORDER BY i.first_seen",
        (time.time(),),
    ).fetchall()
    values = [dict(row) for row in rows]
    if config.INTAKE_TRIAGE_MODE == "enforce":
        def rank(row):
            if row.get("intake_route") == "priority":
                return 0
            if row.get("intake_promoted_at") is not None:
                return 1
            if guide_context.signal_from_context(row.get("discovery_context")):
                return 2
            return 3
    else:
        def rank(row):
            return 0 if guide_context.signal_from_context(row.get("discovery_context")) else 1
    values = [row for _, row in sorted(
        enumerate(values), key=lambda pair: (rank(pair[1]), pair[0])
    )]
    return values[:max(0, int(limit))]


def theme_coverage_snapshot(con, items: list, days: float = 7.0,
                            row_limit: int = 250, key_limit: int = 3,
                            theme_limit: int = 24) -> list[dict]:
    """Advisory recent coverage for current-batch Node themes.

    Absence is deliberately ``coverage_known=false`` because older and non-Node items may
    not carry a theme mapping. This is context for triage, never a novelty gate.
    """
    requested: dict[str, dict] = {}
    for item in items:
        packet = theme_context.parse_discovery_context(item.get("discovery_context"))
        signals = theme_context.signals_by_id(packet)
        for theme_id in packet["theme_ids"]:
            if theme_id in requested or len(requested) >= theme_limit:
                continue
            signal = signals.get(theme_id, {})
            requested[theme_id] = {
                "theme_id": theme_id,
                "name": signal.get("name") or theme_id,
                "trajectory": signal.get("trajectory"),
                "count_7d": signal.get("count_7d"),
                "last_evidence_at": signal.get("last_evidence_at"),
                "coverage_known": False,
                "last_published_at": None,
                "open_draft": False,
                "recent_story_keys": [],
            }
    if not requested:
        return []

    effective = effective_post_ts_sql("p")
    rows = con.execute(
        "SELECT p.*,i.discovery_context,i.story_key AS item_story_key,"
        f" {effective} AS effective_at FROM posts p"
        " LEFT JOIN items i ON i.url_hash=p.item_hash"
        f" WHERE {effective}>? AND p.mode IN ('IMMEDIATE','UNCERTAIN','DRAFT')"
        " AND COALESCE(p.publisher_status,'')<>'deleted'"
        " AND COALESCE(p.class,'')<>'briefing' ORDER BY effective_at DESC LIMIT ?",
        (time.time() - max(1.0, days) * 86400, max(1, min(row_limit, 500))),
    ).fetchall()
    family_packets: dict[str, list[dict]] = {}

    def packets_for_story(story_key: str) -> list[dict]:
        canonical = canonical_story_key(con, story_key)
        if canonical in family_packets:
            return family_packets[canonical]
        family = story_key_family(con, canonical)
        if not family:
            family_packets[canonical] = []
            return []
        placeholders = ",".join("?" for _ in family)
        item_rows = con.execute(
            f"SELECT discovery_context FROM items WHERE story_key IN ({placeholders})"
            " AND COALESCE(discovery_context,'')<>'' ORDER BY first_seen DESC LIMIT 20",
            family,
        ).fetchall()
        packets = [theme_context.parse_discovery_context(row["discovery_context"])
                   for row in item_rows]
        family_packets[canonical] = packets
        return packets

    story_times: dict[str, dict[str, float]] = {theme_id: {} for theme_id in requested}
    for row in rows:
        packet = theme_context.parse_discovery_context(row["discovery_context"])
        packets = [packet] if packet["theme_ids"] else packets_for_story(row["story_key"])
        mapped_ids = {
            theme_id for candidate in packets for theme_id in candidate["theme_ids"]
            if theme_id in requested
        }
        if not mapped_ids:
            continue
        canonical = canonical_story_key(con, row["story_key"])
        for theme_id in mapped_ids:
            entry = requested[theme_id]
            if row["mode"] in ("IMMEDIATE", "UNCERTAIN"):
                entry["coverage_known"] = True
                visible_at = float(row["effective_at"] or row["created"] or 0)
                entry["last_published_at"] = max(
                    float(entry["last_published_at"] or 0), visible_at
                ) or None
                if canonical:
                    story_times[theme_id][canonical] = max(
                        story_times[theme_id].get(canonical, 0), visible_at
                    )
            elif (row["mode"] == "DRAFT" and row["publisher_backend"] == "typefully"
                  and row["nuelink_id"] and row["publisher_status"] != "deleted"):
                entry["coverage_known"] = True
                entry["open_draft"] = True
                if canonical:
                    story_times[theme_id][canonical] = max(
                        story_times[theme_id].get(canonical, 0), float(row["created"] or 0)
                    )
    for theme_id, entry in requested.items():
        ordered = sorted(story_times[theme_id].items(), key=lambda pair: pair[1], reverse=True)
        entry["recent_story_keys"] = [key for key, _ in ordered[:max(1, min(key_limit, 5))]]
    return list(requested.values())


def effective_post_ts_sql(alias: str = "") -> str:
    """SQL expression for when a post became reader-visible (or might have)."""
    prefix = f"{alias}." if alias else ""
    return (f"CASE WHEN {prefix}mode='IMMEDIATE'"
            f" THEN COALESCE({prefix}confirmed_at,{prefix}created)"
            f" ELSE {prefix}created END")


def recent_feed_posts(con, *, hours: float = 48.0, limit: int = 40,
                      modes: tuple[str, ...] = ("IMMEDIATE", "UNCERTAIN")) -> list[dict]:
    """Bounded exact recent copy for newsroom/editor feed awareness."""
    allowed = tuple(mode for mode in modes if mode in {"IMMEDIATE", "UNCERTAIN", "DRAFT"})
    if not allowed:
        return []
    placeholders = ",".join("?" for _ in allowed)
    effective = effective_post_ts_sql()
    rows = con.execute(
        "SELECT story_key,class,body,receipt_url,mode,performance_json,performance_synced_at,"
        f" {effective} AS effective_at FROM posts"
        f" WHERE mode IN ({placeholders}) AND {effective}>=?"
        " AND COALESCE(publisher_status,'')<>'deleted'"
        " ORDER BY effective_at DESC LIMIT ?",
        (*allowed, time.time() - max(1.0, hours) * 3600, max(1, min(limit, 100))),
    ).fetchall()
    out = []
    for row in rows:
        try:
            performance = json.loads(row["performance_json"] or "null")
        except (TypeError, ValueError):
            performance = None
        if not isinstance(performance, dict):
            performance = None
        out.append({
            "story_key": canonical_story_key(con, row["story_key"]),
            "class": row["class"],
            "body": row["body"] or "",
            "receipt_url": row["receipt_url"] or "",
            "mode": row["mode"],
            "effective_at": float(row["effective_at"] or 0),
            "performance": performance,
            "performance_synced_at": float(row["performance_synced_at"] or 0),
        })
    return out


def recent_story_keys(con, days: float = 3.0) -> list:
    """Canonical keys readers saw or may have seen (authorizes UPDATE handling)."""
    effective = effective_post_ts_sql()
    rows = con.execute(
        f"SELECT story_key, MAX({effective}) effective_at FROM posts"
        " WHERE mode IN ('IMMEDIATE','UNCERTAIN') GROUP BY story_key"
        f" HAVING MAX({effective}) > ? ORDER BY effective_at DESC LIMIT 100",
        (time.time() - days * 86400,),
    ).fetchall()
    out = []
    for row in rows:
        key = canonical_story_key(con, row["story_key"])
        if key and key not in out:
            out.append(key)
    return out


def open_story_keys(con, days: float = 2.0) -> list:
    """Keys of stories seen but NOT posted (held/drafted/tracked). Triage must REUSE
    these for new items about the same event — key identity is what makes a second
    outlet's arrival trip the corroboration promotion."""
    rows = con.execute(
        "SELECT DISTINCT story_key FROM items WHERE story_key IS NOT NULL"
        " AND first_seen > ? LIMIT 150", (time.time() - days * 86400,),
    ).fetchall()
    posted = set(recent_story_keys(con, days))
    out = []
    for row in rows:
        key = canonical_story_key(con, row["story_key"])
        if key and key not in posted and key not in out:
            out.append(key)
    return out


def canonical_story_key(con, story_key: str) -> str:
    """Resolve a model-produced key through cycle-safe, news-window aliases."""
    current = str(story_key or "").strip()[:180]
    seen = set()
    while current and current not in seen and len(seen) < 12:
        seen.add(current)
        row = con.execute(
            "SELECT canonical_key,updated_at FROM story_key_aliases WHERE alias_key=?",
            (current,),
        ).fetchone()
        # Event-key aliases bridge adjacent discovery runs, not recurring events months
        # apart. Triage keys remain human-readable while this expiry supplies temporal
        # identity even when a model forgets to include a date in a slug.
        if (not row or not row["canonical_key"]
                or float(row["updated_at"] or 0) < time.time() - 3 * 86400):
            break
        current = str(row["canonical_key"]).strip()[:180]
    return current


def register_story_alias(con, alias_key: str, canonical_key: str, reason: str = "") -> str:
    """Persist one high-confidence event-key merge without allowing mapping churn."""
    alias = str(alias_key or "").strip()[:180]
    canonical = canonical_story_key(con, canonical_key)
    if not alias or not canonical or alias == canonical:
        return canonical or alias
    existing = con.execute(
        "SELECT canonical_key FROM story_key_aliases WHERE alias_key=?", (alias,)
    ).fetchone()
    if existing:
        resolved = canonical_story_key(con, alias)
        con.execute(
            "UPDATE story_key_aliases SET updated_at=? WHERE alias_key=?",
            (time.time(), alias),
        )
        con.commit()
        return resolved
    if canonical_story_key(con, canonical) == alias:
        return alias
    now = time.time()
    con.execute(
        "INSERT INTO story_key_aliases(alias_key,canonical_key,reason,created_at,updated_at)"
        " VALUES (?,?,?,?,?)",
        (alias, canonical, str(reason or "")[:300], now, now),
    )
    con.commit()
    return canonical


def story_key_family(con, story_key: str) -> list[str]:
    """All historical aliases that resolve to the same canonical event cluster."""
    root = canonical_story_key(con, story_key)
    if not root:
        return []
    rows = con.execute("SELECT alias_key FROM story_key_aliases").fetchall()
    family = {root}
    for row in rows:
        alias = row["alias_key"]
        if canonical_story_key(con, alias) == root:
            family.add(alias)
    return sorted(family)


def story_cluster_context(con, days: float = 2.0, limit: int = 50,
                          exclude_hashes: set[str] | None = None) -> list[dict]:
    """Compact recent event catalog for high-precision cross-run key reconciliation."""
    excluded = exclude_hashes or set()
    cutoff = time.time() - days * 86400
    clusters = {}

    def cluster(key: str) -> dict:
        canonical = canonical_story_key(con, key)
        return clusters.setdefault(canonical, {
            "canonical_key": canonical, "aliases": set(), "titles": [], "sources": [],
            "statuses": set(), "post_leads": [], "reader_covered": False,
            "draft_open": False, "updated_at": 0.0,
        })

    for row in con.execute(
        "SELECT url_hash,story_key,title,source,status,first_seen FROM items"
        " WHERE story_key IS NOT NULL AND first_seen>=? ORDER BY first_seen DESC LIMIT 400",
        (cutoff,),
    ).fetchall():
        if row["url_hash"] in excluded:
            continue
        entry = cluster(row["story_key"])
        entry["aliases"].add(row["story_key"])
        if row["title"] and row["title"] not in entry["titles"] and len(entry["titles"]) < 3:
            entry["titles"].append(str(row["title"])[:240])
        if row["source"] and row["source"] not in entry["sources"] and len(entry["sources"]) < 3:
            entry["sources"].append(str(row["source"])[:100])
        entry["statuses"].add(row["status"])
        entry["updated_at"] = max(entry["updated_at"], float(row["first_seen"] or 0))

    for row in con.execute(
        "SELECT story_key,body,mode,created FROM posts"
        " WHERE story_key IS NOT NULL AND created>=? ORDER BY created DESC LIMIT 250",
        (cutoff,),
    ).fetchall():
        entry = cluster(row["story_key"])
        entry["aliases"].add(row["story_key"])
        lead = str(row["body"] or "").split("\n")[0][:260]
        if lead and lead not in entry["post_leads"] and len(entry["post_leads"]) < 2:
            entry["post_leads"].append(lead)
        entry["reader_covered"] |= row["mode"] in ("IMMEDIATE", "UNCERTAIN")
        entry["draft_open"] |= row["mode"] == "DRAFT"
        entry["updated_at"] = max(entry["updated_at"], float(row["created"] or 0))

    # Workbench state aids exact-event continuity but is never coverage authority.
    for memory in newsroom_story_memories(con, limit=12):
        entry = cluster(memory["canonical_key"])
        attempt = memory["attempts"][-1]
        entry["aliases"].add(memory["canonical_key"])
        for title in list(attempt.get("headlines") or [])[:3]:
            if title and title not in entry["titles"] and len(entry["titles"]) < 3:
                entry["titles"].append(str(title)[:240])
        lead = str(attempt.get("proposed_post") or "").split("\n")[0][:260]
        if lead and lead not in entry["post_leads"] and len(entry["post_leads"]) < 2:
            entry["post_leads"].append(lead)
        entry["statuses"].add("workbench:" + str(memory.get("state") or "unknown")[:40])
        entry["updated_at"] = max(entry["updated_at"], float(memory["updated_at"] or 0))

    ordered = sorted(clusters.values(), key=lambda row: row["updated_at"], reverse=True)
    out = []
    for row in ordered[:limit]:
        out.append({
            **row,
            "aliases": sorted(row["aliases"]),
            "statuses": sorted(row["statuses"]),
        })
    return out


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
    story_key = canonical_story_key(con, result.story_key)
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
            (result.item_hash, story_key, now, mode, result.status,
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
                (result.item_hash, story_key, now, ev.ref.url, ev.ref.source_id,
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
    story_key = canonical_story_key(con, story_key)
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
        con.execute(
            "UPDATE research_jobs SET story_key=?,updated_at=? WHERE item_hash=?",
            (story_key, time.time(), item_hash),
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
    family = story_key_family(con, story_key)
    if not family:
        return []
    placeholders = ",".join("?" for _ in family)
    rows = con.execute(
        f"SELECT * FROM source_evidence WHERE story_key IN ({placeholders}) AND observed_at>=?"
        " AND support_verdict=1 AND corroboration_eligible=1"
        " ORDER BY observed_at, id",
        (*family, time.time() - lookback_hours * 3600),
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
    """True only when readers saw, or may have seen, this event cluster."""
    family = story_key_family(con, story_key)
    if not family:
        return False
    placeholders = ",".join("?" for _ in family)
    return con.execute(
        f"SELECT 1 FROM posts WHERE story_key IN ({placeholders})"
        " AND mode IN ('IMMEDIATE','UNCERTAIN') LIMIT 1", family,
    ).fetchone() is not None


def story_handled(con, story_key: str) -> bool:
    """True when an event cluster is already published, uncertain, or queued as a draft."""
    family = story_key_family(con, story_key)
    if not family:
        return False
    placeholders = ",".join("?" for _ in family)
    return con.execute(
        f"SELECT 1 FROM posts WHERE story_key IN ({placeholders})"
        " AND mode IN ('IMMEDIATE','DRAFT','UNCERTAIN') LIMIT 1", family,
    ).fetchone() is not None


def story_produced(con, story_key: str) -> bool:
    """True for any recorded output; used for one-shot jobs such as briefing windows."""
    family = story_key_family(con, story_key)
    if not family:
        return False
    placeholders = ",".join("?" for _ in family)
    return con.execute(
        f"SELECT 1 FROM posts WHERE story_key IN ({placeholders}) LIMIT 1", family,
    ).fetchone() is not None


def exact_output_exists(con, body: str, receipt_url: str) -> bool:
    """Idempotency rail only; semantic novelty belongs to the editorial seats."""
    return con.execute(
        "SELECT 1 FROM posts WHERE (body=? OR receipt_url=?)"
        " AND mode IN ('IMMEDIATE','DRAFT','UNCERTAIN') LIMIT 1",
        (str(body), str(receipt_url)),
    ).fetchone() is not None


def exact_thread_output_exists(con, body: str, receipt_url: str) -> bool:
    """V2 byte-equivalent one-off guard; semantic continuity is relation/state-owned."""
    return con.execute(
        "SELECT 1 FROM posts WHERE body=? AND receipt_url=?"
        " AND mode IN ('IMMEDIATE','DRAFT','UNCERTAIN') LIMIT 1",
        (str(body), str(receipt_url)),
    ).fetchone() is not None


_MUTATION_PROTECTED_STATES = {
    "prepared", "in_flight", "ambiguous", "needs_owner_review", "owner_suppressed",
}
_MUTATION_STATES = _MUTATION_PROTECTED_STATES | {"confirmed", "definite_failure"}
_MUTATION_OPERATIONS = {"create", "replace_draft", "schedule"}


def x_thread_fingerprint(texts: list[str]) -> str:
    """Exact, order-sensitive fingerprint for the complete NBN-authored X thread."""
    encoded = json.dumps([str(value) for value in texts], ensure_ascii=False,
                         separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def canonical_output_state(con, story_key: str) -> dict:
    """Resolve active outputs with visible > draft > none precedence.

    Operator/Desk display state is deliberately ignored. Only authoritative publisher
    lifecycle values `deleted` and `inactive` stop a Typefully draft from blocking.
    """
    root = canonical_story_key(con, story_key)
    family = story_key_family(con, root)
    if not family:
        family = [root] if root else []
    if not family:
        return {"state": "none", "canonical_key": "", "visible": None,
                "drafts": [], "protected_mutations": [], "signature": "none"}
    placeholders = ",".join("?" for _ in family)
    rows = [dict(row) for row in con.execute(
        f"SELECT * FROM posts WHERE story_key IN ({placeholders})"
        " AND mode IN ('IMMEDIATE','DRAFT','UNCERTAIN')"
        " AND NOT (mode='DRAFT' AND COALESCE(publisher_status,'') IN ('deleted','inactive'))"
        " ORDER BY created DESC,id DESC", family,
    ).fetchall()]
    visible = [row for row in rows if row["mode"] in {"IMMEDIATE", "UNCERTAIN"}]
    drafts = [row for row in rows if row["mode"] == "DRAFT"]
    mutations = [dict(row) for row in con.execute(
        f"SELECT * FROM publisher_mutations WHERE canonical_key IN ({placeholders})"
        f" AND state IN ({','.join('?' for _ in _MUTATION_PROTECTED_STATES)})"
        " ORDER BY updated_at DESC",
        (*family, *sorted(_MUTATION_PROTECTED_STATES)),
    ).fetchall()]
    state = "reader_visible" if visible else "open_draft" if drafts else "none"
    signature_rows = [{
        "id": row["id"], "mode": row["mode"],
        "publisher_status": row.get("publisher_status") or "",
        "relation": row.get("coverage_relation") or "legacy",
        "base_post_id": row.get("base_post_id"),
    } for row in rows]
    signature = hashlib.sha256(json.dumps(
        {"root": root, "outputs": signature_rows,
         "mutations": [(row["mutation_id"], row["state"], row["version"])
                       for row in mutations]},
        sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    return {
        "state": state, "canonical_key": root,
        "visible": visible[0] if visible else None,
        "drafts": drafts, "protected_mutations": mutations,
        "signature": signature,
    }


def prepare_publisher_mutation(
        con, *, story_key: str, operation: str, intended_mode: str,
        desired_thread: list[str], materialization: dict,
        expected_output_signature: str, target_draft_id: str = "",
        target_post_id: int | None = None, base_post_id: int | None = None,
        prior_thread: list[str] | None = None, now: float | None = None) -> dict:
    """Persist a Typefully intent before network I/O and fence competing workers."""
    if operation not in _MUTATION_OPERATIONS:
        raise ValueError("invalid publisher mutation operation")
    encoded = json.dumps(materialization, separators=(",", ":"), ensure_ascii=False)
    if len(encoded.encode("utf-8")) > 64 * 1024:
        raise ValueError("publisher mutation materialization exceeds 64 KiB")
    stamp = float(now if now is not None else time.time())
    mutation_id, token = uuid.uuid4().hex, uuid.uuid4().hex
    try:
        con.execute("BEGIN IMMEDIATE")
        current = canonical_output_state(con, story_key)
        if current["signature"] != str(expected_output_signature):
            con.rollback()
            return {"ok": False, "reason": "output_state_changed", "state": current}
        if current["protected_mutations"]:
            con.rollback()
            return {"ok": False, "reason": "mutation_already_protected", "state": current}
        root = current["canonical_key"] or canonical_story_key(con, story_key)
        con.execute(
            "INSERT INTO publisher_mutations(mutation_id,canonical_key,operation,"
            "target_draft_id,target_post_id,base_post_id,desired_fingerprint,prior_fingerprint,"
            "owner_token,version,state,intended_mode,materialization_json,created_at,updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,1,'prepared',?,?,?,?)",
            (mutation_id, root, operation, str(target_draft_id or "")[:200] or None,
             target_post_id, base_post_id, x_thread_fingerprint(desired_thread),
             x_thread_fingerprint(prior_thread) if prior_thread is not None else None,
             token, str(intended_mode or "")[:20], encoded, stamp, stamp),
        )
        con.commit()
        return {"ok": True, "mutation_id": mutation_id, "owner_token": token,
                "version": 1, "canonical_key": root}
    except Exception:
        con.rollback()
        raise


def transition_publisher_mutation(con, mutation_id: str, owner_token: str, version: int,
                                  state: str, *, provider_ref: str = "",
                                  error_kind: str = "", error_message: str = "",
                                  now: float | None = None) -> bool:
    if state not in _MUTATION_STATES:
        raise ValueError("invalid publisher mutation state")
    stamp = float(now if now is not None else time.time())
    cur = con.execute(
        "UPDATE publisher_mutations SET state=?,provider_ref=COALESCE(NULLIF(?,''),provider_ref),"
        "error_kind=?,error_message=?,updated_at=?,resolved_at=CASE WHEN ? IN "
        "('confirmed','definite_failure','owner_suppressed') THEN ? ELSE NULL END,version=version+1"
        " WHERE mutation_id=? AND owner_token=? AND version=?",
        (state, str(provider_ref or "")[:300], str(error_kind or "")[:80] or None,
         str(error_message or "")[:500] or None, stamp, state, stamp,
         str(mutation_id), str(owner_token), int(version)),
    )
    con.commit()
    return cur.rowcount == 1


def publisher_mutation(con, mutation_id: str):
    return con.execute(
        "SELECT * FROM publisher_mutations WHERE mutation_id=?", (str(mutation_id),)
    ).fetchone()


def pending_publisher_mutations(con, limit: int = 20) -> list[dict]:
    rows = con.execute(
        "SELECT * FROM publisher_mutations WHERE state IN "
        "('prepared','in_flight','ambiguous','needs_owner_review')"
        " ORDER BY updated_at LIMIT ?", (max(1, min(int(limit), 100)),),
    ).fetchall()
    return [dict(row) for row in rows]


def owner_resolve_publisher_mutation(con, mutation_id: str, owner_token: str,
                                     version: int, resolution: str) -> dict:
    """Apply one authenticated, version-fenced non-network owner resolution."""
    target = {"confirmed_absent": "definite_failure",
              "keep_suppressed": "owner_suppressed"}.get(str(resolution))
    if not target:
        return {"ok": False, "reason": "invalid resolution"}
    stamp = time.time()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT * FROM publisher_mutations WHERE mutation_id=? AND owner_token=?"
            " AND version=? AND state IN ('ambiguous','needs_owner_review')",
            (str(mutation_id), str(owner_token), int(version)),
        ).fetchone()
        if not row:
            con.rollback()
            return {"ok": False, "reason": "stale or ineligible mutation"}
        con.execute(
            "UPDATE publisher_mutations SET state=?,version=version+1,updated_at=?,resolved_at=?,"
            "error_kind='owner_resolution',error_message=? WHERE mutation_id=? AND owner_token=?"
            " AND version=?",
            (target, stamp, stamp, str(resolution)[:80], mutation_id, owner_token, int(version)),
        )
        con.execute(
            "INSERT OR IGNORE INTO pipeline_events(run_id,item_hash,story_key,event,category,at,metadata)"
            " VALUES (?,?,?,?,?,?,?)",
            (f"owner:{mutation_id[:32]}", f"mutation:{mutation_id[:40]}",
             row["canonical_key"], f"publisher_owner_{resolution}", "delivery", stamp,
             json.dumps({"mutation_id": mutation_id, "version": version},
                        separators=(",", ":"))[:2000]),
        )
        con.commit()
        return {"ok": True, "state": target}
    except Exception:
        con.rollback()
        raise


def finalize_publisher_mutation(
        con, mutation_id: str, owner_token: str, version: int, *, mode: str,
        provider_ref: str, publisher_status: str = "") -> dict:
    """Atomically materialize a remotely confirmed output from durable intent data."""
    stamp = time.time()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            "SELECT * FROM publisher_mutations WHERE mutation_id=? AND owner_token=?"
            " AND version=? AND state IN ('prepared','in_flight','ambiguous','needs_owner_review')",
            (str(mutation_id), str(owner_token), int(version)),
        ).fetchone()
        if not row:
            existing = con.execute(
                "SELECT id FROM posts WHERE mutation_id=?", (str(mutation_id),)
            ).fetchone()
            con.commit()
            return {"ok": bool(existing), "post_id": existing["id"] if existing else None,
                    "already_finalized": bool(existing)}
        data = json.loads(row["materialization_json"])
        relation = str(data.get("coverage_relation") or "distinct")[:30]
        base_post_id = data.get("base_post_id")
        if row["operation"] == "replace_draft":
            target_id = int(row["target_post_id"] or 0)
            cur = con.execute(
                "UPDATE posts SET class=?,body=?,receipt_url=?,editor_note=?,resolution_id=?,"
                "publisher_status=?,publisher_synced_at=?,coverage_relation=?,base_post_id=?,"
                "storyline_key=CASE WHEN ? IS NULL THEN storyline_key"
                " WHEN storyline_key IS NULL OR storyline_key=? THEN ? ELSE storyline_key END,"
                "mutation_id=? WHERE id=? AND mode='DRAFT'",
                (str(data.get("klass") or "")[:40], str(data.get("body") or ""),
                 str(data.get("receipt_url") or "")[:2000],
                 str(data.get("editor_note") or "")[:300],
                 str(data.get("resolution_id") or "")[:200],
                 str(publisher_status or "draft")[:40], stamp, relation, base_post_id,
                 str(data.get("storyline_key") or "")[:120] or None,
                 str(data.get("storyline_key") or "")[:120] or None,
                 str(data.get("storyline_key") or "")[:120] or None,
                 str(mutation_id), target_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("replacement target changed before local finalization")
            post_id = target_id
        else:
            cur = con.execute(
                "INSERT OR IGNORE INTO posts(created,story_key,item_hash,class,body,receipt_url,"
                "mode,nuelink_id,editor_note,resolution_id,publisher_backend,publisher_status,"
                "publisher_synced_at,coverage_relation,base_post_id,storyline_key,mutation_id)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (stamp, row["canonical_key"], str(data.get("item_hash") or "")[:64],
                 str(data.get("klass") or "")[:40], str(data.get("body") or ""),
                 str(data.get("receipt_url") or "")[:2000], str(mode)[:20],
                 str(provider_ref or "")[:300] or None,
                 str(data.get("editor_note") or "")[:300],
                 str(data.get("resolution_id") or "")[:200],
                 str(data.get("publisher_backend") or "typefully")[:40],
                 str(publisher_status or "")[:40] or None, stamp, relation,
                 base_post_id, str(data.get("storyline_key") or "")[:120] or None,
                 str(mutation_id)),
            )
            found = con.execute(
                "SELECT id FROM posts WHERE mutation_id=?", (str(mutation_id),)
            ).fetchone()
            if not found:
                raise RuntimeError("publisher mutation post was not materialized")
            post_id = found["id"]
        for index, member in enumerate(list(data.get("members") or [])[:25]):
            item_hash = str(member.get("url_hash") or "")[:64]
            if not item_hash:
                continue
            status = str(member.get("status") or ("drafted" if mode == "DRAFT" else "posted"))
            if index:
                status = "skipped"
            con.execute(
                "UPDATE items SET status=?,story_key=CASE WHEN ? THEN story_key ELSE ? END,"
                "note=?,decision_stage='delivery',"
                "decision_category='output',defer_until=NULL WHERE url_hash=?",
                (status, int(bool(member.get("preserve_story_key"))),
                 str(member.get("story_key") or row["canonical_key"])[:180],
                 "" if not index else
                 "same story materialized from pooled evidence", item_hash),
            )
            con.execute(
                "UPDATE operator_actions SET state='completed',completed_at=?,result=?"
                " WHERE item_hash=? AND state='pending'",
                (stamp, f"delivery result: {mode}"[:300], item_hash),
            )
        delivery = json.dumps({
            "at": round(stamp, 3), "mode": str(mode)[:40],
            "backend_ref": str(provider_ref or "")[:300],
            "reader_covered": mode in {"IMMEDIATE", "UNCERTAIN"},
        }, separators=(",", ":"))
        con.execute(
            "UPDATE newsroom_story_memory SET state='delivered',delivery_json=?,updated_at=?,"
            "expires_at=? WHERE canonical_key=?",
            (delivery, stamp, stamp + _STORY_MEMORY_TTL_SECONDS, row["canonical_key"]),
        )
        run_id, story_id = str(data.get("run_id") or ""), str(data.get("story_id") or "")
        if run_id and story_id:
            details = json.dumps({"delivery": {"mode": mode,
                                "backend_ref": str(provider_ref or "")[:200]}},
                               separators=(",", ":"))
            con.execute(
                "UPDATE newsroom_story_commits SET state=?,delivery_ref=?,details_json=?,"
                "updated_at=? WHERE run_id=? AND story_id=?",
                ("delivered" if mode != "FAILED" else "held",
                 str(provider_ref or "")[:200], details[:4000], stamp, run_id, story_id),
            )
        item_hash = str(data.get("item_hash") or "")[:64] or f"mutation:{mutation_id[:40]}"
        con.execute(
            "INSERT OR IGNORE INTO pipeline_events(run_id,item_hash,story_key,event,category,at,metadata)"
            " VALUES (?,?,?,?,?,?,?)",
            (run_id or f"mutation:{mutation_id[:32]}", item_hash, row["canonical_key"],
             "publisher_mutation_confirmed", "delivery", stamp,
             json.dumps({"mutation_id": mutation_id, "operation": row["operation"],
                         "post_id": post_id}, separators=(",", ":"))[:2000]),
        )
        con.execute(
            "UPDATE publisher_mutations SET state='confirmed',provider_ref=?,error_kind=NULL,"
            "error_message=NULL,updated_at=?,resolved_at=?,version=version+1"
            " WHERE mutation_id=? AND owner_token=? AND version=?",
            (str(provider_ref or "")[:300], stamp, stamp, mutation_id, owner_token,
             int(version)),
        )
        con.commit()
        return {"ok": True, "post_id": post_id, "already_finalized": False}
    except Exception:
        con.rollback()
        raise


def recent_story_bodies(con, story_key: str, limit: int = 2) -> list[str]:
    family = story_key_family(con, story_key)
    if not family:
        return []
    placeholders = ",".join("?" for _ in family)
    effective = effective_post_ts_sql()
    rows = con.execute(
        f"SELECT body FROM posts WHERE story_key IN ({placeholders})"
        " AND mode IN ('IMMEDIATE','UNCERTAIN')"
        f" ORDER BY {effective} DESC LIMIT ?", (*family, limit),
    ).fetchall()
    return [row["body"] for row in rows]


def recent_delivery_latencies(con, limit: int = 20) -> list[dict]:
    """Derived timing telemetry; missing/naive source times remain unknown."""
    rows = con.execute(
        "SELECT p.*,i.first_seen,i.published_at,m.materialization_json "
        "FROM posts p LEFT JOIN items i ON i.url_hash=p.item_hash "
        "LEFT JOIN publisher_mutations m ON m.mutation_id=p.mutation_id "
        "WHERE p.mode IN ('DRAFT','IMMEDIATE','UNCERTAIN') "
        "ORDER BY p.created DESC LIMIT ?", (max(1, min(int(limit), 20)),),
    ).fetchall()
    out = []
    for raw in rows:
        row = dict(raw)
        published = None
        try:
            parsed = datetime.datetime.fromisoformat(
                str(row.get("published_at") or "").replace("Z", "+00:00")
            )
            if parsed.tzinfo is not None:
                published = parsed.timestamp()
        except (TypeError, ValueError, OverflowError):
            pass
        first_seen = float(row.get("first_seen") or 0) or None
        created = float(row.get("created") or 0) or None
        family = story_key_family(con, row.get("story_key") or "")
        resurfaced = None
        if family and first_seen:
            placeholders = ",".join("?" for _ in family)
            earliest = con.execute(
                f"SELECT MIN(first_seen) t FROM items WHERE story_key IN ({placeholders})",
                family,
            ).fetchone()["t"]
            if earliest is not None:
                resurfaced = max(0.0, first_seen - float(earliest))
        run_id = ""
        try:
            materialization = json.loads(row.get("materialization_json") or "{}")
            run_id = str(materialization.get("run_id") or "")
        except (TypeError, ValueError):
            pass
        newsroom_seconds = editor_ms = recovery_count = None
        if run_id:
            run = con.execute(
                "SELECT created_at,completed_at FROM newsroom_runs WHERE run_id=?", (run_id,)
            ).fetchone()
            if run and run["completed_at"] is not None:
                newsroom_seconds = max(0.0, float(run["completed_at"]) - float(run["created_at"]))
            usage = con.execute(
                "SELECT SUM(CASE WHEN seat IN ('editor','editor_recovery') THEN latency_ms ELSE 0 END) ms,"
                "SUM(CASE WHEN seat='editor_recovery' THEN 1 ELSE 0 END) recovery "
                "FROM model_usage WHERE run_id=?", (run_id,),
            ).fetchone()
            editor_ms = int(usage["ms"] or 0)
            recovery_count = int(usage["recovery"] or 0)
        out.append({
            "post_id": row["id"], "story_key": row.get("story_key") or "",
            "mode": row.get("mode") or "", "created": created,
            "detection_seconds": (max(0.0, first_seen - published)
                                  if first_seen and published else None),
            "conversion_seconds": (max(0.0, created - first_seen)
                                   if created and first_seen else None),
            "resurfaced_seconds": resurfaced, "newsroom_seconds": newsroom_seconds,
            "editor_ms": editor_ms, "editor_recovery_count": recovery_count,
        })
    return out


def open_typefully_draft(con, story_key: str):
    """Newest still-local Typefully draft in an event cluster, if any."""
    family = story_key_family(con, story_key)
    if not family:
        return None
    placeholders = ",".join("?" for _ in family)
    return con.execute(
        f"SELECT * FROM posts WHERE story_key IN ({placeholders}) AND mode='DRAFT'"
        " AND publisher_backend='typefully' AND COALESCE(nuelink_id,'')<>''"
        " ORDER BY created DESC LIMIT 1", family,
    ).fetchone()


def record_draft_promotion(con, post_id: int, klass: str, mode: str) -> None:
    """Record a definitive/ambiguous in-place Typefully draft promotion."""
    if mode not in ("IMMEDIATE", "UNCERTAIN"):
        return
    con.execute(
        "UPDATE posts SET class=?,mode=?,confirmed_at=CASE WHEN ?='IMMEDIATE' THEN ?"
        " ELSE confirmed_at END,publisher_status=? WHERE id=? AND mode='DRAFT'",
        (klass, mode, mode, time.time(),
         "published" if mode == "IMMEDIATE" else "uncertain", post_id),
    )
    con.commit()


def set_status(con, url_hash_: str, status: str, story_key: str = None, note: str = None,
               stage: str = None, category: str = None):
    if story_key:
        story_key = canonical_story_key(con, story_key)
    con.execute(
        "UPDATE items SET status=?,story_key=COALESCE(?,story_key),note=COALESCE(?,note),"
        "decision_stage=COALESCE(?,decision_stage),decision_category=COALESCE(?,decision_category)"
        " WHERE url_hash=?",
        (status, story_key, note, stage, category, url_hash_),
    )
    con.commit()


def defer_item(con, url_hash_: str, note: str, *, delay_seconds: int = 900,
               story_key: str | None = None, stage: str = "newsdesk",
               category: str = "editorial_defer") -> None:
    if story_key:
        story_key = canonical_story_key(con, story_key)
    con.execute(
        "UPDATE items SET status='new',story_key=COALESCE(?,story_key),note=?,"
        "decision_stage=?,decision_category=?,defer_until=? WHERE url_hash=?",
        (story_key, str(note)[:300], stage, category,
         time.time() + max(1, int(delay_seconds)), url_hash_),
    )
    con.commit()


def log_post(con, story_key, item_hash, klass, body, receipt_url, mode, publisher_ref=None,
             editor_note=None, resolution_id=None, publisher_backend=None,
             coverage_relation="legacy", base_post_id=None, mutation_id=None,
             storyline_key=None):
    """Record a produced post. nuelink_id is the legacy schema name for any backend ref."""
    story_key = canonical_story_key(con, story_key)
    con.execute(
        "INSERT INTO posts(created, story_key, item_hash, class, body, receipt_url, mode,"
        " nuelink_id, editor_note, resolution_id, publisher_backend,coverage_relation,"
        "base_post_id,mutation_id,storyline_key) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (time.time(), story_key, item_hash, klass, body, receipt_url, mode, publisher_ref,
         editor_note, resolution_id, publisher_backend, coverage_relation, base_post_id,
         mutation_id, str(storyline_key or "")[:120] or None),
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


def reconcile_typefully_analytics(con, records: list, synced_at: float = None) -> dict:
    """Attach Typefully's normalized X analytics to locally known output rows."""
    synced_at = synced_at or time.time()
    stats = {"fetched": len(records), "matched": 0, "updated": 0,
             "unknown": 0, "duplicates": 0}
    with con:
        for record in records:
            ref = str(record.get("draft_id") or "").strip()
            performance = record.get("performance")
            if not ref or not isinstance(performance, dict):
                stats["unknown"] += 1
                continue
            rows = con.execute(
                "SELECT id,performance_json FROM posts"
                " WHERE publisher_backend='typefully' AND nuelink_id=?",
                (ref,),
            ).fetchall()
            if len(rows) > 1:
                stats["duplicates"] += 1
                continue
            if not rows:
                stats["unknown"] += 1
                continue
            encoded = json.dumps(performance, sort_keys=True, separators=(",", ":"))
            changed = rows[0]["performance_json"] != encoded
            con.execute(
                "UPDATE posts SET performance_json=?,performance_synced_at=? WHERE id=?",
                (encoded, synced_at, rows[0]["id"]),
            )
            stats["matched"] += 1
            stats["updated"] += int(changed)
        con.execute(
            "INSERT INTO kv(k,v) VALUES ('publisher:analytics_last_success',?)"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v", (str(synced_at),))
        con.execute(
            "INSERT INTO kv(k,v) VALUES ('publisher:analytics_last_error','')"
            " ON CONFLICT(k) DO UPDATE SET v=excluded.v")
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
