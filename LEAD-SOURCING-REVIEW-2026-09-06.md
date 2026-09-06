# Lead sourcing: follow the Bitcoin conversation, then get upstream of it

September 6, 2026 · Analysis and recommendations, not an implementation plan or policy change.

Implementation follow-up: the owner approved the focused Plan 0062 lead-fidelity sprint.
Perception is explicitly deferred because its separate REST quota pool is exhausted. Standalone
software releases are excluded; releases can be developments in larger ongoing stories. The
phased plan/release record, not this wider idea inventory, defines what was built.

## The verdict

**NBN is now quite good at noticing our reference accounts. It is less good at receiving the whole story they are showing us, recognizing the full range of useful Bitcoin stories, and going directly to the people or records behind those stories.**

I would not begin by adding another broad news aggregator or making every polling interval shorter. I would begin with fuller lead packets, a small Bitcoin-native reporting beat, and better handling of time-sensitive evidence.

The most important distinction is between three problems:

1. **Discovery:** did we encounter the useful lead?
2. **Understanding and selection:** did we see enough of it, and recognize why readers would care?
3. **Conversion:** did a worthwhile lead become a supported, well-written draft promptly?

Adding sources fixes only the first. Several of our conspicuous delays—and some current rejections—belong to the other two.

## Evidence and limits

I inspected the live intake configuration, source collectors, guide metadata, newsroom tools, production records, accumulated editorial examples, and speed ledger. I also collected a bounded X API sample of **430 original, non-reply posts** across our five guide accounts, including long-post text, media metadata and public engagement counts. Selected examples were inspected in the browser for layout, imagery, video presentation and surrounding context.

The production and peer snapshots were taken around **2:09 PM Central on September 6**. Production includes 6,566 intake records first seen in the preceding seven days. Peer sampling requested the most recent 100 posts per account within seven days; Bitcoin Archive, Bitcoin News and TFTC had additional older results beyond that cap. Bitcoin Magazine returned 40 and Simply Bitcoin 90. These are not five complete, comparable weekly samples.

Engagement is a snapshot, not a causal experiment. Accounts have different audiences; posts have different ages; controversy and affirmation can inflate engagement. I did not independently fact-check every peer claim or watch every video in full. A linked example below establishes what the account posted and how it presented it—not automatic verification of the underlying claim.

Seven-day NBN results span multiple releases and source additions. The latest 24 hours are largely a weekend, not a representative weekday news cycle. Historical failures are labeled as historical rather than assumed to remain unfixed.

## 1. What Bitcoiners are coming for

My working editorial proposition is:

> Tell me what changed in Bitcoin, what it means for using or holding it, and what interesting things people are doing with it—early enough that sharing your post is useful.

That is broader than market news, but narrower than everything a Bitcoin personality discusses.

### The strongest beats

| Beat | A useful NBN story | What does not earn a post by itself |
| --- | --- | --- |
| Self-custody, security and access | A wallet vulnerability with affected versions and a remedy; withdrawal restrictions; a consequential custody or privacy change | A vague hack allegation; a transfer assumed to be a sale; unsupported advice to move funds |
| Bitcoin being used | A payment capability people can actually use; a merchant or community deployment; a concrete example of financial exclusion or censorship | A generic adoption slogan; a partnership announcement with no functioning product |
| Building and operating Bitcoin | A consequential mining or protocol development, public disclosure, or a software release that advances a larger ongoing story | Standalone software-version announcements; every pull request; a proposal presented as adopted; developer conflict without a substantive change |
| Rules governing ownership and use | A tax treatment, court decision, regulatory action or legislative development with an identifiable Bitcoin consequence | Another official expressing generic crypto skepticism; routine political commentary |
| Monetary developments and demand | Material inflation/debasement developments, consequential access or liquidity changes, meaningful ETF flow releases | Incremental yield ticks, seasonal trading statistics, price forecasts and technical-analysis setups |
| Bitcoin-native discovery and culture | A compelling working demo, useful new research, or strong reporting about Bitcoin in people's lives | Engagement bait, recycled inspirational quotes, or a requirement to manufacture a financial consequence |

The final row is the editorial choice I think we should discuss explicitly. A good Bitcoin feed need not require every worthwhile post to change markets or a protocol. A demonstrable project can be interesting on its own. That is not permission for filler, and it does not need a quota.

