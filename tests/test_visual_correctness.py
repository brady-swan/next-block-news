"""Offline regressions for evidence transport, budgets and truthful graphics."""
import copy
import io
import json
import time
import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image, ImageDraw
from nbn import (brain, config, editor, main, newsroom, observations, publisher,
                 store, visual_choices, visual_render, visual_tools, visuals)
from tests import test_visuals as visual_test_support
from tests.test_editorial_v2 import candidate, inspected, materialization_fixture
from tests import test_editorial_v2 as editorial_test_support


class VisualCorrectnessTests(unittest.TestCase):
    setUp = visual_test_support.VisualTests.setUp
    spec = visual_test_support.VisualTests.spec
    fake_session = visual_test_support.VisualTests.fake_session

    def asset(self, *, run_id="test", cid="item", kind="source_image", inspected=True, serial=0):
        buf = io.BytesIO()
        Image.new("RGB", (200, 200), (serial, 90, 180)).save(buf, "PNG")
        asset = visuals.save(self.con, run_id=run_id, candidate_id=cid, kind=kind,
            data=buf.getvalue(), metadata={"source_url":"https://example.org/source",
                "reuse_status":"unknown", "alt_text":"A retained source image.",
                "credit":"Source", "purpose":"Understand reporting"})
        if inspected:
            self.con.execute("UPDATE visual_assets SET writer_inspected_at=1 WHERE asset_id=?", (asset["asset_id"],))
            self.con.commit()
        return visuals.get(self.con, asset["asset_id"])

    def card(self, story, assets, attachment=None):
        return {"story_id":story, "post":"Test copy.", "selected_receipt":{}, "inspected_evidence":[],
            "visual_evidence":[visuals.manifest(a) for a in assets],
            "visual_evidence_scope":{"run_id":"test", "candidate_ids":[a["candidate_id"] for a in assets]},
            **({"visual":{**visuals.manifest(attachment), "reusable":True}} if attachment else {})}

    def review(self, cards, responses, run_id="test"):
        with patch.object(brain, "_create", return_value=Mock()) as create, \
             patch.object(brain, "_json_from", side_effect=responses), \
             patch.object(store, "record_model_usage"), patch.object(store, "recent_feed_posts", return_value=[]):
            result = editor.review_newsroom_batch(cards, self.con, run_id=run_id)
        return result, create

    @staticmethod
    def decision(story):
        return {"story_id":story, "verdict":"publish", "post":"Test copy."}

    def test_evidence_only_unknown_rights_reaches_initial_and_recovery_as_exact_pixels(self):
        a = self.asset()
        result, create = self.review([self.card("s", [a])], [{"decisions":[]}, {"decisions":[self.decision("s")]}])
        self.assertEqual(result["recovery"]["recovered"], 1)
        self.assertFalse(result["decisions"]["s"].get("visual_review"))
        images = [[b for b in call.args[2] if b["type"] == "image"] for call in create.call_args_list]
        self.assertEqual(images[0], images[1])
        self.assertEqual(images[0][0]["source"], visuals.image_block(a)["source"])
        for call in create.call_args_list:
            packet = json.loads(call.args[2][0]["text"])
            self.assertNotIn("visual", packet["candidates"][0])
            self.assertNotIn('"visual_verdict"', json.dumps(call.kwargs.get("schema")))
        retained = self.con.execute("SELECT payload_json FROM run_observations WHERE kind='editor_input'").fetchone()[0]
        self.assertIn(a["asset_id"], retained)
        self.assertNotIn("base64", retained)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM visual_uploads").fetchone()[0], 0)

    def test_attachment_and_evidence_are_transmitted_once(self):
        a = self.asset()
        row = {**self.decision("s"), "visual_verdict":"approve", "visual_asset_id":a["asset_id"],
               "visual_content_hash":a["content_hash"], "text_fallback":None}
        result, create = self.review([self.card("s", [a, a], a)], [{"decisions":[row]}])
        self.assertIn("s", result["decisions"])
        content = create.call_args.args[2]
        self.assertEqual(sum(b["type"] == "image" for b in content), 1)
        self.assertIn("reporting evidence", content[1]["text"])
        self.assertIn("proposed attachment", content[1]["text"])

    def test_image_capacity_admits_each_story_atomically(self):
        assets = [self.asset(cid=str(i), serial=i) for i in range(7)]
        cards = [self.card("first", assets[:2]), self.card("too-many", assets[2:5]), self.card("last", assets[5:])]
        result, create = self.review(cards, [{"decisions":[self.decision("first"), self.decision("last")]}])
        self.assertEqual(result["payload_deferred"], ["too-many"])
        self.assertEqual(set(result["decisions"]), {"first", "last"})
        self.assertEqual(sum(b["type"] == "image" for b in create.call_args.args[2]), 4)

    def test_bad_evidence_is_deferred_without_losing_usable_siblings(self):
        a = self.asset()
        for fault in ("hash", "owner", "run", "scope", "missing", "uninspected", "byte-limit"):
            with self.subTest(fault=fault), ExitStack() as stack:
                card = self.card("bad", [a])
                if fault == "hash": card["visual_evidence"][0]["content_hash"] = "wrong"
                if fault == "owner": card["visual_evidence_scope"]["candidate_ids"] = ["other"]
                if fault == "run": card["visual_evidence_scope"]["run_id"] = "other"
                if fault == "scope": card["visual_evidence_scope"] = None
                if fault == "missing": stack.enter_context(patch.object(visuals, "bytes_for", side_effect=FileNotFoundError()))
                if fault == "uninspected":
                    stack.enter_context(patch.object(visuals, "get", return_value={**a, "writer_inspected_at":None}))
                if fault == "byte-limit": stack.enter_context(patch.object(visuals, "MAX_IMAGE_CONTEXT", 1))
                result, create = self.review([card, {"story_id":"ok", "post":"Test copy."}],
                    [{"decisions":[self.decision("ok")]}])
                self.assertEqual(result["payload_deferred"], ["bad"])
                self.assertEqual(set(result["decisions"]), {"ok"})
                self.assertIsInstance(create.call_args.args[2], str)

    def test_retained_desk_review_uses_original_image_ownership(self):
        a = self.asset()
        story = {"story_id":"s", "story_key":"test-story", "post":"Test copy.", "member_candidate_ids":["item"]}
        store.start_newsroom_run(self.con, "test", "live", "fixture", "test", ["item"])
        store.validate_newsroom_run(self.con, "test", {"stories":[story]}, "fixture", {})
        card = {**self.card("s", [a]), "inspected_evidence_refs":[],
                "selected_receipt":{"url":"https://example.org/source"}}
        observations.record(self.con, "test", "editor_input", {"payload":{"candidates":[card], "evidence_catalog":[]}})
        self.assertTrue(visual_choices.request(self.con, "test", "s", "select", a["asset_id"], "landscape", 0)["ok"])
        original_review = editor.review_newsroom_batch
        captured = []
        def review(cards, con, **kwargs):
            result = original_review(cards, con, **kwargs)
            captured.append((kwargs["run_id"], result))
            return result
        with patch.object(editor, "review_newsroom_batch", side_effect=review), \
             patch.object(brain, "_create", return_value=Mock()) as create, \
             patch.object(brain, "_json_from", return_value={"decisions":[{"story_id":"s", "verdict":"drop", "post":None}]}), \
             patch.object(store, "record_model_usage"), patch.object(store, "recent_feed_posts", return_value=[]):
            visual_choices.process(self.con)
        self.assertEqual(captured[0][0], "visual-choice:test:1")
        self.assertEqual(captured[0][1]["payload_deferred"], [])
        self.assertIn("s", captured[0][1]["decisions"])
        self.assertEqual(sum(b["type"] == "image" for b in create.call_args.args[2]), 1)

    def dossier(self, image_ids, run_id="test"):
        rows = [candidate("item"), candidate("sibling")]
        session = newsroom.NewsroomSession(run_id=run_id, inventory=rows, recent_clusters=[],
            theme_snapshot=[], handles={}, con=self.con, reservation="token")
        record = inspected("fetch-sec", rows[0]["url"], "SEC", "The SEC announced a Bitcoin policy update.")
        session.fetches[record.fetch_id] = record
        stories = [{"story_id":cid, "story_key":"sec-policy-"+cid, "existing_cluster_key":None,
                    "coverage_relation":"distinct", "member_candidate_ids":[cid], "post":record.text,
                    "selected_fetch_id":record.fetch_id, "evidence_fetch_ids":[record.fetch_id],
                    "visual_asset_id":None, "visual_required":False, "elevated_claim":False,
                    "reader_value":"Policy changed.", "reason":"Useful"} for cid in ("item", "sibling")]
        if image_ids is not None: stories[0]["visual_evidence_ids"] = image_ids
        store.start_newsroom_run(self.con, run_id, "live", "fixture", newsroom.PROMPT_VERSION, ["item", "sibling"])
        store.set_newsroom_state(self.con, run_id, "researching")
        return session._validate_and_convert_v2({"decisions":[{"candidate_id":s["story_id"],
            "story_id":s["story_id"], "disposition":"publish", "reason":"Useful"} for s in stories],
            "stories":stories, "run_note":"Fixture"})

    def test_normalization_keeps_evidence_without_attachment_and_legacy_siblings(self):
        a = self.asset()
        outcome = self.dossier([a["asset_id"]])
        draft = outcome.drafts["item"]
        self.assertEqual(draft["visual_evidence"][0]["asset_id"], a["asset_id"])
        self.assertEqual(draft["visual_evidence_scope"], {"run_id":"test", "candidate_ids":["item"]})
        self.assertNotIn("visual", draft)
        self.assertNotIn("visual_evidence", outcome.drafts["sibling"])
        self.assertNotIn("A retained source image", draft["_source_text"])

    def test_normalization_rejects_foreign_uninspected_and_malformed_refs_per_story(self):
        bad = [self.asset(run_id="old"), self.asset(cid="sibling"), self.asset(inspected=False, serial=3)]
        for refs in ([a["asset_id"]] for a in bad):
            outcome = self.dossier(refs)
            self.assertNotIn("item", outcome.drafts)
            self.assertIn("sibling", outcome.drafts)
            self.assertEqual(outcome.story_attempts[0]["failure"], "defer:invalid_visual_evidence")
        for refs in ("visual_invalid", ["visual_missing"], [3], ["visual_missing"]*5):
            with self.subTest(refs=refs):
                self.assertNotIn("item", self.dossier(refs).drafts)
        a = self.asset(serial=4)
        with patch.object(visuals, "bytes_for", side_effect=ValueError("changed hash")):
            self.assertNotIn("item", self.dossier([a["asset_id"]]).drafts)

    def test_main_passes_evidence_and_holds_unreviewed_image_dependent_copy(self):
        for kind in ("outage", "omitted", "capacity"):
            with self.subTest(kind=kind), ExitStack() as stack:
                rid = "run:"+kind
                row, record, draft, session = materialization_fixture(self.con, rid)
                a = self.asset(run_id=rid, cid=row["url_hash"])
                draft.update(visual_evidence=[visuals.manifest(a)],
                             visual_evidence_scope={"run_id":rid, "candidate_ids":[row["url_hash"]]})
                stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
                stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
                review = stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                    "ok":kind != "outage", "decisions":{}, "payload_deferred":["sec"] if kind == "capacity" else []}))
                send = stack.enter_context(patch.object(publisher, "publish"))
                stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
                stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
                self.assertTrue(store.acquire_cycle_lease(self.con, "test-owner"))
                result = main._run_editorial_v2(self.con, lease_owner="test-owner", pipeline_run_id=rid,
                    inventory=[row], pending=[row], result=editorial_test_support.EditorialV2Tests.result_counts(),
                    theme_snapshot=[], overrides={}, run_started=time.time())
                self.assertEqual(result["held"], 1)
                send.assert_not_called()
                sent = review.call_args.args[0][0]
                self.assertEqual(sent["visual_evidence"][0]["asset_id"], a["asset_id"])
                self.assertNotIn("visual", sent)

    def test_four_inspections_do_not_spend_render_allowance(self):
        session = self.fake_session()
        session.by_hash["other"] = {}
        session.fetches = {"fetch_1":self.evidence[0]}
        session._fetch_payload = lambda receipt, **kwargs: receipt
        for cid in ("item", "other"):
            a = self.asset(cid=cid)
            for _ in range(2):
                reply = visual_tools.dispatch(session, SimpleNamespace(name="inspect_visual", id="i",
                    input={"candidate_id":cid, "visual_id":a["asset_id"]}))
                self.assertIn("_pixels", reply)
        def render(spec):
            return visual_tools.dispatch(session, SimpleNamespace(name="render_visual", id="r", input={
                "candidate_id":"item", "evidence_fetch_ids":["fetch_1"], "kind":"quote", "preset":"landscape",
                "spec_json":json.dumps(spec), "alt_text":"Test quote.", "purpose":"Test"}))
        self.assertTrue(render({**self.spec(), "passage":"Not in the source"})["is_error"])
        self.assertEqual(session.visual_state["renders"], 0)
        for _ in range(4): self.assertIn("_pixels", render(self.spec()))
        self.assertIn("run render budget", render(self.spec())["content"])
        self.assertEqual((session.visual_state["inspections"], session.visual_state["renders"]), (4, 4))
        denied = visual_tools.dispatch(session, SimpleNamespace(name="inspect_visual", id="i",
            input={"candidate_id":"other", "visual_id":a["asset_id"]}))
        self.assertIn("run visual inspection budget", denied["content"])

    def test_cached_external_assets_do_not_bypass_story_inspection_limit(self):
        for kind in ("source_image", "pdf_page"):
            with self.subTest(kind=kind):
                a = self.asset(kind=kind, run_id="old")
                session = self.fake_session()
                block = SimpleNamespace(name="inspect_visual", id="i", input={"candidate_id":"item", "visual_id":a["asset_id"]})
                for _ in range(2): self.assertIn("_pixels", visual_tools.dispatch(session, block))
                self.assertIn("story external inspection budget", visual_tools.dispatch(session, block)["content"])
                self.assertEqual(session.visual_state["inspections"], 2)

    def test_attribution_uses_referenced_receipts_not_array_order(self):
        unrelated = {**self.evidence[0], "fetch_id":"unrelated", "final_url":"https://example.org/wrong"}
        for evidence in ([unrelated, *self.evidence], [*self.evidence, unrelated]):
            a = visuals.render_asset(self.con, run_id="test", candidate_id="item", kind="excerpt", preset="landscape",
                spec=self.spec(), evidence=evidence, alt_text="Test excerpt.", purpose="Test")
            self.assertEqual(a["metadata"]["source_url"], self.evidence[0]["final_url"])
            self.assertEqual(a["metadata"]["source_urls"], [self.evidence[0]["final_url"]])
        spec = self.data_spec()
        spec["points"][1]["source_fetch_id"] = "unrelated"
        a = visuals.render_asset(self.con, run_id="test", candidate_id="item", kind="line", preset="landscape",
            spec=spec, evidence=[unrelated, *self.evidence], alt_text="Test series.", purpose="Test")
        self.assertEqual(a["metadata"]["source_urls"], [self.evidence[0]["final_url"], unrelated["final_url"]])

    def test_every_highlight_color_renders_in_both_presets_and_survives_regeneration(self):
        for color, hex_color in visual_render.COLORS.items():
            for preset in ("landscape", "square"):
                with self.subTest(color=color, preset=preset):
                    a = visuals.render_asset(self.con, run_id="test", candidate_id="item", kind="excerpt", preset=preset,
                        spec={**self.spec(), "color":color}, evidence=self.evidence, alt_text="Test excerpt.", purpose="Test")
                    im = Image.open(io.BytesIO(visuals.bytes_for(a))).convert("RGB")
                    counts = dict((rgb, n) for n, rgb in im.getcolors(im.width*im.height))
                    rgb = tuple(bytes.fromhex(hex_color[1:]))
                    self.assertGreater(counts.get(rgb, 0), 1000)
                    valid = visual_render.validate("excerpt", a["metadata"]["spec"], self.evidence)
                    self.assertEqual(valid["color"], color)
                    self.assertEqual(valid["highlight_spans"], [(12, 31)])
        self.assertEqual(visual_render.validate("excerpt", self.spec(), self.evidence)["color"], "yellow")

    def data_spec(self):
        return {"source":"Source", "headline":"Values across time", "unit":"USD millions", "period":"2025–2026",
            "metric":"none", "points":[{"label":label, "date":stamp, "value":value, "source_fetch_id":"fetch_1"}
                for label, stamp, value in [("Dec 31", "2025-12-31", 100), ("Jan 1", "2026-01-01", -20),
                                            ("Jan 10", "2026-01-10", None), ("Jan 31", "2026-01-31", 80)]]}

    def test_irregular_geometry_is_proportional_and_missing_points_break_line(self):
        valid = visual_render.validate("line", self.data_spec(), self.evidence)
        xs = visual_render.line_positions(valid, 200, 1536)
        self.assertAlmostEqual((xs[2]-xs[1])/(xs[1]-xs[0]), 9)
        self.assertAlmostEqual((xs[3]-xs[2])/(xs[1]-xs[0]), 21)
        with patch.object(ImageDraw.ImageDraw, "line", autospec=True) as draw_line, \
             patch.object(ImageDraw.ImageDraw, "ellipse", autospec=True) as dot:
            visual_render.render("line", "landscape", valid)
        segments = [c for c in draw_line.call_args_list if c.kwargs.get("width") == 5]
        self.assertEqual(len(segments), 1)
        self.assertEqual(len(dot.call_args_list), 3)
        self.assertAlmostEqual(segments[0].args[1][0], xs[0])
        self.assertAlmostEqual(segments[0].args[1][2], xs[1])

    def test_line_dates_require_valid_chronology_or_explicit_category(self):
        for dates in (("bad", "2026-01-01"), ("2026-02-30", "2026-03-01"),
                      ("2026-01-01", "2026-01-01"), ("2026-02-01", "2026-01-01"),
                      ("20260101", "2026-02-01")):
            spec = self.data_spec()
            spec["points"] = spec["points"][:2]
            for point, date in zip(spec["points"], dates): point["date"] = date
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                visual_render.validate("line", spec, self.evidence)
        spec = self.data_spec()
        spec["x_axis"] = "category"
        for point in spec["points"]: point["date"] = point["label"]
        valid = visual_render.validate("line", spec, self.evidence)
        xs = visual_render.line_positions(valid, 200, 1536)
        self.assertAlmostEqual(xs[1]-xs[0], xs[3]-xs[2])
        with patch.object(ImageDraw.ImageDraw, "text", autospec=True) as draw:
            visual_render.render("line", "square", valid)
        self.assertIn("Equally spaced observations", [c.args[2] for c in draw.call_args_list])

    def test_close_temporal_labels_fit_without_moving_points(self):
        spec = self.data_spec()
        spec["points"] = [{"label":str(i), "date":stamp, "value":value, "source_fetch_id":"fetch_1"}
            for i, (stamp, value) in enumerate([("2026-01-01",100), ("2026-01-02",None),
                ("2026-01-03",None), ("2026-01-04",100), ("2026-12-31",100)])]
        valid = visual_render.validate("line", spec, self.evidence)
        for preset in ("square", "landscape"):
            with patch.object(ImageDraw.ImageDraw, "text", autospec=True) as draw:
                visual_render.render("line", preset, valid)
            boxes = []
            date_count = 0
            for c in draw.call_args_list:
                if c.kwargs.get("anchor") not in {"mt", "mb"}: continue
                xy, value = c.args[1:3]
                if value in [p["date"] for p in spec["points"]]: date_count += 1
                face = c.kwargs["font"]
                box = face.getbbox(value, anchor=c.kwargs["anchor"])
                boxes.append((box[0]+xy[0], box[1]+xy[1], box[2]+xy[0], box[3]+xy[1]))
            self.assertGreaterEqual(date_count, 2)
            self.assertLess(date_count, len(spec["points"]))
            for i, a in enumerate(boxes):
                self.assertGreaterEqual(a[0], 64)
                self.assertLessEqual(a[2], 1536)
                for b in boxes[i+1:]:
                    self.assertTrue(a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


if __name__ == "__main__":
    unittest.main()
