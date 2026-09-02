# Plan 0048 — Run-scoped Sonnet newsroom

## Decision

Replace the ordinary fragmented `triage -> per-item source assessor -> event clerk ->
per-item Writer` path with one fresh, run-scoped Sonnet newsroom session. The session
sees the complete normalized intake index, recent feed/open-story context, Node themes,
and guide signals; it can selectively search and fetch; and it returns one atomic
newsroom dossier covering every intake item and every story it formed.

This is one continuous model context per decision run, not one giant one-shot response
and not a persistent conversation across runs. Fable remains an independent final
editor and becomes the fail-closed semantic claim checker for newsroom output.
Deterministic source, identity, freshness, copy, evidence-class, and publishing gates
remain authoritative.

## Product objective

Make a useful automated Bitcoin news account. Each run should identify the strongest
factual stories contained in the inbound material, research enough to understand them,
and produce compelling, educational, appropriately weighted posts when the evidence
supports them. It must not optimize for a quota, maximum output, or mere rule compliance.

The newsroom may learn story selection, information order, structure, and approximate
length from proven Bitcoin news desks and, later, successful NBN posts. Those examples
are craft and attention priors, never evidence. Phrasing, emotional framing, and factual
claims require independent work.

## Boundaries and non-goals

- No Marketing Node code or API change is planned. `wire-pulse-v2`, theme signals, and
  ranked refs already provide the discovery packet NBN needs.
- No widening of autonomous publishing authority. Only deterministic `primary` and
  `corroborated` classes may autopost; `secondary` remains draft-only in code.
- No relaxation of URL safety, source-tier eligibility, evidence independence, event
  freshness, numeric/quote integrity, Bitcoin scope, or Typefully confirmation rules.
- No hidden cross-run conversational memory. Durable context comes from NBN's database.
- No fixed story quota and no requirement to fill the feed.
- The daily receipt audit and the external 15-minute production audit remain separate.

## Runtime design

### 1. Deterministic intake envelope

The existing worker continues to fetch, canonicalize URLs, reject stale/non-English
items, consume fresh Node pulses, acquire the cycle lease, and build the bounded pending
batch. Exact URL duplicates and obviously unsafe input never consume newsroom attention.

The initial model packet is a curated editorial desk rather than a database dump:

- `run_brief`: assignment, as-of time, inventory count, and evidence rule;
- `intake_board`: exactly one stable card per candidate, separating what arrived, why it
  surfaced, registry source metadata, evidence status, unverified event hints, advisory
  theme IDs, guide attention priors, and operator/retry state;
- `reference_board`: code-labeled, deduplicated, uninspected intake/Node/guide URLs. These
  are research pointers only and never evidence;
- `coverage_board`: separate exact-event lists for reader-covered stories, open Typefully
  drafts, and other recent decisions;
- `theme_board`: broad Node themes cross-linked to current candidate IDs plus bounded NBN
  coverage context, explicitly advisory and not exact-event identity;
- `verified_handle_directory`: bounded spelling/identity records only.

Raw Node envelopes, provider plumbing, duplicate fields, and unrecognized discovery keys
never reach Sonnet. Every fresh candidate's stable ID, source, headline/post, URL, timestamp,
origin, registry tier/role, and evidence status always survive context compaction. Guide
posts supply bounded craft/attention examples. A published NBN post is not labeled successful
without engagement evidence or explicit operator selection.

Candidate text and all discovery metadata are explicitly untrusted data.

### 2. One session, staged work

The session proceeds inside one Anthropic `messages` history:

1. **Survey:** organize the complete run into potential exact-event stories, identify
   obvious dismissals, and state a research plan through a `submit_survey` tool. Persist
   only the bounded candidate mapping, proposed dispositions, and research needs.
2. **Research:** call bounded NBN-owned tools to fetch an intake item, run SerpAPI, or
   fetch an eligible result. Search results are pointers only. URL safety, redirects,
   tier classification, response size, and tool budgets are enforced by code.
3. **Research close:** call `finish_research` by itself. This closes the tool loop and
   switches the same session to the larger, forced dossier submission round.
