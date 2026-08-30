"""The Desk Report: the wire's judgment, skimmable from a phone.

Server-rendered HTML at /report?k=<NBN_REPORT_TOKEN>. Shows what published, what's
staged, what was held and WHY, and what got skipped — the editor's two-minute view.
"""
import datetime
import html
import time

from . import config, store

CSS = """
body{background:#0b0e14;color:#d8dee9;font:15px/1.5 -apple-system,system-ui,sans-serif;
     margin:0;padding:16px;max-width:760px;margin:auto}
h1{font-size:19px;margin:8px 0 2px} h2{font-size:15px;margin:22px 0 8px;color:#8fa1b3;
     text-transform:uppercase;letter-spacing:.06em}
.meta{color:#6b7686;font-size:13px}
.card{background:#131822;border:1px solid #1e2633;border-radius:10px;padding:12px 14px;
      margin:8px 0;white-space:pre-wrap;word-wrap:break-word}
.card small{color:#6b7686;display:block;margin-bottom:6px;white-space:normal}
.published{border-left:3px solid #3fb950}.draft{border-left:3px solid #d29922}
.held{border-left:3px solid #f85149}.tape{border-left:3px solid #6b7686}
.pill{display:inline-block;background:#1e2633;border-radius:99px;padding:1px 9px;
      font-size:12px;margin-right:6px;color:#8fa1b3}
a{color:#58a6ff;text-decoration:none} .reason{color:#f0883e}
table{width:100%;border-collapse:collapse;font-size:13px}
td{padding:3px 8px 3px 0;color:#8fa1b3;vertical-align:top}
"""


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _ago(ts: float) -> str:
    m = int((time.time() - ts) / 60)
    return f"{m}m ago" if m < 90 else f"{m // 60}h {m % 60}m ago"


def render(con, hours: float = 26.0) -> str:
    cutoff = time.time() - hours * 3600
    now = datetime.datetime.now(datetime.timezone.utc)

    posts = con.execute(
        "SELECT * FROM posts WHERE created > ? ORDER BY created DESC", (cutoff,)).fetchall()
    held = con.execute(
        "SELECT * FROM items WHERE status='held' AND first_seen > ? ORDER BY first_seen DESC",
        (cutoff,)).fetchall()
    skipped = con.execute(
        "SELECT note, COUNT(*) n FROM items WHERE status='skipped' AND first_seen > ?"
        " GROUP BY note ORDER BY n DESC LIMIT 12", (cutoff,)).fetchall()
    counts = con.execute(
        "SELECT status, COUNT(*) n FROM items WHERE first_seen > ? GROUP BY status",
        (cutoff,)).fetchall()

    out = [f"<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>NBN Desk Report</title><style>{CSS}</style>"]
    out.append(f"<h1>Next Block News — Desk Report</h1>"
               f"<div class=meta>{now:%a %b %d, %H:%M} UTC · last {int(hours)}h · "
               f"autopost {'ON' if config.AUTOPOST_ENABLED else 'OFF'} "
               f"({', '.join(sorted(config.AUTOPOST_CLASSES))}) · "
               f"freshness window {store.current_max_age_hours()}h</div>")

    intake = " · ".join(f"{r['status']}: {r['n']}" for r in counts) or "nothing new"
    out.append(f"<h2>Intake</h2><div class=meta>{_esc(intake)}</div>")

    by_mode = {"IMMEDIATE": [], "DRAFT": [], "TAPE": []}
    for p in posts:
        by_mode.setdefault(p["mode"], []).append(p)

    def cards(rows, klass):
        for p in rows:
            receipt = (f"<a href='{_esc(p['receipt_url'])}'>receipt</a>"
                       if p["receipt_url"] and p["receipt_url"].startswith("http") else "")
            out.append(
                f"<div class='card {klass}'><small>"
                f"<span class=pill>{_esc(p['class'])}</span>"
                f"{_ago(p['created'])} · {_esc(p['story_key'] or '')} {receipt}</small>"
                f"{_esc(p['body'])}</div>")

    out.append(f"<h2>Published autonomously ({len(by_mode['IMMEDIATE'])})</h2>")
    cards(by_mode["IMMEDIATE"], "published") if by_mode["IMMEDIATE"] else out.append(
        "<div class=meta>none</div>")

    out.append(f"<h2>Staged as drafts ({len(by_mode['DRAFT'])})</h2>")
    cards(by_mode["DRAFT"], "draft") if by_mode["DRAFT"] else out.append(
        "<div class=meta>none</div>")

    if by_mode["TAPE"]:
        out.append(f"<h2>Tape only — publish rail unavailable ({len(by_mode['TAPE'])})</h2>")
        cards(by_mode["TAPE"], "tape")

    out.append(f"<h2>Held, with reasons ({len(held)})</h2>")
    for h in held:
        out.append(
            f"<div class='card held'><small><span class=pill>{_esc(h['source'])}</span>"
            f"{_ago(h['first_seen'])} · <a href='{_esc(h['url'])}'>source</a></small>"
            f"{_esc(h['title'])}\n<span class=reason>{_esc(h['note'] or 'no reason recorded')}"
            f"</span></div>")
    if not held:
        out.append("<div class=meta>none</div>")

    out.append("<h2>Skip reasons (top)</h2><table>")
    for s in skipped:
        out.append(f"<tr><td>{s['n']}</td><td>{_esc(s['note'] or 'triage: out of scope/dup')}"
                   f"</td></tr>")
    out.append("</table>")
    return "".join(out)
