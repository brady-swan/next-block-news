# Next Block News — editorial core v2

*Current code description: 2026-09-09, Sprint0075 source handoff and replacement handling. Deployment proof/status: SPRINT-0075-FINDINGS.md.*

### Source handoff and replacements — Sprint0075

Prepared source lookup prefers a repost's immediate original speaker over that speaker's
outbound links. Quoted originals also precede ordinary outbound pointers. Compact social
cards retain author, relation and URL; their previews remain discovery, not inspected evidence.

When native research and the final dossier arrive in the same response with unretained
source pointers, the Writer may complete the evidence handoff once inside the existing shared
correction allowance. This offers no new research tools or budget. Relevant source-specific
extracts/receipt assignments can be added; copy, identity, members, visuals, decisions, follow-ups
and letter stay unchanged. Unused search hits need not be retained. Failed/exhausted completion
keeps the original usable dossier and normal Editor review; URLs are never automatically evidence.
`native_evidence_handoff` observations distinguish requested/completed/incomplete/not-attempted.

For an actual `replace_draft`, non-drop Editor decisions require `replacement_decision`:
`approve` permits the existing guarded replacement path; `reject` keeps the old draft and
returns the candidate for identity correction. Missing/unavailable/capacity-deferred review
also keeps the draft, but is labeled review-incomplete, not a semantic rejection. Proposed
aliases, notebook updates and artifact-family links wait for approval. Drops discard only
the proposal without changing target-story memory. No automatic split/new key is invented.
Candidate-local diagnostics reach the next eligible Writer. Ordinary creates, including
updates to published posts without an open update draft, retain their existing fallback.
Luna, model roster/efforts, cadence, all budgets and autopost OFF are unchanged. No migration.

### Writer continuity — Sprint0073

The audience brief now reflects the approved Bitcoin knowledge-graph review: Bitcoin, monetary
conditions, financial freedom, privacy, energy and related open tools/AI, judged by concrete
consequences. Routine software releases and small treasury-company announcements still do not
clear the bar. Four explicit expert-query cohorts retain useful replies, quotes and reposts
with actor/parent identity and original dates. Peer-to-Peer joins RSS; Kobeissi is a guide
attention signal but remains Tier2 research evidence. No personal knowledge base is ingested.

Every completed Writer session, including a no-post session, supplies a useful next-shift
letter in its dossier. The latest preceding letter is injected with date/run identity;
actual later Editor decisions and current publication states are joined separately.
A missing letter may use the existing shared one-shot correction slot, never a new model
budget or publication gate. Failed/exhausted handoffs are visible, not fabricated. Prep-only
cycles do not write letters. Optional human-only desk_feedback remains separate and unindexed.

The Writer may schedule a concrete question against a current notebook or a read/created
storyline. Normal cadence admits up to two due checks within the existing25 candidate slots,
even without new intake. Assignments are internal work, not fresh articles; item.story_key is
initially unset. Old evidence retains its dates. No-change/inconclusive results do not become
fresh storyline signals. A completed development whose story is technically deferred reuses
the same candidate; delivered/held/uncertain rows never reopen. Per-run attempts preserve
check history independently of actual Editor/delivery outcomes.

The existing memory catalog/read tools now retrieve substantive notebooks, source artifacts,
storylines and30-day letters with ranked keywords plus cached semantic similarity. Visual
metadata remains keyword-searchable. Similarity does not establish truth or event identity.
NBN uses SQLite projections/vector cache; private Ollama/nomic-embed-text:v1.5 supplies768D
embeddings. Content/model-digest/version keys avoid re-embedding unchanged chunks; one hit per
document prevents long records flooding results. Changed/deleted/expired projections cannot
be revived by old vectors. A bounded background thread owns its own SQLite connection and
does not hold write transactions across network calls or block intake on service startup.
Missing/malformed/slow embeddings fall back to keywords. QMD is reserve only.

Controls: WRITER_FOLLOWUPS_ENABLED=false stops new/scheduled check processing;
empty MEMORY_EMBED_URL disables semantics without deleting memory. Model, effort, cadence,
Writer/tool/packet budgets and autopostOFF remain unchanged. Additive tables:
writer_handoffs, writer_followups, writer_followup_checks, writer_followup_attempts,
memory_documents and memory_vectors. See the sprint plan for lifecycle/rollback details.

Next Block News is an automated Bitcoin news wire on X at `@nextblocknews_`. One Python
worker runs continuously on Railway. It polls intake on a loop with a 60-second sleep after
each cycle (long work can delay the next poll), opens a fresh Grok
story desk every 15 minutes when prepared candidates exist, sends the resulting stories through a
separate Grok editor, and delivers approved work through Typefully. Autopost is OFF while
Brady reviews drafts.

## Model roster — unchanged in Plan 0070

| Role | Model | Effort |
| --- | --- | --- |
| RSS/EDGAR intake | Haiku 4.5 | unchanged |
| Assignment preparation + storyline selection | GPT-5.6 Luna | low |
| Run-scoped reporting, native web/X research and writing | Grok 4.3 | medium |
| Separate batch editor | Grok 4.5 | medium |
| Internal daily receipt audit | Disabled (`NBN_AUDIT_UTC` empty) | historical Anthropic path retained |

Production seats have explicit environment overrides. `NBN_MODEL` remains the Anthropic
legacy-stack setting; `NBN_NEWSROOM_MODEL` selects the v2 writer. Unconfigured installations
keep the previous Anthropic defaults. Intake is intentionally still Haiku, not Luna.

### Perception reporting — Plan 0071

The Writer has optional coverage/company, regulatory and article tools alongside native web/X.
Intake retains dated source text instead of discarding everything beyond600summary characters.
Query caches are short-lived; unchanged source versions keep their original capture/expiry.
The existing30-day memory and exact Editor receipt path carry provider-captured text, original
publisher/date and completeness limitations. Search pointers remain uninspected leads.

One acknowledged feed page per900-second poll alternates newest and backlog reads. Up to8
persisted subject-survey slots/day add normal discovery candidates; no topic publication quotas.
REST/MCP have separate provider quotas and shared article artifacts. New work is capped24daily
attempts across interfaces, including surveys; at most4REST research attempts. A soft20MCP
threshold can route equivalent plain-keyword queries to REST; specialists may still use the
remaining allowance. Shared account remaining is unknown. Node configuration is unchanged.
Known backoff, partial coverage and source reuse are visible in System; actual research appears
in each run. Writer response/time/tool/context budgets and autopostOFF are unchanged.
See PERCEPTION.md for contracts, limitations and feature-disable rollback.

