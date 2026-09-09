# Perception integration — revision 2 / sprint 0071

September 9, 2026 UTC. **Owner authorized the revised plan, independent lead review,
implementation, deployment and smoke in turn01a0846d. Independent lead APPROVED main plan
and the bounded routing addendum below.**
The earlier research below remains supporting evidence; this revision governs this release.

## Release scope and decisions

Build one coherent first release: durable Perception intake with richer retained material;
three precise Writer tools (coverage/entity search, article read, regulatory search); short-lived
query caching and 30-day reporting-artifact reuse; a small scheduled subject survey; existing
Desk telemetry; and the resumed audit's outcome checks. No new researcher, knowledge graph,
model roster, publication rules, compulsory research, or image provider. Autopost stays OFF.

Keep broad Perception intake at its existing 900-second interval initially. Do not silently slow
primary RSS/X, alter Marketing Node settings, or promise complete Perception coverage. Preserve
one bounded next-page checkpoint across worker cycles; poll newest page periodically while
making bounded progress through a frozen overlapping date window. Commit collector progress only
after items AND source artifacts are durable. Expose backlog/partial coverage; date-only and unstable
pagination cannot support an exactly-once or lossless-streaming claim.

Live September9 capacity check: Node recorded62 MCP tools/call requests on each of September7/8
and roughly80+ REST attempts/day, many unsuccessful. It is a substantial shared consumer, not
the hypothetical40-call reserve in the earlier proposal. For NBN's new MCP work start with a
conservative **24 attempted calls/day total**, of which scheduled discovery uses at most8.
Unmetered initialization/taxonomy do not consume this local research allowance but remain bounded.
This is an NBN allocation, NOT knowledge of account-wide remaining capacity. Do not buy credits,
enable a paid fallback or change Node to fit it. Retain unknown shared consumption explicitly.
REST's provider-reported daily remaining and retry reset govern backoff, separately from MCP's
minute headers. Quota/auth failures are errors, never an empty research result. Scope/funding
uncertainty is a rollout limitation and audit watch, not a claimed exact bill ceiling.

## Writer budget and caching

Owner routing addendum: one Writer-facing interface and shared dated source artifacts, with
separate physical REST/MCP quotas and transport-specific query caches. A September9 Railway
parity probe returned the same six URLs for the plain keyword `Lummis` over September8–9.
Enable the alternate route only for plain single-keyword coverage searches with those same
date semantics (not entity/operator/subject/filter/regulatory/article equivalence). Prefer MCP
for Writer work to preserve REST intake headroom; use REST only after a definite MCP daily/local
capacity block, at most once, never after ambiguous timeout/shared-minute limiting. Count BOTH
surfaces against the24/day new-work allowance. After20MCP calls prefer REST for equivalent simple
queries, with at most4REST new-work attempts/day;20is NOT a specialist hard stop. Unknown account
remaining stays unknown, known cooldowns veto calls. This keeps REST research bounded for intake. This is routing
across documented access, not merging the vendor's balances or enabling purchased overage.

Reviewer implementation requirements: stable source-version IDs, no implicit commit within
item/artifact persistence, unchanged material never gets a fresh capture timestamp, explicit
provider-captured receipt provenance, both Writer allowlists, and optional failure semantics.

Keep production's six successful responses,360-second lifecycle,24 shared tool operations,
12 native-search operations, and existing fetch/context byte limits. Perception operations
count in the shared24, not the four local-memory retrieval slots. Apply remaining-time deadlines
and the existing final-submission reserve. Optional provider calls cannot force every story
through a new sequence. If fixed-case testing actually demonstrates useful reporting cut short
by six responses, bring the concrete result back before a separate six-to-eight adjustment.

Search cache: SQLite, restart-safe, exact normalized operation+arguments+date range+filters+contract
key, five-minute successful search TTL, one-minute legitimate empty result TTL. No failure-as-empty
caching. Do not round distinct filters/date windows into one key. A cache hit makes no provider
request but still consumes a model-requested tool operation/context when read. Per-run/cache/HTTP
attempt counts remain separate. Use one logical idempotency key per provider operation; no blind
retry of ambiguous requests, auth, quota or tool errors.

Article reuse: preserve source identity/URL, provider item ID, byline, original publication date
and precision, retrieval time, body vs summary/unknown completeness, truncation, links, image
pointers and content fingerprint. Strip vendor workflow suggestions from evidence payloads.
Short bodies are not made 'full text' merely by a provider heading. Store known text as
provider-captured material (not a direct HTTP capture or independent corroboration). Refresh
requests bypass reuse; changes create a dated version. Reading never renews evidence freshness.

