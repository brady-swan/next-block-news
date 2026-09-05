# NBN model cost analysis

_Planning snapshot: September 4, 2026 (Central). No provider migration is approved or implemented by this document._

## Objective

Find a model mix that keeps Next Block News useful, fast, and editorially sound while bringing model spend closer to the original target of roughly $100-$180 per month. Cost is subordinate to output quality, but the present architecture must become affordable before the account has meaningful revenue or reach.

## Production baseline

The live configuration at the time of this snapshot is:

- Newsdesk and writer: Claude Sonnet 5
- Independent editor: Claude Opus 5
- Intake, preparation, and delegated research: Claude Haiku 4.5
- Autopost: off

A representative trailing 24-hour measurement contained 413 model calls, 4,955,909 ordinary input tokens, 409,717 output tokens, 269,249 cache-write tokens, and 911,526 cache-read tokens. Estimated spend was **$13.94**.

That window substantially preceded the switch from Sonnet to Opus for the editor:

| Seat | Model measured | Calls | Estimated cost |
|---|---|---:|---:|
| Newsdesk | Sonnet 5 | 166 | $10.23 |
| Editor | Sonnet 5 | 39 | $2.62 |
| Haiku preparation, RSS triage, and research | Haiku 4.5 | 207 | $1.07 |
| Editor recovery | Sonnet 5 | 1 | $0.02 |
| **Total** |  | **413** | **$13.94** |

At the same workload and token volume, using Opus 5 for the editor would raise the estimate to approximately **$17.91 per day, or $537 per 30 days**. A lighter trailing 12-hour sample implied approximately $370 per month after the Opus substitution, so the responsible current estimate is a volume-dependent **$370-$540 per month** rather than a single precise run rate.

The measured 24 hours produced 18 Typefully drafts, or about $0.77 in model spend per draft before the Opus switch and about $0.99 at the projected Opus rate. This is not a quality-adjusted measure; some drafts should be rejected.

Of 91 newsroom runs with recorded usage, 50 produced no story commit and cost $3.57 in aggregate. A commit can be either delivered or held, so this does not prove those runs were wasted. It does show that reducing unnecessary expensive newsroom wakes could save roughly $100 per month at the observed volume.

## Public API prices

Prices are USD per million input, cached-input, and output tokens.

| Provider and model | Input | Cached input | Output | Likely NBN role to test |
|---|---:|---:|---:|---|
| Claude Haiku 4.5 | $1.00 | $0.10 | $5.00 | Current preparation baseline |
| Claude Sonnet 5 | $2.00 | $0.20 | $10.00 | Current newsdesk/writer baseline |
| Claude Opus 5 | $5.00 | $0.50 | $25.00 | Current editor experiment |
| OpenAI GPT-5.6 Luna | $0.20 | $0.02 | $1.20 | Intake, extraction, assignment |
| OpenAI GPT-5.4 Mini | $0.75 | $0.075 | $4.50 | Newsdesk/writer candidate |
| OpenAI GPT-5.6 Terra | $2.00 | $0.20 | $12.00 | Editor or higher-judgment desk candidate |
| OpenAI GPT-5.6 Sol | $4.00 | $0.40 | $20.00 | High-judgment editor candidate |
| xAI Grok 4.3 | $1.25 | $0.20 | $2.50 | Newsdesk or editor candidate |
| xAI Grok 4.6 | $2.00 | $0.50 | $6.00 | X-aware research or editor candidate |

Official references:

