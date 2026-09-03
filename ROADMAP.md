# Next Block News — roadmap (updated 2026-08-30, end of launch weekend)

## Where we are

Alpha declared Saturday morning; by Sunday evening the wire is a complete autonomous
newsroom: five source layers, active web-verification, deterministic gates, a Fable
editor with recorded verdicts, scheduled-publish autonomy with links, a designed Desk
with an action queue, a daily self-audit, a corrections doctrine, and a dead-man's
switch paging Brady on silence. Four stories found and published autonomously in the
first ~30 hours; two voice defects caught on the live timeline and made structurally
impossible; zero factual errors; first editor verdict on record.

The first weekday cycles showed that scheduled multi-story Blocks delayed and duplicated
material that works better as timely one-offs. On 2026-09-03 the Block product was disabled;
fresh EIC citations still feed the ordinary newsroom.

## Week 1 (launch weekend) — ALL SHIPPED ✅

1. ✅ Desk Report → shipped, then redesigned via Claude Design ("Filed, action-first"),
   incl. dismiss flow, day navigation, editor verdicts per post
2. ✅ Pinned methodology post (published + pinned; "produced by a team of agents")
3. ✅ Corrections protocol (`CORRECTIONS.md`)
4. ✅ Daily self-audit (09:00 UTC; material findings stage CORRECTION drafts)

Shipped beyond plan: the Editor seat (Fable 5 @ low) · scheduled-publish loophole
(links + autonomy, no provider switch) · X List as UI-managed roster · web-corroboration
promotion · follow-up framing (`already_covered`) · attribution lint · non-English
intake gate · time-varying freshness · heartbeat/healthchecks · real logo + favicon.

## Week 2 — watch, grade, then build

**The editor week proper (no code needed):**
- Grade the wire daily from the Desk: wrongly held? wrongly skipped? class labels right?
  editor verdicts sound? Feedback lands as charter lines or lint rules, same as launch
  weekend's three cycles.
- Watch the metrics that compound: followers-per-post, profile-visit conversion,
  time-to-post vs the aggregators on shared stories.

**Build queue, in order:**
1. **Editor casebook** — once ~a week of agree/overrule gradings exists, quote the best
   as precedents inside the editor prompt. The closest thing to training we have.
2. **Data posts class** — computed from CoinGecko/mempool (daily close, difficulty,
   halving milestones; ETF flows once Farside is read properly). Zero-hallucination
   cadence filler; activates the dormant `data` autopost class.
3. **Small queued fixes**: no-verdict triage requeue · retry infra-failed verifications
   (search-quota holds) · ⚠️ **regenerate the shared X bearer** (partial chat exposure
   8/30) and update Node + wire envs.

## Growth — once week 2 proves quality

- Register **nextblock.news** (checked available 8/29) — future site/newsletter home.
- **Nostr mirror** — near-zero cost, exactly this audience, credibility with Bitcoiners.
- First **being-first moment** (wire beats everyone to a Fed statement or 8-K):
  quote-post from Brady's personal account. Sparingly. Never from @Swan.
- The **go-loud decision**: when the wire has earned it, Marketing Node integration +
  team disclosure ends skunkworks mode (supersedes the "quiet" constraint in memory).

## Deferred deliberately

On-this-day almanac · newsletter · PACER/international surfaces · engagement-metrics
ingestion (X read costs) · X-API direct write path (only if Typefully's scheduled-post
loophole ever closes).

## Idea bank — everything stashed, from the founding plan + weekend notes

*(Source of record for the founding strategy: `~/claude/bitcoin-news-handle-plan.md` —
competitive study, charter rationale, phase plan, metrics. Nothing there is superseded
except what shipped.)*

**Content & products**
- **Evergreen daily history slot** — the DocumentingBTC lane between news cycles;
  requires the **verified on-this-day almanac** (365 source-verified entries; flagged in
  tape 001, never built). The soul of the feed on quiet days.
- **Price-milestone posts at genuine milestones** — the competitive study's top-performing
  format (BitcoinMagazine/WatcherGuru data); belongs to the data-posts class.
- **Real-data charts on data posts** — house dataviz standards; never model charts,
  never image-model charts.
- **Weekly recap Block** ("The Week Block") — Sunday synthesis once daily Blocks are
  autonomous. *(new idea, unvetted)*

**Detection & sources**
- **Perception Watchlist keyword ALERTS** — push, not poll, and credit-free; unlimited
  keywords on the plan. A delivery channel the worker can read would make this a free
  intraday detection layer (flagged 8/30 when reviewing the Perception plan).
- **Grok Bot as read-only detection scout** — the bounded experiment from the original
  assessment: race it against bitcoin_pulse + hop-crawl on time-to-detection; no logins,
  no posting rights; adopt only if it consistently wins (~$300/mo bundle cost).
- **PACER / court filings** and **non-US regulators** — the named blind spots for
  stories that break outside our surfaces.

**Distribution & growth**
- **Multi-platform mirrors via the existing rail** — Typefully natively posts to
  Threads, Bluesky, Mastodon; the wire could mirror everywhere for near-zero marginal
  work. Nostr separately (also near-zero, highest credibility-per-dollar).
- **nextblock.news** — site/newsletter home (checked available 8/29; register before
  someone reads a podcast transcript).
- **Canonical @nextblocknews acquisition** — Brady pursuing via the X handle marketplace.
- **Public corrections count** — the trust moat made into a visible stat (methodology
  page / pinned thread update); the Desk already tracks it.
- **First being-first quote-post** from Brady's personal account; never @Swan.

**Metrics & governance (from the founding plan)**
- The compounding metric: **followers-per-post** (DocumentingBTC benchmark ~136/post
  lifetime; Cointelegraph ~15). Secondary: likes/1k followers (wire benchmark 1.0).
- **Day-90 kill/persevere review**: if followers-per-post economics aren't visibly
  compounding and the workload isn't automating, fold the learnings into @Swan and stop.
- **The go-loud decision**: Marketing Node integration + team disclosure + Swan weight,
  when the quality record earns it.

**Engineering**
- Evidence-component refinement: replace greedy owner/artifact/near-copy collapse with
  connected components if live observe data shows bridge-chain false corroboration.
- Editor casebook (precedent-quoting from Brady's gradings) — week 2 queue.
- Evaluate a single end-of-day recap only after one-off volume and reader demand justify it.
- Data-posts generator — week 2 queue.
- No-verdict triage requeue · infra-failed verification retry · X bearer regeneration.
- X-API direct write path — only if Typefully's scheduled-post loophole closes.
- Engagement-metrics ingestion (own posts' impressions/likes for tuning) — deferred on
  X read costs; revisit if a decision actually depends on it.
