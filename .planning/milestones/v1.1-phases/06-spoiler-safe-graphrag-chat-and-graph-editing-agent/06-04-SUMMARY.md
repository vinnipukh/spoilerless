---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: 04
subsystem: api
tags: [fastapi, neo4j, cypher, chat-persistence, ownership-scoping, rate-limiting, sse]

requires:
  - phase: 06-01
    provides: "ChatRepository/ChatService/api/chat.py tracer slice with shared list_messages_for_context/list_messages_for_response filter"
  - phase: 06-03
    provides: "ProgressNotFoundError fail-closed handling in chat.py/pipeline.py"
provides:
  - "Verified end-to-end RAG-09 hide-not-delete regression test against real Neo4j (Episode-3-then-Episode-1 scenario)"
  - "DELETE /api/series/{series_id}/chat/sessions/{session_id} with identical generic 404 for cross-user/cross-series/missing sessions"
  - "Per-user bounded concurrent-generation counter (services/chat.py), released on normal completion, exceptions, and client disconnect"
  - "Turkish-language Unicode-code-point-based length bound and count-leakage guarantees"
  - "Updated closed-inventory contract tests and docs/frontend-api-contract.md for the new DELETE route and 429 status"
affects: [06-05, 06-06, 06-07, 06-08, 06-09]

actuals:
  tokens: 12876
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Single user-scoped MATCH suffices for chat-session ownership 404s (no origin/conflict two-query pattern needed — unlike user_content.py, ChatSession has no third 404-vs-409 outcome to distinguish)"
    - "Per-user concurrent-generation counter as a module-level dict with synchronous check-and-increment (no lock needed — asyncio guarantees no interleaving between non-await statements)"
    - "Concurrency-slot acquire/release wrapped in the async generator's own try/finally so it releases identically on normal completion, any exception, and GeneratorExit (Starlette's client-disconnect signal)"

key-files:
  created:
    - backend/tests/test_chat_persistence.py
  modified:
    - backend/app/graph/chat.py
    - backend/app/repository/chat.py
    - backend/app/services/chat.py
    - backend/app/api/chat.py
    - backend/app/core/errors.py
    - backend/tests/test_chat_api.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_frontend_contract_doc.py
    - docs/frontend-api-contract.md

key-decisions:
  - "DELETE session uses a single user-scoped Cypher MATCH, not the origin-conflict two-query pattern from user_content.py — ChatSession has no origin/conflict state to distinguish (no 409 case), so foreign/cross-series/missing are already indistinguishable (zero rows) through one query, matching get_session's existing precedent exactly"
  - "Concurrent-generation acquire/release lives inside ChatService.answer_stream's try/finally (not a separate pre-check in the API layer) so both the non-streaming answer() path and the streaming SSE path share one code path with symmetric acquire/release"
  - "For the SSE route specifically, a concurrency rejection after headers are already committed cannot become a 429 status line — it is instead surfaced as a structured `event: error` SSE payload ({code: too_many_requests, message}), documented as a known transport limitation in docs/frontend-api-contract.md"
  - "Added HTTP 429 (too_many_requests) as a new shared error-response spec in core/errors.py, used only by the two chat message routes"

requirements-completed: [RAG-09, RAG-10]

