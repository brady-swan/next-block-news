# Next Block News - current handoff

Updated 2026-09-08 for Plan 0069 and its dense-packet follow-up. Start here, then read SYSTEM.md and DOCUMENTATION.md.
This replaces the accumulated launch-era handoff; its unmodified body is archived at
docs/history/HANDOFF-PRE-0060.md. Historical instructions there are not current authority.

## Product and state

NBN is an independent Bitcoin news wire on X at @nextblocknews_. It is not Swan-affiliated.
The objective is useful, timely, clear Bitcoin coverage, not a perfect-paperwork newsroom or
a generic macro statistics feed. Five to eight one-offs is an estimate, never a quota.
Scheduled Blocks are disabled; fresh EIC citations remain ordinary discovery inputs.

Production uses one Python 3.12 worker plus a threaded HTTP server on Railway, one replica,
and SQLite on the /data volume. Autopost was verified OFF for this release and must stay off.
Drafting, research and editing still run fully. Runtime values on Desk / System take priority
over dated descriptions.

Plan 0068 keeps this architecture and roster. It repairs event/storyline/output identity
handoffs within the existing shared correction budget; retains precise candidate retry failures;
simplifies text-only editor schemas while requiring actual visual decisions; and lets the editor
choose a reader source from exact supplied evidence. That final source follows delivery,
provenance, memory and subsequent confirmed image changes. Source history uses compact pointers
to retained evidence, never full article bodies in publisher mutations. Models get targeted
later-outcome/date/selection guidance and clearer existing image-tool affordances. See SYSTEM.md
and SPRINT-0068-FINDINGS.md. Nano Banana is parked by owner; GEMINI_API_KEY exists but is unused.
Do not implement or enable it until Brady explicitly reopens that proposal.

Plan 0069 is a separate packet-compaction repair, not a repeat of 0068. It moves prepared
receipt metadata/full capture behind existing context IDs under pressure, preserves candidate
control hints and all in-scope open-draft identities/ledes, and records section sizes on true
overflow. The initial 64 KiB and optional retrieval budgets are unchanged. Excerpts are honestly
fingerprinted and full retained receipts remain unchanged. See SPRINT-0069-FINDINGS.md.
The v2.27 follow-up removes remaining mechanical fail-open preparation repetition and empty
optional fields only at the final density tier. Real preparation, source evidence, controls
and every coverage key/lede are unchanged. See AUDIT-FIX-2026-09-08-DENSE-PACKET.md for the
distinct residual failure, reproduction, independent review and release status.
The audit's start-of-pass continuity check reconciles completed, deployed, local-only and paused
work before acting; old task summaries or repair notes are not fresh build instructions.

## Live roster

| Seat | Model | Effort |
| --- | --- | --- |
| RSS/EDGAR mailroom | claude-haiku-4-5 | default |
| Assignment preparation and relevant storyline selection | gpt-5.6-luna | low |
| Run-scoped newsroom / writing | grok-4.3 | medium |
| Native web/X research | same grok-4.3 writer context | medium |
| Independent batch editor | grok-4.5 | medium |

The legacy daily receipt audit is disabled (NBN_AUDIT_UTC empty); its retained path uses NBN_MODEL.
NBN_NEWSROOM_MODEL controls
the active writer; old HAIKU_* configuration/counter names are compatibility names, not
proof that Haiku performed a research or preparation call.

The worker sleeps 60 seconds after each cycle. A persisted 15-minute editorial deadline
controls normal nonempty desk sessions; priority, operator work and batch backlog can advance
the next session. Long model/network work can delay the single worker's next poll.

## Editorial and evidence boundaries

The loaded orientation is prompts/orientation-brief-v2.md (body after the separator).
PROMPTS.md lists every live and retained legacy prompt source. The tuning examples file is
a review record, not automatically injected memory. Do not revive obsolete hard freshness,
exact-number, semantic-key, forced-survey or single-receipt-completeness vetoes.

Guide accounts are strong attention signals, not factual authorities. The model researches,
selects, clusters and writes; a separate editor judges support, novelty, relevance and craft.
One credible inspected report can support a routine narrow claim. The registry labels source
capabilities, not a closed universe of permissible journalism. Inspectable unknown sources,
social statements and provider-reported extracts stay clearly labeled. Quotes need actual
verbatim support. Safe URLs, structural IDs, exact output idempotency, publisher constraints,
mentions, investment-instruction and kill-switch rails remain code-owned.

