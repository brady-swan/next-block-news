# Audit continuation repair — September 8, 2026

Status: implemented and independently approved; 14 tests and four recorded-incident checks pass.
Same audit resumed at 21:31 UTC and saved settings verified. No NBN runtime change or deployment.

## Observed failure

Four scheduled turns switched to answering an already-answered user request immediately after
Codex context compaction: 14:35, 15:26, 20:07 and 21:00 UTC. The raw session log retains each
real heartbeat trigger; the replacement message history does not retain that trigger as a
message. The last ordinary user request is still visible. Repeated status checks/answers are
confirmed; this is not evidence that the Typefully-comment feature was rebuilt.

The earlier prompt cleanup is complete and is not being repeated. It removed stale assignments,
but its start-of-pass-only check did not protect resumption after compaction.

## Narrow implementation

1. Keep the existing audit paused temporarily, preserving its prompt, interval and target.
2. Add a read-only, standard-library local helper that identifies the latest actual turn in
   this task's session log. Return the turn ID, start, trigger identity/time, current user
   message if any, compaction time and completed/interrupted state. Read only a bounded tail;
   missing/ambiguous evidence stops continuation rather than falling back to an old request.
3. Add a short task-workspace AGENTS.md instruction to run that helper on entry and after
   compaction, before commentary, mutations or a final response. Keep the immutable starting
   trigger separate from later genuine user steering. Answer status questions/incorporate
   clarifications without automatically abandoning work; honor explicit stops or replacements.
   Historical user messages cannot become new assignments; standing authority still applies.
   This is agent guidance plus a diagnostic check, not an app-level enforcement hook.
4. Keep the latest verified turn/trigger receipt beside the existing editorial checkpoint.
   Completed user turns stay closed; unfinished repairs keep their own explicit status.
5. Update only the continuity portion of the recurring prompt/policy, test historical-shaped
   and actual recorded cases offline, verify saved automation text and resume the same audit.

No new daemon, model calls, scheduled task, production migration, editorial change or paid replay.
The editor-reference repair stays local and unfinished; do not build/deploy it in this task.
Independent review focuses on the local helper and continuation rules. Preserve unrelated work.

## Acceptance and limitations

- Heartbeat + compaction + old visible user request remains a heartbeat.
- A genuinely new user message during an audit is separately visible and honored without
  erasing the original trigger or automatically canceling authorized work.
- Completed/interrupted turns, wrong task, absent trigger and incomplete logs cannot authorize work.
- Repeated reads are identical and side-effect-free. No session-log writes or secret output.
- Verify the four recorded incidents and the current interactive turn without invoking models.
- Future live compaction still needs observation: offline checks do not prove the agent will
  always follow instructions. AGENTS.md loading follows the app's instruction-discovery behavior;
  the recurring prompt and checkpoint also point to the same check.

Rollback: pause the existing audit and revert only these local instructions/helper changes.
Do not restore the retired 30,000-character prompt or touch NBN runtime/data.

## Completed verification

- Independent reviewer approved the plan and final implementation. Review preserved the original
  trigger separately from user steering, and caught a clipped-input gap before release.
- All 14 `tests.test_audit_turn_context` tests pass, including earlier restrictions followed by
  a status question, full-input recovery, wrong task, closed turns and partial journals.
- Offline checks against the actual journal at all four compactions recovered the correct
  heartbeat turn, with no invented new user input. No models, drafts or production runs invoked.
- Live helper correctly identifies current user turn `01a082e1-dcd2-7221-887b-d934496c59c1`.
  CLI checks reject an older expected turn and a different task with exit status 2.
- Existing automation `audit-nbn-production` is ACTIVE; saved prompt exactly matches the
  canonical 6,722-character procedure. Target task and 15-minute schedule are unchanged.
- Workspace instruction installed at `/Users/brady/Documents/ChatGPT/Next Block News/AGENTS.md`.
  [Official AGENTS.md guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
  establishes instruction discovery, not a guarantee of reloading during an existing session.
  Actual instruction loading/compliance through a future live compaction remains an audit watch.
- Existing editor-reference edits, pending release, production code and Typefully content were
  not changed by this repair. Full NBN tests/deployment were intentionally not repeated.

The earlier issue was real; these checks establish a concrete mitigation, not proof that the
app's compaction behavior is fixed. On the next genuine audit trigger, verify its own turn,
resume the existing checkpoint once, and observe compliance without reopening this repair.

## First live entry follow-up — 21:48 UTC

Workspace AGENTS.md did load. The host recorded it as role=user with structured metadata
`content_item_kinds=["agents_md.instructions"]` immediately before the actual heartbeat.
The helper incorrectly treated that injected instruction document as a fresh owner request.
Full-input/raw-metadata inspection resolved the true trigger; no old request was answered.

Smallest correction, now implemented: exclude only messages wholly identified by that host metadata
as AGENTS instructions from trigger/steering classification. The instructions remain binding;
this is not a content-prefix filter. Untagged owner messages, including those mentioning
AGENTS.md, and mixed content kinds remain ordinary input. Four focused regression cases added;
all18tests pass. Independent final reviewer approved the six-line change and independently
ran the tests/diff check with no actionable findings. Local-only; no NBN runtime deployment.

Live verification: the actual21:48:40.690UTC heartbeat resolved correctly after the correction.
The same turn then compacted at21:54:57.387UTC. The required immediate guard invocation preserved
turn `01a082fe-a173-71d0-b040-439669efa70a`, the original heartbeat trigger and an empty set of
new user messages. The agent continued the pending final review/record rather than reopening
an older owner request. This is one successful live continuation observation, not proof that
every future host format or compaction behavior is covered.

Separately, the saved automation prompt changed after the prior exact-sync check. No update
call in this task explains the 21:38 modification. Preserve it pending provenance clarification
rather than silently replacing a potentially external/user change. This does not justify
rebuilding prompts, expanding scope or re-running completed NBN releases.

Fresh production pulse21:50:29.664UTC: healthy, autopostOFF, same v2.27 runtime, latest four runs
completed, no ambiguous/in-flight publisher mutations. No Typefully writes or automation
mutations in this follow-up. Full editorial coverage remains through13:50UTC, unchanged.