4. **News judgment and writing:** decide `draft`, `update`, `hold`, or `skip`; select the
   strongest receipt; explain the reader value; and write the post from the inspected
   evidence. A story can combine multiple intake items and evidence pages.
5. **Atomically validated dossier:** call `submit_newsroom_dossier` with
   exactly one disposition for every intake hash plus a bounded story dossier for every
   formed cluster. Missing/duplicate hashes, unknown fetch IDs, invalid story references,
   or malformed output reject the whole dossier. Publication itself remains per-story
   and is not transactionally atomic.
6. **Optional repair:** after validation and deterministic lint, code may send one
   aggregate repair request in the same message history. Sonnet may answer only through
   `submit_newsroom_patch`; research cannot reopen. The session then closes.

The model may decide that no publishable story exists. It may not silently omit an item.

### 3. Tool contract

Expose only these read-only tools to Sonnet:

- `submit_survey(survey)` — one bounded operational checkpoint; no hidden reasoning.
- `fetch_intake_item(url_hash)` — fetch the canonical item page through NBN's existing
  safe article fetcher.
- `search_web(query)` — bounded SerpAPI organic results with credentials suppressed.
- `fetch_source(url)` — fetch only public HTTP(S) pages passing SSRF and source-policy
  checks; return canonical URL, byline, source classification, and bounded text.
- `finish_research()` — closes research; it must be the only tool call in its round.
- `submit_newsroom_dossier(dossier)` — strictly validated submission that closes all
  research and dossier mutation.
- `submit_newsroom_patch(patches)` — available exactly once, only after a valid dossier
  and an explicit lint-repair request. Each patch may contain only story ID, revised post,
  and bounded draft metadata. Attempts to change action, key, membership, receipt,
  evidence, claims, or provenance hold that story. A malformed patch cannot reopen
  research or trigger legacy fallback; unaffected stories continue and the session closes.

Every successful fetch receives an immutable, code-generated `fetch_id`. Tool results
carry that ID plus code-owned requested/final/canonical URLs, redirect chain, source ID,
tier, receipt role, official status, adapter provenance, publication metadata, byline,
content fingerprint, and bounded text. The model cannot set or override those fields.
Search snippets can prompt a fetch but can never become evidence.

Each unique final URL is cached within the run. Tool calls and returned bytes are capped.
Tool failures are returned as typed results so Sonnet can choose another source. The
model cannot write state, call Typefully/X, change configuration, or invoke arbitrary
network requests.

The protocol is closed:

- Research tools are rejected until one valid survey has been submitted.
- Allowed assistant stop reasons are `tool_use` while working, dossier submission, and—if
  explicitly requested—the single patch submission. `end_turn`, refusal, truncation, or
  exhaustion before the required submission is failure.
- Unknown tools, invalid arguments, duplicate tool-use IDs, repeated identical loops,
  or projected context overflow fail the session before materialization.
- Limits: 7 Sonnet rounds through dossier plus one optional patch round; 24 total research
  tool calls; 8
  searches; 16 fetches; 6 fetches associated with one story; one tool executed at a
  time; 8,000 characters per fetched page; 160,000 aggregate fetched characters;
  24 KiB survey; 96 KiB final dossier; at most the inventory size (currently 25) story
  objects; and 240 seconds wall clock. This is complete accounting, not a publishing quota.

Context/output bounds are explicit:

- initial packet: 96 KiB encoded JSON;
- total message history sent on any round: 480 KiB;
- survey/research round `max_tokens`: 8,000;
- dossier round `max_tokens`: 32,000;
- optional patch round `max_tokens`: 8,000.

Initial-packet trimming order is guide engagement/text detail, reference pointers beyond
three per candidate, older coverage cards, expanded theme activity, the verified-handle
directory, then event summaries/reference pointers recoverable by tools. Every candidate's
stable ID, source, headline/post, URL, timestamp, origin, registry tier/role, evidence
status, and reason for reaching the desk is always retained.
If those minimal records do not fit, the newsroom does not start. During research, code
rejects a tool result before it would cross the aggregate fetch/history limit; the model
receives a typed capacity result and may finish with inspected evidence. Projected overflow
before a valid dossier fails the session before materialization. No inventory item is
dropped to fit context.

