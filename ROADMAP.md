# Next Block News — roadmap (updated 2026-08-30, end of launch weekend)

## Where we are

Alpha declared Saturday morning; by Sunday evening the wire is a complete autonomous
newsroom: five source layers, active web-verification, deterministic gates, a Fable
editor with recorded verdicts, scheduled-publish autonomy with links, a designed Desk
with an action queue, a daily self-audit, a corrections doctrine, and a dead-man's
switch paging Brady on silence. Four stories found and published autonomously in the
first ~30 hours; two voice defects caught on the live timeline and made structurally
impossible; zero factual errors; first editor verdict on record.

**Monday 2026-08-31 is the real test**: first weekday news cycle — regulators awake,
EDGAR flowing, the 14:40 UTC Morning Block firing on its own.

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
2. **Block number cross-check** — verify the brief's figures against wire-verified items
   and cited sources before threading (the "60%" fix). Prerequisite for promoting
   `briefing` to autopost.
3. **`briefing` autopost decision** — after ~5 good Blocks + the cross-check.
4. **Data posts class** — computed from CoinGecko/mempool (daily close, difficulty,
   halving milestones; ETF flows once Farside is read properly). Zero-hallucination
   cadence filler; activates the dormant `data` autopost class.
5. **Small queued fixes**: no-verdict triage requeue · retry infra-failed verifications
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
