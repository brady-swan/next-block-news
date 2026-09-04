# Plan 0055 — Editorial calibration and owner-feedback loop

**Status:** Owner-approved and independently reviewed. Approved for implementation.

## Objective

Turn the accumulated editorial evidence into a small, coherent calibration pass:

1. select fewer Bitcoin-adjacent finance stories that are too small for the feed;
2. put the Bitcoin-relevant consequence ahead of procedure and background;
3. make final copy materially easier to scan through simpler sentences and better rhythm;
4. let future audit passes read Brady's Typefully comments without granting Typefully write access;
5. preserve the faster, more decisive newsroom behavior achieved in Editorial v2.9.

This is an editorial-calibration sprint, not another architecture sprint.

## Evidence being consolidated

### Direct owner feedback

- Typefully `10625995`, Druckenmiller/Duquesne miner equities: do not post; the story is too
  small for NBN. A famous investor plus indirect Bitcoin exposure does not create sufficient
  importance.
- Typefully `10626036`, Trump/Fed/trade: the selected paragraph contains two long sentences that
  should be separated. The issue is sentence construction and presentation, not a request to
  drop the story.
- Typefully `10622958`, CLARITY calendar: worthwhile and fast, but the Bitcoin consequence was
  buried behind the procedural mechanism.
- Typefully `10621265`, Norway sovereign-fund allocation: accurate and polished, but too small and
  indirectly related to Bitcoin.
- Typefully `10620908`, ETF flows: good post, but recurring primary/near-primary data should reach
  the wire earlier.

### Repeated audit pattern

The same density problem appears in the Ireland savings-wrapper, Hyperscale, Ledger, Coldcard,
Cornell adoption, and `$81,000` drafts. White space improved, but Sonnet frequently preserves too
much of the research memo inside the final post. Paragraphs often contain one or two sentences
that each carry attribution, event, mechanics, chronology, numbers, and qualification.

A rough read-only sample of the 15 most recently edited Typefully drafts contained 90 sentences.
About 39 were at least 24 words, with individual sentences reaching roughly 44 words. These are
diagnostic observations, not proposed limits or publishing gates.

### What is already working

- Detection and first-intake speed are generally strong.
- Guide-account leads now convert more reliably.
- The Trezor/ShipMonk and Standard Chartered drafts show good ledes and useful copy.
- The editor made a strong substantive call on CLARITY.
- Recent output continuity and draft replacement now address duplicate event outputs.

The sprint must not make the desk timid again.

## Editorial decisions

### 1. Teach selection at the actual failure boundary

Add one narrow selection lesson rather than expanding a general prohibition:

> A famous investor, a large portfolio, or exposure through Bitcoin-linked equities does not by
> itself make a Bitcoin story. A small 13F allocation, portfolio rebalance, or subsequent
> mark-to-market is general investing coverage unless it materially changes a major Bitcoin
> business, signals adoption at meaningful scale, or changes the reader's understanding of the
> Bitcoin system. Do not manufacture Bitcoin relevance from indirect exposure.

This reinforces the existing generic-macro rule without suppressing major monetary events,
material miner operations, or direct Bitcoin adoption.

### 2. Separate research depth from output depth

Add this principle to the production orientation:

> Write selectively. The final post is not a transcript of the desk's work.
> Every detail may be true and still not belong. Keep the facts that establish the change, its
> scale, and the minimum context a Bitcoin reader needs. A research memo proves you looked; wire
> copy proves you chose.

This is the central correction. The model should retain broad context internally while producing
the smallest useful public version.

### 3. Strengthen the scannability guidance without a mechanical style gate

Replace the current abstract paragraph with more operational guidance:

> **Write for the scan.** Put the news in the opening sentence. If procedure caused the news,
> lead with the consequence that matters to a Bitcoin reader and explain the procedure next.
>
> Default to one main fact per sentence and one clear job per paragraph. A paragraph may contain
> two sentences when both are short and naturally connected. If one sentence is long or
> clause-heavy, let it stand alone and make the next sentence short. Never stack two sentences
> that both ask the reader to hold several actors, numbers, dates, or qualifications at once.
>
> Split any sentence carrying the event, attribution, mechanism, chronology, and qualification
> together. Prefer a clean period to another em dash, parenthesis, or dependent clause. Keep an
> occasional longer sentence when the ideas genuinely belong together; the goal is readable
> rhythm, not staccato copy.
>
> Blank lines expose structure; they do not create it. If every paragraph is still a dense block,
> cut secondary detail. Small stories should normally end after the lede and one useful context
> sentence.

