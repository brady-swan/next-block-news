# Plan 0054 — Output idempotency, editor recovery, and desk hygiene

## Objective

Stabilize Editorial Core v2 without redesigning its editorial judgment. NBN is now producing
useful work; this sprint removes mechanical failure modes that create duplicate Typefully output,
waste Sonnet attention, obscure conversion latency, or make the Marketing Node theme path look
healthier or less healthy than it is.

The central invariant is **one active output per canonical event**, not one draft:

- while autopublish is off, later same-event evidence updates the one still-open NBN Typefully
  draft when it is safe to do so;
- when autopublish is on, an already reader-visible event is not posted again merely because a
  new outlet repeats it;
- after publication, a genuinely material new development may become a separate `UPDATE:` post;
- a material development arriving before an open draft is published is folded into that draft,
  because readers have not yet seen the original version.

Editorial calls remain with Sonnet and the independent editor. Code enforces output identity,
API idempotency, bounded payloads, and honest telemetry only.

## Observed production evidence

- On September 4, the Coldcard Wave 3/THORChain event already had Typefully draft `10606656`.
  A later TFTC signal used the same canonical event family, the batch editor omitted the story,
  and the fallback created draft `10627075`. Exact body/receipt dedup did not catch the semantic
  duplicate.
- The batch editor currently retries neither a missing decision nor a partial response. One
  omitted story therefore bypasses independent judgment and is staged immediately.
- A recent 23-item assignment-desk packet exceeded its 48 KiB limit. The failure mode correctly
  advanced everything, but that gave Sonnet the noisy full batch and defeated the cost/attention
  purpose of Haiku.
- X intake recently passed generic replies, thank-you fragments, and sponsorship copy from guide
  and company accounts into the pipeline.
- The live Node pulse at run `181219` reported 79 active themes, 14 qualified candidates, and zero
  classifier or taxonomy matches. NBN parsed zero signals because the producer emitted none; this
  is not an NBN schema-rejection event. The cause is not yet proven.

## Scope boundaries

- Preserve the current Sonnet newsroom/editor models, 15-minute cadence, source standards,
  corroboration posture, orientation brief, treasury policy, and Bitcoin scope.
- Preserve `NBN_AUTOPOST_ENABLED=false` through deployment. This sprint must nevertheless be
  correct when the owner later enables it.
- Do not turn a Node theme into evidence, event identity, corroboration, a quota, or a publishing
  mandate. Do not loosen theme matching without evidence of a specific defect.
- Do not use exact-string similarity as semantic story identity. Canonical family plus an explicit
  Sonnet relation supplies identity; code validates state consistency.
- Do not overwrite a Typefully draft that the owner edited or annotated after NBN created it.
- Do not retry an ambiguous Typefully create or patch. `UNCERTAIN` remains reader-covered because
  another attempt could duplicate a live scheduled post.
- No destructive database migration and no new dependency.
- Preserve the owner's modified `prompts/orientation-examples.md` and untracked audit/reference
  files.

## Architecture

### 1. Explicit relation to prior output

Add a required `coverage_relation` to each v2 publishable story:

- `distinct` — a new exact event;
- `same_event` — another lead/receipt for an existing exact event;
- `material_update` — a genuinely new development to a reader-visible exact event.

This is Sonnet's editorial/semantic judgment, not a code classifier. `existing_cluster_key` remains
the only way to name a supplied prior canonical cluster. Validation enforces only coherent shape:

- `distinct` cannot claim an existing cluster;
- `same_event` and `material_update` must name a code-supplied existing cluster or resolve through
  the candidate's existing canonical family;
- `material_update` against reader-visible output must begin with `UPDATE:` under the existing
  hard rail;
- an event with only an open draft is not reader-visible, so new material consolidates into that
  draft rather than creating an `UPDATE:` post.

The coverage board will explicitly state these output semantics so Sonnet does not confuse an
open operator draft with public coverage.

### 2. Canonical output-state rail

Add one store query that resolves the complete canonical alias family and returns output state
with this precedence, regardless of row recency:

- `open_draft` — locally known Typefully `DRAFT`;
- `reader_visible` — `IMMEDIATE` or `UNCERTAIN` using effective publication time;
- `none`.

`reader_visible` always outranks `open_draft`, and `open_draft` outranks `none`. It also returns
the number and order of active open drafts. If legacy state already contains more than one,
NBN suppresses any additional create, records `multiple_open_drafts`, and leaves consolidation or
deletion to the owner; it does not guess which human-edited draft to overwrite.

Apply the query after validated canonical identity and before the editor/delivery call.

Decision table:

| Existing state | Relation | Result |
|---|---|---|
| none | distinct | normal editor and delivery path |
| none, but supplied workbench/held cluster | same_event | normal first-delivery path using that canonical family |
| none | material_update | incoherent: there is no reader-visible output to update; defer |
| open draft | same_event or material_update | editor reviews the newest consolidated copy, then update the existing draft in place |
| reader-visible | same_event | suppress as already covered; no Typefully call |
| reader-visible | material_update | normal editor and new `UPDATE:` delivery path |
| reader-visible plus a newer open draft | same_event | suppress; reader-visible coverage takes precedence |
| reader-visible plus one later pending update draft | material_update | consolidate only into that pending update when it passes every untouched-draft check |
| reader-visible plus an unrelated/stale open draft | material_update | suppress for owner cleanup; do not create a third output |
| multiple active open drafts | any | suppress for owner cleanup; no mutation |
| any | incoherent relation | defer as an identity/continuity error; no Typefully call |

`UNCERTAIN` is reader-visible for safety. Tape-only and definitively failed/superseded local rows do
not block a new output. Desk dismissal is display-only and must not deactivate or unblock a live
Typefully object. A draft stops blocking only after an authoritative remote state proves it is
inactive, such as a confirmed Typefully `404`/deletion.

Persist `coverage_relation` and nullable `base_post_id` on every new output. A pending material-
update draft must point to the exact reader-visible post it updates. Consolidation into such a
draft is permitted only when it is the sole active draft in the canonical family, was explicitly
created as `material_update`, and its `base_post_id` is the current highest-precedence visible
output. Legacy/unclassified drafts, drafts aimed at another base output, and timestamp/text-only
inferences all suppress for owner review; neither an `UPDATE:` prefix nor row recency proves
provenance.

The existing cross-process worker lease reduces concurrency but cannot make a remote Typefully
mutation and a local SQLite commit atomic. The durable mutation protocol below owns that boundary.

### 3. Durable Typefully mutation boundary

Add an append-preserving `publisher_mutations` table. Before any Typefully create, draft replace,
or schedule operation, commit an intent containing:

- canonical alias family/root and operation (`create`, `replace_draft`, or `schedule`);
- target draft when applicable;
- an exact desired X-thread fingerprint, including receipt placement, plus the prior fingerprint
  for replacement;
- a unique owner token and monotonic version, state, timestamps, and provider reference/error;
- bounded local-materialization data sufficient to finish without the model or original process:
  exact body/thread and receipt, post class and intended mode, input member IDs, editor/resolution
  IDs and notes, target/base post, canonical key, and workbench delivery metadata.

States are `prepared`, `in_flight`, `confirmed`, `definite_failure`, `ambiguous`,
`needs_owner_review`, and `owner_suppressed`. Acquiring an intent and checking canonical output state happen in one SQLite
transaction. Any active, ambiguous, or owner-review intent for the alias family suppresses another
mutation across process restart or worker-lease expiry; `owner_suppressed` remains a canonical
block until an authenticated owner resolution supersedes it. Only the matching owner token/version
may advance or finalize an intent, so a stale worker cannot overwrite a newer reconciliation.

Commit `prepared` before the network call, then mark `in_flight`; finalize only after the remote
response is unambiguous. Remote confirmation, post insert/update, input statuses, workbench
delivery, append-only audit event, and intent finalization then commit in one SQLite transaction.
If the process dies after remote success but before that transaction, reconciliation uses the
persisted materialization data and idempotently performs the same transaction. A uniqueness key on
the intent/output prevents a second local post. On restart, reconcile outstanding intents before
allowing new delivery:

- for create, inspect recent drafts in the configured social set for the exact desired fingerprint
  and bounded attempt window. Exactly one match confirms it; zero or multiple matches become
  `needs_owner_review`. Never blindly repeat an ambiguous create;
- for replace/schedule, `GET` the target. Exact desired state confirms the mutation; exact prior
  state remains protected through a bounded grace/recheck and then becomes a definite failure;
  unrelated edits or an indeterminate state become `needs_owner_review`. Never blindly repeat an
  ambiguous patch;
- provider `404`/deleted marks the remote output inactive and the intent definite failure. A later
  fresh cycle may reconsider the event; the recovery path itself does not create.

Recovery work is bounded per NBN run: inspect at most two Typefully list pages/100 recent objects,
consider create matches only within 30 minutes either side of the recorded attempt, and issue at
most five targeted `GET`s across outstanding intents. Work left by those limits remains protected
for the next run; it does not block unrelated canonical families.

