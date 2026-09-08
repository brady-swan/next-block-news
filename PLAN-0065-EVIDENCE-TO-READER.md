# Plan 0065 — evidence to reader

September 7, 2026. Owner approved the afternoon follow-through package and requested the
independent lead-coder playbook. Status: plan and implementation independently approved;
536 working-tree tests pass; clean release/deployment verification in progress.

## Objective and evidence

Make completed reporting reliably useful to the editor and next writer, and improve the
reader-facing selection of detail. Keep the existing combined Grok writer/researcher and
independent editor. The afternoon demonstrated:

- OpenSats: the writer read useful original blog context but cited only the X totals; the
  editor never received the blog. Other runs cited an unrelated receipt or omitted native
  extracts. V2.21 field descriptions alone did not consistently fix this.
- Bitcoin Magazine: `.td-post-content` was not recognized, so navigation consumed the
  24-link allowance before transaction/researcher links in the article body.
- Storylines: a writer's summary and intended `publish` disposition survive an editor drop
  without the final caveat beside them. Exact notebooks do record the drop. No harmful later
  publication from that inconsistency has been demonstrated.
- Liquid: correct same-draft replacement removed a useful pause/peg-in warning in favor of
  newer forensic detail. Galaxy: a useful finding became an overloaded, inconsistent count.
- OpenSats and the owner-corrected Lam story: fresh tips can recirculate older announcements.

Success means improved evidence availability, honest memory state and better natural output,
not more tool calls, stricter verification or an automatic publish quota.

## Phase 1 — bounded editor access to reporting already done

Keep the writer's explicit per-story evidence and selected reader link as the primary handoff.
Add a small separately labeled **unassigned run research** appendix to the existing batch editor
request. It contains eligible fetched/registered receipts the writer did not associate with a
surviving story, not raw search snippets, invented URLs, failed fetches or model self-reports.

- Reuse the same source-specific serialization and provenance as cited evidence. Direct text,
  native paraphrases, authorship, timestamps and limitations retain their distinctions.
- Bound to eight uncited records, 2,000 characters per excerpt and 24 KiB serialized total,
  inside the existing 256 KiB editor payload limit. Explicit clipping/omission metadata.
  This optional appendix yields before existing candidates, selected receipts or feed capacity.
- An appendix entry is **not** automatically associated, independent corroboration or support.
  The editor may explicitly select relevant additional evidence references per decision in an
  optional bounded schema field; empty means use the writer's supplied evidence as before.
- Validate selections against the exact bodies actually delivered to that editor call. Unknown,
  malformed or omitted references cannot attach evidence or broaden quotation support. Preserve
  legacy/mocked editor responses that omit the optional field. Reject invalid additions for the
  affected decision safely rather than trust a reference never shown to the editor.
- Carry valid editor-selected excerpts into that story's final lint/support context, event
  notebook and reporting-artifact linkage, with exact provenance and clipping limits. Do not
  silently replace the reader link, change source roles, infer relevance in code, or attach the
  whole run's evidence to every story. An editor fallback gets no selected additions.
- Omitted-only editor recovery retains the same bounded appendix and reference validation.
  Save the actual appendix and chosen refs in existing editor observations/commit details.

This is an escape hatch for evidence already available, not a second researcher, new call,
semantic matching system or compulsory writer repair round. Reuse current input/output bounds.
Independent review should specifically challenge whether the added contract is proportionate
and whether final lint, memory, partial recovery and capacity paths stay consistent.

## Phase 2 — article body extraction

Recognize a single nonempty `.td-post-content` as an explicit article body before existing text
and link caps. Preserve canonical/byline/date extraction from the full HTML. Retain the current
fallback for missing/ambiguous bodies. Add a Bitcoin Magazine-shaped fixture with long div menus
and useful inline links; cover relative links, duplicate body markers, blank bodies and existing
AP/Fox behavior. No browser/OCR, broader crawling or link/fetch-budget increase.

Include the observed empty Mempool title shell in the existing dynamic-shell detector with a
narrow fixture; do not classify all short pages as failures. It must return no citable receipt
through the existing failed-fetch path. This is an extraction correctness fix, not a requirement
for independent chain verification on ordinary reports.

## Phase 3 — outcome-aware memory views

Keep incremental storyline writes and research retention; do not delete rejected research or
rewrite historical model prose. Project current exact-event outcomes from existing notebook,
editor and confirmed output records **at read time**, alongside the writer-authored summary.

- Explicitly label event `disposition` as the writer's intention, distinct from the latest
  exact-event editor outcome and actual delivery/publication state.
