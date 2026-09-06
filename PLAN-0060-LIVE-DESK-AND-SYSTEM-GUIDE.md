# Plan 0060 - Live Desk and system guide

Status: shipped and smoke-tested on 2026-09-06. Independent plan/code reviews approved; rolling audit ACTIVE.

Review refinements: SQLite `mode=ro` (never migration-bearing `store.connect()`); count
confirmed publications separately from sent outputs; bound daily costs by both timestamps;
label newsroom records as dated checkpoints. Typefully scope is locally tracked outputs,
not every draft in the remote account. No new event engine needed.

## Outcome and boundaries

Make NBN understandable and observable without changing its editorial behavior. Keep the
existing Python worker, SQLite database, Railway deployment, source policy, model roster,
cadence, and Typefully lifecycle. Autopost remains off. Pause the rolling Codex audit while
building and restore it after deployment and smoke tests. No test publishes or edits content.

## 1. Live Desk, not a second application stack

- Extend the existing authenticated HTTP server with `/desk` and focused views for intake,
  newsroom runs/decisions, outputs, and system/costs. Retain `/report` and every existing
  review action/deep link; make Review accessible in the new navigation.
- Provide a bounded, read-only snapshot endpoint using the same report token. Poll every
  15 seconds while the page is visible, with manual refresh/pause, last-success time,
  connection failure and stale-worker states. This is observed production state, not
  simulated progress. In-flight runs are labeled as such, not inferred model thought.
- Show current worker state, next desk deadline, pending work, latest run, recent intake,
  recorded decisions, publisher states, and known model spend. Distinguish discovered items,
  model calls, event/story decisions, Typefully drafts and confirmed publication; exclude
  marked evaluation/replay outputs from normal feed performance.
- Use bounded server-side filters/pagination and drill-downs for a selected run. Never send
  raw dossiers, credentials, research bodies, mutation ownership tokens, or complete database
  rows to the browser. Project explicit fields, escape content, validate external URL schemes,
  authenticate every Desk route, and send no-store/no-referrer headers.
- Preserve the dark/orange Desk identity with readable type, compact navigation, short cards,
  responsive tables and plain language. No new frontend framework or external asset services.
- Use existing persistence first. Add only narrowly scoped telemetry if a necessary live
  status cannot be represented honestly from the existing tables. Polling must not call
  models, sources or Typefully, run migrations, or take write locks.

## 2. Documentation refresh

- Inventory every tracked operational/system description, including root docs, prompt index,
  config examples, script/eval docs and relevant module descriptions.
- Establish an explicit current-document index and update README, SYSTEM, HANDOFF, PROMPTS,
  inbound flow, operating/correction/audit guidance and roadmap against code and selected
  non-secret production settings.
- Preserve historical plans, experiments, cost analyses and tuning records. Mark their scope
  and link to current documentation instead of rewriting historical results as current truth.
  Preserve pre-existing uncommitted work. Do not alter runtime editorial prompts in this sprint.
- Document the exact live roster, source/poll clocks, mailroom/prep distinctions, research
  evidence types, exact-event and storyline memory, editor/Typefully lifecycle, kill switch,
  legacy/disabled paths, costs, and the Desk's refresh/metric limitations.

## 3. Visual system guide

- Produce a concise vector PDF in `output/pdf/` with a source/cadence map, model-seat flow,
  example event journey, evidence and continuity layers, publishing/owner controls, and a
  guide to reading the Desk. Label the production snapshot date and distinguish configured
  behavior from guarantees. Explain SHA-256 as a fingerprint, not encryption.
- Use the PDF skill's authoring marker, ReportLab and page-by-page rendered visual QA.
  Provide the guide in the repository and through one fixed authenticated download route.

## 4. Review, verification and release

- Independent lead coder reviews this plan before implementation; resolve concrete concerns.
- Test all authentication boundaries, read-only snapshots, filtering/bounds, escaping/unsafe
  URLs, run detail projection, empty/error/stale states, counts, replay exclusions, and legacy
  report/actions compatibility. Verify browser script syntax and HTTP payloads. Run the full
  offline suite and a clean-release suite; PDF text and visual checks are separate.
