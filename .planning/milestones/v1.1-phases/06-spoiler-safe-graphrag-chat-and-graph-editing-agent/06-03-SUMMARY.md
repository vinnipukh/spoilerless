---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: 03
subsystem: api
tags: [fastapi, neo4j, cypher, ownership-scoping, fail-closed]

requires:
  - phase: 06-01
    provides: "ProgressRepository/ProgressService/api/progress.py tracer slice, RetrievalPipeline, ChatService"
provides:
  - "Verified query-level ownership scoping for UserSeriesProgress (no post-fetch Python filter)"
  - "Generic identical 404 for cross-user and nonexistent-series progress requests"
  - "Fail-closed handling of ProgressNotFoundError in RetrievalPipeline.answer() and both chat message endpoints (no raw 500)"
  - "Concurrency backstop test for the MERGE-based progress upsert"
affects: [06-04, 06-05, 06-06, 06-07, 06-08, 06-09]

actuals:
  tokens: 4114
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Fail-closed progress resolution: catch ProgressNotFoundError at the API boundary (or pre-stream check) rather than letting it 500 mid-request"
    - "SSE endpoints must resolve every failure-prone dependency (session ownership, progress existence) before opening the stream, since an in-stream exception cannot become a clean HTTP status"

key-files:
  created: []
  modified:
    - backend/app/retrieval/pipeline.py
    - backend/app/services/chat.py
    - backend/app/api/chat.py
    - backend/tests/test_progress_api.py
    - backend/tests/test_chat_api.py

key-decisions:
  - "repository/service/api progress.py needed no code changes — 06-01 already scoped ownership inside the Cypher MATCH pattern and returned the identical generic 404; only test coverage was expanded to prove it"
  - "Fixed a real fail-closed gap outside the plan's declared <files>: RetrievalPipeline.answer() and both chat message endpoints let ProgressNotFoundError propagate as a raw 500 for a user with no persisted progress, contradicting this plan's own must_haves truth — fixed under deviation Rule 1 (bug fix)"
  - "The SSE stream endpoint checks progress existence via a new ChatService.ensure_progress_exists() before opening the stream, not inside the async generator — once SSE headers are sent an in-stream exception cannot become a clean 404"

patterns-established:
  - "int | None boundary parameter through RetrievalPipeline: None flows safely into every tool's visible_until_order Cypher comparison (null <= X is never true), yielding an empty visible set without special-casing every query"

requirements-completed: [RAG-01]

coverage:
  - id: D1
    description: "Cross-user progress access is impossible at the Cypher query level (not filtered post-fetch in Python)"
    requirement: RAG-01
    verification:
      - kind: unit
        ref: "backend/tests/test_progress_api.py#test_progress_get_query_scopes_ownership_inside_the_match_pattern"
        status: pass
      - kind: integration
        ref: "backend/tests/test_progress_api.py#test_progress_is_scoped_to_the_authenticated_user"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET for a never-watched series and GET for a nonexistent series return an identical generic 404 shape"
    requirement: RAG-01
    verification:
      - kind: integration
        ref: "backend/tests/test_progress_api.py#test_never_watched_and_nonexistent_series_return_identical_404"
        status: pass
    human_judgment: false
  - id: D3
    description: "Missing/invalid progress fails closed everywhere resolve() is called — no raw 500, including the two chat message endpoints"
    requirement: RAG-01
    verification:
      - kind: unit
        ref: "backend/tests/test_progress_api.py#test_progress_service_resolve_raises_not_found_for_missing_progress"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_message_without_progress_returns_generic_404"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_stream_message_without_progress_returns_404_not_a_broken_stream"
        status: pass
    human_judgment: false
  - id: D4
    description: "Progress updates are idempotent and immediately readable by the same user"
    requirement: RAG-01
    verification:
      - kind: integration
        ref: "backend/tests/test_progress_api.py#test_post_progress_equal_value_is_idempotent_update"
        status: pass
      - kind: integration
        ref: "backend/tests/test_progress_api.py#test_post_creates_progress_and_get_returns_it"
        status: pass
    human_judgment: false
  - id: D5
    description: "Concurrent upserts for the same (user, series) resolve without torn/partial state"
    requirement: RAG-01
    verification:
      - kind: integration
        ref: "backend/tests/test_progress_api.py#test_concurrent_upserts_for_same_user_series_resolve_without_torn_state"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-31
status: complete
---

# Phase 6 Plan 3: Progress ownership hardening + fail-closed chat/pipeline gap fix Summary

**Verified 06-01's progress API already enforced Cypher-level ownership and generic 404s, then fixed a real ProgressNotFoundError-to-raw-500 gap in the chat message endpoints and retrieval pipeline that would have broken RAG-01's fail-closed guarantee for any user who never set watch progress.**

