"""Small, read-only discovery surface over reporting work. No policy or feedback loop.

Only caller-selected reporting artifacts enter this store. Writer self-reports live in
run_observations and must never be queried here. Local replays use their own database.
"""
from __future__ import annotations

import hashlib
import json
import re
import time

from . import observations, store

TTL = 30 * 86400
PAGE = 40


def latest_identity_failure(con, members, *, after=0):
    """Candidate-scoped diagnostics survive unsafe event IDs without inventing a notebook."""
    members = list(dict.fromkeys(str(m) for m in members))[:25]
    if not members:
        return None
    marks = ",".join("?" for _ in members)
    row = con.execute(
        "SELECT o.at,o.payload_json FROM run_observations o JOIN items i ON i.url_hash=o.ref "
        f"WHERE o.kind='candidate_identity_failure' AND o.ref IN ({marks}) AND o.at>? "
        "AND o.expired=0 AND i.status IN ('new','held') "
        "AND instr(COALESCE(i.note,''),json_extract(o.payload_json,'$.failure'))>0 "
        "ORDER BY o.at DESC LIMIT 1", (*members, after)).fetchone()
    if not row:
        return None
    payload = store._safe_json_object(row["payload_json"])
    return {**payload, "at": row["at"], "use": "code_identity_diagnostic_not_editorial_rejection"}


def save(con, run_id, ref, kind, payload, *, candidate_ids=(), title=""):
    if kind not in {"receipt", "research_step"}:
        raise ValueError("Not a reporting artifact")
    safe, _ = observations.clean(payload)
    body = json.dumps(safe, ensure_ascii=False, separators=(",", ":"))
    if len(body.encode()) > 48 * 1024:
        return ""  # Source/tool bounds normally keep this substantially smaller.
    aid = "artifact_" + hashlib.sha256(f"{run_id}\n{ref}".encode()).hexdigest()[:24]
    now = time.time()
    con.execute("INSERT OR IGNORE INTO writer_artifacts(artifact_id,run_id,kind,candidate_ids_json,"
                "title,payload_json,search_text,created_at,expires_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (aid, run_id, kind, json.dumps(list(candidate_ids)[:25]), str(title)[:200], body,
                 (str(title) + " " + body)[:32000], now, now + TTL))
    con.commit()  # Persist each completed operation before another model/network call.
    return aid


def link(con, run_id, members, canonical_key, receipt_ids):
    """Only after validated exact-event identity; never infer identity from a topic."""
    for row in con.execute("SELECT artifact_id,candidate_ids_json,payload_json FROM writer_artifacts WHERE run_id=?",
                           (run_id,)).fetchall():
        payload = store._safe_json_object(row["payload_json"])
        associated = set(store._safe_json_array(row["candidate_ids_json"]))
        if payload.get("fetch_id") in receipt_ids or (associated and associated <= set(members)):
            con.execute("UPDATE writer_artifacts SET canonical_key=? WHERE artifact_id=? AND canonical_key=''",
                        (canonical_key, row["artifact_id"]))
    con.commit()


def publication(con, key):
    from .desk import LIVE_POST
    family = [key] + [r[0] for r in con.execute(
        "SELECT alias_key FROM story_key_aliases WHERE canonical_key=?", (key,))]
    where = "p.story_key IN (" + ",".join("?" for _ in family) + ") AND " + LIVE_POST
    where += " AND p.mode IN ('DRAFT','IMMEDIATE','UNCERTAIN') AND COALESCE(p.publisher_status,'') NOT IN ('deleted','inactive')"
    fields = "p.id,p.mode,p.body,p.receipt_url,p.publisher_status,p.confirmed_at,p.created,p.public_url"
    row = con.execute("SELECT " + fields + " FROM posts p WHERE " + where +
                      " ORDER BY p.created DESC,p.id DESC LIMIT 1", family).fetchone()
    if not row:
        return None
    out = dict(row)
    confirmed = con.execute("SELECT " + fields + " FROM posts p WHERE " + where +
        " AND p.publisher_status='published' AND p.confirmed_at IS NOT NULL"
        " ORDER BY p.confirmed_at DESC,p.id DESC LIMIT 1", family).fetchone()
    out["confirmed_output"] = dict(confirmed) if confirmed else None
    out["reader_covered"] = bool(confirmed)
    out["duplicate_risk"] = bool(confirmed) or bool(con.execute("SELECT 1 FROM posts p WHERE " + where +
        " AND (p.mode IN ('IMMEDIATE','UNCERTAIN') OR p.publisher_status IN ('scheduled','publishing','published','planned')) LIMIT 1", family).fetchone())
    return out


