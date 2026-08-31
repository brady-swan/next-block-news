# How Next Block News works — the owner's manual

*Current as of 2026-08-31, matching deployed code. One always-on
Python worker on Railway watches the news, judges it, writes it, checks itself twice —
once with rules, once with an editor — and publishes to @nextblocknews_ through
Typefully. Two products: breaking singles (anytime) and the Morning/Afternoon Block.*

---

## The 30-second version

```
 every 60s ──────────────────────────────────────────────────────────────────────┐
 │                                                                               │
 │ WATCH          INTAKE GATES      TRIAGE           DRAFT          FACT GATES   │ EDITOR        PUBLISH
 │ 12 RSS feeds   dedup by URL      Sonnet 5:        Sonnet 5,      lint: scope, │ Fable 5 @low: Typefully,
 │ SEC EDGAR      freshness         draft/hold/skip  numbers only   hype, attrib,│ reader value, scheduled
 │ Perception     (2.5h day/6h      + story key      from FETCHED   mentions,    │ feed context, +30s (links
 │ X (list+       night/wknd)       + class          source text    numbers vs   │ craft; spike/ survive),
 │ bundles)       non-English                                       source (+1   │ revise/publish confirm-
 │ web search     gate                                              retry)       │               polled
 └───────────────────────────────────────────────────────────────────────────────┘
 weekdays 14:40 & 21:15 UTC: Node brief + wire's own catches → the Block (staged DRAFT)
 daily 09:00 UTC: self-audit re-verifies yesterday's posts against their receipts
 every cycle: heartbeat ping → healthchecks.io (silence >15 min pages Brady)
```

Everything lands in the daily tape (`/data/tapes/`) and SQLite (`/data/nbn.db`),
including the editor's verdict on every gate-passed delivery candidate
(`posts.editor_note`).

---

## 1. Watching (sources)

**RSS, every cycle (60s):** Federal Reserve press, SEC press releases, CFTC press
(primaries), Bitcoin Magazine (their broken URL 301s to a working /feed), CoinDesk,
The Block, Cointelegraph, Bloomberg Markets, CNBC, WSJ Markets, Fox Business,
PR Newswire Financial (where corporate announcements originate). Per-feed failures
never kill a cycle.

**SEC EDGAR full-text watch (60s):** every 8-K mentioning "bitcoin", filed today or
yesterday — corporate Bitcoin news before journalists write it. Free, unmetered,
`primary` class.

**Perception `/feed` (15 min):** 1,000+ outlets. The API key is SHARED with the
Marketing Node (one key per Perception account) — the interval is a budget decision;
`/feed` 429s in either system's logs mean widen `NBN_PERCEPTION_POLL_SECONDS` first.

**Marketing Node curated discovery (5 min, UTC-day run):** NBN consumes the Node's
authenticated `/api/daily-intel/wire-candidates/by-date/{date}` projection. It is a
bounded, ordered list of source links from `DailyBrief.more_reads`, plus theme/must-know
context. A valid accepted/partial run is consumed exactly once, including a zero-item
run; malformed candidates are skipped individually. The two projects remain separate
codebases and databases. The API is their explicit contract.

Node prose is discovery context, never source evidence. It is stored separately from an
item summary, labeled `detector_context_untrusted`, and shown only to triage. It never
reaches source resolution, Writer, claim checks, lint, or Editor. NBN independently
DNS-checks each public URL and verifies the Node's deterministic candidate ID before
ingestion.

**X recent-search (3 min), `since_id`-gated** — critical: X bills ~$0.005 per post
*returned*, and search re-returns matches unless you ask for "only new"; quiet polls
cost zero. Three tiers:
- **The public list "Next Block News Follows"** — membership fetched hourly and
  compiled into `from:` queries. Brady edits the wire's coverage from the X app;
  changes take effect within the hour. (Never poll a list *timeline*: no since_id,
  re-bills reads.)
- **Quiet hardcoded bundles**: watched legislators; company newsrooms (BitGo, NYDIG,
  Coinbase, Strategy, Galaxy, BlackRock, Fidelity, Bitwise, Grayscale, River, Strike,
  Unchained, Casa, Swan) — kept off the public list for association optics.
- **Fast detectors** (WatcherGuru, CoinDesk, TheBlockCo, Bitcoin Magazine,
  BitcoinNewsCom, TFTC21, BitcoinArchive) — tips only, never sources (see §3).

**Web search (on demand):** Claude's server-side web_search, used by verification (§3)
and the self-audit.

## 2. Intake gates (deterministic, pre-model)

