# Plan 0051 — Editorial flow reliability and model-owned judgment

## Decision

Keep editorial core v2 and repair the seams that are suppressing good work. Do not start
over and do not add another editorial layer. Sonnet remains the run-scoped story desk and
the independent Sonnet editor remains the final editorial seat. Code becomes a small,
visible mechanical shell around those judgments.

This combines two production findings:

- useful inspected evidence, source work, and editor feedback can be lost or hidden between
  runs, causing the same story to restart and fail repeatedly; and
- source tiers, elevated-claim corroboration, semantic identity, quote exactness, and scope
  checks still operate as hidden code vetoes after Sonnet has already made a reasonable
  editorial call.

The product stance remains practical: produce good Bitcoin coverage, learn in production,
and reserve hard failure for conditions code can determine with near certainty.

## Authority boundary

### Hard code rails

Code may block delivery only for:

1. unsafe/private URLs or failed/empty fetches;
2. malformed protocol identity (unknown candidate/fetch IDs, duplicate membership, empty
   post, or a story with no inspected evidence);
3. publisher constraints (URL embedded in copy, post length, invalid/unverified mentions);
4. a verbatim quotation absent from every inspected receipt;
5. explicit investment instructions;
6. exact output/receipt duplication and publisher idempotency/lifecycle ambiguity;
7. lost worker lease or kill switch. An unavailable final editor may stage only a candidate
   that already passes every mechanical rail as a Typefully draft; mechanically invalid copy
   remains held with its typed rail.

These rails are mechanical and must produce a typed, owner-visible reason. They do not judge
whether a source is prestigious enough, whether a discrepancy is material, whether a story
is important, or whether two descriptions are semantically the same event.

### Advisory editorial signals

The following become structured warnings supplied to the independent editor, not code vetoes:

- unknown or lower-tier source, aggregator/discovery provenance, or a source not yet listed;
- elevated allegation/hack/legal claim with only one inspected report;
- first-party/official identity not recognized by the registry;
- Bitcoin-scope ambiguity or mention of another asset in a Bitcoin-relevant story;
- paraphrase, quote attribution/style, source-attribution, and numerical presentation concerns
  that are not a mechanically unsupported verbatim quotation;
- proposed event-key conflict, possible prior coverage, or suspected semantic duplicate;
- freshness, story weight, macro relevance, treasury-company relevance, and whether a guide
  account's framing is stronger than the evidence.

The editor receives the complete inspected evidence pool, source metadata, recent feed, and
warnings. It may publish, revise, route to Typefully draft, or drop. A publish/revise decision
that passes the small hard shell is authoritative; code must not apply another editorial veto.

## Evidence and source behavior

Any safely fetched public page with usable text is inspectable evidence in v2. The source
registry remains valuable metadata — tier, known identity, role, independence, and preferred
receipt — but is not a closed allowlist. The editor packet must label each receipt's capability
as known reporting, unknown-domain material, first-party statement, discovery/guide material,
aggregator/wrapper, or syndicated release.

The newsroom and editor are told:

- prefer primary artifacts and original reporting;
- one credible inspected source can support an ordinary factual story;
- allegations, hacks, crime, disputed claims, and consequential legal assertions should
  ordinarily have a primary artifact or two credible independent reports;
- when that ideal is unavailable, use common sense: narrow and attribute the claim, send it
  as a human draft, or drop it. Do not let code make that editorial choice invisibly;
- a company or authority's own safely captured page may be treated by the editor as first-party
  evidence of its own action even when its domain is absent from the curated registry, but an
  unknown page never becomes first-party merely because feed text or the model names a company;
- X intake text is context until a tool produces a real inspected fetch record. An inspected X
  post can support only “this account said X,” not the truth of the underlying claim or an
  independent corroboration count. Guide/detector posts remain attention priors and should
  normally be replaced by a stronger receipt;
- aggregators, wrappers, and syndicated copies are never labeled official or independent, even
  when the editor elects to use one with narrow attribution;
- search snippets remain pointers and can never enter the inspected evidence pool.

The selected receipt is the reader-facing link. Other inspected receipts may jointly support
the copy; the selected page no longer has to reproduce every detail by itself.

## Durable workbench repair

Add a bounded `evidence_pool_json` field to `newsroom_story_memory` through the existing additive
column migration. Existing rows are seeded lazily from all stored attempts, newest-first — never
only `attempts[-1]`. Every saved attempt merges up to eight unique inspected evidence cards into
this pool. Each card retains at most 8 KiB of text and preserves the original `inspected_at`;
reuse never refreshes its age. The same canonical URL replaces its older version. The same
content fingerprint across different URLs collapses to one evidence body so mirrored or
syndicated pages cannot create false independence.

Once evidence is pooled, attempt history retains provenance/reference fields but not a second
full copy of evidence text. The pool has a 70 KiB serialized ceiling, compact attempt history an
18 KiB ceiling, and the entire memory row a 96 KiB ceiling. Oldest attempt details are removed
before valid pooled evidence. A later empty attempt never erases the pool. The next run rehydrates
evidence from the pooled field rather than only `attempts[-1]`. Rehydration still enforces:

