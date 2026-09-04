"""Curated discovery leads from the Marketing Node.

The Node payload is deliberately discovery-only: its prose may help triage decide
whether to investigate a link, but it is never evidence for drafting or verification.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
import re
import time

import httpx

from . import config, sources, store, theme_context

log = logging.getLogger("nbn.node_discovery")

THROTTLE_SECONDS = 300
ACCEPTED_STATUSES = {"accepted", "partial"}
V2_SCHEMA = "wire-pulse-v2"
V2_EVENT_KEY_VERSION = "wire-event-v1"


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


def _ref_id(discovery_key: str) -> str:
    return hashlib.sha256(f"wire-ref-v1\n{discovery_key}".encode()).hexdigest()[:24]


def _v2_candidate_id(run_id: int, event_version: str, ref_id: str,
                     discovery_key: str) -> str:
    material = f"{V2_SCHEMA}\n{run_id}\n{event_version}\n{ref_id}\n{discovery_key}"
    return hashlib.sha256(material.encode()).hexdigest()[:32]


def _iso_datetime(value, field: str) -> datetime.datetime:
    if not isinstance(value, str) or not value.strip():
        raise InvalidNodeEnvelope(f"{field} missing")
    try:
        parsed = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidNodeEnvelope(f"{field} invalid") from exc
    if parsed.tzinfo is None:
        raise InvalidNodeEnvelope(f"{field} lacks timezone")
    return parsed.astimezone(datetime.timezone.utc)


def _bounded_list(value, limit: int, item_limit: int, field: str) -> list[str]:
    if not isinstance(value, list) or len(value) > limit:
        raise InvalidNodeEnvelope(f"{field} outside contract")
    return [_short_text(item, item_limit, required=True) for item in value]


_ANCHOR_STOP = {
    "bitcoin", "btc", "crypto", "news", "latest", "update", "report", "reports",
    "the", "and", "for", "with", "from", "into", "after", "amid", "says",
}
_ACTION_WORDS = {
    "buy", "buys", "bought", "purchase", "purchases", "file", "files", "filed",
    "launch", "launches", "launched", "approve", "approves", "approved", "reject",
    "rejects", "rejected", "appoint", "appoints", "appointed", "resign", "resigns",
    "resigned", "vote", "votes", "voted", "pass", "passes", "passed", "flow",
    "flows", "inflow", "inflows", "outflow", "outflows", "release", "releases",
}
_ANCHOR_ALIASES = {
    "buy": "purchase", "buys": "purchase", "bought": "purchase",
    "purchases": "purchase", "purchased": "purchase",
    "files": "file", "filed": "file",
    "launches": "launch", "launched": "launch",
    "approves": "approve", "approved": "approve",
    "rejects": "reject", "rejected": "reject",
    "appoints": "appoint", "appointed": "appoint",
    "resigns": "resign", "resigned": "resign",
    "votes": "vote", "voted": "vote", "passes": "pass", "passed": "pass",
    "inflows": "flow", "outflows": "flow", "flows": "flow",
    "releases": "release",
}
_DIRECTION_ALIASES = {
    "inflow": "in", "inflows": "in", "outflow": "out", "outflows": "out",
    "rise": "up", "rises": "up", "rose": "up", "rising": "up", "higher": "up",
    "increase": "up", "increases": "up", "increased": "up",
    "fall": "down", "falls": "down", "fell": "down", "falling": "down",
    "lower": "down", "decrease": "down", "decreases": "down",
    "decreased": "down", "drop": "down", "drops": "down", "dropped": "down",
}
_MONTH_WORDS = {
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december",
}


def _anchor_tokens(value: str) -> set[str]:
    return {
        _ANCHOR_ALIASES.get(token, token)
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", str(value or "").lower())
        if token not in _ANCHOR_STOP and not token.isdigit()
    }


def _primary_anchors_align(primary: dict, headline: str, event_key: str) -> bool:
    title_tokens = _anchor_tokens(primary.get("title", ""))
    headline_tokens = _anchor_tokens(headline)
    if not title_tokens or not headline_tokens:
        return False
    shared = title_tokens & headline_tokens
    if " ".join(str(primary.get("title") or "").lower().split()) != \
            " ".join(str(headline or "").lower().split()) and len(shared) < 2:
        return False
    key_tokens = _anchor_tokens(str(event_key or "").replace(":", " ").replace("-", " "))
    return event_key.startswith(("artifact:", "period:")) or len(title_tokens & key_tokens) >= 1


def _ref_date(ref: dict) -> str:
    return str(ref.get("published_at") or ref.get("observed_at") or "")[:10]


def _related_ref_aligns(primary: dict, related: dict) -> bool:
    if store.canonical_discovery_key(primary.get("url", "")) == \
            store.canonical_discovery_key(related.get("url", "")):
        return True
    left_title = str(primary.get("title") or "")
    right_title = str(related.get("title") or "")
    left = _anchor_tokens(left_title)
    right = _anchor_tokens(right_title)
    shared_specific = _specific_title_entities(left_title) & _specific_title_entities(right_title)
    shared_action = (left & right) & _ACTION_WORDS
    if not shared_specific or not shared_action:
        return False
    left_directions = _direction_tokens(left_title)
    right_directions = _direction_tokens(right_title)
    if (left_directions or right_directions) and (
        len(left_directions) != 1
        or len(right_directions) != 1
        or left_directions != right_directions
    ):
        return False
    left_date, right_date = _ref_date(primary), _ref_date(related)
    if not left_date or left_date != right_date:
        return False
    return _typed_ref_numbers_compatible(
        left_title, right_title
    )


def _specific_title_entities(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"\b(?:[A-Z][A-Za-z0-9&.-]{2,}|[A-Z]{2,})\b", value)
        if token.lower() not in _ANCHOR_STOP
        and token.lower() not in _ACTION_WORDS
        and token.lower() not in _MONTH_WORDS
        and not any(character.isdigit() for character in token)
    }


def _direction_tokens(value: str) -> set[str]:
    return {
        direction for token in re.findall(r"[a-z]+", value.lower())
        if (direction := _DIRECTION_ALIASES.get(token))
    }


def _typed_ref_numbers_compatible(left: str, right: str) -> bool:
    pattern = (
        r"(\$\s*)?(\d+(?:\.\d+)?)\s*"
        r"(%|percent|bp|bps|bitcoin|btc|million|billion)"
    )
    unit_aliases = {"%": "percent", "btc": "bitcoin", "bps": "bp"}

    def normalize(value: str) -> set[tuple[str, float, bool]]:
        return {
            (unit_aliases.get(unit.lower(), unit.lower()), float(number), bool(dollars))
            for dollars, number, unit in re.findall(pattern, value.replace(",", ""), re.I)
        }

    left_values, right_values = normalize(left), normalize(right)
    if not left_values and not right_values:
        return True
    return bool(left_values and left_values == right_values)


def _minimal_v2_context_json(run: dict, refs: list[dict] | None, reason: str,
                             provenance: dict | None = None) -> str:
    value = {
        "untrusted_discovery_context": True,
        "origin": "marketing_node_wire_pulse_v2",
        "schema_version": V2_SCHEMA,
        "node_pulse_run_id": run["run_id"],
        "generated_at": run["generated_at"],
        "completed_at": run["completed_at"],
        "context_downgrade": reason,
        "theme_ids": [],
        "theme_signal_version": None,
        "theme_signals": [],
    }
    if refs is not None:
        value["source_refs"] = refs
    elif provenance:
        value["candidate_provenance"] = {
            "primary_ref_id": str(provenance.get("ref_id") or "")[:24],
            "publisher": str(provenance.get("publisher") or "")[:120],
        }
    while True:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode()) <= 8192:
            return encoded
        if len(value.get("source_refs") or []) > 1:
            value["source_refs"].pop()
        else:
            raise InvalidNodeEnvelope("minimal pulse context exceeds bound")


def _v2_context_json(raw: dict, run: dict, refs: list[dict]) -> str:
    value = {
        "untrusted_discovery_context": True,
        "origin": "marketing_node_wire_pulse_v2",
        "schema_version": V2_SCHEMA,
        "node_pulse_run_id": run["run_id"],
        "generated_at": run["generated_at"],
        "completed_at": run["completed_at"],
        "event_key_hint": raw["event_key_hint"],
        "event_key_version": raw["event_key_version"],
        "event_date": raw.get("event_date"),
        "disclosure_date": raw.get("disclosure_date"),
        "reporting_period": raw.get("reporting_period"),
        "cluster_headline": raw["cluster_headline"],
        "cluster_summary": raw.get("cluster_summary"),
        "why_surfaced": raw["why_surfaced"],
        "bitcoin_relevance": raw["bitcoin_relevance"],
        "relevance_reasons": list(raw["relevance_reasons"]),
        "theme_ids": list(raw["theme_ids"]),
        "theme_signal_version": raw.get("theme_signal_version"),
        "theme_signals": list(raw.get("theme_signals") or []),
        "novelty_hint": raw["novelty_hint"],
        "confidence_hint": raw["confidence_hint"],
        "source_refs": list(refs),
    }
    optional_text = ["cluster_summary", "why_surfaced", "cluster_headline"]
    while True:
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) <= 8192:
            return encoded
        if len(value["source_refs"]) > 1:
            value["source_refs"].pop()
        elif value["relevance_reasons"]:
            value["relevance_reasons"].pop()
        elif value["theme_ids"]:
            value["theme_ids"].pop()
            if value["theme_signals"]:
                value["theme_signals"].pop()
            if not value["theme_signals"]:
                value["theme_signal_version"] = None
        elif optional_text:
            key = optional_text.pop(0)
            value[key] = None
        else:
            raise InvalidNodeEnvelope("primary pulse context exceeds bound")


def _parse_v2(payload: object, *, now: float) -> tuple[dict, dict, dict, list[dict]]:
    if not isinstance(payload, dict) or payload.get("schema_version") != V2_SCHEMA:
        raise InvalidNodeEnvelope("v2 schema version mismatch")
    run_raw = payload.get("run")
    if not isinstance(run_raw, dict):
        raise InvalidNodeEnvelope("v2 run metadata missing")
    run_id = run_raw.get("run_id")
    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
        raise InvalidNodeEnvelope("v2 run id invalid")
    status = run_raw.get("status")
    if status not in ACCEPTED_STATUSES:
        raise InvalidNodeEnvelope("v2 run status is not consumable")
    generated = _iso_datetime(run_raw.get("generated_at"), "generated_at")
    completed = _iso_datetime(run_raw.get("completed_at"), "completed_at")
    age = now - generated.timestamp()
    if age < -300 or age > config.NODE_PULSE_MAX_AGE_SECONDS:
        raise InvalidNodeEnvelope("v2 pulse is stale")

    provider_rows = payload.get("provider_diagnostics")
    if not isinstance(provider_rows, list) or len(provider_rows) > 3:
        raise InvalidNodeEnvelope("v2 provider diagnostics outside contract")
    providers = []
    provider_names = set()
    for row in provider_rows:
        if not isinstance(row, dict) or row.get("provider") not in {"perception", "rss", "twitter"}:
            raise InvalidNodeEnvelope("v2 provider diagnostic invalid")
        if row["provider"] in provider_names:
            raise InvalidNodeEnvelope("v2 provider diagnostic duplicated")
        provider_names.add(row["provider"])
        if not isinstance(row.get("attempted"), bool) or not isinstance(row.get("success"), bool):
            raise InvalidNodeEnvelope("v2 provider state invalid")
        item_count, error_count = row.get("item_count"), row.get("error_count")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
               for value in (item_count, error_count)):
            raise InvalidNodeEnvelope("v2 provider counts invalid")
        providers.append({
            "provider": row["provider"], "attempted": row["attempted"],
            "success": row["success"], "item_count": item_count,
            "error_count": error_count,
        })
    if provider_names != {"perception", "rss", "twitter"}:
        raise InvalidNodeEnvelope("v2 provider diagnostics incomplete")

    node_theme_diagnostics = _parse_theme_diagnostics(payload.get("theme_diagnostics"))
    node_theme_match_diagnostics = _parse_theme_match_diagnostics(
        payload.get("theme_match_diagnostics_v1")
    )
    node_alignment_diagnostics = _parse_alignment_diagnostics(
        payload.get("alignment_diagnostics")
    )

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or len(candidates) > 24:
        raise InvalidNodeEnvelope("v2 candidate list outside contract")
    items, all_key_hashes, primary_key_hashes = [], set(), set()
    timestamp_counts = {"parseable": 0, "unknown": 0, "unparseable": 0}
    rejected = theme_rejected = theme_signals_parsed = 0
    primary_downgrades = context_downgrades = related_refs_dropped = 0
    rejected_candidate_keys, dropped_candidate_keys = [], []
    for position, raw in enumerate(candidates, 1):
        try:
            if not isinstance(raw, dict) or raw.get("order") != position:
                raise ValueError("v2 candidate order invalid")
            refs_raw = raw.get("source_refs")
            if not isinstance(refs_raw, list) or not 1 <= len(refs_raw) <= 6:
                raise ValueError("v2 source refs outside contract")
            refs, keys = [], []
            for rank, ref_raw in enumerate(refs_raw, 1):
                if not isinstance(ref_raw, dict) or ref_raw.get("rank") != rank:
                    raise ValueError("v2 source ref rank invalid")
                url = ref_raw.get("url")
                if not isinstance(url, str) or not url.strip() or len(url) > 2000:
                    raise ValueError("v2 source ref URL invalid")
                sources._assert_public_http_url(url)
                key = store.canonical_discovery_key(url)
                expected_ref_id = _ref_id(key)
                if ref_raw.get("ref_id") != expected_ref_id or expected_ref_id in {
                    ref["ref_id"] for ref in refs
                }:
                    raise ValueError("v2 source ref identity invalid")
                source_id = ref_raw.get("source_id")
                if source_id is not None and (
                    not isinstance(source_id, str) or len(" ".join(source_id.split())) > 120
                ):
                    raise ValueError("v2 source id invalid")
                timestamp_value = ref_raw.get("published_at") or ref_raw.get("observed_at")
                if timestamp_value:
                    try:
                        _iso_datetime(timestamp_value, "source_ref timestamp")
                    except InvalidNodeEnvelope as exc:
                        timestamp_counts["unparseable"] += 1
                        raise ValueError("v2 source ref timestamp invalid") from exc
                    timestamp_counts["parseable"] += 1
                else:
                    timestamp_counts["unknown"] += 1
                ref = {
                    "ref_id": expected_ref_id,
                    "rank": rank,
                    "source_id": " ".join(source_id.split()) if source_id else None,
                    "publisher": _short_text(ref_raw.get("publisher"), 120, required=True),
                    "title": _short_text(ref_raw.get("title"), 240, required=True),
                    "url": url.strip(),
                    "published_at": str(ref_raw.get("published_at") or "")[:100] or None,
                    "observed_at": str(ref_raw.get("observed_at") or "")[:100] or None,
                }
                refs.append(ref)
                keys.append(key)
            primary = refs[0]
            if raw.get("primary_ref_id") != primary["ref_id"]:
                raise ValueError("v2 primary ref mismatch")
            event_version = raw.get("event_key_version")
            if event_version != V2_EVENT_KEY_VERSION:
                raise ValueError("v2 event key version invalid")
            expected_id = _v2_candidate_id(
                run_id, event_version, primary["ref_id"], keys[0]
            )
            if raw.get("candidate_id") != expected_id:
                raise ValueError("v2 candidate id mismatch")
            cluster_headline = _short_text(raw.get("cluster_headline"), 240, required=True)
            cluster_summary = _short_text(raw.get("cluster_summary"), 1200) or None
            why = _short_text(raw.get("why_surfaced"), 500, required=True)
            event_key = _short_text(raw.get("event_key_hint"), 180, required=True)
            reasons = _bounded_list(raw.get("relevance_reasons", []), 6, 240,
                                    "relevance_reasons")
            packet = theme_context.validate_packet(raw)
            themes = packet["theme_ids"]
            theme_signals_parsed += len(packet["theme_signals"])
            relevance = raw.get("bitcoin_relevance")
            if isinstance(relevance, bool) or not isinstance(relevance, int | float) \
                    or not 0 <= relevance <= 1:
                raise ValueError("v2 relevance invalid")
            novelty = raw.get("novelty_hint")
            confidence = raw.get("confidence_hint")
            if novelty not in {"new", "developing", "unknown"} \
                    or confidence not in {"low", "medium", "high"}:
                raise ValueError("v2 hint enums invalid")
            normalized_raw = {
                **raw,
                "cluster_headline": cluster_headline,
                "cluster_summary": cluster_summary,
                "why_surfaced": why,
                "event_key_hint": event_key,
                "relevance_reasons": reasons,
                "theme_ids": themes,
                "theme_signal_version": packet["theme_signal_version"],
                "theme_signals": packet["theme_signals"],
                "bitcoin_relevance": float(relevance),
                "novelty_hint": novelty,
                "confidence_hint": confidence,
            }
            run_context = {
                "run_id": run_id,
                "generated_at": generated.isoformat(),
                "completed_at": completed.isoformat(),
            }
            primary_ok = _primary_anchors_align(primary, cluster_headline, event_key)
            if not primary_ok:
                primary_downgrades += 1
                accepted_refs = [dict(primary)]
                context_json = _minimal_v2_context_json(
                    run_context, None, "primary_alignment", primary
                )
                dropped_candidate_keys.append(expected_id)
            else:
                accepted_refs = [dict(primary)]
                for ref in refs[1:]:
                    if _related_ref_aligns(primary, ref):
                        accepted_refs.append(dict(ref))
                    else:
                        related_refs_dropped += 1
                for rank, ref in enumerate(accepted_refs, 1):
                    ref["rank"] = rank
                if len(accepted_refs) != len(refs):
                    context_downgrades += 1
                    dropped_candidate_keys.append(expected_id)
                    context_json = _minimal_v2_context_json(
                        run_context, accepted_refs, "related_ref_alignment"
                    )
                else:
                    context_json = _v2_context_json(normalized_raw, run_context, accepted_refs)
            items.append({
                "source": primary["publisher"],
                "title": primary["title"],
                "url": primary["url"],
                "published": primary["published_at"] or primary["observed_at"] or "",
                "summary": "",
                "discovery_origin": "marketing_node",
                "discovery_candidate_id": expected_id,
                "discovery_context": context_json,
            })
            all_key_hashes.update(
                store.url_hash(store.canonical_discovery_key(ref["url"]))
                for ref in accepted_refs
            )
            primary_key_hashes.add(store.url_hash(keys[0]))
        except theme_context.InvalidThemePacket:
            rejected += 1
            theme_rejected += 1
            rejected_candidate_keys.append(f"{run_id}:{position}")
            log.warning("Node v2 candidate rejected: invalid theme packet")
        except (ValueError, InvalidNodeEnvelope, sources.UnsafeSourceURL) as exc:
            rejected += 1
            rejected_candidate_keys.append(f"{run_id}:{position}")
            log.warning("Node v2 candidate rejected: %s", exc)

    selected_date = generated.date().isoformat()
    context = {
        "schema_version": V2_SCHEMA,
        "generated_at": generated.isoformat(),
        "completed_at": completed.isoformat(),
        "provider_diagnostics": providers,
        "theme_diagnostics": node_theme_diagnostics,
        "theme_match_diagnostics_v1": node_theme_match_diagnostics,
        "alignment_diagnostics": node_alignment_diagnostics,
    }
    diagnostics = {
        "candidates_returned": len(candidates),
        "nbn_rejected": rejected,
        "theme_candidates_rejected": theme_rejected,
        "theme_signals_parsed": theme_signals_parsed,
        "validated_candidates": len(items),
        "primary_context_downgrades": primary_downgrades,
        "related_context_downgrades": context_downgrades,
        "related_refs_dropped": related_refs_dropped,
        "node_clusters_repaired": node_alignment_diagnostics["clusters_repaired"],
        "node_related_refs_dropped": node_alignment_diagnostics["related_refs_dropped"],
        "theme_match_diagnostics_rejected": int(
            node_theme_match_diagnostics.get("present", False)
            and not node_theme_match_diagnostics.get("valid", False)
        ),
        "theme_match_producer_no_match": int(
            node_theme_match_diagnostics.get("valid", False)
            and node_theme_match_diagnostics.get("candidates_checked", 0) > 0
            and node_theme_match_diagnostics.get("unmatched_candidates", 0)
            == node_theme_match_diagnostics.get("candidates_checked", 0)
        ),
        "rejected_candidate_keys": rejected_candidate_keys[:24],
        "dropped_candidate_keys": list(dict.fromkeys(dropped_candidate_keys))[:24],
    }
    return ({
        "run_id": run_id, "status": status, "selected_date": selected_date,
        "generated_at": generated.isoformat(), "completed_at": completed.isoformat(),
        "all_key_hashes": sorted(all_key_hashes),
        "primary_key_hashes": sorted(primary_key_hashes),
        "timestamp_counts": timestamp_counts,
    }, context, diagnostics, items)


def _parse_theme_diagnostics(value) -> dict:
    keys = {
        "active_themes": 150,
        "classifier_matches": 500,
        "keyword_matches": 500,
        "matched_candidates": 500,
        "qualified_before_cap": 500,
        "eligible_tiebreak_candidates": 500,
        "rank_moves": 500,
        "cap_displacements": 24,
    }
    if value is None:
        return {key: 0 for key in keys}
    if not isinstance(value, dict) or set(value) != set(keys):
        raise InvalidNodeEnvelope("theme diagnostics invalid")
    parsed = {}
    for key, limit in keys.items():
        raw = value.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= limit:
            raise InvalidNodeEnvelope("theme diagnostics invalid")
        parsed[key] = raw
    return parsed


def _parse_theme_match_diagnostics(value) -> dict:
    keys = {
        "candidates_checked": 500,
        "classifier_identity_candidates": 500,
        "classifier_above_threshold_candidates": 500,
        "taxonomy_match_candidates": 500,
        "unmatched_candidates": 500,
    }
    if value is None:
        return {"present": False, "valid": False}
    if not isinstance(value, dict) or value.get("version") != "theme-match-diagnostics-v1" \
            or set(value) != {"version", *keys}:
        return {"present": True, "valid": False}
    parsed = {"present": True, "valid": True, "version": value["version"]}
    for key, limit in keys.items():
        raw = value.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= limit:
            return {"present": True, "valid": False}
        parsed[key] = raw
    return parsed


def _parse_alignment_diagnostics(value) -> dict:
    keys = {"clusters_repaired": 500, "related_refs_dropped": 3000}
    if value is None:
        return {key: 0 for key in keys}
    if not isinstance(value, dict) or set(value) != set(keys):
        raise InvalidNodeEnvelope("alignment diagnostics invalid")
    parsed = {}
    for key, limit in keys.items():
        raw = value.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int) or not 0 <= raw <= limit:
            raise InvalidNodeEnvelope("alignment diagnostics invalid")
        parsed[key] = raw
    return parsed


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


def _cache_v2_state(con, run: dict, context: dict, candidate_count: int) -> None:
    value = {
        "schema_version": V2_SCHEMA,
        "run_id": run["run_id"],
        "status": run["status"],
        "generated_at": run["generated_at"],
        "completed_at": run["completed_at"],
        "all_key_hashes": run["all_key_hashes"][:144],
        "primary_key_hashes": run["primary_key_hashes"][:24],
        "candidate_count": candidate_count,
        "provider_diagnostics": context["provider_diagnostics"],
        "theme_diagnostics": context.get("theme_diagnostics", {}),
        "timestamp_counts": run["timestamp_counts"],
    }
    store.kv_set(con, "node:latest_pulse", json.dumps(value, separators=(",", ":")))
    store.kv_set(con, "node:last_pulse_generated", run["generated_at"])
    store.kv_set(con, "node:last_pulse_run_id", str(run["run_id"]))
    store.kv_set(con, "node:last_pulse_status", run["status"])
    store.kv_set(con, "node:last_pulse_candidates", str(candidate_count))
    store.kv_set(con, "node:last_pulse_providers", json.dumps(
        context["provider_diagnostics"], separators=(",", ":")))


def _ingest_v1(con, http: httpx.Client, *, selected_date: str) -> dict:
    url = (config.NODE_BASE_URL.rstrip("/")
           + f"/api/daily-intel/wire-candidates/by-date/{selected_date}")
    response = http.get(url, headers={"Authorization": f"Bearer {config.NODE_READ_TOKEN}"})
    response.raise_for_status()
    run, context, diagnostics, items = _parse(response.json(), selected_date)
    saved = store.ingest_node_discovery_run(
        con, run_id=run["run_id"], selected_date=selected_date, status=run["status"],
        context=context, diagnostics=diagnostics, items=items,
    )
    return {"attempted": True, "contract": "v1", "run_id": run["run_id"], **saved}


def ingest(con, *, now: float | None = None, client: httpx.Client | None = None) -> dict:
    """Poll v2 at most every five minutes; fall back to v1 only when v2 is unusable."""
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
    owned = client is None
    http = client or httpx.Client(timeout=20)
    try:
        v2_url = config.NODE_BASE_URL.rstrip("/") + "/api/daily-intel/wire-candidates/v2/latest"
        try:
            response = http.get(
                v2_url, headers={"Authorization": f"Bearer {config.NODE_READ_TOKEN}"}
            )
            response.raise_for_status()
            run, context, diagnostics, items = _parse_v2(response.json(), now=current)
        except (httpx.HTTPError, ValueError, InvalidNodeEnvelope, json.JSONDecodeError) as exc:
            v2_error = f"{type(exc).__name__}: {exc}"[:300]
            store.kv_set(con, "node:last_v2_error", v2_error)
            result = _ingest_v1(con, http, selected_date=selected_date)
            store.kv_set(con, "node:last_success", str(time.time()))
            store.kv_set(con, "node:last_error", "")
            return {**result, "v2_error": v2_error}

        saved = store.ingest_node_discovery_run(
            con, run_id=run["run_id"], selected_date=run["selected_date"],
            status=run["status"], context=context, diagnostics=diagnostics, items=items,
        )
        _cache_v2_state(con, run, context, len(items))
        store.kv_set(con, "node:last_success", str(time.time()))
        store.kv_set(con, "node:last_error", "")
        store.kv_set(con, "node:last_v2_error", "")
        return {"attempted": True, "contract": "v2", "run_id": run["run_id"], **saved}
    except (httpx.HTTPError, ValueError, InvalidNodeEnvelope, json.JSONDecodeError) as exc:
        message = f"{type(exc).__name__}: {exc}"[:300]
        store.kv_set(con, "node:last_error", message)
        log.warning("Marketing Node discovery unavailable: %s", message)
        return {"attempted": True, "error": message, "inserted": 0}
    finally:
        if owned:
            http.close()
