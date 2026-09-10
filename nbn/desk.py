"""Read-only, bounded live Desk views over the worker's existing checkpoints.

No provider calls or migrations are allowed here. All activity is observed state, not
inferred model progress. Existing owner mutations remain on the legacy /report surface.
"""
from __future__ import annotations

import datetime as dt
import hmac
import html
import json
import math
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

from . import config, store

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).with_name("desk_assets")
GUIDE = ROOT / "output/pdf/nbn-system-guide.pdf"
TZ = ZoneInfo("America/Chicago")
VIEWS = {"live": "Live", "intake": "Intake", "runs": "Newsroom", "outputs": "Outputs",
         "system": "System & costs"}
PAGE_SIZE = 40
ITEM_STATES = {"new", "researching", "held", "skipped", "drafted", "posted", "error",
               "uncertain", "failed", "taped"}
OUTPUT_STATES = {"confirmed", "DRAFT", "IMMEDIATE", "UNCERTAIN", "FAILED", "TAPE"}
# Evaluation exports normally live outside this DB. Exclude only explicitly marked rows;
# do not guess from dates or from an ordinary story that happens to discuss a replay.
LIVE_POST = "NOT (lower(COALESCE(p.class,'')) IN ('replay','eval') OR lower(COALESCE(p.story_key,'')) LIKE 'replay:%' OR lower(COALESCE(p.body,'')) LIKE '[replay]%')"
CONFIRMED = "(p.publisher_status='published' AND p.confirmed_at IS NOT NULL)"


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def clock(value) -> str:
    value = number(value)
    if value is None or value <= 0:
        return "not recorded"
    try:
        return dt.datetime.fromtimestamp(value, TZ).strftime("%b %d · %I:%M:%S %p CT")
    except (OverflowError, OSError, ValueError):
        return "not recorded"


def obj(value, kind=dict):
    try:
        result = json.loads(value or ("{}" if kind is dict else "[]"))
        return result if isinstance(result, kind) else kind()
    except (TypeError, ValueError):
        return kind()


def safe_url(value):
    value = str(value or "").strip()
    try:
        parsed = urlsplit(value)
        if (parsed.scheme in {"http", "https"} and parsed.hostname
                and not parsed.username and not parsed.password
                and not any(ord(c) < 33 for c in value)):
            return value[:3000]
    except ValueError:
        pass
    return ""


def external(url, label):
    url = safe_url(url)
    return (f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)} ↗</a>'
            if url else esc(label))


def link(view="live", **params):
    return "/desk" + ("/" + view if view != "live" else "") + "?" + urlencode(
        {"k": config.REPORT_TOKEN, **{k: v for k, v in params.items() if v not in (None, "")}})


def review_link(day=None, anchor=""):
    return "/report?" + urlencode({"k": config.REPORT_TOKEN, **({"d": day} if day else {})}) + anchor


@contextmanager
def reader():
    """Do not replace with store.connect(): that function writes/migrates on connect."""
    con = sqlite3.connect(config.DB_PATH.resolve().as_uri() + "?mode=ro", uri=True, timeout=1)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    deadline = time.monotonic() + 3
    con.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    try:
        con.execute("BEGIN")  # One coherent SQLite snapshot, held only for this request.
        yield con
    finally:
        con.rollback()
        con.close()


def options(query):
    today = dt.datetime.now(TZ).date().isoformat()
    day = query.get("d", [today])[0]
    if day == "today":
        day = today
    try:
        if dt.date.fromisoformat(day).isoformat() != day:
            raise ValueError()
        start, end = store.day_bounds(day)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Use a calendar date: YYYY-MM-DD") from None
    try:
        page = int(query.get("page", ["1"])[0])
        if not 1 <= page <= 250:
            raise ValueError()
    except ValueError:
        raise ValueError("Page must be between 1 and 250") from None
    return {"day": day, "start": start, "end": end, "page": page,
            "state": query.get("state", [""])[0][:32],
            "q": query.get("q", [""])[0][:120],
            "run": query.get("run", [""])[0][:120]}


