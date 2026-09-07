# Sprint 0063 — reporter-writer, memory and operator feedback

September 7, 2026. Deployed after independent review, isolated replays and clean-release
tests. No replay was sent to Typefully or published.

## What changed

- Grok 4.3 medium can research with native web/X inside its writing conversation, alongside
  direct fetch, SerpAPI and local context tools. Grok 4.5 medium remains the independent editor.
- Six successful responses / 360 seconds, with finalization time reserved; at most 12 native
  calls inside the existing 24-tool limit. These are ceilings, not research requirements.
- Articles retain useful source links. Recent intake search covers 72 hours, optionally seven
  days, including skipped originals. Search is read-only and does not resurrect an item.
- Dated reporting notebooks and useful tool artifacts remain searchable for 30 days. A
  notebook-first catalog exposes more than Luna's suggestions, with current publication flags,
  readable titles and unresolved questions. Partial returned work survives interruption.
- Confirmed publication is projected from actual output records. A newer open draft cannot
  erase an older confirmed post; old notebook evidence is not silently made fresh.
- Optional writer feedback is visible per run and in a paginated System panel. It is an
  unverified self-report for human discussion, never injected into the editor or future memory.
  Null feedback is valid; a null protocol resubmission does not hide earlier provided feedback.

Autopost remains OFF. No source weighting, model roster, cadence, publication standards or
Marketing Node changes. Existing publishing and duplicate protections remain in force.

## Paid diagnostics

These are small reconstructed live-retrieval diagnostics, not a frozen statistical bake-off.
Preparation was bypassed to isolate the writer. Inputs are much smaller than a normal busy
desk. The first-party sufficient-evidence case is explicitly synthetic, not an actual BPI study.
Paid calls use isolated temporary databases and the existing authorized keys; no publisher is
called. Costs below include writer and editor, using xAI's reported amounts.

| Case | Writer responses / native calls | Writer time | Including editor | Model cost | Result |
| --- | --- | --- | --- | --- | --- |
| Lummis, old code | 3 / 0 | 37.33s | 49.29s | $0.04006 | Cited The Block's X report; editor approved |
| Lummis, final integration | 1 / 5 | 23.26s | 46.63s | $0.08268 | Registered original post target; editor revised |
| Sufficient first-party fixture | 1 / 0 | 13.31s | 39.52s | $0.03501 | No discretionary research; editor improved the lede |

The final Lummis receipt resolves to `https://x.com/i/status/2096644344795246746`, the original
post ID present in earlier intake. Its material is **provider-reported paraphrase**, not a direct
page capture. An anonymous `/i/status/` URL does not establish the account identity by itself.
That limitation stays visible. The old path's search failed and it used the usable secondary
report; this was reasonable behavior under the old input/tool limits.

The new writer added a September 15 vote sentence not supported by its selected receipt.
The editor removed it. The final copy remained a concise two-paragraph Lummis warning. This
is a useful success for the complete stack, but a writing/research grounding issue to watch.

Earlier diagnostic attempts exposed real integration problems: function-call output may lack
ordinary native citation annotations; writer-selected discovery pointers can be mistaken for
receipt IDs; native keyword search alone may not attest the claimed URL. We fixed exact source
target handling and added one bounded receipt-reference repair using the remaining run budget.
No source is automatically chosen, and unknown/uninspected references still fail validation.
A mixed dossier preserves valid stories if the reference repair fails.

Another intermediate replay retained only the secondary source and was routed by the editor
for human review. This variation is why one successful final replay is not a reliability rate.
Do not extrapolate these small-packet costs into a daily bill. Watch real run costs, research
selection, follow-through to original sources and single-worker polling delay.

## Feedback is useful precisely because it is not authoritative

In the final replay, the writer said direct X access helped and suggested prefetching key
handles. It also described the vote context as useful; the independent editor found that line
unsupported by the submitted evidence. This is a concrete example of how to use the panel:
compare self-reports with actual sources and outcomes, then decide what is worth changing.
There is no automatic prompt, policy or memory update from that feedback.

## Verification

- Independent lead approved the plan and reviewed implementation. Five substantive findings
  were fixed: eight-source registration, confirmed-output precedence, notebook-first indexing,
  finalization reserve across tools, and durable native partial work. The bounded reference
  repair was separately approved.
- Full working-tree suite: 487 passing tests; 22 focused reporter-writer tests. TypeScript
  check, production asset build and Desk polling checks pass. Clean-release results follow.
- Existing eight-page system PDF refreshed and every rendered page inspected.
- Regression coverage includes source provenance, exact native post IDs, mixed valid/invalid
  dossiers, repair exhaustion/failure, tool budgets, memory date/integrity/publication state,
  catalog paging and read-only access, and feedback isolation/absence.

## Production release

- Runtime commit `68a7b36`, pushed to origin/main; clean archive
  `/tmp/nbn-0063-release.w9VbaA` passed **485 tests**. The working tree's two additional
  evaluator tests and unrelated evaluator/tuning/planning changes were excluded.
- Online backup `/data/backups/nbn-pre-source-policy-20260907T051030Z.db` passed its full
  integrity check. The new artifact table is additive. Rollback means the prior runtime,
  old 3-response/240-second settings and combined-reporter flag off, not rewinding live data.
- Railway deployment `29213e94-0bcc-4716-8d28-b6c568877e83` succeeded on the existing service,
  one replica and `/data` volume. No keys or publication-mode settings changed.
- Public/internal health and all four authenticated Desk JSON views returned 200. HTML,
  JS/CSS and the PDF returned 200; missing authorization returned 403. Runtime newsroom and
  PDF hashes matched the release exactly. New artifact table and read-only catalog work.
- Runtime confirmed v2.17, combined reporter enabled, six responses / 360 seconds, native
  cap 12, autopost OFF and the legacy daily receipt audit disabled. The first ordinary
  worker cycle completed without error. Historical runs correctly say feedback not recorded;
  feedback is not manufactured or backfilled for old runs.
- The live catalog exposes 84 currently eligible notebook/storyline entries; read-only
  intake search finds eight Lummis items. This is broader than the prior 12-card subset.
- Rolling audit `audit-nbn-production` restored ACTIVE on its existing 15-minute schedule,
  preserving autonomy and quiet-notification rules. New watches cover source follow-through,
  notebook use, native costs/limits, polling delay and self-reports versus observed work.

The first natural v2.17 run, `cycle:1788758319:c62553d5`, completed at 05:19:05 UTC without
error. Preparation advanced one of three items. The writer completed in one response using
the prefetched source, with no discretionary research or new output. The actual 44,769-byte
packet included 46 catalog entries and an explicit continuation into the 85-entry catalog.
Its fetched source is retained in the artifact table. The optional feedback value was null;
both the run view and System correctly show **no feedback**, not a missing-record error.
All Desk endpoints were rechecked after this run. No production model run was forced.

The preexisting Node by-date endpoint returned 404 overnight; the last Node pulse was stale.
This did not prevent direct intake or the newsroom session. Node/Perception are outside this
sprint; no settings were changed to mask that condition.
