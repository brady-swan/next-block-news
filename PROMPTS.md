# Next Block News prompt inventory

This file is an index, not a compiled copy. Prompt text previously lived here as a
snapshot and repeatedly drifted from runtime. Read and edit the sources of truth below.

| Prompt | Source of truth | Used by | Runtime setting |
|---|---|---|---|
| Wire voice charter | `prompts/wire_voice.md` | Injected into triage and drafting | — |
| Run newsroom | `nbn/newsroom.py` (`NEWSROOM_V2_SYSTEM` + strict tools) | One fresh context surveys, researches, judges, and writes a complete intake run | `NBN_MODEL`; `NBN_RUN_NEWSROOM_MODE` |
| Legacy triage | `nbn/brain.py` (`TRIAGE_SYSTEM`) | Feature-off, shadow continuation, or pre-materialization fallback | `NBN_TRIAGE_MODEL` |
| Legacy event identity reconciliation | `nbn/brain.py` (`CLUSTER_SYSTEM`) | Legacy fetched candidates vs. recent event catalog | `NBN_TRIAGE_MODEL` at low effort |
| Legacy single-post drafting | `nbn/brain.py` (`DRAFT_SYSTEM`) | Legacy selected items and one lint retry | `NBN_MODEL` |
| Legacy source resolution | `nbn/verify.py` (`RESOLVE_PROMPT`) | Legacy actionable non-primary receipts | `NBN_MODEL` |
| Provider claim support | `nbn/verify.py` (`CLAIM_SUPPORT_PROMPT`) | One provider-specific redraft | `NBN_MODEL` |
| Legacy publishing editor | `nbn/editor.py` (`EDITOR_PROMPT`) | Gate-passed legacy candidates | `NBN_EDITOR_MODEL`, `NBN_EDITOR_EFFORT` |
| V2 batch editor | `nbn/editor.py` (`BATCH_EDITOR_PROMPT`) | Independent source-sufficiency, support, novelty, selection, compression, and craft judgment over all inspected receipts; one omitted-only recovery is permitted | `NBN_EDITOR_MODEL`, `NBN_EDITOR_EFFORT` |
| Legacy Block thread | `nbn/briefing.py` (`BRIEFING_PROMPT`) | Disabled rollback/experiment path | `NBN_MODEL` |
| Daily audit | `nbn/audit.py` (`AUDIT_PROMPT`) | Receipt and class verification | `NBN_MODEL` |

V2 prompts own editorial judgment; code supplies a deliberately small mechanical boundary:

- `nbn/main.py`: inspected-ID integrity, exact-delivery idempotency, lease, kill-switch, and
  Typefully lifecycle routing.
- `nbn/lint.py`: empty/long copy, embedded URLs, unsupported verbatim quotes, verified mentions,
  and investment instructions. Scope/style/number concerns are editor warnings in v2.
- `config/source_tiers.toml` + `nbn/source_policy.py`: canonical tiers, aliases, ownership,
  domain/handle normalization, and receipt eligibility.
- `nbn/verify.py`: candidate support, originality, independent evidence, and provider claims.
- `nbn/briefing.py`: receipt allowlist and Swan-reference exclusion for Blocks.
- `nbn/config.py`: master autopost switch and allowed delivery classes.

The run newsroom receives a curated desk, not persisted records verbatim. Its
`run_brief`, `intake_board`, `reference_board`, exact-event `coverage_board`, broad
`theme_board`, and verified-handle directory explicitly separate tips, uninspected
pointers, historical coverage, and advisory context. Raw Node envelopes and unknown
discovery fields are not passed through. Every candidate retains one stable ID and must
be accounted for in both the opening survey and terminal dossier.

The same Sonnet message history uses bounded search/fetch tools and ends with a strict
`submit_newsroom_dossier`. Search results are pointers; only NBN-generated `fetch_id` records
can be cited. Code validates structural IDs and reconstructs provenance, while the batch editor
may use all inspected receipts together. Source sufficiency, corroboration, semantic novelty,
freshness, numerical materiality, scope, and importance are model judgments, not post-model
code vetoes. Unsupported verbatim quotation remains a hard rail both before and after editing.
The production orientation explicitly separates research depth from output depth: write
selectively, lead with the Bitcoin-relevant consequence, split overloaded sentences, and do not
manufacture Bitcoin importance from a famous investor's small indirect equity exposure.

Cross-run continuity is a bounded evidence pool and attempt/editor workbench, not an immortal
model conversation. SerpAPI also has a per-run failure circuit so search outages do not consume
the desk's research budget repeatedly.

The newsroom must declare `coverage_relation` (`distinct`, `same_event`, or `material_update`);
code—not prompt prose—enforces the resulting one-active-output Typefully invariant.

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
