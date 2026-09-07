# Plan 0063 — an integrated reporter-writer with a usable reporting notebook

Status: owner approved implementation, independent review, deployment, and smoke checks,
including optional writer feedback visible in the Desk. Independent lead approved the plan
and implementation. Runtime `68a7b36` is deployed; clean-release tests and HTTP/runtime
smokes pass. Release evidence and replay limitations: `SPRINT-0063-FINDINGS.md`.

Prepared September 6, 2026 Central / September 7 UTC. This gathers the owner's discussion
of research/writing integration, working budgets, source following, research retention,
memory quality, and an injected index of available memory artifacts.

## Sprint at a glance

1. Give Grok 4.3 medium native web/X research in its existing writing conversation.
2. Start with six responses and six minutes, with shared tool accounting and room to finish.
3. Preserve source links and add local lookup of earlier intake, including skipped originals.
4. Save useful research as it happens; make 30-day reporting notebooks accurate and reusable.
5. Inject the active memory catalog; let the writer open records beyond Luna's suggestions.
6. Show research, memory use, and honest combined costs in the existing Desk and rolling audit.
7. Record optional end-of-task writer feedback and expose it per run and in a rolling Desk view.
8. Independently review, replay known successes/failures, test, deploy, smoke, and restore audit.

## Outcome

Give the existing Grok newsroom the tools and continuity to follow a promising tip to its
best available source and write a useful, concise post. Research and writing happen in the
same run-scoped conversation. A separate editor still reviews the proposal and evidence.

The writer starts with a clean desk, a compact catalog of available reporting memory, and
a few relevant notebooks already open. It can open other records or search earlier intake
without depending on preparation to have anticipated every connection. Useful reporting
survives an unfinished draft or an interrupted run.

This is an extension and simplification of the existing newsroom, evidence workspace,
event workbench, and storyline ledger. It is not another ingestion platform, a new general
knowledge graph, an immortal conversation, or an additional recurring model seat.

## Why this sprint

- Research was delegated to save expensive Sonnet context while Haiku investigated. The
  roster migration intentionally preserved that architecture. Both seats are now Grok 4.3
  medium; the handoff remains even though the original model-price advantage is gone.
- In the 7.18-hour sample ending September 7 at 03:40 UTC, 26 writer sessions made no native
  research assignments. Sixteen made no discretionary research/context call. This does not
  mean every such run needed research; it does show that native research is not a normal
  reporting route. Earlier routing-prompt replays also failed to induce its use.
- The writer currently has three successful responses including final submission. A search,
  then article fetch, can consume the opportunities to follow that article to its source.
- Article extraction removes citation hyperlinks. The writer cannot search arbitrary earlier
  intake, including skipped original statements. Lummis's original post was captured hours
  before a later draft cited The Block repeating it.
- Across 32 runs with detailed writer packets, September 6 19:04 through September 7 04:02 UTC,
  14 received storyline cards, seven storyline updates were proposed, and two Liquid proposals
  cited saved evidence. There were no explicit historical-memory reads; the one context read
  opened a current X lead. Some memory is supplied directly, so lookup count alone is not a
  measure of effectiveness.
- Production held 49 active event-memory records, but selected 12 by state/recency before
  assessing current relevance. The writer's catalog therefore hid potentially useful records.
- Liquid's authoritative output was published while its notebook still described a draft and
  surfaced an earlier resolved handle issue. Expanding access without fixing this would expose
  more misleading context.

Evidence: `RESEARCH-FLOW-ASSESSMENT-2026-09-07.md`, `SPRINT-0059-FINDINGS.md`,
`ROSTER-REPLAY-FINDINGS-2026-09-05.md`, and the recorded production handoffs. This plan
supersedes the assessment's delegation-first recommendation, not its dated observations.

## Scope and unchanged boundaries

Keep Haiku intake, Luna low preparation, Grok 4.3 medium newsroom, and Grok 4.5 medium editor.
Keep the existing cadence/priority behavior, source registry, guide attention, Bitcoin scope,
treasury-company bar, owner overrides, concise writing style, and source-in-first-reply format.
No new source-count requirement, primary-only publication gate, mandatory search per lead,
minimum research-turn count, or target number of posts.

Autopost stays OFF. Normal automatic draft delivery remains the existing production behavior;
this sprint does not authorize manual publication, dismissal, rewriting of Typefully drafts,
ambiguous publisher recovery, credential changes, or destructive database operations. Exact
event/output identity, confirmed publication, owner edits, and existing delivery safeguards
remain authoritative. Storyline membership and notebook state never become publication gates.

