# Live Desk browser bundle

Approved prototype components, integrated with `/desk/api/workspace`. Python serves the built
assets; no JavaScript server or provider credential is shipped to the browser.

```
cd desk_ui
npm ci
npm run check
npm run build
```

Commit the resulting `nbn/desk_assets/workspace.js`, `workspace.css` and hash manifest with
their source changes. Keep bundles single-entry (no unauthenticated chunk fetches). All internal
navigation/assets/API requests carry the existing report token; external links have no referrer.

Offline browser acceptance:

```
PYTHONPATH=. python3.12 scripts/preview_workspace.py
# separate terminal, repo/desk_ui:
node qa.mjs
node reconsider-qa.mjs
```

The fixture server binds only loopback, owns a disposable SQLite database, and never starts
the worker or calls providers. `qa.mjs` uses Playwright from the configured Codex runtime
(override `NBN_QA_RUNTIME` with an installed package.json path). Screenshots and results are
under ignored `outputs/qa/`. These fixtures are not production editorial examples.
The reconsideration QA script is hardwired to loopback: it tests a real queue POST only
against the disposable fixture, including double-clicks, reload and conflict feedback.

`app/globals.css` preserves the approved visual system; `app/production.css` handles live-data
states and adaptations. Base UI primitives retain keyboard behavior. `main.tsx` owns a single
run/story/view URL state and fetch lifecycle. Schema changes belong in `nbn/desk_api.py` with
offline tests. Do not make provider calls or silently infer missing historical observations.
