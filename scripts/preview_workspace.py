"""Loopback-only, disposable UI fixtures. Never starts the worker or calls providers."""
import json
import os
import time
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from nbn import config, main, observations, store, writer_continuity
from tests.support import temporary_store
from tests.test_workspace import seed_run, seed_usage

POST = ("Bitcoin Policy Institute’s new report follows how people use Bitcoin when their local financial system stops working.\n\n"
        "It examines savings, cross-border payments and access to money across four countries.\n\n"
        "The distinction matters: individual adoption and a government’s crypto strategy are different stories.")
TITLES = ["How Bitcoin is being used beyond state-led crypto strategies", "Bitcoin’s mempool becomes a live musical instrument", "Can lenders reuse mortgage borrowers’ Bitcoin?", "New exchange product lacks a meaningful Bitcoin development", "Bitcoin mining chart fails to load; fresh confirmation still needed"]


def populate(con):
    now=time.time()
    for i,title in enumerate(TITLES):
        con.execute("INSERT INTO items(url_hash,title,source,url,first_seen,status,note) VALUES (?,?,?,?,?,'held',?)",
                    (f"lead{i}",title,["Bitcoin Policy Institute","@BitcoinArchive","CoinDesk","RSS wire","@BitcoinNewsCom"][i],"https://example.org/fixture",now-i*150,"Offline UI fixture, not production news."))
    con.commit()
    ids=["lead0","lead1","lead2","lead3","lead4"]
    for idx,age in enumerate((86420,1800,900)):
        rid=f"cycle:fixture-{idx}";at=now-age
        stories=[{"story_id":"story-bpi","member_candidate_ids":["lead0"],"post":POST,"story_key":"policy-research","reader_value":"A concrete Bitcoin adoption finding.","evidence_fetch_ids":["fetch:one"]},
                 {"story_id":"story-mortgage","member_candidate_ids":["lead2"],"post":"A proposed lending product lets customers pledge Bitcoin.","story_key":"mortgage","reader_value":"A material custody distinction."}]
        dossier={"run_note":"Offline QA fixture · two proposals, one delivery and one editor rejection. The remaining leads were deferred or dropped.","stories":stories if idx!=0 else [],"decisions":[{"candidate_id":"lead1","disposition":"drop","reason":"Interesting project, but not a new development today."},{"candidate_id":"lead4","disposition":"defer","reason":"Dynamic chart was unavailable; retain the lead for another source."}]}
        seed_run(con,rid,at,inventory=ids,dossier=dossier)
        if idx:
            packet={"run_brief":{"run_id":rid,"assignment":"Offline QA fixture. Not a production model call."},"intake_board":[{"candidate_id":h,"headline_or_post":TITLES[i],"source":{"label":["Bitcoin Policy Institute","@BitcoinArchive","CoinDesk","RSS wire","@BitcoinNewsCom"][i]},"intake_url":"https://example.org/fixture","what_arrived":"A relevant lead with useful context."} for i,h in enumerate(ids) if i!=3],"prepared_evidence":[{"fetch_id":"fetch:one","source_name":"Bitcoin Policy Institute","final_url":"https://example.org/report","text":"Offline source excerpt for layout verification. This source-specific capture is not a production receipt.","text_truncated":False}],"recent_reader_feed_48h":[{"body":"A prior post supplies duplicate context."}]}
            observations.record(con,rid,"writer_input",{"packet":packet},phase="delivered")
            observations.record(con,rid,"tool",{"tool":"research_story","arguments":{"candidate_ids":["lead0"],"objective":"Identify the genuinely new Bitcoin findings."},"returned":{"memo_untrusted_not_evidence":{"summary":"The report distinguishes household use from government financial strategy.","uncertainties":"Publication date needs a current source."},"inspected_evidence":[{"source_name":"Research publication","url":"https://example.org/report","retrieval_kind":"provider_reported_extract","source_summary":"A source-specific paraphrase retained for review."}]}},phase="completed")
            observations.record(con,rid,"editor_applied",{"verdict":"revise","reason":"Lead with the Bitcoin finding, remove broad regional framing, and use simpler sentences.","post":POST,"origin":"initial","canonical_key":"policy-research"},ref="story-bpi",phase="applied")
            observations.record(con,rid,"editor_applied",{"verdict":"drop","reason":"The custody claim is not supported by the retained terms. This is an actual editorial rejection, not a missing response.","origin":"initial"},ref="story-mortgage",phase="applied")
            store.save_desk_preparations(con,[{"run_id":rid,"item_hash":"lead3","effective_route":"background","event_summary":"Broad product announcement, no Bitcoin change."}],mode="enforce")
        con.execute("INSERT INTO newsroom_story_commits(run_id,story_id,state,dossier_digest,details_json,updated_at) VALUES (?,'story-bpi','delivered','fixture','{}',?)",(rid,at+15));con.commit()
        seed_usage(con,rid,at+10,.06);seed_usage(con,rid,at+11,.014,"editor")
        if idx:
            writer_continuity.save_letter(con,rid,"Lead with individual Bitcoin use, not broad government crypto strategy. The mining chart is still unavailable; check the original dataset before calling it a fresh record.",model="offline fixture",prompt_version="editorial-core-v2.35-writer-continuity")
    store.save_newsroom_story_attempt(con,"mining-watch","research_pending",{"objective":"Has the original dataset confirmed a new record?"})
    writer_continuity.apply_updates(con,"cycle:fixture-2",[{"followup_id":None,"base_revision":None,"context_id":"notebook:mining-watch","question":"Has the original dataset confirmed a new record?","source_paths":["https://example.org/data"],"next_check_minutes":60,"state":"open","result":"pending","note":"Offline UI fixture."}],allowed_contexts={"notebook:mining-watch"},inventory=[])
    store.set_status(con, "lead3", "skipped", "fixture-product", "Broad product announcement, no Bitcoin change.", stage="desk_prep", category="background")
    con.execute("INSERT INTO posts(created,story_key,item_hash,class,body,receipt_url,mode,nuelink_id,publisher_backend,publisher_status,publisher_synced_at) VALUES (?,?,?,?,?,?,'DRAFT','12345','typefully','draft',?)",(now-850,"policy-research","lead0","secondary",POST,"https://example.org/report",now));con.commit()
    observations.source_poll(con,"rss:fixture","Fixture feed","rss",count=0)
    store.kv_set(con,"publisher:last_success",str(now-50))
    store.kv_set(con,"editorial:next_run_at",str(now+600))
    main.STATE.update(last_cycle_ts=now-30,last_error="")
    if os.environ.get("NBN_VISUAL_QA") == "1":
        from nbn import visuals
        rid="cycle:fixture-2"
        text="Bitcoin gives people a way to hold and send money without asking permission. That matters most where access to reliable banking is limited."
        evidence=[{"fetch_id":"fetch:one","text":text,"retrieval_kind":"direct_fetch","final_url":"https://example.org/report"}]
        common={"source":"Offline QA · not news","date":"September 2026"}
        points=[{"label":d,"value":v,"date":"Illustration","source_fetch_id":"fetch:one"} for d,v in zip(["Mon","Tue","Wed","Thu","Fri"],[182,-75,246,0,112])]
        specs={"quote":{**common,"passage":text.split(". ")[0]+".","speaker":"Example speaker","source_fetch_id":"fetch:one"},
            "excerpt":{**common,"passage":text,"source_fetch_id":"fetch:one","highlights":["without asking permission"]},
            "bar":{**common,"headline":"A mixed week for Bitcoin ETF flows","unit":"USD millions","period":"Illustrative week","points":points,"metric":"sum"},
            "line":{**common,"headline":"Daily flows turned positive","unit":"USD millions","period":"Illustrative week","points":points,"metric":"none"},
            "comparison":{**common,"headline":"Before and after","unit":"Institutions","period":"Illustrative","points":[{**points[0],"label":"Before","value":24},{**points[1],"label":"After","value":47}],"metric":"none"}}
        first=None
        for kind,spec in specs.items():
            a=visuals.render_asset(con,run_id=rid,candidate_id="lead0",kind=kind,preset="landscape",
                spec=spec,evidence=evidence,alt_text="Offline illustrative "+kind+" proof. Not news.",purpose="Verify actual stored image previews and spacing.")
            first=first or a
        dossier=json.loads(con.execute("SELECT dossier_json FROM newsroom_runs WHERE run_id=?",(rid,)).fetchone()[0])
        dossier["stories"][0]["visual_asset_id"]=first["asset_id"]
        con.execute("UPDATE newsroom_runs SET dossier_json=? WHERE run_id=?",(json.dumps(dossier),rid));con.commit()
        observations.record(con,rid,"editor_input",{"payload":{"candidates":[{"story_id":"story-bpi","post":POST,
            "selected_receipt":{"url":"https://example.org/report"},"inspected_evidence_refs":[]}],"evidence_catalog":[]}})


if __name__=="__main__":
    with temporary_store() as con, patch.object(config,"REPORT_TOKEN","local-preview"),patch.object(config,"AUTOPOST_ENABLED",False),patch.object(config,"AUDIT_UTC",""),patch.object(config,"RUN_NEWSROOM_MODE","live"),patch.object(config,"EDITORIAL_ENGINE","v2"):
        populate(con)
        print("Offline UI fixture at http://127.0.0.1:8766/desk?k=local-preview",flush=True)
        ThreadingHTTPServer(("127.0.0.1",8766),main.Health).serve_forever()
