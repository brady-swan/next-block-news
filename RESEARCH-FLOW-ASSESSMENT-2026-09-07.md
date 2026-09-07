# NBN: following tips to original sources

Assessment, not an implementation authorization. Based on deployed code and retained production
handoffs through September 7, 2026, 03:40:41 UTC. No prompts, configuration, production records,
or Typefully content changed. The rolling audit remains separate from this investigation.

## Conclusion

NBN has useful retrieval machinery but does not reliably practice source-following reporting.
It often judges and rewrites whichever page preparation has already fetched. We should improve
how it identifies and follows the origin of a promising claim, not require perfect corroboration
or make every candidate pass a longer research process.

The current gaps are tool affordances, lost source links, incomplete access to prior intake,
and a workflow that makes finishing cheap but following a source chain comparatively awkward.
They are not explained by bot blocking alone, a lack of native X-search capability, or exhausted
context-retrieval allowances.

## What actually happens

1. **Intake supplies a lead.** Direct X can preserve long text, quoted originals, outgoing links,
   media pointers and timestamped engagement. Other paths, including older/Perception X cards,
   can supply only a short text preview and URL. A supplied media pointer is not visual inspection.
2. **Luna prepares the assignment.** It suggests what happened, relevance, freshness questions,
   a research objective and up to three source leads. It has no research tools in this pass.
   Suggestions such as “find the original interview” remain advice, not completed work.
3. **Code prefetches likely receipts.** Up to six URL attempts / 24,000 characters per run.
   It prefers explicit official Node references, then guide/material source links, then the intake
   URL. It selects one candidate URL per item; it does not traverse that page's citations or turn
   Luna's prose suggestions into searches. Media URLs such as X `/photo/1` can win this selection
   and resolve back to the same tweet, not an upstream source.
4. **Grok 4.3 medium owns research and writing.** It can submit immediately, Google-search via
   SerpAPI, fetch URLs, retrieve indexed desk context, or delegate one focused research assignment.
   It sees prior coverage, selected storylines and bounded reusable evidence, not a searchable
   archive of every past intake item.
5. **The optional Grok researcher has native web and X search.** Native search is not directly
   enabled in the main writer call. The writer must call `assign_research`. That assignment has
   a 90-second ceiling, up to eight native calls requested, and at most five retained source
   findings. Native call limits are not a guaranteed dollar cap. Returned extracts are labeled
   source-specific paraphrases; the system prefers direct page text when it can fetch it.
6. **The editor judges the assembled packet.** Grok 4.5 medium receives the draft and supplied
   evidence. It does not independently browse or find a better source. A credible-source label
   and matching text can therefore lead to approval without upstream reporting ever occurring.

The writer has three successful responses total, including final submission. A common path is
search in response one, fetch in response two, then forced dossier in response three. It cannot
then follow a newly discovered article citation with another direct tool round. It can batch
known independent fetches, or use the multi-step researcher inside one round. The latter is not
being selected in the observed production sample.

Code anchors: `nbn/desk_prep.py` (`SYSTEM`, `prepare`); `nbn/newsroom.py`
(`NEWSROOM_V2_SYSTEM`, `_reference_urls`, `prefetch_prepared_receipts`, `_initial_packet`,
`_native_research`, `conduct_v2`); `nbn/sources.py` (`fetch_article`); `nbn/research.py`;
`nbn/editor.py` (`review_newsroom_batch`); `nbn/models.py` (`ResponsesClient.create`).

## Production sample: behavior, not just advertised capability

Current-worker window: September 6 20:30:03 UTC to September 7 03:40:41 UTC, about 7.18 hours.
This is one afternoon/evening sample, not a causal benchmark or all-day quality estimate.

| Measure | Observed |
| --- | ---: |
| Completed desk/preparation runs | 27 |
| Runs reaching the writer | 26 |
| Writer runs with no discretionary research/context tool call | 16 / 26 |
| Runs with Google search | 7 |
| Google search attempts / recorded failures | 13 / 2 |
| Prefetch attempts / reported successes | 71 / 66 |
| Writer-requested fetch tool returns | 14: 12 successful, 2 failed |
| Successful writer fetches that reused cached evidence | 6 |
| New successful writer fetches | 6; three were empty explorer shells |
| Native research assignments / native web or X calls | 0 / 0 |
| Optional stored-context reads / capacity hits | 0 / 0 |
| New local Typefully deliveries | 3 |

