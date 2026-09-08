# Plan 0067 — Nano Banana as the writer's illustrator

Status: **PARKED BY OWNER — September 8, 2026. Do not implement.**
The independent lead previously approved this proposal for owner review. Brady now wants NBN
to produce useful original images with the existing tools before reconsidering Nano Banana.
Reopening this plan requires explicit owner approval; the first existing-tool image does not
automatically activate it. See Plan 0068 for the proposed existing-capability work.
Prepared September 7, 2026 Central, against the shipped Plan 0066 image pipeline.
Brady confirmed the key is from Google and, on September 8, reported saving it in Railway as
`GEMINI_API_KEY`. Its value has not been read or tested for this plan. Key availability does
not authorize implementation, API generation, deployment, or an audit change.

## Recommendation in one minute

Give the reporter-writer an optional **commission an illustration** tool backed by Google's
Nano Banana 2. The writer supplies a concise creative brief grounded in the story it has
reported. Generation runs as a durable background job while the writer continues working.
If the image is ready in time, the writer inspects it and the existing editor reviews the
exact final pixels with the copy. Otherwise the story proceeds without it; the result remains
available in the Desk. An illustration is never evidence and never a requirement to post.

Reuse the asset store, Visuals tab, editor image inspection, Typefully uploads, and delivery
protections built in 0066. Add one small job queue and one Google adapter, not another newsroom,
new hosting service, art-director model, or automatic late-image rewriting workflow.

The important tradeoff: this deliberately favors timely reporting over putting an image on
every post. We should measure how often an otherwise useful image finishes too late before
adding special waiting or continuation machinery.

## 1. What the writer should use it for

The writer has four visual choices, not a requirement to use the new tool:

| Reader need | Preferred route |
| --- | --- |
| A real person, place, device, incident, or documentary record | Relevant source image with established reuse rights |
| Exact quantities, comparisons, quotations, or source text | Existing code-rendered charts, quote cards, and excerpts |
| A relationship, mechanism, or abstract idea that a picture makes clearer | Nano Banana illustration or simple conceptual explainer |
| A short news item already clear in words | Text only |

Good uses include a distinctive self-custody illustration, an understandable visual metaphor
for a policy bottleneck, or a simple explanation of how a Bitcoin mechanism works. The aim is
recognizable, useful, attractive editorial work—not a generic gold Bitcoin floating beside a
flag on every post. Atmosphere can be useful, but should be specific to the story.

Keep the first release narrow:

- Generate still illustrations; allow one targeted revision of an NBN-generated result.
- Use an optional NBN-owned style reference or the earlier generated image as an edit target.
  Do not upload arbitrary third-party images for restyling in this release.
- Do not manufacture purported news photographs, screenshots, official documents, quotes,
  charts, maps asserting facts, endorsements, or depictions of a named person doing something
  the reporting does not establish. A clearly illustrative object or conceptual scene is fine.
- Exact numbers, factual labels, quotes, and the NBN logo remain code-rendered. A model-drawn
  arrow can itself assert a relationship: the editor still checks explanatory diagrams.
- No Google search/grounding tools in the image request. The reporter supplies the facts;
  Nano Banana composes the visual rather than opening another research process.
- Existing editorial remit, source policy, model roster/effort, writer cadence and research
  budgets stay unchanged. Autopost stays OFF during implementation and rollout.

These are proposed visual guidelines for Brady's review, not a silent orientation change.

## 2. Writer experience and prompting

### Small tool surface

Add `request_illustration` to the writer's existing tool set. It saves the request locally and
returns immediately with a job ID, status, cost reservation, and next action. It does **not**
wait for Google or imply the image exists. Extend `list_visuals` with pending/completed jobs;
reuse `inspect_visual` to retrieve actual finished pixels. No separate polling tool is needed.

The brief is structured enough to prevent lost context, but the writer retains creative choice:

| Field | What the writer supplies |
| --- | --- |
| `candidate_id`, `evidence_fetch_ids` | Existing candidate and relevant retained receipts |
| `purpose` | One sentence explaining how this picture helps the reader |
| `story_context` | A short, factual description including scope and important caveats |
| `creative_brief` | Subject, visual idea, composition, style, and what must not be implied |
| `preset` | Landscape 4:3 or square 1:1 |
| `overlay_text` | Optional short explanatory heading, rendered locally—not a quotation/data table |
| `reference_asset_id`, `reference_role` | Optional registered NBN style reference or prior generated result |
| `revision_of`, `change_request` | Optional one-change revision, preserving the original |

These are proposed field names, not an API the current writer can call. All nullable optional
fields are explicit in the eventual strict tool schema. Keep the complete text brief within
6,000 characters and evidence to four references. The application supplies format, disclosure,
brand settings, and API configuration; the writer does not choose credentials, provider, model,
price tier, arbitrary output dimensions, or filesystem paths.

The tool should return something like:

```json
{
  "job_id": "illustration_…",
  "state": "queued",
  "next_action": "Continue reporting. A ready notice will appear at a later normal tool boundary. Inspect the image before selecting it. Do not wait or repeatedly poll."
}
```

At natural writer-turn boundaries, add a tiny ready/failed notice for jobs that changed since
the last notice. Metadata notices do not include image bytes or count as inspection. The writer
can then call `inspect_visual` when useful. Suppress unchanged notices and repeated local polls.
Never create a new model turn just to announce a job.

### Proposed prompt addition

> You can commission an original illustration when it makes this particular story clearer or
> more compelling. Think like a reporter briefing an illustrator: explain the story, the one
> idea the reader should grasp, the scene or visual relationship you want, and anything the
> picture must not imply. Give Nano Banana a coherent description, not a pile of style keywords.
>
> Request it once the reporting supports a stable concept, then continue your work. An image
> job is not a finished image. If it becomes ready, inspect the actual result at phone size:
> does it help, does it suggest anything untrue, and is it worth the space? You may request one
> specific correction. Keep what works; do not ask it to start over simply to explore variants.
>
> Prefer our exact graphics tools for data, quotations, and document excerpts. Generated images
> are illustrations, never sources. Write the post so it stands on its own. If the illustration
> is slow, weak, or unnecessary, submit the story without it. Do not spend your remaining turns
> polling, delay breaking news for decoration, or imply that an unselected image is attached.

Put this next to the existing visual tool guidance in `nbn/visual_tools.py` (or a small imported
illustration guidance module), not in the main editorial orientation. Keep the brand/prompt
scaffold in one versioned file such as `prompts/illustration-brief.md`. Both the live prompt
hash and Desk provenance must include the effective guidance version.

### Example commission — conceptual policy story

This example assumes the reporter has already established a specific legislative bottleneck;
it is a design example, not a claim about today's news.

**Writer brief:**

> Help readers understand that a Bitcoin-related bill still needs two chambers to agree on one
> text. Create a restrained editorial cut-paper illustration of two differently shaped sheets
> approaching a single document-shaped opening. The mismatch is the point. Charcoal background,
> pale paper, one muted orange accent. Clear silhouette, readable as a small feed image. Do not
> show a signed law, a passed vote, named politicians, official seals, a price chart, or an
> inevitable outcome. Leave a calm lower margin for our small credit and heading.

The application wraps this with: intended use on NBN's X feed; illustrative rather than
documentary treatment; fixed aspect/size; no invented text/logos/data; optional explicitly
labeled style reference; space for the local overlay. It sends the compact factual brief, not
the whole newsdesk, raw article pages, source instructions, or private operational history.

An optional local heading could be “Two chambers. One bill.” The renderer adds the approved
NBN mark and “AI illustration” disclosure. The writer's alt text must describe the **returned
image**, not repeat its requested scene. Existing quote/excerpt templates remain the right
choice when the actual statement or document is the useful visual.

