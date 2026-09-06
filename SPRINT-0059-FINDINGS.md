# Sprint 0059 — selective research and craft

2026-09-06. Independently approved narrowed release is deployed and smoke-tested.

## Bottom line

Ship the craft examples, audit correction, and Background-control repair. **Do not ship the
experimental research-routing prompts:** all nine runs used zero native assignments. The
reviewer independently inspected the traces and agreed to stop the experiment at its declared
limit, not force calls or expand budgets. Native route selection remains unresolved.

The final CFTC editor output did bring the CLARITY consequence forward. ETF copy stayed clean.
This is useful reinforcement evidence, not proof that writing or selection is now solved.

## Scope

The independent lead coder approved the plan and reviewed the initial implementation. Keep
the approved roster, effort, 15-minute cadence, one research assignment, existing time/turn
budgets, evidence provenance, and publication standards. Autopost remains OFF. Replays use
isolated databases and a captured publisher; no Typefully export or content mutations.

The experimental newsroom guidance and two turn-budget fields were removed before deployment.
The shipped prompt is `editorial-core-v2.15.2-craft`; operational research instructions/tool
descriptions remain identical to the prior release. Changes are historical craft examples,
audit corrections, and a separate preparation-provenance repair.

## What the audit repair fixes

Preparation Background items were correctly saved as `desk_prep/background`, then overwritten
as `newsdesk/editorial_drop` when the session's merged audit verdicts materialized. That hid
the owner's one-time SEND TO DESK button. This happened in both all-Background and mixed runs.
The regression test failed in both cases before the repair and passed afterward.

The repair preserves current-run enforced/applied preparation provenance, using persisted
state rather than model-authored reason text. Actual newsroom drops remain terminal. Tests
check the button and one-time promotion against isolated databases, never production items.
Existing historical rows are not rewritten; previously mislabeled items are not retroactively
made promotable by this release.

## Audit correction

The earlier claim that the IMF/private-donations draft necessarily duplicated 10619385 was
overconfident. The fresh reads recorded in the roster replay showed different reader-visible
claims: reserve-versus-Chivo ownership denial versus private-donation funding. Local tuning
and speed ledgers now explicitly supersede the old conclusion while retaining historical
timings. Neither content nor canonical aliases were changed. Future audits must compare the
actual latest claims instead of inheriting an old model grouping or audit note as truth.

## Replay method and limitations

Same historical snapshot and three batch targets as the prior replay: IMF, ETF, CFTC. Baseline
is clean commit `bd64248` (runtime prompt v2.14.1); changed runs use v2.15. No native-first
injection. Each batch starts in a separate local database. Live source fetching and model
sampling vary; this is a diagnostic comparison, not a causal benchmark or recall score.

The ETF/CFTC examples deliberately teach those known writing lessons, so performance on them
is an instruction-following check, not evidence of generalization to unseen stories. Raw
inputs, outputs, provider traces, usage, and decisions are retained in `.model-eval/0059-*`.

## Initial observation

The first routing wording was not enough: the IMF changed run submitted a drop with no native
assignment because its receipt lacked primary support. The baseline searched/fetched, hit
CoinDesk 429, and was rejected by the editor. Neither is a successful research completion.
The reviewer approved a bounded clarification distinguishing missing support from a completed
editorial rejection, conditioned on genuine news value and novelty. No forced native call,
relaxed standard, or extra research budget is justified by that failure.

## Complete comparison

Times include preparation, live retrieval, writing, editor, and isolated materialization where
applicable. They are batch wall times, not peer-to-NBN publication latency. No rows enter the
production speed ledger as genuine deliveries.

| Variant | Batch | Seconds | Model cost | Result |
| --- | --- | ---: | ---: | --- |
| Baseline v2.14.1 | IMF | 56.19 | $0.0701 | Search/fetch; CoinDesk blocked; editor dropped IMF |
| Baseline v2.14.1 | ETF | 94.61 | $0.0731 | ETF draft; no native research |
| Baseline v2.14.1 | CFTC | 79.18 | $0.0627 | Editor revised; attempted prior-draft replacement blocked by isolation |
| First wording v2.15 | IMF | 27.57 | $0.0218 | Immediate drop, missing support; no research |
| First wording v2.15 | ETF | 70.06 | $0.0643 | ETF draft; direct retrieval, no native |
| First wording v2.15 | CFTC | 80.81 | $0.0623 | Editor accepted; replacement blocked by isolation; lede still procedural |
| Revised wording v2.15.1 | IMF | 61.33 | $0.0586 | IMF dropped on prior-day/routine-compliance judgment; related CLARITY revision blocked by isolation |
| Revised wording v2.15.1 | ETF | 67.13 | $0.0804 | ETF + IMF drafts; direct BeInCrypto retrieval succeeded; still no native |
| Revised wording v2.15.1 | CFTC | 60.34 | $0.0573 | Distinct draft; editor brought CLARITY consequence forward |

