"""Small fixtures shared by unit and cycle tests."""
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from nbn import config, store


@contextmanager
def temporary_store():
    with tempfile.TemporaryDirectory(prefix="nbn-db-") as directory:
        root = Path(directory)
        with patch.object(config, "DATA_DIR", root), \
                patch.object(config, "DB_PATH", root / "nbn.db"), \
                patch.object(config, "TAPE_DIR", root / "tapes"):
            con = store.connect()
            try:
                yield con
            finally:
                con.close()


def item(url="https://example.com/story", source="Example", title="Bitcoin test story",
         published="", summary=""):
    return {
        "source": source,
        "title": title,
        "url": url,
        "published": published,
        "summary": summary,
    }
