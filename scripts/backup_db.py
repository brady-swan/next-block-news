"""Create and integrity-check an online SQLite backup of the production state."""
import datetime
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbn import config  # noqa: E402


def backup() -> Path:
    if not config.DB_PATH.exists():
        raise FileNotFoundError(config.DB_PATH)
    backup_dir = config.DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"nbn-pre-source-policy-{stamp}.db"
    source = sqlite3.connect(config.DB_PATH)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
        verdict = destination.execute("PRAGMA integrity_check").fetchone()[0]
        if verdict != "ok":
            raise RuntimeError(f"backup integrity check failed: {verdict}")
    finally:
        destination.close()
        source.close()
    return target


if __name__ == "__main__":
    print(backup())

