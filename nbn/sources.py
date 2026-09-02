"""Feed watchers. RSS/Atom via stdlib XML parsing; optional X recent-search.

Feed URLs are inherited from the proven swan-daily-brief curation (verified working
config), trimmed to wire scope: Bitcoin-native + markets + primary regulatory.
Bitcoin Magazine's feed has returned 403 for months upstream; kept here so a fix
shows up on its own, failures are per-feed and non-fatal.
"""
import html
import ipaddress
import json
import logging
import re
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit

import httpx

from . import config, guide_context

log = logging.getLogger("nbn.sources")


class UnsafeSourceURL(ValueError):
    """Raised before a source fetch can reach a local or non-HTTP destination."""


def _assert_public_http_url(url: str) -> None:
    parts = urlsplit((url or "").strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username:
        raise UnsafeSourceURL("source URL must be public HTTP(S) without credentials")
    host = parts.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise UnsafeSourceURL("local source host rejected")
    try:
        addresses = [ipaddress.ip_address(host)]
    except ValueError:
        try:
            addresses = {
                ipaddress.ip_address(row[4][0])
                for row in socket.getaddrinfo(
                    host, parts.port or (443 if parts.scheme == "https" else 80),
                    type=socket.SOCK_STREAM)
            }
        except (OSError, ValueError) as exc:
            raise UnsafeSourceURL(f"source host did not resolve safely: {host}") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise UnsafeSourceURL("private, loopback, link-local, or reserved source host rejected")

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
    # Regulators + newswires (added with the speed package; URLs live-tested 2026-08-30)
    "CFTC": "https://www.cftc.gov/RSS/RSSGP/rssgp.xml",
    "PR Newswire Financial": "https://www.prnewswire.com/rss/financial-services-latest-news/financial-services-latest-news-list.rss",
}

PRIMARY_SOURCES = {"Federal Reserve", "SEC Press Releases", "CFTC", "SEC EDGAR"}

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


# ── Perception feed (1,000+ aggregated outlets; activates with NBN_PERCEPTION_API_KEY) ──
_last_perception_poll = 0.0


def fetch_perception() -> list:
    """Poll Perception /feed for fresh Bitcoin articles, throttled to respect rate budget."""
    global _last_perception_poll
    import datetime
    import time as _time
    if not config.PERCEPTION_DIRECT_ENABLED or not config.PERCEPTION_API_KEY:
        return []
    if _time.time() - _last_perception_poll < config.PERCEPTION_POLL_SECONDS:
        return []
    _last_perception_poll = _time.time()
    today = datetime.datetime.now(datetime.timezone.utc).date()
    out = []
    try:
        with httpx.Client(timeout=20, headers={
            "Authorization": f"Bearer {config.PERCEPTION_API_KEY}"}) as client:
            resp = client.get("https://api.perception.to/feed", params={
                "keyword": "bitcoin",
                "startDate": (today - datetime.timedelta(days=1)).isoformat(),
                "endDate": today.isoformat(),
                "limit": 50, "page": 1,
            })
            resp.raise_for_status()
            raw = resp.json()
        rows = raw.get("data") or raw.get("items") or raw.get("results") or [] \
            if isinstance(raw, dict) else raw
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            get = lambda *ks: next((str(row[k]).strip() for k in ks if row.get(k)), "")  # noqa: E731
            title = get("Title", "title", "headline")
            url = get("URL", "url", "link")
            if title and url:
                out.append({
                    "source": get("Outlet", "outlet", "publisher", "source") or "Perception",
                    "title": title, "url": url,
                    "published": get("Date", "date", "published_at"),
                    "summary": get("Content", "content", "summary")[:600],
                })
    except Exception as exc:  # noqa: BLE001
        log.warning("perception feed failed: %s", exc)
    return out


# ── SEC EDGAR full-text watch: where corporate Bitcoin news legally originates ──
# Free, unmetered (SEC fair use). Filings mentioning "bitcoin", filed today or later.
EDGAR_URL = "https://efts.sec.gov/LATEST/search-index"


