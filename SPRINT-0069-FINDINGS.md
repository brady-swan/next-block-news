# Plan 0069 — Compact desk repair

September 8, 2026. Separate follow-up to the already completed Plan 0068.
Brady explicitly resumed this paused repair and requested audit resumption after release.

## Evidence and exact change

The original audit found three pre-writer `initial_context_overflow` deferrals in nine runs.
Two subsequent v2.24 runs also deferred: `cycle:1788874432:1eab54da` and
`cycle:1788875337:4ab38684`. Production newsroom SHA-256 matched runtime 58baaf6;
autopost was OFF. This is a current production defect, not a stale pre-release finding.

Prepared source link/image metadata bypassed every compaction tier. Severe compaction also
removed candidate correction/visual/prior-state hints and retained only three coverage cards.
The audit saw an older Strategy open draft disappear from a later packet, followed by a second
draft of the related announcement. Context preservation can help grouping, but does not prove
the model will always recognize related events or guarantee no duplicate proposals.

The repair moves bulky receipt sidecars behind existing context IDs first. When necessary,
byte-bounded evidence excerpts retain honest fingerprints and explicit partial-capture labels;
full retained FetchRecords remain unchanged and retrievable without refetching. Candidate
control hints survive severe compaction, with full candidate/reference context available.
All in-scope open-draft exact keys and short ledes survive rather than only the newest three.
An irreducible overflow records section byte sizes/counts; it is never called a writer handoff.

No model, cadence, editorial, publication, identity/aliasing, schema, budget or vendor change.
The 64 KiB initial bound and four optional lookups / 48 KiB total remain. Nano Banana stays
parked. No manual Typefully mutation or paid replay is part of this repair.

## Offline verification

- A frozen crowded fixture (25 candidates, six rich prepared receipts, eight open drafts)
  fails with `initial_context_overflow` when run through the exact deployed v2.24 packet method.
  That method's source SHA-256 matches the read-only production check.
- The same fixture on v2.25 assembles at **63,502 bytes**, preserving 25 candidates, six
  receipts and all eight draft identities/ledes. This is a synthetic regression fixture,
  not a reconstructed exact historical failed packet.
- Six new tests cover crowded packets, retained owner/retry/identity/visual hints, older
  Strategy coverage, UTF-8 excerpts and capture fingerprints, exact context readback including
  bounded sections, small-receipt behavior, excerpt pressure and measured irreducible overflow.
- The existing size assertion now measures the actual compact wire serialization rather than
  Python's whitespace/ASCII-escaped default serialization. The production limit is unchanged.
- Focused suite: **70 tests passed**. Complete-suite and release results follow below.
- Full working-tree suite: **583 tests passed**, including two unrelated evaluator tests that
  are excluded from the release. The reviewer independently ran 46 focused tests and approved
  release with no blockers. Their narrow tool-wording clarification was incorporated: context
  retrieval opens current receipt/candidate details as well as history, without requiring a fetch.

## Production release — complete

- Runtime **bb900b3**, pushed to origin/main and deployed from clean archive
  `/tmp/nbn-0069-release.WSgO7x`. **581 clean-release tests passed**. The two unrelated
  working-tree evaluator tests and all unrelated dirty work were excluded from this release.
- Online backup `/data/backups/nbn-pre-source-policy-20260908T140556Z.db` passed its integrity
  check. No database migration, credentials, editorial settings or model budgets changed.
- Railway deployment **c71a4a74-09a4-4728-a75f-a4e24a149444** reached **SUCCESS** on the
  existing production service. Ten deployed runtime/document/test file hashes match the archive.
  Newsroom SHA-256: `c6c0030089f723e6ed9ff29e7790dc4c2369ea0ecca45b2433d62463102c8768`.
- All four authenticated Desk workspace views returned HTTP 200 / JSON; unauthenticated
  workspace access returned 403. Health returned 200 with autopost OFF and no worker error.
- First natural run **cycle:1788876448:195d7ba4** completed at **14:08:27 UTC**. Its actual
  writer packet was **58,307 bytes**, with **22 candidates, four prepared receipts and all
  20 in-scope open-draft cards**. Four receipt sidecars were offloaded, and all 22 candidates
  had full context IDs. Four writer responses, five native research operations and one
  710-byte context lookup completed; there was no packet overflow. This directly exercises
  the repaired path under assignment-preparation fail-open (`seat_cap`). It is smoke proof,
  not an assertion that every editorial decision or source choice is now correct.
- The existing **audit-nbn-production** automation was restored to **ACTIVE**, unchanged at
  15-minute intervals, with the start-of-pass continuity guard intact. The saved prompt marks
  Plans 0068 and 0069 complete and adds the new compact-desk outcome watches. Autopost stays OFF;
  Nano Banana remains parked. No manual Typefully mutation or forced paid live run was used.

The full editorial audit cutoff remains September 8, 11:15:56.744 UTC. Diagnostic reads and
repair testing do not advance it. The resumed audit will backfill subsequent normal records
in bounded chronological batches, advancing only genuinely completed editorial checkpoints.

Rollback: redeploy the previous runtime 58baaf6 (or documentation-only 29a6e25 with identical
runtime code); no database restore or config change is required.
