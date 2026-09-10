# Sprint0075 — source handoff and replacement handling

Status: independent implementation review approved; final release verification in progress.

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
360-second lifecycle, autopost OFF. Deployment/smoke evidence follows after release.
