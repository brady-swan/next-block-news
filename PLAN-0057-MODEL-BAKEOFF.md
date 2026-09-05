# Plan 0057 — Isolated NBN model bake-off

**Status:** Approved after four independent lead-review passes. Phase-one execution complete;
owner-blind adjudication and a genuinely prospective holdout remain before any production adoption.

## Objective

Determine provisionally which affordable model configuration best performs each existing NBN
seat: intake/assignment preparation, run-scoped news judgment and writing, bounded research, and
independent editing. Measure Grok's base editorial behavior separately from its live X Search
retrieval advantage.

This sprint produces evidence only. It does not change the production model, prompt, cadence,
source policy, publishing behavior, Typefully state, or routing path. Adoption of any winner is a
separate owner-approved production change.

## Hard boundaries

- Historical evaluation runs in a standalone serialized CLI using a detached database snapshot,
  a separate evaluation SQLite database, and an artifact directory outside production state.
- The evaluation process receives provider model credentials only. It does not receive Typefully
  credentials, production database write credentials, publisher or operator tools, production
  source cursors, or a production model-call reservation.
- Evaluation code reads only `NBN_EVAL_ANTHROPIC_API_KEY`, `NBN_EVAL_OPENAI_API_KEY`,
  `NBN_EVAL_XAI_API_KEY`, and optional `NBN_EVAL_SERPAPI_KEY`; it never performs an implicit
  fallback. On September 5, the owner explicitly authorized reuse of the existing Anthropic,
  OpenAI, and xAI credentials for this bounded test. At launch, a sanitizing process boundary maps
  those three authorized values into the evaluation namespace and removes the ordinary key names,
  Typefully credentials, database paths, and source tokens before Python starts. Provider-side
  quota is therefore shared, while attribution and the lifetime `$40` cap remain independent in
  the evaluation ledger. Missing explicitly mapped credentials still skip before transport.
- Historical and editor lanes cannot call the live web. Research conditions are explicitly
  separate and read-only.
- Outputs never enter production decision, story, item, storyline, publisher, or audit tables.
- Before and after each run, fingerprints of the detached source snapshot and selected production
  table counts/checksums are compared. Tests prove publisher and operator functions are absent
  from the evaluator's tool registry.
- Preserve `RAW-POOL-LAST-2H.md`, `X-ALGORITHM-DISTRIBUTION-BRIEF.md`, `audit/`, the owner's
  orientation examples, and all unrelated working-tree changes.
- The paid benchmark has a hard $40 lifetime cap. The runner reserves a conservative worst-case
  cost before every request and refuses a call or lane that cannot fit.

## Questions

1. Can GPT-5.4 Mini or Grok 4.3 replace Sonnet 5 at the newsdesk without losing selection,
   evidence judgment, continuity, or writing quality?
2. Is `low` or `medium` the better provider-local effort for Mini and Grok? Effort labels are not
   treated as equivalent across providers.
3. Does Grok improve X-native judgment when all models see identical evidence?
4. Does Grok's live X Search retrieve useful facts or context that NBN's current search surface
   misses, and do non-Grok editorial models agree that those discoveries are publishable?
5. Can a cheaper model match Opus or Sonnet as the independent editor?
6. Can GPT-5.6 Luna replace Haiku 4.5 for the two high-volume preparation jobs without hiding
   worthwhile leads or degrading the desk packet?

## Exact conditions

Free model-list/capability discovery may run before corpus generation. Before any inference or
billable tool probe, initialize and validate the versioned price manifest and durable hard-cap
ledger described below. Every paid capability probe reserves and settles cost exactly like a
corpus call. Avoid `latest` aliases and record both requested and provider-returned identity.

Where a provider exposes no immutable dated snapshot for a selected Claude or Grok condition,
record that limitation, the exact alias requested, the provider-returned identity, and the raw
redacted model-list/capability response captured at benchmark start. Never silently substitute a
newer alias target during a resumed run.

### Newsdesk effort calibration

