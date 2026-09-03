"""The Desk Report v3 — "Filed, action-first" (Claude Design turn 2, option 2a).

Ported from Desk Report Refresh.dc.html: IBM Plex Sans/Mono, panel-and-hairline,
verb-led needs-you cards with full-width tap targets, 7-day strip with jump-link
counts, lede-only published cards (the charter's standalone atom makes the summary
lossless), grouped holds and audit in hairline stacks. All times America/Chicago.
Server-rendered, native <details> only, token-gated at /report?k=...
"""
import datetime
import html
import json
import time
from zoneinfo import ZoneInfo

from . import config, store

TZ = ZoneInfo("America/Chicago")
PROFILE_URL = "https://x.com/nextblocknews_"
TYPEFULLY_URL = "https://typefully.com"
LOGO_B64 = "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"
LOGO_IMG = (f'<img src="data:image/png;base64,{LOGO_B64}" width="22" height="22" '
            f'alt="Next Block News" style="display:block;border-radius:5px;flex:none">')

CSS = """
:root{
  --bg:#07090b; --panel:#0e1218; --panel2:#141a22;
  --line:#1c232d; --line2:#2a333f;
  --txt:#dfe5ec; --sub:#93a2b3; --dim:#5c6875;
  --green:#3fb950; --amber:#d2a02b; --red:#f85149; --orange:#f7931a; --link:#58a6ff;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,monospace;
  --sans:'IBM Plex Sans',system-ui,sans-serif;
}
*{box-sizing:border-box}
body{margin:0 auto;max-width:780px;background:var(--bg);color:var(--txt);
     font:400 15px/1.5 var(--sans);padding:0 16px 44px}
a{color:var(--link);text-decoration:none} a:hover{color:var(--orange)}
summary{cursor:pointer;list-style:none}
summary::-webkit-details-marker{display:none}
summary::after{content:'+';float:right;font-family:var(--mono);color:var(--dim)}
details[open]>summary::after{content:'\\2013'}
.strip{position:sticky;top:0;z-index:5;padding:14px 0 12px;
       background:linear-gradient(180deg,var(--bg) 0,var(--bg) 78%,rgba(7,9,11,0) 100%)}
.ident{display:flex;align-items:center;gap:9px}
.ident .name{font:600 14px/1.1 var(--sans);letter-spacing:.01em;flex:1}
.ident .name span{color:var(--dim);font-weight:400}
.dot{width:7px;height:7px;border-radius:99px;background:var(--green);
     box-shadow:0 0 0 3px rgba(63,185,80,.16)}
.pills{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}
.pill{font:500 11px/1 var(--mono);letter-spacing:.04em;text-transform:uppercase;
      color:var(--sub);background:var(--panel2);border:1px solid var(--line);
      border-radius:4px;padding:5px 8px;white-space:nowrap}
.pill.on{color:var(--green);background:rgba(63,185,80,.1);border-color:rgba(63,185,80,.28)}
.pill.off{color:var(--red);background:rgba(248,81,73,.1);border-color:rgba(248,81,73,.28)}
.pill.warn{color:var(--amber);background:rgba(210,160,43,.1);border-color:rgba(210,160,43,.28)}
.clock{font:400 12px/1.4 var(--sans);color:var(--sub);margin-top:9px}
h2{display:flex;align-items:center;gap:8px;font:600 11px/1 var(--mono);
   letter-spacing:.12em;text-transform:uppercase;color:var(--sub);margin:26px 0 10px}
h2 .fill{flex:1}
h2.needs{color:var(--orange)}
.count{font:600 11px/1 var(--mono);border-radius:3px;padding:3px 6px}
.count.o{color:var(--bg);background:var(--orange)}
.count.g{color:var(--green);background:rgba(63,185,80,.12)}
.count.r{color:var(--red);background:rgba(248,81,73,.12)}
.emptybox{border:1px dashed var(--line2);border-radius:10px;padding:26px 18px;text-align:center}
.emptybox b{font:500 15px/1.4 var(--sans);color:var(--txt);display:block}
.emptybox span{font:400 13.5px/1.5 var(--sans);color:var(--dim);margin-top:3px;display:block}
.flow{display:grid;grid-template-columns:repeat(5,1fr);gap:1px;background:var(--line);
      border:1px solid var(--line);border-radius:9px;overflow:hidden;margin-top:14px}
.flow div{background:var(--panel);padding:8px 5px;text-align:center}
.flow b{display:block;font:600 15px/1.2 var(--mono);color:var(--txt)}
.flow span{display:block;margin-top:3px;font:500 9px/1.2 var(--mono);letter-spacing:.05em;
           text-transform:uppercase;color:var(--dim)}
.stack{display:flex;flex-direction:column;gap:12px}
.need{background:var(--panel);border:1px solid var(--line2);border-radius:10px;overflow:hidden}
.verb{display:flex;align-items:center;gap:9px;border-bottom:1px solid var(--line);padding:9px 13px}
.verb b{font:600 12.5px/1 var(--mono);letter-spacing:.03em;flex:1}
.verb span{font:400 11.5px/1 var(--mono);color:var(--sub)}
.verb.amber{background:rgba(210,160,43,.1)} .verb.amber b{color:var(--amber)}
.verb.red{background:rgba(248,81,73,.1)} .verb.red b{color:var(--red)}
.verb.orange{background:rgba(247,147,26,.1)} .verb.orange b{color:var(--orange)}
.need .body{padding:11px 13px}
.need .body p{margin:0;font:400 14.5px/1.5 var(--sans);white-space:pre-wrap;overflow-wrap:anywhere}
.need .ednote{margin:9px 0 0;font:400 13.5px/1.5 var(--sans);color:var(--orange)}
.acts{display:flex;border-top:1px solid var(--line)}
.acts a{flex:1;text-align:center;min-height:32px;display:flex;align-items:center;
        justify-content:center;font:600 12.5px/1 var(--mono);letter-spacing:.04em;
        background:rgba(247,147,26,.1);border-right:1px solid var(--line);color:var(--orange)}
.acts a.sec{flex:none;min-width:116px;font-weight:500;background:none;border-right:none;
            color:var(--sub)}
.itemacts{display:flex;gap:7px;align-items:center;flex-wrap:wrap;margin-top:10px}
.itemacts form{margin:0}
.itemacts button{appearance:none;border:1px solid rgba(247,147,26,.4);border-radius:5px;
                 background:rgba(247,147,26,.1);color:var(--orange);cursor:pointer;
                 padding:7px 10px;font:600 11.5px/1 var(--mono);letter-spacing:.03em}
.itemacts button.dismiss{border-color:var(--line2);background:none;color:var(--sub)}
.itemacts .actionstatus{font:500 11.5px/1.4 var(--mono);color:var(--amber)}
.days{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
.day{text-decoration:none;background:var(--panel);border:1px solid var(--line);
     border-radius:8px;padding:7px 0 6px;text-align:center}
.day div{font:400 10px/1.3 var(--mono)}
.day .lbl{font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:var(--dim)}
.day .pub{font:600 15px/1.2 var(--mono);color:var(--green);margin-top:4px}
.day .h{color:var(--red)} .day .s{color:var(--dim)}
.day.today{background:rgba(247,147,26,.08);border-color:var(--orange)}
.day.today .lbl{color:var(--orange);font-weight:600}
.day.today .pub{color:var(--txt)}
.day.sel{border-color:var(--link)} .day.sel .lbl{color:var(--link)}
.day.stall .lbl{color:var(--red)}
.dnav{display:flex;align-items:center;justify-content:space-between;margin-top:8px;
      font:500 12px/1 var(--mono)}
.dnav .mid{color:var(--sub);letter-spacing:.04em}
.dnav .off{color:var(--line2)}
.jumps{display:flex;flex-wrap:wrap;gap:12px;margin-top:9px;font:500 12px/1 var(--mono)}
.rec{background:var(--panel);border:1px solid var(--line);border-left:2px solid var(--green);
     border-radius:0 10px 10px 0}
.rec summary{padding:11px 13px}
.gut{display:flex;gap:8px;align-items:baseline;font:400 11.5px/1 var(--mono);
     color:var(--dim);margin-bottom:7px}
.gut .cls{color:var(--green);font-weight:500;text-transform:uppercase}
.gut .t{color:var(--sub)}
.gut .key{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lede{font:400 14.5px/1.45 var(--sans);color:var(--txt);padding-right:14px;
      white-space:pre-wrap;overflow-wrap:anywhere}
.rest{padding:0 13px 12px}
.rest p{margin:0;font:400 14.5px/1.5 var(--sans);color:var(--sub);white-space:pre-wrap;
        overflow-wrap:anywhere}
.edblock{margin-top:10px;padding-top:9px;border-top:1px solid var(--line)}
.edblock .lab{font:500 10.5px/1 var(--mono);letter-spacing:.09em;text-transform:uppercase;
              color:var(--dim);margin-bottom:5px}
.edblock .lab.rev{color:var(--amber)}
.edblock p{margin:0;font:400 13.5px/1.5 var(--sans);color:var(--sub)}
.links{display:flex;gap:16px;margin-top:10px;font:500 12.5px/1 var(--mono)}
.hstack{display:flex;flex-direction:column;gap:1px;background:var(--line);
        border:1px solid var(--line);border-radius:10px;overflow:hidden}
.hstack details{background:var(--panel)}
.hstack summary{padding:11px 13px;font:500 13px/1.3 var(--sans);color:var(--txt)}
.hstack summary .n{font:400 12px var(--mono);color:var(--dim)}
.hentry{border-left:2px solid var(--red);padding-left:10px;margin:0 13px 9px}
.hentry .m{font:400 11.5px/1 var(--mono);color:var(--dim);margin-bottom:5px}
.hentry .ttl{font:400 14px/1.45 var(--sans)}
.hentry .why{font:400 12.5px/1.4 var(--mono);color:var(--red);margin-top:4px;
             overflow-wrap:anywhere}
.mailentry{border-left-color:var(--dim)}
.mailentry .why{color:var(--sub)}
.decision{border-left:2px solid var(--orange)}
.decision summary{padding:11px 13px}
.decision .route{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:7px}
.decision .route .chip{margin:0;color:var(--sub);border-color:var(--line2)}
.decision .route .final{color:var(--orange);border-color:rgba(247,147,26,.35)}
.decision .ttl{font:500 14px/1.4 var(--sans);color:var(--txt);padding-right:18px}
.decision .meta{font:400 11.5px/1.4 var(--mono);color:var(--dim);margin-top:5px}
.decision .body{padding:0 13px 12px;color:var(--sub);font-size:13px}
.decision .body p{margin:6px 0 0}
.decision .themes{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.decision .themes .chip{color:var(--sub);border-color:var(--line2);margin:0}
.decision .themectx{font:400 12px/1.5 var(--mono);color:var(--dim);margin-top:6px}
.countdefs{margin-top:10px;border:1px solid var(--line);border-radius:8px;background:var(--panel)}
.countdefs summary{padding:9px 11px;font:500 11px/1.3 var(--mono);color:var(--sub)}
.countdefs .body{padding:0 11px 10px;font:400 12.5px/1.5 var(--sans);color:var(--dim)}
.countdefs .body p{margin:5px 0}
.chip{font:500 10.5px var(--mono);letter-spacing:.08em;border-radius:3px;padding:2px 5px;
      margin-right:7px;border:1px solid}
.chip.material{color:var(--red);border-color:rgba(248,81,73,.4)}
.chip.minor{color:var(--amber);border-color:rgba(210,160,43,.4)}
.chip.clean{color:var(--green);border-color:rgba(63,185,80,.4)}
.chip.unverifiable{color:var(--dim);border-color:var(--line2)}
.audrow summary{font:400 13.5px/1.4 var(--sans);color:var(--txt)}
.audrow .find{padding:0 13px 12px;font:400 13.5px/1.5 var(--sans);color:var(--sub)}
.skipbox{margin-top:22px;background:var(--panel);border:1px solid var(--line);border-radius:10px}
.skipbox summary{padding:11px 13px;font:600 11px/1 var(--mono);letter-spacing:.12em;
                 text-transform:uppercase;color:var(--sub)}
.skipbox td{padding:3px 13px 3px 0;font:400 12.5px/1.5 var(--mono);color:var(--sub);
            vertical-align:top}
.skipbox td.n{padding:3px 13px;width:34px;color:var(--txt);text-align:right}
.metaline{font:400 12px/1.4 var(--mono);color:var(--dim);margin-bottom:9px}
.suspect{font:400 11.5px var(--mono);color:var(--red)}
.empty{color:var(--dim);font-size:14px}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600'
         '&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">')


def _esc(s) -> str:
    return html.escape(str(s or ""))


def _bounded_count(value, limit: int = 1000) -> int:
    if isinstance(value, bool):
        return 0
    try:
        return max(0, min(int(value), limit))
    except (TypeError, ValueError):
        return 0


def _ct(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, TZ).strftime("%-I:%M %p")


def _u(day=None):
    base = f"?k={config.REPORT_TOKEN}"
    return base + (f"&d={day}" if day else "")


def _split_lede(body: str):
    parts = (body or "").split("\n", 1)
    rest = parts[1].strip() if len(parts) > 1 else ""
    return parts[0], rest


def _ed_parts(note):
    if not note:
        return None, None
    verdict, _, reason = note.partition(":")
    return verdict.strip(), reason.strip()


def _age(ts: float, now: float) -> str:
    seconds = max(0, now - ts)
    if seconds < 90:
        return "just now"
    if seconds < 3600:
        return f"{int(seconds // 60)}m ago"
    return f"{int(seconds // 3600)}h ago"


def _iso_age(value, now: float) -> str:
    if not value:
        return "unknown"
    try:
        timestamp = datetime.datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).timestamp()
    except (TypeError, ValueError):
        return "unknown"
    return _age(timestamp, now)


def _decision_theme_context(item: dict, coverage_by_id: dict, now_ts: float) -> str:
    signals = item.get("theme_signals") if isinstance(item.get("theme_signals"), list) else []
    signal_by_id = {
        row.get("theme_id"): row for row in signals
        if isinstance(row, dict) and row.get("theme_id")
    }
    ids = item.get("theme_ids") if isinstance(item.get("theme_ids"), list) else []
    if not ids:
        return ""
    chips = []
    details = []
    for theme_id in ids[:2]:
        signal = signal_by_id.get(theme_id, {})
        coverage = coverage_by_id.get(theme_id, {})
        name = signal.get("name") or coverage.get("name") or theme_id
        chips.append(f"<span class=chip>Node theme · {_esc(name)}</span>")
        trajectory = signal.get("trajectory") or coverage.get("trajectory") or "unknown"
        count = signal.get("count_7d")
        count_text = str(count) if isinstance(count, int) else "unknown"
        evidence_age = _iso_age(
            signal.get("last_evidence_at") or coverage.get("last_evidence_at"), now_ts)
        if coverage.get("coverage_known"):
            parts = []
            if coverage.get("last_published_at"):
                parts.append(f"published {_age(float(coverage['last_published_at']), now_ts)}")
            if coverage.get("open_draft"):
                parts.append("open draft")
            coverage_text = " / ".join(parts) or "known tagged history"
        else:
            coverage_text = "unknown"
        details.append(
            f"<div class=themectx>Node activity: {_esc(trajectory)} · "
            f"{_esc(count_text)} evidence items / 7d · latest {_esc(evidence_age)}<br>"
            f"NBN coverage: {_esc(coverage_text)}</div>"
        )
    if len(ids) > 2:
        chips.append(f"<span class=chip>+{len(ids) - 2}</span>")
    return f"<div class=themes>{''.join(chips)}</div>{''.join(details)}"


def _kv_float(con, key: str) -> float:
    try:
        return float(store.kv_get(con, key) or 0)
    except ValueError:
        return 0


def _kv_iso_ts(con, key: str) -> float:
    value = store.kv_get(con, key)
    if not value:
        return 0
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0


def _freshness_pills(con, now_ts: float) -> str:
    worker = _kv_float(con, "worker:last_success")
    if worker:
        worker_class = " off" if now_ts - worker > 600 else ""
        worker_html = f"<span class='pill{worker_class}'>cycle {_age(worker, now_ts)}</span>"
    else:
        worker_html = "<span class='pill warn'>cycle pending</span>"

    if not (config.TYPEFULLY_API_KEY and config.TYPEFULLY_SOCIAL_SET_ID):
        publisher_html = "<span class=pill>publisher sync off</span>"
    else:
        synced = _kv_float(con, "publisher:last_success")
        error = store.kv_get(con, "publisher:last_error")
        if error:
            publisher_html = (f"<span class='pill off' title='{_esc(error)}'>"
                              "publisher sync error</span>")
        elif synced:
            sync_class = " off" if now_ts - synced > 900 else ""
            publisher_html = (f"<span class='pill{sync_class}'>"
                              f"publisher sync {_age(synced, now_ts)}</span>")
        else:
            publisher_html = "<span class='pill warn'>publisher sync pending</span>"
    if not config.NODE_READ_TOKEN:
        node_html = "<span class=pill>Node discovery off</span>"
    else:
        node_error = store.kv_get(con, "node:last_error")
        pulse_generated = _kv_iso_ts(con, "node:last_pulse_generated")
        if node_error:
            node_html = (f"<span class='pill off' title='{_esc(node_error)}'>"
                         "Node discovery error</span>")
        elif pulse_generated:
            stale_class = " off" if now_ts - pulse_generated > config.NODE_PULSE_MAX_AGE_SECONDS \
                else ""
            run_id = store.kv_get(con, "node:last_pulse_run_id")
            status = store.kv_get(con, "node:last_pulse_status")
            count = store.kv_get(con, "node:last_pulse_candidates") or "0"
            providers = store.kv_get(con, "node:last_pulse_providers")
            node_html = (f"<span class='pill{stale_class}' title='{_esc(providers)}'>"
                         f"Node pulse #{_esc(run_id)} {_esc(status)} · {count} leads · "
                         f"{_age(pulse_generated, now_ts)}</span>")
        else:
            node_html = "<span class='pill warn'>Node discovery pending</span>"
    return worker_html + publisher_html + node_html


def _dismissed(con, kind, ref) -> bool:
    return bool(store.kv_get(con, f"dismissed:{kind}:{ref}"))


def _dismiss_link(kind, ref, day):
    return (f"<a class=sec href='/dismiss?k={config.REPORT_TOKEN}&kind={kind}&id={ref}&d={day}' "
            f"style='color:var(--dim)'>dismiss ✓</a>")


def _hold_label(note: str) -> str:
    gate = store.hold_gate(note)
    if gate:
        return gate
    value = str(note or "").lower()
    if value.startswith("research pending:") or value.startswith("research exhausted:"):
        return "research infrastructure"
    if value.startswith("source policy:") or "source unresolved" in value:
        return "source"
    if "thin source" in value:
        return "thin source"
    if value.startswith("update lacks"):
        return "coverage"
    return "held"


def _item_controls(con, item_hash: str, day: str) -> str:
    current = con.execute(
        "SELECT status,note FROM items WHERE url_hash=?", (item_hash,)
    ).fetchone()
    action = store.latest_operator_action(con, item_hash)
    if action and action["state"] in ("queued", "processing"):
        noun = "research retry" if action["action"] == "retry" else "draft request"
        label = f"{noun} · awaiting next run" if action["state"] == "queued" \
            else f"{noun} processing"
        return f"<div class=itemacts><span class=actionstatus>{_esc(label)}</span></div>"
    if not current or current["status"] != "held":
        if action and action["action"] == "dismiss" and action["state"] == "completed":
            return "<div class=itemacts><span class=actionstatus>dismissed</span></div>"
        return ""
    hidden = (f"<input type=hidden name=k value='{_esc(config.REPORT_TOKEN)}'>"
              f"<input type=hidden name=id value='{_esc(item_hash)}'>"
              f"<input type=hidden name=d value='{_esc(day)}'>")
    buttons = []
    research = con.execute(
        "SELECT state FROM research_jobs WHERE item_hash=?", (item_hash,)
    ).fetchone()
    if research and research["state"] in {"pending", "exhausted"}:
        buttons.append(
            f"<form method=post action='/item-action'>{hidden}"
            "<input type=hidden name=action value=retry>"
            "<button type=submit>RETRY RESEARCH → DRAFT</button></form>"
        )
    if store.hold_gate(current["note"]):
        buttons.append(
            f"<form method=post action='/item-action'>{hidden}"
            "<input type=hidden name=action value=stage>"
            "<button type=submit>STAGE DRAFT</button></form>"
        )
    buttons.append(
        f"<form method=post action='/item-action'>{hidden}"
        "<input type=hidden name=action value=dismiss>"
        "<button class=dismiss type=submit "
        "onclick=\"return confirm('Dismiss this item?')\">DISMISS</button></form>"
    )
    return f"<div class=itemacts>{''.join(buttons)}</div>"


def _mailroom_control(row: dict, day: str) -> str:
    if row.get("promoted_at") is not None:
        return "<div class=itemacts><span class=actionstatus>sent to desk</span></div>"
    if (row.get("status") != "skipped" or row.get("decision_stage") != "intake_triage"
            or row.get("decision_category") != "background"):
        return ""
    hidden = (f"<input type=hidden name=k value='{_esc(config.REPORT_TOKEN)}'>"
              f"<input type=hidden name=id value='{_esc(row.get('item_hash'))}'>"
              f"<input type=hidden name=d value='{_esc(day)}'>")
    return (f"<div class=itemacts><form method=post action='/item-action'>{hidden}"
            "<input type=hidden name=action value=promote>"
            "<button type=submit>SEND TO DESK</button></form></div>")


def render(con, day: str = None) -> str:
    now = datetime.datetime.now(TZ)
    now_ts = time.time()
    today = now.strftime("%Y-%m-%d")
    day = day or today
    try:
        s, e = store.day_bounds(day)
    except ValueError:
        day, (s, e) = today, store.day_bounds(today)
    is_today = day == today

    effective_ts = store.effective_post_ts_sql("p")
    posts = con.execute(
        "SELECT p.*, r.original_source AS resolution_original_source,"
        " r.original_tier AS resolution_original_tier,"
        " r.selected_source AS resolution_selected_source,"
        " r.selected_tier AS resolution_selected_tier, r.status AS resolution_status,"
        " r.note AS resolution_note,"
        f" {effective_ts} AS effective_at,"
        " (SELECT COUNT(*) FROM source_evidence ev WHERE ev.item_hash=p.resolution_id"
        "  AND ev.support_verdict=1 AND ev.receipt_eligible=1) AS resolution_evidence_count"
        " FROM posts p"
        " LEFT JOIN source_resolutions r ON r.item_hash=p.resolution_id"
        f" WHERE {effective_ts}>=? AND {effective_ts}<? ORDER BY effective_at DESC",
        (s, e)).fetchall()
    held = con.execute(
        "SELECT i.*, r.original_tier AS resolution_original_tier,"
        " r.selected_source AS resolution_selected_source,"
        " r.selected_tier AS resolution_selected_tier, r.status AS resolution_status,"
        " r.note AS resolution_note FROM items i"
        " LEFT JOIN source_resolutions r ON r.item_hash=i.url_hash"
        " WHERE i.status='held' AND i.first_seen>=? AND i.first_seen<?"
        " ORDER BY i.first_seen DESC", (s, e)).fetchall()
    skipped = con.execute("SELECT note, COUNT(*) n FROM items WHERE status='skipped' AND "
                          "first_seen>=? AND first_seen<? GROUP BY note ORDER BY n DESC "
                          "LIMIT 14", (s, e)).fetchall()
    summary = store.day_summary(con, day)
    backlog = {
        row["state"]: row["n"] for row in con.execute(
            "SELECT state,COUNT(*) n FROM research_jobs"
            " WHERE state IN ('pending','processing','exhausted') GROUP BY state"
        ).fetchall()
    }
    activity_allowed = {
        "research_started": "research started",
        "research_completed": "research completed",
        "research_failed": "research failed",
        "node_packet_rejected": "Node packets rejected",
        "node_packet_dropped": "Node packets downgraded",
        "guide_lead_advanced": "guide leads advanced",
        "research_recovery_requeued": "recovery requeued",
    }
    event_rows = con.execute(
        "SELECT event,item_hash,metadata FROM pipeline_events WHERE at>=? AND at<?",
        (s, e),
    ).fetchall()
    activity_sets = {key: set() for key in activity_allowed}
    typed_failure_sets = {
        key: set() for key in (
            "support_assessment_timeout", "search_timeout", "source_fetch",
            "exhausted", "unknown",
        )
    }
    recovery_count = 0
    for row in event_rows:
        event = row["event"]
        if event.startswith("research_failed:"):
            activity_sets["research_failed"].add(row["item_hash"])
        elif event in activity_sets and event != "research_recovery_requeued":
            activity_sets[event].add(row["item_hash"])
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except (TypeError, ValueError):
            metadata = {}
        if event.startswith("research_failed:"):
            kind = event.partition(":")[2] or str(metadata.get("error_kind") or "unknown")
            if kind not in typed_failure_sets:
                kind = "unknown"
            typed_failure_sets[kind].add(row["item_hash"])
        elif event == "research_recovery_requeued":
            recovery_count += _bounded_count(metadata.get("count", 0))
    activity = {key: len(values) for key, values in activity_sets.items()}
    activity["research_recovery_requeued"] = recovery_count
    audit_raw = store.kv_get(con, "audit:last")
    audit = json.loads(audit_raw) if audit_raw else None
    decision_raw = store.kv_get(con, "desk:last_decision_run")
    try:
        decision_run = json.loads(decision_raw) if decision_raw else None
    except (TypeError, ValueError):
        decision_run = None
    coverage_by_id = {
        row.get("theme_id"): row
        for row in (decision_run or {}).get("theme_coverage_snapshot", [])
        if isinstance(row, dict) and row.get("theme_id")
    }
    usage = store.model_usage_summary(con, s)
    mailroom_usage = store.model_usage_seat_summary(
        con, seat="rss_triage", since=s, until=e
    )
    mailroom = store.intake_triage_summary(con, s, e)
    mailroom_sources = store.intake_triage_source_summary(con, s, e, limit=12)
    mailroom_background = store.intake_triage_background(con, s, e, limit=25)
    try:
        next_editorial = float(store.kv_get(con, "editorial:next_run_at") or 0)
    except ValueError:
        next_editorial = 0
    latest_newsroom = store.latest_newsroom_run(con)
    latest_story_commits = []
    if latest_newsroom:
        latest_story_commits = con.execute(
            "SELECT story_id,state,details_json FROM newsroom_story_commits"
            " WHERE run_id=? ORDER BY story_id LIMIT 25",
            (latest_newsroom["run_id"],),
        ).fetchall()

    out = ["<!doctype html><meta charset=utf-8>"
           "<meta name=viewport content='width=device-width,initial-scale=1'>"
           f"<title>NBN Desk</title>"
           f"<link rel=icon type=image/png href='data:image/png;base64,{LOGO_B64}'>"
           f"{FONTS}<style>{CSS}</style>"]

    # ── Status strip ─────────────────────────────────────────────────────────
    auto = (f"<span class='pill on'>autopost on · "
            f"{', '.join(sorted(config.AUTOPOST_CLASSES))}</span>"
            if config.AUTOPOST_ENABLED else "<span class='pill off'>autopost off</span>")
    out.append(
        f"<div class=strip><div class=ident>{LOGO_IMG}"
        f"<div class=name>Next Block News <span>· Desk</span></div>"
        f"<span class=dot></span></div>"
        f"<div class=pills>{auto}"
        f"{_freshness_pills(con, now_ts)}"
        f"<span class=pill>source policy: {_esc(config.SOURCE_POLICY_MODE)}</span>"
        f"<span class=pill>direct Perception: {'on' if config.PERCEPTION_DIRECT_ENABLED else 'off'}</span>"
        f"<span class=pill>X guides + detectors: {'on' if config.X_DETECTOR_ENABLED else 'off'}</span>"
        f"<span class=pill>editorial core: {_esc(config.EDITORIAL_ENGINE)}</span>"
        f"<span class=pill>mailroom: {_esc(config.INTAKE_TRIAGE_MODE)} · "
        f"{_esc(config.INTAKE_TRIAGE_MODEL.replace('claude-', ''))}</span>"
        f"<span class=pill>desk every {config.DESK_INTERVAL_SECONDS // 60}m · "
        f"intake {config.DESK_CANDIDATE_MAX_AGE_HOURS:g}h</span>"
        f"<span class=pill>writer: {_esc(config.ANTHROPIC_MODEL.replace('claude-', ''))}"
        f" @ high</span>"
        f"<span class=pill>editor: {_esc(config.EDITOR_MODEL.replace('claude-', ''))}"
        f" @ {_esc(config.EDITOR_EFFORT)}</span></div>"
        f"<div class=clock>{now:%A %B %-d · %-I:%M %p} Central</div></div>")

    next_text = (_ct(next_editorial) if next_editorial else "on next worker cycle")
    out.append(
        "<h2><span class=fill>Editorial core v2</span></h2>"
        f"<div class=metaline><b>Next desk</b> · {_esc(next_text)} Central<br>"
        f"<b>Selected day model usage</b> · {_bounded_count(usage.get('calls', 0), 10000)} calls"
        f" · {_bounded_count(usage.get('input_tokens', 0), 100000000)} input"
        f" · {_bounded_count(usage.get('output_tokens', 0), 100000000)} output"
        f" · {_bounded_count(usage.get('cache_read_input_tokens', 0), 100000000)} cache-read"
        f" · estimated ${float(usage.get('estimated_cost_usd', 0) or 0):.4f}"
        f" · rates {_esc(store.MODEL_RATE_VERSION)}</div>"
    )
    if latest_newsroom:
        commit_bits = []
        for row in latest_story_commits:
            try:
                detail = json.loads(row["details_json"] or "{}")
            except (TypeError, ValueError):
                detail = {}
            warning_count = len(detail.get("warnings") or []) if isinstance(detail, dict) else 0
            reason = str(detail.get("reason") or "")[:120] if isinstance(detail, dict) else ""
            label = f"{row['story_id']}: {row['state']}"
            if warning_count:
                label += f" · {warning_count} warning{'s' if warning_count != 1 else ''}"
            if reason:
                label += f" · {reason}"
            commit_bits.append(_esc(label))
        out.append(
            "<div class=metaline><b>Latest newsroom lifecycle</b> · "
            f"{_esc(latest_newsroom['run_id'])} · {_esc(latest_newsroom['status'])} · "
            + ("<br>".join(commit_bits) if commit_bits else "no dossier stories")
            + (f"<br><b>Run issue</b> · {_esc(latest_newsroom['error_kind'])}: "
               f"{_esc(latest_newsroom['error_message'])}"
               if latest_newsroom["error_kind"] else "")
            + "</div>"
        )
    try:
        from .newsroom import ORIENTATION_BRIEF
        orientation = ORIENTATION_BRIEF
    except Exception:  # noqa: BLE001 - report must remain available during deploys
        orientation = "Orientation brief unavailable."
    out.append(
        "<details class=countdefs><summary>Review the live orientation brief</summary>"
        f"<div class=body><p style='white-space:pre-wrap'>{_esc(orientation)}</p></div></details>"
    )

    # ── Haiku intake mailroom ───────────────────────────────────────────────
    out.append(
        "<h2><span class=fill>Intake mailroom</span>"
        f"<span class='count o'>{mailroom['priority']}</span></h2>"
        f"<div class=metaline><b>Selected day</b> · {mailroom['priority']} priority · "
        f"{mailroom['candidate']} candidate · {mailroom['background']} background · "
        f"{mailroom['promoted']} promoted · {mailroom['fail_open']} fail-open<br>"
        f"<b>Haiku usage</b> · {int(mailroom_usage.get('calls', 0) or 0)} calls · "
        f"{int(mailroom_usage.get('input_tokens', 0) or 0)} input · "
        f"{int(mailroom_usage.get('output_tokens', 0) or 0)} output · estimated "
        f"${float(mailroom_usage.get('estimated_cost_usd', 0) or 0):.4f}<br>"
        f"<b>Bounds</b> · {config.INTAKE_TRIAGE_BATCH_SIZE} cards/call · "
        f"{config.INTAKE_TRIAGE_MAX_CALLS_PER_HOUR} calls/hour · background never reaches "
        "Sonnet unless promoted</div>"
    )
    if mailroom_sources:
        source_bits = " · ".join(
            f"{_esc(row['source'])}: {_esc(row['route'])} {int(row['n'])}"
            for row in mailroom_sources
        )
        out.append(
            "<details class=countdefs><summary>Routes by source (top 12)</summary>"
            f"<div class=body><p>{source_bits}</p></div></details>"
        )
    if mailroom_background:
        out.append("<details class=skipbox><summary>Background decisions · latest 25</summary>")
        for row_value in mailroom_background:
            row = dict(row_value)
            outcome = "" if row.get("outcome") == "model" else f" · {row.get('outcome')}"
            out.append(
                "<div class='hentry mailentry'>"
                f"<div class=m>{_ct(float(row['triaged_at']))} · {_esc(row['source'])} · "
                f"{_esc(row['category'])}{_esc(outcome)} · "
                f"<a href='{_esc(row['url'])}'>source ↗</a></div>"
                f"<div class=ttl>{_esc(row['title'])}</div>"
                f"<div class=why>{_esc(row['reason'])}</div>"
                f"{_mailroom_control(row, day)}</div>"
            )
        out.append("</details>")

    # ── Needs you ────────────────────────────────────────────────────────────
    needs = []
    for p in posts:
        if p["mode"] not in ("DRAFT", "UNCERTAIN", "FAILED", "TAPE") \
                or _dismissed(con, "post", p["id"]):
            continue
        body_html = _esc(p["body"])
        treatments = {
            "DRAFT": ("amber", "AWAITING PUBLICATION",
                      [("OPEN TYPEFULLY ↗", TYPEFULLY_URL, False),
                       ("receipt ↗", p["receipt_url"], True)]),
            "UNCERTAIN": ("orange", "VERIFY ON TYPEFULLY / X",
                          [("OPEN TYPEFULLY ↗", TYPEFULLY_URL, False),
                           ("CHECK X ↗", PROFILE_URL, True),
                           ("receipt ↗", p["receipt_url"], True)]),
            "FAILED": ("red", "PUBLISH FAILED",
                       [("OPEN TYPEFULLY ↗", TYPEFULLY_URL, False),
                        ("receipt ↗", p["receipt_url"], True)]),
            "TAPE": ("amber", "TAPE ONLY",
                     [("receipt ↗", p["receipt_url"], True)]),
        }
        color, verb, actions = treatments[p["mode"]]
        source_meta = ""
        if p["resolution_selected_tier"]:
            source_meta = (f"<p class=ednote>Source: {_esc(p['resolution_original_source'])} "
                           f"({_esc(p['resolution_original_tier'])}) → "
                           f"{_esc(p['resolution_selected_source'])} "
                           f"({_esc(p['resolution_selected_tier'])}) · "
                           f"{_esc(p['resolution_status'])} · "
                           f"eligible evidence: {p['resolution_evidence_count']}<br>"
                           f"{_esc(p['resolution_note'])}</p>")
        needs.append(_need_card(color, verb,
                                f"{_ct(p['created'])} · {_esc(p['class'])}",
                                f"<p>{body_html}</p>{source_meta}",
                                actions,
                                extra=_dismiss_link("post", p["id"], day)))
    for h in held:
        note = h["note"] or ""
        if note.startswith("editor spiked") and not _dismissed(con, "item", h["url_hash"]):
            reason = note.replace("editor spiked:", "").strip()
            needs.append(_need_card("orange", "AGREE OR OVERRULE",
                                    f"{_ct(h['first_seen'])} · {_esc(h['source'])}",
                                    f"<p>{_esc(h['title'])}</p>"
                                    f"<p class=ednote>Editor: {_esc(reason)}</p>",
                                    [("source ↗", h["url"], True)],
                                    extra=_dismiss_link("item", h["url_hash"], day)))
    if audit and is_today:
        for i, r in enumerate(audit.get("results", [])):
            if (r.get("verdict") == "material" or not r.get("class_ok", True)) \
                    and not _dismissed(con, "audit", f"{audit.get('ran')}-{i}"):
                needs.append(_need_card(
                    "red", "AUDIT FLAG",
                    _esc(r.get("verdict", "")) + (" · class suspect"
                                                  if not r.get("class_ok", True) else ""),
                    f"<p>{_esc(r.get('title'))}</p>"
                    f"<p class=ednote>{_esc('; '.join(r.get('findings', [])))}</p>", [],
                    extra=_dismiss_link("audit", f"{audit.get('ran')}-{i}", day)))

    out.append(f"<h2 class=needs><span class=fill>Needs you</span>"
               f"<span class='count o'>{len(needs)}</span></h2>")
    if needs:
        out.append(f"<div class=stack>{''.join(needs)}</div>")
    else:
        out.append("<div class=emptybox><b>Nothing.</b>"
                   "<span>The wire is running itself.</span></div>")

    out.append(
        "<div class=flow>"
        f"<div><b>{summary['seen']}</b><span>items seen</span></div>"
        f"<div><b>{summary['evaluated']}</b><span>evaluated</span></div>"
        f"<div><b>{summary['outputs_created']}</b><span>outputs created</span></div>"
        f"<div><b>{summary['published']}</b><span>published</span></div>"
        f"<div><b>{summary['held']}</b><span>currently held</span></div>"
        "</div>")

    run_result = decision_run.get("result", {}) if decision_run else {}
    path_labels = {
        "direct": "direct", "node_ref": "Node ref", "guide_ref": "guide ref",
        "serpapi": "SerpAPI", "hosted_web": "hosted web",
        "run_newsroom": "run newsroom", "unknown": "unknown",
    }
    outcome_labels = {
        "selected": "selected", "support_assessment_timeout": "support assessment timeout",
        "search_timeout": "search timeout", "source_fetch": "source fetch",
        "exhausted": "exhausted", "unknown": "unknown",
    }
    paths = run_result.get("resolver_paths") if isinstance(run_result, dict) else {}
    outcomes = run_result.get("resolver_outcomes") if isinstance(run_result, dict) else {}
    paths = paths if isinstance(paths, dict) else {}
    outcomes = outcomes if isinstance(outcomes, dict) else {}
    path_text = " · ".join(
        f"{_esc(label)} {_bounded_count(paths.get(key, 0))}"
        for key, label in path_labels.items() if _bounded_count(paths.get(key, 0)) > 0
    ) or "no resolver paths recorded"
    outcome_text = " · ".join(
        f"{_esc(label)} {_bounded_count(outcomes.get(key, 0))}"
        for key, label in outcome_labels.items() if _bounded_count(outcomes.get(key, 0)) > 0
    ) or "no resolver outcomes recorded"
    activity_text = " · ".join(
        f"{_esc(label)} {_bounded_count(activity.get(key, 0))}"
        for key, label in activity_allowed.items() if activity.get(key, 0)
    ) or "no research activity"
    failure_labels = {
        "support_assessment_timeout": "support assessment timeout",
        "search_timeout": "search timeout", "source_fetch": "source fetch",
        "exhausted": "exhausted", "unknown": "unknown",
    }
    failure_text = " · ".join(
        f"{_esc(label)} {_bounded_count(len(typed_failure_sets[key]))}"
        for key, label in failure_labels.items() if typed_failure_sets[key]
    ) or "none"
    out.append(
        "<h2><span class=fill>Research health</span></h2>"
        f"<div class=metaline><b>Backlog now</b> · pending {int(backlog.get('pending', 0))}"
        f" · processing {int(backlog.get('processing', 0))}"
        f" · exhausted {int(backlog.get('exhausted', 0))}<br>"
        f"<b>Selected CT day · distinct items</b> · {activity_text}<br>"
        f"<b>Selected CT day · typed failures</b> · {failure_text}<br>"
        f"<b>Last decision run · paths</b> · {path_text}<br>"
        f"<b>Last decision run · outcomes</b> · {outcome_text}</div>"
    )

    # ── Last completed non-empty decision run ───────────────────────────────
    decision_items = decision_run.get("items", []) if decision_run else []
    out.append(f"<h2><span class=fill>Last decision run</span>"
               f"<span class='count o'>{len(decision_items)}</span></h2>")
    if decision_run:
        newsroom_run = run_result.get("newsroom") if isinstance(run_result, dict) else None
        newsroom_decisions = (
            isinstance(newsroom_run, dict)
            and newsroom_run.get("mode") in {"draft", "live"}
            and newsroom_run.get("status") == "completed"
        )
        completed = datetime.datetime.fromtimestamp(
            decision_run.get("completed", 0), TZ).strftime("%a %b %-d · %-I:%M %p Central")
        out.append(f"<div class=metaline>{_esc(completed)} · "
                   f"{run_result.get('fetched', 0)} fetched · "
                   f"{run_result.get('new', 0)} new · "
                   f"{run_result.get('considered', len(decision_items))} considered · "
                   f"{run_result.get('pending', 0)} sent to "
                   f"{'newsroom' if newsroom_decisions else 'triage'}</div>")
        if isinstance(newsroom_run, dict) and newsroom_run.get("mode"):
            out.append(
                "<div class=metaline><b>Run newsroom</b> · "
                f"{_esc(newsroom_run.get('mode'))} · {_esc(newsroom_run.get('status'))} · "
                f"{_esc(newsroom_run.get('prompt_version') or 'unknown prompt')} · "
                f"{_bounded_count(newsroom_run.get('stories', 0))} stories · "
                f"{_bounded_count(newsroom_run.get('rounds', 0))} model rounds · "
                f"{_bounded_count(newsroom_run.get('tool_calls', 0))} research tools · "
                f"{_bounded_count(newsroom_run.get('fetches', 0))} fetches · "
                f"{_bounded_count(newsroom_run.get('search_http_attempts', 0))} search HTTP"
                + (" · search degraded" if newsroom_run.get("search_degraded") else "")
                + (f"<br><b>Run issue</b> · {_esc(newsroom_run.get('error_kind'))}: "
                   f"{_esc(newsroom_run.get('error'))}"
                   if newsroom_run.get("status") in {"fallback", "deferred"} else "")
                + "</div>"
            )
        out.append("<div class=hstack>")
        for index, item in enumerate(decision_items):
            decision_seat = "newsroom" if newsroom_decisions else "triage"
            triage_action = item.get("triage_action") or "intake skip"
            triage_reason = item.get("triage_reason") or item.get("final_note") or \
                "No reason recorded."
            final_status = item.get("final_status") or "unknown"
            output_mode = item.get("output_mode")
            final_label = f"{final_status} / {output_mode}" if output_mode else final_status
            final_note = item.get("final_note") or ""
            if final_status == "held":
                final_label = f"held · {_hold_label(final_note)}"
            elif final_status == "new" and final_note.startswith("defer:"):
                final_label = "deferred · will return to desk"
            source_path = ""
            if item.get("selected_source"):
                source_path = (f"<p>Receipt: {_esc(item.get('original_source') or item.get('source'))} "
                               f"({_esc(item.get('original_tier'))}) → "
                               f"<a href='{_esc(item.get('selected_url'))}'>"
                               f"{_esc(item.get('selected_source'))}</a> "
                               f"({_esc(item.get('selected_tier'))}) · "
                               f"{_esc(item.get('resolution_status'))}</p>")
            downstream = (f"<p>Final: {_esc(final_note)}</p>"
                          if final_note and final_note != triage_reason else "")
            theme_html = _decision_theme_context(item, coverage_by_id, now_ts)
            newsroom_detail = ""
            if item.get("newsroom_story_id"):
                newsroom_detail += (
                    f"<p>Newsroom story: {_esc(item.get('newsroom_story_id'))}</p>"
                )
            if item.get("newsroom_reader_value"):
                newsroom_detail += (
                    f"<p>Reader value: {_esc(item.get('newsroom_reader_value'))}</p>"
                )
            unresolved = item.get("newsroom_unresolved") or []
            if unresolved:
                newsroom_detail += (
                    "<p>Unresolved: " + _esc(" · ".join(str(value) for value in unresolved[:8]))
                    + "</p>"
                )
            out.append(
                f"<details class=decision{' open' if index == 0 else ''}>"
                f"<summary><div class=route>"
                f"<span class=chip>{decision_seat} · {_esc(triage_action)}</span>"
                f"<span class='chip final'>final · {_esc(final_label)}</span></div>"
                f"<div class=ttl>{_esc(item.get('title'))}</div>"
                f"<div class=meta>{_esc(item.get('source'))} · "
                f"{_esc(item.get('discovery_origin') or 'legacy')} · "
                f"{_esc(item.get('story_key') or 'no story key')}</div>"
                f"{theme_html}</summary>"
                f"<div class=body><p>Decision: {_esc(triage_reason)}</p>"
                f"{newsroom_detail}{downstream}{source_path}<p><a href='{_esc(item.get('url'))}'>"
                f"discovery item ↗</a></p>"
                f"{_item_controls(con, item.get('url_hash'), day)}</div></details>")
        out.append("</div>")
    else:
        out.append("<div class=empty>no completed non-empty decision run recorded yet</div>")

    # ── Seven days + nav + jump links ────────────────────────────────────────
    out.append("<h2><span class=fill>Seven days</span></h2><div class=days>")
    for i in range(6, -1, -1):
        d_dt = now - datetime.timedelta(days=i)
        d = d_dt.strftime("%Y-%m-%d")
        sm = store.day_summary(con, d)
        classes = ["day"]
        if d == today:
            classes.append("today")
        elif d == day:
            classes.append("sel")
        if d != today and d_dt.weekday() < 5 and sm["seen"] == 0:
            classes.append("stall")
        label = "Today" if d == today else d_dt.strftime("%a")
        detail = (f"published {sm['published']} · drafts {sm['drafts']} · "
                  f"uncertain {sm['uncertain']} · failed {sm['failed']} · tape {sm['tape']}")
        out.append(f"<a class='{' '.join(classes)}' href='{_u(d)}' title='{detail}'>"
                   f"<div class=lbl>{label}</div><div class=pub>{sm['published']}</div>"
                   f"<div class=h>{sm['held']}</div><div class=s>{sm['seen']}</div></a>")
    out.append("</div>")
    prev_d = (datetime.date.fromisoformat(day) - datetime.timedelta(days=1)).isoformat()
    next_d = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()
    nxt = (f"<span class=off>{next_d} ›</span>" if is_today
           else f"<a href='{_u(next_d)}'>{next_d} ›</a>")
    out.append(f"<div class=dnav><a href='{_u(prev_d)}'>‹ {prev_d}</a>"
               f"<span class=mid>{day}</span>{nxt}</div>")
    n_skip = summary["skipped"]
    out.append(f"<div class=jumps>"
               f"<a href='#published' style='color:var(--green)'>{summary['published']} published</a>"
               f"<span style='color:var(--amber)'>{summary['drafts']} drafts</span>"
               f"<span style='color:var(--orange)'>{summary['uncertain']} uncertain</span>"
               f"<span style='color:var(--red)'>{summary['failed']} failed</span>"
               f"<span style='color:var(--dim)'>{summary['tape']} tape</span>"
               f"<a href='#held' style='color:var(--red)'>{summary['held']} held</a>"
               f"<a href='#skipped' style='color:var(--sub)'>{n_skip} skipped</a>"
               f"<span style='color:var(--dim)'>intake: {summary['seen']} seen · "
               f"{summary['evaluated']} evaluated</span></div>")
    out.append(
        "<details class=countdefs><summary>What these counts mean</summary><div class=body>"
        "<p><b>Published</b> is a locally tracked story output confirmed live during this "
        "Central-time day. <b>Drafts, uncertain, failed,</b> and <b>tape</b> are outputs "
        "created this day in those current delivery states.</p>"
        "<p><b>Held</b> and <b>skipped</b> are source items first seen this day whose current "
        "state is held or skipped. <b>Seen</b> is every unique source URL first ingested; "
        "<b>evaluated</b> is seen items no longer awaiting triage.</p>"
        "<p>These are different units and date axes—several source items can resolve to one "
        "story output—so the status counts are not expected to add up to seen.</p>"
        "</div></details>")

    # ── Published (lede-only + expand) ───────────────────────────────────────
    pub = [p for p in posts if p["mode"] == "IMMEDIATE"]
    out.append(f"<h2 id=published><span class=fill>Published</span>"
               f"<span class='count g'>{len(pub)}</span></h2>")
    if pub:
        out.append("<div class=stack style='gap:10px'>")
        for idx, p in enumerate(pub):
            lede, rest = _split_lede(p["body"])
            verdict, reason = _ed_parts(p["editor_note"] if "editor_note" in p.keys() else None)
            ed_html = ""
            if verdict:
                lab_cls = " rev" if verdict == "revise" else ""
                ed_html = (f"<div class=edblock><div class='lab{lab_cls}'>Editor · "
                           f"{_esc(verdict)}</div><p>{_esc(reason)}</p></div>")
            source_html = ""
            if p["resolution_selected_tier"]:
                source_html = (f"<div class=edblock><div class=lab>Source resolution</div>"
                               f"<p>{_esc(p['resolution_original_source'])} "
                               f"({_esc(p['resolution_original_tier'])}) → "
                               f"{_esc(p['resolution_selected_source'])} "
                               f"({_esc(p['resolution_selected_tier'])}) · "
                               f"{_esc(p['resolution_note'])}</p></div>")
            receipt = (f"<a href='{_esc(p['receipt_url'])}'>receipt ↗</a>"
                       if (p["receipt_url"] or "").startswith("http") else "")
            out.append(
                f"<details class=rec{' open' if idx == 0 else ''}>"
                f"<summary><div class=gut><span class=cls>{_esc(p['class'])}</span>"
                f"<span class=t>{_ct(p['effective_at'])}</span>"
                f"<span class=key>{_esc(p['story_key'] or '')}</span></div>"
                f"<div class=lede>{_esc(lede)}</div></summary>"
                f"<div class=rest>{f'<p>{_esc(rest)}</p>' if rest else ''}{source_html}{ed_html}"
                f"<div class=links>{receipt}"
                f"<a href='{_esc(p['public_url'] or PROFILE_URL)}' "
                f"style='color:var(--sub)'>on X ↗</a></div>"
                f"</div></details>")
        out.append("</div>")
    else:
        out.append("<div class=empty>none this day</div>")

    # ── Held, grouped ────────────────────────────────────────────────────────
    groups = [("Freshness",
               lambda n: n.startswith("stale event:")),
              ("Waiting on a second source",
               lambda n: "second source" in n or "unconfirmed" in n),
              ("Editor spiked", lambda n: n.startswith("editor spiked")),
              ("Style gate (lint)", lambda n: n.startswith("lint")),
              ("Research infrastructure",
               lambda n: n.startswith("research pending:") or n.startswith("research exhausted:")),
              ("Thin source / unverifiable",
               lambda n: "thin source" in n or "unverifiable" in n)]
    grouped, other = {g: [] for g, _ in groups}, []
    for h in held:
        note = h["note"] or ""
        for gname, test in groups:
            if test(note):
                grouped[gname].append(h)
                break
        else:
            other.append(h)
    if other:
        grouped["Other"] = other
    out.append(f"<h2 id=held><span class=fill>Held</span>"
               f"<span class='count r'>{len(held)}</span></h2>")
    if held:
        out.append("<div class=hstack>")
        first = True
        for gname, rows in grouped.items():
            if not rows:
                continue
            out.append(f"<details{' open' if first else ''}><summary>{_esc(gname)} "
                       f"<span class=n>{len(rows)}</span></summary>")
            first = False
            for h in rows:
                resolution_meta = ""
                if h["resolution_original_tier"]:
                    resolution_meta = (f" · {_esc(h['resolution_original_tier'])} → "
                                       f"{_esc(h['resolution_selected_tier'])} "
                                       f"({_esc(h['resolution_status'])})")
                out.append(f"<div class=hentry><div class=m>{_ct(h['first_seen'])} · "
                           f"{_esc(h['source'])}{resolution_meta} · "
                           f"<a href='{_esc(h['url'])}'>source ↗</a></div>"
                           f"<div class=ttl>{_esc(h['title'])}</div>"
                           f"<div class=why>{_esc(h['note'] or '')}"
                           f"{(' · ' + _esc(h['resolution_note'])) if h['resolution_note'] else ''}"
                           f"</div>{_item_controls(con, h['url_hash'], day)}</div>")
            out.append("</details>")
        out.append("</div>")
    else:
        out.append("<div class=empty>none this day</div>")

    # ── Self-audit ───────────────────────────────────────────────────────────
    out.append("<h2><span class=fill>Self-audit</span></h2>")
    if audit:
        out.append(f"<div class=metaline>last run {_esc(audit.get('ran'))} · "
                   f"{audit.get('posts_checked', 0)} posts checked</div><div class=hstack>")
        for idx, r in enumerate(audit.get("results", [])):
            v = r.get("verdict", "unverifiable")
            flags = ("" if r.get("class_ok", True)
                     else " <span class=suspect>· class suspect</span>") + \
                    (" · source drift" if r.get("source_drift") else "")
            out.append(f"<details class=audrow{' open' if idx == 0 and v != 'clean' else ''}>"
                       f"<summary><span class='chip {v}'>{v.upper()}</span>"
                       f"{_esc(r.get('title'))}{flags}</summary>"
                       f"<div class=find>{_esc('; '.join(r.get('findings', [])) or 'No findings.')}"
                       f"</div></details>")
        out.append("</div>")
    else:
        out.append(f"<div class=empty>no audit yet (daily at {_esc(config.AUDIT_UTC)} UTC)</div>")

    # ── Skipped ──────────────────────────────────────────────────────────────
    out.append(f"<details class=skipbox id=skipped><summary>Skipped "
               f"<span style='color:var(--dim)'>{n_skip} · top reasons</span></summary><table>")
    for r in skipped:
        out.append(f"<tr><td class=n>{r['n']}</td>"
                   f"<td>{_esc(r['note'] or 'triage: out of scope / duplicate')}</td></tr>")
    out.append("</table></details>")
    return "".join(out)


def _need_card(color, verb, meta, body_html, actions, extra=""):
    acts = ""
    if actions or extra:
        links = []
        primary = True
        for label, url, secondary in actions:
            if not url:
                continue
            links.append(f"<a{' class=sec' if not primary else ''} "
                         f"href='{html.escape(url)}'>{html.escape(label)}</a>")
            primary = False
        acts = f"<div class=acts>{''.join(links)}{extra}</div>"
    return (f"<article class=need><div class='verb {color}'><b>{html.escape(verb)}</b>"
            f"<span>{meta}</span></div><div class=body>{body_html}</div>{acts}</article>")
