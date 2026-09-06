# Plan 0059 — research routing and writing reinforcement

> Status reviewed 2026-09-06: Historical design/evaluation record. Preserve dated findings; later releases may supersede the proposal. For the current system, see [DOCUMENTATION.md](DOCUMENTATION.md) and [SYSTEM.md](SYSTEM.md).

Final review decision: **approved narrower rollout** after all nine diagnostic runs. Ship craft
examples, audit correction, and Background provenance repair. Do not ship experimental routing
instructions/tool description or turn-budget fields: no replay demonstrated native selection.
See `SPRINT-0059-FINDINGS.md`. The original plan below is retained as the experiment record.

Deployment complete: `0b2e8e3`, Railway `f17b6c71-b5f6-4e1c-a43d-f3b72d82ade6` SUCCESS.
409 clean tests, deployed isolated regression smoke, health/dashboard and DB integrity passed.
Autopost OFF; the existing audit is ACTIVE. No Typefully content was changed in this sprint.

2026-09-06. Owner approved the scope; independent lead coder approved the plan before implementation.
Review refinements: delegate early when a multi-step gap is apparent, before a second-turn
fetch can consume the last research opportunity; ordinary search failure does not disable
the independent native research route. Measure delegation, useful support, and editor outcome
separately. No extra architecture or budget requested.

After the initial six paired batches, the reviewer approved one bounded revision: distinguish
an unresolved verification gap from an editorial rejection, while preserving relevance/novelty
judgment. Initial v2.15 did not induce native use on the IMF case. The final v2.15.1 gets the
three predeclared follow-up batches (same targets, no forced native-first intervention).

## Objective and boundaries

Help the approved roster finish useful reporting with its existing tools and preserve its
improved writing. No model, effort, cadence, research-budget, source-standard, publication
policy, or architecture changes. Autopost stays OFF. No Typefully mutation in this sprint.

## Phase 1 — bounded research-routing guidance

Clarify the newsroom system prompt and the existing research tool description: for a
worthwhile, not-already-covered candidate with a blocked or inadequate receipt, prefer one
focused native research assignment while a tool-using turn remains, rather than spending the
remaining opportunities repeating direct retrieval. If direct evidence already suffices,
write immediately; do not require a search, extra sources, or a minimum number of turns.
The researcher may still fail; preserve the unresolved objective, not unsupported certainty.

Keep the final forced dossier turn, existing one-assignment cap, timeout, and provenance rules.
Provider-reported extracts are source-specific paraphrases, never direct page captures, and
two wrappers of the same report are not independent corroboration. The newsroom retains
editorial judgment; no automatic delegation or new fallback loop.

## Phase 2 — writing examples and audit corrections

Add compact illustrative examples to the runtime orientation: ETF writing that stops after
the meaningful total/comparison/leader, and a CFTC opening that leads with the significance
for CLARITY before the procedural detail. Clearly label examples as craft illustrations,
not current facts or a word-count/template requirement. Preserve attribution and uncertainty.
Bump the newsroom prompt version; no sentence-length gates or extra editor calls.

Correct the stale IMF duplicate conclusions in the local tuning and speed records. Preserve
historical measurements but explicitly supersede the claim that draft 10619385 already
contained the private-donations claim. Compare the reader-visible claims and current draft
text before future duplicate/miss conclusions. No event aliases or draft dispositions change.

## Separate technical repair — preparation provenance

The interrupted audit reproduced a bug: merged preparation Background verdicts are overwritten
as newsroom editorial drops at materialization, hiding SEND TO DESK. The already-tested local
repair preserves current-run, enforced, applied Background provenance using persisted state,
not a model reason prefix. Genuine editorial drops remain terminal. Cover all-Background and
mixed runs, including one-time promotion, with isolated DB tests. Do not rewrite historical
production rows or promote real candidates. Report this historical limitation explicitly.

## Validation and ship criteria

1. Independent lead coder reviews scope, implementation approach, and acceptance criteria.
2. Focused regression tests for routing/craft instructions and background provenance; full suite.
3. Reuse the historical replay runner without native-first injection or Typefully export.
   Run baseline and changed prompts over the same IMF blocked-source, ETF straightforward,
   and CFTC lede cases, in separate local databases. Use the same snapshot and settings;
   record live-retrieval and stochastic limitations. Do not cherry-pick reruns to obtain passes.
4. Compare chosen tools, research completion, editor outcomes, source provenance, copy, total
   latency, and per-seat spend. Expect selective native use on unresolved reporting, no blanket
   research on already-sufficient evidence. If the routing change does not demonstrate the
   intended behavior, diagnose and review a bounded revision before shipping; do not increase
   budgets or force output to pass the test. Cap this diagnostic at six initial batch executions
   and at most three targeted follow-ups; seek direction for a larger experiment.
5. Independent implementation/result review; resolve real defects without expanding scope.
6. Commit only sprint-owned changes. Back up production DB; deploy a clean tested archive.
   Smoke health, dashboard, roster, autopost OFF, prompt content, and isolated deployed
   background finalization. Do not call production promotion or publisher writes as smoke.
7. Record findings, caveats, deployment, rollback reference, and audit follow-up. The rolling
   audit remains active (or restore it if temporarily paused) and excludes REPLAY copies.

Rollback: redeploy the prior clean release if runtime smoke fails. For an editorial routing
regression, revert only this prompt change, retaining independently verified technical repairs.