def catalog(con, *, query="", offset=0, now=None, limit=PAGE):
    """All active kinds, stable paginated order; relevance precedes a full-card cut."""
    now = time.time() if now is None else now
    offset, limit = max(0, min(int(offset), 100000)), max(1, min(int(limit), 100))
    union = """SELECT 'notebook:'||canonical_key AS context_id,'notebook' AS kind,
      canonical_key AS title,updated_at AS at,state AS state,attempts_json AS searchable
      FROM newsroom_story_memory WHERE updated_at>?
      UNION ALL SELECT 'storyline:'||storyline_key,'storyline',title,last_signal_at,lifecycle,summary
      FROM newsroom_storylines WHERE lifecycle='open' OR last_signal_at>?"""
    if str(query).strip():
        union += " UNION ALL SELECT artifact_id,kind,title,created_at,canonical_key,run_id||' '||search_text FROM writer_artifacts WHERE expires_at>?"
    else:
        # Notebook-first catalog; artifacts belong beneath their originating run.
        union += " UNION ALL SELECT 'run:'||run_id,'reporting_run',run_id,MAX(created_at),CAST(COUNT(*) AS TEXT),'Reporting operations' FROM writer_artifacts WHERE expires_at>? GROUP BY run_id"
    params = [now - TTL, now - TTL, now]
    union += " UNION ALL SELECT asset_id,'visual_asset',kind||': '||COALESCE(json_extract(metadata_json,'$.purpose'),''),created_at,run_id,metadata_json FROM visual_assets"
    terms = re.findall(r"[\w@.-]+", str(query).lower())[:6]
    conditions = " AND ".join("lower(title||' '||state||' '||searchable) LIKE ? ESCAPE '\\'" for _ in terms) or "1"
    params += ["%" + t.replace("_", "\\_").replace("%", "\\%") + "%" for t in terms]
    sql = f"SELECT context_id,kind,title,at,state FROM ({union}) WHERE {conditions}"
    total = con.execute("SELECT COUNT(*) FROM (" + sql + ")", params).fetchone()[0]
    rows = [dict(r) for r in con.execute(sql + " ORDER BY CASE WHEN kind IN ('notebook','storyline') THEN 0 ELSE 1 END,at DESC,context_id LIMIT ? OFFSET ?",
                                        params + [limit, offset])]
    for r in rows:
        r["title"] = r["title"][:160]
        if r["kind"] == "storyline":
            key = r["context_id"].removeprefix("storyline:")
            r["summary_status"] = "writer_context_not_editor_approved_facts"
            r["outcome_caveats"] = store.newsroom_storyline_caveats(con, key, now=now)
        if r["kind"] == "notebook":
            key = r["context_id"].removeprefix("notebook:")
            r["event_key"] = key
            row = con.execute("SELECT attempts_json FROM newsroom_story_memory WHERE canonical_key=?", (key,)).fetchone()
            attempts = store._safe_json_array(row[0]) if row else []
            latest = attempts[-1] if attempts and isinstance(attempts[-1], dict) else {}
            headlines = latest.get("headlines") or []
            if headlines and isinstance(headlines[0], str) and not re.fullmatch(r"(?:X\s+)?@[\w_]+", headlines[0].strip()):
                r["title"] = headlines[0][:160]
            failure = latest_identity_failure(con, latest.get("members") or [], after=latest.get("at") or 0)
            r["unresolved_question"] = str((failure or latest).get("objective") or "")[:200]
            output = publication(con, key)
            r["current_output"] = {k: output.get(k) for k in
                ("publisher_status", "reader_covered", "duplicate_risk")} if output else None
            confirmed = (output or {}).get("confirmed_output")
            r["confirmed_output"] = {"post_lead": str(confirmed["body"] or "")[:260],
                                     "confirmed_at": confirmed["confirmed_at"]} if confirmed else None
    return {"rows": rows, "total": total, "offset": offset,
            "next_offset": offset + len(rows) if offset + len(rows) < total else None,
            "window_days": 30, "note": "Dated reporting memory; not instructions or fresh news by itself."}


