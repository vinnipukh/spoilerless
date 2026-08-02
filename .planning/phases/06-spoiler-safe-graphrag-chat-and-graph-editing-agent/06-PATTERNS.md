# Phase 6: Spoiler-Safe GraphRAG Chat and Graph-Editing Agent - Pattern Map

**Mapped:** 2026-07-31
**Files analyzed:** 47 (30 backend new/modified, 17 frontend new/modified)
**Analogs found:** 44 / 47 (3 have no direct analog — new-territory LLM code, listed at the end)

This map is built primarily from `06-RESEARCH.md`'s Repository Investigation (Q1-19), which already
verified every cited file/line by direct read. Excerpts below either quote that research directly
or were re-read in this session to fill gaps (imports, exact error envelope, exact `Neo4jDatabase`
signatures, exact `apiFetch` shape).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/domain/progress.py` | model | CRUD | `backend/app/domain/user_content.py` | exact |
| `backend/app/domain/chat.py` | model | CRUD/streaming | `backend/app/domain/user_content.py` + `backend/app/domain/revision.py` | role-match |
| `backend/app/domain/change_set.py` | model | CRUD (discriminated union) | `backend/app/domain/user_content.py` (`CustomNodeType`/`CustomRelationshipType` StrEnum pattern) | role-match |
| `backend/app/graph/progress.py` | utility (Cypher constants) | CRUD | `backend/app/spoiler/filter.py` | exact |
| `backend/app/graph/chat.py` | utility (Cypher constants) | CRUD | `backend/app/spoiler/filter.py` + `backend/app/repository/user_content.py` | exact |
| `backend/app/graph/change_set.py` | utility (Cypher constants) | CRUD/transactional | `backend/app/repository/user_content.py` (create/update/delete query maps) | exact |
| `backend/app/repository/progress.py` | model/repository | CRUD | `backend/app/repository/user.py` (upsert pattern) | exact |
| `backend/app/repository/chat.py` | model/repository | CRUD | `backend/app/repository/user_content.py` | exact |
| `backend/app/repository/change_set.py` | model/repository | CRUD/transactional | `backend/app/repository/user_content.py` (`_create_custom_node`) + `backend/app/revisions/__init__.py` | exact |
| `backend/app/llm/provider.py` | service | streaming | `backend/app/services/auth.py` (`GoogleTokenVerifier` Protocol pattern) | role-match (no LLM analog exists) |
| `backend/app/llm/system_prompt.py` | config/utility | — | `backend/app/graph/ontology.py` (versioned, server-owned constant data) | partial |
| `backend/app/retrieval/tools.py` | service | request-response | `backend/app/spoiler/filter.py` + `backend/app/services/graph.py` | exact |
| `backend/app/retrieval/pipeline.py` | service | event-driven/streaming | `backend/app/services/graph.py` (`GraphService.fetch_graph`, `asyncio.gather` fan-out) | role-match |
| `backend/app/services/progress.py` | service | CRUD | `backend/app/services/series.py` | exact |
| `backend/app/services/chat.py` | service | streaming/CRUD | `backend/app/services/auth.py` (orchestration + Protocol injection) | role-match |
| `backend/app/services/change_set.py` | service | transactional | `backend/app/api/revisions.py`'s `revert_revision` (read-branch-apply-log transaction shape) | exact |
| `backend/app/api/deps.py` | middleware | request-response | `backend/app/api/auth.py` (`get_auth_service` `Depends` provider + `/me` route body) | exact |
| `backend/app/api/progress.py` | controller/route | request-response | `backend/app/api/user_content.py` | exact |
| `backend/app/api/chat.py` | controller/route | streaming | `backend/app/api/user_content.py` (CRUD routes) + hand-rolled SSE (no existing analog) | role-match |
| `backend/app/api/change_set.py` | controller/route | request-response/transactional | `backend/app/api/revisions.py` | exact |
| `backend/app/api/auth.py` | controller/route | request-response | itself (modify in place) | exact (self) |
| `backend/app/main.py` | config | — | itself (modify in place — router registration block) | exact (self) |
| `backend/app/graph/seed.py` | migration | batch | itself (modify in place — constraints/index block, `appuser_id_unique` precedent) | exact (self) |
| `backend/app/core/config.py` | config | — | itself (modify in place — `Settings` field block) | exact (self) |
| `backend/tests/test_progress_api.py` | test | integration | `backend/tests/test_auth.py` (fake-injection pattern) | exact |
| `backend/tests/test_retrieval_tools.py` | test | integration | `backend/tests/test_auth.py` + spoiler-filter test precedent | role-match |
| `backend/tests/test_llm_provider.py` | test | unit | `backend/tests/test_auth.py` (`FakeGoogleVerifier`) | exact |
| `backend/tests/test_chat_api.py`, `test_change_set_api.py`, etc. | test | integration | `backend/tests/test_auth.py` | exact |
| `backend/tests/test_openapi_contract.py` | test | contract | itself (modify — expand closed inventory) | exact (self) |
| `backend/tests/test_frontend_contract_doc.py` | test | contract | itself (modify — expand `EXPECTED_OPERATIONS`) | exact (self) |
| `frontend/src/types/chat.ts`, `types/changeSet.ts` | model/type | — | `frontend/src/api/graph.ts`'s existing response types (`GraphResponse`, etc.) | exact |
| `frontend/src/api/chat.ts` | service (API client) | request-response/streaming | `frontend/src/api/userContent.ts` + `frontend/src/api/client.ts` | exact for CRUD, no analog for streaming |
| `frontend/src/api/changeSet.ts` | service (API client) | request-response | `frontend/src/api/revisions.ts` | exact |
| `frontend/src/api/progress.ts` | service (API client) | request-response | `frontend/src/api/userContent.ts` | exact |
| `frontend/src/hooks/useChatSessions.ts` | hook | CRUD | `frontend/src/hooks/useGraph.ts` | role-match |
| `frontend/src/hooks/useChatMessages.ts` | hook | streaming | `frontend/src/hooks/useGraph.ts` (fetch-status state machine pattern) | role-match |
| `frontend/src/hooks/useWatchProgress.ts` | hook | CRUD (modify) | itself (modify in place) | exact (self) |
| `frontend/src/components/chat/ChatPanel.tsx` | component | request-response/streaming | `frontend/src/components/detail/DetailPanel.tsx` | role-match |
| `frontend/src/components/chat/MessageList.tsx`, `MessageBubble.tsx` | component | streaming | `frontend/src/components/detail/DetailPanel.tsx` (Notes-tab list rendering) | role-match |
| `frontend/src/components/chat/CitationChip.tsx` | component | request-response | `frontend/src/components/detail/DetailPanel.tsx` (Claims/Evidence accent-colored cards) | exact |
| `frontend/src/components/chat/ChangeSetCard.tsx` | component | request-response | `frontend/src/components/episode/ConfirmAdvanceModal.tsx` (confirm/reject + warnings pattern) | exact |
| `frontend/src/components/chat/SessionPicker.tsx` | component | CRUD | `frontend/src/components/detail/DetailPanel.tsx` (`NoteItem` hover-reveal delete pattern) + shadcn `Select` | role-match |
| `frontend/src/components/chat/ChatLauncher.tsx` | component | request-response | `frontend/src/components/graph/GraphControls.tsx` (icon button + `aria-label` convention) | exact |
| `frontend/src/components/graph/GraphFocusIndicator.tsx` | component | request-response | `frontend/src/components/graph/GraphLegend.tsx` (collapsed-pill overlay treatment) | exact |
| `frontend/src/components/graph/GraphCanvas.tsx` | component (modify) | event-driven | itself (modify — add `focusedElementIds` prop, extend existing `tap`-handler highlight logic at lines 268-322) | exact (self) |
| `frontend/src/components/detail/DetailPanel.tsx` | component (modify) | request-response | itself (modify — add mode toggle, stateful `open`, mount `ChatPanel`) | exact (self) |
| `frontend/src/App.tsx` | component (modify) | event-driven | itself (modify — wire progress-to-backend, panel collapse state, `ChatLauncher`) | exact (self) |
| `frontend/src/test/fixtures/chatFixtures.ts` | test fixture | — | `frontend/src/test/fixtures/graphResponse.ts` | exact |
| `frontend/src/components/chat/ChatPanel.test.tsx` etc. | test | component | `frontend/src/components/episode/ConfirmAdvanceModal.test.tsx`, `GraphCanvas.test.tsx`, `DetailPanel.test.tsx` | exact |

## Pattern Assignments

### Backend domain models — `backend/app/domain/progress.py`, `chat.py`, `change_set.py` (model, CRUD)

**Analog:** `backend/app/domain/user_content.py`

**Imports pattern:**
```python
from __future__ import annotations
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from pydantic import BaseModel, Field, ConfigDict
```

**StrictModel / closed-enum pattern (copy for ChangeSet operation validation, per RAG-11/RAG-12/Pitfall 5):**
`backend/app/domain/user_content.py` lines 61-86 define `CustomNodeType`/`CustomRelationshipType` as
`StrEnum`s — Pydantic rejects any value outside the enum at the API boundary before the repository is
ever called. `ChangeSetOperation` must use a `Literal["create_node", "update_node", ...]` discriminator
field with `Field(discriminator="operation_type")` on the top-level union, and **must not** declare
`origin`, `visible_from_order`, or `id` as settable fields on any operation model at all (Pitfall 5 —
don't rely on "just not using" a settable field; don't declare it).

**Validated-boundary type to extend, not fork (`VisibleUntilOrder`):**
```python
# backend/app/domain/user_content.py lines 19-26 (existing, quoted by research)
VisibleUntilOrder = Annotated[int, Field(gt=0, description="Persisted positive episode order used as a spoiler boundary.")]
```
New progress/chat models should reuse this exact `Annotated` type for any `visible_until_order`-shaped
field rather than redefining bounds.

**Error handling pattern:** none in the domain layer itself — domain models raise via Pydantic
validation only; repository/service layers raise the sentinel exception classes shown below.

---

### Cypher constant modules — `backend/app/graph/progress.py`, `chat.py`, `change_set.py` (utility, CRUD)

**Analog:** `backend/app/spoiler/filter.py` (pure Cypher constants) + `backend/app/repository/user_content.py` (query-map convention)

**Core pattern — module-level UPPER_SNAKE query constants, values always `$params`, labels/rel-types
selected only from closed dicts (never interpolated from request data):**
```python
# Source: backend/app/spoiler/filter.py-style constant + backend/app/repository/user_content.py's
# CUSTOM_NODE_CREATE_QUERIES map convention (verified by research Q2/Q3)
GET_ENTITY_QUERY = """
MATCH (node)
WHERE node.id = $entity_id
  AND node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $allowed_labels)
  AND node.visible_from_order IS NOT NULL
  AND node.visible_from_order <= $visible_until_order
RETURN node.id AS id, node.label AS label, node.visible_from_order AS visible_from_order, node.origin AS origin
"""
```
(Full excerpt in `06-RESEARCH.md` Pattern 1, lines 472-505 — copy verbatim as the shape for all ten
retrieval tools' queries.)

**AppUser label — critical correction (Pitfall/Anti-pattern, RESEARCH Q6 + Anti-Patterns):**
Every new relationship touching the authenticated user node MUST use `(:AppUser {id})`, never
`(:User)` — the label `User` does not exist in this schema and Cypher silently matches zero rows
against a wrong label (no error). Precedent: `backend/app/repository/user.py` line 42
`MERGE (u:AppUser {...})`; `backend/app/repository/session.py`'s `(:AppUser)-[:HAS_SESSION]->(:Session)`.
New `UserSeriesProgress` follows: `(:AppUser {id})-[:HAS_PROGRESS]->(:UserSeriesProgress {id, user_id, series_id, visible_until_order, updated_at})-[:FOR_SERIES]->(:Series {id})`.

**Origin-tagging pattern (hardcode in query text, never accept from payload):**
```python
# backend/app/repository/user_content.py line ~180 (CUSTOM_NODE_CREATE_QUERIES) — origin literal baked
# into the CREATE clause, never a bound parameter derived from client/model input.
CUSTOM_NODE_CREATE_QUERY = """
CREATE (n:%s {id: $id, origin: 'user', ...})
"""
```
ChangeSet-apply's node/relationship/claim creation queries must copy this exact discipline: `origin:
'user'` and `visible_from_order` are literal/server-computed in the query text, not `$params` sourced
from the operation payload.

---

### Repositories — `backend/app/repository/progress.py`, `chat.py`, `change_set.py` (model/repository, CRUD/transactional)

**Analog:** `backend/app/repository/user_content.py` + `backend/app/repository/user.py` (upsert) + `backend/app/graph/database.py`

**Imports pattern (verified this session):**
```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4
from backend.app.domain.revision import RevisionAction
from backend.app.domain.user_content import (...)   # -> swap for backend.app.domain.chat / change_set
from backend.app.graph.database import Neo4jDatabase
from backend.app.revisions import RevisionRepository
```

**`Neo4jDatabase` primitives to call (exact signatures, confirmed this session, `backend/app/graph/database.py`):**
```python
class Neo4jDatabase:
    async def execute_query(self, query: str, **parameters: Any) -> list[dict[str, Any]]: ...
    async def execute_write(self, work: ManagedWork, command: T) -> Any: ...
