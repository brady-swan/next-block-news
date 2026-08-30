"""The loop: poll -> triage -> draft -> gate -> publish. Plus a /health endpoint."""
import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import brain, briefing, config, lint, publisher, sources, store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("nbn.main")

STATE = {"started": time.time(), "cycles": 0, "last_cycle": None, "last_error": None}


def cycle(con) -> dict:
    items = sources.fetch_feeds() + sources.fetch_perception() + sources.fetch_x(con)
    inserted = store.upsert_new_items(con, items)
    # Keep summaries for freshly fetched items; DB-recovered items carry title only.
    summaries = {store.url_hash(i["url"]): i.get("summary", "") for i in items}
    pending = store.pending_items(con, config.MAX_ITEMS_PER_TRIAGE)
    fresh = []
    for it in pending:
        if store.is_stale(it.get("published", "")):
            store.set_status(con, it["url_hash"], "skipped", None, "stale at intake")
            continue
        it["summary"] = summaries.get(it["url_hash"], it.get("summary", ""))
        fresh.append(it)
    result = {"fetched": len(items), "new": len(inserted), "pending": len(fresh),
              "drafted": 0, "held": 0, "posted": 0}
    if not fresh:
        return result

    verdicts = brain.triage(fresh, store.recent_story_keys(con))
    handles = lint.verified_handles()

    # Persist every story_key first so corroboration sees all of this cycle's items.
    for item in verdicts:
        if item.get("story_key"):
            store.set_status(con, item["url_hash"], "new", item["story_key"])

    for item in verdicts:
        action = item.get("action", "skip")
        if action == "draft" and store.story_already_posted(con, item.get("story_key")):
            store.set_status(con, item["url_hash"], "skipped", item.get("story_key"),
                             "story already posted")
            continue
        if action != "draft":
            store.set_status(con, item["url_hash"], "skipped" if action == "skip" else "held",
                             item.get("story_key"), item.get("reason"))
            result["held" if action == "hold" else "drafted"] += 0
            continue

        article_text = sources.fetch_article_text(item["url"])
        try:
            d = brain.draft(item, article_text, handles)
        except Exception as exc:  # noqa: BLE001
            store.set_status(con, item["url_hash"], "error", item.get("story_key"), str(exc)[:200])
            continue

        post = d.get("post")
        if not post:
            store.set_status(con, item["url_hash"], "held", item.get("story_key"), "thin source")
            result["held"] += 1
            continue

        klass = item.get("class", "secondary")
        # Two-source rule, mechanized: a secondary story confirmed by 2+ independent
        # publishers is promoted to "corroborated" (auto-postable when enabled).
        corroboration = store.corroboration_count(con, item.get("story_key"))
        if klass == "secondary" and corroboration >= 2:
            klass = "corroborated"
        if d.get("needs_second_source") and klass == "secondary":
            # Actively hunt for an independent second source before holding.
            from . import verify
            v = verify.web_corroborate(item)
            if v.get("confirmed"):
                klass = "corroborated"
                store.set_status(con, item["url_hash"], "new", item.get("story_key"),
                                 f"web-corroborated via {v.get('confirming_outlet')}: "
                                 f"{v.get('confirming_url', '')[:150]}")
            else:
                store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                                 f"needs second source ({v.get('reason', '')[:150]})")
                result["held"] += 1
                continue

        src = article_text or item.get("summary", "")
        errors = lint.check(post, {**d, "_source_text": src}, item)
        if errors:
            # One retry with the violations fed back; still failing -> held.
            log.info("lint retry %s: %s", item["title"][:60], errors)
            try:
                d = brain.draft(item, src + "\n\n[Your previous draft was rejected by the "
                                f"style gate for: {'; '.join(errors)}. Rewrite avoiding "
                                "exactly those violations.]", handles)
                post = d.get("post")
                errors = lint.check(post, {**d, "_source_text": src}, item) if post else ["empty retry"]
            except Exception as exc:  # noqa: BLE001
                errors = [f"retry failed: {exc}"]
        if errors:
            store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                             "lint: " + "; ".join(errors)[:300])
            log.warning("lint held %s: %s", item["title"][:60], errors)
            result["held"] += 1
            continue

        mode, nuelink_id = publisher.publish(post, item["url"], klass)
        store.set_status(con, item["url_hash"], "posted" if mode == "IMMEDIATE" else "drafted",
                         item.get("story_key"))
        store.log_post(con, item.get("story_key"), item["url_hash"], klass, post,
                       item["url"], mode, nuelink_id)
        result["posted" if mode == "IMMEDIATE" else "drafted"] += 1
    return result


class Health(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        con = store.connect()
        body = json.dumps({**STATE, "db": store.status_summary(con),
                           "autopost": config.AUTOPOST_ENABLED}).encode()
        con.close()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # quiet
        pass


def run():
    threading.Thread(
        target=lambda: ThreadingHTTPServer(("0.0.0.0", config.PORT), Health).serve_forever(),
        daemon=True,
    ).start()
    log.info("next-block-news worker up; autopost=%s poll=%ss", config.AUTOPOST_ENABLED,
             config.POLL_SECONDS)
    con = store.connect()
    while True:
        try:
            STATE["last_cycle"] = cycle(con)
            if config.NODE_READ_TOKEN:
                briefing.maybe_run(con)
            STATE["cycles"] += 1
            STATE["last_error"] = None
        except Exception as exc:  # noqa: BLE001 - the loop survives everything
            STATE["last_error"] = str(exc)[:300]
            log.exception("cycle failed")
        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    run()