Every model round counts against the existing hourly call budget. Preflight atomically
reserves `8 + inventory_size` calls: at most eight Sonnet rounds and at most one Fable
call for every possible story. This is at most 33 calls for the current 25-item inventory.
Fable and legacy fallback capacity are mutually exclusive: on dossier success, story
review consumes the Fable portion; on pre-materialization session failure, the unused
Fable/remaining-Sonnet portion is reassigned to legacy calls. Legacy still obeys the
existing budget and may hold/retry if the allowance is exhausted.

Implement the process-local rolling budget behind one lock. A reservation token owns a
fixed remaining count; each newsroom, Fable, or fallback call atomically consumes one slot
and records the real call timestamp. Unreserved calls cannot consume reserved capacity.
Release unused slots on successful completion, fallback completion, or exception. `off`
is unchanged. If reservation fails, `shadow` skips the newsroom and runs legacy; `draft`
or `live` immediately invokes the configured pre-materialization fallback without starting
the session.

### 4. Atomic output contract

The terminal dossier contains:

- `items[]`: exactly one row per input hash with final disposition, story key, and reason;
- `stories[]`: stable run-local story ID, proposed exact story key, optional code-supplied
  recent-cluster key plus `distinct|same_event|new_development` relationship, exact member
  hashes, `draft|update|hold|skip`, reader-value rationale, selected `fetch_id`, supporting
  fetch IDs, bounded support/originality recommendations, unresolved questions, post or
  null, event/disclosure/period dates, data provider, second-source requirement, handles,
  every number used, and a bounded list of the post's material factual claims keyed to
  the selected fetch ID;
- `run_note`: a short newsroom-level assessment of the run.

Every evidence reference must be a unique `fetch_id` issued by NBN in this session; the
selected fetch appears exactly once. A primary artifact may be named only through a second
code-issued `primary_artifact_fetch_id`, from which NBN derives the artifact URL. Invented,
failed, blocked, discovery-only, or search-only references reject the story. Model-supplied
URLs, tiers, outlet names, canonical metadata, and provenance are ignored or rejected.

### 5. Deterministic evidence reconstruction

For each story, code reconstructs the existing `ResolutionResult` and evidence records
from code-owned fetch records plus Sonnet's bounded support/originality recommendations.
Sonnet does not certify support or provenance. Existing source policy remains authoritative:

- blocked/discovery/aggregator/syndication roles cannot become receipts;
- official/research/original-reporting claims retain the current canonical URL, path,
  actor, metadata, byline, and ownership checks;
- independent corroboration is computed from persisted evidence chains, not declared by
  Sonnet;
- the selected receipt must independently support every factual assertion actually used
  in the post, even when the broader story was understood from pooled evidence.

The evidence pool helps Sonnet discover and understand the story. The linked receipt
must still support the copy placed above it.

### 6. Deterministic identity acceptance

Sonnet proposes story membership and canonical keys; it does not register aliases. Before
accepting a group, code applies the existing high-precision event compatibility checks:

- event-type conflicts;
- distinct actors/entities;
- exact event/disclosure/reporting dates;
- direction conflicts and ambiguous mixed directions;
- material numeric conflicts;
- the narrow U.S. 10-year-yield instrument/date/direction/unit/reading anchor;
- recurring purchases, filings, reports, and market moves across different dates.

A Node theme match is never same-event evidence. Conflicting mappings split into safe
single-event groups or hold when they cannot be separated. Alias registration happens
only after the complete dossier and identity mappings validate. Exact-story novelty and
reader-covered checks then run unchanged.

### 7. Independent support and terminal pipeline

After dossier conversion, retain the current terminal path:

- exact-story novelty and reader-covered checks;
- event/disclosure freshness;
- provider ownership and evidence class;
- deterministic lint for scope, attribution, URLs, mentions, numbers, quotes, and voice;
- one bounded aggregate newsroom-session revision when lint reports repairable copy
  errors. A revision may change only post text and its draft metadata; it cannot change
  story membership, action, story key, receipt, evidence, or source classification;
