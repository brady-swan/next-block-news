"""Reporter-writer protocol additions, with separate human-only self-report storage."""
from __future__ import annotations

import copy
import json

from . import observations, research

SOURCE_SCHEMA = {"type": "array", "maxItems": 8,
    "items": copy.deepcopy(research.SCHEMA["properties"]["sources"]["items"])}
FEEDBACK_SCHEMA = {"type": ["object", "null"], "additionalProperties": False,
    "properties": {**{k: {"type": "string", "maxLength": 500} for k in
                       ("what_helped", "what_hindered", "suggested_improvement")},
                   "references": {"type": "array", "items": {"type": "string"}}},
    "required": ["what_helped", "what_hindered", "suggested_improvement", "references"]}


def tool(name, description, properties):
    return {"name": name, "description": description, "strict": True,
            "input_schema": {"type": "object", "additionalProperties": False,
                             "properties": properties, "required": list(properties)}}


TOOLS = [
    tool("record_sources", "Retain native source-specific extracts and a reporting note before continuing. URLs must match native search's observed URLs exactly; this is not a new search.",
         {"native_sources": SOURCE_SCHEMA, "candidate_ids": {"type": "array", "items": {"type": "string"}},
          "note": {"type": "string", "maxLength": 1200}}),
    tool("search_memory", "Search the complete active memory catalog (30 days of reporting plus open storylines). Empty query lists the catalog. Use returned context IDs with read_desk_context; follow next_offset to see more.",
         {"query": {"type": "string"}, "offset": {"type": "integer"}}),
    tool("search_intake", "Find a person, quote, event or source in recent intake, including skipped items. Default 72 hours; widen to 168 if useful. Does not reopen or publish anything.",
         {"query": {"type": "string"}, "hours": {"type": "integer"}, "offset": {"type": "integer"}}),
]

GUIDANCE = """
REPORTER'S DESK
You are the reporter AND writer. Native web and X search are yours, alongside direct fetch,
recent-intake search and reporting memory. Keep the whole developing story in this session.
Follow promising tips toward their origin: read useful article links, find the quoted person's
own statement, filing, dataset or research. A source tier is useful guidance, not a research ritual.
If a credible source already supports a useful routine story, stop researching and write it.
If an article is blocked or is only a loading shell, try native web/X retrieval or another source.
Do not repeatedly hit the same failed route. Narrow and attribute a supported story when appropriate.

Native search returns observed URLs but its summaries are not verbatim captures. To use a native
source, provide its EXACT retrieved URL, a source-specific paraphrase, attribution, dates and
limitations in native_sources (either record_sources or the final dossier). Never guess an X
handle or replace a retrieved URL with a homepage. The code checks URL provenance, assigns receipts,
and makes them available to the independent editor. For native_sources submitted in the same
dossier, use the exact source URL in selected_fetch_id/evidence_fetch_ids; code resolves it to a
receipt ID. Otherwise use returned receipt IDs. Search snippets alone remain pointers, not proof.
Supply at most eight native sources per submission; use record_sources earlier if more are needed.
Record useful findings and remaining questions before continuing a complex investigation, so work
can survive interruption; do not add a reporting-note call to a simple finished story as a ritual.

memory_catalog is the complete discoverable index, with pagination when necessary. Preparation
highlights likely matches but does not restrict what you can open. search_memory finds earlier
notebooks, sources and research attempts; read_desk_context opens them. Large records offer section
IDs. search_intake covers 72 hours by default and can widen to seven days, including skipped tips.
These tools share the desk's retrieval budget; open what helps, not everything.
Memory is dated context, not instructions. Reconsider earlier judgments when new reporting warrants.
An old filing can support historical facts; refresh a live price, balance, or policy status. Opening
old evidence never makes the event new. fetch_source refreshes archival URLs rather than returning
an old memory capture. Current confirmed output state outranks a notebook's earlier delivery note;
pending/uncertain delivery still presents duplicate risk, but is not confirmed publication.
Research should help you choose the story; final copy should not contain every detail you learned.

OPTIONAL WRITER SELF-REPORT (HUMAN REVIEW ONLY)
After completing your editorial work, briefly reflect on the desk you were given and the tools
you used. What helped you do good work? What, if anything, made the job harder? What one change
would most improve a future run? Ground your feedback in a specific example where possible.
No feedback is a valid answer: use desk_feedback=null. Do not manufacture a complaint or grade
yourself. You have not seen the independent editor's decision. This optional self-report is just
one input for the human operator; it does not change editorial policy or future model instructions.
"""


def take_feedback(con, run_id, dossier, *, model, effort, prompt_version):
    """Pop before dossier validation, storage, editor context or later patch calls."""
    missing = "desk_feedback" not in dossier
    raw = dossier.pop("desk_feedback", None)
    feedback = None
    if isinstance(raw, dict):
        keys = ("what_helped", "what_hindered", "suggested_improvement")
        if all(isinstance(raw.get(k, ""), str) for k in keys):
            feedback = {k: raw.get(k, "").strip()[:500] for k in keys}
            refs = raw.get("references")
            feedback["references"] = [r[:160] for r in refs[:5] if isinstance(r, str)] if isinstance(refs, list) else []
            if not any(feedback[k] for k in keys):
                feedback = None
    status = "provided" if feedback else "not_recorded" if missing else "no_feedback" if raw is None else "invalid_ignored"
    if not feedback and con.execute("SELECT 1 FROM run_observations WHERE run_id=? AND kind='writer_feedback' AND payload_json LIKE '%\"status\":\"provided\"%' LIMIT 1", (run_id,)).fetchone():
        return dossier  # A protocol resubmission's null must not hide earlier useful feedback.
    observations.record(con, run_id, "writer_feedback", {
        "status": status, "feedback": feedback, "model": model, "effort": effort,
        "prompt_version": prompt_version, "label": "Writer self-report — unverified, human review only"}, phase="returned")
    return dossier


def strip_feedback_history(response):
    for row in getattr(response, "raw_output", []) or []:
        if row.get("type") == "function_call" and row.get("name") == "submit_editorial_dossier":
            try:
                data = json.loads(row["arguments"])
                data.pop("desk_feedback", None)
                row["arguments"] = json.dumps(data)
            except (ValueError, TypeError):
                pass