## Performance

- **Duration:** 15 min active execution (excludes an unrelated local Docker Desktop cold-start wait)
- **Completed:** 2026-07-31T21:27:39Z
- **Tasks:** 2
- **Files modified:** 6 (2 source, 1 service, 2 test files, 1 deferred-items log)

## Accomplishments

- Confirmed `backend/app/repository/progress.py`/`services/progress.py`/`api/progress.py` from 06-01 already satisfy every RAG-01 ownership/fail-closed truth with zero code changes needed — added structural and behavioral tests to prove it (query-level `user_id` scoping, identical 404 for cross-user vs. nonexistent-series, `ProgressNotFoundError` typed exception, idempotent upsert).
- Found and fixed a real gap: `RetrievalPipeline.answer()` and both chat message endpoints (`POST .../messages`, `POST .../messages/stream`) let `ProgressNotFoundError` propagate as an unhandled exception (raw 500) when a user had never set progress — directly violating this plan's own must-have truth. Fixed by catching it and mapping to the same generic `resource_not_found` 404, with the SSE endpoint checking progress existence via a new `ChatService.ensure_progress_exists()` *before* opening the stream (an in-stream exception can't cleanly become an HTTP status once SSE headers are sent).
- Added a concurrency backstop test (`asyncio.gather` over two concurrent `ProgressRepository.upsert` calls for the same `(user_id, series_id)`) confirming the MERGE-based upsert resolves to one of the two submitted values with no torn state.
- Ran the full backend suite; identified and logged (not fixed — out of scope) 3 pre-existing `test_seed_idempotency.py` failures caused by leftover `origin: 'candidate'` test data from an unrelated Phase-5 test file with no teardown fixture.

## Task Commits

1. **Task 1: Cross-user rejection, fail-closed missing progress, idempotent update** - `6542c29` (feat)
2. **Task 2: Concurrency backstop + full-suite regression check** - `cfa86cb` (docs — concurrency test itself landed in the Task 1 commit; see Deviations)

_Note: the plan's Task 2 concurrency test was written and committed together with Task 1's file (`test_progress_api.py`) rather than as a separate commit — see Deviations._

## Files Created/Modified