- Fable feed-context Editor receives the final post, exact bounded selected-receipt text,
  code-owned canonical provenance, and the structured claim list. It must return both an
  editorial verdict and `claims_supported` plus unsupported claims;
- a second deterministic lint/support check after any revision;
- Typefully delivery and confirmation;
- daily tape, post log, pipeline events, and operator-action handling.

Open Typefully drafts remain open evidence clusters. New independent evidence may promote
an existing approved draft without creating duplicate copy.

For newsroom output only, Fable is fail closed: timeout, refusal, malformed output,
unknown support, or `claims_supported=false` holds the story and cannot autonomously
publish it. Any Fable revision is re-linted against the same selected receipt. The legacy
Editor's current behavior is unchanged while the legacy path exists.

## Reliability and rollback

### Feature switches and rollout modes

- `NBN_RUN_NEWSROOM_MODE=off|shadow|draft|live` defaults `off` in code.
  - `off`: exact legacy behavior; the newsroom is not called.
  - `shadow`: newsroom runs read-only, records bounded diagnostics, then the untouched
    frozen inventory follows the legacy path.
  - `draft`: validated newsroom stories materialize through real gates but publishing is
    forced to Typefully drafts regardless of evidence class.
  - `live`: the existing primary/corroborated autonomous classes apply.
- `NBN_RUN_NEWSROOM_FALLBACK` supports `legacy` (production setting) or `hold`.
- Bounded settings cover model/tool rounds, tool calls, fetched characters, and timeout.

The legacy pipeline remains intact for one migration window. Fallback is legal only before
materialization starts. There is no mixed partial dossier/legacy processing.

### Read-only seam and materialization boundary

Before connecting the newsroom, mechanically extract and regression-test three narrow
seams from the existing cycle:

1. immutable inventory preparation;
2. validated story materialization into existing verdict/resolution/draft structures;
3. the existing deterministic terminal gates and delivery.

The lifecycle is explicit:

1. Freeze the inventory after intake freshness/language filtering and due-job/operator
   selection, but before any research attempt, status, evidence, alias, draft, or
   operator-action mutation.
2. Run the newsroom read-only against that immutable inventory.
3. Validate the complete dossier and deterministic identity mappings into an in-memory
   staging structure.
4. If validation fails, mark the newsroom run `fallback` and give that identical inventory
   to legacy, or leave it unmodified under fallback `hold`.
5. Persist the validated dossier digest and set `validated`.
6. Set `materializing` before the first existing-store mutation. Legacy fallback is now
   forbidden. Per-story failures resume idempotently or hold; they never re-enter legacy.
7. Mark `completed` only after every story/item disposition has materialized and delivery
   outcomes have been recorded.

The model output is atomically validated; external publishing remains per-story.

### Checkpoints and crash recovery

Add a bounded `newsroom_runs` record keyed by pipeline run ID with status, model, prompt
version, inventory hashes, survey checkpoint, final summary, failure kind, and timestamps.
States are `surveying`, `researching`, `validated`, `materializing`, `completed`, and
`fallback`. Store the inventory fingerprint and hash list, prompt/schema version, validated
dossier digest, bounded dossier, tool counters, timestamps, and bounded error. Add indexes
on status and creation time. Prune completed/fallback bodies after 14 days while retaining
the compact run summary used by the Desk.

Add bounded per-story materialization rows with `pending|materialized|delivered|held`, the
run-local story ID, dossier digest, and delivery reference. Do not persist full article
bodies, model conversations, hidden reasoning, or API credentials.

Crash rules:

- `surveying|researching`: no editorial store mutation exists; the abandoned run is
  marked fallback/failed and its items remain eligible for an identical-inventory retry.
- `validated`: re-fetch referenced pages, require matching canonical identity/content
  fingerprints, reconstruct staging, and resume materialization; mismatch holds/researches
  the affected story.
- `materializing`: resume only pending stories. Materialized/delivered story IDs, existing
  post rows, story keys, operator actions, and Typefully uncertainty guards prevent a
  duplicate delivery.
- `completed`: never re-run.
- `fallback`: legacy owns the inventory and the newsroom never materializes it.