- Seek a focused independent implementation review, fix actual defects without expanding scope.
- Commit only this sprint's changes, back up production SQLite, deploy a clean git archive,
  confirm health and new authenticated pages/snapshots/PDF, and observe a natural cycle.
  No forced editorial run or Typefully test write. Roll back code if a regression appears.
- Restore the existing audit as ACTIVE, retaining all established autonomy boundaries and
  adding checks for stale Desk telemetry, metric mismatches and the new observability views.

## Acceptance

The owner can see what NBN has received, what the newsroom decided, what reached Typefully,
what actually published, and whether the worker is healthy, without treating missing telemetry
as zero or a draft as a post. Current docs and the PDF agree with the deployed implementation.
The old review links/actions still work, autopost is off, and the rolling audit is active again.

## Implementation and verification record

- Implemented five read-only views, fixed authenticated assets/PDF route, visible-tab snapshot
  polling, server-rendered no-JavaScript fallback, filters, pagination and run/item drill-down.
- Added no dependency, database migration, event engine, provider call or editorial prompt-body
  change. Existing Review actions stay on `/report`; its selected-day cost sum now has an end bound.
- Independent code review found one carryover-item date-link defect; fixed using each item's
  first-seen Central date. Reviewer approved the final change; the cross-midnight regression passes.
- 13 focused Desk tests; 424 working-tree tests passed on Python 3.12. This working tree includes
  two pre-existing evaluator tests not part of the clean release. JavaScript syntax and diff checks pass.
- Eight-page vector PDF built and every rendered page inspected at 1400px. No clipping/overlap;
  extracted text checked on all eight pages. Build dependency remains outside worker requirements.
- Current docs rewritten/aligned; contradictory old handoff, roadmap and inbound descriptions
  preserved in labeled history. Evaluation results and plans retain dated findings and new status
  pointers. Unrelated evaluator code and tuning work are preserved outside this release.

## Production release

- Runtime commit: `2d9dcad` (pushed to main). Clean archive deployed explicitly to the existing
  Railway project/service/production environment; unrelated dirty evaluator/tuning files excluded.
- Railway deployment: `5996010b-e732-47ae-98e6-ef138696d7a3`, SUCCESS; one replica, `/data` retained.
- Online backup: `/data/backups/nbn-pre-source-policy-20260906T060258Z.db`.
- Clean-release Python 3.12 suite: **422 passed**. Working-tree suite: **424 passed** (two
  existing unreleased evaluator cases). The dependency-free JS controller tests passed for
  pause/resume, hidden tabs, stale-error retention, date/run preservation, disclosure state
  and reading-focus behavior. No browser screenshot test was performed; HTTP/controller
  verification and the PDF's separate rendered visual review are the documented checks.
- **42 production HTTP checks passed**, split across localhost/container and public HTTPS:
  health; unauthenticated pages/assets/PDF refused; authenticated unknown route 404; five
  views and historical snapshots; static assets; legacy report/backlink; PDF exact-byte readback;
  filtered intake and actual latest-run detail. New views took 4-95 ms inside the container in
  this smoke, including first import, with ordinary public snapshots 12-28 ms from the container.
  These samples are not an uptime or latency guarantee.
- Natural post-deploy cycle completed: process started `1788674630.706077`, successful cycle
  `1788674637.3118486`, no worker error. SQLite quick_check: `ok`. No forced editorial run,
  provider research probe, Typefully write, publication or content dismissal was used as a test.
- Autopost remained **false** before and after deploy. Prompt remains
  `editorial-core-v2.15.2-craft`; model roster, cadence, editorial prompt bodies and dependencies unchanged.
- PDF: eight pages, 21,313 bytes; SHA-256
  `4bca260f0c54c7f01d7a323d52c6c08d85cbaf6c10561ab28b4d3b8a144f5865`.
- Existing `audit-nbn-production` heartbeat restored **ACTIVE**, every 15 minutes, same task.
  Added Desk freshness/metric-scope checks and the cost-ledger caveat; preserved all autonomy,
  writing-quality, misses, peer-speed, replay-exclusion and meaningful-notification boundaries.

The new site is reached through **Live Desk** at the top of the existing authenticated report.
The existing review URL and tools remain supported. Current-document entry point: DOCUMENTATION.md.
