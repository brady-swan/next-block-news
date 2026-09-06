# Plan 0061 — Run-first Desk: data map

Date: 2026-09-06. Phase 1 complete; interface design and implementation remain pending.

Scope: map existing records, identify the smallest missing observations, and recommend supporting
views. This is not an editorial or runtime change. The rolling Codex audit is **paused at Brady's
request**; NBN intake, newsroom runs, and Typefully delivery continue. Autopost remains OFF.

Based on local code and bounded, read-only production inspection, including the production
snapshot around 16:25 UTC on September 6. Live counts below are examples from that snapshot,
not a current health report or a claim that every historical record has the same shape.

## 1. The organizing object is a run

Open the current/latest recorded production newsroom run. Previous/Next moves the entire
workspace through runs, across dates. A run with no output is still useful: it explains what the
desk considered and why nothing advanced. A source poll with no newsroom session is not a run.

The central question is:

> What did we give the newsroom, what did it decide, what did the editor do, and what happened next?

The main view should answer this with concise story rows and a selected-story inspector, not a
wall of telemetry. Use the extra-wide layout for side-by-side context and copy comparison.

### Identity and clocks

| Object | Identity | Meaning and limitation |
| --- | --- | --- |
| Run | `newsroom_runs.run_id` | Stable selection and deep-link anchor. Order by `created_at` plus a stable ID tie-breaker, not list position. |
| Input candidate | `items.url_hash` | A retained intake item; several candidates can support one story. Current item status is not its historical run disposition. |
| Story in a run | `(run_id, story_id)` | The writer's proposed story and downstream handling in that run. `story_id` alone is not globally unique. |
| Event across runs | Canonical story key and aliases | Links retries and updates. Aliases can change later; distinguish the submitted key, the effective key at the time, and today's canonical identity. |
| Storyline | `newsroom_storylines` key | Broader ongoing context, not a substitute for event identity or a run. |
| Delivery attempt/output | Publisher mutation ID, local post ID, provider reference | A Typefully draft ID is not an X publication. A confirmed mutation means the requested delivery operation succeeded, not necessarily that readers saw the post. |

Keep three clocks explicit:

- **Selected run:** recorded inputs, decisions, copy, and outcomes at that time.
- **Output now:** later edits, scheduling, publication, or failure, with a last-checked time.
- **System now:** current worker/source/publisher health, independent of the historical run selected.

Browsing history pins the run. New arrivals do not move the selection. Back to latest resumes
following. Older runs using a different architecture/model must retain their own labels; today's
configuration must not be presented as their configuration. Production/replay provenance needs
an explicit, verified filter, not an assumption that every run header is a normal production run.

## 2. What we can actually show

Availability below means recorded evidence, not what we could infer plausibly.

