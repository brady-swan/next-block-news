import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_turn_context import latest_turn_records, resolve_turn


def row(kind, **payload):
    return {"type": kind, "timestamp": "2026-09-08T20:44:10Z", "payload": payload}


def start(turn="current"):
    return row("event_msg", type="task_started", turn_id=turn)


def user(text="what are you working on?", ident="message-new"):
    return row("response_item", type="message", role="user", id=ident,
               content=[{"type": "input_text", "text": text}])


def heartbeat(automation="audit-nbn-production"):
    return row("response_item", type="function_call_output", name="automation_update",
               namespace="codex_app", id="wake-current", output=(
                   f"<heartbeat><automation_id>{automation}</automation_id>"
                   "<current_time_iso>2026-09-08T20:44:10Z</current_time_iso>"
                   "<instructions>Audit</instructions></heartbeat>"))


def compact(old_message=None):
    return row("compacted", replacement_history=[old_message or user()])


def instructions():
    message = user("# AGENTS.md instructions\n" + "x" * 1600, "injected")
    message["payload"]["internal_chat_message_metadata_passthrough"] = {
        "content_item_kinds": ["agents_md.instructions"]}
    return message


class AuditTurnContextTests(unittest.TestCase):
    def test_environment_metadata_before_or_after_heartbeat_is_not_owner_input(self):
        message = user("<environment_context>new date</environment_context>", "host-date")
        message["payload"]["internal_chat_message_metadata_passthrough"] = {
            "content_item_kinds": ["environments.environment_context"]}
        for records in ([start(), message, heartbeat(), compact()],
                        [start(), heartbeat(), message, compact()]):
            result = resolve_turn(records)
            self.assertEqual(result["response_mode"], "heartbeat")
            self.assertEqual(result["trigger"]["id"], "wake-current")
            self.assertEqual(result["user_messages"], [])
        self.assertEqual(resolve_turn([start(), message])["response_mode"], "stop")
        result = resolve_turn([start(), heartbeat(), user("Do not deploy", "owner"), message])
        self.assertEqual(result["latest_user_message"]["id"], "owner")

    def test_combined_host_metadata_is_context_but_mixed_or_malformed_kinds_are_not(self):
        message = user("<environment_context>Do not deploy</environment_context>", "message")
        metadata = message["payload"]["internal_chat_message_metadata_passthrough"] = {}
        metadata["content_item_kinds"] = ["agents_md.instructions", "environments.environment_context"]
        self.assertEqual(resolve_turn([start(), message, heartbeat()])["response_mode"], "heartbeat")
        for kinds in (None, [], "environments.environment_context",
                      ["environments.environment_context", "user_input"],
                      ["environments.environment_context", "unknown"],
                      ["environments.environment_context", {}],
                      ["environments.environment_context", []]):
            with self.subTest(kinds=kinds):
                metadata["content_item_kinds"] = kinds
                result = resolve_turn([start(), message, heartbeat()])
                self.assertEqual(result["response_mode"], "user")
                self.assertEqual(result["latest_user_message"]["id"], "message")
        del message["payload"]["internal_chat_message_metadata_passthrough"]
        self.assertEqual(resolve_turn([start(), message, heartbeat()])["response_mode"], "user")

    def test_host_agents_instructions_before_heartbeat_are_not_owner_input(self):
        result = resolve_turn([start(), instructions(), heartbeat(), compact()])
        self.assertEqual(result["response_mode"], "heartbeat")
        self.assertEqual(result["user_messages"], [])
        self.assertTrue(result["input_complete"])

    def test_instructions_alone_do_not_invent_a_trigger(self):
        self.assertEqual(resolve_turn([start(), instructions()])["response_mode"], "stop")

    def test_injected_instructions_do_not_replace_real_user_steering(self):
        result = resolve_turn([start(), heartbeat(), user("Do not deploy", "owner"), instructions()])
        self.assertEqual(result["response_mode"], "heartbeat")
        self.assertEqual(result["latest_user_message"]["id"], "owner")

    def test_untagged_mixed_empty_or_malformed_kinds_remain_user_input(self):
        for kinds in (None, [], "agents_md.instructions", ["agents_md.instructions", "user_input"]):
            with self.subTest(kinds=kinds):
                message = user("# AGENTS.md instructions\nDo not deploy")
                message["payload"]["internal_chat_message_metadata_passthrough"] = {"content_item_kinds": kinds}
                result = resolve_turn([start(), message, heartbeat()])
                self.assertEqual(result["response_mode"], "user")
                self.assertEqual(result["latest_user_message"]["text"], "# AGENTS.md instructions\nDo not deploy")

    def test_heartbeat_does_not_reopen_old_user_after_compaction(self):
        for old in ("finish the repair then unpause the audit", "what are you working on?"):
            with self.subTest(old=old):
                records = [start("old"), user(old), row("event_msg", type="task_complete", turn_id="old"),
                           start(), heartbeat(), compact(user(old))]
                result = resolve_turn(records)
                self.assertEqual(result["response_mode"], "heartbeat")
                self.assertEqual(result["turn_id"], "current")
                self.assertEqual(result["trigger"]["id"], "wake-current")
                self.assertIsNotNone(result["compacted_at"])

    def test_real_user_during_heartbeat_is_separate_steering(self):
        result = resolve_turn([start(), heartbeat(), compact(), user("pause the audit")])
        self.assertEqual(result["response_mode"], "heartbeat")
        self.assertEqual(result["trigger"]["id"], "wake-current")
        self.assertEqual(result["latest_user_message"]["text"], "pause the audit")

    def test_user_trigger_survives_compaction_and_later_heartbeat(self):
        result = resolve_turn([start(), user("new request"), heartbeat(), compact()])
        self.assertEqual(result["response_mode"], "user")
        self.assertEqual(result["trigger"]["text"], "new request")

    def test_completed_or_interrupted_turn_stays_closed(self):
        for status in ("task_complete", "turn_aborted"):
            result = resolve_turn([start(), user(), row("event_msg", type=status, turn_id="current"), compact()])
            self.assertEqual(result["response_mode"], "stop")

    def test_new_turn_without_trigger_cannot_borrow_the_old_one(self):
        self.assertEqual(resolve_turn([start("old"), user(), start()])["response_mode"], "stop")

    def test_wrong_automation_or_missing_timestamp_is_not_a_valid_wake(self):
        missing = heartbeat()
        missing["payload"]["output"] = "<heartbeat><automation_id>audit-nbn-production</automation_id></heartbeat>"
        for trigger in (heartbeat("other-audit"), missing):
            self.assertEqual(resolve_turn([start(), trigger])["response_mode"], "stop")

    def test_quoted_heartbeat_and_compacted_summary_are_not_triggers(self):
        trigger = heartbeat()
        trigger["payload"]["name"] = "exec_command"
        records = [start(), trigger, compact(heartbeat())]
        self.assertEqual(resolve_turn(records)["response_mode"], "stop")

    def test_user_xml_is_still_user_input(self):
        self.assertEqual(resolve_turn([start(), user(heartbeat()["payload"]["output"])])["response_mode"], "user")

    def test_other_turn_completion_does_not_close_current(self):
        result = resolve_turn([start(), heartbeat(), row("event_msg", type="task_complete", turn_id="other")])
        self.assertEqual(result["response_mode"], "heartbeat")

    def test_last_new_user_message_wins_and_excerpt_is_bounded(self):
        result = resolve_turn([start(), user("old"), user("x" * 1500, "latest")])
        self.assertEqual(result["trigger"]["id"], "message-new")
        self.assertEqual(result["latest_user_message"]["id"], "latest")
        self.assertEqual(len(result["latest_user_message"]["text"]), 1200)
        self.assertTrue(result["latest_user_message"]["text_truncated"])
        self.assertFalse(result["input_complete"])
        self.assertEqual(result["response_mode"], "stop")

    def test_earlier_steering_survives_a_later_status_question(self):
        result = resolve_turn([start(), heartbeat(), user("Do not post comments", "restriction"),
                               user("status?", "question"), compact()])
        self.assertEqual(result["response_mode"], "heartbeat")
        self.assertEqual([m["id"] for m in result["user_messages"]], ["restriction", "question"])
        self.assertEqual(result["user_messages"][0]["text"], "Do not post comments")

    def test_full_input_recovers_restriction_beyond_excerpt(self):
        text = "x" * 1201 + " Do not deploy."
        records = [start(), heartbeat(), user(text, "restriction"), user("status?")]
        clipped = resolve_turn(records)
        self.assertEqual(clipped["response_mode"], "stop")
        full = resolve_turn(records, excerpt_limit=None)
        self.assertTrue(full["input_complete"])
        self.assertEqual(full["response_mode"], "heartbeat")
        self.assertEqual(full["user_messages"][0]["text"], text)

    def test_readonly_snapshot_uses_actual_latest_turn(self):
        records = [row("session_meta", id="thread"), start("old"), user(), start(), heartbeat(), compact()]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            data = b"".join((json.dumps(r) + "\n").encode() for r in records)
            path.write_bytes(data)
            first = resolve_turn(latest_turn_records(path, "thread"))
            self.assertEqual(first, resolve_turn(latest_turn_records(path, "thread")))
            self.assertEqual(first["response_mode"], "heartbeat")
            self.assertEqual(path.read_bytes(), data)
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                latest_turn_records(path, "wrong")
            with self.assertRaisesRegex(ValueError, "bounded tail|complete records"):
                latest_turn_records(path, "thread", max_bytes=100)

    def test_truncated_last_record_stops_instead_of_missing_new_input(self):
        records = [row("session_meta", id="thread"), start(), heartbeat()]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in records) + '{"type":', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete final record"):
                latest_turn_records(path, "thread")


if __name__ == "__main__":
    unittest.main()
