"""Read-only Typefully coverage and feedback snapshots for the reporter."""
import json
import re
import time

import httpx

from . import config, publisher_typefully as tf, reporter_store as rs, store

MORNING_BASELINE = ("10708378", "10708508", "10708509", "10708684", "10708911",
                    "10709124", "10709361", "10709480")


def capture(con, raw, *, comments=None):
    ident = tf._feedback_draft_id(raw.get("id"))
    old = con.execute("SELECT payload_json FROM reporter_remote_coverage WHERE draft_id=?", (ident,)).fetchone()
    previous = json.loads(old[0]) if old else {}
    payload = {"id": ident, "status": raw.get("status", "unknown"),
               "created_at": tf._timestamp(raw.get("created_at")), "published_at": tf._timestamp(raw.get("published_at")),
               "remote_updated_at": raw.get("updated_at"), "texts": tf.draft_x_texts(raw),
               "public_url": tf._public_x_url(raw.get("x_published_url")),
               "typefully_url": f"https://typefully.com/?a={config.TYPEFULLY_SOCIAL_SET_ID}&d={ident}",
               "comments": comments if comments is not None else previous.get("comments", []),
               "comments_checked_at": time.time() if comments is not None else previous.get("comments_checked_at"),
               "media": (raw.get("platforms") or {}).get("x", {}).get("posts", [])}
    with con:
        con.execute("INSERT INTO reporter_remote_coverage(draft_id,status,created_at,published_at,synced_at,payload_json) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(draft_id) DO UPDATE SET status=excluded.status,created_at=excluded.created_at,"
            "published_at=excluded.published_at,synced_at=excluded.synced_at,payload_json=excluded.payload_json",
            (ident, payload["status"], payload["created_at"], payload["published_at"], time.time(), rs.encoded(payload)))
        # Keep authored copy intact; current remote copy lives in this snapshot.
        con.execute("UPDATE posts SET publisher_status=?,publisher_synced_at=? "
                    "WHERE publisher_backend='typefully' AND nuelink_id=?",
                    (payload["status"], time.time(), ident))
        # Register the known eight outputs without creating/changing remote drafts.
        if ident in MORNING_BASELINE and payload["texts"] and not con.execute(
                "SELECT 1 FROM posts WHERE publisher_backend='typefully' AND nuelink_id=?", (ident,)).fetchone():
            published = payload["status"] == "published" and payload["published_at"] is not None
            receipt = re.search(r"https?://\S+", "\n".join(payload["texts"][1:]))
            con.execute("INSERT INTO posts(created,story_key,class,body,receipt_url,mode,nuelink_id,editor_note,"
                "publisher_backend,publisher_status,publisher_synced_at,confirmed_at,public_url) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (payload["created_at"] or time.time(), "manual-baseline:" + ident, "codex_manual_baseline",
                 payload["texts"][0], receipt.group(0) if receipt else "", "IMMEDIATE" if published else "DRAFT", ident,
                 "Known September 10 manual reporting experiment; imported read-only.", "typefully", payload["status"],
                 time.time(), payload["published_at"] if published else None, payload["public_url"]))
    return payload


def synchronize(con, *, force=False):
    if not config.TYPEFULLY_API_KEY or not config.TYPEFULLY_SOCIAL_SET_ID:
        return {"ok": False, "reason": "Typefully not configured"}
    stamp = time.time()
    last = float(store.kv_get(con, "reporter:coverage_attempt_at") or 0)
    if not force and stamp - last < 300:
        return {"cached": True}
    store.kv_set(con, "reporter:coverage_attempt_at", str(stamp))
    candidates = {}
    complete = False
    for page in range(10):
        response = httpx.get(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
            params={"order_by": "-updated_at", "limit": 50, "offset": page * 50}, headers=tf._headers(), timeout=20)
        response.raise_for_status()
        data = response.json()
        for raw in data.get("results", []):
            ident = tf._feedback_draft_id(raw.get("id"))
            published = tf._timestamp(raw.get("published_at"))
            if raw.get("status") != "published" or (published and published >= stamp - 48 * 3600) or ident in MORNING_BASELINE:
                candidates[ident] = raw
        if not data.get("next"):
            complete = True
            break
    # Known IDs are checked even when they are not present in the list page.
    for ident in MORNING_BASELINE:
        candidates.setdefault(ident, {"id": ident})
    # List absence is not deletion. Exact-ID readback resolves previously tracked drafts.
    for row in con.execute("SELECT draft_id FROM reporter_remote_coverage "
                           "WHERE status IN ('draft','scheduled','planned','publishing') ORDER BY synced_at LIMIT 100"):
        candidates.setdefault(row[0], {"id": row[0]})
    detailed = comments_read = 0
    comments_deferred = False
    for ident, summary in candidates.items():
        old = con.execute("SELECT payload_json FROM reporter_remote_coverage WHERE draft_id=?", (ident,)).fetchone()
        previous = json.loads(old[0]) if old else None
        changed = not previous or summary.get("updated_at") != previous.get("remote_updated_at") or summary.get("status") != previous.get("status")
        wants_comments = summary.get("status") == "draft" and (
            not previous or stamp - (previous.get("comments_checked_at") or 0) >= 600)
        if not changed and not wants_comments:
            continue
        if detailed >= 40:
            # Missing/changed COPY blocks duplicate-safe reporting. A deferred
            # refresh of comments on unchanged copy must not make it incomplete.
            if changed: complete = False
            if wants_comments: comments_deferred = True
            continue
        raw = tf.get_draft(ident)
        detailed += 1
        comments = None
        if raw.get("status") == "draft" and wants_comments and comments_read < 20:
            comments = tf.list_comment_threads(ident, status="all")
            comments_read += 1
        elif raw.get("status") == "draft" and wants_comments:
            comments_deferred = True
        if tf._has_comment_marker(raw):
            # Display only, never fed back into a PATCH.
            raw = tf.get_draft_for_feedback(ident)
        capture(con, raw, comments=comments)
    result = {"complete": complete, "candidates": len(candidates), "detail_reads": detailed,
              "comment_reads": comments_read, "comments_deferred": comments_deferred, "checked_at": stamp}
    store.kv_set(con, "reporter:coverage_sync", json.dumps(result))
    store.kv_set(con, "reporter:coverage_synced_at", str(stamp))
    return result