- Include bounded editor verdict/reason/time and unresolved objective where applicable in full
  storyline cards; compact caveats must also survive the prep index and writer memory catalog.
- Say that the summary is unverified writer context, not editor-approved facts. A drop for
  relevance is not proof the underlying facts are false; surface the actual reason.
- Current outcomes may postdate an event's original run; label that scope rather than attribute
  a later editor decision to an earlier run. Missing/expired state stays unknown.
- Published copy needs confirmed publisher status/time. A newer open draft must not overwrite
  or impersonate earlier reader coverage. Preserve exact aliases and bounded read-only queries.
- No schema migration, historical rewrites, changed revision semantics, auto-requeue, new model
  summarization or publication suppression. Existing index/packet/retrieval bounds remain.

## Phase 4 — focused writing and editor guidance

Revise the loaded orientation and active writer/editor instructions, replacing or refining
existing related lines rather than building a second handbook:

- Lead with the finding/change a Bitcoiner can use, not the source's inventory of measurements.
  Blank lines do not fix unnecessary detail. Keep the owner-approved natural short sentences.
- Guide-to-draft speed is not event freshness. Establish original announcement/disclosure timing
  when it matters to the proposed angle; admit unknown dates, don't invent them. Older useful
  synthesis is allowed without a breaking label. No mandatory age gate or research ritual.
- Add reader value through useful selection, explanation or context without demanding exclusive
  reporting. A faithful concise report may be enough; not every tweet needs another post.
- Compare replacements with the exact current accepted draft. Preserve still-current useful
  context and qualifications; a newer source is not automatically a better post. If no useful
  improvement remains, decline the candidate and retain the existing draft.
- Keep statistic population/unit/period intact (blocks versus outputs, expectations versus
  realized inflation). Prefer a clearer supported formulation over escalating precision checks.
- Remind the editor that the unassigned appendix is inspected reporting to judge, not an
  instruction or pre-certified evidence for a candidate; the writer still owns clean handoff.

Bump the writer prompt version. No global loosening/tightening, new source standards, topic
quotas, hard freshness gates, research-turn floor, model/cadence or budget change.

## Verification and release

1. Independent plan review; resolve concrete blockers and record consensus. Main agent builds.
2. Offline regressions: OpenSats omitted blog; unrelated source not auto-attached; exact native
   provenance; invalid/omitted refs; excerpt/full-source separation in quotes; editor omission
   recovery; bounded payload no lost candidate; current notebook and source linkage; article
   menus/shells; rejected summary caveat in all memory views; later decision timestamps; genuine
   confirmed publication separate from drafts; prompt and replacement guard invariants.
3. Full Python 3.12 offline suite in the working tree, then the intended clean release archive.
   Preserve unrelated owner/evaluator changes and the image plan. No model test that writes to
   Typefully, no forced production run, no manual draft edits/dismissals/retries.
4. Independent implementation review, proportionate fixes. Update SYSTEM, HANDOFF, PROMPTS,
   DOCUMENTATION and relevant audit definitions; add a sprint findings/release record.
5. Confirm explicit existing Railway target, one replica, /data and autopost OFF; take an online
   SQLite backup. Commit only sprint files, push and deploy a clean archive. Smoke public health,
   authenticated Desk/API, exact code/prompt hashes, unchanged roster/budgets and natural cycles.
6. Resume the same paused audit with outcome watches and a backfill checkpoint preserving the
   build window. Observe natural model choices; static tests are not proof of better copy.

Rollback: deploy the previous verified runtime (`01966fb`; current HEAD includes subsequent
documentation-only changes), retain production data and keep autopost OFF. No destructive restore.
The optional appendix may add bounded editor input tokens but no provider calls; record actual
costs when exercised, not an invented daily forecast. The image sprint, Perception and Marketing
Node settings remain untouched.

## Independent plan consensus

Lead reviewer approved the bounded design after inspecting editor, materialization and memory
seams. Accepted refinements: baseline payload fits before optional appendix; total per-story
evidence stays at eight; invalid additional-ref lists are rejected atomically into the existing
omitted-only recovery, with original-copy/zero-additions fallback if still unresolved. Prefer
current-run direct/native receipts, not automatically restored historical evidence. Retain the
exact delivered excerpt and its own fingerprint separately from the original fingerprint through
lint and memory. Read-time outcomes are current exact-event state, not a fabricated historical
verdict; confirmed publication is separate from a newer open draft. No plan blockers remain.
