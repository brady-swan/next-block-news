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
    # "crypto" allowed as a business adjective (crypto exchange/custody firm...) and in
    # quoted official titles; banned as market/asset coverage.
    BUSINESS_NOUN = (r"\s+(custody|exchanges?|trading|firms?|company|companies|providers?|"
                     r"lenders?|brokers?|banks?|platforms?|startups?)")
    stripped = re.sub(r"\bcrypto" + BUSINESS_NOUN, " ", unquoted, flags=re.I)
    if re.search(r"\bcryptos?\b|\bcryptocurrenc\w*", stripped, re.I):
        errors.append("'crypto' as coverage (allowed only as business adjective or quoted title)")
    if m := ALLCAPS_RUN.search(post):
        if not all(w in CAPS_OK for w in m.group(0).split()):
            errors.append(f"all-caps run: {m.group(0)!r}")

    # Price discipline (owner rule 2026-08-31): the wire reports, it never wonders.
    # A question mark outside quotes is speculation's tell.
    if "?" in unquoted:
        errors.append("question in post (the wire states facts, it does not speculate)")

    # Data belongs to whoever measured it: attributing a second-tier aggregator is a
    # laddering failure (BeInCrypto/Coinglass lesson, 2026-08-31).
    if m := re.search(r"\bper\s+(BeInCrypto|CryptoPotato|U\.?Today|Coinpedia|AMBCrypto|"
                      r"CryptoNews|NewsBTC|Bitcoinist|ZyCrypto|CoinGape)\b", post, re.I):
        errors.append(f"attribution to second-tier aggregator: {m.group(1)!r} — "
                      "attribute the original data provider or reporter")

    # Prefix semantics are deterministic, not a model judgment: first coverage is NEW;
    # only an explicit, exact-key update may use UPDATE.
    coverage_action = item.get("_coverage_action")
    if coverage_action == "update" and not post.startswith("UPDATE:"):
        errors.append("covered-story update must start with 'UPDATE:'")
    elif coverage_action == "draft" \
            and item.get("class") in ("primary", "secondary", "corroborated") \
            and not post.startswith("NEW:"):
        errors.append("first-coverage news post must start with 'NEW:'")
    elif coverage_action is None \
            and item.get("class") in ("primary", "secondary", "corroborated") \
            and not post.startswith(("NEW:", "UPDATE:")):
        # Compatibility for non-pipeline callers that do not carry coverage metadata.
        errors.append("news post must start with 'NEW:' (or 'UPDATE:' on covered stories)")

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

    # Attribution repetition: name the source once; the receipt covers the rest.
    attributions = re.findall(r"\bper\s+((?:[A-Z@][\w.']*\s?){1,4})", post)
    seen_attr = {}
    for a in attributions:
        k = a.strip().lower()
        seen_attr[k] = seen_attr.get(k, 0) + 1
    for k, n in seen_attr.items():
        if n > 1:
            errors.append(f"attribution repeated {n}x: 'per {k}' (name the source once)")

    if len(post) > 2800:
        errors.append(f"post too long ({len(post)} chars)")
    return errors
