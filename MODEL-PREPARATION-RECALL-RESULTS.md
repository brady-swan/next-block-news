# NBN preparation-model editorial recall test

> Status reviewed 2026-09-06: Historical design/evaluation record. Preserve dated findings; later releases may supersede the proposal. For the current system, see [DOCUMENTATION.md](DOCUMENTATION.md) and [SYSTEM.md](SYSTEM.md).

- **Evaluated:** September 5, 2026
- **Frozen corpus:** 300 raw cards in six RSS-intake and six assignment-desk batches
- **Gold set:** 33 high-confidence must-forward leads and 68 high-confidence safe-background
  items; ambiguous cards were excluded
- **Meaning of must-forward:** the item should reach the newsroom for judgment, not necessarily be
  published
- **Production changes:** none

## Bottom line

Use a split preparation stack:

- **Haiku 4.5 for RSS/EDGAR intake.** It had better recall and perfect transport reliability in
  the two balanced comparison repetitions.
- **Luna low for the run-scoped assignment desk.** It recalled every labeled worthwhile lead,
  failed open less often, reduced more obvious noise, and cost about 84% less than Haiku on the
  same packets.

This hybrid dominated either single-model stack on the measured objective: 65/66 must-forward
records recalled, all 40/40 core Bitcoin records recalled, 21/24 valid batches, and 70/138 known
background records suppressed. Its measured test cost was $0.235031 versus $0.573879 for
Haiku-only, a 59% reduction.

## Recall and workload

The balanced Haiku-versus-Luna-low comparison uses repetitions 1 and 3. Repetition 2 is excluded
because a stale local OpenAI credential produced seven 401 responses before the run was stopped;
the failed attempts remain in the evaluator ledger.

| Stack | Must-forward recall | Core Bitcoin recall | Safe-background suppression | Valid batches | Cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| Haiku everywhere | 63/66 (95.5%) | 40/40 (100%) | 62/138 (44.9%) | 19/24 | $0.573879 |
| Luna low everywhere | 61/66 (92.4%) | 39/40 (97.5%) | 70/138 (50.7%) | 19/24 | $0.093358 |
| **Haiku intake + Luna assignment** | **65/66 (98.5%)** | **40/40 (100%)** | **70/138 (50.7%)** | **21/24** | **$0.235031** |

### RSS/EDGAR intake

| Model | Must-forward recall | Core recall | Safe-background suppression | Valid batches | Cost | Mean latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Haiku 4.5** | **31/32 (96.9%)** | **16/16 (100%)** | 17/30 (56.7%) | **12/12** | $0.171173 | 20.2s |
| Luna low | 27/32 (84.4%) | 15/16 (93.8%) | 17/30 (56.7%) | 10/12 | $0.029500 | 15.9s |

Haiku's only intake miss in the balanced comparison was one classification of Brent above $96
after Iranian missiles hit Kuwait as background. Luna low repeatedly backgrounded a major US-Iran
oil escalation and an SEC novel-ETF rules story, and once backgrounded Bitcoin's 5% move tied to
dollar weakness and suspected Japanese intervention.

### Run-scoped assignment desk

| Model | Must-forward recall | Core recall | Safe-background suppression | Valid batches | Cost | Mean latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Haiku 4.5 | 32/34 (94.1%) | 24/24 (100%) | 45/108 (41.7%) | 7/12 | $0.402706 | 65.0s |
| **Luna low** | **34/34 (100%)** | **24/24 (100%)** | **53/108 (49.1%)** | **9/12** | **$0.063858** | **43.8s** |

Haiku missed two borderline but plausibly useful monetary leads: a yen carry-trade unwind ahead
of a Bank of Japan decision and the two-year Treasury yield reaching its highest level since
January 2025 after a hot jobs report. Luna low missed none of the labeled assignment leads.

The assignment result is the clearest finding in the test. Haiku's malformed batches were also
slow—about 67 seconds on average—and fail-open sent all 25 cards onward. That preserves recall but
defeats the attention-saving purpose of the assignment desk.

## Luna medium intake check

Luna medium received two additional complete intake repetitions after the answer key was fixed.
It was fast, inexpensive, and mechanically reliable, but more aggressive than desired for a
recall-first intake layer.

| Model | Must-forward recall | Core recall | Safe-background suppression | Valid batches | Cost | Mean latency |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Haiku 4.5, matching repetitions | **30/32 (93.8%)** | **16/16 (100%)** | 20/30 (66.7%) | 12/12 | $0.168668 | 19.9s |
| Luna medium | 29/32 (90.6%) | 15/16 (93.8%) | **29/30 (96.7%)** | **12/12** | **$0.029609** | **12.0s** |

Luna medium is an excellent noise filter, but that is not the primary objective of this lane. It
backgrounded the US-Iran tanker escalation in both runs and the Bitcoin/yen-intervention story in
one. Keep it as a future option if intake volume becomes the bottleneck; it does not beat Haiku on
editorial recall today.

## Interpretation and limits

The gold set was created retrospectively from the approved orientation and recorded owner
feedback. To reduce hindsight overfitting, only clear must-forward and clear background examples
were scored, and the must-forward pool was separated into 20 core Bitcoin/policy/data leads and
13 broader monetary edge cases. Borderline material was omitted.

Invalid model output is scored two ways in the analysis. Operationally it is a forward because the
production system fails open. It is also counted as a reliability failure and workload penalty;
otherwise a model could appear to have perfect recall merely by returning unusable output.

The test establishes a safe routing candidate, not permanent model supremacy. A production
shadow should compare identical live packets before any enforced switch, especially because the
sample represents one news cycle and macro judgments remain the main source of disagreement.

## Evaluation accounting

The complete model-evaluation ledger now charges $4.18971672 against its independent $40 lifetime
cap, leaving $35.81028328. That total includes conservative full reservations for interrupted or
failed calls; it is not all confirmed provider spend.
