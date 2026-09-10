import unittest
from unittest.mock import patch
from nbn import config, reporter_api as api, reporter_store as rs
from tests.support import temporary_store


class ReporterAPITests(unittest.TestCase):
    def test_explicit_enable_and_distinct_tokens(self):
        with patch.multiple(config, OPERATING_MODE="infrastructure", REPORTER_API_ENABLED=True,
                            REPORTER_TOKEN="r"*40, REPORTER_CONTROL_TOKEN="c"*40):
            self.assertEqual(api.authorized("Bearer " + "r"*40), "reporter")
            self.assertEqual(api.authorized("Bearer " + "c"*40), "control")
            self.assertIsNone(api.authorized("Bearer wrong"))
            with patch.object(config, "REPORTER_API_ENABLED", False):
                self.assertIsNone(api.authorized("Bearer " + "r"*40))
            with patch.object(config, "REPORTER_CONTROL_TOKEN", "r"*40):
                self.assertIsNone(api.authorized("Bearer " + "r"*40))

    def test_reporter_cannot_control_or_impersonate_owner(self):
        with temporary_store() as con:
            for name in ("start", "stop", "heartbeat", "record", "message", "delivered", "coverage_sync", "delivery_maintenance"):
                with self.assertRaises(PermissionError): api.dispatch(con, "POST", name, "reporter", {})
            with self.assertRaises(ValueError): api.dispatch(con, "POST", "publish", "control", {})
            with self.assertRaises(PermissionError): api.dispatch(con, "POST", "tool", "control", {})
            api.dispatch(con, "POST", "start", "control", {"shift_id":"test", "worker_id":"local"})
            api.dispatch(con, "POST", "message", "control", {"shift_id":"test", "record_id":"m1", "payload":{"text":"lead"}, "sender":"owner"})
            self.assertEqual(rs.records(con)["rows"][0]["sender"], "main_assistant")

    def test_coverage_poll_timestamp_does_not_wake_model(self):
        import json
        with temporary_store() as con:
            def add(stamp):
                with con:
                    con.execute("INSERT OR REPLACE INTO reporter_remote_coverage VALUES ('1','draft',0,NULL,?,?)",
                        (stamp,json.dumps({"id":"1","texts":["hello"],"comments_checked_at":stamp})))
            add(1); first=api.pulse(con)
            add(2); second=api.pulse(con)
            self.assertEqual(first["coverage_hash"],second["coverage_hash"])
