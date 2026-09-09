# Post-0074 packet follow-up — completed September 9, 2026

**Status: implemented, independently reviewed, tested, deployed and smoke-checked.** Final runtime commit `c3e066d`, Railway deployment `09bbbaf6-5eb8-4297-9e22-58d2647eb5e8` SUCCESS. The first ordinary worker cycle completed cleanly. A nonempty natural Writer session has not yet run on the final release; observe it at the ordinary cadence. Do not rebuild this follow-up or completed repairs 0073/0074 from earlier pending notes.

## Problem and change

After completed repair 0074, natural run `89cc847a` successfully prepared 25 cards but failed initial assembly at 71,700 bytes against the unchanged 65,536-byte cap. The following `41e84766` failed at 72,617 bytes. Neither reached the Writer. This was distinct from preparation timeout and later raw conversation-history overflow.

The new final pressure tier aliases exact repeated display metadata only after all existing fitting steps have failed. It shares the exact expert-attention warning and duplicate post URL, empty coverage preview arrays, an identical original/capture fingerprint, an exact two-endpoint redirect chain, a repeated code-generated technical-defer tuple, and an exact eight-field social-prefetch metadata tuple. Explicit row markers distinguish shared values from absent fields. It preserves candidate and coverage identities, real preparation, dates, owner/retry/followup controls, receipt text and provenance, original captured contexts, incoming letter/outcomes and retrieval pointers. Packets that already fit do not enter this tier. Irreducible packets still report honest overflow.

No model, effort, preparation timeout, budget, cadence, editorial/source policy, input quota, publisher behavior, database schema or embedding service changed. Autopost remains OFF. Main confirmed non-overlap; its separately authorized preparation/Writer comparison is a local experiment only.

## Reconstruction limits and verification correction

Original failed packets were not retained; immutable observations retain byte totals and sections. Read-only reconstruction reused original membership, saved preparation and six receipt artifacts, with current mutable item/coverage/memory state and assembly time. Production SQLite was opened mode=ro/query_only, HTTP sends blocked, and telemetry writes intercepted; none were encountered. No paid model or publisher replay occurred.

The first reconstruction omitted the production mapping `items.published_at AS published`, and its receipt stubs used cached=false instead of the actual cached=true display value. Its apparent fit was insufficient evidence. This was caught before declaring completion. Both fixtures and full context rows were regenerated with the correct date mapping and receipt display metadata. Remaining differences from the historical packets are explicit; these are not exact historical replays.

Corrected fixture results:

| Reconstruction | Before final aliases | After final aliases | Margin |
| --- | ---: | ---: | ---: |
| 89cc847a | 71,779 | 64,700 | 836 |
| 41e84766 | 72,530 | 65,207 | 329 |

These demonstrate bounded fit, not broad headroom or guaranteed future success. The second original run's preparation was also successful: 25 cards / 46,166 request bytes / 36.231 seconds, 22 advances and three Background. The first was 47,025 bytes / 39.928 seconds, 21 advances and four Background. Both were under the existing 90-second timeout; no Writer-budget displacement conclusion is possible because assembly failed first.

Independent review caught an initial redirect legend ambiguity: a previously omitted single-final chain could be misread as a two-endpoint chain. Explicit `chain_pair` markers fixed it. A mixed-tier roundtrip test covers single-final, endpoint-pair, repeated-hop and equal-endpoint cases. The later prefetch alias requires every field with its exact type/value, so missing/null/0/1 values cannot masquerade as booleans. All non-tuple fields and full contexts remain unchanged.

Final independent implementation approval received. Nineteen focused tests and **691 clean isolated tests passed in 34.598 seconds**. Coverage includes both corrected fixtures, date/preparation preservation, receipt roundtrip, mixed metadata, no original-context mutation, idempotence, pressure-only execution, actual bounded/sectioned context retrieval and honest irreducible overflow. Retrieval tests exercise individual legal choices; they do not claim all full receipts fit together within the shared allowance.

## Release and smoke

Intermediate commit dd80004 was deployed before the reconstruction correction; it is superseded by c3e066d. Its worker restart interrupted old-code run fe3e2dcf before materialization. The normal worker lease/recovery path cleared it at 21:10:30.682 UTC, with no stories delivered, no items held and no ambiguity. No manual database recovery occurred.

Final commit c3e066d was fast-forwarded and pushed to main while preserving unrelated dirty evaluator/audit files. Deployment used a clean archive at `/var/folders/_b/_wrm1hf95fl9hm3kdm2l2ntc0000gn/T/nbn-post0074-final.hzyx69eq`. Final online backup `/data/backups/nbn-pre-source-policy-20260909T211431Z.db` passed integrity checking. Rollback remains the reviewed prior runtime, without database restoration.

Final deployment created 21:14:43.866 UTC and confirmed SUCCESS. Production newsroom SHA256:
`11d7b11ce66d332814c5cb2c2791f4052eb90490c7569374d255a5540d99a472`.

Smoke at **21:16:12.990 UTC / 1788988572.9896483** independently matches the code hash. Health and four Desk endpoints return 200. Effective configuration is unchanged: Luna/low, preparation 90 seconds, compact initial 65,536 bytes, compact history 196,608 bytes, session 360 seconds, autopost false. Worker started 21:15:22.951 and completed its first ordinary cycle at 21:15:31.083 without error. No lease remained. Publisher counts remain 100 confirmed / 17 definite failures / zero ambiguous, with 149 posts and 141 drafted items. No new Typefully content or audit comment was written.

The SAME audit automation was paused 21:06:49.207–21:16:43.090 UTC and restored ACTIVE with its original prompt, audit task target and 15-minute cadence. Canonical prompt readback verified. Main requested no progress callback; release evidence and the audit checkpoint are available for its local experiment to pin.

## Next observation

Implementation/deployment work is complete. Next persisted editorial opening is **21:22:35.002 UTC / 16:22:35 CT**. Observe a natural nonempty packet and Writer/Editor outcome, real source/context use, letters and latency; do not force a paid replay. Tight fixtures and a passing health check do not prove future useful outputs or solve genuine raw-history limits.

Full historical editorial cutoff remains **September 9, 10:50 UTC**, completed separately in `research/audit-2026-09-09-2051.md`. Companion files include corrected-first/second reconstruction JSON, `post0074-final-smoke.json`, and worker handoff/recovery evidence. Initial reconstruction evidence is retained with its limitations and superseded sufficiency claim.
