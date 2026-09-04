"""Environment configuration. Every knob is an env var; defaults are safe (nothing posts)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# LLM
ANTHROPIC_MODEL = os.environ.get("NBN_MODEL", "claude-sonnet-5")
TRIAGE_MODEL = os.environ.get("NBN_TRIAGE_MODEL", ANTHROPIC_MODEL)
TRIAGE_EFFORT = os.environ.get("NBN_TRIAGE_EFFORT", "medium")
# The Editor: last-mile judgment seat. It runs only on autonomous candidates, so the
# higher-judgment Fable seat remains a small share of the model budget.
EDITOR_MODEL = os.environ.get("NBN_EDITOR_MODEL", "claude-sonnet-5")
EDITOR_EFFORT = os.environ.get("NBN_EDITOR_EFFORT", "medium")
MAX_LLM_CALLS_PER_HOUR = int(os.environ.get("NBN_MAX_LLM_CALLS_PER_HOUR", "60"))

# One fresh Sonnet newsroom may own survey, research, judgment, and writing for a complete
# intake run. Rollout is deliberately explicit: off -> shadow -> draft -> live.
RUN_NEWSROOM_MODE = os.environ.get("NBN_RUN_NEWSROOM_MODE", "off").strip().lower()
if RUN_NEWSROOM_MODE not in {"off", "shadow", "draft", "live"}:
    raise RuntimeError("NBN_RUN_NEWSROOM_MODE must be off, shadow, draft, or live")
RUN_NEWSROOM_FALLBACK = os.environ.get(
    "NBN_RUN_NEWSROOM_FALLBACK", "legacy"
).strip().lower()
if RUN_NEWSROOM_FALLBACK not in {"legacy", "hold"}:
    raise RuntimeError("NBN_RUN_NEWSROOM_FALLBACK must be legacy or hold")
RUN_NEWSROOM_MAX_ROUNDS = int(os.environ.get("NBN_RUN_NEWSROOM_MAX_ROUNDS", "6"))
RUN_NEWSROOM_MAX_TOOL_CALLS = int(os.environ.get("NBN_RUN_NEWSROOM_MAX_TOOL_CALLS", "24"))
RUN_NEWSROOM_MAX_SEARCHES = int(os.environ.get("NBN_RUN_NEWSROOM_MAX_SEARCHES", "8"))
RUN_NEWSROOM_MAX_FETCHES = int(os.environ.get("NBN_RUN_NEWSROOM_MAX_FETCHES", "16"))
RUN_NEWSROOM_MAX_FETCH_CHARS = int(
    os.environ.get("NBN_RUN_NEWSROOM_MAX_FETCH_CHARS", "8000")
)
RUN_NEWSROOM_MAX_FETCH_TOTAL_CHARS = int(
    os.environ.get("NBN_RUN_NEWSROOM_MAX_FETCH_TOTAL_CHARS", "160000")
)
RUN_NEWSROOM_MAX_INITIAL_BYTES = int(
    os.environ.get("NBN_RUN_NEWSROOM_MAX_INITIAL_BYTES", "98304")
)
RUN_NEWSROOM_MAX_HISTORY_BYTES = int(
    os.environ.get("NBN_RUN_NEWSROOM_MAX_HISTORY_BYTES", "491520")
)
RUN_NEWSROOM_TIMEOUT_SECONDS = float(
    os.environ.get("NBN_RUN_NEWSROOM_TIMEOUT_SECONDS", "240")
)
RUN_NEWSROOM_RETRY_ALLOWANCE = int(
    os.environ.get("NBN_RUN_NEWSROOM_RETRY_ALLOWANCE", "1")
)
# Editorial core v2 keeps the one-minute intake/health loop, but opens a fresh
# run-scoped Sonnet desk only on a persisted editorial cadence. ``v1`` is a temporary,
# manual rollback switch; there is never an automatic fallback into it.
EDITORIAL_ENGINE = os.environ.get("NBN_EDITORIAL_ENGINE", "v2").strip().lower()
if EDITORIAL_ENGINE not in {"v1", "v2"}:
    raise RuntimeError("NBN_EDITORIAL_ENGINE must be v1 or v2")
DESK_INTERVAL_SECONDS = int(os.environ.get("NBN_DESK_INTERVAL_SECONDS", "900"))
DESK_CANDIDATE_MAX_AGE_HOURS = float(
    os.environ.get("NBN_DESK_CANDIDATE_MAX_AGE_HOURS", "24")
)
DESK_RECENT_FEED_HOURS = float(os.environ.get("NBN_DESK_RECENT_FEED_HOURS", "48"))
DESK_RECENT_FEED_LIMIT = int(os.environ.get("NBN_DESK_RECENT_FEED_LIMIT", "40"))
COMPACT_DESK_ENABLED = os.environ.get(
    "NBN_COMPACT_DESK_ENABLED", "false"
).lower() == "true"
COMPACT_DESK_INITIAL_BYTES = int(
    os.environ.get("NBN_COMPACT_DESK_INITIAL_BYTES", str(64 * 1024))
)
COMPACT_DESK_HISTORY_BYTES = int(
    os.environ.get("NBN_COMPACT_DESK_HISTORY_BYTES", str(192 * 1024))
)
COMPACT_DESK_RETRIEVAL_CALLS = int(
    os.environ.get("NBN_COMPACT_DESK_RETRIEVAL_CALLS", "2")
)
COMPACT_DESK_RETRIEVAL_ROWS = int(
    os.environ.get("NBN_COMPACT_DESK_RETRIEVAL_ROWS", "8")
)
COMPACT_DESK_RETRIEVAL_BYTES = int(
    os.environ.get("NBN_COMPACT_DESK_RETRIEVAL_BYTES", str(16 * 1024))
)
COMPACT_DESK_RETRIEVAL_TOTAL_BYTES = int(
    os.environ.get("NBN_COMPACT_DESK_RETRIEVAL_TOTAL_BYTES", str(24 * 1024))
)

# A run-scoped Haiku assigning editor prepares the cross-source desk before Sonnet.
DESK_PREP_MODE = os.environ.get("NBN_DESK_PREP_MODE", "off").strip().lower()
if DESK_PREP_MODE not in {"off", "observe", "enforce"}:
    raise RuntimeError("NBN_DESK_PREP_MODE must be off, observe, or enforce")
DESK_PREP_MODEL = os.environ.get("NBN_DESK_PREP_MODEL", "claude-haiku-4-5")
DESK_PREP_BATCH_SIZE = int(os.environ.get("NBN_DESK_PREP_BATCH_SIZE", "25"))
DESK_PREP_MAX_PACKET_BYTES = int(
    os.environ.get("NBN_DESK_PREP_MAX_PACKET_BYTES", str(48 * 1024))
)
DESK_PREP_MAX_OUTPUT_TOKENS = int(
    os.environ.get("NBN_DESK_PREP_MAX_OUTPUT_TOKENS", "6000")
)
DESK_PREP_TIMEOUT_SECONDS = float(
    os.environ.get("NBN_DESK_PREP_TIMEOUT_SECONDS", "45")
)
DESK_PREP_MAX_CALLS_PER_HOUR = int(
    os.environ.get("NBN_DESK_PREP_MAX_CALLS_PER_HOUR", "6")
)
DESK_PREFETCH_MAX_URLS = int(os.environ.get("NBN_DESK_PREFETCH_MAX_URLS", "6"))
DESK_PREFETCH_MAX_CHARS = int(os.environ.get("NBN_DESK_PREFETCH_MAX_CHARS", "24000"))
DESK_PREFETCH_RESERVE_FETCHES = int(
    os.environ.get("NBN_DESK_PREFETCH_RESERVE_FETCHES", "8")
)
DESK_PREFETCH_RESERVE_CHARS = int(
    os.environ.get("NBN_DESK_PREFETCH_RESERVE_CHARS", "80000")
)

# Sonnet may delegate one bounded source-resolution assignment to Haiku.
HAIKU_RESEARCH_MODE = os.environ.get("NBN_HAIKU_RESEARCH_MODE", "off").strip().lower()
if HAIKU_RESEARCH_MODE not in {"off", "on"}:
    raise RuntimeError("NBN_HAIKU_RESEARCH_MODE must be off or on")
HAIKU_RESEARCH_MODEL = os.environ.get("NBN_HAIKU_RESEARCH_MODEL", "claude-haiku-4-5")
HAIKU_RESEARCH_MAX_ASSIGNMENTS = int(
    os.environ.get("NBN_HAIKU_RESEARCH_MAX_ASSIGNMENTS", "1")
)
HAIKU_RESEARCH_MAX_ROUNDS = int(os.environ.get("NBN_HAIKU_RESEARCH_MAX_ROUNDS", "2"))
HAIKU_RESEARCH_MAX_TOOL_CALLS = int(
    os.environ.get("NBN_HAIKU_RESEARCH_MAX_TOOL_CALLS", "8")
)
HAIKU_RESEARCH_MAX_SEARCHES = int(os.environ.get("NBN_HAIKU_RESEARCH_MAX_SEARCHES", "3"))
HAIKU_RESEARCH_MAX_FETCHES = int(os.environ.get("NBN_HAIKU_RESEARCH_MAX_FETCHES", "5"))
HAIKU_RESEARCH_MAX_FETCH_CHARS = int(
    os.environ.get("NBN_HAIKU_RESEARCH_MAX_FETCH_CHARS", "20000")
)
HAIKU_RESEARCH_MAX_PACKET_BYTES = int(
    os.environ.get("NBN_HAIKU_RESEARCH_MAX_PACKET_BYTES", str(32 * 1024))
)
HAIKU_RESEARCH_MAX_HISTORY_BYTES = int(
    os.environ.get("NBN_HAIKU_RESEARCH_MAX_HISTORY_BYTES", str(96 * 1024))
)
HAIKU_RESEARCH_MAX_MEMO_BYTES = int(
    os.environ.get("NBN_HAIKU_RESEARCH_MAX_MEMO_BYTES", "4096")
)
HAIKU_RESEARCH_TIMEOUT_SECONDS = float(
    os.environ.get("NBN_HAIKU_RESEARCH_TIMEOUT_SECONDS", "90")
)
MODEL_DAILY_TARGET_USD = float(os.environ.get("NBN_MODEL_DAILY_TARGET_USD", "6"))


def editorial_reservation_calls(*, include_mailroom: bool = False,
                                direct_fallback: bool = False) -> int:
    """Worst-case API attempts for one v2 cycle under the enabled configuration."""
    # One normal editor call plus at most one omitted-only recovery call.
    total = max(0, RUN_NEWSROOM_MAX_ROUNDS) + max(0, RUN_NEWSROOM_RETRY_ALLOWANCE) + 2
    if not direct_fallback:
        total += int(DESK_PREP_MODE != "off")
        if HAIKU_RESEARCH_MODE == "on":
            total += (max(0, HAIKU_RESEARCH_MAX_ASSIGNMENTS)
                      * max(0, HAIKU_RESEARCH_MAX_ROUNDS))
        total += int(include_mailroom)
    return total

# One cheap semantic mailroom pass keeps broad RSS and EDGAR noise off Sonnet's desk.
# Rollout is explicit; runtime failures always fail open as candidates.
INTAKE_TRIAGE_MODE = os.environ.get("NBN_INTAKE_TRIAGE_MODE", "off").strip().lower()
if INTAKE_TRIAGE_MODE not in {"off", "observe", "enforce"}:
    raise RuntimeError("NBN_INTAKE_TRIAGE_MODE must be off, observe, or enforce")
INTAKE_TRIAGE_MODEL = os.environ.get("NBN_INTAKE_TRIAGE_MODEL", "claude-haiku-4-5")
INTAKE_TRIAGE_MAX_CALLS_PER_HOUR = int(
    os.environ.get("NBN_INTAKE_TRIAGE_MAX_CALLS_PER_HOUR", "8")
)
INTAKE_TRIAGE_BATCH_SIZE = int(os.environ.get("NBN_INTAKE_TRIAGE_BATCH_SIZE", "50"))
INTAKE_TRIAGE_RECOVERY_LIMIT = int(
    os.environ.get("NBN_INTAKE_TRIAGE_RECOVERY_LIMIT", "100")
)
INTAKE_TRIAGE_RECOVERY_HOURS = float(
    os.environ.get("NBN_INTAKE_TRIAGE_RECOVERY_HOURS", "24")
)
INTAKE_TRIAGE_MAX_PACKET_BYTES = int(
    os.environ.get("NBN_INTAKE_TRIAGE_MAX_PACKET_BYTES", str(96 * 1024))
)
INTAKE_TRIAGE_TIMEOUT_SECONDS = float(
    os.environ.get("NBN_INTAKE_TRIAGE_TIMEOUT_SECONDS", "45")
)
INTAKE_TRIAGE_MAX_OUTPUT_TOKENS = int(
    os.environ.get("NBN_INTAKE_TRIAGE_MAX_OUTPUT_TOKENS", "8000")
)

# Model-free Google organic discovery. The credential is shared with the Marketing
# Node account, but NBN calls SerpAPI directly and applies its own source policy.
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
SERPAPI_TIMEOUT_SECONDS = float(os.environ.get("NBN_SERPAPI_TIMEOUT_SECONDS", "15"))
SERPAPI_MAX_RESULTS = int(os.environ.get("NBN_SERPAPI_MAX_RESULTS", "5"))
SEARCH_RESILIENCE_ENABLED = os.environ.get(
    "NBN_SEARCH_RESILIENCE_ENABLED", "false"
).lower() == "true"
SEARCH_ACCOUNT_TTL_SECONDS = int(
    os.environ.get("NBN_SEARCH_ACCOUNT_TTL_SECONDS", "300")
)
SEARCH_CACHE_TTL_SECONDS = int(
    os.environ.get("NBN_SEARCH_CACHE_TTL_SECONDS", "3600")
)
SEARCH_POINTER_TTL_SECONDS = int(
    os.environ.get("NBN_SEARCH_POINTER_TTL_SECONDS", "21600")
)
SEARCH_PROVIDER_COOLDOWN_SECONDS = int(
    os.environ.get("NBN_SEARCH_PROVIDER_COOLDOWN_SECONDS", "300")
)
DESK_CLUSTER_COMPANIONS_ENABLED = os.environ.get(
    "NBN_DESK_CLUSTER_COMPANIONS_ENABLED", "false"
).lower() == "true"
HOSTED_SEARCH_ENABLED = os.environ.get(
    "NBN_HOSTED_SEARCH_ENABLED", "true"
).lower() == "true"
HOSTED_SEARCH_TIMEOUT_SECONDS = float(
    os.environ.get("NBN_HOSTED_SEARCH_TIMEOUT_SECONDS", "45")
)
YIELD_IDENTITY_NORMALIZER_ENABLED = os.environ.get(
    "NBN_YIELD_IDENTITY_NORMALIZER_ENABLED", "false"
).lower() == "true"

# Desk Report (/report?k=<token>) — read-only editor view; unset token disables it
REPORT_TOKEN = os.environ.get("NBN_REPORT_TOKEN", "")

# Daily self-audit fire time (UTC HH:MM); empty disables
AUDIT_UTC = os.environ.get("NBN_AUDIT_UTC", "09:00")

# Loop
POLL_SECONDS = int(os.environ.get("NBN_POLL_SECONDS", "60"))
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

# Typefully (preferred posting rail; long posts, threads, scheduled publishing)
TYPEFULLY_API_KEY = os.environ.get("TYPEFULLY_API_KEY", "")
TYPEFULLY_SOCIAL_SET_ID = os.environ.get("TYPEFULLY_SOCIAL_SET_ID", "")
DRAFT_REPLACEMENT_ENABLED = (
    os.environ.get("NBN_DRAFT_REPLACEMENT_ENABLED", "false").lower() == "true"
)

# Marketing Node read API (the Brady-tuned daily brief; read-only bearer)
NODE_BASE_URL = os.environ.get("NBN_NODE_BASE_URL",
                               "https://swan-marketing-node-production.up.railway.app")
NODE_READ_TOKEN = os.environ.get("NBN_NODE_READ_TOKEN", "")
NODE_PULSE_MAX_AGE_SECONDS = int(
    os.environ.get("NBN_NODE_PULSE_MAX_AGE_SECONDS", "10800")
)
# Fresh EIC briefs remain a twice-daily discovery input for the one-off newsroom.
EIC_DISCOVERY_SCHEDULE = [
    tuple(x.split(",")) for x in
    os.environ.get("NBN_EIC_DISCOVERY_UTC", "14:40,Morning;21:15,Afternoon").split(";") if x
] if os.environ.get("NBN_EIC_DISCOVERY_ENABLED", "true").lower() == "true" else []

# Legacy multi-story Block packaging is retained as an opt-in rollback path. One-offs are
# the default product; a fresh EIC brief no longer implies a scheduled thread.
BRIEFING_SCHEDULE = [
    tuple(x.split(",")) for x in
    os.environ.get("NBN_BRIEFING_UTC", "14:40,Morning;21:15,Afternoon").split(";") if x
] if os.environ.get("NBN_BRIEFING_ENABLED", "false").lower() == "true" else []

# Perception (api.perception.to). The deployed key is shared with the Marketing Node,
# so /feed polling in either service consumes the same account budget. Activates when set.
PERCEPTION_API_KEY = os.environ.get("NBN_PERCEPTION_API_KEY", "")
PERCEPTION_POLL_SECONDS = int(os.environ.get("NBN_PERCEPTION_POLL_SECONDS", "900"))
PERCEPTION_DIRECT_ENABLED = (
    os.environ.get("NBN_PERCEPTION_DIRECT_ENABLED", "true").lower() == "true"
)

# X read access — SHARED with the Marketing Node's bearer (Brady's call 2026-08-30);
# recent-search rate limits are per app, Node's 2x/day pulse + our throttled poll fit easily.
X_BEARER_TOKEN = os.environ.get("NBN_X_BEARER_TOKEN", "")
X_POLL_SECONDS = int(os.environ.get("NBN_X_POLL_SECONDS", "180"))
# Public X List whose MEMBERS define the primary watch roster (managed in the X app).
# Membership is fetched hourly and compiled into a since_id-gated search query —
# never the list timeline itself (that endpoint lacks since_id and re-bills reads).
X_LIST_ID = os.environ.get("NBN_X_LIST_ID", "")
X_LIST_REFRESH_SECONDS = int(os.environ.get("NBN_X_LIST_REFRESH_SECONDS", "3600"))
X_DETECTOR_ENABLED = os.environ.get("NBN_X_DETECTOR_ENABLED", "true").lower() == "true"

# Classes allowed to auto-publish when AUTOPOST_ENABLED. In editorial v2, a routine
# claim supported by one inspected Tier 1/2 receipt is allowed to ship as secondary;
# the independent batch editor remains the final judgment seat.
AUTOPOST_CLASSES = {
    c.strip() for c in os.environ.get(
        "NBN_AUTOPOST_CLASSES", "primary,secondary,corroborated"
    ).split(",") if c.strip()
}

# Autonomous publishes are scheduled this many seconds out (publish_at:"now" rejects
# drafts containing URLs; scheduled posts carry links fine — probed 2026-08-30)
PUBLISH_DELAY_SECONDS = int(os.environ.get("NBN_PUBLISH_DELAY_SECONDS", "30"))
PUBLISH_RECONCILE_SECONDS = int(os.environ.get("NBN_PUBLISH_RECONCILE_SECONDS", "300"))
PUBLISH_ANALYTICS_SECONDS = int(os.environ.get("NBN_PUBLISH_ANALYTICS_SECONDS", "900"))

# Source ladder. Enforcement is the safe code default. Observe mode records the
# policy's decision but forces every delivery to a human draft/tape.
SOURCE_POLICY_MODE = os.environ.get("NBN_SOURCE_POLICY_MODE", "enforce").strip().lower()
if SOURCE_POLICY_MODE not in {"observe", "enforce"}:
    raise RuntimeError("NBN_SOURCE_POLICY_MODE must be 'observe' or 'enforce'")
SOURCE_EVIDENCE_LOOKBACK_HOURS = float(
    os.environ.get("NBN_SOURCE_EVIDENCE_LOOKBACK_HOURS", "24")
)
SOURCE_RESOLUTION_CACHE_SECONDS = int(
    os.environ.get("NBN_SOURCE_RESOLUTION_CACHE_SECONDS", "3600")
)
# A live worker renews this lease in the background. Keep the orphan window short
# so a Railway deploy cannot pause intake for the duration of a long model cycle.
CYCLE_LEASE_SECONDS = int(os.environ.get("NBN_CYCLE_LEASE_SECONDS", "120"))
CYCLE_LEASE_HEARTBEAT_SECONDS = int(
    os.environ.get("NBN_CYCLE_LEASE_HEARTBEAT_SECONDS", "30")
)

# A Block must be backed by an EIC brief generated from the current Daily Intel
# window. This is a second bound after the provenance checks in briefing.py.
BRIEFING_MAX_AGE_SECONDS = int(
    os.environ.get("NBN_BRIEFING_MAX_AGE_SECONDS", "14400")
)

# Dead-man's switch: ping this URL after every successful cycle (healthchecks.io);
# alerts fire on SILENCE, catching crash and stall alike. Empty = disabled.
HEARTBEAT_URL = os.environ.get("NBN_HEARTBEAT_URL", "")

# Events, not write-ups: a story whose underlying EVENT is older than the freshness
# window never posts, however fresh the article covering it (HWI/quantum lesson,
# 2026-08-30; Brady: "got to earn that NEW tag"). Default: the EVENT window tracks the
# same time-varying schedule as the article gate (2.5h active / 6h quiet). Since the
# extracted event_date is date-only and measured from END of the event's day, this
# means: NEW = a same-day event (yesterday's only with an early-morning grace equal to
# the window). Set NBN_MAX_EVENT_AGE_HOURS to a number to override with a fixed window.
_fixed_event_age = os.environ.get("NBN_MAX_EVENT_AGE_HOURS", "")


def max_event_age_hours() -> float:
    if _fixed_event_age:
        return float(_fixed_event_age)
    from . import store
    return store.current_max_age_hours()
