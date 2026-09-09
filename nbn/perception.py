"""Bounded Perception transport, dated evidence and quota accounting. No model calls.

REST/MCP are separate provider pools. Only plain keyword search has a verified
alternate route; their result caches never alias. Articles share stable versions.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import time
import uuid
from urllib.parse import urlsplit

import httpx

from . import config, observations, source_policy, store, writer_memory

CONTRACT = "perception-2026-09-09-v1"
MCP = "https://mcp.perception.to/mcp"
REST = "https://api.perception.to/feed"
MAX_BODY = 1024 * 1024
TOOLS = {"coverage": "perception_search_mentions", "entity": "perception_search_companies",
         "regulatory": "perception_search_regulatory", "article": "perception_get_article"}
LIMITATION = ("Perception corpus, not exhaustive coverage. Search rows are pointers, not inspected "
              "evidence. Original publication dates are distinct from discovery/retrieval time.")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def state(con, key):
    row = con.execute("SELECT v FROM kv WHERE k=?", ("perception:" + key,)).fetchone()
    return store._safe_json_object(row[0]) if row else {}


def set_state(con, key, value):
    con.execute("INSERT INTO kv(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                ("perception:" + key, encoded(value)))


def public_url(url):
    # No arbitrary URL is fetched here: provider URLs are fixed. Reject unsafe
    # pointers before they can become sources or be passed to the article service.
    from .newsroom import _cached_url_is_public
    return isinstance(url, str) and _cached_url_is_public(url)


def strip_guidance(text):
    return re.split(r"(?im)^\*\*Try next|^\*Data:|^---\s*$", str(text), maxsplit=1)[0].strip()


def publication(value, args=None):
    value = str(value or "").strip()
    for fmt, precision in (("%Y-%m-%d %H:%M:%S UTC", "second"),
                           ("%Y-%m-%d", "day"), ("%b %d, %Y", "day")):
        try:
            parsed = dt.datetime.strptime(value, fmt).replace(tzinfo=dt.timezone.utc)
            return (parsed.isoformat() if precision == "second" else parsed.date().isoformat()), precision
        except ValueError:
            pass
    try:
        if "T" in value:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo:
                return parsed.astimezone(dt.timezone.utc).isoformat(), "second"
        # Markdown search rows omit the year. Only infer it when the supplied
        # bounds select exactly one possible calendar date.
        if args and args.get("startDate") and args.get("endDate"):
            start, end = (dt.date.fromisoformat(args[k]) for k in ("startDate", "endDate"))
            possible = []
            for year in range(start.year, end.year + 1):
                try:
                    day = dt.datetime.strptime(value + f", {year}", "%b %d, %Y").date()
                    if start <= day <= end:
                        possible.append(day.isoformat())
                except ValueError:
                    pass
            if len(possible) == 1:
                return possible[0], "day_inferred_from_query"
    except (ValueError, TypeError):
        pass
    return "", "unknown"


def article_row(raw, now, args=None):
    get = lambda *keys: next((str(raw[k]).strip() for k in keys if raw.get(k)), "")
    url = get("URL", "url", "link")
    title = get("Title", "title", "headline")
    if not title or not public_url(url):
        return None
    text = strip_guidance(get("Content", "content", "text", "summary"))
    date_raw = get("Date", "date", "published_at")
    published, precision = publication(date_raw, args)
    body = text.encode("utf-8")[:24000].decode("utf-8", errors="ignore")
    links = [u for u in dict.fromkeys(re.findall(r"https?://[^\s<>\]\)\"']+", body)) if len(u) <= 1000][:8]
    return {"url": url, "canonical_url": source_policy.normalize_url(url), "title": title[:300],
            "source": get("Outlet", "outlet", "publisher", "source") or "Perception",
            "provider_item_id": get("id"), "byline": get("author_name", "author"),
            "text": body, "published_at": published, "publication_precision": precision,
            "publication_display": date_raw[:80], "inspected_at": now,
            "completeness": "unknown", "text_truncated": len(text) > len(body),
            "links": [{"url": u} for u in links if public_url(u)],
            "image_url": get("image_url") if len(get("image_url")) <= 2000 and public_url(get("image_url")) else "",
            "retrieval_kind": "provider_captured_text"}


def rpc_payload(text):
    if text.lstrip().startswith("{"):
        raw = json.loads(text)
    else:
        events = []
        for event in text.replace("\r\n", "\n").split("\n\n"):
            data = "\n".join(line[5:].lstrip() for line in event.splitlines() if line.startswith("data:"))
            if data:
                events.append(json.loads(data))
        raw = next((e for e in reversed(events) if "result" in e or "error" in e), {})
    if not isinstance(raw, dict):
        raise ValueError("rpc_format_unknown")
    if raw.get("error"):
        raise ValueError("rpc_error")
    result = raw.get("result")
    if not isinstance(result, dict) or result.get("isError"):
        raise ValueError("tool_error_or_missing_result")
    if "content" in result and (not isinstance(result["content"], list) or
            any(not isinstance(c, dict) or (c.get("type") == "text" and not isinstance(c.get("text"), str))
                for c in result["content"])):
        raise ValueError("content_format_unknown")
    return result


def parse_mcp(text, operation, args, now):
    result = rpc_payload(text)
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and isinstance(structured.get("data"), list):
        return {"rows": [v for r in structured["data"][:100] if isinstance(r, dict)
                         and (v := article_row(r, now, args))], "partial": True}
    body = strip_guidance("\n".join(c.get("text", "") for c in result.get("content", [])
                                   if c.get("type") == "text"))
    if operation == "article":
        heading = re.search(r"^##\s+\[(.*?)\]\((https?://[^\s]+)\)", body, re.M)
        meta = dict(re.findall(r"\|\s*\*\*(\w+)\*\*\s*\|\s*(.*?)\s*\|", body))
        parts = re.split(r"(?im)^###\s+Full Text\s*$", body, maxsplit=1)
        if not heading or len(parts) < 2:
            raise ValueError("article_format_unknown")
        row = article_row({"URL": meta.get("URL") or heading[2], "Title": heading[1],
                           "Content": parts[1], "Date": meta.get("Date"),
                           "Outlet": meta.get("Outlet"), "author_name": meta.get("Author")}, now, args)
        if not row or not row["text"]:
            raise ValueError("article_empty_or_unsafe")
        if source_policy.normalize_url(args["url"]) != row["canonical_url"]:
            raise ValueError("article_identity_mismatch")
        return {"article": row}
    rows = []
    if operation == "regulatory":
        for match in re.finditer(r"(?m)^\*\*\[(.*?)\]\((https?://[^\s]+)\)\*\*\s*\n([^\n]*?)\s*·\s*([^\n]+)", body):
            row = article_row({"Title": match[1], "URL": match[2], "Outlet": match[3], "Date": match[4]}, now, args)
            if row:
                rows.append(row)
    for line in body.splitlines():
        match = re.match(r"\|\s*\d+\s*\|\s*\[(.*?)\]\((https?://[^\s]+)\)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", line)
        if match:
            row = article_row({"Title": match[1], "URL": match[2], "Outlet": match[3], "Date": match[4]}, now, args)
            if row:
                rows.append(row)
    empty = re.search(r"(?im)(?:^\*\*0(?:\*\*\s+|\s+)(?:mentions|results|documents)|^No (?:matching )?(?:mentions|results|articles|documents)(?: found(?: for [^\n]+)?)?\.?\s*$)", body)
    if operation == "regulatory":
        empty = empty or re.search(r"(?m)^No regulatory documents found for this query and date range\.\s*$", body)
    if not rows and not empty:
        raise ValueError("search_format_unknown")
    if not rows and empty:
        return {"rows": [], "total": 0, "partial": False}
    count = re.search(r"\*\*(\d+)\*\*(?: of \*\*(\d+)\*\*)? mentions", body)
    total = int(count[2] or count[1]) if count else None
    if operation == "regulatory":
        count = re.search(r"\*\*(\d+) documents?\*\*", body)
        total = int(count[1]) if count else None
    return {"rows": rows, "total": total, "partial": total is None or total > len(rows)}


def daily_counts(con, now):
    start = now - now % 86400
    return [dict(r) for r in con.execute("SELECT surface,purpose,COUNT(*) AS attempts FROM perception_requests "
                                        "WHERE started_at>=? GROUP BY surface,purpose", (start,))]


def observe_quota(con, surface, headers, now):
    """Honor observed exhaustion; do not relabel the shared minute pool as daily."""
    policy = headers.get("ratelimit-policy", "")
    if "w=60" in policy and headers.get("ratelimit-remaining") == "0":
        set_state(con, "shared_cooldown", {"kind": "shared_minute_limit", "until": now + 60})
    if surface == "rest" and headers.get("x-ratelimit-remaining") is not None:
        try:
            remaining = int(headers["x-ratelimit-remaining"])
            raw_reset = headers.get("x-ratelimit-reset", "")
            try:
                reset = float(raw_reset)
                reset = reset if reset > now else now + min(86400, max(1, reset))
            except ValueError:
                reset = dt.datetime.fromisoformat(raw_reset.replace("Z", "+00:00")).timestamp()
            reset = max(now+1, min(now+86400, reset))
            set_state(con, "rest_reported_quota", {"remaining": remaining, "until": reset,
                       "observed_at": now, "scope": "REST provider-reported window; separate from shared minute quota"})
            if remaining <= 0:
                set_state(con, "rest_cooldown", {"kind": "rest_reported_quota_exhausted", "until": reset})
        except (ValueError, OverflowError):
            # Missing reset is explicit uncertainty, never invented headroom.
            if headers.get("x-ratelimit-remaining") == "0":
                set_state(con, "rest_cooldown", {"kind": "rest_reported_quota_reset_unknown", "until": now+300})


def availability(con, surface, purpose, now):
    for key in ("shared_cooldown", surface + "_cooldown"):
        row = state(con, key)
        if row.get("until", 0) > now:
            return row.get("kind", "cooldown")
    if purpose != "intake":
        used = sum(r["attempts"] for r in daily_counts(con, now) if r["purpose"] != "intake")
        if used >= config.PERCEPTION_NEW_WORK_DAILY:
            return "local_new_work_limit"
        # No provider balance means no evidence that REST has spare intake capacity.
        if surface == "rest":
            used_rest = sum(r["attempts"] for r in daily_counts(con, now)
                            if r["purpose"] != "intake" and r["surface"] == "rest")
            if used_rest >= 4:
                return "rest_new_work_reserve"
    return ""


def request(con, surface, operation, args, *, purpose="writer", timeout=20, refresh=False):
    now = time.time()
    if not config.PERCEPTION_API_KEY:
        return {"ok": False, "kind": "not_configured"}
    key = digest([CONTRACT, surface, operation, args])
    cached = con.execute("SELECT payload_json FROM perception_cache WHERE cache_key=? AND expires_at>?", (key, now)).fetchone()
    if cached and not refresh:
        reused = state(con, "reuse")
        set_state(con, "reuse", {**reused, "query_cache_hits": int(reused.get("query_cache_hits", 0)) + 1,
                                 "last_cache_hit": now})
        con.commit()
        return {**json.loads(cached[0]), "cached": True}
    blocked = availability(con, surface, purpose, now)
    if blocked:
        return {"ok": False, "kind": blocked, "surface": surface}
    uid = str(uuid.uuid4())
    con.execute("INSERT INTO perception_requests(request_id,surface,operation,purpose,started_at,status) "
                "VALUES(?,?,?,?,?,'started')", (uid, surface, operation, purpose, now))
    con.commit()  # Attempts survive timeout/process death, before any network work.
    started, status, code, quota = time.monotonic(), "error", None, {}
    deadline = started + max(1, min(float(timeout), 20))
    try:
        headers = {"Authorization": "Bearer " + config.PERCEPTION_API_KEY,
                   "Accept": "application/json, text/event-stream", "Idempotency-Key": uid}
        kwargs = {"params": args} if surface == "rest" else {"json": {
            "jsonrpc": "2.0", "id": uid, "method": "tools/call",
            "params": {"name": TOOLS[operation], "arguments": args}}}
        with httpx.Client(timeout=max(1, min(float(timeout), 20)), headers=headers) as client:
            with client.stream("GET" if surface == "rest" else "POST", REST if surface == "rest" else MCP, **kwargs) as response:
                code = response.status_code
                quota = {k: v for k, v in response.headers.items() if k.lower() in {
                    "ratelimit-policy", "ratelimit-limit", "ratelimit-remaining", "ratelimit-reset",
                    "x-ratelimit-limit", "x-ratelimit-remaining", "x-ratelimit-reset", "retry-after"}}
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    if time.monotonic() >= deadline:
                        raise ValueError("request_deadline_exceeded")
                    size += len(chunk)
                    if size > MAX_BODY:
                        raise ValueError("response_too_large")
                    chunks.append(chunk)
                text = b"".join(chunks).decode("utf-8")
        if time.monotonic() >= deadline:
            raise ValueError("request_deadline_exceeded")
        observe_quota(con, surface, quota, now)
        if code != 200:
            if code in (401, 403, 402, 429):
                # Minute throttling is shared. Unknown quota errors do NOT authorize
                # automatic cross-pool attempts or wallet spending.
                kind = "auth" if code in (401, 403) else "payment_required" if code == 402 else "quota_unknown"
                seconds = 3600 if code != 429 else 300
                daily = code == 429 and bool(re.search(r"(?i)daily.{0,30}(?:quota|limit)|(?:quota|limit).{0,30}daily", text[:1000]))
                if daily:
                    kind, seconds = surface + "_daily_exhausted", 86400 - now % 86400
                try:
                    seconds = max(seconds, min(86400, int(quota.get("retry-after", "0"))))
                except ValueError:
                    pass
                set_state(con, "shared_cooldown" if code == 429 and not daily else surface + "_cooldown",
                          {"kind": kind, "until": now + seconds})
                raise ValueError(kind)
            raise ValueError("http_" + str(code))
        if surface == "rest":
            raw = json.loads(text)
            raw_rows = raw.get("data") if isinstance(raw, dict) else raw
            if not isinstance(raw_rows, list):
                raise ValueError("feed_format_unknown")
            valid_rows = [v for r in raw_rows[:100] if isinstance(r, dict) and (v := article_row(r, now, args))]
            paging = raw.get("pagination", {}) if isinstance(raw, dict) else {}
            if not isinstance(paging, dict):
                raise ValueError("pagination_format_unknown")
            parsed = {"rows": valid_rows, "pagination": paging,
                      "partial": not bool(paging) or bool(paging.get("hasNextPage")) or bool(paging.get("truncated"))
                                 or len(valid_rows) < len(raw_rows)}
        else:
            parsed = parse_mcp(text, operation, args, now)
        result = {"ok": True, "surface": surface, "operation": operation, "cached": False,
                  "retrieved_at": now, "scope": LIMITATION, **parsed}
        ttl = 300 if parsed.get("rows") or parsed.get("article") else 60
        con.execute("INSERT INTO perception_cache VALUES(?,?,?) ON CONFLICT(cache_key) DO UPDATE "
                    "SET payload_json=excluded.payload_json,expires_at=excluded.expires_at",
                    (key, encoded(result), now + ttl))
        if purpose == "survey":
            # Replay completed survey delivery after a crash without paying again.
            set_state(con, "survey_pending", result)
        status = "ok"
        return result
    except (httpx.HTTPError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        status = type(exc).__name__ if not isinstance(exc, ValueError) else str(exc)[:70]
        # Persist a bounded backoff on failures, not a bogus cached empty answer.
        if code not in (401, 403, 402, 429):
            set_state(con, surface + "_cooldown", {"kind": "provider_backoff", "until": now + 60})
        return {"ok": False, "kind": status, "surface": surface,
                "retry_same_call": False, "message": "Use other available research or finish supported work."}
    finally:
        con.execute("UPDATE perception_requests SET completed_at=?,status=?,http_status=?,elapsed_ms=?,quota_json=? "
                    "WHERE request_id=?", (time.time(), status, code, int((time.monotonic()-started)*1000), encoded(quota), uid))
        con.commit()


def save_article(con, row, candidate_id=""):
    """Stable source version; caller owns transaction. Unchanged capture never renews."""
    if not row.get("text"):
        return ""
    fingerprint = source_policy.content_fingerprint(row["text"])
    version = digest([row["canonical_url"], fingerprint, row["published_at"], row["byline"]])
    aid = "artifact_perception_" + version[:24]
    source = source_policy.classify(row["url"], "")
    payload = {**row, "fetch_id": aid, "requested_url": row["url"], "final_url": row["url"],
               "source_id": source.source_id, "source_name": source.display_name,
               "adapter_provenance": "perception", "content_fingerprint": fingerprint,
               "limitations": "Provider-captured text; completeness unknown (may be a summary). "
                              "Not a direct page fetch or independent corroborating publisher. "
                              "Publication precision: " + row["publication_precision"],
               "image_candidates": []}
    safe, _ = observations.clean(payload)
    body = encoded(safe)
    if len(body.encode()) > 48 * 1024:
        raise ValueError("source_artifact_too_large")
    now = row["inspected_at"]
    run = "perception-source:" + dt.datetime.fromtimestamp(now, dt.timezone.utc).date().isoformat()
    con.execute("INSERT OR IGNORE INTO writer_artifacts(artifact_id,run_id,kind,candidate_ids_json,title,payload_json,"
                "search_text,created_at,expires_at) VALUES(?,?,'receipt',?,?,?,?,?,?)",
                (aid, run, encoded([candidate_id] if candidate_id else []), row["title"], body,
                 (row["title"] + " " + body)[:32000], now, now + writer_memory.TTL))
    if candidate_id:
        prior = con.execute("SELECT candidate_ids_json FROM writer_artifacts WHERE artifact_id=?", (aid,)).fetchone()
        ids = list(dict.fromkeys(store._safe_json_array(prior[0]) + [candidate_id]))[:25]
        con.execute("UPDATE writer_artifacts SET candidate_ids_json=? WHERE artifact_id=?", (encoded(ids), aid))
    return aid


def retained_article(con, url, now=None):
    now = time.time() if now is None else now
    row = con.execute("SELECT artifact_id,payload_json FROM writer_artifacts WHERE kind='receipt' "
                      "AND json_extract(payload_json,'$.canonical_url')=? "
                      "AND json_extract(payload_json,'$.adapter_provenance')='perception' AND expires_at>? "
                      "ORDER BY created_at DESC LIMIT 1", (source_policy.normalize_url(url), now)).fetchone()
    return {**json.loads(row["payload_json"]), "artifact_id": row["artifact_id"]} if row else None


def summary(con, now):
    recent = [dict(r) for r in con.execute("SELECT surface,operation,purpose,status,http_status,elapsed_ms,started_at,quota_json "
                                          "FROM perception_requests ORDER BY started_at DESC LIMIT 12")]
    return {"enabled": config.PERCEPTION_TOOLS_ENABLED, "daily_new_work_limit": config.PERCEPTION_NEW_WORK_DAILY,
            "survey_daily_limit": config.PERCEPTION_SURVEY_DAILY, "today": daily_counts(con, now),
            "quota_scope": "NBN local attempts only; shared account remaining unknown; REST/MCP are separate pools",
            "feed": state(con, "feed"), "survey": state(con, "survey"), "recent": recent,
            "reuse_since_release": state(con, "reuse"),
            "reported_rest_quota": state(con, "rest_reported_quota"),
            "cooldowns": {k: state(con, k) for k in ("rest_cooldown", "mcp_cooldown", "shared_cooldown")}}


def collect(con):
    from .sources import CollectedBatch
    batch = CollectedBatch()
    if con is None or not config.PERCEPTION_DIRECT_ENABLED or not config.PERCEPTION_API_KEY:
        return batch
    now = time.time()
    with con:
        con.execute("DELETE FROM perception_cache WHERE expires_at<?", (now - 3600,))
        con.execute("DELETE FROM perception_requests WHERE started_at<?", (now - 30*86400,))
    checkpoint = state(con, "feed")
    today = dt.datetime.fromtimestamp(now, dt.timezone.utc).date()
    dates = {"startDate": (today-dt.timedelta(days=1)).isoformat(), "endDate": today.isoformat()}
    if now >= checkpoint.get("next_poll_at", 0):
        # Alternate newest-page reads with backlog pages. A frozen window is only
        # best-effort under the vendor's mutable offset ordering, never lossless.
        catchup = bool(checkpoint.get("next_page", 0)) and not checkpoint.get("last_was_backlog", False)
        page = checkpoint["next_page"] if catchup else 1
        bounds = checkpoint.get("window", dates) if catchup else dates
        result = request(con, "rest", "feed", {"keyword": "bitcoin", **bounds, "limit": 50, "page": page}, purpose="intake")
        if result["ok"]:
            batch.extend(as_items(result.get("rows", [])))
            paging = result.get("pagination") or {}
            next_page = page + 1 if paging.get("hasNextPage") else 0
            window = bounds
            if not catchup and checkpoint.get("next_page"):
                next_page, window = checkpoint["next_page"], checkpoint["window"]
            progress = {"next_poll_at": now + config.PERCEPTION_POLL_SECONDS,
                        "next_page": next_page, "window": window, "last_was_backlog": catchup,
                        "last_page": page, "last_success": now, "partial": bool(next_page) or not bool(paging)
                          or result.get("partial", False) or bool(paging.get("truncated")),
                        "pagination": paging}
            batch.checkpoints["perception:feed"] = encoded(progress)
            observations.source_poll(con, "perception", "Perception", "perception", count=len(batch))
        else:
            observations.source_poll(con, "perception", "Perception", "perception", error=result["kind"])
    survey = state(con, "survey")
    pending_survey = state(con, "survey_pending")
    if pending_survey.get("ok"):
        batch.extend(as_items(pending_survey.get("rows", [])))
        batch.checkpoints["perception:survey_pending"] = "{}"
        batch.checkpoints["perception:survey"] = encoded({**survey,
            "last_success": pending_survey["retrieved_at"],
            "returned": len(pending_survey.get("rows", [])),
            "partial": pending_survey.get("partial", True)})
        return batch
    if config.PERCEPTION_TOOLS_ENABLED and config.PERCEPTION_SURVEY_DAILY > 0 and now >= survey.get("next_at", 0):
        count = sum(r["attempts"] for r in daily_counts(con, now) if r["purpose"] == "survey")
        if count < config.PERCEPTION_SURVEY_DAILY:
            slot = int(now // (86400 / min(8, config.PERCEPTION_SURVEY_DAILY)))
            if state(con, "survey_attempt").get("slot") == slot:
                return batch
            set_state(con, "survey_attempt", {"slot": slot, "at": now})
            con.commit()  # At most one attempt per slot, even across failure/restart.
            index = slot % 4
            operation = "regulatory" if index == 3 else "coverage"
            params = {"q": "bitcoin"} if index == 3 else {
                "subject_ids": [["self-custody"], ["mining-pools"], ["merchant-payments"]][index]}
            result = request(con, "mcp", operation, {**params, **dates, "limit": 10}, purpose="survey", timeout=10)
            if result["ok"]:
                batch.extend(as_items(result.get("rows", [])))
                batch.checkpoints["perception:survey"] = encoded({
                    "next_at": (slot + 1) * (86400 / min(8, config.PERCEPTION_SURVEY_DAILY)),
                    "last_success": now, "beat": index, "returned": len(result.get("rows", [])),
                    "partial": result.get("partial", True)})
                batch.checkpoints["perception:survey_pending"] = "{}"
    return batch


def as_items(rows):
    return [{"source": row["source"], "title": row["title"], "url": row["url"],
             "published": row["published_at"], "summary": row["text"][:600],
             "_perception_article": row} for row in rows]


def coverage(con, operation, args, *, timeout, refresh=False):
    # Routing is deliberately narrow. Shared throttling, failures or timeouts are
    # not evidence that switching transport would be a safe equivalent retry.
    simple = operation == "coverage" and re.fullmatch(r"[A-Za-z0-9]+", args.get("q", ""))
    basic = not (set(args) - {"q", "startDate", "endDate", "limit"})
    now = time.time()
    mcp_count = sum(r["attempts"] for r in daily_counts(con, now)
                    if r["purpose"] != "intake" and r["surface"] == "mcp")
    # Soft preference only: specialists can still use all remaining total calls.
    prefer_rest = simple and basic and (mcp_count >= 20 or
        availability(con, "mcp", "writer", now) == "mcp_daily_exhausted")
    started = time.monotonic()
    result = {"ok": False, "kind": "mcp_daily_exhausted"} if prefer_rest and not availability(con, "rest", "writer", now) else request(
        con, "mcp", operation, args, timeout=timeout, refresh=refresh)
    remaining = timeout - (time.monotonic() - started)
    if simple and basic and result.get("kind") == "mcp_daily_exhausted" and remaining >= 2:
        params = {"keyword": args["q"], "startDate": args["startDate"], "endDate": args["endDate"],
                  "limit": args.get("limit", 10), "page": 1}
        result = request(con, "rest", "feed", params, timeout=remaining, refresh=refresh)
    if result.get("ok"):
        # REST results may contain bodies; retain them once, but expose only
        # pointers until the Writer explicitly reads that dated article.
        rows = result.get("rows", [])[:args.get("limit", 10)]
        with con:
            for row in rows:
                save_article(con, row)
        result = {**result, "rows": [{k: row.get(k) for k in (
            "url", "title", "source", "published_at", "publication_precision", "publication_display")}
                                      for row in rows]}
    return result


def writer_tools():
    dates = {"start_date": {"type": "string", "description": "YYYY-MM-DD inclusive"},
             "end_date": {"type": "string", "description": "YYYY-MM-DD inclusive"}}
    def tool(name, description, properties, required):
        return {"name": name, "description": description,
                "input_schema": {"type": "object", "properties": properties,
                                 "required": required, "additionalProperties": False}}
    common = {**dates, "candidate_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
              "limit": {"type": "integer", "minimum": 1, "maximum": 15},
              "refresh": {"type": "boolean"}}
    return [tool("perception_coverage", "Search Perception's industry corpus for original reports and company coverage. "
                 "Returns dated source pointers, not article evidence. Read a promising original; do not research every lead by ritual.",
                 {**common, "query": {"type": "string"}, "company": {"type": "string", "description": "Optional entity-recognition mode instead of keyword search"},
                  "outlet": {"type": "string"}}, ["query", "start_date", "end_date"]),
            tool("perception_article", "Read retained Perception article text or retrieve it by original URL. "
                 "May be partial/summary. Keeps publication and capture dates; refresh bypasses retained reuse. "
                 "This is provider-captured material, not an independent second source.",
                 {"url": {"type": "string"}, "publication_date": {"type": "string"},
                  "refresh": {"type": "boolean"}, "candidate_ids": common["candidate_ids"]}, ["url"]),
            tool("perception_regulatory", "Find agency/jurisdiction-specific filings, policy documents and reporting. "
                 "Returned links are research pointers, not proof of a law's status.",
                 {**common, "query": {"type": "string"}, "agency": {"type": "string"},
                  "jurisdiction": {"type": "string", "enum": ["US", "EU", "UK", "Asia", "International"]}},
                 ["query", "start_date", "end_date"])]


WRITER_TOOL_NAMES = {t["name"] for t in writer_tools()}


def writer_call(desk, name, value):
    if not config.PERCEPTION_TOOLS_ENABLED:
        return {"ok": False, "kind": "perception_disabled"}
    timeout = min(20, desk._research_seconds_left() - 2)
    if timeout < 2:
        return {"ok": False, "kind": "finalization_reserve"}
    refresh = bool(value.get("refresh"))
    candidates = [str(cid) for cid in value.get("candidate_ids", []) if cid in desk.by_hash][:10]
    if name == "perception_article":
        url = str(value.get("url", ""))
        if not public_url(url):
            return {"ok": False, "kind": "invalid_source_url"}
        # Article reads share the established text/fetch budget, even from cache.
        remaining = config.RUN_NEWSROOM_MAX_FETCH_TOTAL_CHARS - desk.fetch_chars
        if desk.fetch_count >= config.RUN_NEWSROOM_MAX_FETCHES or remaining <= 0:
            return {"ok": False, "kind": "fetch_capacity"}
        cached = retained_article(desk.con, url) if not refresh else None
        reused_capture = bool(cached)
        if not cached:
            args = {"url": url}
            if value.get("publication_date"):
                dt.date.fromisoformat(value["publication_date"])
                args["publication_date"] = value["publication_date"]
            result = request(desk.con, "mcp", "article", args, timeout=timeout, refresh=refresh)
            if not result["ok"]:
                return result
            with desk.con:
                aid = save_article(desk.con, result["article"], candidates[0] if candidates else "")
            cached = retained_article(desk.con, url)
            if not aid or not cached:
                return {"ok": False, "kind": "article_not_retained"}
        raw = dict(cached)
        raw["text"] = raw["text"][:min(config.RUN_NEWSROOM_MAX_FETCH_CHARS, remaining)]
        raw["text_truncated"] = raw.get("text_truncated", False) or len(raw["text"]) < len(cached["text"])
        raw["original_content_fingerprint"] = raw["content_fingerprint"]
        raw["content_fingerprint"] = source_policy.content_fingerprint(raw["text"])
        desk.fetch_count += 1
        desk.fetch_chars += len(raw["text"])
        restored = desk._restore_receipt(raw)
        if not restored.get("ok"):
            return {"ok": False, **restored}
        writer_memory.save(desk.con, desk.run_id, restored["fetch_id"], "receipt", restored,
                           candidate_ids=candidates, title=cached["title"])
        if reused_capture:
            stats = state(desk.con, "reuse")
            set_state(desk.con, "reuse", {**stats, "retained_article_reads": int(stats.get("retained_article_reads", 0)) + 1})
            desk.con.commit()
        return {**restored, "artifact_id": cached["artifact_id"], "capture_reused": reused_capture,
                "note": "Retained dated Perception text; reading it does not refresh its evidence date."}
    start, end = (dt.date.fromisoformat(str(value[k])) for k in ("start_date", "end_date"))
    if end < start or (end - start).days > 30:
        return {"ok": False, "kind": "date_range_must_be_0_to_30_days"}
    args = {"startDate": start.isoformat(), "endDate": end.isoformat(),
            "limit": max(1, min(15, int(value.get("limit") or 10)))}
    operation = "regulatory" if name == "perception_regulatory" else "entity" if value.get("company") else "coverage"
    args["company" if operation == "entity" else "q"] = str(value.get("company") if operation == "entity" else value.get("query", ""))[:200]
    for key in ("agency", "jurisdiction") if operation == "regulatory" else ("outlet",) if operation == "coverage" else ():
        if value.get(key):
            args[key] = str(value[key])[:100]
    return coverage(desk.con, operation, args, timeout=timeout, refresh=refresh)


def candidate_hint(con, url):
    row = retained_article(con, url)
    if not row:
        return None
    return {"url": row["final_url"], "artifact_id": row["artifact_id"],
            "published_at": row["published_at"], "captured_at": row["inspected_at"],
            "characters": len(row["text"]), "completeness": row["completeness"],
            "use": "Available dated text, not yet read in this session; use perception_article if useful."}
