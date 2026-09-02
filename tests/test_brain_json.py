import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from nbn import brain, guide_context


def response(text):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text)],
    )


class BrainJsonTests(unittest.TestCase):
    def test_decodes_first_valid_json_value_when_model_appends_another(self):
        value = brain._json_from(response(
            'Result:\n[{"action":"skip","story_key":"one"}]\n'
            '{"note":"unrequested trailing object"}'
        ))
        self.assertEqual(value, [{"action": "skip", "story_key": "one"}])

    def test_skips_non_json_brackets_before_json(self):
        value = brain._json_from(response('Use [this format].\n```json\n{"post":null}\n```'))
        self.assertEqual(value, {"post": None})

    def test_lenient_draft_still_degrades_prose_to_empty_post(self):
        self.assertEqual(
            brain._json_from(response("No suitable post."), lenient_draft=True),
            {"post": None, "needs_second_source": False},
        )

    def test_node_context_reaches_only_triage_as_untrusted_detector_context(self):
        item = {
            "url_hash": "abc", "source": "CoinDesk", "title": "Bitcoin policy",
            "url": "https://coindesk.com/story", "published": "",
            "summary": "", "discovery_origin": "marketing_node",
            "discovery_context": json.dumps({
                "untrusted_discovery_context": True, "theme": "Bitcoin policy",
            }),
        }
        seen = []

        def fake_create(_model, _system, user, **_kwargs):
            seen.append(json.loads(user))
            return response('[{"url_hash":"abc","action":"skip","story_key":null,'
                            '"class":"secondary","reason":"test"}]')

        with patch.object(brain, "_create", side_effect=fake_create):
            brain.triage([item], [], [])
        self.assertTrue(seen[0]["items"][0]["detector_context_untrusted"]
                        ["untrusted_discovery_context"])

        draft_payload = []
        with patch.object(brain, "_create", side_effect=lambda _m, _s, user, **_k: (
                draft_payload.append(json.loads(user)) or response('{"post":null}'))):
            brain.draft(item, "Verified source text", {})
        self.assertNotIn("detector_context_untrusted", draft_payload[0])
        self.assertNotIn("discovery_context", draft_payload[0])

    def test_triage_retries_items_omitted_by_the_first_response(self):
        items = [
            {"url_hash": "one", "source": "CoinDesk", "title": "First", "url":
             "https://coindesk.com/one", "published": "", "summary": ""},
            {"url_hash": "two", "source": "X guide @BitcoinArchive", "title": "Second",
             "url": "https://x.com/BitcoinArchive/status/2", "published": "", "summary": "",
             "discovery_context": json.dumps({
                 "untrusted_discovery_context": True, "guide_account_signal": True,
             })},
        ]
        replies = [
            response('[{"url_hash":"one","action":"skip","story_key":null,'
                     '"class":"secondary","reason":"test"}]'),
            response('[{"url_hash":"two","action":"draft","story_key":"second-story",'
                     '"class":"secondary","reason":"guide lead"}]'),
        ]
        with patch.object(brain, "_create", side_effect=replies) as create:
            out = brain.triage(items, [], [])
        self.assertEqual(create.call_count, 2)
        self.assertEqual(out[1]["action"], "draft")
        self.assertEqual(out[1]["story_key"], "second-story")

    def test_triage_receives_advisory_theme_snapshot_without_quota_rule(self):
        item = {
            "url_hash": "one", "source": "Node", "title": "Bitcoin development",
            "url": "https://example.com/one", "published": "", "summary": "",
        }
        snapshot = [{
            "theme_id": "institutional-adoption", "coverage_known": False,
            "last_published_at": None, "open_draft": False, "recent_story_keys": [],
        }]
        payloads = []
        with patch.object(brain, "_create", side_effect=lambda _m, _s, user, **_k: (
                payloads.append(json.loads(user)) or response(
                    '[{"url_hash":"one","action":"skip","story_key":null,'
                    '"class":"secondary","reason":"test"}]'))):
            brain.triage([item], [], [], snapshot)
        self.assertEqual(payloads[0]["theme_coverage_snapshot"], snapshot)
        self.assertIn("no theme has a publishing quota", brain.TRIAGE_SYSTEM)
        self.assertIn("does NOT mean", brain.TRIAGE_SYSTEM)

    def test_empty_initial_triage_response_uses_recovery_batch(self):
        item = {
            "url_hash": "one", "source": "CoinDesk", "title": "First",
            "url": "https://coindesk.com/one", "published": "", "summary": "",
        }
        replies = [
            response(""),
            response('[{"url_hash":"one","action":"draft","story_key":"first",'
                     '"class":"secondary","reason":"recovered"}]'),
        ]
        with patch.object(brain, "_create", side_effect=replies) as create:
            out = brain.triage([item], [], [])
        self.assertEqual(create.call_count, 2)
        self.assertEqual(create.call_args_list[0].kwargs["effort"], "medium")
        self.assertEqual(create.call_args_list[0].kwargs["max_tokens"], 6000)
        self.assertEqual(out[0]["action"], "draft")
        self.assertEqual(out[0]["story_key"], "first")

    def test_two_empty_triage_responses_fail_closed_except_guide_research(self):
        items = [
            {
                "url_hash": "ordinary", "source": "CoinDesk", "title": "First",
                "url": "https://coindesk.com/one", "published": "", "summary": "",
            },
            {
                "url_hash": "guide1234567890abcd", "source": "X guide @BitcoinArchive",
                "title": "Second", "url": "https://x.com/BitcoinArchive/status/2",
                "published": "", "summary": "",
            },
        ]
        with patch.object(brain, "_create", return_value=response("")) as create:
            out = brain.triage(items, [], [])
        self.assertEqual(create.call_count, 2)
        self.assertEqual(out[0]["action"], "hold")
        self.assertEqual(out[1]["action"], "hold")
        self.assertEqual(out[1]["reason"], "triage incomplete: guide non-claim")

    def test_omitted_guide_verdict_fails_into_research_not_skip(self):
        item = {
            "url_hash": "abcdef1234567890ffff", "source": "X guide @BitcoinNewsCom",
            "title": "Bitcoin ETF inflows rose 25% after the latest filing",
            "url": "https://x.com/BitcoinNewsCom/status/1",
            "published": "", "summary": "", "discovery_context": json.dumps({
                "untrusted_discovery_context": True, "guide_account_signal": True,
            }),
        }
        with patch.object(brain, "_create", return_value=response("[]")):
            out = brain.triage([item], [], [])
        self.assertEqual(out[0]["action"], "draft")
        self.assertEqual(out[0]["reason"], "guide lead recovery")

    def test_story_key_reconciliation_accepts_only_known_high_confidence_cluster(self):
        items = [{
            "url_hash": "candidate", "source": "Bloomberg", "title": "G7 yields rise",
            "summary": "", "story_key": "g7-yields", "action": "draft",
            "_selected_source": "Bloomberg", "_selected_text": "Global yields rose.",
        }]
        clusters = [{"canonical_key": "global-yields", "titles": ["Bond yields rise"]}]
        reply = response('[{"url_hash":"candidate","canonical_key":"global-yields",'
                         '"relationship":"same_event","confidence":0.96,'
                         '"reason":"same dated move"}]')
        with patch.object(brain, "_create", return_value=reply):
            out = brain.reconcile_story_keys(items, clusters)
        self.assertEqual(out[0]["canonical_key"], "global-yields")
        self.assertEqual(out[0]["relationship"], "same_event")

        low = response('[{"url_hash":"candidate","canonical_key":"global-yields",'
                       '"relationship":"same_event","confidence":0.6,"reason":"unclear"}]')
        with patch.object(brain, "_create", return_value=low):
            out = brain.reconcile_story_keys(items, clusters)
        self.assertEqual(out[0]["canonical_key"], "g7-yields")
        self.assertEqual(out[0]["relationship"], "distinct")

    def test_story_identity_receives_theme_only_as_broad_context(self):
        item = {
            "url_hash": "candidate", "source": "Bloomberg", "title": "Vote",
            "summary": "", "story_key": "vote", "action": "draft",
            "discovery_context": json.dumps({
                "untrusted_discovery_context": True,
                "theme_ids": ["strategic-bitcoin-reserves"],
            }),
        }
        payloads = []
        with patch.object(brain, "_create", side_effect=lambda _m, _s, user, **_k: (
                payloads.append(json.loads(user)) or response(
                    '[{"url_hash":"candidate","canonical_key":"vote",'
                    '"relationship":"distinct","confidence":1,"reason":"distinct"}]'))):
            brain.reconcile_story_keys([item], [])
        self.assertEqual(
            payloads[0]["candidates"][0]["node_theme_ids"],
            ["strategic-bitcoin-reserves"],
        )
        self.assertIn("never sufficient", brain.CLUSTER_SYSTEM)

    def test_story_key_reconciliation_failure_preserves_provisional_key(self):
        items = [{
            "url_hash": "candidate", "source": "CNBC", "title": "Treasury yields rise",
            "summary": "", "story_key": "treasury-yields", "action": "draft",
        }]
        with patch.object(brain, "_create", side_effect=TimeoutError("model timeout")):
            out = brain.reconcile_story_keys(items, [])
        self.assertEqual(out[0]["canonical_key"], "treasury-yields")
        self.assertEqual(out[0]["relationship"], "distinct")

    def test_guide_post_reaches_writer_as_format_example_not_evidence(self):
        guide = guide_context.build_signal(
            "BitcoinArchive", "https://x.com/BitcoinArchive/status/1",
            "JUST IN: Bitcoin policy changed. • First fact • Second fact",
            {"likes": 42, "characters": 60}, [],
        )
        item = {
            "source": "Bloomberg", "title": "Verified Bitcoin story",
            "url": "https://bloomberg.com/story", "published": "", "class": "secondary",
            "discovery_context": json.dumps({
                "untrusted_discovery_context": True,
                "guide_signal": guide,
            }),
        }
        payloads = []
        with patch.object(brain, "_create", side_effect=lambda _m, _s, user, **_k: (
                payloads.append(json.loads(user)) or response('{"post":null}'))):
            brain.draft(item, "The verified source text.", {})
        example = payloads[0]["guide_format_example_untrusted"]
        self.assertEqual(example["handle"], "BitcoinArchive")
        self.assertIn("First fact", example["text"])
        self.assertEqual(payloads[0]["source_text"], "The verified source text.")


if __name__ == "__main__":
    unittest.main()
