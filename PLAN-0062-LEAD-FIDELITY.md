# Plan 0062 — better leads, without another ingestion platform

Status: independently reviewed, implemented and deployed; production smoke passed, 2026-09-06.

## Objective and evidence

Improve lead quality and breaking-news speed by delivering the story our guide accounts
actually posted, and preventing avoidable collector gaps. The Sept 6 sourcing review found
all 74 sampled recent guide posts in intake (median capture 1.87 minutes), but 78 of 430
sampled posts had longer note text, 58 referenced other posts, and 347 included media.
The current collector truncates text and omits that context. Selection/conversion, not
simply polling faster, is the first problem to address.

Owner corrections: routine wallet/payment/software releases are not standalone news.
A release can be a development in a bigger ongoing story. Perception's separate REST
quota is exhausted; Perception work is explicitly deferred, with no configuration changes.

## Phase 1 — lossless-enough collection and durable progress

- Request long text, referenced posts/authors, and media metadata in the existing X search
  call. Prefer long text over ordinary text; accept current/legacy note field names on read.
  Keep the original post, one level of referenced posts, source links, media type/preview/alt
  text, publication time, capture time, and age-stamped public metrics. Missing references
  remain explicit IDs/URLs, not fabricated text. No recursive crawls, media downloads, or
  automatic reuse of someone else's image/video.
- Store bounded X material in one additive items column, separate from the 8 KiB Node/guide
  contract. Cap normalized JSON at 12 KiB (below the 16 KiB retrieval call), expose truncation explicitly, and retain it with
  its item. Summary remains a preview. Upserts can enrich material without reopening skipped
  items, changing first-seen, or replacing first-origin attribution.
  Enrich only the same X post ID. When distinct posts canonicalize to one outbound page,
  retain the first attached material, never mix a later author's text with the first headline.
  Carry the new column through pending/restarted inventory; research retries reload material
  by durable candidate ID rather than duplicating it in their already-bounded frozen JSON.
- Page recent search, at most three 25-result pages per query per poll. Persist unfinished
  pagination (original lower bound, first-page high-water ID, next token). Resume on the
  next poll. Advance the regular since_id only once that window is drained.
- Collection returns a list-compatible batch with pending acknowledgments; the worker
  acknowledges only after upsert has committed. A crash before acknowledgment replays safely.
  Failed pages retain the last successfully stored continuation. Non-rate-limit query errors
  do not suppress other queries. A shared 429 stops additional requests without advancing
  unconsumed work. No new collector process or changed polling interval.

## Phase 2 — a clean desk, not a giant payload

- Give preparation a bounded, richer text preview plus quoted-original/source/media pointers.
  Put fuller material behind the newsroom's existing read_desk_context surface, with stable
  per-candidate IDs that survive packet compaction. Show compact useful context immediately;
  retain the 64 KiB initial-packet and 16 KiB per-call budget. Owner approved raising on-demand
  retrieval from two calls / 24 KiB total to four calls / 48 KiB total during implementation.
  This is optional headroom, not an instruction to consume it; audit use and capacity hits.
- Promote original/quoted outbound URLs into existing uninspected reference pointers and
  prefetch candidates; do not manufacture new evidence IDs from discovery material.
- Explain capture age: near-zero engagement shortly after publication is not a dismissal
  reason. Metrics are attention context, never authority. Quoted sources are a research path,
  not an independent corroboration vote. Media metadata is not visual inspection.
- Align mailroom, preparation, orientation, and batch editor guidance: useful Bitcoin-native
  demonstrations, real adoption/access, and substantive culture can qualify without moving
  markets or changing consensus. Require a concrete, interesting development or finding,
  not promotion, generic celebrations, or a quota. Explicitly exclude standalone software
  releases; retain larger-story release coverage, no TA/predictions, and the existing three-
  company/high-bar treasury policy. Preserve the agreed concise writing guidance.
- Preserve owner skip overrides and all publication/duplicate/evidence rails. No model change,
  mandatory research call, or new publication gate.

## Phase 3 — small upstream source pilot

Add only verified working official RSS feeds for Bitcoin Core announcements, Bitcoin Optech,
and BTCPay Server's blog (at most three). These are direct source leads for protocol, real use,
and access stories, not a releases beat. Route through the existing Haiku mailroom. First-party
authority is scoped to their own work; no blanket trust or bypass. Mark the pilot for audit:
novel useful leads, duplicates of guides, background noise, earliest-source timing and cost.
On each pilot feed's first successful snapshot only, persist entries older than the existing
24-hour intake window as skipped with a clear bootstrap/background reason, before Haiku.
Missing/invalid dates continue normally. Acknowledge feed initialization only after item
commit. Subsequent entries follow normal editorial routing; this is not a new ongoing age gate.

## Intentionally deferred

Perception; X streaming; a second worker/concurrent editorial architecture; a new breaking
scheduler (priority wakes already exist); ongoing storyline watch jobs; direct-data detectors;
autonomous open-ended scouts; native image/video understanding. This build retains media and
original-source paths so their value can be assessed before paying for another research lane.

## Verification and release

