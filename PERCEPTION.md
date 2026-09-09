# Perception reporting integration

Sprint0071 integration + Sprint0072 adoption · September9,2026.
Current code/prompt `editorial-core-v2.35-writer-continuity`.
Release status and production proof belong in SPRINT-0073-FINDINGS.md.

Sprint0073 keeps these tools, quotas and transport/cache contracts unchanged. Existing survey
slots now rotate audience-aligned reporting questions around custody/privacy, mining/energy,
payments/capital controls and central-bank policy/financial surveillance. Writer letters and
scheduled follow-ups can point future sessions toward useful Perception searches; using one
is not compulsory. NBN's hybrid memory finds retained dated reporting, not fresh vendor data.

## What the Writer gets

- `perception_coverage`: bounded date/keyword or company-entity search, optional outlet.
- `perception_regulatory`: bounded query, agency and jurisdiction search.
- `perception_article`: read an already-retained article or retrieve it using its original URL.
  `refresh` bypasses retained/query reuse. Reading unchanged material never renews its evidence date.

Search returns original-source pointers, not proof. Article reads return exact receipt IDs through
the normal Writer→Editor→source-reply path. `provider_captured_text` means text supplied by
Perception: possibly an excerpt/summary, neither a native-search paraphrase nor NBN's direct page
capture. Original source identity, publication date/precision, byline, capture time, limitations,
fingerprints and truncation survive storage/restoration. Perception is not a second independent
publisher. Web/X/direct fetching remain available; no compulsory extra research sequence.

Candidate cards point to available retained text. Full text stays out of the initial packet until
read. Existing memory catalogs/notebooks/search remain the only reporting memory system. Current
editor/output states stay in their existing live projections, not duplicated in source records.

The availability hint survives dense-packet reconstruction: original URL, artifact ID, publication
and capture dates, length and completeness remain on each applicable candidate. It means available,
not already inspected. Optional excerpt/metadata repetition shrinks before the notebook map.
The stable catalog page keeps honest continuation offsets; separate exact current/prep notebook
matches can surface old relevant work beyond that first page. Matching accepted-output snippets
and coverage context IDs open the full local accepted-copy snapshot, with draft/published states
and separate creation/sync/confirmation clocks. Later manual Typefully edits may differ. Accepted
copy, Writer proposals and source evidence are not interchangeable.

The four local retrieval calls, eight rows/call,16KiB/response and48KiB total are unchanged. Full
UTF-8 response envelopes count toward the byte allowance, including conservative remaining-budget
metadata. Responses distinguish exact capacity-omitted IDs from already-read IDs; repeated-only
reads do not consume another call. Control-only errors contain no evidence and are not charged to
the evidence allowance. Large memory records retain explicit section IDs.

## Discovery and durability

REST `/feed` continues on a900-second cadence. One acknowledged page per poll alternates newest
coverage and progress through an overlapping frozen date window. The provider's mutable offset
ordering cannot guarantee lossless capture. Empty, missing pagination and truncation are distinct;
Desk reports partial coverage/backlog. A storage failure cannot acknowledge a lost page.

Up to8subject-survey slots per UTC day alternate self-custody, mining-pools, merchant-payments and
Bitcoin regulatory coverage. These are verified provider subject IDs/operations, not editorial
topic quotas. Each slot permits one attempt, persisted before request. Completed pending results
survive restart until durable intake acknowledgement; failures cannot spend all slots retrying
one beat. Source pointers go through normal preparation. Routine releases remain out of remit.

Unchanged article versions deduplicate by canonical URL, content fingerprint, original date and
byline. Their original capture/expiry stays fixed. Changed text creates another dated version.
Duplicate enrichment cannot change first-seen time, status, keys, comments, drafts or publication.
Body/metadata storage is bounded; article versions use existing30-day writer_artifacts retention.
Successful query caches live5minutes; legitimate empty results1minute. Errors are never cached
as empty. Requests/cooldowns are durable; historical request records retain30days. Cache keys
include contract, transport, operation and exact arguments. Source versions may be shared across
interfaces, while different searches never masquerade as equivalent cached results.
The recorded successful “No regulatory documents found” MCP response is a complete empty result
(`rows=[]`, `total=0`, `partial=false`), cached for60seconds without setting failure cooldown.