def base_snapshot(con, opt, state, now):
    start, end = opt["start"], opt["end"]
    kv_names = ["worker:last_success", "editorial:next_run_at", "publisher:last_success",
                "publisher:last_error", "publisher:analytics_last_success", "node:last_error",
                "node:last_pulse_generated", "node:last_success", "intake_triage:last_success"]
    kv = {r["k"]: r["v"] for r in con.execute(
        "SELECT k,v FROM kv WHERE k IN (" + ",".join("?" for _ in kv_names) + ")", kv_names)}
    last = number(kv.get("worker:last_success"))
    current_last = number(state.get("last_cycle_ts"))
    # A previous process's successful heartbeat is not this process's completed cycle.
    worker = ("error" if state.get("last_error") else
              "starting" if not current_last and now - state.get("started", now) < 600 else
              "stale" if not current_last or now - current_last > 600 else "healthy")
    item_counts = {r["status"]: r["n"] for r in con.execute(
        "SELECT status,COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<? GROUP BY status",
        (start, end))}
    queued = con.execute("SELECT COUNT(*) n FROM items WHERE status='new'").fetchone()["n"]
    confirmations = con.execute(
        f"SELECT COUNT(*) n FROM posts p WHERE {LIVE_POST} AND {CONFIRMED}"
        " AND p.confirmed_at>=? AND p.confirmed_at<?", (start, end)).fetchone()["n"]
    outputs = {r["mode"]: r["n"] for r in con.execute(
        f"SELECT mode,COUNT(*) n FROM posts p WHERE {LIVE_POST} AND created>=? AND created<? GROUP BY mode",
        (start, end))}
    pending = con.execute(
        "SELECT COUNT(*) n FROM publisher_mutations WHERE state IN ('prepared','in_flight','ambiguous','needs_owner_review')"
    ).fetchone()["n"]
    usage = dict(con.execute(
        "SELECT COUNT(*) calls,COALESCE(SUM(estimated_cost_usd),0) cost,"
        "COALESCE(SUM(cost_source='unknown'),0) unknown FROM model_usage WHERE created_at>=? AND created_at<?",
        (start, end)).fetchone())
    return {"generated_at": now, "worker": worker, "last_cycle": current_last,
            "persisted_cycle": last, "kv": kv, "items": item_counts, "queued": queued,
            "confirmed": confirmations, "outputs": outputs, "pending_mutations": pending,
            "usage": usage}


def pill(text, tone=""):
    return f'<span class="badge {esc(tone)}">{esc(text)}</span>'


def empty(text):
    return f'<div class="empty">{esc(text)}</div>'


def table(headers, rows):
    return ('<div class="table-scroll"><table><thead><tr>' +
            "".join(f"<th scope=col>{esc(h)}</th>" for h in headers) +
            "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) +
                                           "</tr>" for row in rows) + "</tbody></table></div>")


def metric(label, value, note):
    return f'<div class="metric"><span>{esc(label)}</span><strong>{esc(value)}</strong><small>{esc(note)}</small></div>'


def pager(view, opt, more):
    bits = []
    for page, label in ((opt["page"] - 1, "← Newer"), (opt["page"] + 1, "Older →")):
        if page >= 1 and page <= 250 and (page < opt["page"] or more):
            bits.append(f'<a href="{esc(link(view, d=opt["day"], page=page, state=opt["state"], q=opt["q"]))}">{label}</a>')
    return f'<div class="pager"><span>Page {opt["page"]} · up to {PAGE_SIZE} records</span>{"".join(bits)}</div>'


def item_cards(rows, day):
    out = []
    for row in rows:
        seen = number(row["first_seen"])
        try:
            item_day = dt.datetime.fromtimestamp(seen, TZ).date().isoformat() if seen else day
        except (ValueError, OverflowError, OSError):
            item_day = day
        route = " · ".join(str(row[k]) for k in ("decision_stage", "decision_category") if row[k])
        out.append(
            f'<article class="card"><div class="eyebrow">{esc(row["source"])} · {esc(clock(row["first_seen"]))}</div>'
            f'<h3>{external(row["url"], row["title"])}</h3>'
            f'<div class="chips">{pill(row["status"])}{pill(row["discovery_origin"] or "legacy")}</div>'
            f'<p>{esc(row["note"] or "No decision recorded yet.")}</p>'
            f'<small>{esc(route)}{(" · " + esc(row["story_key"])) if row["story_key"] else ""}</small>'
            f'<details id="item-{esc(row["url_hash"])}"><summary>Timing & review</summary>'
            f'<p>Source timestamp (as supplied): {esc(row["published_at"] or "unknown")}. '
            'This is not a verified event time.</p>'
            f'<p><a href="{esc(review_link(item_day))}">Open review tools</a> · '
            f'<a href="{esc(link("intake", d=item_day, q=row["url_hash"]))}">Item details</a></p></details></article>')
    return "".join(out) or empty("No matching intake records in this window.")


ITEM_FIELDS = "url_hash,source,title,url,published_at,first_seen,status,story_key,note,discovery_origin,decision_stage,decision_category"


