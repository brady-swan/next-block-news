"""Immutable visual assets and bounded source-image discovery; no publishing authority."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup
from PIL import Image

from . import config, visual_render

MAX_BYTES = 4 * 1024 * 1024
MAX_PIXELS = 12_000_000
MAX_STORAGE = 512 * 1024 * 1024
MAX_IMAGE_CONTEXT = 12 * 1024 * 1024


def initialize(con):
    con.executescript("""
      CREATE TABLE IF NOT EXISTS visual_assets (
        asset_id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, mime TEXT NOT NULL,
        byte_size INTEGER NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
        run_id TEXT NOT NULL, candidate_id TEXT NOT NULL, kind TEXT NOT NULL,
        metadata_json TEXT NOT NULL, created_at REAL NOT NULL,
        writer_inspected_at REAL, retained INTEGER NOT NULL DEFAULT 0);
      CREATE INDEX IF NOT EXISTS visual_assets_run ON visual_assets(run_id,candidate_id);
      CREATE TABLE IF NOT EXISTS visual_uploads (
        upload_key TEXT PRIMARY KEY, asset_id TEXT NOT NULL, alt_text TEXT NOT NULL,
        media_id TEXT, upload_url TEXT, state TEXT NOT NULL, error TEXT,
        created_at REAL NOT NULL, updated_at REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS visual_choices (
        run_id TEXT NOT NULL, story_id TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
        asset_id TEXT, action TEXT NOT NULL, preset TEXT, state TEXT NOT NULL,
        created_at REAL NOT NULL, updated_at REAL NOT NULL,
        PRIMARY KEY(run_id,story_id));
    """)
    choice_columns={r[1] for r in con.execute("PRAGMA table_info(visual_choices)")}
    if "payload_json" not in choice_columns:
        con.execute("ALTER TABLE visual_choices ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'")
    columns={r[1] for r in con.execute("PRAGMA table_info(posts)")}
    for name in ("media_payload_json", "media_remote_version"):
        if columns and name not in columns:
            con.execute(f"ALTER TABLE posts ADD COLUMN {name} TEXT")
    con.commit()


def root():
    return Path(config.DB_PATH).parent / "visual-assets"


def encoded(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def digest(value):
    return hashlib.sha256(value if isinstance(value,bytes) else encoded(value).encode()).hexdigest()


def check_image(data):
    if not data or len(data)>MAX_BYTES:
        raise ValueError("image exceeds 4 MiB limit")
    with Image.open(io.BytesIO(data)) as im:
        if im.format not in {"PNG","JPEG","WEBP"} or getattr(im,"n_frames",1)!=1:
            raise ValueError("only static PNG/JPEG/WebP images are supported")
        if im.width*im.height>MAX_PIXELS or min(im.size)<200:
            raise ValueError("image dimensions outside supported range")
        mime=Image.MIME[im.format]; size=im.size
        im.verify()
    return mime,size


def save(con, *, run_id, candidate_id, kind, data, metadata):
    mime,(width,height)=check_image(data)
    if len(encoded(metadata).encode())>128*1024:
        raise ValueError("visual evidence metadata exceeds 128 KiB")
    content_hash=digest(data)
    asset_id="visual_"+digest([content_hash,run_id,candidate_id,metadata])[:32]
    if con.execute("SELECT 1 FROM visual_assets WHERE asset_id=?",(asset_id,)).fetchone():
        return get(con,asset_id)
    usage=con.execute("SELECT COALESCE(SUM(byte_size),0) FROM visual_assets").fetchone()[0]
    if usage+len(data)>MAX_STORAGE:
        raise ValueError("visual storage admission limit; existing assets preserved")
    folder=root(); folder.mkdir(parents=True,exist_ok=True)
    path=folder/content_hash
    if not path.exists() or digest(path.read_bytes())!=content_hash:
        # Atomic immutable content-addressed file; interrupted writes are never accepted.
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".asset-", delete=False) as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
            temporary=stream.name
        os.replace(temporary,path)
    con.execute("INSERT INTO visual_assets(asset_id,content_hash,mime,byte_size,width,height,"
                "run_id,candidate_id,kind,metadata_json,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (asset_id,content_hash,mime,len(data),width,height,run_id,candidate_id,kind,
                 encoded(metadata),time.time()))
    con.commit()
    return get(con,asset_id)


def get(con,asset_id):
    row=con.execute("SELECT * FROM visual_assets WHERE asset_id=?",(str(asset_id),)).fetchone()
    if not row:
        raise ValueError("unknown visual asset")
    result=dict(row); result["metadata"]=json.loads(result.pop("metadata_json"))
    return result


def bytes_for(asset):
    data=(root()/asset["content_hash"]).read_bytes()
    if len(data)!=asset["byte_size"] or digest(data)!=asset["content_hash"]:
        raise ValueError("visual asset bytes changed or unavailable")
    return data


def manifest(asset):
    return {k:asset[k] for k in ("asset_id","content_hash","mime","width","height","kind",
                                "candidate_id","run_id","writer_inspected_at","metadata")}


def image_block(asset):
    return {"type":"image","source":{"type":"base64","media_type":asset["mime"],
            "data":base64.b64encode(bytes_for(asset)).decode()},"_asset_id":asset["asset_id"],
            "_content_hash":asset["content_hash"]}


def without_pixels(value):
    if isinstance(value,list):
        return [without_pixels(v) for v in value]
    if isinstance(value,dict):
        if value.get("type")=="image":
            return {"type":"image_manifest","asset_id":value.get("_asset_id"),
                    "content_hash":value.get("_content_hash")}
        return {k:without_pixels(v) for k,v in value.items()}
    return value


def image_bytes(value):
    if isinstance(value,list): return sum(image_bytes(v) for v in value)
    if isinstance(value,dict):
        if value.get("type")=="image": return len(value.get("source",{}).get("data", ""))
        return sum(image_bytes(v) for v in value.values())
    return 0


def discover_html(body,page_url):
    """Metadata only, before text extraction removes figures. No network."""
    soup=BeautifulSoup(body,"html.parser"); out=[]; seen=set()
    container=soup.select_one(".td-post-content,article,[itemprop=articleBody],main") or soup
    for node in list(container.find_all("img"))[:30]+list(soup.select('meta[property="og:image"],meta[name="twitter:image"]')):
        src=node.get("data-src") or node.get("data-lazy-src") or node.get("src") or node.get("content") or ""
        if not src and node.get("srcset"):
            src=node["srcset"].split(",")[-1].strip().split(" ")[0]
        url=urljoin(page_url,src)
        if not src or urlsplit(url).scheme not in {"http","https"} or url in seen or len(url)>2000:
            continue
        if any(s in url.lower() for s in ("logo","favicon","tracking","pixel.gif","/ads/")):
            continue
        dims=[]
        for key in ("width","height"):
            v=str(node.get(key) or "")
            dims.append(int(v) if v.isdigit() else None)
        if any(v is not None and v<200 for v in dims): continue
        fig=node.find_parent("figure"); caption=fig.find("figcaption") if fig else None
        seen.add(url)
        out.append({"url":url,"source_url":page_url,"alt_text":str(node.get("alt") or "")[:500],
                    "caption":caption.get_text(" ",strip=True)[:700] if caption else "",
                    "width":dims[0],"height":dims[1],"credit":"","image_date":None,
                    "kind":"article_image" if node.name=="img" else "social_preview",
                    "reuse_status":"unknown","inspected":False})
        if len(out)==6: break
    return out


def download(url, *, deadline=None):
    from . import sources
    end=min(deadline or float("inf"),time.monotonic()+10)
    current=url
    with httpx.Client(follow_redirects=False,headers={"User-Agent":sources.UA}) as client:
        for _ in range(6):
            sources._assert_public_http_url(current)
            remaining=end-time.monotonic()
            if remaining<=0: raise ValueError("visual fetch deadline")
            with client.stream("GET",current,timeout=remaining) as resp:
                if resp.is_redirect:
                    if not resp.headers.get("location"): raise ValueError("image redirect without location")
                    current=urljoin(current,resp.headers["location"]); continue
                resp.raise_for_status()
                if resp.headers.get("content-type","").split(";")[0] not in {"image/png","image/jpeg","image/webp"}:
                    raise ValueError("unsupported image response type")
                data=bytearray()
                for part in resp.iter_bytes(65536):
                    data.extend(part)
                    if len(data)>MAX_BYTES or time.monotonic()>end: raise ValueError("image byte/time limit")
                check_image(bytes(data))
                return bytes(data),current
    raise ValueError("image redirect limit")


def pdf_page(url,page,*,deadline):
    """One original-layout page, with bounded download/render. No OCR, cropping or resizing later."""
    import subprocess
    from . import sources, pdf_source
    if not isinstance(page,int) or isinstance(page,bool) or not 1<=page<=pdf_source.MAX_PAGES:
        raise ValueError("PDF page must be within first 20 pages")
    end=min(deadline,time.monotonic()+10); current=url; data=None
    with httpx.Client(follow_redirects=False,headers={"User-Agent":sources.UA}) as client:
        for _ in range(6):
            sources._assert_public_http_url(current)
            remaining=end-time.monotonic()
            if remaining<=0: raise ValueError("PDF image deadline")
            with client.stream("GET",current,timeout=remaining) as resp:
                if resp.is_redirect:
                    current=urljoin(current,resp.headers.get("location", "")); continue
                resp.raise_for_status(); buf=bytearray()
                for part in resp.iter_bytes(65536):
                    buf.extend(part)
                    if len(buf)>pdf_source.MAX_INPUT_BYTES or time.monotonic()>end:
                        raise ValueError("PDF image input/time limit")
                data=bytes(buf); break
    if not data or not data.startswith(b"%PDF-"): raise ValueError("not a PDF")
    with tempfile.TemporaryDirectory(prefix="nbn-visual-pdf-") as directory:
        path=Path(directory)/"source.pdf"; path.write_bytes(data)
        prefix=Path(directory)/"page"
        remaining=end-time.monotonic()
        if remaining<=0: raise ValueError("PDF image deadline")
        try:
            subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),"-singlefile","-scale-to","2000",
                "-png",str(path),str(prefix)],check=True,timeout=remaining,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            output=prefix.with_suffix(".png")
            if output.stat().st_size>MAX_BYTES: raise ValueError("PDF page image exceeds byte allowance")
            result=output.read_bytes(); check_image(result)
        except (subprocess.SubprocessError,OSError) as exc:
            raise ValueError("PDF page could not be rendered within allowance") from exc
    return result,{"source_url":current,"source_pdf_hash":digest(data),"page":page,
        "transformation":"Full original-layout page, longest side 2000 px; no crop/highlight/OCR", "reuse_status":"unknown"}


def render_asset(con, *, run_id,candidate_id,kind,preset,spec,evidence,alt_text,purpose,parent=None):
    alt=visual_render.short(alt_text,1000,"alt text")
    purpose=visual_render.short(purpose,500,"visual purpose")
    validated=visual_render.validate(kind,spec,evidence)
    data,size=visual_render.render(kind,preset,validated)
    return save(con,run_id=run_id,candidate_id=candidate_id,kind=kind,data=data,metadata={
        "spec":validated,"preset":preset,"template_version":visual_render.VERSION,"evidence":evidence,
        "alt_text":alt,"purpose":purpose,"parent_asset_id":parent,"reuse_status":"nbn_original",
        "credit":validated["source"],"source_url":evidence[0]["final_url"],"emphasis":"NBN added"})


def proposal(con,asset_id,*,run_id,members,required=False):
    a=get(con,asset_id)
    if a["run_id"]!=run_id or a["candidate_id"] not in members or not a["writer_inspected_at"]:
        raise ValueError("visual was not inspected for this story in this run")
    bytes_for(a)
    return {**manifest(a),"required":bool(required),"reusable":a["metadata"]["reuse_status"] in
            {"nbn_original","public_domain","licensed","permission"}}
