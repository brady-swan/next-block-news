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
