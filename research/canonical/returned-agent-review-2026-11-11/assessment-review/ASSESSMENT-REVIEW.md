# Independent assessment/source review — 2026-11-11

Scope: returned `workspace/lat-ai/integration/ai`, compared with old canonical `work/lat-ai`; related assessment reports, source tests and local-profile builder read. No live model inference, load/unload, shared lock/process operations, browser operations or edits to returned evidence. Tests ran in `assessment-review/test-source`, copied from returned source, with old cached Ajv 8.17.1 dependencies. Node v24.11.1.

## Result

The returned implementation contains substantive, reproducible work: two separately prompted model passes; per-criterion agreement gate; bounded original-answer spans; a read-only receipt lookup with identity/revision conflicts; and synthetic tests for abort, durable pending, isolation and lost HTTP. No new release-blocking implementation regression was established in this review. This is not pedagogical acceptance or permission to deploy automatic grading.

### Independently rerun

- Integration suite: **80/80 pass**, 0 skipped, approximately 8.47 s (`integration-node-tests-localhost.log`). Initial restricted attempt was 75/80: five ephemeral localhost fixture failures (EACCES / no dispatch), not product failures. Explicit sandbox escalation allowed the inspected loopback-only fixtures; the full suite then passed.
- `integration/ai/check.mjs`: 3 schemas, 2 request examples, 6 response examples, 20 pinned core files, 2 synthetic generators, **0 live model calls** (`integration-contract-check.log`). This validates recorded hash consistency, not provenance authenticity or semantic correctness of the new prompts.
- Independent deterministic replay of 160 saved model outputs: **136 match author labels, 1 mismatch, 23 refusals; 0 decision changes; only V11 evidence changes**. See `verify-replay.mjs` and `independent-replay160.json`. This corroborates the v3e report; it is explicitly NOT 160 new neural tests or a new holdout.

## Material unresolved findings

1. **Known wrong score remains reproducible from saved output (V05).** `outputs/assessment-v3-2026-11-11/holdout-review.txt` documents answer “Плюс означает конкатенацию строковых значений. Содержимое вывода я здесь не называю.” Author expectation is `[true,true,false]`; both passes produce `[false,true,false]`. Current validator reproduces it. `integration/ai/core/src/assessment.mjs:38–43` only requires agreement of decisions; two same-model calls do not independently establish truth. This is openly acknowledged by the handoff and is an unresolved quality defect, not evidence of a concealed regression.
2. **Correct answers can still be refused.** U02/U26/H18 and other cases remain unresolved. Historical repeated runs demonstrate stable refusals as well as stable correct outputs. They cannot be counted as successful accurate grading, and repeated versions of the same answer cannot increase independent sample size.
3. **Default source timing is incompatible with the reported weak-PC two-pass latency.** `integration/ai/lifecycle.mjs:10` sets 7900 ms; `core/src/tutor.mjs:25` enforces maximum 8000 ms. Returned historical new32 median is 10.32 s/max13.94 s; latest two known-case smoke timings are14.43/10.13 s. The separate machine-bound local profile uses60000/70000/80000 ms, but the imported profile is bound to `DESKTOP-VBSRT7B`. Its builder modifies only disposable copies and fails on another hostname. These measurements do not establish behavior on this current PC/model. No long-budget local-profile run was performed here.
4. **Receipt recovery is an AI-only building block.** `assessment-receipt.mjs` reads the durable result and does not regenerate; absence/pending/completed/identity-conflict behavior passes tests. The handoff explicitly leaves Django reconciliation, manual-grade priority, user-facing recovery/history and class-scale asynchronous queue unimplemented. Tests include killing a child with stub inference, not crashing real LLM/Django after a live request.
5. **v3e is a targeted citation adjustment, not a general semantic validator.** `assessment-evidence-context.mjs:4–19` only handles `L1.condition.1`, uses regex/unique-fragment matching to extend positive spans and never changes checks. It cannot establish that the appended context is semantically correct. Refusals and jointly wrong decisions are unaffected. Tests cover notation, decimal exclusion, ambiguous context and exact CRLF preservation. The replay confirms the claimed narrow effect.

## What tests do and do not establish

The new tests meaningfully exercise two-pass dispatch, no verification after malformed proposal/abort, aggregate token accounting, disagreement by criterion rather than total score, strict evidence references, corrupt/closed journals, actor isolation, revision conflicts and pending persistence. Their model outputs are scripted. `assessment-generation.test.mjs` exercises native sampling parameters with malformed `{}` only; it does not establish successful native-protocol grading (the production lifecycle uses the structured default). Current native path has no positive terminal stop proof and remains fail-closed, as in the old source.

The 335 archived baseline tests belong to an older core and are not evidence of current prompt quality. The historical synthetic datasets and their author labels are useful regression evidence, but there are no real student works, independent blind human labels or approved release criteria. Current/old model artifact hashes differ according to the root audit; historical latency/quality must not silently be attributed to the old local model.

The original source, frozen outputs and reports were read only. Test fixtures that create journals relative to their test directory were run exclusively in the isolated copy. No unknown model POST was issued or repeated.

