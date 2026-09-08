"""Versioned read-only projections for the run-first workspace. No provider calls."""
from __future__ import annotations

import datetime as dt
import json
import time
from collections import defaultdict
from urllib.parse import urlencode

from . import config, desk, observations, store

LIVE_RUN = "mode='live' AND run_id LIKE 'cycle:%'"
HEADER = "run_id,status,mode,model,prompt_version,created_at,updated_at,completed_at,error_kind"
STAGES = {"rss_triage": "Intake filtering", "desk_prep": "Assignment preparation",
          "research_assistant": "Delegated research", "newsdesk": "Writing + desk research",
          "editor": "Editing", "editor_recovery": "Editing"}


def rows(con, sql, params=()):
    return [dict(r) for r in con.execute(sql, params)]


def decode(value, kind=dict):
    return desk.obj(value, kind)


def header(row):
    return {k: row[k] for k in HEADER.split(",")} if row else None


def roster(now):
    def seat(role, model, effort, mode, note=""):
        provider = ("xAI" if model.startswith("grok-") else
                    "OpenAI" if model.startswith("gpt-") else "Anthropic")
        return {"role": role, "model": model, "provider": provider, "effort": effort or "No override",
                "mode": mode, "note": note}
    return {"observed_at": now, "seats": [
        seat("Intake filtering", config.INTAKE_TRIAGE_MODEL, "", config.INTAKE_TRIAGE_MODE, "RSS and SEC EDGAR mailroom"),
        seat("Assignment & storyline recall", config.DESK_PREP_MODEL,
             config.DESK_PREP_EFFORT if not config.DESK_PREP_MODEL.startswith("claude-") else "",
             config.DESK_PREP_MODE, "Prepares the writer’s desk"),
        seat("Delegated research (legacy)", config.RESEARCH_MODEL,
             config.RESEARCH_EFFORT if not config.RESEARCH_MODEL.startswith("claude-") else "",
             "disabled" if config.REPORTER_WRITER_ENABLED and config.NEWSROOM_MODEL.startswith("grok-") else config.HAIKU_RESEARCH_MODE,
             "Replaced by the reporter-writer in the same session"),
        seat("Reporter / writer", config.NEWSROOM_MODEL, config.NEWSROOM_EFFORT, config.RUN_NEWSROOM_MODE,
             "Native web/X, memory, news judgment and writing · shared token cost"),
        seat("Independent editor", config.EDITOR_MODEL, config.EDITOR_EFFORT, config.EDITORIAL_ENGINE,
             "Reviews surviving proposals"),
        seat("Daily receipt audit", config.ANTHROPIC_MODEL, "", "enabled" if config.AUDIT_UTC else "disabled",
             "Retired by owner; separate from the Codex rolling audit"),
    ]}


def now_data(con, state, now):
    keys = ["worker:last_success", "editorial:next_run_at", "publisher:last_success", "publisher:last_error",
            "node:last_success", "node:last_error", "node:last_pulse_generated"]
    kv = {r["k"]: r["v"] for r in con.execute("SELECT k,v FROM kv WHERE k IN ("+",".join("?" for _ in keys)+")", keys)}
    last = desk.number(state.get("last_cycle_ts"))
    health = ("error" if state.get("last_error") else "starting" if not last and now-state.get("started", now)<600
              else "stale" if not last or now-last>600 else "healthy")
    return {"observed_at": now, "worker": health, "last_cycle": last, "next_desk": desk.number(kv.get("editorial:next_run_at")),
            "publisher_sync": desk.number(kv.get("publisher:last_success")), "publisher_error": bool(kv.get("publisher:last_error")),
            "node_fetch": desk.number(kv.get("node:last_success")), "node_generated": kv.get("node:last_pulse_generated"),
            "node_error": bool(kv.get("node:last_error")), "autopost": config.AUTOPOST_ENABLED,
            "pending_delivery": con.execute("SELECT COUNT(*) FROM publisher_mutations WHERE state IN ('prepared','awaiting_media','in_flight','ambiguous','needs_owner_review')").fetchone()[0]}