def fetch_edgar() -> list:
    import datetime
    today = datetime.datetime.now(datetime.timezone.utc).date()
    out = []
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": UA}) as client:
            resp = client.get(EDGAR_URL, params={
                "q": '"bitcoin"', "forms": "8-K",
                "startdt": str(today - datetime.timedelta(days=1)), "enddt": str(today),
            })
            resp.raise_for_status()
            hits = resp.json().get("hits", {}).get("hits", [])
        for h in hits[:25]:
            src = h.get("_source", {})
            adsh, _, filename = h.get("_id", "::").partition(":")
            cik = (src.get("ciks") or [""])[0].lstrip("0")
            if not (adsh and filename and cik):
                continue
            name = (src.get("display_names") or ["Unknown filer"])[0]
            url = (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                   f"{adsh.replace('-', '')}/{filename}")
            out.append({
                "source": "SEC EDGAR",
                "title": f"{name} filed {src.get('file_type', '8-K')} mentioning bitcoin",
                "url": url,
                # file_date is date-only; leave published empty so the freshness gate
                # doesn't misread a same-day filing as stale (startdt bounds age anyway).
                "published": "",
                "summary": f"Form {src.get('file_type', '8-K')} filed {src.get('file_date', '')} by {name}. Items: {src.get('items', '')}",
            })
    except Exception as exc:  # noqa: BLE001
        log.warning("edgar fetch failed: %s", exc)
    return out


# ── X recent-search poller ───────────────────────────────────────────────────
# from: bundles only — X's job here is account-watching, not searching.
# The PRIMARY roster comes from the public X List (membership fetched hourly, compiled
# into search queries); the bundles below stay hardcoded because they are deliberately
# NOT on the wire's public list (companies = association optics, detectors = tips only).
X_PRIMARY_QUERIES = [
    # Watched officials not on the public list
    '(from:SenLummis OR from:RepTomEmmer) -is:retweet',
    # Company newsrooms (primary for their own announcements)
    '(from:BitGo OR from:NYDIG OR from:coinbase OR from:Strategy OR from:galaxyhq'
    ' OR from:BlackRock OR from:DigitalAssets OR from:BitwiseInvest OR from:Grayscale'
    ' OR from:River OR from:Strike OR from:unchainedcom OR from:CasaHODL OR from:Swan)'
    ' -is:retweet',
]
X_RESEARCH_QUERIES = [
    # Tier 2 research signal monitored directly, eligible only for its own analysis.
    '(from:KobeissiLetter OR from:Barchart) -is:retweet',
]
X_GUIDE_HANDLES = tuple(guide_context.GUIDE_HANDLES.values())
X_GUIDE_QUERIES = [
    # Proven Bitcoin-news desks. Their posts are editorial leads: NBN still replaces
    # the receipt, but substantive claims should reach research before being judged.
    "(" + " OR ".join(f"from:{handle}" for handle in X_GUIDE_HANDLES) + ") -is:retweet",
]
X_DETECTOR_QUERIES = [
    # Fast detectors — DETECTION ONLY: never our source; a hit triggers the
    # source-resolution hunt that finds an eligible receipt.
    '(from:WatcherGuru OR from:CoinDesk OR from:TheBlockCo OR from:Blockworks_)'
    ' -is:retweet',
]
X_STATIC_QUERIES = (
    X_PRIMARY_QUERIES + X_RESEARCH_QUERIES + X_GUIDE_QUERIES + X_DETECTOR_QUERIES
)

_list_cache = {"members": [], "fetched": 0.0}


def _list_member_queries(client) -> list:
    """Compile the X List's membership into from: search queries (chunked under 512 chars)."""
    import time as _time
    if not config.X_LIST_ID:
        return []
    if _time.time() - _list_cache["fetched"] > config.X_LIST_REFRESH_SECONDS:
        try:
            resp = client.get(
                f"https://api.twitter.com/2/lists/{config.X_LIST_ID}/members",
                params={"max_results": 100},
            )
            resp.raise_for_status()
            members = [u["username"] for u in resp.json().get("data", [])]
            if members:
                _list_cache["members"] = members
                _list_cache["fetched"] = _time.time()
                log.info("x list roster refreshed: %d members", len(members))
        except Exception as exc:  # noqa: BLE001 - stale roster beats no roster
            log.warning("x list members fetch failed: %s", exc)
            _list_cache["fetched"] = _time.time()  # don't hammer on failure
    queries, chunk = [], []
    for m in _list_cache["members"]:
        chunk.append(f"from:{m}")
        if len("(" + " OR ".join(chunk) + ") -is:retweet") > 460:
            queries.append("(" + " OR ".join(chunk[:-1]) + ") -is:retweet")
            chunk = chunk[-1:]
    if chunk:
        queries.append("(" + " OR ".join(chunk) + ") -is:retweet")
    return queries


_last_x_poll = 0.0


