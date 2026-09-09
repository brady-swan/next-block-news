# Perception × Next Block News: integration questions and highest-value requests

Prepared September 8, 2026 CT. Draft for Brady to review/share; **not sent**.

## The opportunity

Next Block News is building an automated Bitcoin wire. Our Writer researches leads, retains evidence,
writes posts, and hands them to an independent Editor. We use Perception Intelligence and want to
make its industry-specific corpus a core discovery and reporting resource.

The most valuable product for us is a timely stream of meaningful developments, with a short path
from a tip to the underlying source. We are not looking for another generic crypto summary or a
provider to make our publication decisions.

We can offer concrete integration examples and feedback on lead quality, source follow-through,
freshness and retrieval ergonomics. We'd like to learn what is already possible before requesting
new features. The requests below are proposed questions, not assumptions about your roadmap.

## Three priorities

### 1. Source-rich, structured research results

Could REST and MCP expose a consistent structured source object with:

- Stable ID, canonical URL, publisher/author and document type.
- Original publication, modification and Perception first-seen/indexed times, with unknowns explicit.
- Text with a status such as full body, excerpt, transcript segment or extraction unavailable.
- Outbound source links from the body, especially linked statements, filings, reports and original posts.
- Where known, citation relationships: this article cites that document or quotes that statement.
- For transcripts, speaker, occurrence timestamp, original recording/document URL and surrounding text.

This would let our Writer follow reporting upstream while preserving what was actually inspected.
An extracted outbound-link list alone would be useful; an inferred primary-source graph could follow.
The graph should distinguish a known link from an inferred connection and earliest indexed coverage
from the true origin. We do not need a vendor verdict that a claim is universally verified.

Observed examples: a Bitcoin Magazine article's `get_article` response labeled Full Text contained
only a 399-character feed summary. A CFTC speech retrieval returned substantial source text promptly.
Several REST article bodies were thousands of characters long. Differentiating these cases in the
response would save unnecessary writer work. Our current NBN collector also truncates bodies; that
part is our own integration defect to fix.

### 2. Efficient delivery of new and changed items

Is there an existing incremental feed, cursor or push option we should use? Ideally:

- An `updated_since`/cursor interface for additions and changed records, with pagination.
- Subject/entity/source filters, stable IDs and deterministic ordering.
- Original publication time separate from discovery/indexing time.
- Updates/corrections identified without relabeling an old event as new.
- Optionally signed webhooks for matching developments, with replay/catch-up through the API.

Your API page advertises 90-second updates. We want to access that freshness without repeatedly
querying two calendar days or losing records behind page one. We understand indexing cadence is not
an end-to-end delivery guarantee. Public alerts describe 15-minute evaluation and Slack/email delivery;
we have not found a public webhook contract. [API](https://perception.to/api),
[alerts](https://perception.to/features/alerts).

If push is not available, a well-defined incremental REST response would be an excellent first step.
Can we also confirm the appropriate shared allowance for a small always-on newswire? Our current
15-minute schedule alone can consume 96 REST requests/day before catch-up or our other application.
We are not asking you to make every poll invoke an AI analysis.

### 3. Coverage visibility and precise research controls

Can we inspect which sources/handles/corpora are actually available, their last successful collection,
and what an empty result means? We'd especially value clear coverage for Bitcoin guide accounts,
primary institutions, technical/governance discussions and original conference/podcast statements.

For statement search, date range, speaker/entity, exact phrase, document type and result-size controls
would help considerably. A query for CLARITY matched ordinary uses of the word; CLARITY Act improved
relevance but still returned a long set of historical corporate documents. Neither test returned
conference/podcast matches or original source URLs. These are small samples, not a conclusion that
the corpus is generally missing those materials.

An explicit `not_tracked`, `no_matches`, `stale_collection` or `collection_error` distinction would be
more useful than inferring the cause from an empty list. `get_brains_corpus` for BitcoinArchive returned
zero for September 8–9; we'd like to understand coverage and whether the account-owned Brain route is
the right alternative, not assume the account had no activity.

## Small contract questions with reproducible examples

Read-only tests on September 9, 2026, approximately 02:12–02:28 UTC:

| Operation | Observation | Question |
| --- | --- | --- |
| REST `/feed`, keyword `Lummis`, dates Sep 5–9, `limit=5`, page 1 | Ten rows; returned page size 50 | Is another parameter required, or is `limit` not being applied? |
| REST keyword `Lummis CLARITY` versus MCP `q=Lummis CLARITY`, same dates | REST zero; MCP nine matches | What are each surface's supported Boolean/phrase semantics? |
| MCP `search_mentions`, subject IDs self-custody/merchant-payments/mining-pools, Sep 8–9 | Nineteen matches; twelve shown | Useful taxonomy; can results expose timestamps, matched subjects and a pagination cursor? |
| MCP company search for Block, Sep 8–9 | Relevant Bloomberg and The Block results in 0.97s | Useful entity matching; can we discover canonical IDs/aliases for our beat entities? |
| MCP research results | Sample calls primarily returned markdown | Is there a structured-content/JSON option? Can presentation hints be omitted? |

Can daily included usage/remaining calls be read separately for REST, MCP and article access, with
reset times and wallet/overage behavior? Observed MCP rate headers described the per-minute window,
not the daily remaining balance. This matters because two applications share the subscription.

## A useful design-partner experiment

If there's interest, we could propose a bounded Bitcoin newswire pilot around meaningful policy,
self-custody/security, mining and real-world adoption. Compare incremental leads, original-source
access, meaningful updates and discovery latency against our existing direct intake.

We would provide selected, anonymized integration examples—not credentials, full private writer
sessions or automatic public access to your corpus. Our request is for data and retrieval improvements;
NBN retains its editorial standards and its own model/editor/publisher stack.

No feature should require waiting for several outlets to repeat a story before the first source is
available. That would defeat the speed advantage we are trying to create.
