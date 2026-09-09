"""Sprint 0072: visible retained research, usable context, honest transport evidence."""
import copy
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx

from nbn import brain, config, desk_prep, editor, main, newsroom, perception, publisher, source_policy, store, writer_memory
from tests.support import temporary_store
from tests.test_compact_desk import crowded_desk
from tests.test_editorial_v2 import candidate
from tests.test_reporter_writer import session
from tests.test_perception import article, transport


def notebook(con, key, at=None):
    at = at or time.time()
    con.execute("INSERT INTO newsroom_story_memory(canonical_key,state,created_at,updated_at,expires_at,attempts_json) "
                "VALUES(?,'held',?,?,?,?)", (key, at, at, time.time() + 86400,
                json.dumps([{"at": at, "proposed_post": "Unaccepted proposal", "members": []}])))


def post(con, key, body, *, mode="DRAFT", status="draft", created=None, cls="secondary"):
    at = created or time.time()
    return con.execute("INSERT INTO posts(story_key,body,mode,publisher_status,created,class,confirmed_at,"
        "publisher_synced_at,receipt_url) VALUES(?,?,?,?,?,?,?,?,?)",
        (key, body, mode, status, at, cls, at if status == "published" else None,
         at+5, "https://www.sec.gov/report")).lastrowid


