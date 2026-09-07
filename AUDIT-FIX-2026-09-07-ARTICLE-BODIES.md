# Audit repair — article text before navigation menus

September 7, 2026. Small technical repair under AUDIT-AUTONOMY.md; no editorial change.

## Evidence

Run `cycle:1788794930:5f4e477c` fetched the AP Malone Lam hearing article twice, but
its 8,000-character receipt was consumed by menus and unrelated headlines. The second
call returned the same cached material. The writer declined the story for lack of usable
article text. This follows the earlier separate choice not to inspect AP at all; do not
collapse the two failures into one explanation.

A read-only Railway fetch returned HTTP 200 for AP and Fox's corresponding report. Both
contain actual story HTML, after long div-based navigation. AP uses `RichTextStoryBody`;
Fox uses `article-body`. The old regex strips nav/header elements, not div-based menus.
The AP hearing sentence is present deep in the returned HTML. This is not an API quota
failure or proof all rejected legal tips need a court docket. A laptop fetch received 403;
access varies by environment, so production-side verification matters.

## Repair

Use Beautiful Soup with Python's HTML parser to select a single explicitly marked article
body (`itemprop=articleBody`, `RichTextStoryBody`, or `article-body`) before existing text
and link limits. Keep the document title and metadata. Multiple ambiguous bodies, missing
markers, empty bodies and parser failures retain the previous fallback. This is deliberate
HTML extraction, not generated content or a new source-trust rule.

No larger budget, prompt/model/cadence change, source tier change, PDF/video reader, page-block
bypass, forced newsroom retry, Typefully mutation, or Node/Perception configuration change.
Existing receipts remain dated historical captures; no database rewrite or cache flush.

## Verification

- The regression test failed under all three article markers before the fix.
- Focused source suite: 13 tests passed. Full working-tree offline suite: 494 passed,
  including two unrelated evaluator tests that will not be part of the release.
- Tests cover long menus exhausting text/link caps, nested article structure, title,
  metadata, canonical/redirect provenance, original links, entities, script removal,
  unchanged text limit, ambiguous-page fallback, PDF rejection and URL safety.

## Production release

- Clean commit archive `/tmp/nbn-article-body-release.fDJcza`: **492 tests passed**.
  Runtime `a9e1bb2` was pushed and deployed to the existing service/environment as Railway
  `4c1aad2f-b82b-4499-99f0-8a75fc0cea49`, which reached SUCCESS September 7 at about 16:05 UTC.
- Backup `/data/backups/nbn-pre-source-policy-20260907T153931Z.db` passed SQLite integrity
  verification. The service retains one replica and the `/data` volume.
- Production source SHA-256 is
  `2578a97a2cb054d5679acea2ccbe0e1179bedc8d5da6a8d881fe49d56e9ad6b4`, matching the release;
  Beautiful Soup 4.15.0 loads successfully.
- Actual Railway adapter fetches now return readable AP and Fox hearing reports. The Tuesday
  hearing reference appears within the first 1,000 characters of each, rather than behind
  navigation. AP's author/publication metadata and links to court documents survive. Related
  inserts inside article bodies may remain; this is not perfect boilerplate removal.
- Authenticated `newsroom`, `intake`, `outputs`, and `system` JSON views returned 200. The
  initial smoke mistakenly requested unsupported `view=runs` (correctly 400); the actual
  `view=newsroom` endpoint was then verified. Public health is 200, two natural cycles completed
  by 16:05:06 UTC, autopost OFF, and no pending delivery. Node's 16:00 pulse is fresh.
- No forced newsroom call, article retry, historical receipt rewrite or Typefully mutation.
  No post-deploy newsroom use of AP/Fox is claimed; these were direct read-only adapter checks.
  The existing rolling audit remains ACTIVE. Rollback requires code only, not a DB restore.
