"""Phase-one worker: persistent runtime setup and health, no editorial loop."""
import json
import os
from pathlib import Path
import pwd
import shutil
from http.server import BaseHTTPRequestHandler, HTTPServer


def prepare():
    root = Path("/reporter-state")
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o711)
    account = pwd.getpwnam("reporter")
    for name in ("codex", "control", "workspace"):
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        directory.chmod(0o700)
        os.chown(directory, account.pw_uid, account.pw_gid)
    # Configuration is maintained by the supervisor; auth is never seeded/overwritten.
    target = root / "codex" / "config.toml"
    shutil.copyfile("/opt/nbn-reporter/config.toml", target)
    target.chmod(0o600)
    os.chown(target, account.pw_uid, account.pw_gid)
    os.setgroups([])
    os.setgid(account.pw_gid)
    os.setuid(account.pw_uid)
    os.chdir(root / "workspace")


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        content = json.dumps({"status": "compatibility_spike", "reporter_enabled": False,
                              "publishing": "unavailable"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    prepare()
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Health).serve_forever()
