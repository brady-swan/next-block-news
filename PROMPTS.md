# Next Block News prompt inventory

This file is an index, not a compiled copy. Prompt text previously lived here as a
snapshot and repeatedly drifted from runtime. Read and edit the sources of truth below.

| Prompt | Source of truth | Used by | Runtime setting |
|---|---|---|---|
| Wire voice charter | `prompts/wire_voice.md` | Injected into triage and drafting | — |
| Run newsroom | `nbn/newsroom.py` (`NEWSROOM_SYSTEM` + strict tools) | One fresh context surveys, researches, judges, and writes a complete intake run | `NBN_MODEL`; `NBN_RUN_NEWSROOM_MODE` |
| Legacy triage | `nbn/brain.py` (`TRIAGE_SYSTEM`) | Feature-off, shadow continuation, or pre-materialization fallback | `NBN_TRIAGE_MODEL` |
| Legacy event identity reconciliation | `nbn/brain.py` (`CLUSTER_SYSTEM`) | Legacy fetched candidates vs. recent event catalog | `NBN_TRIAGE_MODEL` at low effort |
| Legacy single-post drafting | `nbn/brain.py` (`DRAFT_SYSTEM`) | Legacy selected items and one lint retry | `NBN_MODEL` |
| Legacy source resolution | `nbn/verify.py` (`RESOLVE_PROMPT`) | Legacy actionable non-primary receipts | `NBN_MODEL` |
| Provider claim support | `nbn/verify.py` (`CLAIM_SUPPORT_PROMPT`) | One provider-specific redraft | `NBN_MODEL` |
| Legacy publishing editor | `nbn/editor.py` (`EDITOR_PROMPT`) | Gate-passed legacy candidates | `NBN_EDITOR_MODEL`, `NBN_EDITOR_EFFORT` |
| Newsroom support editor | `nbn/editor.py` (`NEWSROOM_EDITOR_PROMPT`) | Independent, fail-closed claim and craft review against the exact selected receipt | `NBN_EDITOR_MODEL`, `NBN_EDITOR_EFFORT` |
| Legacy Block thread | `nbn/briefing.py` (`BRIEFING_PROMPT`) | Disabled rollback/experiment path | `NBN_MODEL` |
| Daily audit | `nbn/audit.py` (`AUDIT_PROMPT`) | Receipt and class verification | `NBN_MODEL` |

Prompts do not define the final publishing boundary. Deterministic vetoes and routing
live in:

- `nbn/main.py`: freshness, event age, source tier, corroboration, class routing.
- `nbn/lint.py`: scope, copy, URLs, mentions, attribution, and numeric integrity.
- `config/source_tiers.toml` + `nbn/source_policy.py`: canonical tiers, aliases, ownership,
  domain/handle normalization, and receipt eligibility.
- `nbn/verify.py`: candidate support, originality, independent evidence, and provider claims.
- `nbn/briefing.py`: receipt allowlist and Swan-reference exclusion for Blocks.
- `nbn/config.py`: master autopost switch and allowed classes; `secondary` is removed
  from `NBN_AUTOPOST_CLASSES` in code.

The run newsroom receives a curated desk, not persisted records verbatim. Its
`run_brief`, `intake_board`, `reference_board`, exact-event `coverage_board`, broad
`theme_board`, and verified-handle directory explicitly separate tips, uninspected
pointers, historical coverage, and advisory context. Raw Node envelopes and unknown
discovery fields are not passed through. Every candidate retains one stable ID and must
be accounted for in both the opening survey and terminal dossier.

The same Sonnet message history moves through forced `submit_survey`, bounded research
tools, `finish_research`, and forced `submit_newsroom_dossier`. Search results are pointers;
only NBN-generated `fetch_id` records can be cited as evidence. A valid dossier can receive
one post-only lint repair in that same context. Sonnet may propose exact-event membership,
receipt support, and copy, but code reconstructs provenance, checks identity, applies
freshness/novelty/source/lint gates, and routes delivery. Fable independently checks every
final factual assertion against the exact selected receipt and fails closed for newsroom
output.

Triage receives optional Node theme activity plus NBN's bounded recent coverage snapshot.
Both are advisory, untrusted context. Runtime instructions explicitly prohibit treating a
theme as evidence, corroboration, same-event identity, a quota, or a reason to lower a gate;
`coverage_known=false` means historical tagging is incomplete. The identity prompt receives
theme IDs only to state that a broad shared theme is insufficient to merge story keys.

The identity clerk is the only component that may propose an event-key alias. Its closed
event-type conflict guard can veto a proposal. When
`NBN_YIELD_IDENTITY_NORMALIZER_ENABLED=true`, the prompt may propose only the demonstrated
same-day U.S. 10-year Treasury-yield threshold family; deterministic code then requires
the exact instrument/date/direction/percent unit and a reading within 0.10 percentage
point. Code never turns a clerk `distinct` result into a merge.

Triage and Writer read guide examples through the versioned `guide-signal-v1` namespace
(with legacy-read compatibility). Guide prose is an attention/format example only. It is
never supplied as factual authority, and omitted-verdict recovery can route a substantive
claim to research or a non-claim to visible hold, but cannot establish support.

When a prompt changes, update its runtime source directly, add a regression case for the
behavior where practical, and observe one complete live cycle after deployment as
described in `HANDOFF-CODEX.md`.
