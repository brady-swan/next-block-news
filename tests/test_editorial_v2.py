import time
import unittest
import json
from unittest.mock import Mock, patch
from types import SimpleNamespace

from contextlib import ExitStack

from nbn import (
    brain, config, desk_prep, editor, lint, main, newsroom, publisher, report, search, source_policy, sources, store,
    verify,
)
from tests.support import temporary_store


def candidate(item_hash="candidate-1"):
    return {
        "url_hash": item_hash, "source": "SEC", "title": "SEC updates Bitcoin policy",
        "url": "https://www.sec.gov/newsroom/press-releases/test", "published": "",
        "summary": "", "discovery_origin": "rss", "discovery_context": "",
    }


def inspected(fetch_id, url, source, text, *, inspected_at=None):
    ref = source_policy.classify(url, source)
    return newsroom.FetchRecord(
        fetch_id=fetch_id, requested_url=url, final_url=url, canonical_url=url,
        redirect_chain=(url,), source=ref, byline="", text=text,
        content_fingerprint=source_policy.content_fingerprint(text), outcome="ok",
        inspected_at=inspected_at or time.time(),
    )


def materialization_fixture(con, run_id="run:v2-fixture", post=None):
    saved = store.upsert_new_items(con, [{
        "source": "SEC", "title": "SEC updates Bitcoin policy",
        "url": f"https://www.sec.gov/newsroom/press-releases/{run_id.replace(':', '-')}",
        "published": "", "summary": "",
    }])[0]
    row = {**candidate(saved["url_hash"]), **saved}
    record = inspected(
        "fetch-sec", row["url"], "SEC", "The SEC announced a Bitcoin policy update.",
    )
    resolution = verify.ResolutionResult(
        row["url_hash"], "sec-bitcoin-policy", row["source"], record.source,
        record.source, record.text, "selected", True, "primary_artifact", True,
        False, record.final_url, source_policy.artifact_fingerprint(record.final_url),
        record.content_fingerprint, None, "v2 fixture", (), resolver_path="run_newsroom",
    )
    copy = post if post is not None else "The SEC announced a Bitcoin policy update."
    draft = {
        "post": copy, "reader_value": "Policy changed.", "needs_second_source": False,
        "selected_fetch_id": record.fetch_id, "evidence_fetch_ids": [record.fetch_id],
        "_source_text": record.text, "editorial_warnings": [],
    }
    verdict = {
        **row, "action": "draft", "story_key": "sec-bitcoin-policy",
        "class": "secondary", "reason": "useful",
    }
    attempt = {
        "story_id": "sec", "canonical_key": "sec-bitcoin-policy",
        "identity_valid": True, "members": [row["url_hash"]],
        "headlines": [row["title"]], "submitted_story_key": "sec-bitcoin-policy",
        "existing_cluster_key": "", "allow_alias": True, "proposed_post": copy,
        "failure": "", "objective": "", "evidence": [{
            "inspected_at": record.inspected_at, "requested_url": record.requested_url,
            "final_url": record.final_url, "canonical_url": record.canonical_url,
            "source_label": record.source.display_name,
            "content_fingerprint": record.content_fingerprint, "text": record.text,
        }],
    }
    outcome = newsroom.NewsroomOutcome(
        run_id, {"stories": [{"story_id": "sec"}]}, "b" * 64,
        [verdict], {row["url_hash"]: resolution}, {row["url_hash"]: draft},
        {record.fetch_id: record}, {"rounds": 1}, Mock(),
        {row["url_hash"]: "sec"}, [attempt], [{
            "story_id": "sec", "state": "pending",
            "details": {"validation": "accepted"},
        }],
    )
    session = Mock()
    session.conduct.return_value = outcome
    return row, record, draft, session


