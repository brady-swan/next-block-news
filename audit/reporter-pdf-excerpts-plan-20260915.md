# Bounded repair: legislative PDF excerpts

Status: independent lead approved with refinements; implementation in progress. Evidence: overnight record1348,
draft10771366; baseline code HEAD5a2ccb4. Existing Plan0077 PDF fetch and visual renderer are
complete and are not being rebuilt. This is a newly reproduced usability defect.

## Problem

Reporter selected the actual Section301(e) effective-date sentence from H.R.10357 p51.
The default PDF extraction inserts margin numbers6/7/8 into the sentence, and exact-match
excerpt validation rejects the correct prose. Actual original-layout pixels were inspected
by the audit and support the passage. Source SHA256
0350266fd99072e5a700fcdc76f21687d9f6eab0a58f7b88cddf4e9a598bc7d6.

## Proposed smallest change

1. Add an explicit opt-in legislative-layout text mode to reporter PDF fetching. Default
   plain extraction and all legacy paths remain unchanged. Reporter can retry a selected
   page with this mode when margin numbering interferes with an excerpt. Reject pdf_query;
   selected pages only, raw layout separately capped at24KiB (narrow range on overflow).
2. Use existing Poppler layout output. Recognize only the distinctive GPO legislative-page
   format (XML header plus printer footer) and a separate, regularly sequenced margin-number
   column (allow actual one-character alignment shift from labels9 to10). Remove matched
   label tokens alone, rejecting broken numbering/displaced labels/unexplained body rows,
   preserving substantive digits, punctuation, paragraph
   sequence, headings and section numbers. Reject unrecognized/ambiguous layout; suggest
   ordinary text or original-page inspection. No fuzzy quotation match, blanket digit removal,
   arbitrary writer-supplied cleaned receipt or OCR inference.
3. Preserve exact original-PDF hash, physical page references, extraction mode/version and
   raw layout evidence in the retained receipt metadata. The returned text explicitly states
   the transformation and its limitations. Continuation must retain the same mode.
4. Existing quote/excerpt validator still requires contiguous verbatim text in the retained
   source view with whitespace-only matching. No publishing/media/rights-policy changes.
5. Test the actual failing sentence, meaningful numbers at line starts and inside prose,
   numbered lists/tables and unsupported layouts, default behavior, bounds, continuation,
   tool schema/dispatch and strict excerpt rejection of altered text. Render the fixed
   passage locally and inspect pixels. Use synthetic fixtures for committed tests; actual
   downloaded source stays in the audit evidence directory.
6. Independently review final diff; deploy only this delta against current known production
   baseline. If deployment needs reporter pause, preserve exact same shift and13:00UTC cutoff.
   Smoke read/render without creating or editing Typefully drafts. Give reporter concise new
   tool guidance and verify acknowledgment; no demand to recreate the already-staged tax draft.

## Scope/rollback

Authorized overnight bounded tool improvement; no model, cadence, editorial-policy or system
architecture change. Existing drafts remain read-only and autopostOFF. Preserve unrelated dirty
work. Revert only this focused commit and deployment to remove the opt-in path; no DB restore.
If layout recognition becomes complex or unreliable, stop and propose the smaller alternative
of a narrowly scoped inspected-page excerpt tool, rather than building general PDF reconstruction.
