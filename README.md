# Next Block News

Autonomous Bitcoin news wire for X at `@nextblocknews_`. A single Python worker watches
primary sources, press feeds, Perception, and selected X accounts. A bounded Haiku assignment
desk prepares each due batch; a fresh run-scoped Sonnet desk researches and writes the useful
work; an independent Sonnet editor makes
the final editorial call; a small mechanical shell then delivers eligible work through
Typefully.

This project is independent and is not Swan-affiliated. The wire's editorial source of
truth is `prompts/wire_voice.md`; the complete owner's manual is `SYSTEM.md`.

## Pipeline

```text
poll -> RSS/EDGAR Haiku mailroom -> Haiku assignment desk -> Sonnet newsroom -> Sonnet editor -> Typefully
```

| Module | Responsibility |
|---|---|
| `nbn/sources.py` | RSS, SEC EDGAR, Perception, X recent-search, article text, FRED charts |
| `nbn/intake_triage.py` | Cheap RSS/EDGAR priority/candidate/background mailroom; all failures fail open |
| `nbn/desk_prep.py` | Run-scoped Haiku distillation/routing; protected work and every failure advance |
| `nbn/store.py` | SQLite deduplication, bounded cross-run workbenches, commit lifecycle, post log |
| `nbn/newsroom.py` | Run-scoped Sonnet newsroom, compact/retrievable desk context, bounded Haiku delegation, and atomic dossier |
| `nbn/brain.py` | Shared model budget plus legacy triage and single-post drafting fallback |
| `config/source_tiers.toml` | Canonical P0/T1/T2/T3/T4 source registry |
| `nbn/source_policy.py` | Validated source classification, normalization, and ranking |
| `nbn/search.py` | Bounded model-free SerpAPI discovery; returned links are untrusted pointers |
| `nbn/verify.py` | Typed source metadata and legacy claim-support machinery |
| `nbn/lint.py` | V2 mechanical delivery rails plus advisory warnings; legacy lint remains separate |
| `nbn/editor.py` | Independent support, source-sufficiency, novelty, framing, and craft judgment |
| `nbn/publisher.py` | Typefully-first output routing plus the daily tape |
| `nbn/briefing.py` | Fresh AM/PM EIC one-off discovery; legacy Block builder (disabled) |
| `nbn/audit.py` | Daily receipt and class audit; stages material correction drafts |
| `nbn/report.py` | Token-protected Desk report |
| `nbn/main.py` | Poll loop, orchestration, health/status HTTP server |

## Safety invariants

- `NBN_AUTOPOST_ENABLED=false` means nothing publishes automatically.
- `NBN_SOURCE_POLICY_MODE=observe` forces all delivery to DRAFT/TAPE regardless of the
  autopost setting; the code default is the safer `enforce` mode.
- The default v2 autopost classes are `primary`, `secondary`, and `corroborated`; the master
  kill switch, editor verdict, operator actions, identity conflicts, and source-policy mode
  can still force a Typefully draft.
- The model may select only a code-issued inspected `fetch_id`; the system attaches its URL.
- Mentions are limited to the manually verified entries in `handles.json`.
- Corrections are always staged for human review and never autopublish.
- Every regular pipeline post is appended to a daily tape and recorded in SQLite.
- Unsafe/empty fetches, malformed dossier identity, exact duplicate delivery, embedded URLs,
  length, unsupported verbatim quotes, invalid mentions, and investment instructions are hard.
- Source tier, corroboration sufficiency, semantic identity, freshness, numerical materiality,
  Bitcoin relevance, novelty, and importance are explicit model/editor judgments.
- Conflicting canonical families never auto-merge; they use an isolated review key and can
  only produce a human Typefully draft.

## Source ladder

Source tier measures receipt quality; it does not by itself decide publication. P0 is an
official artifact, Tier 1 is premier reporting, Tier 2 is reliable specialist reporting or
original research, Tier 3 is discovery-only, and Tier 4 is a wrapper/syndicator that never
counts as independent corroboration. Any safely fetched public page with usable text is
inspectable in v2, but every receipt is labeled by capability: known reporting/research,
known first-party statement, unknown-domain material, social statement, guide/discovery,
aggregator/wrapper, or syndication. The editor sees those labels and every inspected body.
Search snippets remain pointers, never evidence.

## Output modes

