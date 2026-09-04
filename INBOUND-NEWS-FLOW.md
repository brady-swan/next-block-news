# Next Block News: Inbound News Flow

**Production reference — September 4, 2026**

This document describes every path by which a news candidate currently reaches Next
Block News (NBN), when each path runs, and how all paths converge into the same editorial
funnel. It describes the Plan 0052 production flow and its rollout controls.

## At a glance

```text
NBN native discovery                              Marketing Node discovery
--------------------                              ------------------------
RSS feeds          every 1 minute                 Wire Pulse hourly, 5am-8pm CT
SEC EDGAR           every 1 minute                   |- Perception: 6 searches
X account watches  every 3 minutes                   |- 24 RSS feeds
Perception         every 15 minutes                  |- 10 X searches
                                                      `- active Node theme signals
        |                                                   |
        |                               NBN polls Node every 5 minutes
        |                                                   |
        +--------------------> canonical URL dedupe <-------+
                                     |
                  RSS + EDGAR -> Haiku semantic mailroom
                  priority | candidate | background (omitted)
                                      |
                      Haiku assignment desk (all lanes)
                         advance | background (audited)
                                      |
                     one fresh compact Sonnet newsroom
                    retrieve/delegate/search/fetch -> dossier
                                      |
                 consequential mechanical rails -> Sonnet editor
                                      |
                           Typefully / tape / hold
