"""Required next-shift letters and deliberately scheduled reporting work.

Letters are viewpoints, checks are work, receipts are evidence. None implies publication.
"""
from __future__ import annotations

import hashlib
import json
import time

from . import config, observations, store

FOLLOWUP_SCHEMA = {
    "type": "array", "maxItems": 8, "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "followup_id": {"type": ["string", "null"]},
            "base_revision": {"type": ["integer", "null"]},
            "context_id": {"type": "string", "description": "notebook:exact-event-key or storyline:read-or-created-key"},
            "question": {"type": "string", "maxLength": 400},
            "source_paths": {"type": "array", "maxItems": 4, "items": {"type": "string", "maxLength": 500}},
            "next_check_minutes": {"type": "integer", "minimum": 15, "maximum": 10080},
            "state": {"type": "string", "enum": ["open", "closed"]},
            "result": {"type": "string", "enum": ["pending", "development", "no_change", "inconclusive"]},
            "note": {"type": "string", "maxLength": 600},
        },
        "required": ["followup_id", "base_revision", "context_id", "question", "source_paths",
                     "next_check_minutes", "state", "result", "note"],
    },
}

GUIDANCE = """
NEXT-SHIFT CONTINUITY — part of finishing the job
Every completed Writer session MUST submit a useful shift_letter, including no-post sessions.
Write to the next Writer: what mattered, the current best understanding and its uncertainty,
useful source routes, corrected assumptions, and what deserves attention next. Be concrete and
brief, not a performance report. No minimum length or invented lesson; a quiet run still has
useful judgment to hand over. Do not claim an Editor decision or publication you have not seen.
The incoming letter is dated, fallible editorial memory; actual outcomes are supplied separately.

Use follow_up_updates for important unresolved questions worth deliberately checking later.
Choose a current notebook or a storyline you read/created. Supply a useful question, source paths,
and next-check interval; do not schedule everything. For a supplied internal reporting assignment,
report its check result and reschedule or close it. A failed fetch is inconclusive, not no_change.
No development can mean drop this assignment and extend/close the watch, with a useful letter.
Assignments have no event date: their queue time does not make old evidence fresh. A genuinely
new discovery can become a normal sourced story using the assignment candidate ID; keep the
watched event and a distinct new event separate. Fresh related intake may inform the same check.
An assignment marked completed_check_reporting_retry already finished research; continue its
deferred sourced story using the retained event identity/evidence, not a new check or event.
Search/read memory when useful; semantic similarity finds context, not truth or event identity.
"""


def letter_body(value):
    return value.strip()[:4000] if isinstance(value, str) else ""


def save_letter(con, run_id, value, *, model, prompt_version):
    body = letter_body(value)
    if body:
        con.execute("INSERT OR IGNORE INTO writer_handoffs VALUES (?,?,?,?,?)",
                    (run_id, time.time(), model, prompt_version, body))
        con.commit()
    return bool(body or con.execute("SELECT 1 FROM writer_handoffs WHERE run_id=?", (run_id,)).fetchone())


def _handoff_output_keys(con, run_id):
    # Receipts may be reused/tagged to another sibling. Confirmed delivery intents
    # retain the canonical event even after later replacements change posts.mutation_id.
    keys = []
    for row in con.execute(
            "SELECT c.story_id,m.canonical_key,m.materialization_json "
            "FROM newsroom_story_commits c JOIN publisher_mutations m "
            "ON m.provider_ref=c.delivery_ref WHERE c.run_id=? "
            "AND c.state='delivered' AND c.delivery_ref<>'' "
            "AND m.state='confirmed' AND m.canonical_key<>'' "
            "ORDER BY c.updated_at DESC,c.story_id,m.updated_at DESC,m.mutation_id",
            (run_id,)):
        data = store._safe_json_object(row["materialization_json"])
        if data.get("run_id") == run_id and data.get("story_id") == row["story_id"]:
            if row["canonical_key"] not in keys:
                keys.append(row["canonical_key"])
    for row in con.execute(
            "SELECT canonical_key FROM writer_artifacts WHERE run_id=? AND canonical_key<>'' "
            "ORDER BY created_at,artifact_id", (run_id,)):
        if row[0] not in keys:
            keys.append(row[0])
    return keys[:8]


