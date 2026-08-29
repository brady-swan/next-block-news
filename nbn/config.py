"""Environment configuration. Every knob is an env var; defaults are safe (nothing posts)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# LLM
ANTHROPIC_MODEL = os.environ.get("NBN_MODEL", "claude-opus-5")
TRIAGE_MODEL = os.environ.get("NBN_TRIAGE_MODEL", ANTHROPIC_MODEL)
MAX_LLM_CALLS_PER_HOUR = int(os.environ.get("NBN_MAX_LLM_CALLS_PER_HOUR", "60"))

# Loop
POLL_SECONDS = int(os.environ.get("NBN_POLL_SECONDS", "120"))
MAX_ITEMS_PER_TRIAGE = int(os.environ.get("NBN_MAX_ITEMS_PER_TRIAGE", "25"))
PORT = int(os.environ.get("PORT", "8080"))

# State
DATA_DIR = Path(os.environ.get("NBN_DATA_DIR", "/data" if Path("/data").is_dir() else str(ROOT / "data")))
DB_PATH = DATA_DIR / "nbn.db"
TAPE_DIR = DATA_DIR / "tapes"

# Posting
AUTOPOST_ENABLED = os.environ.get("NBN_AUTOPOST_ENABLED", "false").lower() == "true"
NUELINK_API_KEY = os.environ.get("NUELINK_API_KEY", "")
NUELINK_BRAND_ID = os.environ.get("NUELINK_BRAND_ID", "")
NUELINK_COLLECTION_ID = os.environ.get("NUELINK_COLLECTION_ID", "")
NUELINK_BASE = "https://nuelink.com/api/public/v1"

# Optional X read access (its own key, never the Marketing Node's)
X_BEARER_TOKEN = os.environ.get("NBN_X_BEARER_TOKEN", "")

# Classes allowed to auto-publish when AUTOPOST_ENABLED (secondary never auto-publishes)
AUTOPOST_CLASSES = {"primary", "data"}
