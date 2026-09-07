"""Small Responses boundary for the existing newsroom seats (no publishing tools)."""
from __future__ import annotations

import copy
import json
import os
from types import SimpleNamespace

import httpx


def provider_for(model: str) -> str:
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith("grok-"):
        return "xai"
    if model.startswith("gpt-"):
        return "openai"
    raise ValueError(f"Unsupported model: {model}")


def response_input(messages: list[dict]) -> list[dict]:
    result = []
    for message in messages:
        # Replay the complete output, including encrypted reasoning and phase metadata.
        # This lives in the bounded run history, never the editorial workbench.
        if "_responses_output" in message:
            result.extend(copy.deepcopy(message["_responses_output"]))
            continue
        content = message["content"]
        if isinstance(content, str):
            result.append({"role": message["role"], "content": content})
            continue
        for block in content:
            if block["type"] == "text":
                result.append({"role": message["role"], "content": block["text"]})
            elif block["type"] == "tool_use":
                result.append({"type": "function_call", "call_id": block["id"],
                               "name": block["name"], "arguments": json.dumps(block["input"])})
            elif block["type"] == "tool_result":
                result.append({"type": "function_call_output",
                               "call_id": block["tool_use_id"], "output": block["content"]})
            else:
                raise ValueError("Unsupported message content")
    return result


def native_counts(body: dict) -> tuple[int, int]:
    usage = body.get("usage") or {}
    reported = usage.get("server_side_tool_usage_details") or {}
    names = {
        "web_search_call": "web", "web_search": "web", "browse_page": "web",
        "open_page": "web", "web_search_with_snippets": "web",
        "x_search_call": "x", "x_keyword_search": "x", "x_semantic_search": "x",
        "x_user_search": "x", "x_thread_fetch": "x",
    }
    observed = {"web": 0, "x": 0}
    for row in body.get("output") or []:
        name = row.get("name") if row.get("type") == "custom_tool_call" else row.get("type")
        if name in names:
            observed[names[name]] += 1
    # Returned counters are billable calls; observations are the fallback, not additive.
    return tuple(int(reported[key]) if key in reported else observed[seat]
                 for key, seat in (("web_search_calls", "web"), ("x_search_calls", "x")))


def normalize(body: dict, *, provider: str, effort: str | None):
    raw_usage = body.get("usage") or {}
    detail = raw_usage.get("input_tokens_details") or {}
    cached = int(detail.get("cached_tokens") or 0)
    cache_write = int(detail.get("cache_write_tokens") or 0)
    web, x = native_counts(body)
    usage = SimpleNamespace(
        input_tokens=max(0, int(raw_usage.get("input_tokens") or 0) - cached - cache_write),
        output_tokens=int(raw_usage.get("output_tokens") or 0),
        cache_read_input_tokens=cached, cache_creation_input_tokens=cache_write,
        cache_creation=None,
        reasoning_tokens=int((raw_usage.get("output_tokens_details") or {}).get("reasoning_tokens") or 0),
        native_web_calls=web, native_x_calls=x,
        cost_in_usd_ticks=raw_usage.get("cost_in_usd_ticks"),
    )
    blocks = []
    stop = "end_turn"
    refused = False
    try:
        for row in body.get("output") or []:
            if row.get("type") == "function_call":
                args = json.loads(row["arguments"])
                if not isinstance(args, dict) or not row.get("call_id"):
                    raise ValueError("invalid function call")
                blocks.append(SimpleNamespace(type="tool_use", id=row["call_id"],
                                              name=row["name"], input=args))
                stop = "tool_use"
            elif row.get("type") == "message":
                for part in row.get("content") or []:
                    if part.get("type") == "refusal":
                        refused = True
                    elif part.get("type") == "output_text":
                        blocks.append(SimpleNamespace(type="text", text=part.get("text", "")))
    except (ValueError, KeyError, TypeError):
        stop, blocks = "invalid_response", []
    if body.get("status") != "completed" or body.get("error"):
        stop = "max_tokens" if body.get("status") == "incomplete" else "invalid_response"
    if refused:
        stop = "refusal"
    if stop in {"refusal", "max_tokens", "invalid_response"}:
        blocks = []  # Partial JSON is never a usable decision, even if it parses.
    return SimpleNamespace(
        content=blocks, stop_reason=stop, stop_details=body.get("incomplete_details"),
        usage=usage, provider=provider, effort=effort or "",
        model=str(body.get("model") or ""), raw_output=body.get("output") or [],
        raw=body, usage_available=("input_tokens" in raw_usage and "output_tokens" in raw_usage),
    )


class ResponsesClient:
    def __init__(self, model: str, *, timeout: float = 90):
        self.provider = provider_for(model)
        if self.provider == "anthropic":
            raise ValueError("Use the Anthropic SDK for Anthropic models")
        self.timeout = timeout
        self.messages = self  # The existing seats use .messages.create.

    def create(self, *, model: str, system, messages: list[dict], max_tokens: int,
               tools: list[dict] | None = None, tool_choice: dict | None = None,
               output_config: dict | None = None, schema: dict | None = None,
               native_tools: bool = False, max_tool_calls: int | None = None):
        if provider_for(model) != self.provider:
            raise ValueError("Provider changed during a model session")
        key_name = "XAI_API_KEY" if self.provider == "xai" else "OPENAI_API_KEY"
        key = os.environ.get(key_name)
        if not key:
            raise RuntimeError(f"Missing {key_name}")
        base = "https://api.x.ai/v1" if self.provider == "xai" else "https://api.openai.com/v1"
        system_text = system if isinstance(system, str) else "\n".join(b["text"] for b in system)
        effort = (output_config or {}).get("effort")
        payload = {"model": model, "input": [{"role": "system", "content": system_text}]
                   + response_input(messages), "max_output_tokens": max_tokens,
                   "store": False, "include": ["reasoning.encrypted_content"]}
        if effort:
            payload["reasoning"] = {"effort": effort}
        if tools:
            payload["tools"] = [{"type": "function", "name": t["name"],
                                 "description": t["description"],
                                 "parameters": t["input_schema"], "strict": t.get("strict", False)}
                                for t in tools]
        if tool_choice:
            kind = tool_choice["type"]
            payload["tool_choice"] = ({"type": "function", "name": tool_choice["name"]}
                                      if kind == "tool" else "required" if kind == "any" else kind)
            if kind == "tool":
                payload["parallel_tool_calls"] = False
        if schema:
            payload["text"] = {"format": {"type": "json_schema", "name": "nbn_result",
                                          "strict": True, "schema": schema}}
        if native_tools:
            if self.provider != "xai":
                raise ValueError("Native research is configured for xAI only")
            payload.setdefault("tools", []).extend([{"type": "web_search"}, {"type": "x_search"}])
            payload["max_tool_calls"] = max_tool_calls
            payload["include"].extend(["web_search_call.action.sources", "no_inline_citations"])
        # No SDK retries: the owning seat reserves and accounts for each attempt explicitly.
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            response = client.post(base + "/responses", json=payload,
                                   headers={"Authorization": f"Bearer {key}"})
        if not response.is_success:
            # Avoid echoing headers/prompts/provider error bodies in production logs.
            raise RuntimeError(f"{self.provider} Responses HTTP {response.status_code}")
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Provider response is not an object")
        return normalize(body, provider=self.provider, effort=effort)
