"""Curated discovery leads from the Marketing Node.

The Node payload is deliberately discovery-only: its prose may help triage decide
whether to investigate a link, but it is never evidence for drafting or verification.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
import time

import httpx

from . import config, sources, store

log = logging.getLogger("nbn.node_discovery")

THROTTLE_SECONDS = 300
ACCEPTED_STATUSES = {"accepted", "partial"}


class InvalidNodeEnvelope(ValueError):
    """The authenticated endpoint returned data outside the reviewed contract."""


def _short_text(value, limit: int, *, required: bool = False) -> str:
    if not isinstance(value, str):
        if required:
            raise InvalidNodeEnvelope("required candidate text missing")
        return ""
    cleaned = " ".join(value.split())
    if required and not cleaned:
        raise InvalidNodeEnvelope("required candidate text empty")
    if len(cleaned) > limit:
        raise InvalidNodeEnvelope("candidate text exceeds contract")
    return cleaned


def _candidate_id(run_id: int, source_id: str | None, discovery_key: str) -> str:
    normalized = " ".join(str(source_id or "").split())
    if not normalized or len(normalized) > 120:
        normalized = "-"
    material = f"v1\n{run_id}\n{normalized}\n{discovery_key}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _bounded_context(payload: dict, run: dict, selected_date: str) -> dict:
    if not isinstance(payload, dict):
        raise InvalidNodeEnvelope("context must be an object")
    theme = _short_text(payload.get("theme"), 240) or None
    must_know = payload.get("must_know_titles", [])
    limitations = payload.get("limitations", [])
    if not isinstance(must_know, list) or len(must_know) > 8:
        raise InvalidNodeEnvelope("must_know_titles outside contract")
    if not isinstance(limitations, list) or len(limitations) > 20:
        raise InvalidNodeEnvelope("limitations outside contract")
    brief_date = payload.get("daily_brief_date")
    if brief_date != selected_date:
        raise InvalidNodeEnvelope("daily brief date does not match selected date")
    workflow_id = payload.get("daily_brief_workflow_run_id")
    if workflow_id is not None and (isinstance(workflow_id, bool) or not isinstance(workflow_id, int)):
        raise InvalidNodeEnvelope("daily brief workflow run id is invalid")
    return {
        "theme": theme,
        "must_know_titles": [_short_text(v, 240, required=True) for v in must_know],
        "limitations": [_short_text(v, 300, required=True) for v in limitations],
        "daily_brief_workflow_run_id": workflow_id,
        "daily_brief_date": brief_date,
        "node_snapshot_run_id": run["run_id"],
    }


def _diagnostics(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise InvalidNodeEnvelope("diagnostics must be an object")
    result = {}
    for key in ("refs_seen", "invalid_refs", "duplicate_refs", "candidates_returned"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidNodeEnvelope(f"invalid diagnostic {key}")
        result[key] = value
    if result["candidates_returned"] > 12:
        raise InvalidNodeEnvelope("too many returned candidates")
    return result


def _candidate_context_json(context: dict, run_id: int, selected_date: str) -> str:
    value = {
        "untrusted_discovery_context": True,
        "origin": "marketing_node_daily_brief_more_reads",
        "theme": context["theme"],
        "must_know_titles": list(context["must_know_titles"]),
        "limitations": list(context["limitations"]),
        "node_snapshot_run_id": run_id,
        "daily_brief_workflow_run_id": context["daily_brief_workflow_run_id"],
        "daily_brief_date": selected_date,
    }
    while True:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) <= 8192:
            return encoded
        if value["limitations"]:
            value["limitations"].pop()
        elif value["must_know_titles"]:
            value["must_know_titles"].pop()
        elif value["theme"]:
            value["theme"] = str(value["theme"])[: max(0, len(str(value["theme"])) // 2)] or None
        else:
            # Fixed provenance alone is comfortably below the bound.
            return json.dumps({
                "untrusted_discovery_context": True,
                "origin": "marketing_node_daily_brief_more_reads",
                "node_snapshot_run_id": run_id,
                "daily_brief_date": selected_date,
            }, separators=(",", ":"))


def _parse(payload: object, expected_date: str) -> tuple[dict, dict, dict, list[dict]]:
    if not isinstance(payload, dict):
        raise InvalidNodeEnvelope("response must be an object")
    run = payload.get("run")
    if not isinstance(run, dict):
        raise InvalidNodeEnvelope("run metadata missing")
    run_id = run.get("run_id")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
        raise InvalidNodeEnvelope("invalid run id")
    if run.get("selected_date") != expected_date:
        raise InvalidNodeEnvelope("selected date mismatch")
    status = run.get("status")
    if status not in ACCEPTED_STATUSES:
        raise InvalidNodeEnvelope("run status is not consumable")
    context = _bounded_context(payload.get("context"), run, expected_date)
    diagnostics = _diagnostics(payload.get("diagnostics"))
    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 12:
        raise InvalidNodeEnvelope("candidate list outside contract")
    if diagnostics["candidates_returned"] != len(candidates):
        raise InvalidNodeEnvelope("candidate diagnostic mismatch")

    items = []
    rejected = 0
    for position, raw in enumerate(candidates, 1):
        try:
            if not isinstance(raw, dict):
                raise ValueError("candidate is not an object")
            if raw.get("order") != position:
                raise ValueError("candidate order mismatch")
            if raw.get("origin") != "daily_brief_more_reads":
                raise ValueError("candidate origin mismatch")
            title = _short_text(raw.get("title"), 240, required=True)
            publisher = _short_text(raw.get("publisher"), 120, required=True)
            url = raw.get("url")
            if not isinstance(url, str) or not url.strip() or len(url) > 2000:
                raise ValueError("invalid URL")
            sources._assert_public_http_url(url)
            discovery_key = store.canonical_discovery_key(url)
            source_id = raw.get("source_id")
            if source_id is not None and not isinstance(source_id, str):
                raise ValueError("invalid source id")
            normalized_source_id = " ".join(str(source_id or "").split()) or None
            if normalized_source_id and len(normalized_source_id) > 120:
                normalized_source_id = None
            supplied_id = raw.get("candidate_id")
            expected_id = _candidate_id(run_id, normalized_source_id, discovery_key)
            if supplied_id != expected_id:
                raise ValueError("candidate id mismatch")
            items.append({
                "source": publisher,
                "title": title,
                "url": url.strip(),
                "published": str(raw.get("published_at") or raw.get("observed_at") or "")[:100],
                "summary": "",
                "discovery_origin": "marketing_node",
                "discovery_candidate_id": expected_id,
                "discovery_context": _candidate_context_json(context, run_id, expected_date),
            })
        except (ValueError, sources.UnsafeSourceURL) as exc:
            rejected += 1
            log.warning("Node candidate rejected: %s", exc)
    diagnostics["nbn_rejected"] = rejected
    return {"run_id": run_id, "status": status}, context, diagnostics, items


def ingest(con, *, now: float | None = None, client: httpx.Client | None = None) -> dict:
    """Poll at most once per five minutes and atomically consume a valid UTC-day run."""
    if not config.NODE_READ_TOKEN:
        return {"attempted": False, "reason": "disabled", "inserted": 0}
    current = time.time() if now is None else now
    try:
        last_attempt = float(store.kv_get(con, "node:last_attempt") or 0)
    except ValueError:
        last_attempt = 0
    if current - last_attempt < THROTTLE_SECONDS:
        return {"attempted": False, "reason": "throttled", "inserted": 0}
    # Commit the throttle before any network request so restarts cannot hammer Node.
    store.kv_set(con, "node:last_attempt", str(current))
    selected_date = datetime.datetime.fromtimestamp(current, datetime.timezone.utc).date().isoformat()
    url = (config.NODE_BASE_URL.rstrip("/")
           + f"/api/daily-intel/wire-candidates/by-date/{selected_date}")
    owned = client is None
    http = client or httpx.Client(timeout=20)
    try:
        response = http.get(url, headers={"Authorization": f"Bearer {config.NODE_READ_TOKEN}"})
        response.raise_for_status()
        run, context, diagnostics, items = _parse(response.json(), selected_date)
        saved = store.ingest_node_discovery_run(
            con, run_id=run["run_id"], selected_date=selected_date, status=run["status"],
            context=context, diagnostics=diagnostics, items=items,
        )
        store.kv_set(con, "node:last_success", str(time.time()))
        store.kv_set(con, "node:last_error", "")
        return {"attempted": True, "run_id": run["run_id"], **saved}
    except (httpx.HTTPError, ValueError, InvalidNodeEnvelope, json.JSONDecodeError) as exc:
        message = f"{type(exc).__name__}: {exc}"[:300]
        store.kv_set(con, "node:last_error", message)
        log.warning("Marketing Node discovery unavailable: %s", message)
        return {"attempted": True, "error": message, "inserted": 0}
    finally:
        if owned:
            http.close()
