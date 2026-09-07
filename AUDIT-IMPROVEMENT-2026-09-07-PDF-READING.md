# Bounded PDF reading

September 7, 2026. Authorized by the owner's expanded audit autonomy. Status: independently approved implementation; release verification underway.

## Why this, now

The Philippines payment-controls story had an original BSP draft circular available as a
PDF. Our article reader could not read it. The earlier PDF repair correctly stopped raw
binary data becoming a receipt; this small follow-up makes readable PDFs usable evidence.
It does not make extraction success proof of a claim or establish an event's date.

## Implementation boundary

- Keep the existing `fetch_source` / article-reader route, source identities, redirect safety,
  receipt registration, memory and text budgets. No new agent or model call.
- Use local Poppler `pdftotext` in the runtime image. Detect PDF content by MIME/signature,
  not filename. Parse at most the first 20 pages, with a 10-second subprocess ceiling bounded
  by the caller's remaining deadline, and reject parser inputs above 10 MiB. The existing HTTP
  client still reads responses before format detection; this is a parser-input limit, not a
  new general download/memory guarantee.
- Read only a bounded excerpt from the temporary extraction output. Preserve paragraph/page
  boundaries and respect the caller's character cap. Clean temporary files on every path.
- Label every result as text-only and potentially incomplete; say explicitly that scanned
  pages, charts/images and layout-sensitive tables are not verified. Don't infer publication
  dates or authorship from PDF metadata. Preserve the actual URL and redirects.
- Preserve those bounded limitations through story-attempt storage, the evidence pool and
  next-session restored receipts, not only the immediate fetch/artifact/editor payload. This
  was the independent reviewer's required addition; it extends existing metadata, not memory design.
- Invalid/password-protected/empty or image-only PDFs, missing extractor, and timeouts return
  typed empty failures. They must not enter receipts, source caches or reporting memory.
- Advertise PDF text support in the existing tool description. No OCR, screenshots, page
  selection API, new research mandate, source policy, editorial rules, model budget or cadence.

## Checks and release

Use offline fixtures for readable/multi-page text, clipping, empty/malformed documents,
oversize inputs, missing executable and subprocess timeout. Retain MIME/signature,
redirect-safety and HTML-at-PDF-URL tests. Exercise successful and failed extraction through
the real newsroom receipt/memory path. Run the full suite in a clean release archive.

Independently review the plan and patch. Verify extraction against the real BSP circular,
visually inspect the relevant pages locally, and smoke the production reader directly without
paid model calls or Typefully mutations. Check health/Desk and the next natural worker cycle.
Keep autopost OFF. Pause and then restore the existing rolling audit, preserving its scope.

No database migration. Rollback is runtime `c7887fd` (the preceding production code) or its
clean archive; restoring a database is neither needed nor authorized. Track release IDs,
verification, limitations and measured latency below. No new model call or larger context budget
is added; a readable PDF excerpt consumes ordinary input tokens if supplied to a model. Extraction
itself adds local CPU only when a PDF is fetched. Unrelated worktree changes stay out of this release.

## Review and real-source limits

Independent lead reviewer approved the plan with the memory-metadata addition. Writer tool
description is versioned as `editorial-core-v2.19-pdf-text`; the orientation/editor policy is unchanged.

The actual BSP document has 27 PDF pages (including annexes). Direct local extraction and a
rendered page-4 check confirm the draft's virtual-asset-firm provision is readable text. The
registration-pause provision is on page 15. The default 8,000-character receipt cannot include
all of this document: successful adapter extraction must not be reported as full verification
of the story. This implementation deliberately does not add page-selection or OCR tools.
File creation metadata is not a verified first-publication time.

## Local verification

- Independent review: 48 targeted tests passed. Reviewer also caught marker-only output under
  tiny character allowances; the repaired path returns an empty failure and creates no receipt,
  cache entry or memory artifact. Final implementation approved.
- Full working-tree suite: 518 tests passed (including unrelated evaluator tests).
- Real BSP extraction: 8,000 returned characters in 0.161 seconds locally, explicitly clipped
  partway through page 3. Original PDF bytes and invented metadata dates never enter the receipt.
- Temporary extraction files are removed on success and all tested failure paths. Poppler runs
  without a shell, with stderr/stdout suppressed, and timeout cleanup kills/reaps the subprocess.
