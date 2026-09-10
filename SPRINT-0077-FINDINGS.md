# Sprint0077 — reporter tooling

September10, 2026. Owner-approved bounded tooling sprint. The previous pilot is stopped;
later steering permits test drafts if necessary, not publication or an audit restart.

## Implemented and reviewed

- Independent bounded read/notebook/delivery lanes replace the serial MCP bottleneck.
  Timeout, cancellation, EOF and bridge death clean owned workers/browser descendants.
  Ambiguous submissions retain the stable ID; no automatic retry creates another draft.
- Daemon SDK turn consumption; distinct operator_stop, shift_cutoff and turn_timeout states.
- PDF literal search and selected pages1–500,32MiB input, bounded parser/context and
  same-page continuation. Physical page numbers, capture scope, byte count and document
  hash remain attached. Page pixels are separate from text evidence.
- Browser text query/offset, outbound pointers and actual viewport screenshots.
- Complete visual schemas/example, with missing fields reported together.
- Existing Google cache/provider health; typed X/Google failures distinct from zero hits.
  Permanent narrow SerpAPI log filter avoids concurrent credential-bearing URL logging.

No model/effort/cadence, editorial, auth or publication-policy changes. Independent lead
approved the plan, then approved implementation after six bounded corrections covering
crash cleanup, protocol/cleanup races, timeout status, PDF continuation, log safety and
X errors-only responses. Dedicated regressions cover each correction.

## Verification

- Final full suite:804passed in47.690s. Log: `/private/tmp/nbn-0077-tests.log`.
- Actual Railway Google:0.98s,3results,4871requests remaining; X recent search:0.28s,
  10posts,HTTP200. Earlier transient failures' exact cause remains unestablished.
- CLARITY literal search:500pages in1.10s. Targeted pages214–215:0.45s; these were
  inaccessible under the previous20-page reader cap.
- Anthropic threat-report PDF:154pages in0.75s. The specific literal query returned no
  matches, correctly distinguished from failure to read the document.
- Treasury PDF:1.39s. Original table pixels and generated chart inspected;5.187Baccepted,
  6Bmaximum,10.489Boffered, all face value, agree with the original table.
- Actual bounded browser worker: official Fed text,80outbound pointers and screenshot;
  successful response, zero remaining owned tool jobs.
- No model calls, Typefully draft/comment writes, publication or audit wake needed for
  these checks. Delivery tests use mocks and temporary databases.

Local inspection artifacts:
`/Users/brady/Documents/ChatGPT/Next Block News/output/0077-tooling-smoke/`.

## Limits

Bot blocks, outages and missing text layers remain possible. PDF search is literal/capped,
not semantic understanding of a whole document. Screenshots do not establish reuse rights
or publication date. Timeouts release slots but cannot make an upstream provider respond.
Tool smokes do not establish improved editorial judgment or autonomous image selection.

## Release and rollback

Final review and tests complete; clean backend deployment and local install/smoke pending.
Rollback keeps reporter/audit/autopost stopped, restores the previous backend deployment
and two backed-up runtime files, then refreshes the sandbox receipt. Never reset a cutoff,
silently create a shift or restart the legacy model pipeline as part of rollback.
