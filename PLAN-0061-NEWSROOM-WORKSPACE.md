# Plan 0061 - NBN newsroom workspace

Date: 2026-09-06.
Status: owner approved build and disabling the legacy daily receipt audit, September 6.
Independent lead approved integration, then the code subject to focused attribution corrections.
Those corrections are implemented. Verification/release is in progress; rolling audit stays paused
until deployment and smoke complete.

## Brief and acceptance

Build a calm, beautiful operational workspace for spending time with NBN. The central task is
understanding the latest editorial run: what reached the writer, what the writer did, what the
editor changed or rejected, and what actually reached Typefully or X. Raw intake and technical
health support that task; they must not dominate it. A working endpoint is not visual acceptance.

The **run is the primary unit of navigation**, not the calendar day or an endless activity feed.
The main view opens on the current/latest recorded production newsroom run. Brady can page
backward and forward through previous runs without leaving this same workspace.

Brady's explicit responsive requirement: use extra horizontal space for a persistent details
pane; use an overlay at intermediate widths and a full-screen detail view on mobile. Preserve
the selected story when the viewport changes. This is one interaction model, not three unrelated
interfaces. The full-width 16-inch MacBook Pro and large-monitor experiences are first-class.

Primary design references:
- Rabbet visual direction: https://me.muz.li/mindinventory/rabbet-smart-real-estate-dashboard-design-2
- Linear's 2026 hierarchy refresh: https://linear.app/now/behind-the-latest-design-refresh
- Langfuse linked overview/detail: https://langfuse.com/changelog/2026-07-28-langfuse-pulse
- Langfuse adaptive run view: https://langfuse.com/changelog/2026-08-28-responsive-timeline
- Linear's Triage/Peek interaction and Stripe's object-centered dashboard hierarchy.

Borrow composition and interaction principles, not decorative graphs, mockup-sized text, an
icon-only guessing game, or a new infrastructure product. Keep the NBN identity. Dark charcoal
surfaces, clear type, consistent spacing and restrained orange are the starting palette.

## Phase 1 - Define the run and story view contract

Completed mapping: [Run-first Desk data map](PLAN-0061-DATA-MAP.md). It includes the field-to-record
contract, real production examples, historical gaps, supporting views and useful health checks.
In particular, publisher finalization currently replaces saved editor details with delivery
details; the final writer input and full per-run editor response are not reliably preserved.
The mapping identifies recording changes; it does not implement them or reconstruct old history.

Read the existing schema and actual production examples before designing idealized cards.
The initial code inspection establishes:
- `newsroom_runs` holds candidate inventory IDs, final writer dossier, counters and checkpoints.
- `desk_preparations` records preparation routing, distilled leads, source pointers and context choices.
- `newsroom_story_commits` records per-run delivery/validation details; the workbench holds
  evolving evidence and editor feedback, not immutable history for every previous run.
- `posts` and publisher state support locally tracked delivery and confirmed publication.
- `/desk/api/snapshot` currently supplies a server-rendered fragment, not a complete run inspector.

Map each visible field to a recorded source and clock. In particular, candidate inventory is not
automatically the exact packet delivered to the writer, and today's mutable workbench is not
proof of what an old editor saw. Classify fields as already recorded, needing a new checkpoint,
or historically unavailable. Do not backfill fictional detail or infer unrecorded execution.

Define four linked views within one selected run:
1. Delivered input: original lead, source, prepared assignment and relevant context actually sent.
   Separately identify upstream Background/not-sent items; never label them writer rejections.
2. Writer: grouping, research/tool outcomes, proposed copy, defer/drop/publish recommendation,
   and explicit decision note. Preserve many source items becoming one story.
3. Editor: verdict, explanation and revised copy. Offer readable original/final comparison.
   Distinguish not reached, pending, unavailable/fallback and an actual editor rejection.
4. Delivery: draft, scheduled, publishing, confirmed published, ambiguous or failed, with the
   observed timestamp and relevant link. A writer recommendation is never a publication count.

Maintain an independent current-health/arriving-now area and an explicitly selected run clock.
Historical runs remain fixed; Follow live deliberately advances to new work. Live stage labels
must be supported by timely checkpoints; silence is not a simulated running animation.

Run navigation behavior:
- Default to latest and follow new runs until the owner explicitly browses history or opens
  a run-specific link. Show an in-progress run as such, including stages not yet reached.
- Provide persistent **Previous run** (older), **Next run** (newer), a timestamped run picker,
  and **Back to latest**. The last action also resumes Follow live.
- Paging into history pins that run. New runs do not shift the selected run or renumber the
  owner's position; show a quiet newer-run indicator. Reaching the latest by paging alone
  does not silently resume Follow live.
