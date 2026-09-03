# Plan 0052 — Haiku assignment desk and Sonnet-directed research

## Objective

Bring the editorial core back to a justifiable operating cost without reducing the quality or
authority of the final editorial judgment. Keep the 15-minute intake cadence, but stop opening a
large multi-round Sonnet newsroom merely because the queue is nonempty.

The new division of labor is:

- the existing Haiku RSS/EDGAR mailroom remains the fast relevance filter at ingestion;
- one new Haiku assignment-desk pass prepares every due cross-source batch, records clearly
  irrelevant/background decisions, and advances only plausible Bitcoin news work;
- Sonnet receives a compact prepared desk and remains the sole autonomous news judgment and
  writing seat;
- Sonnet may assign bounded, candidate-specific research to a Haiku reporting assistant, whose
  fetched receipts enter the same code-owned evidence workspace;
- the independent Sonnet editor continues to run only for proposed posts.

This is cost architecture, not a stricter editorial funnel. Haiku may remove clear noise from the
expensive desk, but it never publishes, writes final copy, establishes truth by assertion, or
overrides Sonnet. Uncertainty about plausible Bitcoin relevance advances to Sonnet.

The initial operating target is no more than roughly $5–$6/day under ordinary volume. That is a
measurement target, not a publishing quota or a code-owned editorial veto. The audit must report
when actual spend departs materially from it.

## Baseline and success measures

The rolling 24-hour production baseline immediately before this plan was:

- 96 newsroom sessions at the full 15-minute cadence;
- 390 Sonnet newsdesk responses, or about 4.1 per session;
- 14.76 million ordinary Sonnet newsdesk input tokens plus cache traffic;
- $36.94 estimated newsdesk cost, $2.93 editor cost, and $0.34 Haiku mailroom cost;
- about $40.21/day total, or roughly $1,200/month if sustained.

The first Sonnet round averaged about 32,600 ordinary input tokens and later rounds grew toward
43,000 because each research turn resent the accumulated conversation and tool results. The
existing five-minute system-prompt cache does not bridge the 15-minute session cadence.

Success is measured over natural production traffic, not a synthetic empty run:

1. Sonnet is not called when the assignment desk advances no candidates.
2. An ordinary active Sonnet desk completes in one or two calls; three is an exception, not the
   steady state. The resource bound does not change what stories qualify.
3. The Sonnet initial request is materially smaller than the 32,600-token baseline.
4. Guide-account, primary-source, operator-promoted, and continuity-retry leads remain visible and
   auditable; savings cannot come from silently losing them.
5. Every Haiku preparation/research claim remains explicitly non-evidentiary until backed by a
   code-issued inspected `fetch_id`.
6. The Desk and rolling audit expose cost per prepared batch, Sonnet wake, proposed draft, and
   delivered post, as well as the suppression and fail-open rates.
7. Editorial quality is judged separately from spend: publishability, guide-account recall,
   misses, excessive caution, scannability, source-resolution health, and continuity remain in
   the audit.

The first-call target is a 64 KiB hard packet ceiling and a rolling production median below
15,000 ordinary input tokens. The expected ordinary-day envelope, using the current recorded
Haiku $1/$5 and Sonnet $2/$10 per-million input/output rates, is:

| Work | Assumption | Estimated daily cost |
|---|---|---:|
| Assignment desk | 96 calls; about 6k input + 1.5k output | $1.30 |
| Sonnet newsdesk | 32 active desks; 1.5 calls and about 25k total input + 2.25k output per desk | $2.32 |
| Haiku reporting | 8 assignments; 2 calls and about 18k input + 2k output per assignment | $0.22 |
| Sonnet editor | 8 proposed posts; about 15k input + 1.5k output | $0.36 |
| Existing RSS mailroom | Current observed volume | $0.34 |
| Cache writes/variance | One-hour stable-prefix writes and traffic variance | $0.75 |
| **Expected total** | **Measurement hypothesis, not a promise** | **about $5.29/day** |

