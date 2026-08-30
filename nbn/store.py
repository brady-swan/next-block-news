"""SQLite state: seen items, story-level dedup, post log."""
import hashlib
import json
import sqlite3
import time

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS items (
  url_hash TEXT PRIMARY KEY,
  source TEXT, title TEXT, url TEXT, published_at TEXT,
  first_seen REAL, status TEXT DEFAULT 'new',   -- new|skipped|held|drafted|posted|error
  story_key TEXT, note TEXT
);
CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created REAL, story_key TEXT, item_hash TEXT, class TEXT,
  body TEXT, receipt_url TEXT, mode TEXT, nuelink_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_posts_story ON posts(story_key);
"""


def kv_get(con, k: str) -> str:
    row = con.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return row["v"] if row else ""


def kv_set(con, k: str, v: str):
    con.execute("INSERT INTO kv(k, v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, v))
    con.commit()


def url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:24]


def connect() -> sqlite3.Connection:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def upsert_new_items(con, items) -> list:
    """Insert unseen items; return the newly inserted subset."""
    fresh = []
    for it in items:
        h = url_hash(it["url"])
        cur = con.execute(
            "INSERT OR IGNORE INTO items(url_hash, source, title, url, published_at, first_seen)"
            " VALUES (?,?,?,?,?,?)",
            (h, it["source"], it["title"], it["url"], it.get("published", ""), time.time()),
        )
        if cur.rowcount:
            fresh.append({**it, "url_hash": h})
    con.commit()
    return fresh


def is_stale(published: str, max_age_hours: float = None) -> bool:
    """Deterministic freshness gate: a wire never posts old news as NEW.

    Unparseable dates pass through (triage judges them); parsed-and-old is skipped.
    """
    import datetime
    import email.utils
    if max_age_hours is None:
        max_age_hours = float(__import__("os").environ.get("NBN_MAX_AGE_HOURS", "36"))
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
    age = datetime.datetime.now(datetime.timezone.utc) - dt
    return age.total_seconds() > max_age_hours * 3600


def pending_items(con, limit: int) -> list:
    """Items awaiting triage — includes anything stranded by a crash mid-cycle."""
    rows = con.execute(
        "SELECT url_hash, source, title, url, published_at AS published,"
        " '' AS summary FROM items WHERE status='new' ORDER BY first_seen LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def recent_story_keys(con, days: float = 3.0) -> list:
    """Story keys already POSTED (triage skips duplicates of these)."""
    rows = con.execute(
        "SELECT DISTINCT story_key FROM posts WHERE created > ? ORDER BY created DESC LIMIT 100",
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


def corroboration_count(con, story_key: str) -> int:
    """Distinct publishers whose items map to this story."""
    if not story_key:
        return 0
    row = con.execute(
        "SELECT COUNT(DISTINCT source) n FROM items WHERE story_key=?", (story_key,)
    ).fetchone()
    return row["n"]


def story_already_posted(con, story_key: str) -> bool:
    if not story_key:
        return False
    return con.execute(
        "SELECT 1 FROM posts WHERE story_key=? LIMIT 1", (story_key,)
    ).fetchone() is not None


def set_status(con, url_hash_: str, status: str, story_key: str = None, note: str = None):
    con.execute(
        "UPDATE items SET status=?, story_key=COALESCE(?, story_key), note=COALESCE(?, note) WHERE url_hash=?",
        (status, story_key, note, url_hash_),
    )
    con.commit()


def log_post(con, story_key, item_hash, klass, body, receipt_url, mode, nuelink_id=None):
    con.execute(
        "INSERT INTO posts(created, story_key, item_hash, class, body, receipt_url, mode, nuelink_id)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (time.time(), story_key, item_hash, klass, body, receipt_url, mode, nuelink_id),
    )
    con.commit()


def status_summary(con) -> dict:
    rows = con.execute("SELECT status, COUNT(*) n FROM items GROUP BY status").fetchall()
    posts = con.execute("SELECT COUNT(*) n FROM posts").fetchone()["n"]
    return {"items": {r["status"]: r["n"] for r in rows}, "posts": posts}
