# Preserve explicitly identified report headers

Distinct repair from completed ae4d270/v2.33. The production source reader returned 952
characters of navigation from BPI's Data Center Dividends report because its generic header
cleanup deleted the 85,675-character header containing the report. Raw production-UA and
Python-UA fetches were identical and included the complete report. Evidence and completed
historical audit through08:20UTC: audit/research/audit-2026-09-09-1759.md.

The smallest repair extends existing explicit body selection with BPI's
`.section_blog-post2-content` marker. A uniquely selected root header becomes a div before
normal chrome cleanup. Unmarked headers, nested chrome, ambiguous wrappers, source metadata,
image discovery, URL safety, 8,000-character default and 24-link cap keep their current behavior.
No model/prompt content, source weighting, editorial policy, budget or publishing behavior changes.
Runtime version is editorial-core-v2.34-header-article-extraction. Autopost stays OFF.

Independent plan and exact-diff review by article_header_review approved with no blockers;
16 source tests independently passed. Baseline28 source/evidence tests and43 focused tests passed.
Same saved174,539-byte production HTML now returns the full8,000-character excerpt, both separate
estimate scenarios and a leading PDF link. Later Hut8 detail remains outside this excerpt;
extraction success is not independent verification of the report's fiscal assumptions.

Full local and clean-release suite, deployment and production smoke pending. Rollback target
ae4d270; deploy a clean commit archive and use an online SQLite backup, never routine DB restore.
Main task was idle with discussion-only work and no overlapping build. Standing audit authority
explicitly permits bounded extraction improvements and requires independent substantive review.
