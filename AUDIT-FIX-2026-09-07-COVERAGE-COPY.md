# Audit repair — keep draft copy out of reader-covered summaries

September 7, 2026. Narrow data-shaping repair under AUDIT-AUTONOMY.md.

## Evidence

Natural run `cycle:1788796754:7d15a14e` dropped Bitcoin Archive's new 3,400-BTC Liquid
return tip because it supposedly conflicted with prior coverage of a 3,998-BTC return.
The earlier recovery claim was actually the incorrect unpublished Typefully draft 10663389,
not either confirmed published Liquid post. The audit already warned against publishing it.

The saved writer packet shows a concrete input bug: `reader_covered_exact_events` and
`open_drafts` contained the same combined `post_leads` list for this canonical event, led by
the unpublished recovery claim. The separate 48-hour reader-feed index was correctly limited
to the older published incident/conditional-return posts. The writer did no extra retrieval.
The reason is consistent with the bad card, but the card is not proof of the model's private
reasoning or the sole cause of the dismissal. Draft accuracy remains an editorial concern.

Read-only audit retrieval independently found a newer transaction,
`a6d697a25266ce3c78774fd1d75f896b7af522ada209b0f6228ea497bc49a46d`, sending 3,400 BTC to
the previously reported federation return address, with about 598.5 BTC back to the sender.
It was unconfirmed at the 16:04 UTC check. This is not the earlier change-output transaction,
proof of recipient identity from chain data alone, or confirmation of complete recovery.
No draft or item was reopened, rewritten, dismissed or published by the audit.

## Repair and scope

Retain two bounded lede lists in the event catalog: IMMEDIATE/UNCERTAIN copy for the existing
reader-covered/reserved category, and DRAFT copy for open drafts. Build each model-facing
card from its own list. Failed/TAPE copy cannot displace either list. Keep the existing mixed
catalog field for compatibility and historical/legacy callers; current board shaping selects
the explicit lists. Empty explicit lists never fall back to mixed copy.

No new model prompt or instruction, stage, API schema, query budget, source policy, fuzzy
identity, deduplication predicate or Typefully operation. Existing IMMEDIATE/UNCERTAIN behavior
continues to protect potentially delivered work; this repair does not redefine uncertain as
confirmed publication or change which candidate can be published. Source cards remain context,
not factual evidence. Stored historical packets and incorrect drafts are not rewritten.

## Verification

Regression fixture reproduces a published event followed by two aliased open drafts, FAILED
and TAPE outputs. Before the fix, the reader card contained the failed/TAPE ledes. The repaired
normal and compact packets separately retain the published and draft ledes, preserve aliases,
and retain UNCERTAIN duplicate protection. Release and smoke results follow below.