| Question in the interface | Existing record | Availability / presentation rule |
| --- | --- | --- |
| When did this run start and finish? What was its result? | `newsroom_runs`: timestamps, status, error, model, prompt version, counters | Available. Status is a checkpoint, not a detailed live stage trace. A completed run does not mean it produced or published a post. |
| What was in the captured intake pool? | Run `inventory_json` joined to `items` | Item IDs are recorded. Original item text is bounded; current enrichment can differ from what the writer saw. Label this the captured pool, not the exact writer packet. |
| What did Haiku keep out? | `intake_triage`: route, reason, batch, outcome, timestamps | Available for recorded intake decisions. This is upstream work and may predate the selected run. Do not attribute its whole batch or cost to one desk run. |
| What did Luna advance or background? | `desk_preparations`, keyed by run and item | Good run-scoped routing, summaries, source pointers, related keys and application state. Only applied decisions change the delivered pool. Background is not a writer rejection. |
| Exactly what reached the writer? | `_initial_packet()` and later context-tool responses | **Not fully retained.** The final packet is assembled and compacted in memory. Initial byte count is stored, not the exact packet. Indexed/available context is not the same as content delivered. |
| What context did it retrieve during the run? | Aggregate context counters; mutable story memory and context stores | Counts survive; exact returned records/omissions generally do not. Cannot reconstruct a faithful historical desk from today's workbench. |
| How did it group leads and what did it recommend? | `newsroom_runs.dossier_json`: decisions and stories | Available for retained, valid dossiers. Shows membership, proposed keys, publish/drop/defer recommendations and explicit explanations. Preparation backgrounds must be shown separately. |
| What did the writer write? | Story `post` in the stored dossier | Proposed copy is retained. This is not automatically editor-approved or submitted copy. Invalid/absent dossiers need an explicit unavailable state. |
| Which searches and sources did it use? | Run counters, `search_activity`, current source-resolution/evidence records, story memory | **Partial.** Aggregates exist; the complete per-run sequence, source text, failures and returned search results do not. Current caches/evidence rows are not historical truth. |
| Did the editor actually see this story? | Commit details; model-call metadata; editor code path | Partial. Pre-editor validation, payload-capacity handling, and failure-preserving fallbacks can stop or bypass a true verdict. Do not label every downstream hold as an editor decision. |
| What did the editor decide/change? | Commit `details_json.editor`; mutable editor feedback | **Important gap:** delivered stories lose their saved editor details during publisher finalization. Full per-run editor copy/input is not reliably retained. |
| What was actually sent to Typefully? | `publisher_mutations.materialization_json` | Retains submitted body, short editor note, run/story linkage and delivery context for recorded mutations. Useful fallback for submitted copy, but not a substitute for the full editor response. |
| What is the output's status now? | `posts`, publisher mutations and reconciliation state | Available for locally tracked outputs, with freshness/scope labels. `posts.body` can change later; it is not an immutable record of an old run's copy. |
| Was it published on X? | Reconciled publisher status, confirmation timestamp and public URL | Show confirmed publication separately from draft, scheduled, immediate delivery intent, uncertain or failed. Never infer publication from the writer's recommendation. |
| Why was something dropped or deferred? | Dossier reason, prep result, commit validation/editor detail, current item state | Usually available but from different stages. Preserve actor and timing. `held` alone does not mean awaiting research or scheduled for retry. |
| What does this run cost? | `model_usage` linked by run/seat plus stored run counters | Recorded actual/reported or rate-estimated usage, with unknown-cost flags. Shared batch costs are not exact per-story costs. Input/output/cache token detail belongs in the inspector/System. |
| How long did each stage take? | Run start/end, model-call latency, some pipeline events | Total duration and call latency are available. Full exact stage timing is not. Do not build a precise waterfall from estimated call starts or deduplicated events. |

### Counts must preserve their units

Use labels such as **8 captured leads → 4 delivered leads → 1 proposed story → 1 staged draft**.
These are different units, not interchangeable funnel totals. Source companions marked handled
or skipped may have been merged into a successful story rather than rejected.

Separate the writer's recommendation, editor verdict, run outcome, and output's current state.
Useful display states include: not sent, dropped by writer, research deferred, stopped before
editor, dropped by editor, delivery pending, staged, confirmed published, failed, and uncertain.
Use these only when the records support them. Otherwise show “not recorded” or “partial history.”

### Research output and quality — approved addition

Research is a substantive work product, not just tool activity. The selected run and its story
inspector must expose the assignment, returned findings, supporting sources, unresolved questions,
downstream use by the writer/editor, and attributable effort. Distinguish a discovery link from
an inspected supporting receipt, a researcher finding from the writer's inference, and an actual
research return from an audit annotation.

Owner/audit review should ask whether the research answered the assignment, used relevant and
timely evidence, separated support from inference, spent proportionate effort, and translated into
good copy. A well-supported drop can be a good research result. No additional grading model,
automatic quality score or new publication threshold is part of the prototype.

Historical missing returns remain missing. An explicitly authored illustrative return can show
the intended presentation in the prototype, but must never be attributed to a past model session.
The recording additions below must capture the actual research deliverable and its downstream use,
not merely search counts, URLs and error totals.

## 3. Three real runs the design must handle

| Recorded run | What happened | Design consequence |
| --- | --- | --- |
| `cycle:1788700036:f741b64b` — BPI | 8 inventory items; 4 advanced and 4 backgrounded; writer dossier with 4 candidate decisions and 1 story; Typefully delivery succeeded. Current output was a draft at inspection. | Show the narrowing correctly and distinguish staged from published. Writer copy and submitted body survive, but the commit now contains only delivery detail, not its original editor result. |
| `cycle:1788707454:ca08a92e` — mempool music | 8 inventory items; 4 advanced; 1 proposed story. Editor dropped it as an art/demo item without a sufficiently relevant development. Commit state is `held`. | Say “Dropped by editor,” with the actual rationale. A generic held badge would misleadingly suggest unfinished corroboration. |
| `cycle:1788711140:e992c915` — Strive warrants | 4 advanced leads; 1 proposed story; handling stopped before the editor because a material update had no visible base. The older commit remained `pending`. | Do not animate it as active work or invent an editor verdict. Show the historical inconsistency and the recorded pre-editor reason. The previously deployed lifecycle fix does not rewrite this old row. |

