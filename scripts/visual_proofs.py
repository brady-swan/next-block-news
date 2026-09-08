"""Offline illustrative template proofs. Never calls a model or publisher."""
import argparse
from pathlib import Path
from nbn import visual_render


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("directory",type=Path); args=parser.parse_args()
    args.directory.mkdir(parents=True,exist_ok=True)
    text="Bitcoin gives people a way to hold and send money without asking permission. That matters most where access to reliable banking is limited. The technology is global, but the reasons people use it are often local."
    evidence=[{"fetch_id":"illustration","text":text,"retrieval_kind":"direct_fetch"}]
    common={"source":"Illustrative data · not news","date":"September 2026"}
    points=[{"label":d,"value":v,"date":"Illustration","source_fetch_id":"illustration"} for d,v in zip(["Mon","Tue","Wed","Thu","Fri"],[182,-75,246,0,112])]
    specs={"bar":{**common,"headline":"A mixed week for Bitcoin ETF flows","eyebrow":"Bitcoin · ETF flows","unit":"USD millions","period":"Illustrative five-day period","points":points,"metric":"sum"},
        "line":{**common,"headline":"Daily flows moved back into positive territory","unit":"USD millions","period":"Illustrative five-day period","points":points,"metric":"none"},
        "comparison":{**common,"headline":"Before and after the policy change","unit":"Participating institutions","period":"Illustration","metric":"none",
            "points":[{**points[0],"label":"Before","value":24},{**points[1],"label":"After","value":47}]},
        "quote":{**common,"passage":text[:87],"speaker":"Example speaker","source_fetch_id":"illustration","highlights":[]},
        "excerpt":{**common,"passage":text,"source_fetch_id":"illustration","highlights":["without asking permission","the reasons people use it are often local"]}}
    specs["quote"]["passage"]=text.split(". ")[0]+"."
    for kind,spec in specs.items():
        for preset in ("landscape","square"):
            validated=visual_render.validate(kind,spec,evidence)
            data,_=visual_render.render(kind,preset,validated)
            (args.directory/f"{kind}-{preset}.png").write_bytes(data)
    print(args.directory)


if __name__=="__main__": main()
