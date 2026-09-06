"""Paid read-only roster probes. No publisher, production database, or Typefully writes.

Run with the owner's existing provider keys. Results/usage use a temporary SQLite database.
"""
import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nbn import config, desk_prep, editor, models, newsroom, research, store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seat", choices=["prep", "writer", "editor", "research", "all"], default="all")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="nbn-roster-smoke-") as folder:
        config.DATA_DIR = Path(folder)
        config.DB_PATH = Path(folder) / "smoke.db"
        con = store.connect()
        def call(seat, model, effort, **kwargs):
            started = time.monotonic()
            response = None
            try:
                response = models.ResponsesClient(model, timeout=100).create(
                    model=model, output_config={"effort": effort}, **kwargs)
                if response.stop_reason in {"refusal", "max_tokens", "invalid_response"}:
                    raise RuntimeError(response.stop_reason)
                return response
            finally:
                store.record_model_usage(con, run_id="roster-smoke", seat=seat, model=model,
                    round_number=1, response=response,
                    latency_ms=int((time.monotonic()-started)*1000),
                    outcome="ok" if response and response.content else "error")
                print(json.dumps(dict(con.execute(
                    "SELECT seat,model,returned_model,effort,estimated_cost_usd,cost_source,"
                    "native_web_calls,native_x_calls,latency_ms FROM model_usage ORDER BY id DESC LIMIT 1"
                ).fetchone())), flush=True)
        seats = ["prep", "writer", "editor", "research"] if args.seat == "all" else [args.seat]
        for seat in seats:
            if seat == "prep":
                card = {"candidate_id": "smoke", "headline_or_post": "Bitcoin Core releases a new version",
                        "summary": "Read-only adapter test. Do not publish.", "source": "Bitcoin Core",
                        "url": "https://bitcoincore.org/en/releases/30.0/"}
                response = call(seat, "gpt-5.6-luna", "low", system=desk_prep.SYSTEM,
                    messages=[{"role": "user", "content": json.dumps({"candidates": [card],
                        "supplied_coverage_keys": [], "supplied_storyline_index": []})}], max_tokens=2000,
                    tools=[desk_prep.TOOL], tool_choice={"type": "tool", "name": desk_prep.TOOL["name"]})
                assert next(b for b in response.content if b.type == "tool_use").input["decisions"][0]["candidate_id"] == "smoke"
            elif seat == "writer":
                first_tool = {"name": "read_smoke_context", "description": "Read the adapter test context.",
                    "strict": True, "input_schema": {"type": "object", "properties": {},
                                                    "additionalProperties": False, "required": []}}
                history = [{"role": "user", "content": "Adapter test only: read context, then submit an empty editorial dossier. No real candidates."}]
                response = call(seat, "grok-4.3", "medium", system=newsroom.NEWSROOM_V2_SYSTEM,
                    messages=history, max_tokens=1000, tools=[first_tool],
                    tool_choice={"type": "tool", "name": "read_smoke_context"})
                block = next(b for b in response.content if b.type == "tool_use")
                history += [{"role": "assistant", "content": [], "_responses_output": response.raw_output},
                            {"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id,
                                                           "content": '{"candidates":[],"test":true}'}]}]
                response = call(seat, "grok-4.3", "medium", system=newsroom.NEWSROOM_V2_SYSTEM,
                    messages=history, max_tokens=2000, tools=[newsroom.V2_DOSSIER_TOOL],
                    tool_choice={"type": "tool", "name": newsroom.V2_DOSSIER_TOOL["name"]})
                assert next(b for b in response.content if b.type == "tool_use").input["stories"] == []
            elif seat == "editor":
                response = call(seat, "grok-4.5", "medium", system=editor.BATCH_EDITOR_PROMPT,
                    messages=[{"role": "user", "content": json.dumps({"candidates": [{
                        "story_id": "smoke", "post": "This is an adapter smoke test, not news.",
                        "inspected_evidence_refs": []}], "evidence_catalog": [],
                        "recent_feed_newest_first": []})}], max_tokens=2000, schema=editor.BATCH_EDITOR_SCHEMA)
                decisions = json.loads("".join(b.text for b in response.content if b.type == "text"))["decisions"]
                assert decisions[0]["story_id"] == "smoke"
            else:
                response = call(seat, "grok-4.3", "medium", system=research.SYSTEM,
                    messages=[{"role": "user", "content": json.dumps({"objective":
                        "Use web search to locate Bitcoin Core 30.0's official release page AND X search for its official announcement. What dates and concrete changes do they support? This is a historical read-only adapter test, not a request to publish."})}],
                    max_tokens=5000, schema=research.SCHEMA, native_tools=True, max_tool_calls=8)
                memo, sources = research.extract_sources(response)
                assert sources, "No provider-cited source findings"
                print(json.dumps({"seat": seat, "sources": [r["url"] for r in sources],
                                  "remaining_gap": memo["remaining_gap"]}), flush=True)
            print(json.dumps({"seat": seat, "status": "passed", "returned_model": response.model,
                              "effort": response.effort}), flush=True)
        print(json.dumps([dict(row) for row in con.execute(
            "SELECT seat,model,returned_model,effort,input_tokens,output_tokens,cache_read_input_tokens,"
            "reasoning_tokens,native_web_calls,native_x_calls,estimated_cost_usd,cost_source,latency_ms FROM model_usage")]), flush=True)
        con.close()


if __name__ == "__main__":
    main()
