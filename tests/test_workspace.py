"""Offline contracts for the approved run-first workspace and its recordings."""
import datetime as dt
import io
import json
import sqlite3
import time
import unittest
from unittest.mock import Mock, patch

from nbn import config, desk, desk_api, main, observations, store
from tests.support import temporary_store


def seed_run(con, rid, at, *, inventory=None, dossier=None, mode="live", status="completed"):
    con.execute("INSERT INTO newsroom_runs(run_id,status,mode,model,prompt_version,inventory_fingerprint,inventory_json,dossier_json,created_at,updated_at,completed_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (rid,status,mode,"grok-4.3","fixture","fixture",json.dumps(inventory or []),json.dumps(dossier or {}),at,at+10,at+10 if status=="completed" else None))
    con.commit()


def seed_usage(con, rid, at, cost, seat="newsdesk", source="provider_reported"):
    con.execute("INSERT INTO model_usage(run_id,seat,model,round,outcome,estimated_cost_usd,cost_source,rate_version,created_at) VALUES (?,?,?,1,'ok',?,?,'fixture',?)",
                (rid,seat,"grok-4.3",cost,source,at))
    con.commit()


class WorkspaceTests(unittest.TestCase):
    def test_savepoints_do_not_commit_or_rollback_caller_work(self):
        with temporary_store() as con:
            con.execute("INSERT INTO kv VALUES ('caller','pending')")
            observations.record(con,"cycle:a","writer_input",{"packet":{"value":"ok"}})
            self.assertTrue(con.in_transaction)
            con.rollback()
            self.assertIsNone(con.execute("SELECT v FROM kv WHERE k='caller'").fetchone())
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations").fetchone()[0],0)
            con.execute("DROP TABLE run_observations")
            con.commit()
            con.execute("INSERT INTO kv VALUES ('caller','still pending')")
            observations.record(con,"cycle:a","writer_input",{})
            self.assertTrue(con.in_transaction)
            self.assertEqual(con.execute("SELECT v FROM kv WHERE k='caller'").fetchone()[0],"still pending")

    def test_privacy_large_editor_packet_and_valid_json_limit(self):
        with temporary_store() as con, patch.object(config,"REPORT_TOKEN","private-owner-secret"):
            payload={"packet":{"posts":["x"*250000]},"owner_token":"never","thinking":"private","url":"https://example.test/?k=private-owner-secret","text":"private-owner-secret"}
            observations.record(con,"cycle:a","editor_input",payload)
            r=con.execute("SELECT * FROM run_observations").fetchone()
            self.assertLess(r["payload_bytes"],observations.ROW_BYTES)
            self.assertEqual(len(json.loads(r["payload_json"])["packet"]["posts"][0]),250000)
            self.assertNotIn("private-owner-secret",r["payload_json"])
            self.assertNotIn("thinking",r["payload_json"])
            observations.record(con,"cycle:a","tool",{"huge":["x"*200000]*3})
            r=con.execute("SELECT * FROM run_observations ORDER BY id DESC").fetchone()
            self.assertEqual(r["truncated"],1)
            self.assertIn("unavailable",json.loads(r["payload_json"]))

    def test_critical_capacity_is_reserved_and_retention_includes_abandoned_runs(self):
        with temporary_store() as con:
            for i in range(85): observations.record(con,"cycle:abandoned","tool",{"n":i})
            observations.record(con,"cycle:abandoned","editor_result",{"decisions":[]})
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='tool'").fetchone()[0],80)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='trace_limit'").fetchone()[0],1)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE kind='editor_result'").fetchone()[0],1)
            con.execute("UPDATE run_observations SET at=?",(time.time()-15*86400,));con.commit()
            observations.prune(con)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE payload_json IS NOT NULL").fetchone()[0],0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM run_observations WHERE expired=1").fetchone()[0],82)

    def test_zero_poll_is_success_and_failure_preserves_last_success(self):
        with temporary_store() as con:
            observations.source_poll(con,"rss:A","A","rss",count=0)
            r=dict(con.execute("SELECT * FROM source_poll_health").fetchone())
            self.assertEqual((r["outcome"],r["result_count"]),("ok",0))
            observations.source_poll(con,"rss:A","A","rss",error="TimeoutError")
            failed=dict(con.execute("SELECT * FROM source_poll_health").fetchone())
            self.assertEqual(failed["succeeded_at"],r["succeeded_at"])
            self.assertIsNone(failed["result_count"])
            self.assertEqual(failed["outcome"],"error")

    def test_navigation_stable_ties_across_midnight_and_zero_output(self):
        with temporary_store() as con:
            for rid,at,mode in (("cycle:old",100,"live"),("cycle:a",200,"live"),("cycle:b",200,"live"),("replay:c",300,"live"),("cycle:shadow",400,"shadow")):
                seed_run(con,rid,at,mode=mode)
            row,nav=desk_api.run_window(con)
            self.assertEqual(row["run_id"],"cycle:b")
            self.assertEqual(nav["older"],"cycle:a")
            row,nav=desk_api.run_window(con,"cycle:a","older")
            self.assertEqual(row["run_id"],"cycle:old")
            self.assertIsNone(nav["older"])
            self.assertEqual(nav["newer"],"cycle:a")
            with self.assertRaises(LookupError):desk_api.run_window(con,"cycle:shadow")

    def test_exact_packet_not_current_mutable_item_and_editor_not_clobbered(self):
        with temporary_store() as con:
            con.execute("INSERT INTO items(url_hash,title,source,url,first_seen) VALUES ('a','Changed title','Changed source','https://example.test/new',10)");con.commit()
            seed_run(con,"cycle:a",10,inventory=["a"],dossier={"stories":[{"story_id":"story-a","member_candidate_ids":["a"],"post":"Writer copy","story_key":"event","reader_value":"Worth knowing"}]})
            packet={"intake_board":[{"candidate_id":"a","headline_or_post":"Original lead","source":{"label":"Original source"},"intake_url":"https://example.test/original"}],"run_brief":{"assignment":"Actual final assignment"}}
            observations.record(con,"cycle:a","writer_input",{"packet":packet})
            observations.record(con,"cycle:a","editor_applied",{"verdict":"revise","reason":"Clearer lede","post":"Editor copy","origin":"recovery","canonical_key":"event"},ref="story-a")
            row,_=desk_api.run_window(con);data=desk_api.run_detail(con,row)
            self.assertEqual(data["candidates"][0]["title"],"Original lead")
            self.assertEqual(data["packet"],packet)
            self.assertEqual(data["stories"][0]["editor"]["origin"],"recovery")
            self.assertEqual(data["stories"][0]["editor"]["post"],"Editor copy")
            con.execute("UPDATE run_observations SET payload_json=? WHERE kind='editor_applied'",
                        (json.dumps({"verdict":"publish","post":"Writer copy","origin":"omitted_fallback"}),));con.commit()
            self.assertEqual(desk_api.run_detail(con,row)["stories"][0]["outcome"],"Editor fallback")
            con.execute("UPDATE run_observations SET expired=1,payload_json=NULL");con.commit()
            data=desk_api.run_detail(con,row)
            self.assertFalse(data["packet_recorded"])
            self.assertEqual(data["candidates"][0]["provenance"],"retained_intake_not_exact_packet")
            self.assertIsNone(data["stories"][0]["editor"])

    def test_background_excluded_from_writer_only_if_applied(self):
        with temporary_store() as con:
            for h in "ab":con.execute("INSERT INTO items(url_hash,title) VALUES (?,?)",(h,h))
            con.commit();seed_run(con,"cycle:a",10,inventory=["a","b"])
            store.save_desk_preparations(con,[{"run_id":"cycle:a","item_hash":"b","effective_route":"background"}],mode="enforce")
            row,_=desk_api.run_window(con);result=desk_api.run_detail(con,row)
            self.assertIsNone(result["delivered_count"])
            self.assertEqual(result["advanced_estimate"],1)
            self.assertEqual(result["background"][0]["id"],"b")
            self.assertEqual([s["id"] for s in result["stories"]],["lead:a"])

    def test_cost_units_scope_coverage_and_unknown(self):
        def ts(day):return dt.datetime.fromisoformat(day).replace(tzinfo=desk.TZ).timestamp()
        with temporary_store() as con:
            seed_run(con,"cycle:a",ts("2026-09-06T08:00:00"))
            seed_usage(con,"cycle:old",ts("2026-08-01T12:00:00"),1)
            seed_usage(con,"cycle:a",ts("2026-09-06T08:01:00"),2)
            seed_usage(con,"cycle:a",ts("2026-09-06T08:02:00"),1,"editor")
            seed_usage(con,"cycle:a",ts("2026-09-06T08:03:00"),.25,"rss_triage")
            seed_usage(con,"cycle:filtered",ts("2026-09-06T08:04:00"),.1,"desk_prep")
            seed_usage(con,"cycle:a",ts("2026-09-06T08:05:00"),0,"editor","unknown")
            seed_usage(con,"replay:case",ts("2026-09-06T08:06:00"),50)
            seed_usage(con,"unclassified",ts("2026-09-06T08:07:00"),20)
            cost=desk_api.costs(con,ts("2026-09-06T12:00:00"));p=cost["periods"]["today"]
            self.assertAlmostEqual(p["cost"],3.35)
            self.assertEqual(p["runs"],1);self.assertEqual(p["per_run"],3)
            self.assertAlmostEqual(p["shared_cost"],.35)
            self.assertEqual(p["unknown"],1)
            self.assertEqual(cost["excluded"]["cost"],50)
            self.assertEqual(cost["unclassified"]["cost"],20)
            self.assertEqual(cost["averages"]["day"]["count"],35)
            self.assertEqual(cost["averages"]["day"]["value"],0)
            self.assertEqual(cost["averages"]["week"]["count"],4)
            self.assertIsNone(cost["averages"]["month"]["value"])

    def test_workspace_routes_auth_escaping_readonly_and_empty_views(self):
        with temporary_store() as con, patch.object(config,"REPORT_TOKEN","owner-key"):
            seed_run(con,"cycle:a",10,dossier={"run_note":"<script>alert('x')</script>"})
            before=con.total_changes
            for view in ("newsroom","intake","outputs","system"):
                h=main.Health.__new__(main.Health);h.path=f"/desk/api/workspace?k=owner-key&view={view}"
                h.wfile=io.BytesIO();h.send_response=Mock();h.send_header=Mock();h.end_headers=Mock()
                with patch.object(store,"connect",side_effect=AssertionError("GET must not migrate")):
                    h.do_GET()
                h.send_response.assert_called_once_with(200)
                self.assertEqual(json.loads(h.wfile.getvalue())["version"],1)
                self.assertNotIn("owner-key",h.wfile.getvalue().decode())
            self.assertEqual(con.total_changes,before)
            for route in ("/desk/api/workspace","/desk/assets/workspace.js","/desk/assets/workspace.css"):
                h.path=route;h.send_response.reset_mock();h.do_GET();h.send_response.assert_called_once_with(403)

    def test_publication_requires_confirmation(self):
        card=desk_api.output_card({"mode":"IMMEDIATE","publisher_status":"publishing"})
        self.assertEqual(card["state"],"Publishing")
        self.assertEqual(desk_api.output_card({"mode":"IMMEDIATE","publisher_status":"published"})["state"],"Delivery requested")
        self.assertEqual(desk_api.output_card({"mode":"DRAFT","publisher_status":"published","confirmed_at":10})["state"],"Published")
        self.assertEqual(desk_api.output_card({"mode":"DRAFT","publisher_status":"deleted"})["state"],"Deleted")
        self.assertEqual(desk_api.output_card({"mode":"DRAFT","publisher_status":"planned"})["state"],"Planned")

    def test_full_editor_batch_and_pruned_unknown_counts(self):
        with temporary_store() as con:
            seed_run(con,"cycle:full",10)
            for i in range(6):observations.record(con,"cycle:full","editor_input",{"packet":i})
            for i in range(25):observations.record(con,"cycle:full","editor_applied",{"verdict":"publish","origin":"initial"},ref=str(i))
            row,_=desk_api.run_window(con)
            result=desk_api.run_detail(con,row)
            self.assertEqual(sum(a["kind"]=="editor_applied" for a in result["artifacts"]),25)
            self.assertIsNone(result["cost"])
            con.execute("UPDATE newsroom_runs SET dossier_json=NULL,inventory_json='[]'");con.commit()
            row,_=desk_api.run_window(con);result=desk_api.run_detail(con,row)
            self.assertIsNone(result["proposal_count"])
            self.assertIsNone(result["captured"])
            self.assertIsNone(result["delivered_count"])


if __name__ == "__main__":unittest.main()