def intake(con, opt):
    where, params = "first_seen>=? AND first_seen<?", [opt["start"], opt["end"]]
    if opt["state"]:
        if opt["state"] not in ITEM_STATES:
            raise ValueError("Unknown intake state")
        where += " AND status=?"
        params.append(opt["state"])
    if opt["q"]:
        where += " AND (instr(lower(title),lower(?))>0 OR instr(lower(source),lower(?))>0 OR url_hash=? OR story_key=?)"
        params.extend([opt["q"]] * 4)
    rows = con.execute(f"SELECT {ITEM_FIELDS} FROM items WHERE {where} ORDER BY first_seen DESC,url_hash LIMIT ? OFFSET ?",
                       [*params, PAGE_SIZE + 1, (opt["page"] - 1) * PAGE_SIZE]).fetchall()
    out = ['<p class="muted">Unique items first seen on the selected Central day. Status is current, not a historical snapshot. '
           'Background is omitted from the writer; use Review to send a qualifying item back to the desk.</p>']
    out.append(item_cards(rows[:PAGE_SIZE], opt["day"]))
    if len(rows) == 1:
        h = rows[0]["url_hash"]
        prep = con.execute("SELECT run_id,effective_route,event_summary,bitcoin_relevance,research_objective,prepared_at,protection_reason FROM desk_preparations WHERE item_hash=? ORDER BY prepared_at DESC LIMIT 5", (h,)).fetchall()
        mail = con.execute("SELECT route,reason,triaged_at FROM intake_triage WHERE item_hash=?", (h,)).fetchone()
        if mail:
            out.append(f'<section><h2>Mailroom decision</h2><p>{pill(mail["route"])} {esc(mail["reason"])} · {esc(clock(mail["triaged_at"]))}</p></section>')
        if prep:
            out.append('<section><h2>Assignment history</h2>' + table(
                ["Run / prepared", "Route", "Assessment"], [[
                    f'<a href="{esc(link("runs", d=opt["day"], run=r["run_id"]))}">{esc(r["run_id"])}</a><small>{esc(clock(r["prepared_at"]))}</small>',
                    pill(r["effective_route"]), esc(r["event_summary"]) + "<p>" + esc(r["bitcoin_relevance"]) + "</p>" + esc(r["research_objective"])
                ] for r in prep]) + '</section>')
    out.append(pager("intake", opt, len(rows) > PAGE_SIZE))
    return "".join(out)


def run_detail(con, run_id, day):
    r = con.execute("SELECT run_id,status,mode,model,prompt_version,created_at,updated_at,completed_at,error_kind,counters_json,inventory_json,dossier_json FROM newsroom_runs WHERE run_id=?", (run_id,)).fetchone()
    if not r:
        return empty("Run not found. It may be outside retained history.")
    counters = obj(r["counters_json"])
    inventory = obj(r["inventory_json"], list)
    dossier = obj(r["dossier_json"])
    out = [f'<section><h2>{esc(run_id)}</h2><div class="chips">{pill(r["status"])}{pill(r["mode"])}{pill(r["model"])}</div>'
           f'<p>Started {esc(clock(r["created_at"]))}. Last recorded checkpoint {esc(clock(r["updated_at"]))}. '
           f'Completed: {esc(clock(r["completed_at"]))}.</p>'
           f'<small>Prompt: {esc(r["prompt_version"])} · error kind: {esc(r["error_kind"] or "none recorded")}.</small>'
           '<p class="muted">A checkpoint is not an exact live stage. Decisions below are from this run; item state may have changed since.</p>']
    keys = [("rounds", "API attempts"), ("initial_packet_bytes", "Initial packet bytes"),
            ("searches", "Direct searches"), ("fetches", "Fetch attempts"),
            ("prefetch_successes", "Prepared receipts"), ("haiku_assignments", "Delegated research jobs")]
    out.append('<div class="metrics compact">' + "".join(metric(label, counters.get(key, "—"), "recorded counter") for key, label in keys) + '</div></section>')
    decisions = dossier.get("decisions") if isinstance(dossier.get("decisions"), list) else []
    rows = []
    for decision in decisions[:100]:
        if not isinstance(decision, dict):
            continue
        h = str(decision.get("candidate_id") or decision.get("url_hash") or "")[:64]
        item = con.execute("SELECT title,source,status FROM items WHERE url_hash=?", (h,)).fetchone()
        rows.append([esc(item["title"] if item else h), pill(decision.get("disposition", "unknown")),
                     esc(str(decision.get("reason") or "")[:1200]), pill(item["status"] if item else "unavailable")])
    out.append('<section><h2>Newsroom decisions</h2>' + (table(["Candidate", "Decision then", "Reason", "Item now"], rows)
               if rows else empty("No terminal decisions recorded. The run may be in progress, deferred, or its dossier has been pruned.")) + '</section>')
    commits = con.execute("SELECT story_id,state,details_json,updated_at FROM newsroom_story_commits WHERE run_id=? ORDER BY story_id LIMIT 50", (run_id,)).fetchall()
    if commits:
        rows = []
        for c in commits:
            detail = obj(c["details_json"])
            ed = detail.get("editor") if isinstance(detail.get("editor"), dict) else {}
            rows.append([esc(c["story_id"]), pill(c["state"]), pill(ed.get("verdict", "not recorded")),
                         esc(str(ed.get("reason") or detail.get("reason") or "")[:1600])])
        out.append('<section><h2>Editor & delivery checkpoints</h2>' + table(["Story", "Commit state", "Editor", "Reason"], rows) + '</section>')
    # Full intake identity includes assignment-background items absent from the writer's dossier.
    hashes = [h for h in inventory[:100] if isinstance(h, str)]
    if hashes:
        items = con.execute(f"SELECT {ITEM_FIELDS} FROM items WHERE url_hash IN (" + ",".join("?" for _ in hashes) + ") ORDER BY first_seen DESC", hashes).fetchall()
        out.append('<section><h2>Input inventory</h2><p class="muted">Includes candidates removed by assignment preparation before the writer saw them. '
                   'Open an item to inspect that routing.</p>' + item_cards(items, day) + '</section>')
    return "".join(out)


