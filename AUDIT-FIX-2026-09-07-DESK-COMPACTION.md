# Audit repair — optional storyline context must not prevent a desk run

September 7, 2026. Narrow technical repair under AUDIT-AUTONOMY.md.

## Evidence

Run `cycle:1788787510:fcec6b98` deferred at 13:26:05 UTC before any writer call:
`initial_context_overflow`. Preparation advanced 13 of 23 items; six sources were
successfully prefetched. Candidates remained pending for normal retry. The following
13:40 desk completed on the old code; this was not an ongoing worker outage.

A read-only production snapshot, copied into an isolated in-memory database, reproduced
the failure with a 66,626-byte packet after all existing compaction. Its six prepared
receipts occupied 30,046 bytes, candidates 17,201 bytes, and three optional storyline
cards 6,590 bytes. The actual initial limit is 65,536 bytes. Historical source/coverage
state was reconstructed from retained records, not claimed to be an exact saved packet:
the failed run never recorded a final writer input.

## Repair and boundaries

Move full storyline cards behind the existing context lookup when severe compaction
still exceeds the limit. Retain their stable IDs and readable index entries, and retain
all candidate IDs, owner overrides, prepared source text, source links and receipt IDs.
Cards omitted by the existing four-card cut also remain retrievable. Only cards actually
supplied inline count as initially read; opening one later updates the existing counters.

No larger context/model/retrieval budget, new tool, prompt or editorial change, schema
change, forced retry, Typefully mutation, or Node/Perception setting change. A genuinely
oversized mandatory packet still defers. This does not promise unlimited packet capacity.

## Verification

- Regression test reproduced the old overflow, then passed with the fix; verifies source
  text/links, candidate identity, owner override, deferred-card retrieval and read counters.
- Full working-tree offline suite: 492 tests passed, including two unrelated evaluator tests.
- Running only the patched packet method in the isolated production snapshot succeeded at
  60,604 bytes, keeping all 13 candidates and all six prepared receipts unchanged. No model,
  source-provider or publishing calls; no writes to the live database.

## Production release

- Runtime `b26d3ab` pushed to origin/main, deployed from clean archive
  `/tmp/nbn-desk-compaction-release.qE6vee`; **490 clean-release tests passed**.
- Online backup `/data/backups/nbn-pre-source-policy-20260907T134542Z.db` passed the
  full integrity check. No schema or configuration change.
- Railway deployment `38ac4c30-a6b3-43b4-864a-02884dab743a` reached SUCCESS on the
  existing production service, one replica and `/data` volume.
- Runtime newsroom SHA-256 `950177ac4520b7c4c33c8711fc15cdf779dff9f95d514253299711c08c354105`
  matches the release. All four authenticated Desk views returned 200. Public health
  reports two natural cycles after restart, latest completed 13:49:56 UTC, no error,
  autopost OFF. No pending delivery or unfinished X pagination.
- No post-deployment nonempty newsroom session had occurred at smoke time. The isolated
  reconstruction verifies the precise failure path without forcing a paid model run.
  The existing rolling audit remains ACTIVE and will watch the next ordinary session.

Rollback is the previous runtime; no database rollback or configuration change is needed.
