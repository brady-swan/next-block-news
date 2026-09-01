# Next Block News: Inbound News Flow

**Production reference — September 1, 2026**

This document describes every path by which a news candidate currently reaches Next
Block News (NBN), when each path runs, and how all paths converge into the same editorial
funnel. It describes live production configuration, not merely code defaults.

## At a glance

```text
NBN native discovery                              Marketing Node discovery
--------------------                              ------------------------
RSS feeds          every 1 minute                 Wire Pulse hourly, 5am-8pm CT
SEC EDGAR           every 1 minute                   |- Perception: 6 searches
X account watches  every 3 minutes                   |- 24 RSS feeds
Perception         every 15 minutes                  |- 10 X searches
                                                      `- active Node themes
        |                                                   |
        |                               NBN polls Node every 5 minutes
        |                                                   |
        +--------------------> canonical URL dedupe <-------+
                                      |
                             freshness/language gates
                                      |
                           model triage (up to 25 items)
                                      |
                     fetch source and seek better receipt
                                      |
                         writer -> gates -> editor
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
| Morning Block | Weekdays at 14:40 UTC | 9:40 a.m. CDT / 8:40 a.m. CST; one-hour catch-up window |
| Afternoon Block | Weekdays at 21:15 UTC | 4:15 p.m. CDT / 3:15 p.m. CST; one-hour catch-up window |

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
4. **Tier 3 detectors.** WatcherGuru, CoinDesk, The Block, Bitcoin Magazine,
   BitcoinNewsCom, TFTC, and Bitcoin Archive. These are tips: NBN must find an eligible
   underlying receipt before publication.

When a primary or research account links to exactly one external public page, NBN uses
that page as the candidate URL and retains the X post as context. Detector posts remain
tips and enter source resolution before they can become receipts.

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
- Adds matching active Node theme IDs as context.
- Generates a versioned event-key hint and stable reference/candidate identifiers.
- Returns at most 24 candidates.

Themes influence surfacing and ranking context; they do not approve a story. Node titles,
summaries, relevance, confidence, and event keys are untrusted discovery hints to NBN.

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
- Deduplicates against URLs already known from native NBN discovery.

If the current v2 pulse is missing, stale, incomplete, or invalid, NBN may fall back to
the legacy Daily Intel `more_reads` candidate projection for the current UTC date. That is
a failure path, not the normal one-off discovery route.

## 3. Shared intake gates

All sources converge before model judgment.

1. **Canonical URL deduplication.** Tracking parameters are removed while meaningful
   query parameters are retained. The first ingestion provenance is immutable. A Node
   pulse may attach context to an existing still-new row, but cannot rewrite a processed
   item.
2. **Freshness.** During weekdays from 7:00 a.m. to 7:00 p.m. Eastern, the normal maximum
   age is 2.5 hours. Overnight and weekends it is six hours. Parsed stale items are skipped
   before a model call.
3. **Language.** Titles with more than 30% non-Latin letters are skipped before triage.
4. **Batching.** Up to 25 pending items are sent to triage in one cycle. Excess items stay
   pending for the next minute's cycle.

## 4. Editorial funnel

### Triage

The triage model assigns `draft`, `update`, `hold`, or `skip`; creates or reuses the stable
NBN story key; and proposes a post class. It sees already-published and still-open story
keys so separate reports about the same event converge.

There is no target quota. Discovery volume should not force publication.

### Source resolution and verification

For `draft` and `update` decisions, NBN fetches the page and independently classifies its
receipt quality:

- **P0:** official or primary source.
- **Tier 1:** premier reporting.
- **Tier 2:** approved reporting or research/data.
- **Tier 3:** discovery/corroboration lead only.
- **Unknown/lower:** not autonomously receipt-eligible.

A Tier 3 or weak source triggers an upgrade search for a primary source or stronger
reporter. Web search is therefore a research step, not a raw inbound feed. A second-tier
publication can alert NBN to an event without becoming the link in the final post.

Retryable network failures are persisted and retried after five minutes. Editorial holds
are kept separate from infrastructure failures.

### Writer, deterministic gates, and Editor

The Writer drafts only from the selected source text. Deterministic gates check freshness,
style, numbers, receipt integrity, source support, and data-provider attribution. The
Editor then publishes, revises, or spikes the surviving copy.

The same complete stack runs whether autopost is on or off.

## 5. Delivery outcomes

- **Autopost on:** eligible primary/corroborated copy can be scheduled through Typefully.
- **Autopost off:** the same approved copy lands as a Typefully draft for human release.
- **Held:** an editorial or evidence gate stopped the candidate; the Desk can stage or
  dismiss it.
- **Skipped:** the candidate was stale, duplicate, out of scope, weak, or otherwise not
  worth advancing.
- **Researching/retry:** an external fetch or search failed transiently and will retry.
- **Tape/failed/uncertain:** the publishing rail could not give a normal confirmed result.

## 6. Morning and Afternoon Blocks

Blocks are a separate batch product, not another one-off candidate feed. On weekdays NBN
fetches the latest Marketing Node Daily Intel brief, removes Swan-specific framing, adds
independent one-off wire items published since the previous Block, and builds a 5-9 post
thread from citations already present in those inputs.

- Morning Block: 14:40 UTC.
- Afternoon Block: 21:15 UTC.
- Each has a one-hour catch-up window and a once-per-window database guard.

If Wire Pulse v2 is healthy, the Daily Intel brief does not normally feed individual NBN
posts. Its `more_reads` list is retained only as the Wire Pulse fallback described above.

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

