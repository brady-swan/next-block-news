"""Version-fenced owner requests. HTTP only queues; the leased worker reviews/delivers."""
import json
import time

from . import editor, publisher, publisher_visuals, store, visuals


def panel(con,run_id,story_id,members,selected_id=None,review=None):
    reviewed_id=(review or {}).get("asset_id")
    decision=(review or {}).get("verdict") or ("proposed" if selected_id else "none")
    delivery_state=None
    if decision in {"omit","hold"}: selected_id=None
    placeholders=",".join("?" for _ in members)
    rows=con.execute(f"SELECT asset_id FROM visual_assets WHERE run_id=? AND candidate_id IN ({placeholders}) ORDER BY created_at DESC LIMIT 12",
        (run_id,*members)).fetchall() if members else []
    assets=[visuals.manifest(visuals.get(con,r[0])) for r in rows]
    if (selected_id or reviewed_id) and not any(a["asset_id"]==(selected_id or reviewed_id) for a in assets):
        try: assets.insert(0,visuals.manifest(visuals.get(con,selected_id or reviewed_id)))
        except ValueError: pass
    for a in assets:
        a["metadata"]={k:v for k,v in a["metadata"].items() if k not in {"evidence","reuse_evidence"}}
        upload=con.execute("SELECT state,error,media_id,updated_at FROM visual_uploads WHERE asset_id=? ORDER BY updated_at DESC LIMIT 1",(a["asset_id"],)).fetchone()
        a["upload"]=dict(upload) if upload else None
    row=con.execute("SELECT version,asset_id,action,preset,state,updated_at FROM visual_choices WHERE run_id=? AND story_id=?",
        (run_id,story_id)).fetchone()
    request=dict(row) if row else None
    mutation=con.execute("SELECT state,materialization_json FROM publisher_mutations WHERE json_extract(materialization_json,'$.run_id')=?"
        " AND json_extract(materialization_json,'$.story_id')=? AND json_extract(materialization_json,'$.media_payload') IS NOT NULL"
        " ORDER BY created_at DESC LIMIT 1",(run_id,story_id)).fetchone()
    if mutation:
        payload=json.loads(mutation["materialization_json"])
        media=[m for p in payload["media_payload"]["posts"] for m in p["media"]]
        selected_id=media[0]["asset_id"] if media else None
        decision="text_fallback" if payload.get("visual_fallback_reason") else (payload.get("visual_review") or {}).get("verdict","none")
        delivery_state=mutation["state"]
        if request and payload.get("visual_choice_version")==request["version"]:
            request["state"]={"confirmed":"completed","definite_failure":"delivery_failed"}.get(mutation["state"],mutation["state"])
    return {"assets":assets,"selected_asset_id":selected_id,"reviewed_asset_id":reviewed_id,
        "decision":decision,"delivery_state":delivery_state,"request":request,
        "version":row["version"] if row else 0}


