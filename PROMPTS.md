# Next Block News prompt inventory

This file is an index, not a compiled copy. Prompt text previously lived here as a
snapshot and repeatedly drifted from runtime. Read and edit the sources of truth below.

| Prompt | Source of truth | Used by | Runtime setting |
|---|---|---|---|
| Wire voice charter | `prompts/wire_voice.md` | Injected into triage and drafting | — |
| Triage | `nbn/brain.py` (`TRIAGE_SYSTEM`) | Each pending-item batch | `NBN_TRIAGE_MODEL` |
| Single-post drafting | `nbn/brain.py` (`DRAFT_SYSTEM`) | Each item selected for drafting and one lint retry | `NBN_MODEL` |
| Source resolution | `nbn/verify.py` (`RESOLVE_PROMPT`) | Actionable non-primary receipts | `NBN_MODEL` |
| Provider claim support | `nbn/verify.py` (`CLAIM_SUPPORT_PROMPT`) | One provider-specific redraft | `NBN_MODEL` |
| Publishing editor | `nbn/editor.py` (`EDITOR_PROMPT`) | Gate-passed autonomous candidates | `NBN_EDITOR_MODEL`, `NBN_EDITOR_EFFORT` |
| Block thread | `nbn/briefing.py` (`BRIEFING_PROMPT`) | Weekday Morning/Afternoon Blocks | `NBN_MODEL` |
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

When a prompt changes, update its runtime source directly, add a regression case for the
behavior where practical, and observe one complete live cycle after deployment as
described in `HANDOFF-CODEX.md`.