def runs(con, opt):
    if opt["run"]:
        return run_detail(con, opt["run"], opt["day"])
    rows = con.execute("SELECT run_id,status,mode,model,created_at,updated_at,completed_at,error_kind FROM newsroom_runs WHERE created_at>=? AND created_at<? ORDER BY created_at DESC,run_id LIMIT ? OFFSET ?",
                       (opt["start"], opt["end"], PAGE_SIZE + 1, (opt["page"] - 1) * PAGE_SIZE)).fetchall()
    out = '<p class="muted">Persisted newsroom sessions, newest first. One run can produce several stories or none. Mailroom and prep calls are separate model seats.</p>'
    out += table(["Started / run", "Last checkpoint", "Model / mode", "Finished"], [[
        f'<a href="{esc(link("runs", d=opt["day"], run=r["run_id"]))}">{esc(clock(r["created_at"]))}</a><small>{esc(r["run_id"])}</small>',
        pill(r["status"]) + f'<small>{esc(clock(r["updated_at"]))}</small>' + esc(r["error_kind"]),
        esc(r["model"]) + f'<small>{esc(r["mode"])}</small>', esc(clock(r["completed_at"]))
    ] for r in rows[:PAGE_SIZE]]) if rows else empty("No newsroom sessions started on this day.")
    return out + pager("runs", opt, len(rows) > PAGE_SIZE)


def outputs(con, opt):
    where = f"{LIVE_POST} AND ((p.created>=? AND p.created<?) OR ({CONFIRMED} AND p.confirmed_at>=? AND p.confirmed_at<?))"
    params = [opt["start"], opt["end"], opt["start"], opt["end"]]
    if opt["state"]:
        if opt["state"] not in OUTPUT_STATES:
            raise ValueError("Unknown output state")
        where += " AND " + (CONFIRMED if opt["state"] == "confirmed" else "p.mode=?")
        if opt["state"] != "confirmed":
            params.append(opt["state"])
    if opt["q"]:
        where += " AND (instr(lower(p.body),lower(?))>0 OR p.story_key=?)"
        params.extend([opt["q"], opt["q"]])
    rows = con.execute(
        "SELECT p.id,p.created,p.body,p.mode,p.publisher_status,p.confirmed_at,p.public_url,p.nuelink_id,p.publisher_backend,p.story_key,p.receipt_url,p.editor_note,p.publisher_synced_at,p.performance_json,p.performance_synced_at,i.first_seen "
        f"FROM posts p LEFT JOIN items i ON i.url_hash=p.item_hash WHERE {where} ORDER BY COALESCE(p.confirmed_at,p.created) DESC,p.id DESC LIMIT ? OFFSET ?",
        [*params, PAGE_SIZE + 1, (opt["page"] - 1) * PAGE_SIZE]).fetchall()
    out = ['<p class="muted">Locally tracked outputs created or confirmed on this day. Not a complete Typefully account inventory. '
           'Manual publication appears after reconciliation (normally every 5 minutes). Explicit replay/eval rows are excluded.</p>']
    for r in rows[:PAGE_SIZE]:
        confirmed = r["publisher_status"] == "published" and r["confirmed_at"] is not None
        status = "confirmed published" if confirmed else (r["publisher_status"] or r["mode"])
        title = str(r["body"] or "").split("\n", 1)[0][:250]
        actions = external(r["public_url"], "View on X") if r["public_url"] else ""
        if r["publisher_backend"] == "typefully" and str(r["nuelink_id"] or "").isdigit():
            url = "https://typefully.com/?" + urlencode({"a": config.TYPEFULLY_SOCIAL_SET_ID, "d": r["nuelink_id"]})
            actions += " · " + external(url, "Open in Typefully")
        latency = (round((r["created"] - r["first_seen"]) / 60, 1)
                   if r["first_seen"] and r["created"] >= r["first_seen"] else None)
        perf = obj(r["performance_json"])
        out.append(f'<article class="card"><div class="chips">{pill(status, "good" if confirmed else "")}{pill("local #" + str(r["id"]))}</div>'
                   f'<h3>{esc(title)}</h3><p>{actions}</p>'
                   f'<div class="timing"><span>First seen<small>{esc(clock(r["first_seen"]))}</small></span>'
                   f'<span>Output recorded<small>{esc(clock(r["created"]))}</small></span>'
                   f'<span>Confirmed published<small>{esc(clock(r["confirmed_at"]) if confirmed else "not confirmed")}</small></span></div>'
                   f'<p class="muted">Intake → local output: {esc(str(latency) + " min" if latency is not None else "unknown")}. '
                   'Not peer-to-NBN latency and not proof of a Typefully arrival time.</p>'
                   f'<details id="post-{r["id"]}"><summary>Read copy & receipt</summary><div class="copy">{esc(str(r["body"] or "")[:12000])}</div>'
                   f'<p>{external(r["receipt_url"], "Receipt")}</p><p>Editor note: {esc(str(r["editor_note"] or "not recorded")[:1400])}</p>'
                   f'<small>Event: {esc(r["story_key"])} · Last publisher sync: {esc(clock(r["publisher_synced_at"]))}</small>'
                   f'<p>Engagement: {esc(perf.get("likes") if perf.get("likes") is not None else "unknown")} likes · {esc(perf.get("reposts") if perf.get("reposts") is not None else "unknown")} reposts. '
                   f'Observed {esc(clock(r["performance_synced_at"]))}; low-volume feedback, not an editorial score.</p></details></article>')
    if not rows:
        out.append(empty("No matching local outputs. This does not mean the intake worker is idle."))
    out.append(pager("outputs", opt, len(rows) > PAGE_SIZE))
    return "".join(out)


