"""Feed watchers. RSS/Atom via stdlib XML parsing; optional X recent-search.

The roster covers Bitcoin-native, markets and primary regulatory discovery. A listed
feed is not guaranteed available; errors are isolated per feed and retried later.
"""
import html
import ipaddress
import json
import logging
import re
import socket
import time
import datetime as dt
import hashlib
from email.utils import parsedate_to_datetime
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlsplit

import httpx

from . import config, guide_context, lead_material

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

PILOT_FEEDS = {
    "Bitcoin Core": "https://bitcoincore.org/en/rss.xml",
    "Bitcoin Optech": "https://bitcoinops.org/feed.xml",
    "BTCPay Server": "https://blog.btcpayserver.org/rss.xml",
}

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
    **PILOT_FEEDS,
}

PRIMARY_SOURCES = {"Federal Reserve", "SEC Press Releases", "CFTC", "SEC EDGAR"}

UA = "NextBlockNews/0.1 (+news wire; contact via x.com)"
_TAG_RE = re.compile(r"<[^>]+>")


class CollectedBatch(list):
    """Items plus collector-owned progress. Acknowledge only after durable upsert."""

    def __init__(self):
        super().__init__()
        self.checkpoints = {}


def acknowledge(con, batch) -> None:
    if not isinstance(batch, CollectedBatch) or not batch.checkpoints:
        return
    with con:
        con.executemany("INSERT OR REPLACE INTO kv(k,v) VALUES (?,?)",
                        list(batch.checkpoints.items()))


def _bootstrap_old(published: str, now: float) -> bool:
    try:
        try:
            stamp = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            stamp = parsedate_to_datetime(published)
        return bool(stamp.tzinfo is not None and
                    now - stamp.timestamp() > config.DESK_CANDIDATE_MAX_AGE_HOURS * 3600)
    except (ValueError, TypeError, AttributeError, OverflowError):
        return False  # Unknown date is not silently suppressed.


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


def fetch_feeds(con=None) -> list:
    """Fetch all feeds; per-feed failures are logged and skipped."""
    from . import observations, store
    out = CollectedBatch()
    with httpx.Client(timeout=15, headers={"User-Agent": UA}, follow_redirects=True) as client:
        for source, url in FEEDS.items():
            try:
                resp = client.get(url)
                resp.raise_for_status()
                rows = _parse_feed(source, resp.text)
                bootstrap_key = "pilot_feed_initialized:" + source
                if (source in PILOT_FEEDS and con is not None
                        and not store.kv_get(con, bootstrap_key)):
                    for row in rows:
                        if _bootstrap_old(row["published"], time.time()):
                            row["_bootstrap_background"] = True
                    out.checkpoints[bootstrap_key] = str(time.time())
                out.extend(rows)
                observations.source_poll(con, "rss:" + source, source, "rss", count=len(rows))
            except Exception as exc:  # noqa: BLE001 - one bad feed must not kill the cycle
                observations.source_poll(con, "rss:" + source, source, "rss", error=type(exc).__name__)
                log.warning("feed %s failed: %s", source, exc)
    return out


# ── Perception feed (1,000+ aggregated outlets; activates with NBN_PERCEPTION_API_KEY) ──
_last_perception_poll = 0.0


def fetch_perception(con=None) -> list:
    """Poll Perception /feed for fresh Bitcoin articles, throttled to respect rate budget."""
    global _last_perception_poll
    from . import observations
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
        observations.source_poll(con, "perception", "Perception", "perception", count=len(out))
    except Exception as exc:  # noqa: BLE001
        observations.source_poll(con, "perception", "Perception", "perception", error=type(exc).__name__)
        log.warning("perception feed failed: %s", exc)
    return out


# ── SEC EDGAR full-text watch: where corporate Bitcoin news legally originates ──
# Free, unmetered (SEC fair use). Filings mentioning "bitcoin", filed today or later.
EDGAR_URL = "https://efts.sec.gov/LATEST/search-index"