def run_window(con, run_id="", direction=""):
    latest = con.execute(f"SELECT {HEADER} FROM newsroom_runs WHERE {LIVE_RUN} ORDER BY created_at DESC,run_id DESC LIMIT 1").fetchone()
    selected = con.execute(f"SELECT * FROM newsroom_runs WHERE run_id=? AND {LIVE_RUN}", (run_id,)).fetchone() if run_id else None
    if run_id and not selected:
        raise LookupError("Run not found in production history")
    if selected and direction in {"older", "newer"}:
        op, order = ("<", "DESC") if direction == "older" else (">", "ASC")
        neighbor = con.execute(f"SELECT * FROM newsroom_runs WHERE {LIVE_RUN} AND (created_at,run_id) {op} (?,?) ORDER BY created_at {order},run_id {order} LIMIT 1",
                               (selected["created_at"], run_id)).fetchone()
        if neighbor:
            selected = neighbor
    if not selected and latest:
        selected = con.execute("SELECT * FROM newsroom_runs WHERE run_id=?", (latest["run_id"],)).fetchone()
    older = newer = None
    if selected:
        for direction, op, order in (("older", "<", "DESC"), ("newer", ">", "ASC")):
            result = con.execute(f"SELECT run_id FROM newsroom_runs WHERE {LIVE_RUN} AND (created_at,run_id){op}(?,?) ORDER BY created_at {order},run_id {order} LIMIT 1",
                                 (selected["created_at"], selected["run_id"])).fetchone()
            if direction == "older":
                older = result[0] if result else None
            else:
                newer = result[0] if result else None
    recent = rows(con, f"SELECT {HEADER} FROM newsroom_runs WHERE {LIVE_RUN} ORDER BY created_at DESC,run_id DESC LIMIT 40")
    if selected and not any(r["run_id"] == selected["run_id"] for r in recent):
        recent.append(header(selected))
    return selected, {"latest": header(latest), "older": older, "newer": newer, "recent": recent}


def output_card(r):
    confirmed = r.get("publisher_status") == "published" and r.get("confirmed_at") is not None
    state = "Published" if confirmed else {"DRAFT": "Draft", "UNCERTAIN": "Uncertain", "FAILED": "Failed", "TAPE": "Tape"}.get(r.get("mode"), "Delivery requested")
    if not confirmed and r.get("publisher_status") in {"scheduled", "publishing", "error", "deleted", "planned", "inactive"}:
        state = r["publisher_status"].capitalize()
    result = {k: r.get(k) for k in ("id", "created", "body", "receipt_url", "story_key", "publisher_status", "confirmed_at", "publisher_synced_at", "editor_note", "first_seen")}
    result.update({"state": state, "public_url": desk.safe_url(r.get("public_url")), "typefully_url": "", "performance": decode(r.get("performance_json")), "performance_synced_at": r.get("performance_synced_at")})
    if r.get("publisher_backend") == "typefully" and str(r.get("nuelink_id") or "").isdigit():
        result["typefully_url"] = "https://typefully.com/?" + urlencode({"a": config.TYPEFULLY_SOCIAL_SET_ID, "d": r["nuelink_id"]})
    return result


POST_FIELDS = "p.id,p.created,p.body,p.mode,p.publisher_status,p.confirmed_at,p.public_url,p.nuelink_id,p.publisher_backend,p.story_key,p.receipt_url,p.editor_note,p.publisher_synced_at,p.performance_json,p.performance_synced_at"