```
Reads go through `execute_query`; every mutation goes through `execute_write(callback, command)` where
`callback` is `@staticmethod async def _do_thing(tx, command)` running `tx.run(...)` — this is the
single-transaction primitive ChangeSet-apply must use (never two separate transactions for mutation +
revision log — see RESEARCH Anti-Patterns).

**Upsert / MERGE idempotency pattern (for `UserSeriesProgress`, no composite constraint available in
Neo4j Community — RESEARCH Q6/A3):**
```python
# Pattern derived from backend/app/repository/user.py's UPSERT_USER_QUERY
PROGRESS_UPSERT_QUERY = """
MERGE (u:AppUser {id: $user_id})
MERGE (u)-[:HAS_PROGRESS]->(p:UserSeriesProgress {user_id: $user_id, series_id: $series_id})
ON CREATE SET p.id = $id, p.created_at = $now
SET p.visible_until_order = $visible_until_order, p.updated_at = $now
MERGE (p)-[:FOR_SERIES]->(s:Series {id: $series_id})
RETURN p.id AS id, p.visible_until_order AS visible_until_order
"""
```

**Create-then-log-revision-in-same-transaction pattern (copy exactly for ChangeSet apply, RAG-12/RAG-15):**
```python
# Source: backend/app/repository/user_content.py's _create_custom_node +
# backend/app/revisions/__init__.py's RevisionRepository.log_revision (both called inside one tx)
async def _apply_change_set(tx: Any, command: ApplyChangeSetCommand) -> dict[str, Any]:
    current_progress = await _read_progress(tx, command.user_id, command.series_id)
    if command.visible_until_order_snapshot > current_progress:
        raise ChangeSetStaleError()
    applied = [await _apply_one_operation(tx, op, current_progress) for op in command.operations]
    await RevisionRepository.log_revision(
        tx, series_id=command.series_id, resource_type="ChangeSet",
        resource_id=command.change_set_id, action=RevisionAction.CREATED,
        before=None, after={"operations": [r["id"] for r in applied]},
        visible_from_order=current_progress, created_at=command.now,
    )
    return {"status": "applied", "resources": applied}
