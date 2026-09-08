# Plan 0070 — image evidence and graphics correctness

Owner authorized all five priorities and the established independent review playbook on September 8, 2026. Approved highlight styling is included. Status: independent plan and actual-code review approved; all 628 offline tests pass. Clean release verification is in progress.

Checkout: /Users/brady/claude/nbn-post-visuals-0070, branch codex/post-visuals-correctness.
Base: c4bc70e (current main; runtime last recorded ab7529e). The main checkout contains unrelated owner evaluator/audit edits and a separately pending appendix-reference repair. Preserve those. Import only this task's already-approved style changes. Reconcile any intervening reviewed release before deployment.

## Outcome and scope

1. A story's inspected source images reach the editor even when the post has no image attachment.
2. Four source inspections do not spend the separate allowance for four original renders.
3. Quotes/excerpts retain the source actually quoted; evidence-list order cannot change attribution.
4. The six approved highlight colors work in both presets.
5. A time-series line chart uses elapsed-time spacing; category/session spacing is explicit.

Preserve source/reuse policy, immutable assets, current writer/editor models and effort, six-call/360-second writer ceiling, shared tool limit, source receipts, publisher lifecycle, current visual review/fallback contracts and autopost OFF. Nano Banana remains parked. No forced production run, test publication or additional mandatory model turn.

Approved design: no internal fixture labels on images; meaningful source/date/unit qualifiers remain. NBN branding appears once at bottom-right. Highlights enlarge the unchanged passage within doubled outer padding. Approved mockups remain in the shared design workspace; offline proofs are synthetic fixtures documented outside their pixels.

## Implementation contracts

### Image evidence and attachments are separate

Add story-scoped visual_evidence_ids (bounded array of immutable inspected asset IDs) to the writer dossier, with an empty array for no image evidence. Existing persisted dossiers without the field remain valid. Each reference must resolve to this run, one of the story's member candidates, an inspected asset, and its recorded content hash. Reject malformed, foreign or uninspected references explicitly rather than dropping claimed support.

Normalize references into a distinct visual_evidence list carried through draft → main editor candidate → bounded editor card, retained review context and observations. An evidence-only image may have unknown reuse rights. It must never become attachable or acquire a visual approval because it was supplied as evidence.

The editor receives the exact pixels and provenance for all referenced evidence plus the optional attachment. Deduplicate repeated asset/hash pairs in transport; label role and story ownership. Keep the existing maximum four unique images/12 MiB per editor request and existing text limit. If a story's required evidence cannot be supplied, explicitly defer the whole affected candidate using existing safe human-review handling; keep usable siblings. Initial review and omitted-only recovery use the same immutable bytes. Evidence-only cards do not require attachment-approval fields.

Images can support independent visual judgment. This change does not invent OCR receipts or relax exact textual-quotation checks. Literal words unavailable in a retained textual receipt still require appropriate supported copy; editor pixel access alone is not permission to reinterpret writer transcription as direct source text.

### Separate allowances

Maintain external inspections (source images/PDF pages) separately from new rendered graphics. Limit each to four per run, and keep the existing two external inspections per candidate. Reinspection uses its applicable inspection allowance; rendering never increments the external counter. Retain the aggregate image-byte bound and ordinary tool/time ceilings. Count completed operations consistently; malformed specs should not spend the successful-render allowance. No retry loop or increased global tool/model budget.

Expose truthful inspection/render counters in existing observations so a rejection names the resource actually exhausted.

### Attribution

Resolve quote/excerpt source_url from validated source_fetch_id. Retain all evidence and exact passage/context metadata. For data graphics, record a deduplicated source_urls list based on the receipts actually referenced by points; keep the singular compatibility field deterministic from an actually used reference rather than arbitrary evidence-array order. The visible source label still receives editor scrutiny. Preserve legacy stored assets and pending delivery identities.

### Highlight palette

