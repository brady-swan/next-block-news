# The run-first Desk

Current 2026-09-09, Plan 0071. The Desk is part of the existing NBN Railway service, not a separate app
or public news site. All /desk routes, assets, snapshots and the PDF require the existing
NBN_REPORT_TOKEN. Do not share authenticated links or put them in public documentation.

## Views

| View | Use it for |
| --- | --- |
| Newsroom (/desk) | Latest run; page older/newer across dates, inspect input, research, decisions and copy |
| Intake (/desk/intake) | First-seen-day pool; inspect decisions and request reconsideration of skipped leads |
| Newsroom (/desk/runs or /desk/live) | Compatible entry points for the same run-first workspace |
| Outputs (/desk/outputs) | Locally tracked copy, receipt, observed timing, Typefully link, confirmation and weak engagement context |
| System & costs (/desk/system) | Current roster/effort, spend and averages by stage/run/period, source/search health and PDF |
| Review tools (/report) | Existing guarded Stage draft, Dismiss, Send to desk, mutation-resolution controls and loaded orientation |

Viewing or refreshing does not change editorial settings or call a model, source API or Typefully.
Navigating to an external source/Typefully opens that site normally. Review retains the existing
guarded actions. Intake adds one explicit owner action: **Send to newsdesk** on skipped leads.

This overrides the skip for reconsideration on the next scheduled newsdesk run, not publication.
The writer receives a labeled Brady override, original skip reason and request time, with actual
source/event dates preserved. Mailroom/preparation cannot discard the request before the writer
sees it; normal writer/editor, duplicate and delivery checks still apply. It does not accelerate
the 15-minute cadence or enable autopost. Queued requests survive restarts and pre-handoff failures.
“Delivered to the writer” means a valid writer response, not editorial acceptance. If another run
has already moved the item to held/drafted/delivered, the request is blocked rather than rewinding it.
The page shows queued/delivered/blocked status; a newly skipped item can be reconsidered again
only with a fresh explicit request. Repeat clicks or delayed retries do not create duplicate intent.

## What “live” means

The browser reads versioned same-origin JSON every 15 seconds while visible. Pause/resume is
explicit; selected text and focused inputs are not replaced on automatic refresh. The default
follows the latest production run. Previous/Next and the timestamp picker pin a historical run;
new arrivals do not move it. Back to latest resumes following. Browser URLs/Back/Forward retain
run, story and tab. Intake/output day filters are independent of cross-midnight run paging.

The connection line gives the last successful snapshot time. A failed request keeps the
previous content with an error/retry notice. Without JavaScript, use server-rendered Review tools.
The worker banner is separate: starting, healthy, error or stale (no current-process completed
cycle for ten minutes). An old persisted success is displayed, not confused with this process.

Newsroom statuses are **last recorded checkpoints** (surveying, researching, validated,
materializing, completed, deferred or fallback), not exact live stages. A stopped worker's
old researching checkpoint is not proof of ongoing research. Model calls appear after they
start and return; the Desk does not stream hidden reasoning or tokens. New source-health records
come from existing ordinary polls, not extra probes. Successful zero results are healthy; failures
retain last-success time; throttle skips do not replace observations. Not observed is not failure.

## Run workspace and research review

Decisions group source leads into stories. Delivered desk shows the actual safe writer packet,
including coverage, recent reader feed, continuity and selected storyline context. Background
is separate and not sent. Without a retained packet, preparation is an advanced estimate, not
proof the writer received it. Missing/pruned dossiers and editor returns display as unavailable,
not zero work. Intake polls or skipped cadence windows are not fabricated as newsroom runs.

Research displays assignments, prepared source captures, tool returns and reporter findings.
The combined reporter-writer uses native web/X in its own session. Research shows observed
source URLs, returned source-specific extracts and native call counts; zero delegated assignments
does not mean no research. Delivered desk includes the memory catalog with explicit pagination.
Provider-reported extracts are source-specific paraphrases, not verbatim page text. Evidence IDs
establish recorded use, not how much a finding influenced judgment. Human quality questions
guide review without an invented score. Unassigned research remains visible at run level.
Perception coverage/regulatory/article requests use that same Research view. Search rows are
pointers; provider-captured article text has its own provenance and may be partial. System's
Perception section shows UTC-day local REST/MCP attempts, new-work allowance, cache/article
reuse, provider observations, survey state and partial/backlogged feed progress. These are not
account-wide remaining quotas; Node may be consuming the same subscription elsewhere.
Copy compares writer proposals with actual editor-returned or submitted copy. Omitted/unavailable
editor fallbacks are not editor rewrites. Activity shows actual timestamped handoffs.

