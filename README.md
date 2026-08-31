# Next Block News

Autonomous Bitcoin news wire for X at `@nextblocknews_`. A single Python worker watches
primary sources, press feeds, Perception, and selected X accounts; classifies new items;
drafts wire-format posts with Claude; applies deterministic and editorial gates; and
publishes eligible stories through Typefully.

This project is independent and is not Swan-affiliated. The wire's editorial source of
truth is `prompts/wire_voice.md`; the complete owner's manual is `SYSTEM.md`.

## Pipeline

```text
poll -> intake -> tier annotation -> triage -> resolve source/evidence -> draft -> gates -> publish
```

| Module | Responsibility |
|---|---|
| `nbn/sources.py` | RSS, SEC EDGAR, Perception, X recent-search, article text, FRED charts |
| `nbn/store.py` | SQLite URL/story deduplication, item state, post log, runtime key/value state |
| `nbn/brain.py` | Claude triage and single-post drafting |
| `config/source_tiers.toml` | Canonical P0/T1/T2/T3/T4 source registry |
| `nbn/source_policy.py` | Validated source classification, normalization, and ranking |
| `nbn/verify.py` | Typed source resolution, evidence qualification, and claim support |
| `nbn/lint.py` | Scope, style, mention, URL, attribution, and number-integrity vetoes |
| `nbn/editor.py` | Last-mile reader-value and feed-context judgment for autonomous posts |
| `nbn/publisher.py` | Typefully-first output routing plus the daily tape |
| `nbn/briefing.py` | Weekday Morning and Afternoon Block threads |
| `nbn/audit.py` | Daily receipt and class audit; stages material correction drafts |
| `nbn/report.py` | Token-protected Desk report |
| `nbn/main.py` | Poll loop, orchestration, health/status HTTP server |

## Safety invariants

- `NBN_AUTOPOST_ENABLED=false` means nothing publishes automatically.
- `NBN_SOURCE_POLICY_MODE=observe` forces all delivery to DRAFT/TAPE regardless of the
  autopost setting; the code default is the safer `enforce` mode.
- The default autopost classes are `primary` and `corroborated`; `secondary` is removed
  from the allowed set in code even if supplied through the environment.
- The model never supplies a receipt URL. The system attaches the source item's URL.
- Every number in a post must appear in fetched source text.
- Mentions are limited to the manually verified entries in `handles.json`.
- Corrections are always staged for human review and never autopublish.
- Every regular pipeline post is appended to a daily tape and recorded in SQLite.
- Tier 3, Tier 4, and unknown sources are discovery only: enforcement requires an eligible
  P0/Tier 1/Tier 2 receipt before drafting.
- Corroboration counts persisted, directly supporting evidence chains—not outlet names.
  Same-owner outlets, official account + website pairs, near-copy syndication, and pages
  resolving to the same artifact collapse.
- Official identity is not enough for `primary`: support, artifact-scoped paths, fetched
  canonical metadata, and official-X own-action scope all fail closed.
- A complete exact-story group—including provider substitutions—is finalized before the
  strongest receipt is selected, making receipt/class independent of feed order.

## Source ladder

Source tier measures receipt quality; it does not set the story's evidence class. P0 is an
official artifact, Tier 1 is premier reporting, Tier 2 is reliable specialist reporting or
original research, Tier 3 is discovery-only, and Tier 4 is a wrapper/syndicator that never
serves as a receipt. Unknown sources fail closed. The system preserves the original tip,
selects and drafts from the final receipt, and records both in `source_resolutions` for the
Desk and audit trail.

For data stories, a named provider that differs from the receipt triggers one targeted
provider lookup and one redraft. The replacement copy must pass deterministic number and
quote checks plus an adversarial semantic support check; mismatch or ambiguity holds.

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
`production` environment. Source-policy rollout is manual and phased:

```bash
# 1. Confirm production, one replica, and the /data volume in serviceManifest.
railway status --json

# 2. Confirm the publication kill switch without listing any secrets.
railway ssh -- printenv NBN_AUTOPOST_ENABLED

# 3. Before new code/migrations exist remotely, make an online SQLite backup.
railway ssh -- "python -c 'import datetime,os,sqlite3; p=os.environ.get(\"NBN_DB_PATH\",\"/data/nbn.db\"); d=\"/data/backups\"; os.makedirs(d,exist_ok=True); q=f\"{d}/nbn-pre-source-policy-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}.db\"; a=sqlite3.connect(p); b=sqlite3.connect(q); a.backup(b); print(q,b.execute(\"PRAGMA integrity_check\").fetchone()[0]); b.close(); a.close()'"

# 4. Upload in explicit observe mode; setting is batched with the code deploy.
railway variable set --skip-deploys NBN_SOURCE_POLICY_MODE=observe
railway up --detach

# 5. Do not run scripts/run_once.py. Watch one natural worker cycle and /health.
railway logs --since 10m
curl -fsS https://next-block-news-production.up.railway.app/health

# 6. After a clean natural cycle, enable enforcement (this triggers a config deploy).
railway variable set NBN_SOURCE_POLICY_MODE=enforce
railway logs --since 10m
curl -fsS https://next-block-news-production.up.railway.app/health
```

Stop the rollout and return to `observe` on any validation/migration/integrity error,
source-resolution exceptions above 10% of actionable items, any accepted Tier 3/Tier 4/
unknown receipt in enforce mode, more than 2× normal draft volume, or any
`IMMEDIATE`/`UNCERTAIN` result while `NBN_AUTOPOST_ENABLED=false`:

```bash
railway variable set NBN_SOURCE_POLICY_MODE=observe
```

Then use Railway's prior successful deployment rollback. The schema migration is additive;
restore the timestamped backup only for demonstrated database corruption, not as a routine
code rollback. Once this release is installed, `python scripts/backup_db.py` is the shorter
online-backup command for later maintenance.

The worker uses an expiring SQLite lease across news, briefing, and audit work so overlapping
deploy processes or an accidental `run_once` invocation cannot execute external work
concurrently. Fresh persisted resolutions are reused across worker restarts.

The worker exposes `/health` and `/status`; both return runtime and database state, and
health becomes HTTP 500 when the last completed cycle is more than ten minutes old. The
Desk is available at `/report?k=<token>` when `NBN_REPORT_TOKEN` is configured.

See `HANDOFF-CODEX.md`, `SYSTEM.md`, `ROADMAP.md`, and `CORRECTIONS.md` before changing
publishing behavior.
