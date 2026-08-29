"""Feed watchers. RSS/Atom via stdlib XML parsing; optional X recent-search.

Feed URLs are inherited from the proven swan-daily-brief curation (verified working
config), trimmed to wire scope: Bitcoin-native + markets + primary regulatory.
Bitcoin Magazine's feed has returned 403 for months upstream; kept here so a fix
shows up on its own, failures are per-feed and non-fatal.
"""
import html
import logging
import re
import xml.etree.ElementTree as ET

import httpx

from . import config

log = logging.getLogger("nbn.sources")

FEEDS = {
    # Primary sources (an item here is presumptively class=primary)
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "SEC Press Releases": "https://www.sec.gov/news/pressreleases.rss",
    # Bitcoin-native / industry
    "Bitcoin Magazine": "https://bitcoinmagazine.com/.rss/full/",
    "CoinDesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "The Block": "https://www.theblock.co/rss.xml",
    "Cointelegraph": "https://cointelegraph.com/rss",
    # Markets / macro
    "Bloomberg Markets": "https://feeds.bloomberg.com/markets/news.rss",
    "CNBC": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "Wall Street Journal": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "Fox Business": "https://moxie.foxbusiness.com/google-publisher/latest.xml",
}

PRIMARY_SOURCES = {"Federal Reserve", "SEC Press Releases"}

UA = "NextBlockNews/0.1 (+news wire; contact via x.com)"
_TAG_RE = re.compile(r"<[^>]+>")


def _text(el, *names) -> str:
    for name in names:
        found = el.find(name)
        if found is not None:
            val = found.text or found.get("href") or ""
            if val.strip():
                return html.unescape(_TAG_RE.sub(" ", val)).strip()
    return ""


def _parse_feed(source: str, body: str) -> list:
    items = []
    root = ET.fromstring(body)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    channel_items = root.findall(".//item") or root.findall(".//a:entry", ns)
    for el in channel_items[:30]:
        title = _text(el, "title", "{http://www.w3.org/2005/Atom}title")
        link = _text(el, "link", "{http://www.w3.org/2005/Atom}link")
        if not link:
            link_el = el.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
        published = _text(
            el, "pubDate", "{http://www.w3.org/2005/Atom}published",
            "{http://www.w3.org/2005/Atom}updated",
        )
        summary = _text(el, "description", "{http://www.w3.org/2005/Atom}summary")[:600]
        if title and link:
            items.append({
                "source": source, "title": title, "url": link,
                "published": published, "summary": summary,
            })
    return items


def fetch_feeds() -> list:
    """Fetch all feeds; per-feed failures are logged and skipped."""
    out = []
    with httpx.Client(timeout=15, headers={"User-Agent": UA}, follow_redirects=True) as client:
        for source, url in FEEDS.items():
            try:
                resp = client.get(url)
                resp.raise_for_status()
                out.extend(_parse_feed(source, resp.text))
            except Exception as exc:  # noqa: BLE001 - one bad feed must not kill the cycle
                log.warning("feed %s failed: %s", source, exc)
    return out


# ── Optional X recent-search poller ─────────────────────────────────────────
# Curated queries on the bitcoin_pulse pattern; official accounts are primary-class.
X_QUERIES = [
    '(from:SECGov OR from:federalreserve OR from:USTreasury) -is:retweet',
    '(bitcoin ETF OR bitcoin custody) (filing OR approved OR acquires OR acquisition) -is:retweet lang:en',
]
X_PRIMARY_AUTHORS = {"SECGov", "federalreserve", "USTreasury"}


def fetch_x() -> list:
    if not config.X_BEARER_TOKEN:
        return []
    out = []
    headers = {"Authorization": f"Bearer {config.X_BEARER_TOKEN}"}
    with httpx.Client(timeout=15, headers=headers) as client:
        for q in X_QUERIES:
            try:
                resp = client.get(
                    "https://api.twitter.com/2/tweets/search/recent",
                    params={
                        "query": q, "max_results": 25,
                        "tweet.fields": "created_at,public_metrics,author_id",
                        "expansions": "author_id", "user.fields": "username,verified",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                for t in data.get("data", []):
                    user = users.get(t["author_id"], {})
                    uname = user.get("username", "unknown")
                    out.append({
                        "source": f"X @{uname}",
                        "title": t["text"][:200],
                        "url": f"https://x.com/{uname}/status/{t['id']}",
                        "published": t.get("created_at", ""),
                        "summary": t["text"][:600],
                    })
            except Exception as exc:  # noqa: BLE001
                log.warning("x query failed: %s", exc)
                break  # a 429 would fail the rest too
    return out


def fetch_article_text(url: str, limit: int = 8000) -> str:
    """Best-effort article body fetch for the drafting step (numbers must come from here)."""
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": UA}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            body = resp.text
        body = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", body)
        text = html.unescape(_TAG_RE.sub(" ", body))
        return re.sub(r"\s+", " ", text).strip()[:limit]
    except Exception as exc:  # noqa: BLE001
        log.warning("article fetch failed %s: %s", url, exc)
        return ""