No Marketing Node or Perception work, polling-frequency change, new worker, new external
search vendor, vector database, memory-maintenance model, general browser/screenshot service,
or automatic media acquisition. Preserve existing useful fetch/search adapters and historical
records; remove the normal delegation boundary without a broad legacy-code cleanup.

## Target workflow and ownership

1. Existing intake and Luna preparation supply the current leads and suggested connections.
2. Code assembles a compact memory catalog, authoritative coverage/open-draft state, relevant
   notebook summaries, source pointers, and already-inspected evidence.
3. Grok evaluates worthwhile leads, opens prior work, searches web/X, follows source links,
   and writes in the same conversation. It may finish immediately when supplied evidence is
   enough. Luna's selections are recommendations, not the limit of discoverable memory.
4. Code records retrieved artifacts as work happens. The writer contributes concise findings
   and remaining questions; source material, editorial interpretations, and operational state
   remain distinguishable.
5. The independent editor receives the proposed copy and its actual source-specific evidence.
6. Existing delivery/reconciliation updates authoritative output state. Later notebooks and
   catalog entries derive current publication status from those records.

## Phase 0 — review, baseline, and provider contract

After owner approval, run the established independent lead-coder plan review. Resolve concrete
correctness, scope, and test gaps until there is agreement. The implementing agent owns the
final call and prevents an open-ended hardening/review spiral. No parallel implementation
before approval. Pause the existing rolling audit only when building begins; retain its saved
prompt, schedule, notification policy, and autonomy scope for restoration.

Capture the deployed revision, effective budgets, autopost state, recent source-to-draft times,
normal model costs, memory catalog size, and representative source/memory failures. Distinguish
recorded fact, audit judgment, missing telemetry, and owner feedback.

Verify the current xAI contract with a small isolated, metered test: native web/X tools mixed
with custom functions, conversation continuation, source metadata, and final structured dossier
submission. Official reference: https://docs.x.ai/developers/tools/advanced-usage.

The current adapter overwrites custom tools when native tools are enabled. Fix the integration,
not just a configuration flag. Demonstrate the exact deployed model/effort combination; do not
assume a documentation example using another model proves our contract.

## Phase 1 — make source following practical

### Same-context native research

- Expose native web and X search alongside ordinary search, safe direct fetch, context access,
  archive lookup, and dossier submission. Retire `assign_research` from the normal writer tool
  menu. Reuse the native-source parsing and usage-accounting helpers rather than duplicate them.
- Preserve provider conversation state across turns. Handle a native-search result that has not
  yet called a client function or submitted a dossier without silently losing the research or
  accepting it as final output. Maintain explicit finalization and incomplete/refusal handling.
- Register useful native sources in the existing evidence workspace before dossier validation,
  including sources first returned in the same response as a dossier. Resolve observed source
  references to code-issued receipts; do not ask the writer to invent IDs. The contract test
  must establish what citation/source metadata is actually available with function outputs.
- One bounded in-session reference repair may correct a dossier that uses uninspected or
  unknown source IDs. Return actual accepted receipts and distinguish unattested pointers;
  use the existing response/tool/deadline budgets. Never auto-select a source or retry editorial
  judgment. If repair fails, per-story validation preserves supported work and defers the rest.
- Retain exact observed URLs, attribution, dates, source-specific findings, and limitations.
  Direct page text and provider-reported paraphrases remain visibly different. A discovered
  URL alone proves neither that its contents were read nor that it supports a claim. Never turn
  the model's general answer into a source, or several echoes of one report into independent
  corroboration. Quotes still need actual verbatim support.
- Do not force another model call solely to write a research handoff. Persist normalized tool
  results in code and allow concise reporting notes with the existing final submission. Keep
  the separate editor; do not add an editor research/delegation loop in this sprint.

### Better source material

Return bounded readable article text with useful citation anchors and their real destinations,
canonical URL, available author/publication metadata, and truncation/content limitations. Resolve
relative links against the final page URL. Exclude obvious navigation noise; retain the links
needed to follow a statement, filing, study, or dataset. Preserve X main/quoted-post boundaries,
real links, and available context. Do not invent missing transaction IDs, author handles, or URLs.

Distinguish a successful HTTP response from useful retrieved content. Empty chart/explorer shells
must be reported as insufficient content, with another retrieval route available. Native retrieval
can remain useful when local fetch is blocked; do not require a second successful local fetch to
erase that benefit. Retain existing public-URL protections and specific useful adapters such as
FRED CSV. Media metadata remains a pointer, not proof of visual inspection.

