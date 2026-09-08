# Sprint 0065 — evidence to reader

September 7, 2026. Owner-approved afternoon follow-through. Independent plan and implementation
reviews approved; clean release deployed and smoke-tested. Existing audit restored.

## What the afternoon taught us

Reporting was sometimes better than the final handoff. OpenSats' original blog had already been
read, but only its X receipt reached the editor; the useful separate-operating-budget explanation
was removed. More research would not fix evidence that was already available but omitted.

The other failures were distinct:

- Bitcoin Magazine's div-based menu consumed text/link capacity before the article's transaction
  and researcher links. Its `.td-post-content` body needed recognition.
- A Mempool title-only page was recorded as successful material. The writer did not cite it,
  but the adapter should report an empty dynamic shell honestly.
- Writer-authored inflation storyline context survived an editor drop. Exact notebooks retained
  the editor verdict, but broader summaries lacked the nearby caveat. No harmful later publication
  from this inconsistency was demonstrated.
- Liquid replacements worked technically but traded useful pause/peg-in context for forensic
  detail. A newer source was not necessarily an improved reader post.
- Galaxy's useful early-mining finding became an overloaded inventory; a block-count denominator
  was used for qualifying output counts. This was population mismatch, not harmless rounding.
- Owner feedback corrects earlier provisional audit positives: Lam was September 4 news, and
  AnchorWatch added little beyond its quoted tweet. Guide-to-draft speed is not event freshness.

For context, the completed afternoon audit through 23:26:34.834 UTC counted $1.79361935 in models:
prep $0.03552895, intake $0.044393, writer $1.3147554, editor $0.398942; no unknown-cost calls.
The 22 completed runs included prep-only runs, not 22 full writer sessions. Four new drafts and
four replacements of the same Liquid draft did not mean eight useful new stories.

## Shipped design

The writer still owns reporting, story selection and copy. Its explicit story receipts remain
the primary editor input. A separately labeled optional appendix exposes completed current-run
research it omitted: up to eight receipts, 2,000 characters each, 24 KiB total inside the existing
256 KiB editor request. Baseline candidates/evidence/feed fit first. Restored historical receipts
are excluded. The editor may explicitly select relevant refs, with eight total receipts per story.
Unrelated material is never automatically attached.

Only the exact excerpt delivered to that editor request enters the story's final support context
and notebook. Its own fingerprint, original fingerprint, clipping flag and unchanged source caveats
are retained. Native extracts do not become direct captures. The reader-facing URL is unchanged.
Malformed ref lists reject that decision atomically into existing omitted-only recovery; unresolved
fallback retains original copy with no additions. No new research call or mandatory turn was added.

Read-time storyline projections now distinguish writer intention, current exact-event editor
state and actual publisher confirmation. Compact caveats survive prep/index/catalog views. They
may postdate the original run, and missing/expired notebook state stays unknown. Old summary prose
and revisions are not rewritten. Confirmed reader coverage survives a newer open draft.

Article extraction recognizes the Bitcoin Magazine body and narrowly rejects the observed Mempool
shell. V2.22 orientation/writer/editor guidance reinforces original disclosure time, useful reader
takeaways, statistic population/scope, and preserving still-current qualifications in replacements.
No new semantic gate, quota, model, cadence, research allowance, source policy or publication rule.

## Independent review and tests

Plan review established baseline-first capacity, exact-excerpt support, atomic ref validation,
current-run-only additions and current-not-historical outcome labels. Implementation review caught
three issues that were corrected before release:

1. A malformed verdict must not throw away valid sibling decisions.
2. Excerpt clipping must not truncate the source's original limitations.
3. Actual request serialization must match compact UTF-8 byte accounting.

New full materialization tests also caught a missing local import before deployment. Fifteen new
tests exercise optional/invalid refs, partial recovery, capacity/Unicode, exact excerpt quotation
boundaries, original-copy fallback, native rehydration, memory reads/aliases, Mempool shells and
ambiguous/blank Bitcoin Magazine bodies. Existing extraction fixtures now include its body marker.