### What our own feedback already teaches us

The accumulated examples are consistent, not contradictory:

- The gold-correlation/debasement observation was useful; the trading-signal digression was not.
- Ireland's actual savings-wrapper exclusion was a story; generic national skepticism about crypto was not.
- Geyser/Cuba is about a real constraint on permissionless money, not another abstract freedom slogan.
- Wallet security and access changes matter because readers may need to understand or act on them.
- A routine small treasury-company financing is not rescued by having Bitcoin in the headline. Keep the high bar for Strategy, Metaplanet and Strive; do not reopen the roster through this sourcing review.
- An ETF release can be worthwhile without every subsequent reaggregation of the same numbers becoming another story.
- Clear, short sentences and one- or two-sentence paragraphs work. Additional detail must earn its space.

These observations suggest sourcing around **reader consequences and useful discoveries**, not around the mere presence of the word Bitcoin.

**Owner clarification, September 6:** Software releases are not a standalone NBN beat. Watch or cite a release when it is part of a larger story—for example, a Bitcoin Core version relevant to an ongoing protocol/governance story, or remediation within an established security incident. A new wallet or payment-software version is not itself a reason to post.

## 2. What the reference accounts actually do

| Account | Sample | Median text length¹ | Posts with direct media | Distinctive approach |
| --- | ---: | ---: | ---: | --- |
| Bitcoin Archive | 100 | 167 characters | 96% | One strong fact or contrast, immediate implications, visual support, often an identity-affirming finish |
| Bitcoin News | 100 | 288 characters | 74% | A broader Bitcoin beat; short headlines through longer explainers; concrete examples, clips, demos and community stories |
| Bitcoin Magazine | 40 | 151 characters | 100% | Very concise alerts, recognizable figures, strong numeric hooks and highly visual presentation |
| TFTC | 100 | 232 characters | 82% | Explanations and arguments, often a speaker-led clip; technology, freedom and monetary-system context |
| Simply Bitcoin | 90 | 132 characters | 61% | Bitcoin identity, accessible contrasts, recognizable advocates, clips, humor and audience participation |

¹ Full long-post text where supplied; character counts include links. “Direct media” excludes media that may appear only inside a quoted post. This measures these samples, not a recommended NBN length.

**347 of 430 posts had a direct image or video attachment.** Video alone accounted for 54 of TFTC's 100 posts. A text-only intake system is observing a materially incomplete version of these feeds.

### Transfer the useful technique, not every editorial choice

