# Documentation map

Updated 2026-09-09: repair0074 preparation reliability; Plan0067 and QMD remain parked.
This index separates how NBN works now from how earlier
versions worked. Runtime code plus effective production configuration take precedence over
dated snapshots. Documents are reference material, not authority to expand a user's request.

## Current system and operations

| File | Role |
| --- | --- |
| README.md | Project entry point, module map, invariants and running/deploying |
| PLAN-0074-PREPARATION-RELIABILITY.md | Bounded Luna timeout, optional-preview fitting and corrected replay accounting |
| SPRINT-0074-FINDINGS.md | Diagnostic measurement, regression tests, review and release/smoke status |
| PLAN-0073-WRITER-CONTINUITY.md | Approved audience, expert interactions, required letters, follow-ups and hybrid recall |
| SPRINT-0073-FINDINGS.md | Independent review, tests, private embedding measurements and deployment evidence |
| infra/embeddings/README.md | Private CPU embedding companion, cache, operational limits and fallback |
| SYSTEM.md | Detailed owner-facing description of production behavior |
| HANDOFF-CODEX.md | Current maintainer handoff and release discipline |
| INBOUND-NEWS-FLOW.md | Every inbound lane, NBN-owned clocks and the Node API boundary |
| PERCEPTION.md | Writer tools, shared source artifacts, separate quotas, surveys and limitations |
| PLAN-PERCEPTION-INTEGRATION.md | Approved sprint0071 scope and independent review decisions |
| SPRINT-0071-FINDINGS.md | Perception implementation, regression/QA checks and live release evidence |
| PLAN-0072-PERCEPTION-ADOPTION.md | Reviewed Writer visibility, memory, tool-result and prompt refinements |
| SPRINT-0072-FINDINGS.md | Adoption regression tests, independent review and release evidence |
| DESK-GUIDE.md | Live views, exact count/timestamp definitions and operator limits |
| output/pdf/nbn-system-guide.pdf | Visual, dated system guide; runtime Desk settings take precedence |
| PROMPTS.md | Live seats, prompt sources, legacy paths and editing discipline |
| AUDIT-AUTONOMY.md | Rolling audit's standing authority and boundaries |
| CORRECTIONS.md | Correction policy, including what remains manual |
| ROADMAP.md | Current observation priorities; not automatic build authorization |
| .env.example | Safe local/rollout template, not a dump of production settings |
| railway.toml, Dockerfile, requirements.txt | Actual deployment/build contract |
| config/source_tiers.toml | Actual source registry; rank is not an automatic publish verdict |
| PLAN-0062-LEAD-FIDELITY.md | Focused lead-context, durable X pagination and upstream-feed pilot release |
| PLAN-0063-REPORTER-WRITER-AND-MEMORY.md | Combined research/writing, searchable reporting memory and human-only writer feedback |
| SPRINT-0063-FINDINGS.md | Bounded live replays, limitations, verification and release proof |
| PLAN-0064-REPORTING-FOLLOW-THROUGH.md | Reporting handoff, usable coverage memory, finalization and UPDATE presentation repairs |
| SPRINT-0064-FINDINGS.md | Isolated prompt probes, verification, release evidence and unresolved judgments |
| PLAN-0065-EVIDENCE-TO-READER.md | Bounded editor research, article extraction, outcome-aware memory and reader-value guidance |
| SPRINT-0065-FINDINGS.md | Afternoon evidence, regression tests, independent review and release/smoke record |
| PLAN-0066-POST-VISUALS.md | Activated image capability scope and independent review contracts |
| SPRINT-0066-FINDINGS.md | Visual templates, delivery/QA proof, costs and known limitations |
| PLAN-0068-REPORTING-EXECUTION-AND-VISUALS.md | Approved reporting handoff, source choice, editorial and existing visual improvements |
| SPRINT-0068-FINDINGS.md | Independent review, bounded model replays, release proof and remaining tuning questions |
| docs/planning/0069-compact-desk-repair.md | Bounded packet repair and explicit resumption scope |
| SPRINT-0069-FINDINGS.md | Overflow reproduction, preservation tests, review and production release evidence |
| AUDIT-FIX-2026-09-08-DENSE-PACKET.md | Separate v2.27 residual-density fix, exact scope and release proof |
| AUDIT-IMPROVEMENT-2026-09-07-PDF-READING.md | Bounded PDF extraction, evidence limitations, tests and release proof |