### Failure containment

- One malformed or omitted item rejects the whole dossier.
- One failed tool result does not fail the run; Sonnet can search/fetch another source.
- Tool/model timeout before validation invokes the configured whole-batch fallback.
- A lint failure affects only its story; it does not discard other validated stories.
- A delivery failure retains the current Typefully uncertainty/reconciliation behavior.
- Existing cycle-lease heartbeat continues through the longer newsroom session.

### Retries, operator actions, and manual paths

- Due research retries enter the frozen inventory with their saved candidate references,
  retry/manual flags, and original attempt count. Read-only newsroom tool failures do not
  consume an attempt. Attempts change only during materialization into a typed retry state.
- Queued `stage` and `retry` actions enter with action ID and gate. They remain queued until
  materialization, then start/finish through existing audited methods. `stage` and manual
  force-draft can never autonomously publish.
- Open Typefully drafts and reader-covered clusters are supplied as feed state and remain
  governed by existing promotion/novelty code after accepted identity mapping.
- Previously held/researching items appear only through existing due-job/operator selection;
  ordinary terminal items are never silently reopened.
- Guide candidates retain their deterministic priority in inventory ordering, but remain
  tips rather than evidence.
- Typed fetch/search/model outcomes map at materialization to retryable infrastructure,
  editorial hold, or terminal ineligibility. A pre-materialization whole-session failure
  alone may invoke legacy fallback.

## Desk and audit visibility

Update the Desk's last-decision-run section to show:

- newsroom mode, prompt version, model, duration, tool rounds/calls;
- survey story count and final story count;
- per-story member items, decision, reason, reader-value rationale, selected receipt,
  evidence count, unresolved questions, and final gate outcome;
- every original item's final mapping/disposition;
- fallback reason when the legacy path ran.

Store only bounded summaries. No API keys, raw model reasoning, or complete article text
appear in the database, logs, or Desk.

The external 15-minute production audit stays active throughout development and release.

## Implementation phases

### Phase 0 — Behavior-preserving seam

1. Extract immutable inventory preparation, story materialization, and terminal delivery
   seams without changing feature-off behavior.
2. Add feature-off regression coverage before connecting a new model call.

### Phase A — Session and contracts

3. Add configuration, typed dossier/session/fetch records, strict tool schemas, complete
   coverage validation, identity vetoes, and bounded checkpoint persistence.
4. Implement code-owned fetch IDs and read-only tool dispatch with fetch caching and
   deterministic URL/source/redirect guards.
5. Add the mission-first newsroom prompt and staged survey/research/final protocol.

### Phase B — Pipeline integration

6. Add a mode-gated newsroom preparation path that converts a validated dossier to
   the existing verdict, resolution, evidence, and draft structures.
7. Preserve operator actions, research retry behavior, evidence pooling, open-draft
   promotion, aliases, terminal gates, Fable, and delivery.
8. Extend Fable with the newsroom-only fail-closed semantic support contract and keep the
   legacy Editor behavior unchanged.
9. Keep the legacy preparation path callable only as a pre-materialization whole-batch
   fallback.

### Phase C — Observability and documentation

10. Add Desk rendering and pipeline events for survey, tool use summary, final stories,
   fallback, and per-item dispositions.
11. Update `SYSTEM.md`, `HANDOFF-CODEX.md`, `PROMPTS.md`, and the flow documentation to
   describe the new primary path and temporary fallback.

### Phase D — Verification and release

12. Run unit/integration tests, Ruff, and compile checks locally and in the production
   image/environment.
13. Run a Railway-env isolated cycle with publishing forcibly disabled and fixture/new
    candidates; confirm one session, multiple tool turns, complete item accounting,
    evidence reconstruction, lint, and Fable behavior.
14. Deploy `off`; verify health and feature-off parity through one legacy cycle.
15. Enable `shadow`; observe at least two non-empty natural batches with no newsroom item
    or publisher mutations and inspect their complete diagnostics.
16. Enable `draft`; allow natural newsroom output through real gates but force it to
    Typefully drafts. Confirm draft reconciliation, evidence, Desk rendering, and Fable
    support behavior.