Continuity consists of exact-event keys/aliases, output state, 48-hour recent-reader coverage,
open drafts, a 30-day event workbench and incremental reporting artifacts with dated reusable evidence, and NBN-native
storylines. Node themes do not reach the live models. The Node is a separate API-only
supplemental discovery source; do not conflate its cluster keys with NBN coverage.

Plan 0063: native web/X now belongs to the writer, not a separate assignment. Six responses /
360 seconds, native allowance 12 across requests, shared tool budget 24; retrieval remains
four calls / 48 KiB. A complete paginated memory catalog and 72h-to-7d intake search expose
earlier originals and research. Current confirmed output outranks stale notebook delivery notes.
Writer self-reports are optional 14-day run observations shown in Desk; never feed them into
reporting memory or future models. They are one input for the owner, not verified diagnoses.

Plan 0064 keeps that architecture and budget. It adds a bounded optional per-story reporting
note for the editor/notebook (untrusted context, not evidence), preserves full source identity
in editor receipt deduplication, and makes event keys/confirmed copy visible in the memory index.
Text-only completion without native activity requests a dossier next, preserving one reference
repair and the same provider history. Explicit updates with resolved visible bases get mechanical
UPDATE-prefix repair before/after editing; all final rails and mutation protections remain.
The orientation clarifies consequential legislative timing/scope statements versus generic
advocacy. See PLAN-0064-REPORTING-FOLLOW-THROUGH.md and SPRINT-0064-FINDINGS.md for diagnostics
and release evidence; prompt quality still needs live observation.

Bounded metric-scope tuning (v2.20) reminds both writer and editor that all-digital-asset flow
totals are not Bitcoin-only totals. Preserve the source's scope, unit and period; correct the
wording rather than discard useful news. Practical rounding remains allowed. No new research
requirement or gate; see AUDIT-TUNING-2026-09-07-METRIC-SCOPE.md.

V2.21 clarifies the existing evidence handoff at the four dossier fields: a retained native
source or reporting note is not automatically a story citation. The writer lists relevant
sources for the editor separately from its reader-facing link. No auto-attachment or extra
turn; see AUDIT-TUNING-2026-09-07-EVIDENCE-HANDOFF.md.

Plan 0065 / v2.22 adds a bounded unassigned current-run research appendix to the editor; only
explicit valid refs attach its exact delivered excerpts to a story. Eight total receipts/story;
eight optional records, 2,000 characters each, 24 KiB appendix within the existing 256 KiB request.
It yields before baseline evidence/candidates. Invalid refs use existing omitted-only recovery;
unresolved fallback gets original copy and no additions. Clipping/native provenance and original
caveats survive final rails and memory. The reader-facing link and publishing safeguards do not
change. Read-time storyline cards/indexes add current exact-event editor/publication caveats
without rewriting old summaries or conflating intentions with approvals. Bitcoin Magazine body
selection and Mempool empty-shell handling are repaired. Orientation tuning emphasizes original
disclosure time, useful findings, and preserving valuable context during draft replacement.
See PLAN-0065-EVIDENCE-TO-READER.md and SPRINT-0065-FINDINGS.md. Natural behavior remains an audit
question, not something offline plumbing tests can establish.

Packet-pressure repair: optional full storyline cards become retrievable index entries before
an oversized compact desk is refused. The 64 KiB limit, candidate identity, source receipts,
owner overrides and lookup budgets are unchanged. See AUDIT-FIX-2026-09-07-DESK-COMPACTION.md.

The article adapter now reads text-based PDFs through local Poppler, detected by MIME/signature.
The first 20 pages, 10 MiB parser-input and 10-second/deadline bounds are separate from the
ordinary 8,000-character receipt allowance. Source URLs/redirects and explicit partial/text-only
limits survive into editor and next-session memory. No OCR, chart/layout verification or dates
inferred from file metadata. Unreadable PDFs remain empty failures; native retrieval and other
sources remain available. See AUDIT-IMPROVEMENT-2026-09-07-PDF-READING.md for release proof.

Article-body selection repair: explicitly marked HTML story bodies take precedence over long
navigation menus before the existing text and link caps. Unmarked/ambiguous pages keep the
whole-page fallback. Metadata and URL safety are unchanged. See
AUDIT-FIX-2026-09-07-ARTICLE-BODIES.md for the AP/Fox regression and release verification.

