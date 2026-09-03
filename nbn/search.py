"""Bounded model-free public web search for source discovery."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

import httpx

from . import config

_SEARCH_URL = "https://serpapi.com/search.json"


class SearchError(Exception):
    """A retryable SerpAPI transport or response failure."""

    def __init__(self, message: str, *, kind: str = "transport"):
        super().__init__(message)
        self.kind = kind


def google(query: str, *, max_results: int | None = None) -> list[dict]:
    """Return bounded Google organic results without model judgment.

    Results are discovery pointers only. Callers must independently validate the URL,
    fetch the page, and determine whether the page supports the story.
    """
    if not config.SERPAPI_KEY:
        return []
    normalized_query = " ".join(str(query or "").split()).strip()
    if not normalized_query:
        return []
    limit = max(1, min(int(max_results or config.SERPAPI_MAX_RESULTS), 8))
    params = {
        "engine": "google",
        "q": normalized_query[:400],
        "gl": "us",
        "hl": "en",
        "num": limit,
        "no_cache": "false",
        "api_key": config.SERPAPI_KEY,
    }
    # SerpAPI requires its credential in the query string. NBN's root logger enables
    # httpx INFO access logs, which otherwise record the full URL (and key). Suppress
    # only this synchronous request and restore the prior logger level immediately.
    httpx_log = logging.getLogger("httpx")
    prior_level = httpx_log.level
    httpx_log.setLevel(max(prior_level, logging.WARNING))
    try:
        try:
            response = httpx.get(
                _SEARCH_URL,
                params=params,
                timeout=config.SERPAPI_TIMEOUT_SECONDS,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            raise SearchError(
                f"serpapi transport error: {type(exc).__name__}", kind="transport"
            ) from exc
    finally:
        httpx_log.setLevel(prior_level)
    if not response.is_success:
        raise SearchError(
            f"serpapi HTTP {response.status_code}",
            kind="rate_limited" if response.status_code == 429 else "http",
        )
    try:
        body = response.json()
    except ValueError as exc:
        raise SearchError("serpapi returned invalid JSON", kind="invalid_response") from exc
    if not isinstance(body, dict) or body.get("error"):
        raise SearchError("serpapi returned an error response", kind="provider_error")
    metadata_status = (body.get("search_metadata") or {}).get("status")
    if metadata_status and metadata_status != "Success":
        raise SearchError("serpapi search did not complete", kind="provider_error")
    return _organic_results(body, limit)


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
        results.append(
            {
                "rank": int(raw.get("position") or len(results) + 1),
                "url": url,
                "outlet": publisher,
                "title": str(raw.get("title") or "").strip()[:300],
                "snippet": str(raw.get("snippet") or "").strip()[:1200],
            }
        )
        if len(results) >= limit:
            break
    return results