Offline fixtures: long text beyond 600 characters; missing/available quote expansions; media
metadata and long-note URLs; Unicode byte bounds; missing versus zero engagement and timestamp
age; material persistence and enrichment without disposition/first-seen changes; pagination
over three pages; restart/partial failure/429; no cursor before durable insertion; query isolation;
initial packet compaction/retrieval and owner-override preservation; source-feed fixtures and
prompt consistency. Existing full Python 3.12 suite must pass, including publication invariants.
Also test canonical outbound collisions, retry reload, first-poll bootstrap/restart, missing
dates, and a runtime retrieval limit smaller than a material row (return an explicit bounded
preview/truncation, never an empty successful read that hides the lead).

Independent lead reviews plan before implementation and focused final diff afterward. Resolve
concrete blockers, not speculative hardening. Stage only this sprint's files; preserve existing
evaluator/tuning changes. Test a clean archive, online-backup SQLite, deploy that archive to the
existing one-replica Railway service, verify health/config and a natural intake/desk cycle.
No forced production models, drafts, or publisher actions for testing. Keep autopost OFF.
Update current system/flow/prompt/maintenance docs and record release evidence here.

Rolling Codex audit is paused while building. Restore its previous scope after successful smoke
or safe rollback, adding material/cursor/pilot/conversion checks. Notify only useful changes.

## Sources

- Sourcing evidence: LEAD-SOURCING-REVIEW-2026-09-06.md and its dated local research sample.
- X pagination: https://docs.x.com/x-api/posts/search/integrate/paginate
- X fields: https://docs.x.com/x-api/posts/search-recent-posts (live sample used note_tweet;
  current docs describe note_post; verify field compatibility before release).
- Feed discovery: https://bitcoincore.org/en/rss/, https://bitcoinops.org/,
  https://blog.btcpayserver.org/.

## Independent review and pre-release evidence

Independent lead approved the plan and focused implementation. Review improved retrieval sizing,
first-snapshot feed bootstrap, same-post quote enrichment and durable inventory/retry propagation.
The root owns implementation and release. No Perception, publisher or model changes were bundled.

All 465 working-tree tests pass, including 16 new sourcing/storage/packet/prompt regressions and
the real worker's commit-before-ack boundary. Two evaluator tests belong to preexisting uncommitted
work and will be excluded from the clean release. Reviewer separately passed 60 targeted tests.
Pilot feeds all returned HTTP 200 and parsed valid entries. A read-only production X query with
the new fields/expansions returned HTTP 200, no field errors and zero new posts; it did not move
any collector cursor. The live API accepts note_tweet; parsing also accepts note_post. Production
retrieval environment overrides are unset, so the owner-approved defaults apply on deployment.

Deployment, clean-archive test, backup and natural-cycle smoke evidence follows below.

## Release evidence

- Runtime commit `f298b2c`, pushed to origin/main. Clean archive:
  `/tmp/nbn-0062-release.tn9guy`; **463 released tests passed**. Unrelated evaluator/tuning
  changes remain untouched and excluded.
- Online SQLite backup `/data/backups/nbn-pre-source-policy-20260906T202846Z.db` passed the
  backup script's full integrity check. Rollback runtime is the prior `f5b14a0`; the additive
  item column is backward-compatible. Never rewind production data to roll back code.
- Railway deployment `db6c7860-65d0-4cdc-85ee-a7dab205f142`: **SUCCESS**, existing service,
  one replica and `/data` volume. No credential, Perception or publication-mode changes.
- Public and internal health returned 200; natural worker cycles completed without error.
  All four authenticated Desk API views returned 200/version 1; missing authorization returned
  403. Runtime confirmed the new prompt, additive column, retrieval caps **4 / 16 KiB / 48 KiB**,
  **64 KiB initial**, autopost OFF and the daily receipt audit still disabled.
- Three pilot feeds returned valid parsed results and initialized after durable insertion.
  Seventy older archive entries were recorded as explicit bootstrap skips before Haiku.
  Six query cursors were committed, no unfinished windows at that check; two naturally
  collected X items already carried the new material.
- A separate bounded read-only lookup of one known guide quote returned 200, with the original
  `@Rob1Ham` post available (267 characters), preserving authorship and text in a 2,114-byte
  material card. No ingestion cursor or item was mutated by that contract check.
- Offline normalization of the existing 430-post sample preserved all post text without
  truncation: 85 note fields (78 longer than ordinary text), 347 media-bearing posts, and 58
  reference chains. Median material 981 bytes, maximum 2,399. That older sample lacked expanded
  quote bodies; the live lookup above verifies the newly requested expansions separately.
- Rolling audit `audit-nbn-production` restored ACTIVE on its existing 15-minute schedule,
  preserving autonomy/notification boundaries and adding lead fidelity, conversion, pagination,
  retrieval-budget and pilot-quality checks. No forced production model calls or Typefully
  mutations were used for testing.

The first natural run, `cycle:1788726993:93716e48`, completed at 20:37:25 UTC without error.
Its actual saved writer handoff contained seven candidates, three new X material previews and
three full-context retrieval IDs, with no observation truncation. Initial packet: 63,213 bytes,
below 64 KiB. Two successful writer calls, one search, three fetches; no optional context reads
or capacity hits. It returned seven decisions and zero stories, so the editor/delivery path
was not exercised by this natural run (those paths remain covered by the offline suite).
Successful intake/handoff is not represented as proof the new guidance has improved output
quality yet; the restored audit measures that over subsequent real runs.