This target requires both a roughly one-third Sonnet wake rate and mostly one-call prepared desks.
If natural traffic keeps Sonnet awake every interval or the median remains above 15,000 input
tokens, the design has missed its economic goal even if the code works.

## Scope boundaries

- Do not change source tiers, treasury-company policy, the approved orientation brief, Bitcoin
  scope, Typefully semantics, autopublish state, or the independent editor's authority.
- Do not add a second external search vendor or modify the Marketing Node API/codebase.
- Do not make Haiku's summary an evidence receipt. Only the existing safe fetch path creates
  evidence.
- Do not use a hard daily story quota, a hard number of candidates Sonnet must publish, or a
  deterministic quality score.
- Do not add an automatic monetary kill switch in this sprint. Use structural call/context bounds,
  visible spend, and an operator warning so a temporary traffic spike does not silently stop the
  wire.
- Keep the 15-minute due clock. Reduce expensive wakeups rather than making the wire slower.
- Preserve the owner's modified `prompts/orientation-examples.md` and untracked
  `RAW-POOL-LAST-2H.md` and `audit/` tree.

## Architecture

### 1. Existing intake mailroom remains

The existing `intake_triage` Haiku pass continues to process RSS and SEC EDGAR at ingestion.
It may mark obvious background, pass plausible candidates, and wake the due clock for priority
items. This protects the primary-source fast lane and avoids combining two different temporal
jobs into one opaque model call.

### 2. New run-scoped Haiku assignment desk

When the persisted editorial clock is due and fresh inventory exists, run one bounded Haiku pass
before reserving or calling Sonnet. It receives compact, untrusted cards for all inventory items
plus a compact code-owned coverage index. The card contains:

- candidate ID, source/origin, arrival time, headline/post text, bounded summary, and URL;
- attention priors such as guide account, Node curated lead, official direct source, operator
  request, or continuity retry;
- unverified Node event/theme hints when present;
- the existing RSS/EDGAR mailroom route/category/reason when present;
- compact exact-event coverage/open-draft keys and ages, without full historical post bodies.

It returns exactly one preparation per candidate:

- `advance`: plausibly useful NBN work that Sonnet should judge;
- `background`: facially outside Bitcoin/monetary scope, facially contains no new development, or
  is an exact output/receipt duplicate already proved by code;
- a bounded event summary, Bitcoin relevance, freshness observation, research objective, and
  suggested source/search leads;
- zero or more supplied exact coverage keys that may be related, copied only from the packet.

Code, not Haiku, synthesizes effective `advance` for operator-promoted/staged items, due research
retries with a real unresolved objective, and current candidates matching an unresolved
`newsroom_story_memory` continuity workbench. These protected rows are omitted from the Haiku
routing batch when every field needed for preparation already exists; otherwise Haiku may distill
them but cannot suppress them. The persisted preparation records both `model_route` and
`effective_route` plus a code-owned `protection_reason`.

Guide-account, Node-curated, and recognized official/primary leads also receive deterministic
attention protection: a Haiku `background` may stand only when the card is facially outside
Bitcoin/monetary scope or contains no new development. Because code cannot safely infer that
semantic condition, the first implementation treats these attention classes as effective
`advance`; Haiku still supplies their distillation. This deliberately favors recall while the
audit measures their cost. Later evidence may justify a narrower protected set, but not in this
sprint.

For ordinary candidates, `background` has that same single narrow meaning: facially out of scope,
facially no development, or a code-proven exact duplicate. Low apparent weight, uncertain
freshness, or suspected semantic redundancy always advances. `background` is a reversible
preparation decision, not a claim that the underlying facts are false.

Validation is item-local. Unknown IDs, duplicates, missing decisions, invalid enums, oversized
fields, refusal, timeout, or model failure fail open as `advance` with a typed code-owned reason.
If the entire call fails, every candidate advances. An unavailable Haiku can increase Sonnet cost
but can never make the news wire go dark.

