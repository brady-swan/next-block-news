"""Collection-only path for the Codex pilot; no editorial decisions or delivery jobs."""
import json
import time

from . import config, node_discovery, sources, store


def collect(con, *, lease_owner):
    started = time.time()
    node = node_discovery.ingest(con)
    groups = [("rss", sources.fetch_feeds(con)), ("edgar", sources.fetch_edgar(con)),
              ("x", sources.fetch_x(con)), ("perception", sources.fetch_perception(con))]
    items = [{**item, "discovery_origin": origin} for origin, batch in groups for item in batch]
    if not store.renew_cycle_lease(con, lease_owner, ttl_seconds=config.CYCLE_LEASE_SECONDS):
        raise RuntimeError("intake lease lost before durable collection")
    inserted = store.upsert_new_items(con, items)
    for _, batch in groups:
        sources.acknowledge(con, batch)
    result = {"operating_mode": "infrastructure", "fetched": len(items), "new": len(inserted),
              "collected_at": time.time(), "duration_seconds": round(time.time() - started, 2),
              "by_origin": {name: len(batch) for name, batch in groups}, "node": node,
              "editorial_calls": 0, "delivery_jobs_executed": 0}
    store.kv_set(con, "reporter:last_intake", json.dumps(result, separators=(",", ":")))
    from . import reporter_remote
    try:
        result["coverage_sync"] = reporter_remote.synchronize(con)
    except Exception as exc:
        result["coverage_sync"] = {"ok": False, "error": type(exc).__name__}
        store.kv_set(con, "reporter:coverage_sync", json.dumps(result["coverage_sync"]))
    return result
