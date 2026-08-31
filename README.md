# Next Block News

Autonomous Bitcoin news wire for X at `@nextblocknews_`. A single Python worker watches
primary sources, press feeds, Perception, and selected X accounts; classifies new items;
drafts wire-format posts with Claude; applies deterministic and editorial gates; and
publishes eligible stories through Typefully.

This project is independent and is not Swan-affiliated. The wire's editorial source of
truth is `prompts/wire_voice.md`; the complete owner's manual is `SYSTEM.md`.

## Pipeline

```text
poll sources -> intake gates -> triage -> corroborate -> draft -> lint -> editor -> publish
```

| Module | Responsibility |
|---|---|
| `nbn/sources.py` | RSS, SEC EDGAR, Perception, X recent-search, article text, FRED charts |
| `nbn/store.py` | SQLite URL/story deduplication, item state, post log, runtime key/value state |
| `nbn/brain.py` | Claude triage and single-post drafting |
| `nbn/verify.py` | Independent web corroboration with deterministic domain checks |
| `nbn/lint.py` | Scope, style, mention, URL, attribution, and number-integrity vetoes |
| `nbn/editor.py` | Last-mile reader-value and feed-context judgment for autonomous posts |
| `nbn/publisher.py` | Typefully-first output routing plus the daily tape |
| `nbn/briefing.py` | Weekday Morning and Afternoon Block threads |
| `nbn/audit.py` | Daily receipt and class audit; stages material correction drafts |
| `nbn/report.py` | Token-protected Desk report |
| `nbn/main.py` | Poll loop, orchestration, health/status HTTP server |

## Safety invariants

- `NBN_AUTOPOST_ENABLED=false` means nothing publishes automatically.
- The default autopost classes are `primary` and `corroborated`; `secondary` is removed
  from the allowed set in code even if supplied through the environment.
- The model never supplies a receipt URL. The system attaches the source item's URL.
- Every number in a post must appear in fetched source text.
- Mentions are limited to the manually verified entries in `handles.json`.
- Corrections are always staged for human review and never autopublish.
- Every regular pipeline post is appended to a daily tape and recorded in SQLite.

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
python3 scripts/run_once.py
python3 -m nbn.main
python3 -m unittest discover -v
```

Configuration is read from environment variables; the code does not automatically load
`.env`. Defaults keep autopost disabled. Be careful when using `railway run`, which injects
the production service environment.

The test package removes inherited credentials, forces autopost off, uses temporary data
paths, and blocks real socket connections. HTTP, model, and publisher boundaries must be
mocked in tests.

## Deploy

The repository is linked to the Railway project and service `next-block-news` in the
`production` environment. Deployment is manual:

```bash
railway status
railway up --detach
railway logs
```

The worker exposes `/health` and `/status`; both return runtime and database state, and
health becomes HTTP 500 when the last completed cycle is more than ten minutes old. The
Desk is available at `/report?k=<token>` when `NBN_REPORT_TOKEN` is configured.

See `HANDOFF-CODEX.md`, `SYSTEM.md`, `ROADMAP.md`, and `CORRECTIONS.md` before changing
publishing behavior.
