# Plan 0061 — Prototype review

Date: 2026-09-06. Owner approved the visual direction; requested post-card padding correction
is implemented and browser-tested. Owner-requested System cost review and model roster added.
No production integration.

Prototype checkout: `/Users/brady/codex/nbn-desk-prototype`.
Validated source: `06dc575b9cb528cf48c782529eb50c68194e8f2e`.

Private prototype: https://nbn-newsroom-prototype.bradyswenson.chatgpt.site
Owner-only Sites publication succeeded on September 6, 2026 at 17:59:28 UTC. This is separate
from the NBN Railway deployment. Site version 4; deployment `appgdep_6a9da9e9b2248191bd4347a6647c7015`.
The same Codex browser tab was moved from the local preview to this URL; the hosted run view
rendered successfully and exposed its run picker, decisions, research/copy tabs and controls.

## What to try

1. Widen the browser. Open the latest sample, then page backward and forward. The run's input,
   decisions, research, copy and activity move together. The selection remains pinned when a
   simulated new run arrives; Back to latest resumes following.
2. In the **8:07 AM BPI run**, open Copy. Compare the original writer proposal and the actual
   submitted body, with research in the adjacent inspector. The saved editor delivery note is
   distinguished from the missing full editor response.
3. Open Research in that run. Its assignments, partial findings and review questions are visible.
   “Preview a structured research return” shows the desired richer deliverable, explicitly
   labeled as an authored example, not a historical model response.
4. In the **10:11 AM run**, compare the editor's mempool-music drop with the mortgage lead's
   failed research. These are different review questions, not the same held state.
5. In the **11:12 AM run**, inspect the Strive proposal's pre-editor defer and old recording
   mismatch. A pending historical commit is not animated as currently running work.
6. Resize while inspecting a story. Wide screens keep a persistent inspector; intermediate
   widths use a drawer; mobile uses the viewport width. Selection and detail tab remain intact.
7. Inspect Intake & Sources, Outputs and System. Their scope is these historical examples,
   not live account state. System costs use a broader September 2–6 ledger snapshot at 12:45 PM
   Central: switch today/week/month totals and stage breakdowns; compare direct run averages and
   completed-period averages. Weeks/months remain unavailable until complete history exists.
   The role/model/effort roster uses a separate 12:56 PM production-configuration snapshot, not
   historical usage; delegated research and the daily receipt audit are explicitly distinguished.
   Quiet/interrupted/new-arrival demonstrations are illustrative.

## What is real vs illustrative

Recorded run IDs, counts, decisions, writer copy, selected preparation work and BPI's submitted
body came from bounded read-only production queries. Timing/freshness observations also use the
existing audit record. Headlines and explanatory summaries are condensed; review questions are
annotations. No prompt changes, model calls, Typefully API calls or publishing actions were made.

The new-arrival, quiet and interrupted previews and structured research return are explicitly
illustrative. Historically unavailable exact packets, full research transcripts, stage timing,
source health and full editor responses remain labeled unavailable/partial.

## Verification

- TypeScript and production build passed; app-scoped lint passed.
- 60 browser assertions passed with no browser errors: run and timestamp navigation, browser
  history, pinned arrivals, follow state, intake filtering, research/copy provenance, output
  status distinction, responsive detail mode, selection preservation, Escape/focus return,
  mobile navigation, quiet/interrupted examples and horizontal-overflow checks. The two added
  checks verify all-side padding on both writer and final-copy cards at desktop and mobile widths.
- Cost checks cover period switching, distinct-run averages, incomplete-period labels and System
  overflow at 320/390/768/1024/1920/2560px. Separate arithmetic tests cover stage/provenance
  reconciliation, shared-cost exclusion, empty/partial periods, zero-use dates, calendar boundaries
  and unknown-cost counts. Read-only cost sampling made no production/model/publisher changes.
- Model roster checks match five primary roles to verified model IDs and effort; the daily
  Sonnet receipt audit is shown separately. Desktop/mobile roster screenshots are included.
- Screenshots captured at 320, 390, 768, 864, 1024, 1440, 1728, 1920 and 2560 CSS pixels;
  visual inspection informed the tablet-wrap and mobile-pagination fixes. The 864px case is a
  CSS-viewport approximation for 200% zoom at 1728px, not a native browser zoom test.
- Local evidence: `/Users/brady/codex/nbn-desk-prototype/outputs/qa/`, including `results.json`.
- Scaffold-wide lint has pre-existing diagnostics in generated/vendor primitives and the
  mobile hook. Dependencies reported 11 installation-audit findings; no force upgrades or
  vendor rewrites were performed. These are not a production-stack endorsement. Review the
  actual integration stack in the lead-coder phase; do not blindly import the prototype scaffold.

## Handoff boundary

The prototype is a separate private review surface, not a replacement for the Railway Desk.
NBN runtime code, credentials, database, prompts, model roster and publication settings were
not changed. The rolling audit remains PAUSED as requested.

Next: the established independent lead review and bounded live implementation. The owner's
visual approval does not fulfill production
integration, live observability recording, legacy report restyling or deployment smoke checks.
