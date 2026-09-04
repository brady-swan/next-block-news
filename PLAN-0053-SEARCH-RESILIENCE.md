# Plan 0053 — Search resilience and same-event receipt pooling

## Objective

Make NBN's source-discovery path reliable enough for a 15-minute newsroom without turning search
into a new subsystem or weakening Sonnet's editorial authority. The immediate production failure
was not publisher bot blocking: the shared SerpAPI Starter allowance reached 1,000/1,000 searches.
The owner has upgraded the account to Developer; production now reports a 5,000-search allowance
with 4,000 remaining before the September 6 renewal.

This sprint will:

- distinguish quota exhaustion, hourly throttling, provider/transport failure, and downstream page
  fetch blocking;
- reuse recent search work across newsroom runs;
- keep a provider outage or exhausted quota from consuming one doomed search attempt every 15
  minutes while still detecting a renewal or upgrade promptly;
- retain alternate same-event reporting on Sonnet's desk instead of suppressing it before evidence
  can be pooled;
- expose search capacity, cache use, and failure state on the Desk and in run telemetry.

The standard remains practical and editorial: search results are research pointers, fetched pages
are evidence, and Sonnet decides whether the available evidence is enough.

## Scope boundaries

- Change only the Next Block News repository and Railway service. Do not modify the Marketing Node.
- Do not add a second search provider in this sprint. First measure SerpAPI after quota governance,
  caching, and receipt pooling remove known waste.
- Do not change source tiers, Bitcoin scope, treasury-company policy, writer/editor models,
  editorial cadence, Typefully behavior, or autopublish state.
- Do not automatically renew, upgrade, purchase, or otherwise mutate the SerpAPI account.
- Do not bypass paywalls or publisher access controls. A blocked page remains a typed fetch result;
  the desk may use another public receipt.
- Do not treat search snippets, Haiku grouping, or account metadata as factual story evidence.
- Preserve the owner's modified `prompts/orientation-examples.md` and untracked working files.

## Architecture

### 1. Structured provider and quota status

Extend the SerpAPI client with a bounded, free account-status request. Return only safe operational
fields: plan name, monthly allowance, usage, remaining searches, hourly throughput/usage, renewal
date, and check time. Never return or log the API key, account email, account ID, request URL, or
raw response.

Make `SearchError` carry a typed kind and optional retry time. Parse the bounded error body and
`Retry-After` header so HTTP 429 becomes:

- `quota_exhausted` when the account has no searches left;
- `rate_limited` for hourly throughput throttling;
- `provider_error` when the response is not safely classifiable.

Transport, invalid-response, HTTP, and provider errors remain separately typed. Error text is
bounded and scrubbed before persistence or display.

### 2. Durable provider state with active recovery

Add an additive SQLite `search_provider_state` table keyed by provider. Persist the safe account
snapshot, state, next provider-search retry time, `last_status_attempt_at`,
`last_status_success_at`, last successful search, consecutive failures, and a bounded safe error.
The last successful account snapshot is preserved when a later status request fails; failure
metadata never overwrites its allowance or renewal fields.

Before a provider search HTTP request:

1. serve a valid local query-cache hit even if the provider circuit is open;
2. refresh SerpAPI account status when the last successful snapshot is older than five minutes,
   including while a quota circuit is open, while separately throttling failed account checks to
   at most one attempt per five minutes so multiple tool calls cannot hammer the free endpoint;
3. clear the circuit immediately when the free account endpoint shows new capacity after an
   upgrade, renewal, or added credits;
4. skip the provider search endpoint when remaining capacity is zero;
5. respect a safe `Retry-After` value for hourly throttling, otherwise use a bounded five-minute
   retry window;
6. use a short bounded cooldown for repeated transport/provider failures, not a month-long hold.

If account status is unavailable and there is no explicit provider-search circuit, search fails
open to the ordinary provider request—including first-run/unknown state. An old last-good snapshot
with capacity also remains advisory when its refresh fails. Only an explicit known-zero allowance,
an unexpired throughput cooldown, or a provider-search failure circuit prevents the request.
`Retry-After` is parsed as seconds or an HTTP date, clamped to 1–3,600 seconds, and ignored when
invalid. Restart and repeated-tool-call behavior use the same persisted timestamps.

A known-zero quota circuit is not permanent. Its retry time is the recorded renewal time, or a
bounded six-hour fallback when renewal is absent or invalid. Once that time arrives, if account
status still cannot be refreshed, one worker may atomically claim a half-open provider probe using
a random claim token, claim time, and lease expiry. The lease is bounded to the configured provider
search timeout plus a small fixed margin. Acquisition/reclamation uses one SQLite immediate
transaction and compare-and-set conditions: an unexpired claim excludes concurrent workers, while
an expired abandoned claim may be replaced after a worker crash. Only the matching claim token may
record the result or release the lease. Success clears the circuit; another typed quota response
records the next known renewal/fallback window; any other typed failure uses its ordinary bounded
cooldown. This prevents every 15-minute desk from probing without making a crashed probe permanent.