## Phase 2 — a shared reporting notebook that survives the run

### Extend existing records; do not create a competing source of truth

Use the event workbench for story-level reporting state and the storyline ledger for broader
continuity. Add only the small artifact/association storage needed to save useful research before
a canonical event or final dossier exists. Associate artifacts with actual candidate IDs and run
IDs first, then with validated event identity when known. A source may support more than one event.
Do not create speculative canonical aliases merely to give a research note somewhere to live.

Each notebook exposes:

- the question under investigation and the current concise findings;
- source artifact references, supporting material, attribution, and relevant timestamps;
- important conflicts, limitations, failed approaches, and useful next steps;
- prior proposals and editor feedback, with historical versus current issues distinguished;
- current output state derived from authoritative publication/draft records;
- what genuinely new information could warrant revisiting the event.

Code saves normalized retrieved artifacts when tools return, not only after a valid dossier.
Persist recoverable partial work on timeout, malformed final output, or restart without marking
the item handled or covered. Where the provider never returns a result, report that gap rather
than claiming to have saved unseen research. Repeated saves are idempotent; retain retrieval
provenance and original observation dates. Native and ordinary research use the same notebook.

Writer notes are short operational summaries, not transcripts, hidden reasoning, or self-issued
instructions. Useful notes may exist even when no story is proposed. Update only records the
writer actually opened; preserve the current storyline revision checks and apply equivalent
stale-write protection where needed. Source records and decisions remain available beneath a
summary so a later writer can disagree with it.

### Fix stale state before exposing a larger catalog

Derive scheduled/published/draft status from current output and reconciliation records rather
than trusting an old notebook snapshot. IMMEDIATE or UNCERTAIN mode alone is not confirmed
publication. Recheck the normal delivery guards if the owner publishes while a run is working.

Do not resurrect the last nonempty historical failure as the current research objective after
later work resolved it. Preserve the failure in history, but clear or supersede its active status.
A completed drop need not remain an urgent unfinished assignment. A prior skip is advisory;
new facts can justify a different decision without rewriting the earlier record.

### Retrieval windows and freshness

| Material | Proposed behavior |
| --- | --- |
| Recent intake, including skips | Search 72 hours by default; explicitly widen to seven days. Return a few relevant records, not the whole window. |
| Reporting notebooks and useful source artifacts | Searchable for 30 days after meaningful reporting activity; ordinary reads/retries do not renew freshness. |
| Current open notebooks | Prioritize relevant active work, unresolved questions, and current editor feedback. Older work remains discoverable within the archive window. |
| Storylines and publication records | Preserve durable history beyond those windows; show current lifecycle and dated signals. |
| Detailed run observations | Keep the existing 14-day rich audit history; it is not the only storage for reusable 30-day research. |

These are retrieval/working-set policies, not permission to delete existing records or make old
leads fresh. Preserve original event/publication time, first seen, fetched time, and notebook
updated time separately. Loading, rereading, or summarizing a source does not reset its clock.

Replace the blanket 24-hour exclusion of reusable evidence with explicit age and context.
A stored filing can support a historical statement after a day; an old balance, price, or live
status cannot establish the current value. Let the writer decide when the proposed claim needs
a fresh check, with the dates and limitations visible to the editor. Retain integrity/URL checks.
An older source's availability must not bypass the existing editorial judgment about freshness.

## Phase 3 — an injected index with selective retrieval

### Catalog, open notebooks, and archive

Give the writer a compact table of contents for the active reporting notebooks and storylines,
not merely the 12 events or Luna-selected lines chosen upstream. An entry contains a stable
retrieval ID, readable title, type, last meaningful update, contents available, authoritative
output status where linked, and a short unresolved-question summary when applicable.

The catalog describes notebook contents; individual documents are listed inside their notebook.
At the observed size, all 49 active event records and five storylines should be discoverable in
the compact catalog. Relevant records may be highlighted and a few useful summaries opened
automatically. Match current candidates against the available memory before limiting full cards.
Luna still helps select likely connections in its existing pass, but its choices are not an
access gate. Looking at an index entry alone does not authorize rewriting that notebook.

Consolidate duplicated current indexes rather than appending another large board. Retain the
64 KiB initial packet ceiling. Measure catalog size on actual packets; shorten descriptions and
move full bodies behind retrieval before sacrificing candidate identity or source provenance.
When growth requires pagination, return explicit total/shown counts and an accessible continuation.
Never label a silently filtered subset as the complete inventory.

