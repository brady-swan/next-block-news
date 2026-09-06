# Corrections protocol

The pinned post promises: "When we get something wrong, we say so. Corrections are posted
and quote the original. Nothing is deleted." This document is how that promise is kept.
It exists so the first error is handled by a checklist, not by adrenaline.

## The severity ladder — what triggers what

| Tier | Definition | Action |
|---|---|---|
| **Material error** | A reader now believes something false about what happened, who did it, or a number that matters (wrong actor, wrong amount, wrong action, fabricated-seeming claim) | **CORRECTION quote-post** of the original, promptly |
| **Minor error** | Imprecise but not misleading: typo in a name, rounding, a mislabeled form type where the story stands | **Reply** to the original with the fix — no quote-post (don't amplify a post to fix a comma) |
| **Superseded** | Was true when posted; events moved (deal terms revised, ruling reversed) | **UPDATE post**, new story, links the old one. Not a correction — we weren't wrong |
| **Process fault, content holds** | Wrong class (posted as corroborated when single-source), receipt link imperfect, gate slipped — but the facts stand | Internal only: log it, fix the gate. No public action |

The test for "material": would the reader have understood the story differently? If yes,
correct publicly. When genuinely unsure, correct — eating a marginal correction costs a
little pride; a spotted-but-silent error costs the entire premise of the account.

## The format

CORRECTION posts start with the word and follow the wire's own atom shape:

> CORRECTION: We reported [what we said]. That was wrong. [What is true], per [source].
>
> The original post stands below, uncorrected, per our policy.

- Quote-post the original (never delete it — the policy IS the product).
- The corrected fact gets its receipt link, same as any story.
- No apology theater, no "we deeply regret" — state the error, state the truth, move on.
- UPDATE posts start "UPDATE:" and quote the original the same way.

Minor-error replies: "Correction to this post: [fix]. The story stands."

## Who fires it, and when

Implementation note (reviewed 2026-09-06): the daily receipt self-audit is implemented in
`nbn/audit.py`. It uses the retained Anthropic `NBN_MODEL` path, separate from the Grok editor
and Codex rolling audit. It checks locally logged IMMEDIATE/UNCERTAIN output from the prior
26 hours, reports findings, and stages a single correction draft for material findings.
It does not itself attach the original quote-post, publish the correction, or turn autopost
off. Those policy steps below require owner action or the rolling audit's explicit emergency
OFF authority. The staging path's model usage is not currently in the editorial-seat ledger.

- **Corrections NEVER auto-publish.** Whatever detects the error (Brady, a reader, an
  agent, the daily self-audit), the correction is drafted and staged as a Typefully
  DRAFT titled `CORRECTION: <story>`; Brady taps publish. The standing autopost grant
  covers news that passed the gates — it explicitly does not cover corrections.
- Target latency: within the hour during waking hours; overnight errors are corrected
  first thing, before any new posting resumes. Nothing new publishes over an
  uncorrected material error — the queue holds until the correction is out
  (`NBN_AUTOPOST_ENABLED=false` is the one-flip way to enforce that while drafting).
- A reader who caught it gets acknowledged in a reply to their comment — readers who
  correct the wire are doing free editorial work; thank them plainly.

## Block corrections

A material error inside a Block thread gets the CORRECTION quote-post aimed at the
specific post in the thread that carried the error, not at the index post.

## Record

Every public correction should receive an operator-maintained record linking the original,
correction, reason and publication time. The current daily staging helper only sends the
Typefully draft and logs its result; it does not call `record_post`, append a correction row
to the normal output ledger, or maintain a verified public corrections count. Do not infer
that no corrections exist from an empty Desk count. Preserve evidence for the owner to
complete the record. The goal is not zero corrections issued; it is zero known errors left
uncorrected.