Plan0072 preserves retained-text hints through crowded packet compaction, keeps a bounded memory
map with separate exact-event matches, and makes coverage expansion return full local accepted
copy rather than another lede. Current draft and confirmed output stay separate; local accepted
copy is not guaranteed to reflect later manual Typefully edits. Context tools report remaining
capacity, exact omissions and already-read IDs within unchanged limits. Successful empty regulatory
searches are cached empties, not failures. Observations distinguish available, tool-supplied,
Writer-selected and Editor-delivered evidence; visibility is not proof of editorial use.
Gap-driven tool guidance and the owner-approved Bessent/Warsh signaling clarification add no new
research ritual, model seat, quota, publication gate or routine macro beat.

### Reporting execution — Plan 0068

Exact event keys, broader storylines, open drafts and confirmed reader coverage are labeled
separately. Invalid event/output relationships can use one code-described correction, sharing
the existing receipt-repair allowance and six-response/360-second writer budget. Preview
validation has no state effects; valid sibling stories survive correction. Unresolved failures
are retained against known candidate IDs and appear in later eligible retry context without
inventing an event notebook. Empty editor feedback is not a completed review.

Text-only editor requests omit image-review fields. Visual/mixed requests require an explicit
image verdict and asset/hash fields; prose approval is insufficient. Received malformed JSON
and invalid references use the existing one omitted-only recovery. Transport failures/refusals
do not gain a new retry loop. Remaining fallback copy is labeled **Needs human review — editor
response failed** in the Desk; human-draft fallback applies to creates. Replacements instead
retain the existing draft until explicitly approved. Autopost protections remain.

The editor may select the final reader source by exact inspected evidence reference, including
an explicitly selected relevant research-appendix receipt. Null keeps the writer's choice. The
same source follows into the first reply, provenance, memory and Desk. Delivery stores compact
pointers to retained exact evidence, not duplicated article bodies. Later visual changes use
the last confirmed delivery's source context; a proposed or uncertain mutation cannot replace
it. If retained evidence no longer matches an owner-changed source, the old action stops.

Preparation may advance relevant later-outcome evidence even when it does not justify a second
post. Writers selectively check whether a requested action was approved or another outcome
changed, distinguish disclosure/outcome/reporting-period/article dates, and favor the meaningful
Bitcoin development over a promotional headline. This adds no mandatory research checklist.

Relevant cards now point to available images; post/article media precedes avatars and duplicate
thumbnails. Existing visual guidance includes valid chart examples and explains at-a-glance
comprehension and potential reach. Images remain optional and require actual pixel review.
Nano Banana is parked by owner; the saved Gemini key is unused. No new model, worker, quota,
cadence or budget was introduced. See SPRINT-0068-FINDINGS.md for measured results and limits.

Each desk receives the exact reader-visible post copy from the preceding 48 hours, newest
first, with publication time, event key, class, and receipt. This is distinct from the compact
event catalog and the open-draft board: the feed supplies voice and continuity context, while
the other boards support event identity and prevent duplicate drafting.
Within the exact-event coverage board, reader-covered and open-draft cards use separate
post-lede lists. A newer unpublished update cannot replace the summary of earlier reader
coverage merely because both share a canonical key. Existing IMMEDIATE/UNCERTAIN reservation
semantics and publisher duplicate guards are unchanged; uncertain delivery is not confirmed
publication. See AUDIT-FIX-2026-09-07-COVERAGE-COPY.md.
Typefully's batched analytics endpoint adds impressions, likes, reposts, comments, post age,
and snapshot time when available. These are explicitly weak, age-dependent craft signals—not
evidence, importance scores, or a mandate to chase popular subject matter.

Fresh model context no longer means discarded reporting work. A bounded 30-day editorial
workbench carries canonical exact-event identity, the prior proposed post, the precise
unresolved research objective, revalidated inspected evidence, and independent-editor
feedback into later sessions. The workbench is informational: it never marks a story covered,
suppresses a new candidate, or publishes anything by itself.
The paginated catalog explicitly includes canonical event keys and a short confirmed-output
lede/date where known, distinct from newer open-draft status. Account-only notebook titles do
not hide the event key. Catalog and initial-packet byte limits are unchanged.

The product stance is practical: publish useful, well-supported Bitcoin coverage and learn
from production. This is an early, low-visibility account, not the New York Times. The
system keeps consequential safety and idempotency rails, but freshness, semantic novelty,
rounding, numerical materiality, and story importance are editorial judgments—not brittle
code vetoes.

## The flow

```text
every 60 seconds
  reconcile Typefully + poll sources + ingest/deduplicate + health/heartbeat
       │
       ├─ RSS + EDGAR → Haiku mailroom (priority / candidate / background)
       │                    └─ background is audited, not sent to the newsroom
       │
       ├─ fresh AM/PM EIC citations enter one-off intake; legacy daily receipt audit disabled
       │
       └─ every 15 minutes, if the desk is non-empty
            run-scoped Luna low assignment desk
              distill all leads → advance / background; protected work always advances
              bounded deterministic prefetch prepares likely receipts
            fresh run-scoped Grok 4.3 medium story desk
              read clean desk + memory catalog → native web/X / fetch / recall → write dossier
            small consequential code rails
            one independent batch Grok 4.5 medium editor
              publish | revise | draft | drop
            Typefully → X (or human draft when appropriate)
```

The editorial deadline is persisted in SQLite (`editorial:next_run_at`), so restarts do not
accidentally create rapid duplicate sessions. Empty due windows use zero model calls.
Operator stage/retry requests bypass the wait, and a backlog larger than one 25-item batch
is eligible to drain on the next healthy worker cycle. The global worker remains at 60
seconds because source intake, health, EIC discovery, audits, and publication reconciliation must
not wait 15 minutes.

## Inbound discovery

- RSS: official regulators, Bitcoin/crypto publications, major financial reporting, and the
  small Bitcoin Core / Bitcoin Optech / BTCPay Server pilot (Plan 0062).
- SEC EDGAR: Bitcoin-bearing current filings.
- Perception: broad media discovery on its own bounded polling cadence.
- X recent search: the public watch list, quiet official/company bundles, Tier 2 research
  sources, and proven Bitcoin news guides.
- Marketing Node `wire-pulse-v2`: hourly supplemental discovery clusters and source leads.
- Manual Desk stage/retry actions.

