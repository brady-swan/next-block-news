"""Resumable media preparation inside the existing publisher mutation lifecycle.

No new editorial decisions: only an exact, independently approved payload can enter here.
Uploads may resume; ambiguous draft POST/PATCH never retries automatically.
"""
import datetime
import json
import time

import httpx

from . import config, publisher_typefully as tf, store, visuals, x_payload

UPLOAD_TIMEOUT = 15*60


def media_get(media_id):
    resp=httpx.get(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/media/{media_id}",
        headers=tf._headers(),timeout=10)
    resp.raise_for_status()
    return resp.json()


def update_intent(con,row,data,*,state=None):
    encoded=visuals.encoded(data)
    if len(encoded.encode())>64*1024: raise ValueError("visual materialization too large")
    payload=data.get("media_payload")
    fingerprint=x_payload.fingerprint(payload) if payload else row["desired_fingerprint"]
    cur=con.execute("UPDATE publisher_mutations SET materialization_json=?,desired_fingerprint=?,"
        "state=?,version=version+1,updated_at=? WHERE mutation_id=? AND owner_token=? AND version=?",
        (encoded,fingerprint,state or row["state"],time.time(),row["mutation_id"],row["owner_token"],row["version"]))
    con.commit()
    if cur.rowcount!=1: raise ValueError("visual intent ownership changed")
    return dict(store.publisher_mutation(con,row["mutation_id"]))


def queue(con, *, visual_review, desired_thread, prior_payload=None, prior_version=None, **kwargs):
    if visual_review is None:
        # Once a draft has a versioned identity, retain that identity after an image
        # was omitted. Later ordinary text revisions must not leave a stale snapshot.
        if not prior_payload or any(p["media"] for p in prior_payload["posts"]):
            raise ValueError("image removal requires editor approval")
        asset = None
    else:
        asset = _approved_asset(con, visual_review, kwargs["materialization"]["body"])
    data=dict(kwargs.pop("materialization"),visual_review=visual_review,
        media_payload=x_payload.build(desired_thread,asset if visual_review and visual_review["verdict"]=="approve" else None),prior_media_payload=prior_payload,
        prior_media_version=prior_version)
    prepared=store.prepare_publisher_mutation(con,desired_thread=desired_thread,materialization=data,**kwargs)
    if not prepared["ok"]: return prepared
    row=dict(store.publisher_mutation(con,prepared["mutation_id"]))
    row=update_intent(con,row,data,state="awaiting_media")
    if asset:
        con.execute("UPDATE visual_assets SET retained=1 WHERE asset_id=?",(asset["asset_id"],)); con.commit()
    return {"ok":True,"mutation_id":row["mutation_id"]}


def _approved_asset(con, visual_review, body):
    asset=visuals.get(con,visual_review["asset_id"])
    if (visual_review.get("verdict") not in {"approve","omit"} or asset["content_hash"]!=visual_review.get("content_hash")
            or visual_review.get("post_hash")!=visuals.digest(body)):
        raise ValueError("visual approval does not bind final output")
    if visual_review["verdict"]=="approve" and asset["metadata"].get("reuse_status") not in {"nbn_original","public_domain","licensed","permission"}:
        raise ValueError("image reuse not authorized")
    if visual_review.get("alt_text")!=asset["metadata"].get("alt_text"):
        raise ValueError("alt text changed after review")
    if visual_review.get("credit")!=asset["metadata"].get("credit", ""):
        raise ValueError("credit changed after review")
    return asset


