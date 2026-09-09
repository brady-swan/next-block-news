# Sprint0071 — Perception reporting integration

September9,2026. Owner-authorized turn01a0846d; pooling follow-up incorporated. **Code review
APPROVED; runtime ad864ff deployed successfully and live adapter/health/Desk smoke passed.**

## Built

Three optional Writer tools, dated retained article text, short query caching, stable source
versions, acknowledged feed pagination, bounded subject surveys, per-interface usage/backoff,
shared-budget routing, existing memory/Editor handoff and System telemetry. No model/budget/
publishing-policy change; autopostOFF. Source images retained as pointers only, not inspection.

## Independent review

Lead reviewed plan, routing addition and actual diff. Resolved findings: survey retries spending
multiple slots on one failure; durable pending survey delivery; explicit unknown completeness;
malformed MCP content/pagination errors; known quota exhaustion; partial/truncated final pages;
bounded request duration and honest timeout wording. Stable source versions use existing memory
without implicit transaction commits. Reviewer independently passed75focused tests and approved
release. No extra transport framework/agent/memory graph added.

## Verification

-22focused Perception regression tests pass: real SSE/JSON/markdown contracts, unsafe pointers,
  publication precision, stable versions, duplicate state, partial-storage replay, cache hit,
  failure accounting, quota scope/routing, survey retries/pending replay, Writer budgets and
  actual Editor receipt-card/catalog provenance.
-49existing browser checks pass across320–2560px; no console errors. TypeScript/build pass.
-654 working-tree tests passed; clean committed archive passed652tests in27.299seconds.
  The two additional working-tree tests belong to unrelated, uncommitted evaluator work and
  were not shipped. The updated prompt-version expectation is covered in the clean suite.
-Railway authenticated REST and MCP probes succeeded using the existing key. PlainLummis
  searches returned the same6sourceURLs; multiword/entity/regulatory semantics are not assumed
  equivalent. Live regulatory/entity fixtures caught and covered the distinct document-list format.
-An article tool response headed Full Text contained only a short summary. It is explicitly
  completeness-unknown, not falsely certified as a complete/direct/or independent source.

## Release proof

- Runtime: `ad864ff`, `editorial-core-v2.30-perception-reporting`; pushed to origin/main.
- Railway: `fd4f02bb-3b24-4e79-82ac-5983e495dd6c`, created04:52:21.454UTC, SUCCESS.
  Deployed the clean archive, not the dirty working directory; existing single replica and/data.
- Online SQLite backup with integrity check:
  `/data/backups/nbn-pre-source-policy-20260909T045135Z.db`.
- Live04:55–04:57UTC smoke: exact perception.py/newsroom.py/workspace.js hashes matched the
  archive; health200/no last_error/autopostOFF. Authenticated System HTML, System workspace
  JSON and both compiled assets returned200. New Perception projection present.
- Natural intake: REST feed50records in1.319s; MCP mining/pools survey4pointers in1.417s.
  Fifty Perception source artifacts retained. Feed explicitly partial: page1of11,505provider
  records, truncated=true, nextpage2. This is not a claim of50new stories or complete capture.
- Railway adapter smoke, tagged `purpose=smoke`: MCP Lummis search returned6pointers in1.675s;
  identical repeat hit cache with zero additional attempts. One MCP article lookup took9.606s,
  retained399characters under `artifact_perception_062e37fdb519005846110918`; repeated local
  read returned the same artifact with zero additional attempts. Bitcoin Magazine identity,
  September8publication date/day precision and unknown-completeness warning survived.
  Only two smoke requests; no forced model replay, test candidate, Typefully draft or publication.
- REST response reported70remaining without a reset timestamp. Retain the observed header in
  telemetry, but do not invent a current daily balance; MCP headers described the shared minute
  window. This confirms access, not account-wide quota availability.

Several normal worker cycles completed onv2.30 with no error. No newv2.30Writer session had yet
started at04:56UTC; organic tool adoption/editorial benefit are audit observations, not inferred
from adapter smoke. The existing15-minute audit was restored ACTIVE04:57:44UTC with the
canonical Perception checks; exact saved-prompt equality, same task and cadence verified.
Its full historical editorial coverage remainsSeptember8,18:20UTC, not the smoke time.

## Known limitations

Unknown account-wide remaining quota; Node observed62MCPcalls/day on September7/8. NBN24/day
new-work allowance is not an account or dollar ceiling. At most4REST new-work attempts, soft20MCP
routing preference; specializedMCP can use remaining allowance. No credits purchased/configured.
Offset feed pagination is best-effort; changed ordering and truncation stay visible. Search dates
may be day-only.20-second request budget/per-I/O timeout is not a hard wall-clock cap; one
in-flight operation may overrun. Organic Writer use and editorial benefit require observation.

Rollback: disable NBN_PERCEPTION_TOOLS_ENABLED for tools/surveys, and
NBN_PERCEPTION_DIRECT_ENABLED for feed. Code-only rollback preserves additive tables/artifacts.
