# Next Block News prompt inventory

This file is an index, not a compiled copy. Prompt text previously lived here as a
snapshot and repeatedly drifted from runtime. Read and edit the sources of truth below.

| Prompt | Source of truth | Used by | Runtime setting |
|---|---|---|---|
| Wire voice charter | `prompts/wire_voice.md` | Injected into triage and drafting | — |
| Triage | `nbn/brain.py` (`TRIAGE_SYSTEM`) | Each pending-item batch | `NBN_TRIAGE_MODEL` |
| Single-post drafting | `nbn/brain.py` (`DRAFT_SYSTEM`) | Each item selected for drafting and one lint retry | `NBN_MODEL` |
| Corroboration | `nbn/verify.py` (`VERIFY_PROMPT`) | Secondary stories and detector tips | `NBN_MODEL` |
| Publishing editor | `nbn/editor.py` (`EDITOR_PROMPT`) | Gate-passed autonomous candidates | `NBN_EDITOR_MODEL`, `NBN_EDITOR_EFFORT` |
| Block thread | `nbn/briefing.py` (`BRIEFING_PROMPT`) | Weekday Morning/Afternoon Blocks | `NBN_MODEL` |
| Daily audit | `nbn/audit.py` (`AUDIT_PROMPT`) | Receipt and class verification | `NBN_MODEL` |

Prompts do not define the final publishing boundary. Deterministic vetoes and routing
live in:

- `nbn/main.py`: freshness, event age, source tier, corroboration, class routing.
- `nbn/lint.py`: scope, copy, URLs, mentions, attribution, and numeric integrity.
- `nbn/verify.py`: confirming-domain independence and aggregator exclusions.
- `nbn/briefing.py`: receipt allowlist and Swan-reference exclusion for Blocks.
- `nbn/config.py`: master autopost switch and allowed classes; `secondary` is removed
  from `NBN_AUTOPOST_CLASSES` in code.

When a prompt changes, update its runtime source directly, add a regression case for the
behavior where practical, and observe one complete live cycle after deployment as
described in `HANDOFF-CODEX.md`.