- `claude-sonnet-5`, effort `medium` — control, three repeats.
- `gpt-5.4-mini-2026-03-17`, effort `low`, three repeats.
- `gpt-5.4-mini-2026-03-17`, effort `medium`, three repeats.
- `grok-4.3`, effort `low`, three repeats.
- `grok-4.3`, effort `medium`, three repeats.

The winning effort for each challenger advances. If quality and reliability are tied, lower cost
wins. A more expensive Grok model is not included initially. Grok 4.6 becomes a later spot-check
only if 4.3 shows distinctive X/editorial value but an identifiable capability shortfall.

### Historical newsdesk holdout

- `claude-sonnet-5`, effort `medium`.
- Winning GPT-5.4 Mini condition.
- Winning Grok 4.3 condition.

Each packet runs twice. The Sonnet control is repeated equally, so consistency comparisons remain
paired.

### Preparation

- `claude-haiku-4-5-20251001` — pinned production-family control. Production currently inherits
  the repository's `claude-haiku-4-5` convenience alias because neither prep model environment
  variable is set; the evaluation uses the immutable snapshot instead.
- `gpt-5.6-luna`, effort `low` — challenger.
- Luna `medium` is added only if low shows a material comprehension, preservation, or recall
  weakness. It is not run merely because medium is the provider default.

Test intake mailroom and assignment-desk preparation separately; never blend their scores.

### Editor

- `claude-opus-5`, effort `medium` — production control. A read-only Railway variable snapshot at
  plan revision time showed `NBN_EDITOR_MODEL=claude-opus-5` and
  `NBN_EDITOR_EFFORT=medium`; retain the redacted configuration snapshot in the benchmark
  manifest. The repository default remains Sonnet and is not treated as proof of deployed state.
- `claude-sonnet-5`, effort `medium`.
- Winning GPT-5.4 Mini condition.
- Winning Grok 4.3 condition.

The editor sees fixed evidence and has no search tools. Writer and editor results are scored by
seat. A shared-model writer/editor configuration does not automatically advance because
independence is itself a useful system property.

## Provider-equivalent execution

Thin evaluation-only adapters normalize:

- system and user content;
- one strict semantic JSON result contract per lane;
- provider-specific schema syntax, with every size/count/enum bound also enforced in code;
- maximum assistant/tool rounds, searches, fetches, fetched bytes, output tokens, timeouts,
  retries, and validation behavior;
- provider-local effort configuration;
- a common internal stop/outcome taxonomy.

Every request records:

- evaluation run, lane, condition, case, repetition, and randomized execution position;
- requested and returned provider/model/version, API endpoint, effort, and service tier;
- orientation/prompt version and hash, semantic tool-contract hash, normalized input hash, and
  exact provider wire-payload hash with secret values removed;
- timestamps, latency, retries, timeout/refusal/invalid-schema status, and stop reason;
- ordinary, cached, cache-write, reasoning, and output tokens where reported;
- provider-reported cost and tool usage plus the versioned local price estimate.

Invalid JSON, refusal, timeout, rate limit, and exhausted output remain in the denominator as
reliability failures. A retry is a separate billed request attached to the same attempt and cannot
silently replace the failure.

## Frozen benchmark construction

### As-of manifest

Each historical packet has an immutable manifest containing:

- capture timestamp and historical editorial clock;
- source item IDs, timestamps, original captured title/summary/post text, provenance, URL, and
  engagement fields available then;
- the exact orientation, source policy, recent 48-hour post cards, open-draft state, exact-event
  continuity, storyline cards, Haiku preparation, research receipts, and editor state available
  at that time;
- a field-by-field origin and capture timestamp;
- SHA-256 hashes for every artifact and the assembled packet.

Every model-visible field must carry a provable `available_at` no later than the packet's
`editorial_clock`. The `validate` command rejects the entire case when any visible field lacks
that proof or crosses the clock. Later-synced engagement, edited/current page text, reconstructed
receipts, later editor state, later Typefully state, and unverifiable fields are excluded rather
than guessed. Artifact creation time is not proof that its contents were historically available.

