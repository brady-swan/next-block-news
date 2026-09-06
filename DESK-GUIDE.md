# The live Desk

Current 2026-09-06. The Desk is part of the existing NBN Railway service, not a separate app
or public news site. All /desk routes, assets, snapshots and the PDF require the existing
NBN_REPORT_TOKEN. Do not share authenticated links or put them in public documentation.

## Views

| View | Use it for |
| --- | --- |
| Live (/desk) | Worker health, next editorial deadline, latest checkpoint, recent intake and completed model calls |
| Intake (/desk/intake) | First-seen-day pool; filter status/title/source/event; inspect mailroom/prep reasons for one item |
| Newsroom (/desk/runs) | Historical run checkpoints; open a run for its terminal candidate decisions and editor/delivery reasons |
| Outputs (/desk/outputs) | Locally tracked copy, receipt, observed timing, Typefully link, confirmation and weak engagement context |
| System & costs (/desk/system) | Effective roster/cadence, recorded editorial-seat spend, current NBN storylines and visual PDF |
| Review tools (/report) | Existing guarded Stage draft, Dismiss, Send to desk, mutation-resolution controls and loaded orientation |

No new view changes editorial settings or calls a model, source API or Typefully. Navigating
to an external source/Typefully opens that site normally. Existing actions remain explicit
on Review; no automatic publishing, dismissing, draft editing or retry is triggered by viewing.

## What “live” means

The server renders an initial snapshot. JavaScript refreshes its read-only fragment every
15 seconds while visible. Hidden tabs stop polling; returning refreshes. Pause/resume and
Refresh now are explicit controls. Open details are retained across refreshes. Automatic
refresh waits while you are selecting text or have a control focused inside the content.
The selected Central day stays fixed, including over midnight; choose Today to advance it.

The connection line gives the last successful snapshot time. A failed request keeps the
previous content and labels it potentially stale. JavaScript off means manual reload only.
The worker banner is separate: starting, healthy, error or stale (no current-process completed
cycle for ten minutes). An old persisted success is displayed, not confused with this process.

Newsroom statuses are **last recorded checkpoints** (surveying, researching, validated,
materializing, completed, deferred or fallback), not exact live stages. A stopped worker's
old researching checkpoint is not proof of ongoing research. Model calls appear after they
return; the Desk does not stream hidden reasoning or tokens. It does not poll every feed's
health independently, so a healthy loop is not proof that every source responded.

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

Run input links use each item's own first-seen day, including carried-over leads. Older
completed runs may have pruned dossiers (normally after 14 days); missing detail is explicit,
not interpreted as no work. Up to 100 inventory/decision entries and 50 story commits are
projected for a run. Lists page in groups of 40, at most 250 pages; search narrows the window.

## Cost boundaries

Costs use [Central midnight, next Central midnight), not “since that date forever.” xAI
reported charges take precedence; other supported providers use recorded rate estimates.
Unknown billing stays unknown, not free. Reasoning is already included in output tokens.
The displayed ledger covers recorded intake/prep/research/writer/editor calls. It omits the
legacy daily receipt-audit path, hosting, external source/search subscriptions/reads and
Codex audit usage. It is not a full invoice or a monthly forecast.

## Technical contract

nbn/desk.py explicitly opens SQLite mode=ro and query_only; it never calls migration-bearing
store.connect(). One short read transaction gives a coherent snapshot, with a three-second
query deadline and bounded field projections. No credentials, raw dossiers, evidence bodies
or mutation ownership tokens are projected. HTML is escaped; external links allow only HTTP(S)
without embedded credentials. Assets are fixed routes, not arbitrary filesystem access.

Responses are no-store/no-referrer, with a same-origin content policy. Snapshot JSON contains
only the server-rendered safe fragment, generated_at and worker state. /report remains a
separate legacy action surface and is not automatically refreshed. The new views do not add
a frontend framework, websocket server, database schema, event bus, or model calls.

The PDF is a dated explanatory artifact, not a live settings dump. Its fixed authenticated
route is /desk/system-guide.pdf. Rebuild with scripts/build_system_guide.py in a documentation
environment with ReportLab; ReportLab is not added to worker requirements.
