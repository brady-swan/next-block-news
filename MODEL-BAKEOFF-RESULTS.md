# NBN model bake-off — phase-one results

- **Run:** `090799e2f78a49be98435420f66e295a`
- **Executed:** September 5, 2026
- **Spend:** `$2.72994060` across 105 settled provider calls
- **Lifetime test cap remaining:** `$37.27005940` of `$40`
- **Production changes:** none

## Bottom line

The current evidence does not justify a production model switch yet, but it identifies the useful
finalists and rules out several branches:

- Use `medium`, not `low`, for both GPT-5.4 Mini and Grok 4.3 in further editorial tests. Both low
  conditions produced an invalid result and weaker judgment.
- Grok 4.3 medium is the serious newsdesk challenger. It nearly matched Sonnet's mechanical
  disposition score, wrote much shorter copy, and cost about one-third as much on the same frozen
  desk packets.
- GPT-5.4 Mini medium is inexpensive and concise, but its news judgment was materially weaker on
  this small calibration set. It remains interesting as an editor or bounded preparation model,
  not the leading newsdesk replacement.
- Luna low was cheaper, faster, and slightly more schema-reliable than Haiku on preparation. The
  preparation pool was intentionally unadjudicated, however, so this run cannot tell us whether
  Luna suppressed worthwhile leads. A blind route review is required before switching it on.
- The editor ranking is not valid. The mechanical corpus builder treated historical production
  editor verdicts as truth, even where current coverage memory made a draft an obvious duplicate
  or later owner feedback contradicted that verdict. Preserve the outputs as blind copy evidence;
  do not use their objective percentages to choose an editor.
- Grok's native X Search works through the API. The strengthened probe recorded one real X search,
  returned a current `@BitcoinArchive` post and its X URL, and incurred the provider's additional
  `$0.005` search charge. That proves capability, not editorial quality.

## Newsdesk calibration

Three frozen four-story desks ran three times per condition. Percentages below are mechanical
disposition alignment against the preregistered acceptable sets. Cost is total for all nine calls.

| Condition | Valid | Alignment | Mean words in a drafted post | Mean sentence words | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Sonnet 5 medium | 9/9 | 77.78% | 138.4 | 25.9 | $0.434114 |
| Grok 4.3 medium | 9/9 | 75.00% | 73.2 | 15.8 | $0.143601 |
| Mini medium | 9/9 | 66.67% | 54.0 | 17.3 | $0.109451 |
| Grok 4.3 low | 8/9 | 71.88% | 65.7 | 18.2 | $0.104753 |
| Mini low | 8/9 | 56.25% | 50.8 | 15.9 | $0.067470 |

The apparent two-point Sonnet/Grok-medium gap is far too small for a winner claim on 12 events.
Grok's concise default is directionally aligned with the owner's repeated scannability feedback;
Sonnet remained prone to turning a clean fact pattern into a long analytical post. Grok also
occasionally supplied an interpretive conclusion that exceeded the frozen receipt, so brevity is
not the same thing as restraint.

All medium newsdesk conditions missed at least two preregistered must-cover/update cases across
the calibration set. Under Plan 0057's strict advancement rule, no challenger advances from this
calibration alone. More importantly, the control also fails that bar. This is evidence that a
larger owner-adjudicated holdout is necessary, not evidence that the wire should stop.

## Preparation: Haiku versus Luna

Each condition processed six intake batches and six assignment batches covering 300 raw items.

| Condition | Valid | Mean latency | Cost |
| --- | ---: | ---: | ---: |
| Haiku 4.5 pinned | 9/12 | 41.2s | $0.279322 |
| Luna low | 10/12 | 30.7s | $0.048871 |

Luna was about 82.5% cheaper and 25% faster in this run. Its errors were one malformed candidate
ID and one invalid assignment batch. Haiku completed intake cleanly but failed three assignment
batches through an unexpected field or incomplete output.

The important question is editorial recall, not API savings. The sampled items did not have
complete preregistered positive and negative labels, so route disagreements are presented only in
the blind review. Until those disagreements are judged, Luna is a promising candidate rather than
a safe replacement.

## Editor run: exploratory only

The following figures describe output shape and transport reliability. The disposition percentages
in the generated scorecard are invalid for model selection and are intentionally omitted here.

| Condition | Valid | Mean words in edited post | Mean sentence words | Cost |
| --- | ---: | ---: | ---: | ---: |
| Opus 5 medium | 6/6 | 97.8 | 21.3 | $0.842580 |
| Sonnet 5 medium | 5/6 | 112.9 | 26.4 | $0.353358 |
| Mini medium | 6/6 | 85.1 | 17.2 | $0.172856 |
| Grok 4.3 medium | 6/6 | 118.9 | 24.0 | $0.141076 |

Mini produced the shortest and simplest edited copy in this sample. Opus was the most expensive
condition. Sonnet had one strict-schema failure. Those facts are usable; the verdict ranking is
not. The owner-blinded sheet is the correct next evaluation surface for quality.

## X Search capability

The first strengthened probe found the right recent X post and incurred the search charge, but the
harness initially failed to recognize xAI's `server_side_tool_usage_details` and
`custom_tool_call: x_keyword_search` envelope. That attempt was correctly retained as a billed
instrumentation failure. The normalizer was expanded and unit-tested, and the second probe
recorded:

- one native `x_search` invocation;
- a current `@BitcoinArchive` post and direct `x.com` status URL;
- `$0.009545` total provider cost, including `$0.005` for the search;
- successful strict structured output.

The returned summary also repeated the source account's promotional conclusion. A live research
test must therefore grade whether native X retrieval adds useful leads while the newsdesk still
applies NBN judgment and corroboration.

## Method and isolation

The existing Railway `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and `XAI_API_KEY` were reused with the
owner's approval. A sanitized `env -i` launcher mapped them transiently to evaluator-only
`NBN_EVAL_*` names. The Python process received no Typefully credential, production database path,
publisher control, source cursor, or ordinary provider-key name.

Provider quota is shared with production, but spend attribution is not: the evaluator's durable
SQLite ledger records provider, model, lane, case, effort, tokens, latency, reported cost, and
native-tool use for every request. A persisted reservation system prevents the experiment from
crossing its independent lifetime cap after a crash or restart.

## What remains before adoption

1. Complete the owner-blind review of the newsdesk, preparation, and editor disagreements.
2. Build a truly prospective, uncontaminated holdout with owner judgments fixed before seeing
   model identities. Do not repair the flawed editor labels after looking at candidate outputs.
3. Run a bounded live research comparison once an isolated search credential or an explicitly
   approved equivalent search boundary is available. Grok native X Search should be a separate
   treatment, not bundled into base-model judgment.
4. If a finalist survives those checks, run it in non-publishing shadow mode and measure cost and
   decisions on identical production packets before proposing a routing change.

## Artifacts

Generated artifacts are intentionally ignored by Git and remain under `.model-eval/`:

- `calibration-report/blind-review.md`
- `preparation-report/blind-review.md`
- `editor-report/blind-review.md`
- `*/objective-scorecards.json`
- `evaluation.sqlite`, redacted result JSONL, model discovery, corpora, and manifests
