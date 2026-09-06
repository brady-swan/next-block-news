# Plan 0058 — Deploy the bake-off roster

Status: approved by independent lead coder after one focused provenance clarification.
Owner authorized plan/review/build/deploy/smoke. Implementation and final independent diff
review approved. Deployment/smoke in progress.

## Outcome and scope

Keep NBN's existing editorial core, cadence, source policy, continuity, source-in-first-reply
format, and Typefully lifecycle. Change the models occupying the existing seats:

| Seat | Provider/model | Effort |
| --- | --- | --- |
| RSS/EDGAR intake | Anthropic / claude-haiku-4-5 | unchanged |
| Assignment preparation and relevant storyline selection | OpenAI / gpt-5.6-luna | low |
| Run-scoped newsroom/writer | xAI / grok-4.3 | medium |
| Focused research assistant | xAI / grok-4.3, native web + X search | medium |
| Independent batch editor | xAI / grok-4.5 | medium |

The evidence is in MODEL-BAKEOFF-RESULTS.md, MODEL-PREPARATION-RECALL-RESULTS.md,
and MODEL-RESEARCH-BAKEOFF-RESULTS.md. Small samples justify a monitored rollout, not a
claim that these models are universally superior. No new keys, new discovery service, prompt
rewrite, extra research quota, or publication-policy change. Autopost stays OFF.

## Phase 1 — Provider boundary and accounting

Add a small production Responses adapter using the existing HTTP dependency. Preserve the
existing Anthropic path for intake and explicit rollback. Model-name routing is sufficient;
do not build a general model orchestration framework or import the evaluation harness in prod.

Translate the existing tool schemas, tool results, and tool choices to Responses. Preserve
provider output items (including reasoning/state) across a run's tool turns, not just visible
text. Normalize text/function calls back to NBN's current response interface so validation,
candidate coverage, event identity, reservations, and publication mechanics stay intact.
Bound timeouts; disable hidden retries. Existing newsroom's single retry remains explicit.
Incomplete/refused/malformed responses cannot become valid tool submissions.

Record provider, requested and returned model, effort, uncached/cache/reasoning tokens,
native web/X calls, and cost provenance in the existing additive model-usage table. Use xAI's
reported dollar ticks when present (already includes tools); otherwise clearly identified rate
estimates. Do not count cached tokens twice or add tool charges twice. Unknown/failed billing
remains explicitly unknown, not a claim of a free call. Keep existing report totals compatible.

## Phase 2 — Wire existing seats

Use explicit per-seat model/effort configuration. Keep legacy NBN_MODEL as the Anthropic
legacy-stack setting; add a dedicated newsroom model setting. Assignment preparation uses
Luna low with the current schema and fail-open/guide/continuity protections. Editor uses
Grok 4.5 medium with the current payload, decisions, omitted-ID recovery, and safe-draft outage
behavior. Writer keeps its current local read-only tools and complete-dossier contract.
Neutralize hardcoded Sonnet/Haiku names only on active tool descriptions and runtime labels.

## Phase 3 — Native research with an honest evidence handoff

Expose a provider-neutral research assignment tool (accept the old name for compatibility).
Preserve concrete objectives, supplied candidate IDs, existing receipts, one assignment per run,
parent model-call reservation, and a bounded memo. Native web/X research is not compulsory.

Use one bounded native research call with a strict result shape, followed by local normalization;
limit server-side turns with the documented provider control and enforce local wall/payload
bounds. Record actual internal search invocations even when a provider turn contains several.
Do not pretend a turn cap is a hard per-search dollar cap. No recursive delegation.

Return source-specific findings with exact URLs and dates, plus conflicts, gaps, and a supportable
angle. URLs must appear in provider retrieval/citation metadata before a source-specific finding
can enter the evidence board. Prefer existing/directly fetched text when obtainable. When native
retrieval succeeds but local fetch cannot, preserve the source-specific provider-reported extract
with explicit xAI-search provenance; never label it a verbatim locally fetched document or use
the whole memo as the source body. The writer and separate editor see that distinction. Unknown
or uncited URLs remain pointers. AI-generated X answers are not independent reporting.

