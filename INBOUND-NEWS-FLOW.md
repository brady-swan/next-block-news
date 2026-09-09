# Next Block News - inbound news flow

Current NBN consumer contract, verified against code and selected production settings on
2026-09-09 (Sprint0073 code; live proof in SPRINT-0073-FINDINGS.md). SYSTEM.md explains the editorial/publisher lifecycle; DESK-GUIDE.md defines metrics.
The pre-refresh flow, including historical Node implementation details, is archived at
docs/history/INBOUND-PRE-0060.md.

## All roads to one newsroom

Sprint0073 adds Peer-to-Peer RSS and four explicit expert-query cohorts (financial freedom,
security/open tools, Bitcoin conversation, monetary conditions/energy). These include useful
replies, quotes and reposts, retaining parent dates/authors and missing-context warnings.
New queries bootstrap only a small recent window and retain existing acknowledged cursors.
Kobeissi is a guide attention signal without a Tier2 evidence upgrade. Perception's existing
survey slots rotate broader reporting questions; no quota or source cadence increase.

Separately, Writer-scheduled follow-ups supply up to2internal assignments on normal desk
cadence even when external intake is empty. They use existing25slots, have no article date,
and are counted apart from fetched/new source leads. They cannot accelerate the desk clock.
Required previous-shift letters and hybrid memory provide continuity, not another news feed.

```text
RSS + SEC EDGAR --------------------------+
X guide/watch posts ---------------------+
Direct Perception -----------------------+-> canonical URL intake
Marketing Node wire + fresh EIC citations +       |
Owner promotions / pending continuity ---+       v
                                            RSS/EDGAR only: Haiku mailroom
                                            other lanes pass through
                                                    |
                                            Luna low preparation
                                            relevant storyline recall
                                            bounded receipt prefetch
                                                    |
                                            Grok 4.3 medium newsroom
                                            search / fetch / optional native research
                                                    |
                                            Grok 4.5 medium editor
                                                    |
                                            Typefully lead + source reply
```

Autopost OFF changes the final delivery destination to a human draft, not the completeness
of preparation, research, writing or editing.

## Clocks: targets, not guarantees

| Path | NBN cadence / bound | Important limitation |
| --- | --- | --- |
| RSS | Every worker cycle; up to 30 entries per feed | Loop sleeps 60 seconds after work; long work delays polls |
| SEC EDGAR | Every worker cycle; up to 25 Bitcoin-bearing 8-K hits | Query covers today/yesterday, not all filing types |
| X recent search | 180-second throttle; up to three 25-post pages/query/poll | Durable continuation; since_id advances only after storage and full window drain; initial lookback six hours |
| X public-list membership | 3,600 seconds | The list supplies accounts, not a polled timeline |
| Direct Perception | 900-second acknowledged poll; one page | Broad Bitcoin discovery; alternates newest page and frozen-window backlog |
| Perception subject survey | Up to 8 slots/day, one attempt per slot | Custody, mining, payments and policy source pointers; normal preparation decides relevance |
| Node wire API | Persisted 300-second throttle | Each valid run consumed once, including empty runs |
| Fresh Morning EIC cited reads | Weekdays 14:40 UTC | One-hour catch-up; current date/window/provenance required |
| Fresh Afternoon EIC cited reads | Weekdays 21:15 UTC | Same freshness checks; not a scheduled thread |
| Normal editorial batch | Persisted 900-second deadline | Only eligible nonempty work; priority/operator/backlog exceptions |
| Typefully reconciliation | 300-second throttle | Updates only locally known outputs |
| Typefully analytics | 900-second throttle | May return missing data; not zero performance |

The Node's last-known upstream Wire Pulse schedule is hourly 05:00-20:00 America/Chicago.
NBN does not own or verify that scheduler by reading a pulse. The live generation timestamp
and consumer freshness checks are the authority; upstream internals were not re-audited in
this documentation sprint. NBN accepts wire pulses at most three hours old. An invalid/stale
v2 pulse may fall back to the bounded legacy Daily Intel projection for the current Central
calendar date. It never treats stale Node prose as source evidence.

## Native sources