The existing in-run circuit remains as a second guard, but a known durable outage must not consume
another provider HTTP attempt in each fresh Sonnet session. Account-status failures must not by
themselves block search when the last known state had capacity and no provider-search circuit is
open.

No background poller is added. The free account endpoint is refreshed lazily on search demand and
the last safe snapshot is rendered on the Desk.

### 3. Persistent bounded query cache

Add an additive SQLite `search_query_cache` table with a versioned hashed cache key, normalized
query, provider, bounded results JSON, creation/expiry times, and hit count. Cache identity includes
every result-affecting request parameter: key version, provider, engine, normalized query, locale,
result limit, and pagination/start value. Normalize Unicode and whitespace while preserving
meaningful operators, quoting, and word order. Never sort tokens or reuse results across
semantically different queries.

- Cache successful organic results, including an empty result set, for one hour by default.
- Bound each entry to five public HTTP(S) results; query to 400 characters, URL to 2,000, outlet to
  160, title to 300, snippet to 1,200, and the serialized result array to 20 KiB.
- Reclassify and validate URLs at read time; corrupt, oversized, unsafe, or expired entries miss
  safely and are pruned.
- Count cache hits, misses, actual provider-search HTTP attempts, provider skips, and failures
  separately. A cache hit does not consume the run's provider-search capacity but remains one bounded
  tool action.

The one-hour TTL matches SerpAPI's documented cache horizon and spans four NBN desk intervals. It
is configurable, but not dynamically extended during outages because stale discovery can hide a
new development.

### 4. Reusable event-scoped search pointers

Extend `search_web` so Sonnet may supply up to eight current candidate IDs with its query.
Candidate IDs remain code-issued and are validated against the active desk. Successful result
pointers are stored in a bounded `search_result_pointers` table for six hours by default. Pointer
reuse is allowed only for an exact candidate hash or a pre-existing code-owned canonical story key
already attached to that candidate. A Haiku `event_group`, Node theme, model story ID/slug, search
query, or headline similarity can never create a durable pointer scope.

On a later run, matching current candidates receive these recent URLs, titles, outlets, snippets,
and observation times on the reference board. They remain explicitly `uninspected_pointer`, never
evidence. Sonnet can fetch a useful prior result directly instead of rephrasing the same search.
Unsafe, expired, duplicate, or no-longer-matching pointers are omitted.

If a legacy/model call omits candidate IDs, search still works and the exact query cache still
applies, but no candidate/event pointer is persisted. This keeps protocol repair
backward-compatible.

### 5. Same-run alternate receipt pooling

The Haiku assignment desk will return a short run-local `event_group` for every candidate: exact
same-event candidates share a value; unrelated candidates use different values. This label is
untrusted organization, not evidence or canonical identity.

After parsing the complete batch, code applies one recall-only rule: when any member of an event
group is already effective `advance`—including operator, guide, Node, official, or unresolved
continuity protection—other members Haiku marked `background` are promoted as
`same_event_companion`. If every member is background, none is promoted. Grouping therefore can
only expose an additional possible receipt to Sonnet; it can never suppress work or establish that
two claims are true or identical.

Persist the bounded, escaped run-local `event_group`, the deterministic advanced anchor candidate
hash, and `same_event_companion` provenance on each `desk_preparations` row. These fields are
auditable organization only: they are explicitly noncanonical, expire with ordinary preparation
history, and are never copied into story aliases, search-pointer scopes, evidence, or publication
identity.

Companions enter the ordinary intake/reference board and the existing bounded prefetch order.
Sonnet sees the distinct URLs and decides whether to fetch, combine, separate, or dismiss them.
This directly addresses the observed failure where a working The Block report was hidden as a
near-duplicate while an older CoinDesk page remained blocked.

### 6. Direct-source-first guidance

Keep search discretionary. Tighten the operational wording—without adding a deterministic gate—so
the desk first inspects a promising supplied receipt, same-event companion, reusable evidence, or
prior search pointer when one appears adequate. Search fills a real gap; it is not a ritual every
candidate must pass.

When search is unavailable, Sonnet is told the precise operational category and may use supplied
public receipts, narrow and attribute the copy, defer a genuinely unresolved high-risk claim, or
drop the story. Quota exhaustion is not mislabeled as publisher blocking.

### 7. Desk and audit telemetry

Add a compact Search health line to the Desk showing:

- provider state and last account check;
- remaining searches / monthly allowance and renewal date when known;
- cache entries and last-24-hour cache hits, provider HTTP attempts, provider skips, and typed
  failures;
- the latest run's query-cache hits/misses and event-pointer reuse.

Extend sanitized newsroom counters and stored decision-run summaries with those values. Never
display secrets or raw provider payloads. Label allowance and usage deltas as shared-account
capacity rather than NBN spend: SerpAPI can serve its own identical-query cache without charging a
credit, and other services use the account. NBN measures its own provider HTTP attempts and locally
avoided requests, not falsely precise paid usage.

