# Sprint 0064 — reporting follow-through

September 7, 2026. Independently reviewed, deployed and smoke-tested; rolling audit restored.
Plan: PLAN-0064-REPORTING-FOLLOW-THROUGH.md.

## What changed

- The delivered assignment and reporting guidance distinguish exact facts from broad event
  identity, promise from execution, and unverified-but-worthwhile leads from non-stories.
  Preparation/writer/editor clarify meaningful Bitcoin/monetary data and legislative scope.
  The orientation distinguishes material legislative viability/timing/scope statements from
  generic advocacy. No new model, source standard, quota or mandatory research stage.
- The 30-day memory catalog shows canonical event identity plus confirmed-output lede/date,
  separately from newer draft status. Account-only titles no longer obscure the event.
- A nullable 800-character reporting note carries the writer's checks/limitations to the editor
  and notebook. It is untrusted context, not evidence. The separate human-only self-report stays
  separate. Supporting and qualifying receipts must still be explicitly referenced by story.
- Editor evidence deduplication preserves source URL, authorship, date, limitations, retrieval
  provenance and actual body. Identical wording cannot inherit another outlet's authority.
- A plain completion with no native work forces a dossier next instead of repeating research
  offers. Real observed native activity still continues; provider history remains intact. One
  dossier-only reference repair remains available after early completion within existing limits.
- Missing/wrong NEW prefixes on explicit, resolved material updates are repaired before editing
  and on non-drop final copy. Final rails still run; no-base, duplicate, owner/mutation and
  multiple-draft protections are unchanged. Open-draft replacements are not relabeled.

## Independent review and verification

The independent lead approved the bounded plan and reviewed implementation. Review caught and
resolved three concrete integration details: early completion must retain the existing reference
repair; normalized notes must precede dossier hashing; and the longer assignment must be included
before packet compaction/byte checks. Source-provenance and UPDATE guard edge cases were reviewed.

Working-tree suite: **505 tests passed** (includes two pre-existing unrelated evaluation tests).
Ten new focused tests cover response progress, receipt repair, note isolation/digest consistency,
source identity, confirmed-vs-draft catalog copy, UPDATE fallback/final rails/protected outputs,
prompt boundaries and packet size. Tests block real network calls and isolate storage.

## Small live-model diagnostic — mixed, not an end-to-end win

Ten one-response requests cost **$0.20376890** in reported/recorded model usage, below the $5 cap.
Models: Grok 4.3 medium writer and Grok 4.5 medium editor. Existing keys were used; no new
credentials. The isolated diagnostic database records usage separately. No returned research tool
was executed, no native search was enabled in these probes, no production database was opened,
and nothing was exported to Typefully. These are next-action/prompt checks, not full-run replays.

Inputs and results are retained locally in `.model-eval/0064-reporting-followthrough/` (ignored
diagnostic artifacts). Liquid uses a captured six-lead packet with the already-released
reader/open-draft coverage correction applied equally; Lummis and ETF period comparison are
small hand-built probes based on audited cases. The latter have fixture receipts, not live fetches.

| Probe | Observed result | What it establishes |
| --- | --- | --- |
| Initial Liquid old/new prompt | Both dropped the recovery lead as already covered or unsupported; both used an overly narrow macro rationale | Initial prompt changes alone did not resolve the failure pattern |
| Refined Liquid assignment | Opened three relevant lead-context records, including the 3,400 BTC return tip | A better next action, not completed verification or a proven useful post |
| Lummis initial/refined | Initial probes dropped; one retest interpreted “nothing will be published” as an instruction to drop | Harness wording was a confound, not a production failure |
| Lummis with that notice removed | Older system prompt searched; final new prompt proposed a post | Story recognition improved in this sample, but original-source follow-through did not: new draft still cited the tip and added background absent from the fixture |
| Full-week ETF period | Both editor versions accepted matching Aug 31–Sep 4 totals and concise copy | The full-period fixture is handled; no incremental win shown |

The clean Lummis comparison used the same refined desk assignment for both system-prompt variants.
Thus it is not an isolated before/after release benchmark. Samples are tiny and model behavior is
nondeterministic. No claim is made that the sprint solved all missed stories or improved research
quality merely because a tool was requested. We stopped after one bounded prompt refinement and
a harness-notice correction, rather than building a new enforcement funnel.

## What remains to watch

Original statements can still be overlooked, and a well-written proposal can still omit a useful
receipt or include background its evidence does not support. The independent editor remains
essential. Watch actual source upgrades, original dates, corroboration and selected link quality;
the reporting note is not proof of those actions. Compare natural post usefulness, latency and
cost, not research counts alone. Check the new finalization observations and any guard deferrals.

Strategy draft 10663976 remains an owner-review item. No manual draft mutation or dismissal was
performed. The normal worker updated Liquid draft 10663389 during the natural smoke (see below).
Autopost remains OFF. Node and Perception are unchanged. The
dated system PDF still represents the same architecture; current prose documents describe these
protocol/prompt refinements without regenerating the PDF.