- 24-hour evidence age;
- content fingerprint integrity;
- public HTTP(S) URL safety;
- current source reclassification; and
- per-run code-owned `memory_*` fetch IDs.

Continuity cards use the most recent nonempty proposed post, the newest unresolved objective,
the pooled evidence set, and the latest editor feedback. Expired/corrupt evidence is omitted,
but its absence never suppresses the candidate.

## Story identity and materialization

Structural identity remains hard: candidate and fetch IDs must exist, and one candidate cannot
belong to two output stories. Semantic identity becomes advisory:

- if members already carry one canonical family, reuse it;
- if members carry conflicting families, do not auto-merge aliases. Use a separate submitted
  attempt/output key for the commit, workbench, and draft record; preserve every member's existing
  `items.story_key`; warn the editor; and force the result to Typefully `DRAFT` even if the editor
  says publish;
- if Sonnet supplies an unknown `existing_cluster_key`, ignore it for mutation, retain the
  submitted key, and warn the editor;
- only register a proposed alias after an unambiguous one-family match;
- recent feed and coverage cards remain the primary duplicate/UPDATE context for both models.

A conflict attempt/output key must not equal or canonicalize to any member family and must not
already identify a post or workbench. On collision, derive a deterministic non-aliased review key
from the submitted key plus the run/story digest. Never register that key as an alias during the
conflicted run. Existing member keys remain unchanged; only previously keyless members may receive
the review key. Resolution persistence and `log_post()` use the isolated review key without
canonicalizing it into a conflicting family.

Every unique, nonempty story ID in the accepted bounded dossier gets a durable
`newsroom_story_commits` row
before the shadow/materialization branch, including stories that fail protocol validation.
Add a bounded `details_json` column (12 KiB maximum) containing the validation outcome, typed
reason, editorial warnings, editor verdict/reason, force-draft reason, and delivery outcome.
Duplicate story IDs create one held commit with `defer:invalid_story_identity`; empty IDs cannot
have a commit and remain visible through item-level `defer:invalid_story_identity` diagnostics.
Valid stories begin `pending`; protocol-invalid stories begin `held`. Editor drop, omission,
outage, post-editor mechanical failure, and publisher delivery update that same row. This removes
the current observability hole where a model says `publish` but no story commit exists because
conversion rejected it first.

Candidate omissions still become `defer:model_output_missing`, never `skip`.

The strict dossier contract and code both cap decisions at 25, stories at 25, member candidate
IDs per story at 25, and evidence fetch IDs per story at eight. A provider response that exceeds
any bound despite the strict schema is a run-level protocol failure: defer the inventory and
record no silently sliced or uncommitted stories.

Shadow runs also close commit lifecycle. After observation, every valid `pending` shadow story
transitions to terminal `observed`; invalid stories remain `held`. `pending` always means real
materialization is still in progress.

## Search degradation

SerpAPI remains the model-free search provider, but a 429/transport failure must not consume the
entire research budget or become a reason to abandon usable inspected evidence:

- open a per-session search circuit after the first provider 429 or two retryable transport
  failures;
- subsequent calls return one typed `search_unavailable_for_run` result without another HTTP
  request;
- instruct Sonnet to use direct intake/reference URLs, outbound links, pooled evidence, and
  narrower attributed copy when search is unavailable;
- persist search-degraded status in newsroom counters/diagnostics so the audit can distinguish
  editorial drops from infrastructure-limited research.

This sprint does not add a fragile scraped-search fallback or a second paid vendor. Search
provider redundancy can be evaluated separately from the editorial repair.

## Independent editor contract

Replace `code_notes_to_fix_before_delivery` with two explicit fields:

- `mechanical_rails_to_fix`: deterministic failures that must be removed before delivery;
- `editorial_warnings`: source, corroboration, identity, quote, scope, and novelty concerns
  requiring judgment.

The editor prompt makes the objective explicit: build a useful, fast, trustworthy Bitcoin wire;
publish good work rather than demand unimpeachable proof; narrow/attribute uncertain claims;
and use `draft` when human review is the proportional answer. It may use all inspected receipts
together. It must resolve mechanical rails in any revised copy.

After the editor, code reruns only the hard mechanical shell. There is no post-editor source,
corroboration, semantic identity, freshness, numerical, scope, quote-attribution, or quote-style
veto beyond the mechanical unsupported-verbatim-quotation rail. That quotation rail runs both
before editorial review and against the editor's final revision.

The complete editor payload is capped at 256 KiB. Build it deterministically: preserve each
candidate's selected receipt and warnings first, deduplicate identical evidence bodies globally,
then trim nonselected evidence text to 2 KiB and old recent-feed copy. If a candidate still cannot
receive its selected evidence within the cap, exclude it from autonomous editor approval and
stage mechanically valid copy as a Typefully draft with `editor_payload_capacity`; never truncate
the selected receipt and then pretend the editor reviewed it.

## Implementation phases

### Phase 1 — Contracts and regression fixtures

- Split v2 lint into `hard_rails_v2()` and `editorial_warnings_v2()` while preserving the
  legacy v1 `check()` path.
