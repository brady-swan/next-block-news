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
    items = (sources.fetch_feeds() + sources.fetch_edgar()
             + sources.fetch_perception() + sources.fetch_x(con))
    inserted = store.upsert_new_items(con, items)
    # Keep summaries for freshly fetched items; DB-recovered items carry title only.
    summaries = {store.url_hash(i["url"]): i.get("summary", "") for i in items}
    pending = store.pending_items(con, config.MAX_ITEMS_PER_TRIAGE)
    fresh = []
    for it in pending:
        if store.is_stale(it.get("published", "")):
            store.set_status(con, it["url_hash"], "skipped", None, "stale at intake")
            continue
        if store.is_non_english(it.get("title", "")):
            store.set_status(con, it["url_hash"], "skipped", None, "non-English source")
            continue
        it["summary"] = summaries.get(it["url_hash"], it.get("summary", ""))
        fresh.append(it)
    result = {"fetched": len(items), "new": len(inserted), "pending": len(fresh),
              "drafted": 0, "held": 0, "posted": 0, "uncertain": 0,
              "failed": 0, "taped": 0}
    if not fresh:
        return result

    verdicts = brain.triage(fresh, store.recent_story_keys(con), store.open_story_keys(con))
    handles = lint.verified_handles()

    # Persist every story_key first so corroboration sees all of this cycle's items.
    for item in verdicts:
        if item.get("story_key"):
            store.set_status(con, item["url_hash"], "new", item["story_key"])

    for item in verdicts:
        action = item.get("action", "skip")
        story_key = item.get("story_key")
        if action == "draft" and store.story_handled(con, story_key):
            store.set_status(con, item["url_hash"], "skipped", item.get("story_key"),
                             "story already handled")
            continue
        if action == "update" and not store.story_reader_covered(con, story_key):
            store.set_status(con, item["url_hash"], "held", story_key,
                             "update lacks exact reader-covered story")
            result["held"] += 1
            continue
        if action not in ("draft", "update"):
            status = "skipped" if action == "skip" else "held"
            store.set_status(con, item["url_hash"], status,
                             item.get("story_key"), item.get("reason"))
            if status == "held":
                result["held"] += 1
            continue

        item["_coverage_action"] = action

        # Detector tips (aggregator accounts) are never our source: hunt the primary
        # first, then draft from IT. The detector + confirming outlet = 2 distinct
        # sources on the story_key, so a confirmed tip rides the corroborated lane.
        if item["source"].startswith("X detector"):
            from . import verify
            v = verify.web_corroborate(item)
            if not v.get("confirmed"):
                store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                                 f"detector tip unconfirmed ({v.get('reason', '')[:120]})")
                result["held"] += 1
                continue
            if store.event_is_stale(v.get("earliest_coverage_date"), config.max_event_age_hours()):
                store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                                 f"stale event: earliest coverage {v['earliest_coverage_date']}")
                result["held"] += 1
                continue
            item["url"] = v["confirming_url"]
            item["source"] = v.get("confirming_outlet", "confirmed source")

        article_text = sources.fetch_article_text(item["url"])
        # Exact prior reader coverage authorizes UPDATE. Prefix-key matching is unsafe:
        # unrelated keys can collide and drafts/tape output are not reader coverage.
        covered = [r["body"].split("\n")[0][:200] for r in con.execute(
            "SELECT body FROM posts WHERE story_key=?"
            " AND mode IN ('IMMEDIATE','UNCERTAIN') ORDER BY created DESC LIMIT 2",
            (story_key,)).fetchall()]
        try:
            d = brain.draft(item, article_text, handles, already_covered=covered)
        except Exception as exc:  # noqa: BLE001
            store.set_status(con, item["url_hash"], "error", item.get("story_key"), str(exc)[:200])
            continue

        post = d.get("post")
        if not post:
            store.set_status(con, item["url_hash"], "held", item.get("story_key"), "thin source")
            result["held"] += 1
            continue

        # Events, not write-ups: the drafter dates the underlying EVENT from the source
        # text; an event older than the window never posts, however fresh the article
        # (HWI Aug 18 / StarkWare Aug 26 posted as NEW on Aug 30 — Brady: should not
        # have posted at all). Null/unparseable dates pass; the article gate already ran.
        if store.event_is_stale(d.get("event_date"), config.max_event_age_hours()):
            store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                             f"stale event: dated {d['event_date']}, window "
                             f"{config.max_event_age_hours():g}h")
            log.info("stale event held %s (event_date %s)", item["title"][:60], d["event_date"])
            result["held"] += 1
            continue

        # A data story deserves a data receipt: if the load-bearing number belongs to
        # a named provider and our only link is a second-tier aggregator, that link
        # does not ride the feed — hold for a better source or Brady's call.
        from urllib.parse import urlparse
        _dom = (urlparse(item["url"]).netloc or "").lower().removeprefix("www.")
        if d.get("data_provider") and _dom in config.LOW_TIER_DOMAINS:
            store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                             f"second-tier receipt ({_dom}) for {d['data_provider']} data"
                             " — source from the provider")
            result["held"] += 1
            continue

        klass = item.get("class", "secondary")
        # Two-source rule, mechanized: a secondary story confirmed by 2+ independent
        # publishers is promoted to "corroborated" (auto-postable when enabled).
        corroboration = store.corroboration_count(con, item.get("story_key"))
        if klass == "secondary" and corroboration >= 2:
            klass = "corroborated"
            # Count-based promotion proves the story is REAL, not that it is FRESH —
            # two rewrites of a 3-day-old report count the same as two fresh reports
            # (Galaxy dormant-wallets miss, 2026-08-30). One web pass for recency.
            from . import verify
            v = verify.web_corroborate(item)
            if store.event_is_stale(v.get("earliest_coverage_date"), config.max_event_age_hours()):
                store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                                 f"stale event: earliest coverage {v['earliest_coverage_date']}")
                result["held"] += 1
                continue
        if d.get("needs_second_source") and klass == "secondary":
            # Actively hunt for an independent second source before holding.
            from . import verify
            v = verify.web_corroborate(item)
            if v.get("confirmed") and store.event_is_stale(
                    v.get("earliest_coverage_date"), config.max_event_age_hours()):
                store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                                 f"stale event: earliest coverage {v['earliest_coverage_date']}")
                result["held"] += 1
                continue
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
                                "exactly those violations.]", handles,
                                already_covered=covered)
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

        # The Editor: last-mile judgment (feed context + craft) after all gates.
        # Only gates autonomous publishes; drafts get Brady's eyes anyway.
        editor_note = None
        if config.AUTOPOST_ENABLED and klass in config.AUTOPOST_CLASSES:
            from . import editor
            item["class"] = klass
            ed = editor.review(post, item, con)
            editor_note = f"{ed['verdict']}: {ed['reason']}"[:300]
            if ed["verdict"] == "spike":
                store.set_status(con, item["url_hash"], "held", item.get("story_key"),
                                 f"editor spiked: {ed['reason'][:220]}")
                log.info("editor spiked %s: %s", item["title"][:60], ed["reason"][:120])
                result["held"] += 1
                continue
            if ed["verdict"] == "revise" and ed["post"] != post:
                # Revised copy must re-pass the full lint; on failure, original stands.
                if not lint.check(ed["post"], {**d, "_source_text": src}, item):
                    post = ed["post"]
                else:
                    log.warning("editor revision failed lint; original published")

        chart = sources.chart_image(item["url"])
        mode, publisher_ref = publisher.publish(post, item["url"], klass, image=chart)
        lifecycle = {
            "IMMEDIATE": ("posted", "posted"),
            "DRAFT": ("drafted", "drafted"),
            "UNCERTAIN": ("uncertain", "uncertain"),
            "FAILED": ("failed", "failed"),
            "TAPE": ("taped", "taped"),
        }
        item_status, counter = lifecycle.get(mode, ("failed", "failed"))
        store.set_status(con, item["url_hash"], item_status, item.get("story_key"))
        store.log_post(con, item.get("story_key"), item["url_hash"], klass, post,
                       item["url"], mode, publisher_ref, editor_note=editor_note)
        result[counter] += 1
    return result


