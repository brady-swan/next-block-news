# Documentation map

Updated 2026-09-06 for Plan 0062. This index separates how NBN works now from how earlier
versions worked. Runtime code plus effective production configuration take precedence over
dated snapshots. Documents are reference material, not authority to expand a user's request.

## Current system and operations

| File | Role |
| --- | --- |
| README.md | Project entry point, module map, invariants and running/deploying |
| SYSTEM.md | Detailed owner-facing description of production behavior |
| HANDOFF-CODEX.md | Current maintainer handoff and release discipline |
| INBOUND-NEWS-FLOW.md | Every inbound lane, NBN-owned clocks and the Node API boundary |
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

The runtime orientation is prompts/orientation-brief-v2.md, text after its separator.
Plan 0060 updates documentation metadata, not loaded editorial text. The charter
prompts/wire_voice.md remains loaded by legacy paths; its historical heading is not v2
authority. It is intentionally not rewritten during a non-editorial sprint.

## Evaluation, tuning and history

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
publishing rails are unchanged. The dated visual PDF predates these incremental intake details;
SYSTEM.md and INBOUND-NEWS-FLOW.md contain the current contract.
