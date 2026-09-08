# Dense-packet follow-up to completed Plan 0069

## Continuity delta — September 8, 2026

Plan 0069 is already complete and deployed as bb900b3 / editorial-core-v2.25-compact-desk.
Its independent review, 581 clean-release tests and successful 22-candidate natural run
are existing evidence, not work to repeat. The audit was successfully resumed.

A subsequent production run, cycle:1788877356:e49e36e0, still deferred with
initial_context_overflow. The new overflow observation reports 73,702 bytes for 25
candidates and five receipts against the unchanged 65,536-byte limit. Intake cards
account for 38,360 bytes; prepared receipts 13,523; coverage 13,291. A later smaller
run completed. Read-only verification confirms the deployed newsroom hash still
matches bb900b3; this is a residual density case, not a missing deployment.

Current user request: finish the repair, then unpause the audit. The smallest next
action is to reproduce this remaining pressure on the current implementation and
move only redundant/verbose context behind the existing retrieval surface. Preserve
every candidate, owner/retry/identity hints, exact coverage keys, receipt provenance
and the existing byte/tool budgets. No editorial policy or model change, no forced
paid run and no manual Typefully mutation. Use the established independent review,
focused regression tests, clean deployment and natural-run smoke. Autopost remains
OFF. The audit is temporarily paused for this distinct follow-up; its full editorial
checkpoint remains 2026-09-08T11:15:56.744Z until actual audit backfill completes.

Diagnosis and final scope are pending the targeted reproduction below. This is not
a restart of Plans 0068 or 0069, nor a claim that every possible input can fit 64 KiB.

## Reproduction and narrower implementation

A read-only reconstruction on deployed v2.25 used the failed run's 25 IDs, its five
retained prefetch receipts and its exact persisted preparation rows, with current
coverage and item notes. It failed at **73,313 bytes**. This is not the exact historical
73,702-byte packet: mutable notes and coverage are read at diagnosis time. Its runtime
source hash matches the deployed bb900b3 release.

The cause in this case is **8,570 bytes of mechanical batch_fail_open preparation**:
repeated intake headlines plus generic unavailable/inspect boilerplate. The existing
severe tier also omits the outcome label that distinguishes this from real preparation.

The smaller fix adds one final density tier only if the existing tiers still overflow:
retain the batch_fail_open outcome and protection reason, omit its duplicate mechanical
prose, and remove empty optional top-level card fields. Preserve false/zero values and
all nonempty control fields. Do not shorten genuine preparation, source evidence,
identity diagnostics, owner overrides or any coverage key/lede. Full original candidate
details remain behind the existing candidate_context_id. A packet note explains the
missing optional fields and the unavailable preparation. The offline packet projection
fits **62,736 bytes**. No budget, model, tool, editorial or publication policy change.

The independent lead approved this narrower mechanical-deduplication plan and the final
implementation with no blockers, independently running all eight compact-desk tests.
The new mixed-outcome test preserves real model preparation, nested identity/owner controls,
false/zero values and unmodified originals. The crowded integration fixture preserves 25
candidates, five receipts and all 20 open-draft ledes plus the other in-scope coverage.
Without the new density tier it overflows; with it, it fits at 56,842 bytes. This synthetic
fixture supplements, rather than substitutes for, the separately labeled production
reconstruction. Full original fallback text is verified through the existing lookup tool.

The actual reconstructed packet projects from 73,313 to 62,736 bytes using the implemented
helper, with byte-for-byte equal coverage, prepared evidence and continuity boards.
Initial focused tests caught only the expected old prompt-version assertion; it is updated
to editorial-core-v2.26-dense-desk. Clean full-suite and release checks follow below.

All **585 working-tree tests passed**. This includes two unrelated evaluator tests that
will not be included in the clean release. Independent implementation review approved
with no blockers. The production target remains the existing single Railway service;
autopost is OFF and the audit is temporarily PAUSED for release verification.

## Release-smoke extension: cover every mechanical failure outcome