No-research is not inherently a failure: many candidates are obvious skips, and good supplied
receipts can be sufficient. Conversely, fetch success is not research success. Six reported
new fetches included three 34-character explorer shells; the other three were reporting pages
and Liquid's own statement from a single useful research run.

Recorded seat cost was about $0.994, plus unknown billing for one preparation timeout:
writer $0.7685; editor $0.1267; preparation $0.0452; intake $0.0538. These figures exclude
external data subscriptions, hosting and the Codex audit. This short window does not establish
a daily or monthly rate. The timeout failed open for all 25 affected candidates.

## What is working

- **Useful direct and reporting sources are fetchable.** The source network and APIs are not
  generally down. Native research also worked in an earlier controlled IMF replay: four web
  and two X searches retrieved source-specific findings including an IMF release despite local
  blocking. The measured assignment cost was $0.069, not a universal expected cost.
- **Evidence survives sessions.** Liquid's inspected reporting was reused. Search pointers can
  survive for the exact candidate or known event. This is helpful even though unrelated or
  unkeyed rejected originals remain difficult to rediscover.
- **Provenance distinctions exist.** Direct text, native paraphrases, social statements and
  independent reporting are not all silently treated as the same thing. Exact URLs and source
  authorship matter. The models can use a reliable secondary report without an official-source veto.
- **Practical reporting is possible.** The Liquid draft was useful enough for Brady to publish.
  A later run searched, read reporting and fetched Liquid's original statement. Its attempted
  draft replacement was safely stopped because Brady had published during the run.
- **Some data-specific handling is already good.** FRED chart links can resolve to their CSV
  data rather than a nonfunctional chart shell. This is a small example of choosing the right
  evidence format rather than repeatedly scraping the same page.

## Where source following breaks

### 1. We lose the trail inside fetched pages

`fetch_article` strips HTML tags, collapses whitespace and truncates text. It retains canonical
URL and byline, but not article citation anchors and their href destinations, a useful article
publication-time record, or structured main-post/reply boundaries on X. It has no general
rendered-browser or screenshot workflow; documents and dynamic charts do not have general
specialist handling. The FRED CSV exception is narrow.

A page can say “according to this filing” while its filing URL disappears. Abbreviated visible
transaction labels can survive while their real hyperlinks do not. In the Liquid technical
follow-up, the writer filled missing transaction-ID characters with invented text and fetched
explorer shells. Nothing was delivered, but those requests were not verification.

### 2. Our own source archive is harder to use than another publication

Lummis's original 2030 statement was captured at 12:01 PM CT and dropped at 12:14 as advocacy.
At 9:14 PM, essentially the same statement arrived in Typefully through The Block's tweet.
The original had no canonical story key and was not connected to the later tip. No search or
article inspection occurred. Peer-to-draft time was 17 minutes; primary-source-to-draft time
was **9 hours 15 minutes**. The earlier audit overpraised the former without checking the latter.

Current context retrieval opens code-issued cards. It cannot search arbitrary old intake by
speaker, quote or topic. Storyline context is not a substitute for the original source record.

### 3. Our instructions reward an adequate immediate receipt more than finding the origin

The prompt repeatedly encourages immediate submission when prepared evidence is enough.
That helps cost and throughput. It also makes a fetched intermediary tweet look like a finished
research task. “Primary sources preferred” competes with “finish in one response.”

Luna sometimes supplies an oversized research objective: find original remarks, establish all
legislative deadlines, voting prospects and Bitcoin implications. The useful next step may
only be “find the senator's post and date.” A focused reporter needs a concrete question.

We should distinguish **source reputation**, **originality**, and **what this specific artifact
proves**. A reputable publisher's restatement is not original reporting because of its tier.
A senator's own tweet is primary for that senator's statement; it is not proof that the senator's
prediction will come true. An exclusive reported article may itself be the best original source.

### 4. Fallback behavior is too narrow

The generic failed-fetch guidance recommends another Google search and fetch, then hold/skip.
It does not point to the available native X/web researcher. More broadly, that researcher is
presented as optional delegation for a multi-step verification problem rather than the normal
way to follow a promising social tip to its source.

