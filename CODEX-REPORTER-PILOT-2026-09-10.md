# Codex reporter pilot — September 10, 2026

## In progress, not a completed quality evaluation

Fixed window: **12:58:05–2:58:05 PM Central**. Local Mac reporter, Astra medium,
Standard service, dedicated ChatGPT-account login. No API model fallback. Only new
unscheduled Typefully drafts; existing drafts are read-only. Autopost and both old
editorial/audit processes remain off. The original cutoff was not extended by repairs.

Session: `01a08c78-b1fa-70d3-8f3e-ef3c9c1a0920`.
Shift: `pilot-20260910T175805Z`.
Backend release: `533d0f0`, Railway deployment `765a1eda-fd12-43fa-be62-f6b135d6250c`.
Local permission correction: `5429087`.

## Verified readiness

- Independent implementation review approved. Full suite773 tests plus3 runtime-cutoff
  regressions passed; Desk type-check/build passed.
- Dedicated runtime/auth/resume and actual browser/PDF/image checks passed.
- All10 filesystem/network isolation canaries passed after the final configuration
  correction. No personal credentials or desktop account configuration were copied.
- Infrastructure health200, autopostfalse, zero old editorial calls/delivery jobs.
  First collection:528 items,219 new;331 RSS,5 EDGAR,133 X,59 Perception.
  Marketing Node's daily endpoint returned404; direct intake works independently.
- Separate reporter/supervisor credentials verified: unauthenticated and wrong-role
  requests rejected. Twelve backend tools plus the isolated browser initialized.
- Typefully's154 candidate records synchronized read-only, including all eight known
  morning experiment drafts. The current coverage payload is about384KB of JSON.
- Deployed Desk → Codex pilot visually inspected at1728px, HTTP200, no JavaScript errors.

## First-turn integration finding — repaired

The runtime could discover MCP tools but would not execute them: `auto` is not explicit
preapproval under an unattended `never` approval policy. Catalog/configuration tests
alone did not catch this. First turn created no draft and saved a local fallback letter.

Correction, independently reviewed: default `prompt`, an exact13-name tool allowlist,
and per-tool `approve`. The shell/auth/control denials and backend delivery restrictions
are unchanged. The idle supervisor and its verified SDK child were torn down, then the
same session/generation/cutoff resumed after fresh sandbox/config checks. No new shift.
Actual model-initiated context, intake, fetch, note and handoff calls now succeed.

Lesson: future readiness checks must include a real model-initiated read-only tool call,
not merely `tools/list`. The dedicated runtime also needed its already-pinned HTTPX
dependency installed; syntax checks do not prove runtime imports.

## First working research pass

The reporter inspected original Wells Fargo and EIA material and an oil-market lead.
It logged why it deferred or dropped each and saved a useful letter and timed agenda.
It acknowledged both operator messages. No draft was forced from this pass, and real
Typefully creation/media readback is therefore **not yet smoke-confirmed by this pilot**.
The existing delivery regression tests are passing; that is a separate kind of evidence.

Its own workflow feedback: the154-draft embedded coverage snapshot was too large to
scan comfortably and tool display truncated it. It recommended a compact coverage index
with detail lookup. The payload repeats text in the draft-text and platform-post fields.
This is a credible preparation issue to evaluate, not evidence yet of poor model judgment.

After the second completed turn, SDK cumulative usage was2,056,967 input tokens,
1,722,112 cached input tokens, and3,271 output tokens, across the session's model/tool
passes. These are cumulative values, **not per-turn sums** and not API-dollar charges.
Account allowance was13% consumed before the pilot; account totals also include this
development conversation and cannot cleanly attribute the reporter's share.

## Remaining observation

- Confirm automatic same-session wake and follow-through on agenda/new intake.
- Verify the first genuinely useful draft's exact text, source reply, and unscheduled
  Typefully state; verify media pixels/readback if a sensible visual opportunity arises.
- Compare selection, writing, timing and source-following with the manual morning run.
- Watch coverage refresh: distinguish incomplete draft content from deferred comment
  refresh before deciding it must block reporting.
- Confirm fixed cutoff and final handoff. Do not automatically renew the shift or audit.

Do not mistake this interim record for the final two-hour retrospective.
