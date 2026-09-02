# Handoff: Next Block News → Codex

*Written 2026-08-31 by Claude (Brady's session), then updated 2026-09-01 by Codex.
The deeper owner's manual is `SYSTEM.md`; this file is orientation and the rules you must
not break.*

**Operational update, 2026-09-02:** editorial core v2 supersedes the architecture described
later in this historical handoff. Read `SYSTEM.md` first. Production uses a persisted
15-minute, run-scoped Sonnet story desk plus one independent batch Sonnet editor. Intake,
health, Blocks, audits, and publication reconciliation still run every minute. The v2 path
has no automatic legacy fallback and does not inherit the old hard freshness, semantic-key,
exact-number, mandatory-prefix, or single-receipt-completeness vetoes. It keeps safe URL,
exact-delivery idempotency, Bitcoin scope, quote support, mention, investment-instruction,
correction, and kill-switch rails. Routine claims may ship from one credible inspected
Tier 1/2 report; elevated claims need a primary artifact or two credible independent reports.
The Desk exposes the live orientation brief and selected-day model token/cost telemetry.
`NBN_EDITORIAL_ENGINE=v1` is a short-lived manual rollback switch only.

**Live proof, 2026-09-02:** commits `3956883`, `e51ca8d`, and `7ae5f10` are deployed in
Railway deployment `58d2d08d-519d-4406-94ad-390501759b3a`. The first non-empty live v2
run reviewed 38 eligible candidates, used six Sonnet desk rounds plus one independent
Sonnet editor call, inspected 11 pages, and published a U.S. spot-Bitcoin-ETF monthly-flow
story through Typefully. Typefully confirmed the X publication. That intentionally
backlog-heavy validation run cost about $0.66; normal incremental runs should be measured
separately. The complete local suite passes 267 tests, `/health` reports no worker error,
and the Desk renders the live orientation brief and selected-day usage/cost telemetry.

## What this is

**Next Block News** (@nextblocknews_) is an autonomous Bitcoin news wire on X, running as
a single Python worker on Railway (project `next-block-news`, id
`1e1f32d1-6153-4f71-80b3-9543050caa7e`, one service + volume at `/data`). It watches
sources continuously, and for stories that pass every gate it **publishes to X by itself**
via Typefully. It has been live and autonomously publishing since 2026-08-30.

⚠️ **This is a secret skunkworks between Brady and his agents. It is NOT Swan-affiliated.**
No Swan branding, no Swan mentions in posts (the briefing module strips them). Integration
with the Swan Marketing Node is read-only through versioned brief and wire-pulse APIs; the
codebases and databases remain separate. Don't
discuss it in Swan channels.

**2026-09-01 integration update:** `wire-pulse-v2` may carry bounded Node theme activity.
NBN validates it as untrusted discovery context, computes a seven-day advisory coverage
snapshot from its own tagged output, supplies that context to the newsroom, and renders the exact
snapshot on the Desk. Themes are broad subjects, not event keys or evidence. They cannot
establish corroboration, force/suppress a post, lower gates, or create quotas. Missing
historical tags are explicitly unknown.

**Deployment:** Plan 0048's run-scoped newsroom is live at NBN commit `aff659c`; the final
Railway configuration deployment is `852cee28-5052-435e-8016-6f0edce7b584`. The staged
rollout caught and fixed Anthropic schema-size compatibility, model-visible candidate-ID
ambiguity, blocked-page retry behavior, and mandatory dossier-round accounting before live
cutover. The local suite passes 261 tests; the production image passes the 31 focused
newsroom/config tests. A natural shadow run accounted for two noise candidates; a natural
draft run replaced a The Block X tip with Farside primary data and withheld the already
covered ETF-flow event; the first non-empty live run completed normally. `/health` is clean,
the Desk renders newsroom diagnostics, and the external 15-minute audit remains active.

**Prior integration deployment:** Plan 0047 conversion recovery remains in the history.
Node commit `891d27a` produced production wire run `177450`, whose versioned pulse is still
consumed normally by NBN.

## The pipeline (read `nbn/main.py:cycle` and `nbn/newsroom.py`)

```
poll sources → intake gates → one run-scoped Sonnet newsroom
(survey → selective research → exact-event judgment → writing → atomic dossier)
→ deterministic gates/one post-only repair → Fable support+craft Editor → Typefully
```

- **Newsroom** (`nbn/newsroom.py`): one fresh Sonnet context owns every non-empty
  bounded run; it does not persist across runs. The model receives a clean editorial desk:
  one stable intake card per item, a separate uninspected-reference board, exact recent
  coverage/open-draft boards, a broad advisory theme board, and verified handle spellings.
  Raw Node envelopes and unknown metadata are removed. What arrived is a lead; only a
  code-issued `fetch_id` from an inspected page can become evidence.
- **Protocol**: forced complete survey → bounded safe fetch/SerpAPI tools → explicit
  research close → forced dossier covering every candidate exactly once. Unknown fetches,
  unsafe grouping, omissions, or malformed output reject the whole batch before
  materialization. Once materialization starts, legacy fallback is forbidden.

- **Sources** (`nbn/sources.py`): 12 RSS feeds, SEC EDGAR full-text, Perception /feed,
  X recent-search (roster from a public X List, compiled hourly; detector accounts are
  tips, never sources). X reads are billed per post returned — `since_id` keying is the
  cost seam, don't break it, and never poll a list TIMELINE endpoint (no since_id).
- **Classes**: `primary` (official artifact) and `corroborated` auto-post;
  **`secondary` NEVER auto-posts** (code-enforced); `data` dormant; `briefing` stages DRAFT.
- **Source ladder**: `config/source_tiers.toml` is the canonical P0–T4 registry;
  `nbn/source_policy.py` validates and classifies domains, aliases, and X handles.
- **Corroboration**: 2+ fresh, directly supporting, independent persisted evidence chains
  on one exact story_key. Same owners, syndication copies, and a shared primary artifact
  collapse. A detector plus the artifact it finds is one chain, not two.
- **Editor** (`nbn/editor.py`): independent Fable last-mile judgment. Newsroom output
  fails CLOSED unless Fable confirms every final assertion against the exact selected
  receipt; revisions are re-linted. The migration-only legacy Editor still fails open.
- **Publishing** (`nbn/publisher_typefully.py`): Typefully v2. `publish_at:"now"` REJECTS
  drafts containing URLs (X policy, draft-wide) — so "immediate" = scheduled +30s
  (`NBN_PUBLISH_DELAY_SECONDS`). Media: upload → presigned S3 PUT → poll ready →
  `media_ids` on the lead post. Only confirmed publication records as `IMMEDIATE`;
  ambiguous confirmation records as `UNCERTAIN` and never triggers a duplicate create.
  Typefully v2 now exposes an exact-draft DELETE endpoint; use it only for a precisely
  identified, owner-authorized cleanup. Ordinary feed-post deletion remains Brady's call.

## Editorial doctrine (each rule was bought with a live mistake — do not relax)

1. **Events, not write-ups.** A fresh article about a stale event is not news. The
   drafter extracts `event_date` from source text (range → END date; report → FIRST
   published; NEVER the article's own date — return null instead); `store.event_is_stale`
   holds violations. The event window tracks the article window (2.5h weekday
   7am–7pm ET / 6h nights+weekends): **NEW: = a same-day event.** Brady: "got to earn
   that NEW tag."
2. **Post grammar is closed**: `NEW:` / `UPDATE:` / `CORRECTION:` / the Block (unprefixed
   digest thread). UPDATE only for a story the wire already covered + a material new
   development. Everything else holds. (Data-posts lane is a future design, not a leak.)
3. **Never restate an X source.** The reader sees the original under our copy — extend
   with what it does NOT say (from fetched source text only) or skip.
4. **Tweets are pointers.** A primary account's tweet with one outbound link → THAT page
   is the story URL; draft from it, receipt links it. FRED graph links resolve to
   `fredgraph.csv` (data as source text) and attach `fredgraph.png` (official chart) to
   the post. FRED's WAF resets browser UAs from non-browser TLS — use `curl/8.7.1` UA.
5. **Price discipline.** Prices/flows reported flat. Never why-is-price-here framing,
   never metric-vs-price "tension" as the story, never questions in posts (lint bans `?`
   outside quotes).
6. **A number belongs to whoever measured it.** Attribute the original data provider
   (Coinglass, Glassnode...), never the aggregator. A different named provider triggers
   one targeted lookup and redraft; mismatch or unsupported copy holds. `per <aggregator>`
   also fails lint.
7. **Attribute ONCE per post.** Numbers verbatim from fetched source text (`numbers_used`
   is lint-checked). Mentions only from `handles.json`, max 2. Bitcoin-only scope —
   "crypto" allowed solely as a business adjective. No hype, no forecasts, no em dashes
   convention doesn't apply here (this is not Swan content), but the wire voice charter
   (`prompts/wire_voice.md`) governs everything the model writes.
8. **Corrections never auto-publish** (`CORRECTIONS.md`, 4-tier severity). The daily
   self-audit (09:00 UTC, `nbn/audit.py`) stages correction drafts for Brady.
9. **Deletion policy**: never-delete protects ERRORS (corrections doctrine); redundant or
   below-standard posts CAN be deleted for feed hygiene — Brady's call, he deletes manually.

## 🚫 Hard guardrails (non-negotiable)

- **Autopost authority comes from Brady's standing grant and is scoped to this worker's
  gate-passing posts only.** Never widen `NBN_AUTOPOST_CLASSES` (secondary is
  subtracted in code — keep it that way), never bypass a gate to force a publish, never
  post manually to any channel on Brady's behalf. Kill switch: `NBN_AUTOPOST_ENABLED=false`.
- **Never print secrets** into chat/logs (API keys, bearers). `.env` here holds Typefully
  + Node tokens; Railway holds the rest. ⚠️ Queued task: the shared X bearer needs
  regeneration (partial chat exposure 2026-08-30) — coordinate with Brady, it's shared
  with the Marketing Node.
- **Ask Brady before installing anything.** The worker is stdlib + httpx + anthropic;
  keep it that way.

## Ops cheat sheet

```bash
railway status                 # linked: project/service next-block-news, env production
railway up --detach            # deploy (this is THE deploy path; no auto-deploy on push)
railway logs                   # worker logs
railway ssh "python3 -c ..."   # run code ON the box (DB surgery on /data/nbn.db)
railway run python3 script.py  # run LOCAL code with the service's env vars (API keys)
PYTHONPATH=. NBN_DATA_DIR=/tmp/x railway run python3 test.py   # local pipeline tests
```

- Health: `https://next-block-news-production.up.railway.app/health` (500 if last cycle
  >10 min old); `/status` = JSON state. healthchecks.io dead-man's switch pings Brady on
  silence — if you take the worker down deliberately, warn him.
- **Desk Report** (Brady's browse/action surface): `/report?k=<token>` — token in
  `DESK-REPORT-URL.txt` (gitignored). Day nav `?d=YYYY-MM-DD`, dismiss links, editor
  verdicts, held groups with reasons, and source-resolution status/note/evidence counts on
  draft cards. If you change pipeline behavior, keep the Desk honest.
- **Test pattern for pipeline changes**: local full suite first, then staged newsroom
  rollout `off → shadow → draft → live`. Shadow compares without materializing; draft runs
  real gates but forces Typefully draft. A live prompt/tool change must survive a natural
  non-empty run and production logs before promotion. For a focused legacy rerun via
  `railway run` (draft+lint+editor,
  nothing publishes), then if Brady wants a live test, inject the item into `/data/nbn.db`
  via `railway ssh` (INSERT into items with status 'new') and let the worker's own cycle
  handle it. Regression-test lint with the actual offending copy (see git log for examples).
- **After any model/prompt change, watch one full LIVE cycle in the logs** — a local pass
  has masked a production 400 before (Sonnet 5 rejects the `fallbacks` param; the code
  gates it on opus-5/fable-5 prefixes — don't "simplify" that away).

## Where things are

| What | Where |
|---|---|
| Owner's manual (architecture, knobs, costs, failure modes) | `SYSTEM.md` |
| Voice/scope charter (in every model call) | `prompts/wire_voice.md` |
| Roadmap: week-2 queue + Idea Bank | `ROADMAP.md` |
| Corrections protocol | `CORRECTIONS.md` |
| Verified mention handles | `handles.json` |
| Prompt inventory | `PROMPTS.md` |
| Session-by-session history (this project's entries) | `~/claude/PROJECT-LOG.md`, tag `[Bitcoin Wire]` |

## Open queue (in priority order)

1. ⚠️ Regenerate the shared X bearer (Brady coordinates; update Node + wire envs).
2. Watch the first full weekday cycle — Morning Block fires 14:40 UTC weekdays
   (`nbn/briefing.py`, stages as DRAFT; number cross-check before it ever autoposts).
3. Grade-then-build (ROADMAP): editor casebook from Brady's gradings; no-verdict triage
   requeue; retry infra-failed verifications; data-posts lane design (own convention,
   never NEW).
4. Growth (Brady-led): nextblock.news domain, Nostr mirror, canonical handle acquisition.

## How Brady works this project

Feedback arrives as a link to a live post plus what's wrong with it. The response he
expects: diagnose from the DB/logs (not guesses), fix at EVERY layer the failure touched
(charter + prompt + deterministic lint/gate + editor), regression-test against the actual
offending copy, deploy, and log the lesson. Speed matters (it's a news wire) but a
factual error matters more — when in doubt, hold; held items are visible on the Desk
with reasons, and that's a feature.