```
(Full source: `06-RESEARCH.md` Pattern 4, lines 585-607.)

**Ownership two-query pattern (no existing precedent for cross-user 404 — must be built fresh, per
RESEARCH Q7's "critical gap" finding):** try the `user_id`-scoped mutation query first; on no-match,
run a second unauthenticated existence-check query (mirroring `user_content.py`'s `OWNERSHIP_QUERY`
lines 276-279) only to decide 404-vs-409 internally — **never surface the distinction to the
client**; hidden and missing must return the identical generic 404 (RAG-03/RAG-13, Anti-Patterns).

**Error handling — sentinel exception classes to mirror exactly:**
```python
# backend/app/repository/user_content.py
class UserContentValidationError(ValueError): ...
class UserContentConflict(RuntimeError): ...
class UserContentNotFound(LookupError): ...
```
New: `ChatSessionNotFound`, `ChangeSetStaleError`, `ChangeSetConflict`, etc. — same three-way shape
(validation/conflict/not-found), caught in the API layer and mapped to the shared error envelope.

---

### LLM provider — `backend/app/llm/provider.py` (service, streaming)

**Analog:** `backend/app/services/auth.py`'s `GoogleTokenVerifier` `Protocol` (no direct LLM analog exists — this is genuinely new territory per RESEARCH Q16, but the *injection/testability shape* is a direct copy)

**Core pattern — Protocol + real + fake, constructor-injected exactly like `AuthService.__init__(self, ..., verifier: GoogleTokenVerifier | None = None)`:**
```python
from typing import Protocol, AsyncIterator

