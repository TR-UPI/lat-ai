# I02.1 API contract and boundary adapter Implementation Plan

> For agentic workers: use superpowers:executing-plans inline; one fresh-context review at completion.

Goal: give frontend/backend teams a concrete versioned ask contract including full code and selection, plus a tested Node mapping boundary against unchanged v10.
Architecture: browser -> existing Django JWT/access boundary -> trusted mapping/history -> shared Node Tutor. The existing 501 view and frontend are not rewired in I02.1; HTTP transport, persistent idempotency, DB mapping and UI are I02.2. No new independent backend, no installers or model calls.
Spec: TUTOR_API_V1.md and ../../contracts/tutor-v1.request.schema.json.
Authority: owner explicitly requested I02 and contract first,10.11. Existing I02 architecture accepted in that request; no repeated approval needed for reversible contract/adapter work. Team acceptance not claimed.
Approaches: authenticated Django facade (selected, matches I02); browser -> demo4173 rejected because JWT/history boundary differs; rewrite core inPython rejected as unnecessary before deadline. Existing isolated clone, local branch codex/i02-api-contract, no push.
Constraints: Node22+, RU PythonL1/L2, no newweights/paidAPI/RAG, modeloff default,8s core/10s full response target. question2000/code4000/combined6000 UTF16 units. Teacher review remains pending. Exact task hints only, trusted history, no client level/permissions. The hint catalogue never enables level 4. Free explain remains unverified and has no equivalent semantic guarantee.

- [x]1 Write API spec, strict request/success/error schemas and fixtures. Include compatibility, status codes, replay semantics, deadlines, snapshots and frontend rendering rules.
- [x]2 Red tests for request validation, UTF16/CRLF, authorization/binding, policy priority, unsupported mapping, history trust, output projection, no leaks. Files integration/ai/test/contract.test.mjs and contracts/examples.
- [x]3 Implement integration/ai/adapter.mjs with prepareRequest/toPublicResponse/errorResponse; unchanged core files pinned in UPSTREAM.json. No HTTP listener or implicit persistence.
- [x]4 Run adapter+v10 regressions; schema/example consistency and source hashes. Review exact branch; resolve critical findings. Package handoff and evidence without runtime/secrets.
- [x]5 Update canonical roadmap I02.1 vsI02.2 and original STATUS. Preserve v10/v4 and original source commit.

Review focus: offsets are UTF16 notPythonlen; selected-end exclusive includingCRLF; context captured before await; body cannot forgeactor/lessonkey/history; crisis in unselected code wins even if mapping unsupported; replay must not issue newhint; unknown output fails closed without echoingcoredebug.

Rulings10.11: canonical fingerprint added as reusable pure helper; all replay/storage remains I02.2. Existing staticserver required narrow integration-deny because privatecoredata would otherwise be exposed. Explicit scope check proves backend/assets untouched. Solution guarantee narrowed to hint4; no new semantic admission. Human/team acceptance and finalconnectedAPI not claimed.