class Health(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        from urllib.parse import parse_qs, urlparse
        parsed = urlparse(self.path)
        if parsed.path == "/dismiss":
            q = parse_qs(parsed.query)
            token = (q.get("k") or [""])[0]
            if not config.REPORT_TOKEN or token != config.REPORT_TOKEN:
                self.send_response(403)
                self.end_headers()
                return
            kind = (q.get("kind") or [""])[0]
            ref = (q.get("id") or [""])[0]
            day = (q.get("d") or [""])[0]
            if kind in ("post", "item", "audit") and ref:
                con = store.connect()
                store.kv_set(con, f"dismissed:{kind}:{ref}",
                             str(time.time()))
                con.close()
            self.send_response(302)
            self.send_header("Location", f"/report?k={token}" + (f"&d={day}" if day else ""))
            self.end_headers()
            return
        if parsed.path == "/report":
            token = (parse_qs(parsed.query).get("k") or [""])[0]
            if not config.REPORT_TOKEN or token != config.REPORT_TOKEN:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"forbidden")
                return
            from . import report
            day = (parse_qs(parsed.query).get("d") or [None])[0]
            con = store.connect()
            body = report.render(con, day=day).encode()
            con.close()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        con = store.connect()
        body = json.dumps({**STATE, "db": store.status_summary(con),
                           "autopost": config.AUTOPOST_ENABLED}).encode()
        con.close()
        stale = time.time() - STATE.get("last_cycle_ts", STATE["started"]) > 600
        self.send_response(500 if stale else 200)
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
            if config.AUDIT_UTC:
                from . import audit
                audit.maybe_run(con)
            STATE["cycles"] += 1
            STATE["last_cycle_ts"] = time.time()
            STATE["last_error"] = None
            if config.HEARTBEAT_URL:
                try:
                    import httpx
                    httpx.get(config.HEARTBEAT_URL, timeout=5)
                except Exception:  # noqa: BLE001 - heartbeat failure never breaks news
                    pass
        except Exception as exc:  # noqa: BLE001 - the loop survives everything
            STATE["last_error"] = str(exc)[:300]
            log.exception("cycle failed")
        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    run()