If no candidate advances, complete the run without a Sonnet call: record each preparation as a
visible desk-prep skip and advance the ordinary cadence. If at least one advances, only those
candidates enter the Sonnet packet. Background candidates are accounted for in the same run and
may be returned to a later desk through the existing guarded operator-action mechanism.

### 3. Persistence and auditability

Add a bounded `desk_preparations` table keyed by `(run_id, item_hash)` with:

- `model_route` and `effective_route` (20 characters each);
- `event_summary` (400), `bitcoin_relevance` (300), `freshness_note` (240),
  `research_objective` (400), and JSON arrays of at most three source leads and three supplied
  related exact keys under a 4 KiB row ceiling;
- `protection_reason` (80), model (80), prompt version (80), outcome (40), typed error kind (80),
  preparation mode (`observe|enforce`), application state (`observed|applied`), and
  preparation/applied timestamps;
- whether the candidate was advanced, suppressed, or later operator-promoted, with `promoted_at`;
- no raw prompts, article bodies, chain of thought, or model reasoning.

The item remains the canonical source of workflow status. Assignment-desk backgrounds become
`skipped` with `decision_stage=desk_prep` and `decision_category=background` only after the
complete validated preparation batch is persisted. A transaction must make preparation
persistence and status application atomic.

Persist the complete validated or fail-open batch in one `BEGIN IMMEDIATE` transaction. In
`observe`, every row is terminally marked `observed`/applied without changing item status. In
`enforce`, suppression and each row's terminal `applied` marker occur in that same transaction. A
transaction failure persists none of the batch and leaves every item unsuppressed; the next due
cycle may prepare it again. There is no cross-mode reconciliation: an observe result can never be
enforced after restart or after an observe-to-enforce configuration change.

Extend the existing `SEND TO DESK` action so it can safely restore either an intake-mailroom
background or the latest unpromoted assignment-desk background whose item is still exactly
`skipped/desk_prep/background`. In the latter case one transaction marks `promoted_at`, restores
the item to `new`, records a durable protection marker for the next prep, and wakes the persisted
desk clock. It still routes through Sonnet and the editor; it never publishes directly. Keep the
two promotion predicates distinct behind the shared endpoint. Repeated or concurrent promotion
remains idempotently guarded.

### 4. Deterministic first-receipt preparation

After effective routing and before the first Sonnet call, safely inspect at most one best
candidate-owned URL for selected advanced items. The global automatic-prefetch envelope is six
unique normalized URLs and 24,000 fetched characters per desk. Always leave at least eight fetches
and 80,000 fetched characters of the existing parent capacity available for Sonnet or its Haiku
assignment; when either reserve would be crossed, prefetch stops.

Deduplicate normalized URLs before attempting them. Rank candidates first by operator/retry/
unresolved-continuity protection, then guide/Node/official attention, then Haiku urgency and
arrival order. Within a candidate, prefer a known official/primary reference, then a Node/guide
outbound source, then the intake URL. Do not search or crawl from code. A successful fetch creates
the normal `FetchRecord`; a typed failure is preparation context and never suppresses the
candidate. Prefetch consumes the parent's ordinary fetch and character counters but no search
capacity.

This model-free step lets a routine prepared story reach Sonnet with an inspected receipt and
finish in one response. It uses the same URL safety, redirects, source classification,
fingerprinting, fetch deduplication, and character bounds as model-requested research.

### 5. Compact Sonnet desk

Build Sonnet's packet from advanced candidates and their Haiku preparations. Preserve the original
headline/post and bounded summary beside Haiku's distillation so Sonnet can disagree with it.

Replace the globally expanded context with progressive access:

- include all 48-hour reader-visible posts as a compact index: time, exact event key, short
  code-generated excerpt, receipt URL, and performance fields;
- include full recent post copy only for exact keys linked by code-owned coverage or preparation
  keys; expose a read-only `read_recent_posts` tool for Sonnet to request any indexed full copy;
