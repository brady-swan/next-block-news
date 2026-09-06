import datetime as dt
import hashlib
import json
import time
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import httpx

from nbn import config, desk_prep, editor, intake_triage, lead_material, main, newsroom, sources, store
from tests.support import temporary_store


def tweet(ident="400", **changes):
    return {"id": ident, "author_id": "7", "text": "A short Bitcoin lead",
            "created_at": "2026-09-06T19:00:00Z", **changes}


INCLUDES = {"users": [{"id": "7", "username": "BitcoinArchive"}]}


def page(ident="400", token=None, **extra):
    return {"data": [tweet(ident)], "includes": INCLUDES,
            "meta": {"newest_id": ident, **({"next_token": token} if token else {})}, **extra}


@contextmanager
def x_client(handler, queries=None):
    client = MagicMock()
    client.return_value.__enter__.return_value.get.side_effect = handler
    with patch.object(sources.httpx, "Client", client), \
            patch.object(config, "X_BEARER_TOKEN", "test"), \
            patch.object(config, "X_POLL_SECONDS", 0), \
            patch.object(config, "X_DETECTOR_ENABLED", False), \
            patch.object(sources, "X_PRIMARY_QUERIES", queries or ["from:BitcoinArchive"]), \
            patch.object(sources, "X_RESEARCH_QUERIES", []), \
            patch.object(sources, "_list_member_queries", return_value=[]):
        yield client.return_value.__enter__.return_value


def response(body, status=200):
    return httpx.Response(status, json=body, request=httpx.Request("GET", "https://api.x.com/test"))


def saved_lead(con, ident="400", text=None, **changes):
    t = tweet(ident, note_tweet={"text": text or "Full note " * 120})
    item = sources._x_item(t, INCLUDES, "from:BitcoinArchive", time.time())
    item.update(changes)
    return store.upsert_new_items(con, [item])[0]


