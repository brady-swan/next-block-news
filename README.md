# Next Block News

Always-on Bitcoin news wire worker. Watches primary sources and Bitcoin/finance feeds, classifies new items, drafts wire-format posts with Claude, runs deterministic gates, and stages them to Nuelink (DRAFT by default; class-based autopost when enabled).

**Charter:** `prompts/wire_voice.md`. Full project plan: `~/claude/bitcoin-news-handle-plan.md` (private).

## Architecture

```
sources.py   RSS pollers (Fed, SEC, CoinDesk, The Block, Bloomberg, ...) + optional X recent-search
store.py     SQLite state: seen items, story-level dedup, post log
brain.py     Claude: triage (draft/hold/skip + story key + class) then wire-format drafting
lint.py      Deterministic gates: banned patterns, mention whitelist, receipt-URL integrity
publisher.py Nuelink REST (DRAFT default / IMMEDIATE per class policy) + daily tape file
main.py      Poll loop + healthcheck server
```

**Affiliation note:** this project is NOT Swan-affiliated content. Swan's brand rulebook
and compliance posture do not bind the wire; do not port Swan rules in. The gates below
exist because they ARE the wire's product (accuracy, neutrality, receipts), not as
compliance inheritance.

Safety invariants (do not weaken):
- The model never supplies a URL. Receipts come from the feed item's own link.
- Mentions only from `handles.json` (every handle manually verified against the live profile).
- Numbers in a draft must appear in the fetched source text or the draft is held.
- `AUTOPOST_ENABLED=false` means nothing ever publishes; everything stages as Nuelink DRAFT and lands in the tape file.
- Corrections are posted, never deleted (the Nuelink API cannot delete anyway).

## Run locally

```
cp .env.example .env   # fill in keys
python3 scripts/run_once.py          # one full cycle, dry
python3 -m nbn.main                  # the loop
```

## Deploy (Railway)

```
railway login
railway init            # new project: next-block-news
railway volume add --mount-path /data
railway up
```

Then set the `.env.example` variables in the Railway service settings. Healthcheck path: `/health`.

## Autopost policy

`AUTOPOST_ENABLED=false` (default): everything is a Nuelink DRAFT + tape entry.
`AUTOPOST_ENABLED=true`: items classified `primary` (official-source: Fed/SEC/Treasury/filings) and `data` posts publish IMMEDIATE with the receipt as delayed first comment; `secondary` (press reports) always stay DRAFT for human review. Flipping this on is governed by the standing rule in `~/claude/CLAUDE.md` — requires Brady's written, handle-scoped authorization.