17. Enable `live` only after the natural draft phase passes; existing autonomous classes
    then apply. Observe at least two complete live cycles, including one non-empty run
    when available.
18. Confirm Desk telemetry, Typefully/X delivery state, Node pulse consumption, worker
    lease/heartbeat, and external audit activity. Do not manufacture a public post solely
    to prove deployment; an isolated Typefully draft smoke is allowed.

The external production audit will remain active throughout this release. It will not be
paused automatically.

## Required tests

- Complete multi-item run forms two stories and maps every input exactly once.
- Thirteen through twenty-five unrelated candidates receive distinct, complete story/item
  accounting without capacity-forced skips.
- Feature-off behavior is byte/structure-equivalent at the extracted seam and calls no
  newsroom code.
- No candidate status, evidence, alias, research attempt, operator action, or post changes
  before dossier validation; legacy fallback receives the identical frozen inventory.
- Two outlets plus an aggregator become one story with pooled independent evidence.
- A guide tip triggers research but cannot become evidence or a receipt.
- One model omission/duplicate/unknown hash rejects the entire dossier.
- Invented URL/provenance/fetch ID and a model-selected but unfetched source are rejected.
- Invalid tool name/schema, duplicate tool-use ID, timeout, repeated loop, oversized result,
  unsafe redirect, cache reuse, and projected context exhaustion have deterministic outcomes.
- Unsafe, blocked, discovery-tier, wrapper, and ineligible fetches cannot become receipts.
- Model-declared primary/original reporting cannot bypass path/actor/byline/ownership
  guards.
- A source supporting only part of the inbound headline can still support narrower copy;
  unsupported headline components are excluded and recorded.
- Every number and quote in the final post exists in the selected receipt text.
- Same-story multi-source evidence promotes an existing Typefully draft without duplicate
  drafting.
- False same-event merges fail on actor, event type, date, direction, material numbers, or
  yield anchors; a genuine same event is accepted.
- Reader-covered same event skips; a material new development becomes `UPDATE:`.
- Stale event, unsupported provider attribution, secondary-only evidence, and Fable spike
  retain current outcomes.
- Tool timeout can recover inside a session; session failure invokes atomic legacy
  fallback and does not lose items.
- Lint feedback is repaired in one aggregate same-session patch or held without affecting
  another story; patch attempts to change receipt, evidence, membership, action, or key
  are rejected.
- Patch-before-dossier, duplicate patch, research-after-dossier, malformed patch, and
  `end_turn` instead of a required tool submission close safely without legacy re-entry.
- Fable timeout, malformed output, or unsupported/unknown claims cannot autonomously
  publish newsroom copy.
- Crash before validation, after validation, during materialization, and after one delivery
  resumes without loss or duplicate delivery.
- Due retries, queued operator actions, open drafts, guide priority, and manual force-draft
  preserve their current authority and accounting.
- Model-budget preflight, atomic reservation, per-call consumption, successful release,
  failure reassignment to fallback, exception release, concurrent unreserved calls, budget
  exhaustion, and a long-session lease heartbeat are covered.
- Initial-packet truncation preserves every minimal candidate record; survey/research,
  dossier, patch, total-history, and output-token ceilings are enforced.
- Checkpoints and Desk output are bounded and contain no article bodies or credentials.
- Desk/checkpoint strings are escaped and omit hidden reasoning.
- Feature-disabled behavior matches the current suite.

## Acceptance criteria

- Exactly one Sonnet message history owns survey, research, judgment, and writing for a
  successful non-empty run.
- The primary path makes no separate Sonnet triage, source-assessment, identity-clerk, or
  Writer calls.
- Every considered item has an inspectable final disposition and story mapping.
- Every drafted claim is backed by an inspected, eligible selected receipt; evidence
  independence and autopost class remain deterministic.
- Fable independently and fail-closed verifies semantic support for newsroom copy; terminal
  publishing authority is otherwise unchanged.
- A single Railway switch restores the proven legacy path without a code rollback.
- Production health, Node ingestion, Typefully state, the Desk, and both audit mechanisms
  are healthy after deployment.
