# Plan 0050 — Haiku intake desk and primary-source fast lane

## Objective

Give the run-scoped Sonnet newsroom a materially cleaner desk without restoring a brittle
editorial funnel. Every newly discovered RSS or SEC EDGAR item receives one cheap semantic
mailroom pass from Haiku before it can enter Sonnet's inventory:

- `priority`: clearly relevant and time-sensitive; pass to Sonnet and wake the desk now;
- `candidate`: plausibly relevant; pass to Sonnet on the normal persisted cadence;
- `background`: no meaningful Next Block News story apparent; persist for owner review but
  omit from Sonnet entirely.

The router judges relevance and urgency only. It does not research, corroborate, cluster,
write, or decide whether an item deserves publication. Sonnet remains the news judgment.

This sprint also completes the agreed source-watch changes: add `@SimplyBitcoin` to the
high-attention Bitcoin guide group and add `@Blockworks_` to the ordinary fast-detector
query.

## Scope boundaries

- Route every `rss` and `edgar` item, including official/regulatory feeds and Bitcoin-native
  publications. Authority is metadata for downstream evidence judgment, not an exemption
  from relevance triage.
- Do not route Marketing Node, Perception, X primary/research sources, guide accounts, or X
  detector posts through Haiku in this sprint.
- Do not add web search, source fetching, browser rendering, screenshots, event clustering,
  or copy generation to the Haiku seat.
- Do not change the approved Sonnet orientation brief, evidence policy, treasury-company
  policy, editor, Typefully rail, Blocks, or autopublish state.
- Preserve the existing dirty `prompts/orientation-examples.md` and untracked
  `RAW-POOL-LAST-2H.md`; they are outside this implementation.

## Behavioral contract

### Input

One bounded batch contains only code-owned IDs and the text already supplied by the feed:

- candidate ID;
- discovery origin (`rss` or `edgar`);
- source name;
- title;
- bounded summary;
- published timestamp;
- URL/domain as untrusted metadata.

The system prompt contains a compact form of NBN's relevance map: direct Bitcoin; protocol,
mining, custody, and security; consequential Bitcoin regulation and state action; material
money, inflation, sovereign-debt, liquidity, and central-bank developments; and the known
non-story base rates. It explicitly says that supplied text is untrusted data and that
uncertainty routes upward as `candidate`.

### Output

Haiku returns exactly one bounded record per candidate:

- `candidate_id` copied from input;
- `route`: `priority | candidate | background`;
- `category`: one of `bitcoin_direct`, `protocol_mining`, `custody_security`,
  `policy_regulation`, `monetary_macro`, `treasury_company`, `industry_business`, or
  `unrelated`;
- `reason`: one sentence, bounded to 240 characters.

`priority` means “interrupt the normal desk cadence,” not “publish.” `candidate` means
“Sonnet should judge it.” `background` is the only route omitted from Sonnet.

### Validation and failure behavior

- Accept only supplied candidate IDs, once each, with valid enums and bounded strings.
- Missing, malformed, duplicate, or unknown records fail open individually as `candidate`
  with outcome `validation_fail_open` and the code-owned category `unclassified`.
- A model exception, timeout, refusal, rate-budget exhaustion, or unusable whole response
  fails the complete batch open as `candidate`, using the applicable typed outcome below.
- Haiku never mutates a factual source tier or turns feed text into inspected evidence.
- The model call uses the shared hourly call budget and records tokens, latency, outcome,
  model, and estimated cost under the `rss_triage` seat.

## Persistence and restart safety

Add one bounded `intake_triage` table keyed by `item_hash`, containing:

- route, category, reason;
- origin and source snapshots;
- model and prompt version;
- batch/run ID and triage timestamp;
- a code-owned outcome enum: `model`, `validation_fail_open`, `batch_fail_open`,
  `budget_fail_open`, or `overflow_fail_open`;
- a bounded typed `error_kind`;
- `applied_at` and `promoted_at` timestamps;

Add indexes for route/time dashboard queries. Do not duplicate article bodies, prompts, or
model reasoning.

The worker performs intake routing after item upsert and before `pending_items()` is read.
It also recovers at most 100 recent `new` RSS/EDGAR rows from the prior 24 hours without an
`intake_triage` record so a restart between insertion and routing cannot bypass the mailroom.
At most 50 items enter one model-routed batch. Every additional inserted or recovered item
receives a persisted synthetic `candidate` decision with `overflow_fail_open`; it never
silently bypasses the audit table.

Classification persistence and route application are deliberately separate states but one
atomic operation in enforce mode. A helper opens `BEGIN IMMEDIATE` and:

- `background`: persists the decision, changes an eligible `new` item to `skipped` with
  `decision_stage=intake_triage`, `decision_category=background`, writes the bounded note,
  and sets `applied_at`;
