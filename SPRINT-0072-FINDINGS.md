# Sprint0072 — Perception adoption and Writer desk usability

September9,2026. Owner turn01a0864b-aa94-7593-9ae2-f3118215c329.
Status: independent plan and code review APPROVED; deployed and production smoke PASSED.

## Shipped scope

- Perception retained-text hints survive crowded packet reconstruction. Optional prose and
  evidence excerpts shrink before the bounded memory catalog; exact current/prep notebook
  matches are separate from stable full-catalog pagination, including matches beyond page100.
- Relevant accepted-copy snippets and full coverage expansion use existing local posts, valid
  canonical aliases and separate draft/confirmed output. Creation, sync and confirmation clocks
  remain distinct; local copy may differ from later manual Typefully edits. Proposals are not
  accepted copy, and missing/deleted/replay/eval output is not promoted into current coverage.
- Local retrieval reports remaining capacity and exact omitted/already-read IDs. The entire
  UTF-8 envelope is bounded; repeated-only reads consume no extra call. Control errors contain
  no evidence and do not consume the evidence allowance. All four-call/8-row/16KiB/48KiB limits
  remain unchanged. No model, paid quota, cadence or time-budget increase.
- Recorded successful empty FIU regulatory SSE responses produce a complete empty result with
  a60-second cache and no failure backoff. Real errors and unfamiliar bodies remain failures.
- Existing prompt text now suggests routes by the actual reporting gap, not a required sequence.
  Original X statements, Perception industry text, accepted-copy memory and meaningful images
  have clear uses. Returned evidence should update the decision. First NBN coverage of an old
  disclosure is not NEW. Consequential dated Bessent/Warsh monetary signaling is eligible before
  policy action; attribution, uncertainty and the no-routine-macro bar remain. Prep receives the
  same clarification. Writer v2.31; assignment prep v2.7.
- Additive observations record packet visibility, literal tool receipts in the next Writer
  request and history overflow sizes. Existing Writer-result and Editor-input/decision records
  retain selection evidence. Visibility is not proof of attention; eagerly restored memory and
  sectioned JSON are not misreported as literal delivered receipt bodies.

## Review and verification

Independent lead approved the plan, then requested four bounded fixes: narrowly recognize the
successful regulatory-empty format; propagate monetary guidance to prep; retain omitted IDs
and page offsets in exhausted-capacity errors; finish the actual Writer→Editor fixture.
All resolved. Lead independently passed61focused offline tests and approved the code.

Eight new tests cover crowded25-candidate packets, retained hints/owner controls, an old exact
match beyond105recent notebooks, alias expiry, accepted copy beyond260characters, separate newer
draft/older publication, excluded output classes, unreadable notebook pointers, Unicode envelope
capacity, repeated/mixed IDs, paginated omissions and final capacity failure. The recorded FIU
response is exercised through request/cache, not only the parser. Existing oversized-section
readback and explicit-overflow tests remain in the suite.

A scripted Writer runs through the real session and materialization path: it opens retained
Perception text, the next mocked model request contains that exact text, the Writer chooses its
returned receipt ID, and the actual mocked Editor request contains the matching evidence/catalog
reference. No Perception network request or publisher mutation occurs. This proves wiring, not
that a live model will choose well or that Perception always has useful full text.

Full working-tree suite passed664tests in26.672seconds; clean committed archive passed662tests
in27.546seconds. Two unrelated evaluator tests exist only in the dirty working tree and were
not shipped. No UI assets or database schemas changed; existing offline UI/API tests passed.

## Release verification

Runtime `d8b2a46` pushed to origin/main and deployed from its clean archive, not the dirty working
tree. Railway deployment `b0d6f330-cc4f-488d-a122-5332996bf5ee`, created13:38:29.603UTC, SUCCESS.
Single replica and/data preserved. Online SQLite backup with integrity_check=ok:
`/data/backups/nbn-pre-source-policy-20260909T133805Z.db`.

At13:40UTC, six exact runtime/prompt SHA256 hashes matched the archive. Loaded Writer v2.31
and prep v2.7 confirmed. Health, authenticated System HTML and System/Newsroom workspace JSON
all returned200. Empty regulatory parser smoke returned rows=[],total0,partialfalse. AutopostOFF.
Initial post-restart cycles correctly waited on the previous process's lease. The natural
cycle completed13:41:13.146UTC onv2.31:335 fetched,1new,14pending, no worker error/autopostOFF.
Normal recovery closed one deployment-interrupted v2.30 pre-materialization run;0items held and
0outputs delivered by recovery. No lease clearing or database repair was needed.

The same audit-nbn-production heartbeat was restored ACTIVE in NBN Audit
`01a08641-aacb-7121-befa-4ca836497496`, same15-minute cadence and standing autonomy. Exact canonical
prompt, target and ACTIVE status verified after update13:42:22.022UTC. Added checks
cover hint retention, exact memory/copy access, actual supplied versus selected evidence, honest
empty/capacity results, freshness and consequential monetary signaling. Full historical editorial
review remains at the audit lane's checkpoint; this smoke does not advance it. No organic v2.31
Writer/Editor outcome was yet observed at smoke time; the resumed audit measures that separately.
No forced paid Writer replay, historical test post, Typefully content change, new audit schedule,
Node change or Nano Banana implementation is part of this release.
