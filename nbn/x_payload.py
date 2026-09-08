"""Versioned text/media identity shared by delivery, recovery and owner binding."""
from . import visuals

VERSION = "x-payload-v2"


def version(raw):
    from .publisher_typefully import _timestamp
    if not raw.get("id") or "created_at" not in raw or "updated_at" not in raw:
        return None
    if _timestamp(raw["created_at"]) is None or (raw["updated_at"] is not None and _timestamp(raw["updated_at"]) is None):
        return None
    return {"id":str(raw["id"]),"created_at":raw["created_at"],"updated_at":raw["updated_at"]}


def build(texts, asset=None, media_id=""):
    posts=[{"text":str(t),"media":[]} for t in texts]
    if asset:
        if asset["kind"] in {"source_image", "pdf_page"}:
            credit=asset["metadata"].get("credit", "").strip()
            if not credit or len(posts)<2: raise ValueError("source image requires visible credit in receipt reply")
            posts[-1]["text"] += "\n\nImage: " + credit
        posts[0]["media"]=[{"media_id":str(media_id),"asset_id":asset["asset_id"],
            "content_hash":asset["content_hash"],"alt_text":asset["metadata"]["alt_text"],
            "credit":asset["metadata"].get("credit","")}]
    return {"version":VERSION,"posts":posts}


def fingerprint(payload):
    if payload.get("version")!=VERSION: raise ValueError("unknown media payload version")
    return VERSION+":"+visuals.digest(payload)


def request_posts(payload):
    return [{"text":p["text"],"media_ids":[m["media_id"] for m in p["media"]]} for p in payload["posts"]]


def has_media(raw):
    """Legacy absence is acceptable only for old text-only objects, not a v2 proof."""
    try:
        return any(p.get("media_ids") or p.get("quote_post_url") for p in raw["platforms"]["x"]["posts"])
    except (KeyError,TypeError):
        return True


def editable_surface(raw):
    """We do not own non-default per-post settings; never reset them through a rebuild."""
    try:
        x=raw["platforms"]["x"]
        if x.get("settings") or set(x)-{"enabled","posts","settings"}: return False
        for p in x["posts"]:
            if set(p)-{"text","media_ids","quote_post_url","subscribers","subscribers_only","paid_partnership","made_with_ai","hide_link_preview"}:
                return False
            if any(p.get(k) for k in ("quote_post_url","subscribers","subscribers_only","paid_partnership","made_with_ai","hide_link_preview")):
                return False
        return True
    except (KeyError,TypeError): return False


def matches(raw, payload, *, media_lookup, remote_version=None):
    from . import config, publisher_typefully as tf
    if payload.get("version")!=VERSION or tf._has_comment_marker(raw): return False
    if not editable_surface(raw): return False
    if str(raw.get("social_set_id"))!=str(config.TYPEFULLY_SOCIAL_SET_ID): return False
    if remote_version is not None and (not remote_version or version(raw)!=remote_version): return False
    try:
        x=raw["platforms"]["x"]; posts=x["posts"]
        if x.get("enabled") is not True or len(posts)!=len(payload["posts"]): return False
        for actual, expected in zip(posts,payload["posts"]):
            if actual.get("text")!=expected["text"] or actual.get("media_ids")!=[m["media_id"] for m in expected["media"]]:
                return False
            if any(actual.get(k) for k in ("quote_post_url","subscribers","subscribers_only","paid_partnership","made_with_ai")):
                return False
            if set(actual)-{"text","media_ids","quote_post_url","subscribers","subscribers_only","paid_partnership","made_with_ai","hide_link_preview"}:
                return False
            for media in expected["media"]:
                meta=media_lookup(media["media_id"])
                if meta.get("status")!="ready" or meta.get("alt_text")!=media["alt_text"]: return False
        return True
    except (KeyError,TypeError,ValueError):
        return False
