# Returned-agent evidence review — 2026-11-11

The central numerical claims reconcile with the saved evidence. The work provides substantial engineering and synthetic diagnostic evidence, but does not establish student-facing grading quality or complete the requested isolated SDK cancellation experiment. No new material arithmetic inconsistency or concealed success/failure substitution was found in the reviewed current reports.

## Scope and reproducibility

Reviewed the four supplied inbox documents, all 18 immediate stage `REPORT.txt` files listed with SHA in `report-inventory.json`, relevant raw result files/summary files, SDK helper v1/v2, isolation policy, their tests, the SDK live runner/read-only runner and installed SDK load implementation. Audit-tool implementation tests, current-source scope comparison and archive verification belong to the parent review and are not claimed here.

Source root throughout this report: `C:/Users/ASUS ROG STRIX/Documents/Codex/lat-return-1111/workspace`. The exact absolute input paths and computations are recorded in `recompute.mjs` and `recomputed-metrics.json` in this review directory. Re-running `node recompute.mjs` only reads the imported workspace/inbox and writes review artifacts beside itself. It neither imports nor executes project inference/runtime code.

No model load, inference, unload, shared-process mutation, browser, network request, source/prompt edit, lock removal or historical-result rewrite was performed. Historical runtime evidence is not a statement about current ready/idle/ownership. Node used: `C:/Program Files/nodejs/node.exe`, v24.11.1. The default Python executable was an unusable WindowsApps alias; computation used Node instead.

## Priority findings and limits

1. **P1 — Correlated two-pass mistakes remain an unresolved grading defect.** In `outputs/u02-runtime-controls-2026-11-11/known128-live-3/R3-U02.json`, expected TTT becomes FTT because both passes give FTT. In `.../R3-U46.json`, expected TTF becomes TTT: proposal loses the contradiction counter and verifier accepts all criteria. The latter explicitly disproves the proposed policy of automatically releasing every full score. These are existing defects disclosed in the latest report, not newly introduced bugs. They justify retaining experimental/shadow use until quality acceptance; this review does not prescribe or implement a new grading policy.

2. **P1 — Real-world acceptance is still absent.** Reports consistently identify author-created cases, four known tasks, no real student returns or independent human labels, and open T01/S02/D01/D02. The known128 scan contains 128 unique task+answer pairs and 384 observations in three load/order clusters; 768 POSTs are not independent trials. It excludes V01–V32, so does not retest V05. A formal zero-of-109 one-sided 95% upper bound is 2.7109%, already above the suggested 2% target; synthetic selection and correlated observations prevent interpreting even that bound as a student population guarantee. Technical fixtures and UUIDs are not people or evidence of their independence.

3. **P2 — Requested isolated SDK normal-load/forced-abort remains NOT_RUN/BLOCKED.** `outputs/sdk-isolation-live-2026-11-11/readonly-live/summary.json` explicitly records `helper_load_exercised:false`, `load_unload_inference_calls:0`, both live statuses `NOT_RUN`, and `blocked_before_model_dispatch`. `tools/sdk-isolation-policy.mjs` is a declarative checklist, always returns `model_dispatch_supported:false`, and implements no launcher, process ownership or Windows job containment. The user asked to conduct the experiment; preparing a plan plus reading shared-server metadata is incomplete fulfillment, though the report states this honestly. Resources/independent environment are the blocking condition, not an existing proof that isolation is impossible.

4. **P2 — SDK deadline fix has a narrow proven scope.** `tools/sdk-load-with-deadline.mjs` and `...-v2.mjs` clear a managed timer after load settles; v2 validates integer 1..2147483647ms. Installed `work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs:8448` attaches an abort listener that sends cancel and rejects, with no listener removal upon successful load in the inspected method. Clearing the wrapper timer addresses that late-signal path. It does not itself prove the server stopped provisioning after cancellation, enforce process containment or bound a noncooperative SDK Promise. Offline tests use cooperative stubs. v1 has historical successful-load/dispose evidence; v2 normal live and forced abort have no completed evidence. Do not relabel either as a fully verified timeout lifecycle.

5. **P3 — Specify normalization when quoting “raw verifier changed in 14/128.”** The historical analyzer parses JSON and sorts keys; that comparison reproduces 14. Literal saved answer strings differ in 17 cases, including formatting differences. Proposal is 11 under either comparison. The 14 figure is valid for parsed raw JSON structure/values, not byte-for-byte text equality; it is not semantic citation accuracy. This distinction does not change any grade/refusal totals.

6. **Historical overstatements already corrected in later evidence.** The pasted review at `CHAT_READABLE.txt:673` says errors appeared in “5 из 8 загрузок.” Raw diagnostic results show 5/12 observations, but only 3/8 loads. The same historical review's suggestion that disabling checkpoints would identify a cache mechanism is too strong: checkpoint0 changes both pass vectors and produces refusals, not correct U02 grades. `u02-runtime-controls.../REPORT.txt` and current inbox context correctly qualify both claims. The two within-instance three-U02 sequences support a limited observed persistence, not a general rule that a mode always locks after first U02.

