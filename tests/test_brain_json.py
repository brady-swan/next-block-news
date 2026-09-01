import unittest
import json
from types import SimpleNamespace
from unittest.mock import patch

from nbn import brain


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
        self.assertEqual(out[1]["action"], "draft")
        self.assertEqual(out[1]["reason"], "guide lead recovery")

    def test_omitted_guide_verdict_fails_into_research_not_skip(self):
        item = {
            "url_hash": "abcdef1234567890ffff", "source": "X guide @BitcoinNewsCom",
            "title": "A Bitcoin claim", "url": "https://x.com/BitcoinNewsCom/status/1",
            "published": "", "summary": "", "discovery_context": json.dumps({
                "untrusted_discovery_context": True, "guide_account_signal": True,
            }),
        }
        with patch.object(brain, "_create", return_value=response("[]")):
            out = brain.triage([item], [], [])
        self.assertEqual(out[0]["action"], "draft")
        self.assertEqual(out[0]["reason"], "guide lead recovery")

    def test_guide_post_reaches_writer_as_format_example_not_evidence(self):
        item = {
            "source": "Bloomberg", "title": "Verified Bitcoin story",
            "url": "https://bloomberg.com/story", "published": "", "class": "secondary",
            "discovery_context": json.dumps({
                "untrusted_discovery_context": True,
                "guide_account_signal": True,
                "guide_handle": "BitcoinArchive",
                "guide_post_text": "JUST IN: Bitcoin policy changed. • First fact • Second fact",
                "guide_format_metrics": {"likes": 42, "characters": 60},
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
