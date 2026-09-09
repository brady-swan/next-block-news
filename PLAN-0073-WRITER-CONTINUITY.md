# Sprint 0073 — audience, reporting continuity and useful recall

September 9, 2026. Owner-authorized turn `01a0877a-d077-7c02-b8de-2229b7410228`.
Status: independently APPROVED; implemented and production smoke-tested September9.
Runtime2276766/v2.35. Release measurements and audit status: SPRINT-0073-FINDINGS.md.

Scope authority: [agreed roll-up](docs/planning/writer-work-sprint-2026-09-09.md).
The owner approved all five decisions and made the next-shift letter a required deliverable,
including no-post Writer sessions. Current runtime0374290/v2.34 and preceding sprints are
complete, not work to redo. Dedicated audit confirmed PAUSED18:44:13UTC, no shared-code work
or uncertain mutation pending. Autopost remains OFF throughout this sprint and afterward.

## Outcome and architecture

Keep the existing single-run Writer, independent Editor, publisher and run-centered Desk.
Improve what reaches that Writer, what it remembers, and what it deliberately follows up.
No new researcher, editorial model/effort change, cadence increase, personal KB import,
QMD installation, publication quota, or requirement to use a tool in every story.

Small additive modules should carry the new storage/retrieval lifecycle; avoid further
inflating the main orchestration and dossier validator. Existing validated receipts and
exact-event identity remain the only route into normal Editor/delivery materialization.

## Phase A — audience and source interactions

1. Replace the two audience sections of prompts/orientation-brief-v2.md using the approved review
   document, including conversational awareness. Reconcile the narrower topical language
   in intake_triage, desk_prep and active Editor/Writer prompts. Preserve ordinary evidence,
   freshness, treasury-company, software-release, source-reply and writing-style boundaries.
   Add the approved calibration anchors without putting the whole evaluation set in prompts.
2. Add Peer-to-Peer RSS using its verified feed, Kobeissi to GUIDE_HANDLES without changing
   its Tier2 evidence classification, and the four-row approved expert cohort in explicit
   source configuration. Reconcile existing live list/query membership to avoid redundant
   queries; do not mutate the public X list or subscribe the whole KB graph.
3. For this cohort, collect original posts plus replies, quotes and reposts in bounded
   from-account queries. Reuse lead_material.capture for referenced originals/parents/media.
   Preserve each interaction's own X URL as candidate identity even if it has one external
   link; preserve the expert actor, interaction type, original target ID/author/date, and
   unavailable parent context. Never give a parent the expert's authority or retweet time.
4. Query-cursor migration is deliberate: new cohort queries bootstrap a small recent window
   and use the existing acknowledged pagination checkpoints/idempotent insertion. Avoid a
   full historical sweep. Shared originals remain one evidence source, not corroboration.
   Expert items get normal topical preparation, not automatic guide-style protection merely
   because an expert reposted them. Kobeissi retains its separately approved guide role.
5. Reframe existing Perception survey/search topics toward the approved audience and reporting
   questions. Reuse supported adapters, quota pools and caches; no new vendor workflow suite.

## Phase B — required handoff and active reporting assignments

### B1. Next-shift letter

- Add required nonblank `shift_letter` to the normal v2 dossier, bounded to roughly4,000
  characters (a safety ceiling, not a target). Instructions make this part of completing
  every Writer session, including drop/no-change runs. Capture concrete judgment, useful
  routes, corrected assumptions and open questions; no optional nothing-to-add escape,
  generic performance report, forced length or invented lesson.
- Store in `writer_handoffs`, keyed by run_id, with written_at/model/prompt version and body.
  Persist the first useful returned letter before Editor/delivery. Idempotently preserve it
  through the existing one-shot receipt/identity repair and later patch. A missing/blank letter
  can itself trigger that SAME shared correction slot when time/round capacity remains,
  coalesced with receipt/identity corrections: no new slot, budget or dedicated letter call.
  It gets an explicit incomplete-handoff observation and must not silently become a
  valid blank. If correction cannot run, preserve useful stories and expose the failure.
