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

## Proposed smallest change (independent plan review pending)

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
Local diff check for implementation/tests clean. Release/deployment/smoke/resume still pending;
no claim of a live change yet. Existing CoinEx10772268 remains fully resolved and untouched.