Expose `ambiguous`/`needs_owner_review` intents on the authenticated Desk. A small authenticated
POST action, protected by the existing report key plus the intent's current owner token/version,
allows the owner to record one of three append-only audited resolutions:

- `confirmed_absent` — close the attempt as a definite failure; a later fresh cycle may reconsider;
- `bind_remote_draft` — supply one Typefully draft ID, verify its social set and exact fingerprint,
  then run the normal atomic local materialization;
- `keep_suppressed` — close into an explicit `owner_suppressed` terminal state that continues to
  block the canonical family until a newer authenticated resolution changes it.

Stale tokens/versions fail without changing state. No action retries a remote mutation, and the
Desk never treats a display dismissal as one of these authoritative resolutions.

### 4. Safe Typefully draft replacement

Implement `replace_draft` with Typefully's documented v2 edit flow:

1. `GET` the exact draft, including comment-thread markers.
2. Verify it belongs to the configured social set, has remote status exactly `draft`, has the
   expected X-only structure, and its complete original NBN X thread—including receipt—matches the
   locally logged prior fingerprint.
3. Any Typefully comment marker freezes automatic replacement. Refuse to overwrite on any remote
   text change, marker, unexpected platform/thread structure, or non-draft state. Record a bounded
   typed result and keep the existing output; do not create a replacement.
4. `PATCH` only the changed X post texts while carrying forward every untouched remote post field.
   Do not change draft title, schedule, other platforms, media, quote URLs, subscribers, or other
   settings, and never use `force_overwrite_comments`.
5. Treat transport/5xx ambiguity as a distinct `draft_update_uncertain`; never issue a second
   patch automatically. This does not call the unpublished draft reader-visible. It freezes
   automatic replacement of that draft until a later read reconciles its actual remote content or
   the owner acts.

On confirmed replacement, update the existing local `posts` row in place: body, receipt, class,
editor note, resolution link, updated-at/performance invalidation, and an append-only pipeline
event. Mark the new input members as handled by that output. Do not insert another `posts` row.

Remote states are handled explicitly: `draft` may be replaced under these checks;
`planned`/`scheduled` remain active but immutable; `publishing` remains active and ambiguous;
`published` reconciles to reader-visible; confirmed `404`/deleted becomes inactive. When
autopublish is enabled, a submitted/publishing/published event is therefore suppressed unless
Sonnet identifies a genuinely material new development and the state matrix permits a new
`UPDATE:`. There is no scheduled-draft editing exception.

`draft_update_uncertain` persists the target, prior fingerprint, and desired fingerprint but does
not update the local post body. A later `GET` distinguishes prior, desired, and unrelated remote
content. Disabling automatic replacement means **retain and suppress**, never fall back to create;
the canonical output rail and pending/ambiguous intents remain active in every flag mode.

### 5. Partial editor recovery

Keep the existing one batch editor pass. If it returns valid decisions for only part of the batch:

- accept and retain those valid decisions;
- make one compact recovery call containing only omitted candidates, their selected evidence, and
  the minimal recent-feed/open-output context;
- merge unique valid recovery decisions without allowing a recovery response to change a first-
  pass decision;
- if a candidate is still omitted, label it `editor_incomplete` and stage its newsroom copy only
  when no active canonical output exists;
- if an open draft exists, do not create another draft: retain it, record the omitted decision and
  new evidence on the Desk/workbench, and leave the input handled by that existing output.

A complete editor outage keeps the current human-draft fallback for distinct events. For open-draft
consolidation, the editor receives the exact currently accepted X thread, proposed replacement,
new evidence, and immutable target draft/canonical family. Recovery may decide only the omitted
candidate; it cannot change a valid first-pass decision or retarget the output.

Reserve capacity for at most one additional editor call in both the normal v2 and direct-fallback
paths. Consume it only when the first response is valid-but-partial, release it when unused, and
record recovery usage separately. Budget denial records `editor_incomplete`; it does not bypass
output idempotency. No loop.

### 6. Haiku packet repair and X reply hygiene

Remove repeated shared coverage keys from every Haiku card and send them once at packet top level.
Cap fields so a worst-case 25-card packet has a regression-proven upper bound below the configured
48 KiB limit. If malformed configuration still exceeds the bound, compact optional summaries and
event hints deterministically before failing open; never truncate candidate IDs or protection
flags.

Add `-is:reply` to the bounded X recent-search account queries (public-list, primary, research,
guide, and detector lanes) while retaining original posts and quote posts. Retweets remain
excluded. The query hash will change once, so the first production poll uses the existing six-hour
freshness bound rather than replaying seven days. Haiku remains responsible for filtering
promotional original posts and other semantic noise.

