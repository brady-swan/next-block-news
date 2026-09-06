"""Owner-requested historical roster replay; isolated DBs, explicit draft-only export.

Uses current production functions, not the bake-off's simplified editorial contracts.
Live retrieval is not time-frozen, so this is a diagnostic replay, not a causal benchmark.
Run via Railway's environment injection. Never opens or writes the production database.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n")


def run(folder, requested_targets=None, native_first=False):
    # Set filesystem destinations before importing any runtime module.
    os.environ["NBN_DATA_DIR"] = str(folder / "bootstrap")
    os.environ["NBN_AUTOPOST_ENABLED"] = "false"
    from nbn import brain, config, intake_triage, main, models, newsroom, publisher, store
    expected = {"NEWSROOM_MODEL": "grok-4.3", "NEWSROOM_EFFORT": "medium",
                "DESK_PREP_MODEL": "gpt-5.6-luna", "DESK_PREP_EFFORT": "low",
                "RESEARCH_MODEL": "grok-4.3", "RESEARCH_EFFORT": "medium",
                "EDITOR_MODEL": "grok-4.5", "EDITOR_EFFORT": "medium"}
    assert all(getattr(config, k) == v for k, v in expected.items()), "roster mismatch"
    assert not config.AUTOPOST_ENABLED
    tables = json.loads((folder / "source-snapshot.json").read_text())["tables"]
    by_hash = {row["url_hash"]: row for row in tables["items"]}
    targets = requested_targets or ["btc-gold-correlation-surge-sept2026",
               "imf-confirms-el-salvador-btc-private-donations",
               "oklahoma-bitcoin-mining-site-condemned-water-leak"]
    results = []
    for index, key in enumerate(targets, 1):
        case_dir = folder / f"case-{index}"
        if case_dir.exists():
            raise RuntimeError(f"Refusing to replay or overwrite existing {case_dir}")
        case_dir.mkdir()
        prior = next(p for p in tables["posts"] if p["story_key"] == key)
        source_run = max((r for r in tables["newsroom_runs"]
                          if prior["item_hash"] in json.loads(r["inventory_json"])
                          and r["created_at"] < prior["created"]), key=lambda r:r["created_at"])
        as_of = source_run["created_at"]
        config.DATA_DIR = case_dir
        config.DB_PATH = case_dir / "replay.db"
        config.TAPE_DIR = case_dir / "tapes"
        con = store.connect()
        assert str(config.DB_PATH).startswith(str(folder))
        # Seed pre-batch output coverage only. Current memory rows cannot reconstruct
        # historical versions and are deliberately not fed back as old knowledge.
        columns = [r[1] for r in con.execute("PRAGMA table_info(posts)")]
        for old in tables["posts"]:
            if old["created"] >= as_of:
                continue
            fields = [k for k in columns if k in old]
            con.execute(f"INSERT INTO posts ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
                        [old[k] for k in fields])
        con.commit()
        baseline_post_ids = {r[0] for r in con.execute("select id from posts")}
        cards = []
        for h in json.loads(source_run["inventory_json"]):
            raw = by_hash[h]
            cards.append({k: raw.get(k) for k in ("source", "title", "url", "summary",
                         "discovery_origin", "discovery_context", "discovery_candidate_id")})
            cards[-1]["published"] = raw.get("published_at") or ""
        inventory = store.upsert_new_items(con, cards)
        run_id = f"roster-replay-{index}-{int(time.time())}"
        for item in inventory:
            item["_run_id"] = run_id
        save(case_dir / "input.json", {"original_run": source_run, "baseline_post": prior,
             "as_of_utc": datetime.datetime.fromtimestamp(as_of, datetime.timezone.utc).isoformat(),
             "inventory": inventory, "roster": expected,
             "limitations": "Current live retrieval; pre-batch post coverage only; historical workbench/storyline versions unavailable."})
        owner = f"isolated-replay-{index}"
        assert store.acquire_cycle_lease(con, owner, ttl_seconds=1800)
        captured = []
        def capture(post, receipt_url, klass, **kwargs):
            captured.append({"post": post, "receipt_url": receipt_url, "class": klass})
            save(case_dir / "captured.json", captured)
            return "DRAFT", f"isolated-replay-{index}-{len(captured)}"
        def no_replace(*args, **kwargs):
            return "FAILED", "Replay does not modify existing Typefully drafts"
        class ReplayDateTime(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return cls.fromtimestamp(as_of, tz)
        clock = SimpleNamespace(datetime=ReplayDateTime, timezone=datetime.timezone,
                                timedelta=datetime.timedelta)
        original_packet = newsroom.NewsroomSession._initial_packet
        original_create = models.ResponsesClient.create
        trace = []
        def traced_create(client, **kwargs):
            response = original_create(client, **kwargs)
            trace.append({"model": kwargs["model"], "tool_choice":kwargs.get("tool_choice"),
                          "stop_reason":response.stop_reason,
                          "blocks":[vars(b) for b in response.content]})
            save(case_dir / "provider-trace.json", trace)
            return response
        def replay_packet(session):
            packet = original_packet(session)
            if native_first:
                assignment = session._native_research({
                    "candidate_ids":[prior["item_hash"]], "fetch_ids":[],
                    "objective":"Verify this candidate using native web AND X search. Find the original report or primary statement, establish its date and exactly what it supports, and resolve gaps in any repost. Only evidence available by the supplied historical date belongs in this replay."})
                packet["replay_operator_assigned_native_research"] = assignment
                save(case_dir / "native-assignment.json", assignment)
            packet["run_brief"]["assignment"] += (
                " This is a historical diagnostic replay for human review. Judge newsworthiness"
                " as of as_of_utc, not the actual wall clock. Do not treat later-dated research"
                " as known then. Do not put replay labels in the news copy. No quota.")
            save(case_dir / "desk-packet.json", packet)
            return packet
        start = time.monotonic()
        print(json.dumps({"case": index, "status": "running", "candidates": len(inventory),
                          "baseline": key}), flush=True)
        try:
            with patch.object(publisher, "publish", capture), \
                 patch.object(publisher, "replace_draft", no_replace), \
                 patch.object(newsroom, "datetime", clock), \
                 patch.object(models.ResponsesClient, "create", traced_create), \
                 patch.object(newsroom.NewsroomSession, "_initial_packet", replay_packet):
                mailroom = intake_triage.route_cycle(con, inventory, run_id=run_id)
                reservation = mailroom.pop("reservation", None)
                remaining = {r[0] for r in con.execute("select url_hash from items where status='new'")}
                fresh = [i for i in inventory if i["url_hash"] in remaining]
                result = {"fetched": len(inventory), "new": len(inventory),
                          "considered":len(inventory), "pending":len(fresh),
                          **{k:0 for k in ("drafted","held","posted","uncertain","failed","taped","policy_held")},
                          "intake_triage":mailroom}
                if fresh:
                    result = main._run_editorial_v2(con, lease_owner=owner,
                        pipeline_run_id=run_id, inventory=fresh, pending=inventory,
                        result=result, theme_snapshot=[], overrides={},
                        run_started=time.time(), reservation=reservation)
                posts = [dict(r) for r in con.execute("select * from posts") if r["id"] not in baseline_post_ids]
                report = {"case":index, "run_id":run_id, "baseline":prior,
                          "result":result, "duration_seconds":round(time.monotonic()-start,2),
                          "posts":posts, "captured":captured,
                          "usage":[dict(r) for r in con.execute("select * from model_usage")],
                          "items":[dict(r) for r in con.execute("select * from items")],
                          "commits":[dict(r) for r in con.execute("select * from newsroom_story_commits")],
                          "dossiers":[dict(r) for r in con.execute("select * from newsroom_runs")],
                          "preparations":[dict(r) for r in con.execute("select * from desk_preparations")]}
                save(case_dir / "result.json", report)
                results.append(report)
                save(folder / "results.json", results)
                print(json.dumps({"case":index, "status":"complete", "result":result,
                     "cost_usd":sum(r["estimated_cost_usd"] or 0 for r in report["usage"])}),flush=True)
        finally:
            brain.release_active_model_reservation()
            store.release_cycle_lease(con, owner)
            con.close()


def stage(folder):
    os.environ["NBN_AUTOPOST_ENABLED"] = "false"
    os.environ["NBN_DATA_DIR"] = str(folder / "bootstrap")
    import httpx
    from nbn import config, publisher_typefully as tf
    assert not config.AUTOPOST_ENABLED
    rows = json.loads((folder / "results.json").read_text())
    manifest_path = folder / "typefully-export.json"
    if manifest_path.exists():
        raise RuntimeError("Export already attempted; inspect manifest, do not blindly retry")
    manifest = []
    for case in rows:
        export_posts = list(case["posts"])
        # A legitimate in-place revision is captured as a NEW review-only copy. Never
        # PATCH its live predecessor or change the recorded replay delivery outcome.
        for commit in case["commits"]:
            details = json.loads(commit["details_json"])
            if "Replay does not modify existing Typefully drafts" not in details.get("reason", ""):
                continue
            story = next(s for d in case["dossiers"] for s in
                         json.loads(d["dossier_json"])["stories"] if s["story_id"] == commit["story_id"])
            case_dir = folder / f"case-{case['case']}"
            trace = json.loads((case_dir / "provider-trace.json").read_text())
            decision = next(d for call in reversed(trace) if call["model"] == "grok-4.5"
                            for b in call["blocks"] if b["type"] == "text"
                            for d in json.loads(b["text"])["decisions"]
                            if d["story_id"] == commit["story_id"] and d["verdict"] in {"publish","revise","draft"})
            packet = json.loads((case_dir / "desk-packet.json").read_text())
            receipt = next(r["final_url"] for r in packet["prepared_evidence"]
                           if r["fetch_id"] == story["selected_fetch_id"])
            export_posts.append({"mode":"DRAFT", "nuelink_id":"isolated-replay-replacement-preview",
                "body":decision["post"], "receipt_url":receipt, "story_key":story["story_key"],
                "review_only_replacement_preview":True})
        for post in export_posts:
            if post["mode"] != "DRAFT" or not str(post["nuelink_id"]).startswith("isolated-replay-"):
                continue
            texts = [post["body"], f"Source: {post['receipt_url']}"]
            entry = {"case":case["case"], "story_key":post["story_key"], "texts":texts,
                     "state":"in_flight", "draft_id":None,
                     "review_only_replacement_preview":post.get("review_only_replacement_preview",False),
                     "draft_title":f"REPLAY {folder.name} | {post['story_key']}"[:120]}
            manifest.append(entry)
            save(manifest_path, manifest)  # Durable intent before every POST; no retries.
            try:
                response = httpx.post(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
                    headers=tf._headers(), json={"draft_title":entry["draft_title"],
                        "platforms":{"x":{"enabled":True,"posts":[{"text":t} for t in texts]}}}, timeout=30)
                response.raise_for_status()
                entry["draft_id"] = str(response.json().get("id") or "")
                save(manifest_path, manifest)
                if not entry["draft_id"]:
                    raise RuntimeError("accepted create without id")
                actual = tf.get_draft(entry["draft_id"])
                assert actual.get("status") == "draft", "unexpected scheduling state"
                assert tf.draft_x_texts(actual) == texts, "content mismatch"
                assert actual.get("draft_title") == entry["draft_title"], "replay label mismatch"
                entry.update(state="confirmed_draft",created_at=actual.get("created_at"))
                save(manifest_path, manifest)
                print(json.dumps({k:entry[k] for k in ("case","state","draft_id","draft_title")}),flush=True)
            except Exception:
                entry["state"] = "uncertain_do_not_retry"
                save(manifest_path, manifest)
                raise
    save(manifest_path, manifest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["run","stage"])
    parser.add_argument("--folder", required=True)
    parser.add_argument("--target", action="append", help="Exact historical story key; max three batches")
    parser.add_argument("--native-first", action="store_true", help="Separate controlled research-assisted replay")
    args = parser.parse_args()
    folder = Path(args.folder).resolve()
    assert folder.is_relative_to(ROOT / ".model-eval"), "isolated artifact directory required"
    if args.mode == "run":
        assert not args.target or len(args.target) <= 3
        run(folder, args.target, args.native_first)
    else:
        stage(folder)
