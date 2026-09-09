# 0074 — preparation reliability and packet fit

Owner-authorized September9,2026, turn01a087d0-800d-7bb3-93c5-add45493f5f3.
Status: independently approved; implementation in review. Audit paused, autopost OFF.

## Evidence and boundary

- Luna low preparation:10errors/25attempts over six hours, errors near45.1seconds.
  Last3failed batches had25cards. The client waits synchronously with45s timeout.
  This is ReadTimeout, not a billing/quota response; upstream latency cause is not proved.
- Run923dc8eb successfully prepared25->17Writer leads, but initial packet66034bytes
  exceeded65536. Continuity records can push a dense packet beyond fixed compaction.
  Separately, history can exceed192KiB later.
- Earlier builds complete. Preserve source weighting, editorial prompts/goals, model/effort,
  cadence, candidate capacity and publication behavior. Richer discovery inputs and a
  stronger preparation model replacing Luna are proposals only for now (owner clarified
  this does not mean replacing Haiku's RSS mailroom).

## Smallest repair

1. Inspect recorded prep latency/size and one isolated existing25-card request if needed.
   Same Luna/low/schema. No Writer/Typefully replay. Account diagnostic usage separately.
   Prefer a measured, bounded timeout suitable for complete batch generation over new
   streaming/background workers, split-batch scheduling or blind retries. Candidate fix:
   90second prep timeout ceiling, unchanged6-minute overall session deadline. Final value
   follows measurement/review. Keep no SDK retry and fail-open on genuine failure.
   Record request bytes/card count/elapsed/error type for future diagnosis.
2. Repair initial packet fitting within existing64KiB cap. Preserve all candidate IDs,
   owner/retry/followup protections, real prep guidance, receipt IDs/provenance, incoming
   letter plus true output state, and discoverable full context. Prefer bounded trimming/
   offloading of optional preview prose/duplicate context, not a cap raise or lost candidates.
   Excerpts remain honestly truncated and full records retrievable. Record compaction.
3. Inspect history serialization for obvious duplicated envelopes/representation inflation;
   fix only a clear small defect if found. No new history compaction architecture or raised
   Writer budgets here. Report anything left unresolved.

## Verification and delivery

Reviewer approved90s headroom after a diagnostic replay of a previously timed-out25-card
batch:43,897input bytes,37.001seconds,25returned decisions,4,325output tokens,estimated
$0.0085296. Current retained item material/storyline index was used without coverage keys;
this is not an exact replay or proof every timeout recovers. Diagnostic usage is recorded
under diagnostic_desk_prep, run diagnostic:repair0074:prep90:1788985355; no Writer or publisher.
The reviewer also reproduced duplicated parsed/raw Responses output crossing the history
cap falsely. Raw output and encrypted reasoning now count once; real overflow still rejects.
Final optional preview fitting retains all real preparation fields at their existing bounds;
coverage ledes, accepted-copy excerpts and candidate display prose yield only under pressure.

- Focused timeout propagation/accounting/fail-open tests; realistic dense17/25candidate
  packets with real prep notes, letters/outcomes/accepted copy; references resolve/full
  text preserved; no editorial semantic changes. Existing suite must pass.
- Independent plan and implementation review; preserve unrelated dirty files.
- Clean reviewed commit, online backup, scoped Railway deploy. No credentials, embedding
  service or unrelated configuration changes. Verify actual timeout, packet cap/model/
  effort/autopost, health, Desk and natural nonempty run when available.
- Resume same dedicated audit after smoke with focused watches and standing autonomy.
- Rollback reviewed code/config, never destructive DB restoration.

## Official references consulted

OpenAI latency and Responses streaming guidance. Streaming does not remove complete
generation work; this protocol needs a whole structured preparation. No model migration.
https://developers.openai.com/api/docs/guides/latency-optimization
https://developers.openai.com/api/docs/guides/streaming-responses