- Add typed per-story validation notes and source/evidence advisory metadata.
- Encode the observed Pocket Bitcoin, Hargreaves Lansdown, Bitcoin $81K, and CLARITY Act failure
  shapes as model-free regression tests.

### Phase 2 — Evidence continuity and source acceptance

- Add/migrate `evidence_pool_json` and merge/load helpers with strict bounds.
- Rehydrate pooled evidence across attempts instead of reading only the latest attempt.
- Treat any safely fetched, nonempty public page as inspectable v2 evidence while retaining
  registry metadata and explicit discovery/aggregator warnings.
- Remove the deterministic elevated-claim source-count veto; create an editor warning instead.

### Phase 3 — Identity, editor authority, and observability

- Convert semantic key conflicts into non-mutating, forced-draft warnings.
- Initialize commits for every identifiable dossier story before shadow/materialization and
  persist validation, warnings, editor outcome, and delivery outcome.
- Pass mechanical rails and editorial warnings to the editor.
- Enforce only the mechanical shell after the editor and ensure editor outage remains
  Typefully-draft-only.
- Surface validation/search-degraded reasons in existing Desk/run diagnostics without adding a
  new dashboard subsystem.

### Phase 4 — Search circuit and documentation

- Add the per-session SerpAPI degradation circuit and counters.
- Update `SYSTEM.md`, `README.md`, and the handoff's current operational note.
- Keep `prompts/orientation-examples.md`, `RAW-POOL-LAST-2H.md`, and `audit/` uncommitted and
  otherwise untouched; they are owner/audit working files.

## Test plan

Focused tests must prove:

1. a later evidence-empty retry cannot hide an earlier valid Pocket Bitcoin-style first-party
   receipt;
2. unknown safe first-party pages reach the editor with warnings rather than failing conversion;
3. an elevated single-source story reaches the editor, which can publish, revise, draft, or drop;
4. a lower-tier/aggregator receipt is marked clearly without being a hidden veto;
5. identity conflicts do not mutate aliases and still reach the editor with warnings;
6. missing candidate/fetch IDs, duplicate membership, empty copy, unsafe URLs, and no inspected
   evidence still hold;
7. paraphrase/scope/source-tier warnings do not block an editor-approved post, while URL, length,
   unsupported verbatim quote, invalid mentions, and investment-instruction rails do; the quote
   rail is exercised before review and again against an editor revision;
8. every Sonnet story has a commit row and exact validation note even when held;
9. conflicting canonical families preserve every member key, register no alias, use a separate
   non-canonicalizing attempt/output key (including submitted-key collision cases), and can only
   create a Typefully draft;
10. omitted candidates defer; a valid candidate plus editor outage calls the publisher with
    `force_draft=True`; a mechanically invalid candidate plus editor outage never calls it;
11. the first SerpAPI 429 opens the session circuit and later search calls make no HTTP request;
12. editor-payload bounds preserve selected receipts, warnings, and deterministic degradation;
13. exact output/receipt dedupe, publisher uncertainty, lease loss, and kill-switch behavior are
    unchanged;
14. all existing intake, newsroom, report, Typefully, source-policy, and reconciliation tests
    remain green.

Schema-bound tests also prove over-limit decisions, stories, membership, or evidence produce a
run-level defer rather than silent slicing, and shadow commits terminate as `observed` rather than
remaining `pending`.

Run the full suite under Python 3.13 and a local mocked end-to-end v2 cycle.

## Deployment and production smoke

1. Confirm production health, one replica, attached `/data` volume, current variables, and
   autopublish state. Do not change the owner's autopublish setting.
2. Create and integrity-check an online SQLite backup.
3. Confirm the actual production autopublish setting immediately before rollout. If it is off,
   deploy with the current `v2/live` configuration. If it is on, stop for owner acknowledgement
   or use `NBN_RUN_NEWSROOM_MODE=draft` for the first natural run. The additive columns migrate
   on start.
4. Verify `/health`, `/status`, Desk rendering, schema, story-memory bounds, and Railway logs.
5. Observe one natural nonempty 15-minute Sonnet run. Confirm:
   - no run-level fallback;
   - each dossier story has a commit/validation record;
   - at least one persisted warning is visible and reaches the editor when naturally present;
   - any Typefully result matches the editor verdict and current autopublish setting;
   - a search 429, if encountered, opens the circuit rather than causing repeated calls.
6. Run a read-only production query proving the evidence-pool migration and bounds, complete
   commit lifecycle, and truthful costs/counters. Do not inject synthetic production news.
7. Leave the external audit running and use its next observations to tune editorial judgment,
   not to add new deterministic vetoes.

## Acceptance criteria

- A credible safely inspected story cannot disappear solely because its source domain was absent
  from the registry or its elevated claim had only one source.
- Good evidence survives later failed retries and is reusable within the 24-hour evidence window.
- The independent editor, not hidden code, decides source sufficiency, corroboration, semantic
  novelty, numerical materiality, and Bitcoin relevance.
- Mechanical safety/idempotency rails remain intact and visible.
- Every model-proposed story has a traceable terminal or pending materialization outcome.
- Production remains healthy and any generated content lands according to the existing Typefully
  gate.