coverage:
  - id: D1
    description: "The Episode-3-then-Episode-1 critical regression scenario passes end-to-end against real Neo4j: hidden messages are excluded from the API response and the LLM conversation-memory load (identical shared filter) but never deleted, and reappear unchanged when progress is raised again"
    requirement: RAG-09
    verification:
      - kind: integration
        ref: "backend/tests/test_chat_persistence.py#test_episode_3_then_episode_1_regression_hides_not_deletes"
        status: pass
      - kind: unit
        ref: "backend/tests/test_chat_persistence.py#test_no_delete_cypher_targets_chat_message_on_progress_decrease"
        status: pass
    human_judgment: false
  - id: D2
    description: "Boundary-exactness: a message exactly at the current progress boundary is visible, one order above is hidden, one order below is visible"
    requirement: RAG-09
    verification:
      - kind: integration
        ref: "backend/tests/test_chat_persistence.py#test_boundary_exactness_matrix"
        status: pass
    human_judgment: false
  - id: D3
    description: "DELETE session removes the session and its messages, returning generic identical 404s for cross-user, cross-series, and nonexistent sessions, and 204-then-404 on retry"
    requirement: RAG-10
    verification:
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_delete_session_removes_it_and_its_messages_from_subsequent_get"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_delete_session_cross_user_and_nonexistent_return_identical_404"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_delete_session_cross_series_is_generic_404"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_delete_session_retried_twice_returns_204_then_404"
        status: pass
    human_judgment: false
  - id: D4
    description: "Bounded concurrent generations per user: a second concurrent generation is rejected with a clear non-500 error, does not block a different user, and the slot releases on normal completion and on client disconnect (aclose/GeneratorExit)"
    requirement: RAG-10
    verification:
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_concurrent_generation_for_same_user_is_rejected_with_clear_error"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_concurrent_generation_does_not_block_a_different_user"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_answer_stream_releases_generation_slot_on_client_disconnect"
        status: pass
    human_judgment: false
  - id: D5
    description: "Turkish-language message bounds are code-point- not byte-based, and no API response ever numerically leaks the true (visible+hidden) message count"
    requirement: RAG-09
    verification:
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_turkish_question_length_bound_counts_unicode_code_points_not_bytes"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_api.py#test_session_message_count_never_leaks_hidden_message_count"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_persistence.py#test_turkish_message_content_round_trips_without_corruption"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_persistence.py#test_messages_return_in_stable_created_at_ascending_order_across_repeated_reads"
        status: pass
      - kind: integration
        ref: "backend/tests/test_chat_persistence.py#test_sessions_list_newest_updated_first"
        status: pass
    human_judgment: false
  - id: D6
    description: "The two closed-inventory contract tests and docs/frontend-api-contract.md are updated in the same plan that adds the new DELETE route (mandatory same-commit contract-inventory rule)"
    verification:
      - kind: unit
        ref: "backend/tests/test_openapi_contract.py#test_user_route_openapi_has_exact_operations_and_templates"
        status: pass
      - kind: unit
        ref: "backend/tests/test_frontend_contract_doc.py#test_document_and_openapi_have_exact_locked_inventory"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-01
status: complete
---

# Phase 6 Plan 4: Chat persistence hardening — hide-not-delete regression, DELETE session, bounded concurrency Summary

**Verified the RAG-09 Episode-3-then-Episode-1 hide-not-delete regression end-to-end against real Neo4j, added `DELETE /api/series/{series_id}/chat/sessions/{session_id}` with generic ownership 404s, a per-user bounded concurrent-generation counter with disconnect-safe release, and Turkish-language/count-leakage guarantees — plus the mandatory same-commit contract-inventory updates.**

## Performance

- **Duration:** ~20 min active execution
- **Completed:** 2026-08-01T00:47:47+03:00
- **Tasks:** 3
- **Files modified:** 10 (1 new test file, 5 source files, 3 test files, 1 doc)

## Accomplishments

