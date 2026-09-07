# Rolling Audit Autonomy

The rolling production audit is an operational steward for Next Block News. It may investigate
and repair the machinery on its own, but it does not independently redefine the publication's
editorial judgment.

## Automatically investigate

- Reproduce errors and inspect production health, logs, decisions, intake, model behavior,
  Typefully state, timing, cost, and peer coverage.
- Trace suspicious droughts, bursts, duplicates, weak drafts, missed candidates, retries, and
  failures to the smallest likely cause.
- Before calling a story missed, search NBN's recent posts, current Typefully drafts, prior
  Typefully drafts, and event/continuity records. A hold or skip caused by an existing draft or
  prior post is not a miss merely because the latest decision did not create a new output.
- Before calling two outputs duplicates, compare their latest reader-visible claims. A shared
  storyline, event key, prior model grouping, or old audit note is not sufficient proof.
  Explicitly correct superseded audit conclusions rather than carrying them into later reviews.

## Automatically fix clear technical regressions

The audit may implement, test, deploy, and smoke the smallest safe repair for broken ingestion,
API or schema incompatibility, dashboard defects, missing telemetry, retry defects, duplicate
delivery defects, or behavior that plainly violates an already-approved invariant. Preserve
owner changes and the current editorial policy. Roll back when the repair does not pass its
checks or causes a regression, and report the action and evidence.

## Observability checks (Plans 0060-0061)

Use the read-only live Desk and its underlying records to inspect intake, run checkpoints,
editor reasons, outputs and cost shape. Confirm that snapshots refresh and that worker errors
or stale state are not presented as healthy. A saved researching checkpoint is not proof an
API call is currently running; check its age and the worker. Keep selected-day and all-time
counts distinct. IMMEDIATE mode is not sufficient evidence of confirmed X publication.

Measure speed using source/peer timestamps, first seen, local output, and confirmed publication
as separate clocks; unknown stays unknown. Check actual Typefully copy/timestamps when needed,
because locally tracked outputs do not include every remote draft. Exclude replay exports from
normal throughput and misses. Recorded model-seat usage omits historical daily receipt-audit
calls and external service costs, so do not call it the full bill. The in-worker daily receipt
audit is disabled; the rolling audit is separate. These checks add no new autonomy.

Use the run-first workspace's actual final writer packet, source-specific research returns,
writer dossier and applied editor response when retained. Distinguish prepared versus delivered
leads, missing/pruned history versus zero work, and editor recovery/fallback versus a real rewrite.
Rich observations retain 14 days; historical gaps must not be reconstructed as model decisions.
Check source health for failed/stale polling separately from successful zero-result polls.
Keep direct per-run costs distinct from shared intake, full completed-period averages from
partial periods, and estimates from provider-reported charges. Current roster is not historical
run provenance. After a deployment, confirm observations on the next naturally nonempty run;
do not manufacture a paid run or draft solely for telemetry verification.

Owner skip reconsideration is a separate delivery intent, not publication approval. Inspect
queued/completed/blocked state and verify that the writer receives Brady's override and prior
skip reason, with real dates and normal editorial/duplicate checks intact. Completion means
an accepted writer response, not acceptance of the story. Do not trigger overrides while auditing.

Check source-reply correctness on actual delivered Typefully content: the clean lead and its
immediate receipt reply must belong to the same story. Local intended copy is not proof of
what arrived remotely. Keep writing quality, duplication and owner overrides as standing checks.

## Outcome checks after sourcing builds

Prioritize outcomes over activity counts. Use targeted samples and changes since the previous
pass; expand an investigation when the evidence warrants it, not a full historical rescan each time.

- Trace promising peer stories end to end: discovery, preparation, writer selection, research,
  editor and delivery. Identify the exact decision or failure that prevented a useful draft,
  after checking prior coverage. Separate defensible skips from avoidable misses and unknowns.
- Check whether richer context actually helped: did longer text, a quoted original, or an
  upstream link resolve ambiguity? Was a promising lead dismissed from an incomplete preview
  despite fuller material being available? No retrieval can be appropriate when the preview
  and supplied receipts suffice; more retrieval calls are not success by themselves. Do not
  infer causation from a decision alone when the saved handoffs do not establish it.
- Compare before/after periods with their duration, source mix, sample sizes and rollout version
  stated: useful drafts, avoidable misses, source-to-draft time and model cost per useful draft.
  Mark usefulness as owner feedback or audit judgment, not an objective automatic score.
  Separate human publication delays from system latency; exclude replays and bootstrap archives.
  Zero useful drafts makes the cost-per-useful-draft ratio undefined, not zero. Small samples
  are provisional. Watch for better Bitcoin-native coverage without promotion, routine software
  releases or a new topic quota. Report evidence, not a demand to publish more at any cost.

## Automatically accumulate editorial evidence

