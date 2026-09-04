"""Bounded model-free public web search for source discovery."""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
import time
import unicodedata
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit

import httpx

from . import config

_SEARCH_URL = "https://serpapi.com/search.json"
_ACCOUNT_URL = "https://serpapi.com/account.json"
_CACHE_KEY_VERSION = "serpapi-google-v1"
_MAX_RETRY_AFTER_SECONDS = 3600


class SearchError(Exception):
    """A typed retryable SerpAPI transport or response failure."""

    def __init__(self, message: str, *, kind: str = "transport",
                 retry_after_seconds: int = 0):
        super().__init__(str(message or "search failed")[:240])
        self.kind = str(kind or "transport")[:80]
        self.retry_after_seconds = max(
            0, min(int(retry_after_seconds or 0), _MAX_RETRY_AFTER_SECONDS)
        )


def normalize_query(query: str) -> str:
    """Normalize transport-insignificant text without changing search semantics."""
    value = unicodedata.normalize("NFKC", str(query or ""))
    return " ".join(value.split()).strip()[:400]


def request_identity(query: str, *, max_results: int | None = None,
                     engine: str = "google", gl: str = "us", hl: str = "en",
                     start: int = 0) -> dict[str, Any]:
    """Return the complete, versioned identity for one supported search request."""
    limit = max(1, min(int(max_results or config.SERPAPI_MAX_RESULTS), 8))
    identity = {
        "version": _CACHE_KEY_VERSION,
        "provider": "serpapi",
        "engine": str(engine or "google")[:40],
        "query": normalize_query(query),
        "gl": str(gl or "us")[:10].lower(),
        "hl": str(hl or "en")[:10].lower(),
        "limit": limit,
        "start": max(0, min(int(start or 0), 100)),
    }
    material = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    identity["cache_key"] = hashlib.sha256(material.encode()).hexdigest()
    return identity


def _retry_after_seconds(response: httpx.Response, *, now: float | None = None) -> int:
    raw = str(response.headers.get("retry-after") or "").strip()
    if not raw:
        return 0
    try:
        seconds = int(raw)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=datetime.timezone.utc)
            seconds = int(parsed.timestamp() - float(now if now is not None else time.time()))
        except (TypeError, ValueError, OverflowError):
            return 0
    return max(1, min(seconds, _MAX_RETRY_AFTER_SECONDS))


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _request(url: str, *, params: dict, timeout: float) -> httpx.Response:
    # SerpAPI requires its credential in the query string. Suppress httpx access logs
    # for this request so the key can never appear in the root logger.
    httpx_log = logging.getLogger("httpx")
    prior_level = httpx_log.level
    httpx_log.setLevel(max(prior_level, logging.WARNING))
    try:
        try:
            return httpx.get(
                url, params=params, timeout=timeout, follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            raise SearchError(
                f"serpapi transport error: {type(exc).__name__}", kind="transport"
            ) from exc
    finally:
        httpx_log.setLevel(prior_level)


def account_status() -> dict[str, Any]:
    """Return a scrubbed free SerpAPI account-capacity snapshot."""
    if not config.SERPAPI_KEY:
        return {"provider": "serpapi", "state": "unconfigured", "checked_at": time.time()}
    response = _request(
        _ACCOUNT_URL, params={"api_key": config.SERPAPI_KEY},
        timeout=min(max(1.0, config.SERPAPI_TIMEOUT_SECONDS), 15.0),
    )
    if not response.is_success:
        raise SearchError(
            f"serpapi account HTTP {response.status_code}",
            kind="rate_limited" if response.status_code == 429 else "account_http",
            retry_after_seconds=_retry_after_seconds(response),
        )
    body = _safe_json(response)
    if not body or body.get("error"):
        raise SearchError("serpapi account returned an error response", kind="account_response")

    def bounded_int(name: str) -> int | None:
        value = body.get(name)
        if value is None or isinstance(value, bool):
            return None
        try:
            return max(0, min(int(value), 1_000_000_000))
        except (TypeError, ValueError):
            return None

    remaining = bounded_int("total_searches_left")
    state = "unknown" if remaining is None else (
        "quota_exhausted" if remaining == 0 else "healthy"
    )
    return {
        "provider": "serpapi",
        "state": state,
        "plan_name": str(body.get("plan_name") or "")[:80],
        "plan_renewal_date": str(body.get("plan_renewal_date") or "")[:40],
        "searches_per_month": bounded_int("searches_per_month"),
        "this_month_usage": bounded_int("this_month_usage"),
        "total_searches_left": remaining,
        "this_hour_searches": bounded_int("this_hour_searches"),
        "last_hour_searches": bounded_int("last_hour_searches"),
        "account_rate_limit_per_hour": bounded_int("account_rate_limit_per_hour"),
        "checked_at": time.time(),
    }


def google(query: str, *, max_results: int | None = None) -> list[dict]:
    """Return bounded Google organic results without model judgment.

    Results are discovery pointers only. Callers must independently validate the URL,
    fetch the page, and determine whether the page supports the story.
    """
    if not config.SERPAPI_KEY:
        return []
    identity = request_identity(query, max_results=max_results)
    if not identity["query"]:
        return []
    params = {
        "engine": identity["engine"], "q": identity["query"],
        "gl": identity["gl"], "hl": identity["hl"],
        "num": identity["limit"], "start": identity["start"],
        "no_cache": "false", "api_key": config.SERPAPI_KEY,
    }
    response = _request(_SEARCH_URL, params=params, timeout=config.SERPAPI_TIMEOUT_SECONDS)
    if not response.is_success:
        body = _safe_json(response)
        provider_error = str(body.get("error") or "").lower()
        if response.status_code == 429:
            if "run out of searches" in provider_error or "no searches" in provider_error:
                kind = "quota_exhausted"
            elif any(marker in provider_error for marker in (
                    "rate limit", "too many requests", "per hour", "hourly")):
                kind = "rate_limited"
            else:
                kind = "provider_error"
        else:
            kind = "http"
        raise SearchError(
            f"serpapi HTTP {response.status_code}", kind=kind,
            retry_after_seconds=_retry_after_seconds(response),
        )
    body = _safe_json(response)
    if not body:
        raise SearchError("serpapi returned invalid JSON", kind="invalid_response")
    if body.get("error"):
        raise SearchError("serpapi returned an error response", kind="provider_error")
    metadata_status = (body.get("search_metadata") or {}).get("status")
    if metadata_status and metadata_status != "Success":
        raise SearchError("serpapi search did not complete", kind="provider_error")
    return _organic_results(body, identity["limit"])


def _organic_results(body: dict[str, Any], limit: int) -> list[dict]:
    results: list[dict] = []
    rows = body.get("organic_results") or []
    if not isinstance(rows, list):
        return results
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("link") or "").strip()
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        publisher = str(raw.get("source") or "").strip()
        if not publisher:
            publisher = parsed.hostname.lower().removeprefix("www.")
        try:
            rank = max(1, min(int(raw.get("position") or len(results) + 1), 100))
        except (TypeError, ValueError):
            rank = len(results) + 1
        results.append({
            "rank": rank,
            "url": url[:2000], "outlet": publisher[:160],
            "title": str(raw.get("title") or "").strip()[:300],
            "snippet": str(raw.get("snippet") or "").strip()[:1200],
        })
        if len(results) >= limit:
            break
    return results