Historical URLs are identifiers only. Models grade and write only from captured text and receipts;
they cannot fetch a page that changed later. Factual-support grading uses the frozen evidence key,
not later knowledge or owner taste.

Prefer events after every candidate model's published knowledge cutoff. Any older event is labeled
`training_contaminated`. Such a case is excluded from disposition, newsworthiness, evidence,
factual, duplicate/UPDATE, and continuity comparisons. It may score only bounded copy/style or
schema behavior for which later knowledge cannot confer an advantage.

### Disjoint sets

The effort-calibration set and historical holdout are disjoint. The holdout excludes cases quoted
or used to develop the current orientation brief, prompt examples, owner rules, or model-cost
experiments. A case registry records exclusion reasons before the first model output is generated.

### Calibration set

Twelve difficult events arranged into three production-shaped four-story desks, stratified across
publishable, negative, duplicate/update, elevated claim, treasury, market data, primary artifact,
guide/X, and stale/thin examples. Some cases may carry multiple strata. Every condition runs three
times in randomized order.

### Historical holdout

Forty-eight real event clusters in twelve four-story desk packets. Predeclare the strata and
minimum representation before sampling:

- 12 owner-confirmed or otherwise adjudicated publishable events;
- 10 explicit negatives;
- 6 duplicate/update/continuity cases;
- 5 elevated claims;
- 5 treasury boundaries;
- 4 market-data or macro boundaries;
- 3 primary-artifact leads;
- 3 guide/X or stale/thin leads.

Where a case belongs to several categories, choose one primary stratum for sampling and retain all
secondary labels for analysis. Do not disclose this balance to candidate models.

### Preparation corpus

Use 250–300 captured raw items across RSS, EDGAR, government feeds, ordinary X, guide accounts,
primary sources, duplicates, boilerplate, unrelated material, direct Bitcoin, and subtle
Bitcoin-adjacent leads. Predeclare the expected preservation fields and minimum acceptable route
for owner-confirmed or later-published items.

Every item entering a prep correctness denominator must have a preregistered acceptable route set,
acceptable category set, same-event grouping key, permissible storyline/source-lead mappings, and
field-preservation key as applicable to its lane. Fully label negatives as well as positives.
Unadjudicated items may measure only cost, latency, schema validity, and literal field preservation;
they never enter recall, suppression, category, grouping, or source-lead correctness denominators.

### Editor corpus

Use 24 fixed, pre-editor drafts: eight already good, eight salvageable, and eight requiring
rejection or major correction. Include the exact evidence, recent coverage, event identity, and
owner feedback basis while hiding the final production editor result from candidate models.

## Preregistered case key and scoring

Before paid generation, each scored case records:

- acceptable disposition set, plus dispositions that are clearly wrong;
- required facts and permissible factual range;
- supported and unsupported material claims from the frozen evidence;
- canonical event identity and expected duplicate/UPDATE relationship;
- freshness-label allowance;
- explicit owner judgment and provenance when one exists;
- serious-error triggers;
- which dimensions are unscored because no reliable ground truth exists.

Owner review remains blind and is the final authority on editorial taste and usefulness. Frozen
evidence remains the authority on factual support. Model names, costs, latency, and ordering are
hidden until adjudication is locked.

Do not collapse seats into a single opaque score. Report paired case wins, losses, ties, invalid
outputs, and bootstrap confidence intervals where sample size permits. Conclusions are
provisional for this workload, not universal model claims.

### Newsdesk scorecard

- 35% disposition alignment and must-cover recall;
- 20% evidence judgment and material-claim support;
- 20% finished-copy usefulness, lede, and information order;
- 15% clarity, paragraph rhythm, restraint, and NBN voice;
- 5% duplicate/UPDATE/storyline continuity;
- 5% reliability, latency, and cost reported separately as components.

### Preparation scorecards

Intake mailroom:

- 45% recall/minimum-route preservation on worthwhile leads;
- 25% correct background suppression;
- 15% category quality;
- 10% exact field preservation and valid schema;
- 5% latency and cost.