def handoff(con, run_id=None, *, before=None):
    row = con.execute("SELECT * FROM writer_handoffs WHERE " +
        ("run_id=?" if run_id else "written_at<?") + " ORDER BY written_at DESC LIMIT 1",
        (run_id if run_id else before or time.time(),)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["context_id"] = "letter:" + row["run_id"]
    result["kind"] = "writer_letter_not_evidence"
    # Actual outcomes remain live; never alter the historical letter to pretend foresight.
    run = con.execute("SELECT status FROM newsroom_runs WHERE run_id=?", (row["run_id"],)).fetchone()
    result["actual_run_status"] = run["status"] if run else "unknown"
    result["actual_story_outcomes"] = []
    for commit in con.execute("SELECT story_id,state,details_json,updated_at FROM newsroom_story_commits WHERE run_id=? LIMIT 8",
                              (row["run_id"],)):
        details = store._safe_json_object(commit["details_json"])
        editor = details.get("editor") or {}
        result["actual_story_outcomes"].append({"story_id": commit["story_id"],
            "state": commit["state"], "at": commit["updated_at"],
            "editor_verdict": editor.get("verdict"), "editor_reason": str(editor.get("reason") or "")[:500],
            "validation": details.get("validation"), "reason": str(details.get("reason") or "")[:500]})
    from . import writer_memory
    result["actual_outputs"] = [{"event_key": key, "output": writer_memory.publication(con, key)}
                                for key in _handoff_output_keys(con, row["run_id"])]
    # Copy is retrievable via notebooks; don't bloat every initial desk.
    for entry in result["actual_outputs"]:
        output = entry["output"]
        if output:
            output.pop("body", None)
            if output.get("confirmed_output"):
                output["confirmed_output"].pop("body", None)
    return result


def card(row):
    value = dict(row)
    value["source_paths"] = store._safe_json_array(value.pop("sources_json", "[]"))
    value["kind"] = "internal_reporting_watch_not_evidence"
    return value


def active(con, limit=20):
    return [card(r) for r in con.execute("SELECT * FROM writer_followups WHERE state='open' "
        "ORDER BY next_check_at LIMIT ?", (limit,))]


def assignment_context(item):
    if item.get("discovery_origin") != "followup":
        return None
    return store._safe_json_object(item.get("discovery_context", "")).get("reporting_assignment")


def hydrate(con, row):
    item = dict(row)
    item["published"] = item.pop("published_at", "") or ""
    context = assignment_context(item)
    if context:
        current = con.execute("SELECT * FROM writer_followups WHERE followup_id=?",
                              (context.get("followup_id"),)).fetchone()
        if current:
            item["_followup"] = card(current)
            check = con.execute("SELECT completed_at,status FROM writer_followup_checks WHERE assignment_id=?",
                                (item["url_hash"],)).fetchone()
            if check and check["completed_at"]:
                item["_followup"]["completed_check_reporting_retry"] = True
                item["_followup"]["completed_check_result"] = check["status"]
    return item


def due_assignments(con, *, now=None, limit=2):
    """Called only after the ordinary cadence gate. Creation/recovery is atomic."""
    if not config.WRITER_FOLLOWUPS_ENABLED or limit <= 0:
        return []
    now = time.time() if now is None else now
    selected = []
    with con:
        # A completed reporting check may still have a technically deferred story.
        # Preserve the SAME candidate/event/evidence; never admit terminal output rows.
        retries = con.execute("SELECT i.* FROM items i JOIN writer_followup_checks c ON c.assignment_id=i.url_hash "
            "WHERE i.discovery_origin='followup' AND i.status='new' AND COALESCE(i.defer_until,0)<=? "
            "AND c.completed_at IS NOT NULL AND c.status='development' ORDER BY i.first_seen LIMIT ?",
            (now, min(2, limit))).fetchall()
        selected.extend(hydrate(con, row) for row in retries)
        retry_watches = {i["_followup"]["followup_id"] for i in selected if i.get("_followup")}
        rows = con.execute("SELECT f.* FROM writer_followups f LEFT JOIN items i ON i.url_hash=f.queued_assignment "
                           "WHERE f.state='open' AND f.next_check_at<=? AND COALESCE(i.defer_until,0)<=? "
                           "ORDER BY f.next_check_at", (now, now)).fetchall()
        for row in rows:
            if len(selected) >= min(2, limit):
                break
            if row["followup_id"] in retry_watches:
                continue
            if con.execute("SELECT 1 FROM writer_followup_checks c JOIN items i ON i.url_hash=c.assignment_id "
                           "WHERE c.followup_id=? AND c.completed_at IS NOT NULL AND c.status='development' "
                           "AND i.status='new' LIMIT 1", (row["followup_id"],)).fetchone():
                continue  # Its existing story is still deferred, not another research assignment.
            assignment = row["queued_assignment"]
            if assignment:
                item = con.execute("SELECT * FROM items WHERE url_hash=?", (assignment,)).fetchone()
                if item and item["status"] != "new":
                    # Recovery after delivery/termination but before check finalization.
                    finish_assignments(con, "recovery", [hydrate(con, item)])
                    continue
                if item and (item["defer_until"] or 0) > now:
                    continue
            else:
                assignment = hashlib.sha256(f"followup:{row['followup_id']}:{row['revision']}".encode()).hexdigest()
                context = json.dumps({"untrusted_discovery_context": True,
                    "reporting_assignment": card(row)}, separators=(",", ":"))
                con.execute("INSERT OR IGNORE INTO items(url_hash,source,title,url,published_at,first_seen,"
                    "summary,discovery_key,discovery_origin,discovery_context) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (assignment, "NBN follow-up", row["question"], "nbn-assignment:" + assignment,
                     "", now, "Internal reporting assignment, not an external news arrival.",
                     "nbn-assignment:" + assignment, "followup", context))
                con.execute("UPDATE writer_followups SET queued_assignment=? WHERE followup_id=?",
                            (assignment, row["followup_id"]))
                con.execute("INSERT OR IGNORE INTO writer_followup_checks"
                    "(assignment_id,followup_id,due_at,started_at,status) VALUES (?,?,?,?,?)",
                    (assignment, row["followup_id"], row["next_check_at"], now, "queued"))
                item = con.execute("SELECT * FROM items WHERE url_hash=?", (assignment,)).fetchone()
            if item:
                selected.append(hydrate(con, item))
    return selected


