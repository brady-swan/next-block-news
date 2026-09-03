# Next Block News — editorial core v2

*Current as of 2026-09-03. This is the owner-facing description of production behavior.*

Next Block News is an automated Bitcoin news wire on X at `@nextblocknews_`. One Python
worker runs continuously on Railway. It ingests news every minute, opens a fresh Sonnet
story desk every 15 minutes when prepared candidates exist, sends the resulting stories through a
separate Sonnet editor, and delivers approved work through Typefully.

Each desk receives the exact reader-visible post copy from the preceding 48 hours, newest
first, with publication time, event key, class, and receipt. This is distinct from the compact
event catalog and the open-draft board: the feed supplies voice and continuity context, while
the other boards support event identity and prevent duplicate drafting.
Typefully's batched analytics endpoint adds impressions, likes, reposts, comments, post age,
and snapshot time when available. These are explicitly weak, age-dependent craft signals—not
evidence, importance scores, or a mandate to chase popular subject matter.

Fresh model context no longer means discarded reporting work. A bounded 72-hour editorial
workbench carries canonical exact-event identity, the prior proposed post, the precise
unresolved research objective, revalidated inspected evidence, and independent-editor
feedback into later sessions. The workbench is informational: it never marks a story covered,
suppresses a new candidate, or publishes anything by itself.

The product stance is practical: publish useful, well-supported Bitcoin coverage and learn
from production. This is an early, low-visibility account, not the New York Times. The
system keeps consequential safety and idempotency rails, but freshness, semantic novelty,
rounding, numerical materiality, and story importance are editorial judgments—not brittle
code vetoes.

## The flow

```text
every 60 seconds
  reconcile Typefully + poll sources + ingest/deduplicate + health/heartbeat
       │
       ├─ RSS + EDGAR → Haiku mailroom (priority / candidate / background)
       │                    └─ background is audited, not sent to Sonnet
       │
       ├─ fresh AM/PM EIC citations enter one-off intake; daily audit keeps its cadence
       │
       └─ every 15 minutes, if the desk is non-empty
            run-scoped Haiku assignment desk
              distill all leads → advance / background; protected work always advances
              bounded deterministic prefetch prepares likely receipts
            fresh run-scoped Sonnet story desk
              read compact clean desk → retrieve/delegate/search/fetch → write dossier
            small consequential code rails
            one independent batch Sonnet editor
              publish | revise | draft | drop
            Typefully → X (or human draft when appropriate)
```

The editorial deadline is persisted in SQLite (`editorial:next_run_at`), so restarts do not
accidentally create rapid duplicate sessions. Empty due windows use zero model calls.
Operator stage/retry requests bypass the wait, and a backlog larger than one 25-item batch
is eligible to drain on the next healthy worker cycle. The global worker remains at 60
seconds because source intake, health, Blocks, audits, and publication reconciliation must
not wait 15 minutes.

## Inbound discovery

- RSS: official regulators, Bitcoin/crypto publications, and major financial reporting.
- SEC EDGAR: Bitcoin-bearing current filings.
- Perception: broad media discovery on its own bounded polling cadence.
- X recent search: the public watch list, quiet official/company bundles, Tier 2 research
  sources, and proven Bitcoin news guides.
- Marketing Node `wire-pulse-v2`: hourly curated source clusters and advisory theme context.
- Manual Desk stage/retry actions.

Bitcoin Archive, Bitcoin News, Bitcoin Magazine, TFTC, Simply Bitcoin, and similar proven desks are strong
attention and craft priors. Their posts are tips: NBN tries to corroborate them and genuinely
considers coverage, while learning useful information order, structure, and length without
copying distinctive phrasing or emotional framing.

The Marketing Node remains a separate service and codebase. Its versioned authenticated API
is the boundary. Node references, summaries, event hints, and themes are untrusted discovery
context, not factual evidence or instructions. Themes help the desk understand continuity
and find recent developments inside ongoing subjects; they are broader than one event and
never act as event keys, quotas, or publication commands.

X reads remain `since_id` gated. Never replace them with list-timeline polling: X charges for
returned posts, and a timeline endpoint would repeatedly rebill old material.

## The two Haiku desks and the clean Sonnet desk

