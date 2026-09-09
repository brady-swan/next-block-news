import copy
import json
import time
import unittest
from unittest.mock import Mock, patch
from contextlib import ExitStack

import httpx

from nbn import config, editor, publisher, publisher_typefully as tf, publisher_visuals as delivery, store, visuals, x_payload
from tests import test_visuals


def response(value):
    r=Mock(); r.raise_for_status.return_value=None; r.json.return_value=value; return r


class VisualDeliveryTests(unittest.TestCase):
    setUp=test_visuals.VisualTests.setUp
    spec=test_visuals.VisualTests.spec

    def asset(self):
        return visuals.render_asset(self.con,run_id="test",candidate_id="item",kind="quote",preset="landscape",
            spec=self.spec(),evidence=self.evidence,alt_text="A synthetic quote.",purpose="Test")

    def queue(self,asset=None,**changes):
        asset=asset or self.asset()
        review={"verdict":"approve","asset_id":asset["asset_id"],"content_hash":asset["content_hash"],
            "post_hash":visuals.digest("Test copy."),"alt_text":asset["metadata"]["alt_text"],"credit":asset["metadata"]["credit"],"text_fallback":None}
        kwargs={"visual_review":review,"desired_thread":["Test copy.","Source: https://example.org/statement"],
            "materialization":{"run_id":"test","story_id":"s","body":"Test copy.","receipt_url":"https://example.org/statement","klass":"secondary"},
            "story_key":"test-story","operation":"create","intended_mode":"DRAFT",
            "expected_output_signature":store.canonical_output_state(self.con,"test-story")["signature"],**changes}
        result=delivery.queue(self.con,**kwargs)
        self.assertTrue(result["ok"])
        return dict(store.publisher_mutation(self.con,result["mutation_id"]))

    def remote(self,payload,**changes):
        return {"id":123,"social_set_id":config.TYPEFULLY_SOCIAL_SET_ID,"status":"draft",
            "created_at":"2026-09-07T12:00:00Z","updated_at":None,
            "platforms":{"x":{"enabled":True,"posts":x_payload.request_posts(payload)}},**changes}

    def test_payload_identity_and_nullable_version(self):
        asset=self.asset(); payload=x_payload.build(["Test","Source"],asset,"media-1")
        raw=self.remote(payload); version=x_payload.version(raw)
        self.assertIsNone(version["updated_at"])
        lookup=lambda _: {"status":"ready","alt_text":"A synthetic quote."}
        self.assertTrue(x_payload.matches(raw,payload,media_lookup=lookup,remote_version=version))
        for key,value in [("updated_at","2026-09-07T12:01:00Z"),("social_set_id","wrong")]:
            self.assertFalse(x_payload.matches({**raw,key:value},payload,media_lookup=lookup,remote_version=version))
        self.assertFalse(x_payload.matches(raw,payload,media_lookup=lambda _: {"status":"ready","alt_text":"owner edit"},remote_version=version))
        changed=copy.deepcopy(payload); changed["posts"][0]["media"][0]["alt_text"]="other"
        self.assertNotEqual(x_payload.fingerprint(changed),x_payload.fingerprint(payload))
        self.assertIsNone(x_payload.version({k:v for k,v in raw.items() if k!="updated_at"}))

    def test_queue_reserves_family_and_retains_asset(self):
        row=self.queue()
        self.assertEqual(row["state"],"awaiting_media")
        self.assertTrue(row["desired_fingerprint"].startswith(x_payload.VERSION))
        self.assertEqual(len(store.canonical_output_state(self.con,"test-story")["protected_mutations"]),1)
        self.assertEqual(self.con.execute("SELECT retained FROM visual_assets").fetchone()[0],1)
        self.assertNotIn("base64",row["materialization_json"])

    def test_upload_is_persisted_and_polls_once(self):
        asset=self.asset()
        with patch.object(delivery.httpx,"post",return_value=response({"media_id":"m1","upload_url":"https://upload.example/one"})) as post, \
             patch.object(delivery.httpx,"put",return_value=response({})) as put, \
             patch.object(delivery,"media_get",side_effect=[{"status":"processing"},{"status":"ready","alt_text":"A synthetic quote."}]) as get:
            self.assertIsNone(delivery.upload_step(self.con,asset))
            self.assertEqual(self.con.execute("SELECT state FROM visual_uploads").fetchone()[0],"processing")
            self.assertEqual(delivery.upload_step(self.con,asset),"m1")
            self.assertEqual(post.call_count,1); self.assertEqual(put.call_count,1); self.assertEqual(get.call_count,2)

    def test_upload_timeout_is_terminal(self):
        asset=self.asset()
        key=visuals.digest([asset["asset_id"],asset["metadata"]["alt_text"]])
        self.con.execute("INSERT INTO visual_uploads(upload_key,asset_id,alt_text,state,created_at,updated_at) VALUES (?,?,?,'processing',?,?)",
            (key,asset["asset_id"],asset["metadata"]["alt_text"],time.time()-901,time.time())); self.con.commit()
        with patch.object(delivery,"media_get") as get:
            with self.assertRaises(ValueError): delivery.upload_step(self.con,asset)
            get.assert_not_called()

    def test_create_confirms_exact_media_and_alt(self):
        row=self.queue(); data=json.loads(row["materialization_json"])
        data["media_payload"]["posts"][0]["media"][0]["media_id"]="m1"
        raw=self.remote(data["media_payload"])
        with patch.object(delivery,"upload_step",return_value="m1"), \
             patch.object(delivery,"media_get",return_value={"status":"ready","alt_text":"A synthetic quote."}), \
             patch.object(delivery.httpx,"post",return_value=response(raw)) as post, \
             patch.object(tf,"get_draft",return_value=raw):
            self.assertEqual(delivery.process_one(self.con,row),"confirmed")
        saved=dict(self.con.execute("SELECT * FROM posts").fetchone())
        self.assertEqual(json.loads(saved["media_payload_json"]),data["media_payload"])
        self.assertEqual(saved["mode"],"DRAFT")
        self.assertNotIn("publish_at",post.call_args.kwargs["json"])

    def test_lost_create_ack_never_retries_or_falls_back(self):
        row=self.queue()
        with patch.object(delivery,"upload_step",return_value="m1"), \
             patch.object(delivery,"media_get",return_value={"status":"ready","alt_text":"A synthetic quote."}), \
             patch.object(delivery.httpx,"post",side_effect=httpx.ReadTimeout("lost")) as post:
            self.assertEqual(delivery.process_one(self.con,row),"unresolved")
            row=dict(store.publisher_mutation(self.con,row["mutation_id"]))
            self.assertEqual(delivery.process_one(self.con,row),"unresolved")
            self.assertEqual(post.call_count,1)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM posts").fetchone()[0],0)

    def test_text_revision_after_image_omission_keeps_versioned_identity(self):
        prior=x_payload.build(["Old copy.","Source: https://example.org/statement"])
        old=self.remote(prior)
        self.con.execute("INSERT INTO posts(id,created,story_key,class,body,receipt_url,mode,nuelink_id,publisher_backend,publisher_status)"
            " VALUES (1,?,'test-story','secondary','Old copy.','https://example.org/statement','DRAFT','123','typefully','draft')",(time.time(),))
        self.con.commit()
        row=self.queue(visual_review=None,operation="replace_draft",target_draft_id="123",target_post_id=1,
            prior_thread=[p["text"] for p in prior["posts"]],prior_payload=prior,prior_version=x_payload.version(old))
        data=json.loads(row["materialization_json"])
        updated=self.remote(data["media_payload"],updated_at="2026-09-07T12:01:00Z")
        with patch.object(delivery,"upload_step") as upload,patch.object(delivery.httpx,"patch",return_value=response(updated)), \
             patch.object(tf,"get_draft",side_effect=[old,updated]):
            self.assertEqual(delivery.process_one(self.con,row),"confirmed")
        upload.assert_not_called()
        saved=dict(self.con.execute("SELECT * FROM posts").fetchone())
        self.assertEqual(json.loads(saved["media_payload_json"]),data["media_payload"])
        self.assertEqual(json.loads(saved["media_remote_version"]),x_payload.version(updated))

    def test_no_implicit_image_removal_or_owner_edit_overwrite(self):
        a=self.asset(); prior=x_payload.build(["Old copy.","Source"],a,"old-media")
        with self.assertRaisesRegex(ValueError,"removal requires"):
            self.queue(a,visual_review=None,prior_payload=prior)
        old=self.remote(prior)
        row=self.queue(a,operation="replace_draft",target_draft_id="123",prior_payload=prior,
            prior_version=x_payload.version(old),prior_thread=["Old copy.","Source"])
        with patch.object(delivery,"upload_step",return_value="new-media"), \
             patch.object(delivery,"media_get",return_value={"status":"ready","alt_text":"A synthetic quote."}), \
             patch.object(tf,"get_draft",return_value={**old,"updated_at":"2026-09-07T12:01:00Z"}), \
             patch.object(delivery.httpx,"patch") as patch_http:
            self.assertEqual(delivery.process_one(self.con,row),"failed")
        patch_http.assert_not_called()

    def test_upload_failure_only_uses_separately_approved_fallback(self):
        row=self.queue(); data=json.loads(row["materialization_json"])
        data["visual_review"]["text_fallback"]="Standalone copy."
        row=delivery.update_intent(self.con,row,data)
        payload=x_payload.build(publisher.one_off_x_thread("Standalone copy.",data["receipt_url"]))
        raw=self.remote(payload)
        with patch.object(delivery,"upload_step",side_effect=ValueError("upload rejected")), \
             patch("nbn.lint.hard_rails_v2",return_value=[]), \
             patch.object(delivery.httpx,"post",return_value=response(raw)) as post,patch.object(tf,"get_draft",return_value=raw):
            self.assertEqual(delivery.process_one(self.con,row),"confirmed")
        self.assertEqual(post.call_args.kwargs["json"]["platforms"]["x"]["posts"],x_payload.request_posts(payload))
        from nbn import visual_choices
        panel=visual_choices.panel(self.con,"test","s",["item"],data["visual_review"]["asset_id"],review=data["visual_review"])
        self.assertIsNone(panel["selected_asset_id"])
        self.assertEqual(panel["decision"],"text_fallback")

    def test_omitted_image_is_not_selected_and_planned_is_not_published(self):
        from nbn import visual_choices
        a=self.asset()
        panel=visual_choices.panel(self.con,"test","s",["item"],a["asset_id"],review={"verdict":"omit","asset_id":a["asset_id"]})
        self.assertEqual(panel["decision"],"omit"); self.assertIsNone(panel["selected_asset_id"])
        row=self.queue(a); data=json.loads(row["materialization_json"])
        data["media_payload"]["posts"][0]["media"][0]["media_id"]="m1"
        raw=self.remote(data["media_payload"],status="planned")
        with patch.object(delivery,"upload_step",return_value="m1"), \
             patch.object(delivery,"media_get",return_value={"status":"ready","alt_text":"A synthetic quote."}), \
             patch.object(delivery.httpx,"post",return_value=response(raw)),patch.object(tf,"get_draft",return_value=raw):
            self.assertEqual(delivery.process_one(self.con,row),"confirmed")
        self.assertEqual(self.con.execute("SELECT mode FROM posts").fetchone()[0],"DRAFT")

    def test_desk_request_is_versioned_and_does_not_review_in_http(self):
        from nbn import observations, visual_choices
        a=self.asset()
        story={"story_id":"s","story_key":"test-story","post":"Test copy.","member_candidate_ids":["item"]}
        store.start_newsroom_run(self.con,"test","live","fixture","test",["item"])
        store.validate_newsroom_run(self.con,"test",{"stories":[story]},"fixture",{})
        observations.record(self.con,"test","editor_input",{"payload":{"candidates":[{
            "story_id":"s","post":"Test copy.","selected_receipt":{"url":"https://example.org/statement"},
            "inspected_evidence_refs":[]}],"evidence_catalog":[]}})
        with patch.object(editor,"review_newsroom_batch") as review:
            result=visual_choices.request(self.con,"test","s","select",a["asset_id"],"landscape",0)
            self.assertTrue(result["ok"])
            stale=visual_choices.request(self.con,"test","s","omit",a["asset_id"],"landscape",0)
            self.assertFalse(stale["ok"]); review.assert_not_called()
        decision={"verdict":"publish","post":"Test copy.","reader_receipt_ref":None,"visual_review":{
            "verdict":"approve","asset_id":a["asset_id"],"content_hash":a["content_hash"],
            "post_hash":visuals.digest("Test copy."),"alt_text":a["metadata"]["alt_text"],"credit":a["metadata"]["credit"]}}
        with patch.object(editor,"review_newsroom_batch",return_value={"decisions":{"s":decision}}), \
             patch("nbn.lint.hard_rails_v2",return_value=["mechanical error"]) as rails, \
             patch.object(delivery,"queue") as queue:
            visual_choices.process(self.con)
        rails.assert_called_once(); queue.assert_not_called()
        self.assertIn("mechanical_rails",self.con.execute("SELECT state FROM visual_choices").fetchone()[0])

    def test_readback_4xx_after_success_keeps_duplicate_protection(self):
        row=self.queue(); data=json.loads(row["materialization_json"])
        data["media_payload"]["posts"][0]["media"][0]["media_id"]="m1"
        raw=self.remote(data["media_payload"])
        error=httpx.HTTPStatusError("not visible yet",request=httpx.Request("GET","https://api.typefully.com/drafts/123"),
            response=httpx.Response(404))
        with patch.object(delivery,"upload_step",return_value="m1"), \
             patch.object(delivery,"media_get",return_value={"status":"ready","alt_text":"A synthetic quote."}), \
             patch.object(delivery.httpx,"post",return_value=response(raw)),patch.object(tf,"get_draft",side_effect=error):
            self.assertEqual(delivery.process_one(self.con,row),"unresolved")
        self.assertEqual(store.publisher_mutation(self.con,row["mutation_id"])["state"],"ambiguous")
        self.assertTrue(store.canonical_output_state(self.con,"test-story")["protected_mutations"])

    def test_editor_initial_and_recovery_receive_identical_pixels(self):
        from nbn import brain
        a=self.asset(); visual={**visuals.manifest(a),"reusable":True}
        candidate={"story_id":"s","post":"Test copy.","visual":visual,"selected_receipt":{},"inspected_evidence":[]}
        row={"story_id":"s","verdict":"publish","post":"Test copy.","reader_receipt_ref":None,"visual_verdict":"approve",
            "visual_asset_id":a["asset_id"],"visual_content_hash":a["content_hash"],"text_fallback":None}
        with patch.object(brain,"_create",return_value=Mock()) as create, \
             patch.object(brain,"_json_from",side_effect=[{"decisions":[]},{"decisions":[row]}]), \
             patch.object(store,"record_model_usage"),patch.object(store,"recent_feed_posts",return_value=[]):
            result=editor.review_newsroom_batch([candidate],self.con,run_id="test")
        self.assertEqual(result["recovery"]["recovered"],1)
        one,two=[call.args[2] for call in create.call_args_list]
        first=[b for b in one if b["type"]=="image"][0]
        self.assertEqual(first,[b for b in two if b["type"]=="image"][0])
        self.assertNotIn("base64",self.con.execute("SELECT payload_json FROM run_observations WHERE kind='editor_input'").fetchone()[0])

    def test_media_capacity_does_not_call_editor_without_pixels(self):
        from nbn import brain
        a=self.asset()
        candidate={"story_id":"s","post":"Test.","visual":{**visuals.manifest(a),"reusable":True},"selected_receipt":{},"inspected_evidence":[]}
        with patch.object(visuals,"MAX_IMAGE_CONTEXT",1),patch.object(brain,"_create") as create:
            result=editor.review_newsroom_batch([candidate],self.con,run_id="test")
        self.assertEqual(result["payload_deferred"],["s"]); create.assert_not_called()

    def test_main_never_stages_unreviewed_visual_fallbacks(self):
        from nbn import brain, main, newsroom
        from tests.test_editorial_v2 import materialization_fixture, EditorialV2Tests
        for kind in ("outage","omitted","capacity"):
            with self.subTest(kind=kind), ExitStack() as stack:
                rid="run:"+kind
                row,record,draft,session=materialization_fixture(self.con,rid)
                draft["visual"]={"error":"visual unavailable","required":True}
                stack.enter_context(patch.object(brain,"reserve_model_calls",return_value="token"))
                stack.enter_context(patch.object(newsroom,"start_session",return_value=session))
                stack.enter_context(patch.object(editor,"review_newsroom_batch",return_value={
                    "ok":kind!="outage","decisions":{},"payload_deferred":["sec"] if kind=="capacity" else []}))
                send=stack.enter_context(patch.object(publisher,"publish"))
                stack.enter_context(patch.object(publisher,"backend_name",return_value="typefully"))
                stack.enter_context(patch.object(config,"RUN_NEWSROOM_MODE","live"))
                self.assertTrue(store.acquire_cycle_lease(self.con,"test-owner"))
                result=main._run_editorial_v2(self.con,lease_owner="test-owner",pipeline_run_id=rid,
                    inventory=[row],pending=[row],result=EditorialV2Tests.result_counts(),theme_snapshot=[],overrides={},run_started=time.time())
                self.assertEqual(result["held"],1); send.assert_not_called()

    def test_external_credit_is_actually_in_the_reply(self):
        a=self.asset(); a.update(kind="source_image")
        a["metadata"]["credit"]="Photo: Example Agency, licensed"
        payload=x_payload.build(["Copy.","Source: https://example.org"],a,"m")
        self.assertIn("Example Agency",x_payload.request_posts(payload)[1]["text"])
        for field in ("hide_link_preview","made_with_ai","subscribers_only"):
            raw=self.remote(payload); raw["platforms"]["x"]["posts"][0][field]=True
            self.assertFalse(x_payload.editable_surface(raw))

    def test_legacy_media_is_not_safe_for_text_patch(self):
        raw={"status":"draft","platforms":{"x":{"enabled":True,"posts":[{"text":"old","media_ids":["m"]}]}}}
        with patch.object(tf,"get_draft",return_value=raw),patch.object(tf.httpx,"patch") as patch_http:
            outcome,reason=tf.replace_draft("123",["old"],["new"])
        self.assertEqual(outcome,tf.PublishOutcome.FAILED)
        self.assertEqual(reason,"media_requires_versioned_review"); patch_http.assert_not_called()

    def test_editor_approval_binds_exact_asset_hash_and_copy(self):
        asset=self.asset(); visual={**visuals.manifest(asset),"reusable":True}
        card={"visual":visual,"inspected_evidence_refs":[]}
        row={"verdict":"publish","post":"Test copy.","reader_receipt_ref":None,"visual_verdict":"approve",
            "visual_asset_id":asset["asset_id"],"visual_content_hash":asset["content_hash"],"text_fallback":"Standalone."}
        result=editor._editor_decision(row,{},card,"initial")
        self.assertEqual(result["visual_review"]["post_hash"],visuals.digest("Test copy."))
        self.assertIsNone(editor._editor_decision({**row,"visual_content_hash":"other"},{},card,"initial"))
        self.assertIsNone(editor._editor_decision({"verdict":"publish","post":"Test copy.","reader_receipt_ref":None},{},card,"initial"))
        omitted=editor._editor_decision({**row,"visual_verdict":"omit"},{},card,"initial")
        self.assertEqual(omitted["post"],"Standalone.")
        self.assertIsNone(editor._editor_decision({**row,"visual_verdict":"omit","text_fallback":None},{},card,"initial"))


if __name__=="__main__": unittest.main()
