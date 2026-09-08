"""Optional writer tools. Inspection has an explicit image return, not a textual claim."""
import json
import re
import time
import httpx

from . import lead_material, visuals, writer_memory

GUIDANCE = """
When the story turns on a comparison or trend, consider showing it. Inspect a relevant source
chart, or make an original NBN chart from the evidence using the existing renderer. A useful
image helps readers understand the story at a glance, making it easier to engage with and
share, which can extend its reach. Aim for one clear takeaway, not extra decoration.
Image tools can also help you understand an image-only lead. Unknown reuse rights do not
prevent inspection; they do prevent automatic attachment. If an image would not improve
this post, finish the text and move on.
Optional visuals: use them when a chart, exact quote/excerpt or relevant source photo helps
readers understand THIS story. Text-only is normal; do not hunt for decoration or use a quota.
list_visuals returns metadata, not inspected pixels. inspect_visual and render_visual return
the actual stored image: look at it before selecting its asset_id in the dossier. Check mobile
legibility, factual support, dates/units, framing and credit. Never call a URL or caption inspection.
Source images with unknown reuse rights are review-only; do not claim permission from availability.
Our fixed templates are bar, line, comparison (before/after), quote and excerpt; landscape or square.
render_visual takes a JSON spec plus existing evidence_fetch_ids. Common spec: source (<=70 chars),
date, color (blue/red/yellow/green/orange/purple). Data: headline, optional eyebrow, unit, period,
points [{label,value (number or null for missing),date,source_fetch_id}], metric (none/sum/change/last).
Code calculates geometry and summary figures. Preserve signs/units and distinguish missing from zero.
Line charts default to x_axis=time: use distinct, increasing YYYY-MM-DD dates. Use x_axis=category
explicitly for equally spaced categories or trading sessions. Close labels may be omitted for
legibility while every point stays plotted at its true date; describe the observations in alt_text.
Use image text for source attribution, dates/periods, units and useful data qualifications such as
estimated, preliminary or seasonally adjusted. Do not add internal production/test labels such as
"illustrative data", "not news" or "test graphic" to the image. Keep fixture status in internal
metadata or development notes. Preserve literal source passages and meaningful data qualifications.
Keep Next Block News branding in the bottom-right lockup only; do not repeat it as a bottom-left
label. Retain actual external source attribution there. The renderer suppresses a duplicate NBN name.
Quotes/excerpts: source_fetch_id, passage (contiguous verbatim source text), highlights (exact spans),
document_title, location; quotes also speaker. Native paraphrases cannot supply literal quotations.
No hidden truncation: shorten a faithful passage if it cannot fit. Add alt_text and a short purpose.
Use blank lines between natural paragraphs in an excerpt; they affect layout, never its words.
Excerpt cards enlarge the selected passage to fill the content area. Choose the relevant passage
and useful surrounding context; prefer larger type to padding it with copy that adds no context.
For source-image reuse, inspect_visual accepts reuse_status plus reuse_fetch_id/reuse_quote:
an exact directly fetched permission/license statement, accurate alt_text and credit are required.
The editor judges whether that permission actually applies. External-image credit goes in the source
reply. inspect_pdf_page is available for the first 20 pages of an already fetched text PDF;
page inspection alone does not establish reuse permission.
Choose visual_required only if the final copy cannot stand without the image; otherwise write useful
standalone copy. An independent editor reviews the exact image, data/quote evidence, alt and credits.
Whenever image pixels support your reporting, include their inspected asset IDs in the story's
visual_evidence_ids (at most four), even when visual_asset_id is null. Evidence is separate from
attachment permission. Do not claim literal image text is a directly fetched textual quotation.
There are four inspection returns and four new renders per run, within the shared time/tool/image
byte limits. Cached source/PDF inspection still counts toward two external inspections per candidate.

Two render_visual examples (illustrative values only: replace with exact sourced facts and
returned candidate/receipt IDs, never reuse these as news). spec_json is JSON-encoded:
1. kind=bar, preset=landscape, evidence_fetch_ids=["fetch_id_from_tool"],
   spec_json={"headline":"Revenue by quarter","source":"Company results","date":"2026-09-08",
   "unit":"USD millions","period":"Q2 year-over-year","metric":"none","points":[
   {"label":"Q2 2025","date":"2025-06-30","value":100,"source_fetch_id":"fetch_id_from_tool"},
   {"label":"Q2 2026","date":"2026-06-30","value":32,"source_fetch_id":"fetch_id_from_tool"}]},
   alt_text="Revenue was $100 million in Q2 2025 and $32 million in Q2 2026.",
   purpose="Show the size of the revenue change."
2. kind=line, preset=landscape, evidence_fetch_ids=["fetch_id_from_tool"],
   spec_json={"headline":"Daily Bitcoin ETF net flows","source":"Issuer data","date":"2026-09-08",
   "unit":"USD millions","period":"September 1–3, 2026","metric":"none","points":[
   {"label":"Sep 1","date":"2026-09-01","value":100,"source_fetch_id":"fetch_id_from_tool"},
   {"label":"Sep 2","date":"2026-09-02","value":-20,"source_fetch_id":"fetch_id_from_tool"},
   {"label":"Sep 3","date":"2026-09-03","value":80,"source_fetch_id":"fetch_id_from_tool"}]},
   alt_text="Daily net flows: September 1 +$100M, September 2 -$20M, September 3 +$80M.",
   purpose="Show the direction of each day's flow, not price predictions."
Include candidate_id in both calls. Independently designed graphics can use adequately sourced
facts when source-image reuse is not permitted. Do not trace protected graphics or invent data
from unlabeled axes. Check actual pixels, dates, units, alt and the source handle/credit.
"""