class PerceptionAdoptionTests(unittest.TestCase):
    def test_crowded_packet_keeps_hints_and_exact_match_beyond_first_catalog_page(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            for i in range(105):
                notebook(con, f"recent-{i}")
            notebook(con, "previous-event-0", time.time()-86400)
            desk = crowded_desk(con)
            for item in desk.inventory[:-1]:
                perception.save_article(con, {**article(time.time()), "url": item["url"],
                    "canonical_url": source_policy.normalize_url(item["url"]), "text": "Useful dated source text."}, item["url_hash"])
            con.commit()
            packet = desk._initial_packet()
            self.assertLessEqual(newsroom._json_bytes(packet), 65536)
            self.assertEqual(len(packet["intake_board"]), 25)
            for row in packet["intake_board"][:-1]:
                hint = row["available_perception_text"]
                self.assertTrue(hint["artifact_id"])
                self.assertTrue(hint["published_at"])
                self.assertIn("owner_override", row)
            self.assertFalse(packet["intake_board"][-1].get("available_perception_text"))
            catalog = packet["memory_catalog"]
            self.assertGreaterEqual(len(catalog["rows"]), 2)
            self.assertEqual(catalog["matching_notebooks"][0]["context_id"], "notebook:previous-event-0")
            page = writer_memory.catalog(con, offset=catalog["next_offset"])
            self.assertFalse({r["context_id"] for r in catalog["rows"]} &
                             {r["context_id"] for r in page["rows"]})
            self.assertIsNotNone(writer_memory.read(con, catalog["matching_notebooks"][0]["context_id"]))

    def test_accepted_copy_expands_beyond_lede_and_keeps_published_separate(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            old = post(con, "covered-event-0", "Earlier confirmed copy.", status="published", created=time.time()-60)
            full = "Accepted first paragraph. " * 35 + "EXACT FOLLOWUP DETAIL"
            new = post(con, "covered-event-0", full)
            store.register_story_alias(con, "current-alias", "covered-event-0")
            desk = crowded_desk(con)
            desk.inventory[0]["story_key"] = "current-alias"
            packet = desk._initial_packet()
            match = packet["matching_accepted_output"][0]
            self.assertEqual(match["id"], new)
            self.assertEqual(match["confirmed_output"]["id"], old)
            opened = desk._read_desk_context([match["context_id"]])["rows"][0]["accepted_output"]
            self.assertEqual(opened["body"], full)
            self.assertIn("manual Typefully edits may differ", opened["copy_provenance"])
            self.assertIsNone(opened["confirmed_at"])
            self.assertGreater(opened["publisher_synced_at"], opened["created"])
            self.assertEqual(opened["confirmed_output"]["body"], "Earlier confirmed copy.")

    def test_alias_and_live_output_rules_not_proposals(self):
        with temporary_store() as con:
            notebook(con, "root")
            post(con, "root", "Accepted")
            store.register_story_alias(con, "alias", "root")
            self.assertEqual(writer_memory.publication(con, "alias")["body"], "Accepted")
            con.execute("UPDATE story_key_aliases SET updated_at=?", (time.time()-4*86400,))
            self.assertIsNone(writer_memory.publication(con, "alias"))
            self.assertEqual(writer_memory.matching_notebooks(con, ["alias"]), [])
            for key, mode, status, cls in [("deleted", "DRAFT", "deleted", "secondary"),
                    ("eval", "DRAFT", "draft", "eval"), ("replay:x", "DRAFT", "draft", "secondary")]:
                post(con, key, "Not usable", mode=mode, status=status, cls=cls)
                self.assertIsNone(writer_memory.publication(con, key))
            notebook(con, "proposal")
            self.assertIsNone(writer_memory.read(con, "notebook:proposal")["current_output"])
            self.assertIsNone(writer_memory.publication(con, "missing"))
            con.execute("UPDATE newsroom_story_memory SET attempts_json='[]' WHERE canonical_key='proposal'")
            self.assertEqual(writer_memory.matching_notebooks(con, ["proposal"]), [])

    def test_whole_unicode_envelope_and_exact_omissions(self):
        with temporary_store() as con:
            desk = session(con)
            desk.context_rows = {"a": {"kind": "test", "text": "₿"*4500},
                                 "b": {"kind": "test", "text": "😀"*1000}}
            first = desk._read_desk_context(["a", "b"])
            self.assertEqual(first["capacity_omitted_ids"], ["b"])
            self.assertEqual(first["already_read_ids"], [])
            self.assertLessEqual(newsroom._json_bytes(first), config.COMPACT_DESK_RETRIEVAL_BYTES)
            self.assertEqual(desk.context_retrieval_bytes, newsroom._json_bytes(first))
            second = desk._read_desk_context(["a", "b"])
            self.assertEqual(second["already_read_ids"], ["a"])
            self.assertEqual(second["capacity_omitted_ids"], [])
            count = desk.context_retrieval_calls
            repeated = desk._read_desk_context(["a", "b"])
            self.assertEqual(repeated["rows"], [])
            self.assertEqual(repeated["omitted_for_capacity"], 0)
            self.assertEqual(desk.context_retrieval_calls, count)
            self.assertEqual(repeated["remaining"]["calls"], 4-count)
            desk.context_retrieval_calls = 4
            desk.context_rows["c"] = {"kind": "test"}
            exhausted = desk._read_desk_context(["a", "c"])
            self.assertEqual(exhausted["capacity_omitted_ids"], ["c"])
            self.assertEqual(exhausted["already_read_ids"], ["a"])
            self.assertEqual(exhausted["remaining"]["calls"], 0)

    def test_search_accounting_and_nonzero_page_offset(self):
        with temporary_store() as con:
            desk = session(con)
            payload = {"offset": 40, "next_offset": 60,
                       "rows": [{"context_id": str(i), "text": "漢"*2000} for i in range(20)]}
            result = desk._context_result(payload)
            self.assertLessEqual(newsroom._json_bytes(result), config.COMPACT_DESK_RETRIEVAL_BYTES)
            self.assertEqual(result["next_offset"], 40+len(result["rows"]))
            self.assertEqual(result["capacity_omitted_ids"], [str(i) for i in range(len(result["rows"]), 20)])
            self.assertEqual(desk.context_retrieval_bytes, newsroom._json_bytes(result))
            self.assertLessEqual(result["remaining"]["bytes_total"],
                config.COMPACT_DESK_RETRIEVAL_TOTAL_BYTES-desk.context_retrieval_bytes)
            desk.context_retrieval_bytes = config.COMPACT_DESK_RETRIEVAL_TOTAL_BYTES - 20
            exhausted = desk._context_result({"offset": 40, "rows": [{"context_id": "notebook:known"}]})
            self.assertEqual(exhausted["capacity_omitted_ids"], ["notebook:known"])
            self.assertEqual(exhausted["next_offset"], 40)

    def test_regulatory_textual_error_is_not_empty_and_prep_gets_owner_clarification(self):
        error = "Error: no regulatory documents could be returned because the backend is unavailable."
        for operation in ("regulatory", "coverage"):
            with self.assertRaises(ValueError):
                perception.parse_mcp(json.dumps({"result": {"content": [{"type": "text", "text": error}]}}), operation, {}, time.time())
        self.assertIn("Bessent or Warsh", desk_prep.SYSTEM)
        self.assertIn("attribution", desk_prep.SYSTEM)
        self.assertIn("First coverage by NBN does not make an old disclosure NEW", newsroom.NEWSROOM_V2_SYSTEM)

    def test_empty_fiu_sse_is_success_cached_60_seconds_not_cooldown(self):
        # Recorded successful content from utility-2, September 9; tool suggestions are stripped.
        body = '## Regulatory Intelligence: "FIU"\n\nNo regulatory documents found for this query and date range.\n\n**36 agencies tracked:** SEC, ECB, Federal Reserve, BIS, CFTC, FCA, HKMA, MAS Singapore, ESMA, IMF, and 26 more.\n\nTry broadening your date range or simplifying your query.\n\n---\n**Suggested next steps:**\n- See how media is covering "FIU" beyond regulatory sources\n- Track narrative trends related to FIU-IND activity\n- Check enforcement actions (restrictive stance)\n\n---\n*Regulatory data from [Perception](https://perception.to) — 36 agencies, full document text including PDFs.*'
        sse = "event: message\ndata: " + json.dumps({"result": {"content": [{"type": "text", "text": body}]},
            "jsonrpc": "2.0", "id": "686f6d4d-87c6-49c7-87a3-2c826447c22e"}) + "\n\n"
        client = transport(httpx.Response(200, text=sse))
        with temporary_store() as con, patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(perception.httpx, "Client", return_value=client), \
                patch.object(perception.time, "time", return_value=10000):
            result = perception.request(con, "mcp", "regulatory", {"q": "FIU"})
            self.assertTrue(result["ok"])
            self.assertEqual((result["rows"], result["total"], result["partial"]), ([], 0, False))
            self.assertTrue(perception.request(con, "mcp", "regulatory", {"q": "FIU"})["cached"])
            self.assertEqual(client.stream.call_count, 1)
            self.assertEqual(con.execute("SELECT expires_at FROM perception_cache").fetchone()[0], 10060)
            self.assertEqual(perception.state(con, "mcp_cooldown"), {})

    def test_writer_next_request_and_actual_editor_payload_receive_retained_text(self):
        with temporary_store() as con, patch.object(config, "EDITORIAL_ENGINE", "v2"), \
                patch.object(config, "PERCEPTION_API_KEY", "test"), \
                patch.object(config, "PERCEPTION_TOOLS_ENABLED", True), \
                patch.object(config, "RUN_NEWSROOM_MODE", "live"), \
                patch.object(brain, "consume_model_call"), patch.object(brain, "activate_model_reservation"):
            item = store.upsert_new_items(con, [candidate()])[0]
            desk = session(con)
            desk.all_inventory = [item]
            desk.inventory = [item]
            desk.by_hash = {item["url_hash"]: item}
            url = item["url"]
            text = "The SEC announced a Bitcoin policy change. RETAINED-ONLY-EVIDENCE."
            perception.save_article(con, {**article(time.time(), text), "url": url, "canonical_url": source_policy.normalize_url(url)})
            con.commit()
            usage = SimpleNamespace(input_tokens=100, output_tokens=50, cache_creation_input_tokens=0,
                cache_read_input_tokens=0, cache_creation=None, native_web_calls=0, native_x_calls=0)
            seen = []
            def writer(**kwargs):
                seen.append(copy.deepcopy(kwargs))
                if len(seen) == 1:
                    block = SimpleNamespace(type="tool_use", id="read", name="perception_article",
                        input={"url": url, "refresh": False})
                else:
                    returned = json.loads(kwargs["messages"][-1]["content"][0]["content"])
                    self.assertIn("RETAINED-ONLY-EVIDENCE", json.dumps(returned))
                    fid = returned["fetch_id"]
                    block = SimpleNamespace(type="tool_use", id="dossier", name="submit_editorial_dossier",
                        input={"decisions": [{"candidate_id": item["url_hash"], "disposition": "publish", "story_id": "sec"}],
                            "stories": [{"story_id": "sec", "story_key": "sec-policy", "member_candidate_ids": [item["url_hash"]],
                                "post": "The SEC announced a Bitcoin policy change.", "selected_fetch_id": fid,
                                "evidence_fetch_ids": [fid]}], "run_note": "Supported by returned source."})
                return SimpleNamespace(content=[block], usage=usage, stop_reason="tool_use")
            desk.client = Mock()
            desk.client.messages.create.side_effect = writer
            editor_seen = []
            def edit(*args, **kwargs):
                payload = json.loads(args[2])
                editor_seen.append(payload)
                self.assertEqual(payload["evidence_catalog"][0]["text"], text)
                self.assertEqual(payload["candidates"][0]["selected_evidence_ref"], payload["evidence_catalog"][0]["evidence_ref"])
                return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps({"decisions": [
                    {"story_id": "sec", "verdict": "drop", "reason": "test only"}]}))], usage=usage, stop_reason="end_turn")
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            with patch.object(newsroom, "start_session", return_value=desk), \
                    patch.object(brain, "_create", side_effect=edit), patch.object(publisher, "publish") as publish, \
                    patch.object(perception, "request") as network:
                outcome = main._run_editorial_v2(con, lease_owner="test-owner", pipeline_run_id=desk.run_id,
                    inventory=[item], pending=[item], result={k: 0 for k in ("posted", "held", "skipped", "drafted", "taped", "uncertain", "failed")},
                    theme_snapshot=[], overrides={}, run_started=time.time(), reservation="test")
                network.assert_not_called()
                publish.assert_not_called()
            self.assertEqual(len(seen), 2)
            self.assertEqual(len(editor_seen), 1, (outcome, [dict(r) for r in con.execute("SELECT * FROM newsroom_story_commits")]))
            calls = [json.loads(r[0]) for r in con.execute("SELECT payload_json FROM run_observations WHERE kind='writer_call' AND phase='started'")]
            self.assertEqual(calls[1]["last_tool_receipts_supplied"][0]["text_characters"], len(text))


if __name__ == "__main__":
    unittest.main()