The current RSS roster in nbn/sources.py is Federal Reserve, SEC Press Releases, CFTC,
Bitcoin Magazine, CoinDesk, The Block, Cointelegraph, Bloomberg Markets, CNBC, Wall Street
Journal, Fox Business, PR Newswire Financial, plus the Plan 0062 pilot: Bitcoin Core,
Bitcoin Optech, and BTCPay Server. Feed failures are isolated, not proof
that every listed feed is currently responding. No general Treasury/congress/court RSS
feed is present just because those institutions are allowed source categories.

EDGAR searches Bitcoin-bearing 8-Ks from today/yesterday. Official-feed candidates still
pass through the cheap mailroom; the user explicitly accepted false-negative review there.

Pilot feeds initialize without flooding the desk with archives: on their first successful
snapshot only, entries older than the configured intake window (24 hours) are persisted as
`bootstrap_background` skips before Haiku. Unknown dates pass normally. Initialization is
acknowledged after item commit; later new entries use normal routing. Software releases are
not a new beat: they qualify only as developments in a bigger ongoing story.

X uses recent-search queries with persisted since_id, not repeated full-list
timeline. The public X List supplies a user-managed primary roster. Fixed queries add
official/company accounts, Tier 2 research (including Kobeissi Letter and Barchart), strong
Bitcoin guide accounts, and broader detectors. BitcoinNewsCom, Bitcoin Archive, Bitcoin
Magazine, TFTC and Simply Bitcoin are guide signals. The exact current queries/registry
are in nbn/sources.py, nbn/guide_context.py and config/source_tiers.toml.

Guide posts carry stable versioned attention/context metadata regardless of which query
found them. They get genuine consideration and research when useful, not automatic posts.
A guide's news tip is not corroboration; inspected social text proves what the author said,
not an independently verified underlying event. Links remain uninspected pointers until
fetched or processed by the native research path.

X also retains a separate, bounded 12 KiB `source_material` record: long note text, original
author/post/date, one level of quoted/referenced sources, links, media metadata, and age-stamped
engagement. Missing quote expansions and truncated text are explicit. Media is neither downloaded
nor visually inspected during intake. Plan 0066 lets the reporter-writer explicitly inspect
relevant still images or render sourced NBN graphics later; captions/pointers are not pixels,
and reusable rights are separate from relevance. Preparation gets a richer preview; the writer can
retrieve the fuller card via `full_lead_context_id`. Source-chain URLs enter the existing pointer
and prefetch path, not the evidence catalog automatically. Same-post enrichment never changes
first-seen, first origin or disposition; different posts sharing an article do not overwrite
one another's attached material. Pending inventory and research retries reload durable material.

`x_cursor:<query hash>` stores the lower bound and unfinished page token/high-water ID. It is
acknowledged after upsert, so an interruption replays instead of losing returned posts. A failed
query leaves others running; a shared 429 stops further requests. Three-page overflow continues
next poll, rather than jumping past unread posts. Existing `x_since_` keys seed the new cursor.

Direct Perception queries the Bitcoin feed separately from the Node. The approved integration
retains dated source bodies on new and duplicate arrivals without reopening skipped stories.
Items and articles are committed before page progress is acknowledged. Offset pagination is
best-effort; partial/truncated coverage and backlog remain visible. The Writer can search the
industry corpus, find regulatory originals, or read retained/retrieved text through one interface.
REST and MCP have separate provider quotas; shared evidence avoids duplicate article retrieval.
New research uses at most24attempts/day (including up to8survey attempts), with at most4REST
research attempts. This is NBN-local accounting, not account-wide remaining capacity or a promise
of free calls. Marketing Node configuration is unchanged. See PERCEPTION.md for exact behavior.

## Marketing Node boundary

NBN reads the authenticated wire-candidates/v2/latest endpoint from the separate Node
service. It validates schema, age, identifiers, reference URLs, source alignment and bounded
context, then persists one run transactionally. Selected source references supply intake
fields; Node prose and keys remain hints. NBN keeps immutable first-ingestion provenance
and can attach compatible enrichment to still-new items without rewriting terminal decisions.

