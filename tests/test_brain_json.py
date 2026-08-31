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


if __name__ == "__main__":
    unittest.main()