- Confirmed 06-01's `list_messages_for_context`/`list_messages_for_response` already share one underlying parameterized Cypher filter (`WHERE visible_until_order_snapshot <= $visible_until_order`), then wrote the exact five-step Episode-3-then-Episode-1 regression scenario named verbatim by 06-CONTEXT.md as a repository-level test against live Neo4j — asserting the hidden message is absent from both the API-response shape and the LLM conversation-memory load, is never deleted (direct Neo4j existence check), and reappears unchanged (same id, same content) when progress is raised back.
- Added a boundary-exactness matrix test (equal-to-boundary visible, one-above hidden, one-below visible) and a structural guard confirming no Cypher `DELETE` clause in `repository/chat.py`'s reachable query text targets `ChatMessage` on any progress-related path.
- Added `DELETE /api/series/{series_id}/chat/sessions/{session_id}`: a single user-scoped Cypher MATCH plus a `FOREACH`-guarded cascade delete of the session's messages, returning 204. Cross-user, cross-series, and nonexistent sessions all return the identical generic 404; retrying twice returns 204 then 404, never a duplicate side effect.
- Added a per-user in-process concurrent-generation counter (`services/chat.py`) acquired/released inside `ChatService.answer_stream`'s `try`/`finally` — covering normal completion, any exception, and `GeneratorExit` (Starlette's disconnect signal) identically. A second concurrent `POST .../messages` for the same user returns 429 `too_many_requests`; a different user is never blocked. The streaming variant, where SSE headers are already committed by the time the limit is checked, emits a structured `event: error` payload instead of a status-line rejection — documented as a known transport limitation.
- Added Turkish-language tests: the 4000-character question bound accepts Turkish text (İ, ı, ş, ğ, Ç, ö, Ü) up to exactly 4000 Unicode code points and rejects one code point over (proving the bound is code-point-, not byte-based), content round-trips without corruption at the repository layer, and messages/sessions return in stable order across repeated reads.
- Added a count-leakage test proving a session's exposed message count (2 visible) provably differs from the true persisted total (6, including 4 hidden) — the API never exposes a raw/total count.
- Updated `test_openapi_contract.py`, `test_frontend_contract_doc.py` (37→38 operations, 27 path templates unchanged), and `docs/frontend-api-contract.md` for the new DELETE route and the new 429 status code, per 06-RESEARCH.md's mandatory same-commit contract-inventory rule.
- Ran the full backend suite: 282 passed, the same 3 pre-existing `test_seed_idempotency.py` failures from 06-03's deferred-items.md (unrelated Phase-5 leftover candidate-origin test data, no teardown fixture) — confirmed identical failure signature (node/relationship counts off by +8/+6, `incomplete_claims` count 3), no regression introduced by this plan.

## Task Commits

1. **Task 1: RAG-09 hide-not-delete regression test + boundary-exactness matrix** - `855ff3d` (test)
2. **Task 2: Full session CRUD (DELETE), ownership 404s, bounded concurrency + contract updates** - `e6f66d7` (feat)
3. **Task 3: Turkish-text bounded-length + ordering + count-leakage tests** - `aaae9e2` (test)

_Note: Task 1's commit also included the Task 3 repository-level Turkish round-trip, stable-ordering, and session-ordering tests (they were authored together in `test_chat_persistence.py` in one pass); Task 3's commit adds only the remaining `test_chat_api.py`-level Turkish length-bound and count-leakage tests. No source-code changes were bundled across task boundaries — only test-file authoring order._

## Files Created/Modified

- `backend/tests/test_chat_persistence.py` - NEW: repository-level chat persistence tests (regression scenario, boundary matrix, DELETE-cypher guard, Turkish round-trip, stable ordering, session ordering)
- `backend/app/graph/chat.py` - added `CHAT_SESSION_DELETE_QUERY` (single user-scoped MATCH + `FOREACH`-guarded cascade message delete)
- `backend/app/repository/chat.py` - added `ChatRepository.delete_session`
- `backend/app/services/chat.py` - added the per-user concurrent-generation counter (`_acquire_generation_slot`/`_release_generation_slot`, `ConcurrentGenerationLimitExceeded`), `ChatService.delete_session`/`acquire_generation_slot`/`release_generation_slot`, wrapped `answer_stream` in a `try`/`finally` around the slot
- `backend/app/api/chat.py` - added `DELETE /sessions/{session_id}` route, 429 handling for `post_message` and a structured SSE `event: error` for `stream_message`
- `backend/app/core/errors.py` - added the 429 `too_many_requests` shared error-response spec
- `backend/tests/test_chat_api.py` - added DELETE ownership/retry tests, concurrency-rejection/cross-user/disconnect tests, Turkish length-bound and count-leakage tests
- `backend/tests/test_openapi_contract.py` - added the DELETE operation to the closed-inventory method set
- `backend/tests/test_frontend_contract_doc.py` - added the DELETE operation, updated the locked operation count to 38
- `docs/frontend-api-contract.md` - added the DELETE route row and prose, the 429 status and `too_many_requests` code, and streaming-concurrency-limitation prose