Bitcoin Archive, Bitcoin News, Bitcoin Magazine, TFTC, Simply Bitcoin, and similar proven desks are strong
attention and craft priors. Their posts are tips: NBN tries to corroborate them and genuinely
considers coverage, while learning useful information order, structure, and length without
copying distinctive phrasing or emotional framing.

The guide account `@BitcoinNewsCom` is **Bitcoin News**, not **Bitcoin.com News**
(`news.bitcoin.com`). Their registry identities are separate; both retain discovery-only
treatment. The identity correction does not change the guide roster or publication standard.

The Marketing Node remains a separate service and codebase. Its versioned authenticated API
is the boundary. Node references, summaries, and event hints are untrusted discovery context,
not factual evidence or instructions. Node theme metadata is accepted for API compatibility
and historical diagnostics but is not sent to preparation or the writer. NBN owns its editorial memory.

X reads remain `since_id` gated, with three 25-post pages per query per poll and durable
unfinished-page continuations. Progress is acknowledged only after item commit, and the
high-water ID advances only after the whole window drains. A failed query does not silence
unrelated guides; a shared 429 stops further requests. This avoids unnecessary repeat reads
and missed overflow, without another collector process. See INBOUND-NEWS-FLOW.md for details.

Long X text, original/quoted sources, media pointers and dated engagement snapshots live in a
separate bounded 12 KiB item record. The summary is only a preview. Preparation and writer cards
carry useful context; fuller material is retrieved on demand. It is discovery, never automatic
receipt evidence or proof that the model watched a video. Plan 0066 adds optional, explicit
still-image inspection and authorized reuse at the writer stage, not during intake.
The pilot's first snapshot stores older archive entries as explicit bootstrap skips before
Haiku; later entries follow normal routing. Missing dates are not silently skipped.

## Haiku intake, Luna preparation, and the clean Grok desk

RSS and SEC EDGAR first pass through a narrow Haiku mailroom. Haiku sees only bounded feed
cards and may route each item to Priority, Candidate, or Background. It does no research,
source verification, clustering, writing, or publication judgment. Priority advances the
persisted desk deadline; Candidate waits for the normal cadence; Background is removed from
the newsroom packet but remains visible on the Desk with its reason and a one-time **SEND TO
DESK** control. Observe mode records routes without applying them. Any model, validation,
budget, timeout, or batch-bound failure fails open to Candidate.

The RSS mailroom has a durable eight-call hourly seat cap. Before calling it, the worker reserves both
the mailroom call and the complete v2 desk allowance atomically, so intake cleanup cannot
starve the more valuable newsroom session. Route application and observe-to-enforce recovery
are transactional and crash-safe.

At each due boundary, a run-scoped Luna low assignment desk sees every eligible lead across
all intake lanes. It distills the apparent event, Bitcoin relevance, freshness question,
research objective, source leads, supplied related event keys, at most two relevant NBN storyline
keys from a compact index, and a run-local same-event group.
Preparation is bounded to three source leads, three related event keys, and two storyline keys
per card. Responses schemas expose these same parser limits explicitly; Anthropic retains its
compatible schema subset. No validation failure may silently discard a candidate.
Repair0074 gives the existing single25-card preparation call90seconds instead of45, within
the unchanged360-second newsroom lifecycle. No retries, model/effort changes or added calls.
Run preparation counters report compact request bytes, cards, timeout, elapsed milliseconds
and error class for success and failure; the same attempt is accounted once in model usage.
It may mark a card Background
only when it is facially outside scope, contains no development, or is an exact code-identified
duplicate. Guide tips, official/primary items, operator promotions, research
retries, and unresolved continuity are code-protected and advance even if preparation disagrees. Every
timeout, malformed row, capacity limit, or validation error also fails open item-by-item. Observe
records can never become enforced later.

In enforce mode, a batch containing only Background cards uses no newsroom call. Those cards remain
visible on the Desk with **SEND TO DESK**. For advanced cards, code may prefetch up to six unique
likely receipts and 24,000 characters, while reserving at least eight fetches and 80,000 characters
for the newsroom's own reporting. Preparation prose is not evidence.
Materialization preserves current-run enforced Background provenance instead of relabeling those
audit-only skips as newsroom rejections. Plan 0059 fixes new runs; historical mislabeled rows
are not rewritten or automatically promoted.

When one member of a preparation same-event group advances, any Background companions in that exact
run-local group advance with it. This changes only which leads reach the newsroom; it is not canonical
identity, evidence, corroboration, or approval. The persisted preparation records name the
companion anchor that caused the promotion. An all-Background group remains Background.

Each non-empty prepared run gets a new Grok context. It receives a run brief, one clean card per
candidate, the Luna preparation, safe reference pointers, prepared receipts, recent coverage/open
drafts, Luna-selected NBN storyline cards, guide attention signals, and verified handle
spellings. Raw provider payloads and internal plumbing do not reach the model. Large recent-feed,
continuity, storyline, and handle context is sent as compact indexes with code-issued IDs; the writer can
retrieve bounded full records on demand: at most four calls, 16 KiB per call and 48 KiB total,
with the initial desk still capped at 64 KiB. Plan 0069 first moves bulky prepared-receipt
link/image metadata behind that same lookup when the packet is oversized. Full captures stay
retained with their fetch IDs; inline evidence can become shorter UTF-8-bounded excerpts with
explicit truncation and separate excerpt/full-capture fingerprints. Candidate identity,
retry, owner-override and visual hints survive compaction, with full candidate/reference cards
retrievable. Every in-scope open draft retains its exact key and a short lede rather than
disappearing behind a three-row cap. Full storyline cards can likewise move behind indexes.
A final density tier removes only empty optional card fields and repetitive code-generated
preparation-failure boilerplate. It retains the exact fail-open outcome and protection
reason, rather than presenting fallback prose as model judgment. Real preparation and all
nonempty control fields remain intact; original full cards stay retrievable. This adds no
model calls and does not change the packet or retrieval limits.
If still oversized, optional coverage ledes, matching accepted-copy excerpts and candidate
headline/arrival previews shorten further with explicit truncation flags and existing full
context IDs. No candidate, exact event, incoming letter, output state, control or real
preparation guidance is removed. Full originals remain available through read_desk_context.
An irreducibly oversized packet still defers, recording section sizes as an assembly failure,
not a delivered writer input. Only inline cards count as initially supplied/read. These are
ceilings, not required consumption. The
stable prompt benefits from provider caching. Responses tool turns preserve the provider's complete
output state, including encrypted reasoning, in bounded run history only—not editorial memory.
The192KiB history cap counts each Responses replay once, not both its raw provider output
and the duplicate locally parsed tool blocks. Raw replay and encrypted reasoning remain
unchanged. Image manifests and the separate image-byte limit retain their prior accounting.
Native-only research turns may continue in the same conversation; they do not require fake
client-tool results. A plain-text response is not a final editorial decision. The last allowed
response forces the dossier specifically.
Plan 0064 also requests a dossier immediately after a text-only response with no native work,
instead of repeatedly offering research tools. Current-response native operations or positive
usage count as progress even when no new URL appears. The complete provider history remains.
Early completion still permits one dossier-only receipt-reference repair within existing
time/round bounds; it does not reopen research. `writer_finalization` records the reason.