The retrieval kind survives workbench serialization and reload, not merely the current run's
adapter label. Source tier/official status cannot upgrade a provider-reported extract into direct
inspection or an independent evidence chain. Its originality/capability stays explicitly
provider-reported; public URL identity and claim support are separate facts. A later successful
local retrieval may replace it with genuine direct text. Test this across two sessions.
Final review refinement: preserve BOTH the native finding and any direct text for a URL.
A nonempty local wrapper is not proof that it contains the useful facts. Memory deduplication
and editor catalogs distinguish retrieval kinds, while only genuine direct reporting can
contribute an independent reporting chain. No new page-quality heuristics are introduced.
For X, derive the author only from the provider-observed status URL, never from a model-supplied
handle. `/i/status/...` leaves authorship unknown unless a direct fetch resolves it. A claimed
author conflicting with an observed named status URL is flagged, not accepted as first-party
evidence. Preserve this distinction through the editor catalog and final resolution metadata.

Reuse current FetchRecord/continuity machinery and source classification, with a distinct
evidence capability for provider-reported extracts. Keep safe URL checks and existing byte/fetch
limits. Do not require every research result to pass the same bot-blocked local fetch that the
native-search lane is meant to improve. On research error, preserve any usable receipts and
let the existing newsroom finish or defer normally; no extra autonomous research loop.

## Phase 4 — Verification and rollout

1. Tests: Responses request/turn translation, forced tools, incomplete output; Luna failure and
   omission behavior; editor handling; native research cited/uncited/unsafe sources and bounds;
   pricing including cached inputs/reasoning/tool costs; full existing suite.
2. Bounded live read-only provider smoke with existing Railway keys: Luna structured prep,
   Grok writer function-call round trip, Grok editor, and native web/X evidence return. No
   production candidate or publishing mutations during adapter probes.
3. Independent final diff review for concrete correctness issues (not another architecture cycle).
4. Confirm production target, one replica, /data, autopost OFF. Online SQLite backup before
   additive migrations. Deploy code, explicitly set roster variables, verify deployed revision.
5. Health, DB integrity, effective roster, billing rows, and one natural non-empty worker cycle.
   Verify draft delivery/source reply through Typefully when a genuine candidate is produced;
   never fabricate a public post to test transport and never enable autopost. If live news does
   not yield a draft promptly, report the limit and retain monitoring rather than force a story.
6. Update SYSTEM.md and handoff with actual rollout/smoke results. Preserve user/audit edits.

Rollback: restore the prior per-seat Anthropic model settings (Sonnet writer, Haiku preparation
and research, prior editor) or previous deployment on protocol/integrity/delivery regression.
No database restore for normal code rollback; additive telemetry is backward compatible.
Inspect the existing audit automation and resume it if this bake-off left it paused, with the
new roster/cost and retrieval failure observations; do not duplicate monitors.

Deployment configuration is explicit. Retain the prior conservative code defaults for unconfigured
installations and the legacy stack; the checked-in example and production override manifest show
the new five-seat roster. Do not silently retarget every ANTHROPIC_MODEL consumer.

## Verification record

- Full suite: 407 tests pass, including ten new provider/research tests.
- Independent final review approved after fixing refusal-order handling and preserving both
  native findings and local wrapper text across memory reload. No remaining deploy blocker.
- Existing-key live read-only probes passed: Luna low strict preparation; Grok 4.3 medium
  two-turn function call and production dossier schema; Grok 4.5 medium editor JSON; Grok
  4.3 native web/X research with five citation-bound sources.
- Native probe: six web + two X calls, 22 seconds, provider-reported $0.07376625. Small writer
  two-turn probe: $0.0042937; editor probe: $0.0037872. These are compatibility probes,
  not representative full-run cost estimates.
- SQLite online backup, integrity checked by script:
  `/data/backups/nbn-pre-source-policy-20260906T033407Z.db`.
- Rollout observation: Luna prep retains its existing 45-second timeout; watch fail-open rate
  against the benchmark's 43.8-second average before changing that setting.