Extend the existing bounded context tool to open notebook summaries and specific artifact
sections by stable ID, including multiple IDs in one call. An oversized notebook must return a
useful section and explicit continuation/truncation, not an empty successful response. Artifact
IDs remain resolvable across runs; immutable source versions and mutable notebook revisions are
distinguished. Opening stored evidence registers its proper run-local receipt without implying
a new network fetch.

Add bounded local search across intake and reporting memory by person, quote, topic, source, and
known event. Return exact stored records, real dates, prior decisions, and IDs for deeper reading.
Use SQLite retrieval, not a new model or embedding service. Every hit is context to assess, not
an automatic event merge or reopening of a skipped item. Exclude evaluation/replay-only material
from normal reporting memory and publication history. Empty results and missing history stay explicit.

## Phase 4 — writer guidance and working budgets

Put tool use and notebook workflow in `NEWSROOM_V2_SYSTEM` and tool descriptions, with the
minimum necessary matching preparation/editor clarification. Do not duplicate a large new
instruction manual in every layer. Preserve the approved orientation and craft guidance except
for a reviewed conflict that actually needs correction; document the exact prompt diff.

Proposed core direction:

> Treat incoming posts as leads. For a worthwhile story, follow the claim toward its origin:
> the speaker, announcement, filing, study, data release, or original reporting. Use the best
> available source and write what it actually establishes. Stop when you have enough for a
> useful, accurately attributed post.

> Consult the notebook index for relevant prior work. Reuse what answers the question, check
> what needs updating, and investigate what remains. Earlier judgments are context, not binding
> verdicts; being tracked in a storyline is not the same as having been published.

Remove obsolete delegation/one-response pressure. An adequate supplied source can still go
straight to writing. A credible original report can itself be the best source; an official
document is not compulsory. A source's reputation, whether it originated the claim, and what
this particular artifact establishes are separate questions. A person's own statement proves
what they said, not that their prediction is true. Prefer a focused useful question over an
expansive research assignment. Preserve the current treatment of consequential claims.

Before submission, keep the compression pass: consequence-led lede, one main job per sentence,
no adjacent clause-heavy sentences, and "Use single sentences or two-sentence short paragraphs
with blank lines between each." More research is not a reason to write longer posts. Do not
turn a news story into a dense research memo, trading take, or generic macro statistics update.

| Budget | Current production | Proposed starting point |
| --- | --- | --- |
| Successful writer responses, including final dossier | 3 | 6 |
| Newsroom elapsed-time envelope | 240 seconds | 360 seconds |
| Requested native research allowance | 8 within one delegated assignment | 12 accounted across the combined run |
| Shared retrieval/tool-operation allowance | 24 | Keep 24; account for native activity rather than stacking budgets |
| Initial writer packet | 64 KiB | Keep 64 KiB |
| On-demand context reads | 4 calls; 16 KiB/call; 48 KiB total | Keep initially; batch IDs and support bounded sections |
| Direct source retrieval | 16 fetches; 8,000 characters/page; 160,000 total | Keep initially |
| Writer output-token ceiling | 16,000 per response | Keep initially |

Ceilings are not targets. Preserve a final response and sufficient elapsed time to finish;
stop opening research paths before the deadline. A difficult lead must not prevent supported
stories from being submitted. Carry its specific unfinished work into the next run instead.
Do not create a new streaming-publication or concurrent-worker architecture to achieve this.

Apply the elapsed deadline to preparation/prefetch/research in the existing newsroom lifecycle;
bound individual calls by remaining time. The editor keeps its separate existing bound. Check
the actual xAI control semantics: a per-request turn limit is not necessarily a strict cap on
billable searches. Track real reported usage, pass remaining allowances, and do not reset the
budget on each follow-up request. No claim of an exact dollar ceiling. Update model-call
reservations for the active path so a retired researcher does not reserve extra calls.

The single worker cannot poll intake while doing long model work. Measure added intake lag and
total run time, including editing, rather than treating six minutes as a free latency increase.
Do not conceal a regression by relaxing health thresholds or changing cadence in this sprint.

## Phase 5 — Desk, cost reporting, and audit

### Writer feedback: an input for human judgment, nothing more

Add an optional bounded `desk_feedback` object to the final writer dossier, with short fields
for what helped, what made the work harder, and one suggested improvement; allow a small list
of candidate/tool/artifact references. Null or omission means no feedback. Malformed optional
feedback is discarded independently and must not reject a valid editorial dossier. There is
no additional writer turn, mandatory complaint, automatic score, or required follow-up call.