Use existing writer_artifacts/notebooks/catalog. Save each useful operation before the next
network/model turn and link it to candidates/exact events only when identity is known.
Duplicate URLs may enrich evidence without changing first discovery, status, event keys,
owner comments, draft content or publication. Do not revive a skipped item merely because
the same text arrived through Perception. Search pointers are not article receipts.

Supply small relevant artifact links/dated excerpts beside existing continuation context:
previously read evidence, unresolved question, latest real editor outcome, actual current
draft/published state, and newly available material. Reuse existing projections, not copied
stale outcome fields. Full source text remains retrievable; the Editor receives selected
receipts through the existing exact-reference/appendix path. Retention remains30days.

## Advanced workflows in this release

An NBN-scheduled, persisted subject survey (up to8/day, one bounded call per slot) adapts
Perception's repeatable-workflow approach without inventing a hosted-job API. Alternate verified
custody/security, mining/energy, Bitcoin access/payment and policy subject groups. Survey outside
the Writer session using the existing worker boundary, with a short deadline so primary sources
are not stuck behind a briefing. No extra model pass.

Only returned source pointers enter normal intake; Perception trends/sentiment are context,
not verified events. Preserve dates and deduplicate across regular intake and previous surveys.
Existing preparation/writer/editor decide significance. Repeated unchanged rows must not
generate another candidate, wake or publication. Useful changed evidence can be linked for
an already-returning story without automatically reopening it.

Voice search and trend/narrative tools remain disabled/deferred until their recorded limitations
are resolved and a measured pilot shows usefulness. No owner Space/Brain creation, Perception
saved-notes database, vendor workflow activation, email scraping or founder outreach. Retain
the unsent founder feature brief for the account-wide capacity/incremental delivery discussion.

## Implementation slices

1. **Contracts/storage:** versioned fixtures from live schemas and representative JSON/SSE/markdown;
   narrow allowlisted REST/MCP adapter; request ledger, exact cache keys, bounded parsing,
   persistent cooldown/daily local cap, source artifacts and storage/duplicate tests.
2. **Intake/workflows:** migrate the in-memory broad-feed throttle to durable acknowledged
   checkpoints; preserve rich source artifacts on new AND duplicate intake; bounded pagination;
   subject-survey rotation/delta dedup and failure/backlog telemetry.
3. **Writer/memory:** three tools with small schemas, corpus/freshness limitations, read-through
   retained artifacts, existing fetch/receipt IDs and exact editor/memory source handoff.
   Candidate hints use existing compact catalog facilities. Prompt v2.30-perception-reporting.
4. **Desk/docs/audit:** extend existing System/source/research views with REST vs MCP local
   attempts, cached calls, reported quota scope/time, partial text, latency, backlog, artifact
   reuse and source contribution. No new website or hosting architecture. Preserve existing
   Railway-hosted React/Python Desk and its visual system. Add audit watches, synchronize saved
   automation prompt, restart the SAME15-minute heartbeat after successful deployment/smoke.

## Acceptance and rollout

Independent lead reviews this plan, then actual diff before release. Use offline fixtures/tests
for parser ambiguity/errors, JSON/SSE, escaping, date precision, cache isolation/expiry/refresh,
restart-safe quota and pagination, partial storage failure, duplicate enrichment, memory freshness,
claim/source identity, complete editor return, and optional-tool budget/finalization behavior.
Build/test the existing Desk bundle if changed. No live-model or Typefully test replay required.

One bounded live search/article/cached repeat smoke with existing credential proves transport
and no extra provider request on a cache hit; preserve exact inspected source scope and limitations.
Use remaining local/day capacity, never force a paid failure. Backup SQLite online, deploy a
clean archive of only the reviewed commit, verify runtime hashes, health/Desk, autopostOFF,
and a natural nonempty Writer run when available. Tool availability/fixture correctness is not
organic adoption. If no writer chooses Perception during smoke, report that limitation honestly.

Record deployed flag/budget values, latency/model-cost deltas, known account limitations and
rollback (feature disable/code-only, never destructive data restore). Pause audit before the build;
resume with new Perception checks and preserved18:20UTC historical checkpoint. Preserve unrelated
dirty evaluator files and existing comments. Do not rerun completed repairs or old user requests.