def run_detail(con, row):
    run = dict(row)
    rid = run["run_id"]
    inventory = decode(run.get("inventory_json"), list)[:100]
    dossier = decode(run.get("dossier_json"))
    dossier_recorded = bool(run.get("dossier_json"))
    counters = decode(run.get("counters_json"))
    artifacts = rows(con, "SELECT id,kind,ref,phase,at,payload_json,truncated,expired FROM run_observations WHERE run_id=? ORDER BY id LIMIT 122", (rid,))
    for a in artifacts:
        a["payload"] = decode(a.pop("payload_json"))
    packet_obs = next((a for a in artifacts if a["kind"] == "writer_input" and not a["expired"]), None)
    packet = (packet_obs or {}).get("payload", {}).get("packet", {})
    packet_rows = {c["candidate_id"]: c for c in packet.get("intake_board", []) if isinstance(c, dict) and c.get("candidate_id")}
    prep = rows(con, "SELECT item_hash,effective_route,event_summary,bitcoin_relevance,freshness_note,research_objective,source_leads_json,related_storyline_keys_json,protection_reason,mode,application_state,model FROM desk_preparations WHERE run_id=? LIMIT 100", (rid,))
    prep_by = {p["item_hash"]: p for p in prep}
    items = rows(con, "SELECT "+desk.ITEM_FIELDS+" FROM items WHERE url_hash IN ("+",".join("?" for _ in inventory)+")", inventory) if inventory else []
    by_id = {i["url_hash"]: i for i in items}
    commits = {r["story_id"]: r for r in rows(con, "SELECT story_id,state,delivery_ref,details_json,updated_at FROM newsroom_story_commits WHERE run_id=? LIMIT 100", (rid,))}
    applied = {a["ref"]: a for a in artifacts if a["kind"] == "editor_applied" and not a["expired"]}
    mutations = rows(con, "SELECT materialization_json,provider_ref,state,operation,created_at,updated_at FROM publisher_mutations WHERE json_extract(materialization_json,'$.run_id')=? ORDER BY created_at LIMIT 50", (rid,))
    deliveries = {}
    for m in mutations:
        mat = decode(m.pop("materialization_json"))
        sid = str(mat.get("story_id") or "")
        post = con.execute("SELECT "+POST_FIELDS+" FROM posts p WHERE p.nuelink_id=? AND "+desk.LIVE_POST+" ORDER BY p.id DESC LIMIT 1", (m["provider_ref"],)).fetchone() if m["provider_ref"] else None
        deliveries[sid] = {"operation_now": {k: m[k] for k in ("state", "operation", "created_at", "updated_at")},
                           "submitted_copy": mat.get("body") or mat.get("post") or "",
                           "now": output_card(dict(post)) if post else None}
    decisions = {d.get("candidate_id"): d for d in dossier.get("decisions", []) if isinstance(d, dict)}
    delivered = list(packet_rows) if packet_obs else [h for h in inventory if not (
        prep_by.get(h, {}).get("effective_route") == "background" and prep_by[h].get("mode") == "enforce"
        and prep_by[h].get("application_state") == "applied")]

    def candidate(h):
        item, frozen, p = by_id.get(h, {}), packet_rows.get(h, {}), prep_by.get(h, {})
        return {"id": h, "title": frozen.get("headline_or_post") or item.get("title") or h,
                "source": (frozen.get("source") or {}).get("label") or item.get("source") or "Unknown source",
                "url": desk.safe_url(frozen.get("intake_url") or item.get("url")), "summary": frozen.get("what_arrived"),
                "first_seen": item.get("first_seen"), "status_now": item.get("status"),
                "assignment": p.get("research_objective") or "No preparation assignment recorded.",
                "preparation": {k: p.get(k) for k in ("event_summary", "bitcoin_relevance", "freshness_note", "effective_route", "protection_reason", "model")},
                "provenance": "writer_packet" if frozen else "retained_intake_not_exact_packet",
                "decision": decisions.get(h, {}), "writer_card": frozen}
    cards = {h: candidate(h) for h in inventory}
    stories, used = [], set()
    for s in dossier.get("stories", [])[:50]:
        if not isinstance(s, dict):
            continue
        sid = str(s.get("story_id") or "")
        members = [h for h in s.get("member_candidate_ids", []) if h in cards]
        used.update(members)
        commit = commits.get(sid, {})
        details = decode(commit.get("details_json"))
        editor = applied.get(sid, {}).get("payload") or details.get("editor") or None
        if editor and not editor.get("origin"):
            editor = {**editor, "origin": "legacy_summary_not_full_response"}
        verdict = (editor or {}).get("verdict")
        reason = (editor or {}).get("reason") or details.get("reason") or s.get("reader_value") or ""
        outcome = ("Dropped by editor" if verdict == "drop" else "Delivered" if commit.get("state") == "delivered"
                   else "Held" if commit.get("state") == "held" else "Unfinished record" if run["completed_at"] and commit.get("state") == "pending"
                   else "Editor reviewed" if editor and editor.get("origin") in {"initial", "recovery"}
                   else "Editor fallback" if editor else "Writer proposal")
        stories.append({"id": sid, "title": cards[members[0]]["title"] if members else str(s.get("story_key") or sid),
                        "source": cards[members[0]]["source"] if members else "Merged story", "members": members,
                        "writer": s.get("post"), "writer_reason": s.get("reader_value"), "story_key": s.get("story_key"),
                        "effective_key": (applied.get(sid, {}).get("payload") or {}).get("canonical_key"),
                        "selected_fetch_id": s.get("selected_fetch_id"), "evidence_fetch_ids": s.get("evidence_fetch_ids") or [],
                        "editor": editor, "delivery": deliveries.get(sid), "outcome": outcome, "reason": reason,
                        "commit_at": commit.get("updated_at"), "validation": details.get("validation")})
        from . import visual_choices
        selected_visual=(editor or {}).get("visual_review", {}) or {}
        stories[-1]["visuals"]=visual_choices.panel(con,rid,sid,members,
            selected_visual.get("asset_id") or s.get("visual_asset_id"),review=selected_visual)
    for h in delivered:
        if h not in used and h in cards:
            d = decisions.get(h, {})
            disposition = d.get("disposition")
            stories.append({"id": "lead:"+h, "title": cards[h]["title"], "source": cards[h]["source"], "members": [h],
                            "outcome": {"drop": "Dropped by writer", "defer": "Deferred by writer", "covered": "Already covered"}.get(disposition, "No recorded decision"),
                            "reason": d.get("reason") or "The run did not retain a writer decision for this lead.",
                            "writer": None, "editor": None, "delivery": None, "evidence_fetch_ids": []})
    usage = rows(con, "SELECT seat,model,effort,outcome,latency_ms,estimated_cost_usd,cost_source,created_at,native_web_calls,native_x_calls FROM model_usage WHERE run_id=? ORDER BY id LIMIT 100", (rid,))
    feedback = next((a for a in reversed(artifacts) if a["kind"] == "writer_feedback"), None)
    return {**header(run), "counters": counters, "packet": packet, "packet_recorded": bool(packet_obs),
            "writer_feedback": feedback_card(feedback),
            "packet_truncated": bool(packet_obs and packet_obs["truncated"]), "artifacts": artifacts,
            "captured": len(inventory) if inventory else None,
            "dossier_recorded": dossier_recorded,
            "proposal_count": sum(bool(s.get("post")) for s in dossier.get("stories", []) if isinstance(s,dict)) if dossier_recorded else None,
            "delivery_records": sum(c["state"] == "delivered" for c in commits.values()),
            "delivered_count": len(packet_rows) if packet_obs else None,
            "advanced_estimate": len(delivered) if inventory else None, "delivered_exact": bool(packet_obs),
            "candidates": list(cards.values()), "background": [cards[h] for h in inventory if h not in delivered],
            "stories": stories, "run_note": dossier.get("run_note") or "", "usage": usage,
            "cost": sum(r["estimated_cost_usd"] for r in usage) if usage else None,
            "metered_calls": len(usage), "unknown_cost": sum(r["cost_source"] == "unknown" for r in usage)}