**Bitcoin Archive: make the consequence obvious.** Its [Netherlands gold-logistics post](https://x.com/BitcoinArchive/status/2095221321663684878) turns a large monetary story into a tangible logistical problem, using a short opening, two supporting bullets and an image. The sample recorded 2,202 likes and 199 reposts. We can learn the clarity and concreteness without adopting the insinuation that Bitcoin is unconditionally more secure. The image depicts guards, gold and an aircraft; it should not be treated as documentary proof of the reported operation.

**Bitcoin News: explain the interesting mechanism.** Its [OCEAN/BIP-110 post](https://x.com/BitcoinNewsCom/status/2095242224758108401) uses a clear headline and separated short paragraphs to explain a mining-pool decision and the consequence for rewards. At 226 likes and 29 reposts, it substantially outperformed that account's sample median of 35.5 likes. This is an example of useful longer-form presentation, not proof it was breaking: a visible reply disputes its freshness, which would require checking the underlying announcement.

Longer Bitcoin News posts are not inherently underperformers. Among its sampled posts at least 12 hours old, posts over 280 characters had a median of 50 likes, versus 30 for shorter posts. Topic, timing and selection differ, so this is **not evidence that length causes engagement**. It does support leaving room for a good explanation instead of imposing a rigid short-post rule.

**TFTC: make an explanation worth saving.** Its [Luke Gromen clip about insurers and Treasuries](https://x.com/TFTC21/status/2095977860972597283) received 682 likes, 81 reposts and 352 bookmarks in the snapshot. It is approximately five minutes long. The post names the speaker, foregrounds one argument, and connects the clip to a longer discussion. The useful lesson is a clear explanatory payoff—not that NBN should routinely relay alarming macro predictions, or that every video must be very short.

**Simply Bitcoin: make the reader's lived experience visible.** Its [Bitcoin-versus-Apple-Pay post](https://x.com/SimplyBitcoin/status/2096177075241590944) had 414 likes and 37 reposts. The attached image is a screenshot of an exchange in which a person identifies Iran as their location and describes payment exclusion. Without the image, it reads like a generic slogan. With it, we understand the human context. It still isn't established as a new event; the right lesson is to seek current, attributable examples of this experience, not to relabel an old screenshot as news.

**Bitcoin News also looks for things that are simply interesting to Bitcoiners.** The [mempool-music demonstration](https://x.com/BitcoinNewsCom/status/2096613927681401038), [Real Bedford profile](https://x.com/BitcoinNewsCom/status/2096592481525653872), and [Taipei Bitcoin hub video](https://x.com/BitcoinNewsCom/status/2096646800400605593) are a different editorial vocabulary from ETF flows and corporate treasuries. They expose builders, places, people and uses. Not all deserve an NBN post, but they deserve a category other than “no market-moving event.”

### The writing and visual principles I would carry forward

- Put the result, consequence, or interesting discovery first—not the executive's title or a long institutional setup.
- Give each sentence a job. Short paragraphs help, but line breaks cannot rescue overloaded sentences.
- Let one useful number establish scale. Add more only when they change the reader's understanding.
- Use attribution economically. Distinguish a speaker's interpretation from a reported fact without burying the lede.
- A longer post should unfold, not restate its opening in progressively denser language.
- Use a chart to show a relationship, a document excerpt to show the relevant wording, a demo to show a capability, or a clip to let a reader hear the statement.
- Keep receipt and illustration separate. A logo, dramatic stock image or screenshot is not automatically evidence. Preserve original context and dates, and use assets we have appropriate rights to reuse or link to the original.
- Do not delay an important supported text alert while hunting for decoration. Sources in the first reply remain the approved NBN format.

The strongest-performing posts also include price celebration, deterministic bullish claims, forecasts and explicit like-bait. **We should follow the guides' attention and curiosity, not optimize for their raw like counts.** Their audiences overlap ours; their full editorial products are not identical to ours.

## 3. How NBN sources leads today

These are the live collectors, not simply sources the registry permits us to cite.

| Lane | Current behavior | What it contributes / limits |
| --- | --- | --- |
| RSS | 12 feeds, up to 30 entries each; fetched during the worker loop | Fed, SEC and CFTC; Bitcoin Magazine, CoinDesk, The Block and Cointelegraph; Bloomberg Markets, CNBC, WSJ, Fox Business; PR Newswire Financial. Good reporting/official alerts, but much is broad finance. |
| X | Nominally every 3 minutes; one list-derived query plus five static query groups | Official/data accounts, senators, companies, research, five guides and fast detectors. Original and quote posts; replies and reposts excluded. |
| Perception | Every 15 minutes, keyword Bitcoin, yesterday/today, first 50 results only | Broad discovery, including secondary publications, X wrappers, Reddit and foreign-language reporting. Not just unique fresh events. |
| SEC EDGAR | Searches for Bitcoin in 8-K filings, first 25 hits over yesterday/today | A narrow keyword detector. Initial cards do not contain the actual substantive Bitcoin passage. It is not a comprehensive filing-change monitor. |
| Marketing Node | NBN checks for arrivals every 5 minutes; accepts bounded recent wire packets, with brief-related fallbacks/imports | Supplementary discovery and source pointers. Five-minute consumption does not make an upstream hourly pulse five-minute discovery. Upstream cadence is from the existing integration documentation, not a fresh Node scheduler inspection. |

The actual X list has 21 members: Farside, BPI, mempool, CoinGlass, Galaxy Research, Glassnode, The Block, Bitcoin Core, CoinDesk, BLS, Bitcoin Magazine, BEA, CFTC, BIS, Treasury, OCC, St. Louis Fed, FDIC, Federal Reserve, SEC and New York Fed.

Static queries add the five guides, Kobeissi and Barchart, legislative/company accounts, and fast detectors including WatcherGuru and Blockworks. Bitcoin Magazine and some reporting accounts appear in more than one query.

**Important: putting a source in `source_tiers.toml` does not subscribe to it.** We permit many official sources that we do not actively poll. Treasury is watched on X, for example; that is different from watching the specific official document or sanctions change we expect.

After ingestion:

1. Haiku routes RSS/EDGAR into Priority, Candidate or Background. Background stays out of the newsroom unless promoted; technical failures fail open.
2. Luna prepares the desk. Guide, official, continuity and owner-override protections preserve attention, but do not force publication.
3. Grok 4.3 medium receives a fresh newsroom session on the 15-minute cadence, with up to 25 candidates and relevant existing context. It can search, fetch and delegate native web/X research.
4. Grok 4.5 medium edits proposed stories. Delivery stages supported output in Typefully. Autopost remains off.

### The latest 24-hour intake

| First recorded origin | Unique intake records | Share | Linked new output rows² |
| --- | ---: | ---: | ---: |
| Perception | 226 | 61.2% | 1 |
| Direct X | 65 | 17.6% | 3 |
| RSS | 45 | 12.2% | 0 |
| Marketing Node | 33 | 8.9% | 1 |
| EDGAR | 0 | 0% | 0 |
| Total | 369 | 100%³ | 5 |

² Output rows linked to the originating item, not an editorial-quality score or attribution of all supporting evidence. Several drafts have tuning concerns. Another lane can enrich an event first found elsewhere. These are not independent-event conversion rates.

³ Individual percentages round. Item state at the snapshot was 364 skipped and five drafted; some early leads later resurfacing under other records make raw item disposition an imperfect measure of editorial recall.

The Node's one output in this window originated with a local mining-site story. That is a useful reminder: low volume does not mean zero unique value. Conversely, Perception supplying 61% of stored items does not establish that it supplies 61% of our useful news. I would make source decisions using incremental useful events and earlier discovery, not item volume alone.

## 4. The concrete gaps

### A. Capture is better than our historical experience might suggest

Exact post IDs from **406 of 430** peer posts appeared somewhere in NBN intake. The 24 absent posts were all Simply Bitcoin posts dated before its September 2 addition; they do not demonstrate a current hole.

More importantly, **all 74 sampled posts created in the last 48 hours were present**:

- Median guide-post-to-intake time: **1.87 minutes**.
- 90th percentile: **3.27 minutes**.
- Slowest in that subset: **4.53 minutes**.

This is exact-post capture, not proof of full-context delivery or qualified-story coverage. It strongly argues against beginning with “follow more aggregators” or treating current three-minute polling as our largest general problem.

### B. We are throwing away available meaning

The X collector requests ordinary text and basic metrics. It does **not** request `note_tweet`, media attachments, media-source identity or quoted-post expansions.

In the API sample:

- **78 posts** had full text longer than their ordinary API text.
- **42 of Bitcoin News's 100 posts** were affected by that difference.
- 35 full posts exceeded even our later 600-character guide-context cap.
- 58 posts referenced another post; that parent can contain the actual claim or evidence.
- 347 had direct media attachments that our initial intake does not represent.

Later source fetching can recover text, so this does not mean all 78 were ultimately truncated for the writer. But the model may already have formed its selection judgment from a fragment. Ordinary HTML text extraction also does not deliver an image, a video's contents, or a clean structured original-post relationship.

This is not an unavailable capability: X documents long-post text, media and reference expansions in its [post data model](https://docs.x.com/x-api/fundamentals/data-dictionary) and [recent-search API](https://docs.x.com/x-api/posts/search-recent-posts).

The source-in-first-reply convention creates another specific blind spot: excluding all replies is sensible for a clean feed, but we should selectively retrieve an author's own source reply when needed. We should not ingest everyone's replies as new candidates.

### C. Newborn engagement counts are influencing judgment

Eight stored dispositions over the last 48 hours mentioned low engagement or small like counts. Examples include:

| Lead | Likes in saved discovery context | Likes at research snapshot |
| --- | ---: | ---: |
| Simply Bitcoin's debt/money-supply commentary | 3 | 393 |
| TFTC's Rob Hamilton/Core development anecdote | 1 | 50 |
| TFTC's Michael Every episode promotion | 1 | 43 |
| Bitcoin News's Treasury-return statistic | 3 | 31 |

Some skips remain entirely sensible. The problem is the supporting logic: **a count observed at discovery is not the post's eventual reception.** At one-to-three-minute intake latency, low counts are expected.

I would keep early likes out of negative news judgment. If performance is supplied, attach the observation time and post age. Use mature, age-comparable engagement primarily to learn what our audience values—not as a prerequisite for covering a breaking story. We do not need constant metric refreshes on every lead to solve this.

### D. We have native research available but are barely exercising that route

Across the 73 recorded newsroom runs in the latest 24-hour snapshot:

- 29 SERP HTTP attempts, three recorded failures.
- 105 successful prefetches out of 114 attempts.
- **Zero recorded delegated research assignments**, and no research-seat model calls.

The assignment counter retains a legacy Haiku name in code, but it also counts the configured Grok research route. This means no delegated native research in this window, **not** that the newsroom did no research or that the Grok service is broken.

The native tool configuration supplies plain `web_search` and `x_search`; it does not explicitly enable image or video understanding. xAI documents [image/video understanding and thread fetching](https://docs.x.ai/developers/tools/x-search). I would test selective use for media-dependent leads, with a bounded cost, rather than turning multimodal research on for everything or mandating delegation on every story.

### E. A new event may be real before search engines know about it

The latest snapshot contains a Bitcoin News allegation about a large Liquid-related transfer, including a transaction ID and a quoted original post. The newsroom searched and dropped it for lack of corroboration.

Not asserting an exploit was the right caution. But a transaction ID suggests a different reporting move: identify the correct chain, inspect the transaction directly, follow the quoted original, and check the responsible project's statements. A fresh identifier returning no search results is not evidence that the underlying transaction does not exist.

This is a general sourcing opportunity: **resolve concrete identifiers to their native records**—transaction IDs, filing accessions, bill numbers, pull requests and advisory IDs—before relying on a search engine to discover an article about them. The supplied identifier may still be wrong; direct inspection establishes only what that record actually proves.

### F. There are real collection reliability risks, but don't exaggerate their observed impact

- X fetches one page of at most 25 posts per query and ignores pagination. It advances the newest-ID cursor before the batch is durably stored. A burst, catch-up period or intervening crash can leave a gap.
- One X query exception stops the remaining queries in that pass, so an early query failure can delay the guide query.
- Perception reads only the first page of 50 results. A busy period can outrun that window.
- The 12 RSS requests run sequentially with per-request timeouts. They, X collection and the newsroom share the main worker loop. The worker sleeps 60 seconds **after** its work, so the configured polling intervals are targets, not independent clockwork guarantees.

The recent peer sample does not show missing posts from these risks. Still, draining bounded pages, checkpointing after storage and isolating query failures are ordinary reliability work, not a new editorial architecture. X's [pagination guidance](https://docs.x.com/x-api/posts/search/integrate/paginate) supports the cursor distinction.

### G. Perception's REST response reports an exhausted pool; dashboard discrepancy remains

Its latest source-health record showed an HTTP error. A separate, read-only diagnostic returned **HTTP 429** and `Retry-After: 15748`—about 4 hours 22 minutes at that check.

**Follow-up after Brady supplied a dashboard screenshot showing 44/100 used and 56 remaining:** I read the current [API overview](https://perception.to/api), [endpoint/pool reference](https://perception.to/api/reference) and [REST authentication reference](https://perception.to/docs/rest). The docs explicitly describe separate REST and MCP daily pools. Intelligence has 100 included calls; REST calls use a flat one credit. There is also a separate 60-requests-per-minute limit. `/feed` and `/v1/feed` are both documented routes, so the missing prefix is not itself a defect.

At 19:54:46 UTC, a fresh Railway request using NBN's configured key returned HTTP 429, `x-ratelimit-limit: 100`, `x-ratelimit-remaining: 0`, and a reset of September 7 at 00:00 UTC. Its JSON body explicitly said all 100 requests for the day had been used. A `/v1/feed` check at 19:55:37 UTC returned the same result. A private fingerprint comparison also confirmed that NBN and the Marketing Node use the same Perception REST key; no key was displayed or changed.

Thus the server is specifically reporting daily REST exhaustion, not merely an unspecified HTTP error. **That is evidence of what Perception is enforcing, not independent proof its accounting is correct.** The screenshot's 44/100 cannot yet be reconciled: it may show the separate MCP pool, or there may be an account/UI/backend accounting mismatch. The cropped screenshot does not establish which pool it displays. I have not verified its authenticated page or concluded that the screenshot is wrong.

Do not recommend an upgrade on this evidence. First identify the dashboard pool and reconcile it with the REST response and combined NBN/Node usage. The latest X and RSS health records were successful. Its substantial earlier intake also rules out “Perception never worked.”

No retry configuration or production state was changed in this review.

## 5. Where we can be substantially better

### First: turn each promising lead into a complete, compact reporting packet

Preserve the full material in storage; give the desk a concise index with selective expansion:

- Complete original text, original author and post URL.
- Quoted original or reused-media source; relevant author source reply when needed.
- Media type and a usable preview/reference; extracted chart text or a relevant transcript segment only when useful.
- Original-report time, event time if known, first-seen time, and metrics-observed time as separate fields.
- A primary-document or first-party candidate link, plus what has actually been inspected.
- The interesting claim, reader consequence, known uncertainty, and relation to existing coverage.

Do not turn this into another large model-generated dossier for every input. Most of the packet is available from the API or existing ingestion. A cheap preparer can index it; the writer can open relevant parts. Preserve creator links and timestamps instead of asking research to rediscover them.

**This is my highest-confidence first improvement.** It makes existing sources more useful and can reduce research work rather than adding another mandatory model step.

### Second: build a small reporting beat, not another firehose

These are the first upstream sources I would pilot, using existing intake and filtering wherever possible:

| Source/watch | Why it earns a place | How to use it |
| --- | --- | --- |
| [Bitcoin Core security/release feeds](https://bitcoincore.org/en/rss/) | Official evidence for ongoing protocol and security stories | Selectively watch relevant developments; do not publish version announcements on their own. Core is already on our X list, so this adds direct delivery and redundancy. |
| [Bitcoin Optech](https://bitcoinops.org/) and the original discussions it links | Curated leads and context for larger technical stories | Weekly gap-finder and source map; skip routine software-release listings. Its current [newsletter](https://bitcoinops.org/en/newsletters/2026/09/04/) points to miner-payout privacy work and a CLN disclosure. |
| [Delving Bitcoin](https://delvingbitcoin.org/) | Where proposals, experiments and disclosures first appear | Selected topics and authors; summarize real user implications. A discussion is not an adopted protocol change. |
| Project sources such as [BTCPay's blog](https://blog.btcpayserver.org/) and [Sparrow's official release surface](https://www.sparrowwallet.com/download/) | Supporting evidence for an already-selected larger adoption, custody or security story | Case-specific research/watch targets, not a general wallet/payment-release feed or standalone publication trigger. Follow the project's authoritative links. |
| [HRF Financial Freedom](https://hrf.org/program/financial-freedom/) and [OpenSats](https://opensats.org/blog) | Financial access, builders, projects and first-party grant announcements | Find the actual people and projects; don't turn every grant or tangential Nostr item into news. |
| Farside's [ETF flow surface](https://farside.co.uk/bi/), issuer disclosures and [mempool data](https://mempool.space/pl/docs/api/rest) | Structured observations before articles repackage them | Event-aware data checks. Farside is a data aggregator, not each issuer's primary disclosure; distinguish estimates, completed sessions and missing entries. |
| Specific legislative records and relevant court dockets | Concrete changes rather than political paraphrases | Bind watches to active stories. [GovInfo feeds](https://www.govinfo.gov/feeds) and [court RSS availability](https://pacer.uscourts.gov/help/faqs/how-can-i-receive-case-alerts-using-rss-feed) are starting points; court coverage and document access vary. |

This is a pilot roster, not a recommendation to dump every underlying feed into Grok. We already received some CLN/Optech-related material through other routes; the case for these watches is earlier, fuller and less accidental coverage—not a claim that we have never covered these subjects.

BPI is already a direct X source and trusted for its own research. Add a publication watch if needed; do not pretend its source status needs another overhaul. EDGAR can likewise improve through targeted company submissions and the actual filing passage, instead of broadening into every company's financial trivia. The [SEC submissions API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) updates as filings are disseminated, subject to its access policies.

### Third: follow the guides' sources, not just their conclusions

For worthwhile guide stories, record a simple source chain:

> Who alerted us → who originally reported or demonstrated it → what primary record supports it.

This is not a new knowledge-graph platform. It can be a few fields and a reviewable table using our current storylines and provenance.

Examples: the mempool demo points to its creator; the Taipei video identifies the person filming; a security report points to a researcher and advisory; a local mining dispute points to a municipal record and local reporter. Learning these sources does not override the exclusion of standalone software-release coverage.

When a person repeatedly supplies good original leads, propose adding them to a small beat roster. Follow one useful hop, not an unlimited social crawl. Do not automatically promote source trust based on popularity or because several aggregators repeat the same original.

**This is the most promising way to evolve from following to leading:** learn where the guides find things, then watch those sources directly.

### Fourth: use our storylines as reporting assignments

Our local storyline memory already has “what to watch.” Make that operational, selectively:

- A bill has a scheduled action: watch that bill's action record, relevant committee and official calendar.
- An established wallet security story promises details or remediation later: watch the relevant advisory/release and original researcher, as follow-through on that larger story rather than standalone release coverage.
- A daily ETF session is incomplete: check the missing data, then supply a completed-session comparison once appropriate.
- A known case is awaiting an order: watch that case, not every legal headline.

Each watch needs an expected development, a direct source, the last known state and an expiry. Code can detect a document/data change; the model decides whether the change matters. This avoids paying a general-purpose researcher to rediscover the same background every 15 minutes.

### Fifth: give visual and human stories a real discovery path

Media should be considered twice: **as evidence to understand** and **as material to present**. Those are separate decisions.

For a promising clip, retrieve the relevant segment or transcript and original date. For a chart, retrieve its labels, date range and methodology. For a demo, inspect the creator's demonstration or product documentation. For a screenshot, seek the original exchange when it matters.

This can recover stories our current text-only pipeline makes look empty. It does not require attaching a photo to every post, downloading competitors' videos, or buying a new media platform.

An occasional bounded scout could also look for current Bitcoin deployments, tools and disclosures outside the fixed roster. It should return a handful of strong candidates with original references—not another hundred headlines. I would test this after the richer packets and direct beats, not add it as a compulsory daily cost immediately.

## 6. Speed: remove the right wait

Our historical [speed ledger](audit/speed-performance.md) contains striking cases:

| Story | First useful signal detected | Time after intake to Typefully | Interpretation |
| --- | ---: | ---: | --- |
| Coldcard update, September 2–3 | Under one minute | 6h 27m | Historical selection/conversion delay, not a slow initial feed |
| Cornell adoption research, September 2–3 | Under one minute | 21h 2m | Historical evidence/validation handoff problem |
| Geyser/Cuba, September 4 | About two hours | 28m | A genuine upstream detection opportunity |
| Standard Chartered access story, September 3 | About three minutes | 1h 51m | Earlier report existed; decisive later guide converted in about 15m |

These cases cross old architectures and fixes. They identify the kinds of delay to measure, not today's failure rate.

For current breaking news I would prioritize:

1. Keep lightweight collection progressing while a newsroom session researches and writes; don't let one slow feed or research session delay all subsequent intake.
2. Carry original references forward so the desk starts with the likely receipt, not an empty search box.
3. Resolve structured identifiers directly when appropriate. Search-index lag is especially relevant in the first minutes.
4. Consider a **bounded breaking-news wake-up** for genuinely urgent, plausible leads, coalesced into one run and subject to the existing budget. Keep the ordinary 15-minute cadence. This is a cadence/editorial proposal requiring approval—not “run the full newsroom for every tweet.”
5. Evaluate a small filtered X stream only after these improvements. It could replace part of polling, but it is not the first fix for a two-minute median detection time followed by much larger downstream delays.

X currently documents roughly ten-second stream latency and one pay-per-use connection in its [stream comparison](https://docs.x.com/x-api/posts/filtered-stream/migrate/overview). Actual account access, shared use with the Node, connection recovery and charges need validation before a pilot. Its [billing documentation](https://docs.x.com/x-api/fundamentals/post-cap) also describes daily deduplication of repeated post reads; do not extrapolate costs from old per-read comments in our code. More polling is not automatically proportional cost, and streaming is not automatically free.

While autopost is off, the operational finish line is **ready in Typefully**, not the owner's later click on Publish. Measure primary-to-ready and peer-to-ready separately: beating a late aggregator is not the same as breaking a story.

## 7. The editorial boundary worth resolving before a sourcing sprint

Two current cases expose a product decision:

- **Mempool music:** the writer proposed a concise post; the editor rejected an art/demo without a material system, market, protocol or custody development. The guide was fetched successfully. This was not a code-level source-tier block. I would explore the creator's demo and consider it a legitimate Bitcoin-native discovery.
- **Real Bedford:** NBN saw the guide in roughly two minutes and researched it, then rejected a profile built around older developments. The audit did not inspect a full transcript. I would distinguish a recycled old announcement from worthwhile new reporting about a continuing Bitcoin experiment. Whether the latter belongs in NBN is an explicit editorial choice.

Neither is an independently verified missed breaking story. Both illustrate why upstream expansion alone might disappoint: we could add wonderful builder/community sources and then reject their characteristic output for lacking financial materiality.

My proposed principle is: **material consequences earn attention, but usefulness, a working demonstration, or genuinely illuminating Bitcoin reporting can earn it too.** Freshness labels must still be honest. This is a discussion proposal, not a shipped prompt change.

## 8. The package I would choose

| Priority | Work | Expected value | Restraint |
| --- | --- | --- | --- |
| First | Complete X packets; preserve source chains, long text and media references; timestamp performance signals | Better judgment from leads we already pay to collect; less rediscovery | No mandatory additional research model call |
| First | Fix bounded pagination/checkpointing, isolate collector failures, reconcile Perception REST exhaustion with the dashboard pool and shared usage | Reliable discovery during bursts and interruptions | No assumption that every historical miss was a collector bug; no upgrade recommendation without reconciliation |
| First | Approve the Bitcoin-native discovery boundary and remove newborn-like counts as negative evidence | Avoid filtering out the exact kinds of useful leads we want more of | Keep the existing exclusions on hype, TA and routine treasury stories |
| Next | Pilot a small technical/access/adoption beat and direct data watches | More original Bitcoin signal and earlier receipts | Add selectively; reuse Haiku filtering; retire poor-yield watches |
| Next | Turn a few active storylines into expiring source watches; test direct-ID research | Faster follow-through on expected or developing events | No autonomous sprawling crawler or new memory platform |
| Later, if measured need | Breaking wake-up, narrow X streaming, bounded gap scouting | Reduce the remaining time-sensitive delay and broaden discovery | Explicit marginal cost and latency comparison before expansion |

I would **not** combine all of this into a giant rebuild. The first increment should fix the information arriving on the desk and agree what deserves consideration. Then add a small upstream beat and measure it.

### What success should mean

The audit should distinguish:

- **Capture recall:** which sampled guide posts arrived at all?
- **Qualified-story recall:** which distinct, genuinely suitable peer stories did we cover, reasonably decline, or miss? Not all peer posts are suitable stories.
- **Receipt readiness:** did the first useful packet include a usable original reference, and how much reporting remained?
- **Speed:** primary/peer timestamp → first seen → desk → ready in Typefully, with p50/p90 and slow-case explanations.
- **Incremental source value:** unique useful events, useful earlier warnings, and supporting evidence—not just first-origin counts or article volume.
- **Cost and content quality together:** extra service/model spend per useful event, with stale output, weak selection and unnecessary duplication beside it.

Compare runs on the same model/configuration and allow for the news cycle. Keep a bounded, manually reviewed sample of missed opportunities; do not turn this into deterministic publication quotas.

## Evidence files and reproducibility

- [Production snapshot](audit/research/2026-09-06/db.json): bounded read-only export; source settings, intake, runs, decisions, outputs and health.
- [Peer snapshot](audit/research/2026-09-06/peers.json): public posts, full text, metrics and media metadata; no downloaded media.
- [Collector](audit/research/2026-09-06/collect_sourcing.py): credentials stay on Railway; no cursor or pipeline mutations.
- [Descriptive analysis](audit/research/2026-09-06/analyze_sourcing.py): reproduces capture, latency, format and recent intake/run counts from those files without network access.
- [Inbound flow](INBOUND-NEWS-FLOW.md), [orientation brief](prompts/orientation-brief-v2.md), [tuning examples](prompts/orientation-examples.md), and [speed ledger](audit/speed-performance.md).
- Implementation inspected: `nbn/sources.py`, `nbn/guide_context.py`, `nbn/main.py`, `nbn/newsroom.py`, `nbn/models.py`, `nbn/store.py`, and `config/source_tiers.toml`.

No production code, sources, prompts, models, cadence, autopost settings, Typefully content or audit automation were changed for this review.