Candidate cards, storyline summaries, and search snippets are leads. The writer may submit
immediately or research selectively with native web/X, existing SerpAPI and safe fetch tools.
Reporting and writing use the same Grok context. Six successful responses and a 360-second
lifecycle replace the separate research handoff; the lifecycle includes preparation/prefetch.
Native allowance starts at 12 and is reduced by observed usage across requests; all tools share
24 calls. Provider-side batching means this is not a strict billable-call or dollar ceiling.
Actual counts and reported charges remain authoritative. Direct fetch bounds remain 16 sources,
8,000 characters each, 160,000 total. Research requests reserve time for finalization.
Article links, byline, publication metadata and limitations survive extraction. Loading shells
are failed material, not useful source text. Explicitly marked HTML article bodies are selected
before text/link caps so long navigation menus cannot crowd out the story; ambiguous or unmarked
pages retain the existing whole-page fallback. Bitcoin Magazine's `.td-post-content` is included;
an empty Mempool explorer title shell is failed material, not a citable receipt. This does not
read video or unlock blocked pages.
Fetched receipt identity comes from the final destination URL, not the discovery item's source
label. Referenced posts and redirects cannot borrow the tip author's name. Known registry sources
keep their names/tiers; unregistered destinations display their domain, with URL/byline alongside.
Discovery context and candidate linkage remain separate. Historical saved receipts are not rewritten.
Text-based PDF responses use local Poppler extraction in the same fetch route. At most the first
20 pages are parsed, within 10 seconds and the caller's remaining deadline; parser inputs over
10 MiB are rejected. The existing HTTP download happens before that parser-input check. Returned
text still obeys the ordinary source allowance (normally 8,000 characters), with page markers
and explicit clipping/text-only limitations. This is not full-document reading, OCR or chart/
table-layout verification. No author or publication date is inferred from PDF file metadata.
Unreadable, protected, image-only or timed-out documents return empty typed failures, never
binary receipts. Limitations survive the editor and next-session memory. The writer can use
another existing retrieval route for missing material; no primary-only requirement is added.
Native source manifests cite exact observed URLs;
code registers source-specific receipts before validating even a same-response dossier.
The writer is prompted to include useful supporting and qualifying receipts for each story,
not merely the selected reader link. A nullable 800-character `reporting_note` carries origin,
freshness checks and limitations into the editor and event notebook as untrusted context, never
evidence or instructions. Equal text at different URLs/authorship/dates is not deduplicated into
one source identity in the editor's evidence catalog. No extra model turn is added for this note.
V2.22 keeps that primary handoff and adds an optional unassigned run-research appendix to the
batch editor. It contains only eligible current-run fetched/native receipts, excluding restored
historical memory: at most eight records, 2,000 characters each and 24 KiB total, inside the existing
256 KiB editor payload. It yields to the already-fitted candidates, selected evidence and feed.
These excerpts are not automatically story support. The editor can explicitly select relevant
`additional_evidence_refs`, with eight total receipts per story. Invalid ref lists reject only that
decision into the existing one omitted-only recovery; unresolved cases use original-copy draft
fallback with no additions. The exact delivered excerpt, its fingerprint, original fingerprint,
clipping status and unmodified source limitations reach final rails and the event notebook.
Unseen text never expands quote support. Native paraphrases remain native; the reader link is
unchanged. Existing observations store the appendix and the chosen refs. No research call is added;
editor input can grow by the bounded appendix. Actual costs remain in the usage ledger.

Plan 0059 tested stronger selective research-routing prompts but did not demonstrate reliable
native assignment. Those experimental instructions and turn-budget fields were not shipped.
That dated experiment remains in `SPRINT-0059-FINDINGS.md`; Plan 0063 now replaces delegation
with the reporter-writer's own native tools rather than another routing-prompt experiment.

Research returns a bounded memo plus source-specific findings. Only provider-observed citation
URLs can supply native extracts. Existing/directly fetched text is preferred; blocked pages and
native X findings can carry a clearly labeled `provider_reported_extract` instead. That is a
researcher's paraphrase, not a verbatim page capture. The entire memo is never a source body.
Authorship comes from the observed X status URL; `/i/status` does not establish an author. The
writer and editor see the distinction, and it survives saved evidence and later sessions. An
official URL alone cannot upgrade an extract to direct primary evidence or independent reporting.
Source judgment remains with the models; receipt provenance is not a new allowlist. There is no
forced survey, forced research phase, or mandatory minimum number of turns. The model sees
the entire batch and owns research, clustering, judgment, and writing together.

It returns independent story rows. One malformed story defers only its members; it cannot
invalidate the rest of the batch. A candidate omitted from model output becomes
`defer:model_output_missing` and returns on a later desk instead of silently skipping.

When an explicit `material_update` has a resolved reader-visible base, code repairs a missing
or mistaken NEW prefix to `UPDATE:` before independent editing and again on non-drop final copy.
Empty copy remains invalid. Final delivery rails still run; same-event duplicates, missing base,
protected mutations and multiple drafts still stop delivery. This is presentation repair, not
code deciding materiality. Ordinary unpublished-draft replacements are not relabeled.

One transport retry is allowed with the exact same newsroom session state. A billed session is never
replayed from scratch after a protocol or validation error. If the attempt fails, advanced items
remain pending with a typed technical defer while already-applied Background routes remain intact.
V2 never automatically falls into the legacy triage/writer/resolver stack.

Before materialization, v2 reconciles exact-event identity. One canonical family already
attached to the member items wins. If a proposed story crosses conflicting existing families,
code does not merge or overwrite them: it creates an isolated review key, warns the editor,
preserves every member key, and forces any resulting output to a Typefully draft. The writer may
also select an exact key exposed by the coverage or continuity board. Only an unambiguous
one-family match may register the newly proposed slug as an alias. There is no fuzzy automatic
merge, and Node theme IDs remain too broad to serve as event keys.

