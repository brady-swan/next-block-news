# Nano Banana integration — independent lead review

Date: September 7, 2026 Central.
Plan: `PLAN-0067-NANO-BANANA.md`.
Reviewer: `lead_0066_review` (independent lead coder from Plan 0066).
Scope: planning only. No implementation, provider calls, deployments or production changes.

September 8 owner update: **PARKED** while NBN learns to produce useful original visuals with
its existing tools. The earlier technical approval below is preserved as review history, not
authorization to build. `GEMINI_API_KEY` is saved in Railway per Brady; it remains unused by
this plan. Brady must explicitly reopen implementation.

## Verdict

**APPROVED for Brady's review. No blocking changes.**

The reviewer read the full saved draft and checked the existing writer visual tools,
`visuals.proposal`, and `visual_choices` behavior. This is not authorization to implement.

## Design feedback incorporated

1. Keep generation jobs separate from publisher mutations. Pending images must not reserve
   canonical output or enter `awaiting_media`; doing so would block timely text delivery.
2. Request early, inspect same-run results, and retain late assets for Desk review or a later
   genuine editorial run. Do not build an automatic image-only writer/editor continuation yet.
3. Save the factual brief, evidence, references, prompt/config/model, request identity, provider
   ID, output hash, timing and cost. Unknown paid submissions must not automatically regenerate.
4. Live-test the selected Google image model's background contract at activation. If unsupported,
   place its bounded synchronous request in the isolated image I/O worker, never the writer tool.
5. Actual final pixels are required. Generated art is not a receipt. Existing run/candidate and
   inspection checks remain; cross-run reuse imports and inspects the retained asset properly.
6. Alt text must be written from the returned image, not assumed from the prompt. The plan now
   has a final-alt metadata variant bound to the same inspected pixel hash and editor approval.
7. The generic Desk action currently permits creating a draft when its target is absent. A
   late generated-image selection must explicitly require an existing sole untouched unpublished
   draft at request and execution, with a no-target/disappearing-target regression test.

## Why the reviewer called it ready

The plan separates generation from publication, keeps text delivery timely, represents uncertain
spend honestly, and reuses the existing image-review/delivery system rather than creating a
second newsroom. Remaining provider capability, real image quality and latency questions are
explicit first-phase tests, not claimed production guarantees.

## Current boundary

Only the plan, this review record and its documentation-index entry were added/edited for
this request. No API key was read or installed, no image was generated, and the audit was not
paused. Brady reviews the proposal before any implementation starts.