The Node remains supplemental discovery, not an editor or continuity authority. Theme fields
may survive API compatibility/diagnostics, but neither Luna nor Grok receives Node themes.
The shared thematic context is now NBN's own storyline ledger. Exact-event identity is separate.

Fresh EIC briefs supply at most 12 cited more_reads links each, with source Daily Intel run,
window, generation and receipt timestamps checked. They enter ordinary one-off intake.
The legacy multi-post Block builder is disabled by default and in production.

## What is removed before the writer

1. Canonical URL deduplication prevents the same known URL becoming a new item repeatedly.
   Meaningful query parameters are retained; tracking parameters can be normalized away.
2. Haiku's RSS/EDGAR mailroom labels Priority, Candidate or Background. Priority advances
   the desk deadline; Candidate waits; Background is not sent to the writer. Every model,
   validation, timeout or capacity error fails open. The Desk retains reasons and promotion.
3. Luna's due-batch preparation distills every eligible lane, groups apparent same-event
   companions and selects relevant NBN storyline keys. Guide/official/operator/retry and
   unresolved-continuity work is protected. Background is visible but omitted; failures advance.
4. An advancing run-local group member can bring its Background companions along. That is
   attention routing, not canonical identity or factual corroboration.
5. Intake age, language/usability, pending state and the 25-item batch cap bound the working
   set. Article first-seen age is not proof of the underlying event's freshness.

## What the writer does

Grok gets a new context for each prepared run, not an immortal conversation. It can judge
immediately from usable prepared receipts, search SerpAPI, fetch safe public pages, retrieve
full indexed continuity, or use native web/X directly in the same conversation. There is no
mandatory research turn count. Plan 0063 gives the writer six responses / six minutes, source
links from fetched articles, a complete paginated memory catalog, and searchable earlier intake
(72 hours by default, up to seven days, including skips). This is recall, not a second ingestion
lane: reading a skipped item does not automatically reopen it. Source collection cadence is unchanged.

Search snippets and cached URLs are pointers, never evidence. SerpAPI queries cache for one
hour; exact-candidate/event pointers can persist six hours. Shared quota/rate-limit circuits
avoid repeated doomed calls. Native source-specific findings can yield labeled
provider-reported extracts; those are paraphrases, not exact page captures. Safe direct
fetches and native extracts retain their different capabilities through editor and memory.

Primary sources are preferred. One credible inspected report can support routine narrow
news; elevated claims normally merit stronger corroboration or narrowed attribution.
The registry is not a closed allowlist for live v2: source quality and sufficiency are model
judgments with capability labels. BPI's own research is trusted first-party research within
that scope. Syndication and wrappers do not become independent reports.

The writer accounts for all advanced candidates and declares exact-event stories; malformed
stories and omitted candidates defer locally. It writes selective copy, then a separate Grok
editor may approve, revise, stage or drop. A newsroom defer can carry a precise objective and
inspected evidence into a later desk. Legacy research_jobs statuses alone do not guarantee a
live v2 retry time; inspect current item defer state, workbench and run decisions.

## Coverage and output

Exact canonical event families, the recent reader-visible feed and remote lifecycle govern
duplicate prevention. NBN-native storylines supply broader context but never establish truth
or mark an event covered. A safe open draft may be replaced; already-visible or ambiguous
work cannot be blindly recreated. Genuine material developments can become UPDATE posts.

Eligible primary, secondary and corroborated copy may schedule through Typefully only when
the master autopost switch is on and all other conditions allow it. It is currently off.
New delivery is clean lead text plus Source reply. Durable intents and ordered-content read-back
separate safe delivery from ambiguous attempts. Local IMMEDIATE mode is not, on its own,
the new Desk's definition of confirmed X publication.

## Measuring provenance

Persisted discovery_origin is first arrival: rss, edgar, perception, x or marketing_node.
Raw results, unique URLs, candidates considered, stories and outputs are different units.
One event can combine multiple sources. An already-known Node URL is not a new Node-origin
story, but additional useful evidence may still matter. Measure incremental usefulness and
timing, not only raw volume. Check exact recent NBN/Typefully copy before labeling a miss.
