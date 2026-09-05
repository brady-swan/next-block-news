# NBN model bake-off

This directory contains the immutable registry for Plan 0057. Generated corpora, provider
responses, the evaluation SQLite ledger, scorecards, and blinded review sheets belong under the
ignored `.model-eval/` directory.

The evaluator is offline from production. It does not publish or mutate NBN state. Inside the
Python process it recognizes only:

- `NBN_EVAL_ANTHROPIC_API_KEY`
- `NBN_EVAL_OPENAI_API_KEY`
- `NBN_EVAL_XAI_API_KEY`
- optional `NBN_EVAL_SERPAPI_KEY`

## Safe execution with Railway variables

The owner explicitly authorized this bounded test to reuse the existing Anthropic, OpenAI, and
xAI credentials. Map them into the evaluator namespace only across a sanitizing `env -i` boundary;
do not add implicit fallback behavior to the evaluator itself:

```sh
railway run -- sh -c 'exec env -i PATH="$PATH" HOME="$HOME" NBN_EVAL_ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" NBN_EVAL_OPENAI_API_KEY="$OPENAI_API_KEY" NBN_EVAL_XAI_API_KEY="$XAI_API_KEY" python3 scripts/model_bakeoff.py credentials'
```

This reuses provider-side quota, but the evaluation SQLite ledger attributes each request and
enforces its independent lifetime `$40` cap. The sanitized Python process receives no ordinary
provider key names, Typefully credentials, production database path, or source tokens.

If dedicated evaluation credentials are supplied later, first confirm only credential presence;
this command never prints key values, lengths, prefixes, or suffixes:

```sh
railway run -- sh -c 'exec env -i PATH="$PATH" HOME="$HOME" NBN_EVAL_ANTHROPIC_API_KEY="$NBN_EVAL_ANTHROPIC_API_KEY" NBN_EVAL_OPENAI_API_KEY="$NBN_EVAL_OPENAI_API_KEY" NBN_EVAL_XAI_API_KEY="$NBN_EVAL_XAI_API_KEY" NBN_EVAL_SERPAPI_KEY="$NBN_EVAL_SERPAPI_KEY" python3 scripts/model_bakeoff.py credentials'
```

Use the same `railway run -- sh -c 'exec env -i ...'` boundary for `discover`, `probe`, and `run`.
That ensures the Python evaluation process receives the evaluation keys and basic process paths,
but not Typefully credentials, the production database path, source tokens, or ordinary provider
keys.

## Sequence

1. `validate` every frozen corpus.
2. `estimate` the planned lane before spending.
3. `discover` provider model identities.
4. `probe` structured output, effort, usage, and native-tool compatibility.
5. `run` one lane at a time. The persistent ledger refuses any request whose conservative
   reservation would cross the lifetime `$40` cap.
6. `report` generates objective scorecards and a blinded owner-review sheet.

Do not delete or replace `.model-eval/evaluation.sqlite` during the experiment. It is the
restart-safe cost ledger and records unsettled reservations at their full worst-case charge.