- Optional `desk_feedback` remains human-only and separate; it is never indexed or injected.
  Per-story reporting_note is also distinct. Prep-only/empty cycles did not run a Writer and
  do not fabricate letters or wake a model solely to write one.
- Inject the latest preceding letter prominently with its timestamp/run ID and clear viewpoint.
  Join actual later Editor/commit/publication outcomes dynamically, not by rewriting what the
  Writer supposedly witnessed. Older letters are searchable within existing30-day memory.
  Keep this small section through packet compaction; don't increase the64KiB packet budget.

### B2. Follow-up storage and Writer contract

- Add `writer_followups` (stable ID, context_id, question, source pointers, next_check_at,
  state, revision, last_check_at/outcome/notes, queued assignment ID, originating run/date)
  and an append-only `writer_followup_checks` ledger (followup ID, run/check ID, assignment
  candidate ID, due/started/completed times, status/result). These are reporting tasks, not
  another source of facts or an editable duplicate of the story notebook.
- Add bounded `follow_up_updates` to the dossier: nominate/reschedule/close a watch and
  report the current check's outcome. Target a current candidate notebook or a storyline
  actually read/created in this run, not an invented old key. Keep exact events separate
  from broader storylines. Echo revisions for existing work; use run IDs for idempotency.
- Writer specifies the useful question, where to look and an appropriate next check;
  support15minutes through7days, clamped only to operational scheduling bounds. No-change
  results can extend the interval or close the watch. No research or post quota. Do not
  turn all letter text into tasks or schedule every story by default.

### B3. Due work through the existing pipeline

- Evaluate due work only at the existing editorial cadence, without adding it to force_desk.
  Internal assignment backlog also cannot trigger editorial_run_soon cadence acceleration.
  Admit up to2 due assignments per desk within the current25-candidate envelope; this is a
  workload bound, not a publication quota. Leave excess watches due for later runs.
- Bridge into the existing candidate-based evidence/Editor/delivery flow using an explicitly
  internal assignment row: `discovery_origin=followup`, source `NBN follow-up`, its own stable
  assignment ID/internal URI, no article publication date, plus original context and source
  pointers. Leave item.story_key UNSET at creation; watched event keys belong in context and
  the supplied exact-key set, not candidate identity, so a distinct new development remains
  possible through existing identity validation. It is a real reporting assignment, NOT a
  claim that an external article arrived.
  Keep external fetched/new-source counts separate. Desk and packet identify it as internal.
  Old observed evidence retains its date; an assignment timestamp never refreshes an event.
- Create the row/check atomically under the existing single-worker lease. One queued
  assignment per watch; retries reuse it rather than minting another candidate. Pending-item
  hydration preserves the follow-up metadata; prep protects due work from disappearance, while
  the Writer remains free to find no development. Skip pointless prefetch of internal URIs.
- A due-only desk can therefore research original sources and submit a genuinely new sourced
  story with the assignment as member_candidate_id. It must still supply current inspected
  receipts and a correct exact-event relation/key. This reuses all existing Editor/output
  safeguards and does not reopen or rewrite the old published item's state.
- When fresh related candidates are present, show the same context/follow-up ID and let the
  ordinary grouping handle them together. Exact matching can avoid a redundant assignment
  where justified; semantic similarity must not silently merge events. Check completion and
  repeated-worker recovery are idempotent whether one or several candidates informed it.
- Separate actual check outcome from delivery outcome: new information may still be dropped
  by Editor. Missing check report/model timeout is inconclusive/technical, never no-change.
  Reuse a pending assignment for retry with bounded backoff; expose repeated failures in Desk.
  A completed check does not advance storyline.last_signal_at unless genuine new external
  evidence warrants it. Do not make a no-change assignment count as a fresh story signal.

## Phase C — lightweight meaning-based retrieval

1. Add a small memory-search module using existing SQLite for substantive projected documents,
   chunks and vector cache. Sources: notebook reasoning/evidence, dated receipt/research text,
   storyline summary/watch_for and letters. Exclude navigation/index listings, repetitive tool
   envelopes, optional Writer feedback, credentials/configuration and the personal corpus.