def system(con, opt, data):
    roster = [("RSS / EDGAR mailroom", config.INTAKE_TRIAGE_MODEL, "default", config.INTAKE_TRIAGE_MODE),
              ("Assignment & storyline recall", config.DESK_PREP_MODEL, config.DESK_PREP_EFFORT, config.DESK_PREP_MODE),
              ("Newsroom / writer", config.NEWSROOM_MODEL, config.NEWSROOM_EFFORT, config.EDITORIAL_ENGINE),
              ("Delegated native research", config.RESEARCH_MODEL, config.RESEARCH_EFFORT, config.HAIKU_RESEARCH_MODE),
              ("Independent editor", config.EDITOR_MODEL, config.EDITOR_EFFORT, "configured")]
    roster.append(("Internal daily receipt audit", config.ANTHROPIC_MODEL, "legacy defaults", "enabled" if config.AUDIT_UTC else "disabled"))
    from .newsroom import PROMPT_VERSION
    out = ['<section><h2>Runtime roster</h2><p>These values come from this running process, not a saved documentation snapshot.</p>',
           table(["Seat", "Model", "Effort", "Mode"], [[esc(v) for v in row] for row in roster]),
           f'<p class="muted">Prompt {esc(PROMPT_VERSION)} · Source policy {esc(config.SOURCE_POLICY_MODE)} · '
           f'Autopost {"ON" if config.AUTOPOST_ENABLED else "OFF"}. No switches on this read-only page.</p></section>']
    cadence = [("Worker loop / RSS / EDGAR", f"{config.POLL_SECONDS}s sleep after each cycle", "Long work can delay the next poll"),
               ("X guides + monitored accounts", f"{config.X_POLL_SECONDS}s throttle", "Requires configured X access"),
               ("Direct Perception", f"{config.PERCEPTION_POLL_SECONDS}s throttle", "enabled" if config.PERCEPTION_DIRECT_ENABLED else "disabled"),
               ("Editorial batch", f"{config.DESK_INTERVAL_SECONDS // 60} minutes", "Due, nonempty work; not a post quota"),
               ("Typefully reconciliation", f"{config.PUBLISH_RECONCILE_SECONDS}s throttle", "Locally known outputs only"),
               ("Typefully analytics", f"{config.PUBLISH_ANALYTICS_SECONDS}s throttle", "Missing metrics stay unknown"),
               ("Node EIC one-off discovery", "; ".join(f"{t} {name} UTC" for t, name in config.EIC_DISCOVERY_SCHEDULE) or "disabled", "Freshness/provenance checked"),
               ("Legacy Block threads", "; ".join(f"{t} {name} UTC" for t, name in config.BRIEFING_SCHEDULE) or "disabled", "Not implied by EIC discovery")]
    out.append('<section><h2>Clocks & dependencies</h2>' + table(["Work", "Configured cadence", "Meaning"], [[esc(v) for v in row] for row in cadence]) + '</section>')
    costs = con.execute("SELECT seat,model,effort,COUNT(*) calls,SUM(input_tokens) input,SUM(output_tokens) output,SUM(cache_read_input_tokens) cached,SUM(native_web_calls) web,SUM(native_x_calls) x,SUM(estimated_cost_usd) cost,SUM(cost_source='unknown') unknown FROM model_usage WHERE created_at>=? AND created_at<? GROUP BY seat,model,effort ORDER BY cost DESC", (opt["start"], opt["end"])).fetchall()
    out.append('<section><h2>Selected-day model usage</h2><p class="muted">xAI reported totals where available; otherwise rate estimates. '
               'Reasoning is included in output tokens. Unknown costs are not free. These are recorded editorial-seat costs, not a full invoice: '
               'the legacy daily receipt audit, source APIs, hosting, and Codex audit are outside this ledger.</p>' +
               table(["Seat / model / effort", "Calls", "Input / output / cache read", "Native web / X", "Known/estimated USD", "Unknown calls"], [[
                   esc(r["seat"]) + f'<small>{esc(r["model"])} · {esc(r["effort"])}</small>', esc(r["calls"]),
                   f'{r["input"]:,} / {r["output"]:,} / {r["cached"]:,}', f'{r["web"]} / {r["x"]}', f'${r["cost"]:.4f}', esc(r["unknown"])
               ] for r in costs]) + f'<p>Daily target ${config.MODEL_DAILY_TARGET_USD:.2f}; a guide, not a publication quota.</p></section>')
    lines = con.execute("SELECT title,lifecycle,summary,updated_at FROM newsroom_storylines ORDER BY updated_at DESC LIMIT 12").fetchall()
    out.append('<section><h2>Storyline memory</h2><p class="muted">Current NBN-native context, not source evidence. Separate from exact-event deduplication. Up to 12 recent lines.</p>' +
               table(["Storyline", "State", "Summary", "Updated"], [[esc(r["title"]), pill(r["lifecycle"]), esc(r["summary"]), esc(clock(r["updated_at"]))] for r in lines]) + '</section>')
    out.append(f'<section><h2>System guide</h2><p><a href="{esc(link("system-guide.pdf"))}">Download the visual PDF guide</a></p>'
               '<p>The PDF is a dated deployment snapshot; the runtime values above take precedence. SHA-256 identifiers are fingerprints, not encryption.</p></section>')
    return "".join(out)


