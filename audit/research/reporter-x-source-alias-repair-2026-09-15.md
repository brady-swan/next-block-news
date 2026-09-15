# Bounded X source-URL repair — September 15

## New evidence and scope

Main heartbeat01a0a35b-a738-7e92-b562-b198b7f72e9b, started04:38:07.944UTC. Overnight
autonomy permits obvious technical/tool usability repairs with independent review, tests,
deployment/smoke and the unchanged13:00UTC cutoff. This is NOT a rerun of the completed
legislative-PDF repair, reporter launch or CoinEx delivery.

CoinEx submission rejected twice before dispatch because its selected original X source used
the author's handle while `nbn_x` retained only `/i/status/ID`. Read-only diagnosis proved no
remote mutation; one operator clarification resolved it. Draft10772268 is now confirmed staged
with the exact retained URL, sameID and unchanged copy/evidence. NO further recovery is needed.

The reusable problem remains in `nbn/reporter_tools.py`: exact/read/search responses expand
author_id and users.username, but omit the already-supported evidence `canonical_url`. This
unnecessarily rejects a legitimate source link the model read in an article.

## Reviewed smallest change

1. Preserve existing `url` and `final_url` `/i/status/ID` strings and all source text.
2. Add `canonical_url=https://x.com/USERNAME/status/ID` only when the API's returned post
   author_id uniquely matches a well-formed expanded user with an ASCII X username. Never
   infer a handle from a query, quoted post, article or unverified source URL. Missing,
   conflicting or malformed author data keeps the existing `/i/status/ID` fallback.
3. Keep `reporter_delivery` validation unchanged: it already accepts canonical_url tied to
   a nonempty successfully inspected receipt. No general URL relaxation or retroactive evidence
   editing; no existing submissions/drafts touched. Do not tackle generic failure-label redesign
   in this change.
4. Tests: exact and search results bind each post's own author (not a quoted author's), missing/
   wrong/invalid/conflicting users fall back; handle-form source can pass existing delivery
   validation once; another post/unbound source remains rejected without a POST. Existing
   stable-ID/uncertain-delivery protections pass unchanged. Run a focused baseline first.
5. After approval and code review, clean focused release, proportional tests, bounded same-shift
   maintenance pause/deploy/smoke/resume preserving thread/start/cutoff. Smoke only read-only
   X fetch into an ephemeral test DB and mocked delivery—not another Typefully draft. Verify
   active lease/autopostOFF. No runtime/model/credential/cadence change. Send one concise tool
   update only if needed; old CoinEx receipt/draft stays unchanged.

Baseline deployed backend: e5983b58-17ee-4671-b47f-e698a4a0c8e8, commit a726a00;
local latest audit-only commit7f414d2. `nbn/reporter_tools.py` and relevant tests clean on entry;
other dirty work must be preserved. Implementation/review/test/deploy/rollback receipts will
be added here; this file is a plan, not a claim of completed work.

## Implementation and independent review

Independent reviewer `/root/review_x_source_alias` approved the plan, then reviewed the actual
implementation and tests and approved bounded deployment. Reviewer did not run tests or touch
production. All required checks are implemented: unique author match including malformed
duplicates, ASCII IDs/username, no query/quote-derived identity, unchanged raw/source provenance.
Implementation adds one small pure helper and one dictionary merge in reporter_tools.py;
reporter_delivery.py is unchanged. Five new test methods in test_reporter_x_identity.py cover
real-dispatch-shaped exact/search receipts and mocked create-once delivery, including rejection
of unbound handles, other post IDs and failed/empty evidence before dispatch.

Baseline22 focused tests PASS before edit;27 focused tests PASS after edit (1.722seconds).
Local diff check for implementation/tests clean. Existing CoinEx10772268 remains fully resolved
and untouched. Deployment and same-shift resume are complete; receipts below supersede plan state.

Commit d3500ce8b5e8358834930601965c3deccfa70ece pushed. Clean archive release
/private/tmp/nbn-x-alias-release.F97Rzh passed all778tests in43.503seconds with network-enabled
DNS validation. Initial sandbox-only run failed12tests/9errors in DNS-dependent paths; this
was not repaired by changing unrelated tests or code. Same suite passes unchanged outside
that network restriction. One-time rollout helper independently approved; initial pause attempt
exited before intent or mutation because a reporting turn was active. A later completed turn
allowed the maintenance recorded below; that initial check must not trigger another pause.

## Deployed, smoked, resumed — COMPLETE

Railway86bc122d-652a-4733-9fc4-f03fe50d83cd SUCCESS, created04:58:44.901UTC from clean archive.
Live reporter_tools.py hash f1fee802d88a2febac84da72f9ef6b057bac0848fd4ac672ba19947117febc9a
matches reviewed commit. Unchanged PDF hash also verified. Actual exact-X request returned
post2099680499094737251/author260702356, canonical yhaiyang URL, original i/status URL,
3091characters/hash7af157dfcfba88eeb1d4260829b6232ed151d86d0bebe66cc63964cfd91c267a.
Real response retained only in ephemeral test DB; unboundhandle rejected beforePOST. Five
deployed fixture tests prove accepted correctalias/create-once and negative cases with mocks.
No production evidence/submission/asset row or Typefully draft created by smoke. First smoke
attempt imported tests' network-blocking harness before liveGET; corrected helper import order,
not production code, then passed. Those attempts failed before any outgoing X request.

Bounded maintenance04:58:19.838–05:01:31.902UTC (192seconds). Exact oldPID46997 exited;
same original shift/thread/start/cutoff resumed once, newPID52851. Live lease/autopostfalse/
infrastructure/no pending verified05:02UTC. Tool message1651 tools:20260915:x-source-alias-v1
delivered to turn01a0a372-11d6-7f53-b4a1-4d2ecf9a3d64 and acknowledged1654 at05:02:48.462UTC.
Acknowledgment proves delivery, not a subsequent natural source-alias draft. No further resume,
message or CoinEx recovery is pending. Original13:00UTC cutoff unchanged.

Receipts: workspace output/reporter-overnight-20260915-0438/x-alias-{clean-tests.log,deploy.log,
maintenance-pause.json,production-smoke.json,maintenance-resume.json,final-status.json,
acknowledgment.json}. Helpers are one-time only. Rollback: focused revert of d3500ce/release
or prior deployment e5983b58-17ee-4671-b47f-e698a4a0c8e8. No DB restore; no existing content
changes. No additional recurring API/model cost, no runtime/credential/cadence/standards change.
