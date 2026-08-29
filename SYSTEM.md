# How Next Block News works — the owner's manual

*Written 2026-08-29, matching the deployed code. One always-on Python worker on Railway
watches the news, decides what's worth publishing, writes it in the wire voice, checks
itself against deterministic gates, and publishes through Typefully to @nextblocknews_.
Two products: breaking singles (anytime) and the Morning/Afternoon Block (scheduled).*

---

## The 30-second version

```
 every 120s ────────────────────────────────────────────────────────────────┐
 │                                                                          │
 │  WATCH            TRIAGE              DRAFT              GATE            │ PUBLISH
 │  10 RSS feeds     Sonnet 5 judges     Sonnet 5 writes    deterministic   │ Typefully
 │  (+Perception     each new item:      the post from      lint: scope,    │ IMMEDIATE
 │  when keyed,      draft / hold /      the FETCHED        hype, numbers,  │ (auto) or
 │  +X when keyed)   skip, story key,    article text —     mentions, no    │ DRAFT (your
 │                   class               never from memory  model URLs      │ tap)
 └──────────────────────────────────────────────────────────────────────────┘
 weekdays 14:40 & 21:15 UTC: fetch the Marketing Node's tuned brief → the Block thread
```

Everything that happens is also appended to a daily tape file (the audit trail) and a
SQLite database on the Railway volume.

---

## 1. Watching (sources)

**RSS, every cycle (120s):** Federal Reserve press, SEC press releases (the two *primary*
sources), Bitcoin Magazine, CoinDesk, The Block, Cointelegraph, Bloomberg Markets, CNBC,
WSJ Markets, Fox Business. A feed failing never kills the cycle; it's logged and skipped.

**Perception `/feed`** (1,000+ outlets): polled every 10 minutes, activates the moment
`NBN_PERCEPTION_API_KEY` is set. Must be the wire's own key, never the Node's.

**X recent-search** (regulator accounts + Bitcoin-ETF/custody breaking terms): built,
dormant until `NBN_X_BEARER_TOKEN` is set with the wire's own key.

Every item is deduplicated by URL hash — seen once, never re-processed.

## 2. Triage (the intake editor)

New items go to Sonnet 5 in a batch (max 25/cycle) with the charter and the recently
covered story keys. For each item it returns:

- **action** — `draft` (in scope, newsworthy), `skip` (out of scope, promo, altcoin,
  duplicate), `hold` (in scope but unverifiable right now)
- **story_key** — names the underlying STORY, so two outlets covering one event share a
  key. This drives corroboration and the never-post-twice guard.
- **class** — decides publish behavior (see §4)

Before triage, a deterministic freshness gate drops anything published more than
`NBN_MAX_AGE_HOURS` ago (currently 6) — a wire never posts old news as NEW.

## 3. Drafting (the writer)

For each `draft` item the worker fetches the article's full text and hands it to Sonnet 5
with the charter (`prompts/wire_voice.md`). Hard rules baked into the seam:

- **Every number must appear verbatim in the fetched source text.** No source text (fetch
  blocked, paywall) → no post; the item is held as "thin source."
- **The model never writes URLs.** The system appends the verified receipt link afterward.
  This is the anti-fabrication seam: a hallucinated link is structurally impossible.
- Mentions only from `handles.json` (each handle manually verified against the live
  profile), max 2, tagging data sources at first mention.
- Shape: narrative by default in short scannable paragraphs; `•` bullets (max 4) only for
  genuinely enumerable stories; mixed allowed — bullets carry lists, prose carries the
  story, never bullet a causal argument.

## 4. Classes — what publishes itself vs. waits for you

