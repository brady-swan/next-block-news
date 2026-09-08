# Plan 0066 — source images and exact NBN graphics

Status: activated by owner September 7 evening; independent plan and implementation review
APPROVED. Release verification recorded in SPRINT-0066-FINDINGS.md.
Baseline: Plan 0065, runtime `02c864d`, prompt v2.22; owner approved the previously queued
PLAN-NEXT-POST-VISUALS.md. This activation supersedes that document's planning-only restriction.
All five templates and the four approved design references remain in scope.

## Product and boundaries

Offer useful source images plus deterministic bar/line charts, before/after, quote and styled
document-excerpt cards. Text-only is normal. Keep the current writer/editor models and effort,
15-minute cadence, research budgets, source policy and first-reply receipt. Autopost OFF.
No image-generation provider, new subscription/service, generic browser screenshot engine,
video/GIF, arbitrary cropping, quote-post publishing or image quota.
The existing Railway Desk receives a compact Visuals panel; no new Sites-hosted application.

## Kickoff updates to the queued plan

- Extend the combined reporter-writer, not the former delegated research seat. Add bounded
  tools to list candidates, inspect actual pixels, and render a selected fixed-template asset.
  Result metadata is not visual inspection. Both writer and editor receive exact stored bytes.
- Image inputs use existing Anthropic-compatible blocks converted to Responses `input_image`.
  Verify the configured Grok 4.3/4.5 models with a small isolated image-input smoke; never
  silently switch models. Separate encoded-image accounting from existing text-context limits.
  Observations retain asset manifests/hashes, not base64 copies.
- Exact source snapshots support verbatim excerpts/quotes. Native source paraphrases cannot
  supply literal quotation text. Preserve offsets, highlight spans, context, source dates,
  limitations and transformation metadata. Reject overflow rather than silently cut text.
- Immutable asset records/files are outside the 30-day reporting-artifact TTL. Link assets
  from existing notebook/Desk surfaces. Retain approved, pending-delivery, draft and published
  assets/evidence indefinitely for correction; unselected assets may expire after 30 days.
  Start with a 512 MiB soft admission cap: keep existing assets, decline new optional renders
  when full. No destructive pruning of delivered or pending assets.
- Keep existing image reuse permission separate from visual relevance. Unknown rights means
  review-only recommendation, never an autonomous upload. Record source/credit and the exact
  reuse basis. NBN-generated factual graphics use our own template, with source attribution.

## Concrete budgets and rendering

At most six candidate metadata records per source/story shortlist, two external image
inspections per story, four inspections and four new renders per run. Reuse cached assets.
Download at most 4 MiB and 12 million decoded pixels per static PNG/JPEG/WebP; no animated media
or external SVG. Use existing public-URL/redirect checks. Bound each fetch to 10 seconds within
the writer's existing deadline. Do not resize factual content behind the editor's back.
Model transport at most four selected images / 12 MiB base64 total per editor batch, separately
from 256 KiB text; capacity overflow explicitly defers the affected image-bearing candidate.
No new mandatory model turn: writer tool use and editor review use existing calls/reservations.
Track actual usage/cost and added latency; unchanged total model-call ceilings.

Code renderer: Pillow with packaged permissively licensed sans-serif fonts and existing NBN
icon; immutable PNG output, template version and deterministic input fingerprint. Match approved
charcoal/white/light-gray references, restrained accents and bottom-right branding.
Landscape data/quote/comparison 1600×1200; excerpt 1600×900; square 1600×1600 for every template,
reflowed rather than stretched. Exact text remains code rendered. Original-layout PDF excerpts
use installed Poppler within existing supported text-PDF/page limits; no OCR or arbitrary crops.
If that source's layout is unneeded, prefer the designed excerpt card.

## Delivery identity and resumable work

One shared versioned full-payload contract covers ordered post text/media IDs, immutable asset
hash, alt text and visible credits. Preserve historical text-only fingerprint calculation,
but never use text equality to confirm a media-bearing intent. Legacy drafts with unrecorded
media cannot be assumed untouched. Add full payload to canonical signatures and durable intent
materialization, create confirmation/matching, PATCH preconditions/read-back, reconciliation,
and owner bind. Media-only or alt-only owner edits stop automatic replacement.