NBN's durable storyline ledger sits one level above exact events. A storyline is an ongoing named
subject such as CLARITY Act progress or the Coldcard vulnerability, not a generic beat and never
evidence. Luna highlights relevant lines; the writer can discover all active lines in the memory
catalog independently. The writer may create at most three
new lines per run or update a line whose full revisioned card it actually read. Optimistic revision
checks prevent a stale run from overwriting newer memory. Storyline writes happen independently
before publisher materialization; any failure drops the optional link and delivery continues.
Exact-event keys, receipts, output lifecycle, and Typefully reconciliation remain authoritative.
Read-time cards now label writer summaries as context, not editor-approved facts. Event dispositions
are writer intentions; a separate current exact-event outcome supplies the latest editor reason/time,
unresolved work and publisher state. It may postdate the originating run, and missing/expired notebook
state is unknown. Compact caveats also appear in the preparation index and writer memory catalog.
A relevance drop is not proof that all summary facts are false. Original summaries/revisions are not
rewritten. Confirmed reader publication remains separate from a newer open draft.

When research is incomplete, v2 retains the canonical key, proposed post, inspected evidence,
and a code-mapped objective such as “find one independent second report.” The next fresh desk
sees this on `continuity_board` and can continue rather than rediscovering the story. Stored
evidence retains its original inspection date and requires fingerprint/public-URL checks.
An old filing may support historical facts; live balances, prices and current status need
fresh retrieval. Memory never makes old news new. Archival receipts do not populate the fresh
URL cache. Only intact records receive citable `memory_*` IDs.
If final lint defers a story, the exact verbatim-quote/URL/length issue and inspected evidence
also become the next workbench objective rather than being reduced to a transient item note.

Completed reporting operations also persist incrementally in `writer_artifacts`, before the
next network/model call—even when no final story or canonical key exists. Initial associations
are to run/candidates; canonical linkage follows validated identity only. Records last 30 days,
with actual observation times and bounded contents. Reads and identical retries do not renew
their reporting freshness. Current confirmed post state is projected into notebooks; an older
delivery note or resolved failure is not today's publication state or research objective.

The compact active catalog lists notebooks, storylines and reporting artifacts, with explicit
pagination when it cannot all fit. `search_memory` finds names, topics and source text;
`read_desk_context` opens records or bounded sections. `search_intake` searches the previous
72 hours, including skips, and can widen to seven days. Searching never reopens or publishes
an item. These operations share four retrieval calls / 16 KiB per call / 48 KiB total.

The final dossier may include a short optional writer self-report: what helped, what hindered,
and one suggested improvement. Null is valid; malformed feedback does not invalidate stories.
It is stored separately as `writer_feedback` in run observations, shown per run and in System,
and retained for 14 days. It is unverified human-review input, never injected into future writer,
preparation or editor prompts, never reporting evidence, and never an automatic policy change.

## Editorial doctrine

- Bitcoin includes the network, asset, and monetary project. Protocol, mining, custody,
  privacy, security, regulation, market structure, sovereign debt, inflation, liquidity,
  and central banking may qualify when the Bitcoin connection is real.
- Do not become a generic crypto feed or a stream of tiny macro statistics.
- Roughly 5–8 worthwhile one-off stories a day is a planning estimate, not
  a quota.
- A narrow story supported by the evidence is better than holding a promising lead while
  searching for a perfect version.
- Routine treasury-company coverage is limited to Strategy, Metaplanet, and Strive.
  Strategy purchases can qualify because the company leads the category and can move the
  market. Routine buys by the others face a high bar. Closely related disclosures should be
  collapsed into one useful post.
- Effective structure and length are legitimate things to learn from successful accounts.
  Distinctive phrasing and emotional framing are not copied.
- No hype, fabricated certainty, forecasts, trading advice, or investment instructions.
- A famous investor or small allocation to Bitcoin-linked equities is not inherently a Bitcoin
  story. Selection turns on material effect, meaningful adoption, or new understanding—not the
  prominence of the portfolio owner.
- Research can be broad while public copy stays selective. The writer and editor lead with the
  Bitcoin-relevant consequence, split overloaded sentences, avoid consecutive clause-heavy
  sentences, and cut verified detail that does not change the reader's picture.
- The orientation includes historical ETF and CFTC/CLARITY craft illustrations, explicitly not
  current facts, fixed-length templates, or permission to omit necessary attribution.

## Practical evidence standard

For a routine factual claim, one inspected official, original, Tier 1, or reliable Tier 2
report may be sufficient. Primary sources are preferred, not mandatory. The Block and
CoinDesk are Tier 2 reporting sources in the registry.

For allegations, hacks, crime, disputed claims, and consequential legal assertions, a primary
artifact or two credible independent reports is the normal ideal. When that is unavailable,
the editor may narrow and attribute the claim, route it to human draft, or drop it. Source count
is not a hidden code veto. Discovery tweets and search snippets never count as evidence. A
captured X post proves what that account said, not the underlying claim; aggregators, wrappers,
and syndicated copies are not independent corroboration.

Bitcoin Policy Institute is a scoped exception to the generic social-post rule. BPI's site and
`@bitcoinpolicy` account are first-party receipts for research BPI says it published and for its
stated findings; that research may be posted without separate confirmation. This trust does not
extend to third-party facts or allegations BPI cites, and it does not classify BPI as a government
or company-action official source.

The desk and editor may use all inspected receipts together. The linked receipt is the best
useful source for the reader; it is not required to reproduce every harmless detail alone.
The source registry is strong guidance rather than a closed universe: the writer may inspect and
use a safely fetched public page outside the list, and the independent editor judges its
credibility. Aggregators, syndication, and social posts carry explicit capability warnings;
they are not silently promoted to official or independent evidence, but code does not veto a
narrow, honestly attributed draft merely because the domain is absent from the registry.

Numerical agreement is judged for meaning. `2.99%` may be written as “roughly 3%,” and
`159.95` versus `160.1` does not fail merely because the strings differ. Verbatim quotations
still must appear in inspected evidence.

Both active prompts also preserve a statistic's category, unit and reporting period: a total
across digital-asset investment products must not become a Bitcoin-only total in the copy.
Correct the scope in wording or use an explicitly reported Bitcoin subtotal. This adds no
research call, evidence gate or change to the practical-rounding allowance. See
AUDIT-TUNING-2026-09-07-METRIC-SCOPE.md for the observed draft and release record.