Add one compact before/after example based on the Typefully comment. It will demonstrate the
pattern without turning word count into a rule:

> **Dense:** One sentence reports the triggering event, embeds three numbers, quotes the actor,
> explains the rationale, and adds a separate policy threat; the next sentence adds another
> multi-clause interpretation.
>
> **Better:** State the triggering fact. Give the quote or response its own sentence. Put the
> separate policy action in a new paragraph, then stop when the reader has the change and why it
> matters.

Do not add a deterministic word-count, sentence-count, paragraph-count, or readability veto.

### 4. Put the verified source in the first reply

Change every new one-off Typefully delivery from one X post containing copy plus a URL to an exact
two-post thread:

1. the clean news post, with no URL;
2. `Source: <verified receipt URL>` as the immediate first reply.

This is an output-format change, not an evidence-policy change. The receipt remains mandatory and
must be the exact selected URL. Images, when present, stay on the lead post. The local `posts` row
continues to store the clean body and receipt separately.

The exact two-post thread must be used for mutation fingerprints, ambiguous-create reconciliation,
duplicate protection, draft replacement, tape rendering, tests, and Typefully confirmation. Do not
restore the old linkless fallback or permit a retry that changes the authorized thread.

Existing open drafts created in the old single-post inline-link format are not rewritten merely to
migrate formatting. If new same-event evidence targets one, the replacement path must compare the
actual remote shape and fail closed/retain it unless it can prove an exact safe edit. New drafts
created after deployment use the two-post shape and can subsequently be replaced in place while
preserving non-text fields and comment markers. Scheduled, publishing, published, human-edited, or
comment-marked drafts remain immutable.

Recent-reader and novelty memory should contain the news body, not the source-reply boilerplate.
Receipt replies must not be mistaken for separate NBN stories or counted as separate editorial
outputs. Typefully's draft ID remains the unit for publication reconciliation and speed tracking.

### 5. Make the editor perform a real compression pass

Update the independent editor's permitted operations from “cut, reorder, merge, sharpen” to
“cut, reorder, split, simplify, and sharpen.” The editor should explicitly:

- revise rather than merely note back-to-back complex sentences;
- split overloaded sentences without adding facts;
- remove source-shaped detail that does not change the reader's picture;
- lead with the Bitcoin consequence when procedure is only the mechanism;
- spike famous-investor/indirect-equity stories that remain too small after compression;
- preserve strong concise drafts rather than rewriting them for taste.

This stays model-judged. Density becomes a reason to revise, not a code-owned rejection condition.

### 6. Keep examples compact in production

Continue using `prompts/orientation-examples.md` as the full evidence archive, and append the two
new Typefully comments with the relevant draft excerpts and reusable lessons.

Do **not** inject the 1,700+ line archive into every Sonnet call. Put only the distilled principles
and one compact structural example in the cached orientation/editor prompts. This preserves the
value of the archive without recreating the recent context-cost problem.

## Typefully feedback access

Typefully's official v2 API exposes draft comment threads, including selected text, author,
timestamp, resolution status, and full comments. Add a small read-only client/helper that:

- inspects at most 30 recent drafts, at most two comment pages per draft, 50 threads per page,
  100 comment threads total, and 20 comments per thread;
- emits at most 1,000 characters of selected text, 2,000 characters of each comment, and 120
  characters of each author field, along with draft ID and timestamp;
- lists unresolved or all comment threads using only validated draft IDs, validated status values,
  and integer limit/offset parameters. Pagination reconstructs the configured Typefully endpoint;
  it never follows a response-supplied `next` URL;
- requests draft text with `exclude_comment_markers=true` for display only through a separate read
  path. The marker-preserving `get_draft` used by replacement must retain its existing semantics;
- never creates, edits, resolves, or deletes comments;
- never feeds comments into the newsdesk as story evidence or prompt instructions.

For now, this helper is for Codex/audit inspection and editorial-example collection. It does not
grant the rolling audit permission to modify code or production; that autonomy change remains a
separate step after this deck-clearing sprint.

The existing draft-replacement rail must continue to freeze any comment-marked Typefully draft.