class EditorialV2Tests(unittest.TestCase):
    @staticmethod
    def result_counts():
        return {"held": 0, "skipped": 0, "posted": 0, "drafted": 0,
                "uncertain": 0, "failed": 0, "taped": 0}

    def test_v210_prompts_teach_selection_compression_without_style_gates(self):
        self.assertEqual(newsroom.PROMPT_VERSION, "editorial-core-v2.10")
        self.assertIn("Write selectively", newsroom.ORIENTATION_BRIEF)
        self.assertIn("small 13F allocation", newsroom.ORIENTATION_BRIEF)
        self.assertIn("Never stack two sentences", newsroom.ORIENTATION_BRIEF)
        self.assertIn("split, simplify", editor.EDITOR_PROMPT)
        self.assertIn("perform a real compression pass", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("sentence by sentence", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("sentence two is still a buried lede", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("For research, lead", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("MUST repeat the complete final post", editor.BATCH_EDITOR_PROMPT)
        self.assertNotIn("Research deeply", newsroom.ORIENTATION_BRIEF)
        self.assertNotIn("24 words", newsroom.ORIENTATION_BRIEF)

    def test_assignment_desk_can_suppress_empty_sonnet_wake(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            saved = store.upsert_new_items(con, [{
                "source": "Example", "title": "Unrelated corporate update",
                "url": "https://example.com/unrelated", "published": "", "summary": "",
            }])[0]
            row = dict(con.execute("SELECT * FROM items WHERE url_hash=?",
                                   (saved["url_hash"],)).fetchone())
            store.start_newsroom_run(
                con, "empty-wake", "live", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"]],
            )
            prep_row = desk_prep._synthetic(
                row, run_id="empty-wake", reason="Outside the Bitcoin desk.",
                outcome="model", model_route="background",
            )
            prep_row["effective_route"] = "background"
            session = newsroom.NewsroomSession(
                run_id="empty-wake", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="r",
                prep_mode="enforce", research_mode="off", compact_enabled=True,
            )
            with patch.object(desk_prep, "prepare", return_value=desk_prep.PreparationResult(
                    [prep_row], (), {"mode": "enforce", "sonnet_inventory": 0})):
                outcome = session.conduct_v2()
            self.assertEqual(outcome.verdicts[0]["action"], "skip")
            self.assertEqual(session.successful_newsdesk_calls, 0)

    def test_prefetch_respects_its_budget_and_preserves_parent_research(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            rows = []
            for index in range(10):
                saved = store.upsert_new_items(con, [{
                    "source": "Example", "title": f"Bitcoin lead {index}",
                    "url": f"https://example.com/{index}", "published": "", "summary": "",
                }])[0]
                rows.append(dict(con.execute("SELECT * FROM items WHERE url_hash=?",
                                             (saved["url_hash"],)).fetchone()))
            session = newsroom.NewsroomSession(
                run_id="prefetch", inventory=rows, recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="r", prep_mode="enforce",
                research_mode="off", compact_enabled=True,
            )
            session.preparations = {row["url_hash"]: {"protection_reason": ""}
                                    for row in rows}

            def fetched(url, limit):
                return {"outcome": "ok", "text": "x" * limit, "final_url": url,
                        "canonical_url": url, "redirect_chain": [url]}

            with patch.object(newsroom.sources, "fetch_article", side_effect=fetched), \
                    patch.object(config, "RUN_NEWSROOM_MAX_FETCHES", 20), \
                    patch.object(config, "RUN_NEWSROOM_MAX_FETCH_TOTAL_CHARS", 200000):
                session.prefetch_prepared_receipts()
            self.assertLessEqual(session.prefetch_attempts, config.DESK_PREFETCH_MAX_URLS)
            self.assertLessEqual(session.prefetch_chars, config.DESK_PREFETCH_MAX_CHARS)
            self.assertGreaterEqual(20 - session.fetch_count,
                                    config.DESK_PREFETCH_RESERVE_FETCHES)
            self.assertGreaterEqual(200000 - session.fetch_chars,
                                    config.DESK_PREFETCH_RESERVE_CHARS)

    def test_compact_initial_packet_stays_bounded_with_long_recent_feed(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            rows = []
            for index in range(25):
                saved = store.upsert_new_items(con, [{
                    "source": "Example", "title": "Bitcoin current lead " + "T" * 280,
                    "url": f"https://example.com/current/{index}?context=" + "u" * 700,
                    "published": "", "summary": "S" * 600,
                }])[0]
                rows.append(dict(con.execute("SELECT * FROM items WHERE url_hash=?",
                                             (saved["url_hash"],)).fetchone()))
            session = newsroom.NewsroomSession(
                run_id="compact", inventory=rows, recent_clusters=[], theme_snapshot=[],
                handles={f"handle{index}": "identity " + "z" * 120 for index in range(50)},
                con=con, reservation="r", prep_mode="off", research_mode="off",
                compact_enabled=True,
            )
            recent = [{
                "effective_at": time.time() - index * 60,
                "story_key": f"event-{index}", "class": "secondary",
                "body": "A" * 4000, "receipt_url": f"https://example.com/r/{index}",
                "performance": {}, "performance_synced_at": None,
            } for index in range(40)]
            with patch.object(store, "recent_feed_posts", return_value=recent):
                packet = session._initial_packet()
            self.assertLessEqual(len(json.dumps(packet).encode()),
                                 config.COMPACT_DESK_INITIAL_BYTES)
            self.assertTrue(packet["recent_reader_feed_48h"]["index"])
            self.assertTrue(session.context_rows)

    def test_sonnet_can_delegate_bounded_haiku_reporting_with_code_owned_receipt(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            saved = store.upsert_new_items(con, [{
                "source": "Example", "title": "Bitcoin policy lead",
                "url": "https://example.com/policy", "published": "", "summary": "",
            }])[0]
            row = dict(con.execute("SELECT * FROM items WHERE url_hash=?",
                                   (saved["url_hash"],)).fetchone())
            session = newsroom.NewsroomSession(
                run_id="haiku-assignment", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="r", prep_mode="off",
                research_mode="on", compact_enabled=True,
            )
            usage = SimpleNamespace(input_tokens=100, output_tokens=20,
                                    cache_creation_input_tokens=0,
                                    cache_read_input_tokens=0, cache_creation=None)
            api = Mock()
            calls = 0

            def create(**kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    block = SimpleNamespace(
                        type="tool_use", id="fetch-tool", name="fetch_source",
                        input={"url": "https://example.com/report"},
                    )
                else:
                    fetch_id = next(iter(session.fetches))
                    block = SimpleNamespace(
                        type="tool_use", id="memo-tool", name="submit_research_memo",
                        input={
                            "what_happened": "A policy development happened.",
                            "when": "today", "source_findings": "The report supports it.",
                            "conflicts": "", "supportable_angle": "Report the development.",
                            "remaining_gap": "", "cited_fetch_ids": [fetch_id],
                        },
                    )
                return SimpleNamespace(content=[block], usage=usage)

            api.messages.create.side_effect = create
            fetched = {"outcome": "ok", "text": "A supported Bitcoin policy development.",
                       "final_url": "https://example.com/report",
                       "canonical_url": "https://example.com/report",
                       "redirect_chain": ["https://example.com/report"]}
            with patch.object(newsroom.anthropic, "Anthropic", return_value=api), \
                    patch.object(newsroom.sources, "fetch_article", return_value=fetched), \
                    patch.object(newsroom.brain, "consume_model_call"):
                result = session._haiku_research({
                    "objective": "Resolve the policy lead.",
                    "candidate_ids": [row["url_hash"]], "fetch_ids": [],
                })
            self.assertTrue(result["ok"])
            self.assertEqual(session.haiku_assignments, 1)
            self.assertEqual(session.haiku_rounds, 2)
            self.assertTrue(result["inspected_evidence"][0]["inspectable_evidence"])
            self.assertEqual(store.model_usage_calls(
                con, seat="research_assistant", since=0), 2)

    def test_sonnet_transport_retry_keeps_same_session_and_one_hour_cache(self):
        with temporary_store() as con, patch.object(newsroom.anthropic, "Anthropic"):
            session = newsroom.NewsroomSession(
                run_id="retry-cache", inventory=[], recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="r", prep_mode="off",
                research_mode="off", compact_enabled=True,
            )
            session.messages = [{"role": "user", "content": "same desk"}]
            usage = SimpleNamespace(input_tokens=100, output_tokens=20,
                                    cache_creation_input_tokens=0,
                                    cache_read_input_tokens=0, cache_creation=None)
            response = SimpleNamespace(content=[], usage=usage)
            api = Mock()
            api.messages.create.side_effect = [RuntimeError("transport"), response]
            session.client = api
            with patch.object(newsroom.brain, "consume_model_call"):
                returned = session._call(max_tokens=100, tools=[])
            self.assertIs(returned, response)
            self.assertEqual(api.messages.create.call_count, 2)
            first = api.messages.create.call_args_list[0].kwargs
            second = api.messages.create.call_args_list[1].kwargs
            self.assertEqual(first["messages"], second["messages"])
            self.assertEqual(first["system"][0]["cache_control"],
                             {"type": "ephemeral", "ttl": "1h"})
            self.assertTrue(session.newsdesk_retry_used)
            self.assertEqual(session.successful_newsdesk_calls, 1)
            self.assertEqual(session.rounds, 2)

    def test_v2_materialization_persists_editor_and_typefully_draft_lifecycle(self):
        with temporary_store() as con, ExitStack() as stack:
            saved = store.upsert_new_items(con, [{
                "source": "SEC", "title": "SEC updates Bitcoin policy",
                "url": "https://www.sec.gov/newsroom/press-releases/test",
                "published": "", "summary": "",
            }])[0]
            row = {**candidate(saved["url_hash"]), **saved}
            record = inspected(
                "fetch-sec", row["url"], "SEC",
                "The SEC announced a Bitcoin policy update.",
            )
            ev = verify.EvidenceCandidate(
                record.source, "primary_artifact", True, True, False,
                source_policy.artifact_fingerprint(record.final_url),
                record.content_fingerprint,
            )
            resolution = verify.ResolutionResult(
                row["url_hash"], "sec-bitcoin-policy", row["source"], record.source,
                record.source, record.text, "selected", True, "primary_artifact", True,
                False, record.final_url, ev.primary_artifact_fingerprint,
                record.content_fingerprint, None, "v2 test", (ev,),
                resolver_path="run_newsroom",
            )
            draft = {
                "post": "The SEC announced a Bitcoin policy update.",
                "reader_value": "Policy changed.", "needs_second_source": False,
                "selected_fetch_id": record.fetch_id,
                "evidence_fetch_ids": [record.fetch_id], "_source_text": record.text,
            }
            verdict = {
                **row, "action": "draft", "story_key": "sec-bitcoin-policy",
                "class": "secondary", "reason": "useful",
            }
            attempt = {
                "story_id": "sec", "canonical_key": "sec-bitcoin-policy",
                "identity_valid": True, "members": [row["url_hash"]],
                "headlines": [row["title"]], "submitted_story_key": "sec-policy-update",
                "existing_cluster_key": "", "proposed_post": draft["post"],
                "failure": "", "objective": "", "evidence": [{
                    "inspected_at": record.inspected_at, "requested_url": record.requested_url,
                    "final_url": record.final_url, "canonical_url": record.canonical_url,
                    "source_label": record.source.display_name,
                    "content_fingerprint": record.content_fingerprint, "text": record.text,
                }],
            }
            session = Mock()
            session.conduct.return_value = newsroom.NewsroomOutcome(
                "run:v2-success", {"stories": [{"story_id": "sec"}]}, "a" * 64,
                [verdict], {row["url_hash"]: resolution}, {row["url_hash"]: draft},
                {record.fetch_id: record}, {"rounds": 1}, session,
                {row["url_hash"]: "sec"}, [attempt],
            )
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": True, "decisions": {"sec": {
                    "verdict": "publish", "post": draft["post"], "reason": "clean",
                }},
            }))
            publish = stack.enter_context(patch.object(
                publisher, "publish", return_value=("DRAFT", "typefully-1")
            ))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            result = main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:v2-success",
                inventory=[row], pending=[row],
                result={"held": 0, "skipped": 0, "posted": 0, "drafted": 0,
                        "uncertain": 0, "failed": 0, "taped": 0},
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertEqual(result["drafted"], 1)
            publish.assert_called_once()
            memory = store.newsroom_story_memories(con)[0]
            self.assertEqual(memory["state"], "delivered")
            self.assertEqual(memory["editor"]["verdict"], "publish")
            self.assertEqual(memory["delivery"]["mode"], "DRAFT")
            self.assertFalse(memory["delivery"]["reader_covered"])
            self.assertEqual(store.canonical_story_key(con, "sec-policy-update"),
                             "sec-bitcoin-policy")

            # A later hard-rail defer becomes the workbench's explicit next objective.
            con.execute("DELETE FROM posts WHERE story_key='sec-bitcoin-policy'")
            con.execute(
                "UPDATE items SET status='new',defer_until=0 WHERE url_hash=?",
                (row["url_hash"],),
            )
            con.commit()
            publish.reset_mock()
            with patch.object(lint, "hard_rails_v2", return_value=[
                "verbatim quote not in inspected evidence: 'unsupported quote'"
            ]):
                held = main._run_editorial_v2(
                    con, lease_owner="test-owner", pipeline_run_id="run:v2-hard-rail",
                    inventory=[row], pending=[row],
                    result={"held": 0, "skipped": 0, "posted": 0, "drafted": 0,
                            "uncertain": 0, "failed": 0, "taped": 0},
                    theme_snapshot=[], overrides={}, run_started=time.time(),
                )
            self.assertEqual(held["held"], 1)
            publish.assert_not_called()
            memory = store.newsroom_story_memories(con)[0]
            self.assertEqual(memory["state"], "research_pending")
            self.assertEqual(memory["attempts"][-1]["failure"],
                             "defer:editor_hard_rail")
            self.assertIn("unsupported quote", memory["attempts"][-1]["objective"])

    def test_elevated_single_source_reaches_editor_with_warning(self):
        with temporary_store() as con:
            row = candidate()
            session = newsroom.NewsroomSession(
                run_id="continuity:first", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected(
                "fetch-tftc", "https://tftc.io/tether-lawsuit", "TFTC",
                "A lawsuit alleges Tether froze $42.4 million in USDT.",
            )
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "continuity:first", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"]],
            )
            post = "A lawsuit alleges Tether froze $42.4 million in USDT."
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "tether",
                               "disposition": "publish", "reason": "material allegation"}],
                "stories": [{"story_id": "tether", "story_key": "tether-freeze-lawsuit",
                             "existing_cluster_key": None,
                             "member_candidate_ids": [row["url_hash"]], "post": post,
                             "selected_fetch_id": record.fetch_id,
                             "evidence_fetch_ids": [record.fetch_id],
                             "elevated_claim": True, "reader_value": "Legal control risk.",
                             "reason": "material"}], "run_note": "recommended for delivery",
            })
            self.assertEqual(outcome.verdicts[0]["action"], "draft")
            self.assertEqual(outcome.verdicts[0]["story_key"], "tether-freeze-lawsuit")
            self.assertEqual(outcome.story_attempts[0]["proposed_post"], post)
            self.assertEqual(len(outcome.story_attempts[0]["evidence"]), 1)
            self.assertTrue(any(
                value.startswith("elevated_claim_single_source")
                for value in outcome.drafts[row["url_hash"]]["editorial_warnings"]
            ))

    def test_cached_evidence_rehydrates_and_one_new_independent_source_clears_gate(self):
        with temporary_store() as con:
            first_text = "A lawsuit alleges Tether froze $42.4 million in USDT."
            first = inspected(
                "fetch-old", "https://tftc.io/tether-lawsuit", "TFTC", first_text,
            )
            store.save_newsroom_story_attempt(con, "tether-freeze-lawsuit", "research_pending", {
                "story_id": "prior", "members": ["prior-hash"],
                "headlines": ["Tether freeze lawsuit"],
                "submitted_story_key": "tether-usdt-freeze-lawsuit",
                "proposed_post": first_text,
                "failure": "defer:elevated_claim_needs_primary_or_two_reports",
                "objective": "Find one independent second report.",
                "evidence": [{"inspected_at": first.inspected_at,
                              "requested_url": first.requested_url,
                              "final_url": first.final_url,
                              "canonical_url": first.canonical_url,
                              "source_label": first.source.display_name,
                              "content_fingerprint": first.content_fingerprint,
                              "text": first.text}],
            })
            row = candidate("new-url-hash")
            session = newsroom.NewsroomSession(
                run_id="continuity:second", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            memory_id = next(value for value in session.fetches if value.startswith("memory_"))
            second = inspected(
                "fetch-block", "https://www.theblock.co/post/tether-lawsuit", "The Block",
                "A court complaint says Tether froze $42.4 million tied to the plaintiff.",
            )
            session.fetches[second.fetch_id] = second
            store.start_newsroom_run(
                con, "continuity:second", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"]],
            )
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "tether",
                               "disposition": "publish", "reason": "now corroborated"}],
                "stories": [{"story_id": "tether", "story_key": "tether-42m-lawsuit",
                             "existing_cluster_key": "tether-freeze-lawsuit",
                             "member_candidate_ids": [row["url_hash"]],
                             "post": "A lawsuit alleges Tether froze $42.4 million in USDT.",
                             "selected_fetch_id": second.fetch_id,
                             "evidence_fetch_ids": [memory_id, second.fetch_id],
                             "elevated_claim": True, "reader_value": "Legal control risk.",
                             "reason": "corroborated"}], "run_note": "recommended for delivery",
            })
            self.assertEqual(outcome.verdicts[0]["action"], "draft")
            self.assertEqual(outcome.verdicts[0]["story_key"], "tether-freeze-lawsuit")
            self.assertNotEqual(memory_id, "fetch-old")

    def test_conflicting_member_families_flow_as_isolated_forced_draft(self):
        with temporary_store() as con:
            rows = [candidate("one"), candidate("two")]
            rows[0]["story_key"], rows[1]["story_key"] = "event-one", "event-two"
            session = newsroom.NewsroomSession(
                run_id="identity:conflict", inventory=rows, recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected("fetch-good", rows[0]["url"], "SEC", "Bitcoin policy changed.")
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "identity:conflict", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"] for row in rows],
            )
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "merged",
                               "disposition": "publish", "reason": "same"} for row in rows],
                "stories": [{"story_id": "merged", "story_key": "new-merge",
                             "existing_cluster_key": None,
                             "member_candidate_ids": ["one", "two"], "post": "Bitcoin changed.",
                             "selected_fetch_id": record.fetch_id,
                             "evidence_fetch_ids": [record.fetch_id],
                             "elevated_claim": False, "reader_value": "change", "reason": ""}],
                "run_note": "recommended for delivery",
            })
            self.assertTrue(all(row["action"] == "draft" for row in outcome.verdicts))
            self.assertTrue(outcome.drafts["one"]["preserve_member_story_keys"])
            self.assertEqual(outcome.drafts["one"]["force_draft_reason"], "identity_conflict")
            self.assertFalse(outcome.story_attempts[0]["allow_alias"])
            self.assertNotIn(outcome.verdicts[0]["story_key"], {"event-one", "event-two"})
            self.assertEqual(store.canonical_story_key(con, "new-merge"), "new-merge")

    def test_expired_or_tampered_cached_evidence_is_not_citable(self):
        with temporary_store() as con:
            now = time.time()
            for key, inspected_at, fingerprint in (
                ("expired-event", now - newsroom.MEMORY_EVIDENCE_MAX_AGE_SECONDS - 1, ""),
                ("tampered-event", now, "not-the-text-fingerprint"),
            ):
                text = f"Bitcoin evidence for {key}."
                store.save_newsroom_story_attempt(con, key, "research_pending", {
                    "story_id": key, "members": [key], "headlines": [key],
                    "proposed_post": text, "failure": "defer:test", "objective": "test",
                    "evidence": [{
                        "inspected_at": inspected_at,
                        "final_url": f"https://example.com/{key}",
                        "content_fingerprint": (fingerprint or
                                                source_policy.content_fingerprint(text)),
                        "text": text,
                    }],
                }, now=now)
            session = newsroom.NewsroomSession(
                run_id="continuity:invalid-cache", inventory=[candidate("fresh")],
                recent_clusters=[], theme_snapshot=[], handles={}, con=con,
                reservation="token",
            )
            self.assertEqual(session.fetches, {})
            packet = session._initial_packet()
            self.assertEqual(sum(len(row["reusable_evidence"])
                                 for row in packet["continuity_board"]), 0)

    def test_editor_feedback_is_context_not_coverage_authority(self):
        with temporary_store() as con:
            store.save_newsroom_story_attempt(con, "facility-shutdown", "editor_feedback", {
                "story_id": "facility", "members": ["older-item"],
                "headlines": ["Company shuts Michigan mining facility"],
                "proposed_post": "The company shut its Michigan mining facility.",
                "evidence": [],
            })
            store.save_newsroom_editor_feedback(
                con, "facility-shutdown", verdict="drop",
                reason="Older general intent appeared to conflict.", post=None,
            )
            session = newsroom.NewsroomSession(
                run_id="continuity:editor", inventory=[candidate("new-related-item")],
                recent_clusters=[], theme_snapshot=[], handles={}, con=con,
                reservation="token",
            )
            packet = session._initial_packet()
            card = packet["continuity_board"][0]
            self.assertEqual(card["editor_feedback_untrusted_context"]["verdict"], "drop")
            clusters = store.story_cluster_context(con)
            cluster = next(row for row in clusters
                           if row["canonical_key"] == "facility-shutdown")
            self.assertFalse(cluster["reader_covered"])
            self.assertFalse(cluster["draft_open"])

    def test_editor_prompt_distinguishes_specific_current_fact_from_old_general_intent(self):
        self.assertIn("facility-specific action", editor.BATCH_EDITOR_PROMPT)
        self.assertIn("older statement of general company", editor.BATCH_EDITOR_PROMPT)

    def test_bpi_x_research_is_labeled_first_party_without_becoming_official(self):
        ref = source_policy.classify("https://x.com/bitcoinpolicy/status/1")
        record = newsroom.FetchRecord(
            fetch_id="fetch-bpi", requested_url=ref.url, final_url=ref.url,
            canonical_url=ref.url, redirect_chain=(), source=ref, byline="BPI",
            text="Bitcoin Policy Institute published new research.",
            content_fingerprint="fingerprint", outcome="ok",
        )
        self.assertEqual(record.evidence_capability, "known_first_party_research")
        self.assertFalse(ref.official)
        self.assertIn("without separate confirmation", editor.BATCH_EDITOR_PROMPT)

    def test_persisted_cadence_survives_calls_and_can_be_forced(self):
        with temporary_store() as con, patch.object(config, "DESK_INTERVAL_SECONDS", 900):
            self.assertTrue(store.editorial_run_due(con, now=1000))
            self.assertFalse(store.editorial_run_due(con, now=1100))
            self.assertTrue(store.editorial_run_due(con, now=1100, force=True))
            self.assertAlmostEqual(float(store.kv_get(con, "editorial:next_run_at")), 2000)

    def test_small_numeric_presentation_difference_is_not_a_hard_veto(self):
        errors = lint.check_v2(
            "Japan's 10-year yield eased to roughly 3% while the yen traded near 160.",
            {"_source_text": "The 10-year yield was 2.99%. The yen was 159.95 per dollar."},
            {},
        )
        self.assertEqual(errors, [])

    def test_short_separate_quotes_are_checked_independently(self):
        errors = lint.check_v2(
            'Inflation "stalled" in 2025. The Fed can "take a bit more time."',
            {"_source_text": 'Inflation progress stalled in 2025. The Fed can take a bit more time.'},
            {},
        )
        self.assertEqual(errors, [])

    def test_one_bad_story_does_not_sink_valid_story_and_omissions_defer(self):
        with temporary_store() as con:
            rows = [candidate("candidate-1"), candidate("candidate-2"), candidate("candidate-3")]
            session = newsroom.NewsroomSession(
                run_id="cycle:v2", inventory=rows, recent_clusters=[], theme_snapshot=[],
                handles={}, con=con, reservation="token",
            )
            text = "The SEC announced a Bitcoin policy update."
            ref = source_policy.classify(rows[0]["url"], rows[0]["source"])
            record = newsroom.FetchRecord(
                fetch_id="fetch-good", requested_url=rows[0]["url"],
                final_url=rows[0]["url"], canonical_url=rows[0]["url"],
                redirect_chain=(rows[0]["url"],), source=ref, byline="", text=text,
                content_fingerprint=source_policy.content_fingerprint(text), outcome="ok",
            )
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "cycle:v2", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"] for row in rows],
            )
            dossier = {
                "decisions": [
                    {"candidate_id": "candidate-1", "story_id": "good",
                     "disposition": "publish", "reason": "useful"},
                    {"candidate_id": "candidate-2", "story_id": "bad",
                     "disposition": "publish", "reason": "useful"},
                ],
                "stories": [
                    {"story_id": "good", "story_key": "sec-bitcoin-policy",
                     "member_candidate_ids": ["candidate-1"],
                     "post": "The SEC announced a Bitcoin policy update.",
                     "selected_fetch_id": "fetch-good",
                     "evidence_fetch_ids": ["fetch-good"], "elevated_claim": False,
                     "reader_value": "Policy changed.", "reason": "useful"},
                    {"story_id": "bad", "story_key": "invented",
                     "member_candidate_ids": ["candidate-2"], "post": "Unsupported.",
                     "selected_fetch_id": "fetch-invented",
                     "evidence_fetch_ids": ["fetch-invented"], "elevated_claim": False,
                     "reader_value": "", "reason": ""},
                ], "run_note": "test",
            }
            outcome = session._validate_and_convert_v2(dossier)
            by_hash = {row["url_hash"]: row for row in outcome.verdicts}
            self.assertEqual(by_hash["candidate-1"]["action"], "draft")
            self.assertEqual(by_hash["candidate-2"]["action"], "hold")
            self.assertIn("uninspected", by_hash["candidate-2"]["reason"])
            self.assertEqual(by_hash["candidate-3"]["reason"], "defer:model_output_missing")

    def test_later_empty_attempt_keeps_prior_evidence_pool(self):
        with temporary_store() as con:
            text = "Pocket Bitcoin says a support-system incident exposed customer data."
            fingerprint = source_policy.content_fingerprint(text)
            evidence = {
                "inspected_at": time.time(),
                "requested_url": "https://pocketbitcoin.com/security-incident",
                "final_url": "https://pocketbitcoin.com/security-incident",
                "canonical_url": "https://pocketbitcoin.com/security-incident",
                "source_label": "Pocket Bitcoin",
                "content_fingerprint": fingerprint,
                "text": text,
            }
            store.save_newsroom_story_attempt(con, "pocket-bitcoin-incident", "research_pending", {
                "story_id": "pocket", "members": ["old"], "headlines": ["Incident"],
                "proposed_post": text, "failure": "defer:first", "evidence": [evidence],
            })
            store.save_newsroom_story_attempt(con, "pocket-bitcoin-incident", "research_pending", {
                "story_id": "pocket", "members": ["new"], "headlines": ["Retry"],
                "proposed_post": "", "failure": "defer:search_unavailable", "evidence": [],
            })
            memory = store.newsroom_story_memories(con)[0]
            self.assertEqual(memory["attempts"][-1]["evidence"], [])
            self.assertEqual(len(memory["evidence_pool"]), 1)
            self.assertEqual(memory["evidence_pool"][0]["text"], text)
            session = newsroom.NewsroomSession(
                run_id="memory:reuse", inventory=[candidate("new")], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            self.assertEqual(len(session.fetches), 1)
            self.assertEqual(next(iter(session.fetches.values())).text, text)

    def test_unknown_safe_page_reaches_editor_as_explicit_warning(self):
        with temporary_store() as con:
            row = candidate("pocket")
            session = newsroom.NewsroomSession(
                run_id="unknown:source", inventory=[row], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected(
                "fetch-pocket", "https://pocketbitcoin.com/security-incident",
                "Pocket Bitcoin", "Pocket Bitcoin says customer data was exposed.",
            )
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "unknown:source", "draft", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"]],
            )
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "pocket",
                               "disposition": "publish", "reason": "material"}],
                "stories": [{"story_id": "pocket", "story_key": "pocket-incident",
                             "existing_cluster_key": None,
                             "member_candidate_ids": [row["url_hash"]],
                             "post": "Pocket Bitcoin says customer data was exposed.",
                             "selected_fetch_id": record.fetch_id,
                             "evidence_fetch_ids": [record.fetch_id],
                             "elevated_claim": True, "reader_value": "Customer security.",
                             "reason": "material"}], "run_note": "review",
            })
            self.assertEqual(outcome.verdicts[0]["action"], "draft")
            warnings = outcome.drafts[row["url_hash"]]["editorial_warnings"]
            self.assertTrue(any("unknown_domain_material" in value for value in warnings))
            self.assertTrue(any(value.startswith("elevated_claim_single_source")
                                for value in warnings))

    def test_conflict_collision_preserves_member_keys_and_forces_typefully_draft(self):
        with temporary_store() as con, ExitStack() as stack:
            saved = store.upsert_new_items(con, [
                {"source": "SEC", "title": "One", "url": "https://sec.gov/news/one",
                 "published": "", "summary": ""},
                {"source": "SEC", "title": "Two", "url": "https://sec.gov/news/two",
                 "published": "", "summary": ""},
            ])
            rows = [{**candidate(row["url_hash"]), **row} for row in saved]
            rows[0]["story_key"], rows[1]["story_key"] = "family-one", "family-two"
            con.execute("UPDATE items SET story_key='family-one' WHERE url_hash=?",
                        (rows[0]["url_hash"],))
            con.execute("UPDATE items SET story_key='family-two' WHERE url_hash=?",
                        (rows[1]["url_hash"],))
            store.register_story_alias(con, "submitted-conflict", "family-one", "test")
            session = newsroom.NewsroomSession(
                run_id="conflict:delivery", inventory=rows, recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected(
                "fetch-conflict", "https://sec.gov/news/one", "SEC",
                "The SEC announced a Bitcoin policy change.",
            )
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(
                con, "conflict:delivery", "live", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, [row["url_hash"] for row in rows],
            )
            outcome = session._validate_and_convert_v2({
                "decisions": [{"candidate_id": row["url_hash"], "story_id": "conflict",
                               "disposition": "publish", "reason": "review"} for row in rows],
                "stories": [{"story_id": "conflict", "story_key": "submitted-conflict",
                             "existing_cluster_key": None,
                             "member_candidate_ids": [row["url_hash"] for row in rows],
                             "post": "The SEC announced a Bitcoin policy change.",
                             "selected_fetch_id": record.fetch_id,
                             "evidence_fetch_ids": [record.fetch_id],
                             "elevated_claim": False, "reader_value": "Policy changed.",
                             "reason": "review"}], "run_note": "review",
            })
            review_key = outcome.verdicts[0]["story_key"]
            self.assertNotEqual(review_key, "submitted-conflict")
            self.assertEqual(store.canonical_story_key(con, review_key), review_key)
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            session.conduct = Mock(return_value=outcome)
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": True, "decisions": {"conflict": {
                    "verdict": "publish", "post": "The SEC announced a Bitcoin policy change.",
                    "reason": "supported",
                }},
            }))
            publish = stack.enter_context(patch.object(
                publisher, "publish", return_value=("DRAFT", "draft-conflict")
            ))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="conflict:delivery",
                inventory=rows, pending=rows, result=self.result_counts(),
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertTrue(publish.call_args.kwargs["force_draft"])
            stored_keys = [row["story_key"] for row in con.execute(
                "SELECT story_key FROM items ORDER BY url"
            ).fetchall()]
            self.assertEqual(stored_keys, ["family-one", "family-two"])
            self.assertEqual(con.execute("SELECT story_key FROM posts").fetchone()["story_key"],
                             review_key)

    def test_search_429_opens_one_run_circuit(self):
        with temporary_store() as con:
            session = newsroom.NewsroomSession(
                run_id="search:circuit", inventory=[candidate()], recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            block = Mock()
            block.name, block.input, block.id = "search_web", {"query": "Bitcoin"}, "tool-1"
            with patch.object(search, "google", side_effect=search.SearchError(
                    "serpapi HTTP 429", kind="rate_limited")) as google:
                first = session._dispatch(block)
                block.id = "tool-2"
                second = session._dispatch(block)
            self.assertEqual(google.call_count, 1)
            self.assertIn("search_unavailable_for_run", first["content"])
            self.assertIn("search_unavailable_for_run", second["content"])
            self.assertTrue(session.counters()["search_degraded"])

    def test_v2_dossier_overflow_fails_the_run_instead_of_slicing(self):
        cases = {
            "decisions": {
                "decisions": [{"candidate_id": "candidate-1"} for _ in range(26)],
                "stories": [],
            },
            "stories": {
                "decisions": [],
                "stories": [{"story_id": f"story-{i}"} for i in range(26)],
            },
            "members": {
                "decisions": [],
                "stories": [{"story_id": "story", "member_candidate_ids": [
                    f"candidate-{i}" for i in range(26)
                ]}],
            },
            "evidence": {
                "decisions": [],
                "stories": [{"story_id": "story", "evidence_fetch_ids": [
                    f"fetch-{i}" for i in range(9)
                ]}],
            },
        }
        for name, dossier in cases.items():
            with self.subTest(name=name), temporary_store() as con:
                session = newsroom.NewsroomSession(
                    run_id=f"bounds:{name}", inventory=[candidate()], recent_clusters=[],
                    theme_snapshot=[], handles={}, con=con, reservation="token",
                )
                with self.assertRaises(newsroom.NewsroomError) as caught:
                    session._validate_and_convert_v2({**dossier, "run_note": "overflow"})
                self.assertEqual(caught.exception.kind, "dossier_bounds")

    def test_editor_outage_returns_draft_fallback_and_records_usage(self):
        with temporary_store() as con, patch("nbn.brain._create", side_effect=RuntimeError("offline")):
            result = editor.review_newsroom_batch([
                {"story_id": "s1", "post": "Bitcoin policy changed.",
                 "selected_receipt": {}, "inspected_evidence": []}
            ], con, run_id="cycle:editor")
            self.assertFalse(result["ok"])
            usage = store.model_usage_summary(con, time.time() - 60)
            self.assertEqual(usage["calls"], 1)

    def test_partial_editor_response_gets_one_omitted_only_recovery(self):
        usage = SimpleNamespace(input_tokens=100, output_tokens=20,
                                cache_creation_input_tokens=0,
                                cache_read_input_tokens=0, cache_creation=None)

        def answer(payload):
            return SimpleNamespace(
                content=[SimpleNamespace(type="text", text=json.dumps(payload))],
                usage=usage, stop_reason="end_turn",
            )

        first = answer({"decisions": [{"story_id": "s1", "verdict": "publish",
                                       "post": "First.", "reason": "good"}]})
        second = answer({"decisions": [{"story_id": "s2", "verdict": "draft",
                                        "post": "Second.", "reason": "review"}]})
        candidates = [{
            "story_id": key, "post": text, "selected_receipt": {},
            "inspected_evidence": [], "output_continuity": {"canonical_key": key},
        } for key, text in (("s1", "First."), ("s2", "Second."))]
        with temporary_store() as con, patch("nbn.brain._create",
                                             side_effect=[first, second]) as create:
            result = editor.review_newsroom_batch(candidates, con, run_id="editor:partial")
            self.assertEqual(set(result["decisions"]), {"s1", "s2"})
            self.assertEqual(result["recovery"]["recovered"], 1)
            self.assertEqual(create.call_count, 2)
            recovery_payload = json.loads(create.call_args_list[1].args[2])
            self.assertEqual([row["story_id"] for row in recovery_payload["candidates"]], ["s2"])
            self.assertEqual(store.model_usage_calls(
                con, seat="editor_recovery", since=time.time() - 60
            ), 1)

    def test_editor_outage_stages_mechanically_valid_copy_only(self):
        with temporary_store() as con, ExitStack() as stack:
            row, _record, _draft, session = materialization_fixture(
                con, "run:editor-outage-valid"
            )
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": False, "error": "offline", "decisions": {}, "payload_deferred": [],
            }))
            publish = stack.enter_context(patch.object(
                publisher, "publish", return_value=("DRAFT", "editor-outage-draft")
            ))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            result = main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:editor-outage-valid",
                inventory=[row], pending=[row], result=self.result_counts(),
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertEqual(result["drafted"], 1)
            self.assertTrue(publish.call_args.kwargs["force_draft"])

        with temporary_store() as con, ExitStack() as stack:
            row, _record, _draft, session = materialization_fixture(
                con, "run:editor-outage-invalid",
                post="The SEC announced a Bitcoin policy update. https://example.com",
            )
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": False, "error": "offline", "decisions": {}, "payload_deferred": [],
            }))
            publish = stack.enter_context(patch.object(publisher, "publish"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            result = main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:editor-outage-invalid",
                inventory=[row], pending=[row], result=self.result_counts(),
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertEqual(result["held"], 1)
            publish.assert_not_called()

    def test_quote_rail_runs_before_and_after_editor(self):
        with temporary_store() as con, ExitStack() as stack:
            row, _record, _draft, session = materialization_fixture(
                con, "run:quote-repair", post='The SEC called the change “historic.”',
            )
            captured = {}

            def repair(candidates, *_args, **_kwargs):
                captured.update(candidates[0])
                return {"ok": True, "payload_deferred": [], "decisions": {"sec": {
                    "verdict": "revise", "post": "The SEC announced a Bitcoin policy update.",
                    "reason": "Removed unsupported quote.",
                }}}

            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", side_effect=repair))
            publish = stack.enter_context(patch.object(
                publisher, "publish", return_value=("DRAFT", "quote-repaired")
            ))
            stack.enter_context(patch.object(publisher, "backend_name", return_value="typefully"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:quote-repair",
                inventory=[row], pending=[row], result=self.result_counts(),
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertTrue(any("verbatim quote" in value
                                for value in captured["mechanical_rails_to_fix"]))
            publish.assert_called_once()

        with temporary_store() as con, ExitStack() as stack:
            row, _record, _draft, session = materialization_fixture(
                con, "run:quote-introduced"
            )
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(editor, "review_newsroom_batch", return_value={
                "ok": True, "payload_deferred": [], "decisions": {"sec": {
                    "verdict": "revise", "post": 'The SEC called the change “historic.”',
                    "reason": "Bad revision.",
                }},
            }))
            publish = stack.enter_context(patch.object(publisher, "publish"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            result = main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:quote-introduced",
                inventory=[row], pending=[row], result=self.result_counts(),
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            self.assertEqual(result["held"], 1)
            publish.assert_not_called()

    def test_commit_rows_cover_invalid_and_shadow_story_lifecycle(self):
        with temporary_store() as con:
            rows = [candidate("valid"), candidate("invalid")]
            session = newsroom.NewsroomSession(
                run_id="commit:invalid", inventory=rows, recent_clusters=[],
                theme_snapshot=[], handles={}, con=con, reservation="token",
            )
            record = inspected("fetch-valid", rows[0]["url"], "SEC", "Bitcoin policy changed.")
            session.fetches[record.fetch_id] = record
            store.start_newsroom_run(con, "commit:invalid", "live", config.ANTHROPIC_MODEL,
                                     newsroom.PROMPT_VERSION, ["valid", "invalid"])
            outcome = session._validate_and_convert_v2({
                "decisions": [
                    {"candidate_id": "valid", "story_id": "good", "disposition": "publish"},
                    {"candidate_id": "invalid", "story_id": "bad", "disposition": "publish"},
                ],
                "stories": [
                    {"story_id": "good", "story_key": "good", "member_candidate_ids": ["valid"],
                     "post": "Bitcoin policy changed.", "selected_fetch_id": "fetch-valid",
                     "evidence_fetch_ids": ["fetch-valid"]},
                    {"story_id": "bad", "story_key": "bad", "member_candidate_ids": ["invalid"],
                     "post": "No receipt.", "selected_fetch_id": "missing",
                     "evidence_fetch_ids": ["missing"]},
                ],
            })
            commits = {row["story_id"]: row for row in outcome.story_commits}
            self.assertEqual(commits["good"]["state"], "pending")
            self.assertEqual(commits["bad"]["state"], "held")
            self.assertIn("uninspected", commits["bad"]["details"]["reason"])

        with temporary_store() as con, ExitStack() as stack:
            row, _record, _draft, session = materialization_fixture(con, "run:shadow-observed")
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=session))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "shadow"))
            self.assertTrue(store.acquire_cycle_lease(con, "test-owner"))
            main._run_editorial_v2(
                con, lease_owner="test-owner", pipeline_run_id="run:shadow-observed",
                inventory=[row], pending=[row], result=self.result_counts(),
                theme_snapshot=[], overrides={}, run_started=time.time(),
            )
            commit = con.execute(
                "SELECT state,details_json FROM newsroom_story_commits WHERE run_id=?",
                ("run:shadow-observed",),
            ).fetchone()
            self.assertEqual(commit["state"], "observed")
            self.assertEqual(json.loads(commit["details_json"])["shadow"],
                             "shadow_observation_only")

    def test_desk_escapes_and_exposes_latest_commit_and_run_issue(self):
        with temporary_store() as con:
            store.start_newsroom_run(
                con, "run:<unsafe>", "live", config.ANTHROPIC_MODEL,
                newsroom.PROMPT_VERSION, ["candidate"],
            )
            store.init_newsroom_story_commits(con, "run:<unsafe>", [{
                "story_id": "story:<unsafe>", "state": "held",
                "details": {"reason": "defer:<unsafe>", "warnings": ["warn"]},
            }], "c" * 64)
            store.set_newsroom_state(
                con, "run:<unsafe>", "deferred", error_kind="Bad<Request>",
                error_message="schema <failed>", counters={},
            )
            html = report.render(con)
            self.assertIn("Latest newsroom lifecycle", html)
            self.assertIn("Run issue", html)
            self.assertIn("run:&lt;unsafe&gt;", html)
            self.assertIn("schema &lt;failed&gt;", html)
            self.assertNotIn("schema <failed>", html)

    def test_editor_payload_bound_preserves_selected_receipts_and_defers_whole_cards(self):
        body = "Bitcoin evidence. " * 470
        candidates = []
        for index in range(25):
            selected_id = f"selected-{index}"
            evidence = [{
                "fetch_id": selected_id, "content_fingerprint": f"fingerprint-{index}-selected",
                "url": f"https://example.com/{selected_id}", "text": body,
            }]
            evidence.extend({
                "fetch_id": f"other-{index}-{j}",
                "content_fingerprint": f"fingerprint-{index}-{j}",
                "url": f"https://example.com/other-{index}-{j}", "text": body,
            } for j in range(7))
            candidates.append({
                "story_id": f"story-{index}", "post": "Bitcoin evidence was published.",
                "selected_receipt": {"fetch_id": selected_id},
                "inspected_evidence": evidence,
                "mechanical_rails_to_fix": [],
                "editorial_warnings": [f"warning-{index}"],
            })
        payload, deferred = editor._batch_editor_payload(candidates, [])
        self.assertLessEqual(
            len(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()),
            editor.EDITOR_PAYLOAD_MAX_BYTES,
        )
        self.assertTrue(deferred)
        catalog = {row["evidence_ref"]: row for row in payload["evidence_catalog"]}
        for card in payload["candidates"]:
            self.assertIn(card["selected_evidence_ref"], catalog)
            self.assertGreater(len(catalog[card["selected_evidence_ref"]]["text"]), 2000)
            self.assertEqual(card["editorial_warnings"],
                             [f"warning-{card['story_id'].split('-')[-1]}"])
        self.assertTrue(set(deferred).isdisjoint(
            {card["story_id"] for card in payload["candidates"]}
        ))

    def test_evidence_pool_deduplicates_and_total_row_stays_bounded(self):
        with temporary_store() as con:
            shared = "A" * 8192
            fingerprint = source_policy.content_fingerprint(shared)
            for index in range(14):
                evidence = [{
                    "inspected_at": time.time() + index,
                    "requested_url": f"https://example.com/{index}/" + "u" * 1200,
                    "final_url": f"https://example.com/{index}/" + "f" * 1200,
                    "canonical_url": f"https://example.com/{index}/" + "c" * 1200,
                    "source_label": "Example", "content_fingerprint": (
                        fingerprint if index < 2 else f"fingerprint-{index}"
                    ), "text": shared,
                }]
                store.save_newsroom_story_attempt(con, "bounded-story", "research_pending", {
                    "story_id": "bounded", "members": [str(index)],
                    "headlines": ["H" * 300] * 3, "proposed_post": "P" * 8192,
                    "failure": "defer:test", "objective": "O" * 500,
                    "evidence": evidence,
                })
            row = con.execute(
                "SELECT * FROM newsroom_story_memory WHERE canonical_key='bounded-story'"
            ).fetchone()
            total = sum(len(str(row[field] or "").encode()) for field in (
                "canonical_key", "state", "attempts_json", "evidence_pool_json",
                "editor_json", "delivery_json",
            ))
            self.assertLessEqual(total, store._STORY_MEMORY_ROW_MAX_BYTES)
            pool = json.loads(row["evidence_pool_json"])
            self.assertLessEqual(len(pool), 8)
            self.assertEqual(len({card["content_fingerprint"] for card in pool}), len(pool))
            json.loads(row["attempts_json"])

    def test_newsdesk_outage_never_calls_legacy_triage(self):
        raw = candidate()
        raw.pop("url_hash")
        failed = Mock()
        failed.conduct.side_effect = RuntimeError("offline")
        failed.counters.return_value = {"rounds": 1}
        with temporary_store() as con, ExitStack() as stack:
            stack.enter_context(patch.object(sources, "fetch_feeds", return_value=[raw]))
            stack.enter_context(patch.object(sources, "fetch_edgar", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_perception", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_x", return_value=[]))
            stack.enter_context(patch("nbn.node_discovery.ingest", return_value={"inserted": 0}))
            stack.enter_context(patch.object(newsroom, "start_session", return_value=failed))
            stack.enter_context(patch.object(brain, "reserve_model_calls", return_value="token"))
            legacy = stack.enter_context(patch.object(brain, "triage"))
            stack.enter_context(patch.object(config, "RUN_NEWSROOM_MODE", "live"))
            stack.enter_context(patch.object(config, "EDITORIAL_ENGINE", "v2"))
            result = main.cycle(con)
            saved = con.execute("SELECT status,note FROM items").fetchone()
        legacy.assert_not_called()
        self.assertEqual(result["newsroom"]["status"], "deferred")
        self.assertEqual(saved["status"], "new")
        self.assertIn("newsdesk_unavailable", saved["note"])


if __name__ == "__main__":
    unittest.main()
