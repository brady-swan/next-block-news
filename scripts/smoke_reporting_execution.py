"""Isolated paid Plan0068 replay. No publisher calls, no native search, no production DB.

Uses the existing eval reservation ledger, hard $2 aggregate across restarts. Receipts are
frozen historical fixtures, never live coverage. The chart case deliberately requests a
visual to exercise the tool path; it cannot demonstrate organic editorial adoption.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--only", choices=["all", "saved-visual-editor"], default="all")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    args.data_dir = args.data_dir.resolve()
    if not args.data_dir.name.startswith("nbn-0068-replay-") or str(args.data_dir).startswith("/data"):
        raise ValueError("Use a dedicated mktemp directory named nbn-0068-replay-*")
    os.environ["NBN_DATA_DIR"] = str(args.data_dir)
    os.environ["NBN_AUTOPOST_ENABLED"] = "false"
    from nbn import brain, config, editor, models, newsroom, source_policy, store
    from nbn.eval.budget import BudgetLedger, conservative_reservation
    assert Path(config.DB_PATH).is_relative_to(args.data_dir)
    config.NEWSROOM_MODEL, config.NEWSROOM_EFFORT = "grok-4.3", "medium"
    config.EDITOR_MODEL, config.EDITOR_EFFORT = "grok-4.5", "medium"
    config.MAX_LLM_CALLS_PER_HOUR = 60
    ledger = BudgetLedger(args.data_dir / "budget.sqlite", cap_usd=2.0)
    con = store.connect()
    cases = json.loads(args.input.read_text())
    original_create = models.ResponsesClient.create
    case_id = ""

    def budgeted(client, **kwargs):
        nonlocal case_id
        if kwargs["model"] not in {"grok-4.3", "grok-4.5"}:
            raise ValueError("Unapproved replay model")
        kwargs["native_tools"] = False  # Frozen receipts; not a live research benchmark.
        # Images are conservatively reserved separately, not counted as base64 text tokens.
        def sizing(value):
            if isinstance(value, dict):
                if value.get("type") == "image":
                    return "i" * 32768  # 16,384 token allowance per bounded 1280px image.
                return {k: sizing(v) for k, v in value.items()}
            if isinstance(value, list):
                return [sizing(v) for v in value]
            return value
        amount = conservative_reservation(model=kwargs["model"],
            input_bytes=len(json.dumps(sizing(kwargs), ensure_ascii=False).encode()) * 2,
            max_output_tokens=kwargs["max_tokens"])
        reservation = ledger.reserve(lane="reporting-execution", condition=kwargs["model"],
            case_id=case_id, kind="model", amount_usd=amount)
        try:
            result = original_create(client, **kwargs)
            ticks = getattr(result.usage, "cost_in_usd_ticks", None)
            actual = ticks / 1e10 if isinstance(ticks, (int, float)) else None
            ledger.settle(reservation.request_id, actual_usd=actual, provider_usage={"cost_in_usd_ticks": ticks})
            print(json.dumps({"case": case_id, "model": kwargs["model"], "cost_usd": actual,
                "cap_charged_usd": ledger.charged(), "stop": result.stop_reason}), flush=True)
            return result
        except Exception:
            ledger.fail(reservation.request_id)
            raise
    models.ResponsesClient.create = budgeted
    token = brain.reserve_model_calls(16)
    if not token:
        raise RuntimeError("No test call reservation")
    try:
        if args.only == "saved-visual-editor":
            saved = con.execute("SELECT payload_json FROM run_observations WHERE run_id=? AND kind='editor_input' ORDER BY id DESC LIMIT 1",
                ("canaan-original-chart-tool-exercise",)).fetchone()
            if not saved:
                raise ValueError("Run the original chart case first; preserve the same budget ledger")
            fixture = json.loads(saved[0])["payload"]
            cards = [{**c, "inspected_evidence": [e for e in fixture["evidence_catalog"]
                        if e["evidence_ref"] in c["inspected_evidence_refs"]]} for c in fixture["candidates"]]
            case_id = "canaan-saved-visual-editor-" + str(int(time.time()))
            result = editor.review_newsroom_batch(cards, con, run_id=case_id, reservation=token)
            print(json.dumps({"case": case_id, "result": result}, ensure_ascii=False), flush=True)
            return
        for fixture in cases["editors"]:
            case_id = "editor-" + str(fixture["observation_id"])
            cards = [{**c, "inspected_evidence": [e for e in fixture["evidence_catalog"]
                        if e["evidence_ref"] in c["inspected_evidence_refs"]]} for c in fixture["candidates"]]
            result = editor.review_newsroom_batch(cards, con, run_id=case_id, reservation=token,
                research=fixture.get("unassigned_run_research", {}).get("receipts", []))
            print(json.dumps({"case": case_id, "result": result}, ensure_ascii=False), flush=True)
        case_id = "clarity-identity-correction"
        dossier = cases["clarity"]["dossier"]
        s = dossier["stories"][0]
        raw = cases["clarity"]["receipt"]
        row = {"url_hash": s["member_candidate_ids"][0], "title": "Senate Republicans say crypto bill likely to fail",
            "url": raw["final_url"], "source": "Semafor", "published": "2026-09-08", "summary": ""}
        desk = newsroom.NewsroomSession(run_id=case_id, inventory=[row], recent_clusters=[],
            theme_snapshot=[], handles={}, con=con, reservation=token, prep_mode="off", research_mode="on")
        record = newsroom.FetchRecord(raw["fetch_id"], raw["requested_url"], raw["final_url"], raw["canonical_url"],
            tuple(raw["redirect_chain"]), source_policy.classify(raw["final_url"], raw["source_name"]),
            raw["byline"], raw["text"], raw["content_fingerprint"], "ok", published_at=raw["published_at"])
        desk.fetches[record.fetch_id] = record
        # Retain the exact reported draft and useful receipt; ask only for its identity repair.
        s["selected_fetch_id"] = record.fetch_id; s["evidence_fetch_ids"] = [record.fetch_id]
        desk.messages = [{"role": "user", "content": json.dumps({"diagnostic": "Frozen historical Plan0068 test; no publication. Correct identity only using supplied evidence.",
            "packet": desk._initial_packet(), "previous_dossier": dossier,
            "code_corrections": desk._identity_repairs(dossier), "receipt": desk._fetch_payload(record, cached=True)})}]
        response = desk._call(max_tokens=5000, tools=[newsroom.V2_DOSSIER_TOOL],
            tool_choice={"type": "tool", "name": "submit_editorial_dossier"})
        submitted = next(b.input for b in response.content if b.type == "tool_use" and b.name == "submit_editorial_dossier")
        out = desk._validate_and_convert_v2(submitted, persist=False)
        print(json.dumps({"case": case_id, "dossier": out.dossier,
            "remaining_identity_errors": desk._identity_repairs(out.dossier)}, ensure_ascii=False), flush=True)

        case_id = "canaan-original-chart-tool-exercise"
        raw = cases["chart"]
        rows = store.upsert_new_items(con, [{"url": raw["url"], "source": "Canaan", "title": "Canaan Q2 results: revenue and hardware sales decline",
            "published": "2026-09-08T10:30:00Z", "summary": "Frozen historical visual-tool test."}])
        desk = newsroom.NewsroomSession(run_id=case_id, inventory=rows, recent_clusters=[],
            theme_snapshot=[], handles={}, con=con, reservation=token, prep_mode="off", research_mode="on")
        record = newsroom.FetchRecord("fixture-canaan", raw["url"], raw["url"], raw["url"], (raw["url"],),
            source_policy.classify(raw["url"], "Canaan"), "Canaan", raw["text"], source_policy.content_fingerprint(raw["text"]),
            "ok", adapter_provenance="desk_prefetch", published_at="2026-09-08T10:30:00Z")
        desk.fetches[record.fetch_id] = record
        packet = desk._initial_packet
        def initial():
            p = packet()
            p["diagnostic_receipt"] = desk._fetch_payload(record, cached=True)
            p["diagnostic"] = "Frozen historical tool exercise, not current news. Use the supplied Canaan release to make one original bar chart comparing comparable Q2 revenue, inspect it, then submit concise copy and the visual. This deliberate chart request tests execution, NOT organic editorial selection. No external fetch/search. Never export this replay."
            return p
        desk._initial_packet = initial
        dispatch = desk._dispatch
        def local_only(block):
            if block.name not in {"render_visual", "list_visuals", "inspect_visual", "read_desk_context"}:
                return desk._tool_result(block.id, {"ok": False, "kind": "frozen_replay", "message": "Use supplied retained evidence."}, error=True)
            if block.name == "inspect_visual" and not str(block.input.get("visual_id", "")).startswith("visual_"):
                return desk._tool_result(block.id, {"ok": False, "kind": "frozen_replay"}, error=True)
            return dispatch(block)
        desk._dispatch = local_only
        store.start_newsroom_run(con, case_id, "shadow", config.NEWSROOM_MODEL, newsroom.PROMPT_VERSION, [r["url_hash"] for r in rows])
        out = desk.conduct_v2()
        cards = [{"story_id": out.story_ids[cid], "post": d["post"], "reader_value": d.get("reader_value"),
            "visual": d.get("visual"), "selected_receipt": {"fetch_id": d["selected_fetch_id"]},
            "inspected_evidence": [editor.receipt_card(out.fetches[f]) for f in d["evidence_fetch_ids"]]}
            for cid, d in out.drafts.items()]
        edited = editor.review_newsroom_batch(cards, con, run_id=case_id, reservation=token) if cards else None
        print(json.dumps({"case": case_id, "dossier": out.dossier, "editor": edited,
            "assets": [dict(r) for r in con.execute("SELECT asset_id,kind,content_hash FROM visual_assets WHERE run_id=?", (case_id,))]}, ensure_ascii=False), flush=True)
    finally:
        brain.release_model_reservation(token)
        print(json.dumps({"budget": ledger.summary(), "output_directory": str(args.data_dir)}), flush=True)
        con.close(); ledger.close()


if __name__ == "__main__":
    main()