Pass the selected validated palette color through text layout into highlight fills. Preserve yellow as the excerpt default; explicit blue, red, yellow, green, orange and purple must render as requested. Use dark foreground with these approved fills and retain exact highlight offsets during wrapping/reflow. Same color survives preset regeneration. Increment template version for changed pixels; never overwrite immutable prior assets.

### Line-chart time semantics

Default new line recipes to x_axis=time, requiring unambiguous ISO calendar dates. Validate strictly increasing, distinct dates rather than silently reorder values. Position points in proportion to elapsed days. Keep every point and every missing-observation gap. x_axis=category explicitly opts into equally spaced category/trading-session observations; label this honestly in the chart.

Keep bar/comparison semantics unchanged. Avoid label overlap for closely spaced dates: choose a bounded collision-free subset of axis/direct labels while retaining every plotted observation, full recipe and alt description. Do not move points to make labels fit. Sparse/irregular dates must not be silently rendered at equal distances. Existing original assets stay immutable; old non-date recipes must be explicitly categorized when regenerated.

## Independent review and validation

- Independent plan review before the five-priority implementation. Resolve blockers in this plan.
- Regression tests through real writer normalization, main handoff and mocked editor initial/recovery/fallback, including evidence-only unknown-rights image, attachment/evidence deduplication, cross-story/run/inspection rejection, image capacity and missing bytes.
- Prove four external inspections still permit a render within total bytes/time; invalid rendering doesn't consume successful render count; fifth successful operation is refused in its own category.
- Attribution tests reorder multiple receipts and include an unrelated receipt first.
- Pixel tests cover all six colors, both presets, exact source/highlight preservation and approved margins.
- Temporal geometry tests cover irregular dates, negative/missing values, year boundary, unsorted/duplicate/invalid dates, categorical mode and close-label layout.
- Generate and visually inspect all affected templates, including short/long excerpts and an irregular series; preserve approved style. Use source fixtures without internal disclaimers in pixels.
- Independent actual-code review by a reviewer who did not implement it; resolve actionable findings and rerun relevant checks. Run full offline Python 3.12 suite; repeat full suite from the clean intended commit archive. Build/type-check Desk if its code changes.
- Paid model replay is unnecessary unless an unresolved adapter uncertainty requires it; request a bounded replay budget only if necessary. Do not claim natural model take-up from deterministic tests.

## Release

Follow HANDOFF-CODEX.md release playbook: reconfirm runtime/release identity and other task's pending release, target/one replica/data mount/autopost OFF; online SQLite backup; clean committed archive; explicit Railway deployment; status/health/relevant authenticated Desk and schema/asset smoke; observe natural worker progress without forcing run_once. Preserve active audit settings and its actual full coverage cutoff; do not overwrite its unrelated prompt-provenance investigation or state. No duplicate automation.

If the other task has deployed a newer repair, incorporate that reviewed code and retest rather than overwrite its release. Capture exact commit, backup, deployment, runtime hashes and tests in SPRINT-0070-FINDINGS.md and update current docs. Rollback is code-only to the immediately preceding confirmed runtime; never restore the database destructively or remove durable assets.

Natural production proof is scoped honestly: a healthy natural cycle is required. An image-bearing natural story may not arrive during release validation; explicitly report absence instead of asserting verified organic image creation.

## Review log

Independent reviewer visuals_independent_review: APPROVED, no blockers. Implementation checks
include atomic per-candidate image admission, original ownership during later Desk review IDs,
explicit legacy line-chart categorization, and bounded cached-asset reinspection. Implementation
is now in progress in the isolated checkout.

Main task confirmed at release coordination: no competing deployment and no newer runtime than ab7529e. Include its independently approved nine-line appendix-reference schema repair and five tests in the combined release, preserving all unrelated evaluator/audit changes. Combined marker is editorial-core-v2.29-visual-evidence.

Independent actual-code review: APPROVED with no blockers, including the coordinated appendix-reference repair. Reviewer independently passed 87 focused and 20 combined tests and inspected the v4 graphics. Full local combined suite: 628 passed. See SPRINT-0070-FINDINGS.md for release verification.