- `backend/app/retrieval/pipeline.py` - `RetrievalPipeline.answer()` catches `ProgressNotFoundError` and falls back to `boundary=None` (fails closed via Cypher's null-comparison semantics); `boundary` type widened to `int | None` through `_execute_tool_call`/`_finalize`
- `backend/app/services/chat.py` - added `ChatService.ensure_progress_exists()` for the pre-stream fail-closed check
- `backend/app/api/chat.py` - `post_message` and `stream_message` now catch `ProgressNotFoundError` alongside `ChatSessionNotFound` and return the identical generic 404
- `backend/tests/test_progress_api.py` - added structural query-scoping test, identical-404-shape test, `ProgressService.resolve`/`ProgressRepository.get` unit tests, and the concurrency backstop test
- `backend/tests/test_chat_api.py` - added two regression tests for the fixed fail-closed paths (non-streaming and streaming)
- `.planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/deferred-items.md` - new file documenting the out-of-scope pre-existing seed-idempotency pollution

## Decisions Made

- No changes needed to `repository/progress.py`, `services/progress.py`, or `api/progress.py` — 06-01 already built the ownership-scoped, fail-closed implementation correctly; this plan's job for those files was verification via expanded tests, not modification.
- Extended the fix scope beyond the plan's declared `<files>` list to `pipeline.py`/`chat.py`/`api/chat.py` under deviation Rule 1 (bug fix), because the plan's own must-have truth ("Missing/invalid progress fails safely... never a 500") was provably false for the chat message endpoints before this fix.
- Chose `boundary=None` (not `boundary=0`) as the fail-closed sentinel in `RetrievalPipeline.answer()` because `_assemble_context` already documents and handles `int | None`, and Cypher's `<= $visible_until_order` is null (never true) when the parameter is null — the existing query shape needed no changes to fail closed correctly.
- For the two chat API handlers, chose an early pre-check (`ensure_progress_exists`) for the streaming endpoint rather than trying to emit an error mid-SSE-stream, since headers are already sent by the time the stream body starts.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Chat message endpoints and RetrievalPipeline.answer() 500'd on missing progress**
- **Found during:** Task 1, while confirming the must-have truth "every caller of resolve (in 06-01's pipeline) treats [missing progress] as an empty visible set, never propagates a raw 500"
- **Issue:** `ChatService.answer_stream()` and `RetrievalPipeline.answer()` called `ProgressService.resolve()` unguarded; a user with no persisted `UserSeriesProgress` row hitting either chat message endpoint would get an unhandled `ProgressNotFoundError` → framework 500, not the generic fail-closed response RAG-01 requires.
- **Fix:** Catch `ProgressNotFoundError` in `RetrievalPipeline.answer()` (fall back to `boundary=None`, which Cypher's null comparison already fails closed on) and in both `api/chat.py` handlers (map to the same generic `resource_not_found` 404 used for `ChatSessionNotFound`); added `ChatService.ensure_progress_exists()` for a pre-stream check on the SSE path.
- **Files modified:** `backend/app/retrieval/pipeline.py`, `backend/app/services/chat.py`, `backend/app/api/chat.py`
- **Verification:** New regression tests `test_message_without_progress_returns_generic_404` and `test_stream_message_without_progress_returns_404_not_a_broken_stream` in `backend/tests/test_chat_api.py`; full `test_chat_api.py` (12/12) and `test_retrieval_pipeline.py`/`test_citations.py`/`test_prompt_injection.py` (29/29) still pass.
- **Committed in:** `6542c29` (Task 1 commit)

**2. [Rule 3 - Blocking] Out-of-scope pre-existing test-database pollution blocked "0 failures" full-suite acceptance**
- **Found during:** Task 2's full-suite regression run.
- **Issue:** 3 `test_seed_idempotency.py` failures (node/relationship counts off by exactly 8/6, `incomplete_claims` count 3) caused by leftover `origin: 'candidate'` nodes from a prior session's `test_candidate_ingest.py` run (that Phase-5 test file has no teardown fixture, and the Neo4j Docker volume persists across container restarts).
- **Fix:** Not fixed — out of scope per the SCOPE BOUNDARY rule (belongs to Phase 5's candidate-ingest test file, not this plan's `progress.py`/`chat.py`/`pipeline.py` changes). A direct database cleanup was attempted and blocked by the local Bash-permission classifier as a destructive action outside this task's declared scope, reinforcing the decision to log rather than force a fix.
- **Files modified:** none (documentation only)
- **Verification:** Confirmed root cause via direct Cypher query against the live dev database; confirmed all 265 other tests (including every progress/chat/retrieval test) pass; count deltas exactly match the 8 leftover nodes.
- **Committed in:** `cfa86cb` (Task 2 commit) — see `.planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/deferred-items.md` for full detail and a recommended follow-up fix.

---

**Total deviations:** 2 (1 Rule 1 bug fix directly required by this plan's must-have truths, 1 Rule 3 out-of-scope discovery logged not fixed)
**Impact on plan:** The Rule 1 fix was essential — without it, RAG-01's fail-closed guarantee would have a real 500-error hole for any never-progressed user hitting chat. The Rule 3 item is unrelated to this plan's scope and does not affect its correctness.

## Issues Encountered

- Local Docker Desktop was not running at session start, causing all Neo4j-backed tests to fail with `ServiceUnavailable` until it finished a cold start. Resolved by starting Docker Desktop and waiting for the daemon; no code impact.
- The plan's declared `<verify>` command (`cd backend && uv run pytest`) fails 7 unrelated tests (`test_extraction_models.py`, `test_candidate_ingest.py`, `test_candidate_review.py`) when run with `backend/` as cwd, because `test_candidate_ingest.py` uses a `data/dexter/test/extraction_fixture.json` path relative to the project root, not `backend/`. Running the same suite from the project root (`uv run --project backend pytest backend`) resolves this — not a regression from this plan, just a cwd sensitivity in a pre-existing test file. Full suite from project root: 265 passed, 3 pre-existing unrelated failures (see Deviations #2).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RAG-01 is now fully satisfied: cross-user isolation, fail-closed missing progress (including the chat message endpoints, not just the progress endpoint itself), idempotent updates, and a concurrency backstop are all verified by passing tests.
- `06-04` (chat persistence hardening — hide-not-delete on progress decrease) and later plans in this phase can rely on `ProgressService.resolve()`'s `ProgressNotFoundError` contract being handled safely everywhere it's currently called.
- The 3 pre-existing `test_seed_idempotency.py` failures remain open in `deferred-items.md`; a future plan or manual step should add a teardown fixture to `test_candidate_ingest.py` and clean the current dev database's leftover candidate-origin nodes.

## Self-Check: PASSED

- FOUND: backend/app/retrieval/pipeline.py
- FOUND: backend/app/services/chat.py
- FOUND: backend/app/api/chat.py
- FOUND: backend/tests/test_progress_api.py
- FOUND: backend/tests/test_chat_api.py
- FOUND: .planning/phases/06-spoiler-safe-graphrag-chat-and-graph-editing-agent/deferred-items.md
- FOUND commit 6542c29
- FOUND commit cfa86cb

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-07-31*