## Delivery

Coverage-card repair: one canonical event can have published copy plus a later open draft.
Its reader-covered card and open-draft card now receive separately bounded ledes from their
respective lifecycle modes, not the same combined latest-copy list. No identity, uncertain-
delivery reservation, publication or replacement rule changed. See
AUDIT-FIX-2026-09-07-COVERAGE-COPY.md.

New one-offs are a clean lead plus immediate first reply, "Source: <receipt URL>".
Typefully is the production rail. Scheduling, publication and read-back confirmation are
different states. Durable mutation intents prevent blind retries of ambiguous writes.
Same-event work can replace only a sole untouched, comment-free draft when enabled; a
scheduled/publishing/published event blocks duplicate creation. A genuine material update
may justify a separate UPDATE. Legacy gate/stage actions force draft-only; a skip override
requests normal reconsideration, not forced publication or forced draft-only.

Never enable autopost, mutate Typefully content, resolve ambiguous remote state, rotate
credentials or do destructive database work without specific authority. Corrections are
human-reviewed. AUDIT-AUTONOMY.md preserves the limited emergency authority to turn autopost
OFF for evidenced systemic publishing problems, never back on.

## Desk and monitoring

- /desk?k=<token>: latest run, Previous/Next history, input/research/copy and adaptive inspector.
- /desk/intake: current status and decisions for a selected first-seen day.
- /desk/runs: saved run checkpoints, candidate decisions, editor/delivery reasons.
- /desk/outputs: locally tracked copy, receipts, observed timing and publisher state.
- /desk/system: current roster/effort, stage/period costs and averages, source/search health and PDF.
- /report?k=<token>: existing guarded owner actions, background promotion and orientation.
- /health and /status: worker status; completed-cycle staleness threshold is ten minutes.

Every Desk child route requires the report token. Snapshots are read-only, use no provider
calls, and refresh every 15 seconds in visible tabs. Checkpoint timestamps are not a token
stream or an exact live-stage monitor. Local output records are not the entire Typefully
account. Marked replays are excluded; isolated replay exports generally never entered the DB.
See DESK-GUIDE.md for clock and metric definitions.

The in-worker daily receipt audit is disabled by owner decision September 6; historical results
remain. The separate Codex rolling audit continues after the build pause.
The latter may repair technical regressions and tune execution of the approved writing style,
and, under the September 7 owner expansion, proactively ship obvious bounded improvements
within the existing design, including useful reporting tools such as PDF-text reading. A new
capability is not automatically a systemic change. Track rationale, tests, cost/behavior impact,
deployment/smoke and rollback; keep autopost OFF. Systemic design, editorial-policy, model,
cadence, significant recurring-spend and vendor changes need review. Audit evidence, owner
comments, rewrites, misses and peer speed comparisons remain part of the review. Read
AUDIT-AUTONOMY.md for the exact scope and the PDF improvement record for implemented limits.

Plan 0061 adds bounded safe run observations and source-health recording. Exact writer packets
are saved after shaping; research and true editor returns retain provenance. Missing/pruned history
and costs are not zero. Delivery-now has its own clock. All GETs are read-only, including Review.
Build `desk_ui` before committing its static assets; no Node server runs in production. No newsroom
model, prompt, cadence or publishing rule changed. See DESK-GUIDE.md and Plan 0061 release evidence.

Owner follow-up: Intake **Send to newsdesk** queues skipped-lead reconsideration. The worker
activates it under its cycle lease at the next inventory boundary; it waits for the normal
desk slot. `_owner_reconsider` survives prep Background filtering and both writer packet shapes,
with Brady attribution, prior skip reason, request time and a reminder this is not publication
approval. Keep it separate from legacy operator gates/action IDs. Consume only after a valid
writer protocol response, not transport success. Repeated POSTs check the latest action id;
state changes to held/drafted/delivered are blocked, never rewound. No schema or provider call
was added to the dashboard action.

## Post visuals (0066)

The reporter-writer now has optional bounded still-image/PDF-page inspection and five exact
Pillow templates, without a new seat or quota. `visual_tools`, `visuals` and `visual_render`
own discovery/tools, immutable assets/evidence and deterministic rendering. Both writer and
editor see identical stored pixels; current prompt v2.24 includes visual guidance in its hash.
`x_payload` defines full ordered text/media/alt/credit identity. `publisher_visuals` persists
preparation inside the existing mutation lifecycle (`awaiting_media`), resumes uploads without
models and never repeats an uncertain draft mutation. Text-only revisions of formerly imaged
drafts retain the versioned identity. `visual_choices` queues fenced Desk actions for worker
editor review. All owner visual actions stage drafts. Autopost remains OFF.

