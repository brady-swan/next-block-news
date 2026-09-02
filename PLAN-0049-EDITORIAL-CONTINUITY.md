# Plan 0049 — Editorial continuity workbench

## Decision

Keep each 15-minute Sonnet desk fresh, but carry bounded, structured story work between
runs. One SQLite workbench per canonical exact event preserves the prior proposed post,
still-eligible inspected evidence, the code-defined missing research objective, and the
independent editor's feedback. It informs the next desk; it is not a hidden publication,
novelty, or suppression gate.

This addresses three production failures without another architecture rewrite:

- unresolved research was discarded and repeated from scratch;
- one event acquired several model-written slug variants; and
- editor feedback was reduced to a terminal item note and could not help a later report.

## Canonical identity

Existing member item keys are resolved through the alias table. One existing canonical
family wins. More than one family is an identity conflict and holds without merging.
With no existing family, Sonnet may select only an exact event key supplied by the coverage
or continuity board; otherwise its normalized proposed key starts the family.

The submitted slug is registered as an alias only after membership and supplied-key
validation. There is no fuzzy automatic merge and a Node theme never becomes an event key.

## Workbench record

`newsroom_story_memory` is keyed by canonical event and expires after 72 hours. It stores:

- up to 12 bounded attempts;
- up to 25 member hashes and three headlines per attempt;
- the proposed post, machine failure, and code-mapped research objective;
- up to eight evidence cards with at most 8 KiB of text each;
- the latest editor verdict/reason/post; and
- the actual Typefully delivery mode, reference, time, and reader-coverage meaning.

The complete serialized row is capped at roughly 96 KiB. Older attempts retain provenance but
not full evidence text. Corrupt, oversized, or expired state fails open.

States (`research_pending`, `editor_feedback`, `delivered`, `dropped`) are descriptive.
They never suppress a new candidate. Only terminal item state and the posts table determine
whether an exact item is done or readers have seen a story. A Typefully `DRAFT` is delivered
to Typefully but is not reader-covered.

## Evidence reuse

Stored evidence remains citable for 24 hours, independent of the 72-hour editorial-memory
window. At load time code verifies its fingerprint, validates and normalizes the public URL,
reclassifies it under current source policy, recomputes eligibility and independence,
deduplicates it, and issues a fresh run-owned `memory_*` fetch ID.

Expired or invalid evidence cannot satisfy a gate. Elevated claims still require an official
artifact or two genuinely independent eligible reports across cached and newly inspected
evidence.

## Fresh desk payload

The clean desk now has a bounded `continuity_board`, prioritized for exact current members
and open research. Each card labels history and editor feedback as untrusted context. Only
revalidated cached evidence with a code-owned fetch ID is factual evidence.

Pending item cards also expose bounded prior story key, note, stage, and category as
untrusted historical context. Sonnet is instructed to reuse sound work, research only the
missing piece, and say “recommended for delivery” rather than claiming publication.

## Editor correction

The independent batch editor now tests apparent conflicts by actor, place/facility, time,
and scope. A newer facility-specific action is not contradicted by an older general statement
of company intent. When current evidence supports a narrower accurate story, revision is
preferred to dropping useful news.

Editor feedback is saved before publisher delivery. Delivery then updates the same workbench
with the actual result.

## Review and rollout

The independent lead coder required explicit conflict behavior, a separate evidence-age
clock, non-gating lifecycle semantics, side-effect-light validation, executable storage
bounds, and a nonpublishing smoke. The amended plan was approved before implementation.

Rollout is an additive `CREATE TABLE IF NOT EXISTS` migration. Autopublish remains off.
Tests cover continuity, identity conflicts, cached corroboration, bounds, corruption,
pruning, Typefully draft semantics, and the editor's scope/time rule. Production smoke must
verify schema/CRUD/packet construction and must not deliberately create a Typefully draft.
