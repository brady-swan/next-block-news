# 0077 — Reporter tooling repairs

Owner approved build/test/iteration September 10, 2026, turn
`01a08d5b-def5-7342-807d-fd8262df6a3c`. The reporter test is over, not temporarily
waiting to be restarted. Audit and autopost remain off. This is not editorial tuning.

## Stopping goal

Owner steering22:16:27Z permits Astra-generated, unscheduled Typefully drafts if needed
for a bounded end-to-end test. This does not authorize autopost/audit restart or indefinite
reporting. Prefer no-write acceptance checks; stop any test reporter when testing is done.

A verified toolset ready for a separately authorized reporter test. Reproduce the actual
pilot failure classes, repair local defects, add regression coverage, smoke the repaired
read-only tools and renderer, document external limitations and rollback. Install tested
runtime/backend repairs with all reporting paused. No inference or Typefully writes are
needed for acceptance. Do not keep adding capabilities after these checks pass.

## Observed delta from completed 0076

- One serial stdio bridge handles all tools: a hanging browser prevents subsequent notes
  from reaching the backend. Several calls timed out after90s; an orphan bridge remained.
- A607s turn hit the600s supervisor ceiling. Failure was reported ambiguously as
  pause/cutoff/ceiling. Shutdown initially outlived a7.5s stop check.
- PDF text stops at the first20 pages and rejects files over10MiB. This blocked deeper
  CLARITY clauses and an Anthropic report. Raising output/context limits is not the answer.
- Treasury chart attempted `title/data/subtitle`, then discovered missing `purpose`,
  `headline`, and `unit` through successive errors. The exposed schema says only object.
- Three reporter Google searches failed. Reporter bypasses the existing cache/typed health
  state. Exact X reads worked, several recent searches failed without useful explanations.
- Browser text clips at24k and returns no outbound links or targeted section access.

## Implementation sequence

1. **Runtime and tool isolation.** Give each tool invocation an owned, bounded subprocess;
   consume protocol requests/cancellations independently so a slow read cannot block notes.
   Bounded concurrency, serialized stdout, cleanup on timeout/cancel/EOF/parent exit, and
   kill only explicitly owned process groups. Submission timeout remains an uncertain result,
   never an automatic retry/create. Supervisor distinguishes stop/cutoff/turn timeout and
   cannot hang at interpreter shutdown on a non-daemon SDK-consumer thread. No automatic
   shift restart, cutoff extension, or relaxed publishing boundary.
2. **Targeted PDF reading.** Keep default article behavior compatible. Add reporter PDF
   page-range and literal-search access with bounded download/parser time, byte/page/output
   ceilings, real page numbers and explicit truncation/search scope. Use existing Poppler;
   no OCR service, vector store or new model. PDF pixels remain separate from text evidence.
3. **Usable visual contract.** Expose actual required template fields and a complete working
   example; report all missing fields together. Reuse existing renderer, evidence binding,
   image inspection, attribution and attachment restrictions. No renderer/style redesign.
4. **Read reliability and navigation.** Diagnose live search failures without exposing keys.
   Use existing cache/health records, preserve typed provider errors and provide an actionable
   native-search fallback suggestion. Do not call failure an empty result. Preserve dates and
   source provenance. Add bounded browser text search/offset and outbound links with safe URL
   checks; no login, private network, forms, or bypass of publisher access controls.

## Review and acceptance

- Independent lead approved September10 with two added checks: saturating read slots must
  not block protocol cancellation or notes; cancellation/EOF/worker death during submission
  must retain the stable submission ID and never automatically retry (mock-only tests).
- Independent lead reviews plan, then implementation once material tests pass.
- Hanging read does not block another request; cancellation/EOF leave no owned tool child;
  paused/expired shifts cannot submit; ambiguous delivery retains the same stable ID.
- Regression fixtures prove page25 access/search, bounded oversized/unreadable PDFs, true
  page labels, clipped/empty results, search failure versus zero results/cache behavior.
- A complete public chart example renders successfully with existing source checks intact;
  malformed input returns a useful field list rather than iterative KeyErrors.
- Browser fixture proves a section beyond the initial excerpt and actual outbound links;
  private redirects/non-GET requests remain blocked.
- Focused and full suites pass. Read-only live smoke plus actual rendered pixels inspected.
- Record exact commits, test evidence, local/runtime/backend versions, remaining external
  limits and rollback. No automatic reporting/audit restart; no credentials or model changes.

## Out of scope

Editorial policy/selection/corroboration changes, model/effort/cadence changes, new news
providers, new memory architecture, Nano Banana, fresh reporter shifts, drafts/comments,
Typefully replacement/publishing, and speculative redesigns.