Total: **39 model calls, $0.5506**. Preparation $0.0161; newsroom $0.3087; editor $0.2110;
RSS intake $0.0148. xAI uses reported billing; other seats use token-rate estimates. No native
search charges occurred; SerpAPI subscription/credits and hosting are not included.

In the revised ETF batch, the newsroom still repeated direct CoinDesk retrieval around 429
responses instead of assigning the available native researcher. The IMF output in that batch
is not a native-routing success: its ordinary secondary article happened to become fetchable.
Live retrieval and preparation sampling changed between runs. The revised IMF batch also
advanced five prepared cards rather than three, so attribution to one prompt sentence would
be especially unwarranted.

### Writing and continuity observations

ETF remained a two-sentence post in all variants. The final CFTC output opened:

> NEW: Four empty CFTC seats remain a sticking point in CLARITY Act talks.
>
> The White House has vetted candidates to fill them, three sources told CNBC.

It retained nomination uncertainty, then noted the agency's sole commissioner. Earlier variants
still buried the consequence. Do not infer that one improved replay guarantees later compliance.

CFTC lifecycle judgments varied between replacing an existing related CLARITY draft and treating
commissioner vetting as distinct coverage. The replay correctly blocked real replacement writes;
that technical success does not establish that every model-proposed merge was editorially right.
Likewise, an extra IMF draft is not inherently a throughput improvement. Audit exact claims.

## Decision and next question

The independent reviewer approved shipping only the independently justified changes. More
prompt text did not reliably cause delegation, so the experiment does not justify adding that
text to production. The prior controlled native-first replay still shows the research seat can
retrieve useful support; selecting that route is a separate unresolved problem.

A future experiment should separate newsworthiness/novelty judgment from route selection with
a fixed, clearly worthwhile unresolved reporting question, then evaluate the tool choice. This
is a recommendation for discussion, not an implemented automatic or mandatory research stage.

Raw artifacts: `.model-eval/0059-baseline`, `0059-changed`, and `0059-final`.
The final experimental newsroom source and orientation are also saved in `0059-final` to keep
the non-shipped wording distinct from the release. All nine results are retained; no cherry-picked
reruns and no Typefully export.

## Release verification

- Independent lead coder approved the original plan, reviewed the implementation, and approved
  the narrowed shipment after inspecting the failed routing traces and the report.
- Runtime commit: `0b2e8e3` (pushed). Clean archive: `/tmp/nbn-0059-release.RLEZwx`.
- Tests: **411 working-tree / 409 clean-release tests passed**. Two pre-existing dirty eval
  tests were excluded from the clean archive along with unrelated eval work.
- Backup: `/data/backups/nbn-pre-source-policy-20260906T052938Z.db`.
- Deployment: `f17b6c71-b5f6-4e1c-a43d-f3b72d82ade6`, **SUCCESS**.
- Live smoke: loaded `editorial-core-v2.15.2-craft`, authenticated dashboard showing the new
  examples, production and backup SQLite integrity `ok`, healthy worker with a completed cycle
  and no last error. All roster/effort, three-turn, one-assignment, 900-second settings unchanged.
- Two focused tests also passed inside the deployed container, exercising mixed/all-Background
  finalization and one-time promotion in temporary databases plus the shipped craft contract.
  No production promotion, publisher mutation, or model call was performed by these smoke tests.
- Autopost verified OFF. Rolling audit restored ACTIVE at its existing 15-minute interval,
  with the narrowed-release findings and corrected IMF interpretation included in its instructions.
- No new natural production draft was required to declare the mechanical rollout healthy;
  sustained writing quality and research behavior remain ongoing audit questions.
- Rollback reference: prior runtime `8984e21`, deployment
  `ff64b138-128e-427c-8183-f791e57fa573` (clean HEAD baseline includes later docs at `bd64248`).
