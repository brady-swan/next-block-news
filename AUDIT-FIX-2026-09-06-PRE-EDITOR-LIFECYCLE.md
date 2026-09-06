# Audit repair: pre-editor deferrals left story commits pending

## Evidence and scope

Production run `cycle:1788711140:e992c915` completed at 16:12:57 UTC on September 6.
The writer selected a Strive warrant story as a material update to a previous, unpublished
CEO projection. The existing delivery invariant deferred the item with
`defer:material_update_has_no_visible_base`, before editor review. The story commit incorrectly
remained `pending` with validation `accepted`, even though the run had finished.

Code inspection found the same missing terminal-state write in the adjacent
`defer:material_update_requires_update_label` branch. Both branches already defer their items
and leave the current run; neither had updated the run-scoped story lifecycle.

## Small repair

- Record `held` and the exact existing reason in both pre-editor deferral branches.
- Preserve candidate status, retry timing, canonical identity, existing guards and all editorial
  decisions. Do not loosen the treasury bar, change prompts, or enable the editor/publisher.
- Do not rewrite historical rows or mutate Typefully. Historical pending labels remain a known
  limitation and are documented in DESK-GUIDE.md.
- No migration, new dependency, schema, dashboard layout change or model call is needed.

The regression test reproduces both erroneous pending states before the patch. After the patch
it asserts held state and reason, retained item retry eligibility, no fabricated editor outcome,
and zero editor/publisher calls. Release verification is recorded below when complete.

## Verification and release

- Before repair: both regression subcases failed because actual state was `pending`, not `held`.
- After repair: focused editorial/Desk suite passed 51 tests; working-tree suite passed
  428 tests (including two pre-existing unreleased evaluator tests). Clean Python 3.12 archive
  `/tmp/nbn-lifecycle-release.meK6d6` passed **426 tests**, with 50 subtests.
- Runtime commit `4ba3f3d` was pushed to main and deployed from that clean archive.
- Online SQLite backup, integrity checked:
  `/data/backups/nbn-pre-source-policy-20260906T161746Z.db`.
- Railway deployment `995a195e-9ae9-4458-8ef3-6d2096791b18`: **SUCCESS**.
- Production `nbn/main.py` SHA-256 exactly matches the tested archive:
  `a4d8cbe6471b4341a689301c4662799de4c8293813fbe533da79df6e606663ed`.
- Authenticated Desk, selected-run page/snapshot, intake and legacy report returned 200;
  the unauthenticated snapshot returned 403. Snapshot time was current and worker healthy.
  SQLite quick_check returned `ok`.
- Public health verified process start `1788711520.9644423`, two natural completed cycles
  (latest `1788711586.9762738`), no worker error and autopost OFF.

This release did not force a model run or exercise publisher actions to smoke the edge case.
Its two deferral paths are covered offline; live smoke verifies deployment, reads and normal
worker operation. No historical data was rewritten. The existing rolling audit remained ACTIVE;
the Desk redesign is still a separate unshipped plan. Rollback runtime is `c581510`.