### 7. Honest Node theme diagnostics

First reproduce the zero-match pulse in the Marketing Node with stored/fixture candidate and theme
data. Preserve the existing strict nested `theme_diagnostics` object unchanged. Add a bounded,
optional, versioned top-level sibling `theme_match_diagnostics_v1`, containing prose-free reason
counts:

- active themes;
- candidates checked;
- candidates with matching classifier assignment identity;
- classifier matches above threshold;
- taxonomy matches;
- unmatched candidates;
- existing ranking/displacement counts.

If reproduction proves an identity join defect (source-card ID or canonical URL hash), fix that
narrow join and add a regression fixture. If it proves the candidates legitimately match no active
theme under the reviewed high-precision rules, do not loosen the matcher; ship diagnostics only.

Update NBN to parse the optional top-level sibling while retaining its exact parser for the legacy
nested object, and update the Desk display to distinguish:

- producer emitted no match;
- NBN rejected malformed theme data;
- a valid theme signal was parsed and used as advisory context.

The Node schema change remains additive/backward-compatible. Deploy the tolerant NBN consumer
first, then the additive Node producer. Change matcher/join behavior only if reproduction proves a
specific defect with a failing fixture; otherwise diagnostics are the only Node behavior change.

### 8. Operational speed telemetry

Add a derived, bounded delivery-latency view using existing durable timestamps plus model usage:

- source publication/observation to first NBN intake when parseable (`detection`);
- first intake to final Typefully mutation (`conversion`);
- newsroom created/completed duration;
- editor latency and recovery count;
- first event-family intake versus final trigger (`resurfaced`);
- terminal output mode and editor result.

Render the newest 20 outputs on the Desk with unknown timestamps labeled unknown. This is
measurement, not a target, gate, or editorial score. External peer benchmarks remain in the manual
rolling audit because NBN cannot infer the earliest credible peer publication reliably.

### 9. Audit and documentation

Expose append-only events for:

- `existing_output_suppressed`;
- `existing_draft_replaced`;
- `existing_draft_remote_modified`;
- `editor_recovery_requested`, `editor_recovery_completed`, and `editor_incomplete`;
- assignment packet compaction;
- Node theme match/no-match/rejection distinctions.

Update `SYSTEM.md`, `README.md`, `INBOUND-NEWS-FLOW.md`, prompt inventory/version, and the Desk's
legend. Do not write these mechanics into the orientation brief; they are system behavior, not
Sonnet's enduring editorial worldview.

## Tests

### Next Block News focused tests

1. A supplied held/workbench canonical key with no output accepts `same_event` as its first
   delivery; `material_update` with no visible output defers.
2. An open canonical draft plus same-event evidence performs one verified `GET`/`PATCH`, changes
   one local post row only after confirmation, and makes no create call.
3. An open canonical draft plus material new evidence also consolidates before publication.
4. Reader-visible output outranks a newer draft. Same-event evidence makes no call; a material
   update may consolidate only into the sole draft durably marked `material_update` with
   `base_post_id` equal to the current visible output. Legacy, unclassified, stale-base, prefix-
   only, and timestamp-only drafts suppress.
5. Multiple active drafts suppress; a Desk-dismissed post still blocks while Typefully says it is
   live; a confirmed 404/deleted draft becomes inactive without recovery creating a replacement.
6. A reader-visible same event makes no Typefully call; a model-declared material update may create
   one `UPDATE:` output. `UNCERTAIN` suppresses another output.
7. Alias-family keys share one output reservation and one active mutation-intent namespace.
8. Human-modified/comment-marked/planned/scheduled/publishing/published/malformed or unexpected-
   structure remote drafts are never overwritten and never cause a second create.
9. Replacement preserves exact non-text remote fields and compares the full original X thread,
   including receipt. It never moves comment markers or uses forced overwrite.
10. Crash-after-remote-success create/patch, competing workers, lease expiry, process restart, and
    stale owner tokens cannot issue a second mutation. Crashes between remote confirmation, intent
    finalization, post insert/update, input status updates, workbench delivery, and audit insertion
    either roll back the whole local transaction or reconcile it idempotently from persisted data.
    Ambiguous creates and patches are never blindly retried; reconciliation covers exact-prior,
    exact-desired, zero/multiple match, unrelated-edit, list/time/GET bounds, and deferred work.
11. Authenticated owner resolution validates the report key and current intent token/version;
    `confirmed_absent`, verified `bind_remote_draft`, and `keep_suppressed` have distinct audited
    behavior. Stale or invalid requests cannot unblock or mutate an event.