Copy and the story inspector explicitly label unavailable/omitted editor fallbacks **Needs human
review — editor response failed**. This means the desk's copy may have been staged for Brady;
it is not approved editor copy. The Reader source link shows the editor-selected inspected
receipt, defaulting to the writer's receipt. Current confirmed delivery context takes precedence
after later visual changes; proposed or uncertain source changes are not displayed as accepted.
Historical writer receipt choice remains distinguishable from the final submitted source.

**Writer feedback** is an optional end-of-task self-report: what helped, what hindered, and
one suggested improvement, with references when provided. Open it on a run or browse the
paginated recent-feedback panel in System. It is one unverified input for human discussion,
not a score, verified diagnosis, policy change, or instruction to another model. No feedback,
missing feedback and expired observations have distinct labels. It is retained with rich run
observations for 14 days and excluded from the editor, future writer packets and memory tools.

At 1440+ CSS px the inspector is a persistent side pane; intermediate widths use a drawer,
mobile uses full-width detail. Selection and reading position survive resizing. Escape/close
returns focus. Extra-wide monitors use the space for comparison/context, not unbounded prose.
Post cards retain all-side padding. Review tools preserve guarded actions and old anchors while
collapsing the earlier diagnostic wall.

### Visuals

Each story's **Visuals** tab shows exact stored image previews, alternatives, alt text,
source/credit, reuse status, recipe, editor decision and delivery state. Proposed/approved,
omitted, held and text-only fallback are distinct; an omitted image is not labeled selected.
Click an image for its full-size authenticated asset. Unknown rights are review-only.

**Select for review**, **Use text only**, and **Review square/landscape version** queue a
versioned request. The leased worker gets fresh independent-editor approval, rechecks current
output and owner edits, then uses the normal delivery lifecycle. HTTP clicks do not call models
or immediately PATCH Typefully; refreshes never enqueue work. Published/ambiguous outputs and
pending delivery cannot be overwritten. A request is not guaranteed editorial approval.
Regeneration changes only the fixed layout preset and creates another immutable asset from
retained evidence; it is not an arbitrary image editor. Missing old review context directs the
lead back through the newsdesk rather than inventing it. All actions stage drafts, never enable
autopost. The upload may remain processing between worker cycles, or require owner review if
the exact remote attachment/version cannot be confirmed.

## Count and timestamp definitions

- First seen: unique intake rows first persisted during the selected America/Chicago day.
  Not raw fetched results, events, stories or outputs. The item's status is its current state.
- Waiting for desk: all currently new rows, across all dates. Some may be deferred or too old
  for the next candidate window; this is not a promise all will run next.
- Outputs recorded: local posts rows created that day, across modes. It is not a sum of
  published posts and intake decisions; one event can have many source items.
- Confirmed published: locally tracked rows with publisher_status=published and a non-null
  confirmed_at inside the selected day. IMMEDIATE alone is insufficient. A manually published
  draft is counted on its confirmed publication day once reconciliation sees it.
- Output view includes records created **or confirmed** that day. Its visible row count can
  therefore differ from Outputs recorded. Current state filters operate after that window.
- Source timestamp: supplied feed/article time, not a verified event occurrence or peer time.
- Intake -> local output: created minus first_seen, if both are valid and nonnegative. It is
  not exact Typefully created_at or peer-to-NBN latency. The rolling speed audit keeps that
  richer comparison separate.
- Engagement: last observed Typefully likes/reposts, missing as unknown. No fresh analytics
  request is made by the Desk, and weak early engagement is not an editorial score.

Explicit replay/eval rows are excluded from feed metrics and output views. Historical replay
exports normally live outside the production posts DB entirely. The Desk is not an inventory
of every draft in the Typefully account: unknown/manual/external drafts are not imported merely
by reconciliation. Use the provider API/UI when the account-wide state is needed.

## Reading a decision

Intake may stop at the Haiku mailroom, Luna Background preparation, writer defer/drop,
editor decision, mechanical check or publisher ambiguity. “Held” alone does not identify
the cause or guarantee a future corroboration retry. Open the reason and the related run.
Run decisions are frozen dispositions from that dossier; the adjacent current item state
may have advanced later. Assignment-Background cards can appear in the run's input inventory
without appearing in the writer's decisions because they were never sent to the writer.