Keep `/data/visual-assets` with SQLite backups/restores; do not delete files just because the
14-day observations or 30-day notebook expired. The 512 MiB soft cap declines new optional
assets; there is no automatic pruning. Media-level alt + acknowledged Typefully draft version
is the supported confirmation contract; draft-local alt is absent from draft GET and alt-only
UI version behavior has not been empirically proved. Lost/mismatched identity stays unresolved.
See SYSTEM.md for exact bounds and SPRINT-0066-FINDINGS.md for release proof/limitations.

## Release playbook

1. Read current docs and git status; preserve uncommitted owner/evaluation work.
2. Plan the smallest justified change, seek independent lead-coder review when requested,
   resolve concrete blockers, implement and test. Avoid an overbuilding loop.
3. Run the offline suite on Python 3.12 and again from a clean archive of the intended commit.
   Tests block sockets and use temporary storage. Never run run_once against production to smoke.
4. Confirm Railway target, one replica, /data, current kill switch; create an online SQLite
   backup with scripts/backup_db.py. Do not print credentials or authenticated report URLs.
5. Deploy the clean archive explicitly to the existing Railway project/service/environment.
   A Git push alone is not a deployment. Check the deployment status, HTTP health, relevant
   authenticated endpoints, and a natural worker cycle. Roll back code on regression.
6. Restore the existing rolling audit if paused; keep its autonomy/notification boundaries.
   Do not create a duplicate monitor.

Railway project: 1e1f32d1-6153-4f71-80b3-9543050caa7e.
Service: ff9549a3-6f78-481a-a550-d8c10136af64 (next-block-news).
Production environment: 90c43f68-970a-4f93-a392-414c3c175502.
Public base: https://next-block-news-production.up.railway.app.
Database: /data/nbn.db; tapes: /data/tapes; backups: /data/backups.

## Latest release evidence and unresolved work

Current runtime **684fd39 / editorial-core-v2.27-dense-fallbacks** is live on Railway
**ac251388-dd31-4dd9-aeb9-da3b20eaa134** (SUCCESS). 583 clean-release tests, seven file
hashes, health and four authenticated workspace views passed. A natural 25-candidate
run completed with a 63,856-byte packet and all20 open-draft cards preserved. Its writer
finished; the editor separately timed out and used the existing fallback, which the
audit must inspect rather than count as editor approval. Autopost OFF; same15-minute
audit ACTIVE. The full editorial cutoff remains11:15:56.744 UTC for backfill. See
AUDIT-FIX-2026-09-08-DENSE-PACKET.md. Plans0068/0069 and this follow-up are complete;
do not restart them from stale action notes or a carried-forward summary.

Earlier Plan 0068 runtime **58baaf6** shipped on Railway deployment
**73773e75-534b-4e2a-8261-5942fa170478** (SUCCESS). 575 clean-release tests, compiled-asset parity,
12 live runtime hashes, authenticated Desk views and natural worker cycles passed. Autopost OFF;
same audit ACTIVE. Full release verification is recorded in SPRINT-0068-FINDINGS.md. Its full editorial audit
checkpoint is 2026-09-08T11:15:56.744Z; build/smoke observations do not advance that cutoff.
The same monitor must backfill the build interval when resumed. Organic visual adoption and
editorial quality remain observation questions, not conclusions from a deliberate tool replay.

The following Plan 0066/0065 evidence and audit checkpoints are historical, not current status.

Plan 0066 shipped as `0232620`, Railway deployment `2c7fb9d9-46d9-4e2e-a1dd-837b7447dcec`
SUCCESS. 564 clean-release tests passed (566 with owner evaluator work), clean static build
matched, health/Desk/schema/runtime hashes passed, and a natural intake cycle completed.
Isolated unpublished transport draft 10673284 confirmed exact image + alt + first-reply receipt;
its journal/tapes are outside production editorial tables. Do not publish it or treat it as news.
The existing audit is ACTIVE with image quality/cost/delivery watches and build-window backfill
after 2026-09-08T00:47:12.894Z. First natural image-bearing editorial delivery remains unverified;
see SPRINT-0066-FINDINGS.md. Autopost is OFF. The older release evidence below is historical.