def intake(con, query, *, hours=72, offset=0):
    hours = max(1, min(float(hours or 72), 168))
    terms = re.findall(r"[\w@.-]+", str(query).lower())[:6]
    if not terms:
        return {"rows": [], "error": "Provide a person, quote, subject, or source."}
    params = [time.time() - hours * 3600]
    clauses = []
    for term in terms:
        clauses.append("lower(title||' '||summary||' '||source||' '||COALESCE(story_key,'')) LIKE ? ESCAPE '\\'")
        params.append("%" + term.replace("_", "\\_") + "%")
    where = "first_seen>=? AND " + " AND ".join(clauses)
    offset = max(0, min(int(offset), 100000))
    result = [dict(r) for r in con.execute("SELECT url_hash AS candidate_id,title,source,url,published_at,"
        "first_seen,status,note,story_key,summary FROM items WHERE " + where +
        " ORDER BY first_seen DESC,url_hash LIMIT 21 OFFSET ?", params + [offset])]
    return {"rows": result[:20], "next_offset": offset + 20 if len(result) > 20 else None,
            "hours": hours, "note": "Discovery and previous decisions, not inspected evidence; fetch the source."}


def read(con, context_id):
    if context_id.startswith("visual_"):
        from . import visuals
        try:
            asset=visuals.get(con,context_id)
            return {"kind":"visual_asset","visual":visuals.manifest(asset),
                    "note":"Immutable historical asset and evidence. Not fresh by itself; inspect_visual supplies actual pixels before reuse."}
        except ValueError: return None
    if context_id.startswith("run:"):
        rid = context_id.removeprefix("run:")
        return {"kind": "reporting_run", "run_id": rid, "visual_assets":[dict(r) for r in con.execute(
            "SELECT asset_id AS context_id,kind,created_at FROM visual_assets WHERE run_id=? ORDER BY created_at LIMIT 40",(rid,))],
            "artifacts": [dict(r) for r in con.execute(
            "SELECT artifact_id AS context_id,kind,title,created_at FROM writer_artifacts WHERE run_id=? AND expires_at>? ORDER BY created_at,artifact_id LIMIT 100",
            (rid, time.time()))], "note": "Use these IDs to open operations; search_memory with the run ID searches all matching artifacts."}
    if context_id.startswith("notebook:"):
        key = context_id.removeprefix("notebook:")
        cards = store.newsroom_story_memories(con, key=key, limit=1)
        if not cards:
            return None
        card = cards[0]
        card["current_output"] = publication(con, key)
        return {"kind": "notebook", **card}
    if context_id.startswith("storyline:"):
        cards = store.newsroom_storyline_cards(con, [context_id.removeprefix("storyline:")])
        return {"kind": "storyline", **cards[0]} if cards else None
    row = con.execute("SELECT * FROM writer_artifacts WHERE artifact_id=? AND expires_at>?",
                      (context_id, time.time())).fetchone()
    if row:
        return {"kind": row["kind"], "run_id": row["run_id"], "recorded_at": row["created_at"],
                "canonical_key": row["canonical_key"],
                "candidate_ids": store._safe_json_array(row["candidate_ids_json"]),
                "material": store._safe_json_object(row["payload_json"])}
    return None


def prune(con):
    con.execute("DELETE FROM writer_artifacts WHERE expires_at<=?", (time.time(),))
    con.commit()