- Working-tree offline suite: **536 tests passed**, Python 3.12, 16.765 seconds.
- Clean archive offline suite: **534 tests passed**, Python 3.12, 16.297 seconds.
- Two unrelated dirty evaluator tests are intentionally excluded from the clean release.
- Independent implementation review: **approved**, no remaining concrete blockers.
- No live model replay, forced worker run, manual Typefully edit/dismissal or publication was used
  to test the release. Provider/publisher calls in regression tests are mocked and sockets blocked.

## Release and observation

- Runtime commit: `02c864d`, pushed to `origin/main` and deployed from its clean archive.
- Railway deployment: `d8e6c4bf-b951-4103-b60a-345746823fc2`, **SUCCESS**.
- Existing production project/service/environment verified; one replica, persistent `/data`.
- Online SQLite backup: `/data/backups/nbn-pre-source-policy-20260908T002030Z.db`, integrity OK.
- Read-only smoke at 2026-09-08 00:24:33 UTC / September 7 7:24 PM Central: health, status, Desk,
  Intake, Outputs, System and Review returned 200; all four workspace API views returned valid 200
  JSON; unauthenticated API access returned 403. Public Railway health also returned 200.
- SHA-256 comparison matched all seven changed runtime/prompt files. Production DB quick check OK.
- Real read-only memory projections succeeded: five storyline index entries, four full cards,
  seven compact caveats and a 40-entry catalog page, without writes.
- The first normal intake cycle completed under v2.22 with no worker error. It was waiting for
  the persisted editorial deadline; this initial smoke did not claim a completed new-model run.
- Roster, six responses / 360 seconds, 24 shared tool calls, 15-minute cadence and four retrieval
  calls / 48 KiB total confirmed unchanged. Autopost confirmed **OFF**.
- Existing `audit-nbn-production` heartbeat restored **ACTIVE**, every 15 minutes. New outcome
  watches added; standing authority unchanged. Full-audit cutoff **2026-09-07T23:26:34.834Z**
  preserved so the build window is backfilled rather than silently skipped.

The archive contains the release plan/findings as they stood before deployment; this final
release-proof update is a documentation-only follow-up, not another worker restart.

### First full natural run

`cycle:1788827076:cc52c9a1` completed at 2026-09-08 00:27:43 UTC / 7:27 PM Central without a
worker error. Preparation advanced eight of 18 inputs. The writer used four responses; the batch
editor returned three valid decisions in one call, accepting the new refs contract without recovery.
The actual editor request included three optional unassigned receipts; it selected **zero** additions.
This proves the live appendix/schema path works, not that omitted evidence has yet been rescued.

- Liquid: the editor explicitly identified lost return/outcome context and restored it in its
  revision. Normal worker delivery recorded replacement of existing draft **10663389**, not a
  new draft or publication. This is encouraging for the replacement guidance, not proof that all
  useful warnings or details were optimally preserved.
- ETF: the writer still proposed September 4 daily flow totals. The editor dropped them as routine
  and already contextualized. Freshness/selection is still a live tuning issue.
- Stacks/Xverse: the writer proposed a product launch with an unrelated selected Fidelity receipt;
  the editor dropped it for scope and sourcing. The proposed blanket self-custody wording also
  deserves review rather than being accepted as an established fact. Handoff discipline is not fixed
  merely because the optional appendix exists.

Tracked run spend: preparation **$0.0057745**, writer **$0.213675**, editor **$0.0623212**, total
**$0.2817707**. This is one run, not a daily forecast or an isolated measure of appendix overhead.
The audit will continue evaluating natural choices, misses, freshness, writing and source quality.

Watch natural runs for actual appendix selection, preserved reader context, honest event timing,
and current outcome caveats. Static tests prove the handoff mechanics, not that future copy is
better. Optional editor input can increase cost; no extra provider calls were introduced. Measure
actual usage when exercised. The image sprint and Perception work remain deferred.

Rollback: redeploy prior verified runtime `01966fb` (deployment
`c2f16b3e-68fc-42bf-b24a-a7332377d8c3`), retaining production data and autopost OFF.