- [Claude Sonnet 5 pricing](https://www.anthropic.com/research/claude-sonnet-5)
- [Claude Opus 5 pricing](https://www.anthropic.com/news/claude-opus-5)
- [Claude Haiku 4.5 pricing](https://www.anthropic.com/news/claude-haiku-4-5)
- [OpenAI GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [OpenAI GPT-5.4 Mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini)
- [OpenAI GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [OpenAI GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [xAI Grok 4.3](https://docs.x.ai/developers/models/grok-4.3)
- [xAI Grok 4.6](https://docs.x.ai/developers/models/grok-4.6)
- [xAI tool pricing](https://docs.x.ai/developers/pricing)

ChatGPT Pro does not include general OpenAI API usage. A deployed Railway service must use a separately billed Platform API key. See [OpenAI authentication and billing](https://learn.chatgpt.com/docs/auth).

## Same-workload cost models

These estimates apply each provider's public rates to NBN's measured token categories. They are normalization exercises, not promises: tokenizers, reasoning-token use, tool behavior, cache-hit rates, and the number of turns will differ by model.

| Configuration | Estimated daily | Estimated 30-day |
|---|---:|---:|
| Sonnet writer + Sonnet editor + Haiku preparation | $13.94 | $418 |
| Sonnet writer + Opus editor + Haiku preparation | $17.91 | $537 |
| Sonnet writer + Terra editor + Luna preparation | $13.22 | $397 |
| GPT-5.4 Mini writer + Terra editor + Luna preparation | $6.96 | $209 |
| Grok 4.3 writer + Terra editor + Luna preparation | $8.41 | $252 |
| GPT-5.4 Mini writer + Grok 4.3 editor + Luna preparation | $5.58 | **$167** |
| GPT-5.4 Mini writer/editor + Luna preparation | $5.23 | $157 |

Using one model for both writing and editing weakens the independence of the editor. The mixed OpenAI-writer/Grok-editor configuration is therefore the more interesting low-cost hypothesis if both models meet the quality bar.

## What the numbers suggest

1. **The Sonnet newsroom is the cost center.** It represented about 73% of measured spend. Replacing Haiku alone would save only about $25 per month.
2. **Opus must earn its premium.** At the measured volume, Opus adds roughly $118 per month compared with Sonnet in the editor seat. Its decisions should be compared blindly against cheaper editors before it becomes permanent.
3. **GPT-5.4 Mini is the largest credible pricing opportunity.** Applying its rates to the newsroom's measured token shape reduces that seat from about $10.23 to about $3.96 per day. Whether its reporting judgment and prose are good enough is unknown.
4. **Grok 4.3 is more compelling than Grok 4.6 as a pure cost substitution.** The same-token newsroom estimates are approximately $5.42 and $9.32 per day, respectively. Grok 4.6 may still justify itself through better quality or X-native tools.
5. **Grok's special value is X access.** Built-in X Search supports semantic and keyword search, account restrictions, date ranges, threads, images, and videos. It costs $5 per 1,000 calls plus model tokens. It could improve corroboration and peer monitoring, but it should supplement rather than replace deterministic ingestion of the guide accounts.
6. **Wake suppression is useful but insufficient by itself.** Avoiding all observed no-commit newsroom cost would save about $100 per month, but would not independently restore the original budget—and aggressive suppression risks missing the stories NBN was built to catch.

## Evaluation plan once API credits are available

### 1. Add provider-neutral plumbing

- Put Anthropic, OpenAI, and xAI behind one internal request/response interface.
- Preserve the current Anthropic production path during evaluation.
- Normalize structured output, tool calls, stop reasons, failures, latency, token categories, cache activity, reasoning usage, and tool charges.
- Extend rate-versioned cost accounting by provider and model.
- Keep credentials only in Railway/local secret stores: `OPENAI_API_KEY` and `XAI_API_KEY` must never enter Git or the tuning documents.

### 2. Build a replay set

Replay 30-50 recent real newsroom packets and editor decisions, including:

- Stories the owner published
- Stories the owner rejected
- Passed-over peer stories that should have run
- Treasury-company boundary cases
- Direct Bitcoin news, macro-adjacent news, regulation, security, mining, and ETF flows
- Strong and weak writing examples from the tuning record

Replay must be read-only: no Typefully writes and no publication mutations.

### 3. Compare models by seat

Newsdesk/writer:

- Sonnet 5 baseline
- GPT-5.4 Mini
- Grok 4.3
- Grok 4.6 when X Search materially contributes

Editor:

- Opus 5 baseline
- Sonnet 5 baseline
- GPT-5.6 Terra
- GPT-5.6 Sol
- Grok 4.3 and 4.6

Preparation:

- Haiku 4.5 baseline
- GPT-5.6 Luna

### 4. Score the work, not the benchmark reputation

Measure:

- Recall on stories NBN should cover
- Rejection of stories outside the agreed scope
- Speed and number of research turns
- Evidence quality and honest attribution
- Correct freshness and NEW/UPDATE use
- Lede strength
- Sentence simplicity, paragraph rhythm, and scannability
- Unnecessary detail, TA drift, and crypto drift
- Editor save rate, false rejection rate, and material improvements
- Actual API cost and latency per completed desk, candidate, and accepted draft

Use blinded side-by-side review where practical. Existing owner feedback is the ground truth; generic provider benchmarks are not.

### 5. Change one seat at a time

Start with shadow traffic. If a challenger passes the replay set, run it alongside production without allowing delivery. Only then change one production seat, observe it through the audit, and retain a one-variable rollback.

Suggested order:

1. Luna versus Haiku validates the provider adapter at low editorial risk.
2. Opus/Sonnet versus Terra/Grok evaluates the editor premium.
3. Sonnet versus GPT-5.4 Mini/Grok evaluates the large newsroom savings.
4. Test Grok X Search as a bounded research tool separately from the choice of writing model.

## Morning setup checklist

- Add billing or prepaid credits to the [OpenAI API Platform](https://platform.openai.com/).
- Create a dedicated NBN OpenAI project and scoped API key.
- Add credits and create a dedicated key in the [xAI Console](https://console.x.ai/).
- Do not paste either key into chat or commit it to the repository.
- Once the evaluation implementation is ready, add the keys to Railway as secrets and keep every non-Anthropic path in shadow until explicitly promoted.

