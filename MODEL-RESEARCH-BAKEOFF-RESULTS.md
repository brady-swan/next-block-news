# NBN research model bake-off

> Status reviewed 2026-09-06: Historical design/evaluation record. Preserve dated findings; later releases may supersede the proposal. For the current system, see [DOCUMENTATION.md](DOCUMENTATION.md) and [SYSTEM.md](SYSTEM.md).

- **Executed:** September 5, 2026
- **Production changes:** none
- **Corpus:** 10 frozen source-resolution assignments based on recent NBN failure modes
- **Grok repetitions:** 2 per case and condition
- **Haiku repetitions:** 1 per case; stopped after a decisive reliability and quality gap
- **Research-lane spend:** $4.025113 across 50 calls

## Decision

Use **Grok 4.3 medium with native web and X search available** for bounded source-resolution
assignments.

X search should be optional and selective, not mandatory evidence. A social result remains a lead;
the memo should prefer an official or original receipt when one exists and should never infer the
account from prose when the returned URL identifies a different handle.

The test does not support retaining Haiku as the research assistant. It does support retaining
Haiku for cheap intake classification, where its job is bounded and does not require an agentic
search/fetch loop.

## Results

| Condition | Valid | Avg. latency | Avg. cost | Retrieval calls |
| --- | ---: | ---: | ---: | ---: |
| Grok 4.3 medium, web + X | 20/20 | 27.42s | $0.083025 | 4.60 web + 2.25 X per assignment |
| Grok 4.3 medium, web only | 20/20 | 29.57s | $0.083457 | 6.25 web per assignment |
| Haiku 4.5, SERP + fetch | 2/10 | 40.44s | $0.069548 | 3.00 SERP + 1.90 fetch per assignment |

The Grok conditions used xAI's provider-reported token and native-tool charges. Haiku includes
[SerpAPI's Developer-plan allocation](https://serpapi.com/pricing) at $75 for 5,000 successful
searches, or $0.015 per search.

Enabling X did not increase average cost or latency in this sample. Grok substituted direct X
searches for some broader web searches: web+X averaged 6.85 total searches, versus 6.25 for
web-only, but used fewer tokens and finished about two seconds faster.

## Objective checks

The following checks are deliberately mechanical. They do not replace the case-by-case reporting
review.

| Condition | Expected freshness | Preferred source domain found | All required concepts present |
| --- | ---: | ---: | ---: |
| Grok web + X | 18/20 | 14/20 | 8/20 |
| Grok web only | 16/20 | 14/20 | 6/20 |
| Haiku SERP + fetch | 8/10 | 5/10 | 3/10 |

The concept matcher is intentionally literal, so its absolute scores are not editorial grades.
Its useful signal is the within-corpus comparison.

## Pairwise reporting review

My case-by-case review of the 20 Grok pairs scored **10 wins for web+X, 7 for web-only, and 3
ties**. Several were marginal. The native-X advantage was real but concentrated:

- It found the exact current 600 BTC early-miner movement when web-only returned an older March
  event, and correctly treated an older approximate match as stale in the other repetition.
- It reliably found Alex Thorn's originating Coldcard thread and its follow-up rather than relying
  only on later summaries.
- It found Bukele's exact response URL in one El Salvador repetition where web-only returned only
  an approximate account reference.
- It marked the late ZeroHedge wrapper of the August Oklahoma water-leak story stale in both runs;
  web-only found the same local reporting but labeled the event fresh twice.
- It improved authorship and mechanism detail on the Cornell/BPI analysis.

Web-only also won real cases:

- It was cleaner on the Sheriffs/CLARITY letter; X search added irrelevant Grok-account posts.
- It was more reliable on Trezor's X identity. The X-enabled condition once labeled a
  `BitcoinNewsCom` URL as Trezor and once returned an older Trezor incident post, although both
  conditions still selected Trezor's official blog as the best receipt.
- It found useful public-X results through the web index even without the native X tool. Native X
  is therefore an incremental retrieval advantage, not the only route to social evidence.

The production implication is to give Grok both tools and tell it to use X when the assignment
turns on an originating post, live conversation, first-party response, or ambiguous current event.
For filings, official releases, and ordinary publication reporting, web search may be enough.

## Why Haiku lost

Haiku's 8/10 schema failures were overlength fields rather than broken JSON. That could be repaired
with looser limits or a stricter prompt, but the reporting problems went beyond formatting:

- It called the eight-day-old Oklahoma event fresh even after finding the August 28 local report.
- It wrote that 20.5 BTC was 10% of 1,789 BTC in the Coldcard memo, then noted elsewhere that the
  arithmetic did not reconcile. Grok correctly separated the roughly 208 BTC Wave 3 pool from the
  roughly 1,789 BTC total across attacks.
- It dated the Trezor disclosure to 2024 rather than 2026, selected a Binance aggregation as the
  best receipt, and failed to find Trezor's searchable official post.
- It returned a placeholder rather than a real status URL in the dormant-wallet case.
- It often exhausted three SERP calls while producing longer, less decisive memos and took about
  13 seconds longer than Grok.

This is the wrong failure profile for a reporting assistant. A cheap research memo that introduces
an event-date or arithmetic error creates more expensive downstream work than it saves.

## Cost implication

At the measured $0.083 average:

| Research assignments | Daily | 30-day month |
| --- | ---: | ---: |
| 5/day | $0.42 | $12.45 |
| 10/day | $0.83 | $24.91 |
| 20/day | $1.66 | $49.82 |

Research should be invoked only when the desk has a concrete unresolved assignment. It is not a
mandatory call every 15-minute newsroom session. The theoretical ceiling of one research job on
every run would be about $5.06/day over a 15-hour schedule; that should remain a safety ceiling,
not an operating target.

## Production guardrails for the eventual switch

1. Give Grok native web and X search, but ask for the fewest searches needed to resolve the
   assignment.
2. Require exact source URLs and exact X account/status URLs in the memo.
3. Treat X results as leads unless the post is itself the first-party statement or original
   analysis being reported.
4. Reject an X attribution when the claimed account does not match the status URL path.
5. Preserve the current principle: narrow a supportable claim when the ideal source is blocked;
   do not hold useful routine news merely because the perfect receipt is inaccessible.
6. Meter provider-reported web/X calls, tokens, cost, latency, source-domain quality, and downstream
   editor rejection in the rolling audit.

## Test integrity

The evaluator received only explicitly mapped `NBN_EVAL_*` credentials through a sanitized
environment. It had no Typefully credential, production database path, source cursor, or publisher
control. The immutable corpus and all redacted outputs remain under `.model-eval/`; the lifetime
evaluation ledger remains below its independent $40 cap.