Persist upload preparation independently of draft submission: save asset, upload ID and phase
before the next network step; one bounded processing-status poll at a worker boundary, no sleep
loop. Never enter draft mutation `in_flight` until media is ready and alt text reads back.
Pending approved work resumes without calling writer/editor again, while reserving its exact
canonical output. Extend existing mutation lifecycle with an explicit pre-delivery media state
if needed, rather than building a second publishing service. Read back exact attachment IDs
and their alt text; absent fields remain unresolved. An ambiguous mutation never becomes a
second text-only create. Old text-only flows retain their existing behavior.

The independent editor explicitly approves/omits the selected visual and assesses a standalone
text fallback. Approval binds final copy, asset hash, alt text and source credits. Omission can
deliver only that separately approved text payload; dependent copy holds. Unavailable, omitted,
recovery and capacity branches cannot attach an unreviewed visual. Recovery gets identical
image bytes and evidence. Later factual regeneration requires a new editor review.

## Desk and owner actions

Story inspector shows actual selected image, alternatives, source/credit/reuse status, purpose,
alt text, approval, upload/delivery status and errors. Use existing responsive side pane/modal.
Authenticated image GETs are read-only. Select/omit/fixed-preset regeneration are version-fenced
pending requests consumed by the existing worker, not immediate Typefully PATCHes or hidden
provider work in GET handlers. Recheck current publication and remote owner edits at execution.
No arbitrary image editor. Show pending, approved, omitted, failed and unresolved distinctly.

## Phases and acceptance

1. Prove quote evidence → deterministic PNG → durable storage → actual editor pixels → Desk
   preview → mocked versioned delivery/read-back. Establish adapters/identity/retention first.
2. Extend the same renderer to bar/line/comparison/excerpts and supported PDF page excerpts.
   Add bounded article-body/OpenGraph/lazy-load/X/quoted-X metadata collection while fetching
   relevant material; no extra crawler. Source dimensions/captions/date/credit stay unknown
   when absent. Exact pixels and support must remain separate.
3. Complete writer tools, editor initial/recovery/fallback, pending delivery/restart, owner
   controls and telemetry. Test all five templates at mobile display size and both presets.
4. Independent implementation review; regressions: signs/missing/zero/units/periods/overflow,
   quote paraphrase rejection/highlights/qualifiers, malicious/oversized media, every editor
   fallback, exact selected pixels, upload interruption, media/alt owner edits, unknown read-back,
   legacy fingerprints, ambiguous create/PATCH, notebook expiry, read-only Desk GETs.
5. Full offline suite and clean archive suite/build. Online SQLite backup; explicit Railway
   deploy from clean committed archive; health/Desk/schema/asset smoke and small isolated
   provider vision test. Do not mutate existing Typefully drafts for tests. Observe a natural
   eligible visual delivery and read-back; do not call absence of one a verified media success.
6. Update SYSTEM, HANDOFF, Desk guide, inbound/reporting docs and audit watches. Resume the
   same rolling audit with its previous full cutoff, backfilling build-window activity.
   Record release, costs, limitations and rollback. Runtime rollback is previous clean commit;
   preserve additive database/assets, never destructively restore the backup as routine rollback.

## Provider references checked at kickoff

- https://docs.x.ai/developers/model-capabilities/images/understanding — Responses image inputs.
- https://developers.openai.com/api/docs/guides/images-vision — base64 `input_image` format.
- https://typefully.com/docs/api — upload accepts `alt_text`; media status/metadata GET and PATCH;
  ordered draft `media_ids`. Live read-back compatibility must still be checked.

## Review record

Kickoff reviewer `lead_0066_review` confirmed six required contracts: shared payload identity,
bounded persisted upload, real pixels with separate accounting, safe editor fallbacks, durable
evidence, and versioned worker-owned Desk actions. All are explicit above. Final independent
plan verdict: APPROVED. Reviewer additionally required finite upload timeout and canonical
protection for pre-delivery media work; these are implementation acceptance checks.

Implementation review APPROVED after correcting confirmation ambiguity, same-batch image
accounting, optional tool errors, editor/normalization rails, visible credit, BTC precision,
media-free v2 continuity, truthful Desk selection and inert planned status. Final reviewer
also required the isolated transport fixture's tape path to be separate from production.