def live(con, opt, data):
    kv = data["kv"]
    latest = con.execute("SELECT run_id,status,updated_at FROM newsroom_runs ORDER BY created_at DESC LIMIT 1").fetchone()
    out = [f'<section class="now"><h2>On the desk now</h2><p>Next editorial deadline: <strong>{esc(clock(kv.get("editorial:next_run_at")))}</strong>. '
           'A due deadline waits for the worker and eligible work; it is not a guaranteed post time.</p>']
    if latest:
        out.append(f'<p>Latest newsroom: <a href="{esc(link("runs", d=opt["day"], run=latest["run_id"]))}">{esc(latest["run_id"])}</a> '
                   f'{pill(latest["status"])} · checkpoint {esc(clock(latest["updated_at"]))}.</p>')
    out.append(f'<p>Publisher sync: {esc(clock(kv.get("publisher:last_success")))}'
               f'{" · sync error recorded" if kv.get("publisher:last_error") else ""}. '
               f'Node pulse generated: {esc(kv.get("node:last_pulse_generated") or "not recorded")}'
               f'{" · Node error recorded" if kv.get("node:last_error") else ""}.</p>'
               f'<p>Protected publisher attempts awaiting resolution: {data["pending_mutations"]} (current, all dates).</p>'
               f'<p><a href="{esc(review_link(opt["day"]))}">Open review queue / guarded actions</a>. '
               'Holds need their recorded reason inspected; they do not all mean “waiting for corroboration.”</p></section>')
    out.append('<section><h2>How work moves</h2><ol class="flow"><li>Intake<small>New URLs, guide posts, official feeds</small></li>'
               '<li>Preparation<small>Noise filtered; related leads grouped</small></li><li>Newsroom<small>Research, select, write</small></li>'
               '<li>Editor<small>Approve, revise, stage or drop</small></li><li>Typefully<small>Draft → scheduled → confirmed</small></li></ol>'
               '<p class="muted">This is the system map, not five live queue counters. A story may combine several intake items.</p></section>')
    rows = con.execute(f"SELECT {ITEM_FIELDS} FROM items WHERE first_seen>=? AND first_seen<? ORDER BY first_seen DESC LIMIT 6", (opt["start"], opt["end"])).fetchall()
    out.append('<section><h2>Latest intake in this window</h2>' + item_cards(rows, opt["day"]) + '</section>')
    calls = con.execute("SELECT run_id,seat,model,outcome,created_at,latency_ms,estimated_cost_usd,cost_source FROM model_usage WHERE created_at>=? AND created_at<? ORDER BY created_at DESC LIMIT 12", (opt["start"], opt["end"])).fetchall()
    out.append('<section><h2>Recent completed model calls</h2><p class="muted">Recorded when each request returns. No token-stream or live thought inspection.</p>' +
               table(["Recorded", "Seat / model", "Outcome", "Duration", "Cost USD"], [[esc(clock(r["created_at"])),
                   esc(r["seat"]) + f'<small>{esc(r["model"])}</small>', pill(r["outcome"]), f'{r["latency_ms"] / 1000:.1f}s',
                   "unknown" if r["cost_source"] == "unknown" else f'${r["estimated_cost_usd"]:.4f}'
               ] for r in calls]) + '</section>')
    return "".join(out)


