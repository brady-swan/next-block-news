"""Runs inside Codex sandbox; canaries contain no credentials."""
import json
import socket
from pathlib import Path

results = {}
workspace = Path("/reporter-state/workspace")
test = workspace / "sandbox-allowed.txt"
test.write_text("allowed")
results["workspace_write"] = test.read_text() == "allowed"

for name, path in (
    ("auth_read_denied", "/reporter-state/codex/probe-canary.txt"),
    ("control_read_denied", "/reporter-state/control/probe-canary.txt"),
):
    try:
        Path(path).read_text()
        results[name] = False
    except (PermissionError, FileNotFoundError):
        results[name] = True

for name, path in (
    ("control_write_denied", "/reporter-state/control/probe-canary.txt"),
    ("config_write_denied", "/opt/nbn-reporter/config.toml"),
):
    try:
        with open(path, "a"):
            pass
        results[name] = False
    except (PermissionError, FileNotFoundError):
        results[name] = True

try:
    with socket.create_connection(("1.1.1.1", 443), timeout=2):
        results["shell_network_denied"] = False
except OSError as exc:
    results["shell_network_denied"] = exc.errno in {1, 13, 101}

results["ok"] = all(results.values())
print(json.dumps(results))
raise SystemExit(0 if results["ok"] else 1)
