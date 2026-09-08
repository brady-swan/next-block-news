import json
import tempfile
import unittest
import time
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path
from unittest.mock import patch

from nbn import config, models, store, visual_render, visuals
import httpx


class VisualTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="nbn-visual-test-")
        self.addCleanup(self.temp.cleanup)
        self.patch=patch.object(config,"DB_PATH",Path(self.temp.name)/"nbn.db")
        self.patch.start(); self.addCleanup(self.patch.stop)
        tape_patch=patch.object(config,"TAPE_DIR",Path(self.temp.name)/"tapes")
        tape_patch.start(); self.addCleanup(tape_patch.stop)
        self.con=store.connect(); self.addCleanup(self.con.close)
        visuals.initialize(self.con)
        self.evidence=[{"fetch_id":"fetch_1","text":"The network belongs to everyone. No one can speak for everyone.",
                        "final_url":"https://example.org/statement","retrieval_kind":"direct_fetch",
                        "content_fingerprint":"fixture","limitations":"Synthetic test fixture"}]

    def spec(self):
        return {"source":"Illustrative statement","date":"7 September 2026",
                "passage":"The network belongs to everyone. No one can speak for everyone.",
                "speaker":"Example speaker","source_fetch_id":"fetch_1",
                "highlights":["belongs to everyone"],"location":"Paragraph 1"}

    def test_quote_exact_and_durable(self):
        a=visuals.render_asset(self.con,run_id="test",candidate_id="item",kind="quote",
            preset="landscape",spec=self.spec(),evidence=self.evidence,
            alt_text="Synthetic quotation for testing.",purpose="Test quote card")
        self.assertEqual((a["width"],a["height"]),(1600,1200))
        self.assertEqual(visuals.digest(visuals.bytes_for(a)),a["content_hash"])
        with self.assertRaises(ValueError):
            visuals.proposal(self.con,a["asset_id"],run_id="test",members=["item"])
        self.con.execute("UPDATE visual_assets SET writer_inspected_at=1")
        self.con.commit()
        self.assertTrue(visuals.proposal(self.con,a["asset_id"],run_id="test",members=["item"])["reusable"])

    def test_paraphrase_and_noncontiguous_rejected(self):
        with self.assertRaises(ValueError):
            visual_render.validate("quote",self.spec(),[{**self.evidence[0],"retrieval_kind":"provider_reported_extract"}])
        with self.assertRaises(ValueError):
            visual_render.validate("excerpt",{**self.spec(),"passage":"The network belongs to everyone. everyone."},self.evidence)

    def test_offsets_and_highlights(self):
        spec=visual_render.validate("excerpt",self.spec(),self.evidence)
        a,b=spec["highlight_spans"][0]
        self.assertEqual(spec["passage"][a:b],"belongs to everyone")
        for preset in ("square","landscape"):
            data,size=visual_render.render("excerpt",preset,spec)
            self.assertGreater(len(data),1000)
            self.assertEqual(size,(1600,1600 if preset=="square" else 900))

    def test_data_signed_missing_and_computed(self):
        s={"source":"Illustrative data","headline":"A week of flows","date":"", "unit":"USD millions",
           "period":"7–11 September 2026","metric":"sum", "points":[
               {"label":"Mon","date":"2026-09-07","value":100,"source_fetch_id":"fetch_1"},
               {"label":"Tue","date":"2026-09-08","value":-20,"source_fetch_id":"fetch_1"}]}
        for kind in ("bar","line","comparison"):
            valid=visual_render.validate(kind,s,self.evidence)
            self.assertEqual(valid["metric_value"],80)
            data,_=visual_render.render(kind,"landscape",valid)
            self.assertTrue(data.startswith(b"\x89PNG"))
        s["points"][0]["value"]=None
        with self.assertRaises(ValueError): visual_render.validate("line",s,self.evidence)
        s["metric"]="none"
        self.assertIsNone(visual_render.validate("line",s,self.evidence)["points"][0]["value"])

    def test_images_are_not_text_context_or_observation_base64(self):
        b={"type":"image","source":{"type":"base64","media_type":"image/png","data":"abcd"},
           "_asset_id":"v1","_content_hash":"hash"}
        self.assertNotIn("abcd",json.dumps(visuals.without_pixels([b])))
        self.assertEqual(visuals.image_bytes([b]),4)
        out=models.response_input([{"role":"user","content":[{"type":"text","text":"Inspect v1"},b]}])
        self.assertEqual(out[1]["content"][0]["image_url"],"data:image/png;base64,abcd")

    def test_small_bitcoin_amounts_are_not_rounded_to_zero(self):
        self.assertEqual(visual_render.number(1e-8),"0.00000001")
        self.assertEqual(visual_render.number(-1e-8),"-0.00000001")
        self.assertEqual(visual_render.number(5e-7),"0.0000005")

    def test_visual_memory_survives_reporting_artifact_expiry(self):
        from nbn import writer_memory
        a=visuals.render_asset(self.con,run_id="test",candidate_id="item",kind="quote",preset="landscape",
            spec=self.spec(),evidence=self.evidence,alt_text="Synthetic test quote.",purpose="Memorable visual")
        writer_memory.prune(self.con)
        self.assertEqual(writer_memory.read(self.con,a["asset_id"])["visual"]["content_hash"],a["content_hash"])
        self.assertEqual(writer_memory.catalog(self.con,query="Memorable")["rows"][0]["context_id"],a["asset_id"])

    def fake_session(self):
        return SimpleNamespace(con=self.con,run_id="test",by_hash={"item":{}},messages=[],fetches={},
            _research_seconds_left=lambda:100,
            _tool_result=lambda ident,value,**kwargs:{"type":"tool_result","content":json.dumps(value),"is_error":kwargs.get("error",False)})

    def test_optional_image_http_failures_do_not_escape(self):
        from nbn import visual_tools
        session=self.fake_session()
        session.visual_state={"candidates":{"i":("item",{"url":"https://example.org/image.png"})},
            "inspections":0,"renders":0,"by_story":{},"image_bytes":0}
        block=SimpleNamespace(name="inspect_visual",id="b",input={"candidate_id":"item","visual_id":"i"})
        with patch.object(visuals,"download",side_effect=httpx.ReadTimeout("timeout")):
            result=visual_tools.dispatch(session,block)
        self.assertTrue(result["is_error"])
        self.assertEqual(json.loads(result["content"])["kind"],"visual_unavailable")

    def test_image_byte_budget_reserves_same_batch_returns(self):
        from nbn import visual_tools
        a=visuals.render_asset(self.con,run_id="test",candidate_id="item",kind="quote",preset="landscape",
            spec=self.spec(),evidence=self.evidence,alt_text="Test.",purpose="Test")
        session=self.fake_session(); block=SimpleNamespace(name="inspect_visual",id="b",
            input={"candidate_id":"item","visual_id":a["asset_id"]})
        pixels={"type":"image","source":{"data":"12345"}}
        with patch.object(visuals,"MAX_IMAGE_CONTEXT",7),patch.object(visuals,"image_block",return_value=pixels):
            self.assertIn("_pixels",visual_tools.dispatch(session,block))
            second=visual_tools.dispatch(session,block)
        self.assertTrue(second["is_error"]); self.assertNotIn("_pixels",second)

    def test_pdf_page_renders_actual_bounded_pixels(self):
        from tests.test_pdf_source import pdf_bytes
        from nbn import sources
        client=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(200,
            headers={"content-type":"application/pdf"},content=pdf_bytes(["Original page one.","Original page two."]))))
        with patch.object(visuals.httpx,"Client",return_value=client),patch.object(sources,"_assert_public_http_url"):
            pixels,metadata=visuals.pdf_page("https://example.org/doc.pdf",2,deadline=time.monotonic()+10)
        self.assertEqual(metadata["page"],2)
        self.assertEqual(visuals.check_image(pixels)[0],"image/png")
        self.assertEqual(metadata["reuse_status"],"unknown")
        with self.assertRaises(ValueError): visuals.pdf_page("https://example.org/doc.pdf",21,deadline=time.monotonic()+10)

    def test_asset_get_is_authenticated_and_read_only(self):
        from tests import test_desk
        from nbn import desk
        a=visuals.render_asset(self.con,run_id="test",candidate_id="item",kind="quote",preset="landscape",
            spec=self.spec(),evidence=self.evidence,alt_text="Test.",purpose="Test")
        before=self.con.total_changes
        with patch.object(config,"REPORT_TOKEN","test-key"),patch.object(store,"connect",side_effect=AssertionError("No GET migrations")):
            handler=test_desk.DeskTests().handler("/desk/visuals/"+a["asset_id"]+"?k=test-key")
            handler.do_GET(); handler.send_response.assert_called_once_with(200)
            self.assertEqual(handler.wfile.getvalue(),visuals.bytes_for(a))
            denied=test_desk.DeskTests().handler("/desk/visuals/"+a["asset_id"])
            denied.do_GET(); denied.send_response.assert_called_once_with(403)
        self.assertEqual(before,self.con.total_changes)

    def test_discovery_dedup_and_relative_images(self):
        body='<article><figure><img data-src="/chart.png" width="800"><figcaption>Chart credit</figcaption></figure><img src="/logo.png"></article><meta property="og:image" content="/chart.png">'
        rows=visuals.discover_html(body,"https://example.org/story")
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["url"],"https://example.org/chart.png")
        self.assertFalse(rows[0]["inspected"])
        self.assertEqual(rows[0]["reuse_status"],"unknown")


if __name__ == "__main__":
    unittest.main()
