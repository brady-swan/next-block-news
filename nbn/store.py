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
  first_seen REAL, status TEXT DEFAULT 'new',
  -- new|skipped|held|drafted|posted|uncertain|failed|taped|error
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

MIGRATIONS = ["ALTER TABLE posts ADD COLUMN editor_note TEXT"]


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
    for mig in MIGRATIONS:
        try:
            con.execute(mig)
        except sqlite3.OperationalError:
            pass  # already applied
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
        " '' AS summary FROM items WHERE status='new' ORDER BY first_seen LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def recent_story_keys(con, days: float = 3.0) -> list:
    """Story keys readers saw or may have seen (authorizes UPDATE handling)."""
    rows = con.execute(
        "SELECT DISTINCT story_key FROM posts WHERE created > ?"
        " AND mode IN ('IMMEDIATE','UNCERTAIN') ORDER BY created DESC LIMIT 100",
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


def set_status(con, url_hash_: str, status: str, story_key: str = None, note: str = None):
    con.execute(
        "UPDATE items SET status=?, story_key=COALESCE(?, story_key), note=COALESCE(?, note) WHERE url_hash=?",
        (status, story_key, note, url_hash_),
    )
    con.commit()


def log_post(con, story_key, item_hash, klass, body, receipt_url, mode, publisher_ref=None,
             editor_note=None):
    """Record a produced post. nuelink_id is the legacy schema name for any backend ref."""
    con.execute(
        "INSERT INTO posts(created, story_key, item_hash, class, body, receipt_url, mode,"
        " nuelink_id, editor_note) VALUES (?,?,?,?,?,?,?,?,?)",
        (time.time(), story_key, item_hash, klass, body, receipt_url, mode, publisher_ref,
         editor_note),
    )
    con.commit()


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
    posts = con.execute(
        "SELECT COUNT(*) n FROM posts WHERE created>=? AND created<? AND mode='IMMEDIATE'",
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
    seen = con.execute(
        "SELECT COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<?", (s, e)).fetchone()["n"]
    return {"published": posts, "drafts": drafts, "uncertain": uncertain,
            "failed": failed, "tape": tape, "held": held, "seen": seen}


def status_summary(con) -> dict:
    rows = con.execute("SELECT status, COUNT(*) n FROM items GROUP BY status").fetchall()
    posts = con.execute("SELECT COUNT(*) n FROM posts").fetchone()["n"]
    return {"items": {r["status"]: r["n"] for r in rows}, "posts": posts}