```

The NBN worker wakes every **60 seconds**, continuously. Adapters with a slower cadence
return no items until their own timer is due.

## Production timing

| Inbound path | Production cadence | Coverage window / delay |
|---|---:|---|
| Native NBN RSS | Every 60 seconds | Up to 30 current entries per feed |
| SEC EDGAR | Every 60 seconds | Bitcoin-mentioning 8-Ks filed today or yesterday; up to 25 hits |
| Native NBN X watches | Every 3 minutes | `since_id` means only posts newer than the last successful query; initial watch starts with six hours |
| X public-list membership | Refreshed hourly | A roster change made in X reaches NBN within approximately one hour |
| Native NBN Perception | Every 15 minutes | `bitcoin`, yesterday through today; up to 50 results |
| NBN poll of Marketing Node | Every 5 minutes | Each valid Wire Pulse is consumed once; pulse must be no more than three hours old |
| Marketing Node Wire Pulse | Hourly, **5:00 a.m.-8:00 p.m. America/Chicago**, every day | Searches the preceding eight hours; returns at most 24 curated candidates |
| Automatic research retry | Five minutes after a retryable fetch/search failure | At most one normal automatic retry after the initial attempt |
| Morning EIC cited reads | Weekdays at 14:40 UTC | Enter ordinary one-off intake; one-hour catch-up window |
| Afternoon EIC cited reads | Weekdays at 21:15 UTC | Enter ordinary one-off intake; one-hour catch-up window |

Autopost does not affect discovery, triage, research, writing, or editing. It only changes
the final Typefully delivery mode for copy that survives the complete funnel.

## 1. Native NBN discovery

### RSS and official feeds — every minute

NBN directly polls these feeds:

- Primary/official: Federal Reserve, SEC press releases, CFTC.
- Bitcoin/industry: Bitcoin Magazine, CoinDesk, The Block, Cointelegraph.
- Markets/macro: Bloomberg Markets, CNBC, The Wall Street Journal, Fox Business.
- Newswire: PR Newswire Financial Services.

Each feed failure is isolated; one unavailable feed does not stop the rest of the cycle.
Bitcoin Magazine's current `403` is therefore visible but non-fatal.

An RSS item's publisher is only its discovery provenance. Its URL is independently
classified against NBN's source registry before it can serve as the published receipt.

### SEC EDGAR — every minute

NBN searches the SEC full-text endpoint for 8-K filings containing `bitcoin`, bounded to
today and yesterday. An EDGAR filing is a primary-source candidate. It is not rejected for
lacking a precise publication timestamp because the SEC query itself bounds its age.

### X account watches — every three minutes

NBN uses X recent search, not a list timeline. Every query persists a `since_id`, so quiet
polls return no posts and previously seen posts are not repeatedly ingested.

The watch has four parts:

1. **Public primary roster — “Next Block News Follows.”** Membership is managed in X,
   fetched hourly, and compiled into `from:` searches.
2. **Officials and company newsrooms.** Sen. Lummis, Rep. Tom Emmer, BitGo, NYDIG,
   Coinbase, Strategy, Galaxy, BlackRock, Fidelity Digital Assets, Bitwise, Grayscale,
   River, Strike, Unchained, Casa, and Swan.
3. **Tier 2 research.** The Kobeissi Letter and Barchart. These accounts may support
   their own analysis or data, not unrelated claims.
4. **Bitcoin-news guide accounts.** BitcoinNewsCom, Bitcoin Archive, Bitcoin Magazine,
   TFTC, and Simply Bitcoin. Every original news-bearing post or linked story gets priority intake and a
   corroboration attempt. The account is an attention/format signal, never the receipt.
5. **Broad detectors.** WatcherGuru, CoinDesk, The Block, and Blockworks. These remain ordinary tips:
   NBN must find an eligible underlying receipt before publication.

When a primary or research account links to exactly one external public page, NBN uses
that page as the candidate URL and retains the X post as context. Guide posts remain
distinct leads so they cannot disappear behind an already-ingested RSS URL; their linked
pages are retained as untrusted research hints. Eligible P0/Tier 1/Tier 2 links receive
a bounded direct fetch/assessment before broad web search. Detector and guide posts enter
source resolution before they can become receipts.

Guide metadata is written as one versioned `guide-signal-v1` object and recognized from
the normalized author handle regardless of query route. Duplicate new items merge this
attention signal symmetrically with Node provenance; terminal items never change. Under
the 8 KiB limit, guide metrics, outbounds, then text are shed before the enrichment is
omitted, so valid Node context is never truncated.

### Direct Perception — every 15 minutes

NBN directly searches Perception's aggregated feed for `bitcoin`, from yesterday through
today, with a maximum of 50 results. This path is currently enabled in production.

It overlaps with the Marketing Node's Perception discovery. Canonical URL deduplication
prevents the same article from entering editorial judgment twice, but this is still a
provider-usage overlap worth measuring during the Wire Pulse trial.

## 2. Marketing Node Wire Pulse

The Marketing Node generates a source-only pulse every hour from 5:00 a.m. through
8:00 p.m. Central, including weekends. The pulse uses no language model. It gathers,
clusters, filters, ranks, and labels candidates deterministically.

### Node inputs

Each pulse looks back eight hours across three provider families.

#### Perception

Six searches:

- `bitcoin`
- `bitcoin etf flows`
- `bitcoin regulation legislation`
- `strategic bitcoin reserve`
- `bitcoin mining lightning protocol`
- `bitcoin custody security`

Perception responses are cached by exact request for four hours. Hourly pulses therefore
reuse Perception results between cache refreshes while still refreshing RSS and X.

#### RSS

The Node polls 24 feeds:

- Bitcoin: Bitcoin Magazine, Nakamoto Institute.
- Crypto/industry: CoinDesk, The Block, Cointelegraph.
- Financial/business: The Wall Street Journal, The New York Times Business, CNBC,
  The Washington Post Business, MarketWatch, Fortune, Fox Business.
- Technology: Wired, TechCrunch, The Verge, Ars Technica, MIT Technology Review.
- Macro/institutional: Bloomberg Markets, Financial Times, The Economist,
  Federal Reserve.
- Policy/regulatory: BBC Business, Politico, SEC press releases.

#### X

The Node runs ten recent-search families, with up to ten posts per family:

- Swan mentions.
- Bitcoin ETFs and institutional custody.
- Bitcoin-native companies and competitors.
- Bitcoin regulation, legislation, and strategic reserves.
- Bitcoin-linked macro, Federal Reserve, inflation, and geopolitics.
- Ownership, self-custody, and advisor themes.
- Bitcoin retirement and tax-advantaged accounts.
- Swan leadership accounts.
- ETF issuer accounts.
- Policy and regulator accounts.

### Node curation

The deterministic Curator:

- Clusters multiple references to the same apparent event.
- Requires the selected primary reference itself to contain an explicit Bitcoin signal.
- Rejects candidates below the deterministic relevance threshold.
- Prefers official and research receipts, then reporting, then discovery sources.
- Labels candidates as new/developing/unknown based on timestamps.
- Adds up to eight matching active Node theme signals. Recent Node classifier assignments
  at confidence 0.80+ are preferred; a conservative exact taxonomy fallback is used when
  no assignment exists, with negative examples acting as vetoes.
- Generates a versioned event-key hint and stable reference/candidate identifiers.
- Returns at most 24 candidates.

Before projection, the wire-specific sanitizer compares every related ref directly with
the selected rank-1 source under a closed exact-event anchor rule. It may only subtract
refs; it never joins, splits, or re-homes a cluster. All emitted headline/summary/event,
date, theme, confidence, source-count, and reason fields are then derived from rank 1 plus
surviving refs. Additive alignment diagnostics report repairs without changing the v2
candidate or theme contracts.

Ranking is confidence → primary role → source tier → freshness bucket → eligible theme
activity → exact timestamp → candidate ID. Theme activity can therefore break only an
otherwise-equal attention tie. It does not approve a story, cross a stronger source or
freshness bucket, or create a target output count. Node titles, summaries, relevance,
confidence, themes, and event keys are untrusted discovery hints to NBN.

### NBN consumption of a pulse

NBN checks the authenticated Node API every five minutes. A Wire Pulse must be complete,
schema-valid, internally consistent, and no older than three hours. NBN consumes each run
exactly once, including valid zero-candidate runs.

For each candidate, NBN:

- Validates the candidate and reference identifiers.
- Revalidates that every URL is public HTTP(S).
- Examines up to three Node-ranked references that NBN independently classifies as
  Primary/Tier 1/Tier 2.
- Takes ordinary intake fields only from the selected source reference.
- Does not trust the Node's summary as evidence.
- Independently validates rank-1 identity and headline/event anchors. A primary mismatch
  becomes a normal candidate with only minimal run provenance. If a related ref is dropped,
  all Node hints that might depend on it are removed rather than recomputed in NBN.
- Deduplicates against URLs already known from native NBN discovery.
- Strictly validates the optional versioned theme packet and derives a bounded seven-day
  advisory coverage snapshot from NBN's own tagged publications and open Typefully drafts.
  Untagged history remains `coverage_known=false` rather than being called uncovered.

If the current v2 pulse is missing, stale, incomplete, or invalid, NBN may fall back to
the legacy Daily Intel `more_reads` candidate projection for the current UTC date. That is
a failure path, not the normal one-off discovery route.

## 3. Shared intake gates

All sources converge before model judgment.

1. **Canonical URL deduplication.** Tracking parameters are removed while meaningful
   query parameters are retained. The first ingestion provenance is immutable. A Node
   pulse may attach context to an existing still-new row, but cannot rewrite a processed
   item.
2. **Haiku RSS/EDGAR mailroom.** One cheap semantic pass classifies newly persisted RSS and
   SEC EDGAR cards as `priority`, `candidate`, or `background`. Priority wakes the Sonnet
   desk immediately and sorts ahead of the 25-card cap. Candidate follows the normal
   15-minute cadence. In enforcement mode, Background is retained in the audit trail but
   omitted from Sonnet; the Desk owner can send it back exactly once with **SEND TO DESK**.
   The mailroom does not research, corroborate, cluster, write, or decide publication.
   Model, validation, capacity, and packet-bound failures all fail open as Candidate.
3. **Run-scoped Haiku assignment desk.** At the due boundary, Haiku distills and routes
   candidates from every lane as `advance` or `background`. Guide, Node, official, operator,
   retry, and unresolved-continuity work is protected; every error fails open. In enforce mode,
   an all-Background batch does not wake Sonnet. Background remains visible and promotable.
4. **Same-event companions.** When one member of a Haiku run-local exact-event group advances,
   code advances the group's Background companions too and records which candidate anchored the
   promotion. This is desk organization only: Sonnet still determines canonical event identity,
   evidence sufficiency, news value, and publication. An all-Background group stays Background.
5. **Mechanical eligibility.** Exact URL duplicates, unsafe inputs, and clearly unusable
   language are handled in code. Semantic freshness and news value belong to the models.
6. **Batching.** Up to 25 pending items enter one preparation/newsroom run. Excess items stay
   pending for the next minute's cycle.

## 4. Editorial funnel

### Run-scoped Sonnet newsroom

One fresh Sonnet context owns each prepared intake run: research, exact-event
grouping, news judgment, and writing. It does not persist across runs. This gives the model
the whole current news picture without creating an immortal conversation or losing NBN's
durable database state.

Sonnet receives a deliberately organized editorial desk rather than raw records:

- one stable intake card per candidate, separating what arrived, why it surfaced, and
  whether it is a tip, an uninspected official lead, or a potential receipt;
- the Haiku assignment summary/research objective and code-prefetched receipts;
- a separate board of uninspected intake, Node, and guide-account URLs;
- separate exact-event boards for recent reader coverage, open Typefully drafts, and other
  recent decisions;
- compact indexes for recent posts, continuity, and a broad Node theme board, with bounded
  retrieval of full records; and
- a small verified-handle spelling directory.

Raw Node envelopes and unrecognized metadata do not reach the model. Node summaries,
event hints, themes, guide posts, and engagement counts remain untrusted attention/context,
never evidence.

Sonnet may submit immediately, retrieve full indexed context, fetch intake pages, search SerpAPI,
fetch public results, or give one focused two-round reporting assignment to Haiku. Haiku's memo
is context, not evidence; inspected code-generated `fetch_id` records are evidence. Sonnet then
submits one dossier with a disposition for every candidate and one exact-event record per story.
A malformed story defers only its own members, while an omitted candidate returns on a later run.
There is no forced survey or minimum research phase.

Story keys identify exact events, not themes. Recurring purchases, filings, reports, and
readings include their event/disclosure date (or at least month and year when the day is
unknown). Deterministic actor, event-type, date, direction, numeric, and narrow yield guards
can veto unsafe grouping. Existing canonical aliases and exact prior-coverage checks remain
authoritative.

There is no target quota. Discovery volume should not force publication.

For Node-tagged candidates, the newsroom sees Node activity and the exact NBN coverage
snapshot later shown on the Desk. A theme is a broad ongoing subject, not an event cluster:
it cannot satisfy evidence or corroboration, merge story keys, force a post because coverage
is unknown/thin, or suppress a material distinct development because the theme was covered.

### Selective source resolution and verification

During research, Sonnet chooses which promising leads need inspection and where a stronger
source is needed. NBN independently classifies every fetched page's receipt quality:

- **P0:** official or primary source.
- **Tier 1:** premier reporting.
- **Tier 2:** approved reporting or research/data.
- **Tier 3:** discovery/corroboration lead only.
- **Unknown/lower:** not autonomously receipt-eligible.

Bitcoin Policy Institute's site and `@bitcoinpolicy` account are a scoped first-party research
source: BPI's own published research and stated findings may stand alone without corroboration.
Claims about third parties that BPI merely cites retain the normal evidence standard.

A Tier 3 or weak source is a lead, not a receipt. Sonnet can inspect eligible pages already
supplied by the Node or linked by a guide account, query SerpAPI directly, and fetch stronger
official/research/reporting results. NBN reclassifies every requested and final redirect URL
against its own registry. The search snippets are never evidence. Search is therefore a
research step, not a raw inbound feed. A second-tier publication can alert NBN to an event
without becoming the link in the final post.

Search is resilient across fresh Sonnet sessions. Exact normalized SerpAPI queries use a bounded
one-hour local cache. Their uninspected result pointers may follow only the exact candidate IDs or
already-persisted story key Sonnet names and remain reusable for six hours. This avoids paying for
the same lookup and prevents useful research leads from disappearing at the next 15-minute run;
the page still must be fetched before it becomes evidence.

NBN checks SerpAPI's free account-status endpoint at most once every five minutes across workers.
Confirmed quota exhaustion waits for the provider renewal time, rate limits honor a bounded
`Retry-After`, and transient provider failures use a short shared cooldown. Cached results remain
available while the provider circuit is open. At an expired quota boundary, one worker owns an
expiring half-open probe so a failed status endpoint cannot leave search permanently disabled.
The Desk distinguishes provider HTTP attempts, cache hits/misses, provider skips, pointer reuse,
and typed search/fetch failures.

URL classification decides only whether a fetched page may be considered. Sonnet proposes
support/originality from inspected text, but code reconstructs the source record from
code-owned URL, redirect, ownership, tier, byline, artifact, and fingerprint fields. The
desk and editor may support copy from several inspected receipts and choose the best useful
link for the reader. One credible inspected report is sufficient for routine narrow claims;
elevated allegations normally need an official artifact or two independent reports. Timeouts
and weak sources invite narrower attribution, a human draft, or a later retry—not an automatic
whole-story veto.

### Writing, deterministic gates, and Editor

The same Sonnet run writes after seeing the prepared batch and inspected research. Code keeps
only consequential rails: safe URLs, exact duplicate delivery, non-empty/length constraints,
verified mentions, investment instructions, and verbatim quote support. Freshness, importance,
scope, semantic novelty, source sufficiency, and numerical materiality remain editorial calls.
The independent Sonnet editor can publish, revise, draft, or drop each surviving story. If a
valid response omits candidates, one smaller recovery call handles only those omissions.

Before delivery, Sonnet labels each story `distinct`, `same_event`, or `material_update`. NBN then
checks every output in the canonical event family. An open, untouched draft may be updated in
place; a scheduled, publishing, published, human-edited, comment-marked, or ambiguous output
suppresses a blind duplicate. Once readers may have seen the event, only a genuine material
development may produce a separate `UPDATE:`. These rules are unchanged when autopost is enabled.

The legacy path is a manual rollback only; v2 never falls into it automatically. A same-session
transport retry is allowed, but a billed Sonnet session is never replayed from scratch after a
protocol error.

The same complete stack runs whether autopost is on or off.

## 5. Delivery outcomes

- **Autopost on:** eligible primary/corroborated copy can be scheduled through Typefully.
- **Autopost off:** the same approved copy lands as a Typefully draft for human release.
- **Ambiguous publisher write:** a durable mutation intent suppresses retry and appears on the
  authenticated Desk for reconciliation or explicit owner resolution.
- **Held:** an editorial or evidence gate stopped the candidate; the Desk can stage or
  dismiss it.
- **Skipped:** the candidate was stale, duplicate, out of scope, weak, or otherwise not
  worth advancing.
- **Researching/retry:** an external fetch or search failed transiently and will retry.
- **Tape/failed/uncertain:** the publishing rail could not give a normal confirmed result.

## 6. Morning and Afternoon EIC discovery

The scheduled multi-story Blocks are disabled. On weekdays NBN still fetches the latest
Marketing Node EIC brief at 14:40 and 21:15 UTC, verifies its date, window, source Daily Intel
run, receipt timestamp, generation timestamp, and maximum age, then adds up to 12 cited
`more_reads` links to ordinary one-off intake. Node prose remains an untrusted discovery aid,
never evidence. Each story must be researched, selected, written, and edited independently.

The former 5-9 post Block builder remains in `nbn/briefing.py` behind the explicit
`NBN_BRIEFING_ENABLED=true` rollback/experiment flag. It is off by default and in production.

## 7. Current overlap and how to measure it

The overlap is intentional during calibration but should be measured:

- NBN and the Node share several RSS outlets.
- Both services currently query Perception.
- Both inspect X, although NBN uses a tightly curated account watch with durable
  `since_id`, while the Node uses broader topical searches.

NBN collapses overlap by canonical URL before triage. For evaluating the Node, distinguish:

1. Candidates returned by each Wire Pulse.
2. Candidates already known to NBN.
3. Genuinely new Node-origin URLs.
4. New URLs considered by triage.
5. Drafted, published, held, and skipped outcomes.

The durable `discovery_origin` values are `rss`, `edgar`, `perception`, `x`, and
`marketing_node`. First-ingestion provenance means a story independently found by both
systems is credited to whichever URL reached NBN first; Node overlap may therefore be
useful without appearing as a Node-origin publication.