Typefully is the deployed publishing rail. Autonomous posts are scheduled shortly ahead
instead of using `publish_at: "now"`, because Typefully rejects immediate drafts that
contain URLs. Posts that are not eligible for autonomy become Typefully drafts. With no
publishing credentials, output is tape-only.

Publishing outcomes are explicit: `IMMEDIATE` means Typefully confirmed publication;
`DRAFT` means a human draft exists; `UNCERTAIN` means creation may have succeeded but
confirmation was inconclusive; `FAILED` is a definite backend failure; and `TAPE` means
no publishing backend was configured. An uncertain result is never retried automatically,
because retrying a possibly accepted create could duplicate a live post.

Nuelink remains as a legacy fallback for single posts, but it is not the preferred rail
and cannot publish threads.

## Run locally

```bash
cp .env.example .env
python3.12 scripts/run_once.py
python3.12 -m nbn.main
python3.12 -m unittest discover -s tests -v
```

Configuration is read from environment variables; the code does not automatically load
`.env`. Python 3.12 or newer is required. Defaults keep autopost disabled. Be careful when
using `railway run`, which injects the production service environment.

The test package removes inherited credentials, forces autopost off, uses temporary data
paths, and blocks real socket connections. HTTP, model, and publisher boundaries must be
mocked in tests.

## Deploy

The repository is linked to the Railway project and service `next-block-news` in the
`production` environment. Deploy conservatively without changing the owner's autopost state:

```bash
# 1. Confirm production, one replica, and the /data volume in serviceManifest.
railway status --json

# 2. Confirm the publication kill switch without listing any secrets.
railway ssh -- printenv NBN_AUTOPOST_ENABLED

# 3. Before new code/migrations exist remotely, make an online SQLite backup.
railway ssh -- "python -c 'import datetime,os,sqlite3; p=os.environ.get(\"NBN_DB_PATH\",\"/data/nbn.db\"); d=\"/data/backups\"; os.makedirs(d,exist_ok=True); q=f\"{d}/nbn-pre-deploy-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}.db\"; a=sqlite3.connect(p); b=sqlite3.connect(q); a.backup(b); print(q,b.execute(\"PRAGMA integrity_check\").fetchone()[0]); b.close(); a.close()'"

# 4. Upload. Do not modify NBN_AUTOPOST_ENABLED as part of a code deployment.
railway up --detach

# 5. Do not run scripts/run_once.py. Watch one natural worker cycle, logs, and /health.
railway logs --since 10m
curl -fsS https://next-block-news-production.up.railway.app/health
```

Stop or roll back on a validation, migration, integrity, or delivery-lifecycle error, or any
`IMMEDIATE`/`UNCERTAIN` result while `NBN_AUTOPOST_ENABLED=false`. The schema migration is additive;
restore the timestamped backup only for demonstrated database corruption, not as a routine
code rollback. Once this release is installed, `python scripts/backup_db.py` is the shorter
online-backup command for later maintenance.

The worker uses a short expiring SQLite lease, renewed by a background heartbeat, across
news, scheduled discovery, and audit work. Overlapping deploy processes or an accidental `run_once`
invocation cannot execute external work concurrently, while an orphaned deploy lease
expires within two minutes. Fresh persisted resolutions are reused across worker restarts.

The worker exposes `/health` and `/status`; both return runtime and database state, and
health becomes HTTP 500 when the last completed cycle is more than ten minutes old. The
Desk is available at `/report?k=<token>` when `NBN_REPORT_TOKEN` is configured. The worker
reconciles recent Typefully publication receipts every five minutes, so drafts published
manually are counted by their confirmed X publication time and leave the action queue.
For held items, the Desk can queue a guarded **Stage draft** retry (freshness,
corroboration, style, and Editor holds only) or record **Dismiss**. Operator retries run
the complete source/Writer/lint/Editor stack with a fresh web source search, override only the displayed gate, and are
always delivered as Typefully drafts—not autonomous posts.
The Desk exposes both RSS-mailroom and assignment-desk Background decisions; **Send to desk**
atomically restores one item to the Sonnet queue and advances the next desk deadline. It also
shows per-seat model spend, the daily cost target, initial packet size, Sonnet attempts, prepared
receipts, and delegated Haiku work.

See `HANDOFF-CODEX.md`, `SYSTEM.md`, `ROADMAP.md`, and `CORRECTIONS.md` before changing
publishing behavior.
