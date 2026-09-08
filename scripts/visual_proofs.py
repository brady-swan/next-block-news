"""Offline illustrative template proofs. Never calls a model or publisher."""
import argparse
from pathlib import Path
from nbn import visual_render


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("directory",type=Path); args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    text="Bitcoin gives people a way to hold and send money without asking permission. That matters most where access to reliable banking is limited. The technology is global, but the reasons people use it are often local."
    evidence=[{"fetch_id":"illustration","text":text,"retrieval_kind":"direct_fetch"}]
    common={"source":"Next Block News","date":"September 2026"}
    points=[{"label":d,"value":v,"date":f"2026-09-{day:02d}","source_fetch_id":"illustration"} for day,(d,v) in enumerate(zip(["Mon","Tue","Wed","Thu","Fri"],[182,-75,246,0,112]),start=7)]
    specs={"bar":{**common,"headline":"A mixed week for Bitcoin ETF flows","eyebrow":"Bitcoin · ETF flows","unit":"USD millions","period":"September 7–11, 2026","points":points,"metric":"sum"},
        "line":{**common,"headline":"Daily flows moved back into positive territory","unit":"USD millions","period":"September 7–11, 2026","points":points,"metric":"none"},
        "comparison":{**common,"headline":"Before and after the policy change","unit":"Participating institutions","period":"September 2026","metric":"none",
            "points":[{**points[0],"label":"Before","value":24},{**points[1],"label":"After","value":47}]},
        "quote":{**common,"passage":text[:87],"speaker":"Next Block News","source_fetch_id":"illustration","highlights":[]},
        "excerpt":{**common,"passage":text,"source_fetch_id":"illustration","highlights":["without asking permission","the reasons people use it are often local"]}}
    specs["quote"]["passage"]=text.split(". ")[0]+"."
    for kind,spec in specs.items():
        for preset in ("landscape","square"):
            validated=visual_render.validate(kind,spec,evidence)
            data,_=visual_render.render(kind,preset,validated)
            (args.directory/f"{kind}-{preset}.png").write_bytes(data)
    irregular={**specs["line"],"date":"January 2026","headline":"Flows changed across an uneven reporting window",
        "period":"December 31, 2025 – January 31, 2026","points":[
            {"label":stamp,"date":stamp,"value":value,"source_fetch_id":"illustration"}
            for stamp,value in [("2025-12-31",100),("2026-01-01",-20),("2026-01-10",None),("2026-01-31",80)]]}
    for preset in ("landscape","square"):
        data,_=visual_render.render("line",preset,visual_render.validate("line",irregular,evidence))
        (args.directory/f"line-irregular-{preset}.png").write_bytes(data)
        for color in visual_render.COLORS:
            spec={**specs["excerpt"],"color":color}
            data,_=visual_render.render("excerpt",preset,visual_render.validate("excerpt",spec,evidence))
            (args.directory/f"excerpt-{color}-{preset}.png").write_bytes(data)
    (args.directory/"README.md").write_text(
        "# Offline renderer fixtures\n\n"
        "These files use synthetic values and internally written passages for design review. "
        "They are not sourced reporting or publication inputs. Next Block News identifies the "
        "fixture creator. Production graphics must credit their actual evidence sources.\n\n"
        "Internal fixture labels are kept in this note rather than rendered into the images, "
        "per the owner's September 8, 2026 direction. The irregular line fixtures include a year "
        "boundary, negative value and missing observation; spacing follows elapsed calendar days. "
        "All six highlight colors are included in both presets.\n",encoding="utf-8")
    print(args.directory)


if __name__=="__main__": main()