RSS and SEC EDGAR first pass through a narrow Haiku mailroom. Haiku sees only bounded feed
cards and may route each item to Priority, Candidate, or Background. It does no research,
source verification, clustering, writing, or publication judgment. Priority advances the
persisted desk deadline; Candidate waits for the normal cadence; Background is removed from
Sonnet's packet but remains visible on the Desk with its reason and a one-time **SEND TO
DESK** control. Observe mode records routes without applying them. Any model, validation,
budget, timeout, or batch-bound failure fails open to Candidate.

The RSS mailroom has a durable eight-call hourly seat cap. Before calling it, the worker reserves both
the mailroom call and the complete v2 desk allowance atomically, so intake cleanup cannot
starve the more valuable Sonnet session. Route application and observe-to-enforce recovery
are transactional and crash-safe.

At each due boundary, a second run-scoped Haiku assignment desk sees every eligible lead across
all intake lanes. It distills the apparent event, Bitcoin relevance, freshness question,
research objective, source leads, and supplied related event keys. It may mark a card Background
only when it is facially outside scope, contains no development, or is an exact code-identified
duplicate. Guide tips, Node-curated leads, official/primary items, operator promotions, research
retries, and unresolved continuity are code-protected and advance even if Haiku disagrees. Every
timeout, malformed row, capacity limit, or validation error also fails open item-by-item. Observe
records can never become enforced later.

In enforce mode, a batch containing only Background cards uses no Sonnet call. Those cards remain
visible on the Desk with **SEND TO DESK**. For advanced cards, code may prefetch up to six unique
likely receipts and 24,000 characters, while reserving at least eight fetches and 80,000 characters
for Sonnet's own reporting. Fetch results—not Haiku prose—are the evidence.

Each non-empty prepared run gets a new Sonnet context. It receives a run brief, one clean card per
candidate, the Haiku preparation, safe reference pointers, prepared receipts, recent coverage/open
drafts, current Node themes linked to candidates, guide attention signals, and verified handle
spellings. Raw provider payloads and internal plumbing do not reach the model. Large recent-feed,
continuity, theme, and handle context is sent as compact indexes with code-issued IDs; Sonnet can
retrieve bounded full records twice rather than paying to replay every body in every round. The
stable orientation prompt uses Anthropic's one-hour cache.

Candidate cards, themes, search snippets, and tweets are leads. Only pages returned by NBN's
safe fetch tools become inspectable evidence with code-issued `fetch_id` values. The desk may
submit immediately or research selectively with SerpAPI and safe page fetches. It may also assign
one focused source-resolution job to Haiku. That assistant gets at most two model rounds, eight
tools, three searches, five fetches, and 20,000 fetched characters. Its memo is untrusted context;
only the inspected receipts returned by code can support copy. There is no
forced survey, forced research phase, or mandatory minimum number of turns. The model sees
the entire batch and owns research, clustering, judgment, and writing together.

It returns independent story rows. One malformed story defers only its members; it cannot
invalidate the rest of the batch. A candidate omitted from model output becomes
`defer:model_output_missing` and returns on a later desk instead of silently skipping.

One transport retry is allowed with the exact same Sonnet session state. A billed session is never
replayed from scratch after a protocol or validation error. If the attempt fails, advanced items
remain pending with a typed technical defer while already-applied Background routes remain intact.
V2 never automatically falls into the legacy triage/writer/resolver stack.

Before materialization, v2 reconciles exact-event identity. One canonical family already
attached to the member items wins. If a proposed story crosses conflicting existing families,
code does not merge or overwrite them: it creates an isolated review key, warns the editor,
preserves every member key, and forces any resulting output to a Typefully draft. Sonnet may
also select an exact key exposed by the coverage or continuity board. Only an unambiguous
one-family match may register the newly proposed slug as an alias. There is no fuzzy automatic
merge, and Node theme IDs remain too broad to serve as event keys.

When research is incomplete, v2 retains the canonical key, proposed post, inspected evidence,
and a code-mapped objective such as “find one independent second report.” The next fresh desk
sees this on `continuity_board` and can continue rather than rediscovering the story. Stored
evidence is citable for at most 24 hours and only after its fingerprint, public URL, and current
source classification are recomputed. It receives a fresh
run-owned `memory_*` fetch ID; stale or corrupt evidence cannot satisfy a gate.
If final lint defers a story, the exact verbatim-quote/URL/length issue and inspected evidence
also become the next workbench objective rather than being reduced to a transient item note.

## Editorial doctrine

