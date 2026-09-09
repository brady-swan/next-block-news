# Fetched receipt identity — bounded audit repair

## Current disposition — deployed and smoked

Runtime **993bdc1**, Railway **a12de434-63f2-4be3-a3d1-3c2455a62810 SUCCESS**.
September 9, 03:38:50 UTC smoke verified the clean-archive newsroom hash, unchanged editor,
store and config hashes, internal/external health200, all four authenticated Desk views200,
unauthenticated403, autopostOFF, no worker/publisher error and no unresolved deliveries.
One ordinary intake cycle completed after restart. The next scheduled newsroom is03:41:33;
no post-release newsroom session or natural changed-destination receipt has yet been observed.
The exact bug path is covered by failing-before/passing-after mocked regression tests, not
claimed as a live content replay. No paid test run, test draft, historical rewrite or comment.

Independent plan/code approval; 48 focused, 632 working-tree and **630 clean-release tests** pass.
The only runtime change is the fetched receipt classification call. No prompt, registry,
source policy, model, cadence, budget, schema, API credential or publication setting changed.
Unknown fetched sources now use their actual domain fallback; URLs/bylines retain the author.

Evidence: [smoke snapshot](audit/receipt-label-smoke-2026-09-09.json). Backup and rollback target
are below. No implementation or deployment work remains; continue normal audit observation.
The audit stayed ACTIVE throughout. Do not rebuild this repair from the historical plan below.

## New delta and authority

September 9, 2026, 03:33 UTC heartbeat `01a0842c-520c-7252-85b6-d10e5775cfc7`.
Full historical review is completed through September 8, 17:50 UTC, with current outcomes
reviewed separately. Plans 0068–0070, evidence-URL and editor-reference repairs are complete;
none is being rebuilt. Perception remains planning-only, no integration/config changes.

New evidence: v2.27 run `cycle:1788888895:0ddc01ba` prefetched Semafor's quoted post for a
Lummis intake item. Receipt `fetch_34ddf1832c6ce93729b8` has URL
`https://x.com/semafor/status/2097325338925650358` and Semafor byline but source_name
`X @SenLummis`. Writer called it her primary statement; editor caught the absent quote and
rewrote to Semafor's older story. A later confirmed replacement corrected the current draft;
there is no authority to manually change it now or to claim the wrong label alone caused this.

Current v2.29 production code reproduces the mismatched display label read-only with
`source_policy.classify(semafor_url, "X @SenLummis")`. Tier/source_id stay unknown.
Live/local newsroom.py SHA256:
`6b4aa5488ff824334e7847c81acd15879e11666ca81e05969f18bbbe8d9212ad`.
The fetch path passes intake.source for all destinations, including referenced/redirected URLs.

Standing AUDIT-AUTONOMY authorizes the smallest technical source-link/provenance repair with
independent review, tests, clean deployment and smoke. Autopost remains OFF. No new factual
gate, source weighting, policy, prompts, model, budget, cadence, schema or publishing change.

## Approved minimal change

Classify fetched receipts using their actual final URL without the parent intake source-name
hint. Known registry matches keep their existing display names/tiers. Unknown destinations get
the existing domain fallback rather than borrowing a different source's name; URL and byline
remain visible. Original intake source/context and candidate linkage remain intact. This avoids
a new identity system or changing global classification of discovery items/native sources.

Regression tests should cover a quoted X destination, cross-domain redirect, known destination,
same-source direct fetch, repeated cached fetch, and persisted receipt candidate/provenance fields.
All fetch/model/publisher activity mocked in tests. Historical receipts remain unchanged.

Release only the bounded runtime/test/docs diff from a clean committed archive; exclude unrelated
dirty evaluation work. Verify live hash, health/Desk and autopostOFF after deployment. Observe
natural worker progress without forcing a paid run or Typefully test draft. Roll back to the
previous reviewed runtime if smoke fails; do not restore or rewrite production data.

Independent lead `receipt_label_review` approved the plan and ran a five-case read-only
classification matrix: only unknown-source display_name changes, not other SourceRef fields.
It also confirmed that restored/native receipts already classify without the discovery hint.

Two new test methods (five cases plus cache/persistence assertions) failed before the change:
quoted Semafor inherited Lummis, unknown redirected destination inherited SEC, and a direct
unknown destination inherited its arbitrary feed label. The known-source cases were unchanged.
Implementation now removes the parent hint at this single call site, with an explanatory
comment. No additional helper, policy change or data migration.

Final independent code review approved without blockers; reviewer independently ran all 48
newsroom/source-policy tests successfully. Root's same focused tests passed, followed by the
full working-tree suite: 632 tests in 26.796 seconds. All new regression fetches are mocked.
Unrelated local evaluation changes are not included in the release; a clean-archive suite
will verify the actual artifact before deployment.

Preflight at 03:35:36 UTC: production health200, autopostOFF, no last_error, latest newsroom
run completed; old newsroom hash still matches. Existing production Railway service
ff9549a3-6f78-481a-a550-d8c10136af64 / environment90c43f68-970a-4f93-a392-414c3c175502,
one replica and /data volume; prior successful deployment451d51c7-c9c9-4ef8-8ab8-32b07b96200e.
No deployment or content mutation yet. Rollback is a clean archive of a9cf437 (docs-only after
ccea9a0), preserving the prior v2.29 runtime. Prompt version remains v2.29: this is a fetched
metadata correction, not a prompt/policy change.

## Release evidence

Runtime commit993bdc1; clean archive `/tmp/nbn-receipt-label.muHwrH` passed **630 tests in
24.064 seconds**, excluding unrelated dirty evaluation work. Its newsroom.py SHA256 is
`c75e41b17ca8821391f57f24037c51b770ecc8dc60d5063816270d83f655b746`.
Online backup `/data/backups/nbn-pre-source-policy-20260909T033629Z.db` passed integrity check.
Railway deployment `a12de434-63f2-4be3-a3d1-3c2455a62810` started03:37:11UTC on the same
production target. No autopost/config/credential changes. Completion and smoke are recorded above.