def upload_step(con, asset):
    """At most one ready poll; record each phase before the corresponding network step."""
    key=visuals.digest([asset["asset_id"],asset["metadata"]["alt_text"]])
    stamp=time.time()
    con.execute("INSERT OR IGNORE INTO visual_uploads(upload_key,asset_id,alt_text,state,created_at,updated_at)"
        " VALUES (?,?,?,'new',?,?)",(key,asset["asset_id"],asset["metadata"]["alt_text"],stamp,stamp)); con.commit()
    row=dict(con.execute("SELECT * FROM visual_uploads WHERE upload_key=?",(key,)).fetchone())
    def save(state, **fields):
        values={"state":state,"updated_at":time.time(),**fields}
        con.execute("UPDATE visual_uploads SET "+",".join(k+"=?" for k in values)+" WHERE upload_key=?",(*values.values(),key))
        con.commit(); row.update(values)
    if row["state"]=="ready": return row["media_id"]
    if row["state"]=="failed": raise ValueError(row["error"] or "media upload failed")
    if stamp-row["created_at"]>UPLOAD_TIMEOUT:
        save("failed",error="media preparation timed out after 15 minutes"); raise ValueError(row["error"])
    try:
        if row["state"]=="allocating":
            # Lost allocation response has no draft side effect, but do not leak repeat uploads.
            save("failed",error="upload allocation acknowledgement lost"); raise ValueError(row["error"])
        if row["state"]=="new":
            save("allocating")
            resp=httpx.post(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/media/upload",
                headers=tf._headers(),json={"file_name":asset["asset_id"]+"."+{"image/png":"png","image/jpeg":"jpg","image/webp":"webp"}[asset["mime"]],
                    "alt_text":row["alt_text"]},timeout=10)
            resp.raise_for_status(); result=resp.json()
            if not result.get("media_id") or not result.get("upload_url"): raise ValueError("upload allocation incomplete")
            save("allocated",media_id=result["media_id"],upload_url=result["upload_url"])
        if row["state"] in {"allocated","putting"}:
            save("putting")
            # Re-PUT identical bytes to the same signed object is idempotent after interruption.
            resp=httpx.put(row["upload_url"],content=visuals.bytes_for(asset),timeout=10)
            resp.raise_for_status(); save("processing",upload_url=None)
        meta=media_get(row["media_id"])
        if meta.get("status") in {"error","failed"}: raise ValueError("Typefully rejected image")
        if meta.get("status")=="ready":
            if meta.get("alt_text")!=row["alt_text"]: raise ValueError("media alt read-back mismatch")
            save("ready",error=None); return row["media_id"]
        return None
    except ValueError as exc:
        save("failed",error=str(exc)[:300]); raise
    except httpx.HTTPStatusError as exc:
        if 400<=exc.response.status_code<500:
            save("failed",error="media HTTP "+str(exc.response.status_code)); raise ValueError(row["error"]) from exc
        return None
    except httpx.TransportError:
        return None


def _finish(con,row,data,raw):
    if not data.get("remote_version"):
        return False
    if not x_payload.matches(raw,data["media_payload"],media_lookup=media_get,remote_version=data["remote_version"]):
        return False
    status=str(raw.get("status") or "").lower()
    if status not in {"draft","planned","scheduled","publishing","published"}: return False
    mode="DRAFT" if status in {"draft","planned"} else "IMMEDIATE"
    result=store.finalize_publisher_mutation(con,row["mutation_id"],row["owner_token"],row["version"],
        mode=mode,provider_ref=str(raw["id"]),publisher_status=status)
    if result.get("ok") and not result.get("already_finalized"):
        from . import publisher
        try: publisher.tape(data["body"],data["receipt_url"],data["klass"],mode)
        except OSError: pass  # Confirmed remote/local output remains authoritative.
    return result.get("ok",False)


