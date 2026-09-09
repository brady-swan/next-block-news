# Ongoing-story handoff — current behavior and gap

September 9, 2026 · Explanation/recommendation only; no implementation authorized by this review.

Included in the [living Writer-work sprint](writer-work-sprint-2026-09-09.md).

## Bottom line

NBN preserves previous reporting and can attach it to a related incoming lead. It does not
reliably turn a published developing story into an explicit future reporting assignment.
Memory exists; proactive follow-up is incomplete.

## Evidence inspected

Read current `nbn/main.py`, `nbn/newsroom.py`, `nbn/desk_prep.py`, `nbn/writer_memory.py`, and
the relevant `nbn/store.py` functions. Consulted the separate audit checkpoint read-only;
did not change it or run the audit. Queried Railway SQLite in read-only/query-only transactions
at approximately 17:47 UTC, without importing production modules or reading credentials.

Production had five storyline records. None matched Liquid in key, title, summary, or
linked exact-event keys. Several Liquid exact-event notebooks did exist, including the
September 6 incident, September 9 recovery, and bounty-demand work. They retained prior
attempts and editor outcomes. Those outcomes describe editorial history, not verified
current incident facts. No claim that every historical Liquid attempt was inspected.

## Current mechanisms

1. **Exact-event notebooks:** retain research attempts, evidence, unresolved objectives,
   proposed copy, editor feedback, and delivery context. Reporting artifacts are searchable;
   ordinary notebook/artifact retention is 30 days from relevant activity. Cached evidence
   keeps its inspection date and is not a fresh fetch merely because it was retrieved again.
2. **Broader storylines:** Writer may create/update a named ongoing subject, state summary,
   up to three `watch_for` items, related events, and open/closed lifecycle. This is optional
   model-authored output, not an automatic requirement for every developing story.
3. **Next-run delivery:** preparation receives a compact storyline index and chooses relevant
   lines for current candidates. Full selected cards contain `watch_for`. The prep index
   itself contains title/summary/age/outcome context, but not `watch_for`. The Writer also
   receives a bounded memory catalog and can search/open other notebooks and artifacts.
4. **Deferred work:** in the active v2 path, an editorial defer keeps the item pending with
   a default 15-minute delay. It becomes eligible for a later desk, subject to ordinary
   scheduling, capacity, and intake eligibility. This is distinct from legacy research-job
   attempt limits and is not a follow-up appointment for a successfully delivered story.
5. **Run trigger:** the ordinary desk runs for incoming/pending candidates or due research
   retries. With neither, `main.py` returns an empty result. After preparation, an empty
   candidate inventory likewise ends before a Writer call. A storyline's `watch_for` entry
   does not itself generate a candidate, set a due time, launch a Perception monitor, or
   wake a Writer.

Useful code anchors: `main.py` persistence around 457–499 and run selection around 1280–1310;
`newsroom.py` storyline instructions around 358–374 and selection around 1196–1241;
`store.py` storyline index/cards around 2814–2895 and `defer_item` around 4675;
`writer_memory.py` catalog/search around 106–156. Line positions may move.

## What a thoughtful Liquid handoff should say

Illustrative reporting questions, not assertions about today's incident state:

- What we last established and what readers have actually seen; when that was checked.
- Has the operator published a substantive incident report or revised the affected scope?
- Have funds been returned, and what does the relevant on-chain evidence show?
- Has service resumed, and are there material user actions or remaining risks?
- Where to check first: the operator/project's original updates, relevant measurements,
  and retained primary-source paths from previous research.
- When another check would be useful, and when to stop or reduce attention.

A check can conclude “nothing materially changed” and update the handoff without producing
a post. Do not require every new detail to become another update or treat old cached sources
as confirmation that conditions remain unchanged.

## Recommended direction, not an implemented design

Use the existing storyline/notebook as a small reporting agenda: explicit open questions,
best source paths, last check, and a sensible next check. Surface due follow-ups alongside
fresh leads in an ordinary run even if no new feed item happens to mention the subject.
Let the Writer decide whether the result deserves a new post, an unpublished-draft update,
a memory-only update, or closure. Use bounded attention and space checks out when quiet.

This is a missing use of our existing memory, not a reason to import the whole external
graph or create another research agent. The owner has not approved this implementation yet.
