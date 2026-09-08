# 0069 — Preserve the working desk under its existing byte limit

September 8, 2026. Bounded audit repair; independent lead approved the direction before implementation.

## Observed need

The 11:15:56–13:28:01 UTC audit found three of nine desks deferred before the writer
because their compact packet exceeded 64 KiB. Two were after Plan 0068. The problem
also occurred before that release. Exact failed packets were not retained, so their
individual section sizes are unknown. Nearby successful packets devote about 32 KiB
to prepared receipts, including 13–15 KiB of link/image metadata that bypasses compaction.

The last successful packet also omitted an existing Strategy draft from its three-row
coverage list. A related announcement became a second draft. This is evidence of lost
useful context, not proof that preserving context will guarantee model event grouping.

## Small repair, existing design

1. Offload bulky prepared-receipt sidecars through existing code-issued context IDs
   before trimming lead content. Preserve the complete captured record and its fetch ID.
2. If necessary, shorten evidence excerpts by UTF-8 bytes, label truncation, and preserve
   honest excerpt/full-capture fingerprints. Do not refetch or add model calls.
3. Preserve candidate identity/retry/owner/visual hints at every compaction tier. Keep
   full candidate details behind context IDs; include prior exact key and decision state.
4. Keep compact identities and ledes for every in-scope open draft instead of only three.
   Full coverage cards remain retrievable. Do not create aliases or mutate drafts.
5. Record section byte sizes/counts when an irreducible packet still exceeds the bound.

The 64 KiB initial limit, four optional retrieval calls / 48 KiB, roster, cadence,
editorial standards and publication controls do not change. Autopost stays OFF.
Nano Banana remains parked. An irreducibly large desk still defers honestly.

## Acceptance and release

- Regression fixtures: 25 candidates, six sidecar-heavy receipts, multibyte excerpts,
  more than three open drafts including an older related Strategy output, full context
  readback, preserved control hints, and measurable irreducible overflow.
- Independent implementation review; complete offline suite on a clean commit archive.
- Explicit Railway deployment; verify hashes, health, autopost OFF and next natural
  writer handoff. No paid synthetic live run and no manual Typefully mutations.
- Resume the same audit after deployment, preserving the last complete audit cutoff.
- Roll back code to the previous runtime commit if required; no destructive DB restore.

## Review

Independent lead confirmed the receipt sidecar omission and the lossy three-row coverage
cap. Approved this direction with byte-safe excerpt fingerprints and exact context
readback tests. No new subsystem, larger budget, or automatic editorial aliasing.

## Explicit resumption

Brady requested: "finish the repair then unpause the audit" on September 8. Plan 0068
is already shipped; its review and release are not being repeated. The remaining delta
is the unfinished local compact-desk patch, regression tests, independent implementation
review, a separate clean release and smoke check. The audit stays paused until that
work is shipped. Its full editorial checkpoint remains unchanged until a complete
audit pass actually covers the intervening records.

Implementation review approved with no blockers; the independent reviewer ran 46 focused
tests. Incorporated the reviewer's small tool clarification: existing context lookup opens
current receipt/candidate details as well as history. No new tool or mandatory lookup.

## Completed

Released as **bb900b3**, Railway deployment **c71a4a74-09a4-4728-a75f-a4e24a149444**.
581 clean-release tests passed. The first natural v2.25 run completed with a 58,307-byte
packet containing 22 candidates, four prepared receipts and all 20 open-draft cards.
Audit restored ACTIVE at the existing cadence; autopost OFF. Full proof and boundaries:
SPRINT-0069-FINDINGS.md. This plan is completed, not pending implementation.