def request(con,run_id,story_id,action,asset_id,preset,version):
    if action not in {"select","omit","regenerate"} or preset not in {"landscape","square"}:
        return {"ok":False,"reason":"Invalid visual action/preset"}
    try:
        asset=visuals.get(con,asset_id)
        run=con.execute("SELECT dossier_json FROM newsroom_runs WHERE run_id=?",(run_id,)).fetchone()
        stories=json.loads(run[0]).get("stories",[]) if run else []
        story=next((s for s in stories if s.get("story_id")==story_id),None)
        if not story or asset["candidate_id"] not in story.get("member_candidate_ids",[]):
            raise ValueError("Asset does not belong to this story")
        observation=con.execute("SELECT payload_json FROM run_observations WHERE run_id=? AND kind='editor_input' AND expired=0 ORDER BY id DESC LIMIT 1",(run_id,)).fetchone()
        packet=json.loads(observation[0])["payload"] if observation else {}
        card=next((c for c in packet.get("candidates",[]) if c.get("story_id")==story_id),None)
        if not card: raise ValueError("Retained editorial context is unavailable; send the lead to the newsdesk instead")
        applied=con.execute("SELECT payload_json FROM run_observations WHERE run_id=? AND kind='editor_applied' AND ref=? AND expired=0 ORDER BY id DESC LIMIT 1",(run_id,story_id)).fetchone()
        outcome=json.loads(applied[0]) if applied else {}
        key=outcome.get("canonical_key") or story["story_key"]
        state=store.canonical_output_state(con,key)
        if state["visible"] or len(state["drafts"])>1 or state["protected_mutations"]:
            raise ValueError("Output is published, ambiguous or delivery is pending; no automatic change")
        target=state["drafts"][0] if state["drafts"] else None
        candidate={**card,"post":target["body"] if target else outcome.get("post") or story["post"],
            "inspected_evidence":[r for r in packet.get("evidence_catalog",[]) if r["evidence_ref"] in card["inspected_evidence_refs"]]}
        candidate["inspected_evidence"].extend(outcome.get("additional_evidence") or [])
        final_receipt = outcome.get("reader_receipt")
        current_context = store.accepted_reader_context(con, target["id"]) if target else {}
        if current_context.get("reader_receipt"):
            final_receipt = current_context["reader_receipt"]
        if final_receipt:
            candidate["selected_receipt"] = final_receipt
            candidate["inspected_evidence"] = [final_receipt] + [r for r in candidate["inspected_evidence"]
                if r.get("fetch_id") != final_receipt.get("fetch_id")]
        if target and target["receipt_url"] != candidate["selected_receipt"].get("url"):
            raise ValueError("Current draft source differs from retained context; use the latest run")
        data={"candidate":candidate,"canonical_key":key,"signature":state["signature"],"target":target,
            "members":story["member_candidate_ids"]}
        encoded=visuals.encoded(data)
        if len(encoded.encode())>256*1024: raise ValueError("Visual review context exceeds allowance")
        con.execute("BEGIN IMMEDIATE")
        old=con.execute("SELECT version,state FROM visual_choices WHERE run_id=? AND story_id=?",(run_id,story_id)).fetchone()
        if (old["version"] if old else 0)!=version or old and old["state"] in {"pending","reviewing"}:
            con.rollback(); return {"ok":False,"reason":"Request changed; refresh before trying again"}
        stamp=time.time()
        con.execute("INSERT INTO visual_choices(run_id,story_id,version,asset_id,action,preset,state,created_at,updated_at,payload_json)"
            " VALUES (?,?,?,?,?,?,'pending',?,?,?) ON CONFLICT(run_id,story_id) DO UPDATE SET version=excluded.version,"
            "asset_id=excluded.asset_id,action=excluded.action,preset=excluded.preset,state='pending',updated_at=excluded.updated_at,payload_json=excluded.payload_json",
            (run_id,story_id,version+1,asset_id,action,preset,stamp,stamp,encoded))
        con.execute("UPDATE visual_assets SET retained=1 WHERE asset_id=?",(asset_id,)); con.commit()
        return {"ok":True,"state":"pending","version":version+1}
    except (ValueError,KeyError,TypeError) as exc:
        con.rollback(); return {"ok":False,"reason":str(exc)[:300]}