## Hard code rails

V2 code blocks only what it can determine reliably:

- unsafe/private URLs and dangerous redirects;
- exact duplicate body or receipt delivery;
- empty copy, embedded receipt URLs, excessive length;
- direct investment instructions;
- unverified or excessive X mentions; and
- verbatim quotations absent from all inspected receipts.

There is no v2 hard veto for a 2.5-hour event clock, semantic story-key identity, mandatory
date suffixes, exact numeric string equality, question marks, or mandatory `NEW:`/`UPDATE:`
prefixes. Those are editorial matters. The legacy lint remains unchanged for Blocks and
legacy-only code paths.

## Independent batch editor

One separate Grok 4.5 medium call receives every surviving story, all of its inspected evidence, and
the recent feed. It judges factual support, usefulness, redundancy, numerical materiality,
framing, and craft. It can publish, revise, send to Typefully as a draft, or drop.

If the editor API is unavailable, otherwise safe distinct-event desk work is preserved as a
Typefully draft; it is never autonomously published, discarded, or routed through legacy models.
A valid-but-partial response gets one compact recovery containing only omitted stories; another
omission is marked `editor_incomplete` and cannot bypass canonical output suppression.

Each story declares `distinct`, `same_event`, or `material_update`. Code resolves the complete
canonical alias family with reader-visible output ahead of open drafts. Same-event reports never
create a second output. Before publication, new evidence can replace the sole untouched Typefully
draft in place when replacement is enabled; after publication, only a material development may
become a new `UPDATE:`. This applies when autopost is on: scheduled, publishing, published, and
ambiguous attempts all block a blind second create.

Typefully writes use durable mutation intents. Intent and exact desired-thread fingerprint land in
SQLite before the network call; confirmed remote output and all local post/item/workbench state
then finalize atomically. Restart recovery reconciles but never repeats an ambiguous POST/PATCH.
Unresolved cases appear on the authenticated Desk with version-fenced owner actions.

New creates finalize only after Typefully reads back the exact ordered thread. Persisted mutations
reconcile from their stored fingerprints, so a deployment or formatter rollback cannot reinterpret
an old one-post or new two-post attempt. Legacy inline-link drafts are retained rather than
mechanically migrated. `scripts/typefully_feedback.py` provides a tightly bounded, GET-only view
of recent owner comments; its marker-free display reads are never used for draft replacement.

Since September 8, the rolling Codex audit is authorized to add draft-specific review comments
and replies through Typefully's Comments API. Each starts with `Codex audit`; distinguish these
AI observations from owner feedback even when the connected account supplies the API author.
The audit checks current copy and existing comments, avoids repeated notes, and verifies writes.
It does not edit, schedule, publish or dismiss the draft. Existing comment-based replacement
protection remains unchanged. This is an audit workflow, not a new in-worker model stage;
see `AUDIT-AUTONOMY.md` and the local comment ledger `audit/typefully-comments.md`.

The editor compares apparent conflicts by actor, place or facility, time, and scope. A newer
specific action is not contradicted by an older general intention; when current evidence
supports a narrower accurate version, the editor should revise rather than drop useful news.
Its bounded verdict, reason, and copy are retained as context for later related candidates.
That feedback is not a hidden rejection rule.

The editor payload is bounded to 256 KiB. Repeated evidence bodies are cataloged once; selected
receipts and warnings take priority. If an entire candidate cannot fit without losing its
selected receipt, it is staged as a human draft and labeled `editor_payload_capacity`.

## Optional post visuals — Plan 0066

The existing reporter-writer can list relevant article/X image pointers, inspect actual static
image pixels, inspect one original-layout PDF page, or render an NBN graphic from retained
evidence. Bar, line, before/after, quote and highlighted-excerpt templates support landscape and
square layouts. Pillow draws exact text/numbers with packaged Inter fonts; there is no paid
image-generation provider. Quotations/excerpts must match a contiguous directly fetched source
passage, with whitespace-only normalization. Native paraphrases cannot supply literal quotes.
Source dates, units, signed/missing values, highlights, source context and transformations are
retained. Numerical interpretation and visual usefulness remain editorial judgments.

Plan 0070 includes the owner-requested visual style:
generated images omit internal production/test labels such as "illustrative data" and "not news".
Real source attribution, dates, units and material data qualifications remain. Excerpt cards
enlarge the selected passage to fill the content area in each preset; added copy must provide
useful context. Writer/editor guidance reflects this, and template version nbn-visuals-4 fits
the unchanged excerpt within doubled outer padding and readable-size/footer bounds. Duplicate
bottom-left NBN branding is suppressed; actual external sources and dates remain. Fixture status lives in
the proof directory's README rather than the pixels. See docs/planning/visual-style-2026-09-08.md.

A writer story lists visual_evidence_ids separately from its optional visual_asset_id attachment.
Normalization verifies the original run, story members, inspection and immutable bytes; existing
saved dossiers without image evidence remain valid. Evidence-only assets reach the editor even
with unknown reuse rights. They never receive attachment authority just by being evidence.
If required image evidence cannot reach the editor, or the editor is unavailable/omits the story,
the affected story is held rather than staged as an unreviewed text-only fallback. Usable siblings
remain eligible. Per-candidate image admission is atomic; repeated asset/hash pairs are sent once.
Retained Desk reviews preserve the original evidence ownership despite their new invocation ID.

Quote/excerpt source URLs follow the actual source_fetch_id. Data graphics retain source_urls
from the receipts actually referenced by their points, independently of evidence-list order.
Excerpt highlights honor all six approved colors and default to yellow. Line recipes default to
x_axis=time with distinct increasing YYYY-MM-DD dates and elapsed-day geometry. Explicit
x_axis=category means equally spaced observations. Closely spaced labels may be omitted for
legibility, but points and missing-observation gaps remain; complete data stays in the recipe
and the writer supplies an accurate alt description. Existing immutable assets are preserved.

Both writer and editor receive the exact immutable image bytes. Captions and metadata do not
count as inspection. The independent editor approves, omits or holds an image and separately
considers standalone text fallback. Approval binds final copy, asset hash, alt text and credits.
An unavailable editor cannot attach an unreviewed image or approve fallback text by default.
Unknown external-image rights mean review-only; explicit reusable status and retained permission
evidence are required before attachment. External-image credit is included in the source reply.
Text-only remains normal; there is no visual quota or new mandatory model turn.

