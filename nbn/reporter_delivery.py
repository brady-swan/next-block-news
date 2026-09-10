"""Create-only Codex delivery, reusing NBN's durable outbox and exact media identity.

The reporter performs self-review; this path never invents a separate editor verdict.
No publish/schedule/PATCH/delete endpoint is exposed. Uncertain POSTs are never repeated.
"""
import json
import threading
import time

import httpx

from . import config, publisher, publisher_typefully as tf, publisher_visuals as pv
from . import reporter_store as rs, store, visuals, x_payload

_lock = threading.RLock()


def result(con, submission_id):
    row = con.execute("SELECT * FROM reporter_submissions WHERE submission_id=?", (submission_id,)).fetchone()
    if not row:
        raise ValueError("unknown submission")
    out = dict(row)
    out.pop("payload_json")
    if out.get("provider_ref"):
        out["typefully_url"] = f"https://typefully.com/?a={config.TYPEFULLY_SOCIAL_SET_ID}&d={out['provider_ref']}"
    return out


def update(con, ident, state, *, ref=None, error=None):
    with con:
        con.execute("UPDATE reporter_submissions SET state=?,provider_ref=COALESCE(?,provider_ref),"
                    "error=?,updated_at=? WHERE submission_id=?",
                    (state, ref, error, time.time(), ident))
    return result(con, ident)