---

# Research and earlier proposal (superseded where revision 2 differs)


September 8, 2026 CT / September 9 UTC. **Proposal only; not implemented or approved for build.**

## Recommendation

Develop Perception into an active industry-specific discovery and reporting layer: a source of good
leads, original documents, context and follow-up opportunities. The goal is useful Bitcoin news that
our existing roster would find later or miss, as well as better reporting on leads we already have.
It should not become a second newsroom, a mandatory corroboration step, or another large briefing
pasted into every writer session.

Start with preserving the evidence we already receive, useful Writer retrieval tools and a small
targeted-discovery pilot. Then expand narrative intelligence against actual outcomes. Keep direct
primary feeds and X guides: Perception has not demonstrated enough coverage or freshness to replace them.

The existing Intelligence subscription and NBN Railway credential are sufficient to begin: the key
authenticated successfully to both REST and MCP. No new credential, subscription, Node dependency,
model roster change, publication policy, or autopost change is proposed. Autopost remains OFF.

Owner's follow-up emphasizes that Perception is our strongest paid discovery resource and that a
founder relationship makes targeted feature requests realistic. This expands the planning ambition;
it does not authorize implementation or outreach. See the [founder brief](docs/planning/perception-founder-brief.md).

## The larger opportunity: give Perception actual reporting assignments

Using the industry corpus well means asking questions that matter to NBN, not merely retrieving more
headlines. These are proposed jobs within the existing intake/Writer/memory system, not six new agents:

1. **Work editorial beats.** Survey consequential custody/security, mining/energy, ownership/access
   policy and real-world Bitcoin adoption. Use subjects and entities to find relevant material that
   never says Bitcoin in its headline. A broad subject match is a candidate, not a publication decision.
2. **Follow the entity through the story.** Entity-aware search can separate Block the company from
   The Block the publisher and gather related reporting. Fold this into the coverage tool as an entity
   mode, not a whole new tool. Use aliases returned by the provider rather than inventing identities.
3. **Answer an outstanding reporting question.** A Writer already retaining an unresolved question
   can search for the missing original, updated figures or clarification next time that story returns.
   Begin with those existing records; do not build a separate autonomous watch-task scheduler first.
4. **Find meaningful changes since our last coverage.** Compare newly observed material locally with
   the actual latest draft/published claim and storyline. Hand the Writer the new evidence and what
   readers already saw, rather than the whole theme again. A changed article is not necessarily a new
   event; it can also correct an older draft or settle a research question without another post.
5. **Look outside the usual relay chain.** Local-language reporting, primary company/agency documents,
   and conference/podcast material can give us a source before a guide account packages the story.
   This is a hypothesis worth testing, not a claim that our small samples prove a speed advantage.
6. **Develop added value from evidence.** On worthwhile stories, look for the comparison, timeline,
   affected group or original chart/data that explains why the news matters. Reuse the existing
   visual/PDF tools. Do not manufacture an extra angle or do background research when a short update
   already serves the reader.

There is also a useful coverage-check job: periodically compare a small Perception survey with NBN's
recent intake and outputs, then investigate plausible gaps. Keep that comparison inside NBN; there is
no need to send private drafts to Perception or reprocess every rejected story on every run. Do not
interpret a story we already drafted as a new discovery win.

### New opportunity probes after the follow-up

- Subject-only search across self-custody, merchant payments and mining pools found nineteen mentions,
  showing twelve in 1.67s. These included Galaxy's own IR page, X posts and conference/podcast links,
  alongside off-remit content. The result is promising source breadth, not nineteen qualified stories.
- Entity search for Block found two relevant bank-charter reports, from Bloomberg and The Block, in
  0.97s. This is an already-covered storyline and a useful retrieval example, not a newly established miss.
- A broad CLARITY voice query returned 92 earnings-record matches; refining to CLARITY Act reduced
  that to 24. Better queries matter. However, the refined output still contained 18,515 characters,
  no conference/podcast matches, and no original source URLs in the observed response. Date, speaker,
  source-type and output-size controls are concrete improvement requests, not reasons to abandon the corpus.

[New probe metadata](docs/planning/perception-opportunity-samples-2026-09-08.json).

### Work with the founder on the highest-leverage gaps