## Recomputed accepted evidence

| Evidence | Correct | Wrong | Refused | Additional result |
|---|---:|---:|---:|---|
| evidence-v1 selected dev48 | 48 | 0 | 0 | Development-selected, not holdout |
| evidence-v1 first unseen48 | 44 | 4 | 0 | U02/U26 under; U22/U46 over |
| H32, v2 H live | 26 | 0 | 6 | Joint checks+frozen anchors 26 |
| V32, v3 live | 25 | 1 | 6 | Joint24; V05 error; V11 quote-only failure |
| known128 series1, primary | 109 | 0 | 19 | All refusals review_disagreement |
| known128 series2 | 109 | 0 | 19 | All refusals review_disagreement |
| known128 series3 | 107 | 2 | 19 | U02 under/U46 over |
| stability48 per-case artifact | 18 | 0 | 30 | 8 texts ×6; outcome stable within these runs |

H32 and V32 have zero shared IDs and zero exact task+answer pairs. Their current files match their frozen hashes: H `75c601d9f0048765018036f65012e771acd958206cc93a0b7337b4fb89a8773a`; V `e7b76a978660d54f5a70b6c2abda42e62f792d64ca507e820aec55db95e36e30`. H32 was not silently recounted into V32. Joint recomputation used the predeclared exact anchors, actual evidence substrings and checks from per-case raw results; this reproduces a text-coverage oracle, not an independent semantic judgment.

Exact primary input folders:

- `outputs/assessment-fix-2026-11-11/candidate4/`
- `outputs/assessment-unseen-2026-11-11/first-pass/`
- `outputs/assessment-evidence-v2-2026-11-11/candidate-h-holdout/` with sibling `holdout32.json`
- `outputs/assessment-v3-2026-11-11/holdout32/` with sibling `holdout32.json`
- `outputs/u02-runtime-controls-2026-11-11/known128-live-1/`, `-2/`, `-3/`

For known128, independently checked all 384 result hashes and all 1164 provenance-hash entries, execution orders and per-series result counts. Recorded normalized proposal/verifier request hash pairs match for all 128 cases across three series. Every result has two HTTP200 terminal stage records: 768 total. Summaries report no unknown/not_run entries, no retries and retirement proven; these are historical evidence, not current runtime probes. Full HTTP-body bytes are not retained for the scan; this limits independent reconstruction from SHA.

Final vectors/refusal vary in exactly seven IDs: N07, N11, U02, U22, U29, U46, H14 (7/128=5.46875%). Final evidence/refusal differs in seven. All three series have 109 issued grades but the identities of refusals change. Median observation latency is 10769.41355ms; max16451.4391ms, matching reported10.77/16.45s. No classroom concurrency or arbitrary worst-case latency was established.

U02 diagnostic investigation: 12 raw observations from eight loads, 5 undergrades/7 refusals; by first outcome per load, 3 undergrading loads/5 refusing loads. The raw files are resolved from `outputs/u02-investigation-2026-11-11/investigation-summary.json` and retained exact paths in `recompute.mjs`. Checkpoint experiment: independently counted20 raw assessments/40 calls/eight instances; 12 non-U02 correct, U02 two wrong and six refusals. For32+A, proposalTTT/verifierFTT;32+B,FTT/FTT;0+A/B,FTT/TTF. `process_completed_normally:false` is preserved; terminal rows do not turn the exit1 run into a successful process run.

Historical SDK v1: `outputs/sdk-fix-and-history-scan-2026-11-11/sdk-live/events.jsonl` shows completion23702ms after S1's deadline and3016ms after S2's deadline, after disposal. S1/S2 each retain two terminal HTTP200/stop bodies. This supports survival after two successful loads, not timeout/forced-abort behavior. The later shared-server SDK smoke's five-second hold never creates a load timer.

## Tests performed now

The SDK portion executed three local test files with Node `--test`: `tools/test-sdk-load-with-deadline.mjs` (4), `tools/test-sdk-load-with-deadline-v2.mjs` (6), `tools/test-sdk-isolation-policy.mjs` (8). **18 passed, zero failed/skipped/cancelled; exit0.** Full output: `sdk-offline-tests.log`; exit code: `sdk-offline-exit.txt`. These modules use Node builtins, mocks and the helper/policy files; they do not import the real SDK or call any server. They check timer cleanup, deadline validation, mock cancellation, caller-signal ownership and refusal/checklist logic only. No success claims for live forced abort, normal v2 load, SIGINT, late provisioning, memory peak or Windows containment follow from them.

The independent metric script completed successfully; log `recompute.log`, structured output `recomputed-metrics.json`. Stability48 was recounted from its per-case derived metric artifact rather than revalidated through production parser. Other stage test totals were read as historical claims, not rerun or added together. Their suites overlap; repeated passes do not increase independent test coverage.

### Additional frozen-runner offline coverage