def process(con):
    # A crash in a review is not permission to repeat a model call or remote mutation.
    con.execute("UPDATE visual_choices SET state='review_interrupted',updated_at=? WHERE state='reviewing'",(time.time(),)); con.commit()
    row=con.execute("SELECT * FROM visual_choices WHERE state='pending' ORDER BY created_at LIMIT 1").fetchone()
    if not row: return
    row=dict(row); data=json.loads(row["payload_json"])
    def finish(state):
        con.execute("UPDATE visual_choices SET state=?,updated_at=? WHERE run_id=? AND story_id=? AND version=?",
            (state[:200],time.time(),row["run_id"],row["story_id"],row["version"])); con.commit()
    finish("reviewing")
    try:
        state=store.canonical_output_state(con,data["canonical_key"])
        if state["signature"]!=data["signature"]: raise ValueError("output_changed")
        asset=visuals.get(con,row["asset_id"])
        if row["action"]=="regenerate":
            m=asset["metadata"]
            if asset["kind"] not in {"quote","excerpt","bar","line","comparison"}: raise ValueError("fixed_template_required")
            asset=visuals.render_asset(con,run_id=row["run_id"],candidate_id=asset["candidate_id"],kind=asset["kind"],preset=row["preset"],
                spec=m["spec"],evidence=m["evidence"],alt_text=m["alt_text"],purpose=m["purpose"],parent=asset["asset_id"])
        candidate=data["candidate"]
        candidate["visual"]={**visuals.manifest(asset),"required":False,
            "reusable":asset["metadata"].get("reuse_status") in {"nbn_original","public_domain","licensed","permission"}}
        candidate["editorial_warnings"]=[*candidate.get("editorial_warnings",[]),
            "Owner visual request: "+row["action"]+". Review this image and copy anew. Omit means approve standalone text, not the image."]
        review=editor.review_newsroom_batch([candidate],con,run_id=f"visual-choice:{row['run_id']}:{row['version']}")
        decision=review.get("decisions",{}).get(row["story_id"],{})
        visual_review=decision.get("visual_review")
        if decision.get("verdict") not in {"publish","revise","draft"} or not visual_review:
            raise ValueError("editor_not_approved")
        expected="omit" if row["action"]=="omit" else "approve"
        if visual_review["verdict"]!=expected: raise ValueError("editor_did_not_approve_requested_visual_change")
        target=data["target"]
        selected = decision.get("reader_receipt") or candidate.get("selected_receipt") or {}
        receipt=selected.get("url")
        post=decision["post"]
        from . import lint
        evidence=candidate["inspected_evidence"]+decision.get("additional_evidence",[])
        source="\n".join(e.get("text","") for e in evidence)
        item=dict(con.execute("SELECT * FROM items WHERE url_hash=?",(data["members"][0],)).fetchone() or {})
        if lint.hard_rails_v2(post,{"_source_text":source},item):
            raise ValueError("editor_copy_failed_mechanical_rails")
        materialization={"run_id":row["run_id"],"story_id":row["story_id"],"item_hash":data["members"][0],
            "members":[{"url_hash":cid,"story_key":data["canonical_key"]} for cid in data["members"]],
            "klass":target["class"] if target else "secondary","body":post,"receipt_url":receipt,
            "editor_note":decision.get("reason",""),"publisher_backend":"typefully","coverage_relation":"same_event" if target else "distinct",
            "visual_choice_version":row["version"]}
        context_ref = f"{row['story_id']}:{row['version']}"
        materialization["reader_context"] = {"run_id": row["run_id"], "ref": context_ref, "kind": "visual_reader_receipt"}
        materialization["resolution_id"] = target.get("resolution_id") if target else None
        if decision.get("reader_receipt"):
            from . import config, source_policy, verify, newsroom
            from dataclasses import replace
            records = [editor.restored_receipt(e) for e in evidence]
            chosen = editor.restored_receipt(selected)
            independent = {r.source.independence_key for r in records if r.independent_report}
            materialization["klass"] = "primary" if chosen.source.official else "corroborated" if len(independent) >= 2 else "secondary"
            original = source_policy.classify(item.get("url", ""), item.get("source", ""))
            resolution = verify.ResolutionResult(item["url_hash"], data["canonical_key"], item.get("source", ""),
                original, chosen.source, source, "selected", True, newsroom._record_originality(chosen),
                chosen.eligible, chosen.independent_report,
                chosen.final_url if chosen.direct_primary else "", chosen.content_fingerprint if chosen.direct_primary else "",
                chosen.content_fingerprint, None, "Editor-selected reader receipt during visual review", tuple(
                    verify.EvidenceCandidate(ref=r.source, originality=newsroom._record_originality(r),
                        supported=True, receipt_eligible=True, corroboration_eligible=r.independent_report,
                        content_fingerprint=r.content_fingerprint) for r in records))
            for cid in data["members"]:
                store.persist_resolution(con, replace(resolution, item_hash=cid), config.SOURCE_POLICY_MODE)
            materialization["resolution_id"] = item["url_hash"]
        from . import observations
        observations.record(con, row["run_id"], "visual_reader_receipt", {"reader_receipt": selected,
            "version": row["version"]}, ref=context_ref, phase="proposed")
        queued=publisher_visuals.queue(con,visual_review=visual_review,desired_thread=publisher.one_off_x_thread(post,receipt),
            prior_thread=publisher.one_off_x_thread(target["body"],target["receipt_url"]) if target else None,
            prior_payload=json.loads(target["media_payload_json"]) if target and target.get("media_payload_json") else None,
            prior_version=json.loads(target["media_remote_version"]) if target and target.get("media_remote_version") else None,
            story_key=data["canonical_key"],operation="replace_draft" if target else "create",intended_mode="DRAFT",
            target_draft_id=str(target["nuelink_id"]) if target else "",target_post_id=target["id"] if target else None,
            expected_output_signature=data["signature"],materialization=materialization)
        if not queued["ok"]: raise ValueError("output_changed")
        finish("delivery_pending")
    except Exception as exc:
        finish("held: "+(str(exc) if isinstance(exc,ValueError) else type(exc).__name__))
