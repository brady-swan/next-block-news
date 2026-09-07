# Explain evidence handoff at the dossier fields

September 7, 2026. Bounded prompt/tool-description tuning under AUDIT-AUTONOMY.md.
Status: implementation independently approved; releasing.

## Observed need

The 18:17 v2.19 run researched TFTC's Russian-gold/Hong-Kong lead and retained three native
source-specific paraphrases. The writer nevertheless cited only the original TFTC receipt
in its story's evidence_fetch_ids. Its reporting_note described broader corroboration, but
the editor received only that tweet and dropped the proposed post for lack of supporting
evidence and questionable macro relevance. The earlier 17:31 Lam plea dossier likewise retained
AP/CryptoTimes sources but cited only CoinDesk X, prompting a narrower human draft.

This is not a proven tool-sequencing defect. _register_native_sources runs before validation
and supports exact native URLs in the same dossier. Its focused existing test passed. The
writer's prose guidance already explains the handoff, but selected_fetch_id, evidence_fetch_ids,
reporting_note and native_sources have no field-level descriptions. The author can mistake a
run-level retained source list or a prose note for evidence attached to a particular story.

Multiple summaries of the same FT reporting are not independent corroboration. Fixing the
handoff must not upgrade them, guarantee gold-story publication, or require a primary source.

## Small proposed change

Add descriptions to the existing dossier fields, without changing accepted values or validation:

- selected_fetch_id: the best reader-facing source, distinct from the complete relevant evidence.
- evidence_fetch_ids: the inspected sources supporting or qualifying this story; these are what
  the editor receives. Include relevant new native sources by exact URL when submitted in the
  same dossier. Exclude unrelated sources; a chosen reader link is not the whole evidence list.
- native_sources: retaining extracts here alone does not associate them with a story; cite their
  exact URLs in that story's evidence_fetch_ids (and selected_fetch_id if chosen for readers).
- reporting_note: short context only, not evidence; sources claimed as support must be in the
  story's evidence list.

Update prompt version and current prompt docs. Add a focused offline end-to-end contract test
that a same-response native URL referenced as evidence reaches the editor while the selected
reader link stays unchanged, and an unrelated retained source stays out. Assert descriptions
are present on active schema fields. Existing unobserved-URL rejection remains intact.

No source auto-attachment, semantic matching, new gates, mandatory research, extra model turn,
changed budgets/cadence/roster, memory architecture or Typefully mutation. No broad prompt rewrite.
This adds only brief input text to existing calls. Static tests show contract availability, not
improved writer choices. Subsequent natural dossiers must establish behavior change.

Independent review before implementation; full tests, clean release, read-only smoke, resume
the same audit. Preserve owner work and keep autopost OFF. Rollback is runtime 1d49c2a, with no
database restore. Audit cutoff for editorial backfill is 18:42:17.098 UTC.

## Independent review

Reviewer approved the field-level clarification as more targeted than another prose block.
Two refinements accepted: selected_fetch_id explicitly belongs in evidence_fetch_ids (existing
validator contract), and the dossier native_sources schema is copied rather than mutating the
shared reporter.SOURCE_SCHEMA used by record_sources. No additional attachment logic requested.

Implementation review approved deployment without blockers; reviewer independently passed 76
focused tests. Main-agent full working-tree suite passed **521 tests**. Two unrelated evaluator
tests and other owner work remain outside the clean release. Version is v2.21-evidence-handoff.