def submit(con, *, shift_id, generation, submission_id, payload):
    rs.identifier(submission_id)
    encoded = rs.encoded(payload, 64 * 1024)
    fingerprint = rs.digest(payload)
    with _lock:
        existing = con.execute("SELECT * FROM reporter_submissions WHERE submission_id=?", (submission_id,)).fetchone()
        if existing:
            if existing["payload_hash"] != fingerprint or existing["shift_id"] != shift_id:
                raise ValueError("submission ID already binds different content")
            # Even after cutoff return the existing outcome, never a fresh submission.
            return advance(con, submission_id) if existing["state"] == "awaiting_media" else reconcile(con, submission_id)
        rs.assert_active(con, shift_id, generation)
        if config.OPERATING_MODE != "infrastructure" or config.AUTOPOST_ENABLED:
            raise ValueError("draft-only infrastructure mode required")
        key = store.canonical_story_key(con, rs.identifier(payload.get("event_key")))
        body, source = payload.get("body"), payload.get("source_url")
        if not isinstance(body, str) or not body.strip() or len(body) > 12000:
            raise ValueError("empty or oversized draft")
        from urllib.parse import urlsplit
        parsed = urlsplit(str(source or ""))
        if parsed.scheme not in {"https", "http"} or not parsed.hostname or parsed.username:
            raise ValueError("a source URL is required")
        if not isinstance(payload.get("self_review"), str) or not payload["self_review"].strip():
            raise ValueError("record your concise source/novelty/copy self-review before submission")
        evidence = payload.get("evidence_ids")
        if not isinstance(evidence, list) or not evidence or len(evidence) > 12:
            raise ValueError("include the IDs of evidence actually inspected")
        inspected = []
        for ident in evidence:
            record = con.execute("SELECT payload_json FROM reporter_records WHERE record_id=? AND kind='evidence'",
                                 (rs.identifier(ident),)).fetchone()
            if not record:
                raise ValueError("unknown evidence ID")
            inspected.append(json.loads(record[0]))
        def url_key(value):
            return str(value or "").split("#", 1)[0].rstrip("/")
        if not any(url_key(source) in {url_key(r.get(k)) for k in ("url", "final_url", "canonical_url")}
                   and isinstance(r.get("text"), str) and r["text"].strip()
                   and r.get("outcome", "ok") == "ok" and not r.get("error_kind") for r in inspected):
            raise ValueError("selected source URL must match a successfully inspected, nonempty evidence record")
        if store.exact_thread_output_exists(con, body, source):
            raise ValueError("this exact post and source are already in coverage")
        for r in con.execute("SELECT payload_json FROM reporter_remote_coverage WHERE status!='deleted'"):
            if json.loads(r[0]).get("texts") == publisher.one_off_x_thread(body, source):
                raise ValueError("this exact thread already exists in Typefully")
        for r in con.execute("SELECT payload_json FROM reporter_submissions WHERE state NOT IN ('failed','staged')"):
            pending = json.loads(r[0])
            if pending.get("body") == body and pending.get("source_url") == source:
                raise ValueError("this exact thread has uncertain delivery or preparation under another event key")
        current = store.canonical_output_state(con, key)
        if current["drafts"] or current["protected_mutations"]:
            raise ValueError("this event has an open draft or uncertain delivery; propose a revision in your notebook")
        if current["visible"] and not payload.get("material_update"):
            raise ValueError("event already covered; describe a material update or leave it alone")
        blocked = con.execute("SELECT 1 FROM reporter_submissions WHERE canonical_key=? "
                              "AND state NOT IN ('failed','staged')", (key,)).fetchone()
        if blocked:
            raise ValueError("this event already has protected reporter delivery")
        asset = None
        if payload.get("asset_id"):
            asset = visuals.get(con, payload["asset_id"])
            inspected = con.execute("SELECT 1 FROM reporter_records WHERE shift_id=? AND kind='asset_inspected' "
                "AND json_extract(payload_json,'$.asset_id')=? AND json_extract(payload_json,'$.content_hash')=?",
                (shift_id, asset["asset_id"], asset["content_hash"])).fetchone()
            if not inspected:
                raise ValueError("inspect the exact image pixels before selecting it")
            if asset["metadata"].get("reuse_status") not in {"nbn_original", "public_domain", "licensed", "permission"}:
                raise ValueError("image reuse permission is not established; inspection alone is not reuse authority")
        thread = publisher.one_off_x_thread(body, source)
        media_payload = x_payload.build(thread, asset)
        stamp = time.time()
        with con:
            con.execute("INSERT INTO reporter_submissions(submission_id,shift_id,generation,canonical_key,"
                "payload_hash,payload_json,state,created_at,updated_at) VALUES (?,?,?,?,?,?,'preparing',?,?)",
                (submission_id, shift_id, generation, key, fingerprint, encoded, stamp, stamp))
        materialization = {"body": body, "receipt_url": source, "klass": "codex_pilot",
            "item_hash": str(payload.get("candidate_id") or "")[:64], "publisher_backend": "typefully",
            "editor_note": "Codex self-review; owner review required. " + payload["self_review"][:230],
            "coverage_relation": "material_update" if current["visible"] else "distinct",
            "base_post_id": current["visible"]["id"] if current["visible"] else None,
            "codex_self_review": payload["self_review"], "reporter_shift_id": shift_id,
            "reporter_submission_id": submission_id,
            "evidence_ids": evidence, "media_payload": media_payload}
        intent = store.prepare_publisher_mutation(con, story_key=key, operation="create", intended_mode="DRAFT",
            desired_thread=[p["text"] for p in media_payload["posts"]], materialization=materialization,
            expected_output_signature=current["signature"])
        if not intent["ok"]:
            return update(con, submission_id, "failed", error=intent["reason"])
        with con:
            con.execute("UPDATE reporter_submissions SET mutation_id=?,state='awaiting_media' WHERE submission_id=?",
                        (intent["mutation_id"], submission_id))
        return advance(con, submission_id)


