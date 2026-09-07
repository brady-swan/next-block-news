"""Paid, isolated reporter-writer diagnostic. Never imports publisher or writes Typefully.

Use `railway run --no-local python3.12 scripts/smoke_reporter_writer.py` with the
owner's existing keys. A reconstructed Lummis case tests source following; a seeded
first-party fixture checks that sufficient evidence does not require another search.
Live retrieval is not a frozen historical benchmark. No results enter production memory.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["lummis", "sufficient"], required=True)
    parser.add_argument("--baseline-root", default="")
    args = parser.parse_args()
    root = Path(args.baseline_root) if args.baseline_root else Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    with tempfile.TemporaryDirectory(prefix="nbn-reporter-smoke-") as folder:
        os.environ["NBN_DATA_DIR"] = folder
        os.environ["NBN_AUTOPOST_ENABLED"] = "false"
        from nbn import brain, config, editor, models, newsroom, source_policy, store
        assert Path(config.DB_PATH).is_relative_to(folder)
        config.NEWSROOM_MODEL, config.NEWSROOM_EFFORT = "grok-4.3", "medium"
        config.EDITOR_MODEL, config.EDITOR_EFFORT = "grok-4.5", "medium"
        config.RUN_NEWSROOM_MAX_ROUNDS = 3 if args.baseline_root else 6
        config.RUN_NEWSROOM_TIMEOUT_SECONDS = 240 if args.baseline_root else 360
        config.MAX_LLM_CALLS_PER_HOUR = 60
        con = store.connect()
        rid = "reporter-replay-" + args.case + "-" + str(int(time.time()))
        url = "https://x.com/TheBlockCo/status/2096779780456927469"
        title = 'Sen. Cynthia Lummis warns next real opportunity for crypto market structure legislation is 2030 if CLARITY fails this Congress.'
        if args.case == "sufficient":
            url, title = "https://www.btcpolicy.org/test-fixture", "BPI publishes a new study of Bitcoin adoption"
        inventory = store.upsert_new_items(con, [{"url": url, "source": "The Block" if args.case == "lummis" else "Bitcoin Policy Institute",
            "title": title, "summary": "", "published": "2026-09-06T23:50:00Z", "discovery_origin": "x"}])
        if args.case == "lummis":
            original = store.upsert_new_items(con, [{"url": "https://x.com/SenLummis/status/2096644344795246746",
                "source": "X @SenLummis", "title": "If we fail to pass CLARITY this Congress, the next real opportunity for market structure legislation is 2030.",
                "summary": "That's years of jobs, investment, and tax revenue we can avoid squandering if we finish this now.",
                "published": "2026-09-06T16:59:00Z"}])[0]
            con.execute("UPDATE items SET status='skipped',note='advocacy' WHERE url_hash=?", (original["url_hash"],))
            con.commit()
        store.start_newsroom_run(con, rid, "shadow", config.NEWSROOM_MODEL, newsroom.PROMPT_VERSION,
                                 [r["url_hash"] for r in inventory])
        token = brain.reserve_model_calls(12)
        if not token:
            raise RuntimeError("No test call reservation")
        desk = newsroom.NewsroomSession(run_id=rid, inventory=inventory, recent_clusters=[], theme_snapshot=[],
            handles={}, con=con, reservation=token, prep_mode="off", research_mode="on", compact_enabled=True)
        initial = desk._initial_packet
        def packet():
            p = initial()
            p["run_brief"]["as_of_utc"] = "2026-09-07T02:13:00Z"
            p["diagnostic_context"] = "Read-only historical diagnostic, no publishing tools. Judge as of the run brief. Live retrieval may contain later information."
            if args.case == "sufficient":
                p["diagnostic_context"] += " For this synthetic sufficient-evidence case, treat the supplied receipt as stipulated ground truth inside the hypothetical, and write if worthwhile. Never export this test."
            return p
        desk._initial_packet = packet
        if args.case == "sufficient":
            text = "Synthetic test receipt: BPI released original research today on Bitcoin use under capital controls. Interviewees in Iran, Turkey and Lebanon described using Bitcoin to protect savings from currency collapse and banking failures. The report distinguishes grassroots savings from Gulf states' regulated digital-asset markets. These are qualitative findings, not a quantified causal claim."
            record = newsroom.FetchRecord("fixture-bpi", url, url, url, (url,), source_policy.classify(url, "Bitcoin Policy Institute"),
                "Bitcoin Policy Institute", text, source_policy.content_fingerprint(text), "ok", adapter_provenance="desk_prefetch")
            desk.fetches[record.fetch_id] = record
            desk.fetch_by_url[url] = record.fetch_id
        original_create = models.ResponsesClient.create
        def budgeted(client, **kwargs):
            paid = con.execute("SELECT COALESCE(SUM(estimated_cost_usd),0) FROM model_usage").fetchone()[0]
            if paid >= 1.50:
                raise RuntimeError("Isolated smoke budget reached")
            response = original_create(client, **kwargs)
            if kwargs.get("model") == "grok-4.3":
                print(json.dumps({"protocol_trace": [{"tool": b.name, "native_sources": b.input.get("native_sources"),
                    "selected": [s.get("selected_fetch_id") for s in b.input.get("stories", [])]}
                    for b in response.content if b.type == "tool_use"],
                    "native_output_types": [r.get("type") for r in response.raw_output]}, default=str), flush=True)
            return response
        models.ResponsesClient.create = budgeted
        started = time.monotonic()
        try:
            outcome = desk.conduct_v2()
            editor_cards = []
            for cid, draft in outcome.drafts.items():
                selected = outcome.fetches.get(draft.get("selected_fetch_id"))
                if not selected:
                    continue
                editor_cards.append({"story_id": outcome.story_ids[cid], "post": draft["post"],
                    "reader_value": draft.get("reader_value", ""), "elevated_claim": draft.get("needs_second_source", False),
                    "selected_receipt": {"fetch_id": selected.fetch_id, "url": selected.final_url,
                        "source": selected.source.display_name, "evidence_capability": selected.evidence_capability},
                    "inspected_evidence": [{**desk._fetch_payload(outcome.fetches[fid], cached=True),
                        "url": outcome.fetches[fid].final_url} for fid in draft.get("evidence_fetch_ids", []) if fid in outcome.fetches]})
            edited = editor.review_newsroom_batch(editor_cards, con, run_id=rid, reservation=token) if editor_cards else None
            print(json.dumps({"case": args.case, "baseline": bool(args.baseline_root), "dossier": outcome.dossier,
                "receipts": [desk._fetch_payload(r, cached=True) for r in outcome.fetches.values()],
                "verdicts": [{k: v.get(k) for k in ("action", "reason", "story_key")} for v in outcome.verdicts],
                "editor": edited, "counters": outcome.counters}, default=str), flush=True)
        finally:
            brain.release_model_reservation(token)
            print(json.dumps({"case": args.case, "seconds": round(time.monotonic()-started, 2),
                "usage": [dict(r) for r in con.execute("SELECT seat,model,estimated_cost_usd,cost_source,native_web_calls,native_x_calls FROM model_usage")],
                "tools": [json.loads(r[0]) for r in con.execute("SELECT payload_json FROM run_observations WHERE kind='tool' AND phase='completed'")],
                "feedback": [json.loads(r[0]) for r in con.execute("SELECT payload_json FROM run_observations WHERE kind='writer_feedback'")]}, default=str), flush=True)
            con.close()


if __name__ == "__main__":
    main()