## 3. Model, API, and key

Recommend **Nano Banana 2, `gemini-3.1-flash-image`, 1K**, via the direct Gemini API. Google
currently describes it as the general-purpose member of the family; Pro and Lite are separate
models. Start with one model, not routing or automatic upgrades. [Google image guide](https://ai.google.dev/gemini-api/docs/image-generation),
[model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-image).

`GEMINI_API_KEY` is already saved in Railway, per Brady's September 8 confirmation. Reuse
that existing secret when implementation is authorized; do not create or overwrite a placeholder.
Do not paste its value into chat, commit it, or create evaluator-specific replacement keys.
Document the variable name without its value in the implementation's configuration reference.
Billing attribution belongs in our database. This plan does not inspect or use Brady's key.

The planned adapter targets Google's Interactions image interface. Explicitly request a single
image format, size and aspect ratio, with search disabled. Do not add Gemini to the generic
reporter/editor model router: generation is a tool service, not a new editorial seat.

Google documents background Interactions with a returned ID and resumable status retrieval.
However, the exact combination of **this image model + background execution + chosen API
revision** has not been live-tested here. Phase 1 must verify it. Pin the working contract in
fixtures rather than assuming generic background support proves model compatibility.
[Background execution](https://ai.google.dev/gemini-api/docs/background-execution),
[Interactions reference](https://ai.google.dev/api/interactions-api).

If that combination is unsupported, use one bounded synchronous Google request **inside the
background image worker**, never inside the writer tool call. Choose and implement only the
working adapter path after the capability probe; do not build two speculative transports.
That fallback survives writer timeouts, but an interrupted request without a provider ID cannot
be resumed remotely. Record it as unknown and leave the story unaffected.

Do not use Google's Batch API for the live wire: its documented target can be 24 hours, which
does not fit this job. [Batch guide](https://ai.google.dev/gemini-api/docs/batch-api).

## 4. Async execution without a second newsroom

### One durable table and a small worker

Add `illustration_jobs` in the existing SQLite database and a bounded worker loop in the same
Railway process. Its own SQLite connection and short job claims are separate from the main
cycle lease. No Redis, Celery, new Railway service, webhook endpoint, browser session, or
long-running model conversation is required.

Persist: local job/fingerprint, originating run and candidate IDs, frozen brief/evidence
snapshot, reference hashes, model/config/prompt version, parent revision, timestamps, state,
claim/version, provider interaction ID when known, output asset ID, sanitized error, and billing
usage/reservation. Bind to the application's resolved canonical story only after dossier
validation. A writer-supplied event label must not reserve a story identity.

Suggested job states:

```text
queued → submitting → running → ready
                    ↘ failed / unknown / expired
```

Editorial selection, editor approval, upload, and publication remain separate existing states.
`ready` means bytes are available, not that an image is approved or attached.

Rules that matter:

- Commit the job before waking the worker. Repeating the same request returns the same job.
  A purposeful revision creates a new job linked to the earlier one, never overwrites it.
  Fingerprint candidate membership, frozen brief/evidence, reference/parent hashes and effective
  model/prompt/config—not the request timestamp. Repeated attempts do not refill their budgets.
- The image worker only talks to Google and stores assets/telemetry. It never calls the writer,
  editor, or publisher; never shares their connection or global model-call reservation.
- Claim a job atomically and commit before network I/O. A claim outlives its bounded request;
  result writes require the same ownership/version. No database transaction remains open over
  a provider request. Restart cannot create a second untracked request for the same job.
- With native background support, save the provider ID immediately and resume GETs after a
  restart. Use bounded requests (10 seconds for status; 20 seconds for submission) with local
  scheduled backoff, not a long blocking sleep or model polling loop.
- Use a **five-minute absolute job deadline**, not a five-minute writer wait. Status polls do
  not reset it. A synchronous-worker fallback has a bounded request within that deadline.
- Known-ID lookup failures retry the same ID within the deadline. A lost submission response
  without an ID is `unknown`, not permission to regenerate. The API reference does not establish
  a create-idempotency guarantee; do not invent one. Definitive rejections/refusals are errors,
  not a reason to cycle models or rewrite around a provider safety refusal.
- Deadline expiry stops automatic selection and new work; cancel a known running interaction
  best-effort. Unknown charges remain visible. A late response is retained as late/unselected,
  never resurrects a delivery. Shutdown does not wait indefinitely or lose already saved bytes.
- Generation does **not** enter `publisher_mutations` or `awaiting_media`. Those protect actual
  delivery and would otherwise block the very text-only post we want to preserve.

### When the image finishes

**During the originating writer run:** inspect it with the existing tool, select its asset ID,
and submit the normal dossier. Normal editor review sees the exact final pixels and the brief.
No extra writer session or editor seat is added. Same-run optional tools stay inside existing
writer round/time/image-context ceilings; requesting a job does not increase those ceilings.

**After the writer has submitted:** deliver the standalone copy through the existing editorial
path on its existing timing. The completed illustration appears in that run/story's Visuals
panel. It is not auto-attached, a new lead, a new draft, or a reason to awaken the newsroom.

Brady may select a late image for a sole untouched, unpublished draft using the existing queued
Desk action and fresh editor review. Published, scheduled, owner-edited, commented, ambiguous,
or pending-delivery output remains protected. A later genuine editorial run may retrieve the
asset through memory, inspect it again and select it if still relevant; completion alone does
not earn renewed coverage. No automatic image-only writer/editor continuation in this release.
For this late-image action, require the existing draft at both request and execution: the current
generic `visual_choices` path can create when its target is absent, and that behavior must not
be inherited here. A vanished/no-target draft returns review-only, not a new publication intent.

To make pending intent visible without violating `visual_asset_id`'s inspected-image contract,
add a nullable `illustration_job_id` to a story's dossier metadata. Validate job ownership and
membership and associate it with the resolved story. An unresolved ID never enters `draft.visual`,
never triggers an image hold, and cannot set `visual_required`. All generated images in this
release are optional; the post must make sense without them.

If the candidate is dropped or the writer run fails before a valid dossier, retain a clearly
labeled orphan/unselected request for inspection; cancel pending work when practical. No
recovery path treats that request as a publication decision or automatically promotes it.

## 5. Assets, actual review, and delivery

Save provider originals locally, then make a distinct final asset with any local heading,
NBN mark, and visible **AI illustration** label. Preserve originals and provider provenance;
do not strip or promise to preserve invisible watermark properties through every transform.
Google says its generated images include SynthID. [Image guide](https://ai.google.dev/gemini-api/docs/image-generation).

Both writer and editor inspect the **final composited bytes**, not the raw image alone. Record
each transform, parent hash, model/returned version, complete prompt, reference roles, evidence
snapshot, generated time, selected time, and actual alt text. `kind=ai_illustration` distinguishes
this from a documentary source image and a deterministic chart. Never file generated pixels
as a fetched receipt or let them establish a fact in reporting memory.

Close the current alt-text handoff explicitly: a saved generated asset starts with provisional
alt. After seeing its pixels, the writer supplies final alt alongside selection (a nullable
`visual_alt_text` dossier field). Create an immutable metadata variant linked to the identical
pixel hash and the actual current-run inspection; never infer inspection from the brief.
The editor approves that final asset/alt pair. For late Desk selection, the editor must supply
or confirm an accurate description from the pixels before approval. The existing asset-inspection
tool does not currently update arbitrary saved-asset alt, so this is a real integration task.

Reuse `visual_assets` and the content-addressed file store. Keep generated raw/final assets
under the existing 512 MiB admission policy, accounting for both. Preserve pending/selected/
delivered assets and their provenance outside ordinary notebook expiry. No automatic deletion
or new storage service in this sprint. If full, decline optional generation before spending;
save/validation failures must remain visible rather than attach a partial or different image.

Retain existing static-image/decoded-pixel/context limits. Bound Google's encoded response
before decoding; accept one non-empty final image, not a thought image, partial output or a
text-only refusal. An unexpected oversized result is not usable merely because generation
succeeded. Explicit, recorded local normalization is allowed for an illustration; the exact
result after normalization is what gets inspected and approved.

Editor guidance adds only: does the illustration serve the story, imply something false, look
like fake documentary evidence, repeat unsupported details, or fail mobile readability? Is the
alt accurate and AI disclosure present? The existing approve/omit/hold and independently approved
standalone fallback stay in place. Reuse permission for submitted reference material remains
separate from whether the output is new; do not claim exclusive copyright automatically.

The final image goes on the main post; the factual source stays in the first reply. Add visible
AI provenance to the existing credit/disclosure surface. Use Typefully's `made_with_ai` field
only after confirming its supported mutation/read-back contract. Crucially, current
`x_payload.editable_surface` treats a true value as owner-controlled nondefault data: we must
extend full-payload identity to own/compare the expected flag, not just allow arbitrary true
values. Preserve historical v2 fingerprints through a new version if the shape changes. Flag
omission on image removal/fallback and all create/PATCH/recovery/owner-edit checks need tests.
If the field cannot be supported, use visible image/reply disclosure and document the limitation;
do not weaken payload confirmation to make the flag pass.

## 6. Memory and the Desk

Extend existing surfaces rather than add a new application:

- **Story → Visuals:** request purpose, generation state/age, preview, model/resolution, cost,
  prompt, reference/parent, writer inspection, editor verdict, and actual delivery status.
  Late ready images clearly say **Available, not attached**; a submitted brief is not a preview.
- **Run:** generation requests, completed/used/unused images, pending work and incremental cost.
  A completed editorial run may still have a pending optional image job; label both clocks.
- **System:** “Illustration — Nano Banana 2” role, enabled/disabled/key-present (never key value),
  queue/last success/error and image spend as its own stage in run/day/week/month breakdowns.
- **Actions:** existing select/omit; a bounded “Revise illustration” action saves one concrete
  change request and parent asset. Queuing a revision does not select or attach its result.
  GET requests remain read-only. Owner selection still invokes the existing guarded editor path.
- **Memory:** a compact artifact index entry with job/asset ID, concept, originating event,
  generated date, factual-context date, selection/outcome and reuse caveats. Read on demand,
  never inject all images/prompts into the desk. Pending/rejected/unused is not covered/published.
  Current `visuals.proposal` run/candidate checks must use the existing inspect-and-import path
  for cross-run reuse, not be bypassed for generated assets.

Keep full prompts, source context and errors in authenticated local records. Provider links
are operational references, not permanent storage or public image URLs. The default Google
stored-interaction retention is not our asset retention policy. Background mode needs stored
interactions; document that limited public-story briefs/references are sent to Google.
[Interactions storage documentation](https://ai.google.dev/gemini-api/docs/interactions-overview).

## 7. Cost and practical bounds

Google's current standard 1K Nano Banana 2 image-output price is approximately **$0.0672/image**
(1,120 image tokens at $60/million), plus input and any text/thinking output. A 2K image is
about $0.1008. For illustration only: three 1K generations/day are about **$6.05/month**;
eight/day about **$16.13/month**, using 30 days. These exclude revisions, input, and writer/editor
image inspection—not a promise of all-in cost. [Official pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-image).

Proposed initial operating limits, not editorial quotas:

- One active provider generation at a time; at most four queued/active jobs.
- At most two paid generations per writer run, including revisions; one original and at most
  one targeted revision per story concept. Identical requests reuse their existing job.
- At most ten paid attempts per Central calendar day across writer and Desk actions combined.
- A $1/day **generation admission budget** including known usage and outstanding conservative
  reservations. Start by reserving $0.15/attempt; phase-1 token/response limits must substantiate
  that reserve, otherwise increase it and accept fewer optional jobs. This is a stop-new-work
  guard, not a provider-enforced hard billing cap. Unknown submissions retain reservations.
- 1K only; one reference image at most. No automatic Pro/2K escalation, best-of-N, retries after
  unknown submission, or speculative images for every intake card.

Meter every generation/revision once under `image_generation`, linked to its originating run
and job. Track input by modality, output image/text/thought tokens, actual model, rate version,
latency, rejected/unknown attempts, and cost basis. Extend the existing usage schema/normalizer
so image output is not priced as text. Repeated polls of cumulative provider usage must **not**
insert repeated charges. Missing usage is unknown, not zero; a request with uncertain outcome
can still cost money. No hidden generation retries from an SDK.

Normal writer/editor image tokens remain charged to those seats. Report them alongside generation
cost without claiming a precise incremental review cost when the provider cannot separate it.
Owner-triggered extra editor reviews are visible separately. Track $/used image, unused spend,
request→ready and ready→selected latency, same-run availability, and text delivery latency.

## 8. Phased implementation, after approval

1. **Provider proof and example review.** With the supplied Google key installed securely,
   make a few isolated requests: generation, bounded targeted edit, background restart/retrieval,
   metadata/usage. Check the actual API revision, returned image blocks, refusal handling and
   price accounting. If background is unsupported, prove the isolated-worker fallback instead.
   Produce 3–4 representative NBN illustrations plus phone-size previews for Brady to review;
   no production publishing. Use examples for prompt calibration, not a new benchmark project.
2. **Durable worker → existing assets.** Add the Google adapter/job store, local claims,
   cost reservations, bounded response handling, restart behavior and final local compositor.
   Prove slow/failed Google calls do not stall the newsroom, intake, health, or HTTP Desk.
3. **Writer/editor/Desk integration.** Add the commission tool, brief guidance, natural-boundary
   notices, dossier job reference, exact image inspection, current editor checks, provenance,
   memory indexing, owner selection/revision, cost/role views and disclosure identity handling.
   Generated outputs do not alter normal text delivery or cause automatic late patches.
4. **Independent implementation review and verification.** Test the matrix below; full clean
   suite and Desk type/build checks. Review for disproportionate complexity and reduce it.
5. **Draft-only rollout.** Pause the existing audit only during the authorized build/deploy
   window; preserve its cutoff. Back up SQLite plus assets, deploy a clean archive, smoke health/
   Desk/read-only auth/provider generation and one isolated labeled unpublished Typefully image
   draft. Verify exact image, alt and disclosure read-back. Observe a natural same-run image use
   separately; a synthetic transport test is not proof of editorial value. Resume the same audit
   with image-quality, latency, late/unselected and cost watches. Never enable autopost.

No phase is started by saving this plan. Phase 1's sample review is a deliberate small checkpoint
before using a newly generated visual style on real drafts.

### Concrete code map

| Area | Expected change |
| --- | --- |
| New `nbn/illustration_jobs.py` | Durable jobs, claims, deadlines, admission and worker loop |
| New `nbn/illustration_google.py` | One verified Google request/status/result contract |
| `visual_tools.py`, `newsroom.py` | Commission tool, pending/ready notices, inspected-image selection, dossier metadata |
| `visuals.py`, `visual_render.py` | Original/final generated asset lineage, small deterministic overlay |
| `editor.py` | Generated-image context/disclosure and existing exact-pixel verdicts |
| `main.py`, `config.py`, `.env.example` | Worker lifecycle, explicit enable flag, secret name and bounds |
| `store.py`, `desk_api.py` | Additive job/usage data and truthful stage/role/cost projections |
| `writer_memory.py`, `visual_choices.py` | Bounded job/artifact recall and owner-requested revision/selection |
| `x_payload.py`, publisher modules | Version-aware AI-disclosure flag and unchanged mutation protections |
| `desk_ui` and compiled assets | Extend existing Visuals/System panels, preserve responsive design |
| Current system/prompt/Desk docs | Describe shipped behavior only once implemented; keep this plan separate |

The code map is scope, not a requirement to split more modules or rewrite existing components.
The current generic model client stays for the existing editorial seats.

### Acceptance and failure cases

- A blocked generation call cannot consume the writer's finalization reserve or block sibling
  stories; the original run can finish text-only without an image-specific hold.
- Repeated requests, concurrent claims and restarts do not create unnoticed duplicate spend.
  Known-ID restart resumes that ID; lost-ID ambiguity stays visible and unselected.
- Pending completion after dossier, drop, merge, publication, owner edit or new revision cannot
  attach itself, create coverage, or revive a superseded event. Orphans are inspectable.
- Wrong candidate/run/reference, stale permission, unexpected image count, invalid/oversized
  bytes, text-only refusal, empty success, expired output, and full storage fail locally.
- Final—not raw—pixels go to both models; metadata alone never creates inspection/approval.
  Wrong implications, invented labels, weak visual relevance and unreadable mobile output are
  editorial example checks, not a new deterministic content-scoring gate.
- Test visible AI disclosure and any supported Typefully flag through create, replacement,
  image removal, fallback, confirmation, reconciliation, owner-edited and legacy payloads.
- Publication or a Typefully edit during a queued Desk selection stops that mutation through
  existing version checks. No blind POST/PATCH retry and no mutation from a GET.
- A late-image selection with no target draft, or a draft removed between request and execution,
  cannot take `visual_choices`' existing create branch. No new draft or coverage row is created.
- Meter cumulative usage once, include unknown reservations and rejected attempts, and do
  not show unmeasured costs as free. Prompt/asset expiry cannot erase delivery provenance.
- Disabling generation stops new admissions, permits bounded retrieval/storage of already
  submitted results, and never automatically uses them. Existing drafts/assets remain intact.
  Runtime rollback leaves additive jobs/assets/usage in place; no destructive database restore.

## 9. Explicit non-goals and what to watch first

No automatic late-image editor mini-pipeline, no waiting for an illustration before publishing,
no new image-driven editorial research, no video, arbitrary third-party editing, generated data
charts, browser automation, broad model router, or exhaustive style taxonomy. Do not make an
image a new excuse for holding a good story.

The first useful measurements: Are the images actually good? Are we using fewer generic visual
clichés? Does the writer request early enough for useful same-run results? How many dollars and
seconds produce an image we actually use? Does the disclosure stay readable without dominating?
If late completion is common, bring that measured tradeoff back to Brady before adding a bounded
join or draft-only completion step. Not every foreseeable optimization belongs in this build.

## Independent review

Reviewer: `lead_0066_review`, the independent lead coder from the shipped image sprint.
Initial advice incorporated: generation is distinct from delivery; pending jobs do not reserve
canonical publication state; late images do not earn a new lead/run; avoid a new automatic
image-only writer/editor continuation. The reviewer read the full saved plan and rechecked the
current tool/proposal/Desk contracts. Final verdict: **APPROVED for owner review, no blockers.**
Their final watchpoint—late image selection must not inherit the generic Desk action's ability
to create a draft when no target exists—is now explicit above and in the acceptance tests.
The actual-pixel-to-final-alt metadata path was also reviewed. Review record:
`docs/planning/nano-banana-lead-review.md`. This is plan approval, not implementation approval.

## Owner review / next authorization

This plan asks Brady to approve: the optional illustration remit, Nano Banana 2 at 1K, the
background/no-wait behavior including late Desk-only results, the visible AI disclosure,
small generation allowance, and the sample-review checkpoint. The existing Google key/provider
choice is confirmed. Nothing here grants permission to implement until Brady says to proceed.
