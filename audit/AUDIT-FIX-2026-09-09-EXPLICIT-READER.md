# Explicit reader receipt contract follow-up

Status: implementation and independent review APPROVED; deployment pending. Baseline b8c3410/c3e066d runtime; prior v2.33 source execution clarification is complete and is not repeated.

New production evidence: fe723e1d, observations3757–3758, current Lam draft10700703. Editor identified the supplied reader link as unrelated Emirates NBD, selected DOJ/NYT appendix evidence, and said to point readers to DOJ, but omitted reader_receipt_ref. The optional schema/validator accepted omission as null and preserved the wrong source. Both current draft and earlier Lam10668499 were read; the new draft is also a duplicate. The duplicate/prior-memory issue is separate and is not solved by this repair. Audit comment f1ee7d59-bc06-4cad-b665-ce8def882254 confirmed; no draft edits.

Authority: bounded execution improvement under AUDIT-AUTONOMY.md. Main coordination confirmed no overlap with its owner-approved LOCAL packet experiment and explicitly preserves null-as-retain/no prose inference. Independent lead reader_receipt_required_review approved this scope before implementation.

Change: require an explicit reader_receipt_ref in generated text/visual/recovery schemas and instructions; reject missing non-drop choices through existing omitted-only single recovery. Null retains current source, exact candidate/selected appendix references remain eligible, and legacy missing-field drops remain valid locally. No extra retry, source policy, model, budget, memory or publishing change. Version v2.36-reader-receipt-contract.

Limits: explicit null can still be semantically wrong. An omitted choice may consume the existing recovery call, increasing latency/cost. If recovery fails, current original-copy/source human-draft fallback remains; this is not guaranteed wrong-source prevention. No model replay or manual production draft rewrite is part of validation.

Validation planned: schema propagation, all non-drop omissions, null/legacy drop, permitted/excluded references, valid sibling preservation, recovered source agreeing in delivery and memory, repeated omission preserving original human fallback, full clean suite and independent final diff review. Deploy from clean reviewed commit, online backup, exact runtime/health/Desk/config/ordinary worker smoke, restore same audit automation. Natural later outcomes observed without forced paid replay. Roll back clean code to prior runtime if smoke fails; no database restore.

Independent final review approved the code and strengthened regression. Reviewer caught identical original/revised test copy; corrected to distinct supported copy, then both recovered and repeated-omission branches passed.107affected tests passed. Clean archive5e1ae1a passed694tests32.823s; final clean archive validation follows after that test-only strengthening. No paid models, production draft changes or semantic guarantees.
