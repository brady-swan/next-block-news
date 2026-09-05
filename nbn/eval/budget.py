"""Restart-safe pre-call reservation ledger for the evaluation hard cap."""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .core import EvaluationError, canonical_json

PRICE_VERSION = "nbn-eval-public-2026-09-05-v3"
DEFAULT_CAP_USD = 40.0

PRICES = {
    "claude-sonnet-5": {"input": 2.0, "output": 10.0, "cached": 0.20},
    "claude-opus-5": {"input": 5.0, "output": 25.0, "cached": 0.50},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0, "cached": 0.10},
    "gpt-5.4-mini-2026-03-17": {"input": 0.75, "output": 4.50, "cached": 0.075},
    "gpt-5.6-luna": {"input": 0.20, "output": 1.20, "cached": 0.02},
    "grok-4.3": {"input": 1.25, "output": 2.50, "cached": 0.20},
    "grok-4.5": {"input": 2.00, "output": 6.00, "cached": 0.30},
}

# SerpAPI is deliberately absent until an isolated evaluation plan and its exact marginal
# price are supplied. Treating a shared-plan lookup as free would under-reserve the experiment.
TOOL_PRICES = {"x_search": 0.005, "web_search": 0.005}


def price_manifest() -> dict:
    return {"version": PRICE_VERSION, "retrieved_date": "2026-09-05",
            "currency": "USD", "per_million_tokens": PRICES,
            "per_call_tools": TOOL_PRICES}


def _is_append_only_price_update(previous: dict, current: dict) -> bool:
    """Allow new priced models without rewriting rates used by settled requests."""
    if previous.get("currency") != current.get("currency"):
        return False
    for section in ("per_million_tokens", "per_call_tools"):
        old_values = previous.get(section)
        new_values = current.get(section)
        if not isinstance(old_values, dict) or not isinstance(new_values, dict):
            return False
        if any(new_values.get(key) != value for key, value in old_values.items()):
            return False
    return True


