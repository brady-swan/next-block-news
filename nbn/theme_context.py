"""Bounded parsing for Marketing Node theme context.

Every value handled here is untrusted discovery metadata. The module validates shape
and bounds only; it never turns a theme signal into evidence or an editorial decision.
"""
from __future__ import annotations

import datetime
import json
import re

THEME_SIGNAL_VERSION = "node-theme-signal-v1"
THEME_ID_RX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TRAJECTORIES = {"building", "peaked", "fading", "dormant"}
MATCH_BASES = {"node-classifier-v1", "taxonomy-keyword-v1"}
MAX_THEMES_PER_ITEM = 8
_SIGNAL_KEYS = {
    "theme_id", "name", "trajectory", "count_7d", "count_14d", "count_30d",
    "last_evidence_at", "match_basis", "confidence", "rank_eligible",
}


class InvalidThemePacket(ValueError):
    pass


def _text(value, limit: int, field: str) -> str:
    if not isinstance(value, str):
        raise InvalidThemePacket(f"{field} invalid")
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > limit:
        raise InvalidThemePacket(f"{field} outside bounds")
    return cleaned


def _count(value, limit: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= limit:
        raise InvalidThemePacket(f"{field} outside bounds")
    return value


def _timestamp(value) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 100:
        raise InvalidThemePacket("last_evidence_at invalid")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidThemePacket("last_evidence_at invalid") from exc
    if parsed.tzinfo is None:
        raise InvalidThemePacket("last_evidence_at lacks timezone")
    return parsed.astimezone(datetime.timezone.utc).isoformat()


def validate_packet(raw: dict) -> dict:
    """Validate optional theme fields from one wire-pulse candidate."""
    ids_raw = raw.get("theme_ids", [])
    if not isinstance(ids_raw, list) or len(ids_raw) > MAX_THEMES_PER_ITEM:
        raise InvalidThemePacket("theme_ids outside bounds")
    theme_ids = []
    for value in ids_raw:
        theme_id = _text(value, 120, "theme_id")
        if not THEME_ID_RX.fullmatch(theme_id) or theme_id in theme_ids:
            raise InvalidThemePacket("theme_id invalid or duplicated")
        theme_ids.append(theme_id)

    signals_raw = raw.get("theme_signals", [])
    version = raw.get("theme_signal_version")
    if not isinstance(signals_raw, list) or len(signals_raw) > MAX_THEMES_PER_ITEM:
        raise InvalidThemePacket("theme_signals outside bounds")
    if not signals_raw:
        if version is not None:
            raise InvalidThemePacket("theme signal version without signals")
        return {"theme_ids": theme_ids, "theme_signal_version": None, "theme_signals": []}
    if version != THEME_SIGNAL_VERSION:
        raise InvalidThemePacket("theme signal version mismatch")

    signals = []
    for row in signals_raw:
        if not isinstance(row, dict) or set(row) != _SIGNAL_KEYS:
            raise InvalidThemePacket("theme signal shape invalid")
        theme_id = _text(row.get("theme_id"), 120, "theme_id")
        if not THEME_ID_RX.fullmatch(theme_id):
            raise InvalidThemePacket("theme_id invalid")
        trajectory = row.get("trajectory")
        basis = row.get("match_basis")
        confidence = row.get("confidence")
        rank_eligible = row.get("rank_eligible")
        if trajectory not in TRAJECTORIES or basis not in MATCH_BASES:
            raise InvalidThemePacket("theme signal enum invalid")
        if (isinstance(confidence, bool) or not isinstance(confidence, int | float)
                or not 0 <= confidence <= 1):
            raise InvalidThemePacket("theme confidence outside bounds")
        if not isinstance(rank_eligible, bool):
            raise InvalidThemePacket("theme rank eligibility invalid")
        signals.append({
            "theme_id": theme_id,
            "name": _text(row.get("name"), 160, "theme name"),
            "trajectory": trajectory,
            "count_7d": _count(row.get("count_7d"), 10000, "count_7d"),
            "count_14d": _count(row.get("count_14d"), 20000, "count_14d"),
            "count_30d": _count(row.get("count_30d"), 50000, "count_30d"),
            "last_evidence_at": _timestamp(row.get("last_evidence_at")),
            "match_basis": basis,
            "confidence": round(float(confidence), 3),
            "rank_eligible": rank_eligible,
        })
    signal_ids = [row["theme_id"] for row in signals]
    if len(signal_ids) != len(set(signal_ids)) or signal_ids != theme_ids:
        raise InvalidThemePacket("theme signal ids do not match theme_ids")
    return {
        "theme_ids": theme_ids,
        "theme_signal_version": THEME_SIGNAL_VERSION,
        "theme_signals": signals,
    }


def parse_discovery_context(value) -> dict:
    """Return validated theme context from one persisted discovery envelope."""
    try:
        context = json.loads(value or "") if isinstance(value, str) else value
    except (TypeError, ValueError):
        return {"theme_ids": [], "theme_signal_version": None, "theme_signals": []}
    if (not isinstance(context, dict)
            or context.get("untrusted_discovery_context") is not True
            or context.get("schema_version") != "wire-pulse-v2"):
        return {"theme_ids": [], "theme_signal_version": None, "theme_signals": []}
    try:
        return validate_packet(context)
    except InvalidThemePacket:
        return {"theme_ids": [], "theme_signal_version": None, "theme_signals": []}


def signals_by_id(packet: dict) -> dict[str, dict]:
    return {
        row["theme_id"]: row
        for row in packet.get("theme_signals", []) if isinstance(row, dict)
    }
