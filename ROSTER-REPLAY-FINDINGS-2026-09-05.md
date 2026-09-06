# New roster replay — findings and conclusions

September 5, 2026, late evening Central. Historical review copies, not fresh publication recommendations.

## Bottom line

The roster can produce the concise writing we want. Native Grok research also demonstrated a
real advantage: an IMF story that the editor rejected without adequate receipts passed with
native-retrieved, explicitly labeled source findings—even while ordinary fetching was blocked.

But the newsroom does not reliably choose that research route on its own. We also found two
API-contract defects that the earlier small compatibility probes had not exposed. Those are
fixed and deployed. Editorial/research routing changes are recommendations below, not shipped.

Four review drafts are in Typefully. All were read back and confirmed as unscheduled drafts,
with exact lead text and the source in the first reply. Existing drafts were not edited or
deleted, no replay output was published, and production coverage counts were not changed.

## Review these in Typefully

| Draft | What I think |
| --- | --- |
| [ETF inflows — 10645421](https://typefully.com/?a=329191&d=10645421) | Best straightforward writing sample: 25 words, two clean sentences, actual news first. Editor cut an unrelated Ether detail. |
| [CFTC / CLARITY — 10645422](https://typefully.com/?a=329191&d=10645422) | Much less dense: 63 words versus 155 in the old draft. Still leads with personnel vetting rather than the significance for CLARITY—the same owner feedback remains relevant. |
| [IMF — native research version, 10645420](https://typefully.com/?a=329191&d=10645420) | Stronger source and more precise program context. Four short paragraphs, 72 words. I would question whether the Chivo paragraph is needed in a post whose core is donation-funded accumulation. |
| [IMF — secondary-source version, 10645419](https://typefully.com/?a=329191&d=10645419) | Useful comparison, not the preferred version. The editor explicitly requested human checking. It drifts into program mechanics, acronym use, and loan details that may be expendable. |

The titles begin **REPLAY**. The two IMF versions intentionally cover overlapping material for
comparison; they are not two recommendations to publish. The CFTC copy is an approved in-place
revision exported as a separate review draft because the replay was forbidden to modify its
real predecessor. Its original replay delivery result remains recorded as blocked-for-isolation.

My preferred CFTC opening, for discussion rather than an edit to the submitted model output:

> Four empty CFTC seats remain a sticking point in CLARITY Act talks.
>
> The White House has vetted candidates to fill them, three sources told CNBC.

## What ran

Actual runtime functions and prompts, not the simplified bake-off writing contract:

- Haiku 4.5 for eligible RSS intake.
- Luna low for preparation.
- Grok 4.3 medium for newsroom writing and native research.
- Grok 4.5 medium for editing.

We replayed five historical batches containing **52 unique candidates**, with **nine batch
executions / 96 candidate exposures** after repeats and the controlled research test.

| Test | Result | Model cost |
| --- | --- | ---: |
| Original three batches: correlation, IMF relay, Oklahoma; 37 candidates | One missing-tool defer; IMF editor rejection; no eligible output | $0.0974 |
| Same three batches after contract repairs | All runs completed; zero invalid prep records; still no eligible output | $0.1214 |
| ETF batch; 10 candidates | ETF revision plus a human-check IMF draft | $0.0950 |
| CFTC batch; 5 candidates | Editor revised the story; intended replacement safely blocked in isolation and exported separately | $0.0542 |
| IMF batch with native research explicitly assigned; 7 candidates | Editor revised/accepted the resulting draft | $0.1272 |

The last row is an intervention, **not** evidence that the ordinary newsroom autonomously chose
native research. In the five post-repair ordinary batches, it chose native delegation zero times.

### Replay limits

The source snapshot was captured read-only. Each batch used a separate local database, original
candidate cards, and pre-batch posts from the three-day snapshot; old answers were not supplied
as the new answer. The newsroom's date was set to the original batch date. The historical
workbench/storyline versions were unavailable and were not reconstructed from later memory.

Search/fetch happened live, and prior-post state is not a perfect historical reconstruction.
This is a diagnostic exercise, not a causal benchmark, an unbiased recall score, or a claim that
every candidate deserved a new post. Samples were deliberately selected around known earlier
outputs, then broadened when the first set produced none.

## Findings

### 1. Two mechanical contract problems were real

One initial Grok response completed without a function call. The API allowed ordinary text,
while NBN required a tool submission. The run correctly deferred instead of publishing an
unvalidated response, but the request contract should have matched the parser from the start.

Responses newsroom turns now require a tool call; the model still chooses research versus
dossier submission. The final allowed turn still specifically requires the dossier. This does
not force research, publication, additional turns, or extra retries.

The initial three Luna batches also had **12 of 37 records fail open as invalid**. The parser
enforced list bounds absent from the request schema. Responses preparation schemas now expose
the existing limits: three source leads, three related event keys, two storyline keys. The
prompt states those limits too; Anthropic keeps its compatible schema subset. In the repeated
37-candidate pass, invalid records fell to **zero**. This small stochastic comparison supports
the repair; it does not prove that every original invalid record had the identical cause.

The earlier compatibility smoke was too narrow to establish realistic newsroom reliability.
The replay caught what it missed. No publication/corroboration standard was loosened to fix it.

### 2. Native retrieval works; choosing it is the gap

In the ordinary IMF replay, Grok spent its three newsroom turns searching, fetching CoinDesk,
and submitting. CoinDesk returned 429. The remaining usable receipt was an X repost, and the
editor rejected the consequential IMF/loan-compliance claims as inadequately supported.

In the explicit native-research control, Grok used **four web searches and two X searches**.
It supplied citation-bound findings including an IMF release. Local retrieval still returned
403 for IMF and 429 for CoinDesk, but the provider-reported findings survived with their
provenance intact. The editor accepted the story with revisions, including distinguishing
Chivo ownership from operations. The draft links to the IMF release in its first reply.

The native assignment cost **$0.0690**; the entire prep/research/writer/editor batch cost
**$0.1272** and took **95 seconds**. The ordinary rejected IMF attempt cost $0.0663 and took
46 seconds. Extra cost and time bought a usable result in this case—not a universal guarantee.

This does not independently authenticate every assertion in a model-reported extract. It
does demonstrate that the deployed provenance mechanism can carry native research through
the writer/editor stack without insisting on the same blocked local fetch.

### 3. Better copy does not automatically mean better editorial selection

The ETF post is a strong positive example: a meaningful total, a useful comparison, the leading
fund, then stop. CFTC is dramatically shorter and more readable, but the lede still needs the
Bitcoin-policy consequence brought forward. Native IMF has good paragraph rhythm but could
lose an adjacent subplot. Keep these as examples for tuning; do not infer that short equals good.

Some rejection reasoning was overbroad. Correlation was dismissed partly because it was widely
circulated on X; a bank stablecoin item was dismissed regardless of monetary implications.
Those are reasons to examine calibration, not adopt blanket new exclusions. Conversely, the
correlation core had already appeared in NBN's September 2 coverage, so this replay is not proof
that we missed a publishable new correlation story.

The Oklahoma candidate illustrates date confusion worth reviewing: the first writer pass called
it a resurfaced 2023 incident, whereas the old draft described a 2023 stop-work order as background
to condemnation. After repair, Luna put it in Background. That is a candidate for checking the
event date and relevance—not enough evidence here to label it definitively publishable.

### 4. Keep audit claims and exact-event identity grounded in actual copy

One existing tuning note said the donation clarification was already folded into draft
10619385. A fresh Typefully GET showed that draft still contains Bukele's denial about reserve
ownership versus Chivo ownership; draft 10640277 contains the private-donations claim. These
are related IMF/El Salvador material, but shared theme alone does not establish identical claims.

Do not treat an old audit note, event-key label, or this replay's output count as authoritative
proof of a duplicate or a miss. Compare the actual reader-visible claim and latest draft text.
I made no production disposition changes from this observation.

## Cost and speed

The nine replay batches used **30 model calls, totaling $0.4952** in recorded model costs:

| Seat | Calls | Cost |
| --- | ---: | ---: |
| Newsroom | 13 | $0.2679 |
| Editor | 5 | $0.1289 |
| Native researcher | 1 | $0.0690 |
| Luna preparation | 9 | $0.0245 |
| Haiku intake | 2 | $0.0049 |

xAI amounts use provider-reported billing; the other seats use recorded token-rate estimates.
SerpAPI subscription/credit costs and hosting are not included. Replay usage lives in the
isolated artifacts, not production's daily totals. A separate deployed writer smoke cost $0.0041.

Batch wall time ranged from **30 to 95 seconds**, including prep, retrieval and editing where
used. Do not extrapolate this selected, repeated, partly cached sample to a monthly bill. It
is encouraging evidence that useful draft-level work is affordable, not yet a daily-cost forecast.

## Recommended next step

Keep the roster for now and review these four drafts. I would prioritize one bounded
research-routing clarification: when a worthwhile, not-already-covered story hits a blocked or
insufficient receipt, use the native researcher before spending the remaining turn budget on
another direct lookup. Test that against this IMF case without increasing quotas or research
budget first. This is proposed, not deployed.

Then reinforce the already-approved writing lessons with the ETF positive example and the
CFTC lede comparison. Check the correlation/Oklahoma judgments against exact prior coverage
and event dates before changing selection guidance. No new architecture or model upgrade is
justified by this sample.

## Technical rollout and artifacts

- Repair commit: `8984e21`; Railway deployment `ff64b138-128e-427c-8183-f791e57fa573`, SUCCESS.
- Tests: 409 working-tree tests / 407 clean-release tests passed. Two existing uncommitted eval
  tests were deliberately excluded from the deployment archive.
- Backup: `/data/backups/nbn-pre-source-policy-20260906T043051Z.db`.
- Deployed prompt: `editorial-core-v2.14.1-tool-contract`; prep:
  `assignment-desk-v2.3.1-bounded-preparation`. Live writer smoke passed; health and DB integrity
  checked; autopost OFF. No model/effort, cadence, research-policy or editorial-standard change.
- Existing rolling audit remains active. Historical review copies must not count as live output.
- Runner: `scripts/replay_roster_review.py`. Raw snapshot, per-case inputs, dossiers, decisions,
  provider traces, usage, and confirmed export manifests:
  `.model-eval/roster-replay-20260905/`.
- Contract references: [Responses function calling](https://developers.openai.com/api/docs/guides/function-calling)
  and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