def source_images(item, receipts=()):
    """Same six-image allowance, with actual post media before avatars/navigation/duplicates."""
    found = []
    material = lead_material.parse(item.get("source_material"))
    posts = ([material["post"]] + [r["post"] for r in material.get("referenced_posts", [])]) if material else []
    for post in posts:
        for media in post.get("media", []):
            if media.get("type") == "photo" and media.get("url"):
                found.append({"url": media["url"], "source_url": post["url"],
                    "alt_text": media.get("alt_text", ""), "kind": "x_photo",
                    "image_date": post.get("published_at"), "credit": post.get("handle"),
                    "reuse_status": "unknown", "inspected": False})
    for receipt in receipts:
        found.extend(dict(m, fetch_id=receipt.fetch_id) for m in receipt.image_candidates)
    def rank(m):
        avatar = bool(re.search(r"avatar|profile_images|favicon|(?:^|[/_.-])logo(?:[/_.-]|$)", str(m.get("url", "")), re.I))
        return (avatar, m.get("kind") != "x_photo")
    unique = {}
    for m in sorted(found, key=rank):
        if m.get("url"):
            unique.setdefault(m["url"], m)
    return list(unique.values())[:6]


def availability(images):
    if not images:
        return None
    return {"count": len(images), "tool": "list_visuals → inspect_visual",
        "purpose": "Understand this lead or assess a useful chart; inspection is not reuse permission.",
        "sources": [{"source_url": m.get("source_url"), "image_date": m.get("image_date"),
                     "kind": m.get("kind")} for m in images[:3]]}


def tool(name, description, props):
    return {"name": name, "description": description, "strict": True, "input_schema": {
        "type": "object", "additionalProperties": False, "properties": props, "required": list(props)}}


