# Preserve the scope of a reported statistic

September 7, 2026. Bounded reporting/writing execution tuning under AUDIT-AUTONOMY.md.
Status: deployed and smoked; audit resumed. No editorial-policy or publication-state change.

## Evidence

Normal Typefully draft 10668646 (17:48:45 UTC) says $1 billion entered Bitcoin investment
products in the week to September 4. Both the supplied Cointelegraph capture and the actual
[CoinShares September 4 update](https://coinshares.com/us/insights/research-data/market-update-04-09-2026/)
describe flows across digital-asset investment products, not a Bitcoin-only subtotal. The
writer narrowed the universe while making the story Bitcoin-relevant; the editor retained it.
This changes the claim and is not harmless rounding. The research source is three days old;
that freshness/craft judgment is recorded separately, not a new date cutoff in this change.

The correct broader category was already in the editor's evidence. More search, a primary-only
rule, or code checking exact numbers would not address this execution mistake. The primary
receipt itself is useful progress, but a linked original does not validate every copied noun.
Audit GET confirms the incorrect wording is still in the draft. Do not mutate or publish it.

## Proposed small change

Add matching short guidance to the active writer's final writing pass and the batch editor:

> Keep each statistic's scope, unit and reporting period intact when focusing a story on Bitcoin.
> An all-digital-asset product-flow total is not a Bitcoin-only total. Use the source's category
> or an explicitly reported Bitcoin subtotal; correct the wording rather than discard useful news.

This clarifies existing accuracy/materiality requirements. No new evidence requirement, quota,
deterministic metric gate, model call, model/effort/cadence/budget change or orientation rewrite.
Version the writer prompt and update current prompt/system docs. Add a focused offline regression
asserting both active seats receive the guidance while the practical-rounding allowance remains.

Independent review first; then full tests, clean deployment and read-only smoke. Keep autopost
OFF and the existing draft untouched. Restore the same audit after the build pause. Do not call
static prompt assertions proof of improved model behavior; subsequent natural samples must show it.

Rollback is preceding runtime `d299365`; no database restore or publisher mutation is needed.

## Independent review

The independent lead reviewer approved the plan as written: this is an accuracy clarification,
not stricter corroboration or new coverage policy. Both active prompts must carry it, the
practical-rounding allowance must remain, and the current draft must stay untouched. Static
tests confirm delivery of guidance; natural subsequent output must establish behavioral effect.

The implementation review approved deployment without blockers and independently ran the 40
editorial-v2 tests. Main-agent full working-tree suite passed **519 tests**; unrelated evaluator
changes remain outside this release. Active version: `editorial-core-v2.20-metric-scope`.

## Release preparation

- Code commit `1d49c2a`, pushed to main; deployment uses its clean git archive, not the dirty workspace.
- Clean-archive full suite: **517 tests passed**. The two additional working-tree tests belong
  to unrelated evaluator work and were not shipped.
- Online backup integrity check passed: `/data/backups/nbn-pre-source-policy-20260907T182146Z.db`.
- Last pre-deploy newsroom run was completed and autopost was OFF; no forced model replay.
- Expected cost change is only the short added instruction within existing writer/editor
  calls. No new calls, tools, model settings, budgets or cadence. Exact token/billing delta is
  not separately measured. No claim of improved future decisions from static tests alone.

## Production verification

Railway deployment `d68c5293-72e8-4d2b-8560-91951690b4af` is SUCCESS, running code `1d49c2a`.
Read-only smoke at **18:25:10 UTC** verified:

- Active `editorial-core-v2.20-metric-scope`; writer and editor both contain the reviewed guidance.
- The editor's practical-rounding allowance remains present.
- Writer/editor/main/orientation file hashes exactly match the clean release archive.
- Public health, local health/status, all four Desk pages and all four workspace APIs return 200.
- Natural worker cycles continue without a recorded error; autopost is OFF.
- Grok 4.3 medium writer, Grok 4.5 medium editor, Luna low preparation, six-response/360-second
  writer bounds and four optional retrieval calls are unchanged.

No v2.20 writing session was forced or yet observed; the latest completed desk was v2.19.
The same 15-minute audit is ACTIVE again with its existing authority and a scope-preservation
watch. Full editorial cutoff remains 18:09:34.063 UTC for later backfill. Draft 10668646 was
not mutated, published or dismissed, and this prompt change does not correct its existing text.
Reader-visible improvement remains to be established from subsequent natural output.

Rollback: redeploy previous runtime `d299365` from its clean archive, retain the current database
and keep autopost OFF. The backup is a verified recovery artifact, not permission to restore
over newer production state. Reverting these two prompt additions requires no data migration.