| Class | Meaning | On autopost (now) |
|---|---|---|
| `primary` | The item IS the official source: Fed/SEC/Treasury release, filing, official account | **Publishes immediately, no human** |
| `corroborated` | Secondary story whose story_key has **2+ distinct publishers** (your two-source rule, mechanized) | **Publishes immediately** |
| `secondary` | Single-outlet press report | **Never auto-posts** (hardened in code, not just config) → Typefully DRAFT for your tap |
| `data` | Pure market/chain data point | In the allowed set but deferred until the wire computes its own numbers |
| `briefing` | The Block threads | DRAFT for your tap until you add `briefing` to `NBN_AUTOPOST_CLASSES` |

A `secondary` story that gets held for "needs second source" publishes automatically the
moment a second independent outlet covers it (the new item arrives, corroboration hits 2,
it drafts and goes). And no story_key ever posts twice.

## 5. The gates (deterministic, veto everything)

`nbn/lint.py` runs after the model, before the publisher. Any violation = the draft is
held (after **one retry** where the violations are fed back to the model for a rewrite).

- Bitcoin-only scope: no non-Bitcoin token named or priced, ever; "crypto" allowed only
  as a business adjective ("a crypto custody provider") or inside a quoted official title
- No hype (BREAKING, 🚨, 🚀, "surges", "erupts"...), no forecasts ("will hit $", "price
  target"), no buy-timing ("don't miss", "buy the dip")
- Number integrity: every figure in the post must exist in the fetched source text
- Mention whitelist, max 2; no all-caps runs; no URLs in model output; length cap
- Block-specific: any post containing "swan" is rejected (brand separation), and every
  receipt must be a URL that literally appears in the Node's brief

These gates are the wire's identity (accuracy, neutrality, receipts) — NOT Swan
compliance. The wire is not Swan-affiliated content.

## 6. The Block (scheduled briefing threads)

Weekdays at **14:40 UTC** (Morning Block, after the Node's EIC brief lands at 14:00) and
**21:15 UTC** (Afternoon Block, after the Node's 20:30 intel run). Once per window,
DB-guarded. The worker:

1. Fetches your tuned brief from the Marketing Node's read API (`/api/daily-intel/latest`)
2. Adds the wire's own unique catches since the previous Block (`wire_items`)
3. Rewrites into a 5-9 post thread: post 1 is the link-free index
   (`Morning Block - <date>`, "Top stories:" bullets, "More inside ➡️" — the wire's one
   emoji, only there); each story post from 2 on carries its own receipt link so the card
   renders
4. Gates: Swan-strip, receipts-from-brief-only, the full lint
5. Stages as a Typefully DRAFT (class `briefing`)

**Known tradeoff:** the Block trusts the brief. If the brief carries a wrong number, the
Block inherits it (the "close to 60%" odds figure is the live example). Wire singles, by
contrast, verify against fetched source text. A cross-check pass is the specced upgrade.

## 7. Publishing (the rail)

Typefully API v2, chosen over Nuelink (API can't thread, no read-back) and the direct
X API (pay-per-use charges $0.20/post containing a link; long-post 403 history). Singles
publish as one post with the link appended; Blocks as native threads. `IMMEDIATE` posts
use `publish_at:"now"` and the worker polls until Typefully confirms `finished`.
Failures fall back to tape + log — never silent. There is no delete anywhere in the
chain by design: **corrections are posted, never scrubbed.**

X Premium is required on the handle (long posts) — active.

## 8. Where everything lives

| Thing | Where |
|---|---|
| Code | private repo `brady-swan/next-block-news` (local: `~/claude/next-block-news/`) |
| Deployment | Railway project `next-block-news` (`1e1f32d1…`), single service + volume at `/data` |
| The prompts | `prompts/wire_voice.md` (charter) + constants in `nbn/brain.py`, `nbn/briefing.py`; compiled reference: `PROMPTS.md` |
| Verified handles | `handles.json` — never add one without checking the live profile |
| State | SQLite `/data/nbn.db` (items, stories, post log) |
| Audit trail | `/data/tapes/tape-YYYY-MM-DD.md` — every produced post, timestamped, with mode |
| Health | `GET /health` on the service (cycle stats, DB counts, autopost flag) — generate a public domain in Railway settings if you want it in a browser; otherwise `railway logs` |

## 9. The knobs (Railway service variables)

| Variable | Current | What it does |
|---|---|---|
| `NBN_AUTOPOST_ENABLED` | `true` | **Master kill switch.** `false` = everything stages as DRAFT |
| `NBN_AUTOPOST_CLASSES` | `primary,corroborated` | Which classes may publish unattended (`secondary` is ignored even if listed) |
| `NBN_MAX_AGE_HOURS` | `6` | Freshness gate — older items skipped at intake |
| `NBN_POLL_SECONDS` | `120` | Sweep cadence |
| `NBN_MODEL` | `claude-sonnet-5` | Writer + triage model (`NBN_TRIAGE_MODEL` can split them) |
| `NBN_NODE_READ_TOKEN` | set | Read access to the Marketing Node's brief (Blocks) |
| `TYPEFULLY_API_KEY` / `_SOCIAL_SET_ID` | set / `329191` | The posting rail |
| `NBN_PERCEPTION_API_KEY` | empty | Activates the Perception source when set |
| `NBN_X_BEARER_TOKEN` | empty | Activates the X poller when set |
| `NBN_BRIEFING_UTC` | default `14:40,Morning;21:15,Afternoon` | Block schedule |
| `NBN_MAX_LLM_CALLS_PER_HOUR` | default `60` | Runaway-cost guard |

Changing a variable in the Railway UI restarts the worker with it. Code changes deploy
via `railway up` from the repo directory (or push to GitHub and redeploy).

## 10. Operating it

- **Pause everything:** `NBN_AUTOPOST_ENABLED=false` (posts keep staging as drafts), or
  pause the service entirely in Railway to stop even drafting.
- **See what it's doing:** `railway logs` — every cycle, every hold with its reason,
  every publish. Or read the daily tape for the content view.
- **Why didn't X post?** Check the tape first (was it produced?), then the DB reasons:
  items are marked `skipped` (out of scope/stale/duplicate), `held` (thin source, needs
  second source, lint after retry), `drafted` (waiting for your tap), `posted`.
- **A bad post went out:** post the correction as a reply/quote from the handle. Never
  delete — the accuracy policy is the moat, and visible corrections are part of it.
- **Widen autonomy:** add `briefing` (and later `data`) to `NBN_AUTOPOST_CLASSES` when
  the drafts have earned it.
- **Tune the voice:** edit `prompts/wire_voice.md`, `railway up`. The prompt file is the
  spec; `PROMPTS.md` is the readable compilation.

## 11. Costs (order of magnitude)

Railway ~$5-10/mo. LLM: Sonnet 5 at ~$2/$10 per Mtok; a quiet day is a handful of triage
calls (~$0.10-0.50), a busy day with many drafts maybe $1-3; the hourly call cap bounds
the blowup case. Typefully ~$10/mo tier. X Premium on the handle. Total: roughly
$30-60/mo run rate.

## 12. Failure modes and what they look like

| Failure | What happens | Where you see it |
|---|---|---|
| Feed down / article fetch blocked | Item held "thin source"; other feeds unaffected | logs, DB note |
| Typefully publish fails | Post falls back to tape, item stays `drafted` | logs (`typefully publish failed`) |
| Node brief unavailable at Block time | Block skipped, "no brief available" warning | logs |
| Model writes something out-of-charter | Lint holds it (after one retry) | logs (`lint held`), DB note |
| Press story misclassed `primary` | **The one gate-proof failure** — it would auto-post | audit the class labels on early posts |
| Worker crash | Railway restarts it; unprocessed items recover from DB (`pending` pickup) | Railway deploy panel |

The design principle behind all of it: **the model proposes, deterministic code vetoes,
and every publish decision is reconstructible from the tape + DB.**
