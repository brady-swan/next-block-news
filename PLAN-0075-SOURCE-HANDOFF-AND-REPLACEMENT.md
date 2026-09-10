# 0075 — Attribution, evidence handoff, and replacement handling

Owner authorization: September 9, 2026, “go ahead and work on source attribution,
evidence handoff, and draft-replacement handling.” This is a targeted production
repair informed by the completed packet-v3 evaluation, not approval to remove Luna.

## Scope

1. **Follow the actual speaker.** Prefer a captured repost/quote's immediate original
   URL over links inside that original when choosing its single prepared fetch.
   Keep original author, relation, and URL visible in compact lead previews. Explain
   that a curator, original speaker, and quoted/linked speaker are different people;
   attach the receipts for the people whose claims the copy attributes.
2. **Finish the native-evidence handoff.** Native search and final submission can
   happen inside one response. If that response finds unretained source URLs and
   proposes stories, offer one evidence-only completion using the existing shared
   correction allowance and time/turn limits. No further research on this path.
   Ask for source-specific findings that actually support or qualify the stories,
   not every search result. Keep existing copy/identities and usable siblings intact.
   URLs remain pointers; never manufacture page extracts from a combined answer.
   Record requested/completed/fallback handoff for audit. No-budget/failed correction
   still sends otherwise valid supported work through normal independent review.
3. **Make replacement approval executable.** For a replacement, the Editor must
   explicitly approve or reject that operation separately from its copy verdict.
   Its existing bounded protocol correction handles missing/invalid values. A veto,
   unavailable/omitted Editor, or payload overflow must never replace an open draft.
   Retain the candidate and explanation for future identity review, not a guessed
   new story key or automatic new post. Delay proposed alias/family-memory writes
   until replacement approval; rejection must not poison the existing event's memory.
   Existing accepted aliases, owner edits/comments, pending mutations, published
   bases and ambiguity protections remain untouched. Drops still drop the proposal.

## Non-goals

No model, budget, cadence, topic/quality threshold, autopost, or architecture change.
No manual Typefully changes or paid replay of completed trials. No primary-only
publishing gate, new researcher, general semantic validator, or automatic split.
Preserve audit's b8924a0 confirmed-delivery handoff fix and unrelated dirty work.

## Verification and release

Independent plan review before implementation, then code review. Offline fixtures:
Gladstein/Sirion/Obi attribution and prefetch, native searched-versus-retained source
handoff, mixed siblings and exhausted budget, and Iza/Lam replacement veto through
the real controller. Verify missing Editor cannot mutate a draft, positive approval
still can, veto leaves aliases/notebook unchanged and is visible next run, normal
creates preserve existing fallback. Full isolated suite and clean-tree smoke.

Deploy only this reviewed delta. Coordinate audit/deployment, keep autopost OFF,
verify health/Desk/live code/config with no forced publication, then hand audit the
new watch points. These fixes enable better decisions; tests do not establish that
every future attribution or event-identity judgment will be correct.

Status: independently APPROVED by prep_merge_eval_lead. Missing review is not a semantic
identity veto; preserve that distinction in next-run diagnostics. Ordinary create updates
to published bases do not require replacement approval. Implementation in progress.