def conservative_reservation(*, model: str, input_bytes: int, max_output_tokens: int,
                             max_tool_calls: dict[str, int] | None = None,
                             retry_count: int = 0) -> float:
    if model not in PRICES:
        raise EvaluationError(f"unknown price for {model}")
    # Deliberately pessimistic: one token per two UTF-8 bytes and all input uncached.
    input_tokens = max(1, (int(input_bytes) + 1) // 2)
    rates = PRICES[model]
    token_cost = (input_tokens * rates["input"]
                  + max(1, int(max_output_tokens)) * rates["output"]) / 1_000_000
    tool_cost = 0.0
    for tool, count in (max_tool_calls or {}).items():
        if tool not in TOOL_PRICES:
            raise EvaluationError(f"unknown tool price for {tool}")
        tool_cost += max(0, int(count)) * TOOL_PRICES[tool]
    return round((token_cost + tool_cost) * (1 + max(0, int(retry_count))), 8)


@dataclass(frozen=True)
class Reservation:
    request_id: str
    reserved_usd: float


class BudgetLedger:
    def __init__(self, path: Path, *, cap_usd: float = DEFAULT_CAP_USD):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.con = sqlite3.connect(path)
        self.con.row_factory = sqlite3.Row
        self.con.executescript("""
          PRAGMA journal_mode=WAL;
          CREATE TABLE IF NOT EXISTS eval_meta(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS eval_requests(
            request_id TEXT PRIMARY KEY,
            lane TEXT NOT NULL,
            condition TEXT NOT NULL,
            case_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            reserved_usd REAL NOT NULL,
            actual_usd REAL,
            charged_usd REAL NOT NULL,
            status TEXT NOT NULL,
            provider_usage_json TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            settled_at REAL
          );
        """)
        manifest = price_manifest()
        existing = self.con.execute(
            "SELECT value FROM eval_meta WHERE key='price_manifest'"
        ).fetchone()
        if existing and existing["value"] != canonical_json(manifest):
            previous = json.loads(existing["value"])
            if not _is_append_only_price_update(previous, manifest):
                raise EvaluationError("price manifest changed for existing ledger")
            self.con.execute(
                "UPDATE eval_meta SET value=? WHERE key='price_manifest'",
                (canonical_json(manifest),),
            )
        self.con.execute(
            "INSERT OR IGNORE INTO eval_meta(key,value) VALUES('price_manifest',?)",
            (canonical_json(manifest),),
        )
        existing_cap = self.con.execute(
            "SELECT value FROM eval_meta WHERE key='cap_usd'"
        ).fetchone()
        if existing_cap and float(existing_cap["value"]) != float(cap_usd):
            raise EvaluationError("hard cap changed for existing ledger")
        self.con.execute(
            "INSERT OR IGNORE INTO eval_meta(key,value) VALUES('cap_usd',?)",
            (str(float(cap_usd)),),
        )
        self.con.commit()
        self.cap_usd = float(cap_usd)

    def close(self) -> None:
        self.con.close()

    def charged(self) -> float:
        row = self.con.execute(
            "SELECT COALESCE(SUM(charged_usd),0) total FROM eval_requests"
        ).fetchone()
        return float(row["total"])

    def remaining(self) -> float:
        return max(0.0, self.cap_usd - self.charged())

    def reserve(self, *, lane: str, condition: str, case_id: str, kind: str,
                amount_usd: float) -> Reservation:
        amount = round(float(amount_usd), 8)
        if amount <= 0:
            raise EvaluationError("reservation must be positive")
        request_id = uuid.uuid4().hex
        self.con.execute("BEGIN IMMEDIATE")
        try:
            total = float(self.con.execute(
                "SELECT COALESCE(SUM(charged_usd),0) total FROM eval_requests"
            ).fetchone()["total"])
            if total + amount > self.cap_usd + 1e-9:
                raise EvaluationError(
                    f"hard cost cap would be exceeded: {total + amount:.6f}>{self.cap_usd:.2f}"
                )
            self.con.execute(
                "INSERT INTO eval_requests(request_id,lane,condition,case_id,kind,"
                "reserved_usd,charged_usd,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (request_id, lane, condition, case_id, kind, amount, amount,
                 "reserved", time.time()),
            )
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise
        return Reservation(request_id, amount)

    def settle(self, request_id: str, *, actual_usd: float | None,
               provider_usage: dict) -> None:
        self.con.execute("BEGIN IMMEDIATE")
        try:
            row = self.con.execute(
                "SELECT status,reserved_usd FROM eval_requests WHERE request_id=?",
                (request_id,),
            ).fetchone()
            if not row:
                raise EvaluationError("unknown reservation")
            if row["status"] == "settled":
                raise EvaluationError("reservation already settled")
            reserved = float(row["reserved_usd"])
            if actual_usd is None:
                actual = None
                charged = reserved
            else:
                actual = max(0.0, float(actual_usd))
                # A reservation is intentionally conservative. Never hide an underestimate.
                charged = actual
                prior_other = float(self.con.execute(
                    "SELECT COALESCE(SUM(charged_usd),0) total FROM eval_requests"
                    " WHERE request_id<>?", (request_id,),
                ).fetchone()["total"])
                if prior_other + charged > self.cap_usd + 1e-9:
                    charged = max(actual, reserved)
            self.con.execute(
                "UPDATE eval_requests SET actual_usd=?,charged_usd=?,status='settled',"
                "provider_usage_json=?,settled_at=? WHERE request_id=?",
                (actual, charged, canonical_json(provider_usage), time.time(), request_id),
            )
            self.con.commit()
        except Exception:
            self.con.rollback()
            raise

    def fail(self, request_id: str, *, provider_usage: dict | None = None) -> None:
        # Unknown or failed calls retain their full reservation, including after restart.
        self.con.execute(
            "UPDATE eval_requests SET status='failed',provider_usage_json=?,settled_at=?"
            " WHERE request_id=? AND status='reserved'",
            (canonical_json(provider_usage or {}), time.time(), request_id),
        )
        self.con.commit()

    def summary(self) -> dict:
        rows = self.con.execute(
            "SELECT status,COUNT(*) calls,SUM(charged_usd) charged FROM eval_requests"
            " GROUP BY status ORDER BY status"
        ).fetchall()
        return {"cap_usd": self.cap_usd, "charged_usd": self.charged(),
                "remaining_usd": self.remaining(), "price_version": PRICE_VERSION,
                "statuses": [dict(row) for row in rows]}
