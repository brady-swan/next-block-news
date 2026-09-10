"""Operator-only compatibility probes. Never connected to NBN or Typefully."""
import argparse
import json
import os
from pathlib import Path
import pwd
import subprocess

STATE = Path("/reporter-state")
WORK = STATE / "workspace"
CODEX = "/opt/codex/bin/codex"


def initialize():
    if os.getuid() == 0:
        user = pwd.getpwnam("reporter")
        os.setgroups([])
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
    os.chdir(WORK)
    # SDK config.env merges with its parent's environment rather than replacing it.
    # Sanitize this operator-only probe process before constructing the SDK client.
    allowed = runtime_env()
    os.environ.clear()
    os.environ.update(allowed)


def runtime_env():
    # Do not inherit provider or deployment credentials into Codex/MCP children.
    return {"PATH": "/opt/codex/bin:/usr/local/bin:/usr/bin:/bin",
            "CODEX_HOME": str(STATE / "codex"), "LANG": "C.UTF-8",
            "PLAYWRIGHT_BROWSERS_PATH": "/opt/browsers"}


def sandbox():
    for directory in (STATE / "codex", STATE / "control"):
        (directory / "probe-canary.txt").write_text("not-a-secret; sandbox probe only")
    result = subprocess.run([CODEX, "sandbox", "linux", "--", "/usr/local/bin/python",
                             "/opt/nbn-reporter/sandbox_probe.py"],
                            env=runtime_env(), text=True, capture_output=True, timeout=30)
    print(json.dumps({"exit_code": result.returncode, "stdout": result.stdout,
                      "stderr": result.stderr[-4000:]}), flush=True)
    if result.returncode:
        raise SystemExit(result.returncode)
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    if not payload.get("ok"):
        raise SystemExit("sandbox requirements failed")
    (STATE / "control" / "sandbox-passed.json").write_text(json.dumps(payload))


def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, chromium_sandbox=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        response = page.goto("https://www.bis.org/", wait_until="domcontentloaded", timeout=45000)
        shot = WORK / "bis-browser-probe.png"
        page.screenshot(path=str(shot))
        print(json.dumps({"url": page.url, "status": response.status if response else None,
                          "title": page.title(), "screenshot": str(shot),
                          "bytes": shot.stat().st_size,
                          "text_excerpt": page.locator("body").inner_text()[:800]}), flush=True)
        browser.close()


def codex_client():
    from openai_codex import Codex, CodexConfig
    return Codex(CodexConfig(codex_bin=CODEX, cwd=str(WORK), env=runtime_env(),
                            client_name="nbn_reporter_spike", client_title="NBN Reporter Spike"))


def metadata():
    import openai_codex
    print(json.dumps({"sdk": openai_codex.__version__,
        "runtime": subprocess.check_output([CODEX, "--version"], env=runtime_env(), text=True).strip(),
        "uid": os.getuid(), "publishing": "unavailable"}), flush=True)
    with codex_client() as codex:
        account = codex.account()
        # Deliberately do not log the account/email or any auth payload.
        print(json.dumps({"account_present": account.account is not None}), flush=True)
        models = codex.models()
        print(json.dumps({"astra": [m.model_dump(mode="json") for m in models.data
                                    if m.model == "gpt-6-astra"]}), flush=True)


def login():
    if not (STATE / "control" / "sandbox-passed.json").exists():
        raise SystemExit("sandbox must pass before account login")
    with codex_client() as codex:
        handle = codex.login_chatgpt_device_code()
        print(json.dumps({"verification_url": handle.verification_url,
                          "user_code": handle.user_code}), flush=True)
        completed = handle.wait()
        print(json.dumps({"login_success": completed.success}), flush=True)


def turn(resume=False):
    from openai_codex import ApprovalMode
    if not (STATE / "control" / "sandbox-passed.json").exists():
        raise SystemExit("sandbox must pass before model use")
    record = STATE / "control" / "probe-session.json"
    with codex_client() as codex:
        if resume:
            thread = codex.thread_resume(json.loads(record.read_text())["thread_id"],
                approval_mode=ApprovalMode.deny_all, model="gpt-6-astra", service_tier="default")
            prompt = ("This is the second compatibility-check turn after a runtime restart. "
                      "What was the continuity phrase in the previous turn? Do not research or "
                      "change anything. Reply with that phrase and one sentence confirming the task.")
        else:
            thread = codex.thread_start(model="gpt-6-astra", cwd=str(WORK),
                approval_mode=ApprovalMode.deny_all, service_tier="default",
                developer_instructions="You are performing a bounded NBN runtime compatibility check. "
                    "No publishing or system changes are authorized. Use only the requested read-only check.")
            record.write_text(json.dumps({"thread_id": thread.id}))
            prompt = ("Remember this continuity phrase: cedar lighthouse. Run `pwd` once to verify "
                      "your sandboxed shell works, then say READY. Do not read credentials, search "
                      "the internet, inspect other files, or make changes.")
        result = thread.run(prompt, effort="medium", service_tier="default")
        print(json.dumps({"thread_id": thread.id, "status": str(result.status),
                          "response": result.final_response,
                          "usage": result.usage.model_dump(mode="json") if result.usage else None,
                          "error": result.error.model_dump(mode="json") if result.error else None}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["metadata", "sandbox", "browser", "login", "turn", "resume"])
    action = parser.parse_args().action
    initialize()
    if action == "resume":
        turn(resume=True)
    else:
        globals()[action]()
