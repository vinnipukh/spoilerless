---
phase: 06-spoiler-safe-graphrag-chat-and-graph-editing-agent
plan: "01"
subsystem: graphrag
status: complete
tags: [graphrag, llm, retrieval, watch-progress, chat, fastapi, neo4j, pytest]

requires:
  - phase: 03-user-notes-and-manual-editing
    provides: AppUser/custom-content origin model (UserSeriesProgress-boundary authorization)
  - phase: 04-revision-history-and-revert
    provides: Revision model conventions (auditable mutation patterns, REFERS_TO links)
  - phase: 05-future-extraction-preparation
    provides: candidate/origin conventions for graph-sourced content
provides:
  - Backend-authoritative UserSeriesProgress watch boundary (RAG-01): POST/GET /api/series/{series_id}/progress, resolved server-side, never client input on the chat path
  - LLM provider layer (RAG-04): OpenAICompatibleProvider (SSE streaming, tool-call accumulation) + FakeLLMProvider test double, llm_enabled fail-closed, 503 never 401/403 via install_llm_error_handlers
  - Retrieval pipeline (RAG-05/06/07/08): allowlisted tool loop (get_entity, get_neighborhood), delimited context assembly (<entities>/<claims>/<evidence>/<sources>/<notes>/<chat_history>), this-turn citation validation, INSUFFICIENT_CONTEXT_ANSWER fallback, graph_focus extraction
  - Chat API (RAG-09/10): session CRUD + message endpoints + SSE stream ending in event:done envelope; role included on ChatMessageResponse
  - Contract inventory updates: test_openapi_contract.py, test_frontend_contract_doc.py, docs/frontend-api-contract.md
  - Seed constraints/indexes for the three new node labels; .env.example documents all LLM_* vars (empty values)
  - Prompt-injection defense tests: 5 PRD-quoted malicious strings wrapped inside labeled delimiters
---

# Plan 06-01 — Spoiler-safe GraphRAG Vertical Slice

**Status:** Complete — RED `87ff5c5`, GREEN `9dd5ffc`, contracts `624851b`, injection tests `b1920dd`
**Duration:** ~2h (3 executor attempts + orchestrator fix loop; each subagent capped at 50 tool calls)

## Delivered

| Task | Description | Files | Status |
|------|-------------|-------|--------|
| T1 | RED tests for LLM provider, progress API, retrieval tools, chat API | `backend/tests/test_llm_provider.py`, `test_progress_api.py`, `test_chat_api.py`, `test_retrieval_tools.py` | ✅ |
| T1 | GREEN: full vertical slice implementation | `backend/app/llm/*`, `api/{deps,progress,chat}.py`, `domain/{progress,chat}.py`, `graph/{progress,chat}.py`, `repository/{progress,chat}.py`, `services/{progress,chat}.py`, `retrieval/{__init__,tools,pipeline}.py`, `main.py`, `api/auth.py` (CurrentUserDependency refactor) | ✅ |
| T2 | Contract inventories, seed indexes, env docs | `test_openapi_contract.py`, `test_frontend_contract_doc.py`, `docs/frontend-api-contract.md`, `backend/app/graph/seed.py`, `.env.example` | ✅ |
| T3 | Prompt-injection delimiter tests | `backend/tests/test_prompt_injection.py` | ✅ |

## Verification (exact commands + results)

- `cd backend && uv run pytest tests/test_llm_provider.py tests/test_progress_api.py tests/test_chat_api.py tests/test_retrieval_tools.py -q` → **35 passed**
- `cd backend && uv run pytest tests/test_openapi_contract.py tests/test_frontend_contract_doc.py -x` → **10 passed**
- `cd backend && uv run pytest tests/test_prompt_injection.py -x` → **7 passed**
- `cd backend && uv run pytest tests/test_auth.py tests/test_graph_api.py -q` → regression clean
- Full suite: **191 passed** (7 failed + 7 errors pre-existing Phase-5 debt: missing `data/dexter/test/extraction_fixture.json`, drifted seed counts from earlier-phase DB pollution — not caused by this plan)

## Key Decisions

- Test infrastructure: sync TestClient + `asyncio.run` for in-memory awaits (test_graph_api pattern). Async fixtures + sync TestClient cross event loops and crash the Neo4j async driver (`'NoneType' send` in proactor_events) — fixed via sync fixtures and fresh-driver cleanup teardowns.
- `[tool.pytest.ini_options] asyncio_mode = "auto"` + `testpaths = ["backend/tests"]` added to root `pyproject.toml` (required for the RED tests' async style).
- `MERGE (p)-[:FOR_SERIES]->(s:Series {id: $series_id})` in one statement tried to re-CREATE the Series node → split into `MERGE (s:Series {id: ...})` then relationship MERGE (idempotent upsert).
- `ChatMessageResponse` includes `role` (repo returns it; StrictModel otherwise rejects).
- Provider timeout mapping: httpx `TimeoutException` → `LLMProviderUnavailable` → 503 `LLM_PROVIDER_UNAVAILABLE`; disabled → 503 `LLM_DISABLED`. Test doubles raise transport-level timeouts because `httpx.MockTransport` handlers bypass timeout enforcement.
- Chat/progress tests clean up ChatSession/ChatMessage/UserSeriesProgress nodes via a fresh driver+loop teardown so the seed-integrity audit in `test_graph_api.py` stays green.

## Patterns Established

- Backend-authoritative spoiler boundary: boundary resolved server-side from persisted `UserSeriesProgress`, never accepted as request input on the GraphRAG path.
- Fail-closed provider wiring: `llm_enabled=false` or unconfigured → 503, never 401/403.
- Untrusted graph content always wrapped in labeled delimiters; system prompt names the exact tags and declares them data, not instructions.
- Citation validation against THIS turn's retrieved set (never a fresh DB existence check).

## Issues Encountered

- 3 subagent executions capped at 50 tool calls mid-plan (plan size + broken RED tests); continuation executors + orchestrator inline fix loop completed the work.
- RED tests had `await` in sync `def test_*` (SyntaxError) and an async `_set_progress` helper returning coroutines — fixed to sync pattern.
- Test pollution of live Neo4j (ChatSession/ChatMessage/UserSeriesProgress nodes) broke the seed-integrity audit in test_graph_api.py — cleaned + teardown added.

## Key Files

- created: `backend/app/llm/{__init__,provider,system_prompt}.py`, `backend/app/retrieval/{__init__,tools,pipeline}.py`, `backend/app/api/{deps,progress,chat}.py`, `backend/app/domain/{progress,chat}.py`, `backend/app/graph/{progress,chat}.py`, `backend/app/repository/{progress,chat}.py`, `backend/app/services/{progress,chat}.py`, `backend/tests/test_prompt_injection.py`
- modified: `backend/app/main.py`, `backend/app/api/auth.py`, `backend/app/graph/seed.py`, `backend/tests/test_llm_provider.py`, `test_progress_api.py`, `test_chat_api.py`, `test_retrieval_tools.py`, `test_openapi_contract.py`, `test_frontend_contract_doc.py`, `docs/frontend-api-contract.md`, `.env.example`, `pyproject.toml`
