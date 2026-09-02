"""Bounded guide-account attention metadata; never evidence or source authority."""
from __future__ import annotations

import ipaddress
import json
import re
from urllib.parse import urlsplit

from . import theme_context

GUIDE_SIGNAL_VERSION = "guide-signal-v1"
GUIDE_HANDLES = {
    "bitcoinnewscom": "BitcoinNewsCom",
    "bitcoinarchive": "BitcoinArchive",
    "bitcoinmagazine": "BitcoinMagazine",
    "tftc21": "TFTC21",
    "simplybitcoin": "SimplyBitcoin",
}
MAX_CONTEXT_BYTES = 8192
_METRICS = ("characters", "likes", "reposts", "quotes")


def normalize_handle(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]", "", str(value or "").lstrip("@"))
    return GUIDE_HANDLES.get(token.lower(), "")


def handle_from_source(value: str) -> str:
    match = re.search(r"@([A-Za-z0-9_]{1,30})", str(value or ""))
    return normalize_handle(match.group(1) if match else "")


def _public_url(value: str) -> str:
    raw = str(value or "").strip()
    try:
        parts = urlsplit(raw)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return ""
        host = parts.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".local", ".localhost")):
            return ""
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address and not address.is_global:
            return ""
    except (TypeError, ValueError):
        return ""
    return raw[:2000]


def build_signal(handle: str, post_url: str, text: str, metrics=None,
                 outbound_urls=None) -> dict | None:
    canonical = normalize_handle(handle)
    public_post = _public_url(post_url)
    if not canonical or not public_post:
        return None
    metrics = metrics if isinstance(metrics, dict) else {}
    bounded_metrics = {}
    for key in _METRICS:
        raw = metrics.get(key, 0)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raw = 0
        bounded_metrics[key] = max(0, min(raw, 1_000_000_000))
    urls, seen = [], set()
    raw_outbounds = outbound_urls if isinstance(outbound_urls, list) else []
    for raw in raw_outbounds[:8]:
        url = _public_url(raw)
        if url and url not in seen and "x.com/" not in url and "twitter.com/" not in url:
            seen.add(url)
            urls.append(url)
        if len(urls) >= 4:
            break
    return {
        "version": GUIDE_SIGNAL_VERSION,
        "handle": canonical,
        "post_url": public_post,
        "text": str(text or "")[:600],
        "metrics": bounded_metrics,
        "outbound_urls": urls,
    }


def _parse(value) -> dict | None:
    try:
        parsed = json.loads(value or "") if isinstance(value, str) else value
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def signal_from_context(value) -> dict | None:
    context = _parse(value)
    if not context or context.get("untrusted_discovery_context") is not True:
        return None
    nested = context.get("guide_signal")
    if isinstance(nested, dict) and nested.get("version") == GUIDE_SIGNAL_VERSION:
        return build_signal(
            nested.get("handle", ""), nested.get("post_url", ""),
            nested.get("text", ""), nested.get("metrics"), nested.get("outbound_urls"),
        )
    if context.get("guide_account_signal") is True:
        handle = normalize_handle(context.get("guide_handle", ""))
        raw_metrics = context.get("guide_format_metrics")
        raw_metrics = raw_metrics if isinstance(raw_metrics, dict) else {}
        metrics = {
            key: max(0, min(int(raw_metrics.get(key, 0)), 1_000_000_000))
            for key in _METRICS
            if not isinstance(raw_metrics.get(key, 0), bool)
            and isinstance(raw_metrics.get(key, 0), int)
        }
        raw_outbounds = context.get("outbound_urls")
        raw_outbounds = raw_outbounds if isinstance(raw_outbounds, list) else []
        urls = [url for raw in raw_outbounds[:4]
                if (url := _public_url(raw))]
        return build_signal(
            handle, context.get("guide_post_url", ""),
            context.get("guide_post_text", ""), metrics, urls,
        )
    return None


def is_guide(source: str = "", context=None) -> bool:
    return bool(handle_from_source(source) or signal_from_context(context))


def _valid_node_context(context: dict) -> bool:
    if context.get("schema_version") != "wire-pulse-v2":
        return True
    refs = context.get("source_refs")
    if context.get("context_downgrade") == "primary_alignment" and refs is None:
        provenance = context.get("candidate_provenance")
        return (
            isinstance(provenance, dict)
            and isinstance(provenance.get("primary_ref_id"), str)
            and isinstance(provenance.get("publisher"), str)
        )
    if not isinstance(refs, list) or not 1 <= len(refs) <= 6:
        return False
    try:
        theme_context.validate_packet(context)
    except theme_context.InvalidThemePacket:
        return False
    return all(
        isinstance(row, dict)
        and row.get("rank") == index
        and isinstance(row.get("url"), str)
        and bool(_public_url(row.get("url")))
        for index, row in enumerate(refs, 1)
    )


def merge_context(existing_raw: str, incoming_raw: str) -> str:
    """Symmetrically merge Node provenance and guide attention below the 8 KiB bound."""
    existing = _parse(existing_raw)
    incoming = _parse(incoming_raw)
    node_raw, node = "", None
    for raw, parsed in ((existing_raw, existing), (incoming_raw, incoming)):
        if parsed and parsed.get("schema_version") == "wire-pulse-v2" \
                and _valid_node_context(parsed):
            node_raw, node = str(raw or ""), dict(parsed)
            break
    guide = signal_from_context(incoming) or signal_from_context(existing)
    if node is not None:
        base = node
        original = node_raw
    elif existing:
        base, original = dict(existing), str(existing_raw or "")
    elif incoming:
        base, original = dict(incoming), str(incoming_raw or "")
    else:
        return ""
    base["untrusted_discovery_context"] = True
    for legacy in (
        "guide_account_signal", "guide_handle", "guide_post_url", "guide_post_text",
        "guide_format_metrics", "outbound_urls",
    ):
        base.pop(legacy, None)
    if not guide:
        encoded = json.dumps(base, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode()) <= MAX_CONTEXT_BYTES and _valid_node_context(base):
            return encoded
        return original if len(original.encode()) <= MAX_CONTEXT_BYTES else ""

    candidate = dict(base)
    candidate["guide_signal"] = dict(guide)
    for drop in ("metrics", "outbound_urls", "text", "guide_signal"):
        encoded = json.dumps(candidate, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode()) <= MAX_CONTEXT_BYTES and _valid_node_context(candidate):
            return encoded
        if drop == "guide_signal":
            candidate.pop("guide_signal", None)
        else:
            candidate["guide_signal"].pop(drop, None)
    if node is not None:
        return original
    encoded = json.dumps(base, separators=(",", ":"), ensure_ascii=False)
    return encoded if len(encoded.encode()) <= MAX_CONTEXT_BYTES else ""