Bounds: six shortlist pointers; two external inspections per story; four inspections and four
successful renders per run within the existing writer calls/deadline. Rendering does not spend
inspection returns; cached source/PDF reinspection still spends the per-story inspection limit. Static PNG/JPEG/WebP is limited to
4 MiB / 12 million pixels; downloads to ten seconds. Original-layout PDFs use the first 20 pages,
10 MiB input and ten-second combined download/render bound, without OCR or arbitrary crop.
Editor image context is separately limited to four images / 12 MiB base64; ordinary 256 KiB text
limits remain. Optional overflow is explicit, not hidden source/image truncation.

SQLite `visual_assets` stores immutable metadata; content-hashed files live in
`/data/visual-assets`. They and their evidence survive the 30-day writer-memory TTL. A 512 MiB
soft admission cap declines new optional assets rather than removing retained work; automated
pruning is not enabled. Observations store IDs/hashes, not base64. Visual counters record use;
image tokens are charged inside the existing writer/editor ledger, not a new image-model seat.

Typefully preparation is persisted in `visual_uploads`, then the existing publisher intent
moves from `awaiting_media` to `in_flight` only after a ready upload and matching alt text.
One bounded status poll happens per worker boundary; preparation expires after 15 minutes.
Lost draft acknowledgments/read-back ambiguity never trigger a second create or text fallback.
Full-payload identity includes ordered text/media, immutable asset/hash, alt and credits.
Media-level alt verification plus an acknowledged `{id, created_at, updated_at}` draft version
fences later edits. Present `updated_at: null` is valid; absent version fields are not proof.
Typefully does not expose draft-local alt text in draft GET, and alt-only UI version behavior
has not been empirically verified. Unknown or changed snapshots stay unresolved for review.
Legacy drafts with unrecorded media cannot be automatically replaced. `planned` remains an
inert DRAFT, not confirmed publication. See DESK-GUIDE.md for queued visual review controls.

## Delivery classes and safety

When autopost is enabled, `primary`, `secondary`, and `corroborated` editor-approved v2
stories may publish. `secondary` means one credible inspected report; `corroborated` means
two independent inspected sources; `primary` means an official source. Operator actions,
editor `draft` verdicts, newsroom draft mode, and source-policy observe mode always force a
Typefully draft.

Each new Typefully one-off is an exact two-post X thread: clean news copy first, followed
immediately by `Source: <verified receipt URL>`. Any image stays on the lead. Immediate delivery
is scheduled shortly ahead so receipt links survive platform rules. Confirmed delivery records as
`IMMEDIATE`; ambiguous confirmation records as
`UNCERTAIN` and is never automatically recreated. The kill switch is
`NBN_AUTOPOST_ENABLED=false`. Corrections remain human-reviewed.

## Cost and telemetry

`model_usage` records one row per attempted intake, preparation, research, newsroom, or editor API
call. It includes run ID, seat, requested/returned model, provider, effort, round, input/output/cache
and reasoning token counts, native web/X calls, latency, outcome, and cost provenance. Input
counts exclude cache reads/writes; reasoning is already included in output, not charged twice.
The usage ledger stores no prompts, article bodies, model reasoning text, or tool payloads.
Separate bounded observations retain safe business handoffs. The Desk shows period spend and
averages by stage/run/day/week/month; older Review diagnostics retain the $6/day target. The latest
run shows its initial packet size, newsroom calls/attempts, prepared receipts, and research assignments.
SerpAPI retrieval is counted separately in run diagnostics. This is recorded editorial-seat
usage, not a complete invoice: historical internal daily receipt-audit calls did not write
this ledger, and source API subscriptions/reads, hosting and the external Codex audit are excluded.

For xAI, reported cost ticks are authoritative and already include native searches. When unavailable,
the fallback estimate includes tokens plus observed tools. Other providers use rate estimates.
Unknown billing (such as a transport timeout) is explicitly labeled unknown, not free. The rate
version is `multiprovider-public-2026-09-05-v1`; per-model cache-read rates are separate. Anthropic
five-minute cache writes cost 1.25× input and one-hour writes 2×. The intended ceiling for a
productive due window is one preparation call, up to six combined Grok reporter-writer responses,
one editor call, and at most one omitted-only editor recovery—not a quota
on stories.

## EIC discovery, legacy Blocks, and audit

Fresh, provenance-valid Morning and Afternoon Marketing Node EIC briefs remain discovery
inputs. Their cited reads enter the ordinary one-off intake and must earn publication through
the same newsroom and editor as every other candidate. The scheduled multi-story Block product
is disabled by default; its implementation remains behind `NBN_BRIEFING_ENABLED=true` as a
rollback/experiment path. The legacy daily receipt audit is disabled by owner decision on
September 6 (`NBN_AUDIT_UTC` empty). Historical records and implementation remain; it no longer
calls a model or stages correction drafts on schedule.

The separate rolling production audit follows `AUDIT-AUTONOMY.md`. It may diagnose and repair
clear technical regressions and proactively ship obvious bounded tool, research-execution,
writing, Desk and efficiency improvements within the existing design (owner expansion September 7).
Its recurring procedure is maintained in `audit/rolling-audit-prompt.md`, with one mutable
checkpoint/work-status record in `audit/current-state.md`. Current health checks are separate
from bounded historical editorial coverage; old release notes do not restart completed work.
Local `scripts/audit_turn_context.py` recovers the actual Codex turn and original trigger from a
bounded session-journal tail, separately reporting new user steering. The task workspace's
`AGENTS.md` and recurring prompt require this check on entry and after compaction. Completed
requests stay closed; an unresolved trigger stops continuation for read-only investigation.
This is an agent-workflow safeguard, not a production worker stage or an app-level execution lock.
Bounded PDF-text reading is implemented within that authority; see
`AUDIT-IMPROVEMENT-2026-09-07-PDF-READING.md` for scope and verification.
Record rationale, test/deploy/smoke evidence, cost/behavior impact and rollback. Systemic design,
editorial-policy, source-weighting, model, cadence and significant recurring-spend changes still
require approval. Keep autopost OFF during calibration, including correcting unexpected drift.
Its emergency publication-safety authority is one-way: it may turn
autopost off when a systemic publishing problem is evidenced, must notify the owner immediately,
and may never turn autopost on.

## Operations

### Live Desk and review tools

