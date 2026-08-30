"""Environment configuration. Every knob is an env var; defaults are safe (nothing posts)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# LLM
ANTHROPIC_MODEL = os.environ.get("NBN_MODEL", "claude-opus-5")
TRIAGE_MODEL = os.environ.get("NBN_TRIAGE_MODEL", ANTHROPIC_MODEL)
# The Editor: last-mile judgment seat — few calls/day, so the model bill is irrelevant;
# Fable 5 at low effort is the one-env-flip upgrade if verdicts feel shallow.
EDITOR_MODEL = os.environ.get("NBN_EDITOR_MODEL", "claude-opus-5")
EDITOR_EFFORT = os.environ.get("NBN_EDITOR_EFFORT", "high")
MAX_LLM_CALLS_PER_HOUR = int(os.environ.get("NBN_MAX_LLM_CALLS_PER_HOUR", "60"))

# Desk Report (/report?k=<token>) — read-only editor view; unset token disables it
REPORT_TOKEN = os.environ.get("NBN_REPORT_TOKEN", "")

# Daily self-audit fire time (UTC HH:MM); empty disables
AUDIT_UTC = os.environ.get("NBN_AUDIT_UTC", "09:00")

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

# Typefully (preferred posting rail; long posts + threads + publish-now via API)
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "")

# Marketing Node read API (the Brady-tuned daily brief; read-only bearer)
NODE_BASE_URL = os.environ.get("NBN_NODE_BASE_URL",
                               "https://swan-marketing-node-production.up.railway.app")
NODE_READ_TOKEN = os.environ.get("NBN_NODE_READ_TOKEN", "")
# "HH:MM,Title;HH:MM,Title" in UTC — after the Node's EIC (14:00) and PM intel (20:30) runs
BRIEFING_SCHEDULE = [
    tuple(x.split(",")) for x in
    os.environ.get("NBN_BRIEFING_UTC", "14:40,Morning;21:15,Afternoon").split(";") if x
] if os.environ.get("NBN_BRIEFING_ENABLED", "true").lower() == "true" else []

# Perception (api.perception.to) — the wire's OWN key, never the Marketing Node's
# (their /feed rate budget is shared per key). Activates when set.
PERCEPTION_API_KEY = os.environ.get("NBN_PERCEPTION_API_KEY", "")
PERCEPTION_POLL_SECONDS = int(os.environ.get("NBN_PERCEPTION_POLL_SECONDS", "600"))

# X read access — SHARED with the Marketing Node's bearer (Brady's call 2026-08-30);
# recent-search rate limits are per app, Node's 2x/day pulse + our throttled poll fit easily.
X_BEARER_TOKEN = os.environ.get("NBN_X_BEARER_TOKEN", "")
X_POLL_SECONDS = int(os.environ.get("NBN_X_POLL_SECONDS", "180"))
# Public X List whose MEMBERS define the primary watch roster (managed in the X app).
# Membership is fetched hourly and compiled into a since_id-gated search query —
# never the list timeline itself (that endpoint lacks since_id and re-bills reads).
X_LIST_ID = os.environ.get("NBN_X_LIST_ID", "")
X_LIST_REFRESH_SECONDS = int(os.environ.get("NBN_X_LIST_REFRESH_SECONDS", "3600"))

# Classes allowed to auto-publish when AUTOPOST_ENABLED (secondary never auto-publishes;
# env-tunable so the rollout can start with official sources only)
AUTOPOST_CLASSES = {
    c.strip() for c in os.environ.get("NBN_AUTOPOST_CLASSES", "primary,data").split(",") if c.strip()
} - {"secondary"}

# Autonomous publishes are scheduled this many seconds out (publish_at:"now" rejects
# drafts containing URLs; scheduled posts carry links fine — probed 2026-08-30)
PUBLISH_DELAY_SECONDS = int(os.environ.get("NBN_PUBLISH_DELAY_SECONDS", "90"))

# Dead-man's switch: ping this URL after every successful cycle (healthchecks.io);
# alerts fire on SILENCE, catching crash and stall alike. Empty = disabled.
HEARTBEAT_URL = os.environ.get("NBN_HEARTBEAT_URL", "")

# Events, not write-ups: a story whose underlying EVENT is older than this never posts,
# however fresh the article covering it (HWI/quantum lesson, 2026-08-30).
MAX_EVENT_AGE_HOURS = float(os.environ.get("NBN_MAX_EVENT_AGE_HOURS", "48"))
