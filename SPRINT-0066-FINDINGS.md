# Sprint 0066 — exact post visuals

September 7, 2026 Central. Deployed and smoke-tested. The evidence below distinguishes local
verification, provider capability, actual Typefully transport and still-pending natural image use.

## What changed

- Optional article/X still-image inspection and original-layout PDF-page inspection in the
  combined reporter-writer. No extra crawler, image-generation provider, model seat or quota.
- Exact NBN bar, line, before/after, quote and highlighted-excerpt PNGs, landscape and square,
  using packaged OFL Inter fonts and the approved dark visual direction.
- Immutable pixels plus source snapshots, quote offsets/highlights, data units/periods, alt,
  source credit and reuse basis. Metadata is not inspection; native paraphrases are not quotes.
- Writer/editor image inputs, manifest-only observations and separate encoded-image allowance.
  Optional-image failures do not silently approve image-dependent copy or kill sibling stories.
- Persisted upload preparation and full-payload/version confirmation inside the existing
  publisher lifecycle. Lost acknowledgments stay protected; owner edits are not overwritten.
- Desk Visuals previews and queued selection/omission/preset regeneration with fresh editor review.
  Omitted/fallback images are distinct from the selected attachment. Planned drafts are not
  labeled published. Models, editorial stance, cadence and autopost OFF are unchanged.

## Review and verification

The independent lead reviewer approved the plan. Implementation review found actionable edge
cases in confirmation failures, image budgets, optional network errors, post-review normalization,
source credit, small BTC precision, hard-rail parity and full-payload continuity; these were fixed.
Final review requested only truthful omitted/fallback and inert planned labels, also corrected.
No further architecture expansion was requested.

- Full working-tree suite: 566 tests passed (includes two unrelated owner evaluator tests).
  Clean committed archive: **564 tests passed**; clean npm install, type-check and static build
  passed, with an identical compiled-asset manifest.
- Targeted final visual checks: 30 tests passed, including actual bounded Poppler page rendering,
  quote integrity, signed/missing data, same-batch image allowance, editor recovery/capacity,
  failed confirmation, interrupted upload, owner version changes and queued Desk actions.
- All ten template/preset proofs rendered and visually inspected. Desktop 1728px and mobile
  390px Desk previews loaded all five real PNGs without horizontal overflow; 1024px/2560px
  checks also passed. Disposable selection
  returned queued and did not invoke a model or change Typefully. Full-size asset links work.
- Configured Grok 4.3 medium and Grok 4.5 medium both correctly read a tiny two-color image.
  Combined provider-reported capability-probe cost: approximately $0.001692, recorded under
  `smoke:0066-vision-capability`, not production throughput.
- Read-only Typefully checks confirmed the current X post fields, empty media arrays,
  nullable settings and created/updated draft timestamps. Autopost was false.

The OpenAI documentation skill guided Responses image-input compatibility; PDF skill
render-and-inspect discipline guided original-page and template QA. No raster-generation model
was used: factual text and geometry are rendered in code.

## Limitations and watch items

Typefully exposes media-level alt text but not draft-local copied alt in draft GET. Confirmation
uses an immutable media ID/alt pair and the acknowledged draft version. Alt-only edits in the
Typefully UI have not been empirically proved to advance that version; do not claim otherwise.
Missing/changed snapshots stay unresolved. The transport fixture is not proof of editorial quality
or natural image selection. Until a natural eligible image is delivered, that live editorial path
remains a post-deploy observation item, not a claimed successful test.

Source-image rights must be explicit for autonomous attachment; merely being publicly viewable
is not permission. Original-layout PDF pages are bounded full pages, not arbitrary crops or OCR.
Short square quotes/comparisons deliberately use generous space. Test real long labels/quotes
for legibility and selective utility rather than forcing an image onto every post.

Storage admission stops at 512 MiB; immutable assets/evidence are not automatically deleted.
Back up `/data/visual-assets` alongside SQLite after visual production begins. The older system
PDF predates these tools; current Markdown/Desk documentation describes the new image path.

## Release evidence

Runtime commit **0232620**, pushed to origin/main and explicitly deployed from its clean archive.
Railway deployment **2c7fb9d9-46d9-4e2e-a1dd-837b7447dcec**: SUCCESS, one replica, `/data` mount.
Pre-release online SQLite backup passed integrity check:
`/data/backups/nbn-pre-source-policy-20260908T021831Z.db`.

Production hashes matched newsroom, immutable asset storage, delivery module and compiled Desk
manifest. Health and all four workspace views returned 200; JS/CSS, Review tools and APIs
returned 200; missing authorization returned 403 and nonexistent visual returned 404. The
natural intake cycle completed at 02:20 UTC with healthy process state and unchanged roster /
autopost OFF. Schema contains all three visual tables. No forced newsroom call was made.

One isolated **unpublished** Typefully draft **10673284**, created 02:21:37 UTC, is titled
`IMAGE CAPABILITY TEST — DO NOT PUBLISH`. It used the real renderer and resumable uploader;
the first pass persisted processing, the second confirmed the same intent after ready status.
Read-back verified two ordered posts, media counts `[1, 0]`, exact alt text and acknowledged
draft version. A subsequent read still matched exactly. No existing Typefully draft was modified.
Production `posts` contains zero smoke rows; separate journal/assets/tape remain at
`/data/smoke/visual-0066`. Do not count this synthetic transport fixture as editorial success.

The same `audit-nbn-production` heartbeat was restored ACTIVE at its 15-minute interval with
standing autonomy/quiet notifications preserved. Image-specific checks and first-natural-run
follow-through were added. It must backfill after the last full cutoff
**2026-09-08T00:47:12.894Z**; smoke/health checks do not advance that editorial audit boundary.

Clean npm install reported an existing PostCSS build-tool advisory. The dependency was not
changed by this sprint, processes our repository CSS offline and is absent from the Python
runtime; a routine dependency update remains maintenance work, not a discovered live image-path
vulnerability. No force upgrade or unrelated lockfile changes were bundled here.

Rollback baseline: `02c864d`. Restore code only for ordinary rollback; preserve additive
tables/assets and pending intents. If there are pending v2 media mutations, settle/hold them
before using a baseline that predates media identity; never blindly recreate them as text drafts.