- Navigate by stable run identity and chronological ordering, including a stable tie-breaker,
  rather than mutable list offsets. Run-specific URLs support refresh and browser Back/Forward.
  Cross midnight naturally; changing the date must not be a prerequisite to paging.
- Include recorded production runs with no output, writer/editor drops, and failed or partial
  runs. Do not skip quiet runs or mix historical replay/evaluation runs into the default sequence.
  An intake poll or an empty cadence window with no newsroom run is not an invented run card.
- Page the entire run workspace together: input, writer, editor, outcome, totals and inspector
  must all belong to the selected run. Clear a story selection that does not belong to the new
  run; browser Back restores the prior run/story selection.
- Keep run-time decisions distinct from later delivery updates. An old run may link to the
  current output state, but label that state and its clock separately from the recorded outcome.
- Use bounded history queries and accessible disabled/end-of-history states. Paging through
  recorded history never reruns models or changes editorial state.

## Phase 2 - High-fidelity responsive prototype before production work

Review artifact: [Prototype review guide](PLAN-0061-PROTOTYPE-REVIEW.md). The separate prototype
contains three recorded runs plus clearly labeled illustrative research and lifecycle states.
Its research view exposes assignment, returned/retained findings, downstream use and quality
review questions, not just activity counters. This is not a live data connection.

Produce a working visual prototype with sanitized examples from real NBN runs. Clearly label
prototype/replay data and simulated states. No live provider calls, publishing actions or model
judgment are needed for the prototype. Inspect the real source data but do not ship credentials
or raw provider payloads in assets.

Main composition:
- Quiet navigation: Newsroom, Intake & Sources, Outputs, System. Start with storylines in the
  selected-story inspector; add a dedicated browser only if useful. Review actions are integrated
  with the relevant item rather than another unstructured report to hunt through.
- Compact run header: Previous/Next run, timestamped run picker, Back to latest/Follow live,
  status/time, next due run and small run totals. Keep paging available on narrow screens.
- Primary run workspace: connected input/writer/editor/outcome views, readable story titles,
  concise decisions, obvious selection, and a visible relationship between merged source leads.
- Adaptive inspector: Overview, Sources, Writer/Editor copy, and recorded Activity. Important
  outcomes remain visible in the workspace; technical payloads are optional detail.
- Arriving now: compact recent intake/waiting stream, separate from the selected run.
- Costs and health: restrained supporting information; deep token/model configuration moves
  to System. No invented funnel arithmetic across different units or dates.

Start with content-driven breakpoints, then tune using the prototype:
- 1920+ CSS px: use nearly the full width; persistent inspector beside the run workspace.
- 1440-1919: full-width laptop workspace; keep a persistent inspector where its minimum readable
  width fits, otherwise use the drawer. Collapsible navigation releases useful space.
- 1024-1439: compact workspace; overlay detail with reliable return to the selected row.
- 640-1023: simplified stage navigation and detail overlay/page.
- Under 640: story cards and full-screen detail with a vertical journey and clear Back behavior.

Do not grow prose columns to fill a monitor. Allocate added space to comparison and context.
Breakpoints use the actual CSS viewport, including macOS scaling and browser zoom, not physical
display resolution. Panel presentation changes without losing selected run/story/tab, filter,
history or reading position. Modals/drawers support keyboard focus, Escape and focus return;
mobile supports browser Back. Selection must be available without hover.

Live refresh must not reorder the story under the cursor, replace selected text, reset scroll,
or steal focus. Show an unobtrusive new-run/update affordance when the owner is reading a pinned
run. Include reconnect, stale, empty, many-item, long-title and partial-failure designs.

Review the actual prototype at 390, 768, 1024, 1440, 1728, 1920 and 2560 CSS px, plus zoomed
desktop and intermediate widths. Screenshots and interaction checks are required. The owner
reviews the wide-screen main view, selected-story inspector, writer/editor comparison and mobile
view before the production integration is considered visually approved.

## Phase 3 - Independent review and bounded implementation

Use the established independent lead-coder review for the plan/data contract, then a focused
implementation review. Resolve real blockers; avoid an open-ended review or feature expansion.
The lead review is not a substitute for visual design review.

Reuse the Python/Railway service, SQLite, existing source/model/publisher design and authentication.
Choose the smallest UI implementation that preserves state and remains maintainable; do not
add an event bus, tracing vendor, extra service or frontend framework without a concrete need.

