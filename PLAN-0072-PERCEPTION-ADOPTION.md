# Sprint0072 — make the Writer's existing research desk usable

September9,2026. Owner-authorized turn01a0864b-aa94-7593-9ae2-f3118215c329.
Status: plan approved by independent lead; implementation and release verification underway.

## Objective and judgment

Help the Writer turn useful tips into timely, original-source, readable Bitcoin coverage by
making existing tools and prior work easier to discover and use. This follows the completed
0071 release and cold Writer investigation; it does not rebuild that integration or change models.

Owner clarification: consequential monetary-policy signaling by Bessent or Warsh can itself
be news and a developing storyline. Do not require a completed intervention, new law, immediate
Bitcoin price reaction or Bitcoin-only headline. Attribute what was said, preserve the date,
distinguish remarks/proposals from actions, and select for consequence rather than reporting
every appearance or market tick. The Bessent example is approved audience-fit guidance, not
an instruction to publish that old sample now. Align the writer, editor and prep orientation
where the same remit is expressed; no blanket macro expansion or automatic promotion.

## Evidence already obtained — do not repeat paid exploration

See audit/research/writer-tool-adoption-2026-09-09.md. Across27 Writer packets,126 appearances
lost a valid Perception-text hint during compact-card reconstruction. Legitimate empty FIU
regulatory text became search_format_unknown/backoff. Cold Astra found an original Osmosis
statement through native X, while Perception located an original FT URL but returned only114
body characters. Retained Alby/Lam bodies were useful. Four local retrieval calls exhausted
access after only22.5KB, partly because an accepted-copy lookup yielded only a lede and the
memory map had disappeared. Production Alby evidence reached the log but did not inform the
final decision; this is not yet a proven transport failure.

## Implementation package

### 1. Preserve useful resources through packet compaction

- Keep available_perception_text (source URL/artifact ID, publication/capture dates, length,
  completeness warning and read instruction) on every eligible candidate through every density
  stage. Absence remains absence; availability is not inspection or a second source.
- Reduce verbose optional metadata and oversized evidence excerpts before deleting the entire
  memory map. Keep a bounded compact catalog, prioritizing exact current-candidate/prep matches
  and useful notebook pointers. Retain a correct full-catalog pagination/search path; don't
  reorder a page while pretending its offset is unchanged. No new semantic selector/model.
- Keep every candidate identity/decision requirement and owner control intact. Initial packet
  stays within the existing64KiB bound; oversized cases fail explicitly, never silently lose leads.

### 2. Make accepted copy and local retrieval genuinely useful

- For a small, bounded set of relevant exact/known-alias event matches, expose existing local
  accepted copy, publisher status/as-of time, receipt URL and direct notebook pointer. Reuse
  writer_memory.publication/current output and existing store projections. No remote Typefully
  call during packet assembly, no inferred event merge and no new output table.
- Coverage expansion must open actual stored copy rather than another260-character lede.
  Keep current draft distinct from confirmed published copy; mark local snapshot/provenance and
  truncation honestly. Never call a prior proposed draft accepted or reader-visible.
- Return remaining call/row/byte capacity and exact omitted IDs from context reads, including
  already-read IDs separately. Account for the final response envelope in existing byte limits;
  do not let repeated reads or partial rows silently consume resources without a usable result.
- Keep the four local calls,48KiB total,16KiB per-call and eight requested rows initially.
  Better matched copy/pointers should remove unnecessary search hops. No limit increase bundled
  speculatively; if focused tests show a remaining unavoidable follow-through blockage, bring
  that specific bounded adjustment back to the lead before changing it. Paid research budget
  is explicitly unchanged.

### 3. Correct Perception's legitimate empty result

- Accept the recorded successful regulatory response “No regulatory documents found…” as
  zero results, cache with the existing short empty TTL, and do not set failure cooldown.