Add a bounded `fetch_failure_kinds` counter to sanitized newsroom telemetry so the Desk and audit
can distinguish provider search failures from downstream publisher outcomes such as HTTP 403/429,
JavaScript placeholders, timeout, unsupported content, or access challenge.

Prune expired cache/pointer rows during the existing bounded maintenance path; do not add another
scheduler.

## Configuration and rollback

Add bounded settings:

- `NBN_SEARCH_RESILIENCE_ENABLED` (default `false` for deploy-first rollout);
- `NBN_SEARCH_ACCOUNT_TTL_SECONDS=300`;
- `NBN_SEARCH_CACHE_TTL_SECONDS=3600`;
- `NBN_SEARCH_POINTER_TTL_SECONDS=21600`;
- `NBN_SEARCH_PROVIDER_COOLDOWN_SECONDS=300`;
- `NBN_DESK_CLUSTER_COMPANIONS_ENABLED=false`.

Deploy with both features off, verify schema/health, then enable them independently in production.
Rollback is an environment-variable change; additive tables may remain safely unused.

## Tests

Focused tests must prove:

1. account status exposes only the allowlisted fields and never logs/returns the API key;
2. quota exhaustion opens durable state, suppresses provider HTTP calls across fresh
   sessions/restarts,
   but valid cached results still work;
3. a later free account check showing capacity clears the circuit immediately;
4. failed account checks are separately throttled across restarts and multiple search calls,
   preserve the last-good snapshot, and fail open to provider search when no explicit circuit
   exists;
5. known-zero state permits exactly one persisted half-open provider probe when renewal/fallback
   time has arrived and status refresh is unavailable; an atomic tokenized lease excludes
   concurrent claims, an abandoned claim is recoverable only after its bounded expiry, success
   recovers, another quota response reschedules, and restarts do not multiply probes;
6. throughput 429 respects numerically bounded `Retry-After`, while transport/provider failure
   cooldowns are short and typed;
7. normalized exact queries hit the cache only when engine, locale, result limit, and pagination
   also match; materially different requests miss; expired/corrupt/oversized entries fail safely;
   and unsafe URLs never re-enter the desk;
8. successful candidate-scoped searches create bounded reusable pointers and later desks expose
   them as uninspected references rather than evidence;
9. candidate IDs are capped at eight; invalid/unknown IDs cannot cross-associate pointers; and
   durable reuse never derives from Haiku groups, themes, or model-authored slugs;
10. same-event background members are promoted only when their group contains an existing advanced
   member; all-background groups remain background; malformed Haiku output fails open;
11. promoted companions persist their run-local group, deterministic anchor, and promotion reason
    without creating canonical identity or evidence;
12. promoted companions remain available for prefetch/fetch without expanding the existing
    candidate, fetch, character, or model-call bounds;
13. report rendering and sanitized decision summaries expose shared-account capacity, local
    request avoidance, provider HTTP attempts, and downstream fetch-failure kinds without secrets;
14. search-off rollback preserves the current behavior;
15. the full Python test suite passes.

## Independent review gates

The independent lead coder must explicitly approve:

1. that cached results and event pointers cannot become evidence without an ordinary safe fetch;
2. that provider state recovers from renewal/upgrades and cannot leave search permanently dark;
3. that quota checks and caches are bounded, restart-safe, and do not leak credentials;
4. that companion grouping is recall-only and cannot silently suppress or canonically merge
   stories;
5. that the design actually reduces provider requests and shared-account credit pressure rather
   than just hiding activity in another layer;
6. that telemetry accurately distinguishes locally avoided requests and provider HTTP attempts
   from shared-account credit usage, and search discovery failures from downstream publisher fetch
   blocks;
7. that the sprint is proportionate and should not include a second vendor or browser-automation
   system yet.

Implementation does not begin until the lead returns `APPROVED`. Every
`CHANGES_REQUESTED` finding is incorporated and resubmitted until consensus.

## Deployment and smoke test

1. Capture production health, replica count, current search account snapshot, v2/prep/research
   settings, and autopublish state. Do not change autopublish.
2. Create and integrity-check an online SQLite backup.
3. Deploy with both new feature flags off. Confirm startup migrations, `/health`, `/status`, Desk
   rendering, and the production image's focused/full test results.
4. Enable search resilience. Run a harmless, code-level production search smoke against a real
   current Bitcoin query without invoking publication. Verify one actual result, persisted safe
   account state, no secret in logs/report, and a second identical query served from local cache
   without a second provider HTTP attempt.
5. Enable companion pooling. Verify with a model-independent fixture inside the production image;
   then inspect the next natural assignment batch for auditable grouping/promotion. Do not invent
   or publish a story to force a natural case.
6. Confirm an existing supplied receipt can still be fetched when search is disabled/degraded and
   that a simulated quota state recovers when account capacity returns.
7. Confirm database integrity, bounded cache/pointer rows, search-health telemetry, no unexpected
   worker errors, no duplicate Typefully delivery, and unchanged autopublish state.
8. Confirm the rolling production audit remains active and add search health, cache efficiency,
   publisher-fetch blocking, and hidden-alternate-receipt failures to its observations.