def fetch_edgar(con=None) -> list:
    import datetime
    from . import observations
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
        observations.source_poll(con, "edgar", "SEC EDGAR", "edgar", count=len(out))
    except Exception as exc:  # noqa: BLE001
        observations.source_poll(con, "edgar", "SEC EDGAR", "edgar", error=type(exc).__name__)
        log.warning("edgar fetch failed: %s", exc)
    return out


# ── X recent-search poller ───────────────────────────────────────────────────
# from: bundles only — X's job here is account-watching, not searching.
# The PRIMARY roster comes from the public X List (membership fetched hourly, compiled
# into search queries); the bundles below stay hardcoded because they are deliberately
# NOT on the wire's public list (companies = association optics, detectors = tips only).
X_PRIMARY_QUERIES = [
    # Watched officials not on the public list
    '(from:SenLummis OR from:RepTomEmmer) -is:retweet -is:reply',
    # Company newsrooms (primary for their own announcements)
    '(from:BitGo OR from:NYDIG OR from:coinbase OR from:Strategy OR from:galaxyhq'
    ' OR from:BlackRock OR from:DigitalAssets OR from:BitwiseInvest OR from:Grayscale'
    ' OR from:River OR from:Strike OR from:unchainedcom OR from:CasaHODL OR from:Swan)'
    ' -is:retweet -is:reply',
]
X_RESEARCH_QUERIES = [
    # Tier 2 research signal monitored directly, eligible only for its own analysis.
    '(from:KobeissiLetter OR from:Barchart) -is:retweet -is:reply',
]
X_GUIDE_HANDLES = tuple(guide_context.GUIDE_HANDLES.values())
X_GUIDE_QUERIES = [
    # Proven Bitcoin-news desks. Their posts are editorial leads: NBN still replaces
    # the receipt, but substantive claims should reach research before being judged.
    "(" + " OR ".join(f"from:{handle}" for handle in X_GUIDE_HANDLES)
    + ") -is:retweet -is:reply",
]
X_DETECTOR_QUERIES = [
    # Fast detectors — DETECTION ONLY: never our source; a hit triggers the
    # source-resolution hunt that finds an eligible receipt.
    '(from:WatcherGuru OR from:CoinDesk OR from:TheBlockCo OR from:Blockworks_)'
    ' -is:retweet -is:reply',
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
        if len("(" + " OR ".join(chunk) + ") -is:retweet -is:reply") > 460:
            queries.append("(" + " OR ".join(chunk[:-1]) + ") -is:retweet -is:reply")
            chunk = chunk[-1:]
    if chunk:
        queries.append("(" + " OR ".join(chunk) + ") -is:retweet -is:reply")
    return queries


_last_x_poll = 0.0


def _x_item(tweet: dict, includes: dict, query: str, captured: float) -> dict:
    if not str(tweet.get("id") or "").isdigit() or not isinstance(tweet.get("text"), str):
        raise ValueError("malformed X post; page not acknowledged")
    material = lead_material.capture(tweet, includes, captured)
    post = material["post"]
    uname = post.get("handle") or "unknown"
    canonical_guide = guide_context.normalize_handle(uname)
    label = ("X guide" if canonical_guide else
             "X detector" if query in X_DETECTOR_QUERIES else "X")
    outbound = []
    for url in post.get("linked_urls", []):
        host = (urlsplit(url).hostname or "").lower()
        if not any(host == h or host.endswith("." + h) for h in ("x.com", "twitter.com", "t.co")):
            outbound.append(url)
    story_url = outbound[0] if label == "X" and len(outbound) == 1 else post["url"]
    item = {
        "source": f"{label} @{uname}", "title": post["text"][:200],
        "url": story_url, "published": post.get("published_at") or "",
        "summary": post["text"][:600], "source_material": lead_material.encode(material),
    }
    if canonical_guide:
        metrics = post.get("engagement") or {}
        item["discovery_context"] = json.dumps({
            "untrusted_discovery_context": True, "origin": "bitcoin_news_guide_account",
            "guide_signal": guide_context.build_signal(
                canonical_guide, post["url"], post["text"], {
                    "characters": post.get("text_characters", len(post["text"])),
                    "likes": metrics.get("likes"), "reposts": metrics.get("reposts"),
                    "quotes": metrics.get("quotes"),
                }, outbound),
        }, separators=(",", ":"))
    return item


def fetch_x(con=None) -> list:
    """Bounded recent search; no checkpoint moves until the worker stores this batch."""
    global _last_x_poll
    if not config.X_BEARER_TOKEN or time.time() - _last_x_poll < config.X_POLL_SECONDS:
        return []
    _last_x_poll = time.time()
    from . import store, observations
    out = CollectedBatch()
    headers = {"Authorization": f"Bearer {config.X_BEARER_TOKEN}"}
    with httpx.Client(timeout=15, headers=headers) as client:
        queries = _list_member_queries(client) + X_PRIMARY_QUERIES + X_RESEARCH_QUERIES
        if config.X_DETECTOR_ENABLED:
            queries += X_GUIDE_QUERIES + X_DETECTOR_QUERIES
        for q in dict.fromkeys(queries):
            qkey = hashlib.sha256(q.encode()).hexdigest()[:12]
            cursor_key = "x_cursor:" + qkey
            try:
                saved = store.kv_get(con, cursor_key) if con is not None else ""
                state = json.loads(saved) if saved else {}
                if not isinstance(state, dict):
                    raise ValueError("invalid X cursor")
                legacy_since = store.kv_get(con, "x_since_" + qkey) if con is not None else ""
                if not state:
                    state = ({"since_id": legacy_since} if legacy_since else {"start_time":
                        (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=6))
                        .strftime("%Y-%m-%dT%H:%M:%SZ")})
                lower = {k: state[k] for k in ("since_id", "start_time") if state.get(k)}
                head = state.get("head") or ""
                token = state.get("next_token") or ""
                count = 0
                for _ in range(3):
                    params = {
                        "query": q, "max_results": 25, **lower,
                        "tweet.fields": "created_at,public_metrics,author_id,entities,note_tweet,referenced_tweets,attachments",
                        "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id,attachments.media_keys",
                        "user.fields": "username",
                        "media.fields": "type,url,preview_image_url,alt_text,duration_ms",
                    }
                    if token:
                        params["next_token"] = token
                    resp = client.get("https://api.twitter.com/2/tweets/search/recent", params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    if not isinstance(data, dict) or "meta" not in data:
                        raise ValueError("invalid X search response")
                    if data.get("errors") and not data.get("data"):
                        raise ValueError("X search returned only errors")
                    # Normalize the entire page before accepting any of its progress.
                    rows = [_x_item(t, data.get("includes") or {}, q, time.time())
                            for t in data.get("data", [])]
                    meta = data.get("meta") or {}
                    if not head:
                        head = str(meta.get("newest_id") or
                                   max((int(t["id"]) for t in data.get("data", [])), default=0) or "")
                    token = str(meta.get("next_token") or "")
                    if token and (not rows or not head):
                        raise ValueError("X pagination omitted page identity")
                    out.extend(rows)
                    count += len(rows)
                    progress = ({**lower, "head": head, "next_token": token} if token else
                                {"since_id": head} if head else
                                {"since_id": lower["since_id"]} if lower.get("since_id") else {})
                    out.checkpoints[cursor_key] = json.dumps(progress, separators=(",", ":"))
                    if not token:
                        break
                group = ("Bitcoin news guides" if q in X_GUIDE_QUERIES else
                         "Research accounts" if q in X_RESEARCH_QUERIES else
                         "Detectors" if q in X_DETECTOR_QUERIES else "Watched accounts")
                observations.source_poll(con, "x:" + qkey, group + " · " + qkey, "x", count=count)
            except Exception as exc:  # one query must not suppress unrelated guides
                observations.source_poll(con, "x:" + qkey, "X query · " + qkey, "x",
                                         error=type(exc).__name__)
                log.warning("x query %s failed: %s", qkey, type(exc).__name__)
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
                    break  # shared rate limit; retain acknowledged earlier-page progress
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