This is not an entirely new discovery: Sprint 0059 tested stronger routing wording across nine
replays, with zero native assignments, and correctly did not ship that unproven wording. The
next change must demonstrate route selection, not merely add another paragraph to the prompt.

### 5. Some apparent research failures are elsewhere

Liquid's repeated identity deferrals and Coldcard's collision with two existing drafts happened
despite inspected source material. More search would not repair those delivery/continuity
problems. Similarly, an editorial decision that a quote is not news is not an API failure.
Keep these distinct in the dashboard and audit.

## Recommended direction, in priority order

### A. Make the source trail usable and search our own intake

Return bounded article text plus useful citation links (label and real destination), authorship,
available publication metadata and explicit limitations. Separate X main post, quoted original
and relevant same-author thread content where available. Do not invent URLs or treat a dynamic
shell as useful evidence. Reuse current safe-URL controls.

Add a bounded lookup of recent intake, including skipped leads, by relevant entity/quote/event.
Return a few original records with real dates and previous reasons. Use deterministic retrieval
for candidates and let the model judge relevance; do not automatically merge event identities
or inject the entire archive. This addresses Lummis without buying another search.

### B. Give promising unresolved tips a focused source-following assignment

Have the writer choose worthwhile leads and request one concrete job when the supplied source
is merely an intermediary: find the original speaker, filing, study, data release or reporting.
Use the existing Grok native web/X researcher for that job, particularly when X is the likely
origin or local fetching is blocked. Supply the full relevant lead, its quoted/source links,
existing receipts and a clear remaining question; the current native packet still flattens
candidate summaries to 700 characters and omits much of the rich lead structure.

This is an evidence-gathering action, not a new approval gate. An already-inspected original can
go directly to writing. A strong secondary source can remain the receipt when it is genuinely
the best available source. A normal reporter should not have to reconstruct a hack or demand
an official statement before covering credible original journalism.

Evaluate the routing change on fixed worthwhile questions first. Make use of the current
one-assignment allowance before increasing the global writer-round or context budgets. If a
good direct source chain demonstrably needs another hop, consider targeted room for that case,
not more calls for every batch. Avoid a compulsory native call for every tip.

### C. Define successful research by the question answered

Useful question shapes:

- **Quote:** Where did this person say it, when, and what is the important context?
- **Action:** What announcement, filing, ruling or original reporting establishes what changed?
- **Data:** Who measured it, for what period, and when did that result first become available?
- **Incident:** What does the affected organization or credible investigating source actually
  establish, and what remains uncertain?
- **Journalistic exclusive:** Which report originated the claim, and is there a public underlying
  artifact? Do not require one if the original reporting is sufficient.

Carry a short source trail into the writer/editor handoff: tip; original/best supporting source;
event and disclosure dates; supporting findings; remaining uncertainty; reason for stopping.
Keep it descriptive, not a mechanical requirement for a particular source count or tier.

### D. Measure reporting outcomes, not tool activity

Track whether useful evidence was acquired, whether an original was found when relevant,
whether it was already in intake, whether a fallback answered the question, and which clock
actually limits delivery. Separate “original unavailable after an attempt” from “not sought.”
Keep attribution and opinion uncertainty in the final copy. Do not aim for a 100% primary-source
rate or a minimum research-call count; original journalism, practical speed and cost still matter.

## Next validation set

Use Lummis original versus restatement, Liquid original-statement discovery, the abbreviated
transaction-link failure, the IBIT stale disclosure, one blocked page with a useful native
alternative, and a clean direct-primary case that should require no additional research.
Include obvious non-news controls so better research does not simply create more spending.

Check source identity/date, inspected versus paraphrased content, claim scope, latency and
incremental cost. Do not export test drafts to Typefully without an explicit replay request.
The existing research slot has not been exercised in this production window; raising broad
budgets or changing models is not the first supported recommendation.

## Supporting records

- `prompts/orientation-examples.md`: original Lummis, Liquid, Coldcard and source-shell traces.
- `audit/speed-performance.md`: corrected original-source versus peer timing.
- `ROSTER-REPLAY-FINDINGS-2026-09-05.md`: native IMF control and its limitations.
- `SPRINT-0059-FINDINGS.md`: nine-run routing experiment, zero native assignments, unshipped wording.

All current-window observations were read-only production queries. No code or runtime behavior
changed as part of this assessment.
