# Editor appendix-reference contract — September 8, 2026

## Current disposition

COMPLETE in the coordinated Plan 0070 release: ccea9a0 / editorial-core-v2.29-visual-evidence,
Railway deployment 451d51c7-c9c9-4ef8-8ab8-32b07b96200e SUCCESS. Independent review approved;
628 tests passed locally and from the clean archive. Health, authenticated Desk, runtime hashes
and natural writer-cycle smoke passed. The natural run produced no story requiring editor
appendix selection, so no production proof of that specific selection is claimed. See
SPRINT-0070-FINDINGS.md. No separate v2.28 implementation/release remains. Autopost OFF; audit ACTIVE.

## New evidence and scope

Current production v2.27 run `cycle:1788900137:4537bec5` created Block draft10684538 at20:44UTC.
Writer fetched the company release syndicated by Yahoo. Initial editor2302 and recovery2304
cut the promotional quote but returned malformed appendix IDs/field names inside
`additional_evidence_refs`. Validator correctly rejected them, and applied2306 staged original
writer copy as `omitted_fallback`. Valid Liquid duplicate-drop sibling remained intact.
This is not missing research, a model outage, or proof the editor preferred the longer draft.

The existing structured-output schema allowed arbitrary strings despite already requiring exact
IDs in prose and application validation. Smallest repair: `_batch_contract` names only IDs in
the appendix actually supplied to each request, as `items.enum`. No appendix means `maxItems:0`
with string items, never an invalid empty enum. Nonempty arrays retain the eight-item ceiling.
The schema is rebuilt after recovery pruning; the shared template and payload remain unchanged.

Independent lead recommended limiting this change to appendix IDs. Story/reader ID enums were
considered and deliberately left out as unnecessary scope. No ID guessing, string stripping,
extra retries, source promotion, new model, budget/cadence change or editorial-policy change.
Per-story ownership/relevance/count validation, visual rules, and fallback behavior are unchanged.
Authority: existing bounded execution/reliability improvement scope in AUDIT-AUTONOMY.md.

The xAI structured-output engine documents enums and these array limits as supported, and
rejects empty enums. See [official structured-output documentation](https://docs.x.ai/developers/model-capabilities/text/structured-outputs).
NBN already sends strict schema through Responses; no provider adapter change is needed.
Anthropic's current adapter ignores this schema, so no new benefit is claimed for that path.
Dynamic schema has at most eight IDs; no latency/caching guarantee or automatic cost reduction
is claimed. Monitor ordinary outcomes rather than forcing paid replay.

## Verification and release plan

- Five new tests cover empty/missing appendices, exact request IDs and template immutability,
  strict mocked xAI HTTP payload, actual post-pruning recovery, and valid-sibling preservation.
-43 focused tests pass: new contract, evidence-to-reader, reporting execution and model adapters.
- Original standalone marker was `editorial-core-v2.28-editor-appendix-refs`; writer/orientation prose
  is unchanged. Only editor.py and that marker are runtime edits.
- After code approval: clean commit/archive excluding unrelated dirty evaluation and audit
  changes; full suite in the clean archive; deploy existing Railway service; verify health,
  autopostOFF, hashes, Desk views and natural worker progress. No test draft or manual replay.
- Rollback is the previous runtime `ab7529e` / Railway
  `f97615a4-7de1-44a4-ab67-6d49f37c681c`. No schema migration or database restoration is needed.

The Block advisory comment was separately confirmed20:52:58UTC with content/media/publishing
state unchanged; see audit/typefully-comments.md. The full editorial checkpoint advances through
13:50UTC independently of this targeted current-run investigation and repair.
