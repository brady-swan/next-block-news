# Plan 0070 — visual correctness release

Status: independent plan and actual-code review approved; implementation complete. Clean-archive
verification and deployment smoke are the remaining release steps. Owner authorized the five
priorities and the established independent-review playbook on September 8, 2026.

## Result

- Inspected reporting images travel separately from attachments through writer normalization,
  main handoff, initial editor and omitted-only recovery, observations and retained Desk review.
  Unknown reuse rights permit evidence review only. Original run/story ownership and inspected,
  immutable bytes are required; invalid references hold their story without losing siblings.
- Editor image admission is atomic per candidate, deduplicated by asset/hash, and remains bounded
  to four images / 12 MiB. An outage, omitted decision or payload-capacity deferral cannot stage
  unreviewed image-supported copy as a text-only fallback.
- Four inspections and four successful renders have separate counters within unchanged shared
  time/tool/image bounds. Cached source/PDF inspections retain the two-per-candidate limit.
- Quotes/excerpts attribute the actual source_fetch_id; data source_urls follow referenced points.
- All six highlight colors render in both presets. Excerpts default to yellow, enlarge the exact
  passage within doubled margins, preserve paragraphs/highlights, and avoid duplicate NBN footer
  identity. Fixture labels stay in development metadata/README rather than image pixels.
- Line charts use elapsed calendar days by default, require distinct increasing ISO dates, and
  retain signed values and missing-observation gaps. Explicit category mode has equal spacing.
  Close labels are omitted without moving points; full observations remain in recipe/alt text.

Combined marker: editorial-core-v2.29-visual-evidence. Template: nbn-visuals-4. The main NBN task
explicitly agreed to include its separately independently reviewed appendix-reference contract
repair and five tests, and to avoid a competing deployment. Only that nine-line editor contract
addition was imported; unrelated main evaluator/audit changes remain outside this release.

## Review and validation

Independent reviewer visuals_independent_review did not implement the change. Plan APPROVED;
actual-code review APPROVED with no blockers, including the combined appendix-reference repair.
Reviewer independently ran 87 focused tests and 20 combined visual/reference tests, checked the
diff and inspected square/landscape excerpts and the irregular-date chart.

Local full offline suite: 628 tests passed on Python 3.12, including the combined repair. Earlier
five-priority suite before the additional five appendix tests: 623 passed. Fifteen new visual
correctness tests exercise the actual normalizer/main/editor and retained Desk path, transport
recovery, capacity, bad ownership/bytes, counters, attribution, palette pixels and temporal
geometry. Existing text-only and delivery regressions pass. No Desk code changed.

Generated proof directory:
/Users/brady/Documents/ChatGPT/Next Block News/reviews/post-visuals-2026-09-08/proofs-v4/

All ten template/preset fixtures, all six highlight palettes in both presets, and two irregular
line fixtures were generated offline. Values/passages are synthetic fixtures documented in the
README. Original approved design references and prior proofs were preserved. No model, image
provider or publisher was called for these tests/proofs.

## Release record

Pre-release runtime confirmed ab7529e / editorial-core-v2.27-dense-fallbacks; Railway deployment
f97615a4-7de1-44a4-ab67-6d49f37c681c SUCCESS. Existing project/service/environment, one replica and
/data mount verified. Main task's 22:20:27 UTC pulse confirms healthy worker and autopost OFF.

Clean intended commit, archive suite, online SQLite backup, explicit deployment and production
smoke results will be added here after verification. The audit remains ACTIVE and owns its
coverage cutoff; this release does not advance editorial audit coverage or change its settings.
Rollback is code-only to ab7529e/previous deployment; never restore the database destructively.

## Limits

Deterministic tests prove the repaired contracts, not natural model take-up. No paid replay,
forced production run, test draft, changed model/effort/shared budget or Nano Banana integration.
No source-image rights or exact text-quotation checks were relaxed. Existing assets/delivery
identities remain immutable. Natural visual generation may still be absent during a healthy
release smoke; report its measured state without claiming adoption.
