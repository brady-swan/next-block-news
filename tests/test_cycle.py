import json
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

from nbn import brain, config, editor, main, publisher, source_policy, sources, store, verify
from tests.support import item, temporary_store


def make_resolution(row, text, source_name=None, tier=None, role=None):
    primary = row.get("class") == "primary" and source_name is None
    name = source_name or row.get("source", "Example")
    slug = name.lower().replace(" ", "-")
    selected_tier = tier or ("p0" if primary else "t2")
    selected_role = role or ("official" if primary else "reporting")
    selected_url = ("https://glassnode.com/report" if name == "Glassnode" else row["url"])
    ref = source_policy.SourceRef(
        slug, name, selected_tier, "authority" if primary else "reporting", slug, slug,
        selected_role, selected_url, selected_url.split("/")[2], "", "test")
    originality = "primary_artifact" if primary else (
        "original_research" if selected_role == "research" else "original_reporting")
    ev = verify.EvidenceCandidate(
        ref, originality, True, True, True,
        source_policy.artifact_fingerprint(selected_url) if primary else "",
        source_policy.content_fingerprint(text + " " + slug))
    return verify.ResolutionResult(
        row["url_hash"], row.get("story_key") or "", row["source"], ref, ref, text,
        "selected", True, ev.originality, True, True,
        selected_url if primary else "", ev.primary_artifact_fingerprint,
        ev.content_fingerprint, None, "test resolution", (ev,))