In the sampled trailing 24 hours, all five delivered story commits lacked their editor object;
six of nine held commits retained one. This confirms the delivery overwrite is a real limitation,
not merely a theoretical schema concern. It does not imply the editor failed to run.

## 4. Small recording changes needed before the final interface

These support the dashboard; they do not change editorial judgment or add a new orchestration system.

1. **Save the delivered desk.** Capture the actual sanitized writer packet after final compaction,
   its effective prompt/configuration version, and subsequently returned context. Distinguish
   inline material, an index of available material, and content actually delivered by a tool.
2. **Preserve editor history.** Retain editor input, verdict, explanation and returned copy per
   run/story, including whether it was an actual response, an omission recovery, or a fallback.
   Publisher finalization should append delivery detail rather than replace prior editor detail.
3. **Record a bounded run activity trail.** Stage start/end, tool kind and outcome, source/evidence
   references, relevant safe text, and delivery transitions. Capture observations already being
   produced, not hidden reasoning or extra model calls. Record the effective event identity at
   decision time. Expose partial/truncated traces honestly.
4. **Persist lightweight source-poll health.** Last attempt, success, result count and error for
   RSS feeds and source/query bundles. Successful empty polls must be distinguishable from errors,
   disabled sources and not-yet-due polls. This needs no extra paid polling.

Use the existing Python service and SQLite. One small run-observation mechanism plus source-health
records is enough; no event bus, tracing service or new editorial framework. Define explicit byte
bounds and recording failure behavior during implementation. Never expose credentials, publisher
ownership tokens, arbitrary raw provider responses, or private reasoning in the browser.

Start by aligning rich trace retention with the existing 14-day rich run-history window, retaining
lightweight run headers and outcomes longer. Historical views must label trimmed or unavailable
payloads. Older terminal runs can already lose inventory/survey/dossier data through pruning;
having a run header does not guarantee a full reconstruction. Review storage sizes before choosing
the final artifact budget. Recording failures must not hold up normal editorial work.

Do not reconstruct missing historical editor responses with a model. Submitted copy recovered from
a publisher mutation can be shown as “submitted copy,” with an explicit provenance label.

## 5. Supporting views: what is useful without recreating the wall of text

| View | Main question | First useful version |
| --- | --- | --- |
| **Newsroom** — default | What happened in this run, and why? | Run navigation; concise story/input rows; linked preparation/writer/editor/outcome detail; readable copy comparison. Filters for research defers, drops and writer/editor disagreements. |
| **Intake & Sources** | What arrived, and what never reached the writer? | Source/provenance, original lead/time, Haiku and preparation decisions, guide-account coverage, oldest eligible waiting items. Filter Background for owner review. Source health sits beside source activity. |
| **Outputs** | What is ready, live, changed, or stuck? | Locally tracked Typefully/X inventory, source-reply context, actual submitted copy, current status and original-run link. Separate confirmed publication from staging and ambiguous delivery. |
| **System** | Is the operation healthy, timely and affordable? | Exceptions first; worker/source/model/search/publisher status; latency and cost by run/seat/day; clear clock and measurement scope. Full configuration is secondary detail. |

**Tuning review is a workflow inside these views**, not a fifth sprawling dashboard. Open the run
or filtered decisions beside the existing examples/feedback record. Let the owner see missed
opportunities, questionable passes, excessive research and copy changes in context. No new model
scoring, quotas, publication thresholds or automatic policy changes are needed for this redesign.

**Storylines belong in the inspector initially.** Show the context relevant to the selected story,
its related runs and output history. A dedicated storyline browser can follow if actual use calls
for it; it should not crowd the initial navigation.

For missed-story review, show the guide's lead and NBN's path through intake and decisions. A peer
posting something is a review opportunity, not proof NBN made a mistake. Separate “not ingested,”
“filtered,” “deferred,” “already covered,” and “not worth posting.”