At the parent's follow-up request, statically inspected and executed `tools/test-frozen-assessment-run.mjs` (11 tests) and `tools/test-frozen-assessment-run-v2.mjs` (17 tests). Their dependencies `frozen-assessment-run*.mjs`, `assessment-environment.mjs`, `analyze-frozen-pilot*.py` and `assessment-statistics.py` were inspected before execution. All actual test entry paths inject fake models, generation, retirement and validation; v2 additionally supplies fake environment and model metadata. Generated datasets/plans/results are synthetic fixtures under `mkdtemp(tmpdir())`. The paths named `run-*.mjs` are hashed as dependencies, not executed. The real LocalModel dynamic-import fallback and live environment capture are not reached by these tests.

**Exact original run:27 passed,1 failed,exit1.** The sole failure is the final v2 analyzer test at `tools/test-frozen-assessment-run-v2.mjs:64`: it attempts `work/runtime/python-env/python.exe`, which is absent in the extracted workspace (`ENOENT`). This is an environment/portability dependency, not an observed runner assertion regression. Both test files were executed unchanged from the imported workspace cwd, with TEMP/TMP directed into this review's `frozen-runner-tmp/exact`. Evidence: `frozen-runner-exact.log`, `frozen-runner-exact-exit.txt`. Do not describe the unadapted transferred package as28/28 on this machine.

**Adapted rerun:28 passed,0 failed/skipped/cancelled,exit0.** Review-only `frozen-runner-preload.mjs` redirects only that exact missing interpreter invocation to `C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/work/tester-release/LAD AI Windows/runtime/python/python.exe`, adding `-B` to prevent bytecode writes. It verifies the analyzer script path and all fixture arguments, blocks other execFileSync subprocesses and global fetch, and leaves the imported source/tests unchanged. All fixture paths are under `frozen-runner-tmp/adapted`; no junction or runtime copy was created. `frozen-runner-harness-observations.jsonl` records two Python calls (valid analysis and expected rejection of altered history), zero attempted global-fetch calls and normal test-process exits. Logs: `frozen-runner-adapted.log`, `frozen-runner-adapted-exit.txt`. SDK18 were not rerun.

Coverage now includes freeze/source/data/rubric drift, result persistence and no-overwrite, fake transport and response-body loss with no retry, explicit not_run/unknown, disagreement refusals, fake unproven retirement, v2 distinct permutations, environment/config drift, file fingerprints and ID-aligned three-series analysis that rejects manipulated history even after local rehashing. These are offline engineering checks; they establish no live load/inference/unload, actual server retirement, Windows containment, real-student labels or population grading quality. The rerun is a repeat of28 tests, not28 additional unique tests beyond the first run.

## User decisions versus agent proposals

Source is the imported `C:/Users/ASUS ROG STRIX/Desktop/ыы/CHAT_READABLE.txt`. Full historical USER blocks with source line numbers are in `historical-user-messages.json`. They establish provenance, not new permission for this review.

- Line75: adjust limits for this weaker PC only. The 60/70/80s choice is the agent's measured local operational margin, not a user-established universal maximum.
- Line113: rename to LAT AI and restrict work to the neural/AI part; backend/frontend belong to other developers. Line127 requires reports/logs.
- Line335: sequential roadmap work until unexpected events or a need for manual checks.
- Line395: explicit answer “Пока нет — подготовь пакет сбора и ручной проверки” to whether real student answers/teacher grades exist.
- Line548: explicit answer “дата завтра.имя разраб 1 П”. Reports interpret this as start12.11.2026 and coordinator разраб1П; it is a plan, not proof collection happened.
- Line603 onward: explicit freeze on prompts/backend/frontend, repeated in subsequent specific requests.
- Line758: fix SDK completion failure, check live, run frozen128 in three orders. The subsequent completed scan fits that request.
- Lines894,1032: explicitly consult the open Claude and send stage reports. Saved Claude notes describe reviews of narratives/selected snippets, not independent code audit or teacher labeling.
- Lines1080,1107,1140: implement readable fragments/cards, intake validation and recovery/amendments. Line1204: continue work possible without real answers/manual checks.
- Line1244: explicitly asks to prepare AND conduct isolated SDK live check, without touching shared model. Conducting the load/abort part remains open.
- Line1277: package all materials/context for transfer. Historical authoring instructions embedded in those materials do not authorize further changes during this review.

Pilot80/200 sample counts,2%/20% quality targets and90%/kappa0.8 agreement targets are proposals in agent artifacts, not explicit approved acceptance rules found in this chat. Pasted outside reviews (e.g. lines499/673) contain claims and suggestions; distinguish them from measured evidence and direct implementation requests.

## Open work after this review

Obtain independent real-data/human validation and explicit acceptance criteria; preserve unreviewed/uncertain/adjudication states. Keep U02/U46/V05 quality defects open and avoid promoting full score to automatic safety. Establish a genuinely separate owned SDK runtime plus resource and terminal cleanup proof before the unperformed normal-load/forced-abort test. Backend crash reconciliation/UI/manual queue/class concurrency remain separate responsibilities, not closed by the AI receipt reader or offline card workflow. Current runtime identity/readiness and archive store portability are unverified here; copied stores are inert historical evidence.