class CycleTests(unittest.TestCase):
    def run_cycle(self, con, raw_items, verdicts, drafts=None, mode="DRAFT", auto=False,
                  editor_result=None, resolution_factory=None,
                  provider_resolution=None, claim_support=None,
                  article_text="Bitcoin test source", source_policy_mode="enforce",
                  article_result=None):
        drafts = drafts or [{"post": "NEW: Bitcoin test.", "event_date": None,
                              "needs_second_source": False}]

        def triage(items, _recent, _open):
            return [{**row, **verdicts[index]} for index, row in enumerate(items)]

        draft = Mock(side_effect=drafts)
        publish = Mock(return_value=(mode, "publisher-ref"))
        review = Mock(return_value=editor_result or {
            "verdict": "publish", "post": drafts[-1].get("post"), "reason": "clean",
        })
        def default_resolution(row, text):
            return make_resolution(row, text)

        resolution_effect = resolution_factory or default_resolution
        provider_effect = provider_resolution or (
            lambda row, _provider: make_resolution(
                row, "Glassnode Bitcoin source", "Glassnode", "t2", "research"))
        resolve = Mock(side_effect=lambda row, text, **_kwargs: resolution_effect(row, text))
        provider_resolve = Mock(
            side_effect=lambda row, provider, **_kwargs: provider_effect(row, provider))
        with ExitStack() as stack:
            stack.enter_context(patch.object(sources, "fetch_feeds", return_value=raw_items))
            stack.enter_context(patch.object(sources, "fetch_edgar", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_perception", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_x", return_value=[]))
            stack.enter_context(patch.object(sources, "fetch_article", return_value=(
                article_result or {
                    "text": article_text,
                    "final_url": raw_items[0]["url"] if raw_items else "",
                    "canonical_url": raw_items[0]["url"] if raw_items else "",
                    "byline": "Reporter",
                })))
            stack.enter_context(patch.object(sources, "chart_image", return_value=None))
            stack.enter_context(patch.object(brain, "triage", side_effect=triage))
            stack.enter_context(patch.object(brain, "draft", draft))
            stack.enter_context(patch.object(publisher, "publish", publish))
            stack.enter_context(patch.object(editor, "review", review))
            stack.enter_context(patch.object(verify, "resolve_source", resolve))
            stack.enter_context(patch.object(verify, "resolve_data_provider", provider_resolve))
            stack.enter_context(patch.object(verify, "claims_supported", return_value=(
                claim_support or {"supported": True, "reason": "supported"})))
            stack.enter_context(patch.object(config, "AUTOPOST_ENABLED", auto))
            stack.enter_context(patch.object(config, "SOURCE_POLICY_MODE", source_policy_mode))
            stack.enter_context(patch.object(config, "AUTOPOST_CLASSES",
                                             {"primary", "corroborated"}))
            result = main.cycle(con)
        return result, draft, publish, review, resolve

    def test_each_publisher_mode_gets_explicit_status_and_counter(self):
        expected = {
            "IMMEDIATE": ("posted", "posted"),
            "DRAFT": ("drafted", "drafted"),
            "UNCERTAIN": ("uncertain", "uncertain"),
            "FAILED": ("failed", "failed"),
            "TAPE": ("taped", "taped"),
        }
        for mode, (status, counter) in expected.items():
            with self.subTest(mode=mode), temporary_store() as con:
                result, *_ = self.run_cycle(
                    con, [item(url=f"https://example.com/{mode.lower()}")],
                    [{"action": "draft", "story_key": mode.lower(), "class": "primary"}],
                    mode=mode,
                )
                row = con.execute("SELECT status FROM items").fetchone()
                self.assertEqual(row["status"], status)
                self.assertEqual(result[counter], 1)

    def test_transient_source_fetch_is_durable_research_retry_not_editorial_hold(self):
        with temporary_store() as con:
            result, draft, publish, _review, resolve = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "retryable-source",
                  "class": "secondary", "reason": "material Bitcoin story"}],
                article_result={
                    "text": "", "final_url": "https://example.com/story",
                    "canonical_url": "https://example.com/story", "byline": "",
                    "outcome": "infrastructure_retryable", "error_kind": "ReadTimeout",
                    "error_message": "source timed out",
                },
            )
            self.assertEqual(result["held"], 1)
            saved = con.execute(
                "SELECT state,attempts,stage FROM research_jobs"
            ).fetchone()
            self.assertEqual((saved["state"], saved["attempts"], saved["stage"]),
                             ("pending", 1, "source_fetch"))
            draft.assert_not_called()
            publish.assert_not_called()
            resolve.assert_not_called()

    def test_cycle_records_triage_and_final_decision_for_desk(self):
        with temporary_store() as con:
            result, *_ = self.run_cycle(
                con, [item(title="Candidate <one>")],
                [{"action": "skip", "story_key": "candidate-one",
                  "reason": "outside the Bitcoin charter"}],
            )
            record = json.loads(store.kv_get(con, "desk:last_decision_run"))
            self.assertEqual(result["considered"], 1)
            self.assertEqual(record["items"][0]["title"], "Candidate <one>")
            self.assertEqual(record["items"][0]["triage_action"], "skip")
            self.assertEqual(record["items"][0]["final_status"], "skipped")

    def test_secondary_draft_reaches_editor_with_autopost_off(self):
        with temporary_store() as con:
            result, _draft, _publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "secondary-story",
                  "class": "secondary"}],
                mode="DRAFT", auto=True,
            )
            self.assertEqual(result["drafted"], 1)
            review.assert_called_once()

    def test_editor_spike_holds_candidate_with_autopost_off(self):
        with temporary_store() as con:
            result, _draft, publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "staged-spike", "class": "primary"}],
                auto=False,
                editor_result={"verdict": "spike", "post": None,
                               "reason": "insufficient reader value"},
            )
            self.assertEqual(result["held"], 1)
            review.assert_called_once()
            publish.assert_not_called()

    def test_nonofficial_source_cannot_keep_model_primary_class(self):
        def nonofficial(row, text):
            return make_resolution({**row, "class": "secondary"}, text)

        with temporary_store() as con:
            _result, _draft, publish, review, _resolve = self.run_cycle(
                con, [item(source="CoinDesk")],
                [{"action": "draft", "story_key": "bad-primary", "class": "primary"}],
                auto=True, resolution_factory=nonofficial)
            self.assertEqual(publish.call_args.args[2], "secondary")
            review.assert_called_once()

    def test_hostile_host_labeled_sec_cannot_reach_autopost(self):
        def hostile(row, text):
            ref = source_policy.classify(row["url"], row["source"])
            return verify._held(row, ref, text, "untrusted source identity")

        with temporary_store() as con:
            result, _draft, publish, review, _resolve = self.run_cycle(
                con, [item(url="https://untrusted.example/story", source="SEC")],
                [{"action": "draft", "story_key": "spoof", "class": "primary"}],
                auto=True, resolution_factory=hostile)
            self.assertEqual(result["policy_held"], 1)
            publish.assert_not_called()
            review.assert_not_called()

    def test_directly_supporting_official_artifact_can_promote_primary(self):
        def official(row, text):
            return make_resolution({**row, "class": "primary"}, text)

        with temporary_store() as con:
            _result, _draft, publish, _review, _resolve = self.run_cycle(
                con, [item(source="CryptoSlate")],
                [{"action": "draft", "story_key": "official-upgrade", "class": "secondary"}],
                resolution_factory=official)
            self.assertEqual(publish.call_args.args[2], "primary")

    def test_ordinary_draft_for_handled_exact_key_is_skipped(self):
        with temporary_store() as con:
            store.log_post(con, "same-story", None, "secondary", "NEW: Earlier.",
                           "https://example.com/earlier", "DRAFT")
            result, draft, publish, _review, resolve = self.run_cycle(
                con, [item(url="https://example.com/new-source")],
                [{"action": "draft", "story_key": "same-story", "class": "secondary"}],
            )
            self.assertEqual(result["posted"], 0)
            draft.assert_not_called()
            publish.assert_not_called()
            resolve.assert_not_called()
            row = con.execute("SELECT status, note FROM items").fetchone()
            self.assertEqual(row["status"], "skipped")
            self.assertEqual(row["note"], "story already handled")

    def test_corrected_handled_key_moves_persisted_evidence_before_skip(self):
        with temporary_store() as con:
            raw = item(url="https://coindesk.com/retried", source="CoinDesk")
            inserted = store.upsert_new_items(con, [raw])[0]
            prior = {**inserted, "story_key": "old-wrong-key", "class": "secondary"}
            store.persist_resolution(con, make_resolution(prior, "Bitcoin retry source"), "enforce")
            store.log_post(con, "correct-key", None, "secondary", "NEW: Earlier.",
                           "https://example.com/earlier", "DRAFT")
            result, draft, publish, _review, resolve = self.run_cycle(
                con, [raw],
                [{"action": "draft", "story_key": "correct-key", "class": "secondary"}],
            )
            self.assertEqual(result["posted"], 0)
            draft.assert_not_called()
            publish.assert_not_called()
            resolve.assert_not_called()
            self.assertEqual(store.qualified_evidence_count(con, "old-wrong-key"), 0)
            self.assertEqual(store.qualified_evidence_count(con, "correct-key"), 1)
            row = con.execute("SELECT story_key FROM source_resolutions").fetchone()
            self.assertEqual(row["story_key"], "correct-key")

    def test_update_without_exact_reader_coverage_is_held(self):
        with temporary_store() as con:
            result, draft, publish, *_ = self.run_cycle(
                con, [item()],
                [{"action": "update", "story_key": "missing-story", "class": "primary"}],
            )
            self.assertEqual(result["held"], 1)
            draft.assert_not_called()
            publish.assert_not_called()

    def test_valid_update_receives_exact_prior_copy(self):
        with temporary_store() as con:
            store.log_post(con, "same-story", None, "primary", "NEW: Earlier fact.",
                           "https://example.com/earlier", "IMMEDIATE")
            result, draft, publish, *_ = self.run_cycle(
                con, [item(url="https://example.com/development")],
                [{"action": "update", "story_key": "same-story", "class": "primary"}],
                drafts=[{"post": "UPDATE: Bitcoin test.", "event_date": None,
                         "needs_second_source": False}],
            )
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_args.kwargs["already_covered"], ["NEW: Earlier fact."])
            publish.assert_called_once()

    def test_update_lint_retry_preserves_prior_coverage(self):
        with temporary_store() as con:
            store.log_post(con, "same-story", None, "primary", "NEW: Earlier fact.",
                           "https://example.com/earlier", "IMMEDIATE")
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False},
                {"post": "UPDATE: Bitcoin test.", "event_date": None,
                 "needs_second_source": False},
            ]
            result, draft, publish, *_ = self.run_cycle(
                con, [item(url="https://example.com/development")],
                [{"action": "update", "story_key": "same-story", "class": "primary"}],
                drafts=drafts,
            )
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 2)
            self.assertEqual(draft.call_args_list[1].kwargs["already_covered"],
                             ["NEW: Earlier fact."])
            publish.assert_called_once()

    def test_secondary_needing_verification_is_held_on_failure(self):
        with temporary_store() as con:
            result, _draft, publish, _review, resolve = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "verify-me", "class": "secondary"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": None,
                         "needs_second_source": True}],
            )
            self.assertEqual(result["held"], 1)
            resolve.assert_called_once()
            publish.assert_not_called()

    def test_stale_event_is_held(self):
        with temporary_store() as con:
            result, _draft, publish, *_ = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "stale", "class": "primary"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": "2020-01-01",
                         "needs_second_source": False}],
            )
            self.assertEqual(result["held"], 1)
            publish.assert_not_called()

    def test_owner_freshness_override_reruns_full_stack_and_stages(self):
        raw = item()
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [raw])[0]
            store.set_status(con, inserted["url_hash"], "held", "stale",
                             "stale event: dated 2020-01-01, window 6h")
            action = store.request_operator_action(con, inserted["url_hash"], "stage")
            self.assertTrue(action["ok"])
            result, draft, publish, review, resolve = self.run_cycle(
                con, [raw],
                [{"action": "skip", "story_key": "wrong-key", "class": "primary",
                  "reason": "triage would skip"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": "2020-01-01",
                         "needs_second_source": False}],
                mode="DRAFT", auto=True,
            )
            self.assertEqual(result["drafted"], 1)
            draft.assert_called_once()
            resolve.assert_called_once()
            self.assertTrue(resolve.call_args.kwargs["force_refresh"])
            self.assertFalse(resolve.call_args.kwargs["use_persisted"])
            review.assert_called_once()
            self.assertTrue(publish.call_args.kwargs["force_draft"])
            self.assertEqual(publish.call_args.args[1], "https://example.com/story")
            saved = store.latest_operator_action(con, inserted["url_hash"])
            self.assertEqual((saved["state"], saved["result"]),
                             ("completed", "delivery result: DRAFT"))

    def test_owner_override_does_not_bypass_a_different_gate(self):
        raw = item()
        with temporary_store() as con:
            inserted = store.upsert_new_items(con, [raw])[0]
            store.set_status(con, inserted["url_hash"], "held", "stale",
                             "stale event: dated 2020-01-01, window 6h")
            action = store.request_operator_action(con, inserted["url_hash"], "stage")
            result, _draft, publish, review, _resolve = self.run_cycle(
                con, [raw], [{"action": "draft", "story_key": "stale", "class": "primary"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": "2020-01-01",
                         "needs_second_source": False}],
                auto=True,
                editor_result={"verdict": "spike", "post": None, "reason": "too weak"},
            )
            self.assertEqual(result["held"], 1)
            review.assert_called_once()
            publish.assert_not_called()
            saved = store.latest_operator_action(con, inserted["url_hash"])
            self.assertEqual(saved["id"], action["id"])
            self.assertEqual(saved["state"], "blocked")
            self.assertIn("editor spiked", saved["result"])

    def test_editor_spike_holds_autonomous_candidate(self):
        with temporary_store() as con:
            result, _draft, publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "spike", "class": "primary"}],
                auto=True,
                editor_result={"verdict": "spike", "post": None, "reason": "duplicate"},
            )
            self.assertEqual(result["held"], 1)
            review.assert_called_once()
            publish.assert_not_called()

    def test_two_distinct_sources_promote_secondary_to_corroborated(self):
        with temporary_store() as con:
            raw = [item("https://one.example/story", source="Outlet One"),
                   item("https://two.example/story", source="Outlet Two")]
            verdicts = [
                {"action": "draft", "story_key": "two-source", "class": "secondary"},
                {"action": "draft", "story_key": "two-source", "class": "secondary"},
            ]
            result, _draft, publish, review, resolve = self.run_cycle(
                con, raw, verdicts, mode="IMMEDIATE", auto=True)
            self.assertEqual(result["posted"], 1)
            self.assertEqual(publish.call_args.args[2], "corroborated")
            review.assert_called_once()
            self.assertEqual(resolve.call_count, 2)

    def test_story_receipt_selection_is_permutation_invariant(self):
        def ranked(row, text):
            if row["source"] == "SEC":
                return make_resolution({**row, "class": "primary"}, text)
            return make_resolution({**row, "class": "secondary"}, text)

        t2 = item("https://coindesk.com/report", source="CoinDesk")
        p0 = item("https://sec.gov/newsroom/press-releases/order", source="SEC")
        selected = []
        for rows in ([t2, p0], [p0, t2]):
            with temporary_store() as con:
                verdicts = [
                    {"action": "draft", "story_key": "same-ranked-story",
                     "class": "primary" if row["source"] == "SEC" else "secondary"}
                    for row in rows
                ]
                result, draft, publish, _review, _resolve = self.run_cycle(
                    con, rows, verdicts,
                    drafts=[{"post": "NEW: Bitcoin test.", "event_date": None,
                             "needs_second_source": False} for _ in rows],
                    resolution_factory=ranked)
                self.assertEqual(result["drafted"], 1)
                self.assertEqual(draft.call_count, 2)
                selected.append((publish.call_args.args[1], publish.call_args.args[2]))
        self.assertEqual(selected, [
            ("https://sec.gov/newsroom/press-releases/order", "primary"),
            ("https://sec.gov/newsroom/press-releases/order", "primary"),
        ])

    def test_provider_substitutions_finalize_before_corroboration(self):
        drafts = [
            {"post": "NEW: Bitcoin test.", "event_date": None,
             "needs_second_source": False, "data_provider": "Glassnode"}
            for _ in range(4)
        ]
        with temporary_store() as con:
            rows = [item("https://coindesk.com/one", source="CoinDesk"),
                    item("https://theblock.co/two", source="The Block")]
            verdicts = [{"action": "draft", "story_key": "provider-collapse",
                         "class": "secondary"} for _ in rows]
            result, draft, publish, _review, _resolve = self.run_cycle(
                con, rows, verdicts, drafts=drafts)
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 4)
            self.assertEqual(publish.call_args.args[2], "secondary")
            self.assertEqual(store.qualified_evidence_count(con, "provider-collapse"), 1)

    def test_later_cycle_eligible_source_completes_corroboration(self):
        with temporary_store() as con:
            first_result, *_ = self.run_cycle(
                con, [item("https://one.example/story", source="Outlet One")],
                [{"action": "draft", "story_key": "later-source", "class": "secondary"}],
                drafts=[{"post": "NEW: Bitcoin test.", "event_date": None,
                         "needs_second_source": True}])
            self.assertEqual(first_result["held"], 1)
            second_result, _draft, publish, *_ = self.run_cycle(
                con, [item("https://two.example/story", source="Outlet Two")],
                [{"action": "draft", "story_key": "later-source", "class": "secondary"}],
                mode="IMMEDIATE", auto=True)
            self.assertEqual(second_result["posted"], 1)
            self.assertEqual(publish.call_args.args[2], "corroborated")

    def test_lint_failure_after_retry_is_held(self):
        with temporary_store() as con:
            invalid = {"post": "UPDATE: Bitcoin test.", "event_date": None,
                       "needs_second_source": False}
            result, draft, publish, *_ = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "bad-copy", "class": "primary"}],
                drafts=[invalid, invalid],
            )
            self.assertEqual(result["held"], 1)
            self.assertEqual(draft.call_count, 2)
            publish.assert_not_called()

    def test_data_provider_resolution_redrafts_from_provider_receipt(self):
        with temporary_store() as con:
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
            ]
            result, draft, publish, *_ = self.run_cycle(
                con, [item(source="CoinDesk")],
                [{"action": "draft", "story_key": "provider", "class": "secondary"}],
                drafts=drafts)
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 2)
            self.assertEqual(publish.call_args.args[1], "https://glassnode.com/report")
            self.assertEqual(publish.call_args.args[2], "secondary")
            resolution = con.execute(
                "SELECT original_source, selected_source FROM source_resolutions"
            ).fetchone()
            self.assertEqual(dict(resolution), {
                "original_source": "CoinDesk", "selected_source": "Glassnode"})

    def test_provider_replacement_removes_primary_class_from_final_receipt(self):
        def official(row, text):
            return make_resolution({**row, "class": "primary"}, text)

        with temporary_store() as con:
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
            ]
            result, _draft, publish, review, _resolve = self.run_cycle(
                con, [item(source="SEC")],
                [{"action": "draft", "story_key": "provider-demotion", "class": "primary"}],
                drafts=drafts, auto=True, resolution_factory=official)
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(publish.call_args.args[2], "secondary")
            review.assert_called_once()

    def test_data_provider_second_mismatch_holds_without_loop(self):
        with temporary_store() as con:
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Coin Metrics"},
            ]
            result, draft, publish, *_ = self.run_cycle(
                con, [item(source="CoinDesk")],
                [{"action": "draft", "story_key": "provider-mismatch",
                  "class": "secondary"}], drafts=drafts)
            self.assertEqual(result["held"], 1)
            self.assertEqual(draft.call_count, 2)
            publish.assert_not_called()

    def test_observe_mode_records_provider_failure_but_stages_draft(self):
        def provider_failure(row, _provider):
            ref = source_policy.classify(row["url"], row["source"])
            return verify._held(row, ref, "", "provider lookup offline")

        with temporary_store() as con:
            drafts = [{"post": "NEW: Bitcoin test.", "event_date": None,
                       "needs_second_source": False, "data_provider": "Glassnode"}]
            result, draft, publish, _review, _resolve = self.run_cycle(
                con, [item(source="CoinDesk")],
                [{"action": "draft", "story_key": "provider-observe", "class": "secondary"}],
                drafts=drafts, provider_resolution=provider_failure,
                source_policy_mode="observe")
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 1)
            publish.assert_called_once()
            row = con.execute("SELECT status, note FROM source_resolutions").fetchone()
            self.assertEqual(row["status"], "held")
            self.assertIn("observe would hold", row["note"])

    def test_observe_stages_pre_provider_draft_when_claim_support_fails(self):
        with temporary_store() as con:
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
            ]
            result, draft, publish, _review, _resolve = self.run_cycle(
                con, [item(source="CoinDesk")],
                [{"action": "draft", "story_key": "provider-claim-observe",
                  "class": "secondary"}],
                drafts=drafts, claim_support={"supported": False, "reason": "ambiguous"},
                source_policy_mode="observe")
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 2)
            self.assertEqual(publish.call_args.args[1], "https://example.com/story")
            row = con.execute("SELECT status, selected_source, note FROM source_resolutions").fetchone()
            self.assertEqual((row["status"], row["selected_source"]), ("held", "CoinDesk"))
            self.assertIn("provider terminal gate", row["note"])

    def test_observe_stages_pre_provider_draft_when_provider_lint_fails(self):
        with temporary_store() as con:
            drafts = [
                {"post": "NEW: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
                {"post": "UPDATE: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
                {"post": "UPDATE: Bitcoin test.", "event_date": None,
                 "needs_second_source": False, "data_provider": "Glassnode"},
            ]
            result, draft, publish, _review, _resolve = self.run_cycle(
                con, [item(source="CoinDesk")],
                [{"action": "draft", "story_key": "provider-lint-observe",
                  "class": "secondary"}],
                drafts=drafts, source_policy_mode="observe")
            self.assertEqual(result["drafted"], 1)
            self.assertEqual(draft.call_count, 3)
            self.assertEqual(publish.call_args.args[0], "NEW: Bitcoin test.")
            row = con.execute("SELECT status, note FROM source_resolutions").fetchone()
            self.assertEqual(row["status"], "held")
            self.assertIn("provider terminal gate", row["note"])

    def test_locked_worker_skips_news_briefing_and_audit(self):
        with temporary_store() as con, \
                patch.object(store, "acquire_cycle_lease", return_value=False), \
                patch.object(main, "_cycle_locked") as news, \
                patch.object(main.briefing, "maybe_run") as briefing_run, \
                patch("nbn.audit.maybe_run") as audit_run:
            result = main.worker_iteration(con)
        self.assertEqual(result, {"skipped_locked": 1})
        news.assert_not_called()
        briefing_run.assert_not_called()
        audit_run.assert_not_called()

    def test_cycle_lease_heartbeat_renews_with_separate_connection(self):
        class StopAfterOneRenewal:
            def __init__(self):
                self.calls = 0

            def wait(self, _seconds):
                self.calls += 1
                return self.calls > 1

        connection = Mock()
        stop = StopAfterOneRenewal()
        with patch.object(store, "connect", return_value=connection), \
                patch.object(store, "renew_cycle_lease", return_value=True) as renew, \
                patch.object(config, "CYCLE_LEASE_HEARTBEAT_SECONDS", 30), \
                patch.object(config, "CYCLE_LEASE_SECONDS", 120):
            main._renew_cycle_lease_until_stopped("owner-a", stop)
        renew.assert_called_once_with(connection, "owner-a", ttl_seconds=120)
        connection.close.assert_called_once()

    def test_editor_revision_is_relinted_and_published(self):
        with temporary_store() as con:
            revised = "NEW: Bitcoin test, tightened."
            result, _draft, publish, review, _verify = self.run_cycle(
                con, [item()],
                [{"action": "draft", "story_key": "revise", "class": "primary"}],
                mode="IMMEDIATE", auto=True,
                editor_result={"verdict": "revise", "post": revised, "reason": "tighter"},
            )
            self.assertEqual(result["posted"], 1)
            review.assert_called_once()
            self.assertEqual(publish.call_args.args[0], revised)

    def test_source_overlap_is_one_durable_latest_pulse_url_metric_per_cycle(self):
        now = 1788192000
        shared = "https://example.com/shared?utm_source=direct"
        primary = "https://reuters.com/primary"
        pulse = {
            "run_id": 501,
            "status": "partial",
            "generated_at": "2026-08-31T16:00:00+00:00",
            "candidate_count": 2,
            "all_key_hashes": [
                store.url_hash(store.canonical_discovery_key(shared)),
                store.url_hash(store.canonical_discovery_key(primary)),
            ],
            "primary_key_hashes": [store.url_hash(store.canonical_discovery_key(primary))],
            "timestamp_counts": {"parseable": 2, "unknown": 0, "unparseable": 0},
        }
        direct = [{"url": shared, "published": "2026-08-31T15:55:00Z"}]
        detectors = [{"source": "X detector @CoinDesk", "url": primary, "published": ""}]
        with temporary_store() as con:
            store.kv_set(con, "node:latest_pulse", json.dumps(pulse))
            main._record_source_overlap(con, "cycle-1", direct, detectors, now)
            main._record_source_overlap(con, "cycle-1", direct, detectors, now)
            rows = con.execute(
                "SELECT category,metadata FROM pipeline_events WHERE event='source_overlap'"
            ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["category"], "latest_pulse_url_overlap")
        metadata = json.loads(rows[0]["metadata"])
        self.assertTrue(metadata["pulse"]["fresh"])
        self.assertEqual(metadata["direct_perception"]["any_ref_overlap"], 1)
        self.assertEqual(metadata["direct_perception"]["primary_ref_overlap"], 0)
        self.assertEqual(metadata["broad_detector_x"]["primary_ref_overlap"], 1)
        self.assertEqual(metadata["broad_detector_x"]["timestamps"]["unknown"], 1)


if __name__ == "__main__":
    unittest.main()
