# 0076 — Codex reporter pilot

Owner approved September 10, 2026: run the independent-review/build/deploy/smoke
playbook on the Codex newsroom pilot and its two-way communication addendum.
Full owner-facing draft: `codex-newsroom-pilot-plan-v1.md` in the NBN task workspace.

## Operating contract

- Astra medium / Standard through Codex, using a dedicated Railway-host ChatGPT
  login. No API fallback or existing Haiku/Luna/Grok editorial seats.
- One reporter owns selection, research, writing, visuals and self-review.
- Existing NBN backend owns SQLite, raw intake, evidence, Typefully delivery and
  the Desk. Explicit infrastructure-only mode; no legacy retries/output execution.
- Separate reporter service, persisted exact session and agenda, five-minute idle
  checks without empty model calls, one active turn, explicit two-hour pilot cutoff.
- Draft creation only. No autopost, scheduling, existing-draft replacement/deletion,
  deployment authority for the reporter, or automatic audit/old-engine restart.
- Two-way messages have durable IDs, server-assigned sender identity, reply-to,
  delivered turn and acknowledgement. Ordinary messages enter at a safe boundary;
  pause/cutoff is immediate mechanical control. No automatic desktop-task wakeup.
- Retain original-source tools, browser/PDF/image inspection, chart rendering,
  memory and approved audience/writing guidance. Optional nomic keyword fallback.

## Independent review — approved with bounded changes

Reviewer: `codex_pilot_lead_review`, September 10. Phase 1 may proceed. Authentication
alone does not authorize live drafts; all exit checks below must pass first.

1. Pin SDK/runtime and prove Astra/medium/Standard after restart/resume, without
   inherited API credentials/Fast setting or silent replacement sessions.
2. Prove sandbox enforcement on Railway, including denied credential reads and
   supervisor/config writes. A private volume alone is not a sandbox. Stop if the
   host cannot enforce the required policy; do not silently disable it.
3. Prove real browser navigation, screenshot/image inspection and PDF handling.
   Keep the spike read-only; no Typefully writes or old-engine startup.
4. Split execution from reconciliation: `publisher.reconcile_mutations` currently
   runs pending visual jobs, `_cycle_locked` runs visual choices and triage, and
   `_lease_run` runs scheduled briefing/audit. Quarantine retained legacy jobs.
5. Remove eager old-model client dependency from infrastructure startup/tools.
   Test without old provider credentials and with legacy calls forced to fail.
6. Add caller-stable submission ID + payload hash above the current outbox. Its
   random mutation IDs do not prevent a replay after successful confirmation.
   Atomically enforce create-only/open-draft/ambiguous-state protections.
7. Backend rechecks active shift, cutoff and lease generation immediately before
   remote submission, including after slow image preparation. No stale-worker POST.
8. Preserve exact body/reply/media/alt confirmation and inspected asset binding,
   recording truthful Codex self-review rather than fictitious editor approval.
9. Idempotently recognize the eight morning experiment outputs and synchronize
   current draft contents. Raw intake bypasses legacy status/ranking exclusions.
10. Add genuine Codex shift projections to the Desk; do not fabricate cycle IDs,
    old editorial stages, or API-dollar charges for subscription allowance.

## Phases

1. Isolated worker/runtime/auth/browser compatibility spike on Railway.
2. Thin backend adapter, supervisor/continuity/messages, guarded draft delivery and
   portable context; offline tests and independent implementation review.
3. Deploy disabled; restore only tested infrastructure mode, then end-to-end smoke.
4. Fixed two-hour draft-only pilot, finite retrospective, owner review of extension.

The old system and audit remain paused during construction. At pilot cutoff the
reporter stops; intake/read-only publication sync/Desk can remain for review.
Rollback stops the new reporter without automatically enabling the old pipeline.

## Current progress

- Plan review: complete, approved with the bounded requirements above.
- Phase 1: blocked on the tested Railway host's sandbox compatibility. The isolated
  health-only image deployed successfully and SDK/runtime metadata worked, but both
  normal sandbox setup and the unchanged-policy compatibility probe failed before
  authentication. No account login or inference took place. See
  `CODEX-REPORTER-SPIKE-FINDINGS.md` for evidence and the next hosting decision.
- Integration, live pilot and Typefully writes: not started.
- Independent checkpoint review: approved as a stopped partial spike. Before future
  auth, bind the sandbox pass to runtime/configuration and test the active auth-side
  and workspace configuration boundaries; see the findings' follow-up requirements.
