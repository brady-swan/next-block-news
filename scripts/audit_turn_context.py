#!/usr/bin/env python3
"""Read-only Codex audit continuation check. No NBN imports, writes or network calls.

The session journal, not the last user message retained by compaction, establishes the
current turn. Unknown/incomplete evidence fails closed. This is a local diagnostic,
not an app-level execution lock or permission grant.
"""

import argparse
import json
import os
from pathlib import Path
import re
import sys
from uuid import UUID


AUTOMATION_ID = "audit-nbn-production"
MAX_TAIL_BYTES = 32 * 1024 * 1024


def latest_turn_records(path, thread_id, max_bytes=MAX_TAIL_BYTES):
    """Read a bounded snapshot, stopping at the latest real task_started record."""
    with Path(path).open("rb") as stream:
        meta = json.loads(stream.readline())
        if meta.get("type") != "session_meta" or meta.get("payload", {}).get("id") != thread_id:
            raise ValueError("session identity mismatch")
        end = stream.seek(0, 2)
        start = max(0, end - max_bytes)
        stream.seek(start)
        tail = stream.read(end - start)
    if start:
        _, separator, tail = tail.partition(b"\n")
        if not separator or not tail:
            raise ValueError("no complete records in bounded tail")
    if not tail.endswith(b"\n"):
        raise ValueError("journal has an incomplete final record; reread before acting")
    records = []
    for line in reversed(tail.splitlines()):
        row = json.loads(line)
        records.append(row)
        if row.get("type") == "event_msg" and row.get("payload", {}).get("type") == "task_started":
            return list(reversed(records))
    raise ValueError("latest turn start is outside the bounded tail; do not infer an old trigger")


def resolve_turn(records, automation_id=AUTOMATION_ID, excerpt_limit=1200):
    """Resolve only actual journal events; never inspect replacement_history/tool prose."""
    result = {"turn_id": None, "status": "unknown", "trigger_kind": "unknown",
              "response_mode": "stop", "trigger": None, "compacted_at": None}
    origin = None
    latest_user = None
    user_messages = []
    for row in records:
        kind, payload = row.get("type"), row.get("payload", {})
        event = payload.get("type")
        if kind == "event_msg" and event == "task_started":
            result = {"turn_id": payload.get("turn_id"), "started_at": row.get("timestamp"),
                      "status": "running", "trigger_kind": "unknown", "response_mode": "stop",
                      "trigger": None, "compacted_at": None}
            origin = latest_user = None
            user_messages = []
        elif result["turn_id"]:
            if kind == "compacted":
                result["compacted_at"] = row.get("timestamp")
            elif kind == "event_msg" and event in {"task_complete", "turn_aborted"}:
                if payload.get("turn_id") == result["turn_id"]:
                    result["status"] = "completed" if event == "task_complete" else "interrupted"
            elif kind == "response_item" and event == "message" and payload.get("role") == "user":
                # The host loads instructions and environment updates in user-role
                # envelopes. They are context, not owner requests. Never filter by prose.
                metadata = payload.get("internal_chat_message_metadata_passthrough") or {}
                kinds = metadata.get("content_item_kinds") if isinstance(metadata, dict) else None
                host_kinds = {"agents_md.instructions", "environments.environment_context"}
                if isinstance(kinds, list) and kinds and all(
                    isinstance(k, str) and k in host_kinds for k in kinds
                ):
                    continue
                text = "\n".join(c.get("text", "") for c in payload.get("content", []))
                if text.strip():
                    latest_user = {"id": payload.get("id"), "at": row.get("timestamp"),
                                   "text": text[:excerpt_limit],
                                   "text_truncated": excerpt_limit is not None and len(text) > excerpt_limit}
                    user_messages.append(latest_user)
                    if origin is None:
                        origin = ("user", latest_user)
            elif (kind == "response_item" and event == "function_call_output"
                  and payload.get("name") == "automation_update"
                  and payload.get("namespace") == "codex_app"):
                output = payload.get("output")
                if isinstance(output, str) and output.lstrip().startswith("<heartbeat>"):
                    ident = re.search(r"<automation_id>([^<]+)</automation_id>", output)
                    stamp = re.search(r"<current_time_iso>([^<]+)</current_time_iso>", output)
                    if ident and stamp:
                        if origin is None:
                            origin = ("heartbeat", {"id": payload.get("id"), "at": row.get("timestamp"),
                                                   "automation_id": ident[1], "scheduled_at": stamp[1]})

    # Preserve why the turn started separately from later user steering. A status
    # question does not itself cancel authorized work. The agent interprets new input.
    if origin and (origin[0] == "user" or origin[1]["automation_id"] == automation_id):
        result.update(trigger_kind=origin[0], trigger=origin[1])
    result["latest_user_message"] = latest_user
    result["user_messages"] = user_messages
    result["input_complete"] = not any(m["text_truncated"] for m in user_messages)
    if result["status"] == "running" and result["trigger"]:
        if result["input_complete"]:
            result["response_mode"] = result["trigger_kind"]
        else:
            result["reason"] = "Current-turn user input is clipped; rerun with --full-input before acting."
    else:
        result["reason"] = "No active verified trigger; do not reopen completed requests."
    return result


def find_session(thread_id, codex_home):
    UUID(thread_id)  # Do not interpolate arbitrary path/query strings into discovery.
    matches = list((Path(codex_home) / "sessions").glob(f"*/*/*/*{thread_id}.jsonl"))
    if len(matches) != 1:
        raise ValueError(f"expected one journal for this task, found {len(matches)}")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--thread-id", default=os.environ.get("CODEX_THREAD_ID"))
    parser.add_argument("--expect-turn", help="Optional saved turn ID; mismatch stops continuation")
    parser.add_argument("--full-input", action="store_true", help="Read complete current-turn user messages")
    args = parser.parse_args()
    try:
        if not args.thread_id:
            raise ValueError("CODEX_THREAD_ID unavailable; provide the verified task ID")
        caller = os.environ.get("CODEX_THREAD_ID")
        if caller and caller != args.thread_id:
            raise ValueError("requested task differs from the calling task; do not adopt another turn")
        path = find_session(args.thread_id, os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
        result = resolve_turn(latest_turn_records(path, args.thread_id),
                              excerpt_limit=None if args.full_input else 1200)
        result.update(thread_id=args.thread_id, journal=str(path))
        if args.expect_turn and args.expect_turn != result["turn_id"]:
            result.update(response_mode="stop", reason="Saved turn differs from the actual latest turn.")
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        result = {"response_mode": "stop", "reason": str(exc)}
    print(json.dumps(result, indent=2))
    return 0 if result["response_mode"] != "stop" else 2


if __name__ == "__main__":
    sys.exit(main())