def fetch_x(con=None) -> list:
    """X reads are pay-per-POST-READ (~$0.005 each) on the shared bearer. since_id is the
    cost seam: without it every poll re-returns (re-bills) the same recent tweets; with it
    a quiet poll returns zero posts and costs zero."""
    global _last_x_poll
    import time as _time
    if not config.X_BEARER_TOKEN:
        return []
    if _time.time() - _last_x_poll < config.X_POLL_SECONDS:
        return []
    _last_x_poll = _time.time()
    from . import store
    out = []
    headers = {"Authorization": f"Bearer {config.X_BEARER_TOKEN}"}
    with httpx.Client(timeout=15, headers=headers) as client:
        queries = _list_member_queries(client) + X_PRIMARY_QUERIES + X_RESEARCH_QUERIES
        if config.X_DETECTOR_ENABLED:
            queries += X_GUIDE_QUERIES + X_DETECTOR_QUERIES
        for qi, q in enumerate(queries):
            try:
                params = {
                    "query": q, "max_results": 25,
                    "tweet.fields": "created_at,public_metrics,author_id,entities",
                    "expansions": "author_id", "user.fields": "username,verified",
                }
                # Key since_id by query CONTENT hash, not position — list edits reorder queries.
                import hashlib as _hl
                qkey = _hl.sha256(q.encode()).hexdigest()[:12]
                since_id = store.kv_get(con, f"x_since_{qkey}") if con is not None else ""
                if since_id:
                    params["since_id"] = since_id
                else:
                    # First run: only the freshness window, not 7 days of backlog reads.
                    import datetime
                    params["start_time"] = (
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.timedelta(hours=6)
                    ).strftime("%Y-%m-%dT%H:%M:%SZ")
                resp = client.get(
                    "https://api.twitter.com/2/tweets/search/recent", params=params)
                resp.raise_for_status()
                data = resp.json()
                newest = data.get("meta", {}).get("newest_id")
                if newest and con is not None:
                    store.kv_set(con, f"x_since_{qkey}", newest)
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                for t in data.get("data", []):
                    user = users.get(t["author_id"], {})
                    uname = user.get("username", "unknown")
                    canonical_guide = guide_context.normalize_handle(uname)
                    if canonical_guide:
                        label = "X guide"
                    elif q in X_DETECTOR_QUERIES:
                        label = "X detector"
                    else:
                        label = "X"
                    tweet_url = f"https://x.com/{uname}/status/{t['id']}"
                    # A tweet is usually a POINTER: when a primary/roster account links
                    # out (FRED graph, press release, filing), THAT page is the story —
                    # follow it down so drafting reads the source, not the tweet, and the
                    # published receipt links the primary (SLF/PCE lesson, 2026-08-30).
                    # Detector tips keep the tweet URL (their links get replaced by
                    # web corroboration anyway).
                    outbound = []
                    if label in {"X", "X guide"}:
                        for u in (t.get("entities", {}) or {}).get("urls", []):
                            target = u.get("unwound_url") or u.get("expanded_url") or ""
                            host = target.split("/")[2].lower() if target.count("/") >= 2 else ""
                            if host and not host.endswith(("twitter.com", "x.com", "t.co")):
                                outbound.append(target)
                    # Keep guide posts as distinct leads even when RSS already ingested
                    # the linked page. Their value is the independent attention signal;
                    # source resolution receives the outbound links separately below.
                    story_url = (outbound[0] if label == "X" and len(outbound) == 1
                                 else tweet_url)
                    summary = t["text"][:600]
                    if story_url != tweet_url:
                        summary += f"\n[original post: {tweet_url}]"
                    elif label == "X guide" and outbound:
                        summary += "\n[linked pages: " + " ".join(outbound[:4]) + "]"
                    item = {
                        "source": f"{label} @{uname}",
                        "title": t["text"][:200],
                        "url": story_url,
                        "published": t.get("created_at", ""),
                        "summary": summary,
                    }
                    if label == "X guide":
                        metrics = t.get("public_metrics") or {}
                        signal = guide_context.build_signal(
                            canonical_guide, tweet_url, t["text"], {
                                "characters": len(t["text"]),
                                "likes": int(metrics.get("like_count") or 0),
                                "reposts": int(metrics.get("retweet_count") or 0),
                                "quotes": int(metrics.get("quote_count") or 0),
                            }, outbound,
                        )
                        item["discovery_context"] = json.dumps({
                            "untrusted_discovery_context": True,
                            "origin": "bitcoin_news_guide_account",
                            "guide_signal": signal,
                        }, separators=(",", ":"))
                    out.append(item)
            except Exception as exc:  # noqa: BLE001
                log.warning("x query failed: %s", exc)
                break  # a 429 would fail the rest too
    return out


def chart_image(url: str):
    """(png_bytes, file_name) for story URLs with an official chart image, else None.
    FRED graph pages render a PNG twin at fredgraph.png — the same chart the source's
    own social preview shows (Brady 2026-08-30: FRED links preview poorly on X; attach
    the chart, keep the link)."""
    m = re.search(r"fred\.stlouisfed\.org/graph/\??.*?g=([A-Za-z0-9]+)", url)
    if not m:
        return None
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": "curl/8.7.1"}) as client:
            r = client.get(f"https://fred.stlouisfed.org/graph/fredgraph.png?g={m.group(1)}")
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            return r.content, f"fredgraph-{m.group(1)}.png"
    except Exception as exc:  # noqa: BLE001
        log.warning("chart image fetch failed %s: %s", url, exc)
    return None


