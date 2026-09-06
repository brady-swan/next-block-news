# Next Block News prompt inventory

Current 2026-09-06. This is an index, not a duplicated prompt snapshot.
Live editorial orientation: prompts/orientation-brief-v2.md, body after its separator.
The draft v3 brief and tuning examples are not loaded. The wire_voice charter is retained
for legacy paths; its old "source of truth" heading does not make it current v2 authority.

## Active v2 seats

| Seat | Runtime prompt source | Production model / effort | Configuration |
| --- | --- | --- | --- |
| RSS/EDGAR mailroom | nbn/intake_triage.py | Haiku 4.5 / default | NBN_INTAKE_TRIAGE_MODEL, MODE |
| Assignment preparation and storyline selection | nbn/desk_prep.py | GPT-5.6 Luna / low | NBN_DESK_PREP_MODEL, EFFORT, MODE |
| Run-scoped newsroom/writer | nbn/newsroom.py: NEWSROOM_V2_SYSTEM plus loaded orientation and strict tools | Grok 4.3 / medium | NBN_NEWSROOM_MODEL, EFFORT; NBN_EDITORIAL_ENGINE=v2 |
| Optional research assignment | nbn/research.py | Grok 4.3 / medium with native web/X | NBN_RESEARCH_MODEL, EFFORT; compatibility switch NBN_HAIKU_RESEARCH_MODE |
| Independent batch editor | nbn/editor.py: BATCH_EDITOR_PROMPT plus evidence and recent coverage | Grok 4.5 / medium | NBN_EDITOR_MODEL, EFFORT |
| Legacy receipt audit (disabled) | nbn/audit.py: AUDIT_PROMPT, retained only | historical Anthropic NBN_MODEL | NBN_AUDIT_UTC empty |

The separate Codex rolling audit is an app automation governed by AUDIT-AUTONOMY.md, not a
prompt seat in the worker. Runtime values on Desk / System take priority over this dated table.

## What the writer receives

A fresh run-scoped context contains the orientation, run brief, stable candidate cards,
assignment summaries, uninspected reference pointers, prepared inspected receipts, exact-event
coverage/open-draft boards, compact recent-post and continuity indexes, selected NBN-native
storylines, guide attention context and verified-handle spellings. Full indexed context is
retrievable within bounds. X cards additionally preserve long-note, original/quoted-source,
media-pointer and age-stamped metric context; fuller material is behind per-candidate retrieval
IDs. Default optional retrieval is four calls / 48 KiB total, 16 KiB per call; initial desk 64 KiB.
Raw Node envelopes and Node theme metadata do not reach the live
preparation/writer payload.

Guide prose, preparation, storyline cards and search snippets are context, not proof.
Inspected records have code-issued fetch IDs. Direct fetches and citation-bound native
provider-reported extracts retain different provenance; paraphrases are not verbatim captures.
The same writer history may search, fetch, retrieve, delegate once, or submit immediately.
There is no compulsory survey or minimum research phase. A terminal dossier accounts for
each candidate; omitted candidates defer, and a malformed story does not veto the entire batch.

The writer owns research, event grouping, selection and copy. The separate editor judges the
whole usable evidence pool, source sufficiency, novelty, importance and craft. Code owns safe
URLs, structural identity, exact delivery lifecycle, quote support, mention limits, publisher
constraints, investment-instruction and kill-switch rails. Source tier and harmless numerical
differences are not hidden semantic vetoes.

The orientation teaches short, simple sentences, one- or two-sentence paragraphs with blank
lines, consequence-led ledes, and selective detail. NEW: and UPDATE: are optional leading
labels whose use must match event freshness or material development. Historical examples
illustrate craft, not current facts or fixed templates. The current prompt version is
editorial-core-v2.16-lead-context. Plan 0062 aligns mailroom, preparation, writer and editor on
concrete Bitcoin use, demonstrations, access/adoption and substantive culture without demanding
market/protocol impact. It rejects newborn low engagement as a dismissal reason. Standalone
software releases remain out; releases can advance larger ongoing stories. Treasury and writing
rules are unchanged. Media metadata and quoted-source tips are not inspected corroboration.

## Retained legacy paths - not the active v2 funnel

| Source | Purpose |
| --- | --- |
| prompts/wire_voice.md | Legacy charter loaded by brain.py |
| nbn/brain.py: TRIAGE_SYSTEM, CLUSTER_SYSTEM, DRAFT_SYSTEM | Legacy triage, alias clerk, single-post drafting |
| nbn/verify.py: RESOLVE_PROMPT, CLAIM_SUPPORT_PROMPT | Legacy source resolution/support checks |
| nbn/editor.py: EDITOR_PROMPT | Legacy single-post editor |
| nbn/briefing.py: BRIEFING_PROMPT | Disabled opt-in Block builder |
| nbn/newsroom.py legacy run protocol | v1/shadow compatibility, not forced phases in live v2 |

NBN_MODEL controls legacy Anthropic work, not the explicitly configured v2 writer.
Old HAIKU_* settings and haiku_* / sonnet_inventory counter names survive for compatibility;
read the recorded model/provider fields for actual execution.

## Editing discipline

Edit runtime sources, not this index. Do not modify runtime prompts merely to modernize
historical model names. Policy changes require owner approval; the rolling audit may make
bounded writing-execution improvements under its explicit scope. Test prompt-bound invariants,
bump the version when behavior changes, deploy deliberately and inspect actual output.
