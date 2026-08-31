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


def _create(model: str, system: str, user: str, max_tokens: int = 4000, effort: str = None):
    if not _budget_ok():
        raise RuntimeError("LLM hourly call budget exhausted")
    _call_times.append(time.time())
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    if effort:
        kwargs["output_config"] = {"effort": effort}
    # Server-side refusal fallbacks exist only on Opus 5 / Fable 5 (Sonnet 5 400s on the
    # parameter — learned in production 2026-08-30); TypeError covers pre-fallbacks SDKs.
    if model.startswith(("claude-opus-5", "claude-fable-5")):
        try:
            return client.beta.messages.create(
                betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
        except TypeError:
            pass
    return client.messages.create(**kwargs)


def _json_from(response, lenient_draft: bool = False) -> dict:
    if response.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {response.stop_details}")
    text = "".join(b.text for b in response.content if b.type == "text")
    match = re.search(r"\{.*\}|\[.*\]", text, re.DOTALL)
    if not match:
        if lenient_draft:
            # A prose non-answer from the drafting call = "no post" — degrade to a
            # clean hold ("thin source") instead of an exception in the retry path.
            return {"post": None, "needs_second_source": False}
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
  the same event must get the same key). You receive two key lists: an item matching a
  "posted_story_keys" entry is already covered — action skip, reuse that key. An item
  matching an "open_story_keys" entry is NOT yet covered — do NOT skip for that reason;
  REUSE that exact key (a second outlet on an open story is what confirms it).
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


def triage(items: list, recent_keys: list, open_keys: list = None) -> list:
    payload = {
        "posted_story_keys": recent_keys,
        "open_story_keys": open_keys or [],
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

If the source is an X post, the reader will see the ORIGINAL post right under ours (as a
quote or link). Never restate its copy — that is reading the news back to the reader.
Lead with material the original does NOT say, drawn from the source text (deeper figures,
the prior reading, what changed, who is affected). If the source text offers nothing
beyond the original post's own words, set post to null.

If "already_covered" context is provided, the wire has ALREADY PUBLISHED the underlying
story. Never re-announce it as NEW — if the new development is material, prefix the post
"UPDATE:" and lead with what is new, referencing the earlier news in passing; if the
item adds nothing material, set post to null.

EVENT DATING (hard): determine when the news-making EVENT itself occurred or was
announced, from the source text — NEVER the date of the article in front of you (a
fresh write-up of an old event is the exact failure this field exists to catch). Rules:
a date range ("between Aug. 16 and Aug. 26") uses the END date; a research finding or
report uses when it was FIRST published or reported, not when this article covered it;
an investigative revelation of old facts counts as new disclosure (disclosure date).
If the only date you can anchor is the article's own, return null — do not substitute
it. Return "event_date" (YYYY-MM-DD or null). The wire covers events, not write-ups;
a stale event will be dropped by the system regardless of copy.

DATA PROVENANCE: when the article's load-bearing numbers come from a named third-party
data provider (Coinglass, Glassnode, Farside, SoSoValue...), attribute the PROVIDER in
the copy and return its name as "data_provider". Never attribute the aggregator that
repackaged the number.

Return ONLY JSON:
{{"post": "...", "event_date": "YYYY-MM-DD or null", "data_provider": "name or null",
  "needs_second_source": true/false, "mentions_used": [...],
  "numbers_used": ["every numeric figure you wrote, exactly as written"]}}"""


def draft(item: dict, article_text: str, verified_handles: dict, already_covered: list = None) -> dict:
    payload = {
        "source": item["source"], "title": item["title"], "url_class": item.get("class"),
        "published": item.get("published", ""),
        "verified_handles": verified_handles,
        "source_text": article_text or item.get("summary", ""),
    }
    if already_covered:
        payload["already_covered"] = already_covered
    resp = _create(config.ANTHROPIC_MODEL, DRAFT_SYSTEM, json.dumps(payload), max_tokens=2000)
    return _json_from(resp, lenient_draft=True)
