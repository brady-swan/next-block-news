# Plan 0064 — finish the reporting, carry it into editing

Status: independent lead approved implementation on September 7. Owner delegated this sprint's priorities,
plan/review/implementation/deployment/smoke cycle on September 7, 2026.

## Outcome and evidence

Make the current reporter-writer use its existing tools and memory more effectively, and make
its handoff to the editor faithful. No new seat, source vendor, worker, cadence or larger budget.

The overnight audit found earlier Lummis and Buterin originals in skipped intake, a stale
Strategy purchase repackaged as NEW, useful native research omitted from story evidence, and
text-only completion loops using most of the six-response allowance. A missing UPDATE prefix
also held otherwise reviewable stories before the editor. Liquid demonstrated why unpublished
draft copy must not be treated as truth; the separate coverage-card ledes fix is already live.

## 1. Reporting instructions and a meaningful memory index

- Give writer and preparation concise, specific guidance: a consequential statement/proposal
  can itself be news, even when an earlier pass called it opinion. For a reporting tip quoting
  a named person, consider recent-intake lookup for the original; for an apparent repeat or
  contradictory new development, check the relevant notebook and confirmed copy. Do not require
  a lookup for every lead or force primary-only verification.
- Teach the writer/editor to compare the same actor, event date, reporting period and transaction
  direction. An unpublished draft or previous editorial decision is not factual evidence. A
  weekly number cannot be disproved by a partial month; a change output is not a repayment.
- Reinforce approved scope: useful factual Bitcoin data need not set a record, and a material
  monetary/inflation development need not prove an immediate Bitcoin flow. Avoid routine macro
  ticks, trading advice, routine treasury buys and software-release coverage.
- Keep the 30-day catalog small and paginated, but show the canonical event key explicitly and
  a short confirmed-output lede/date where available. Avoid replacing useful event identity with
  an uninformative account-only headline. The existing 14 KiB catalog/64 KiB packet caps remain.
  This is context, never a new duplicate gate or automated semantic matching system.

Diagnostic refinement: the first one-step prompt probes still rejected a recovery tip as
covered and a legislative warning as out of scope. Clarify the existing orientation's distinction
between empty political advocacy and a material change in legislation's viability/timing/scope;
put a short reminder in the delivered run assignment that promised and completed actions differ,
and worthwhile unresolved leads deserve research or deferral. No forced acceptance or research
for slogans. Retest once; record remaining misses rather than extending the sprint indefinitely.

## 2. A faithful, story-specific editor handoff

- Add one optional bounded `reporting_note` to each writer story (nullable in the tool schema,
  backwards-compatible when absent in old dossiers). It summarizes origin/freshness checked,
  disagreements and remaining limitations in at most 800 characters, not a second research essay.
  Pass it as clearly untrusted writer context to the editor and retain it with the story attempt.
  It cannot become receipt evidence, a verdict, or an instruction.
- Explicitly ask the writer to include every useful inspected source supporting or qualifying
  that story, up to the existing eight-reference cap. Select the best link for readers separately
  from the complete evidence list. Native URLs alone/snippets remain pointers; retain actual
  source-specific extracts using the existing protocol. Do not attach unrelated run receipts.
- Preserve source identity when the editor deduplicates receipt bodies: equal text from different
  URLs must not silently inherit another outlet's URL, authorship or provenance. Deduplicate only
  the same source and retrieval provenance, with identical content.
- Verify selected and additional evidence reach the actual editor payload, including conflicting
  sources. This is a prompt-led improvement plus a concrete provenance repair, not an extra
  verification gate or research turn.

## 3. Stop empty completion loops without ending useful research

- After a text-only response, distinguish native research activity from a plain completion.
  Real native tool activity may continue under the existing bounds. If no custom tool and no
  native activity occurred, request the dossier directly on the next response instead of
  repeatedly offering the full research menu.
- Keep the same conversation/provider output, including reasoning and native results. Never
  replay a paid research round or trim opaque provider state to fit. Preserve the existing
  failure finalization, one receipt-reference repair and omitted-candidate deferral behavior.
- Record why finalization was requested in existing run observations for audit inspection.
  No new dashboard section or monitoring service.
  Detect native work from this response's observed native operations OR positive usage, not
  cumulative URLs/counters. Preserve progress when billing counters explicitly report zero.

## 4. Treat a missing UPDATE prefix as repairable presentation

- Only after code has resolved an existing reader-visible base and the writer explicitly chose
  `material_update`, normalize a missing/wrong NEW prefix to `UPDATE:` before independent review.
  Record before/after as a mechanical presentation correction. Do not infer materiality or change
  event identity. Keep no-visible-base, same-event, multiple-draft and mutation protections.
- Ensure the final non-drop text retains the required UPDATE prefix too, including editor
  fallback. Do not manufacture a new fact or relabel ordinary open-draft replacements as updates.
  Normalize nonempty copy only, update fallback's canonical candidate, and re-run final rails
  after normalization. Receipt deduplication includes URL, body and authorship/date/limitation
  provenance, not just a shared content fingerprint. These are lead-review acceptance details.

## Verification and release

1. Independent lead reviews this plan; resolve substantive objections before runtime edits.
2. Pause the existing rolling audit during implementation; keep autopost OFF.
3. Deterministic regression tests: catalog pagination/caps and old confirmed vs new draft;
   multi-source handoff and same-text/different-source identity; plain completion vs native search;
   required UPDATE normalization vs absent base and protected outputs. Existing identity, delivery,
   source provenance, self-report isolation, budget and network-blocked suites remain green.
4. Run a small isolated, metered diagnostic against captured cases if feasible (maximum $5,
   no production DB mutation or Typefully export). Compare prompts on originals, stale memory,
   source handoff and calibrated judgment; distinguish actual model outcomes from unit fixtures.
   Tests cannot establish editorial quality; do not claim all misses solved from green tests.
5. Independent implementation review, clean archive tests, verified production backup, existing
   single-replica Railway deploy, read-only HTTP/config/runtime smoke, then a naturally nonempty
   run. Do not force a paid production cycle for the smoke.
6. Update current docs, record release evidence and remaining weaknesses, update/restore the
   existing rolling audit. Watch original-source use, honest evidence handoff, empty finalization
   reduction, useful content/speed/cost, repetition and over-cautious choices—not tool counts alone.

## Boundaries

Preserve owner work and unrelated dirty evaluation files. No manual Typefully changes, enabling
autopost, ambiguous delivery recovery, credential changes, Node/Perception configuration, DB
destruction, PDF/browser acquisition, larger model/retrieval budgets, or new publication quotas.
The previously identified Liquid/Strategy drafts remain owner review items, not sprint mutations.
Rollback uses the prior verified runtime (`81eb8d5`) if a runtime regression appears; additive
optional dossier/catalog fields require no destructive schema migration.

## Smoke-discovered technical follow-up

The first natural run completed reporting/editing and replaced the existing Liquid update draft,
then exposed an older variable-shadowing bug in legacy decision recording. The independent lead
approved renaming only the existing-update branch's `pending` local to `pending_update_draft`.
Regression coverage must use real decision storage and mutation finalization for a successful
replacement, plus stale-base suppression. No production-data rewrite or delivery retry. See the
findings report for exact run/cost/release evidence and remaining source-selection limitations.