def fragment(con, view, opt, state, now):
    data = base_snapshot(con, opt, state, now)
    status = data["worker"]
    banner = (f'<div class="worker {"good" if status == "healthy" else "warn"}">{pill("Worker " + status)} '
              f'Last completed cycle in this process: {esc(clock(data["last_cycle"]))}. '
              f'Persisted last success: {esc(clock(data["persisted_cycle"]))}.</div>')
    metrics = '<div class="metrics">' + "".join([
        metric("First seen", sum(data["items"].values()), "unique items · selected day"),
        metric("Waiting for desk", data["queued"], "new items · all time, not all eligible"),
        metric("Outputs recorded", sum(data["outputs"].values()), "created on selected day · all modes"),
        metric("Confirmed published", data["confirmed"], "confirmed timestamp · selected day"),
        metric("Model cost", f'${data["usage"]["cost"]:.2f}', f'{data["usage"]["calls"]} calls · {data["usage"]["unknown"]} unknown-cost'),
    ]) + '</div>'
    content = {"live": lambda: live(con, opt, data), "intake": lambda: intake(con, opt),
               "runs": lambda: runs(con, opt), "outputs": lambda: outputs(con, opt),
               "system": lambda: system(con, opt, data)}[view]()
    return {"html": banner + metrics + content, "generated_at": now, "worker": status}


