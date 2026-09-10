# Sprint0075 — source handoff and replacement handling

Status: **deployed and smoked**, September 9, 2026 (September10 UTC).

## Changes

- Immediate original-speaker URLs precede outbound links during bounded prepared fetch;
  compact previews preserve author/relation. No source-tier policy change.
- Native search plus dossier in one response can use the existing single correction slot
  to retain relevant source-specific extracts. Research is closed. Copy, identity, membership,
  visuals and continuity cannot be rewritten through this completion. No extra turn ceiling.
- Explicit Editor approval is required for an actual draft replacement. Veto/incomplete
  review preserves both the remote draft and the proposed target's memory. Candidate-local
  diagnostics distinguish rejection from missing review; no automatic new post/key is created.
- Ordinary creates and published-base updates without an open update draft are unchanged.
  Preserves prior audit fixes. Luna/roster/budgets/cadence/autopost OFF unchanged.

## Review and checks

Independent plan review approved by prep_merge_eval_lead. Focused offline tests cover actual
controller mutation calls, alias/notebook/artifact-family state, visual queue avoidance,
positive replacement approval, normal published-base creates, native completion and fallback,
identity-preserving source additions, actor visibility and selected prepared URL.

Independent code review identified and verified repairs for malformed mixed-tool completion,
pre-Editor early-exit item identity, and structurally valid but research-invalid replacement
attempts. Reviewer independently passed44focused tests and a real-validator/controller
reproduction; that regression is now in the permanent suite. Initial clean-tree full suite:
705 tests PASS. Final clean-tree suite after all review refinements: **705 tests PASS**,
37.876 seconds. No network/publisher calls in tests. Real-validator failed-receipt regression
is included, along with malformed mixed-tool completion and visual-replacement rejection.

No paid historical replay, manual Typefully content mutation, new API key or schema migration.
Runtime code/tests can prove routing and state invariants, not future editorial judgment.

## Audit watch points

Compare actual speaker/source attribution, not only whether an original URL was found.
Track native_evidence_handoff requests, completions, missing capacity and actual useful added
receipts; unused citations are not failures and source paraphrases are not page captures.
Watch bounded completion cost/latency; do not add research rituals. Inspect replacement
approval/veto and retry outcomes: distinct related events must not overwrite an existing draft
or become a persisted alias merely because a Writer proposed one. Review-incomplete is not
evidence of wrong identity. Confirm ordinary creates and legitimate replacements still flow.

## Release

Pre-deployment online backup: `/data/backups/nbn-pre-source-policy-20260910T014919Z.db`,
integrity checked by the backup script. Audit paused for deployment. Effective production
settings verified: Grok4.3 medium Writer, Grok4.5 medium Editor, Luna prep, six responses,
360-second lifecycle, autopost OFF.

Release commit **44fcea8**, pushed to origin/main. Clean archive deployed explicitly to
next-block-news production (one replica, existing `/data` volume), Railway deployment
`5c731233-7d2b-4a53-a700-665023d047f0`, SUCCESS, created2026-09-10T01:50:32.474Z.

Smoke at epoch1789005141.193: health, Desk, Intake, Outputs, System and workspace JSON all200.
Public health also200. Two natural worker cycles completed; last error null and no held lease.
Exact hashes of all five changed runtime modules match local44fcea8. Prior writer_continuity
hash9bf80a1b03e3d8c1331037774111c1ff337bc3c51484c3c8cc5a2f5272219596 unchanged.
104confirmed/17definite-failure publisher mutations, zero pending/ambiguous. Models/budgets and
autopost OFF unchanged. No manual Typefully mutation or forced paid newsroom replay.

Smoke limitation: no new Writer session had yet run on0075. The last three newsroom attempts
were **pre-deployment v2.36 initial_context_overflow** deferrals, distinct from healthy intake
cycles. These are not a0075 regression or successful newsroom smoke; handed to the resumed
audit for current packet diagnosis, without rerunning completed packet experiments. Field
attribution/evidence/replacement quality remains an organic-run audit watch, not a test claim.

The same15-minute audit automation was restored ACTIVE in the dedicated NBN Audit task with
specific source-handoff/replacement outcome and cost watches; existing autonomy is preserved.
Rollback is code-only to b8924a0 if needed; no schema or historical-data reversal is required.