- Test the full adapter path as well as parsing. Authentication/quota/RPC/tool/malformed
  responses stay errors, not zero-result research. Don't generalize an arbitrary error string
  into a successful empty search. No quota/routing/provider contract expansion.

### 4. Replace scattered routing advice with one gap-driven cue

Replace/reconcile existing overlapping prompt text, rather than adding a new checklist:

> Choose the next tool that resolves the actual reporting gap. Use available dated Perception
> text or coverage search for an industry article or blocked page; use native X or a source
> link for an original statement; open accepted copy and the notebook for a possible repeat.
> Inspect an image when its contents matter. Update your decision with what the tool actually
> returned—not the initial card's evidence status. If it returns the same tip or no useful body,
> switch routes or finish the supported story. Stop when there is enough for a useful, accurate
> narrow report; no tool is mandatory.

Preserve exact source IDs, article identity, publication dates, incomplete-body warnings,
independent Editor, source-in-first-reply policy, existing writing style and media permissions.
Clarify that first coverage by NBN is not NEW by itself; old evidence may provide background
to new reporting but reading it doesn't reset the event clock. This reinforces the already
approved freshness rule, not a new hard age gate. Bump prompt version once for this release.

### 5. Observe evidence incorporation, not a tool-use quota

- Add small existing-observation fields/records for packet hint/catalog retention and final
  inspected/selected evidence IDs, plus source kinds/capture dates where already known. Keep
  attribution to Writer selection versus actual Editor choice distinct. Record history-byte
  composition at the existing pre-call boundary only if it helps diagnose the known overflow;
  no provider-history rewrite or increased cap in this sprint.
- Deterministic scripted Writer tests should prove newly fetched/retained text is delivered to
  the next model message and selected supporting receipts reach the actual Editor projection.
  They cannot prove the model paid attention or improved editorial judgment. Natural audit
  outcomes decide that; an unused useful source remains an observation, not a new blocking gate.
- Score original discovery, useful body recovery, chronology, resolved uncertainty and avoided
  duplicate work separately. FT original-URL success is not full-text recovery. Useful prepared
  material counts even without another network request. No new model grader or mandatory feedback.

## Boundaries

No model/effort/paid tool budget/cadence/quota increase, new researcher, new memory architecture,
Node changes, vendor calls/features, autonomous Typefully copy or publication, forced live model
replay, added generic verification gate, mandatory Perception research, or Nano Banana work.
AutopostOFF. Existing normal worker draft delivery may continue. Preserve unrelated dirty files.
Audit paused in dedicated task; restore SAME automation/target/scope after deployment/smoke.

## Acceptance and release

1. Independent lead reviews this scoped plan, iterates on concrete blockers, then reviews the
   actual diff. Avoid expanding into an unbounded reporting architecture redesign.
2. Offline tests: oversized candidate hint retention; compact catalog pagination and exact-match
   precedence; full accepted-vs-proposed/published copy; unknown/deleted/test outputs excluded;
   UTF-8 response envelope limits and exact omitted/repeated IDs; successful empty regulatory
   response/cache/no backoff versus real errors; source text delivered to next Writer turn and
   selected exact source material reaching Editor; guidance consistency and owner controls.
3. Run focused tests, full offline suite, then clean-commit archive suite. Keep unrelated evaluator
   changes out of the release. Use recorded fixtures, no new paid bake-off.
4. Verify Railway target/autopostOFF/one replica/data volume, make online SQLite backup; deploy
   clean reviewed commit explicitly. Check hashes/prompt version, health and authenticated Desk.
   Confirm a natural worker cycle; inspect a natural new Writer packet if one occurs, without
   manufacturing a story or claiming organic adoption from unit tests.
5. Update SYSTEM/HANDOFF/configuration docs where behavior changed and add audit-specific watches.
   Restore the same15-minute audit in NBN Audit, exact prompt/target/status readback. Hand off
   changed artifacts and remaining empirical questions; safe code rollback if smoke regresses.