Assignment desk:

- 30% worthwhile-lead advancement;
- 25% accurate event summary and Bitcoin relevance;
- 20% useful research objective and source leads;
- 15% event grouping and advisory storyline selection;
- 10% field preservation, compactness, reliability, latency, and cost.

### Editor scorecard

- 30% approve/revise/drop judgment;
- 25% material factual-support handling;
- 20% lede and information-order improvement;
- 15% clarity/scannability improvement without flattening good prose;
- 10% restraint: preserving good drafts, ignoring immaterial differences, and avoiding needless
  research or rejection.

### Serious errors and advancement

Serious errors are counted by distinct case, not repetition. Repetition measures instability.

- Catastrophic: fabricated evidence/receipt, invented material fact presented as supported, or an
  unsafe unsupported allegation. One catastrophic case disqualifies a condition.
- Serious: ordinary off-list treasury publication, a known duplicate presented as `NEW:`, material
  unsupported claim, or passing a preregistered must-cover event without defensible reason. Serious
  errors on at least two distinct cases disqualify a condition.

A challenger can advance only if it is not disqualified, remains within five percentage points of
the best eligible condition on owner-adjudicated disposition alignment, has no material factual-
support regression, and wins or ties at least half of paired copy comparisons against the control.
If editorial results are tied, lower projected production cost wins. A substantial quality winner
may be recommended despite smaller savings, with the tradeoff stated explicitly.

## Research and X Search experiment

### Frozen judgment pass

Twelve unresolved leads first receive an identical captured evidence packet with tools disabled.
Sonnet, winning Mini, and winning Grok conditions decide whether to pass, research, hold, or draft.
This isolates editorial judgment.

### Prospective live retrieval pass

Collect unresolved leads prospectively or enforce an exact historical cutoff. Randomize condition
order and record search timestamps, query text, result IDs/URLs, and returned snippets because live
search is not repeatable.

Conditions:

1. Sonnet with current NBN search/fetch tools.
2. Mini with semantically identical NBN tools.
3. Grok with semantically identical NBN tools and native X Search disabled.
4. Grok with those tools plus bounded xAI X Search, named `grok-4.3+x-search`.

All conditions receive identical round, search, fetch, byte, output, retry, and timeout budgets.
The X-enabled condition receives no larger overall research-turn budget; its extra tool is the
treatment. Every condition is read-only.

The current NBN search path uses shared SerpAPI quota, so the evaluator never receives the
production SerpAPI credential. Conditions requiring NBN SerpAPI search run only when an isolated
`NBN_EVAL_SERPAPI_KEY` is available; otherwise those conditions are marked `skipped:no_isolated_credential`
and the report limits its claims to frozen judgment and provider-native retrieval conditions.

Normalize every X-only discovery into a source card without revealing which model found it. Give
those cards to Sonnet and the winning non-X challenger for blind publishability and usefulness
judgment. This prevents Grok from grading its own retrieval advantage.

Measure resolution, receipt strength, independent-source handling, useful discoveries, chatter
inflation, turns, latency, provider failures, and full token/search cost.

## Cost cap

Before the first paid benchmark call, compute a dry-run envelope from captured packet byte/token
sizes. Include:

- all planned calls and repetitions;
- configured output/reasoning ceilings;
- cold and expected cached input rates;
- maximum retry charges;
- SerpAPI and xAI web/X Search invocations;
- any optional 24-hour shadow collection;
- provider price-table version and retrieval date.

One serialized runner owns a durable cost ledger created before any paid inference or tool probe.
Before each request it reserves that condition's
conservative maximum; after completion it settles against provider-reported usage and retains the
raw usage object. Failed and retried calls remain charged. Unknown provider costs settle to the
larger reserved amount. The runner refuses the next call or entire lane when its reservation would
cross $40. Live shadow is conditional on budget remaining.

On restart, any reservation without a durable settlement remains charged at its full conservative
amount until an explicit provider-supported reconciliation proves otherwise. A crashed capability
probe therefore cannot reopen budget accidentally.