def page(view, opt, snapshot):
    nav = "".join(f'<a {"aria-current=page" if key == view else ""} href="{esc(link(key, d=opt["day"]))}">{esc(label)}</a>' for key, label in VIEWS.items())
    nav += f'<a href="{esc(review_link(opt["day"]))}">Review tools ↗</a>'
    states = ITEM_STATES if view == "intake" else OUTPUT_STATES if view == "outputs" else set()
    selector = ('<label>State<select name="state"><option value="">All states</option>' + "".join(
        f'<option value="{esc(s)}" {"selected" if s == opt["state"] else ""}>{esc(s)}</option>' for s in sorted(states)) + '</select></label>') if states else ""
    search = f'<label>Title, source or event<input type="search" name="q" value="{esc(opt["q"])}" maxlength="120"></label>' if states else ""
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><title>{esc(VIEWS[view])} · NBN Desk</title>
<link rel="stylesheet" href="{esc(link('assets/desk.css'))}"><script src="{esc(link('assets/desk.js'))}" defer></script></head>
<body data-view="{esc(view)}"><a class="skip" href="#content">Skip to content</a>
<header><a class="brand" href="{esc(link())}"><span class="mark">↗</span> Next Block News <span class="muted">/ Desk</span></a>
{pill('AUTOPUBLISH ON' if config.AUTOPOST_ENABLED else 'AUTOPUBLISH OFF', 'warn' if config.AUTOPOST_ENABLED else '')}</header>
<nav aria-label="Desk views">{nav}</nav><main><div class="page-heading"><div><p class="eyebrow">OPERATIONS / {esc(opt['day'])} CENTRAL</p><h1>{esc(VIEWS[view])}</h1></div>
<div class="refresh"><span id="connection" role="status">Snapshot {esc(clock(snapshot['generated_at']))}</span><button type="button" id="pause" aria-pressed="false">Pause updates</button><button type="button" id="refresh">Refresh now</button></div></div>
<form method="get" class="filters"><input type="hidden" name="k" value="{esc(config.REPORT_TOKEN)}"><label>Central day<input type="date" name="d" value="{esc(opt['day'])}" required></label>{selector}{search}<button>Apply</button><a href="{esc(link(view))}">Today</a></form>
<p class="muted refresh-note">Refreshes every 15 seconds while visible. The selected day stays fixed until you choose Today. Current-state panels are labeled separately.</p>
<noscript><p class="worker warn">JavaScript is off. This is a server snapshot; reload to update.</p></noscript>
<div id="content" data-observed="{snapshot['generated_at']}">{snapshot['html']}</div>
<footer>Production observations, not promises. No editorial settings or publishing actions are changed by these views. Existing actions live in Review tools.</footer></main></body></html>'''


def respond(handler, code, body, content_type):
    if isinstance(body, str):
        body = body.encode()
    handler.send_response(code)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
    handler.end_headers()
    handler.wfile.write(body)


def handle(handler, parsed, state):
    """Handle every /desk route, including unknown children. Called before health fallback."""
    query = parse_qs(parsed.query)
    token = query.get("k", [""])[0]
    if not config.REPORT_TOKEN or not hmac.compare_digest(token.encode(), config.REPORT_TOKEN.encode()):
        respond(handler, 403, "Forbidden", "text/plain; charset=utf-8")
        return
    path = parsed.path.removeprefix("/desk").strip("/")
    if path.startswith("visuals/"):
        from . import visuals
        try:
            with reader() as con:
                asset=visuals.get(con,path.split("/",1)[1])
                content=visuals.bytes_for(asset)
            respond(handler,200,content,asset["mime"])
        except (ValueError,OSError,sqlite3.Error):
            respond(handler,404,"Visual not available","text/plain; charset=utf-8")
        return
    assets = {"assets/desk.css": (ASSETS / "desk.css", "text/css; charset=utf-8"),
              "assets/desk.js": (ASSETS / "desk.js", "text/javascript; charset=utf-8"),
              "assets/workspace.css": (ASSETS / "workspace.css", "text/css; charset=utf-8"),
              "assets/workspace.js": (ASSETS / "workspace.js", "text/javascript; charset=utf-8"),
              "system-guide.pdf": (GUIDE, "application/pdf")}
    if path in assets:
        file, content_type = assets[path]
        try:
            respond(handler, 200, file.read_bytes(), content_type)
        except OSError:
            respond(handler, 404, "Artifact not available in this release", "text/plain; charset=utf-8")
        return
    if path == "api/workspace":
        from . import desk_api
        try:
            with reader() as con:
                data = desk_api.snapshot(con, query, dict(state))
            respond(handler, 200, json.dumps(data), "application/json; charset=utf-8")
        except LookupError:
            respond(handler, 404, "Run not found", "text/plain; charset=utf-8")
        except ValueError as exc:
            respond(handler, 400, str(exc), "text/plain; charset=utf-8")
        except sqlite3.Error:
            respond(handler, 503, "Desk data temporarily unavailable. Retrying preserves your selection.", "text/plain; charset=utf-8")
        return
    if path in {"", "live", "runs", "intake", "outputs", "system", "reporter"}:
        # Route aliases/deep links remain supported; the client preserves the auth query.
        respond(handler, 200, workspace_page(), "text/html; charset=utf-8")
        return
    view = query.get("view", ["live"])[0] if path == "api/snapshot" else (path or "live")
    if view not in VIEWS:
        respond(handler, 404, "Desk view not found", "text/plain; charset=utf-8")
        return
    try:
        opt = options(query)
        with reader() as con:
            snapshot = fragment(con, view, opt, dict(state), time.time())
        if path == "api/snapshot":
            respond(handler, 200, json.dumps(snapshot), "application/json; charset=utf-8")
        else:
            respond(handler, 200, page(view, opt, snapshot), "text/html; charset=utf-8")
    except ValueError as exc:
        respond(handler, 400, str(exc), "text/plain; charset=utf-8")
    except sqlite3.Error:
        # No raw SQLite errors/URLs or connection credentials in browser responses.
        respond(handler, 503, "Desk data temporarily unavailable. Retry shortly; prior snapshots may be stale.", "text/plain; charset=utf-8")


def workspace_page():
    return f'''<!doctype html><html lang="en" class="dark"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer">
<title>Newsroom · Next Block News</title><link rel="stylesheet" href="{esc(link('assets/workspace.css'))}">
<script src="{esc(link('assets/workspace.js'))}" defer></script></head><body>
<a class="skip" href="#main">Skip to workspace</a><div id="root"><p class="initial-loading">Opening the newsroom…</p></div>
<noscript><p>Enable JavaScript for run navigation, or use <a href="{esc(review_link())}">the server-rendered review tools</a>.</p></noscript></body></html>'''
