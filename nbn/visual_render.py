"""Deterministic, bounded NBN graphics. No network or model-generated factual pixels."""
from __future__ import annotations

import io
import math
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

VERSION = "nbn-visuals-4"
ROOT = Path(__file__).resolve().parent.parent
BG, FG, MUTED = "#1B222A", "#CDD2D8", "#9DA6B0"
COLORS = {"blue": "#6EABF8", "red": "#ED7379", "yellow": "#F4D35E",
          "green": "#70C999", "orange": "#F59A52", "purple": "#B093EF"}
KINDS = {"quote", "excerpt", "bar", "line", "comparison"}


def normalized(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def font(size, bold=False):
    f = ImageFont.truetype(str(ROOT / "assets/fonts/Inter.ttf"), size)
    f.set_variation_by_axes([32, 650 if bold else 400])
    return f


def short(value, maximum, name, required=True):
    if not isinstance(value, str) or len(value) > maximum or (required and not value.strip()):
        raise ValueError(f"invalid {name}; at most {maximum} characters")
    return value.strip()


def validate(kind, spec, evidence):
    """Bind exact passages to retained receipts; typed data still receives editorial review."""
    if kind not in KINDS or not isinstance(spec, dict):
        raise ValueError("unsupported visual template")
    if not evidence or len(evidence) > 8:
        raise ValueError("visual needs retained source evidence")
    sources = {r["fetch_id"]: r for r in evidence}
    out = dict(spec)
    out["source"] = short(spec.get("source"), 70, "source")
    out["date"] = short(spec.get("date", ""), 40, "date", required=False)
    out["color"] = spec.get("color", "yellow" if kind=="excerpt" else "blue")
    if out["color"] not in COLORS:
        raise ValueError("unknown accent color")
    if kind in {"quote", "excerpt"}:
        receipt = sources.get(spec.get("source_fetch_id"))
        if not receipt or receipt.get("retrieval_kind") != "direct_fetch":
            raise ValueError("literal quotations require direct source text, not provider paraphrases")
        passage = short(spec.get("passage"), 1100 if kind == "excerpt" else 600, "passage")
        paragraphs=[normalized(p) for p in re.split(r"\n\s*\n",passage) if normalized(p)]
        breaks=[]; offset=0
        for paragraph in paragraphs[:-1]:
            offset+=len(paragraph)+1; breaks.append(offset)
        if not breaks and spec.get("paragraph_breaks"):
            breaks=spec["paragraph_breaks"]
            flat=normalized(passage)
            if (not isinstance(breaks,list) or len(breaks)>4 or
                    any(not isinstance(p,int) or p<=0 or p>=len(flat) or flat[p-1]!=" " or flat[p]==" " for p in breaks)):
                raise ValueError("paragraph breaks must fall between complete words")
        out["paragraph_breaks"]=breaks[:4]
        snapshot = normalized(receipt["text"])
        passage = normalized(passage)
        start = snapshot.find(passage)
        if start < 0:
            raise ValueError("passage is not contiguous verbatim source text")
        # Store the original receipt separately; boundaries are in its whitespace-normalized view.
        out.update(passage=passage, passage_start=start, passage_end=start + len(passage),
                   normalization="whitespace-only", surrounding_context=snapshot[max(0,start-500):start+len(passage)+500])
        out["location"] = short(spec.get("location", ""), 150, "source location", required=False)
        out["document_title"] = short(spec.get("document_title", ""), 250, "document title", required=False)
        highlights = spec.get("highlights", [])
        if not isinstance(highlights, list) or len(highlights) > 4:
            raise ValueError("at most four exact highlights")
        spans = []
        for highlight in highlights:
            h = normalized(short(highlight, 300, "highlight"))
            if passage.count(h) != 1:
                raise ValueError("highlight must occur exactly once in the selected passage")
            a = passage.index(h)
            if any(a < b and a + len(h) > c for c,b in spans):
                raise ValueError("overlapping highlights")
            spans.append((a, a+len(h)))
        out["highlight_spans"] = sorted(spans)
        if kind == "quote":
            out["speaker"] = short(spec.get("speaker"), 100, "speaker")
    else:
        out["headline"] = short(spec.get("headline"), 110, "headline")
        out["eyebrow"] = short(spec.get("eyebrow", ""), 60, "eyebrow", required=False)
        out["unit"] = short(spec.get("unit"), 40, "unit")
        out["period"] = short(spec.get("period"), 80, "observation period")
        points = spec.get("points")
        if not isinstance(points, list) or not 2 <= len(points) <= (2 if kind == "comparison" else 8):
            raise ValueError("need 2–8 points (exactly two for comparison)")
        clean = []
        for p in points:
            if not isinstance(p, dict) or p.get("source_fetch_id") not in sources:
                raise ValueError("every point needs a retained source reference")
            v = p.get("value")
            if v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1e18):
                raise ValueError("non-finite, boolean, or excessive numeric value")
            clean.append({"label": short(p.get("label"), 28, "point label"), "value": v,
                          "date": short(p.get("date"), 40, "point date"),
                          "source_fetch_id": p["source_fetch_id"]})
        if not any(p["value"] is not None for p in clean):
            raise ValueError("all points are missing")
        out["points"] = clean
        if kind=="line":
            out["x_axis"]=spec.get("x_axis","time")
            if out["x_axis"] not in {"time","category"}:
                raise ValueError("line x_axis must be time or category")
            if out["x_axis"]=="time":
                dates=[]
                for point in clean:
                    raw=point["date"]
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}",raw):
                        raise ValueError("time-axis dates require YYYY-MM-DD; use x_axis=category explicitly for categories")
                    dates.append(date.fromisoformat(raw))
                if any(b<=a for a,b in zip(dates,dates[1:])):
                    raise ValueError("time-axis dates must be distinct and strictly increasing")
        metric = spec.get("metric", "none")
        if metric not in {"none","sum","change","last"}:
            raise ValueError("unsupported metric; code computes sum/change/last")
        values = [p["value"] for p in clean]
        if metric != "none" and any(v is None for v in values):
            raise ValueError("incomplete observations cannot produce a complete metric")
        out["metric"] = metric
        decimals=[Decimal(str(v)) for v in values] if metric!="none" else []
        metric_value=(sum(decimals) if metric=="sum" else decimals[-1]-decimals[0]
                      if metric=="change" else decimals[-1] if metric=="last" else None)
        out["metric_value"]=(int(metric_value) if metric_value is not None and metric_value==int(metric_value)
                             else float(metric_value) if metric_value is not None else None)
    return out


