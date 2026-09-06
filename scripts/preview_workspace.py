"""Loopback-only, disposable UI fixtures. Never starts the worker or calls providers."""
import json
import time
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from nbn import config, main, observations, store
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
    con.execute("INSERT INTO posts(created,story_key,item_hash,class,body,receipt_url,mode,nuelink_id,publisher_backend,publisher_status,publisher_synced_at) VALUES (?,?,?,?,?,?,'DRAFT','12345','typefully','draft',?)",(now-850,"policy-research","lead0","secondary",POST,"https://example.org/report",now));con.commit()
    observations.source_poll(con,"rss:fixture","Fixture feed","rss",count=0)
    store.kv_set(con,"publisher:last_success",str(now-50))
    store.kv_set(con,"editorial:next_run_at",str(now+600))
    main.STATE.update(last_cycle_ts=now-30,last_error="")


if __name__=="__main__":
    with temporary_store() as con, patch.object(config,"REPORT_TOKEN","local-preview"),patch.object(config,"AUTOPOST_ENABLED",False),patch.object(config,"AUDIT_UTC",""):
        populate(con)
        print("Offline UI fixture at http://127.0.0.1:8766/desk?k=local-preview",flush=True)
        ThreadingHTTPServer(("127.0.0.1",8766),main.Health).serve_forever()