def apply_updates(con, run_id, updates, *, allowed_contexts, inventory):
    """Bounded CAS updates; invalid notes must not block otherwise valid reporting."""
    if not config.WRITER_FOLLOWUPS_ENABLED:
        return {"accepted": 0, "ignored": 0}
    assigned = {v["_followup"]["followup_id"]: v for v in inventory if v.get("_followup")
                and not v["_followup"].get("completed_check_reporting_retry")}
    accepted = ignored = 0
    for raw in (updates if isinstance(updates, list) else [])[:8]:
        if not isinstance(raw, dict):
            ignored += 1
            continue
        ident = raw.get("followup_id")
        prior = con.execute("SELECT * FROM writer_followups WHERE followup_id=?", (ident,)).fetchone() if ident else None
        if prior and prior["updated_run"] == run_id:
            continue
        context = str(raw.get("context_id") or "")
        question = str(raw.get("question") or "").strip()[:400]
        state, result = raw.get("state"), raw.get("result")
        valid_context = (context.startswith("notebook:") and con.execute(
            "SELECT 1 FROM newsroom_story_memory WHERE canonical_key=?", (context[9:],)).fetchone()) or (
            context.startswith("storyline:") and con.execute(
            "SELECT 1 FROM newsroom_storylines WHERE storyline_key=?", (context[10:],)).fetchone())
        if (not question or not valid_context or context not in allowed_contexts and ident not in assigned
                or state not in {"open", "closed"} or result not in {"pending", "development", "no_change", "inconclusive"}
                or ident and not prior or prior and (raw.get("base_revision") != prior["revision"]
                                                    or context != prior["context_id"])):
            ignored += 1
            continue
        try:
            interval = max(15, min(10080, int(raw.get("next_check_minutes", 60)))) * 60
        except (TypeError, ValueError):
            ignored += 1
            continue
        sources = raw.get("source_paths")
        sources = [str(v)[:500] for v in sources[:4]] if isinstance(sources, list) else []
        note = str(raw.get("note") or "").strip()[:600]
        if ident in assigned and (result == "pending" or not note):
            ignored += 1
            continue  # A current check needs a result, not just an altered schedule.
        now = time.time()
        with con:
            if prior:
                checked = ident in assigned and result != "pending" and bool(note)
                con.execute("UPDATE writer_followups SET question=?,sources_json=?,next_check_at=?,state=?,"
                    "revision=revision+1,last_check_at=?,last_result=?,last_note=?,queued_assignment=?,"
                    "updated_run=?,updated_at=? WHERE followup_id=? AND revision=?",
                    (question, json.dumps(sources), now+interval, state,
                     now if checked else prior["last_check_at"], result if checked else prior["last_result"],
                     note if checked else prior["last_note"], None if checked else prior["queued_assignment"],
                     run_id, now, ident, prior["revision"]))
                if checked:
                    con.execute("UPDATE writer_followup_checks SET completed_at=?,run_id=?,status=?,note=? "
                        "WHERE assignment_id=? AND completed_at IS NULL",
                        (now, run_id, result, note, assigned[ident]["url_hash"]))
                    con.execute("UPDATE writer_followup_attempts SET completed_at=?,status=?,note=? "
                        "WHERE assignment_id=? AND run_id=? AND completed_at IS NULL",
                        (now, result, note, assigned[ident]["url_hash"], run_id))
            else:
                ident = "followup_" + hashlib.sha256((context + "\n" + question.lower()).encode()).hexdigest()[:24]
                con.execute("INSERT OR IGNORE INTO writer_followups(followup_id,context_id,question,sources_json,"
                    "next_check_at,state,revision,origin_run,updated_run,created_at,updated_at) VALUES (?,?,?,?,?,?,1,?,?,?,?)",
                    (ident, context, question, json.dumps(sources), now+interval, state, run_id, run_id, now, now))
            accepted += 1
    diagnostics = {"accepted": accepted, "ignored": ignored}
    observations.record(con, run_id, "followup_updates", diagnostics, phase="persisted")
    return diagnostics


