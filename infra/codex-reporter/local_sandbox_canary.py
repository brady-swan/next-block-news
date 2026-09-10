"""Executed only inside the proposed reporter's native macOS sandbox."""
import json
import socket
from pathlib import Path

state = Path('/Users/brady/codex/nbn-reporter-pilot')
work = state / 'workspace'
results = {}
allowed = work / 'sandbox-allowed.txt'
allowed.write_text('allowed')
results['workspace_write'] = allowed.read_text() == 'allowed'

for name, path in (
    ('auth_read_denied', state / 'codex/probe-canary.txt'),
    ('control_read_denied', state / 'control/probe-canary.txt'),
    ('active_config_read_denied', state / 'codex/config.toml'),
    ('unrelated_workspace_read_denied', Path('/Users/brady/claude/bitcoin-study/START-HERE.md')),
):
    try:
        with path.open('rb') as f:
            f.read(1)  # Never print content, including during a failed isolation test.
        results[name] = False
    except PermissionError:
        results[name] = True

for name, path in (
    ('control_write_denied', state / 'control/probe-canary.txt'),
    ('active_config_write_denied', state / 'codex/config.toml'),
    ('workspace_config_write_denied', work / '.codex/config.toml'),
    ('workspace_instructions_write_denied', work / 'AGENTS.md'),
):
    try:
        with path.open('a'):
            pass
        results[name] = False
    except PermissionError:
        results[name] = True

try:
    with socket.create_connection(('1.1.1.1', 443), timeout=2):
        results['shell_network_denied'] = False
except OSError as exc:
    results['shell_network_denied'] = exc.errno in {1, 13}

results['ok'] = all(results.values())
print(json.dumps(results))
raise SystemExit(0 if results['ok'] else 1)