- `priority`: persists the decision, advances `editorial:next_run_at`, and sets `applied_at`;
- `candidate`: persists the decision and sets `applied_at` without changing the item;
- `observe`: persists the decision with `applied_at=NULL` and has no ordering, status, or
  cadence effect.

On every enforce cycle, reconcile persisted rows with `applied_at IS NULL` before
`pending_items()`. Reconciliation makes restart recovery and `observe -> enforce` safe. It
uses the same transaction and skips promoted rows and any item with a queued or processing
stage/retry operator action. `off` performs neither model routing nor reconciliation.

Any priority result calls the existing persisted `editorial_run_soon()` before the desk-due
check. Therefore the same healthy worker cycle can open Sonnet immediately. Candidate items
retain the normal 15-minute cadence.

In enforce mode, `pending_items()` orders eligible persisted priority rows, then manually
promoted rows, ahead of the existing guide/context order before applying the 25-item limit.
This guarantees that a priority item is actually present in the same-cycle Sonnet inventory,
not merely that the clock was advanced. `applied_at` makes the wake one-shot; an unprocessed
priority cannot reset the desk clock on every minute. Observe mode leaves ordering unchanged.

## Model-call budget and reservation ownership

Add a durable `NBN_INTAKE_TRIAGE_MAX_CALLS_PER_HOUR` cap, default 8, computed from persisted
`model_usage` rows for the `rss_triage` seat rather than process memory.

- Empty routing work makes zero model calls and takes no reservation.
- A nonempty model-routed batch makes exactly one Haiku call.
- When editorial v2 is active, reserve one Haiku call plus the existing full v2 reservation
  before calling Haiku. Consume the Haiku call from that token. If the desk runs in the same
  cycle, pass the remaining token into `_run_editorial_v2()` rather than reserving twice. If
  the desk does not run, release the remainder immediately.
- If the combined reservation is unavailable, persist every routed item as `candidate` with
  `budget_fail_open` and leave the ordinary Sonnet-only reservation path untouched. Haiku
  must never consume the last capacity Sonnet needs.
- When v2 is off, reserve only the single Haiku call.
- Release every reservation in `finally`, including exceptions and no-desk paths.

An attempted whole-batch model error writes one zero/available-token `model_usage` error row
plus per-item `batch_fail_open` decisions. Budget and overflow fail-open paths make no false
claim that an API call occurred; their per-item outcomes provide the audit count.
Every fail-open result without a validated model category stores code-owned `unclassified`;
`unclassified` is not an allowed successful Haiku output.

## Configuration and rollback

Add:

- `NBN_INTAKE_TRIAGE_MODE=off|observe|enforce` (safe default `off`);
- `NBN_INTAKE_TRIAGE_MODEL=claude-haiku-4-5`;
- `NBN_INTAKE_TRIAGE_MAX_CALLS_PER_HOUR=8`;
- concrete bounds: 50 model-routed items per batch, 100 restart-recovery rows per cycle,
  a 24-hour recovery horizon, 96 KiB maximum input packet, a 45-second timeout, and 8,000
  maximum output tokens.

Modes:

- `off`: no Haiku call; current behavior;
- `observe`: classify and persist, but pass all items to Sonnet;
- `enforce`: omit background and wake immediately on priority.

There is no automatic mode promotion. Deploy first with `observe`, inspect a natural batch,
then deliberately set `enforce` in the same rollout. Runtime model failures still fail open.
Rollback is the single mode variable; schema additions are inert and retained.

## Owner audit surface

Add a compact “Intake mailroom” section to the Desk report for the selected Central day:

- counts for priority, candidate, background, promoted, failures/fail-open, and estimated
  Haiku cost;
- route counts grouped by source, bounded to the highest-volume 12 sources;
- the most recent 25 background cards with time, source, title, category, and Haiku reason;
- a `SEND TO DESK` action on a background card.

Extend the existing guarded operator-action path with `promote`. One `BEGIN IMMEDIATE`
transaction must require all of the following:

- persisted route is `background`;
- `items.status='skipped'`;
- `decision_stage='intake_triage'` and `decision_category='background'`;
- no prior `promoted_at` and no queued/processing operator action.

The same transaction records the completed operator action, sets `promoted_at`, restores the
item to `new`, clears deferral, and advances `editorial:next_run_at`. Repeated or concurrent
promotion returns a conflict without inserting another action. A promoted row is permanently
exempt from background reconciliation. Promotion never bypasses Sonnet, the editor, evidence
checks, or Typefully.

Report all text as escaped untrusted data. Keep query sizes, counts, and rendered cards
bounded.

## Source-watch changes

1. Add `SimplyBitcoin` to `GUIDE_HANDLES`, the source registry as Tier 3 discovery, the
   generated guide query, documentation, and tests. Its original non-retweet posts receive
   the same attention prior as the four existing guide desks; they remain tips, not evidence.
