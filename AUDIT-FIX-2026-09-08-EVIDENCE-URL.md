# Evidence URL collision — new audit follow-up

## Current disposition — September 8, 2026, 19:32 UTC

Implemented locally and independently approved; release/deployment smoke remains. Only runtime
change is `nbn/store.py`: project the URL-keyed qualification table to one intact candidate per
exact URL, preferring the authoritative selected capture without merging flags. Immutable writer/
editor evidence, notebook captures, source choice and upstream text remain untouched. No schema,
editorial, model, budget, cadence or publishing change. Autopost remains OFF.

Verification:

- New full-materialization regression failed before the patch with the same production unique
  constraint error, for both direct and native reader choices; all model/publisher calls mocked.
- 79 focused evidence/resolver/store tests passed after correcting a test-only existing `www`
  normalization expectation. The helper did not change for that correction.
- Full working-tree suite: 590 tests passed in 23.253 seconds. Unrelated uncommitted evaluation
  work is excluded from the release; the clean archive receives its own complete test run.
- Independent lead approved code and ran 21 focused evidence/materialization/rollback tests,
  plus temporary duplicate-capture rollback and first-exact-match tie checks. Both reader
  variants retain four notebook captures while storing two URL rows. Reviewer made no edits
  or deployments. This reuses the prior plan approval; it is not a new architecture review.
- Fresh 19:31:50.513 UTC production pulse: health 200, autopost false, latest five runs completed,
  runtime still `684fd39`/v2.27, no current worker error. Railway target is the existing production
  service, one replica, `/data` volume, previous deployment `ac251388-dd31-4dd9-aeb9-da3b20eaa134`.

Next: commit only this repair/runtime regression, test a clean archive, online DB backup, deploy
that archive, verify live source hash and read-only Desk/health, then observe a natural run. No
manual Typefully mutation, paid replay or forced run. Rollback is previous clean runtime
`684fd39`, not DB restoration. Full editorial coverage remains through 12:20 UTC; this repair
does not review or advance that gap.

## Historical plan approval and implementation delta

Implementation delta —19:07UTC heartbeat: current deployed v2.27/hash still matches the reviewed
failing code; store.py remains unchanged locally. Completed packet/comment builds are untouched.
Implement the approved persistence-only projection and committed regressions, then independent
code review, clean release and smoke. Existing clear-technical-regression autonomy authorizes this
bounded repair. No editorial/model/budget/schema change; autopostOFF; no manual Typefully mutation.

Independent lead approved the bounded plan during the16:35 heartbeat; no implementation or
deployment yet. Its no-model synthetic full-materialization fixture reproduced the exact unique
constraint error before any publisher call. A temporary runtime projection completed the fixture
with two URL rows, four notebook captures, both editor additions and unchanged direct reader source.
The reviewer also verified native selection and identical-text direct/native selection in both
orders; 16 existing atomic-rollback/evidence-to-reader tests passed. No repository edits or external
mutations were made by the reviewer.

Approved boundary: `persist_resolution` projects to one intact candidate per exact URL, matching
the existing schema. Keep the first nonselected candidate, but prefer the candidate matching the
authoritative selected capture by SourceRef, fingerprint, originality, supported state and receipt/
corroboration eligibility (not fingerprint alone). Keep the first exact match on ties. Do not merge
flags, rank tiers, blanket-ignore inserts, change schema or discard upstream direct/native records.
Original evidence tuple, selected source, combined text, editor additions, observations and notebook
provenance remain intact.

Next implementation needs committed regressions: full materialization; selected capture including
identical text; duplicate writer captures without additions; equal text across distinct URLs; atomic
replacement rollback. Reuse reviewer evidence instead of starting the diagnosis again. The current
audit checkpoint/status lives in `audit/current-state.md`; the snapshot below is historical.

## Continuity delta, September 8, 2026 16:00 UTC heartbeat

Plans 0068/0069 and the dense-packet repair are complete; live runtime remains684fd39 /
editorial-core-v2.27-dense-fallbacks. The comment-only audit workflow is complete in080fc71,
with one verified Strive comment; it is documentation/automation work, not a new runtime.
Do not rerun these builds. The rolling audit remains ACTIVE and autopost remains OFF.

New evidence: production run cycle:1788881042:2abb9360 entered materialization after three
writer responses and editor_applied1965. Railway logs at15:26:40.495 show cycle failed:
main.py934 called store.persist_resolution; store.py3987 raised sqlite3.IntegrityError,
UNIQUE constraint failed: source_evidence.item_hash, source_evidence.url. Recovery recorded
interrupted_materialization and held unresolved stories at15:27:40.985. The label is not proof
of process restart. At16:00:59 current health is200 with no last_error and a later ordinary
25-candidate run completed. This is not a persistent service outage or initial packet overflow.

Smallest next action: independently review the source-evidence assembly and reproduce duplicate
URL persistence locally, with read-only access to the retained failed-run payload if necessary.
Identify a bounded technical fix that preserves receipt provenance and current editorial intent;
no model/policy/budget/cadence change, no destructive DB work and no manual publisher mutation.
Current autonomy explicitly permits clear technical repairs with independent review. Do not
implement or deploy before diagnosis/review. This task is separate from the completed packet fix.

Full editorial checkpoint is still11:15:56.744UTC. Root is completing a bounded oldest-window
audit in parallel; diagnostic reads alone do not advance the checkpoint. Record new findings
and review here before implementation. No repair implemented yet.