The September 6 pre-editor lifecycle repair records update/base or update-label deferrals as
held story commits with the exact reason; the editor was not reached. Older affected commits
may still say pending after their run completed. Their historical rows were not rewritten:
use the recorded item reason and run completion, not that old pending label, to interpret them.

Run inputs include carried-over leads. Older
completed runs may have pruned dossiers (normally after 14 days); missing detail is explicit,
not interpreted as no work. Up to 100 inventory/decision entries and 50 story commits are
projected for a run. Lists page in groups of 40, at most 250 pages; search narrows the window.
Later publisher-operation status and Output now have their own update clocks; they are not
immutable run-time decisions. Deleted/planned/scheduled/publishing/ambiguous states stay distinct.

## Cost boundaries

Costs use [Central midnight, next Central midnight), not “since that date forever.” xAI
reported charges take precedence; other supported providers use recorded rate estimates.
Unknown billing stays unknown, not free. Reasoning is already included in output tokens.
The displayed ledger covers recorded intake/prep/research/writer/editor calls. It omits the
historical legacy daily receipt-audit path, hosting, external source/search subscriptions/reads and
Codex audit usage. It is not a full invoice or a monthly forecast.

System shows today/week-to-date/month-to-date known spend, with stage breakdowns. Per-run cost
uses directly linked production spend divided by distinct metered newsroom runs. Unlinked
intake/preparation stays shared, not arbitrarily allocated. Writing includes in-session research;
zero delegated research calls does not mean zero research. Replay/test/shadow and unclassified
costs are separated. Current role/provider/effort/mode comes from live configuration, not old calls.

Day/week/month averages use complete Central calendar periods in a bounded 93-day review window.
The opening partial ledger day and current partial periods are excluded; covered zero-call days
count. Insufficient complete periods show unavailable. Query truncation above 50,000 calls is
explicit and suppresses completed-period averages. These blend historical rosters, not forecasts.
Unknown costs make known totals lower bounds. The legacy daily receipt audit is disabled by owner
decision, separate from the rolling Codex audit.

## Technical contract

nbn/desk.py explicitly opens SQLite mode=ro and query_only; it never calls migration-bearing
store.connect(). One short read transaction gives a coherent snapshot, with a three-second
query deadline and bounded field projections. Selected business dossiers/evidence are shown safely;
credentials, provider reasoning and mutation ownership tokens are excluded. Text is escaped;
external links allow only HTTP(S)
without embedded credentials. Assets are fixed routes, not arbitrary filesystem access.

Responses are no-store/no-referrer, with a same-origin content policy. Snapshot JSON contains
the versioned `/desk/api/workspace` contract. `/desk/api/snapshot` keeps the prior fragment
contract for compatibility. `/report` remains server-rendered and is not automatically refreshed.
`POST /desk/api/item-action` accepts only authenticated reconsideration, reusing operator_actions
and checking the latest owner-action version. The worker activates it at its leased inventory
boundary; the HTTP handler never invokes a model or publisher. No new table is required.
`POST /desk/api/visual-action` uses a separate versioned `visual_choices` queue. Immutable
images are served through authenticated read-only `/desk/visuals/<asset_id>` lookups, never
arbitrary local paths. Image files/evidence outlive normal rich observation expiry.
The approved React UI compiles to one static bundle; Python remains the sole Railway runtime.
Sources/lockfile/build live in `desk_ui/`. Run `npm ci && npm run build`; committed assets and
their SHA-256 manifest ship with the Python archive. No second service, websocket, tracing vendor
or model/provider call was added.

`run_observations` retains the safe final writer packet, dossier, research/tools, editor inputs,
returns and applied decisions. Rows are capped at 384 KiB; each run reserves 80 ordinary rows /
1 MiB plus 40 critical rows / 2 MiB (122 including limit markers). Truncation is labeled. Worker
maintenance expires rich payloads after 14 days, including abandoned runs; small headers remain.
Savepoint failures are nonfatal and never commit/rollback caller work. Publisher finalization
merges delivery details without destroying editor provenance. `source_poll_health` records the
latest ordinary poll per source. All Desk and Review GET routes remain read-only.

The PDF is a dated explanatory artifact, not a live settings dump. Its fixed authenticated
route is /desk/system-guide.pdf. Rebuild with scripts/build_system_guide.py in a documentation
environment with ReportLab; ReportLab is not added to worker requirements.
