import json
import os
import subprocess
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import patch

from nbn import config, main, publisher, reporter_intake, sources, store
from tests.support import item, temporary_store


class ReporterIntakeTests(unittest.TestCase):
    def test_infrastructure_bypasses_all_legacy_cycle_and_scheduled_work(self):
        with temporary_store() as con, ExitStack() as stack:
            stack.enter_context(patch.object(config, "OPERATING_MODE", "infrastructure"))
            stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", True))
            # Even an accidentally retained old autopost knob cannot execute that path.
            stack.enter_context(patch.object(config, "NODE_READ_TOKEN", "retained"))
            stack.enter_context(patch.object(config, "AUDIT_UTC", "12:00"))
            legacy = stack.enter_context(patch.object(main, "_cycle_locked", side_effect=AssertionError("legacy")))
            sync = stack.enter_context(patch.object(publisher, "reconcile_publications", return_value={}))
            stack.enter_context(patch.object(main.briefing, "maybe_run", side_effect=AssertionError("Block")))
            stack.enter_context(patch.object(reporter_intake.node_discovery, "ingest", return_value={}))
            stack.enter_context(patch.object(sources, "fetch_feeds", return_value=[item()]))
            for name in ("fetch_edgar", "fetch_x", "fetch_perception"):
                stack.enter_context(patch.object(sources, name, return_value=[]))
            result = main.worker_iteration(con)
            self.assertEqual(result["operating_mode"], "infrastructure")
            self.assertEqual(result["new"], 1)
            self.assertEqual(con.execute("SELECT status FROM items").fetchone()[0], "new")
            self.assertEqual(con.execute("SELECT count(*) FROM posts").fetchone()[0], 0)
            self.assertEqual(json.loads(store.kv_get(con, "reporter:last_intake"))["editorial_calls"], 0)
            sync.assert_called_once()
            legacy.assert_not_called()

    def test_import_without_provider_keys_does_not_construct_legacy_clients(self):
        env = {k: v for k, v in os.environ.items() if k not in
               {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY"}}
        env["NBN_OPERATING_MODE"] = "infrastructure"
        result = subprocess.run([sys.executable, "-c",
            "import anthropic; anthropic.Anthropic=lambda **kw: (_ for _ in ()).throw(AssertionError('client created')); "
            "from nbn import main,verify; print('imported')"],
            env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("imported", result.stdout)