- Bitcoin includes the network, asset, and monetary project. Protocol, mining, custody,
  privacy, security, regulation, market structure, sovereign debt, inflation, liquidity,
  and central banking may qualify when the Bitcoin connection is real.
- Do not become a generic crypto feed or a stream of tiny macro statistics.
- Roughly 5–8 worthwhile one-off stories a day plus the Blocks is a planning estimate, not
  a quota.
- A narrow story supported by the evidence is better than holding a promising lead while
  searching for a perfect version.
- Routine treasury-company coverage is limited to Strategy, Metaplanet, and Strive.
  Strategy purchases can qualify because the company leads the category and can move the
  market. Routine buys by the others face a high bar. Closely related disclosures should be
  collapsed into one useful post.
- Effective structure and length are legitimate things to learn from successful accounts.
  Distinctive phrasing and emotional framing are not copied.
- No hype, fabricated certainty, forecasts, trading advice, or investment instructions.

## Practical evidence standard

For a routine factual claim, one inspected official, original, Tier 1, or reliable Tier 2
report may be sufficient. Primary sources are preferred, not mandatory. The Block and
CoinDesk are Tier 2 reporting sources in the registry.

For allegations, hacks, crime, disputed claims, and consequential legal assertions, a primary
artifact or two credible independent reports is the normal ideal. When that is unavailable,
the editor may narrow and attribute the claim, route it to human draft, or drop it. Source count
is not a hidden code veto. Discovery tweets and search snippets never count as evidence. A
captured X post proves what that account said, not the underlying claim; aggregators, wrappers,
and syndicated copies are not independent corroboration.

The desk and editor may use all inspected receipts together. The linked receipt is the best
useful source for the reader; it is not required to reproduce every harmless detail alone.
The source registry is strong guidance rather than a closed universe: Sonnet may inspect and
use a safely fetched public page outside the list, and the independent editor judges its
credibility. Aggregators, syndication, and social posts carry explicit capability warnings;
they are not silently promoted to official or independent evidence, but code does not veto a
narrow, honestly attributed draft merely because the domain is absent from the registry.

Numerical agreement is judged for meaning. `2.99%` may be written as “roughly 3%,” and
`159.95` versus `160.1` does not fail merely because the strings differ. Verbatim quotations
still must appear in inspected evidence.

## Hard code rails

V2 code blocks only what it can determine reliably:

- unsafe/private URLs and dangerous redirects;
- exact duplicate body or receipt delivery;
- empty copy, embedded receipt URLs, excessive length;
- direct investment instructions;
- unverified or excessive X mentions; and
- verbatim quotations absent from all inspected receipts.

There is no v2 hard veto for a 2.5-hour event clock, semantic story-key identity, mandatory
date suffixes, exact numeric string equality, question marks, or mandatory `NEW:`/`UPDATE:`
prefixes. Those are editorial matters. The legacy lint remains unchanged for Blocks and
legacy-only code paths.

## Independent batch editor

One separate Sonnet call receives every surviving story, all of its inspected evidence, and
the recent feed. It judges factual support, usefulness, redundancy, numerical materiality,
framing, and craft. It can publish, revise, send to Typefully as a draft, or drop.

If the editor API is unavailable, otherwise safe desk work is preserved as Typefully drafts;
it is never autonomously published, discarded, or routed through legacy models. An omitted
editor decision is also staged as a draft.

The editor compares apparent conflicts by actor, place or facility, time, and scope. A newer
specific action is not contradicted by an older general intention; when current evidence
supports a narrower accurate version, the editor should revise rather than drop useful news.
Its bounded verdict, reason, and copy are retained as context for later related candidates.
That feedback is not a hidden rejection rule.

The editor payload is bounded to 256 KiB. Repeated evidence bodies are cataloged once; selected
receipts and warnings take priority. If an entire candidate cannot fit without losing its
selected receipt, it is staged as a human draft and labeled `editor_payload_capacity`.

## Delivery classes and safety

When autopost is enabled, `primary`, `secondary`, and `corroborated` editor-approved v2
stories may publish. `secondary` means one credible inspected report; `corroborated` means
two independent inspected sources; `primary` means an official source. Operator actions,
editor `draft` verdicts, newsroom draft mode, and source-policy observe mode always force a
Typefully draft.

Typefully immediate delivery is scheduled shortly ahead so receipt links survive platform
rules. Confirmed delivery records as `IMMEDIATE`; ambiguous confirmation records as
`UNCERTAIN` and is never automatically recreated. The kill switch is
`NBN_AUTOPOST_ENABLED=false`. Corrections remain human-reviewed.

