# Plan 0056 — NBN-native storyline memory

**Status:** Approved by independent lead-coder review; implementation verification complete.

## Objective

Give the Next Block News desk compact, durable editorial memory one level above exact event
clusters. Haiku will map each run's plausible leads to only the relevant existing storylines inside
the assignment-desk call that already runs. Sonnet will receive those relevant cards, decide how
the current events relate, and may update or create a storyline without turning memory into
evidence or a publishing gate.

At the same time, stop treating Marketing Node theme metadata as an NBN editorial-memory system.
The Node remains a cheap supplemental discovery source, but its theme board leaves the live v2
newsroom payload and Node provenance no longer forces Haiku-background material into Sonnet.

This is a focused extension of the current newsroom workbench, not a new knowledge graph, generic
taxonomy, second ingestion system, or additional recurring model seat.

## Why this boundary

Production observation since 2026-08-31 found:

- 64 Node pulses and 703 candidate appearances produced 65 Node-first URLs;
- one Node-first item became a draft, while two already-known items later drafted with Node
  context attached;
- the latest pulse loaded 79 active Node themes but matched none, and no theme signal has reached
  NBN across the observed pulses;
- six of 21 recently prepared Node-first cards were labeled background by Haiku but forced to
  Sonnet by the `node_curated` protection; none of those 21 produced a draft;
- NBN already owns the state the Node cannot know: exact-event aliases, inspected evidence,
  unresolved research, editor feedback, Typefully drafts, reader-visible posts, owner decisions,
  and recent copy.

Marketing themes describe the broader Swan/Bitcoin conversation. NBN needs newsroom storylines:
ongoing subjects whose discrete developments may deserve updates, restraint, or accumulated
context. Separate repositories and the authenticated Node discovery API remain appropriate;
duplicated editorial memory does not.

## Semantics

### Exact event

An exact event remains the unit of deduplication, corroboration, receipts, UPDATE labeling, and
output continuity. Existing canonical event keys and aliases remain authoritative.

Examples:

- one day's reported IBIT inflow;
- movement of funds from the Coldcard attacker addresses;
- a committee scheduling a particular CLARITY Act vote.

### Storyline

A storyline is a broader, NBN-specific editorial thread that can contain several distinct events.
It is context and memory, never evidence or exact-event identity.

Examples:

- institutional Bitcoin ETF demand;
- the Coldcard entropy vulnerability and subsequent thefts;
- CLARITY Act legislative progress.

A shared storyline must never alias event keys, establish corroboration, prove novelty, require
coverage, or turn a routine observation into a post. It helps the desk recognize continuity and
understand what changed.

## Architecture

### 1. Small durable storyline ledger

Add two additive SQLite tables and one nullable post column.

`newsroom_storylines` contains:

- stable `storyline_key` primary key, normalized to readable kebab case and capped at 120 chars;
- title (160), compact state summary (800), and lifecycle `open|closed`;
- at most three `watch_for` strings of 240 characters each in valid bounded JSON;
- a bounded update reason (400), creation/update timestamps, last-signal timestamp, and revision;
- no article bodies, chain of thought, source prose, prompt text, or claim of factual authority.

`newsroom_storyline_events` contains an immutable association between one storyline and a current
candidate/item:

- storyline key, item hash, canonical exact-event key when available, run ID, disposition,
  relationship (`new_storyline|continuing|turn|routine_signal|closing`), and observation time;
- one row per `(storyline_key, item_hash, run_id)` so a same-run retry is idempotent while a
  later run may record a changed bounded disposition without rewriting history;
- an index by storyline/time. The underlying `items`, event aliases, resolutions, and `posts`
  remain the factual and lifecycle records.

Event dispositions use a small code-owned enum. `last_signal_at` is derived from the underlying
item observation time, not retry or persistence time, so retries cannot make a storyline look
newer than its evidence.

Add nullable `storyline_key` to `posts`. New output records carry the Sonnet-confirmed storyline
when present. Existing posts are not guessed or backfilled. Reader coverage and open-draft state
are derived from the posts table rather than copied into mutable storyline prose.

Storylines do not expire after the current 72-hour exact-event workbench TTL. Retrieval considers
at most the 80 most recently updated open storylines plus recently closed lines, with closed or
quiet history naturally falling outside the bounded index. Rows are retained for auditability;
no destructive pruning or speculative backfill occurs in this sprint.

Every JSON field and assembled card has explicit byte/count bounds. Corrupt or oversized rows are
skipped fail-open and can never prevent an editorial run.

### 2. Haiku selects relevant storylines in its existing pass

Extend the existing run-scoped assignment-desk packet with a compact storyline index. Each index
row contains only:

- code-issued storyline key;
- title;
- a short summary excerpt;
- lifecycle and hours since the latest signal;
- last exact-event key and derived last-covered/open-draft indicators.

The index is capped at 80 rows and 24 KiB. If necessary, summaries are shortened and older rows
are removed before any candidate card is reduced. The packet continues to obey the existing
48 KiB assignment-desk ceiling.

Haiku returns at most two `related_storyline_keys` per candidate, copied only from the supplied
index. This is a retrieval suggestion, not an identity or editorial decision. Unknown, duplicate,
or malformed keys are discarded locally without invalidating an otherwise valid preparation.
Persist the selected keys separately from the existing `related_keys_json`, which continues to
mean exact-event keys. Never mix those namespaces.

Use the existing assignment-desk call; add no second Haiku mapping session. A fully protected
batch should still use the existing Haiku preparation call when budget and availability permit so
it can receive storyline mappings. Protection continues to control only effective routing.
Haiku timeout, cap, refusal, invalid output, or absence simply yields no storyline selection and
the newsroom proceeds with its current memory surfaces.

### 3. Sonnet receives only selected storyline cards

After Haiku preparation, collect the unique selected storyline keys for advanced candidates. The
initial Sonnet desk receives at most eight full cards and 16 KiB total. Each card contains:

- stable key, current revision, title, compact state summary, lifecycle, and watch-for list;
- the latest eight linked event records with time, exact-event key, disposition, and short item
  headline;
- derived open-draft and reader-coverage state plus the most recent output lede when present;
- which current candidate IDs Haiku associated with the storyline;
- an explicit `untrusted_editorial_memory_not_evidence` label.

Additional Haiku-selected cards, up to 24 unique keys, appear only in the existing code-issued
retrievable-context index and can be fetched through `read_desk_context` under its current call and
byte budgets. Sonnet never receives or enumerates the full storyline database.

Code tracks the exact set of full cards included initially and successfully returned by
`read_desk_context`. Only that read set is mutable in the dossier; appearance in the retrievable
index alone grants no update authority. Storyline cards participate in the existing combined
Sonnet-packet compaction order and are shortened or removed before candidate identity or inspected
evidence. The 16 KiB storyline-card limit is a subordinate cap, not permission to exceed the
overall packet ceiling.

The current candidate card retains Haiku's selected storyline keys so Sonnet can disagree. The
prompt states that Sonnet may reuse an existing key only when the broader storyline genuinely
fits; it must still make an independent exact-event and publication decision.

### 4. Sonnet maintains the ledger without making it authoritative

Extend the v2 dossier with an optional bounded `storyline_updates` array and an optional
`storyline_key` on each publishable story.

Each update contains:

- one storyline key and title;
- `base_revision` for an existing storyline, echoed from a full card;
- lifecycle `open|closed`;
- compact current state summary;
- at most three watch-for notes;
- relationship enum `new_storyline|continuing|turn|routine_signal|closing`;
- one or more current candidate IDs and a short update reason.

Limits: at most 12 updates, 25 candidate memberships total, and one update per storyline key per
run. At most three updates per run may create a new storyline. A candidate may belong to only one
storyline in this first version. Existing keys may be updated only if their full card is in the
code-owned read set. They update with `WHERE revision = base_revision`; a stale revision is ignored
and audited while editorial output continues. New lines are insert-only. A new key must not already
exist, and collisions are rejected rather than normalized over an existing row.

The exact key grammar is `^[a-z0-9]+(?:-[a-z0-9]+){0,15}$` with a maximum of 120 characters. Sonnet
is told to create a storyline only for a durable named subject likely to receive distinct future
developments—not a generic category, broad beat, or renamed exact event. Excess creations and
invalid updates are ignored and audited without affecting a valid publication decision. Haiku
mapping failure or an empty storyline index does not remove Sonnet's ability to create a justified
new storyline from the current candidates.

Sonnet can record a routine signal or completed editorial drop in an existing storyline even when
no post is proposed. Haiku-background items never reach Sonnet and therefore do not mutate
storyline memory. This is intentional: background means no plausible new development requiring
the expensive desk.

The state summary and watch-for text are explicitly regenerable, untrusted editorial context.
Future copy may not cite them. Only a current, code-issued inspected fetch ID is evidence. Event
links, item decisions, posts, and receipts remain independently queryable so a bad summary cannot
rewrite history.

For a proposed post, `storyline_key` must be null, a selected existing key, or a valid new key in
the same dossier. Code attaches it only after exact-event validation. Draft replacement preserves
the post's existing storyline association when the dossier supplies null or the same key. A
different non-null key on replacement is ignored and audited in this version rather than silently
relabeling a draft.
Reader-visible confirmation remains owned by Typefully reconciliation.