## Release evidence

- Runtime commit `c5c9096`, pushed and deployed from a clean archive, not the dirty worktree.
  Clean-release suite: **503 tests passed**. Unrelated owner/evaluation work was excluded.
- Online SQLite backup `/data/backups/nbn-pre-source-policy-20260907T164834Z.db` passed its
  integrity check before deployment. Rollback runtime remains `81eb8d5`.
- Railway deployment `c7509510-00a4-464d-80b7-d390aa70590a` is **SUCCESS** on the existing
  production service, with one replica and the existing `/data` volume.
- At 11:53 AM CT, `/health`, `/status`, all four Desk pages and all four authenticated workspace
  views returned HTTP 200. Production hashes for newsroom, main, editor and the orientation
  brief matched the clean release. Writer v2.18 and preparation v2.5 were loaded; no worker error.
- Autopost remains **OFF**. Writer/editor models and efforts, six-response/360-second allowance,
  and four-call retrieval allowance are unchanged. No manual production run or Typefully mutation.

## First natural run and the smoke-discovered repair

Run `cycle:1788800447:34e6afcd`, 12:00:51–12:02:05 PM CT, processed ten items; preparation sent
nine to the writer and one to Background. The exact writer packet contained the new assignment,
canonical event identity and confirmed-copy catalog fields in **54,389 bytes**, below the 64 KiB
cap. The run table's longstanding 40-character version bound truncates the suffix; the exact
writer-input observation preserves `editorial-core-v2.18-reporting-followthrough`.

The writer used three responses and three native calls, grouped four Liquid leads into one
material update, and passed six source-specific receipts plus its reporting note to the editor.
Preparation cost $0.00398150, writer $0.11391250, editor $0.02548600: **$0.14338000** recorded
model/provider cost for the run, excluding shared intake/source-service costs. No added diagnostic
run was invoked. Plain-completion finalization/receipt repair and UPDATE normalization were not
needed on this natural case; their edge paths are regression-tested, not claimed live-exercised.

The editor accepted the distinction between a promised return and confirmed return of 3,400 BTC,
tightened the lede and removed accelerator mechanics without primary transaction proof. Normal
production replacement updated the existing untouched draft **10663389**, rather than creating a
second draft or publishing. The worker had already replaced its earlier incorrect 3,998-return
copy with an unconfirmed-3,400-return draft before this run; this run advanced confirmation.

This is better story handling, but **not a complete original-source win**: the final selected link
is still Simply Bitcoin's X post, despite additional reporting in the evidence set, and no direct
transaction-detail fetch was performed. The writer's “independent reports” claim is its own
summary, not a verified independence count. Audit these choices and native-source dates.

After confirmed delivery, a pre-existing variable-shadowing bug (introduced in `3ed0787`) raised
`TypeError` while recording the legacy last-decision summary: the existing-update branch replaced
the `pending` intake list with a draft dictionary. Delivery and newsroom observations were already
saved; the worker continued, but this run's last-decision summary did not update. No remote retry
or historical rewrite was attempted.

The independently approved repair only renames that branch-local variable. A real-store regression
reproduces the failure in both successful replacement and stale-base suppression, then verifies
the original intake is recorded, the existing post is updated exactly once, and the mutation is
confirmed. All publication guards and recovery behavior are unchanged. Follow-up deployment and
audit restoration evidence follows.

## Final release verification

- Repair runtime **`c7887fd`**, pushed and deployed from a new clean archive. Independent lead
  approved the exact rename and independently passed all eleven follow-through tests. Full
  working-tree suite: **506 passed**; clean archive: **504 passed**.
- Fresh online backup `/data/backups/nbn-pre-source-policy-20260907T170748Z.db` passed integrity
  checking. No historical rows, pending mutations or old decision summaries were rewritten.
- Follow-up Railway deployment **`642a327c-c793-4d14-8b04-a1e7c489a06e`** is **SUCCESS**. The
  same ten HTTP checks passed again. Main hash
  `c5fa296aec49e235959d6da41573b68990636f5237a066442478fbe2f8fd8d4d` and the three unchanged
  newsroom/editor/orientation hashes matched the intended archive.
- Two natural worker cycles completed after the repair with no worker error; the next normal
  editorial slot was still pending at sign-off. The successful-replacement edge itself was
  replayed in isolated regression tests, not forced again against Typefully. A read-only
  Typefully GET confirmed draft 10663389 has the edited copy and is still unpublished.
- Existing **15-minute rolling audit ACTIVE**, with its notification/autonomy limits preserved
  and Plan 0064 checks added, including activity during the pause. Autopost **OFF**; no model,
  cadence, budget, credential, Node or Perception changes. Unrelated dirty work remains intact.
