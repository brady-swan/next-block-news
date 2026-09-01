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
            "editor": "claude-fable-5",
            "effort": "low",
            "poll": 60,
            "perception": 900,
            "perception_direct": True,
            "node_pulse_max_age": 10800,
            "x_detector": True,
            "classes": ["corroborated", "primary"],
            "delay": 30,
            "autopost": False,
            "source_policy_mode": "enforce",
        })

    def test_overlap_lanes_can_be_disabled_independently(self):
        values = load_config({
            "NBN_PERCEPTION_DIRECT_ENABLED": "false",
            "NBN_X_DETECTOR_ENABLED": "false",
        })
        self.assertFalse(values["perception_direct"])
        self.assertFalse(values["x_detector"])

    def test_secondary_is_removed_from_autopost_classes(self):
        values = load_config({"NBN_AUTOPOST_CLASSES": "secondary,primary"})
        self.assertEqual(values["classes"], ["primary"])

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