- include continuity workbenches that match an advanced candidate in full and other continuity
  work only as a short index retrievable through `read_continuity`;
- include only themes attached to advanced candidates, plus a short hot-theme index;
- include candidate-owned reference pointers rather than unrelated global pointers;
- keep the verified handle directory retrievable unless a handle is already relevant to the
  advanced candidates.

The finite initial/retrieval contract is:

- at most 40 recent-feed index rows, with `total_rows` and `truncated_rows` metadata;
- at most eight related full recent posts and 24 KiB total full post copy initially;
- at most 12 continuity index rows, five full matching workbenches, and 24 KiB of matching
  continuity/evidence text initially;
- at most 24 theme index rows and 12 full candidate-attached themes;
- at most 12 relevant handle rows initially and 50 in the retrievable index;
- at most two context-retrieval calls per Sonnet desk, eight rows and 16 KiB per response, and
  24 KiB total returned context;
- a 64 KiB initial Sonnet packet and 192 KiB Sonnet message-history ceiling.

Every truncated index exposes its total and omitted count. Retrieval accepts only code-issued
opaque row IDs or indexed exact keys, rejects unknown values, deduplicates repeated reads, and
cannot enumerate arbitrary database rows. Cached evidence is still subject to the existing age,
fingerprint, and public-URL revalidation before it can appear as a receipt.

Access is preserved; unused bulk is removed from the first request. Tool-returned context is
untrusted editorial context, never evidence.

Use a one-hour Anthropic cache breakpoint for the stable Sonnet orientation/system prefix, because
the desk runs every 15 minutes. Record one-hour versus five-minute cache creation/read tokens when
the API exposes the detailed fields. The mutable candidate packet is not placed behind a falsely
stable cache boundary.

### 6. Sonnet-directed Haiku research

Add an `assign_haiku_research` tool to the Sonnet desk. Sonnet supplies:

- one concise research objective;
- one or more current candidate IDs;
- optional already inspected fetch IDs that are relevant to the assignment.

The backend creates a fresh, candidate-scoped Haiku reporting session. It receives only the named
candidate cards, their preparation, named inspected receipts, relevant reference pointers, and a
compact research brief. It may use the existing safe `fetch_intake_item`, `search_web`, and
`fetch_source` operations and must finish with a structured memo containing:

- what appears to have happened and when;
- what the inspected sources establish;
- conflicts or uncertainty;
- the strongest supportable angle;
- remaining gap, if any;
- every cited code-issued `fetch_id`.

The same fetch registry, URL safety checks, search degradation circuit, deduplication, and total
fetch/search capacity remain authoritative. New receipts created during the Haiku assignment are
available to Sonnet and the independent editor. The memo itself is not evidence.

Bound each Haiku assignment to a small independent context and bounded calls/output. Sonnet may
use the tool when multi-step source resolution or comparison is worthwhile; it may directly fetch
an obvious source or submit a dossier immediately when the prepared evidence is enough. Do not
force delegation merely to exercise it.

The reporting assistant is implemented through parent-session callbacks, not a parallel evidence
workspace or concurrent agent. The parent owns all URL validation, fetch records, fingerprints,
search circuit, and cumulative capacities. Only named current candidate IDs and already existing
fetch IDs enter the assignment. New fetches enter the parent registry only through the parent's
ordinary successful safe-fetch path. Memo citations must be a subset of the resulting parent
registry. A typed assignment failure returns to Sonnet while any receipts fetched successfully
before the failure remain available.

Per Sonnet desk, allow at most one assignment, two Haiku responses, eight assistant tool calls,
three searches, five fetches, 20,000 fetched characters, a 32 KiB initial assistant packet, a
96 KiB assistant-history ceiling, a 4 KiB memo, and 90 seconds. These sit inside—not in addition
to—the parent's smaller remaining search/fetch/character capacities. There are no concurrent
assistant sessions and no assistant-specific evidence persistence engine.

