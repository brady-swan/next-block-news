"""Deterministic pre-publish gates. A draft failing ANY check is held, never posted.

These encode the charter mechanically. They run after the model, before the publisher,
and they are the reason class-based autopost is survivable: the model proposes, this vetoes.
"""
import json
import re
from pathlib import Path

HANDLES_PATH = Path(__file__).resolve().parent.parent / "handles.json"

BANNED_SUBSTRINGS = [
    "BREAKING", "🚨", "🚀", "🔥", "don't miss", "dont miss", "last chance",
    "to the moon", "bear market is over", "bull market is confirmed",
    "buy the dip", "load up", "get in before", "you should buy", "time to buy",
]
BANNED_WORDS = re.compile(
    r"\b(surges?|surging|erupts?|explodes?|skyrockets?|plummets?|crashes|massive|huge|"
    r"incredible|insane|parabolic|moon(?:ing)?|slams?|shocking|in shambles)\b", re.I)
FORECAST = re.compile(
    r"\b(will (?:hit|reach|rise|fall|surge)|is (?:headed|going) to \$|price target|"
    r"could (?:hit|reach) \$|next stop)\b", re.I)
URL_RE = re.compile(r"https?://\S+|\bt\.co/\S+", re.I)
MENTION_RE = re.compile(r"@([A-Za-z0-9_]{1,15})")
ALLCAPS_RUN = re.compile(r"\b[A-Z]{2,}(?:\s+[A-Z]{2,}){2,}\b")  # 3+ consecutive caps words

# Acronyms that legitimately appear upper-case and must not trip the caps check
CAPS_OK = {"BTC", "ETF", "SEC", "IRA", "USD", "CME", "NEW", "FED", "AI", "HPC", "CEO", "NYDIG"}


def verified_handles() -> dict:
    return json.loads(HANDLES_PATH.read_text())


NON_BITCOIN_TOKENS = re.compile(
    r"\b(ETH|ethereum|ether|XRP|ripple|ZEC|zcash|solana|SOL(?=\W|$)|dogecoin|DOGE|cardano|ADA(?=\W|$)|"
    r"altcoins?|memecoins?|stablecoins?|tether|USDT|USDC|shitcoins?)\b", re.I)


def _outside_quotes(text: str) -> str:
    """Text with double-quoted spans removed (official document titles are allowed there)."""
    return re.sub(r'"[^"]*"', " ", text)


def check(post: str, meta: dict, item: dict) -> list:
    """Return a list of violations; empty list = pass."""
    errors = []
    if not post or not post.strip():
        return ["empty post"]

    for s in BANNED_SUBSTRINGS:
        if s.lower() in post.lower():
            errors.append(f"banned substring: {s!r}")
    if m := BANNED_WORDS.search(post):
        errors.append(f"banned word: {m.group(0)!r}")
    if m := FORECAST.search(post):
        errors.append(f"forecast pattern: {m.group(0)!r}")
    if URL_RE.search(post):
        errors.append("URL in post body (receipts go in the first reply, system-attached)")
    # HARD SCOPE (owner rule 2026-08-29): Bitcoin only — no crypto, no other tokens.
    unquoted = _outside_quotes(post)
    if m := NON_BITCOIN_TOKENS.search(unquoted):
        errors.append(f"non-Bitcoin token/scope: {m.group(0)!r}")
    if re.search(r"\bcryptos?\b|\bcryptocurrenc\w*", unquoted, re.I):
        errors.append("'crypto' outside a quoted official title")
    if m := ALLCAPS_RUN.search(post):
        if not all(w in CAPS_OK for w in m.group(0).split()):
            errors.append(f"all-caps run: {m.group(0)!r}")

    # News posts must open with the house prefix
    if item.get("class") in ("primary", "secondary") and not post.startswith("NEW:"):
        errors.append("news post must start with 'NEW:'")

    # Mentions: only verified handles, max 2
    allowed = {h.lower() for h in verified_handles()}
    mentions = MENTION_RE.findall(post)
    if len(mentions) > 2:
        errors.append(f"too many mentions ({len(mentions)})")
    for m_ in mentions:
        if m_.lower() not in allowed:
            errors.append(f"unverified handle: @{m_}")

    # Numbers integrity: every figure the model says it used must be in the post,
    # and every figure in the post must appear in the source text we gave it.
    source_text = (meta.get("_source_text") or "").replace(",", "")
    post_numbers = re.findall(r"\d[\d,.]*", post)
    for num in post_numbers:
        plain = num.replace(",", "").rstrip(".")
        if plain and plain not in source_text:
            errors.append(f"number not in source text: {num}")

    if len(post) > 2800:
        errors.append(f"post too long ({len(post)} chars)")
    return errors
