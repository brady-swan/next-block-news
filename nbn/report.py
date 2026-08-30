"""The Desk Report v2: what needs the editor's eyes, then the record — day by day.

Layout answers "what must I see and do?" in priority order:
  status strip -> Needs You -> Published -> The machine's judgment (grouped holds)
  -> Self-audit -> Skips (collapsed). A 7-day activity strip + prev/next navigation
make history browsable; all times are America/Chicago (the desk's clock).
Server-rendered, no JS beyond native <details>; token-gated at /report?k=...
"""
import datetime
import html
import json
import time
from zoneinfo import ZoneInfo

from . import config, store

TZ = ZoneInfo("America/Chicago")

CSS = """
:root{--bg:#0b0e14;--card:#131822;--line:#1e2633;--txt:#d8dee9;--dim:#6b7686;
      --sub:#8fa1b3;--green:#3fb950;--amber:#d29922;--red:#f85149;--blue:#58a6ff;
      --orange:#f0883e}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--txt);font:15px/1.5 -apple-system,system-ui,sans-serif;
     margin:0;padding:0 14px 60px;max-width:780px;margin:auto}
.strip{position:sticky;top:0;background:linear-gradient(var(--bg) 85%,transparent);
       padding:12px 0 8px;z-index:5}
h1{font-size:17px;margin:0 0 4px}
.meta{color:var(--dim);font-size:12.5px}
.pills{margin-top:6px}
.pill{display:inline-block;background:var(--line);border-radius:99px;padding:2px 10px;
      font-size:12px;margin:0 6px 4px 0;color:var(--sub)}
.pill.ok{color:var(--green)} .pill.warn{color:var(--amber)} .pill.err{color:var(--red)}
.days{display:flex;gap:6px;margin:12px 0 4px;overflow-x:auto;padding-bottom:4px}
.day{flex:0 0 auto;text-align:center;background:var(--card);border:1px solid var(--line);
     border-radius:10px;padding:6px 10px;text-decoration:none;color:var(--sub);
     font-size:12px;min-width:64px}
.day b{display:block;color:var(--txt);font-size:15px}
.day.sel{border-color:var(--blue);color:var(--blue)}
.day.sel b{color:var(--blue)}
h2{font-size:13.5px;margin:26px 0 10px;color:var(--sub);text-transform:uppercase;
   letter-spacing:.07em;display:flex;align-items:center;gap:8px}
h2 .n{background:var(--line);border-radius:99px;padding:0 8px;font-size:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;
      padding:12px 14px;margin:10px 0;white-space:pre-wrap;overflow-wrap:anywhere}
.card small{color:var(--dim);display:block;margin-bottom:7px;white-space:normal}
.published{border-left:3px solid var(--green)} .draft{border-left:3px solid var(--amber)}
.held{border-left:3px solid var(--red)} .tape{border-left:3px solid var(--dim)}
.spike{border-left:3px solid var(--orange)}
.need{border:1px solid #3a2d12;background:#1a1508}
a{color:var(--blue);text-decoration:none}
.reason{color:var(--orange)}
.ednote{color:var(--sub);font-size:13px;border-top:1px solid var(--line);
        margin-top:8px;padding-top:7px;white-space:normal}
details{margin:8px 0} summary{cursor:pointer;color:var(--sub);font-size:14px;
        padding:6px 0} summary::marker{color:var(--dim)}
table{width:100%;border-collapse:collapse;font-size:13px}
td{padding:3px 8px 3px 0;color:var(--sub);vertical-align:top}
.empty{color:var(--dim);font-size:14px}
.nav{display:flex;justify-content:space-between;font-size:14px;margin:6px 0 0}
"""


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _ct(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, TZ).strftime("%-I:%M %p")


def _post_card(p, klass_css):
    receipt = (f" · <a href='{_esc(p['receipt_url'])}'>receipt</a>"
               if (p["receipt_url"] or "").startswith("http") else "")
    ed = ""
    try:
        if p["editor_note"]:
            ed = f"<div class=ednote>editor: {_esc(p['editor_note'])}</div>"
    except (KeyError, IndexError):
        pass
    return (f"<div class='card {klass_css}'><small>"
            f"<span class=pill>{_esc(p['class'])}</span>{_ct(p['created'])}"
            f" · {_esc(p['story_key'] or '')}{receipt}</small>"
            f"{_esc(p['body'])}{ed}</div>")