### 7. Sonnet round and retry policy

Set the normal v2 Sonnet maximum to three responses. This is a resource boundary, not an editorial
gate:

- call one may submit the dossier immediately, directly fetch/search, or delegate focused work;
- call two should normally consume results and submit the dossier;
- call three is available for one meaningful follow-up or forced completion.

The prompt tells Sonnet that a narrower well-supported post, a human draft, or a deliberate drop
is preferable to open-ended research. It does not tell Sonnet to lower the story bar or publish to
meet a quota.

Retain one retry allowance. A clean session restart is permitted only when zero successful Sonnet
responses were recorded. After at least one successful response, one transient transport/API
failure may retry only that failed request with byte-identical history; a second failure defers.
A late protocol, tool-contract, or dossier-validation failure persists a typed defer and lets the
next clean run use continuity. It never replays successfully billed rounds.

### 8. Reservation ownership

`_lease_run` remains the sole final releaser of one combined model-call reservation. Compute the
required envelope from enabled configuration rather than a fixed number:

`actual_mailroom_call + enabled_prep_call + configured_sonnet_rounds + retry_allowance +
 enabled_haiku_research_rounds + editor_call`

With the intended production values this is `1 + 1 + 3 + 1 + 2 + 1 = 9` when the same cycle
actually calls the RSS mailroom, and eight otherwise. With prep/research off and the rollback
Sonnet limit restored to six, it correctly becomes eight (`6 + 1 + 1`) rather than retaining a
v2.6-era constant. No nested component reserves or releases capacity.

If the combined reservation is unavailable, the mailroom/prep path fails open and the cycle
attempts the smaller direct envelope computed as
`configured_sonnet_rounds + retry_allowance + editor_call`, with prep/research disabled only for
that cycle. If that is also unavailable, existing typed technical deferral applies. Tests must
prove every mode combination, six-round rollback, and no double reserve, leak, or stranded lease.

### 9. Cost accounting and Desk telemetry

Record model usage under four distinct seats:

- `rss_triage` — existing ingestion mailroom;
- `desk_prep` — new assignment desk;
- `research_assistant` — Sonnet-directed Haiku assignments;
- `newsdesk` and `editor` — existing Sonnet seats.

Add counters and selected-day Desk metrics for:

- due batches, prep calls, prep failures/fail-open, advanced and background counts;
- Sonnet wakes suppressed and Sonnet wake rate;
- Sonnet calls per active desk and input tokens per first/final call;
- Haiku assignment count, rounds, searches, fetches, failures, and cost;
- cost per due batch, active Sonnet desk, proposed draft, Typefully draft, and confirmed post;
- rolling daily estimated spend versus the $6 operating target, clearly labeled as an estimate;
- cache creation/read split by duration when available.

Warn visibly when rolling 24-hour model spend exceeds $6 or when projected 30-day spend exceeds
$180. Do not change publication state automatically.

Add `cache_creation_5m_input_tokens` and `cache_creation_1h_input_tokens` columns through an
additive migration. Cost new rows at 1.25× and 2× base input respectively, with cache reads at
0.1×, and bump the rate version. Preserve the aggregate legacy cache-creation column and never
recompute historical estimates.

## Configuration and rollback

Add explicit knobs with safe defaults:

- `NBN_DESK_PREP_MODE=off|observe|enforce` (default `off`);
- `NBN_DESK_PREP_MODEL=claude-haiku-4-5`;
- prep maximum 25 candidates, 48 KiB packet, 6,000 output tokens, 45-second timeout, and six
  calls/hour;
- `NBN_HAIKU_RESEARCH_MODE=off|on` (default `off`);
- research maximum one assignment/desk, two Haiku responses, eight tools, three searches, five
  fetches, 20,000 fetch characters, 32/96 KiB packet/history, 4 KiB memo, and 90-second timeout;