def begin_assignments(con, run_id, inventory):
    with con:
        for item in inventory:
            if item.get("_followup"):
                con.execute("INSERT OR IGNORE INTO writer_followup_attempts"
                    "(assignment_id,run_id,started_at,status) VALUES (?,?,?,'running')",
                    (item["url_hash"], run_id, time.time()))


def finish_assignments(con, run_id, inventory):
    """Unreported/failed checks remain due work, not falsely recorded negative findings."""
    now = time.time()
    with con:
        for item in inventory:
            if not item.get("_followup"):
                continue
            row = con.execute("SELECT * FROM writer_followup_checks WHERE assignment_id=?",
                              (item["url_hash"],)).fetchone()
            if row and row["completed_at"] is not None:
                con.execute("UPDATE writer_followup_attempts SET completed_at=?,status='reporting_retry',"
                    "note='Prior check complete; this run continued the deferred story. See actual Editor/delivery outcome.' "
                    "WHERE assignment_id=? AND run_id=? AND completed_at IS NULL",
                    (now, item["url_hash"], run_id))
            if row and row["completed_at"] is None:
                con.execute("UPDATE writer_followup_attempts SET completed_at=?,status='inconclusive',"
                    "note='No completed check report; inspect actual editorial/delivery outcome' "
                    "WHERE assignment_id=? AND run_id=? AND completed_at IS NULL",
                    (now, item["url_hash"], run_id))
                con.execute("UPDATE writer_followup_checks SET run_id=?,status='inconclusive',"
                    "note='No completed check report; retry on the ordinary desk cadence',attempts=attempts+1 "
                    "WHERE assignment_id=?", (run_id, item["url_hash"]))
                current = con.execute("SELECT status FROM items WHERE url_hash=?", (item["url_hash"],)).fetchone()
                if current and current["status"] == "new":
                    con.execute("UPDATE items SET defer_until=?,note='Follow-up check incomplete' WHERE url_hash=?",
                                (now+min(14400, 900 * 2**min(row["attempts"], 4)), item["url_hash"]))
                else:
                    # A missing report cannot reopen delivered/uncertain/terminal work.
                    con.execute("UPDATE writer_followup_checks SET completed_at=? WHERE assignment_id=?",
                                (now, item["url_hash"]))
                    con.execute("UPDATE writer_followups SET queued_assignment=NULL,revision=revision+1,"
                        "next_check_at=?,last_check_at=?,last_result='inconclusive',"
                        "last_note='Assignment finished without a check report; inspect actual output before further work',"
                        "updated_at=? WHERE queued_assignment=?", (now+3600, now, now, item["url_hash"]))


def checks(con, run_id):
    return [dict(r) for r in con.execute("SELECT a.*,c.followup_id,c.due_at,f.question,f.context_id "
        "FROM writer_followup_attempts a JOIN writer_followup_checks c USING(assignment_id) "
        "JOIN writer_followups f USING(followup_id) WHERE a.run_id=? ORDER BY a.started_at", (run_id,))]