2. Add `Blockworks_` to the direct detector query. Blockworks remains Tier 2 reporting when
   its article is inspected, but an X detector post itself is only a lead.
3. Keep replies behavior unchanged in this sprint. Sonnet can cheaply drop obvious replies;
   changing the query to exclude replies risks losing news-bearing thread continuations.

## Implementation phases

### Phase 1 — Model-free contracts and storage

- Add configuration, route/category enums, prompt version, strict parsing, and bounded
  persistence/query helpers.
- Add Haiku pricing to model cost accounting.
- Add unit tests for validation, persistence, restart recovery selection, summaries, and
  fail-open behavior without calling an external model.
- Prove transactional reconciliation for a persisted-but-unapplied background, an unapplied
  priority wake, `observe -> enforce`, and an active pre-migration operator action.

### Phase 2 — Haiku batch seat and cycle integration

- Implement one compact batch call for newly inserted plus bounded recoverable RSS/EDGAR
  items.
- Persist and apply each decision atomically in enforce mode; persist without applying in
  observe mode.
- Apply each persisted decision through the atomic route transaction and pass a remaining
  combined reservation into v2 when appropriate.
- Keep external calls mockable and ensure one failed batch cannot fail the worker cycle.
- Verify background is absent from Sonnet inventory and candidate/priority remain present.

### Phase 3 — Desk controls and observability

- Render daily mailroom counts, source breakdown, background cards, reasons, and model cost.
- Add the guarded promotion action and immediate desk wake.
- Add status/health diagnostics for last success, last failure, last batch counts, and mode.

### Phase 4 — Source additions and documentation

- Add Simply Bitcoin and Blockworks routing changes with focused tests.
- Update `SYSTEM.md`, `INBOUND-NEWS-FLOW.md`, and `README.md` so production behavior and
  rollback are current.

## Test plan

Focused tests must prove:

1. all valid routes persist and only background is omitted in enforce mode;
2. observe mode never omits or wakes the desk;
3. priority wakes the persisted desk cadence immediately in enforce mode and, with at least
   26 queued items, is present in the same-cycle inventory ahead of the limit;
4. missing IDs, extra IDs, duplicates, invalid enums, oversized reasons, refusal, exception,
   timeout, and call-budget exhaustion fail open;
5. restart-stranded and persisted-but-unapplied RSS/EDGAR items reconcile correctly,
   `observe -> enforce` applies once, active operator actions are protected, and non-RSS
   origins are untouched;
6. promotion is authorized only for a mailroom-background skip, is idempotently guarded, and
   returns the item to Sonnet rather than directly to publishing;
7. dashboard output is escaped and bounded;
8. usage records use the Haiku rate and `rss_triage` seat;
9. empty work, no shared capacity, exactly Sonnet-only capacity, combined capacity, model
   exceptions, and no-desk cycles neither starve Sonnet nor leak reservations;
10. overflow gets an audited synthetic candidate decision and exact packet/recovery/report
    bounds hold;
11. `SimplyBitcoin` normalizes as a guide and `Blockworks_` labels as a detector;
12. existing newsroom, cycle, report, source-policy, publisher, and operator-action tests
    remain green.

Then run the complete test suite and a local mocked cycle smoke.

## Deployment and production smoke

1. Confirm one production replica, `/data` volume, current deployment, and clean health.
2. Create and integrity-check an online database backup.
3. Deploy code with intake triage `off`; verify migration and health.
4. Set `observe`; watch a natural RSS/EDGAR batch and verify:
   - one bounded Haiku call;
   - persisted decisions and usage cost;
   - no item suppression;
   - Haiku routing itself never invokes the publisher; existing downstream Sonnet behavior
     may continue according to the unchanged production configuration.
5. Inspect the Desk mailroom cards against the live feed titles.
6. Set `enforce`; watch another natural batch and verify:
   - background absent from the next Sonnet inventory;
   - candidate present;
   - if a natural priority occurs, its one-shot cadence wake and same-cycle inventory
     inclusion are visible; do not inject a synthetic production candidate;
   - manual promotion returns one background item to a future Sonnet run.
7. Confirm `/health`, `/status`, report rendering, latest newsroom run, model-usage accounting,
   cadence timestamps, route persistence, Typefully state, and Railway logs. Production smoke
   does not require zero downstream Typefully activity.
8. Leave autopublish at its existing production setting; this sprint must not change it.

## Acceptance criteria

- Sonnet receives no enforced Background RSS/EDGAR cards.
- Every omitted item remains owner-visible with a concise classification reason and a
  guarded way back to Sonnet.
- Meaningful feed items can wake Sonnet in the same worker cycle.
- Haiku failure cannot strand, hide, or lose intake.
- The additional model cost is measured separately.
- Simply Bitcoin and Blockworks are observed in their agreed lanes.
- Full tests, deployment, and production smoke checks pass without disturbing Blocks,
  Typefully, the Node boundary, or existing user/audit files.