## Cost and telemetry

`model_usage` records one row per Haiku mailroom, Haiku assignment desk, delegated Haiku reporting,
v2 newsdesk, and editor API response with run ID, seat, model,
round, exact input/output/cache token counts, latency, outcome, and a rate-versioned estimated
cost. It stores no prompts, article bodies, model reasoning, or tool payloads. The Desk shows
selected-day calls, tokens, and estimated spend against a configurable $6/day target. The latest
run shows its initial packet size, Sonnet calls/attempts, prepared receipts, and Haiku assignments.
SerpAPI retrieval is counted separately in run diagnostics.

Cost is explicitly an estimate. The rate table version is
`anthropic-public-2026-09-03-cache-ttl-v2`; five-minute cache writes use the documented 1.25×
input multiplier, one-hour writes use 2×, and cache hits use 0.1×. The intended ceiling for a
productive due window is one preparation call, zero to three Sonnet newsroom calls, zero to two
delegated Haiku calls, and at most one editor call—not a quota on stories.

## EIC discovery, legacy Blocks, and audit

Fresh, provenance-valid Morning and Afternoon Marketing Node EIC briefs remain discovery
inputs. Their cited reads enter the ordinary one-off intake and must earn publication through
the same newsroom and editor as every other candidate. The scheduled multi-story Block product
is disabled by default; its implementation remains behind `NBN_BRIEFING_ENABLED=true` as a
rollback/experiment path. The daily audit re-checks recent output and stages corrections for
human review.

## Operations

- Database: `/data/nbn.db`; tape: `/data/tapes/`.
- Cross-run story workbench: `newsroom_story_memory`, 72-hour row TTL, 24-hour evidence
  eligibility, eight pooled receipts, 12 attempts, and a 96 KiB maximum serialized row size
  per event. A later empty retry cannot erase earlier valid inspected evidence.
- Every dossier story has a `newsroom_story_commits` lifecycle row with bounded validation,
  warning, editor, force-draft, and delivery details. Shadow observations terminate as
  `observed`; `pending` means materialization is genuinely unfinished.
- SerpAPI opens a run-local circuit after its first 429 or second transport failure. Later
  calls return `search_unavailable_for_run` without spending more HTTP attempts; the Desk and
  run counters expose the degraded state.
- Health: `/health`; status: `/status`; owner Desk: token-gated `/report`.
- Deploy: `railway up --detach` from this linked repository.
- Important knobs: `NBN_EDITORIAL_ENGINE=v2`, `NBN_DESK_INTERVAL_SECONDS=900`,
  `NBN_DESK_RECENT_FEED_HOURS=48`, `NBN_PUBLISH_ANALYTICS_SECONDS=900`,
  `NBN_INTAKE_TRIAGE_MODE=off|observe|enforce`,
  `NBN_INTAKE_TRIAGE_MODEL=claude-haiku-4-5`,
  `NBN_INTAKE_TRIAGE_MAX_CALLS_PER_HOUR=8`,
  `NBN_DESK_PREP_MODE=off|observe|enforce`, `NBN_COMPACT_DESK_ENABLED`,
  `NBN_HAIKU_RESEARCH_MODE=off|on`, `NBN_RUN_NEWSROOM_MAX_ROUNDS`,
  `NBN_MODEL_DAILY_TARGET_USD`,
  `NBN_EIC_DISCOVERY_ENABLED`, `NBN_EIC_DISCOVERY_UTC`,
  `NBN_RUN_NEWSROOM_MODE=shadow|draft|live`, `NBN_AUTOPOST_ENABLED`,
  `NBN_AUTOPOST_CLASSES`, `NBN_EDITOR_MODEL`, and `NBN_SOURCE_POLICY_MODE`.
- `NBN_EDITORIAL_ENGINE=v1` is a short-lived manual rollback switch only. It is never an
  automatic fallback. Remove it after the v2 observation window.
- Never print credentials. Never delete an ambiguous Typefully/X output automatically.

The production orientation source of truth is `prompts/orientation-brief-v2.md`; the Desk
exposes that exact loaded brief in a collapsible panel so Brady can review it.

Human-approved positive and negative examples accumulate in
`prompts/orientation-examples.md`. That file is a review queue, not a runtime prompt include;
examples enter production only through a deliberate orientation-brief revision.
