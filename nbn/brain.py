"""Claude calls: triage new items, then draft wire posts. Rate-limited by a call budget."""
import json
import logging
import re
import time
from pathlib import Path

import anthropic

from . import config

log = logging.getLogger("nbn.brain")
client = anthropic.Anthropic()

CHARTER = (Path(__file__).resolve().parent.parent / "prompts" / "wire_voice.md").read_text()

_call_times: list = []


def _budget_ok() -> bool:
    now = time.time()
    while _call_times and _call_times[0] < now - 3600:
        _call_times.pop(0)
    return len(_call_times) < config.MAX_LLM_CALLS_PER_HOUR


def _create(model: str, system: str, user: str, max_tokens: int = 4000):
    if not _budget_ok():
        raise RuntimeError("LLM hourly call budget exhausted")
    _call_times.append(time.time())
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    try:
        # Server-side refusal fallbacks (needs a current SDK; degrades gracefully on older ones)
        return client.beta.messages.create(
            betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    except TypeError:
        return client.messages.create(**kwargs)


def _json_from(response) -> dict:
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {response.stop_details}")
    text = "".join(b.text for b in response.content if b.type == "text")
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"no JSON in response: {text[:200]}")
    return json.loads(match.group(0))


TRIAGE_SYSTEM = f"""You are the intake editor for Next Block News, a Bitcoin news wire on X.

{CHARTER}

You receive a batch of new feed items (title + summary + source) and the story keys already
covered recently. For EACH item decide:
- action: "draft" (in scope, newsworthy, not already covered), "skip" (out of scope, promo,
  opinion, altcoin-primary, duplicate of a recent story key), or "hold" (in scope but
  single-source rumor / unverifiable — worth watching, not drafting).
- story_key: a short kebab-case key identifying the underlying STORY (two outlets covering
  the same event must get the same key; reuse a recent key if it is the same story).
- class: "primary" (item IS an official source: Fed/SEC/Treasury release, filing, official
  account), "secondary" (press reporting), or "data" (pure market/chain data point).
- reason: five words max.

Source-type rules:
- Source "SEC EDGAR": a filing mentioning bitcoin. Class primary. Action draft ONLY when
  the filing is material Bitcoin news (a treasury purchase, acquisition, ETF change,
  Bitcoin-business event); skip incidental boilerplate mentions of bitcoin.
- Source starting "X detector": an aggregator's post — a TIP, never a source. Never class
  it primary. If genuinely newsworthy, action draft with class secondary (the pipeline
  hunts the primary source before drafting); otherwise skip.
- Source starting "X @" (officials and company accounts): primary for statements about
  themselves and their own actions.

Be strict: a wire that posts everything is noise. Typical batch yields 0-3 drafts.
Return ONLY a JSON array: [{{"url_hash": ..., "action": ..., "story_key": ..., "class": ..., "reason": ...}}]"""


def triage(items: list, recent_keys: list) -> list:
    payload = {
        "recent_story_keys": recent_keys,
        "items": [
            {"url_hash": i["url_hash"], "source": i["source"], "title": i["title"],
             "summary": i.get("summary", ""), "published": i.get("published", "")}
            for i in items
        ],
    }
    resp = _create(config.TRIAGE_MODEL, TRIAGE_SYSTEM, json.dumps(payload), max_tokens=4000)
    verdicts = _json_from(resp)
    by_hash = {v["url_hash"]: v for v in verdicts if isinstance(v, dict) and "url_hash" in v}
    return [
        {**it, **by_hash.get(it["url_hash"], {"action": "skip", "story_key": None,
                                              "class": "secondary", "reason": "no verdict"})}
        for it in items
    ]


DRAFT_SYSTEM = f"""{CHARTER}

You receive one news item plus the fetched source text and a list of verified X handles.
Write the wire post. HARD RULES: every number verbatim from the source text; quotes verbatim
only; no URLs anywhere in the post; mentions only from the verified list, max 2, only if
load-bearing. If the source text is empty or too thin to support a post, set post to null.

Return ONLY JSON:
{{"post": "...", "needs_second_source": true/false, "mentions_used": [...],
  "numbers_used": ["every numeric figure you wrote, exactly as written"]}}"""


def draft(item: dict, article_text: str, verified_handles: dict) -> dict:
    payload = {
        "source": item["source"], "title": item["title"], "url_class": item.get("class"),
        "published": item.get("published", ""),
        "verified_handles": verified_handles,
        "source_text": article_text or item.get("summary", ""),
    }
    resp = _create(config.ANTHROPIC_MODEL, DRAFT_SYSTEM, json.dumps(payload), max_tokens=2000)
    return _json_from(resp)