def number(value):
    if value is None:
        return "Not available"
    rendered=format(Decimal(str(value)),",f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def line_positions(spec,left,right):
    points=spec["points"]
    step=(right-left)/len(points)
    if spec.get("x_axis","time")=="category":
        return [left+step*(i+.5) for i in range(len(points))]
    days=[date.fromisoformat(p["date"]).toordinal() for p in points]
    start,end=left+step/2,right-step/2
    return [start+(day-days[0])/(days[-1]-days[0])*(end-start) for day in days]


def distinct_labels(boxes):
    """Keep endpoint labels first, then other labels that fit, without shifting data points."""
    selected=[]
    order=list(dict.fromkeys([0,len(boxes)-1,*range(len(boxes))]))
    for i in order:
        box=boxes[i]
        if box is None: continue
        if all(box[2]+12<=boxes[j][0] or boxes[j][2]+12<=box[0] or
               box[3]+8<=boxes[j][1] or boxes[j][3]+8<=box[1] for j in selected):
            selected.append(i)
    return set(selected)


def lines(text, face, width, paragraph_breaks=()):
    """Return text and original normalized offsets; never silently truncate."""
    result, line, start = [], "", 0
    for match in re.finditer(r"\S+", text):
        word = match.group()
        if line and match.start() in paragraph_breaks:
            result.extend([(line,start),("",match.start())]); line=""
        if face.getlength(word) > width:
            raise ValueError("word cannot fit at readable size")
        proposed = line + (" " if line else "") + word
        if face.getlength(proposed) > width:
            result.append((line,start))
            line, start = word, match.start()
        else:
            if not line:
                start = match.start()
            line = proposed
    if line:
        result.append((line,start))
    return result


def expanded_text(text, width, height, *, minimum=44, bold=False, paragraph_breaks=(), spans=()):
    """Find the largest readable font that fits the unchanged passage, including highlights."""
    low, high = minimum, int(height*1.5)
    best = None
    while low <= high:
        n = (low+high)//2
        face = font(n,bold)
        step = max(round(n*1.15),n+16)
        try:
            wrapped = lines(text,face,width,paragraph_breaks)
            # Avoid a stranded final word without changing text or crossing a paragraph break.
            if (len(wrapped)>1 and len(wrapped[-1][0].split())==1 and
                    wrapped[-1][1] not in paragraph_breaks):
                previous,start = wrapped[-2]
                split = previous.rfind(" ")
                if split>0:
                    tail = text[start+split+1:wrapped[-1][1]+len(wrapped[-1][0])]
                    if face.getlength(tail)<=width:
                        wrapped[-2] = (previous[:split],start)
                        wrapped[-1] = (tail,start+split+1)
        except ValueError:
            wrapped = None
        # Measure the actual final line; reserving another leading interval leaves a blank band.
        last_height = 0
        if wrapped:
            last,start = wrapped[-1]
            last_height = face.getbbox(last,anchor="lt")[3]
            if any(a < start+len(last) and b > start for a,b in spans):
                last_height = max(last_height,n+9)
        if wrapped and (len(wrapped)-1)*step+last_height <= height:
            best = (n,face,wrapped,step,last_height)
            low = n+1
        else:
            high = n-1
    if best is None:
        raise ValueError("text overflows at readable size; choose a shorter faithful passage")
    n,face,wrapped,step,last_height = best
    if len(wrapped)>1:
        step = min(n*1.43,(height-last_height)/(len(wrapped)-1))
    if (len(wrapped)-1)*step+last_height < height*.9:
        raise ValueError("excerpt cannot fill the card at this wording; select useful surrounding source context")
    return n,face,wrapped,step


def text_block(draw, text, box, *, size=64, minimum=44, color=FG, bold=False, spans=(), paragraph_breaks=(), expand=False, highlight_color="yellow"):
    x,y,w,h = box
    if expand:
        n,face,wrapped,step = expanded_text(text,w,h,minimum=minimum,bold=bold,paragraph_breaks=paragraph_breaks,spans=spans)
    else:
        for n in range(size,minimum-1,-2):
            face = font(n,bold)
            wrapped = lines(text,face,w,paragraph_breaks)
            step = round(n*1.43)
            if len(wrapped)*step <= h:
                break
        else:
            raise ValueError("text overflows at readable size; choose a shorter faithful passage")
    for line,start in wrapped:
        draw.text((x,y),line,font=face,fill=color,anchor="lt")
        for a,b in spans:
            lo,hi = max(a,start),min(b,start+len(line))
            if hi <= lo:
                continue
            left=x+face.getlength(line[:lo-start]); right=x+face.getlength(line[:hi-start])
            draw.rectangle((left-2,y-4,right+2,y+n+8),fill=COLORS[highlight_color])
            draw.text((left,y),line[lo-start:hi-start],font=face,fill=BG,anchor="lt")
        y += step
    return y


def render(kind, preset, spec):
    if kind not in KINDS or preset not in {"landscape","square"}:
        raise ValueError("invalid template/preset")
    w,h = (1600,1600) if preset=="square" else (1600,900 if kind=="excerpt" else 1200)
    im=Image.new("RGB",(w,h),BG); d=ImageDraw.Draw(im)
    inset=128 if kind=="excerpt" else 64
    footer_y=h-(164 if kind=="excerpt" else 128)
    # The footer stays separate from the data/excerpt and never covers text.
    d.line((inset,footer_y,w-inset,footer_y),fill="#36424E",width=1)
    label="Next Block News"; label_font=font(34)
    label_w=label_font.getlength(label)
    icon=Image.open(ROOT/"assets/nbn-logo.png").convert("RGBA")
    icon.thumbnail((56,56))
    im.paste(icon,(int(w-inset-label_w-76),footer_y+36),icon)
    d.text((w-inset-label_w,footer_y+46),label,font=label_font,fill=FG,anchor="lt")
    source=spec["source"]
    if normalized(source).casefold() in {"next block news","nbn"}:
        source=""
    credit=" · ".join(part for part in (source,spec["date"]) if part)
    if credit:
        text_block(d,credit,(inset,footer_y+39,850,66),size=32,minimum=26,color=MUTED)
    if kind in {"quote","excerpt"}:
        if kind=="quote":
            d.text((inset,55),"“",font=font(128,True),fill=COLORS[spec["color"]],anchor="lt")
            y=185
            room=footer_y-y-160
            text_block(d,spec["passage"],(inset,y,w-2*inset,room),size=76,minimum=48,
                       spans=spec["highlight_spans"],paragraph_breaks=spec.get("paragraph_breaks",()),highlight_color=spec["color"])
            text_block(d,"— "+spec["speaker"],(inset,footer_y-118,w-2*inset,80),size=40,minimum=34)
        else:
            text_block(d,spec["passage"],(104,96,w-208,footer_y-128),
                       minimum=44,spans=spec["highlight_spans"],paragraph_breaks=spec.get("paragraph_breaks",()),expand=True,highlight_color=spec["color"])
    else:
        y=55
        if spec["eyebrow"]:
            y=text_block(d,spec["eyebrow"].upper(),(inset,y,w-2*inset,60),size=32,minimum=30,color=MUTED)+28
        y=text_block(d,spec["headline"],(inset,y,w-2*inset,235),size=80,minimum=54,bold=True)+24
        if spec["metric"]!="none":
            val=number(spec["metric_value"])
            y=text_block(d,val,(inset,y,w-2*inset,150),size=112,minimum=64,bold=True)+8
        subtitle=spec["unit"]+" · "+spec["period"]
        y=text_block(d,subtitle,(inset,y,w-2*inset,72),size=32,minimum=28,color=MUTED)+35
        if kind=="comparison":
            for i,p in enumerate(spec["points"]):
                x=inset+i*760
                text_block(d,p["label"],(x,y,660,110),size=44,minimum=38,color=MUTED)
                text_block(d,number(p["value"]),(x,y+125,660,220),size=106,minimum=54,bold=True,
                           color=COLORS[spec["color"]] if i else FG)
        else:
            top=y+30; bottom=footer_y-120
            if bottom-top<220:
                raise ValueError("headline/metric leaves too little chart space")
            vals=[p["value"] for p in spec["points"] if p["value"] is not None]
            low=min(0,min(vals)); high=max(0,max(vals))
            if low==high: high=low+1
            pad=(high-low)*.13; lo=low-pad if low<0 else 0; hi=high+pad
            def cy(v): return bottom-(v-lo)/(hi-lo)*(bottom-top)
            left=200; right=w-inset
            for v in (low, (low+high)/2, high):
                yy=cy(v)
                d.line((left,yy,right,yy),fill="#36424E",width=2)
                label=number(v)
                if font(30).getlength(label)>left-50:
                    raise ValueError("axis number too wide; express data in a readable unit")
                d.text((left-25,yy),label,font=font(30),fill=MUTED,anchor="rm")
            d.line((left,cy(0),right,cy(0)),fill=MUTED,width=2)
            step=(right-left)/len(spec["points"]); prev=None
            xs=line_positions(spec,left,right) if kind=="line" else [left+step*(i+.5) for i in range(len(spec["points"]))]
            temporal=kind=="line" and spec.get("x_axis","time")=="time"
            date_labels=[]; value_boxes=[]
            if kind=="line":
                for x,p in zip(xs,spec["points"]):
                    label=p["date"] if temporal else p["label"]
                    box=d.textbbox((x,bottom+28),label,font=font(26),anchor="mt")
                    date_labels.append(box if box[0]>=inset and box[2]<=w-inset else None)
                    v=p["value"]
                    box=(d.textbbox((x,cy(v)-18 if v>=0 else cy(v)+16),number(v),font=font(34),
                                    anchor="mb" if v>=0 else "mt") if v is not None else
                         d.textbbox((x,cy(0)-20),"n/a",font=font(28),anchor="mb"))
                    value_boxes.append(box if box[0]>=inset and box[2]<=w-inset and box[3]<bottom+12 else None)
                visible_dates=distinct_labels(date_labels)
                if not visible_dates:
                    raise ValueError("line axis labels do not fit; use shorter faithful category labels")
                visible_values=distinct_labels(value_boxes)
                d.text((left,bottom+80),"Calendar dates" if temporal else "Equally spaced observations",
                       font=font(24),fill=MUTED,anchor="lt")
            for i,p in enumerate(spec["points"]):
                x=xs[i]; v=p["value"]
                if kind=="line":
                    if i in visible_dates:
                        d.text((x,bottom+28),p["date"] if temporal else p["label"],font=font(26),fill=FG,anchor="mt")
                else:
                    text_block(d,p["label"],(x-step*.45,bottom+28,step*.9,74),size=34,minimum=26)
                if v is None:
                    if kind!="line" or i in visible_values:
                        d.text((x,cy(0)-20),"n/a",font=font(28),fill=MUTED,anchor="mb")
                    prev=None
                    continue
                yy=cy(v)
                if kind=="bar":
                    d.rectangle((x-step*.28,min(yy,cy(0)),x+step*.28,max(yy,cy(0))),
                                fill=COLORS["red"] if v<0 else COLORS[spec["color"]])
                else:
                    if prev: d.line((*prev,x,yy),fill=COLORS[spec["color"]],width=5)
                    d.ellipse((x-7,yy-7,x+7,yy+7),fill=COLORS[spec["color"]]); prev=(x,yy)
                if kind=="line" and i not in visible_values: continue
                if kind!="line" and font(34).getlength(number(v))>step*.95:
                    raise ValueError("data labels overlap; use an appropriate unit or fewer observations")
                d.text((x,yy-18 if v>=0 else yy+16),number(v),font=font(34),fill=FG,
                       anchor="mb" if v>=0 else "mt")
    output=io.BytesIO(); im.save(output,format="PNG",optimize=True)
    return output.getvalue(),(w,h)
