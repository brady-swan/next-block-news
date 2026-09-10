"""Bounded X discovery material. Metadata is not inspection or corroboration."""
from __future__ import annotations

import copy
import datetime as dt
import json
import math

from .guide_context import _public_url

VERSION = "x-material-v1"
MAX_BYTES = 12 * 1024


def encode(value: dict) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def parse(raw) -> dict:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
        if (not isinstance(value, dict) or value.get("version") != VERSION
                or not isinstance(value.get("post"), dict)
                or not value["post"].get("id")
                or len(encode(value).encode()) > MAX_BYTES):
            return {}
        return value
    except (TypeError, ValueError):
        return {}


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value) and value >= 0 else None


def _age(published: str, captured: float):
    try:
        stamp = dt.datetime.fromisoformat(published.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        return max(0, round(captured - stamp.timestamp()))
    except (ValueError, TypeError):
        return None


def _post(tweet, users, media, captured, *, text_limit=9000):
    ident = str(tweet.get("id") or "")[:30]
    user = users.get(str(tweet.get("author_id") or ""), {})
    handle = str(user.get("username") or "")[:30]
    note = tweet.get("note_tweet") or tweet.get("note_post") or {}
    text = str(note.get("text") or tweet.get("text") or "")
    links = []
    for entities in (note.get("entities") or {}, tweet.get("entities") or {}):
        for row in list(entities.get("urls") or [])[:12]:
            url = _public_url(row.get("unwound_url") or row.get("expanded_url") or "")
            if url and url not in links:
                links.append(url)
    attachments = []
    for key in list((tweet.get("attachments") or {}).get("media_keys") or [])[:4]:
        m = media.get(key, {})
        attachments.append({
            "key": str(key)[:60], "type": str(m.get("type") or "unknown")[:30],
            "url": _public_url(m.get("url") or ""),
            "preview_url": _public_url(m.get("preview_image_url") or ""),
            "alt_text": str(m.get("alt_text") or "")[:500],
            "duration_ms": _number(m.get("duration_ms")), "visually_inspected": False,
        })
    metrics = tweet.get("public_metrics") or {}
    published = str(tweet.get("created_at") or "")[:100]
    return {
        "id": ident, "handle": handle or None,
        "url": f"https://x.com/{handle}/status/{ident}" if handle else
               f"https://x.com/i/status/{ident}",
        "text": text[:text_limit], "text_characters": len(text),
        "text_truncated": len(text) > text_limit, "long_text_available": bool(note.get("text")),
        "published_at": published, "captured_at": captured,
        "engagement": {
            "observed_at": captured, "post_age_seconds": _age(published, captured),
            "likes": _number(metrics.get("like_count")),
            "reposts": _number(metrics.get("retweet_count")),
            "quotes": _number(metrics.get("quote_count")),
            "replies": _number(metrics.get("reply_count")),
        },
        "linked_urls": links[:6], "media": attachments,
    }


def capture(tweet: dict, includes: dict, captured: float) -> dict:
    users = {str(u["id"]): u for u in includes.get("users", [])}
    media = {m["media_key"]: m for m in includes.get("media", [])}
    tweets = {str(t["id"]): t for t in includes.get("tweets", [])}
    refs = []
    for ref in list(tweet.get("referenced_tweets") or [])[:3]:
        ident = str(ref.get("id") or "")[:30]
        original = tweets.get(ident)
        refs.append({
            "relation": str(ref.get("type") or "")[:30], "id": ident,
            "available": original is not None,
            "post": _post(original, users, media, captured, text_limit=1800) if original else
                    {"id": ident, "url": f"https://x.com/i/status/{ident}"},
        })
    return bounded({
        "version": VERSION, "untrusted_discovery_material": True,
        "post": _post(tweet, users, media, captured), "referenced_posts": refs,
        "truncated": False,
    })


def bounded(value: dict, byte_limit=MAX_BYTES) -> dict:
    """Trim prose first; retain honest truncation and source identities."""
    value = copy.deepcopy(value)
    while len(encode(value).encode()) > byte_limit:
        value["truncated"] = True
        posts = [value["post"]] + [r["post"] for r in value.get("referenced_posts", [])]
        texts = [p for p in posts if len(p.get("text", "")) > 80]
        if texts:
            largest = max(texts, key=lambda p: len(p["text"].encode()))
            largest["text"] = largest["text"][:len(largest["text"]) // 2]
            largest["text_truncated"] = True
            continue
        for post in posts:
            post.pop("media", None)
            post.pop("linked_urls", None)
        if len(encode(value).encode()) <= byte_limit:
            break
        # Even pathological URL/metadata packets keep a usable original-post identity.
        return {"version": VERSION, "untrusted_discovery_material": True,
                "post": {k: value["post"].get(k) for k in ("id", "url", "text")},
                "truncated": True}
    return value


def preview(raw, *, text_limit=1200) -> dict | None:
    material = parse(raw)
    if not material:
        return None
    post = material["post"]
    return {
        "post_url": post.get("url"), "handle": post.get("handle"),
        "text": str(post.get("text") or "")[:text_limit],
        "text_truncated": bool(post.get("text_truncated") or
                               len(post.get("text", "")) > text_limit),
        "published_at": post.get("published_at"), "captured_at": post.get("captured_at"),
        "engagement": post.get("engagement"),
        "media_types": [m["type"] for m in post.get("media", [])],
        "quoted_sources": [{"relation": r["relation"], "available": r["available"],
                            "url": r["post"]["url"], "handle": r["post"].get("handle"),
                            "text_preview": str(r["post"].get("text") or "")[:300]}
                           for r in material.get("referenced_posts", [])],
        "source_urls": reference_urls(material)[:4],
        "status": "discovery_only_media_not_inspected",
    }


def reference_urls(raw) -> list[str]:
    material = parse(raw)
    if not material:
        return []
    urls = list(material["post"].get("linked_urls") or [])
    for ref in material.get("referenced_posts", []):
        urls += list(ref["post"].get("linked_urls") or []) + [ref["post"]["url"]]
    return list(dict.fromkeys(url for raw in urls if (url := _public_url(raw))))[:10]


def original_post_urls(raw) -> list[tuple[str, str]]:
    """Immediate quoted/reposted speakers, not links they happen to cite."""
    material = parse(raw)
    return [(str(ref["relation"]), url)
            for ref in material.get("referenced_posts", [])
            if ref.get("relation") in {"retweeted", "quoted"}
            and (url := _public_url((ref.get("post") or {}).get("url") or ""))]


def compact_preview(value: dict | None) -> dict | None:
    if not value:
        return None
    return {
        "post_url": str(value.get("post_url") or "")[:600],
        "handle": value.get("handle"),
        "text": str(value.get("text") or "")[:240], "text_truncated": True,
        "media_types": value.get("media_types", []),
        "engagement": value.get("engagement"),
        "quoted_sources": [{"url": str(r.get("url") or "")[:600],
                            "handle": r.get("handle"), "relation": r.get("relation"),
                            "available": r.get("available")}
                           for r in value.get("quoted_sources", [])[:2]],
        "status": "discovery_only_media_not_inspected",
    }


def merge(prior: dict, incoming: dict) -> dict:
    """Enrich one post without mixing different source identities or losing a quote."""
    if not prior:
        return incoming
    if prior["post"]["id"] != incoming["post"]["id"]:
        return prior
    value = copy.deepcopy(prior)
    if len(incoming["post"].get("text", "")) >= len(prior["post"].get("text", "")):
        value["post"] = copy.deepcopy(incoming["post"])
    refs = {r["id"]: r for r in prior.get("referenced_posts", [])}
    for row in incoming.get("referenced_posts", []):
        old = refs.get(row["id"])
        if not old or len(row["post"].get("text", "")) >= len(old["post"].get("text", "")):
            refs[row["id"]] = row
    value["referenced_posts"] = list(refs.values())[:3]
    for field in ("media", "linked_urls"):
        if not value["post"].get(field):
            value["post"][field] = prior["post"].get(field) or incoming["post"].get(field) or []
    return bounded(value)
