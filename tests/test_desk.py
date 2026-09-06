import io
import json
import sqlite3
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from nbn import config, desk, main, store
from tests.support import temporary_store


class DeskTests(unittest.TestCase):
    def opt(self, **kwargs):
        return desk.options({"d": ["2026-09-06"], **{k: [str(v)] for k, v in kwargs.items()}})

    def handler(self, path):
        h = main.Health.__new__(main.Health)
        h.path = path
        h.wfile = io.BytesIO()
        h.send_response = Mock()
        h.send_header = Mock()
        h.end_headers = Mock()
        return h

    def add_post(self, con, created, mode="DRAFT", **values):
        row = {"created": created, "mode": mode, "body": "A useful Bitcoin development.",
               "class": "secondary", "story_key": "test-event", **values}
        con.execute("INSERT INTO posts(" + ",".join(row) + ") VALUES (" + ",".join("?" for _ in row) + ")", list(row.values()))
        con.commit()

    def usage(self, con, created, cost):
        con.execute("INSERT INTO model_usage(run_id,seat,model,round,outcome,estimated_cost_usd,rate_version,created_at) VALUES ('test','newsroom','grok-4.3',1,'ok',?,'test',?)", (cost, created))
        con.commit()

    def test_auth_for_every_route_and_unknown_children(self):
        with patch.object(config, "REPORT_TOKEN", "owner-key"):
            for path in ("/desk", "/desk/intake", "/desk/api/snapshot", "/desk/assets/desk.js", "/desk/system-guide.pdf", "/desk/nope"):
                h = self.handler(path)
                with patch.object(store, "connect", side_effect=AssertionError("migration forbidden")):
                    h.do_GET()
                h.send_response.assert_called_once_with(403)
        with patch.object(config, "REPORT_TOKEN", ""):
            h = self.handler("/desk?k=")
            h.do_GET()
            h.send_response.assert_called_once_with(403)

    def test_unknown_authorized_path_does_not_fall_into_health(self):
        with patch.object(config, "REPORT_TOKEN", "key"):
            for path in ("/desk/unknown?k=key", "/desk/assets/../../SYSTEM.md?k=key"):
                h = self.handler(path)
                h.do_GET()
                h.send_response.assert_called_once_with(404)

    def test_readonly_connection_never_migrates_or_writes(self):
        with temporary_store() as con:
            before = con.total_changes
            with patch.object(store, "connect", side_effect=AssertionError("migration forbidden")):
                with desk.reader() as read:
                    with self.assertRaises(sqlite3.OperationalError):
                        read.execute("INSERT INTO kv(k,v) VALUES ('oops','x')")
                    self.assertEqual(read.execute("PRAGMA query_only").fetchone()[0], 1)
            self.assertEqual(before, con.total_changes)

    def test_all_views_and_json_are_readonly_bounded_and_private(self):
        with temporary_store() as con, patch.object(config, "REPORT_TOKEN", "key"):
            before = con.total_changes
            for view in desk.VIEWS:
                for path in (f"/desk/{view}?k=key&d=2026-09-06", f"/desk/api/snapshot?k=key&view={view}&d=2026-09-06"):
                    h = self.handler(path)
                    with patch.object(store, "connect", side_effect=AssertionError("must be read-only")):
                        h.do_GET()
                    h.send_response.assert_called_once_with(200)
                    h.send_header.assert_any_call("Cache-Control", "no-store")
                    h.send_header.assert_any_call("Referrer-Policy", "no-referrer")
                    text = h.wfile.getvalue().decode()
                    self.assertNotIn("owner_token", text)
                    self.assertNotIn("dossier_json", text)
                    if "/api/" in path:
                        self.assertEqual(set(json.loads(text)), {"html", "generated_at", "worker"})
            self.assertEqual(con.total_changes, before)

    def test_sent_is_not_confirmed_and_replay_is_excluded(self):
        with temporary_store() as con:
            opt = self.opt(); start = opt["start"]
            self.add_post(con, start + 1, "IMMEDIATE")
            self.add_post(con, start - 100, "IMMEDIATE", publisher_status="published", confirmed_at=start + 5)
            self.add_post(con, start + 2, "DRAFT")
            self.add_post(con, start + 3, "IMMEDIATE", publisher_status="published", confirmed_at=start + 5, **{"class": "replay"})
            self.add_post(con, start + 4, "DRAFT", story_key="replay:test")
            self.add_post(con, start + 5, "DRAFT", body="[REPLAY] isolated evaluation")
            data = desk.base_snapshot(con, opt, {"started": start}, start + 20)
            self.assertEqual(data["confirmed"], 1)
            self.assertEqual(sum(data["outputs"].values()), 2)
            rendered = desk.outputs(con, opt)
            self.assertIn("not confirmed", rendered)
            self.assertNotIn("isolated evaluation", rendered)
            self.assertIn("Not a complete Typefully account inventory", rendered)

    def test_historical_costs_have_end_bound(self):
        with temporary_store() as con:
            opt = self.opt()
            self.usage(con, opt["start"] + 1, 1.25)
            self.usage(con, opt["end"], 100)
            self.assertEqual(desk.base_snapshot(con, opt, {}, time.time())["usage"]["cost"], 1.25)
            self.assertEqual(store.model_usage_summary(con, opt["start"], until=opt["end"])["estimated_cost_usd"], 1.25)
            self.assertEqual(store.model_usage_summary(con, opt["start"])["calls"], 2)

    def test_worker_state_uses_current_process_not_old_saved_checkpoint(self):
        with temporary_store() as con:
            now = time.time()
            store.kv_set(con, "worker:last_success", str(now))
            opt = self.opt()
            self.assertEqual(desk.base_snapshot(con, opt, {"started": now}, now)["worker"], "starting")
            self.assertEqual(desk.base_snapshot(con, opt, {"started": now - 900}, now)["worker"], "stale")
            self.assertEqual(desk.base_snapshot(con, opt, {"last_cycle_ts": now - 5}, now)["worker"], "healthy")
            self.assertEqual(desk.base_snapshot(con, opt, {"last_cycle_ts": now, "last_error": "secret"}, now)["worker"], "error")

    def test_html_and_unsafe_external_urls_are_escaped(self):
        with temporary_store() as con:
            opt = self.opt()
            con.execute("INSERT INTO items(url_hash,source,title,url,first_seen,status,note) VALUES ('bad','<img src=x>','<script>alert(1)</script>','javascript:alert(1)',?,'held','<svg/onload=1>')", (opt["start"] + 1,))
            body = desk.intake(con, opt)
            self.assertNotIn("<script>", body)
            self.assertNotIn("javascript:", body)
            self.assertIn("&lt;script&gt;", body)
            for url in ("data:text/html,foo", "//example.com", "https://a:b@example.com", "https://example.com/\nfoo"):
                self.assertEqual(desk.safe_url(url), "")

    def test_pagination_filters_and_date_errors(self):
        with temporary_store() as con:
            opt = self.opt()
            for i in range(45):
                con.execute("INSERT INTO items(url_hash,source,title,first_seen,status) VALUES (?,?,?,?,?)", (str(i), "Test", f"Card {i}", opt["start"] + i, "held"))
            first = desk.intake(con, opt)
            self.assertEqual(first.count('<article class="card">'), 40)
            self.assertIn("Older →", first)
            self.assertEqual(desk.intake(con, self.opt(page=2)).count('<article class="card">'), 5)
            self.assertIn("No matching", desk.intake(con, self.opt(state="new")))
            self.assertEqual(desk.intake(con, self.opt(q="Card 44")).count('<article class="card">'), 1)
        for kw in ({"d": "nonsense"}, {"page": 0}, {"page": 251}, {"page": "nope"}):
            with self.assertRaises(ValueError):
                self.opt(**kw)

    def test_run_detail_projects_decisions_editor_and_current_status_only(self):
        with temporary_store() as con:
            opt = self.opt()
            store.start_newsroom_run(con, "run-test", "live", "grok-4.3", "test", ["candidate"])
            con.execute("INSERT INTO items(url_hash,title,status,first_seen) VALUES ('candidate','A story','skipped',?)", (opt["start"],))
            dossier = {"decisions": [{"candidate_id": "candidate", "disposition": "defer", "reason": "Needs one better receipt"}], "raw_evidence": "PRIVATE-RESEARCH", "owner_token": "SECRET"}
            con.execute("UPDATE newsroom_runs SET status='researching',dossier_json=?,updated_at=?", (json.dumps(dossier), opt["start"]))
            store.init_newsroom_story_commits(con, "run-test", ["story"], "digest")
            store.set_newsroom_story_state(con, "run-test", "story", "held", details={"editor": {"verdict": "drop", "reason": "Already covered"}, "owner_token": "SECRET"})
            text = desk.run_detail(con, "run-test", opt["day"])
            self.assertIn("A checkpoint is not an exact live stage", text)
            for expected in ("Needs one better receipt", "Already covered", "defer", "skipped"):
                self.assertIn(expected, text)
            self.assertNotIn("PRIVATE-RESEARCH", text)
            self.assertNotIn("SECRET", text)

    def test_service_error_is_safe_and_not_blank_healthy(self):
        with patch.object(config, "REPORT_TOKEN", "key"), patch.object(desk, "reader", side_effect=sqlite3.OperationalError("secret database path")):
            h = self.handler("/desk/api/snapshot?k=key")
            h.do_GET()
            h.send_response.assert_called_once_with(503)
            self.assertNotIn(b"secret database path", h.wfile.getvalue())

    def test_carryover_run_item_links_use_its_first_seen_day(self):
        with temporary_store() as con:
            opt = self.opt()
            store.start_newsroom_run(con, "today-run", "live", "grok-4.3", "test", ["yesterday"])
            con.execute("INSERT INTO items(url_hash,title,status,first_seen) VALUES ('yesterday','Carried over','held',?)", (opt["start"] - 60,))
            text = desk.run_detail(con, "today-run", opt["day"])
            self.assertIn("d=2026-09-05&amp;q=yesterday", text)
            self.assertIn("Carried over", desk.intake(con, self.opt(d="2026-09-05", q="yesterday")))

    def test_assets_and_fixed_pdf_route(self):
        with patch.object(config, "REPORT_TOKEN", "key"):
            for path in ("assets/desk.css", "assets/desk.js"):
                h = self.handler("/desk/" + path + "?k=key")
                h.do_GET()
                h.send_response.assert_called_once_with(200)
            with patch.object(desk, "GUIDE") as guide:
                guide.read_bytes.return_value = b"%PDF-test"
                h = self.handler("/desk/system-guide.pdf?k=key")
                h.do_GET()
                h.send_response.assert_called_once_with(200)
                self.assertEqual(h.wfile.getvalue(), b"%PDF-test")


if __name__ == "__main__":
    unittest.main()