Plan 0061 integrates the approved run-first React workspace as static assets on the existing
Railway HTTP server. Python remains the sole runtime. `/desk` follows the latest run;
Previous/Next and a timestamp picker pin history across dates. Decisions, Research, Delivered
desk, Copy and Activity share the selected run. At 1440+ CSS px the inspector is persistent;
below that it is a drawer. Supporting views are Intake, Outputs and System. Visible tabs poll
read-only JSON every 15 seconds without model/provider calls. Current worker/intake clocks are
separate from historical runs. `/report` is a focused owner queue with collapsed old diagnostics;
guarded handlers and anchors are unchanged. A saved researching checkpoint is not proof of activity.

Intake also exposes explicit **Send to newsdesk** for skipped leads. Authenticated POST records
a reconsider intent in operator_actions; it leaves the item untouched until the leased worker's
inventory boundary. Queued owner leads are prioritized and survive pre-writer filters, without
changing actual dates, cadence, model/editor judgment or duplicate/publication checks. Normal and
compact writer cards contain Brady's override and the prior skip reason. A validated writer
protocol response completes delivery of the intent; transport failure/truncation leaves it queued.
Stale held/drafted/delivered states are not rewound, and repeated POSTs are guarded by the latest
owner-action id. This is separate from legacy Stage draft overrides and does not force publication.

`run_observations` records safe final writer input, dossier, research returns and editor handoffs,
excluding raw provider envelopes/reasoning and credentials. Per row: 384 KiB. Per run: 80 ordinary
rows/1 MiB plus 40 critical handoffs/2 MiB. Limit markers and 14-day payload expiration are visible;
headers remain, including abandoned runs. Savepoints isolate nonfatal recording failures from
caller transactions. Publisher finalization merges rather than replaces editor details.
`source_poll_health` records ordinary existing polls, distinguishing zero results/errors and
preserving last-success time. No extra source polling is introduced. DESK-GUIDE.md specifies
cost denominators, coverage bounds, history gaps and all responsive interactions.

Counts distinguish first-seen items, new backlog, local outputs created, and confirmed
publications. Confirmation requires a published status and timestamp; IMMEDIATE mode alone
does not suffice. The remote account is broader than the locally tracked output log.
Replay/eval markers are excluded, and source time, first-seen, local output and publication
are separate clocks. See `DESK-GUIDE.md` for definitions and limitations. The dated visual
guide is `output/pdf/nbn-system-guide.pdf`, also available through the authenticated Desk.

### Worker and release details

- Database: `/data/nbn.db`; tape: `/data/tapes/`.
- Cross-run story workbench: `newsroom_story_memory`, 30-day meaningful-activity window; dated evidence
  eligibility, eight pooled receipts, 12 attempts, and a 96 KiB maximum serialized row size
  per event. A later empty retry cannot erase earlier valid inspected evidence.
- Every dossier story has a `newsroom_story_commits` lifecycle row with bounded validation,
  warning, editor, force-draft, and delivery details. Shadow observations terminate as
  `observed`; `pending` means materialization is genuinely unfinished.
- With `NBN_SEARCH_RESILIENCE_ENABLED=true`, SerpAPI requests use a complete, versioned identity
  and a bounded one-hour SQLite result cache. Result URLs are revalidated on both write and read;
  snippets remain untrusted pointers. Search pointers are attached only to the exact candidate or
  pre-existing story scopes the writer supplied, and may reappear on a later desk for up to six hours.
- A free, throttled SerpAPI account-status check supplies shared capacity state. Confirmed quota
  exhaustion and rate limits open a durable cross-run circuit until renewal or cooldown, while
  cached results remain usable. If the status endpoint is unavailable at renewal, one worker may
  hold a short expiring half-open probe lease; an abandoned lease can be reclaimed and a stale
  probe cannot overwrite newer state. Typed fetch and search failures are visible on the Desk.
- With resilience disabled, the legacy run-local circuit remains the rollback path: first 429 or
  second transport failure stops later provider calls in that run.
- Health: `/health`; status: `/status`; live Desk: token-gated `/desk`; existing actions: `/report`.
- Deploy a clean commit archive to the explicit existing Railway target; do not upload unrelated
  dirty work. See `HANDOFF-CODEX.md` and the latest plan's release record.
- Important knobs: `NBN_EDITORIAL_ENGINE=v2`, `NBN_DESK_INTERVAL_SECONDS=900`,
  `NBN_DESK_RECENT_FEED_HOURS=48`, `NBN_PUBLISH_ANALYTICS_SECONDS=900`,
  `NBN_INTAKE_TRIAGE_MODE=off|observe|enforce`,
  `NBN_INTAKE_TRIAGE_MODEL=claude-haiku-4-5`,
  `NBN_INTAKE_TRIAGE_MAX_CALLS_PER_HOUR=8`,
  `NBN_DESK_PREP_MODE=off|observe|enforce`, `NBN_COMPACT_DESK_ENABLED`,
  `NBN_HAIKU_RESEARCH_MODE=off|on`, `NBN_RUN_NEWSROOM_MAX_ROUNDS`,
  `NBN_SEARCH_RESILIENCE_ENABLED`, `NBN_SEARCH_ACCOUNT_TTL_SECONDS`,
  `NBN_SEARCH_CACHE_TTL_SECONDS`, `NBN_SEARCH_POINTER_TTL_SECONDS`,
  `NBN_SEARCH_PROVIDER_COOLDOWN_SECONDS`, `NBN_DESK_CLUSTER_COMPANIONS_ENABLED`,
  `NBN_MODEL_DAILY_TARGET_USD`,
  `NBN_EIC_DISCOVERY_ENABLED`, `NBN_EIC_DISCOVERY_UTC`,
  `NBN_RUN_NEWSROOM_MODE=shadow|draft|live`, `NBN_AUTOPOST_ENABLED`,
  `NBN_AUTOPOST_CLASSES`, `NBN_EDITOR_MODEL`, and `NBN_SOURCE_POLICY_MODE`.
- `NBN_EDITORIAL_ENGINE=v1` is a short-lived manual rollback switch only. It is never an
  automatic fallback. Remove it after the v2 observation window.
- Never print credentials. Never delete an ambiguous Typefully/X output automatically.

The production orientation source of truth is `prompts/orientation-brief-v2.md`; the Desk
exposes that exact loaded brief in a collapsible panel so Brady can review it.

Human-approved positive and negative examples accumulate in
`prompts/orientation-examples.md`. That file is a review queue, not a runtime prompt include;
examples enter production only through a deliberate orientation-brief revision.
