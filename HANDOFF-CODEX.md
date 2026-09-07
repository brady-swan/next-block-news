# Next Block News - current handoff

Updated 2026-09-07 for Plan 0063. Start here, then read SYSTEM.md and DOCUMENTATION.md.
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

The ordinary article adapter reads HTML/text, not PDFs. PDF MIME/signature detection returns
`unsupported_document` with no receipt or stored evidence, while preserving the final URL and
redirect trail. Native retrieval and other existing sources remain available. This is an honest
format limitation, not a publication gate or a newly added PDF-reading capability.

## Delivery

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
but broader editorial/model/source/research/cadence changes need approval. Audit evidence,
owner comments, rewrites, misses and peer speed comparisons remain part of the review.

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