class LeadFidelityTests(unittest.TestCase):
    def test_long_note_quotes_media_links_and_metric_age(self):
        original = tweet("399", author_id="8", text="The creator's original demonstration")
        includes = {"users": INCLUDES["users"] + [{"id": "8", "username": "creator"}],
                    "tweets": [original], "media": [{"media_key": "m1", "type": "video",
                    "preview_image_url": "https://pbs.twimg.com/image.jpg", "alt_text": "A demo"}]}
        t = tweet(note_tweet={"text": "A" * 900 + " meaningful ending",
                    "entities": {"urls": [{"expanded_url": "https://example.com/original"}]}},
                  referenced_tweets=[{"type": "quoted", "id": "399"}, {"type": "quoted", "id": "398"}],
                  attachments={"media_keys": ["m1"]}, public_metrics={"like_count": 0})
        material = lead_material.capture(t, includes, 1788721260)
        self.assertTrue(material["post"]["text"].endswith("meaningful ending"))
        self.assertEqual(material["post"]["engagement"]["likes"], 0)
        self.assertIsNone(material["post"]["engagement"]["reposts"])
        self.assertEqual(material["post"]["engagement"]["post_age_seconds"], 60)
        self.assertFalse(material["post"]["media"][0]["visually_inspected"])
        self.assertEqual(material["referenced_posts"][0]["post"]["handle"], "creator")
        self.assertFalse(material["referenced_posts"][1]["available"])
        self.assertIn("https://example.com/original", lead_material.reference_urls(material))
        self.assertIn("https://x.com/creator/status/399", lead_material.reference_urls(material))

    def test_current_note_alias_and_unicode_budget(self):
        material = lead_material.capture(tweet(note_post={"text": "₿😊" * 15000}), INCLUDES, time.time())
        self.assertLessEqual(len(lead_material.encode(material).encode()), lead_material.MAX_BYTES)
        self.assertTrue(material["post"]["long_text_available"])
        self.assertTrue(material["post"]["text_truncated"])
        self.assertTrue(lead_material.parse(lead_material.encode(material)))

    def test_enrichment_preserves_skips_first_seen_and_canonical_collision(self):
        with temporary_store() as con:
            saved = saved_lead(con, text="Short", url="https://example.com/shared")
            h = saved["url_hash"]
            con.execute("UPDATE items SET status='skipped',first_seen=42 WHERE url_hash=?", (h,))
            con.commit()
            richer = {**saved, "source_material": lead_material.encode(lead_material.capture(
                tweet(note_tweet={"text": "Enriched " * 400}), INCLUDES, time.time()))}
            self.assertEqual(store.upsert_new_items(con, [richer]), [])
            collision = {**richer, "source_material": lead_material.encode(lead_material.capture(
                tweet("500", note_tweet={"text": "Different " * 700}), INCLUDES, time.time()))}
            store.upsert_new_items(con, [collision, saved])
            row = dict(con.execute("SELECT * FROM items WHERE url_hash=?", (h,)).fetchone())
            self.assertEqual((row["status"], row["first_seen"], row["title"]), ("skipped", 42, "Short"))
            self.assertEqual(lead_material.parse(row["source_material"])["post"]["text"], "Enriched " * 400)

    def test_new_quote_survives_enrichment_when_root_must_shrink_to_fit(self):
        t = tweet(note_tweet={"text": "A" * 9000}, referenced_tweets=[{"type": "quoted", "id": "399"}])
        prior = lead_material.capture(t, INCLUDES, time.time())
        incoming = lead_material.capture(t, {**INCLUDES, "tweets": [tweet("399", text="Q" * 1800)]}, time.time())
        enriched = lead_material.merge(prior, incoming)
        self.assertTrue(enriched["referenced_posts"][0]["available"])
        self.assertTrue(enriched["referenced_posts"][0]["post"]["text"].startswith("Q"))
        self.assertLessEqual(len(lead_material.encode(enriched).encode()), 12 * 1024)

    def test_pagination_restart_ack_and_first_page_high_water(self):
        query = "from:BitcoinArchive"
        qkey = hashlib.sha256(query.encode()).hexdigest()[:12]
        cursor_key = "x_cursor:" + qkey
        calls = []

        def get(url, params):
            calls.append(params)
            token = params.get("next_token")
            return response({None: page("400", "p2"), "p2": page("300", "p3"),
                             "p3": page("200", "p4"), "p4": page("100")}[token])

        with temporary_store() as con, x_client(get):
            store.kv_set(con, "x_since_" + qkey, "10")
            batch = sources.fetch_x(con)
            self.assertEqual(len(batch), 3)
            self.assertEqual(store.kv_get(con, cursor_key), "")
            # No acknowledgment on a failed insert: the next collection replays page one.
            with patch.object(store, "upsert_new_items", side_effect=RuntimeError("disk")):
                with self.assertRaises(RuntimeError):
                    store.upsert_new_items(con, batch)
            self.assertEqual(store.kv_get(con, cursor_key), "")
            store.upsert_new_items(con, batch)
            sources.acknowledge(con, batch)
            self.assertEqual(json.loads(store.kv_get(con, cursor_key))["next_token"], "p4")
            reopened = store.connect()
            try:
                rest = sources.fetch_x(reopened)
                self.assertEqual(len(rest), 1)
                store.upsert_new_items(reopened, rest)
                sources.acknowledge(reopened, rest)
                self.assertEqual(json.loads(store.kv_get(reopened, cursor_key)), {"since_id": "400"})
                self.assertEqual(reopened.execute("SELECT COUNT(*) FROM items").fetchone()[0], 4)
            finally:
                reopened.close()
            self.assertTrue(all(p["since_id"] == "10" for p in calls))
            self.assertIn("note_tweet", calls[0]["tweet.fields"])
            self.assertIn("referenced_tweets.id.author_id", calls[0]["expansions"])

    def test_worker_acknowledges_after_commit_and_never_after_failed_upsert(self):
        for fail in (False, True):
            with self.subTest(fail=fail), temporary_store() as con:
                batch = sources.CollectedBatch()
                batch.append(sources._x_item(tweet(), INCLUDES, "guide", time.time()))
                batch.checkpoints["x_cursor:test"] = '{"since_id":"400"}'
                def check_boundary(*args, **kwargs):
                    self.assertTrue(con.execute("SELECT 1 FROM items").fetchone())
                    self.assertEqual(store.kv_get(con, "x_cursor:test"), '{"since_id":"400"}')
                    raise RuntimeError("stop after boundary")
                real_upsert = store.upsert_new_items
                with patch.object(sources, "fetch_feeds", return_value=[]), \
                        patch.object(sources, "fetch_edgar", return_value=[]), \
                        patch.object(sources, "fetch_perception", return_value=[]), \
                        patch.object(sources, "fetch_x", return_value=batch), \
                        patch.object(main.publisher, "reconcile_mutations", return_value={}), \
                        patch.object(main.node_discovery, "ingest"), \
                        patch.object(store, "renew_cycle_lease", return_value=True), \
                        patch.object(store, "upsert_new_items", side_effect=RuntimeError("disk") if fail else real_upsert), \
                        patch.object(intake_triage, "route_cycle", side_effect=check_boundary):
                    with self.assertRaisesRegex(RuntimeError, "disk" if fail else "stop after boundary"):
                        main._cycle_locked(con, "test-owner")
                if fail:
                    self.assertEqual(store.kv_get(con, "x_cursor:test"), "")

    def test_partial_failure_keeps_continuation_and_unrelated_queries_run(self):
        calls = []

        def get(url, params):
            calls.append(params)
            if params["query"] == "one" and params.get("next_token"):
                return response({}, 500)
            return response(page("400", "p2") if params["query"] == "one" else page("900"))

        with temporary_store() as con, x_client(get, ["one", "two"]):
            batch = sources.fetch_x(con)
            self.assertEqual(len(batch), 2)
            store.upsert_new_items(con, batch)
            sources.acknowledge(con, batch)
            state = json.loads(store.kv_get(con, "x_cursor:" + hashlib.sha256(b"one").hexdigest()[:12]))
            self.assertEqual(state["next_token"], "p2")
            self.assertEqual(calls[-1]["query"], "two")

    def test_shared_429_stops_requests_without_acknowledging_failed_page(self):
        def get(url, params):
            return response({}, 429) if params.get("next_token") else response(page("400", "p2"))
        with temporary_store() as con, x_client(get, ["one", "two"]) as http:
            batch = sources.fetch_x(con)
            self.assertEqual(http.get.call_count, 2)
            self.assertEqual(len(batch.checkpoints), 1)
            self.assertEqual(len(batch), 1)
            self.assertFalse(con.execute("SELECT 1 FROM kv WHERE k LIKE 'x_cursor:%'").fetchone())

    def test_malformed_page_does_not_advance_but_other_query_survives(self):
        def get(url, params):
            return response(page(data=[tweet(), {"text": "missing id"}]) if params["query"] == "one"
                            else page("900"))
        with temporary_store() as con, x_client(get, ["one", "two"]):
            batch = sources.fetch_x(con)
            self.assertEqual(len(batch), 1)
            self.assertEqual(len(batch.checkpoints), 1)

    def test_empty_initial_poll_does_not_freeze_a_six_hour_lower_bound(self):
        with temporary_store() as con, x_client(lambda u, params: response({"meta": {"result_count": 0}})):
            batch = sources.fetch_x(con)
            self.assertTrue(all(json.loads(state) == {} for state in batch.checkpoints.values()))

    def test_pilot_bootstrap_before_haiku_unknown_dates_and_restart(self):
        body = """<rss><channel><item><title>Old Core release</title><link>https://bitcoincore.org/old</link>
        <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item><item><title>Undated finding</title>
        <link>https://bitcoincore.org/unknown</link></item></channel></rss>"""
        mock = MagicMock()
        mock.return_value.__enter__.return_value.get.return_value = httpx.Response(
            200, text=body, request=httpx.Request("GET", "https://bitcoincore.org/en/rss.xml"))
        with temporary_store() as con, patch.object(sources.httpx, "Client", mock), \
                patch.object(sources, "FEEDS", {"Bitcoin Core": sources.PILOT_FEEDS["Bitcoin Core"]}):
            batch = sources.fetch_feeds(con)
            self.assertTrue(batch[0]["_bootstrap_background"])
            self.assertNotIn("_bootstrap_background", batch[1])
            fresh = store.upsert_new_items(con, [{**r, "discovery_origin": "rss"} for r in batch])
            self.assertEqual(len(fresh), 1)
            work = store.intake_triage_work(con, fresh, recovery_limit=25, recovery_hours=24)
            self.assertEqual(len(work), 1)
            self.assertEqual(work[0]["title"], "Undated finding")
            self.assertEqual(con.execute("SELECT decision_category FROM items WHERE title='Old Core release'").fetchone()[0],
                             "bootstrap_background")
            sources.acknowledge(con, batch)
            self.assertNotIn("_bootstrap_background", sources.fetch_feeds(con)[0])

    def session(self, con, rows):
        with patch.object(newsroom.anthropic, "Anthropic"):
            return newsroom.NewsroomSession(run_id="fidelity", inventory=rows,
                recent_clusters=[], theme_snapshot=[], handles={}, con=con, reservation="r",
                prep_mode="off", research_mode="off", compact_enabled=True)

    def test_durable_pending_preparation_writer_retrieval_and_retry(self):
        with temporary_store() as con:
            saved = saved_lead(con)
            rows = store.pending_items(con, 25)
            self.assertTrue(rows[0]["source_material"])
            self.assertIn("Full note", desk_prep._card(rows[0])["x_lead"]["text"])
            session = self.session(con, rows)
            packet = session._initial_packet()
            card = packet["intake_board"][0]
            self.assertIsNotNone(card["first_seen_at"])
            result = session._read_desk_context([card["full_lead_context_id"]])
            self.assertTrue(result["ok"])
            self.assertEqual(result["rows"][0]["material"]["post"]["text"], "Full note " * 120)
            self.assertFalse(session.fetches)  # Discovery retrieval never mints evidence.
            retry = main._retry_inventory(con, [{"item_hash": saved["url_hash"],
                "manual_draft_only": False, "context_json": json.dumps(saved)}], "retry", materialize=False)
            self.assertEqual(retry[0]["source_material"], rows[0]["source_material"])

    def test_unicode_material_fits_default_retrieval_and_small_limit_is_explicit(self):
        with temporary_store() as con:
            saved_lead(con, text="😊" * 10000)
            rows = store.pending_items(con, 25)
            session = self.session(con, rows)
            ident = session._initial_packet()["intake_board"][0]["full_lead_context_id"]
            result = session._read_desk_context([ident])
            self.assertEqual(len(result["rows"]), 1)
            self.assertLessEqual(len(json.dumps(result, ensure_ascii=False).encode()), 16 * 1024)
            session = self.session(con, rows)
            ident = session._initial_packet()["intake_board"][0]["full_lead_context_id"]
            with patch.object(config, "COMPACT_DESK_RETRIEVAL_BYTES", 2048):
                result = session._read_desk_context([ident])
            self.assertTrue(result["rows"][0]["truncated_for_capacity"])
            self.assertEqual(session.lead_context_truncations, 1)
            self.assertEqual(session.context_capacity_hits, 1)

    def test_compaction_preserves_all_material_ids_and_owner_note(self):
        with temporary_store() as con:
            for index in range(25):
                saved_lead(con, ident=str(index + 400), text="Long text " * 900)
            rows = store.pending_items(con, 25)
            rows[0]["_owner_reconsider"] = {"requested_by": "Brady", "prior_reason": "earlier skip"}
            session = self.session(con, rows)
            with patch.object(store, "recent_feed_posts", return_value=[{
                "effective_at": time.time(), "story_key": str(n), "body": "B" * 4000,
                "class": "secondary",
                "receipt_url": "https://example.com/" + str(n), "performance": {},
            } for n in range(40)]):
                packet = session._initial_packet()
            self.assertLessEqual(len(json.dumps(packet, ensure_ascii=False).encode()), 64 * 1024)
            self.assertEqual(len(packet["intake_board"]), 25)
            self.assertTrue(all(r["full_lead_context_id"] in session.context_rows for r in packet["intake_board"]))
            self.assertEqual(packet["intake_board"][0]["owner_override"]["requested_by"], "Brady")

    def test_prep_packet_compacts_without_losing_candidate_identity(self):
        with temporary_store() as con:
            for n in range(25):
                saved_lead(con, ident=str(n + 400))
            rows = store.pending_items(con, 25)
            packet, compacted = desk_prep._packet([desk_prep._card(r) for r in rows], [], 22000)
            self.assertTrue(compacted)
            self.assertLessEqual(len(packet.encode()), 22000)
            self.assertEqual(len(json.loads(packet)["candidates"]), 25)

    def test_editorial_guidance_is_aligned_without_losing_house_limits(self):
        for prompt in (intake_triage.SYSTEM, desk_prep.SYSTEM, newsroom.ORIENTATION_BRIEF, editor.BATCH_EDITOR_PROMPT):
            self.assertIn("software releases", prompt)
            self.assertIn("demonstrations", prompt)
        self.assertIn("Strategy, Metaplanet and Strive", newsroom.ORIENTATION_BRIEF)
        self.assertIn("trading signals", newsroom.ORIENTATION_BRIEF)
        self.assertIn("Do not put two long", newsroom.NEWSROOM_V2_SYSTEM)


if __name__ == "__main__":
    unittest.main()
