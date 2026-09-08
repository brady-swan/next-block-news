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

## Release status

Implementation review approved. Clean-release verification and deployment pending.
Audit remains paused; autopost remains OFF.
The full editorial audit cutoff remains September 8, 11:15:56.744 UTC. Diagnostic reads and
repair testing do not advance it. The same audit must backfill subsequent normal records.

Rollback: redeploy the previous runtime 58baaf6 (or documentation-only 29a6e25 with identical
runtime code); no database restore or config change is required.