Storyline updates and event associations persist in their own transaction before publisher
mutation preparation. The result is a code-owned set of keys successfully committed for this run.
Only that set, or a previously committed same-key association on replacement, may enter mutation
materialization and `posts.storyline_key`. If any storyline persistence fails, delivery continues
with a null storyline link; memory never widens the publisher transaction or becomes a delivery
dependency.

### 5. Remove Node-theme authority from the v2 desk

Keep consuming `wire-pulse-v2` candidates and preserve their authenticated, bounded discovery
provenance. Keep accepting optional theme fields for API backward compatibility and historical
report rendering, but change live v2 behavior:

- remove `node_curated` as a code-owned Haiku routing protection;
- rename any neutral attention label to `marketing_node_discovery`; provenance is not an
  endorsement;
- stop passing `theme_board`, theme IDs, or Node theme-coverage snapshots to Sonnet;
- remove theme IDs, theme names, and theme signals from the Haiku assignment cards as well;
- stop telling the v2 newsroom that Node themes provide continuity;
- retain exact-event hints and safe source references as untrusted discovery context;
- keep the legacy theme parser/diagnostics only where necessary for API compatibility and
  historical audit, not as a live editorial input.

Guide-account, operator, unresolved-research, exact-event continuity, and official-primary
protections remain unchanged. Node candidates may now be backgrounded by Haiku under the same
narrow rules as ordinary leads.

This sprint does not change the Marketing Node repository, endpoint, schedule, or authentication.
The Node remains a supplemental lead source while later architecture work decides whether it
should own more shared ingestion.

### 6. Audit and Desk visibility

Extend the existing decision record and Desk report to show:

- Haiku-suggested storyline keys per considered candidate;
- Sonnet-confirmed storyline key and relationship, when any;
- ignored storyline updates with bounded validation reasons;
- a compact read-only list of up to 12 recently updated storylines with summary, latest signal,
  last covered/open draft state, recent exact events, and watch-for notes;
- counts for indexed, Haiku-selected, initially supplied, retrieved, created, updated, closed,
  ignored, and output-linked storylines.

Do not add publish, merge, delete, or close controls in this sprint. Typefully comments and owner
feedback remain editorial guidance, not automatic storyline mutation.

Update the rolling audit to watch for duplicate storylines, incorrect Haiku mappings, missed
continuity, stale summaries, useful accumulated signals, context/token growth, and whether Node
leads appropriately stop at Haiku after losing automatic protection. The audit remains read-only.

## Failure and concurrency behavior

- Storyline memory is never a publishing gate. Read, parse, validation, or write failure is
  recorded and the existing exact-event/editorial path continues.
- Writes use `BEGIN IMMEDIATE`; existing-line updates additionally require an optimistic revision
  match, and new lines are insert-only. Duplicate delivery or worker restart cannot append the
  same run/item association twice, while a later run remains auditable.
- A model cannot rename or merge an existing storyline. Merging/aliases require later owner and
  audit evidence rather than an implicit overwrite.
- A closed storyline may be reopened only by an explicit current Sonnet update associated with a
  current candidate. Merely retrieving it changes nothing.
- Publisher mutations persist the nullable storyline key in their existing bounded materialization
  JSON. Reconciliation uses stored intent and does not recompute the association.
- The new tables and nullable post/preparation columns are additive. Older code ignores them, so
  rollback does not require database restoration.

## Files expected to change

- `nbn/store.py` — additive schema, bounded storyline index/cards/upsert/event association,
  post linkage, and audit reads.
- `nbn/desk_prep.py` — compact storyline index input and bounded key selection in the existing
  Haiku pass; remove Node routing protection.
- `nbn/newsroom.py` — relevant-card delivery/retrieval, prompt semantics, dossier contract, and
  isolated validation.
- `nbn/main.py` — persistence and output linkage after exact-event validation.
- `nbn/publisher.py` / publisher mutation materialization only where necessary to preserve the
  selected storyline key through create/replace/reconciliation.
- `nbn/report.py` — compact read-only storyline visibility and decision diagnostics.
- `SYSTEM.md`, `PROMPTS.md`, and the inbound-flow document — current ownership and flow.
- Focused tests in the existing store, desk-prep, newsroom, cycle, publisher, and report suites.

No Marketing Node files, source tiers, treasury policy, orientation brief, cadence, model choice,
corroboration policy, source receipt policy, Typefully thread format, or autopublish setting should
change.

## Verification

### Static and unit checks