def feedback_card(row):
    if not row:
        return {"status": "not_recorded"}
    return {"at": row.get("at"), "run_id": row.get("run_id"),
            **({"status": "expired"} if row.get("expired") else row.get("payload", {}))}


def recent_feedback(con, page):
    data = rows(con, "SELECT o.run_id,o.at,o.payload_json,o.expired FROM run_observations o"
        " JOIN newsroom_runs r ON r.run_id=o.run_id WHERE o.kind='writer_feedback'"
        " AND r.mode='live' AND r.run_id LIKE 'cycle:%' ORDER BY o.at DESC,o.id DESC LIMIT 11 OFFSET ?",
        ((page - 1) * 10,))
    return {"page": page, "more": len(data) > 10,
            "rows": [feedback_card({**r, "payload": decode(r["payload_json"])}) for r in data[:10]],
            "retention_days": 14}


def source_health(con, now):
    from . import sources
    stored = {r["source_key"]: r for r in rows(con, "SELECT * FROM source_poll_health ORDER BY label LIMIT 120")}
    expected = [("rss:"+label, label, "rss", True, config.POLL_SECONDS) for label in sources.FEEDS]
    expected += [("edgar", "SEC EDGAR", "edgar", True, config.POLL_SECONDS),
                 ("perception", "Perception", "perception", bool(config.PERCEPTION_DIRECT_ENABLED and config.PERCEPTION_API_KEY), config.PERCEPTION_POLL_SECONDS)]
    out = []
    for key, label, kind, enabled, cadence in expected:
        r = stored.pop(key, {"source_key": key, "label": label, "kind": kind, "outcome": "not_observed", "result_count": None})
        out.append({**r, "enabled": enabled, "cadence": cadence})
    out += [{**r, "enabled": bool(config.X_BEARER_TOKEN), "cadence": config.X_POLL_SECONDS} for r in stored.values()]
    return out