class LLMProvider(Protocol):
    async def stream_chat(self, *, system_prompt: str, messages: list[dict[str, Any]],
                           tools: list[dict[str, Any]], max_output_tokens: int,
                           temperature: float, timeout_seconds: int) -> AsyncIterator[LLMEvent]: ...

class OpenAICompatibleProvider:
    def __init__(self, *, base_url: str, api_key: str, model: str, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(base_url=base_url, headers={"Authorization": f"Bearer {api_key}"})
        self._model = model
    async def stream_chat(self, **kwargs) -> AsyncIterator[LLMEvent]:
        async with self._client.stream("POST", "/chat/completions", json={"model": self._model, "stream": True, **kwargs}, timeout=kwargs["timeout_seconds"]) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    yield parse_openai_sse_chunk(line[6:])

class FakeLLMProvider:
    """Deterministic — tests configure exact events, never touches the network."""
    def __init__(self, scripted_events: list[LLMEvent]) -> None: self._events = scripted_events
    async def stream_chat(self, **kwargs) -> AsyncIterator[LLMEvent]:
        for event in self._events: yield event
```
(Full source: `06-RESEARCH.md` Pattern 2, lines 507-555. No new dependency — use `httpx.AsyncClient`,
already installed at `0.28.1`.)

**Error handling:** Provider failures (timeout, non-2xx, connection error) must raise a distinct
`LLMProviderError`/`LLMProviderUnavailable` mapped to HTTP 503 via the shared `http_error()` helper —
never 401/403 (RAG-04: "provider failures are infra failures, never authentication errors").

---

### Retrieval tools — `backend/app/retrieval/tools.py` (service, request-response)

**Analog:** `backend/app/spoiler/filter.py` (visibility WHERE-clause composition) + `backend/app/services/graph.py` (service-layer query orchestration)

**Core pattern (full excerpt already in `06-RESEARCH.md` Pattern 1, lines 472-505):** each of the 10
tools is a small async function taking only typed, allowlisted parameters; `visible_until_order` is
always a parameter supplied by the pipeline caller — **never** read from the model's tool-call JSON
arguments (Anti-Patterns #1). Composes `spoiler/filter.py`'s existing `WHERE visible_from_order <=
$visible_until_order` clause pattern rather than reimplementing it (RAG-02/RAG-03, "Don't Hand-Roll"
table row 1).

**Fail-closed return convention:** empty result set on hidden-or-missing, identical in both cases —
`return rows[0] if rows else None` (RESEARCH line 504's comment: "empty result — hidden and missing
are indistinguishable, by design").

---

### Retrieval pipeline — `backend/app/retrieval/pipeline.py` (service, event-driven/streaming)

**Analog:** `backend/app/services/graph.py`'s `GraphService.fetch_graph` (concurrent Cypher fan-out via `asyncio.gather`)

Reuse the `asyncio.gather` concurrency pattern already used there for parallel retrieval-tool calls
within a bounded round, rather than serializing every tool call (RESEARCH Q19 compatibility risk) —
but bound total rounds/items via `LLM_MAX_TOOL_ROUNDS`/`LLM_MAX_CONTEXT_ITEMS` regardless of concurrency.

**Citation validation — check membership against *this turn's* retrieved set, not DB existence (Pitfall 3):**
validate every `claim_id`/`evidence_id`/`source_id` the model cites against the exact context object
passed to the final LLM call for this turn — re-querying Neo4j for existence/visibility independently
is insufficient (it would pass through IDs the model "remembers" but didn't legitimately retrieve now).

---

### System prompt — `backend/app/llm/system_prompt.py` (config/utility)

**Analog:** `backend/app/graph/ontology.py` (versioned, server-owned constant text/data, loaded once)

Module exposes `SYSTEM_PROMPT_VERSION` (string/int constant) + `SYSTEM_PROMPT_V1` (text constant).
Every untrusted context section (Notes/Claims/Evidence/Sources/chat history) must be wrapped in an
explicit, consistently-named delimiter referenced by name in the prompt text itself (Pitfall 2) — e.g.
`<evidence>...</evidence>` — and the prompt must explicitly state that content inside those tags is
data, never instructions. Tests (`test_prompt_injection.py`) must exercise the PRD's five exact
injection strings via malicious Note/Evidence content, not just the user's own chat message.

---

### Services — `backend/app/services/progress.py`, `chat.py`, `change_set.py` (service, CRUD/streaming/transactional)

**Analog:** `backend/app/services/series.py` (thin orchestration over repository) for `progress.py`;
`backend/app/services/auth.py` (Protocol-injected dependency orchestration) for `chat.py`;
`backend/app/api/revisions.py`'s `revert_revision` (read-branch-apply-log shape) for `change_set.py`.

**Core CRUD pattern (services import query constants / call repository, never hold raw Cypher themselves):**
services in this codebase never contain `tx.run`/`session.run` directly except the two documented
exceptions (`api/candidates.py`, `api/revisions.py`) — new services should follow the majority
pattern (delegate all Cypher to `repository/`/`graph/`), not the exception.

---

### API dependency — `backend/app/api/deps.py` (middleware, request-response)

**Analog:** `backend/app/api/auth.py` (`get_auth_service` `Depends` provider, lines 105-115) + the
existing `/me` route handler body (line ~224) that must be *factored out*, not duplicated.

**Core pattern (new code, not a reuse — RESEARCH Q9's correction is load-bearing):**
```python
# backend/app/api/deps.py (new file)
async def require_current_user(request: Request, service: AuthServiceDependency) -> dict[str, Any]:
    token = request.cookies.get(get_settings().session_cookie_name)
    user = await service.get_current_user(token, session_ttl=...) if token else None
    if user is None:
        raise http_error(401, "AUTH_UNAUTHENTICATED", "Authentication required.")
    return user
```
Name it `require_current_user`, **not** `get_current_user` — avoids import-shadowing collision with
the existing route handler of that name in `auth.py` (RESEARCH Q19 compatibility risk). The existing
`/me` route should then call this same dependency instead of duplicating its body.

**Error handling pattern (shared error envelope — copy exactly, do not invent a new shape):**
```python
# backend/app/core/errors.py's http_error()/error_responses() — the ONLY documented error shape,
# locked by test_frontend_contract_doc.py: {"detail": {"code": "...", "message": "..."}}
```
All new routers (chat, progress, change_set) use `http_error(status, code, message)` exactly like
every existing router — LLM-specific failures (503 provider-unavailable, disabled-provider) must use
this same helper, not a bespoke shape.

---

### API routers — `backend/app/api/progress.py`, `chat.py`, `change_set.py` (controller, request-response/streaming/transactional)

**Analog:** `backend/app/api/user_content.py` (CRUD route shape) for `progress.py`/non-streaming parts
of `chat.py`; `backend/app/api/revisions.py` for `change_set.py`.

**Streaming endpoint pattern (no existing analog — hand-rolled per RESEARCH Pattern 3, no new dependency):**
```python
# Source: Starlette/FastAPI built-in StreamingResponse — verified no sse-starlette needed
from fastapi.responses import StreamingResponse
import json

@router.post("/{session_id}/messages/stream")
async def stream_message(...) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        async for chunk in chat_service.answer_stream(...):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield f"event: done\ndata: {json.dumps(final_payload)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Mandatory Wave-0 blocker (apply to every new route file):** every new path template/operation must
be added to `backend/tests/test_openapi_contract.py` and `backend/tests/test_frontend_contract_doc.py`
(`EXPECTED_OPERATIONS`) plus `docs/frontend-api-contract.md`, in the same commit as the route — these
are closed-inventory `len(...) == N` assertions and will fail CI otherwise (RESEARCH Q19, "Wave 0 Gaps").

---

### Frontend API clients — `frontend/src/api/chat.ts`, `changeSet.ts`, `progress.ts` (service, request-response/streaming)

**Analog:** `frontend/src/api/client.ts` (shared `apiFetch` wrapper) + `frontend/src/api/userContent.ts`/`revisions.ts` (thin typed function modules)

**Exact `apiFetch` contract (verified this session, `frontend/src/api/client.ts` lines 1-40):**
```typescript
export type ApiErrorDetail = { code: string; message: string }
export class ApiError extends Error {
  code: string
  constructor(detail: ApiErrorDetail) { super(detail.message); this.name = 'ApiError'; this.code = detail.code }
}
type FetchOptions = { method?: 'GET'|'POST'|'PUT'|'PATCH'|'DELETE'; body?: unknown; headers?: Record<string,string> }
export async function apiFetch<T>(url: string, options?: FetchOptions): Promise<T> {
  const { method = 'GET', body, headers } = options ?? {}
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': body !== undefined ? 'application/json' : '', ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
  // ... throws ApiError on non-2xx, returns undefined on 204
}
```
Every non-streaming call in `chat.ts`/`changeSet.ts`/`progress.ts` must route through `apiFetch<T>`
exactly like `userContent.ts`/`revisions.ts` do — **no fetch/XHR call anywhere in the frontend
bypasses this wrapper** (RESEARCH Q11, verified).

**Streaming — the one call `apiFetch` cannot serve (new pattern, no analog):** `chat.ts`'s
`streamMessage()` needs a dedicated function using raw `fetch()` + manual `ReadableStream` reading
(`credentials: 'include'` preserved manually), since `apiFetch` awaits/parses a single JSON body.
`EventSource` is not viable (cannot POST a body/custom headers with cookies portably).

---

### Frontend hooks — `useChatSessions.ts`, `useChatMessages.ts` (hook, CRUD/streaming)

**Analog:** `frontend/src/hooks/useGraph.ts` (fetch-status state machine: `idle | loading | success | error`)

Copy the same discriminated status-union shape `useGraph.ts` uses for `graphState`; `useChatMessages`
additionally needs a `streaming` status variant and an accumulator for incremental text-delta chunks.

---

### `useWatchProgress.ts` (hook, modify — CRUD)

**Analog:** itself (modify in place)

Current: entirely `sessionStorage`-backed (`hdgraf.watchProgress` key), no backend call at all
(RESEARCH Q6, verified false-negative on backend persistence). Modify per RESEARCH Open Question 1's
recommendation: keep `ConfirmAdvanceModal`'s existing `requestChange`/`confirmChange`/`cancelChange`
API surface **unchanged**, but make `confirmChange` also `await` the new progress-update backend call
before committing local state, and prefer a backend `GET` over sessionStorage on initial hydration
when authenticated (sessionStorage remains a loading-state placeholder / optimistic cache only).

---

### `ChatPanel.tsx` and children (component, request-response/streaming)

**Analog:** `frontend/src/components/detail/DetailPanel.tsx` (730 lines — Sheet/Tabs structure, `NoteItem` hover-reveal pattern, accent-color constants)

**Mode-toggle mount point (06-UI-SPEC.md "Chat & Panel Architecture" is authoritative — quoting the
exact integration seam):** `DetailPanel.tsx`'s `<Sheet open modal={false}>` (line 508) currently has
`open` hardcoded to the literal `true` — making it stateful is a required, non-trivial change to this
component's contract (not additive-only). The mode toggle (two-segment "Inspector"/"Chat" pill, same
visual pattern as `EpisodeSelector`) renders in `SheetHeader` next to `SheetTitle`. Tabs render only
in Inspector mode; `ChatPanel` mounts as the Chat-mode content, independent of node/edge selection
(unlike Inspector's `"Select a node to see details."` fallback).

**Accent-color constants to reuse for `CitationChip` (do not invent new hues):**
`CLAIM_ACCENT_COLOR` (`#D946EF`) and `EVIDENCE_ACCENT_COLOR` (`#FB923C`) already defined in
`DetailPanel.tsx` — citation chips for claim/evidence citations must reuse these exact constants
(06-UI-SPEC.md Color section, "Citation chip accents").

**Hover-reveal delete pattern (for `SessionPicker` row delete icon):** `NoteItem`'s existing
hover/focus-reveal delete-icon micro-pattern in `DetailPanel.tsx` — copy verbatim rather than
inventing a new interaction.

**`ChangeSetCard` confirm/reject pattern:** `frontend/src/components/episode/ConfirmAdvanceModal.tsx`
is the canonical confirm/reject + warnings dialog pattern in this codebase — same Cancel(outline)/
Confirm(warning-or-destructive-styled) button pair, same "the label and color must match the real
consequence" principle already implicit there (06-UI-SPEC.md Copywriting Contract, "ChangeSet confirm
button" row explicitly cites this precedent).

---

### `GraphCanvas.tsx` (modify — component, event-driven)

**Analog:** itself (extend existing selection/highlight mechanism, lines 268-322, verified this session via RESEARCH Q12)

**Exact mechanism to extend (do not fork per RAG-17 "reuse, not fork"):**
```typescript
// frontend/src/components/graph/GraphCanvas.tsx lines 268-322 (existing)
cy.on('tap', 'node', (evt) => {
  const node = evt.target
  const neighborhood = node.closedNeighborhood()
  cy.elements().difference(neighborhood).addClass('faded')
  neighborhood.removeClass('faded')
  cy.elements().removeClass('selected-dominant edge-active')
  node.addClass('selected-dominant')
})
```
New required prop: `focusedElementIds: {nodeIds: string[], edgeIds: string[]} | null`, applied/cleared
in a `useEffect` keyed on that prop (same "prop-driven effect" pattern `useGraph.ts` already uses
elsewhere) — this is a **new capability**, `cyInstanceRef` is currently never exposed outside
`GraphCanvas.tsx` (RESEARCH Q12 "Architectural gap"). Documented, bounded supersession: `graph_focus`
may highlight **multiple** nodes/edges simultaneously (unlike single-click selection) — comment this
supersession in code exactly as `03.1-UI-SPEC.md` documented its own hover-color supersession of Phase 2
(06-UI-SPEC.md "Graph synchronization" section).

**Fit/center convention:** `cy.fit(undefined, 48)` — 48px padding, same as `GraphControls.tsx` line 36's
fit-to-view button; `GraphFocusIndicator`'s "Show in graph" must use this identical padding value.

**CSS classes (already defined, reuse as-is):** `.selected-dominant` (`graphStylesheet.ts`, border/overlay
`#7C3AED` = `--accent`), `.faded`, `.hovered`/`.edge-active`.

---

### `GraphFocusIndicator.tsx` (component, new)

**Analog:** `frontend/src/components/graph/GraphLegend.tsx`'s collapsed-pill overlay treatment

Same `bg-card`/`ring-border`/`text-xs`/`rounded-md`/`shadow-sm` visual treatment, positioned
`fixed top-4 left-4 z-[60]` (the one unclaimed canvas-overlay corner — bottom-left is `GraphLegend`
+ FAB, bottom-right is `GraphControls`). Copy: "Highlighting {N} from chat" + inline "Clear" text
action, same micro-pattern as `NoteItem`'s inline Edit/Delete text buttons.

---

### `ChatLauncher.tsx` (component, new)

**Analog:** `frontend/src/components/graph/GraphControls.tsx` (icon-button + `aria-label` + 44×44px touch-target convention)

Lives in `AppShell`'s `topBar` slot, after `EpisodeSelector`, before the user/avatar cluster (no
structural change needed to `AppShell.tsx` itself — the slot is already generic per RESEARCH Q17's
file list note).