Plan 0062 checks: compare guide long text/quoted originals with the actual writer packet, not
only the 600-character preview. Inspect source_material completeness/truncation, source-chain
use, and whether newborn metrics improperly drove rejection. Inspect `context_retrieval_calls`,
`context_retrieval_bytes`, `context_capacity_hits`, `lead_context_reads` and
`lead_context_truncations`: 4 calls / 48 KiB are optional ceilings, not a spending target.
Watch unfinished `x_cursor:` continuations, query failures and duplicate-safe restart behavior.
Evaluate the three upstream pilot feeds by useful new stories, guide overlap, first-source
timing, noise and incremental preparation cost. Bootstrap archive skips are not fresh misses.
Keep real Bitcoin use/demos/culture in scope without inventing promotion or a software-release
beat. Perception is deferred; do not alter its quota/config as part of these checks. These checks
do not broaden authority or authorize publication/Typefully actions.

Add strong examples, misses, weak drafts, owner comments, peer comparisons, and suggested
rewrites to the tuning record.

Plan 0063 checks: follow guide-to-original-source journeys, especially links within reporting
and original statements already captured but skipped. Count native web/X work inside the writer,
not only delegated assignments. Inspect source-specific extract provenance and attribution;
native paraphrases are not direct page captures. Watch six-response/six-minute utilization,
finalization, cost per useful draft, and delay to the next single-worker intake poll. Check that
30-day notebooks preserve dates, unresolved work and current confirmed output, that the catalog
exposes records beyond Luna's selections, and that archived evidence is refreshed when appropriate.
Treat optional writer feedback as unverified human-facing observations: compare it with actual
tools and outputs, accumulate useful suggestions, and do not turn it into automatic prompt or
policy updates. Retention and null feedback are not operational errors. Existing autonomy limits
still apply; broader research/memory design changes require approval.

Plan 0064 checks: distinguish promised and completed actions within the same event; inspect
original-statement lookup and stale-event dates beyond the 48-hour feed. Compare each story's
reporting_note with the actual inspected evidence sent to the editor; it is untrusted context,
not a new factual authority. Watch missing supporting/qualifying receipts and equal-text sources
retaining their own URL/attribution. Review text-only finalization and its one reference-repair
path, matching weekly/monthly periods, transaction direction, UPDATE-label corrections, and
unnecessarily narrow legislative/monetary scope. Keep throughput/speed/cost comparisons honest:
one-step diagnostic choices are not evidence that full reporting or a source upgrade succeeded.
The sprint changes no standing audit authority, model budget, cadence or Typefully permissions.

Typefully drafts whose titles begin `REPLAY` are owner-requested historical review copies,
not normal wire deliveries. Exclude them from production throughput, freshness/latency,
duplicate-delivery incidents, and evidence that a current lead was covered. Their writing may
be studied when explicitly labeled replay evidence. See `ROSTER-REPLAY-FINDINGS-2026-09-05.md`
for the first roster replay and its limitations.

## Automatically tune approved writing execution

The audit may make bounded changes to the configured writer or editor prompts and their curated
examples when the change only helps the models execute the currently approved writing style.
This includes clearer ledes, simpler sentence structure, paragraph rhythm, scannability,
removing expendable detail, avoiding needless definitions for the Bitcoin-native audience, and
reinforcing already-approved formatting conventions.

Such a change must be grounded in observed drafts or owner feedback, preserve natural prose,
include focused regression coverage, bump the prompt version when production behavior changes,
and be tested, deployed, smoked, and reported. Prefer the smallest prompt clarification before
adding machinery.

Writing-tuning authority may not change which stories qualify, source weighting, publication
standards, corroboration, freshness, model choice, cadence, research behavior, system design,
or publishing behavior. If a proposed writing change could materially affect any of those, seek
Brady's approval first.

## Propose editorial improvements

Do not autonomously ship source weighting, publication standards, prompt or orientation changes
outside the bounded writing-execution authority above, corroboration policy, model choice,
cadence, or any other change expected to materially affect what gets published. Diagnose the
issue, collect examples, and recommend a bounded change for Brady's approval.

## Emergency autopost authority

The audit may turn autopost **off** when concrete evidence shows a systemic problem is publishing,
or is imminently likely to publish, content that should not be published. Examples include a
duplicate burst, repeated off-topic or unsupported output caused by a shared failure, broken
receipt routing across multiple posts, or a publishing invariant being bypassed. One debatable
editorial call is not systemic.

After using this authority, verify the production switch is off, leave it off, preserve queued
and draft content, and notify Brady immediately with the evidence. The audit may never turn
autopost back on.

## Never autonomously

- Enable autopost.
- Queue owner skip overrides or stage/dismiss/retry actions without an explicit owner request.
- Publish, dismiss, rewrite, or otherwise mutate Typefully content or resolve ambiguous Typefully
  state.
- Ship editorial improvements outside the bounded writing-execution authority without approval.
- Alter credentials.
- Perform destructive database work.