Prioritize a source-rich structured response, an efficient new/changed-item delivery path, and visible
source/corpus coverage. Ask what already exists privately or is being developed before building NBN
workarounds. An outbound-link list and honest text-completeness field could help immediately; a
source-lineage graph or signed push delivery could follow. Present observed discrepancies as
reproducible questions, not broad claims that Perception is broken.

Propose a design-partner trial only with owner approval. NBN could contribute concrete, selected
lead-to-source cases and measured outcomes. The [shareable brief](docs/planning/perception-founder-brief.md)
is prepared but unsent. None of the current integration improvements needs to wait for a new vendor feature.

## What “advanced workflows” means

This appears to be Perception's label for repeatable, multi-step research/monitoring, rather than a
separate model or a documented job API. Its guide offers combinations such as reputation monitoring,
partnership research and recurring executive briefings. The public Agent Workflows link currently
redirects to the documentation hub; I did not find a distinct public workflow-execution endpoint.
[Agent guide](https://perception.to/llms-full.txt), [documentation](https://perception.to/docs).

For us, a useful workflow is: a guide account raises a story; the writer searches related reporting,
finds the original statement, retrieves it, and writes a sourced post. Another is a periodic survey
that compares fresh coverage with NBN's existing storylines and identifies what changed. NBN already
supplies the scheduling, judgment, memory, editing and publishing machinery.

Do not confuse this with Perception's separately scoped commercial Systems service for custom
internal or customer-facing products. That is not automatically included custom development.
[Systems](https://perception.to/systems).

## What we actually do now

- `nbn/sources.py:fetch_perception` sends one broad `bitcoin` query, UTC yesterday through today,
  on a 900-second throttle. It reads page 1 only, requesting 50 items.
- It retains headline, source, URL, date and just 600 characters of Content. The store independently
  applies the same summary limit. Author, provider item ID, image pointer and remaining body are lost.
- Poll throttling is in process memory; the attempt time advances before success. There is no durable
  Perception intake checkpoint acknowledged after persistence, unlike the newer intake paths.
- Source health records counts/errors but not enough quota, pagination, body completeness or latency
  detail to distinguish a working connection from useful coverage.
- Existing URL deduplication is valuable, but a later Perception copy does not generally enrich the
  earlier item's evidence. First-discovery attribution alone therefore misses research assistance.
- NBN's writer does not currently have direct Perception research tools. It already has web/X search,
  source fetch, visual/PDF capabilities, reporting memory and storylines; extend those paths.
- The Marketing Node already has a narrow MCP client and uses several research calls in its brief.
  Reuse implementation lessons, not its runtime or a new cross-project service. Its usage must be
  included when allocating shared subscription capacity.

Code anchors: [collector](nbn/sources.py), [persistence](nbn/store.py),
[writer tools](nbn/reporter.py), [newsroom](nbn/newsroom.py), [memory](nbn/writer_memory.py).

## What the live tests established

These are small contract probes, not an exhaustive benchmark. Request metadata and source URLs are
saved in [the evidence file](docs/planning/perception-contract-samples-2026-09-08.json).
No drafts were created, changed or published.

| Test | Observed result | Implication |
| --- | --- | --- |
| MCP initialization/tool discovery | Existing key worked; live server advertised 32 tools | Access is available without a new key |
| CLARITY/Lummis mention search | Nine matches; first five returned in 1.33s | Useful fast paths to related coverage |
| Bitcoin Magazine article retrieval | 13.92s; “Full Text” was only a short feed summary | HTTP success/full-text label does not prove a complete article |
| CFTC search and article read | Search found a speech; read returned substantial speech text in 1.75s | A concrete original-source retrieval capability |
| REST article bodies | Sample Watcher.Guru and Coinspeaker bodies contained 2,628 and 3,999 characters | NBN is discarding useful available material |
| 24-hour trends | Returned some older coverage and off-remit topics despite NBN context | Trend activity is not event freshness or editorial fit |
| Voice search | Older ETF document passages; no conference/podcast matches for the sample | Potentially useful, but not proven comprehensive statement discovery |
| Bitcoin Archive corpus | Zero posts in the tested window | Cannot replace our direct guide-account collection |

Two contract discrepancies matter: REST `limit=5` still reported a page size of 50 and returned ten
items; REST `Lummis CLARITY` returned zero while the MCP search returned matches. A single-keyword REST
query did work. Establish each surface's query semantics rather than assuming they match. The live
MCP samples were mostly presentation markdown, not the uniform structured rows suggested elsewhere.

The current reference, older integration pages, OpenAPI and live schemas are not perfectly aligned.
The OpenAPI lists nine paths while the public reference advertises eighteen. Build against verified
contracts and retain failures explicitly; do not blindly generate a client from the marketing table.
[OpenAPI](https://perception.to/openapi.json), [REST reference](https://perception.to/docs/rest).

## Phase 1 — Preserve evidence and make retrieval useful

### 1. A small provider adapter, not a general MCP framework

Add a narrow NBN Perception client for the operations below, with JSON/SSE handling, bounded timeouts,
HTTP versus tool-error classification, quota observations and fixture tests. The Node's client is a
useful reference. Do not inherit multi-hour caching for breaking searches.

Keep vendor-returned workflow suggestions out of NBN instructions. Normalize data, source links and
limitations; the external tool's suggestions to create charts or perform more searches are not orders.
Send only a short public NBN editorial remit in optional context, not private drafts or the full notebook.

### 2. Preserve the useful payload without enlarging every prompt

Keep the short intake preview, but store a separately retrievable source artifact containing available
text, original URL, publisher/author, provider ID, reported publication time, retrieval time and image
pointers. Record body length and whether extraction is partial/unknown; do not label every Content field
complete. Retain upstream links when supplied; a stripped body cannot be assumed to contain them.

Reuse the existing receipt/memory catalog and bounded retrieval. Do not put generic Perception payloads
into the existing X-only `source_material` format. Make the smallest compatible extension and keep
original first-seen time, event identity, publication state and owner edits unchanged.

A duplicate URL can add evidence to an existing item without creating another lead or waking a writer
just because the same text arrived again. Keep both first-discovery provenance and later evidence
contribution. Source images are candidates for existing inspection, not automatic publishing permission.

### 3. A purpose-built Writer tool suite — the centerpiece

Owner asked whether we should build precise tools for the Writer's research and writing; this is
incorporated as a proposal, not new implementation approval. Precision belongs in the retrieval
contract, while the Writer retains freedom over the
reporting strategy and final judgment. The names below are proposed NBN wrappers, not existing tools.

| Proposed Writer tool | Perception operations behind it | Use |
| --- | --- | --- |
| `search_perception_coverage` | `perception_search_mentions`; entity mode uses `perception_search_companies` | Find related reporting using a question/query, entity, date range, subjects, source, language or region |
| `read_perception_article` | `perception_get_article`, or an already-retained source artifact | Read a known URL, with its publication date when available; distinguish body from summary |
| `search_perception_official` | `perception_search_regulatory` | Find agency statements, filings or policy documents relevant to the claim; expose jurisdiction/source filters |
| `find_perception_statement` — conditional on coverage tests | `perception_search_voices` or a tracked-handle corpus query | Locate a quoted statement in transcripts or an account archive; say explicitly which corpus was searched |
| `explore_perception_context` — later, optional | A selected trend or narrative-momentum operation | Understand a continuing topic and locate related sources; return analytical context, not a verified event |

Ship the first three together. Validate statement search before advertising it as reliable; add the
context tool only after the scheduled trend experiment demonstrates usefulness. A tool name must not
promise a global original-source search when the underlying corpus is narrower.

Every return should have a consistent compact envelope: the question searched, result/source IDs,
original URLs, source identity/type, publication date and its precision, retrieval time, text or
snippet, relevant upstream links when present, and limitations. Also return whether more results
exist when the provider actually exposes that fact. Missing fields stay unknown. Larger text lives
behind existing artifact IDs; content already read must remain accessible to the Editor.

Keep wrappers narrow: normally one provider operation or a cache hit, not a hidden multi-call agent.
The Writer can chain them naturally. For example, a Lummis tip might lead to a coverage search, then
an article read, then the original statement using Perception or existing web/X tools. If the article
already resolves the question, no additional turn is required. If it is only an excerpt, the Writer
sees that limitation immediately. Tools support the writing; they do not write a competing draft.

Give each tool a short description of when it helps, what inputs it needs and what it cannot establish.
Avoid loading the full vendor catalog or prescribing an every-story sequence. Source choice and
publication judgment remain with the Writer and Editor under the agreed editorial guidance.

The live schemas also offer language, event-region and publisher-region search filters. These are
promising for finding a local original behind translated Bitcoin coverage. Use the versioned taxonomy
to form valid subject queries. Do not infer that multiple subject IDs mean AND: the live schema says OR.
[MCP reference](https://perception.to/docs/mcp).

Prefer existing local evidence when sufficient. Use Perception when it plausibly answers the missing
question, not on every story. If it returns only a summary, continue through the writer's existing web,
X or direct-fetch options when useful. An empty corpus result means “not found here,” not “did not happen.”

Route usable source text into the same receipt IDs, editor appendix and reporting memory as other
research. Distinguish provider-captured original text, provider-generated analysis, search pointers and
our model's interpretation. Reading an article about a speech is not reading the speech.

Keep the current writer time/response limits initially. Give network calls deadlines inside the remaining
session time, return explicit limitations on timeout, and retain completed work. Share existing tool
byte limits; do not enlarge the initial packet or silently consume all local-memory retrieval slots.
Instrument saturation before proposing more room. No new researcher agent or compulsory research turn.

## Phase 2 — Repair intake completeness and improve discovery

First verify pagination, date parsing, sort order and search syntax with fixtures and bounded live reads.
Use the returned pagination metadata, not an assumed page size. Persist progress only after item and
artifact storage succeeds. Use an overlapping time range and bounded catch-up; the feed does not expose
a verified updated-since cursor, so do not claim lossless streaming or exactly-once vendor delivery.
Surface backlog/truncation rather than silently claiming all results were collected.

Retain the general Bitcoin feed as one discovery source. Add a small number of scheduled subject-based
surveys for blind spots: meaningful custody/security developments; mining/energy consequences; Bitcoin
access and payment adoption; and material policy affecting ownership, use or access. Local-language
searches should follow a particular developing story, not spray every region on each cycle.

Respect the existing editorial boundaries: no routine wallet/payment software releases unless part of
a larger story; no expansion of treasury-company coverage; no generic price targets, altcoin launches,
or minor macro-stat updates. Perception metadata helps discovery but does not upgrade source authority
or bypass the existing preparation, writer and editor decisions.

MCP mention search has a bounded result limit without a documented pagination cursor. Treat these
surveys as supplements, not a guaranteed complete replacement for paged intake. Keep primary RSS and
X guide routes fast. Do not add another Haiku classifier solely because a provider was added.

## Phase 3 — Use narrative intelligence selectively

Start with a small trend survey at 6am, 10am, 2pm and 6pm CT, proposed for review. Include emerging
coverage, then inspect the underlying dated sources against recent NBN outputs and open storylines.
Supply only relevant changes to the existing preparation process, not an entire crypto digest.

The useful question is “What has changed in a story our readers care about?” not “What has a high score?”
A trend can reveal an overlooked development, a new jurisdiction, conflicting reporting, or a good
follow-up question. A repeated old article must not become NEW simply because it is trending today.
Do not turn provider trend IDs into canonical event IDs or replace NBN's storyline memory.

Later experiments, only if the initial results justify them:

- Compare our coverage with Perception's source-level view to find blind spots.
- Search a specific speaker's conference/podcast statements or tracked account history when a tip lacks
  its original. Validate actual corpus coverage first; the Bitcoin Archive test was empty.
- Import a user-curated Space if it contains genuinely unique leads. Owned Spaces and Brains have REST
  access, but we have not inspected the account's collections. Do not create or alter them implicitly.
- Use narrative/voice-cohort analysis for context on an important Bitcoin debate, with supporting sources.
  Avoid publishing sentiment scores as news by default.

Alerts may be worth an account-level test: the vendor describes 15-minute rule checks and Slack/email
delivery. I found no documented public webhook contract to build against. They are not demonstrated
instant alerts, and email/Slack scraping is not part of this sprint.
[Alerts](https://perception.to/features/alerts).

Defer analyst price targets, hiring rankings, routine insider/treasury activity, broad scenario analysis
and a second saved-research database. These can be useful products without being useful NBN priorities.
In particular, delayed holdings data must not be presented as current ETF trading-day flows.

## Capacity and cost

The current reference gives Intelligence 100 included MCP requests/day, a separate REST pool,
60 requests/minute across surfaces, and a separate 200/day full-text limit in addition to call usage.
Included MCP requests count one each; purchased-wallet usage has different weights. The live REST key
reported a daily limit of 100. MCP's observed `60;w=60` headers describe the minute window, not daily
remaining capacity. Do not confuse those counters or assume NBN owns the whole account allowance.
[Current usage reference](https://perception.to/api/reference).

Before changing cadence, measure the Node's actual consumption and whether a purchased wallet can be
charged automatically. No unapproved paid-overage fallback. Unknown quota state stays unknown in Desk.
Reuse short-lived search results and source artifacts; do not retry auth/quota errors as research gaps.
For retried reads, use the provider's documented idempotency mechanism for the same logical request.

At 15-minute intervals around the clock, NBN alone could attempt 96 feed calls/day before pagination
or Node usage. Simply adding every feature at that cadence does not fit the shared pool.

An illustrative starting allocation, contingent on measuring Node usage:

| Pool | NBN planning allocation | Remaining account headroom |
| --- | --- | --- |
| REST | 48 base polls/day plus up to 24 catch-up pages | 28 calls for Node/other use |
| MCP | Up to 40 writer calls, 8 targeted surveys, 4 trend checks, 2 audit checks, 6 reserve | 40 calls for Node/other use |

These are capacity allocations, not mandatory activity or publication quotas. The REST example implies
30-minute Perception polling; that is a fallback capacity example, not the recommended default or an
implemented change. With the founder channel now available, first ask about incremental delivery and
an appropriate newswire allowance. Preserve the speed objective rather than simply accepting a slower
polling schedule. If the current allowance must remain, choose the explicit cadence/pagination tradeoff
from measured source value and shared usage. Do not silently sacrifice coverage or run a shared pool dry.

Included capacity can avoid incremental provider charges, but NBN still pays for model tokens reading
results. Track those separately from the existing $499 subscription; do not call the integration free.
Confirm attribution/retention rights for the intended use. Keep original source links in reader receipts
and provider provenance internally; attribute proprietary Perception metrics if used. Do not expose a
public copy of the vendor archive or assume image rights follow from an image URL.

## Desk and evaluation

Add Perception to the existing Sources/System/Research views, not a separate dashboard:

- Last successful poll; data freshness; query/page count; unresolved backlog; errors and latency.
- REST and MCP use shown separately, observed remaining values with timestamp/scope, local estimates
  when necessary, and unknown shared consumption clearly labeled.
- Within a run: what the writer asked, what returned, which source/artifact reached the editor, partial
  text or empty results, and whether that evidence contributed to a draft or a reasoned drop.
- First lead versus later research assistance, primary-source upgrades, duplicate enrichment and
  confirmed published outcomes. Do not judge value only by first-discovery origin or draft count.
- Source publication → our first observation → writer delivery → draft → confirmed X publication.
  Vendor-indexing time remains unknown unless actually supplied; date-only results are not precise
  speed measurements. Separate replays from natural production.

Use a small fixed set of recent cases before enabling broadly: Lummis original-source follow-through,
BPI date/denominator context, a readable official document, a thin article, a blocked source, an old
trend, a non-English original and an absent X corpus result. Evaluate preservation and useful evidence,
not whether every case produces a post. No Typefully replay without separate approval.

Then observe seven days of normal operation: useful unique/earlier leads, source upgrades, time saved,
partial/empty retrievals, missed fresh stories, additional model cost and writer packet pressure. This
is an adoption check, not proof from one successful request or a statistically conclusive A/B test.

## Build order and acceptance

1. **Contract/capacity pass:** validate the discrepancies, capture fixtures, establish shared-pool
   consumption and a feasible cadence. Document what remains unsupported.
2. **One bounded first release:** source-artifact preservation, writer search/read access, receipt/memory
   handoff and telemetry. Include a small subject/entity discovery pilot within measured headroom so we
   test discovery value as well as retrieval. Keep optional voice/trend routes disabled until verified.
   No policy changes; use existing preparation and retain the established editorial boundaries.
3. **Discovery release:** durable paged intake and targeted surveys under the agreed call allocation.
4. **Observation, then expansion:** enable the small trend survey and only retain features that provide
   demonstrable editorial value. No requirement to wire all 32 advertised tools.

Before implementation, run the established independent lead review of the final scoped plan. Tests
should cover JSON/SSE, tool errors, malformed/empty results, UTC dates, truncated bodies, pagination,
quota backoff, duplicate enrichment, restart-safe persistence, receipt IDs and editor/source-reply
preservation. Smoke health/Desk/source telemetry with autopost OFF and inspect a natural nonempty run.
Roll back through feature flags/code, preserving accumulated evidence and all existing drafts.

No code, runtime settings, subscription, automation or publishing state changed while preparing this plan.