---

## Shared Patterns

### Auth / Ownership
**Source:** `backend/app/api/auth.py` (`get_auth_service` `Depends` provider) + new `backend/app/api/deps.py::require_current_user`
**Apply to:** every new router (`progress.py`, `chat.py`, `change_set.py`) — all new resources
(`UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`) are the **first ownership-enforced
resources in this codebase** (no existing pattern to copy for cross-user 404 beyond the origin-conflict
two-query pattern in `user_content.py` — build tests fresh, no existing test file pattern-matches this).

### Error Envelope
**Source:** `backend/app/core/errors.py`'s `http_error()`/`error_responses()`, `{"detail": {"code", "message"}}`
**Apply to:** every new backend router and every repository sentinel exception → API error mapping.
This is the **only** documented error shape, locked by `test_frontend_contract_doc.py`.

### Single-transaction mutation + audit
**Source:** `backend/app/graph/database.py::Neo4jDatabase.execute_write` + `backend/app/revisions/__init__.py::RevisionRepository.log_revision`, composed together exactly as `backend/app/repository/user_content.py::_create_custom_node` does.
**Apply to:** `ChangeSet` apply/confirm, and any other new mutation (`progress` upsert does not need
revision logging — only user-content-shaped mutations do, per RAG-15's scope).

### Spoiler visibility filtering (compose, never fork)
**Source:** `backend/app/spoiler/filter.py`'s `WHERE visible_from_order <= $visible_until_order` clause shape.
**Apply to:** every retrieval tool in `retrieval/tools.py`, and `chat.py` repository's message-loading
queries (both the "for LLM context" and "for API response" methods must share the exact same filter
per Pitfall 1 — do not write two independently-maintained filter queries).

### Frontend fetch wrapper
**Source:** `frontend/src/api/client.ts::apiFetch<T>`
**Apply to:** every non-streaming call in `api/chat.ts`, `api/changeSet.ts`, `api/progress.ts`.

### Cytoscape highlight mechanism
**Source:** `frontend/src/components/graph/GraphCanvas.tsx` lines 268-322 + `graphStylesheet.ts`'s `.selected-dominant`/`.faded`/`.hovered` classes.
**Apply to:** `graph_focus` sync (`GraphCanvas`'s new `focusedElementIds` prop), `GraphFocusIndicator`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `backend/app/llm/provider.py` (real `OpenAICompatibleProvider` implementation body) | service | streaming | No existing LLM/HTTP-streaming provider code in repo (RESEARCH Q16, confirmed via grep) — shape borrowed from `GoogleTokenVerifier` Protocol, but the httpx-streaming body itself is genuinely new; use `06-RESEARCH.md` Pattern 2 as the primary reference instead of a repo analog |
| `backend/app/retrieval/pipeline.py` (tool-calling loop orchestration) | service | event-driven | No existing multi-round LLM tool-call loop in repo; bounded by `LLM_MAX_TOOL_ROUNDS` per CONTEXT.md's discretion note — orchestration shape is new, only the surrounding concurrency (`asyncio.gather`) and visibility-filtering pieces have analogs |
| `frontend/src/components/chat/MessageList.tsx` streaming-append + scroll-anchoring behavior | component | streaming | No existing incremental-text-append UI in this codebase (Notes/Claims/Evidence lists are all static-fetch, not streamed) — `scroll-area` shadcn component is new to this phase for this reason; nearest partial analog is `DetailPanel.tsx`'s Notes-tab list rendering for layout only, not streaming behavior |

## Metadata

**Analog search scope:** `backend/app/{api,domain,graph,repository,services,revisions,spoiler,core}/`, `backend/tests/`, `frontend/src/{api,hooks,components,types}/`, `frontend/src/test/`
**Files scanned:** primary source is `06-RESEARCH.md`'s Repository Investigation (19 questions, each with verified file:line citations); this session additionally re-read `backend/app/repository/user_content.py` (lines 1-60), `backend/app/graph/database.py` (grep for `execute_write`/`execute_query`/class signature), `frontend/src/api/client.ts` (lines 1-40) to fill exact-quote gaps not already verbatim in RESEARCH.md
**Pattern extraction date:** 2026-07-31
