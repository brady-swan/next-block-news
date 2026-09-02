# How Next Block News works — the owner's manual

*Current as of 2026-09-01. One always-on
Python worker on Railway watches the news, judges it, writes it, checks itself twice —
once with rules, once with an editor — and publishes to @nextblocknews_ through
Typefully. Two products: breaking singles (anytime) and the Morning/Afternoon Block.*

---

## The 30-second version

```
 every 60s ──────────────────────────────────────────────────────────────────────┐
 │                                                                               │
 │ WATCH          INTAKE GATES      ONE SONNET NEWSROOM              CODE GATES  │ EDITOR        PUBLISH
 │ 12 RSS feeds   dedup by URL      clean run desk: all candidates   novelty,    │ Fable 5 @low: Typefully,
 │ SEC EDGAR      freshness         survey -> selective fetch/search freshness,  │ reader value, scheduled
 │ Perception     (2.5h day/6h      exact-event grouping + judgment  source,     │ exact-receipt +30s (links
 │ X (list+       night/wknd)       + writing -> atomic dossier      numbers,    │ support +     survive),
 │ bundles)       non-English       (fresh context every run)        scope/style │ craft         confirm-polled
 └───────────────────────────────────────────────────────────────────────────────┘
 weekdays 14:40 & 21:15 UTC: fresh Node EIC brief + wire's own catches → the Block
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

**Marketing Node wire pulse (NBN polls every 5 min; Node runs hourly from 5am through
8pm Central, every day):** the Node runs a deliberately narrow,
source-only Scout → Curator profile over an eight-hour window. It gathers only its
curated Perception core, RSS, and curated-X evidence, relates that evidence to active
Node themes, clusters it, and publishes at most 24 discovery candidates. It does not
run a Writer, Editor, or publishing step for this product.

NBN consumes the authenticated
`/api/daily-intel/wire-candidates/v2/latest` `wire-pulse-v2` contract. A pulse must be
complete, schema-valid, no more than three hours old, and internally consistent. Every
reference has a deterministic `ref_id`; the rank-1 reference must be the declared
primary; and the candidate ID commits to the run, event-key version, primary reference,
and canonical primary URL. A fresh accepted/partial pulse is consumed exactly once,
including a zero-candidate pulse. A fresh empty or already-consumed v2 response is valid
and does not invoke the legacy API. NBN falls back to the legacy by-date projection only
when v2 is missing, stale, incomplete, transport-failed, or invalid.

Before projection, the Node now sanitizes each cluster pairwise against its selected
rank-1 source and only removes misaligned refs. Headline, summary, event/date hints,
confidence, reasons, and themes are derived from rank 1 plus surviving refs. Additive
`alignment_diagnostics` reports repaired clusters and dropped refs. NBN still validates
rank-1 identity and headline/event anchors independently. A bad primary becomes an
ordinary candidate with minimal run provenance; one bad related ref removes every Node
hint that might have depended on it. NBN never reimplements Node scoring or theme logic.

Node headlines, summaries, source labels, relevance scores, themes, and event keys are
**untrusted discovery hints**, not evidence or NBN editorial decisions. Ordinary intake
fields come only from the primary source reference, and the item summary is intentionally
empty. NBN independently checks URL safety, re-fetches the page, reclassifies the source
against its own source registry, and independently assesses support/originality. It will
try at most three Node-ranked references that NBN itself classifies P0/Tier 1/Tier 2,
stopping at the first qualified receipt; otherwise its normal web upgrade search runs.
The Node event key is a heuristic cluster hint (artifact ID/reporting period/exact event
date/undated entity-event fingerprint), not the NBN story key. Their mapping is logged.

The optional `node-theme-signal-v1` packet adds a stable theme ID/name, activity trajectory,
bounded 7/14/30-day evidence counts, last-evidence time, and match provenance. NBN strictly
validates it as untrusted context. Node activity is not editorial importance: it cannot
prove a claim, establish corroboration or event identity, lower any gate, or create a quota.
The Node may use building/peaked activity only after confidence, source role, source tier,
and freshness are tied. NBN derives a bounded seven-day coverage snapshot from its own
theme-tagged publications and open Typefully drafts. Missing tagged history is `unknown`,
never “not covered.” The exact snapshot the newsroom saw is preserved on the Desk.

When the same URL already exists in NBN as `new`, the pulse may attach its context and
candidate ID; it may not overwrite title, source, summary, status, or provenance. It
never changes a processed row. The two projects remain separate codebases and databases;
this versioned API is their explicit boundary.

Guide attention uses one nested `guide-signal-v1` namespace regardless of whether the X
post first arrived through the guide query, public list, detector, RSS overlap, or Node.
The merge is symmetric, terminal items are immutable, and valid Node provenance wins.
Under the 8 KiB bound guide metrics, outbound URLs, then text are shed before the guide
enrichment itself is omitted; Node JSON is never sliced.

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
- **Tier 2 research watch** (Kobeissi Letter, Barchart) — eligible for supported
  analysis and market data, but not as authority for claims outside its own work.
- **Bitcoin-news guides** (BitcoinNewsCom, BitcoinArchive, Bitcoin Magazine, TFTC21) —
  proven editorial desks used as strong attention priors and bounded format examples.
  Every original news-bearing post or story link is prioritized into corroboration;
  their post is never evidence and NBN still replaces it with an eligible receipt.
- **Broad detectors** (WatcherGuru, CoinDesk, TheBlockCo) — ordinary tips, never sources.

**Web search (on demand):** NBN calls SerpAPI directly for bounded Google organic
discovery. No model participates in retrieval. Returned URLs and snippets are untrusted
pointers: NBN reclassifies them, fetches eligible pages, and uses Sonnet only to assess
the fetched evidence. Claude's server-side search is a one-use, 45-second last resort.

## 2. Intake gates (deterministic, pre-model)

- Canonical URL dedup across RSS, X, Perception, EDGAR, and Node (tracking parameters
  removed; meaningful query parameters preserved) — first-ingestion provenance is
  immutable and an item is examined once, ever.
- **Freshness** tracks the news metabolism: 2.5h during weekday 7am-7pm ET, 6h
  overnight/weekends (`NBN_MAX_AGE_HOURS_*`; a set `NBN_MAX_AGE_HOURS` overrides with
  one fixed value). EDGAR exempt (date-only stamps; its query bounds age instead).
- **Non-English** (>30% non-Latin letters in the title) — skipped before any model call.

## 3. Judgment (one run-scoped Sonnet newsroom)

One fresh Sonnet 5 context receives the complete bounded intake run (up to 25 items) and
owns survey, selective research, exact-event grouping, editorial judgment, and writing.
The context closes after the run; durable memory remains in SQLite. There is no target
quota. The newsroom may decide that nothing deserves coverage.

The input is a clean editorial desk, not a database dump:

- `run_brief`: assignment, as-of time, inventory count, and the evidence rule;
- `intake_board`: one stable candidate card separating what arrived, why it surfaced,
  registry source metadata, evidence status, unverified event hints, guide priors, and
  operator/retry state;
- `reference_board`: deduplicated, uninspected intake/Node/guide URLs;
- `coverage_board`: separate exact-event lists for reader-covered stories, open Typefully
  drafts, and other recent decisions;
- `theme_board`: broad Node subjects cross-linked to current candidate IDs and NBN's
  bounded recent coverage; and
- `verified_handle_directory`: spelling/identity help only.

Raw Node envelopes, provider plumbing, duplicate fields, and unrecognized discovery keys
never reach Sonnet. Every candidate keeps one stable ID. What arrived is a lead; reference
cards are pointers; themes are context. None becomes evidence until NBN fetches a page and
issues a code-owned `fetch_id`.

The first forced tool call is `submit_survey`, which must account for every candidate.
Sonnet can then fetch an intake item, query SerpAPI, and fetch eligible results through
bounded read-only tools. URL safety, redirects, source-policy classification, page size,
search/fetch counts, total context, rounds, time, and model budget are enforced in code.
`finish_research` closes the research phase. A forced `submit_newsroom_dossier` must then
give exactly one `draft`, `update`, `hold`, or `skip` disposition for every input plus each
formed story's exact members, dated key, reader value, selected receipt, claim bindings,
unresolved questions, and copy. Missing/duplicate items, invented fetch IDs, unsafe story
groups, or malformed output reject the complete dossier before state changes.

Story keys identify exact events, not themes. Recurring purchases, filings, reports, and
readings include their event/disclosure date (at least month/year when the exact day is
unknown). Deterministic actor/entity, event type, date, direction, material-number, and
narrow Treasury-yield guards can veto grouping. Existing aliases and exact reader-covered
checks remain authoritative. `update` is valid only for a material development to an exact
reader-covered event. An open Typefully draft is not reader coverage; later independent
evidence enriches that cluster instead of creating a duplicate draft.

Guide-account posts carry a strong attention and craft prior, so plausible factual posts
are researched rather than dismissed for terseness, hype, or link-only presentation. They
remain tips, never receipts. Node themes can help Sonnet follow meaningful developments
over time, but a shared theme never merges events, establishes support/corroboration,
forces a post, or suppresses a distinct material event.

Factual Bitcoin market state—defined-period price moves, flows, leverage, funding, open
interest, volatility, liquidity, holder activity, and directly relevant rates/yields—is
eligible when a selected receipt supports the figures. Forecasts, price targets, trading
advice, unsupported causal stories, and context-free ticks skip. Relevant official media
links can trigger a transcript/prepared-remarks search rather than failing for missing feed
copy.

Treasury-company intake remains narrow: Strategy, Strive, and Metaplanet are the only
routine candidates, and the allowlist is not approval. Strategy purchases generally clear
the materiality bar; ordinary recurring Strive/Metaplanet buys, rankings, and stock-price
reactions skip absent a consequential development.

The legacy triage → per-item resolver → identity clerk → Writer path remains intact only
for feature-off, shadow comparison, or a failure before materialization. Once the dossier
crosses into `materializing`, it cannot fall back or mix paths. A restart leaves an
interrupted read-only inventory untouched and holds any unknown post-materialization
delivery outcome rather than risking a duplicate.

**Source tier and evidence class are separate:** `config/source_tiers.toml` is the
validated canonical registry. P0 is an official artifact; Tier 1 premier reporting;
Tier 2 reliable specialist reporting/research; Tier 3 discovery only; Tier 4 a wrapper,
aggregator, or syndicator. Unknown sources fail closed. Tier never proves that a page
supports the story, is original, or is independent.

**Classes decide autonomy:**

| Class | Meaning | Autopost |
|---|---|---|
| `primary` | The item IS the official artifact (regulator release, filing, company's own statement) | yes |
| `corroborated` | 2+ eligible independent evidence chains in one canonical event cluster | yes |
| `secondary` | Single-outlet press report | never (code-hardened) → Typefully DRAFT |
| `data` | Pure market/chain data | in the allowed set; dormant until the wire computes its own numbers |
| `briefing` | The Blocks | DRAFT until Brady promotes the class |

**Evidence reconstruction:** the newsroom may recommend support/originality only from text
it actually fetched. Code ignores model-supplied source identity and reconstructs every
typed resolution from immutable fetch records: requested/final/canonical URL, redirect
chain, registry source ID/tier/role/owner, adapter provenance, byline, content fingerprint,
and bounded page text. Official/research identity never proves artifact scope; broad-domain
pages still require the right actor/artifact relationship, and official X is primary only
for the account's own action or statement. Tier 1 is receipt-eligible. Tier 2 must be its
own reporting/research. Tier 3, Tier 4, discovery, aggregator, syndication, and unknown
sources must be replaced by a supporting P0/Tier 1/Tier 2 page or the story holds.

The selected receipt must independently support every factual assertion in the post;
pooled evidence may help understand or corroborate a story but cannot fill a hole under the
linked receipt. Search snippets are pointers only. Fable receives the exact selected text,
code-owned provenance, and declared claim list for an independent fail-closed support check.

The original tip and final receipt are stored separately. A detector plus the artifact it
located is one evidence chain, not two. Eligible evidence persists across cycles for the
canonical story-key family and expires after the configured lookback. Same-owner publications,
aggregators, syndication/content copies, and reports resolving to the same primary artifact
collapse, including lightly boilerplate-modified copies and an entity's website plus its
official X account. Ambiguous originality is never corroboration-eligible. A directly
supporting, artifact-scoped P0 official page may justify `primary`; deterministic code
vetoes `primary` on anything else. Every candidate for one exact story key finishes source
and provider resolution before the strongest final receipt is chosen, so feed order cannot
change the receipt or class and the worker emits at most one post per story group. If a
single-source Typefully draft already exists, later evidence never creates another draft:
it is pooled into the open cluster. When the cluster becomes primary or corroborated and
autopost is enabled, NBN schedules that already-approved Typefully draft in place.

Node-ranked references and guide outbound links are prepared cards on the same research
desk, not a bypass. Their upstream source tiers and roles are discarded and recomputed
locally after fetch. This reduces duplicated searching without delegating source policy,
factual support, or publication authority to the Node or guide account.

The complete inventory identity, opening survey, validated dossier/digest, and per-story
materialization state are durable. Research retries are read-only inputs to the newsroom
until the dossier starts materializing, so a pre-materialization fallback receives the
identical inventory without spending a retry. Existing legacy retry jobs still distinguish
timeouts/transport/rate-limit/5xx/search outages from editorial rejection and permit one
later attempt. Definitive unsafe/4xx/no-evidence outcomes remain normal editorial holds.

## 4. Writing

The same run-scoped Sonnet writes after seeing the complete batch, its exact-event groups,
recent coverage, and selectively fetched evidence. This preserves research context while
still forcing each post to one selected receipt under the charter
(`prompts/wire_voice.md`; prompt index `PROMPTS.md`). The load-bearing seams:
- Every number must appear verbatim in the fetched source text; no text → no post.
- Freshness distinguishes a report's fresh `disclosure_date` from its older
  `underlying_period_end`; the latter must be stated as historical context.
- The model never writes URLs — the system appends the verified receipt (the
  anti-fabrication seam).
- If the wire already covered the exact story, the dossier must use `update` and lead with
  what's new, never re-announce.
- Shape: narrative default in short scannable paragraphs; `•` bullets (max 4) only for
  genuinely enumerable stories; mixed allowed (one run ≤3) — bullets carry lists, prose
  carries the story. Attribute the source ONCE. Mentions only from `handles.json`
  (hand-verified), max 2.
- For a guide-surfaced story, Sonnet receives that post as explicitly untrusted craft
  context. It may borrow information order, structure, and approximate
  length when useful, but not phrasing, emotional framing, or any fact absent from the
  selected receipt.

## 5. The gates (deterministic; one bounded same-session repair)

`nbn/lint.py`: Bitcoin-only scope (no non-Bitcoin token ever; "crypto" only as a
business adjective or inside a quoted official title), no hype/forecast/buy-timing
patterns, number-integrity vs source text, repeated-attribution ban, mention whitelist,
no model URLs, length caps. Block-specific: any "swan" mention rejected; receipts must
be URLs present in the Node's brief. These gates are the wire's identity — NOT Swan
compliance; the wire is not Swan-affiliated content.

Repairable newsroom lint failures are aggregated into one post-only repair request in the
same Sonnet history. The patch may change copy and bounded draft metadata only; it cannot
change action, story membership/key, source, evidence, or claims, and it cannot reopen
research. A named data provider different from the selected receipt holds newsroom output;
the system never swaps a receipt beneath already-written copy.

## 6. The Editor (last mile, before every delivery)

`nbn/editor.py` — **Fable 5 at low effort** (Brady's call). After all deterministic gates,
before publish, it reads the candidate against the wire's last 10 posts for contextual
duplication and craft. For newsroom output it also receives the exact selected receipt
text and code-owned provenance and must explicitly confirm that every final factual
assertion is supported by that receipt. Verdicts are **publish** / **revise**
(downward-only, re-linted and rechecked) / **spike**. A newsroom Editor timeout, refusal,
malformed response, or unknown/false support fails CLOSED to a hold. The migration-only
legacy Editor retains its previous fail-open behavior. Every delivered verdict is recorded
in `posts.editor_note`. The full Editor runs whether final delivery is immediate or a
Typefully draft; `NBN_AUTOPOST_ENABLED` changes delivery mode only.

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

Weekdays 14:40 UTC (Morning, after the Node's 06:10 CT synthesis → EIC chain) and
21:15 UTC (Afternoon, after the 20:30 UTC Daily Intel → quiet EIC chain); once per
window. Fetches Brady's tuned brief
from the Marketing Node read API, folds in the wire's own catches since the previous
Block, renders a 5-9 post thread: post 1 = link-free index (`Morning Block - <date>`,
"Top stories:" bullets, "More inside ➡️" — the wire's one emoji), per-post receipt
links from post 2. Gates: Swan-strip (deterministic), receipts-from-brief-only, full
lint. The worker has a 60-minute catch-up window after each scheduled time, and one
compact feedback retry protects against empty/truncated JSON or a failed factual/style
gate. Before generation, NBN requires the EIC brief to name the exact latest Daily Intel
run for that date and window, match its receipt timestamp, and be no more than four hours
old. A missing, stale, morning-for-afternoon, or prior-run brief fails closed; the worker
retries during the catch-up window and never reuses it. Delivery follows the normal
autopost/Typefully setting. Known
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
and any receipt upgrade; empty polls do not erase it) → **Research health** (backlog now,
selected-day distinct-item activity, and exact last-run resolver paths and outcomes) →
7-day strip (published/held/seen per day,
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

Every cycle also stores one `latest_pulse_url_overlap` telemetry event comparing that
cycle's direct-Perception and broad detector-X URL keys with every reference and every
primary reference in the latest fresh Node pulse. It records timestamp quality and pulse
age. This is an overlap/cost signal only—not a measure of story coverage completeness.
Direct Perception and detector-X have independent switches. Detector-X stays on; direct
Perception may be turned off only after a healthy manual Node pulse, a healthy scheduled
Node Perception pulse, and successful NBN consumption have been observed.

**Switches:** `NBN_AUTOPOST_ENABLED=false` = master kill (everything stages as
drafts). Production currently has it enabled; set it false to pause autonomous
publication. Pause the Railway service to stop even drafting. Tape reads:
`railway ssh "cat /data/tapes/tape-YYYY-MM-DD.md"`.

## 11. The knobs (Railway service variables)

| Variable | Observed 2026-09-01 | Purpose |
|---|---|---|
| `NBN_AUTOPOST_ENABLED` | `true` | master kill switch; autonomy currently enabled |
| `NBN_SOURCE_POLICY_MODE` | `enforce` (code default) | `observe` records decisions but forces DRAFT/TAPE |
| `NBN_SOURCE_EVIDENCE_LOOKBACK_HOURS` | `24` | freshness bound for cross-cycle evidence |
| `NBN_SOURCE_RESOLUTION_CACHE_SECONDS` | `3600` | persisted per-item resolution cache across restarts |
| `NBN_CYCLE_LEASE_SECONDS` / `NBN_CYCLE_LEASE_HEARTBEAT_SECONDS` | `120` / `30` | renewable mutex; dead deploy owners expire within two minutes |
| `NBN_AUTOPOST_CLASSES` | `primary,corroborated` | autonomy surface (`secondary` ignored even if listed) |
| `NBN_PUBLISH_DELAY_SECONDS` | `30` | the scheduled-publish fuse |
| `NBN_PUBLISH_RECONCILE_SECONDS` | `300` | published-receipt reconciliation cadence |
| `NBN_MAX_AGE_HOURS_ACTIVE/QUIET` | `2.5` / `6` | freshness schedule (fixed `NBN_MAX_AGE_HOURS` overrides) |
| `NBN_POLL_SECONDS` | `60` | RSS/EDGAR cadence |
| `NBN_X_POLL_SECONDS` / `NBN_X_LIST_ID` / `NBN_X_LIST_REFRESH_SECONDS` | `180` / set / `3600` | X poller + list roster |
| `NBN_X_DETECTOR_ENABLED` | `true` | broad detector-X lane; independent of curated primary/research X |
| `NBN_PERCEPTION_API_KEY` / `NBN_PERCEPTION_POLL_SECONDS` | set (shared) / `900` | direct Perception fallback lane |
| `NBN_PERCEPTION_DIRECT_ENABLED` | `true` until production cutover gate passes | lets Node own Perception discovery once safely proven |
| `NBN_MODEL` / `NBN_TRIAGE_MODEL` / `NBN_TRIAGE_EFFORT` | `claude-sonnet-5` / `claude-sonnet-5` / `medium` | run newsroom; legacy fallback keeps the separate triage setting |
| `NBN_RUN_NEWSROOM_MODE` / `NBN_RUN_NEWSROOM_FALLBACK` | `off` (pre-rollout) / `legacy` | `off → shadow → draft → live`; fallback only before materialization |
| `NBN_RUN_NEWSROOM_MAX_ROUNDS` / `MAX_TOOL_CALLS` | `8` / `24` | bounded same-session model/tool loop |
| `NBN_RUN_NEWSROOM_MAX_SEARCHES` / `MAX_FETCHES` | `8` / `16` | per-run retrieval bounds |
| `NBN_RUN_NEWSROOM_MAX_FETCH_CHARS` / `MAX_FETCH_TOTAL_CHARS` | `8000` / `160000` | receipt text bounds |
| `NBN_RUN_NEWSROOM_MAX_INITIAL_BYTES` / `MAX_HISTORY_BYTES` | `98304` / `491520` | clean-desk and total-context ceilings |
| `NBN_RUN_NEWSROOM_TIMEOUT_SECONDS` | `240` | wall-clock ceiling before pre-materialization fallback |
| `NBN_EDITOR_MODEL` / `NBN_EDITOR_EFFORT` | `claude-fable-5` / `low` | independent, fail-closed newsroom support/craft editor |
| `NBN_NODE_READ_TOKEN` / `NBN_NODE_BASE_URL` | set / production Node | v2 wire pulse, legacy fallback, and Blocks |
| `NBN_NODE_PULSE_MAX_AGE_SECONDS` | `10800` | maximum accepted v2 pulse age (3h) |
| `NBN_YIELD_IDENTITY_NORMALIZER_ENABLED` | `false` | narrow clerk-proposed, code-validated same-day U.S. 10-year-yield identity rule |
| `NBN_BRIEFING_UTC` | `14:40,Morning;21:15,Afternoon` | Block schedule |
| `NBN_BRIEFING_MAX_AGE_SECONDS` | `14400` | second freshness bound after exact Node run-provenance checks |
| `NBN_AUDIT_UTC` | `09:00` | self-audit |
| `NBN_REPORT_TOKEN` | set | Desk access (rotate to invalidate the bookmark) |
| `NBN_HEARTBEAT_URL` | set | dead-man's switch |
| `TYPEFULLY_API_KEY` / `TYPEFULLY_SOCIAL_SET_ID` | set / `329191` | the rail |
| `NBN_X_BEARER_TOKEN` | set (shared w/ Node) | X reads — ⚠️ regeneration queued (partial chat exposure 8/30) |
| `NBN_MAX_LLM_CALLS_PER_HOUR` | `60` | runaway-cost guard |
| `SERPAPI_KEY` | set (shared account w/ Node) | model-free Google organic source discovery |
| `NBN_SERPAPI_TIMEOUT_SECONDS` / `NBN_SERPAPI_MAX_RESULTS` | `15` / `5` | bounded direct-search request |
| `NBN_HOSTED_SEARCH_ENABLED` / `NBN_HOSTED_SEARCH_TIMEOUT_SECONDS` | `true` / `45` | tightly bounded last-resort model search |

## 12. Costs (order of magnitude)

Railway ~$5-10/mo · Typefully ~$10/mo · X Premium on the handle · LLM: one bounded Sonnet
newsroom context per non-empty run + Fable per surviving story (measure during rollout;
expected same order of magnitude as the fragmented path) · SerpAPI search usage
rides the Node's shared account · X reads ≈ $10-20/mo (since_id makes quiet polls free) ·
Perception rides the shared key.
Run rate ≈ **$100-180/mo all-in**.

## 13. Failure modes

| Failure | Behavior | Where seen |
|---|---|---|
| Transient fetch/search outage | one durable automatic retry, then infrastructure hold with manual retry control | Desk holds, logs |
| Definitive fetch block / paywall / no evidence | held as source/thin-source; other feeds unaffected | Desk holds, logs |
| Typefully confirmation is ambiguous | stored `UNCERTAIN`; no second create | Needs You (VERIFY ON TYPEFULLY / X) |
| Typefully definitively fails | stored `FAILED`; URL fallback only on the known definitive policy rejection | Needs You (PUBLISH FAILED), logs |
| Node discovery unavailable | intake continues from all other sources; status pill turns red; throttle prevents hammering | Desk, logs |
| Node brief unavailable, stale, or from the wrong Daily Intel run/window | Block waits through its catch-up window, then skips without publishing | logs |
| Out-of-charter copy | one same-session post-only repair, then hold | Desk holds ("Style gate") |
| Contextual dup / weak value | editor spikes with reasoning | Needs You (AGREE OR OVERRULE) |
| Newsroom timeout/malformed dossier before materialization | identical frozen inventory enters legacy fallback (or holds if configured) | Desk last run, logs |
| Worker restart during newsroom research | run marked fallback; untouched items remain available | Desk last run, logs |
| Worker restart after materialization began | locally recorded deliveries stand; unknown outcomes hold and never auto-retry | Desk holds, newsroom run state |
| Fable support unknown/false on newsroom copy | fail-closed hold; no autonomous delivery | Desk holds, editor note/logs |
| Press story misclassed `primary` | **the one gate-proof failure** — daily class audit is the net | Self-audit (CLASS SUSPECT) |
| Worker crash or hang | Railway restarts crashes; healthchecks pages on ANY ≥15-min silence; /health 500s when stale | phone |
| Model API outage | newsroom falls back only before materialization; newsroom Editor fails closed; loop survives | Desk, /health `last_error` |

Design principle throughout: **models propose, deterministic code vetoes, an editor
judges, and every decision is reconstructible from the tape and the database.**