def process_one(con,row):
    data=json.loads(row["materialization_json"])
    if row["state"]!="awaiting_media": return reconcile_one(con,row)
    try:
        asset=visuals.get(con,data["visual_review"]["asset_id"]) if data.get("visual_review") else None
        if data["media_payload"]["posts"][0]["media"]:
            try:
                media_id=upload_step(con,asset)
                if not media_id: return "pending"
                data["media_payload"]["posts"][0]["media"][0]["media_id"]=media_id
                if media_get(media_id).get("alt_text")!=data["visual_review"]["alt_text"]:
                    raise ValueError("uploaded alt changed before attachment")
            except ValueError as exc:
                fallback=data["visual_review"].get("text_fallback")
                if not fallback: raise
                from . import lint, publisher
                source="\n".join(r.get("text", "") for r in asset["metadata"].get("evidence",[]))
                if lint.hard_rails_v2(fallback,{"_source_text":source},{"story_key":row["canonical_key"]}): raise
                data["body"]=fallback
                data["media_payload"]=x_payload.build(publisher.one_off_x_thread(fallback,data["receipt_url"]))
                data["visual_fallback_reason"]=str(exc)[:300]
        target=row.get("target_draft_id")
        if row["operation"]=="replace_draft":
            raw=tf.get_draft(target)
            if str(raw.get("status"))!="draft" or tf._has_comment_marker(raw):
                raise ValueError("draft no longer editable or owner comments present")
            if not x_payload.editable_surface(raw):
                raise ValueError("non-default or unknown owner settings; existing draft preserved")
            prior=data.get("prior_media_payload")
            if prior:
                if not data.get("prior_media_version") or not x_payload.matches(raw,prior,
                        media_lookup=media_get,remote_version=data["prior_media_version"]):
                    raise ValueError("owner changed draft media, alt or version")
            else:
                texts=tf.draft_x_texts(raw)
                if x_payload.has_media(raw) or not texts or store.x_thread_fingerprint(texts)!=row["prior_fingerprint"]:
                    raise ValueError("legacy draft changed or contains unrecorded media")
        row=update_intent(con,row,data,state="in_flight")
    except (ValueError,KeyError,OSError) as exc:
        store.transition_publisher_mutation(con,row["mutation_id"],row["owner_token"],row["version"],
            "definite_failure",error_kind="visual_preparation_failed",error_message=str(exc))
        return "failed"
    except httpx.HTTPError:
        return "pending"
    # Draft mutation begins only here. Never retry this block after an uncertain response.
    acknowledged = False
    try:
        body={"platforms":{"x":{"enabled":True,"posts":x_payload.request_posts(data["media_payload"])}}}
        if row["operation"]=="create":
            body["draft_title"]=data["body"][:60]
            if row["intended_mode"]=="IMMEDIATE" and config.AUTOPOST_ENABLED:
                when=datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=config.PUBLISH_DELAY_SECONDS)
                body["publish_at"]=when.isoformat()
            resp=httpx.post(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts",
                headers=tf._headers(),json=body,timeout=20)
        else:
            resp=httpx.patch(f"{tf.BASE}/social-sets/{config.TYPEFULLY_SOCIAL_SET_ID}/drafts/{row['target_draft_id']}",
                headers=tf._headers(),json=body,timeout=20)
        resp.raise_for_status()
        acknowledged = True
        acknowledgement=resp.json()
        data["remote_version"]=x_payload.version(acknowledgement)
        data["acknowledged_draft_id"]=str(acknowledgement.get("id") or row.get("target_draft_id") or "")
        row=update_intent(con,row,data)
        if data["acknowledged_draft_id"] and _finish(con,row,data,tf.get_draft(data["acknowledged_draft_id"])):
            return "confirmed"
    except httpx.HTTPStatusError as exc:
        if not acknowledged and 400<=exc.response.status_code<500:
            store.transition_publisher_mutation(con,row["mutation_id"],row["owner_token"],row["version"],
                "definite_failure",error_kind="visual_draft_rejected",error_message="HTTP "+str(exc.response.status_code))
            return "failed"
    except Exception:
        pass  # May have reached Typefully; protect the exact payload, never fall back to a create.
    store.transition_publisher_mutation(con,row["mutation_id"],row["owner_token"],row["version"],
        "ambiguous",provider_ref=data.get("acknowledged_draft_id", ""),error_kind="visual_confirmation_unknown")
    return "unresolved"


def reconcile_one(con,row):
    data=json.loads(row["materialization_json"])
    ref=data.get("acknowledged_draft_id")
    try:
        if ref and data.get("remote_version") and _finish(con,row,data,tf.get_draft(ref)):
            return "confirmed"
    except httpx.HTTPError:
        return "pending"
    store.transition_publisher_mutation(con,row["mutation_id"],row["owner_token"],row["version"],
        "needs_owner_review",error_kind="visual_confirmation_unknown",
        error_message="Exact draft/alt snapshot cannot be established; no automatic repeat")
    return "unresolved"


def process_pending(con,limit=2):
    rows=con.execute("SELECT * FROM publisher_mutations WHERE state='awaiting_media' ORDER BY created_at LIMIT ?",(limit,)).fetchall()
    return [process_one(con,dict(row)) for row in rows]
