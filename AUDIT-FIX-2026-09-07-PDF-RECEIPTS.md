# Audit repair — unread PDFs must not become inspected receipts

September 7, 2026. Narrow technical repair under AUDIT-AUTONOMY.md.

## Evidence and scope

While auditing the Philippines payments draft (Typefully 10661397), the original BSP circular
linked from Cointelegraph returned HTTP 200 with `application/pdf`. The article adapter reported
`outcome=ok` and 8,000 characters beginning `%PDF-1.7`, rather than readable document text.
That could register binary file syntax as successfully inspected evidence. The production
writer for this particular story used the Cointelegraph capture, not this PDF; do not attribute
the audit's subsequent original-document check to the writer.

The audit independently extracted the BSP draft locally. Its main payment-controls and
12-month registration-pause clauses support the article's core claims. This does not establish
when the draft first became public. PDF text extraction is not a production capability yet.

## Repair

Detect PDF MIME types (case-insensitive, ignoring parameters) and a PDF signature in responses
mislabelled as generic binary or HTML. Return `evidence_failed` / `unsupported_document`, empty
text, and an explicit unread-document limitation. Retain the safe final URL and redirect chain.
Do not reject a readable HTML page merely because its URL ends in `.pdf`.

The existing newsroom failure path prevents a receipt, URL-cache entry, character charge or
reporting-memory receipt from being created. Other retrieval routes remain available. No PDF
library, new provider, mandatory research call, source-count rule, model/prompt/cadence change,
historical data rewrite or Typefully mutation is included.

## Verification

- Full working-tree offline suite: 491 tests passed (including unrelated evaluator tests).
- New cases cover MIME/signature detection, malformed declared PDFs, safe redirects, HTML
  at a PDF-looking URL, and the actual newsroom path excluding unread data from evidence/memory.
- Clean-release test, deployment, backup and production smoke evidence will be recorded below.

Rollback is the prior runtime. No schema/configuration change or database rollback is needed.
