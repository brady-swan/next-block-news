"""Optional writer tools. Inspection has an explicit image return, not a textual claim."""
import json
import time
import httpx

from . import lead_material, visuals, writer_memory

GUIDANCE = """
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
Quotes/excerpts: source_fetch_id, passage (contiguous verbatim source text), highlights (exact spans),
document_title, location; quotes also speaker. Native paraphrases cannot supply literal quotations.
No hidden truncation: shorten a faithful passage if it cannot fit. Add alt_text and a short purpose.
Use blank lines between natural paragraphs in an excerpt; they affect layout, never its words.
For source-image reuse, inspect_visual accepts reuse_status plus reuse_fetch_id/reuse_quote:
an exact directly fetched permission/license statement, accurate alt_text and credit are required.
The editor judges whether that permission actually applies. External-image credit goes in the source
reply. inspect_pdf_page is available for the first 20 pages of an already fetched text PDF;
page inspection alone does not establish reuse permission.
Choose visual_required only if the final copy cannot stand without the image; otherwise write useful
standalone copy. An independent editor reviews the exact image, data/quote evidence, alt and credits.
"""


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
            found=[]
            for fid in v.get("fetch_ids",[])[:8]:
                receipt=session.fetches.get(fid)
                if receipt:
                    found.extend(dict(m,fetch_id=fid) for m in receipt.image_candidates)
            material=lead_material.parse(session.by_hash[cid].get("source_material"))
            posts=([material["post"]]+[r["post"] for r in material.get("referenced_posts",[])]) if material else []
            for post in posts:
                for m in post.get("media",[]):
                    if m.get("type")=="photo" and m.get("url"):
                        found.append({"url":m["url"],"source_url":post["url"],"alt_text":m.get("alt_text",""),
                            "kind":"x_photo","image_date":post.get("published_at"),"credit":post.get("handle"),
                            "reuse_status":"unknown","inspected":False})
            candidates=[]
            for m in found[:6]:
                key="image_"+visuals.digest([cid,m])[:24]
                state["candidates"][key]=(cid,m)
                candidates.append(dict(m,visual_id=key))
            assets=[visuals.manifest(visuals.get(session.con,r[0])) for r in session.con.execute(
                "SELECT asset_id FROM visual_assets WHERE run_id=? AND candidate_id=? ORDER BY created_at DESC LIMIT 6",
                (session.run_id,cid))]
            return session._tool_result(block.id,{"candidates":candidates,"assets":assets})
        if state["inspections"]>=4: raise ValueError("run visual inspection budget used")
        if block.name=="render_visual":
            if state["renders"]>=4: raise ValueError("run render budget used")
            state["renders"]+=1
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
            state["by_story"][cid]=state["by_story"].get(cid,0)+1
            data,metadata=visuals.pdf_page(receipt.final_url,v["page"],deadline=time.monotonic()+session._research_seconds_left())
            asset=visuals.save(session.con,run_id=session.run_id,candidate_id=cid,kind="pdf_page",data=data,
                metadata={**metadata,"evidence":[session._fetch_payload(receipt,cached=True)],
                    "alt_text":f"Page {v['page']} of the source document.","credit":receipt.source.display_name,
                    "purpose":"Inspect the document's original layout"})
        else:
            ident=v.get("visual_id","")
            if ident.startswith("visual_"):
                asset=visuals.get(session.con,ident)
                if asset["run_id"]!=session.run_id or asset["candidate_id"]!=cid:
                    # Reuse is a new candidate/run proposal, preserving old evidence and dates.
                    asset=visuals.save(session.con,run_id=session.run_id,candidate_id=cid,kind=asset["kind"],
                        data=visuals.bytes_for(asset),metadata={**asset["metadata"],"parent_asset_id":asset["asset_id"]})
            else:
                found=state["candidates"].get(ident)
                if not found or found[0]!=cid: raise ValueError("list the image first")
                if state["by_story"].get(cid,0)>=2: raise ValueError("story external inspection budget used")
                state["by_story"][cid]=state["by_story"].get(cid,0)+1
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
        state["inspections"]+=1
        writer_memory.save(session.con,session.run_id,asset["asset_id"],"research_step",
            {"visual_asset_id":asset["asset_id"],"content_hash":asset["content_hash"]},
            candidate_ids=[cid],title="Visual: "+asset["kind"])
        result=session._tool_result(block.id,{"ok":True,"visual":visuals.manifest(asset),
            "note":"Actual image follows. Inspect it before proposing; captions alone do not count."})
        result["_pixels"]=pixels
        return result
    except (ValueError,KeyError,TypeError,OSError,httpx.HTTPError) as exc:
        return session._tool_result(block.id,{"ok":False,"kind":"visual_unavailable","message":str(exc)[:400]},error=True)
