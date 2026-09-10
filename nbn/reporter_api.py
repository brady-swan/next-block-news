"""Owner-approved, explicitly enabled HTTPS bridge behind Railway's TLS ingress.

Reporter and supervisor have separate credentials. No arbitrary publisher requests,
draft editing, scheduling, deletion, credential access, or deployment operations.
"""
import hashlib
import hmac
import json
import threading
import time
import uuid
from urllib.parse import parse_qs

from . import config, reporter_store as rs, reporter_tools as rt, store

PREFIX = "/reporter/api/"
_slots = threading.BoundedSemaphore(4)


def authorized(header):
    if not config.REPORTER_API_ENABLED or config.OPERATING_MODE != "infrastructure":
        return None
    reporter, control = config.REPORTER_TOKEN, config.REPORTER_CONTROL_TOKEN
    if min(len(reporter), len(control)) < 32 or reporter == control:
        return None
    if not isinstance(header, str) or not header.startswith("Bearer "):
        return None
    token = header[7:]
    if hmac.compare_digest(token, reporter):
        return "reporter"
    if hmac.compare_digest(token, control):
        return "control"
    return None


def pulse(con):
    coverage = [json.loads(r[0]) for r in con.execute(
        "SELECT payload_json FROM reporter_remote_coverage ORDER BY draft_id")]
    for row in coverage:
        row.pop("synced_at", None)
        row.pop("comments_checked_at", None)
    return {"shift": rs.shift(con),
            "intake_at": con.execute("SELECT MAX(first_seen) FROM items").fetchone()[0],
            "message_id": con.execute("SELECT MAX(id) FROM reporter_records WHERE sender='main_assistant'").fetchone()[0],
            "coverage_hash": hashlib.sha256(json.dumps(coverage, sort_keys=True).encode()).hexdigest()}


def dispatch(con, method, action, role, data):
    if method == "GET":
        if action == "tools": return {"tools": rt.TOOLS}
        if action == "pulse": return pulse(con)
        if action == "context": return rt.context(con, data.get("shift_id"))
        if action == "records": return rs.records(con, shift_id=data.get("shift_id"), after=data.get("after", 0))
        raise ValueError("unknown reporter read operation")
    if action == "tool":
        if role != "reporter": raise PermissionError("reporter credential required")
        started=time.time()
        outcome="error"
        try:
            result=rt.dispatch(con, shift_id=data["shift_id"], generation=data["generation"],
                               name=data["name"], args=data.get("arguments", {}))
            outcome="completed"
            return result
        finally:
            rs.record(con,shift_id=data["shift_id"],record_id="tool:"+uuid.uuid4().hex,kind="tool_activity",sender="system",
                      payload={"tool":data["name"],"outcome":outcome,"seconds":round(time.time()-started,2)})
    if role != "control": raise PermissionError("supervisor credential required")
    if action == "start": return rs.start(con, worker_id=data["worker_id"], shift_id=data["shift_id"])
    if action == "heartbeat":
        return rs.heartbeat(con, shift_id=data["shift_id"], generation=data["generation"],
                            worker_id=data["worker_id"], thread_id=data.get("thread_id"))
    if action == "stop": return rs.stop(con, data["shift_id"], status=data.get("status", "paused"))
    if action == "message":
        return rs.record(con, shift_id=data["shift_id"], record_id=data["record_id"], kind="message",
                         sender="main_assistant", payload=data["payload"], reply_to=data.get("reply_to"))
    if action == "record":
        if data["kind"] not in {"turn", "usage", "tool_activity", "supervisor", "turn_output"}:
            raise ValueError("supervisor record kind not allowed")
        return rs.record(con, shift_id=data["shift_id"], record_id=data["record_id"],
                         kind=data["kind"], sender="system", payload=data["payload"])
    if action == "delivered":
        ids = data["record_ids"]
        if not isinstance(ids, list) or len(ids) > 100: raise ValueError("invalid delivery IDs")
        with con:
            for ident in ids:
                con.execute("UPDATE reporter_records SET delivered_turn=COALESCE(delivered_turn,?) "
                    "WHERE record_id=? AND shift_id=? AND sender='main_assistant'",
                    (rs.identifier(data["turn_id"]), rs.identifier(ident), data["shift_id"]))
        return {"ok": True}
    if action == "coverage_sync":
        from . import reporter_remote
        return reporter_remote.synchronize(con, force=True)
    if action == "delivery_maintenance":
        from . import reporter_delivery as delivery
        rows = con.execute("SELECT submission_id,state FROM reporter_submissions WHERE shift_id=? "
            "AND state NOT IN ('failed','staged') LIMIT 20", (data["shift_id"],)).fetchall()
        return {"submissions": [(delivery.advance(con, r[0]) if r[1] == "awaiting_media"
                                 else delivery.reconcile(con, r[0])) for r in rows]}
    raise ValueError("unknown supervisor operation")


def handle(handler, parsed):
    role = authorized(handler.headers.get("Authorization"))
    code, result = 403, {"error": "reporter access unavailable"}
    if role and not _slots.acquire(blocking=False):
        code, result = 429, {"error": "reporter bridge busy; retry later"}
    elif role:
        con = None
        try:
            if handler.command == "POST":
                size = int(handler.headers.get("Content-Length", "0"))
                if not 0 < size <= 128 * 1024: raise ValueError("invalid request size")
                if handler.headers.get_content_type() != "application/json": raise ValueError("JSON required")
                data = json.loads(handler.rfile.read(size), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
            else:
                data = {k: v[0] for k, v in parse_qs(parsed.query).items()}
            if not isinstance(data, dict): raise ValueError("JSON object required")
            con = store.connect()
            result = dispatch(con, handler.command, parsed.path[len(PREFIX):], role, data)
            code = 200
        except PermissionError:
            code, result = 403, {"error": "credential role does not permit this operation"}
        except (ValueError, KeyError, TypeError) as exc:
            code, result = 409, {"error": str(exc)[:300]}
        except Exception as exc:
            # Never serialize provider headers, environment or authenticated URLs.
            code, result = 502, {"error": "reporter operation failed", "kind": type(exc).__name__}
        finally:
            if con is not None: con.close()
            _slots.release()
    body = json.dumps(result, ensure_ascii=False, allow_nan=False, default=str).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