The initial narrow candidate 25d9e69 / v2.26 deployed successfully, with seven file
hashes verified, health 200/autopost OFF, and 583 clean-release tests passed. Before
resuming the audit, a read-only reconstruction of the more recent failed run
cycle:1788878541:41a9d5f5 found 25 **budget_fail_open** cards and six receipts still
overflowed at 70,157 bytes: the same mechanical boilerplate under a different label.
This is incomplete case coverage, not a different design issue. No audit checkpoint
was advanced and the audit remained paused during this release check.

The final candidate explicitly covers the four outcomes produced by desk_prep._synthetic:
batch_fail_open, budget_fail_open, overflow_fail_open and validation_fail_open. Keep each
exact outcome plus protection reason. Protected, successful or unknown outcomes are not
treated as failures. Tests cover all four plus genuine/unknown preparation and False/0.
No further prose clipping, budget change or new subsystem is needed. Version becomes
editorial-core-v2.27-dense-fallbacks. Final review/release proof follows below.

Final projections through the implemented helper: batch-failure reconstruction
**73,313 → 62,724 bytes**, budget-failure reconstruction **70,157 → 64,016 bytes**.
Both retain all 25 candidates and all coverage/receipt data unchanged (five and six
receipts respectively). Both are re-materialized diagnostics, not paid writer replays.
All 59 focused tests passed. Independent final review approved the four-outcome set,
truthful packet note and regressions; eight compact-desk tests passed independently.

## Final release verification

- Final runtime **684fd39**, pushed to origin/main and deployed from clean archive
  `/tmp/nbn-dense-final.RMJ7Vt`. **585 working-tree / 583 clean-release tests passed**;
  two unrelated evaluator tests and all unrelated dirty work are excluded from release.
- Railway **ac251388-dd31-4dd9-aeb9-da3b20eaa134**, created 14:56:23 UTC, reached SUCCESS.
  All seven changed file hashes match the archive. Newsroom SHA-256:
  `fcfe1278d116aa7458cca5579c0b0dbf4e046574a103c39eb1a08e711ede28d5`.
- Online SQLite backup `/data/backups/nbn-pre-source-policy-20260908T145535Z.db` passed
  its integrity check. No migration, database rewrite, configuration or credential change.
- Health HTTP 200, autopost OFF, no worker error. Newsroom, Intake, Outputs and System
  authenticated workspace views all returned 200 / JSON; unauthenticated access returned403.
  An initial smoke request used invalid view=runs (400); corrected view=newsroom returned200.
  This was a diagnostic request error, not a dashboard regression.
- Natural-run and audit-resumption evidence follows. No forced paid model run or manual
  Typefully mutation was used. The full editorial cutoff remains unchanged until backfill.

Rollback: redeploy bb900b3 / editorial-core-v2.25-compact-desk. Its original Plan0069
repair remains valid; no database restore or credential/config change is needed.

The first natural v2.27 run, **cycle:1788879499:20338a88**, delivered an actual
**63,856-byte** writer packet with **25 candidates, five prepared receipts and all
20 in-scope open-draft cards**. All25 preparation rows were batch_fail_open; the new
packet note and fallback labels are present. This exercises the repaired path in
normal production, not a manually forced replay. Writer completion is checked next.

The run **completed at15:01:33.893 UTC**, with two successful writer responses and a
returned writer result. No packet overflow. The independent editor separately hit
**ReadTimeout** (observation1894); four applied fallback decisions were recorded.
That is not editor approval or proof of an all-model-success run. The resumed audit
must inspect actual resulting drafts and monitor recurrence; this packet repair
does not change editor timeout, model or fallback policy.

The existing **audit-nbn-production** automation is now **ACTIVE every15minutes**, on
the same task with all prior autonomy and notification boundaries preserved. Its
prompt marks this follow-up and Plans0068/0069 complete, adds the precise fallback/
overflow and editor-timeout watches, and preserves the full11:15:56.744 UTC editorial
checkpoint for chronological backfill. Diagnostic reads are not counted as completed
audits. Autopost remains OFF. This repair is complete; any further fix needs new
current-version evidence rather than repeating this work.