2. Paragraph-aware chunks around1,400characters, split long paragraphs; prefix documents with
   `search_document:` and queries with `search_query:`. Cache key includes model digest,
   prefix/chunking version and content hash. Reuse unchanged vectors and deduplicate results
   to best chunk per document. Keep references to other context available through normal reads.
3. Preserve exact-ID/run-ID lookup and stable empty-query catalog pagination. For a query,
   combine ranked partial keyword matches with linear cosine retrieval using a transparent
   rank merge. Hydrate every result against current revision/expiry and actual output state.
   Similarity retrieves context only; it never establishes truth, duplicate status or identity.
4. Incremental bounded indexing runs in a background worker with its own SQLite connection
   and at most one outstanding embed request, never awaited in the minute intake worker or
   Writer model loop and outside SQLite write transactions. Atomically activate a completed
   document projection only if its source
   revision still matches. Expired/deleted/changed records cannot be resurrected by old vectors.
   Initial backlog catches up in small batches without stalling minute intake or Writer runs.
5. Use Ollama `/api/embed` with `truncate=false`, bounded request deadlines and shape/dimension/
   finite-number validation. Model/digest unavailable, partial index, timeout or malformed vector
   falls back to useful keyword search with honest diagnostics. Search uses existing local
   retrieval call/byte limits, not a new large context budget.
6. Packaging: private companion Railway service `nbn-embeddings`, pinned Ollama Linux image
   (upstream release0.33.3 checked; verify image availability), nomic-embed-text:v1.5 with
   actual digest recorded, persisted model cache, no public domain or API credentials. Keep
   resource limits modest and measure before enabling NBN use. No laptop dependency. Model
   prewarm/bootstrap is bounded and model absence never prevents NBN startup/keyword search.
   Check cold/warm query latency, batch indexing, resident memory and restart/cache survival.
   This is hosting usage, not paid model tokens; document measured rather than guessed cost.
7. QMD remains reserve only. Tests compare the new lightweight retrieval with current lexical
   behavior on held-out NBN queries, exact identifiers and similar-but-distinct events. Do not
   install a second backend or perform a new broad paid model bake-off.

## Desk, documentation and release

- Preserve the existing approved layout. Add a readable per-run next-shift letter plus actual
  outcomes, incoming handoff provenance, due/completed check cards and retrieval results/health.
  Place active watches and embedding model/index/fallback diagnostics on existing appropriate
  system/research views. No new navigation redesign or writable admin tools in this sprint.
- Distinguish external intake from internal assignments and observed evidence from Writer notes.
  Required letter presence is inspectable; no automated prose grader or scoring incentives.
- Update SYSTEM/HANDOFF/config/source documentation, prompt versions and focused audit checks.
  Keep the audit's existing autonomy and quiet-notification rules. Audit lane owns its checkpoint.
- Test: audience consistency; full interaction/parent identity and cursor recovery; no-post
  required letter, protocol repair preservation, later Editor/publication overlays; due-only
  sourced story, due-only no-change, fresh collision, failure/restart idempotency; preserved
  signal dates; exact/lexical/semantic recall and stale projection; offline fallback; Desk/API
  render/build and existing regression suite. Do not claim unit fixtures prove editorial gains.
- After independent implementation approval, create an online SQLite backup and deploy ONLY
  clean reviewed source, leaving unrelated dirty evaluator/audit files untouched. Additive
  migrations are safe for rollback; embedding/follow-up flags can be disabled independently.
- Verify target/replica/volume/autopostOFF, health, prompt/source hashes, embedding CPU/cache,
  authenticated Desk and a natural worker cycle. Test due-only plumbing in isolated DBs rather
  than manufacturing an old live story or publishing content. Existing normal drafts may flow.
- Resume SAME audit in its dedicated task only after release smoke; add watches for useful
  expert interactions, due check outcomes and timing, letter quality/continuity, semantic
  retrieval utility/index lag, repeated unnecessary checks, and actual cost/latency.

## Review focus

Check the internal-assignment bridge carefully: no fabricated external intake/evidence, no old
item mutation, no false freshness, and full due-only discovery-to-normal-Editor path. Check
required handoff behavior without a new publication blocker, and embedding failure/cost isolation.
Keep fixes proportionate; this is one wire newsroom, not a general workflow or vector platform.