TOOLS = [
    tool("list_visuals", "List bounded available source-image metadata and saved assets for a candidate.", {
        "candidate_id": {"type": "string"}, "fetch_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 8}}),
    tool("inspect_visual", "Read actual pixels from a listed source image or an existing asset.", {
        "candidate_id": {"type": "string"}, "visual_id": {"type": "string"},
        "reuse_fetch_id": {"type":["string","null"]}, "reuse_quote": {"type":["string","null"]},
        "reuse_status": {"type":"string","enum":["unknown","public_domain","licensed","permission"]},
        "alt_text": {"type":["string","null"],"maxLength":1000}, "credit": {"type":["string","null"],"maxLength":200}}),
    tool("inspect_pdf_page", "Inspect one full original-layout page of an already fetched text PDF. No crop or OCR.", {
        "candidate_id":{"type":"string"},"fetch_id":{"type":"string"},"page":{"type":"integer","minimum":1,"maximum":20}}),
    tool("render_visual", "Render and inspect an exact fixed-template graphic from retained evidence. Spec format is in your orientation.", {
        "candidate_id": {"type": "string"}, "kind": {"type": "string", "enum": ["bar","line","comparison","quote","excerpt"]},
        "preset": {"type": "string", "enum": ["landscape","square"]}, "spec_json": {"type": "string", "maxLength": 12000},
        "evidence_fetch_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "alt_text": {"type": "string", "maxLength": 1000}, "purpose": {"type": "string", "maxLength": 500}}),
]


def dispatch(session, block):
    v=block.input; cid=v.get("candidate_id")
    try:
        if cid not in session.by_hash: raise ValueError("unknown candidate")
        if not hasattr(session,"visual_state"):
            session.visual_state={"candidates": {}, "inspections":0, "renders":0, "by_story":{}, "image_bytes":0}
        state=session.visual_state
        if block.name=="list_visuals":
            found = source_images(session.by_hash[cid],
                [session.fetches[fid] for fid in v.get("fetch_ids", [])[:8] if fid in session.fetches])
            candidates=[]
            for m in found[:6]:
                key="image_"+visuals.digest([cid,m])[:24]
                state["candidates"][key]=(cid,m)
                candidates.append(dict(m,visual_id=key))
            assets=[visuals.manifest(visuals.get(session.con,r[0])) for r in session.con.execute(
                "SELECT asset_id FROM visual_assets WHERE run_id=? AND candidate_id=? ORDER BY created_at DESC LIMIT 6",
                (session.run_id,cid))]
            return session._tool_result(block.id,{"candidates":candidates,"assets":assets})
        external=False
        if block.name!="render_visual" and state["inspections"]>=4: raise ValueError("run visual inspection budget used")
        if block.name=="render_visual":
            if state["renders"]>=4: raise ValueError("run render budget used")
            refs=v.get("evidence_fetch_ids",[])
            if not refs or any(fid not in session.fetches for fid in refs): raise ValueError("unknown evidence receipt")
            evidence=[session._fetch_payload(session.fetches[fid],cached=True) for fid in refs]
            asset=visuals.render_asset(session.con,run_id=session.run_id,candidate_id=cid,
                kind=v["kind"],preset=v["preset"],spec=json.loads(v["spec_json"]),evidence=evidence,
                alt_text=v["alt_text"],purpose=v["purpose"])
        elif block.name=="inspect_pdf_page":
            receipt=session.fetches.get(v.get("fetch_id"))
            if not receipt or receipt.retrieval_kind!="direct_fetch" or "[PDF page " not in receipt.text:
                raise ValueError("fetch the text PDF first")
            if state["by_story"].get(cid,0)>=2: raise ValueError("story external inspection budget used")
            external=True
            data,metadata=visuals.pdf_page(receipt.final_url,v["page"],deadline=time.monotonic()+session._research_seconds_left())
            asset=visuals.save(session.con,run_id=session.run_id,candidate_id=cid,kind="pdf_page",data=data,
                metadata={**metadata,"evidence":[session._fetch_payload(receipt,cached=True)],
                    "alt_text":f"Page {v['page']} of the source document.","credit":receipt.source.display_name,
                    "purpose":"Inspect the document's original layout"})
        else:
            ident=v.get("visual_id","")
            if ident.startswith("visual_"):
                asset=visuals.get(session.con,ident)
                external=asset["kind"] in {"source_image","pdf_page"}
                if external and state["by_story"].get(cid,0)>=2: raise ValueError("story external inspection budget used")
                if asset["run_id"]!=session.run_id or asset["candidate_id"]!=cid:
                    # Reuse is a new candidate/run proposal, preserving old evidence and dates.
                    asset=visuals.save(session.con,run_id=session.run_id,candidate_id=cid,kind=asset["kind"],
                        data=visuals.bytes_for(asset),metadata={**asset["metadata"],"parent_asset_id":asset["asset_id"]})
            else:
                found=state["candidates"].get(ident)
                if not found or found[0]!=cid: raise ValueError("list the image first")
                if state["by_story"].get(cid,0)>=2: raise ValueError("story external inspection budget used")
                external=True
                data,url=visuals.download(found[1]["url"],deadline=time.monotonic()+session._research_seconds_left())
                metadata={**found[1],"final_image_url":url,"purpose":"Source image under review",
                    "alt_text":str(v.get("alt_text") or found[1].get("alt_text") or "Source image awaiting an accessible description.")[:1000],
                    "credit":str(v.get("credit") or found[1].get("credit") or "")[:200]}
                if v.get("reuse_status","unknown")!="unknown":
                    if not v.get("credit") or not v.get("alt_text"):
                        raise ValueError("reusable images need an accurate alt description and visible credit")
                    receipt=session.fetches.get(v.get("reuse_fetch_id"))
                    quote=str(v.get("reuse_quote") or "").strip()
                    if not receipt or receipt.retrieval_kind!="direct_fetch" or not quote or quote not in receipt.text:
                        raise ValueError("reuse permission needs an exact retained source statement; availability is not permission")
                    metadata.update(reuse_status=v["reuse_status"],reuse_statement=quote,
                        reuse_evidence=session._fetch_payload(receipt,cached=True))
                asset=visuals.save(session.con,run_id=session.run_id,candidate_id=cid,kind="source_image",data=data,metadata=metadata)
        if block.name=="inspect_visual" and v.get("visual_id", "").startswith("visual_") and v.get("reuse_status","unknown")!="unknown":
            receipt=session.fetches.get(v.get("reuse_fetch_id")); quote=str(v.get("reuse_quote") or "").strip()
            if asset["kind"] not in {"source_image","pdf_page"} or not receipt or receipt.retrieval_kind!="direct_fetch" or not quote or quote not in receipt.text or not v.get("alt_text") or not v.get("credit"):
                raise ValueError("source-image reuse needs applicable exact permission, alt text and credit")
            asset=visuals.save(session.con,run_id=session.run_id,candidate_id=cid,kind=asset["kind"],data=visuals.bytes_for(asset),
                metadata={**asset["metadata"],"parent_asset_id":asset["asset_id"],"reuse_status":v["reuse_status"],"reuse_statement":quote,
                    "reuse_evidence":session._fetch_payload(receipt,cached=True),"alt_text":v["alt_text"],"credit":v["credit"]})
        pixels=visuals.image_block(asset)
        if state["image_bytes"]+visuals.image_bytes(pixels)>visuals.MAX_IMAGE_CONTEXT:
            raise ValueError("image context budget used")
        state["image_bytes"] += visuals.image_bytes(pixels)
        state["renders" if block.name=="render_visual" else "inspections"]+=1
        if external: state["by_story"][cid]=state["by_story"].get(cid,0)+1
        writer_memory.save(session.con,session.run_id,asset["asset_id"],"research_step",
            {"visual_asset_id":asset["asset_id"],"content_hash":asset["content_hash"]},
            candidate_ids=[cid],title="Visual: "+asset["kind"])
        result=session._tool_result(block.id,{"ok":True,"visual":visuals.manifest(asset),
            "note":"Actual image follows. Inspect it before proposing; captions alone do not count."})
        result["_pixels"]=pixels
        return result
    except (ValueError,KeyError,TypeError,OSError,httpx.HTTPError) as exc:
        return session._tool_result(block.id,{"ok":False,"kind":"visual_unavailable","message":str(exc)[:400]},error=True)