def intake(con, opt, now):
    where, params = "i.first_seen>=? AND i.first_seen<?", [opt["start"], opt["end"]]
    if opt["q"]:
        where += " AND (instr(lower(i.title),lower(?))>0 OR instr(lower(i.source),lower(?))>0 OR i.url_hash=?)"
        params += [opt["q"]]*3
    if opt["state"]:
        if opt["state"] not in desk.ITEM_STATES:
            raise ValueError("Unknown intake state")
        where += " AND i.status=?"
        params.append(opt["state"])
    fields = ",".join("i."+x for x in desk.ITEM_FIELDS.split(","))
    result = rows(con, f"SELECT {fields},t.route mailroom_route,t.reason mailroom_reason,t.triaged_at FROM items i LEFT JOIN intake_triage t ON t.item_hash=i.url_hash WHERE {where} ORDER BY i.first_seen DESC,i.url_hash DESC LIMIT 41 OFFSET ?", [*params,(opt["page"]-1)*40])
    for r in result[:40]:
        prep = con.execute("SELECT run_id,effective_route,event_summary,research_objective,model FROM desk_preparations WHERE item_hash=? ORDER BY prepared_at DESC LIMIT 1", (r["url_hash"],)).fetchone()
        r["preparation"] = dict(prep) if prep else None
        latest = store.latest_operator_action(con, r["url_hash"])
        active = con.execute(
            "SELECT 1 FROM operator_actions WHERE item_hash=? AND state IN ('queued','processing') LIMIT 1",
            (r["url_hash"],),
        ).fetchone()
        r["reconsider"] = {
            "eligible": r["status"] == "skipped" and not active
                        and config.EDITORIAL_ENGINE == "v2" and config.RUN_NEWSROOM_MODE == "live",
            "latest_action_id": latest["id"] if latest else 0,
            "request": ({k: latest[k] for k in
                         ("id", "state", "requested_at", "completed_at", "original_note", "result")}
                        if latest and latest["action"] == "reconsider" else None),
        }
    counts = rows(con, "SELECT status,COUNT(*) n FROM items WHERE first_seen>=? AND first_seen<? GROUP BY status", (opt["start"],opt["end"]))
    return {"day": opt["day"], "page": opt["page"], "more": len(result)>40, "items": result[:40], "counts": counts, "sources": source_health(con, now)}