## Decisions Made

- DELETE session uses a single user-scoped Cypher MATCH, not the origin-conflict two-query pattern from `user_content.py` — `ChatSession` has no origin/conflict state to distinguish (no legitimate 409 case for a session), so foreign/cross-series/missing already collapse to the identical zero-row outcome through one query, exactly matching `get_session`'s existing precedent and docstring rationale.
- The concurrency slot's acquire/release lives inside `ChatService.answer_stream`'s `try`/`finally`, not a separate pre-check step in the API layer — this keeps one code path shared by both the non-streaming `answer()` (which iterates `answer_stream()`) and the streaming SSE route, with symmetric acquire/release regardless of caller.
- Accepted that a concurrency rejection on the SSE path, arriving after headers are already committed, cannot become an HTTP 429 status line — Starlette sends `http.response.start` before the body iterator is ever pulled. Surfaced instead as a structured `event: error` SSE payload; documented as a known transport limitation rather than silently dropped.
- Added HTTP 429 as a new shared error-response spec in `core/errors.py` (not reused from an existing status) since none of the existing 401/404/409/422/503 codes correctly describe "rejected due to a concurrency limit."

## Deviations from Plan

None (Rules 1-4) - plan executed as written. One clarification, not a deviation: the plan's Task 2 action text mentions "using the ownership two-query pattern from 06-PATTERNS.md," but on inspection that two-query pattern exists specifically to distinguish 404-from-409 for resources with an origin/conflict concept (`user_content.py`'s custom nodes/relationships). `ChatSession` has no such concept — a single user-scoped query already produces the required identical generic 404 for every not-found reason, matching `get_session`'s and `create_message`'s existing single-query precedent exactly. Documented above as a Decision, not logged as a plan deviation, since the underlying requirement (identical generic 404) is fully satisfied by the simpler implementation.

## Issues Encountered

None beyond the already-documented pre-existing `test_seed_idempotency.py` pollution (see `deferred-items.md` from 06-03) — reconfirmed identical, not worsened, by this plan's full-suite run (282 passed, same 3 pre-existing failures).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RAG-09 and RAG-10 are now fully satisfied: the critical hide-not-delete regression is proven against real Neo4j, full session CRUD (including DELETE) exists with generic ownership 404s, bounded concurrent generations are enforced and disconnect-safe, and no API response ever numerically leaks hidden-message counts.
- The DELETE route and 429 status are reflected in both closed-inventory contract tests and `docs/frontend-api-contract.md` — any later plan in this phase that adds routes must repeat this same-commit contract-update discipline.
- Later plans (06-05 onward, the graph-editing agent and frontend chat UI) can rely on `ChatService`'s session CRUD being complete and the concurrent-generation counter being available if the ChangeSet-apply flow needs the same DoS-mitigation pattern.

## Self-Check: PASSED

- FOUND: backend/tests/test_chat_persistence.py
- FOUND: backend/app/graph/chat.py
- FOUND: backend/app/repository/chat.py
- FOUND: backend/app/services/chat.py
- FOUND: backend/app/api/chat.py
- FOUND: backend/app/core/errors.py
- FOUND: backend/tests/test_chat_api.py
- FOUND: backend/tests/test_openapi_contract.py
- FOUND: backend/tests/test_frontend_contract_doc.py
- FOUND: docs/frontend-api-contract.md
- FOUND commit 855ff3d
- FOUND commit e6f66d7
- FOUND commit aaae9e2

---
*Phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent*
*Completed: 2026-08-01*
