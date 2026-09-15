# Overnight audit — September 15, 04:23 UTC

## Scope and health

Verified main heartbeat `01a0a34d-eb4b-7761-a604-6bd31e02ab00`, scheduled04:23:07.849UTC.
Reverified actual journal after compaction and before operator guidance; no new user steering.
Fixed snapshot04:23:29.386UTC covers records1537–1574 and two completed outcomes1557/1573.
Those outcomes are fully reviewed. Subsequent turn1575+ is NOT yet fully audited; its rate-odds
acknowledgment and CoinEx delivery problem received targeted follow-up below.

Same `pilot-20260915T025357Z`, original13:00UTC cutoff and reporter thread, active renewing lease.
AutopostOFF, infrastructure mode,42 drafts/three overnight at snapshot. Collector04:23:16UTC:
346 fetched/two new; no legacy editorial dispatch, as intended. Typefully sync complete:
42 candidates, two detail reads, two comment reads, comments_deferred=false. No pending
submission rows at exact-read04:25:12UTC. No new code deployment, restart or model change.

## New draft: DOJ's USDT forfeiture mechanism

[Draft10772041](https://typefully.com/?a=329191&d=10772041) is a useful source-follow-through
example. The Block's04:01:48 tip led to the original September14 DOJ release and its attached
complaint, case1:26-cv-08010. The reporter read physical pages1–3 and original page3 pixels,
then rendered the complete footnote1 as an original readable excerpt. The audit independently
read the full original release through web, the retained relevant PDF text, original page3
pixels and final graphic. It did NOT read the entire25-page complaint. Audit webPDF open
failed; existing immutable source/rendered assets were inspected instead, not a bypass fetch.

Source release: https://www.justice.gov/usao-sdny/pr/us-attorney-seeks-forfeiture-61-million-cryptocurrency-iranian-militarys-black-market
Complaint/first reply: https://www.justice.gov/usao-sdny/media/1461216/dl

- The release supports approximately$61million and the alleged Iranian oil proceeds/Chinese
  companies' Binance accounts. This is attributed civil-forfeiture reporting, not a finding
  of guilt or an allegation that Binance itself is the defendant.
- Footnote1 describes Tether burning targeted tokens and issuing equal-value replacements
  for government custody. The draft and image preserve future tense, not a completed transfer.
- Direct release fetch was empty; reporter-retained native-web text is correctly distinguished
  from the direct complaint receipt. Audit independent release inspection supports those details.
- Source PDF SHA256 `3325270bb886085a975308d50b18b0f2e91c6f9133162dd9ba2191ae5ddde231`;
  complaint receipt `receipt:3eac1a9d74fe4d81827f5701001bf746`.
- Original page `visual_52e052f453418911124446509fc04ba5`; rendered excerpt
  `visual_5158fd31b039be046f3cb295752cc14f`; attached Typefully media
  `1ac7cab7-56a2-4f5c-ab58-037fed9f3b40`. Complete footnote, legible type/highlight, visible
  DOJ civil-complaint credit and filing date. No clipping or invented words. Asset legacy
  writer_inspected_at is null; this reporter path records inspection separately in records,
  which its delivery guard verifies against exact content hash. Do not call null an omission.
- Stable submission `nbn-20260915-doj-usdt-seizure-v1` is staged; same-payload media completion
  produced one draft. No existing-draft text/media/publishing changes.

Editorially, the research/image is stronger than the lede: the issuer-control mechanism is the
distinctive finding. Suggested concise rewrite in one consolidated Typefully comment:

> Tether will destroy targeted USDT tokens and issue replacements for U.S. government custody,
> a September 14 court complaint says.
>
> U.S. prosecutors are seeking forfeiture of about $61 million they allege came from black-market
> Iranian oil sales.

This is advisory, not owner endorsement, publication approval or a required rewrite. It retains
allegation/planned-action attribution without an extra generic disclaimer. Source reply/image
remain useful. Comment `3db5d758-87c8-4724-84e0-256944496740`, thread
`115ed170-7c3e-4f75-9ef2-47bfb74bb25f`, POST20104:29:40.457UTC; exact readback and full
reader-visible equality confirmed. No pending comment write; do not repeat.

## Selection, misses and continuity

All six newly stored intake title/summary rows from previous boundary04:01:37.051 through
04:19:41.531 were read: DOJ, CoinDesk counteroffer, two Livera posts, WatcherGuru coalition,
and Rizzo vote rhetoric. Linked podcast/reply/video context was not fully reviewed; earlier
pre-shift raw-pool gaps remain. This is not a claim of complete24-hour miss coverage.

Reporter1569 investigates whether a CLARITY counteroffer was actually transmitted, beyond the
planned counterproposal already associated with10769444. Direct CoinDesk429, native open
failure, browser timeout, older search matches and an empty corrected X query did not establish
the new fact. Deferral preserves the question without calling it false or producing a duplicate.
AG coalition repeats10765173; vote rhetoric supplies no verified completed action. Those passes
are reasonable on the retained evidence, not proof all linked context lacked value.

Reporter1563 read the earlier cost-chart audit comment and retained its scope correctly. This
is evidence of continuity, not independent endorsement of our own opinion. Handoffs1555/1571
preserve useful source IDs, exact output IDs, open questions and original cutoff.

### Targeted later follow-up: rate-odds question answered

Question1561 was delivered to turn01a0a34f-7ad9-7273-bbe8-434e0db54874 and acknowledged
04:25:33.089UTC, record1585. Reporter inspected actual photo `visual_3792c5ab162338134948dae40a15d5a5`:
reported US Fed September16 meeting, current350–375bp,93.5% at375–400bp/6.5% unchanged, with
no as-of timestamp or historical comparison visible. It explicitly corrected its overly broad
prediction-only dismissal: market pricing can be reportable, but this snapshot alone did not
demonstrate a material change. No independent current CME validation claimed. The AUDIT has not
yet inspected this image's pixels; preserve that distinction. This response was audit-assisted,
not an unaided improvement or a new editorial policy. Do not resend the answered question.

### Targeted later incident: CoinEx source identity preflight

New accessible Cointelegraph reporting led the reporter to the CEO's complete original X post
`2099680499094737251` with a concrete closure/withdrawal date. Reporter attempted its already
self-reviewed text-only draft, but409 selected-source validation rejected handle-form URL while
the evidence retained `https://x.com/i/status/2099680499094737251`. The generic client wrapper
called it uncertain. The reporter correctly stopped and asked, rather than inventing a new ID.

Read-only production diagnosis at04:32:18.411UTC found NO matching submission, publisher intent,
post or remote-coverage row. Live `reporter_delivery.py` SHA256
`2ef330e367e8ccd96d01a11be7be4722a30e580ce9b4790c09a1b53c1c344c81` matches inspected local code;
that exact validation happens before intent/submission insertion and before remote dispatch.
This is a proven preflight rejection, not an ambiguous Typefully mutation. The original full
CEO evidence1581/`receipt:2df69af11fc544cd98815689deaf74b5` was read, including actual author,
post identity, withdrawal deadline and explicitly attributed backing assurances. First diagnostic
SELECT used an incorrect column and failed read-only; corrected canonical_key query succeeded.

Operator message1601 `audit:20260915:coinex-preflight-url` stored once/read back exactly. It
explains the proof and tells the reporter, conditional on current coverage still being clear,
to use the exact evidence URL with the SAME unused ID/event/body/self-review. No accepted payload
may be changed; any genuinely accepted/uncertain state still requires read-only reconciliation.
No submission was sent by the audit. Acknowledgment/delivery result remains PENDING at closure.
Do not resend this guidance or call the CoinEx draft staged yet. This narrow execution workaround
changes no source standard and requires no production deployment. Future usability improvement:
distinguish pre-dispatch validation failures from uncertain dispatch and avoid X URL-form traps,
but no code change has been made or queued as an already-approved build in this pass.

## Timing, usage and next action

DOJ: The Block04:01:48 → first_seen04:02:30.225 → Typefully04:08:43.556.
Tip-to-draft6m55.556; ingest delay42.225s; first-seen-to-draft6m13.331. Complaint filedSeptember14,
exact original release time unknown, so not first-disclosure speed. No X publication.

Usage1574 cumulative reporter-session input16,865,051, cached15,983,488, output25,900 including
1,133 reasoning; last input97,624. These are ChatGPT allowance counters, not API dollars;
do not sum cumulative snapshots or treat the last request as the whole turn. No account/reset/
model change. Shared allowance was not queried again on this short interval.

NEXT full editorial interval starts1575, prioritizing CoinEx1601 acknowledgment/result and
rate-odds actual pixels if needed. Record targeted checks above without skipping other later
outcomes. Keep exact13:00UTC cutoff and draft-only boundaries. No repair/pause/restart in flight.
Evidence: workspace `output/reporter-overnight-20260915-0423/` fixed snapshot, exact-read,
immutable PNGs, comment intent/delivery and preflight/guidance receipts. All previous repairs,
owner-feedback delivery and comments remain completed; do not replay them.