The current publisher reconciliation is not a complete mirror of the Typefully account. It does
not import every draft or comment. Label local scope and link to Typefully; any additional remote
read sync should be an explicit later addition, not a side effect of opening the dashboard.

## 6. Health checks that would actually help

The main workspace needs only a calm health summary and an exception count. Put the diagnostics
below in System, with links from a real problem to its affected source, run or output.

| Check | Useful question / signal | Existing support and gap |
| --- | --- | --- |
| Worker and display freshness | Is the worker progressing? Is the page showing fresh data? | Current-process heartbeat/cycle state and snapshot generation time exist. Distinguish these from a persisted last success before a restart. |
| Desk due/backlog | Are eligible leads waiting beyond the next due desk, or is this a quiet period? | Next-run deadline, item timestamps and deferrals exist. Count eligible work, not every `new` item. A pre-run budget failure can leave no run header, so show it as an operational issue. |
| Intake completeness | Did each enabled source poll successfully? Is there a partial provider failure? | Node has useful attempt/success/error records. Other sources rely heavily on logs/in-memory timing/cursors and need the lightweight records above. Zero new items is not failure. |
| Node freshness | Did we consume a fresh upstream pulse or repeatedly read an old one? | Show upstream generation time separately from our last successful fetch. Respect its cadence, partial-provider state and disabled/off-hours configuration. |
| Model/protocol outcomes | Are calls timing out, failing parsing, omitting decisions, or falling back? | Usage, preparation and run outcomes cover much of this. A transport-level `ok` can precede a schema failure; do not present it as a successful editorial result. |
| Research/search | Are quotas, backoff, blocked fetches or repeated failures preventing useful research? | Search-provider state and aggregate counters exist. Source-specific run failures need the new trail. Native-search calls are an available path, not a required success metric. |
| Delivery and reconciliation | Are drafts staged? Are uncertain operations aging? Is publication confirmation stale? | Durable mutation state and publisher sync timestamps exist. Keep autopost OFF/ON visible, but do not conflate its being OFF with an outage. No dashboard-triggered publishing/probes. |
| Lifecycle consistency | Does a completed run leave unexplained pending work, or do records disagree about retry state? | Compare run, commit, item and publisher records. Surface the contradiction rather than relabeling it as a legitimate active stage. Current memory alone is not proof a retry is scheduled. |
| Speed | Where was time spent: intake lag, waiting for a desk, model/research, editing, delivery? | Some timestamps exist; exact stage timing needs the trail. Peer-post-to-draft time is distinct from NBN-first-seen-to-draft time. Unknown source publication times remain unknown. |
| Cost | What do runs, days, weeks, months and individual stages cost? | Run/seat usage exists. Provide period totals, direct per-run averages, completed-calendar-period averages and stage attribution; see the cost contract below. Never present this as the full provider invoice. |

### Cost review contract — owner addition, September 6

**Model roster panel:** show the active production configuration by role: intake, assignment /
storyline recall, delegated research, writer, editor and the separate daily receipt audit. Include
provider, exact model ID, effective effort (or explicit no override), enabled/disabled/shadow mode
and on-demand usage. Read an allowlist from the running process's resolved configuration, not the
latest usage rows, cost history or a documentation constant. Timestamp the roster independently
from selected historical runs and the cost observation clock. Configured does not mean currently
executing; historical run details retain their own recorded model. The prototype contains a
read-only 12:56 PM Central configuration snapshot. Do not expose general environment variables,
credentials or add settings controls. Publishing/reconciliation are code paths, not model seats;
the separate Marketing Node/source services are outside this editorial roster.

The System prototype now includes this view using a read-only aggregate ledger snapshot at
12:45 PM Central on September 6. Production implementation must use bounded live ledger queries,
not the fixture. No new model calls, pricing lookups or provider billing requests on page refresh.

- **Period totals:** today through observation time, current Monday–Sunday week to date, current
  calendar month to date. Show the exact observation time and available coverage; the ledger
  currently begins September 2 at 7:14 AM Central, not the beginning of the week/month.
- **Average per newsroom run:** sum known, directly attributed non-intake usage for the selected
  period divided by distinct metered production newsroom run IDs, not model calls or published
  posts. Include metered unsuccessful/no-output runs. Do not invent zero cost for missing usage.
  Usage is time-bucketed by its recorded timestamp. Deduplicate run IDs across midnight for
  multi-day totals. A single selected run's lifetime cost is a separately labeled calculation.