## Implementation

Keep this deliberately small:

- one `nbn/eval/` package containing immutable case models, thin Anthropic/OpenAI/xAI adapters,
  common validators, scoring helpers, and the serialized runner;
- one `scripts/model_bakeoff.py` CLI with `probe`, `freeze`, `validate`, `estimate`, `run`,
  `adjudicate`, and `report` commands;
- one evaluation SQLite database plus JSONL request/result artifacts under an ignored explicit
  directory such as `.model-eval/`;
- reuse pure packet builders and validators where feasible, without importing publisher modules
  or refactoring production model routing;
- focused unit tests for hashes, cutoff manifests, disjointness, preregistration, provider schema
  normalization, usage parsing, cost reservation/settlement, invalid-output accounting, blinded
  ordering, and mutation isolation.

No production provider abstraction, production schema change, Desk page, prompt rewrite, model
switch, or winner cutover belongs in this sprint.

## Optional live shadow

The 24-hour shadow is an operational/cost confirmation, not an additional decisive quality sample.
Run it only if offline finalists and remaining budget justify it.

If deployment is required, use an isolated Railway service that receives one append-only captured
input stream and fans the same packet to every condition. It must not mount `/data`, share source
cursors, access Typefully secrets, participate in model reservations, or write production tables.
Prefer a local detached replay/collector if it can capture the necessary day without introducing a
production dependency.

## Deliverables

- frozen case manifests and exclusion registry;
- preregistered evidence/adjudication keys;
- capability-probe and dry-run cost report;
- raw redacted provider requests, outputs, usage, tool records, and hashes;
- anonymized owner-review sheet containing every publish/pass disagreement, serious error,
  representative copy, and X-only discovery;
- seat-specific paired scorecards, uncertainty, latency, and cost projections;
- a recommendation for each seat and end-to-end combinations;
- a separate owner-approved plan for any production adoption.

## Verification

- Unit and integration tests pass on the repository's supported Python version.
- Evaluation validation rejects overlapping calibration/holdout cases, unregistered cases, live
  URLs as evidence, any model-visible field whose `available_at` is absent or later than the
  editorial clock, missing hashes, unknown prices, incomplete usage, and mutation-capable tools.
- Tests inject unique canary values for every provider credential and assert that none appears in
  JSONL, evaluation SQLite rows, redacted wire payloads, exception strings, captured logs, or final
  reports. This covers Anthropic, OpenAI, xAI, and SerpAPI evaluation canaries. Redaction happens
  before persistence and before logging, including transport failures.
- An isolation regression sets production `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`,
  and `SERPAPI_KEY` to distinct canaries while every `NBN_EVAL_*` key is absent. Every affected
  condition must skip before constructing a provider transport, and no production canary may
  appear in artifacts, logs, errors, or the evaluation database. Provider adapters receive their
  evaluation key explicitly and never permit SDK environment discovery.
- A no-cost fixture run produces deterministic manifests, blinded ordering, and scorecards.
- Capability probes confirm exact IDs, structured output/tool behavior, usage fields, and effort
  settings before corpus calls.
- Detached source hashes and selected production fingerprints remain unchanged.
- A one-case paid smoke stays within its reservation and produces a complete redacted artifact.
- A restart test leaves a paid capability-probe reservation unsettled, reopens the ledger, and
  proves the full reserved amount remains unavailable.
- Full execution cannot cross $40 even after interruption and restart.

## Independent review

The first three reviews returned `CHANGES_REQUIRED`; the fourth returned `APPROVED`. This
revision incorporates all blocking
findings: valid disjoint holdouts and strict field-level as-of evidence, contamination exclusions,
fully adjudicated preparation scoring, preregistered seat scoring, pinned controls and captured
deployed configuration, provider-equivalent execution, judgment/retrieval separation, structural
mutation and quota-credential isolation, a persisted hard cost cap that includes paid probes and
crash recovery, and deliberately small evaluation-only implementation.