def _fred_csv(url: str) -> str:
    """Recent observations for a fred.stlouisfed.org/graph/?g=... URL, else ''."""
    m = re.search(r"fred\.stlouisfed\.org/graph/\??.*?g=([A-Za-z0-9]+)", url)
    if not m:
        return ""
    try:
        # FRED's WAF resets a browser UA on a non-browser TLS stack; plain curl UA passes.
        with httpx.Client(timeout=20, headers={"User-Agent": "curl/8.7.1"}) as client:
            csv = client.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?g={m.group(1)}")
        if csv.status_code != 200 or "," not in csv.text:
            return ""
        lines = csv.text.strip().splitlines()
        return (f"FRED data series (graph {m.group(1)}), header + last 24 observations, "
                f"most recent last:\n" + "\n".join([lines[0]] + lines[-25:]))
    except Exception as exc:  # noqa: BLE001
        log.warning("fred csv fetch failed %s: %s", url, exc)
        return ""


def fetch_article(url: str, limit: int = 8000) -> dict:
    """Best-effort article fetch with redirect/canonical/byline metadata."""
    try:
        # FRED graph pages are JS shells that reset non-browser connections, but every
        # graph has a CSV twin carrying the full data series — the actual primary source
        # behind Fed stat tweets. Go straight to the CSV, never the page.
        csv_text = _fred_csv(url)
        if csv_text:
            return {"text": csv_text[:limit], "final_url": url,
                    "canonical_url": url, "byline": "", "outcome": "ok",
                    "error_kind": "", "error_message": "", "redirect_chain": [url]}
        with httpx.Client(timeout=20, headers={"User-Agent": UA}, follow_redirects=False) as client:
            current_url = url
            redirect_chain = [url]
            for _ in range(6):
                _assert_public_http_url(current_url)
                resp = client.get(current_url)
                if not resp.is_redirect:
                    break
                location = resp.headers.get("location", "")
                if not location:
                    raise UnsafeSourceURL("redirect response omitted Location")
                current_url = urljoin(current_url, location)
                redirect_chain.append(current_url)
            else:
                raise UnsafeSourceURL("too many source redirects")
            resp.raise_for_status()
            body = resp.text
            # Shortlinks (bit.ly) unwrap here — re-check the final URL for a FRED graph.
            csv_text = _fred_csv(str(resp.url))
            if csv_text:
                return {"text": csv_text[:limit], "final_url": str(resp.url),
                        "canonical_url": str(resp.url), "byline": "", "outcome": "ok",
                        "error_kind": "", "error_message": "",
                        "redirect_chain": redirect_chain}
        canonical = ""
        if m := re.search(r'(?is)<link[^>]+rel=["\'][^"\']*canonical[^"\']*["\'][^>]+>', body):
            if href := re.search(r'(?i)href=["\']([^"\']+)', m.group(0)):
                canonical = html.unescape(href.group(1)).strip()
        byline = ""
        for pattern in (
            r'(?is)<meta[^>]+(?:name|property)=["\'](?:author|article:author)["\'][^>]+content=["\']([^"\']+)',
            r'(?is)<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:author|article:author)["\']',
        ):
            if m := re.search(pattern, body):
                byline = html.unescape(m.group(1)).strip()
                break
        body = re.sub(r"(?is)<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", body)
        text = html.unescape(_TAG_RE.sub(" ", body))
        return {"text": re.sub(r"\s+", " ", text).strip()[:limit],
                "final_url": str(resp.url), "canonical_url": canonical or str(resp.url),
                "byline": byline, "outcome": "ok", "error_kind": "",
                "error_message": "", "redirect_chain": redirect_chain}
    except Exception as exc:  # noqa: BLE001
        log.warning("article fetch failed %s: %s", url, exc)
        retryable = isinstance(exc, (httpx.TimeoutException, httpx.TransportError))
        if isinstance(exc, httpx.HTTPStatusError):
            retryable = exc.response.status_code in {408, 425, 429} or exc.response.status_code >= 500
        outcome = "infrastructure_retryable" if retryable else "evidence_failed"
        return {"text": "", "final_url": url, "canonical_url": url, "byline": "",
                "outcome": outcome, "error_kind": type(exc).__name__,
                "error_message": str(exc)[:300], "redirect_chain": [url]}


def fetch_article_text(url: str, limit: int = 8000) -> str:
    """Compatibility wrapper for callers that only need source text."""
    return fetch_article(url, limit)["text"]