Plan 0065 shipped as `02c864d`, Railway deployment `d8e6c4bf-b951-4103-b60a-345746823fc2`
(SUCCESS). Working-tree suite: 536 tests; clean release: 534. Seven runtime/prompt hashes,
Desk/health/API access, read-only production memory projections and a normal intake cycle
verified. Autopost OFF; model roster/budgets/cadence unchanged. The original rolling audit is
ACTIVE with Plan 0065 watches and its full-audit cutoff preserved for backfill. The first full
natural v2.22 run then completed: three editor decisions, one existing Liquid draft replacement,
two drops, $0.2817707 tracked spend. Appendix delivered, zero additions selected. The editor
restored useful outcome context, but stale ETF selection and an unrelated Stacks receipt remain
observed writing issues. Do not infer broad improvement from one run. See SPRINT-0065-FINDINGS.md.

Plan 0064 shipped reporting follow-through as `c5c9096`; production smoke exercised the real
writer/editor handoff and exposed an older intake-variable shadowing bug after successful draft
replacement. Independently reviewed repair `c7887fd` preserves the intake list for decision
recording, with no change to publishing rules. Clean-release suite: 504 tests; working tree: 506
(two unrelated evaluation tests excluded from release). Runtime deployment is
`642a327c-c793-4d14-8b04-a1e7c489a06e` (SUCCESS). See SPRINT-0064-FINDINGS.md for verification,
the $0.14338 natural Liquid run, remaining guide-link/source-date weaknesses and audit state.
No manual Typefully mutation was made; the ordinary worker updated existing Liquid draft 10663389.

Plan 0058 adopted the measured multiprovider roster. Its replay follow-up fixed Responses
tool submission and preparation-schema bounds. Plan 0059 shipped craft examples and new-run
Background provenance preservation; nine historical replay tests did NOT validate automatic
native-research selection, and the experimental routing prompts did not ship.
Read SPRINT-0059-FINDINGS.md and ROSTER-REPLAY-FINDINGS-2026-09-05.md for limits and costs.

Plan 0060 adds observability/docs/PDF, not editorial policy or model changes. Its release
record tracks tests, deployment, natural-cycle smoke, and audit restoration.

Plan 0060 shipped runtime `2d9dcad` in Railway deployment
`5996010b-e732-47ae-98e6-ef138696d7a3` (SUCCESS). Clean suite: 422 tests; 42 production HTTP
checks and a natural cycle passed. Eight-page PDF visually checked. Autopost OFF; existing
15-minute rolling audit ACTIVE with unchanged authority plus observability checks.

Subsequent audit repair `c581510` corrected @BitcoinNewsCom's source identity to Bitcoin News,
separate from Bitcoin.com News, without changing tiers, prompts or discovery. Deployment
`7e3b8a34-b3e8-492e-ad60-adb1f207ad22` succeeded; 425 clean-release tests and production smoke
passed. Existing Typefully copy was not edited. See AUDIT-FIX-2026-09-06-SOURCE-IDENTITY.md.

Audit repair `4ba3f3d` closes two missing pre-editor story-state writes: update/base and
update-label deferrals now record held with the exact reason instead of leaving pending after
run completion. No editorial, retry or publishing behavior changed. Deployment
`995a195e-9ae9-4458-8ef3-6d2096791b18` succeeded; 426 clean-release tests, authenticated
route checks and natural worker cycles passed. Historical rows were not rewritten. See
AUDIT-FIX-2026-09-06-PRE-EDITOR-LIFECYCLE.md. Plan 0061 and its owner skip-override follow-up
subsequently shipped as recorded in PLAN-0061-NEWSROOM-WORKSPACE.md.

Plan 0062's contract: bounded richer X material survives pending/retry inventory; pagination
acknowledgments happen only after upsert commits; unfinished windows resume next poll. Guide
source/media context is still discovery, not evidence. Bitcoin Core, Optech and BTCPay feeds
are a measured upstream pilot with explicit first-snapshot archive skips. No standalone
software-release beat, model/cadence change or Perception work. Owner-approved retrieval caps
are four calls / 48 KiB total, 16 KiB per call and 64 KiB initial. See its release record for
deployment and smoke status. Autopost remains OFF; restore the separate rolling audit after smoke.
