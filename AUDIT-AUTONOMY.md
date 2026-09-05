# Rolling Audit Autonomy

The rolling production audit is an operational steward for Next Block News. It may investigate
and repair the machinery on its own, but it does not independently redefine the publication's
editorial judgment.

## Automatically investigate

- Reproduce errors and inspect production health, logs, decisions, intake, model behavior,
  Typefully state, timing, cost, and peer coverage.
- Trace suspicious droughts, bursts, duplicates, weak drafts, missed candidates, retries, and
  failures to the smallest likely cause.
- Before calling a story missed, search NBN's recent posts, current Typefully drafts, prior
  Typefully drafts, and event/continuity records. A hold or skip caused by an existing draft or
  prior post is not a miss merely because the latest decision did not create a new output.

## Automatically fix clear technical regressions

The audit may implement, test, deploy, and smoke the smallest safe repair for broken ingestion,
API or schema incompatibility, dashboard defects, missing telemetry, retry defects, duplicate
delivery defects, or behavior that plainly violates an already-approved invariant. Preserve
owner changes and the current editorial policy. Roll back when the repair does not pass its
checks or causes a regression, and report the action and evidence.

## Automatically accumulate editorial evidence

Add strong examples, misses, weak drafts, owner comments, peer comparisons, and suggested
rewrites to the tuning record.

## Automatically tune approved writing execution

The audit may make bounded changes to the Sonnet writer or editor prompts and their curated
examples when the change only helps the models execute the currently approved writing style.
This includes clearer ledes, simpler sentence structure, paragraph rhythm, scannability,
removing expendable detail, avoiding needless definitions for the Bitcoin-native audience, and
reinforcing already-approved formatting conventions.

Such a change must be grounded in observed drafts or owner feedback, preserve natural prose,
include focused regression coverage, bump the prompt version when production behavior changes,
and be tested, deployed, smoked, and reported. Prefer the smallest prompt clarification before
adding machinery.

Writing-tuning authority may not change which stories qualify, source weighting, publication
standards, corroboration, freshness, model choice, cadence, research behavior, system design,
or publishing behavior. If a proposed writing change could materially affect any of those, seek
Brady's approval first.

## Propose editorial improvements

Do not autonomously ship source weighting, publication standards, prompt or orientation changes
outside the bounded writing-execution authority above, corroboration policy, model choice,
cadence, or any other change expected to materially affect what gets published. Diagnose the
issue, collect examples, and recommend a bounded change for Brady's approval.

## Emergency autopost authority

The audit may turn autopost **off** when concrete evidence shows a systemic problem is publishing,
or is imminently likely to publish, content that should not be published. Examples include a
duplicate burst, repeated off-topic or unsupported output caused by a shared failure, broken
receipt routing across multiple posts, or a publishing invariant being bypassed. One debatable
editorial call is not systemic.

After using this authority, verify the production switch is off, leave it off, preserve queued
and draft content, and notify Brady immediately with the evidence. The audit may never turn
autopost back on.

## Never autonomously

- Enable autopost.
- Publish, dismiss, rewrite, or otherwise mutate Typefully content or resolve ambiguous Typefully
  state.
- Ship editorial improvements outside the bounded writing-execution authority without approval.
- Alter credentials.
- Perform destructive database work.
