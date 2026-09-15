import copy
import json
import unittest
from unittest.mock import Mock, patch

import httpx

from nbn import config, reporter_delivery as delivery, reporter_store as rs, reporter_tools as tools
from tests.support import temporary_store


class ReporterXIdentityTests(unittest.TestCase):
    def post(self, ident="2099680499094737251", author="260702356"):
        return {"id": ident, "author_id": author, "text": "Original source.",
                "note_tweet": {"text": "Complete original source."},
                "created_at": "2026-09-15T02:03:35.000Z"}

    def includes(self):
        return {"users": [{"id": "260702356", "username": "yhaiyang"}]}

    def fetch(self, con, shift, raw, args):
        with patch.object(config, "X_BEARER_TOKEN", "fixture"), \
                patch.object(tools.httpx, "get", return_value=httpx.Response(200, json=raw)):
            return tools.dispatch(con, shift_id=shift["shift_id"], generation=shift["generation"],
                                  name="nbn_x", args=args)["posts"]

    def test_exact_fetch_persists_api_bound_alias_without_changing_provenance(self):
        with temporary_store() as con:
            shift = rs.start(con, worker_id="test", shift_id="identity")
            post, includes = self.post(), self.includes()
            receipt = self.fetch(con, shift, {"data": post, "includes": includes},
                                 {"post_id": post["id"]})[0]
            self.assertEqual(receipt["canonical_url"], "https://x.com/yhaiyang/status/" + post["id"])
            self.assertEqual(receipt["url"], "https://x.com/i/status/" + post["id"])
            self.assertEqual(receipt["final_url"], receipt["url"])
            self.assertEqual(receipt["text"], "Complete original source.")
            self.assertEqual(receipt["retrieval_kind"], "direct_fetch")
            self.assertEqual(receipt["post"], post)
            self.assertEqual(receipt["includes"], includes)
            self.assertEqual(tools.read_evidence(con, receipt["fetch_id"]), receipt)

    def test_search_uses_each_top_level_author_not_quoted_author(self):
        with temporary_store() as con:
            shift = rs.start(con, worker_id="test", shift_id="identity")
            first, second = self.post(), self.post("2099680499094737252", "99")
            first["referenced_tweets"] = [{"type": "quoted", "id": "2099680499094737253"}]
            includes = {"users": [{"id": "100", "username": "quoted_author"},
                                   {"id": "99", "username": "other_author"},
                                   *self.includes()["users"]],
                        "tweets": [self.post("2099680499094737253", "100")]}
            receipts = self.fetch(con, shift, {"data": [first, second], "includes": includes},
                                  {"query": "from:someone_else bitcoin"})
            self.assertEqual([r["canonical_url"] for r in receipts], [
                "https://x.com/yhaiyang/status/2099680499094737251",
                "https://x.com/other_author/status/2099680499094737252"])

    def test_unbound_or_malformed_author_expansions_leave_existing_url_usable(self):
        cases = [None, [], {}, {"users": None}, {"users": {}}, {"users": []},
                 {"users": [None, 42, {"id": "other", "username": "other"}]},
                 {"users": [{"id": "99", "username": "yhaiyang"}]},
                 {"users": self.includes()["users"] * 2},
                 {"users": [*self.includes()["users"], {"id": "260702356"}]},
                 {"users": [*self.includes()["users"], {"id": "260702356", "username": "different"}]}]
        for username in (None, 1, [], "", "@name", "a/b", "name?x=1", "na mé", "ｎame", "x" * 16):
            cases.append({"users": [{"id": "260702356", "username": username}]})
        with temporary_store() as con:
            shift = rs.start(con, worker_id="test", shift_id="identity")
            for includes in cases:
                with self.subTest(includes=includes):
                    receipt = self.fetch(con, shift, {"data": self.post(), "includes": includes},
                                         {"post_id": self.post()["id"]})[0]
                    self.assertNotIn("canonical_url", receipt)
                    self.assertEqual(receipt["url"], "https://x.com/i/status/2099680499094737251")
                    self.assertEqual(receipt["text"], "Complete original source.")

    def test_alias_rejects_nonstring_nonascii_or_missing_ids(self):
        for field in ("id", "author_id"):
            for value in (None, 12, True, [], "", "12/34", "１２３"):
                with self.subTest(field=field, value=value):
                    post = self.post(); post[field] = value
                    self.assertEqual(tools._x_source_alias(post, self.includes()), {})
        self.assertEqual(tools._x_source_alias(None, self.includes()), {})

    def test_stored_alias_delivery_accepts_once_and_rejects_unbound_or_failed_evidence(self):
        with temporary_store() as con, patch.object(config, "OPERATING_MODE", "infrastructure"), \
                patch.object(config, "AUTOPOST_ENABLED", False), patch.object(delivery.publisher, "tape"):
            shift = rs.start(con, worker_id="test", shift_id="identity")
            receipt = self.fetch(con, shift, {"data": self.post(), "includes": self.includes()},
                                 {"post_id": self.post()["id"]})[0]
            payload = {"event_key": "identity-event", "body": "A sourced operational update.",
                       "source_url": receipt["canonical_url"], "evidence_ids": [receipt["fetch_id"]],
                       "self_review": "Original source inspected."}
            args = dict(shift_id=shift["shift_id"], generation=shift["generation"],
                        submission_id="identity-submission", payload=payload)
            remote = {"id": 123, "status": "draft", "social_set_id": config.TYPEFULLY_SOCIAL_SET_ID,
                      "created_at": "2026-09-15T04:00:00Z", "updated_at": None,
                      "platforms": {"x": {"enabled": True, "posts": [
                          {"text": payload["body"], "media_ids": []},
                          {"text": "Source: " + payload["source_url"], "media_ids": []}]}}}
            response = Mock(); response.json.return_value = remote
            with patch.object(delivery.httpx, "post", return_value=response) as post, \
                    patch.object(delivery.tf, "get_draft", return_value=remote):
                for source in ("https://x.com/unbound/status/2099680499094737251",
                               "https://x.com/yhaiyang/status/2099680499094737252"):
                    with self.assertRaisesRegex(ValueError, "successfully inspected"):
                        delivery.submit(con, **{**args, "payload": {**payload, "source_url": source}})
                for invalid in ({"text": ""}, {"outcome": "evidence_failed"}, {"error_kind": "blocked"}):
                    with con:
                        con.execute("UPDATE reporter_records SET payload_json=? WHERE record_id=?",
                                    (json.dumps({**receipt, **invalid}), receipt["fetch_id"]))
                    with self.assertRaisesRegex(ValueError, "successfully inspected"):
                        delivery.submit(con, **args)
                post.assert_not_called()
                self.assertEqual(con.execute("SELECT count(*) FROM reporter_submissions").fetchone()[0], 0)
                with con:
                    con.execute("UPDATE reporter_records SET payload_json=? WHERE record_id=?",
                                (json.dumps(receipt), receipt["fetch_id"]))
                self.assertEqual(delivery.submit(con, **args)["state"], "staged")
                self.assertEqual(delivery.submit(con, **args)["provider_ref"], "123")
                post.assert_called_once()
                changed = copy.deepcopy(payload); changed["body"] = "Different copy."
                with self.assertRaisesRegex(ValueError, "different content"):
                    delivery.submit(con, **{**args, "payload": changed})