- `NBN_RUN_NEWSROOM_MAX_ROUNDS=3` as the intended production value;
- compact Sonnet 64/192 KiB initial/history bounds, two retrieval calls, eight rows/16 KiB per
  retrieval, and 24 KiB total retrieval output;
- `NBN_MODEL_DAILY_TARGET_USD=6` for reporting only.

Modes:

- prep `off`: current v2.5 behavior;
- prep `observe`: prepare and persist but send the unchanged inventory to Sonnet;
- prep `enforce`: suppress validated background and send only advanced inventory;
- research `off`: Sonnet retains direct search/fetch only;
- research `on`: Sonnet may delegate focused assignments.

Add `NBN_COMPACT_DESK_ENABLED=false|true` independently. Rollback is configuration-only: disable
Haiku research and compact context, set prep to `off`, and restore the production Sonnet round
variable to six. New persistence is inert and retained. Do not use automatic fallback to legacy
editorial v1.

## Implementation phases

### Phase 1 — Contracts, storage, and accounting

- Add preparation enums, strict schema, bounded validation, fail-open conversion, and persistence.
- Add `desk_prep` and `research_assistant` telemetry plus per-response input-position metrics.
- Extend rate accounting for one-hour cache writes without changing historical rows.
- Add focused model-free fixtures for guide, Node, primary, ordinary RSS, operator, continuity,
  duplicate, invalid, and whole-call-failure cases.

### Phase 2 — Assignment desk and wake suppression

- Build the compact preparation packet and one Haiku call at the due boundary.
- Integrate observe/enforce modes before Sonnet reservation/call.
- Atomically account for background items and support guarded promotion.
- Complete zero-advance runs without creating a Sonnet `model_usage` row.

### Phase 3 — Compact progressive Sonnet context

- Feed Sonnet only advanced candidates plus original lead text and Haiku preparations.
- Perform the one-best-URL safe prefetch for advanced candidates.
- Replace expanded global history with compact indexes and read-only retrieval tools.
- Cache only the stable Sonnet prefix for one hour.
- Reduce the ordinary Sonnet maximum to three responses and narrow clean-retry eligibility.

### Phase 4 — Sonnet-directed Haiku reporting

- Add the assignment tool and fresh candidate-scoped Haiku session.
- Reuse the parent workspace's safe fetch/search operations and receipt registry.
- Validate bounded memos and expose their new receipt IDs to Sonnet/editor.
- Fail an individual assignment back to Sonnet as a typed tool error; never fail the whole desk
  solely because Haiku was unavailable.

### Phase 5 — Owner surface and documentation

- Add preparation, delegation, wake-suppression, cache, and unit-cost metrics to the Desk.
- Show recent assignment-desk backgrounds with `SEND TO DESK`.
- Update `SYSTEM.md`, `INBOUND-NEWS-FLOW.md`, `README.md`, and the current handoff note.
- Update the rolling audit instructions with the cost target and explicit false-negative review of
  Haiku-suppressed candidates.

## Test plan

Focused tests must prove:

1. valid assignment preparations persist once and only `background` is suppressed in enforce;
2. observe mode has no ordering, status, or Sonnet-inventory effect;
3. missing/duplicate/unknown IDs, invalid fields, refusal, timeout, budget exhaustion, and model
   exceptions fail open item-locally or batch-wide as appropriate;
4. guide, official, operator, and meaningful continuity uncertainty advances under the prompt and
   model-independent protection policy;
5. zero advanced candidates produce no Sonnet API call and no Sonnet usage row;
6. at least one advanced candidate opens Sonnet with only the advanced inventory while every
   background item receives an auditable terminal decision;
7. assignment-desk promotion is authenticated, atomic, idempotent, and returns the item to Sonnet;
8. the compact packet retains the original lead beside Haiku's summary and remains within its byte
   bound at maximum candidate count;
9. all 48-hour recent posts remain discoverable, but only related full copy enters initial Sonnet
   context; retrieval is bounded and escaped;