def outputs(con, opt):
    where = f"{desk.LIVE_POST} AND (p.created>=? AND p.created<? OR {desk.CONFIRMED} AND p.confirmed_at>=? AND p.confirmed_at<?)"
    params = [opt["start"],opt["end"],opt["start"],opt["end"]]
    if opt["state"]:
        if opt["state"] not in desk.OUTPUT_STATES:
            raise ValueError("Unknown output state")
        where += " AND " + (desk.CONFIRMED if opt["state"] == "confirmed" else "p.mode=?")
        if opt["state"] != "confirmed":
            params.append(opt["state"])
    if opt["q"]:
        where += " AND instr(lower(p.body),lower(?))>0"
        params.append(opt["q"])
    result = rows(con, f"SELECT {POST_FIELDS},i.first_seen FROM posts p LEFT JOIN items i ON i.url_hash=p.item_hash WHERE {where} ORDER BY COALESCE(p.confirmed_at,p.created) DESC,p.id DESC LIMIT 41 OFFSET ?", [*params,(opt["page"]-1)*40])
    cards = []
    for r in result[:40]:
        card = output_card(r)
        m = con.execute("SELECT json_extract(materialization_json,'$.run_id') run_id,json_extract(materialization_json,'$.story_id') story_id FROM publisher_mutations WHERE provider_ref=? ORDER BY created_at DESC LIMIT 1", (r["nuelink_id"],)).fetchone()
        card["run_id"] = m["run_id"] if m else None
        card["story_id"] = m["story_id"] if m else None
        cards.append(card)
    return {"day": opt["day"], "page": opt["page"], "more": len(result)>40, "outputs": cards}


def cost_scope(run_id, mode):
    if run_id.startswith("cycle:"):
        return "production" if mode in (None, "live") else "excluded"
    if any(x in run_id.lower() for x in ("replay", "eval", "shadow", "test")):
        return "excluded"
    return "unclassified"


