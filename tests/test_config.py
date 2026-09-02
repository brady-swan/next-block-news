import json
import os
import subprocess
import sys
import unittest
import socket

from tests import SECRET_ENV_VARS


ROOT = os.path.dirname(os.path.dirname(__file__))


def load_config(extra=None):
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ROOT}
    for name in SECRET_ENV_VARS:
        env.pop(name, None)
    env["NBN_AUTOPOST_ENABLED"] = "false"
    env.update(extra or {})
    code = """
import json
from nbn import config
print(json.dumps({
    'model': config.ANTHROPIC_MODEL,
    'triage': config.TRIAGE_MODEL,
    'triage_effort': config.TRIAGE_EFFORT,
    'editor': config.EDITOR_MODEL,
    'effort': config.EDITOR_EFFORT,
    'poll': config.POLL_SECONDS,
    'perception': config.PERCEPTION_POLL_SECONDS,
    'perception_direct': config.PERCEPTION_DIRECT_ENABLED,
    'node_pulse_max_age': config.NODE_PULSE_MAX_AGE_SECONDS,
    'x_detector': config.X_DETECTOR_ENABLED,
    'classes': sorted(config.AUTOPOST_CLASSES),
    'delay': config.PUBLISH_DELAY_SECONDS,
    'autopost': config.AUTOPOST_ENABLED,
    'source_policy_mode': config.SOURCE_POLICY_MODE,
    'newsroom_mode': config.RUN_NEWSROOM_MODE,
    'newsroom_fallback': config.RUN_NEWSROOM_FALLBACK,
    'newsroom_rounds': config.RUN_NEWSROOM_MAX_ROUNDS,
    'editorial_engine': config.EDITORIAL_ENGINE,
    'desk_interval': config.DESK_INTERVAL_SECONDS,
    'desk_recent_feed_hours': config.DESK_RECENT_FEED_HOURS,
    'desk_recent_feed_limit': config.DESK_RECENT_FEED_LIMIT,
    'intake_triage_mode': config.INTAKE_TRIAGE_MODE,
    'intake_triage_model': config.INTAKE_TRIAGE_MODEL,
    'intake_triage_hourly': config.INTAKE_TRIAGE_MAX_CALLS_PER_HOUR,
    'analytics_interval': config.PUBLISH_ANALYTICS_SECONDS,
    'serpapi': bool(config.SERPAPI_KEY),
    'serpapi_timeout': config.SERPAPI_TIMEOUT_SECONDS,
    'serpapi_results': config.SERPAPI_MAX_RESULTS,
    'hosted_search': config.HOSTED_SEARCH_ENABLED,
    'hosted_search_timeout': config.HOSTED_SEARCH_TIMEOUT_SECONDS,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, env=env, check=True,
        capture_output=True, text=True,
    )
    return json.loads(result.stdout)


class ConfigTests(unittest.TestCase):
    def test_safe_documented_defaults(self):
        values = load_config()
        self.assertEqual(values, {
            "model": "claude-sonnet-5",
            "triage": "claude-sonnet-5",
            "triage_effort": "medium",
            "editor": "claude-sonnet-5",
            "effort": "medium",
            "poll": 60,
            "perception": 900,
            "perception_direct": True,
            "node_pulse_max_age": 10800,
            "x_detector": True,
            "classes": ["corroborated", "primary", "secondary"],
            "delay": 30,
            "autopost": False,
            "source_policy_mode": "enforce",
            "newsroom_mode": "off",
            "newsroom_fallback": "legacy",
            "newsroom_rounds": 6,
            "editorial_engine": "v2",
            "desk_interval": 900,
            "desk_recent_feed_hours": 48.0,
            "desk_recent_feed_limit": 40,
            "intake_triage_mode": "off",
            "intake_triage_model": "claude-haiku-4-5",
            "intake_triage_hourly": 8,
            "analytics_interval": 900,
            "serpapi": False,
            "serpapi_timeout": 15.0,
            "serpapi_results": 5,
            "hosted_search": True,
            "hosted_search_timeout": 45.0,
        })

    def test_overlap_lanes_can_be_disabled_independently(self):
        values = load_config({
            "NBN_PERCEPTION_DIRECT_ENABLED": "false",
            "NBN_X_DETECTOR_ENABLED": "false",
        })
        self.assertFalse(values["perception_direct"])
        self.assertFalse(values["x_detector"])

    def test_secondary_can_autopost_in_editorial_v2(self):
        values = load_config({"NBN_AUTOPOST_CLASSES": "secondary,primary"})
        self.assertEqual(values["classes"], ["primary", "secondary"])

    def test_test_process_blocks_real_network(self):
        with self.assertRaisesRegex(AssertionError, "real network access"):
            socket.create_connection(("127.0.0.1", 9))

    def test_test_process_does_not_inherit_real_credentials(self):
        self.assertEqual(os.environ["ANTHROPIC_API_KEY"], "test-not-a-real-key")
        for name in SECRET_ENV_VARS:
            if name != "ANTHROPIC_API_KEY":
                self.assertNotIn(name, os.environ)


if __name__ == "__main__":
    unittest.main()
