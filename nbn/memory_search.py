"""Small hybrid recall over current NBN records; no vector service/database required.

Indexing owns a background SQLite connection. Similarity is never event identity or evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import threading
import time

import httpx

from . import config, store

VERSION = "nomic-prefix-paragraph-v1"
TTL = 30 * 86400
_lock = threading.Lock()
_TEXT_FIELDS = {"title", "headlines", "text", "summary", "excerpt", "objective", "reason",
    "reporting_note", "unresolved", "unresolved_questions", "next_step", "limitations", "body",
    "proposed_post", "post", "watch_for", "editor_note", "note", "notes", "finding", "findings",
    "query", "answer", "source_summary", "purpose", "caption"}


def prose(value, depth=0):
    """Index substantive text, not JSON navigation/tool schemas or human-only feedback."""
    if depth > 7:
        return []
    if isinstance(value, dict):
        result = []
        for key, child in value.items():
            if key in {"desk_feedback", "raw_response", "input_schema", "request", "prompt"}:
                continue
            if key in _TEXT_FIELDS and isinstance(child, str):
                result.append(child)
            elif isinstance(child, (list, dict)):
                if key in _TEXT_FIELDS and isinstance(child, list):
                    result += [v for v in child if isinstance(v, str)]
                result += prose(child, depth+1)
        return result
    if isinstance(value, list):
        return [text for row in value for text in prose(row, depth+1)]
    return []


def documents(con, now=None):
    now = time.time() if now is None else now
    result = {}

    def add(ident, kind, title, at, state, text):
        body = (str(title) + "\n\n" + str(text)).strip()[:48000]
        result[ident] = {"context_id": ident, "kind": kind, "title": str(title)[:160],
            "at": at, "state": state, "text": body,
            "revision": hashlib.sha256((VERSION+"\n"+str(at)+"\n"+str(state)+"\n"+body).encode()).hexdigest()}

    for row in con.execute("SELECT * FROM newsroom_story_memory WHERE updated_at>?", (now-TTL,)):
        add("notebook:"+row["canonical_key"], "notebook", row["canonical_key"], row["updated_at"],
            row["state"], "\n\n".join(prose(store._safe_json_array(row["attempts_json"]))))
    for row in con.execute("SELECT * FROM newsroom_storylines WHERE lifecycle='open' OR last_signal_at>?", (now-TTL,)):
        add("storyline:"+row["storyline_key"], "storyline", row["title"], row["updated_at"], row["lifecycle"],
            row["summary"]+"\n\n"+"\n".join(store._safe_json_array(row["watch_for_json"])))
    for row in con.execute("SELECT * FROM writer_artifacts WHERE expires_at>?", (now,)):
        add(row["artifact_id"], row["kind"], row["title"], row["created_at"], row["canonical_key"],
            "\n".join([row["run_id"], *prose(store._safe_json_object(row["payload_json"]))]))
    for row in con.execute("SELECT * FROM writer_handoffs WHERE written_at>?", (now-TTL,)):
        add("letter:"+row["run_id"], "writer_letter", "Next-shift letter", row["written_at"], "handoff", row["run_id"]+"\n\n"+row["body"])
    for row in con.execute("SELECT asset_id,kind,created_at,metadata_json FROM visual_assets"):
        add(row["asset_id"], "visual_asset", row["kind"], row["created_at"], "historical_asset",
            "\n".join(prose(store._safe_json_object(row["metadata_json"]))))
    return result


def chunks(text):
    out, current = [], ""
    for paragraph in re.split(r"\n\s*\n", text):
        while len(paragraph) > 2100:
            if current:
                out.append(current)
                current = ""
            out.append(paragraph[:2100])
            paragraph = paragraph[2100:]
        if current and len(current)+len(paragraph) > 1400:
            out.append(current)
            current = ""
        current = (current+"\n\n"+paragraph).strip()
    if current:
        out.append(current)
    return out


def model_digest(timeout=2):
    response = httpx.get(config.MEMORY_EMBED_URL+"/api/tags", timeout=timeout)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict) or not isinstance(body.get("models"), list):
        raise ValueError("invalid_embedding_models_response")
    for model in body["models"]:
        if not isinstance(model, dict):
            raise ValueError("invalid_embedding_model_row")
        if model.get("name") == config.MEMORY_EMBED_MODEL:
            digest = model.get("digest")
            if isinstance(digest, str) and len(digest) >= 32:
                return digest
    raise ValueError("embedding_model_unavailable")


def vector(value):
    if (not isinstance(value, list) or len(value) != 768 or
            any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value)):
        raise ValueError("invalid_embedding_shape")
    norm = math.sqrt(sum(v*v for v in value))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("invalid_embedding_norm")
    return [v/norm for v in value]


def embed(texts, *, timeout=3):
    response = httpx.post(config.MEMORY_EMBED_URL+"/api/embed", json={
        "model": config.MEMORY_EMBED_MODEL, "input": texts, "truncate": False,
        "keep_alive": "30m", "options": {"num_thread": 1}}, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    values = body.get("embeddings") if isinstance(body, dict) else None
    if not isinstance(values, list) or len(values) != len(texts):
        raise ValueError("embedding_count_mismatch")
    return [vector(v) for v in values]


def cache_key(digest, text):
    return hashlib.sha256((VERSION+"\n"+digest+"\n"+text).encode()).hexdigest()


def index_batch(con, *, max_documents=4, seconds=25):
    """One outstanding HTTP call, no write transaction held during inference."""
    started = time.monotonic()
    docs = documents(con)
    digest = model_digest()
    indexed = {r["context_id"]: dict(r) for r in con.execute("SELECT * FROM memory_documents")}
    completed = 0
    for ident, doc in sorted(docs.items(), key=lambda pair: pair[1]["at"], reverse=True):
        if doc["kind"] == "visual_asset":
            continue  # Preserve lexical visual lookup without embedding image metadata.
        if completed >= max_documents or time.monotonic()-started >= seconds:
            break
        old = indexed.get(ident, {})
        if old.get("revision") == doc["revision"] and old.get("model_digest") == digest:
            continue
        pieces = chunks(doc["text"])
        keys = [cache_key(digest, "search_document: "+p) for p in pieces]
        missing = [(key, piece) for key, piece in zip(keys, pieces)
                   if not con.execute("SELECT 1 FROM memory_vectors WHERE cache_key=?", (key,)).fetchone()]
        for start in range(0, len(missing), 4):
            if time.monotonic()-started >= seconds:
                return {"completed": completed, "total": len(docs), "partial": True, "digest": digest}
            batch = missing[start:start+4]
            values = embed(["search_document: "+p for _, p in batch], timeout=10)
            with con:
                con.executemany("INSERT OR IGNORE INTO memory_vectors VALUES (?,?,?)",
                    [(key, json.dumps(v, separators=(",", ":")), time.time()) for (key, _), v in zip(batch, values)])
        # Re-read current source before activation. A changed/deleted source is not resurrected.
        current = documents(con).get(ident)
        if current and current["revision"] == doc["revision"]:
            with con:
                con.execute("INSERT OR REPLACE INTO memory_documents VALUES (?,?,?,?,?)",
                    (ident, doc["revision"], digest, json.dumps(keys), time.time()))
            completed += 1
    with con:
        con.executemany("DELETE FROM memory_documents WHERE context_id=?", [(i,) for i in indexed if i not in docs])
        # Keep only vectors referenced by active documents; partial new work has a day's grace.
        con.execute("DELETE FROM memory_vectors WHERE created_at<? AND cache_key NOT IN "
                    "(SELECT value FROM memory_documents,json_each(chunks_json))", (time.time()-86400,))
    return {"completed": completed, "total": len(docs), "partial": False, "digest": digest}


def search(con, query, *, offset=0, limit=40, now=None):
    started = time.monotonic()
    docs = documents(con, now)
    terms = list(dict.fromkeys(re.findall(r"[\w@.-]+", query.lower())))[:12]
    scored = []
    for ident, doc in docs.items():
        body = doc["text"].lower()
        score = sum(1 + (2 if t in doc["title"].lower() else 0) for t in terms if t in body)
        if query in {ident, ident.removeprefix("notebook:"), ident.removeprefix("storyline:"), ident.removeprefix("letter:")}:
            score += 100
        if score:
            scored.append((ident, score, doc["at"]))
    lexical = [r[0] for r in sorted(scored, key=lambda r: (-r[1], -r[2], r[0]))]
    semantic, reason, eligible_count = [], "embedding_not_configured", 0
    if config.MEMORY_EMBED_URL:
        try:
            digest = model_digest(timeout=1)
            current = [dict(r) for r in con.execute("SELECT * FROM memory_documents WHERE model_digest=?", (digest,))
                       if r["context_id"] in docs and r["revision"] == docs[r["context_id"]]["revision"]]
            eligible_count = len(current)
            if current:
                qv = embed(["search_query: "+query[:1200]], timeout=3)[0]
                similarities = []
                for row in current:
                    best = -1
                    for key in json.loads(row["chunks_json"]):
                        cached = con.execute("SELECT vector_json FROM memory_vectors WHERE cache_key=?", (key,)).fetchone()
                        if cached:
                            values = vector(json.loads(cached[0]))
                            best = max(best, sum(a*b for a, b in zip(qv, values)))
                    if best > 0:
                        similarities.append((row["context_id"], best))
                semantic = [i for i, _ in sorted(similarities, key=lambda r: (-r[1], r[0]))[:100]]
                reason = "hybrid" if semantic else "no_semantic_hits"
            else:
                reason = "index_pending"
        except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError):
            reason = "embedding_unavailable_keyword_fallback"
    scores = {}
    for ranking in (lexical, semantic):
        for rank, ident in enumerate(ranking):
            scores[ident] = scores.get(ident, 0) + 1/(60+rank)
    order = sorted(scores, key=lambda i: (-scores[i], -docs[i]["at"], i))
    # Exact IDs remain exact regardless of a semantically adjacent document's rank.
    order.sort(key=lambda i: query not in {i, i.removeprefix("notebook:"), i.removeprefix("storyline:"), i.removeprefix("letter:")})
    rows = [{k: docs[i][k] for k in ("context_id", "kind", "title", "at", "state")}
            for i in order[offset:offset+limit]]
    return {"rows": rows, "total": len(order), "offset": offset,
        "next_offset": offset+len(rows) if offset+len(rows)<len(order) else None,
        "window_days": 30, "retrieval": {"mode": reason, "indexed_current": eligible_count,
            "available_documents": len(docs), "elapsed_ms": round((time.monotonic()-started)*1000)},
        "note": "Dated reporting memory, not fresh evidence or proof of event identity; open current records before use."}


def health(con):
    value = store._safe_json_object(store.kv_get(con, "memory:index_health"))
    return {"configured": bool(config.MEMORY_EMBED_URL), "model": config.MEMORY_EMBED_MODEL,
            "index": value, "documents": con.execute("SELECT COUNT(*) FROM memory_documents").fetchone()[0],
            "vectors": con.execute("SELECT COUNT(*) FROM memory_vectors").fetchone()[0],
            "fallback": "ranked_keyword"}


def start_worker():
    if not config.MEMORY_EMBED_URL or not _lock.acquire(blocking=False):
        return

    def work():
        # Separate connection; never share the minute worker's transaction or await this thread.
        con = store.connect()
        while True:
            try:
                value = {**index_batch(con), "status": "ok", "at": time.time()}
            except Exception as exc:
                con.rollback()
                value = {"status": "degraded", "error": type(exc).__name__, "at": time.time()}
            try:
                store.kv_set(con, "memory:index_health", json.dumps(value))
            except Exception:
                con.rollback()
            time.sleep(60)
    threading.Thread(target=work, name="nbn-memory-index", daemon=True).start()
