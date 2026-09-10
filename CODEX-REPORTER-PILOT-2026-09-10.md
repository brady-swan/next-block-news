# Codex reporter pilot — September 10, 2026

## In progress, not a completed quality evaluation

Fixed window: **12:58:05–2:58:05 PM Central**. Local Mac reporter, Astra medium,
Standard service, dedicated ChatGPT-account login. No API model fallback. Only new
unscheduled Typefully drafts; existing drafts are read-only. Autopost and both old
editorial/audit processes remain off. The original cutoff was not extended by repairs.

Session: `01a08c78-b1fa-70d3-8f3e-ef3c9c1a0920`.
Shift: `pilot-20260910T175805Z`.
Backend release: `5951548`, Railway deployment `cce5c25a-d954-4788-85ae-9111e8246291`.
Local permission correction: `5429087`.

## Verified readiness

- Independent implementation review approved. Full suite778 tests passed, including
  runtime-cutoff and coverage-refresh regressions; Desk type-check/build passed.
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

After the third completed turn, SDK cumulative usage was4,390,102 input tokens,
3,917,952 cached input tokens, and5,712 output tokens, across the session's model/tool
passes. These are cumulative values, **not per-turn sums** and not API-dollar charges.
Account allowance was13% consumed before the pilot; account totals also include this
development conversation and cannot cleanly attribute the reporter's share.

## Second working pass and integration observations

The next automatic wake inspected Liquid Explorer's18:09UTC original reserve snapshot
and actual chart pixels. It saved an optional dated update for existing draft10708508,
not a duplicate draft or a claim of a newly discovered loss. It noticed the one-block
discrepancy between the text and image. Existing Typefully copy was not changed.

It also followed a TFTC tip to Anthropic's original threat report, but deferred a possible
privacy story because the fetch ended before the relevant surveillance section. This
is a concrete follow-through test for the next pass, not a proved missed story yet.

Two integration defects were identified:

- The Typefully refresh budget treated postponed comment reads like missing draft
  copy. Independently reviewed repair5951548 separates these: comments_deferred is
  visible, while actually unread changed copy still blocks. Live smoke passed.
- The reporter's MCP child did not inherit the browser installation path. The browser
  failed despite the standalone compatibility check; source_image plus actual image
  inspection worked as a fallback. A constant dedicated-browser-path fix passed a
  filtered-environment stdio smoke and independent review. Installed and resumed at
  18:29UTC after the fourth turn completed: same shift/session/generation/cutoff.
  All10 isolation checks and effective configuration checks passed again. The installed
  MCP subprocess returned real text and image with its ambient browser-path variable
  absent. No ambient credential forwarding is needed. Durable operator message73
  tells the reporter it can use the repaired tool at its next natural boundary.

A broad X query returned a provider HTTP error while exact-post reads succeeded.
The cause is not yet established. The generic bridge error gives the reporter too
little diagnostic information to adapt its query; record this for follow-up.

After three turns, the last context measured242,510 of258,400 tokens. Reinjecting the
entire154-draft record set every wake is demonstrably bulky. A compact coverage index
and on-demand exact copy are a strong next adjustment, not a reason to silently change
the pilot mid-run. At that checkpoint, no new Typefully draft had yet been submitted.

## First new draft — delivery smoke confirmed

At18:37:26UTC the reporter created unscheduled Typefully draft10713155, about Mark
Zandi's estimate of the Iran war's effect on household energy costs. Its first post
has three short paragraphs: the attributed$115b estimate, the$860-per-household
average, and clarification that this covers more than gasoline. The source is the
Fox Business original interview article, placed in the first reply.

The operator independently read the exact draft through Typefully: status=draft,
scheduled_date=null, published_at=null, intended body and source reply present.
Thus actual create-only delivery is now confirmed, not just tested with mocks.
No attached image in this draft; actual media attachment remains untested by this
live pilot, separate from successful source-image inspection and renderer tests.

The repaired browser was also used by the reporter itself: Treasury's dynamic table
and a timestamped CNBC30-year quote returned text and actual screenshots. Its feedback
identifies a remaining browser-tool limitation: it returns body text but not the table's
outbound document URLs. It still could not read the relevant Anthropic section; the
original PDF exceeded the retained10MiB parser cap. These are specific tool-design
observations to evaluate, not evidence that more instruction warnings are needed.

## Owner-requested queue cleanup during the experiment

At18:29–18:30UTC Brady explicitly authorized downloading older Typefully drafts and
deleting them if no archive operation exists. The operator exported132plain unscheduled
drafts created AND edited before midnightCentral September10, including55comment
threads and one attached image, with checked content hashes. Today's work and all
other statuses were excluded. The reporter was held after its18:38completed turn
while deletion and exact-ID reconciliation ran. All132deletions were confirmed by404;
final inventory preserves the original57items plus the pilot's new draft:23drafts,
35published. Three explicit synchronization passes cleared the remaining stale open
records. Current reporter desk JSON fell to49,549bytes from about384KB. Worker62140
resumed the SAME shift/thread/generation around18:47UTC; original19:58:05UTC cutoff
unchanged. Durable message98 records the cleanup and independent delivery confirmation.
Local archive and verified ZIP are in the main task workspace's archives directory.

This intervention changes the size of the next desk payload and must be accounted for
when interpreting the experiment. The reporter was explicitly told that queue cleanup
does not make old events new or authorize recreating those archived stories.

## Remaining observation

- Automatic same-session wake is confirmed; continue observing agenda follow-through.
- First new draft text/source/unscheduled readback is confirmed; verify attached media
  pixels/readback if a sensible visual opportunity arises.
- Compare selection, writing, timing and source-following with the manual morning run.
- Watch the deployed coverage-refresh repair and actual browser use after local repair.
- Confirm fixed cutoff and final handoff. Do not automatically renew the shift or audit.

Do not mistake this interim record for the final two-hour retrospective.