12. Disabling automatic draft replacement retains/suppresses the existing output and never returns
    to unrestricted create, with autopublish both off and on. Pending/ambiguous intents remain
    active rails during rollback.
13. A partial editor response gets exactly one omitted-only recovery; valid first-pass decisions
    remain unchanged; immutable target/family cannot be changed; a second omission or recovery-
    budget denial is labeled and cannot duplicate an open draft.
14. Normal and direct-fallback reservations include at most one recovery, exact call usage is
    recorded separately, and unused capacity is released. Complete editor outage still stages one
    distinct draft and never duplicates an existing one.
15. A worst-case 25-card Haiku packet fits; coverage keys occur once; required IDs/protection
    survive compaction.
16. Every X query excludes retweets and replies while quote posts remain eligible.
17. Node no-match, malformed, and valid-signal states remain distinct in parser diagnostics and
    escaped Desk output.
18. Delivery telemetry computes detection/conversion/resurfacing correctly and labels unknown
    source time honestly.

Run the full 339+ unittest suite, focused Typefully mocks, `git diff --check`, syntax compile, and
the repositories' existing format/lint/pre-commit checks without sweeping unrelated lint debt.

### Marketing Node focused tests

- Backward/forward schema compatibility for additive diagnostics.
- Assignment identity by stable source-card ID and canonical URL hash.
- Above/below-threshold classifier matching.
- Legitimate high-precision no-match remains a no-match.
- Ranking is unchanged when diagnostics alone are added.
- Existing API, wire-pulse, scheduler, and full pytest suites.

## Deployment and smoke

1. Back up both production databases using their existing online backup procedures.
2. Build NBN as separately deployable commits: **A**, additive schema plus the always-on canonical-
   output/mutation-intent guard and backward-compatible read path; **B**, draft replacement,
   editor recovery, packet/X hygiene, Desk actions/telemetry, and docs. A rollback-compatibility
   test must prove commit A can read all states written by B and continues to suppress pending,
   ambiguous, review, and owner-suppressed intents.
3. Push/deploy NBN first with the optional Node-diagnostic sibling parser and both commits. Gate
   only automatic draft replacement behind `NBN_DRAFT_REPLACEMENT_ENABLED=false`. Confirm NBN
   still consumes the existing old-shape pulse.
4. If the Node contract changes, commit/push/deploy Node next. Confirm health and one natural wire
   pulse. Inspect only safe counts; never print credentials or raw sensitive payloads. New NBN must
   consume the additive diagnostics with zero schema rejection.
5. Confirm NBN `/health`, `/status`, model reservations, X polling, Node consumption, Typefully
   reconciliation, and a complete natural newsroom run with autopublish still off.
6. Enable automatic draft replacement in production and observe another natural non-empty run.
   Do not inject or publish synthetic news. If no natural duplicate/open-draft case occurs, report
   that mutation path as locally proven but not naturally exercised rather than altering editorial
   state. Preserve `NBN_AUTOPOST_ENABLED=false` throughout.
7. Verify the Desk displays editor recovery, output-state, owner resolution, Node diagnostic, and
   timing data safely.
8. Keep the rolling audit active after deployment.

## Rollback

- Disable `NBN_DRAFT_REPLACEMENT_ENABLED` to stop automatic PATCH operations while retaining and
  suppressing every known active output. The canonical output guard and mutation-intent table are
  mandatory safety rails and have no create-only rollback mode.
- Revert feature commit B if replacement, editor recovery, or packet compaction misbehaves while
  retaining safety commit A. After the guard has been enabled in production, never deploy code
  older than commit A; ship a forward fix instead if the guard itself fails.
- Revert the additive Node diagnostic contract independently; NBN accepts its absence.
- Pending, ambiguous, and owner-review mutation intents continue to suppress retry in every flag
  mode and every supported rollback that retains commit A; resolve them by reconciliation or
  explicit owner action.
- Never delete or rewrite existing Coldcard drafts as part of deployment. Their disposition remains
  an owner/editorial action.

## Review log

| Pass | Reviewer | Result | Required changes |
|---|---|---|---|
| 1 | Independent lead coder | changes requested | Complete relation/state precedence; durable mutation intent; exact draft-edit semantics; fail-safe rollback; bounded editor-recovery budget; preserve strict Node diagnostic object and consumer-first deploy. |
| 2 | Independent lead coder | changes requested | Persist restart-safe local materialization; bounded authenticated owner resolution; durable pending-update provenance; separately deployable retained safety layer for rollback. |
| 3 | Independent lead coder | approved | All prior blockers resolved; implementation authorized. |