## Quotas and routing

The same Railway credential supports both HTTPS interfaces; no laptop/MCP desktop dependency.
Perception documents separate REST/MCP daily pools and a shared60/minute limit. NBN measures its
own attempts only. Node uses the account too; current account-wide remaining capacity is unknown.
Do not interpret a minute counter as the daily balance or add balances into a fungible total.

- Hard cap24new-work attempts/day across Writer and surveys, both transports combined.
- At most4REST new-work attempts/day; the existing broad intake is accounted separately.
- After20MCP new-work attempts, a plain single-keyword coverage query can prefer REST. This is
  not a hard stop for MCP-only work; article/entity/regulatory research can use remaining total
  allowance. A definite MCP daily-quota rejection can use the same equivalent route once.
- Only simple keyword/date semantics have an empirical parity check (same6Lummis URLs). No
  automatic substitution for entity, regulatory, article, operator/multiword or richer filters.
- Known authentication, quota and shared-minute cooldowns are honored; ambiguous failures are
  not blindly retried on another surface. Unknown capacity is not a no-overage guarantee.

Each request has a unique idempotency identity and a durable pre-request attempt record.
No prepaid wallet is purchased or configured; existing subscription/wallet settlement remains
Perception's. No new credentials, Node setting changes or vendor workflow activation.

## Resource boundaries and rollback

Existing six successful Writer responses,360-second lifecycle,24shared tool operations and
12native calls are unchanged. Perception tools count toward24operations, not the four local
memory lookups. Article reads also consume existing fetch-count/text bounds, including cache
reads. Network requests use a20-second budget/per-I/O timeout with elapsed-time checks between
chunks and after receipt. One in-flight I/O can overrun that budget; it is not a guaranteed hard
wall-clock ceiling. Final-submission reserve is accounted before calling; audit actual overruns.

System→Perception shows local attempts, limits, recent timing/errors/observed quota headers,
cache/article reuse, feed backlog and surveys. Run→Research retains requested arguments,
returns and failures through normal tool observations. Source services are not model-token cost.

Disable new tools/surveys with `NBN_PERCEPTION_TOOLS_ENABLED=false` (broad feed remains).
Disable all direct discovery with `NBN_PERCEPTION_DIRECT_ENABLED=false`; disable both flags for
complete integration rollback. Local source artifacts remain recoverable. Do not restore an old
database to roll back code. Autopost stays OFF.

## Measure usefulness

Compare first-seen/source timestamps, original-source follow-through, new useful candidates,
actual Writer adoption, editor evidence scope, cache reuse, latency and new-work capacity use.
More calls or source text is not success. A blocked provider must not become a publication gate.
Do not revive old stories, count provider summaries as independently corroborated, or treat
replayed fixtures as organic uptake. Current limitations include incomplete bodies, date-only
search output, unknown account balance and best-effort pagination.
Article image URLs are retained as metadata, but are not yet promoted into the existing visual
inspection candidate catalog. No claim that Perception images were inspected or attached.

`writer_desk_visibility` records compact assembly counts. Each `writer_call` records history bytes
and literal receipt IDs/bodies supplied by the last tool result; sectioned JSON remains unclassified.
These are transport/visibility facts, not proof of attention or usefulness. Compare `writer_result`
selections with actual `editor_input` and Editor decisions. Eagerly restored `fetches` alone do not
prove the Writer received those bodies. Overflow diagnostics record message sizes without increasing
the history allowance. Native X/direct links, Perception and memory are alternatives chosen for
the missing fact; there is no mandatory tool sequence or extra grading model.

References: [API reference](https://perception.to/api/reference),
[MCP reference](https://perception.to/docs/mcp). Live contract fixtures are under tests/fixtures.