- Canonical URL dedup across RSS, X, Perception, EDGAR, and Node (tracking parameters
  removed; meaningful query parameters preserved) — first-ingestion provenance is
  immutable and an item is examined once, ever.
- **Freshness** tracks the news metabolism: 2.5h during weekday 7am-7pm ET, 6h
  overnight/weekends (`NBN_MAX_AGE_HOURS_*`; a set `NBN_MAX_AGE_HOURS` overrides with
  one fixed value). EDGAR exempt (date-only stamps; its query bounds age instead).
- **Non-English** (>30% non-Latin letters in the title) — skipped before any model call.

## 3. Judgment (triage → source resolution)

**Triage** (Sonnet 5, batch): action draft/update/hold/skip, a `story_key` naming the
underlying story, and a proposed class. It receives both **posted** story keys (skip duplicates)
and **open** ones (REUSE the key — that's what makes a second outlet's arrival trip the
corroboration promotion).

Triage has no target quota. Factual Bitcoin market state—defined-period price moves,
flows, leverage, funding, open interest, volatility, liquidity, holder activity, and
directly relevant rates/yields—is eligible when the underlying figures can be verified.
It judges the factual payload beneath a headline and leaves the writer/editor to strip
sentiment or narrative framing. Forecasts, price targets, trading advice, unsupported
causal stories, and context-free price ticks still skip. A relevant official post linking
only to a speech, hearing, release, or video advances to source resolution so the wire can
find prepared remarks or a transcript; missing feed copy is not itself a rejection.

Measured Bitcoin reaction to a named event can qualify when the measurements are
verifiable and the copy avoids speculative causality. Multi-asset policy or infrastructure
news qualifies only when Bitcoin is materially affected and can be covered without token
market reporting.

Treasury-company intake is deliberately narrow: Strategy, Strive, and Metaplanet are the
only routine candidates, but the allowlist is not approval. Strategy buys generally clear
the materiality bar because the category leader moves the market; ordinary recurring buys,
rankings, and stock-price reactions from Strive or Metaplanet skip absent a consequential
development. Their official identities, plus Core Lightning's, have exact standalone P0
registry entries rather than relying on a shared social identity.

`update` is a separate machine-readable triage action. It is valid only for a material
development matching an exact reader-covered story key. Ordinary `draft` on an already
handled key still skips. Deterministic lint requires `NEW:` for first coverage and
`UPDATE:` for an authorized update.

**Source tier and evidence class are separate:** `config/source_tiers.toml` is the
validated canonical registry. P0 is an official artifact; Tier 1 premier reporting;
Tier 2 reliable specialist reporting/research; Tier 3 discovery only; Tier 4 a wrapper,
aggregator, or syndicator. Unknown sources fail closed. Tier never proves that a page
supports the story, is original, or is independent.

**Classes decide autonomy:**