Add only missing run-scoped observability checkpoints: safe delivered-input snapshots, writer
result, editor result/copy and stage timing where absent. Define bounded sizes, truncation labels,
retention and nonfatal recording behavior before implementing. Keep provider reasoning blobs,
credentials and mutation ownership tokens out of these records and all browser projections.
The dashboard reads data; polling must not invoke models, source APIs or Typefully.

Restyle/consolidate the legacy `/report` experience as part of the same workspace. Keep existing
guarded action handlers and lifecycle rules intact. Preserve old day/item anchors and links through
compatible routing; do not strand users on the old wall-of-text page. Do not add new mutation powers.

No editorial prompt, model, research policy, source weighting, cadence or autopost change is part
of this redesign. It is not a new newsroom engine. Preserve unrelated dirty evaluator/tuning files.

Owner addition, September 6: integrate System cost totals and averages by run/day/week/month and
stage, following the cost review contract in `PLAN-0061-DATA-MAP.md`. Use the existing usage ledger;
do not add provider billing integrations or guess embedded research costs. The prototype includes
a separate 12:45 PM Central aggregate ledger snapshot for design review.
Also add the owner-requested model roster panel: active role/model/provider/effort and mode from
allowlisted runtime configuration, with its own observation time. This must not use older usage
records to infer the current roster or imply that enabled on-demand models are always executing.

## Phase 4 - Verify the experience and production release

The existing rolling audit is already paused at Brady's explicit request for the mapping/build
work. Leave it paused at the phase-1 handoff. Restore it after the release or a safe rollback,
with the existing autonomy boundaries, unless Brady directs otherwise. Do not create a second
monitor. Autopost stays OFF throughout.

Verification must cover both product behavior and data integrity:
- Representative run with a delivered story, writer drop, editor revision/drop, failed receipt,
  source grouping, pending work, no outputs, and historical missing detail.
- Counts and stage labels match real records; writer input excludes not-sent preparation rows.
- Historical decisions are not overwritten by later outcomes; confirmed publication is distinct
  from staging/scheduling and local ledger scope is explicit. Exclude marked replay outputs.
- Previous/Next traverses recorded production runs across dates, including zero-output and failed
  runs. New arrivals do not move a pinned selection; Back to latest resumes following. Verify
  deep links, browser history, sequence boundaries, and consistent run scope across every pane.
- Responsive layouts, real browser screenshots, keyboard navigation, zoom, long content, touch,
  refresh stability, selection across resizing, history and narrow-view focus handling.
- Authentication, escaping, bounded read-only queries, no provider/model calls on refresh, legacy
  guarded-action compatibility, and observability failures not blocking the editorial pipeline.

Run focused and full offline tests plus the clean-release suite. Back up SQLite, deploy a clean
archive to the existing Railway target, check live routes and a natural newsroom cycle. Never
force a production model run or Typefully mutation merely to exercise the UI. Roll back code if
the release is unhealthy. Update current docs/Desk guide and the PDF only where behavior changed.

Release evidence includes real browser screenshots at the key widths and the live data checks,
not just HTTP 200s. Resume the audit with checks for snapshot/run freshness, stage attribution,
selection stability where observable, and accurate output/cost scopes. Hand off a navigable
workspace and the before/after examples that establish it meets the brief.

## Independent review and implementation decisions

The requested independent lead approved the plan and core implementation. Reuse of the approved
React components preserves visual/interaction fidelity; the result is one static bundle with
no second runtime, server, hosting service or dynamic chunks. Python/Railway remain unchanged.

Review corrections implemented: final writer-packet timing; editor-preserving publisher merge;
40 critical observations for a full 25-story batch plus handoffs; true-editor-only copy labels;
deleted/planned states; missing/pruned history and costs are not zero; native research assignment
candidate linkage; mutable publisher state named current with its own clock. See DESK-GUIDE.md.

The daily receipt audit was disabled in production via empty NBN_AUDIT_UTC, deployment
73ca3c42-bd8e-4f75-9719-9cf43861bc28. Runtime confirmed disabled and autopost OFF. Source defaults
and audit.maybe_run also honor disabled directly. No historical audit records were deleted.

Final release evidence follows after deployment and smoke.

Pre-release acceptance: independent lead's final approval; 440 offline tests in the working
tree (including two preexisting uncommitted evaluator tests); TypeScript check and static build;
49 Chrome assertions across 320/390/768/1024/1440/1728/1920/2560 CSS px, navigation/history,
research/prefetch/copy, responsive inspector, padding, Escape, no-overflow, authentication token
preservation, disabled audit, legacy review and error retry. Browser exceptions: zero.
Screenshots were visually inspected; changed PDF pages 6-8 were rendered and inspected.
Backup `/data/backups/pre-0061-20260906T183606Z.db`: 23,498,752 bytes, quick_check=ok.
