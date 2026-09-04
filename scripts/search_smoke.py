"""Exercise production search capacity and local caching without model or publishing calls."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nbn import config, newsroom, store  # noqa: E402


def run(query: str = "site:sec.gov bitcoin", *, con=None) -> dict:
    if not config.SEARCH_RESILIENCE_ENABLED:
        raise RuntimeError("NBN_SEARCH_RESILIENCE_ENABLED is false")
    owns_connection = con is None
    con = con or store.connect()
    run_id = f"search-smoke:{int(time.time())}"
    try:
        first_session = newsroom.NewsroomSession(
            run_id=run_id,
            inventory=[],
            recent_clusters=[],
            theme_snapshot=[],
            handles={},
            con=con,
            reservation="search-smoke-no-model",
        )
        first = first_session._search_web({"query": query, "candidate_ids": []})
        if not first.get("ok"):
            raise RuntimeError(
                f"production search path unavailable: {first.get('reason') or first.get('kind')}"
            )
        second_session = newsroom.NewsroomSession(
            run_id=f"{run_id}:cache",
            inventory=[],
            recent_clusters=[],
            theme_snapshot=[],
            handles={},
            con=con,
            reservation="search-smoke-no-model",
        )
        second = second_session._search_web({"query": query, "candidate_ids": []})
        if not second.get("ok") or not second.get("cached"):
            raise RuntimeError("second identical search did not use the local cache")
        state = store.search_provider_state(con)
        return {
            "ok": True,
            "account_state": str(state.get("state") or "unknown"),
            "plan_name": str(state.get("plan_name") or ""),
            "remaining": state.get("total_searches_left"),
            "first_source": "local_cache" if first.get("cached") else "provider",
            "result_count": len(first.get("results") or []),
            "second_source": "local_cache",
            "provider_http_attempts": first_session.search_http_attempts,
        }
    finally:
        if owns_connection:
            con.close()


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