The runtime orientation is prompts/orientation-brief-v2.md, text after its separator.
Plan 0060 updates documentation metadata, not loaded editorial text. The charter
prompts/wire_voice.md remains loaded by legacy paths; its historical heading is not v2
authority. It is intentionally not rewritten during a non-editorial sprint.

## Evaluation, tuning and history

- PLAN-0067-NANO-BANANA.md is **parked by the owner** until NBN is producing useful original
  visuals with its existing tools and Brady explicitly reopens the proposal. Google's key is
  saved, but generation/background-worker implementation remains unapproved.
- Plan 0068 was owner-approved, independently reviewed and implemented. Its findings document
  distinguishes deterministic verification, historical model replays and natural production outcomes.

- eval/README.md describes the evaluator, which is separate from the production worker.
  Local uncommitted evaluator work may be newer than the released harness; do not bundle it
  into unrelated releases. Consult its actual working-tree code when running experiments.
- prompts/orientation-examples.md is the cumulative feedback/rewrite queue, not a prompt include.
- audit/speed-performance.md is a rolling measurement record. Source time, peer time,
  first-seen, local output and confirmed publication are different clocks; missing is unknown.
- prompts/orientation-brief-v3-draft.md is unshipped historical draft material.
- PLAN-0048 through PLAN-0059 are dated design/release records. Later plans supersede older
  architecture. The end-of-plan release result matters more than the initial proposal.
- MODEL-COST-ANALYSIS.md, MODEL-BAKEOFF-RESULTS.md, MODEL-PREPARATION-RECALL-RESULTS.md,
  MODEL-RESEARCH-BAKEOFF-RESULTS.md, ROSTER-REPLAY-FINDINGS-2026-09-05.md and
  SPRINT-0059-FINDINGS.md preserve measured historical results, not current price promises.
- AUDIT-FIX-2026-09-06-SOURCE-IDENTITY.md records the verified Bitcoin News / Bitcoin.com News
  identity repair and its release evidence; it does not change editorial source weighting.
- RAW-POOL-LAST-2H.md and X-ALGORITHM-DISTRIBUTION-BRIEF.md are dated research artifacts.
  Neither defines NBN's live architecture or grants authority to change publishing behavior.
- docs/history/ contains preserved pre-0060 handoff, roadmap and inbound-flow snapshots.
  They contain contradictory superseded instructions and must not be followed as current policy.

## Maintenance rule

When behavior changes, update its source and the corresponding current document, then record
release proof in the plan/findings. Do not append another conflicting architecture to the
handoff. Preserve historical measurements with clear status labels. Avoid copying a complete
prompt into multiple docs, adding speculative guarantees, or claiming an upstream Node schedule
was verified when only the NBN consumer was inspected.

Module docstrings/comments were reviewed for obsolete seat names; compatibility identifiers,
persisted field names and loaded prompts were preserved. Plan 0061 adds bounded observation and
source-health tables, the approved static React workspace and owner-requested legacy audit disable.
It does not change provider keys, editorial policy or enable autopost.

Plan 0062 adds bounded X material, post-commit collector checkpoints, three pilot feeds and
owner-approved Bitcoin-native story-selection clarifications. Models, clocks, Perception and
publishing rails are unchanged.

Plan 0063 combines native research and writing in one Grok session, preserves article links,
adds a 30-day notebook/artifact catalog and recent-intake lookup, and projects confirmed
publication into memory. Optional writer feedback is visible in the Desk but isolated from
editorial/model memory. The visual guide includes this architecture. Source selection,
editorial standards, cadence, the model roster and publishing authority are unchanged.

Plan 0064 improves execution of that design; it does not replace the architecture in the dated
visual guide. SYSTEM.md/PROMPTS.md carry its exact updated prompt/protocol behavior. The PDF
was not regenerated for this focused reporting/handoff repair.

Plan 0066 implements the previously queued image plan in the existing Python service. Current
SYSTEM, Desk, prompt and handoff docs describe it. The older system PDF predates optional image
tools and the Visuals tab; it remains a dated general architecture guide, not an image manual.