Prompt: "After completing your editorial work, briefly reflect on the desk you were given and
the tools you used. What helped you do good work? What, if anything, made the job harder?
What one change would most improve a future run? Ground your feedback in a specific example
where possible. No feedback is a valid answer."

Persist feedback with the run, model/effort, prompt version, and timestamp, separately from
story notebooks and source evidence. It does not enter subsequent writer/preparation/editor
prompts or alter routing, policy, priorities, budgets, or configuration. The writer has not yet
seen the editor/publication outcome; label it as a writer self-report, not a verified diagnosis.
Occasional deeper debriefs may be run separately when requested, not automatically each run.

The Desk shows "Writer feedback" on the originating run and a paginated recent-feedback panel
in System, linking back to the actual run/research trace. Preserve the existing visual language,
use short readable sections, and distinguish no feedback, not recorded, and expired history.
Keep the observation retention period explicit. No "apply suggestion" action, autonomous
improvement loop, or new review workflow. Audit may compare the suggestions with recorded
evidence under its existing authority; the owner and maintainer decide what merits action.

Tests must prove null/malformed feedback cannot lose a story, older runs render honestly,
feedback stays out of memory and subsequent model payloads, and browser text is safely escaped.

### Existing research, memory, and cost views

Extend the existing run-first workspace, without another redesign:

- Show the catalog and relevant notebooks actually delivered to that run, records the writer
  subsequently opened, and the sources/findings it used. Preserve historical snapshots; a
  current notebook must not silently replace what an older writer actually saw.
- Show recorded native and ordinary research activity, source trails, selected receipts,
  useful fallbacks, and unresolved questions. Distinguish "not sought," "attempted but unavailable,"
  "found," and "already in intake/memory." Surface provider visibility gaps honestly; do not
  claim to expose hidden reasoning or every internal browsing step.
- Show model roster as one Grok 4.3 medium newsroom with research tools, plus the independent
  Grok 4.5 medium editor. Historical runs retain their actual separate research seat.
- Report combined "Newsroom: research + writing" cost, actual native web/X usage, and a tool-cost
  breakdown only where provider data supports it. Shared-context tokens cannot be honestly
  partitioned into exact research versus writing spend. Do not double-count native tool charges
  already included in provider totals. Preserve unknown-cost and replay exclusions.

Audit source quality, claim scope, event freshness, writing quality, memory retrieval relevance,
stale/superseded notes, original-source recovery, avoided repeat research, and actual publication
awareness. A supplied/opened notebook, successful fetch, or large tool count is not proof of a
better outcome. A useful answer already on the desk does not require another lookup.

Compare ordinary and research-heavy runs separately: source-to-intake, intake-to-draft,
human publication delay, cost/run, and cost/useful draft with the judgment labeled. Track context
size, limit hits, native failures, loop/retry behavior, and source polling lag. Memory must not
become a permanent veto on an event or convert a broad storyline into exact-event coverage.

## Verification and acceptance

Run isolated, metered replays with no publisher side effects. Store outputs and an analysis
report locally. Set an initial $10 ceiling for the live contract checks and targeted baseline/
candidate replays combined; stop and report if it is reached, rather than expanding into another
model bake-off. Offline tests do not spend model credits. The owner's earlier Typefully replay
requests are not standing
permission to export this new test set; ask only if review there becomes useful.

| Case | Required demonstration |
| --- | --- |
| Lummis original versus The Block restatement | Find the earlier skipped original, retain its actual time, and cite it when it is the appropriate receipt. |
| Article citing an announcement/filing | Preserve and follow the real anchor; do not guess the URL. |
| Liquid reporting and published-state continuity | Reuse inspected work; find the original statement; distinguish a new development from a rewrite; notebook agrees with current output state. |
| Blocked local page with native evidence | Same writer can continue through native web/X and deliver source-specific evidence to the editor without a delegate. |
| Already-sufficient primary source and obvious non-news | No compulsory search, memory lookup, or extra model round. |
| Old filing versus old live balance/price | Historical support remains usable; current-value claims receive an appropriate refresh or are narrowed/dropped. Old evidence does not become fresh news. |
| Relevant memory beyond the old 12-record cut and a Luna-missed storyline | Writer can discover and open both through the catalog/search. |
| Oversized notebook and catalog overflow | Useful bounded sections and explicit pagination; no invisible truncation or unresolvable listed ID. |
| Interrupted research, malformed dossier, and restart | Returned artifacts survive and can be found next run without falsely handling/publishing the candidate. |
| Resolved failure and stale delivery note | Historical issue remains inspectable but no longer appears active; confirmed publication wins. |
| Mixed batch with a difficult lead | Finish supported proposals within bounds and retain unresolved work; do not spend the whole run repeatedly failing one lookup. |
| Memory that contains a previous wrong judgment | Reconsider on new evidence; do not cite a model summary as source or treat tracked as published. |

