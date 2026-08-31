# Handoff: Next Block News → Codex

*Written 2026-08-31 by Claude (Brady's session), for Codex taking over day-to-day work.
Everything here is current as of this morning. The deeper owner's manual is `SYSTEM.md`;
this file is your orientation and the rules you must not break.*

## What this is

**Next Block News** (@nextblocknews_) is an autonomous Bitcoin news wire on X, running as
a single Python worker on Railway (project `next-block-news`, id
`1e1f32d1-6153-4f71-80b3-9543050caa7e`, one service + volume at `/data`). It watches
sources continuously, and for stories that pass every gate it **publishes to X by itself**
via Typefully. It has been live and autonomously publishing since 2026-08-30.

⚠️ **This is a secret skunkworks between Brady and his agents. It is NOT Swan-affiliated.**
No Swan branding, no Swan mentions in posts (the briefing module strips them), no
integration with the Swan Marketing Node beyond read-only brief consumption. Don't
discuss it in Swan channels.

## The pipeline (read `nbn/main.py:cycle` top to bottom — it's the whole story)

```
poll sources → intake gates → triage (Sonnet 5) → verify/corroborate → draft (Sonnet 5)
→ deterministic lint (+1 retry) → Editor (Fable 5 @ low) → scheduled publish (Typefully)
```

- **Sources** (`nbn/sources.py`): 12 RSS feeds, SEC EDGAR full-text, Perception /feed,
  X recent-search (roster from a public X List, compiled hourly; detector accounts are
  tips, never sources). X reads are billed per post returned — `since_id` keying is the
  cost seam, don't break it, and never poll a list TIMELINE endpoint (no since_id).
- **Classes**: `primary` (official artifact) and `corroborated` auto-post;
  **`secondary` NEVER auto-posts** (code-enforced); `data` dormant; `briefing` stages DRAFT.
- **Corroboration**: 2+ distinct publishers on one story_key, or web-search verification
  (`nbn/verify.py`, adversarial prompt + deterministic domain checks the model can't override).
- **Editor** (`nbn/editor.py`): last-mile judgment before autonomous publish. Fails OPEN
  (an editor outage must not block news). Verdicts logged to `posts.editor_note`.
- **Publishing** (`nbn/publisher_typefully.py`): Typefully v2. `publish_at:"now"` REJECTS
  drafts containing URLs (X policy, draft-wide) — so "immediate" = scheduled +30s
  (`NBN_PUBLISH_DELAY_SECONDS`). Media: upload → presigned S3 PUT → poll ready →
  `media_ids` on the lead post. No delete API — deletions are manual by Brady.

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
   (Coinglass, Glassnode...), never the aggregator. A data story whose only receipt is a
   second-tier domain (`NBN_LOW_TIER_DOMAINS`) is held, and `per <aggregator>` fails lint.
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
  verdicts, held groups with reasons. If you change pipeline behavior, keep the Desk honest.
- **Test pattern for pipeline changes**: local rerun via `railway run` (draft+lint+editor,
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
