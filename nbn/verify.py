"""Web corroboration: actively hunt for an INDEPENDENT second source for a held story.

Called when a single-outlet secondary story would otherwise wait for a second outlet to
drift through our feeds. Uses Claude's server-side web_search tool with an adversarial
prompt (find independent confirmation; default to NOT confirmed), then applies
deterministic independence checks the model cannot override:
- confirming domain must differ from the original story's domain
- known aggregator/syndication domains never count

A confirmed story is promoted to class "corroborated" (auto-postable). Failure modes all
fail safe: any error, timeout, or ambiguity leaves the story held.
"""
import json
import logging
import re
from urllib.parse import urlparse

import anthropic

from . import config

log = logging.getLogger("nbn.verify")
client = anthropic.Anthropic()

# Domains that republish wire copy — never independent confirmation.
AGGREGATOR_DOMAINS = {
    "news.google.com", "msn.com", "finance.yahoo.com", "yahoo.com", "flipboard.com",
    "feedly.com", "newsbreak.com", "smartnews.com", "ground.news", "binance.com",
    "tradingview.com", "investing.com", "marketscreener.com",
}

VERIFY_PROMPT = """You are the verification desk of a Bitcoin news wire. A story has been
reported by ONE outlet. Search the web and decide whether INDEPENDENT confirmation exists.

Independent means: a different news organization doing its own reporting, or a primary
source (official filing, press release, official account of the subject). These do NOT
count: syndicated/republished copies of the same text, aggregators, the same outlet's
other pages, posts that merely link or cite the original report, anonymous social posts.

Be adversarial: your job is to find reasons the story is NOT yet confirmed. If you are
not sure the confirming source is genuinely independent, it is not confirmed.

Story (from {outlet}): {title}
Original URL: {url}

Search for confirmation. Then return ONLY JSON:
{{"confirmed": true/false, "confirming_url": "...", "confirming_outlet": "...",
  "confirmation_type": "independent_report|primary_source|none", "reason": "one sentence"}}"""


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:  # noqa: BLE001
        return ""


def web_corroborate(item: dict) -> dict:
    """Returns {'confirmed': bool, 'confirming_url': ..., 'reason': ...}; fails safe."""
    from . import brain
    if not brain._budget_ok():
        return {"confirmed": False, "reason": "llm budget exhausted"}
    brain._call_times.append(__import__("time").time())
    prompt = VERIFY_PROMPT.format(outlet=item["source"], title=item["title"], url=item["url"])
    try:
        messages = [{"role": "user", "content": prompt}]
        for _ in range(4):  # server tool may pause the turn; resume until done
            resp = client.messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=2000,
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 4}],
                messages=messages,
            )
            if resp.stop_reason != "pause_turn":
                break
            messages = messages + [{"role": "assistant", "content": resp.content}]
        text = "".join(b.text for b in resp.content if b.type == "text")
        m = re.search(r"\{.*\}", text, re.DOTALL)
        verdict = json.loads(m.group(0)) if m else {}
    except Exception as exc:  # noqa: BLE001
        log.warning("web corroboration failed for %s: %s", item["title"][:60], exc)
        return {"confirmed": False, "reason": f"verify error: {exc}"[:150]}

    if not verdict.get("confirmed"):
        return {"confirmed": False, "reason": verdict.get("reason", "not confirmed")}

    # Deterministic independence checks — the model's yes is necessary, not sufficient.
    conf_url = verdict.get("confirming_url", "") or ""
    conf_dom, orig_dom = _domain(conf_url), _domain(item["url"])
    if not conf_dom or conf_dom == orig_dom:
        return {"confirmed": False, "reason": f"confirming domain not independent: {conf_dom or 'missing'}"}
    if conf_dom in AGGREGATOR_DOMAINS or any(conf_dom.endswith("." + a) for a in AGGREGATOR_DOMAINS):
        return {"confirmed": False, "reason": f"aggregator domain: {conf_dom}"}

    log.info("web-corroborated %s via %s", item["title"][:60], conf_dom)
    return {"confirmed": True, "confirming_url": conf_url,
            "confirming_outlet": verdict.get("confirming_outlet", conf_dom),
            "type": verdict.get("confirmation_type"), "reason": verdict.get("reason", "")}