Add focused offline tests for mixed native/custom Responses turns, same-response source capture
and dossier validation, incomplete output, missing citation metadata, author/URL preservation,
native accounting, aggregate budgets, finalization, and safe partial persistence. Test the
real worker restart boundary, memory revision/identity isolation, source dates, archive filters,
read-only GETs, owner overrides, editor handoffs, and publication races.

Run the full Python 3.12 suite and the Desk type/build/polling checks. Repeat from a clean archive
of only the intended release. Do not bundle preexisting uncommitted evaluation or tuning work.
The independent lead reviews the focused implementation and replay findings before release.

Acceptance requires actual use of native tools and memory in the cases that need them, intact
source provenance at the editor, consistent lifecycle state, and no duplicate/mutation regression.
Tool availability alone is not completion. Quality and cost improvements remain measured
hypotheses; compare captured baselines and state sample sizes, not invented daily savings.

## Deployment, rollback, and completion

After approval and passing review/tests, create an online SQLite backup, deploy the clean
archive to the existing one-replica Railway service with its current /data volume, and verify
the effective roster, budgets, autopost OFF, and disabled legacy receipt audit. Use additive
migrations; no database restore, mass requeue, historical rewrite, or destructive pruning.

Smoke health, authenticated Desk run/intake/output/system views, catalog and artifact retrieval,
and a natural worker cycle. Observe the actual writer-to-editor handoff when naturally exercised.
If no suitable research story arrives, report that observational limit and use isolated contract
test/replay evidence rather than forcing production model or Typefully actions. Verify source
polling has resumed and no duplicate worker or unintended deployment target was created.

Keep one clear rollback route to the prior deployed runtime/configuration, compatible with the
additive records. Do not keep both research paths running, duplicate model work, rewind the
database, or enable autopost to test. Roll back on a material protocol, lifecycle, cost-loop,
or delivery regression; preserve accumulated research and ordinary draft records.

Update README, SYSTEM, HANDOFF-CODEX, PROMPTS, DOCUMENTATION, INBOUND-NEWS-FLOW where affected,
DESK-GUIDE, configuration examples, and the visual system guide. Preserve dated historical
plans/findings. Record exact release revision, deployment, schema/config checks, test results,
replay cost/quality findings, and natural-run evidence in the sprint findings.

Restore the existing rolling audit after successful smoke or safe rollback, adding these
research/memory checks while preserving its authority and meaningful-change-only notifications.
No duplicate monitor. The audit still proposes broader editorial changes and never autonomously
enables autopost or mutates Typefully content.

## Likely implementation surfaces

- `nbn/models.py`, `nbn/research.py`: mixed tools, continuation, native source metadata/accounting.
- `nbn/newsroom.py`, `nbn/config.py`: integrated loop, catalog, archive access, source registration,
  working budgets, writer guidance, reporting notes, and run-scoped receipt reuse.
- `nbn/sources.py`, `nbn/lead_material.py`: citation links, readable evidence, rich X context.
- `nbn/store.py`, `nbn/main.py`, `nbn/desk_prep.py`: durable artifacts, candidate/event association,
  notebook lifecycle, publication synchronization, relevance-first selection, Luna suggestions.
- `nbn/editor.py`: complete source-specific handoff and matching provenance clarification, not
  a new research seat or redesigned editorial policy.
- `nbn/observations.py`, `nbn/desk_api.py`, `desk_ui/app/main.tsx`: faithful historical research,
  notebook views, current roster, and honest combined-cost presentation.
- Focused existing tests plus isolated replay fixtures/report and the affected current docs.

## Review checklist

The independent reviewer should concentrate on four questions: Does the combined writer actually
reach the best available source? Can the next run recover useful work without inheriting stale
state? Is the catalog genuinely discoverable without inflating the whole prompt? Do native
tools, evidence registration, budgets, and publishing remain correct at failure boundaries?

Reject unnecessary abstractions or new services. If implementation reveals that a planned change
needs materially different editorial policy or a larger system redesign, bring that decision
back to Brady rather than expanding the sprint silently.
