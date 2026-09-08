# Plan 0070 — visual correctness release

Status: COMPLETE. Runtime ccea9a0 is live on Railway deployment
451d51c7-c9c9-4ef8-8ab8-32b07b96200e (SUCCESS). Independent plan and actual-code review approved;
628 tests pass locally and from the clean release archive. Production checks and a natural
writer run passed. Owner authorized the five priorities and release playbook on September 8.

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

All 24 proof PNGs have verified dimensions/hashes: ten template/preset fixtures, six highlight
palettes in both presets, and two irregular line fixtures, generated offline. Values/passages are synthetic fixtures documented in the
README. Original approved design references and prior proofs were preserved. No model, image
provider or publisher was called for these tests/proofs.

## Release record

Pre-release runtime confirmed ab7529e / editorial-core-v2.27-dense-fallbacks; Railway deployment
f97615a4-7de1-44a4-ab67-6d49f37c681c SUCCESS. Existing project/service/environment, one replica and
/data mount verified. Main task's 22:20:27 UTC pulse confirms healthy worker and autopost OFF.

- Runtime commit ccea9a0cb95e633638a5db2d820d6c81cc3b93dc, fast-forwarded into main and pushed.
  All 26 unrelated dirty files were verified unchanged; originals/patches are preserved in
  /tmp/nbn-0070-main-preserved-2cgp540j. No blanket stash/reset or evaluator/audit edits.
- Clean commit archive /tmp/nbn-0070-release-hmdse24w passed all 628 tests (35.9s, Python 3.12).
  The identical Git archive was freshly extracted to /tmp/nbn-0070-deploy-lfozy_bq for deployment,
  excluding test byproducts and unrelated work. No Desk source/build change was required.
- Online SQLite backup /data/backups/nbn-pre-source-policy-20260908T222815Z.db passed its integrity
  check. Assets remain durable on the existing volume; no database or media was restored/deleted.
- Explicit Railway deployment 451d51c7-c9c9-4ef8-8ab8-32b07b96200e is SUCCESS. Target verified:
  project 1e1f32d1-6153-4f71-80b3-9543050caa7e, service ff9549a3-6f78-481a-a550-d8c10136af64,
  environment 90c43f68-970a-4f93-a392-414c3c175502. One replica; existing /data mount.
- At 22:31:05 UTC, public/local health returned 200, two normal cycles completed and last_error
  was null. Autopost OFF. All four authenticated Desk workspace views returned 200. A retained
  image returned 200 with the stored SHA-256; the unauthenticated request returned 403. Eleven
  runtime/prompt file hashes match the clean archive. See docs/planning/0070-release-smoke.json.
- Natural writer run cycle:1788906635:e1f77c39 completed at 22:31:04 UTC on the new prompt:
  eight preparation candidates, two supplied to the writer with two prefetched receipts, one
  writer turn, zero stories and zero visual tool calls. The new strict dossier contract worked.
  This run did not exercise an image-bearing editor call or appendix selection in production.
  Existing production totals remain four source images and zero renders/uploads; organic image
  creation is still unverified. No forced cycle, paid test replay or test draft was used.
- Main NBN task received the exact commit/deployment/backup/smoke outcome and owns its audit
  continuity update. Its existing audit stays ACTIVE; settings and actual coverage cutoff were
  not changed by this release. No separate v2.28 deployment remains pending.

Rollback is code-only to prior runtime ab7529e / deployment
f97615a4-7de1-44a4-ab67-6d49f37c681c. Never restore the database destructively.

## Limits

Deterministic tests prove the repaired contracts, not natural model take-up. No paid replay,
forced production run, test draft, changed model/effort/shared budget or Nano Banana integration.
No source-image rights or exact text-quotation checks were relaxed. Existing assets/delivery
identities remain immutable. Natural visual generation may still be absent during a healthy
release smoke; report its measured state without claiming adoption.
