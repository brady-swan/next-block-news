"""Thin, evaluation-only provider adapters with explicit credential injection."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import anthropic
import httpx

from .budget import PRICES, TOOL_PRICES
from .core import EvaluationError, canonical_json

EVAL_KEY_ENV = {
    "anthropic": "NBN_EVAL_ANTHROPIC_API_KEY",
    "openai": "NBN_EVAL_OPENAI_API_KEY",
    "xai": "NBN_EVAL_XAI_API_KEY",
    "serpapi": "NBN_EVAL_SERPAPI_KEY",
}


@dataclass(frozen=True)
class Condition:
    name: str
    provider: str
    model: str
    effort: str | None
    native_tools: tuple[str, ...] = ()


CONDITIONS = {
    "sonnet-medium": Condition("sonnet-medium", "anthropic", "claude-sonnet-5", "medium"),
    "opus-medium": Condition("opus-medium", "anthropic", "claude-opus-5", "medium"),
    "haiku-pinned": Condition(
        "haiku-pinned", "anthropic", "claude-haiku-4-5-20251001", None
    ),
    "mini-low": Condition(
        "mini-low", "openai", "gpt-5.4-mini-2026-03-17", "low"
    ),
    "mini-medium": Condition(
        "mini-medium", "openai", "gpt-5.4-mini-2026-03-17", "medium"
    ),
    "luna-low": Condition("luna-low", "openai", "gpt-5.6-luna", "low"),
    "luna-medium": Condition("luna-medium", "openai", "gpt-5.6-luna", "medium"),
    "grok-low": Condition("grok-low", "xai", "grok-4.3", "low"),
    "grok-medium": Condition("grok-medium", "xai", "grok-4.3", "medium"),
    "grok45-low": Condition("grok45-low", "xai", "grok-4.5", "low"),
    "grok45-medium": Condition("grok45-medium", "xai", "grok-4.5", "medium"),
    "grok-medium-x-search": Condition(
        "grok-medium-x-search", "xai", "grok-4.3", "medium", ("x_search",)
    ),
}


def evaluation_key(environment: dict[str, str], provider: str) -> str | None:
    """Read only the evaluation namespace; never consult SDK or production key names."""
    name = EVAL_KEY_ENV.get(provider)
    if not name:
        return None
    return str(environment.get(name) or "") or None


def _text_from_responses(body: dict) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct:
        return direct
    chunks: list[str] = []
    for output in body.get("output") or []:
        if not isinstance(output, dict) or output.get("type") != "message":
            continue
        for content in output.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text":
                chunks.append(str(content.get("text") or ""))
    return "".join(chunks)


def _json_result(text: str) -> dict:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EvaluationError(f"invalid provider JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EvaluationError("provider output must be an object")
    return value


def _token_cost(model: str, usage: dict) -> float:
    rates = PRICES[model]
    input_tokens = int(usage.get("input_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or 0)
    output = int(usage.get("output_tokens") or 0)
    ordinary = max(0, input_tokens - cached)
    return ((ordinary * rates["input"] + cached * rates["cached"]
             + output * rates["output"]) / 1_000_000)


def _native_tool_usage(body: dict, usage_raw: dict) -> dict[str, int]:
    """Normalize provider counters and raw Responses tool-call entries."""
    counts: dict[str, int] = {}
    aliases = {
        "x_search": "x_search", "x_search_call": "x_search",
        "x_search_calls": "x_search", "x_keyword_search": "x_search",
        "x_semantic_search": "x_search", "web_search": "web_search",
        "web_search_call": "web_search", "web_search_calls": "web_search",
    }
    for reported in (
        usage_raw.get("server_side_tool_usage"),
        usage_raw.get("server_side_tool_usage_details"),
    ):
        if isinstance(reported, dict):
            for raw_name, raw_count in reported.items():
                name = str(raw_name).lower().replace("server_side_tool_", "")
                normalized = aliases.get(name)
                if normalized:
                    counts[normalized] = max(
                        counts.get(normalized, 0), int(raw_count or 0)
                    )
    observed: dict[str, int] = {}
    for item in body.get("output") or []:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "").lower()
        raw_name = item.get("name") if item_type == "custom_tool_call" else item_type
        normalized = aliases.get(str(raw_name or "").lower())
        if normalized:
            observed[normalized] = observed.get(normalized, 0) + 1
    for name, count in observed.items():
        counts[name] = max(counts.get(name, 0), count)
    return counts


@dataclass(frozen=True)
class ProviderResult:
    parsed: dict
    raw_response: dict
    usage: dict
    actual_cost_usd: float
    latency_ms: int
    returned_model: str
    stop_reason: str


class ProviderAdapter:
    def __init__(self, *, api_key: str, timeout_seconds: float = 120.0):
        if not api_key:
            raise EvaluationError("evaluation API key is required explicitly")
        self.api_key = api_key
        self.timeout_seconds = float(timeout_seconds)

    def invoke(self, *, condition: Condition, system: str, user_payload: dict,
               output_schema: dict, output_name: str,
               max_output_tokens: int) -> ProviderResult:
        raise NotImplementedError

    def wire_descriptor(self, *, condition: Condition, system: str, user_payload: dict,
                        output_schema: dict, output_name: str,
                        max_output_tokens: int) -> dict:
        raise NotImplementedError


class AnthropicAdapter(ProviderAdapter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Explicit key prevents Anthropic SDK environment discovery.
        self.client = anthropic.Anthropic(
            api_key=self.api_key, timeout=self.timeout_seconds, max_retries=0
        )

    def invoke(self, *, condition: Condition, system: str, user_payload: dict,
               output_schema: dict, output_name: str,
               max_output_tokens: int) -> ProviderResult:
        tool_name = "submit_evaluation_result"
        kwargs: dict[str, Any] = {
            "model": condition.model,
            "max_tokens": int(max_output_tokens),
            "system": system,
            "messages": [{"role": "user", "content": canonical_json(user_payload)}],
            "tools": [{"name": tool_name, "description": output_name,
                       "input_schema": output_schema}],
            "tool_choice": {"type": "tool", "name": tool_name},
        }
        if condition.effort:
            kwargs["output_config"] = {"effort": condition.effort}
        started = time.monotonic()
        response = self.client.messages.create(**kwargs)
        latency = int((time.monotonic() - started) * 1000)
        blocks = [block for block in response.content
                  if getattr(block, "type", "") == "tool_use"
                  and getattr(block, "name", "") == tool_name]
        if len(blocks) != 1 or not isinstance(getattr(blocks[0], "input", None), dict):
            raise EvaluationError("Anthropic response lacks the required result tool")
        raw = response.model_dump(mode="json")
        usage_obj = response.usage
        usage = {
            "input_tokens": int(getattr(usage_obj, "input_tokens", 0) or 0),
            "output_tokens": int(getattr(usage_obj, "output_tokens", 0) or 0),
            "cached_input_tokens": int(getattr(usage_obj, "cache_read_input_tokens", 0) or 0),
            "cache_creation_input_tokens": int(
                getattr(usage_obj, "cache_creation_input_tokens", 0) or 0
            ),
            "reasoning_tokens": 0,
            "native_tools": {},
        }
        local_cost = _token_cost(condition.model, usage)
        # Conservatively include cache writes at ordinary-input price.
        local_cost += (usage["cache_creation_input_tokens"]
                       * PRICES[condition.model]["input"] / 1_000_000)
        usage["local_cost_usd"] = local_cost
        usage["provider_cost_usd"] = None
        return ProviderResult(
            parsed=dict(blocks[0].input), raw_response=raw, usage=usage,
            actual_cost_usd=local_cost, latency_ms=latency,
            returned_model=str(getattr(response, "model", condition.model)),
            stop_reason=str(getattr(response, "stop_reason", "")),
        )

    def wire_descriptor(self, *, condition: Condition, system: str, user_payload: dict,
                        output_schema: dict, output_name: str,
                        max_output_tokens: int) -> dict:
        value = {
            "model": condition.model, "max_tokens": int(max_output_tokens),
            "system": system,
            "messages": [{"role": "user", "content": canonical_json(user_payload)}],
            "tools": [{"name": "submit_evaluation_result", "description": output_name,
                       "input_schema": output_schema}],
            "tool_choice": {"type": "tool", "name": "submit_evaluation_result"},
        }
        if condition.effort:
            value["output_config"] = {"effort": condition.effort}
        return value


class ResponsesAdapter(ProviderAdapter):
    base_url = ""

    def wire_descriptor(self, *, condition: Condition, system: str, user_payload: dict,
                        output_schema: dict, output_name: str,
                        max_output_tokens: int) -> dict:
        payload: dict[str, Any] = {
            "model": condition.model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": canonical_json(user_payload)},
            ],
            "max_output_tokens": int(max_output_tokens),
            "text": {"format": {"type": "json_schema", "name": output_name,
                                "strict": True, "schema": output_schema}},
        }
        if condition.effort:
            payload["reasoning"] = {"effort": condition.effort}
        if condition.native_tools:
            payload["tools"] = [{"type": name} for name in condition.native_tools]
        return payload

    def invoke(self, *, condition: Condition, system: str, user_payload: dict,
               output_schema: dict, output_name: str,
               max_output_tokens: int) -> ProviderResult:
        payload = self.wire_descriptor(
            condition=condition, system=system, user_payload=user_payload,
            output_schema=output_schema, output_name=output_name,
            max_output_tokens=max_output_tokens,
        )
        started = time.monotonic()
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/responses",
                headers={"Authorization": f"Bearer {self.api_key}",
                         "Content-Type": "application/json"},
                json=payload,
            )
        latency = int((time.monotonic() - started) * 1000)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise EvaluationError("provider response is not an object")
        usage_raw = body.get("usage") if isinstance(body.get("usage"), dict) else {}
        if usage_raw.get("input_tokens") is None or usage_raw.get("output_tokens") is None:
            raise EvaluationError("provider response lacks complete token usage")
        input_detail = usage_raw.get("input_tokens_details") or {}
        output_detail = usage_raw.get("output_tokens_details") or {}
        native_usage = _native_tool_usage(body, usage_raw)
        usage = {
            "input_tokens": int(usage_raw.get("input_tokens") or 0),
            "output_tokens": int(usage_raw.get("output_tokens") or 0),
            "cached_input_tokens": int(input_detail.get("cached_tokens") or 0),
            "cache_creation_input_tokens": 0,
            "reasoning_tokens": int(output_detail.get("reasoning_tokens") or 0),
            "native_tools": native_usage,
            "cost_in_usd_ticks": usage_raw.get("cost_in_usd_ticks"),
        }
        cost_ticks = usage_raw.get("cost_in_usd_ticks")
        local_cost = _token_cost(condition.model, usage)
        if cost_ticks is not None:
            provider_cost = float(cost_ticks) / 10_000_000_000
            actual = provider_cost
        else:
            provider_cost = None
            actual = local_cost
            # OpenAI reports tool calls separately only when tools are enabled; xAI may use a map.
            for name, count in native_usage.items():
                normalized = str(name).lower().replace("server_side_tool_", "")
                if normalized in TOOL_PRICES:
                    actual += int(count or 0) * TOOL_PRICES[normalized]
        usage["local_cost_usd"] = local_cost
        usage["provider_cost_usd"] = provider_cost
        parsed = _json_result(_text_from_responses(body))
        return ProviderResult(
            parsed=parsed, raw_response=body, usage=usage, actual_cost_usd=actual,
            latency_ms=latency, returned_model=str(body.get("model") or condition.model),
            stop_reason=str(body.get("status") or body.get("stop_reason") or ""),
        )


class OpenAIAdapter(ResponsesAdapter):
    base_url = "https://api.openai.com/v1"


class XAIAdapter(ResponsesAdapter):
    base_url = "https://api.x.ai/v1"


def make_adapter(provider: str, *, api_key: str,
                 timeout_seconds: float = 120.0) -> ProviderAdapter:
    adapters = {"anthropic": AnthropicAdapter, "openai": OpenAIAdapter, "xai": XAIAdapter}
    cls = adapters.get(provider)
    if cls is None:
        raise EvaluationError(f"unsupported provider {provider}")
    return cls(api_key=api_key, timeout_seconds=timeout_seconds)


def discover_models(provider: str, *, api_key: str,
                    timeout_seconds: float = 30.0) -> dict:
    """Perform the providers' non-inference model-list request with an explicit key."""
    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/models"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
    elif provider in {"openai", "xai"}:
        base = "https://api.openai.com/v1" if provider == "openai" else "https://api.x.ai/v1"
        url = f"{base}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        raise EvaluationError(f"unsupported discovery provider {provider}")
    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.get(url, headers=headers)
    response.raise_for_status()
    body = response.json()
    if not isinstance(body, dict):
        raise EvaluationError("model-list response is not an object")
    return {"provider": provider, "endpoint": url, "response": body}