def costs(con, now):
    today = dt.datetime.fromtimestamp(now, desk.TZ).date()
    first = con.execute("SELECT MIN(created_at) FROM model_usage").fetchone()[0]
    if first is None:
        return {"observed_at": now, "periods": {}, "averages": {}, "ledger_start": None, "bounded": False}
    ledger_day = dt.datetime.fromtimestamp(first, desk.TZ).date()
    cutoff_day = max(ledger_day, today-dt.timedelta(days=93))
    cutoff = dt.datetime.combine(cutoff_day,dt.time(),desk.TZ).timestamp()
    data = rows(con, "SELECT u.run_id,u.seat,u.model,u.effort,u.estimated_cost_usd,u.cost_source,u.created_at,r.mode run_mode,r.run_id linked_run FROM model_usage u LEFT JOIN newsroom_runs r ON r.run_id=u.run_id WHERE u.created_at>=? AND u.created_at<=? ORDER BY u.created_at,u.id LIMIT 50001", (cutoff,now))
    bounded = len(data)>50000
    data = data[:50000]
    for r in data:
        r["date"] = dt.datetime.fromtimestamp(r["created_at"],desk.TZ).date()
        r["scope"] = cost_scope(r["run_id"],r["run_mode"])
    production = [r for r in data if r["scope"] == "production"]
    def aggregate(subset):
        stages, run_ids = {}, set()
        for r in subset:
            name = STAGES.get(r["seat"], "Other")
            s = stages.setdefault(name,{"name":name,"cost":0,"calls":0,"unknown":0,"reported":0,"estimated":0,"linked_cost":0,"models":set()})
            cost = float(r["estimated_cost_usd"] or 0)
            s["cost"] += cost; s["calls"] += 1; s["unknown"] += r["cost_source"] == "unknown"
            s["reported" if r["cost_source"] == "provider_reported" else "estimated"] += cost
            s["models"].add(r["model"])
            if r["linked_run"] and r["seat"] != "rss_triage":
                run_ids.add(r["run_id"]); s["linked_cost"] += cost
        for s in stages.values():
            s["models"] = sorted(s["models"])
        cost = sum(s["cost"] for s in stages.values())
        linked = sum(s["linked_cost"] for s in stages.values())
        return {"cost":cost,"calls":len(subset),"runs":len(run_ids),"per_run":linked/len(run_ids) if run_ids else None,
                "linked_cost":linked,"shared_cost":cost-linked,"unknown":sum(s["unknown"] for s in stages.values()),
                "reported":sum(s["reported"] for s in stages.values()),"estimated":sum(s["estimated"] for s in stages.values()),
                "stages": sorted(stages.values(),key=lambda s:-s["cost"])}
    starts = {"today":today,"week":today-dt.timedelta(days=today.weekday()),"month":today.replace(day=1)}
    periods = {k:{"start":str(d),"through":str(today),**aggregate([r for r in production if r["date"]>=d])} for k,d in starts.items()}
    full_start = max(ledger_day+dt.timedelta(days=1),cutoff_day)
    averages = {}
    for unit in ("day","week","month"):
        values = []
        cursor = full_start
        while cursor < today and not bounded:
            end = cursor+dt.timedelta(days=1 if unit == "day" else 7)
            if unit == "week" and cursor.weekday()!=0:
                cursor += dt.timedelta(days=1); continue
            if unit == "month":
                if cursor.day!=1:
                    cursor += dt.timedelta(days=1); continue
                end = (cursor.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
            if end<=today:
                subset = [r for r in production if cursor<=r["date"]<end]
                values.append(aggregate(subset))
            cursor += dt.timedelta(days=1)
        averages[unit] = {"count":len(values),"value":sum(v["cost"] for v in values)/len(values) if values else None,
                          "unknown":sum(v["unknown"] for v in values)}
    return {"observed_at":now,"ledger_start":first,"coverage_from":str(cutoff_day),"through":str(today),"bounded":bounded,
            "periods":periods,"averages":averages,"excluded":aggregate([r for r in data if r["scope"] == "excluded"]),
            "unclassified":aggregate([r for r in data if r["scope"] == "unclassified"])}


def snapshot(con, query, state, now=None):
    now = now or time.time()
    opt = desk.options(query)
    view = query.get("view", ["newsroom"])[0]
    if view not in {"newsroom","intake","outputs","system"}:
        raise ValueError("Unknown workspace view")
    result = {"version":1,"view":view,"observed_at":now,"now":now_data(con,state,now)}
    if view == "newsroom":
        selected, nav = run_window(con,opt["run"],query.get("direction",[""])[0])
        result.update({"navigation":nav,"run":run_detail(con,selected) if selected else None,
                       "arriving":rows(con,"SELECT "+desk.ITEM_FIELDS+" FROM items ORDER BY first_seen DESC,url_hash DESC LIMIT 6")})
    elif view == "intake":
        result.update(intake(con,opt,now))
    elif view == "outputs":
        result.update(outputs(con,opt))
    else:
        result.update({"roster":roster(now),"costs":costs(con,now),"sources":source_health(con,now),
                       "writer_feedback": recent_feedback(con,opt["page"]),
                       "cadence_minutes":config.DESK_INTERVAL_SECONDS/60,
                       "recent_calls":rows(con,"SELECT seat,model,effort,outcome,created_at,latency_ms,estimated_cost_usd,cost_source FROM model_usage ORDER BY created_at DESC LIMIT 20"),
                       "search":rows(con,"SELECT provider,state,consecutive_failures,next_search_at,error_kind,total_searches_left,last_status_success_at FROM search_provider_state LIMIT 10")})
    return observations.clean(result)[0]