def render(con, day: str = None) -> str:
    now = datetime.datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    day = day or today
    try:
        s, e = store.day_bounds(day)
    except ValueError:
        day, (s, e) = today, store.day_bounds(today)
    is_today = day == today

    posts = con.execute("SELECT * FROM posts WHERE created>=? AND created<? "
                        "ORDER BY created DESC", (s, e)).fetchall()
    held = con.execute("SELECT * FROM items WHERE status='held' AND first_seen>=? AND "
                       "first_seen<? ORDER BY first_seen DESC", (s, e)).fetchall()
    skipped = con.execute("SELECT note, COUNT(*) n FROM items WHERE status='skipped' AND "
                          "first_seen>=? AND first_seen<? GROUP BY note ORDER BY n DESC "
                          "LIMIT 14", (s, e)).fetchall()

    out = [f"<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>NBN Desk</title><style>{CSS}</style>"]

    # ── Status strip ─────────────────────────────────────────────────────────
    fresh_h = store.current_max_age_hours()
    auto = ("<span class='pill ok'>autopost ON · " + ", ".join(sorted(config.AUTOPOST_CLASSES))
            + "</span>") if config.AUTOPOST_ENABLED else "<span class='pill err'>autopost OFF</span>"
    out.append(f"<div class=strip><h1>Next Block News — Desk</h1>"
               f"<div class=meta>{now:%A %B %-d · %-I:%M %p} Central</div>"
               f"<div class=pills>{auto}"
               f"<span class=pill>freshness {fresh_h:g}h</span>"
               f"<span class=pill>editor: {_esc(config.EDITOR_MODEL.replace('claude-',''))}"
               f" @ {_esc(config.EDITOR_EFFORT)}</span></div></div>")

    # ── 7-day strip + day nav ────────────────────────────────────────────────
    out.append("<div class=days>")
    for i in range(6, -1, -1):
        d = (now - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        sm = store.day_summary(con, d)
        label = "today" if d == today else (now - datetime.timedelta(days=i)).strftime("%a")
        sel = " sel" if d == day else ""
        out.append(f"<a class='day{sel}' href='?k={_esc(config.REPORT_TOKEN)}&d={d}'>"
                   f"{label}<b>{sm['published']}</b><span>{sm['seen']} seen</span></a>")
    out.append("</div>")
    prev_d = (datetime.date.fromisoformat(day) - datetime.timedelta(days=1)).isoformat()
    next_d = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()
    nav_next = ("" if is_today else
                f"<a href='?k={_esc(config.REPORT_TOKEN)}&d={next_d}'>{next_d} ›</a>")
    out.append(f"<div class=nav><a href='?k={_esc(config.REPORT_TOKEN)}&d={prev_d}'>"
               f"‹ {prev_d}</a><b>{day}</b>{nav_next}</div>")

    # ── Needs you ────────────────────────────────────────────────────────────
    needs = []
    for p in posts:
        if p["mode"] == "DRAFT":
            needs.append(("Staged draft awaiting your tap in Typefully", _post_card(p, "draft need")))
        if p["mode"] == "TAPE":
            needs.append(("Publish rail failed — post only reached the tape", _post_card(p, "tape need")))
    for h in held:
        note = h["note"] or ""
        if note.startswith("editor spiked"):
            needs.append(("Editor spike — agree or overrule",
                          f"<div class='card spike need'><small><span class=pill>"
                          f"{_esc(h['source'])}</span>{_ct(h['first_seen'])} · "
                          f"<a href='{_esc(h['url'])}'>source</a></small>{_esc(h['title'])}\n"
                          f"<span class=reason>{_esc(note)}</span></div>"))
    audit_raw = store.kv_get(con, "audit:last")
    if audit_raw and is_today:
        a = json.loads(audit_raw)
        for r in a.get("results", []):
            if r.get("verdict") == "material" or not r.get("class_ok", True):
                needs.append(("Self-audit flag",
                              f"<div class='card held need'><small>{_esc(r.get('verdict'))}"
                              f" · class_ok={r.get('class_ok')}</small>{_esc(r.get('title'))}\n"
                              f"<span class=reason>{_esc('; '.join(r.get('findings', [])))}"
                              f"</span></div>"))
    out.append(f"<h2>Needs you <span class=n>{len(needs)}</span></h2>")
    if needs:
        for label, card in needs:
            out.append(f"<div class=meta>{_esc(label)}</div>{card}")
    else:
        out.append("<div class=empty>Nothing. The wire is running itself — "
                   "you can close the tab.</div>")

    # ── Published ────────────────────────────────────────────────────────────
    pub = [p for p in posts if p["mode"] == "IMMEDIATE"]
    out.append(f"<h2>Published <span class=n>{len(pub)}</span></h2>")
    out.extend(_post_card(p, "published") for p in pub) if pub else out.append(
        "<div class=empty>none this day</div>")

    # ── The machine's judgment: holds grouped by reason family ──────────────
    groups = {"Waiting on a second source": [], "Editor spiked": [],
              "Style gate (lint)": [], "Thin source / unverifiable": [], "Other": []}
    for h in held:
        note = h["note"] or ""
        if "second source" in note or "unconfirmed" in note:
            groups["Waiting on a second source"].append(h)
        elif note.startswith("editor spiked"):
            groups["Editor spiked"].append(h)
        elif note.startswith("lint"):
            groups["Style gate (lint)"].append(h)
        elif "thin source" in note or "unverifiable" in note:
            groups["Thin source / unverifiable"].append(h)
        else:
            groups["Other"].append(h)
    out.append(f"<h2>Held <span class=n>{len(held)}</span></h2>")
    for gname, rows in groups.items():
        if not rows:
            continue
        out.append(f"<details><summary>{_esc(gname)} ({len(rows)})</summary>")
        for h in rows:
            out.append(f"<div class='card held'><small><span class=pill>{_esc(h['source'])}"
                       f"</span>{_ct(h['first_seen'])} · <a href='{_esc(h['url'])}'>source</a>"
                       f"</small>{_esc(h['title'])}\n<span class=reason>"
                       f"{_esc(h['note'] or '')}</span></div>")
        out.append("</details>")
    if not held:
        out.append("<div class=empty>none this day</div>")

    # ── Self-audit ───────────────────────────────────────────────────────────
    out.append("<h2>Self-audit</h2>")
    if audit_raw:
        a = json.loads(audit_raw)
        out.append(f"<div class=meta>last run {_esc(a.get('ran'))} · "
                   f"{a.get('posts_checked', 0)} posts checked</div>")
        for r in a.get("results", []):
            css = {"clean": "published", "minor": "draft", "material": "held"}.get(
                r.get("verdict"), "tape")
            flags = ("" if r.get("class_ok", True)
                     else " · <span class=reason>CLASS SUSPECT</span>") + \
                    (" · source drift" if r.get("source_drift") else "")
            out.append(f"<details><summary><span class=pill>{_esc(r.get('verdict'))}</span> "
                       f"{_esc(r.get('title'))}{flags}</summary><div class='card {css}'>"
                       f"{_esc('; '.join(r.get('findings', [])) or 'no findings')}"
                       f"</div></details>")
    else:
        out.append(f"<div class=empty>no audit yet (daily at {_esc(config.AUDIT_UTC)} UTC)</div>")

    # ── Skips (collapsed) ────────────────────────────────────────────────────
    total_skips = sum(sk["n"] for sk in skipped)
    out.append(f"<details><summary><h2 style='display:inline-flex;margin:0'>Skipped "
               f"<span class=n>{total_skips}</span></h2></summary><table>")
    for sk in skipped:
        out.append(f"<tr><td>{sk['n']}</td><td>"
                   f"{_esc(sk['note'] or 'triage: out of scope / duplicate')}</td></tr>")
    out.append("</table></details>")

    return "".join(out)
