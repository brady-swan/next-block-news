# Sprint 0066 — exact post visuals

September 7, 2026 Central. Implementation and release checks in progress; release evidence below
will distinguish local verification, provider capability and actual Typefully transport.

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
- Targeted final visual checks: 30 tests passed, including actual bounded Poppler page rendering,
  quote integrity, signed/missing data, same-batch image allowance, editor recovery/capacity,
  failed confirmation, interrupted upload, owner version changes and queued Desk actions.
- All ten template/preset proofs rendered and visually inspected. Desktop 1728px and mobile
  390px Desk previews loaded all five real PNGs without horizontal overflow; disposable selection
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

Pending clean-archive tests, explicit Railway backup/deploy, health/Desk checks, isolated
unpublished media transport and natural worker cycle. Rollback baseline: `02c864d`.
Restore code only for ordinary rollback; preserve additive tables/assets and pending intents.