- Additive migration works on an existing database and preserves all current rows.
- Storyline keys, strings, arrays, cards, index, events, and dossier updates honor exact bounds;
  corrupt JSON and malicious prose fail open.
- Haiku receives the bounded index within its existing request, selects only supplied keys, and
  produces no additional model call.
- `related_keys` remains exact-event-only and `related_storyline_keys` remains storyline-only.
- Haiku can background a Node lead; guide, operator, unresolved continuity, and official-primary
  protections still work.
- Sonnet receives only Haiku-selected full/retrievable storylines, never the complete ledger or
  Node theme board.
- A shared storyline never aliases exact-event keys, satisfies evidence, or changes UPDATE rules.
- Invalid storyline updates do not reject valid story/output decisions.
- Existing updates require a full card actually read by Sonnet and the matching `base_revision`;
  stale-run updates, concurrent creates, and reopen races fail open without overwriting memory.
- New, continuing, routine, turn, close, and explicit reopen persistence are idempotent and
  auditable.
- Same-run restarts do not duplicate event history; later-run changed dispositions remain visible
  and do not advance freshness beyond the underlying item observation time.
- Worst-case combined Sonnet packets stay within the existing total ceiling, with storyline prose
  compacted before candidate identity or inspected evidence.
- Output creation and draft replacement carry the stored storyline key without changing existing
  mutation fencing, source-reply confirmation, or duplicate protection.
- Manual Typefully publication reconciliation makes linked coverage visible through the existing
  post lifecycle.
- Dashboard rendering escapes untrusted text and exposes no mutation controls.
- Existing Node v2 packets with or without themes still parse and ingest.
- Neither Haiku nor Sonnet receives Node theme IDs, names, or signals; disabling storyline mapping
  does not restore Node routing privilege.
- Full unittest suite, Python compilation, focused Ruff checks for changed files, and
  `git diff --check` pass.

### Bounded non-publishing shadow fixture

Run the proposed Haiku/Sonnet contracts against a small fixture containing:

1. a later Coldcard attacker-fund movement matching an existing security storyline;
2. routine daily ETF flow inside an existing institutional-demand storyline;
3. a material CLARITY Act development inside an existing policy storyline;
4. an unrelated Bitcoin company announcement that should not be forced into a supplied line;
5. two superficially similar macro leads that belong to different storylines or none;
6. a genuinely new development that may explicitly reopen a closed storyline.

Expected qualitative behavior: relevant retrieval, no broad-theme event merging, routine signals
may update memory without requiring posts, meaningful turns remain eligible for coverage, and
Sonnet can reject Haiku's suggested mapping. The fixture does not publish or create Typefully
drafts.

## Review and rollout

1. Run the independent lead-coder review cycle. Challenge scope, data ownership, model authority,
   memory drift, key duplication, concurrency, migrations, context cost, rollback, Node-theme
   removal, publisher linkage, and whether any memory failure can suppress news. Iterate until
   approved.
2. Implement in small independently reversible commits: ledger/persistence; Node de-privileging;
   Haiku storyline retrieval; Sonnet maintenance and delivery linkage; report/docs. Node
   de-privileging and storyline retrieval are independently gated/revertible so disabling memory
   cannot restore `node_curated` routing.
3. Run all verification and the bounded non-publishing shadow fixture. If the shadow reveals an
   unresolved editorial tradeoff, stop before deployment; ordinary implementation defects are
   fixed within the approved plan.
4. Confirm production `NBN_AUTOPOST_ENABLED=false` and editor model remains Sonnet. Back up the
   production SQLite database and verify integrity.
5. Deploy NBN only. Confirm `/health`, `/status`, additive schema, one natural Haiku preparation,
   one natural Sonnet run when traffic warrants, model-call counts, context bounds, and unchanged
   Typefully reconciliation.
6. Do not synthesize a publishable story or Typefully draft for smoke testing. If natural traffic
   does not create a storyline immediately, verify the production read/write path with a
   transaction-rolled-back local fixture against a database backup and report live semantic
   observation as pending.
7. Keep the read-only rolling audit active and evaluate several natural runs before expanding the
   ledger, adding controls, or retiring more ingestion paths.

## Rollback

- Revert the report/docs commit independently if visibility is noisy.
- Revert Sonnet storyline maintenance and output linkage while leaving additive stored rows inert.
- Revert Haiku mapping and restore the prior packet; Node theme fields remain safely accepted by
  the API parser. Do not restore `node_curated` automatic protection unless production evidence
  shows a recall regression attributable to its removal.
- Revert the ledger readers/writers last. Additive tables and nullable columns may remain; older
  code ignores them. No destructive migration or database restore is required.
