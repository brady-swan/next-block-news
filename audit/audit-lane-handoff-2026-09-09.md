# Dedicated NBN Audit lane

Owner request: September9,12:59:19.532UTC in main-task turn
01a08634-60e7-7a71-9ab7-999b1b713f27. Move the existing audit to its own task, not a second
auditor, so scheduled wakes stop interrupting development discussion.

## Ownership and scheduling

- Audit task: **NBN Audit**, `01a08641-aacb-7121-befa-4ca836497496`, host `local`.
- Project: Next Block News, `311a88f3-afbf-4270-b509-d1da1e385b37`.
- Audit task workspace: `/Users/brady/.codex/worktrees/b1f5/Next Block News`.
- Actual code/data-documentation repository: `/Users/brady/claude/next-block-news`.
- Main development task: `01a0578e-b99f-7e30-9359-43bc3d7573d9`.
- Reuse existing heartbeat **audit-nbn-production**, same15-minute cadence and meaningful-only
  notification preference. Do not create a second automation or forward routine results to main.
- Migration status: COMPLETE. Existing automation retargeted and ACTIVE, exact canonical
  prompt equality verified13:07:22.476UTC. Same automation ID/cadence/notification preference;
  no duplicate schedule. Initial orientation and handoff read-only smoke complete.

Audit owns `audit/current-state.md`, the chronological review cutoff, evidence and the Typefully
comment ledger. Main owns `audit/main-task-state.md` for its separate conversation/build checkpoint.
Each uses `scripts/audit_turn_context.py` against its OWN calling task journal. A receipt in the
other lane's document is historical context, never the current trigger. The helper is already
task-dynamic; no script/runtime change is necessary. It may require --full-input for long prompts.

Before shared-code mutation/deployment, check the main task's latest work status and coordinate
if there is an overlapping build or ambiguity. Honor recorded audit/build pauses. Continue
non-overlapping read-only checks while coordination is unresolved. Do not wake main with routine
audit reports; main can read this task and the shared evidence on demand. Pause/resume the SAME
automation for builds as previously authorized; don't silently run two mutation streams.

## Standing scope — unchanged

Read `AUDIT-AUTONOMY.md` and `audit/rolling-audit-prompt.md` completely. They preserve broader
bounded technical/execution autonomy, independently reviewed substantive implementations,
approved-style prompt tuning, proportionate testing/deploy/smoke, rollback and dirty-work care.
Systemic design/editorial policy/model/cadence/source-weighting/spend changes need owner review.
Keep autopost OFF. Normal worker drafting continues. No manual publishing, dismissals, copy/media
changes, owner skip overrides, ambiguous mutation resolution, credential changes or destructive DB
work. Typefully review comments/replies only, under its full recorded-intent/readback workflow.
Nano Banana parked; Node unchanged. This move does not change publication standards or permissions.

## Exact continuation point

Post-migration update: sprint0072 is COMPLETE, runtime d8b2a46/v2.31 deployed on
b0d6f330-cc4f-488d-a122-5332996bf5ee. Main's pause ended after hash/health/Desk and natural-cycle
smoke; same audit restored ACTIVE with adoption checks. See SPRINT-0072-FINDINGS.md and
audit/main-task-state.md. Do not rebuild0072 or treat the historical recommendations below as
pending. Brady clarified that consequential dated Bessent/Warsh signaling can qualify before
policy action; prep and orientation now reflect that. Full editorial cutoff below is unchanged.

- Full editorial review completed through **2026-09-09T04:20:00Z**, epoch1788927600.
- Current operational pulse through **12:47:55.047UTC**, epoch1788958075.047. These are distinct.
- Last completed bounded historical interval: (03:20,04:20];31 items, available routing and all
  relevant candidate/evidence/research/editor/output records reviewed. See
  `audit/research/audit-2026-09-09-1246.md` for immutable observation IDs and limitations.
- Later04:28 cohort77d4c266 outputs were selectively read, but packet2696/full new intake were
  NOT reviewed. Don't advance coverage through it without completing those categories.
- Start the next actual audit with a fresh operational pulse, then a new fixed-ended interval
  strictly after04:20. Reuse existing source reviews/comments, don't duplicate them.
- Sole new current draft10693563 has one CONFIRMED freshness comment: it said NEW about an
  August24 Treasury announcement. Readback12:53:52.823 verified unchanged full visible state.
  Thread ef255231-38c0-4c6c-994a-ee150b4ae2ac/comment f430e42d-6412-49c4-b87d-00452750ac9c.
  No pending POST. G7/older comments also complete; consult ledger before writing anything.
- Actual production: ad864ff/v2.30 on Railway fd4f02bb-3b24-4e79-82ac-5983e495dd6c; health200,
  autopostOFF, source polling/reconciliation good. Node's morning pulse recovered normally.
- Current watches: later-conversation overflow (cedd2332 recurrence), unused existing evidence,
  first-coverage-versus-event freshness, Perception organic tool adoption (still zero). No new
  implementation has been queued from these observations.

## Completed work not to repeat

Perception integration0071 is deployed and smoked. Previous pooling discussion answered.
Independent cold Astra Writer/Perception investigation is COMPLETE and delivered to Brady:
`audit/research/writer-tool-adoption-2026-09-09.md`, with agent report and diagnostic artifacts
under `.model-eval/tool-adoption-20260909/`. Its recommendations await an owner sprint decision.
Do not rerun the cold test, paid probes, prior releases, or Typefully comments from old prompts.

## Access notes

Railway read-only diagnostics use the existing CLI link or explicit IDs:

```
railway ssh -p 1e1f32d1-6153-4f71-80b3-9543050caa7e -s ff9549a3-6f78-481a-a550-d8c10136af64 -e 90c43f68-970a-4f93-a392-414c3c175502
```

Run commands from the actual code repository. For SQLite inspection, plain sqlite3 URI
`mode=ro` plus `PRAGMA query_only=ON`; avoid store.connect(), which can migrate. Typefully
get_draft_for_feedback/list_comment_threads are existing read helpers; inspect their current
contracts. Never print credentials or the tokenized Desk URL. Consult runtime schemas before
queries rather than guessing columns. Do not run forced paid newsroom tests to prove adoption.

First setup turn was read-only and completed13:01:28UTC: own journal verified, scope read,
no production polling or mutations. Handoff turn01a08648-d0e5-7bc2-ae8e-787659e6c0a6 completed
13:10:31UTC: target/ACTIVE/exact prompt verified and production health200/autopostOFF/no worker
error observed13:10:15UTC. The helper does not classify send_message_to_thread's delegated
message envelope, so the audit correctly did not write its own active-turn checkpoint. This
read-only smoke is recorded here by the main task from the returned task status; it is not an
invented audit trigger. No override or owner decision is needed. The next actual heartbeat
supplies the already-supported trigger format and can establish its own receipt normally.