| Class | Meaning | Autopost |
|---|---|---|
| `primary` | The item IS the official artifact (regulator release, filing, company's own statement) | yes |
| `corroborated` | 2+ eligible independent evidence chains on one exact story_key | yes |
| `secondary` | Single-outlet press report | never (code-hardened) → Typefully DRAFT |
| `data` | Pure market/chain data | in the allowed set; dormant until the wire computes its own numbers |
| `briefing` | The Blocks | DRAFT until Brady promotes the class |

**Active source resolution:** all actionable items receive a typed, persisted resolution
before any item in the batch can promote. Official and research identities never prove
artifact scope: broad-domain pages require a directly-supporting role verdict, fetched
canonical/byline metadata wins over model metadata, and official-X is primary only for the
account's own action or statement. Tier 1 is an acceptable receipt; Tier 2 reporting gets
a bounded primary/Tier 1 upgrade search and may fall back only when original reporting is
established. Tier 3, Tier 4, and unknown sources must be replaced by a directly supporting
P0/Tier 1/Tier 2 page or they hold.

The original tip and final receipt are stored separately. A detector plus the artifact it
located is one evidence chain, not two. Eligible evidence persists across cycles for the
exact story key and expires after the configured lookback. Same-owner publications,
aggregators, syndication/content copies, and reports resolving to the same primary artifact
collapse, including lightly boilerplate-modified copies and an entity's website plus its
official X account. Ambiguous originality is never corroboration-eligible. A directly
supporting, artifact-scoped P0 official page may justify `primary`; deterministic code
vetoes `primary` on anything else. Every candidate for one exact story key finishes source
and provider resolution before the strongest final receipt is chosen, so feed order cannot
change the receipt or class and the worker emits at most one post per story group.

Actionable triage decisions are frozen into a durable `research_jobs` record before the
first external fetch. A timeout, transport error, rate limit, 5xx, or source-search outage
is an infrastructure outcome—not an editorial rejection—and receives exactly one later
automatic retry (at most two due jobs per cycle). A crash-held claim is recovered after
its lease; LLM budget exhaustion delays work without consuming an attempt. Definitive
unsafe/4xx/no-evidence outcomes remain normal editorial holds. Provider-substitution
failures remain terminal in this release rather than creating an unbounded retry graph.

## 4. Writing

Sonnet 5 drafts from the FETCHED article text under the charter
(`prompts/wire_voice.md`; compiled reference `PROMPTS.md`). The load-bearing seams:
- Every number must appear verbatim in the fetched source text; no text → no post.
- Freshness distinguishes a report's fresh `disclosure_date` from its older
  `underlying_period_end`; the latter must be stated as historical context.
- The model never writes URLs — the system appends the verified receipt (the
  anti-fabrication seam).
- If the wire already covered the story, drafting receives `already_covered` — lead
  with what's new, never re-announce.
- Shape: narrative default in short scannable paragraphs; `•` bullets (max 4) only for
  genuinely enumerable stories; mixed allowed (one run ≤3) — bullets carry lists, prose
  carries the story. Attribute the source ONCE. Mentions only from `handles.json`
  (hand-verified), max 2.

## 5. The gates (deterministic; one retry with violations fed back)

`nbn/lint.py`: Bitcoin-only scope (no non-Bitcoin token ever; "crypto" only as a
business adjective or inside a quoted official title), no hype/forecast/buy-timing
patterns, number-integrity vs source text, repeated-attribution ban, mention whitelist,
no model URLs, length caps. Block-specific: any "swan" mention rejected; receipts must
be URLs present in the Node's brief. These gates are the wire's identity — NOT Swan
compliance; the wire is not Swan-affiliated content.

If a draft names a data provider different from its selected receipt, the worker performs
one targeted provider lookup and one redraft from the replacement text. A second mismatch,
empty source, unsupported number/quote, or ambiguous adversarial claim-support verdict
holds. It never swaps a receipt beneath already-written copy or loops back to the old one.

## 6. The Editor (last mile, before every delivery)

`nbn/editor.py` — **Fable 5 at low effort** (Brady's call). After all gates, before
publish, it reads the candidate against the wire's last 10 published posts — the two
things rule-gates can't see: contextual duplication and craft. Verdicts:
**publish** / **revise** (downward-only edits, re-linted, original stands on failure) /
**spike** (held, reasoning shown in the Desk for Brady to agree or overrule). An editor
outage fails OPEN — judgment problems never block news. Every verdict is recorded on
the post (`editor_note`): the grading record. The Editor runs on every gate-passed
candidate in enforced source-policy mode, whether the publisher will send it immediately
or stage it in Typefully. `NBN_AUTOPOST_ENABLED` controls delivery mode only; it does not
remove the Editor from the funnel.

## 7. Publishing

**Typefully API v2.** The pivotal discovery: `publish_at:"now"` rejects any draft
containing a URL (X policy, draft-wide, undocumented — the 403 body is the only
written rule), but **scheduled posts carry links fine**. So "immediate" = scheduled
`NBN_PUBLISH_DELAY_SECONDS` (30) out; Typefully fires on minute boundaries → real
latency 30-90s. Fallback ladder if policy shifts: linkless → staged linked DRAFT.
Publishes are confirm-polled. Only a confirmed publish is recorded as `IMMEDIATE`.
Confirmation ambiguity becomes `UNCERTAIN`, is surfaced for manual verification, and is
never retried automatically because a second create could duplicate a live post. Definite
backend failures become `FAILED`; no configured backend is the distinct `TAPE` mode.
No delete exists anywhere in the chain — **corrections
are posted, never scrubbed** (`CORRECTIONS.md`: severity ladder, templates, corrections
never auto-publish, nothing new posts over an uncorrected material error).

## 8. The Block (scheduled briefing threads)

Weekdays 14:40 UTC (Morning, after the Node's 14:00 EIC brief) and 21:15 UTC
(Afternoon, after the 20:30 intel run); once per window. Fetches Brady's tuned brief
from the Marketing Node read API, folds in the wire's own catches since the previous
Block, renders a 5-9 post thread: post 1 = link-free index (`Morning Block - <date>`,
"Top stories:" bullets, "More inside ➡️" — the wire's one emoji), per-post receipt
links from post 2. Gates: Swan-strip (deterministic), receipts-from-brief-only, full
lint. The worker has a 60-minute catch-up window after each scheduled time, and one
compact feedback retry protects against empty/truncated JSON or a failed factual/style
gate. Stages as DRAFT. Known
tradeoff: the Block trusts the brief's numbers (the "60%"
incident); the cross-check pass is the spec'd fix.

## 9. Self-audit (daily 09:00 UTC)

Re-fetches every published post's receipt and re-verifies claims, numbers, quotes
against the CURRENT source (source drift handled honestly), plus the class audit —
press-classed-`primary` is the one gate-proof failure. Material findings auto-stage a
CORRECTION draft (never publish). Results in the Desk.

## 10. Operating it — the Desk and the switches

**The Desk** (`/report?k=<token>`, bookmark in `DESK-REPORT-URL.txt`): Claude-Design
"Filed, action-first" UI. Status strip (worker, publisher-sync, and Node-intel age, model seats,
freshness window, autopost) → **Needs You** (verb-led cards: AWAITING PUBLICATION /
VERIFY ON TYPEFULLY / X / PUBLISH FAILED /
TAPE ONLY / AGREE OR OVERRULE / AUDIT FLAG, each with a `dismiss ✓` that records
acknowledgment without deleting history) → daily lifecycle strip (seen/evaluated/outputs/
confirmed published/currently held) → **Last decision run** (the most recent completed
non-empty cycle, every considered source item, triage action/reason, final state/reason,
and any receipt upgrade; empty polls do not erase it) → 7-day strip (published/held/seen per day,
stalled-weekday flags, day
navigation) → Published (lede-only cards + editor verdicts) → Held grouped by reason
family → Self-audit → Skips.

Held items have an explicit operator disposition. **Stage draft** is offered only when
the pipeline already has usable material and the hold came from freshness,
corroboration, style, or Editor judgment. It queues a one-time retry, preserves the
story key, forces a fresh web source-resolution pass → Writer → lint → Editor, bypasses only that recorded
gate, and forces `DRAFT` delivery even if autopost is enabled. Any different gate can
still hold it. **Dismiss** moves any held item to skipped with an `owner dismissed`
reason. Both actions are persisted in `operator_actions`; neither deletes the decision
history. Source-policy and thin-source holds deliberately have no Stage button because
they do not yet have reliable material to draft from.

Infrastructure research holds instead offer **Retry research → draft**. This control is
available only for a persisted retryable research job; it reruns the full fetch → source
resolution → Writer → lint → Editor path and always forces Typefully DRAFT. Dismiss also
cancels any pending research job.

Desk counters deliberately do not form one equation; they use two units and two date
axes:

- **published** — locally tracked story outputs Typefully confirms live during the
  selected Central-time day (`confirmed_at`); a thread/story output is one row, not a
  count of every tweet in it.
- **drafts / uncertain / failed / tape** — output rows created during the selected day
  whose current delivery mode is respectively staged for human publication, ambiguous
  after a publish attempt, definitively failed, or written without a publisher backend.
- **held / skipped** — source items first seen during the selected day whose current
  state is held or skipped. These are source URLs, not necessarily distinct stories.
- **seen** — unique source URLs first ingested during the selected day, regardless of
  current state. It is intake volume, not the sum of the output and disposition counts.
- **evaluated** — those seen items no longer in `new` state. **outputs created** is every
  post row created during the day, including non-published delivery modes.

Several source items can collapse to one story output; a held item can later change
state; and a manually published draft is dated by its confirmed publication time.
Accordingly, published/held/skipped and seen should not be added together. The Skipped
headline is an exact database count; its expanded table shows only the top 14 reason
groups.

Before each worker cycle, a rate-limited Typefully read reconciles locally known draft IDs
against its published feed. Exact confirmed receipts promote manual drafts, uncertain, or
failed rows to published; Desk dates and every recent-publication consumer use Typefully's
actual `published_at` timestamp. Unknown Typefully-only posts are not imported.

**Watching the watcher:** every successful cycle pings healthchecks.io
(`NBN_HEARTBEAT_URL`); ~15 min of silence pages Brady. `/health` returns 500 when the
last cycle is >10 min old. X notifications on the handle announce publishes.

**Switches:** `NBN_AUTOPOST_ENABLED=false` = master kill (everything stages as
drafts). Pause the Railway service to stop even drafting. Tape reads:
`railway ssh "cat /data/tapes/tape-YYYY-MM-DD.md"`.

## 11. The knobs (Railway service variables)

| Variable | Observed 2026-08-31 | Purpose |
|---|---|---|
| `NBN_AUTOPOST_ENABLED` | `false` | master kill switch; autonomy currently paused |
| `NBN_SOURCE_POLICY_MODE` | `enforce` (code default) | `observe` records decisions but forces DRAFT/TAPE |
| `NBN_SOURCE_EVIDENCE_LOOKBACK_HOURS` | `24` | freshness bound for cross-cycle evidence |
| `NBN_SOURCE_RESOLUTION_CACHE_SECONDS` | `3600` | persisted per-item resolution cache across restarts |
| `NBN_CYCLE_LEASE_SECONDS` | `900` | expiring mutex across news, briefing, and audit work |
| `NBN_AUTOPOST_CLASSES` | `primary,corroborated` | autonomy surface (`secondary` ignored even if listed) |
| `NBN_PUBLISH_DELAY_SECONDS` | `30` | the scheduled-publish fuse |
| `NBN_PUBLISH_RECONCILE_SECONDS` | `300` | published-receipt reconciliation cadence |
| `NBN_MAX_AGE_HOURS_ACTIVE/QUIET` | `2.5` / `6` | freshness schedule (fixed `NBN_MAX_AGE_HOURS` overrides) |
| `NBN_POLL_SECONDS` | `60` | RSS/EDGAR cadence |
| `NBN_X_POLL_SECONDS` / `NBN_X_LIST_ID` / `NBN_X_LIST_REFRESH_SECONDS` | `180` / set / `3600` | X poller + list roster |
| `NBN_PERCEPTION_API_KEY` / `NBN_PERCEPTION_POLL_SECONDS` | set (shared) / `900` | Perception source |
| `NBN_MODEL` / `NBN_TRIAGE_MODEL` | `claude-sonnet-5` | writer + triage (effort = API default high) |
| `NBN_EDITOR_MODEL` / `NBN_EDITOR_EFFORT` | `claude-fable-5` / `low` | the editor seat |
| `NBN_NODE_READ_TOKEN` / `NBN_NODE_BASE_URL` | set / production Node | curated one-off discovery + Blocks |
| `NBN_BRIEFING_UTC` | `14:40,Morning;21:15,Afternoon` | Block schedule |
| `NBN_AUDIT_UTC` | `09:00` | self-audit |
| `NBN_REPORT_TOKEN` | set | Desk access (rotate to invalidate the bookmark) |
| `NBN_HEARTBEAT_URL` | set | dead-man's switch |
| `TYPEFULLY_API_KEY` / `TYPEFULLY_SOCIAL_SET_ID` | set / `329191` | the rail |
| `NBN_X_BEARER_TOKEN` | set (shared w/ Node) | X reads — ⚠️ regeneration queued (partial chat exposure 8/30) |
| `NBN_MAX_LLM_CALLS_PER_HOUR` | `60` | runaway-cost guard |

## 12. Costs (order of magnitude)

Railway ~$5-10/mo · Typefully ~$10/mo · X Premium on the handle · LLM: Sonnet triage/
drafting + Fable editor + web-search verification ≈ $2-5/day typical · X reads ≈
$10-20/mo (since_id makes quiet polls free) · Perception rides the shared key.
Run rate ≈ **$100-180/mo all-in**.

## 13. Failure modes

| Failure | Behavior | Where seen |
|---|---|---|
| Transient fetch/search outage | one durable automatic retry, then infrastructure hold with manual retry control | Desk holds, logs |
| Definitive fetch block / paywall / no evidence | held as source/thin-source; other feeds unaffected | Desk holds, logs |
| Typefully confirmation is ambiguous | stored `UNCERTAIN`; no second create | Needs You (VERIFY ON TYPEFULLY / X) |
| Typefully definitively fails | stored `FAILED`; URL fallback only on the known definitive policy rejection | Needs You (PUBLISH FAILED), logs |
| Node discovery unavailable | intake continues from all other sources; status pill turns red; throttle prevents hammering | Desk, logs |
| Node brief unavailable at Block time | Block skipped with a warning | logs |
| Out-of-charter copy | lint holds after one retry | Desk holds ("Style gate") |
| Contextual dup / weak value | editor spikes with reasoning | Needs You (AGREE OR OVERRULE) |
| Press story misclassed `primary` | **the one gate-proof failure** — daily class audit is the net | Self-audit (CLASS SUSPECT) |
| Worker crash or hang | Railway restarts crashes; healthchecks pages on ANY ≥15-min silence; /health 500s when stale | phone |
| Model API outage | cycle errors logged; loop survives; editor outage fails open | /health `last_error` |

Design principle throughout: **models propose, deterministic code vetoes, an editor
judges, and every decision is reconstructible from the tape and the database.**
