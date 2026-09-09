# Sprint0073 — Writer continuity and audience alignment

September9,2026. Scope: PLAN-0073-WRITER-CONTINUITY.md.

## Review and local verification

Independent lead approved the plan and final runtime implementation. Review caught real
lifecycle bugs before release: missing reports reopening terminal items, dropped assignment
metadata under packet pressure, and completed research orphaning technically deferred stories.
These now have focused regressions. The reviewer independently passed all13continuity tests.

Full local suite:682 tests passed in32.898seconds. TypeScript check and static Desk build pass.
The suite covers no-post required letters/shared correction, actual later Editor outcomes,
due-only new development through normal Editor and mocked Typefully staging, separate retry
history, no reopened delivered/uncertain work, no-change signal-date preservation, partial
keywords/exact runIDs, changed/deleted vector projections, malformed embedding fallback and
expert-parent identity/dates. Fixture outcomes do not prove production editorial gains.

Model/effort/cadence/budgets unchanged; autopost staysOFF. Personal KB not imported.
Ollama is infrastructure usage, not paid model tokens. QMD and Nano Banana remain deferred.

## Release verification

Reviewed commit2276766 pushed. Clean archive tested independently:680testsPASS33.875s;
the two additional dirty-worktree tests belong to unrelated evaluator work excluded from
this release.52Playwright checks pass from320px through2560px; letter and watch panels
visually inspected. No browser errors. Online SQLite backup integrity check passed:
/data/backups/nbn-pre-source-policy-20260909T191714Z.db.

Private companion nbn-embeddings created in the same project/environment/region with no
public/custom domain and a persistent/models volume. Initial deployment
88a439b9-1d5e-44e3-92bc-c6df899e3590SUCCESS. Actual cgroup confirms1CPU/999,997,440byte cap.
Ollama0.33.3 pinned image; nomic-embed-text:v1.5 model digest
0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f;
274,302,450byte model,768finite dimensions. Initial resident+cgroup cache604,110,848bytes.
Measured from NBN over private networking: first query295ms; warm32ms; four short documents
146ms. Two independent synonym controls correctly retrieve financial repression and wallet
seed-compromise topics first. These are plumbing controls, not a production retrieval-quality
evaluation. Hosting cost must be monitored from actual sustained usage, not download size.

Final companion deployment99331bb8-0b05-485d-908d-300460ab4b1bSUCCESS: restarted with the
same model digest/cache; no redownload. Verified private-only networking,1CPU/1GB limit,
healthcheck/api/tags. Loaded indexing sample:684MB cgroup total,402MB anonymous memory,
274MB filecache. The first generic redeploy selected Railpack and lacked Ollama; smoke caught
this before completion. Persisted explicit DockerfilePath and uploaded the clean companion
again. The failed intermediate image is not the active release.

NBN runtime2276766/v2.35 deployed, then scoped caller configuration activated on deployment
811f14c2-7493-4d49-a08a-2d05bc8a3070SUCCESS. Installed CLI skip-deploy variable writes appeared
in listing but were absent from the actual running container/environment config. Explicit
environmentPatchCommit of only the three approved variables fixed that; actual process now
confirms semantics configured, follow-ups enabled and autopostOFF. Both services have explicit
Dockerfile and healthcheck configuration to avoid accidental builder drift.

Production minute cycle completed with no error. All four authenticated Desk snapshot views
return200. Deployed orientation SHA95f63db72530eb5cf7e384934d81099e35b8584116b324d52b780c9619c0a2e7
matches reviewed source. Four new expert cohort X queries return200. Peer-to-Peer RSS was
independently verified HTTP200/XML before inclusion. Search uses actual retained NBN memory:
first index batch4documents/7vectors out of2355documents; hybrid query168ms. Initial index is
partial and catches up in bounded batches; keywords remain available over the whole corpus.
Do not claim production recall-quality gains from this partial-index smoke.

No forced Writer or synthetic production story was created. The next natural editorial
deadline was14:32:47CT; no v2.35 letter/watch yet at smoke. Required/no-post/due-only behavior
is regression-tested; actual use and quality belong to the next audit passes. Audit restart
requested in its dedicated lane with new continuity/interaction/retrieval watches.