def advance(con, submission_id):
    with _lock:
        s = result(con, submission_id)
        if s["state"] != "awaiting_media":
            return reconcile(con, submission_id)
        row = dict(store.publisher_mutation(con, s["mutation_id"]))
        data = json.loads(row["materialization_json"])
        try:
            rs.assert_active(con, s["shift_id"], s["generation"])
            media = data["media_payload"]["posts"][0]["media"]
            if media:
                asset = visuals.get(con, media[0]["asset_id"])
                media_id = pv.upload_step(con, asset)
                if not media_id:
                    return s
                media[0]["media_id"] = media_id
            row = pv.update_intent(con, row, data, state="in_flight")
            update(con, submission_id, "in_flight")
            # Final fence AFTER slow media work and immediately before the remote POST.
            rs.assert_active(con, s["shift_id"], s["generation"])
            if config.OPERATING_MODE != "infrastructure" or config.AUTOPOST_ENABLED:
                raise ValueError("draft-only mode changed before delivery")
        except ValueError as exc:
            store.transition_publisher_mutation(con, row["mutation_id"], row["owner_token"], row["version"],
                "definite_failure", error_kind="reporter_preflight", error_message=str(exc))
            return update(con, submission_id, "failed", error=str(exc))
        acknowledged = False
        try:
            # No publish_at field, no fallback, no retries, no existing draft target.
            body = {"platforms": {"x": {"enabled": True, "posts": x_payload.request_posts(data["media_payload"])}},
                    "draft_title": data["body"][:60]}
            with rs.dispatch_lock:
                rs.assert_active(con, s["shift_id"], s["generation"])
                if config.OPERATING_MODE != "infrastructure" or config.AUTOPOST_ENABLED:
                    raise ValueError("draft-only mode changed before dispatch")
                response = httpx.post(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
                                      headers=tf._headers(), json=body, timeout=20)
            response.raise_for_status()
            acknowledged = True
            raw = response.json()
            ref = tf._feedback_draft_id(raw.get("id"))
            data.update(acknowledged_draft_id=ref, remote_version=x_payload.version(raw))
            row = pv.update_intent(con, row, data)
            update(con, submission_id, "in_flight", ref=ref)
            actual = tf.get_draft(ref)
            if actual.get("status") == "draft" and not actual.get("publish_at") and pv._finish(con, row, data, actual):
                return update(con, submission_id, "staged", ref=ref)
        except httpx.HTTPStatusError as exc:
            if not acknowledged and 400 <= exc.response.status_code < 500:
                store.transition_publisher_mutation(con, row["mutation_id"], row["owner_token"], row["version"],
                    "definite_failure", error_kind="reporter_remote_rejected", error_message=f"HTTP {exc.response.status_code}")
                return update(con, submission_id, "failed", error=f"HTTP {exc.response.status_code}")
        except Exception:
            pass  # Accepted remotely is possible; preserve the intent, never POST again.
        store.transition_publisher_mutation(con, row["mutation_id"], row["owner_token"], row["version"],
            "ambiguous", provider_ref=data.get("acknowledged_draft_id", ""), error_kind="reporter_confirmation_unknown")
        return update(con, submission_id, "uncertain", ref=data.get("acknowledged_draft_id"),
                      error="Delivery may exist. Read-only reconciliation or owner review required; do not resubmit.")


def reconcile(con, submission_id):
    """Read-only remote recovery; never invokes pending legacy jobs or a POST."""
    with _lock:
        return _reconcile_locked(con, submission_id)


def _reconcile_locked(con, submission_id):
    s = result(con, submission_id)
    if s["state"] == "preparing" and not s["mutation_id"]:
        rows = con.execute("SELECT mutation_id,state FROM publisher_mutations WHERE "
            "json_extract(materialization_json,'$.reporter_submission_id')=?", (submission_id,)).fetchall()
        if len(rows) == 1:
            with con:
                con.execute("UPDATE reporter_submissions SET mutation_id=?,state=? WHERE submission_id=?",
                    (rows[0]["mutation_id"], "awaiting_media" if rows[0]["state"] == "prepared" else "uncertain", submission_id))
            return result(con, submission_id)  # A later maintenance pass may advance a proven unsubmitted intent.
        if not rows:
            return update(con, submission_id, "failed", error="Preparation interrupted before any publisher intent; no remote request occurred.")
    if s["state"] not in {"preparing", "in_flight", "uncertain"} or not s["mutation_id"]:
        return s
    row = dict(store.publisher_mutation(con, s["mutation_id"]))
    if row["state"] == "confirmed":
        return update(con, submission_id, "staged", ref=row["provider_ref"])
    data = json.loads(row["materialization_json"])
    ref = s["provider_ref"] or data.get("acknowledged_draft_id")
    if ref:
        try:
            if pv._finish(con, row, data, tf.get_draft(ref)):
                return update(con, submission_id, "staged", ref=ref)
        except Exception:
            pass
    return s