- **Average per day/week/month:** completed Central calendar units inside the ledger's covered
  history. Exclude the partial opening/current units; count zero-call days inside an otherwise
  covered window. Show the denominator and range. No complete week/month yet means unavailable,
  not $0 and not daily average multiplied by 7/30. Any future run-rate forecast must be separate.
  Blended model-roster history is not a forecast of the current roster.
- **Stage mapping:** `rss_triage` → intake filtering; `desk_prep` → preparation;
  `research_assistant` → separately billed research; `newsdesk` → writing AND embedded desk
  research; `editor` + `editor_recovery` → editing. Keep an explicit Other category if additional
  seats appear, so stage totals always reconcile. Show stage spend, share, calls and linked
  cost per metered run. Shared intake is not allocated to an arbitrary newsroom run; preparation
  with no newsroom record also remains shared. No separate research call does not mean no research.
- **Billing basis:** separate provider-reported from rate-estimated amounts and unknown-cost
  calls. Preserve known subtotals/unknown flags; totals and averages with unknown components
  must be labeled incomplete/lower bounds, never interpreted as fully metered. xAI reported
  totals already include native tools; do not add them again. Preserve historical rate versions.
- **Scope:** exclude marked replay/evaluation/shadow/draft-test traffic, with excluded cost
  visible. The prototype's production sample contains only `cycle:` IDs and excludes joined
  newsroom modes other than `live`; standalone production intake cycles remain included.
  Unclassified future identifiers need an explicit bucket, not silent omission.
- **Outside the ledger:** source/external search services, hosting, Typefully, legacy receipt
  audit and Codex usage. Publishing is not a separately billed model seat. They remain labeled
  unmetered; adding full provider billing or new paid telemetry is outside this UI sprint.

Cost math and rendering tests must cover stage reconciliation, no double-counted native calls,
shared versus direct costs, distinct runs across dates, partial calendar periods, missing/unknown
cost, no-call days, model-roster changes, and mobile/extra-wide views. If retention has removed
coverage, expose the gap; do not infer zero-spend calendar units from a pruned ledger.

Avoid multiplying alarms. Show the symptom, affected work, last known success, and an understandable
reason. A no-output run, quiet source, editor drop or deliberate defer is not itself unhealthy.
Thresholds should reflect existing schedules/timeouts, not impose new editorial standards.

One specific labeling correction to carry into implementation: `counters.fetches` currently counts
successful new captures, not every HTTP fetch attempt. The current “Fetch attempts” presentation
should not be reused for that counter.

## 7. Implementation anchors

These are the important code locations inspected for this map, not a request to change them yet:

- `nbn/store.py`: run schema/start/validation/pruning; preparation records; mutable story memory;
  model usage; publisher mutations; `finalize_publisher_mutation()` replacing commit details.
- `nbn/newsroom.py`: `prepare_desk()`, `_initial_packet()`, `_read_desk_context()`, `conduct_v2()`;
  in-memory fetch records and aggregate tool counters.
- `nbn/editor.py`: `_batch_editor_payload()` and `review_newsroom_batch()`; bounded input,
  copy/decisions, omission recovery and fallback handling.
- `nbn/main.py`: preparation application, writer/validation/editor/delivery sequence; pre-run
  budget checks and lifecycle state writes.
- `nbn/publisher.py`: locally scoped publication reconciliation and its clock.
- `nbn/desk.py`: current read-only snapshot and current-process health; existing auth boundary.
- `nbn/sources.py`, `nbn/node_discovery.py`: source polling and the uneven persistence of health.

Existing `pipeline_events` is deduplicated by item/event, so it is not a complete append-only
per-run timeline. `desk:last_decision_run` is a latest-only snapshot, not a historical run store.
Short-lived search caches and mutable source evidence must not be used to invent old traces.

## Stop point / next step

Mapping is complete. Present this to Brady before proceeding. The next phase is a high-fidelity
responsive prototype, using sanitized real examples and clearly labeled illustrative states where
new recording is needed. The separate lead review, implementation, production verification and
audit restart remain later steps in Plan 0061. No runtime fix, UI build, deployment or restart of
the audit was performed as part of this mapping task.