Reference: [Typefully API — Comments](https://typefully.com/docs/api#tag/comments)

## Files expected to change

- `prompts/orientation-brief-v2.md` — selection, lede hierarchy, research/output separation, and
  stronger sentence-rhythm guidance.
- `prompts/orientation-examples.md` — archive the two new owner comments and batch synthesis.
- `nbn/editor.py` — compression authority and explicit craft pass for both single and batch editor
  prompts.
- `nbn/publisher.py` / `nbn/publisher_typefully.py` — exact two-post source-reply materialization,
  fingerprinting, replacement compatibility, and read-only comment-thread helpers.
- `scripts/typefully_feedback.py` — bounded, sanitized owner/audit inspection command.
- Focused tests for prompt contracts, comment pagination/normalization, read-only behavior, and
  preservation of comment-marked draft protection.
- `SYSTEM.md` / `PROMPTS.md` only where needed to describe the resulting behavior accurately.

No database schema, source list, corroboration policy, model, cadence, canonical output-continuity
policy, autopost setting, or Node contract should change.

## Evaluation before deployment

### Static and unit verification

- Assert both writer and editor receive the new selection and scannability guidance.
- Assert no new deterministic readability gate exists.
- Assert new one-offs are exactly `[news body, "Source: <receipt>"]`, with media attached only to
  the first post, and that fingerprints/reconciliation cover both posts.
- Assert a successful create is one Typefully draft/thread and one local editorial output—not two
  stories—and that autopost off/on differ only in scheduling state.
- Assert old inline-link drafts are retained rather than duplicated or destructively migrated;
  new two-post drafts replace in place only after exact remote comparison. Preserve all ambiguity,
  comment-marker, human-edit, and non-editable-state protections from Plan 0054.
- Assert publisher mutations persisted before deployment reconcile against their stored desired and
  prior fingerprints plus the actual remote thread shape. Never recompute those fingerprints with
  the new formatter. Cover a pre-deployment one-post inline-link mutation and a post-deployment
  two-post mutation.
- Require direct create confirmation for both staged drafts and scheduled/autopost outputs: after
  Typefully returns an ID, read that exact draft and verify the ordered X text is precisely
  `[news body, "Source: <receipt>"]` before finalizing the local mutation. A missing, reordered, or
  changed reply is uncertain and remains protected from automatic retry. Scheduled confirmation
  must establish both the exact content and the accepted publishing state.
- Test Typefully comment listing for unresolved/all filters, pagination bounds, malformed payloads,
  authorization/rate-limit failures, every configured cap, malicious or malformed response `next`
  URLs, and zero write requests.
- Retain the existing test that comment-marked drafts cannot be automatically replaced.
- Run the full NBN suite, focused Ruff checks, compile checks, and `git diff --check`.

### Small editorial shadow set

Run the proposed prompts against a bounded, non-publishing six-item fixture:

1. Druckenmiller miner-equity allocation — expected drop as too small/indirect.
2. Trump/Fed/trade paragraph — expected split/simplification, not an inferred story rejection.
3. Coldcard update — expected preservation of the event with materially shorter sentences.
4. Cornell adoption finding — expected finding-first copy and methodology second.
5. CLARITY calendar — expected Bitcoin consequence before House procedure.
6. Trezor/ShipMonk — expected preservation or light trim, proving the editor does not rewrite good
   copy merely to satisfy a style preference.

The shadow run is qualitative evidence for owner review, not a deterministic model test and not a
Typefully submission.

## Review and rollout

1. Brady reviews and edits this plan, especially the exact editorial language. **Complete.**
2. Run the independent lead-coder review cycle. The reviewer should challenge
   scope, prompt duplication, comment-API safety, source-reply/legacy-draft compatibility, mutation
   idempotency, tests, and whether any proposal recreates brittle gates. Iterate until approved.
   **Complete: approved after adding executable comment-reader bounds, persisted-mutation
   compatibility, exact create read-back, and independent rollback units.**
3. Implement as three small commits: editorial calibration; Typefully source-reply compatibility;
   read-only Typefully feedback support.
4. Run the full verification and shadow set. Report the shadow outputs before deployment if they
   reveal a material editorial tradeoff not settled by this plan.
5. Deploy with `NBN_AUTOPOST_ENABLED=false`; do not publish, resolve comments, or edit existing
   Typefully drafts during smoke testing.
6. Confirm `/health`, `/status`, one natural newsroom run, editor behavior, Typefully reconciliation,
   and that comment-marked drafts remain protected.
7. Keep the existing read-only rolling audit active and watch the next natural batch for selection,
   lede hierarchy, sentence rhythm, unnecessary detail, speed, and cost.

## Rollback

- Revert the editorial-prompt commit if the desk becomes choppy, thin, or overly reluctant.
- Revert the comment-helper commit independently; it owns no persistent production state.
- If the source-reply commit is rolled back independently, retained Plan 0054 reconciliation must
  continue to recognize stored two-post fingerprints and safely retain remote two-post drafts. It
  must never create an old-format duplicate merely because the formatter changed.
- No database restoration or Node rollback should be required.
