# Next Block News prompt inventory

Current 2026-09-08, Plan 0070. This is an index, not a duplicated prompt snapshot.
Live editorial orientation: prompts/orientation-brief-v2.md, body after its separator.
The draft v3 brief and tuning examples are not loaded. The wire_voice charter is retained
for legacy paths; its old "source of truth" heading does not make it current v2 authority.

## Active v2 seats

| Seat | Runtime prompt source | Production model / effort | Configuration |
| --- | --- | --- | --- |
| RSS/EDGAR mailroom | nbn/intake_triage.py | Haiku 4.5 / default | NBN_INTAKE_TRIAGE_MODEL, MODE |
| Assignment preparation and storyline selection | nbn/desk_prep.py | GPT-5.6 Luna / low | NBN_DESK_PREP_MODEL, EFFORT, MODE |
| Run-scoped newsroom/writer | nbn/newsroom.py: NEWSROOM_V2_SYSTEM plus loaded orientation and strict tools | Grok 4.3 / medium | NBN_NEWSROOM_MODEL, EFFORT; NBN_EDITORIAL_ENGINE=v2 |
| Native reporting (same writer context) | nbn/reporter.py plus newsroom tools | Grok 4.3 / medium | NBN_REPORTER_WRITER_ENABLED; compatibility research switch NBN_HAIKU_RESEARCH_MODE |
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
Under packet pressure, prepared-receipt sidecars move behind context IDs before candidate
summaries are reduced. Explicit byte-bounded evidence excerpts retain provenance and a link to
the full capture. Compact cards preserve candidate correction/retry/owner/visual hints and all
in-scope open-draft keys/ledes. An irreducible overflow is measured, not disguised as a handoff.
Raw Node envelopes and Node theme metadata do not reach the live
preparation/writer payload.

Guide prose, preparation, storyline cards and search snippets are context, not proof.
Inspected records have code-issued fetch IDs. Direct fetches and citation-bound native
provider-reported extracts retain different provenance; paraphrases are not verbatim captures.
The same writer history may use native web/X, search/fetch, search earlier intake, open the
active memory catalog, record useful findings, or submit immediately. No separate reporting
model call is needed. The retained `nbn/research.py` helper validates observed native URLs.
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
editorial-core-v2.25-compact-desk. Plan 0069 changes packet assembly and clarifies that context
lookup can open current receipt/candidate details as well as history; editorial guidance is unchanged.
The dossier field descriptions distinguish the selected
reader link from the complete story-specific evidence sent to the editor. Retaining native
extracts alone or describing them in a reporting note does not attach them to a story; the
writer cites their exact URLs in the same dossier. A small optional unassigned research appendix
lets the editor explicitly select already-inspected current-run excerpts omitted by the writer.
It is not automatic support or another research turn. The exact delivered excerpts and provenance
follow selected refs into final rails and memory; malformed refs use existing omitted-only recovery.
The editor can choose the reader-facing source with optional reader_receipt_ref from that story's
inspected evidence or explicitly selected appendix evidence; null preserves the writer source.
Text-only schemas omit visual fields; visual/mixed schemas require an explicit visual decision.
Malformed received JSON also gets the existing one bounded recovery, with field-specific errors.
Transport failures and refusals do not gain a new retry. Later identity failures surface in
candidate retry memory. One side-effect-free identity correction shares the existing receipt
repair allowance; valid siblings are frozen and no additional research loop is opened.
Writer and editor preserve each statistic's category, unit
and reporting period when focusing a story on Bitcoin; all-digital-asset totals are not
Bitcoin-only totals. This is a wording/accuracy clarification, not an extra search requirement
or exact-number gate. The existing fetch tool supports bounded text-based PDF reading. Page/text caps,
no OCR and incomplete-extraction warnings remain explicit in receipts and reused memory.
Plan 0063 adds source-following and dated memory guidance,
plus optional human-only writer feedback. Null feedback is valid; it is stripped before editor
or future model context. Plan 0062 aligns mailroom, preparation, writer and editor on
concrete Bitcoin use, demonstrations, access/adoption and substantive culture without demanding
market/protocol impact. It rejects newborn low engagement as a dismissal reason. Standalone
software releases remain out; releases can advance larger ongoing stories. Treasury and writing
rules are unchanged. Media metadata and quoted-source tips are not inspected corroboration.

Plan 0066 appends `nbn/visual_tools.py:GUIDANCE` to the hashed newsroom system prompt and adds
optional list/inspect/render/PDF-page tools. The dossier selects an inspected immutable asset;
the editor sees its exact pixels, evidence, alt text and reuse basis and must explicitly
approve/omit/hold it. No new mandatory turn or model seat is added. The loaded editorial
orientation itself was unchanged in 0066. Plan 0068 adds the owner-approved selection,
later-outcome and date guidance; visual guidance adds relevant image pointers, valid chart
examples and the at-a-glance comprehension/potential-reach rationale. Source quotes remain exact; rendered data remains subject
to editorial support/units/period checks. Text-only is normal, not a failed visual quota.

Plan 0070 uses editorial-core-v2.29-visual-evidence. The strict story dossier includes bounded
visual_evidence_ids; writer/editor guidance separates evidence inspection from attachment and
reuse permission. Image-only words do not become direct-text quotation receipts. Guidance also
teaches separate inspection/render allowances, explicit calendar versus category line charts,
source/date/unit qualifications, no added internal fixture labels, and larger excerpt type within
the approved margins. See docs/planning/visual-style-2026-09-08.md. The combined release includes
the separately reviewed v2.28 appendix-reference schema repair: only IDs in the request's actual
appendix are valid, and an absent appendix permits an empty array only. No extra model call,
new model, effort change or larger shared budget is introduced.

Plan 0064 clarifies original-statement lookup, exact prior facts versus new developments,
matching periods/transaction direction, and practical Bitcoin/monetary scope. Preparation uses
assignment-desk-v2.6-related-outcomes now supersedes v2.5: useful later evidence can advance
without having to justify a second standalone post. The loaded orientation distinguishes consequential
legislative viability/timing/scope statements from generic political advocacy. A short run
assignment reinforces these priorities where decisions are made. No lookup is mandated for
every lead, and no primary-only standard or publication quota is added.

Each story may carry a nullable reporting_note (800 characters), distinct from optional human-only
desk_feedback. The former reaches the editor and notebook as untrusted reporting context; the
latter remains excluded. The editor sees the story's referenced inspected evidence plus the bounded
unassigned appendix, with source provenance preserved even for equal wording. Plain completion without native work now
forces a dossier next; early closure can still repair receipt references once without research.

Plan 0065 reinforces original-disclosure timing versus guide-to-draft speed, reader takeaways
instead of measurement inventories, and preserving useful context/warnings when replacing an open
draft. Statistic populations stay intact (blocks versus outputs; expectations versus actual inflation).
Current memory caveats are not retroactive editor approval or evidence. These are judgment/craft
instructions, not freshness gates, precision vetoes, quotas or a new research ritual.

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
bounded writing/reporting-execution improvements under its explicit scope, including clearer use
of useful existing or newly added tools without redefining editorial policy. Test prompt-bound invariants,
bump the version when behavior changes, deploy deliberately and inspect actual output.