10. only matching continuity evidence is loaded in full and retrieved evidence retains its
    fingerprint/public-URL revalidation;
11. a Sonnet Haiku assignment can search/fetch, returns a bounded memo, adds valid receipts to the
    parent registry, and cannot cite invented candidate/fetch IDs;
12. an assignment failure returns a typed tool error while Sonnet can still submit a dossier;
13. Sonnet completes directly in one response, normally after tools in two, and is forced to submit
    by the third; late protocol failures do not replay all successful billed calls;
14. one-hour stable-prefix cache control is sent correctly and detailed cache usage is costed and
    reported without corrupting older telemetry;
15. source safety, search circuit, exact-delivery idempotency, editor fail-closed behavior,
    mechanical hard rails, Typefully uncertainty, lease, kill switch, and autopublish setting are
    unchanged;
16. existing RSS mailroom enforcement and priority wake behavior remain green;
17. full Python 3.13 test suite and a mocked end-to-end due cycle pass.

Restart-focused tests also prove that a committed observe batch remains terminally observed after
restart or mode change, a committed enforce batch contains all status applications atomically,
transaction failure leaves neither rows nor suppressions, protected/promoted work cannot be
suppressed, and assignment-desk promotion always targets the latest eligible preparation.

Resource tests prove automatic prefetch never attempts more than six unique normalized URLs or
24,000 characters, always leaves eight fetches and 80,000 characters for later research, and
shares the parent's counters without touching search capacity.

## Independent review gates

The lead coder must explicitly approve:

1. that the design lowers Sonnet calls/context rather than merely moving equal token volume to
   Haiku;
2. that Haiku cannot silently suppress plausible guide/primary/operator/continuity work;
3. that shared fetch/search state cannot cross-contaminate evidence or bypass URL safety;
4. that retry and reservation accounting cannot multiply calls or strand the lease;
5. that the persistence/migration and promotion contracts are restart-safe;
6. that compact context preserves Sonnet's access to the 48-hour feed, continuity, themes, and
   original leads;
7. that spend telemetry will reveal whether the structural changes actually reach the target;
8. that the plan is proportionate for a low-stakes early-stage wire and avoids a new overbuilt
   subsystem.

Implementation does not begin until the lead returns `APPROVED`. Any `CHANGES_REQUESTED` finding
must be incorporated and resubmitted until consensus.

## Deployment and production smoke

1. Record production health, replica count, volume attachment, editor model, v2 mode, current
   preparation/research variables, and the owner's autopublish setting. Never change autopublish.
2. Create and integrity-check an online SQLite backup.
3. Deploy code with prep, compact context, and research defaults off and run focused
   production-image tests.
4. Set prep to `observe` with compact context and research still off. Trigger or await one natural
   nonempty due run; verify preparation rows and compare its proposed routes against the unchanged
   Sonnet inventory.
5. Inspect every observe-mode background against the raw candidates. If validation or obvious
   plausible-story loss is found, fix and redeploy before enforcement.
6. Enable prep enforcement, compact context, and the three-round Sonnet limit together while
   research assistance remains off. Verify one natural advanced run and, when naturally
   available, one zero-advance run. Compare wake rate, first-call tokens, rounds, misses, and spend
   against both baseline and observe. Do not fabricate or publish a story to satisfy the smoke.
7. Only after that comparison succeeds, enable Haiku research and verify one natural delegation or
   a model-independent mocked production-container delegation. Lack of a natural need is not a
   reason to force Sonnet to research or fabricate content.
8. Confirm `/health`, `/status`, report rendering/actions, database integrity, no duplicate
   Typefully delivery, and no unexpected worker error.
9. Compare first-call tokens, calls per wake, cost per due batch, and projected daily spend against
   the recorded baseline. A successful deploy requires the mechanics and accounting to work; the
   $6/day target is evaluated over subsequent natural traffic rather than claimed from one run.
10. Confirm the existing rolling audit is active and now reviews both editorial false negatives and
   the new cost metrics.
