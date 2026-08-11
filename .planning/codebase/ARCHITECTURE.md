---
last_mapped: 2026-08-12
focus: arch
last_mapped_commit: 1710d57db7c048a83299cadc072e0779f80f246d
---
<!-- refreshed: 2026-08-12 -->
# Architecture

**Analysis Date:** 2026-08-12

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ React SPA (`frontend/src/`)                                                  │
│ App/Auth providers → hooks → typed API clients → feature components          │
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                                │ HTTP JSON / SSE, credentials included         
                ▼                       ▼                                       
┌──────────────────────────────────────────────────────────────────────────────┐
│ FastAPI (`spoilerless/app/main.py`, `spoilerless/app/api/`)                  │
│ routes → domain validation → services → repositories / graph queries         │
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                │                       │                                       
                ▼                       ▼                                       
┌──────────────────────────────────┐  ┌───────────────────────────────────────┐ 
│ Neo4j (`spoilerless/app/graph/`) │  │ Optional LLM (`spoilerless/app/llm/`)  │
│ data, users, state, settings    │  │ allowlisted GraphRAG tools only   │      
└──────────────────────────────────┘  └───────────────────────────────────────┘ 
```

The product is a three-part web application: a state-driven React single-page application, an asynchronous FastAPI process, and Neo4j. The frontend and optional LLM receive only graph data that Cypher has already bounded by watch progress. Source-backed `Claim` nodes are projected into frontend graph edges by `GraphService`; structural relationships remain direct Neo4j relationships (`spoilerless/app/services/graph.py`, `spoilerless/app/spoiler/filter.py`).

The live API surface contains 50 HTTP operations on 37 unique path templates. Eleven routers are assembled in `spoilerless/app/main.py`; `/health` (GET and HEAD) is defined on the application itself (`spoilerless/app/api/`, `spoilerless/app/main.py`).

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| React composition root | Authentication gate, series/progress selection, graph/detail/chat/settings state | `frontend/src/App.tsx` |
| Typed frontend transport | Cookie-bearing JSON fetch and POST-based SSE parsing | `frontend/src/api/client.ts`, `frontend/src/api/chat.ts` |
| Frontend feature state | Async state machines for graph, progress, notes, revisions, and chat | `frontend/src/hooks/` |
| FastAPI assembly | Lifespan-owned database driver, CORS, handlers, router registration | `spoilerless/app/main.py` |
| HTTP boundary | Path/body/query validation, auth dependencies, response contracts | `spoilerless/app/api/` |
| Domain contracts | Strict Pydantic request/response models and typed ChangeSet union | `spoilerless/app/domain/` |
| Business orchestration | Graph, auth, progress, chat, ChangeSet, series, and settings workflows | `spoilerless/app/services/` |
| Persistence boundary | Neo4j-backed users, sessions, content, progress, chat, settings, ChangeSets | `spoilerless/app/repository/` |
| Graph query modules | Feature-specific parameterized Cypher and database lifecycle | `spoilerless/app/graph/` |
| Spoiler-safe graph reads | Central graph-response Cypher with per-hop visibility predicates, plus the effective-boundary and derived-visibility rules | `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py`, `spoilerless/app/spoiler/visibility.py` |
| GraphRAG retrieval | Twelve typed tools in one `TOOL_SPECS` registry, shared context sections, citation validation | `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/tools.py`, `spoilerless/app/retrieval/context.py` |
| LLM adapter | Gemini and OpenAI-compatible streaming providers and system prompts | `spoilerless/app/llm/provider.py`, `spoilerless/app/llm/system_prompt.py` |
| Revision log | Same-transaction append-only audit helpers | `spoilerless/app/revisions/__init__.py` |
| Share-link access | Token-based read-only share views; hash-stored share tokens | `spoilerless/app/api/share.py`, `spoilerless/app/repository/share.py` |
| Redis integration | Redis-backed rate limiting and cache-aside graph responses | `spoilerless/app/services/rate_limit.py`, `spoilerless/app/cache/` |
| Graph bootstrap | Ontology validation, constraints/indexes, seed, visibility audit | `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/seed.py` |

## Pattern Overview

**Overall:** Layered SPA + service/repository backend over a graph database, with a bounded tool-calling GraphRAG subsystem.

**Key Characteristics:**
- Use the normal backend dependency direction `api → services → repository → graph/database`; shared Pydantic contracts in `spoilerless/app/domain/` may be imported by all layers.
- Keep request values parameterized in Cypher. Dynamic labels or relationship types must come from server-side ontology allowlists (`spoilerless/app/graph/ontology.py`, `spoilerless/app/retrieval/tools.py`).
- Enforce spoiler visibility during Neo4j access, never by filtering an already-returned result in React or Python (`spoilerless/app/spoiler/filter.py`, `spoilerless/app/graph/chat.py`, `spoilerless/app/retrieval/tools.py`).
- Keep frontend wire models aligned with backend domain models (`frontend/src/types/`, `spoilerless/app/domain/`).
- Candidate review is the deliberate layering exception: routes call `CandidateRepository` directly and own transaction orchestration (`spoilerless/app/api/candidates.py`, `spoilerless/app/graph/candidates.py`).

## Layers

**Frontend Presentation:**
- Purpose: Render authentication, graph exploration, detail/editing, revision, chat, and settings experiences.
- Location: `frontend/src/components/`
- Contains: Feature folders plus reusable shadcn/Radix primitives in `frontend/src/components/ui/`.
- Depends on: Hooks and shared types from `frontend/src/hooks/` and `frontend/src/types/`.
- Used by: `frontend/src/App.tsx`.

**Frontend State and API:**
- Purpose: Hold browser state and convert typed actions into backend requests.
- Location: `frontend/src/hooks/`, `frontend/src/api/`, `frontend/src/providers/`
- Contains: Fetch state machines, Google-session context, JSON transport, and manual SSE stream parsing.
- Depends on: Browser Fetch API and contracts in `frontend/src/types/`.
- Used by: `frontend/src/App.tsx` and feature components.

**API Layer:**
- Purpose: Expose the 50-operation HTTP contract and translate domain/repository failures into stable envelopes.
- Location: `spoilerless/app/api/`
- Contains: `APIRouter` modules for auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, settings, and share.
- Depends on: `spoilerless/app/api/deps.py`, domain models, and service factories.
- Used by: `spoilerless/app/main.py`.

**Domain Layer:**
- Purpose: Define validated transport and business shapes.
- Location: `spoilerless/app/domain/`
- Contains: Pydantic models, enums, discriminated ChangeSet operations, and response envelopes.
- Depends on: Pydantic and standard-library types.
- Used by: API, services, repositories, retrieval, and tests.

**Service Layer:**
- Purpose: Orchestrate multi-step business workflows without embedding HTTP concerns.
- Location: `spoilerless/app/services/`
- Contains: `GraphService`, `SeriesService`, `AuthService`, `ProgressService`, `ChatService`, `ChangeSetService`, `SettingsService`, and the Redis-backed rate limiter (`rate_limit.py`). `AuthService` requires injected user/session repositories and a verifier — no silent fallback (PROB-09/#77).
- Depends on: Domain models and repository/database abstractions.
- Used by: API dependencies in `spoilerless/app/api/`.

**Repository Layer:**
- Purpose: Own persistence commands, record normalization, ownership scoping, and managed transactions.
- Location: `spoilerless/app/repository/`
- Contains: Neo4j repositories for users, sessions, user content, progress, chat, settings, ChangeSets, and share tokens.
- Depends on: Query constants in `spoilerless/app/graph/`, `Neo4jDatabase`, and domain models.
- Used by: Services; candidate routes are the direct-use exception.

**Graph and Spoiler Layer:**
- Purpose: Own connection lifecycle, parameterized Cypher, ontology loading, and bootstrap operations.
- Location: `spoilerless/app/graph/`, `spoilerless/app/spoiler/`
- Contains: `Neo4jDatabase`, feature query modules, seed/setup, ontology validation, label inventories (`labels.py`), and spoiler-safe graph queries.
- Depends on: Neo4j async driver, YAML/JSON content under `ontology/` and `data/dexter/`.
- Used by: Repositories, services, and the setup CLI.

**Retrieval and LLM Layer:**
- Purpose: Answer questions from bounded graph context without exposing arbitrary Cypher or direct writes.
- Location: `spoilerless/app/retrieval/`, `spoilerless/app/llm/`
- Contains: Twelve allowlisted retrieval tools in one registry, tool schemas, a shared context-section registry, citation validation, provider adapters, and prompt text.
- Depends on: Persisted progress, Neo4j reads, stored/environment settings, and an external compatible LLM endpoint.
- Used by: `ChatService` in `spoilerless/app/services/chat.py`.

## Data Flow

### Primary Graph Request Path

1. `AuthenticatedApp` passes the selected series and confirmed watch order to `useGraph()`, whose shared `useFetchState` machine keys on series plus visible order (`frontend/src/App.tsx`, `frontend/src/hooks/useGraph.ts`, `frontend/src/hooks/useFetchState.ts`).
2. `getGraph()` uses the shared cookie-bearing client to call `GET /api/series/{series_id}/graph?visible_until_order=N` (`frontend/src/api/graph.ts`, `frontend/src/api/client.ts`).
3. The route verifies the series, resolves `N` to a persisted episode, and consults the Redis cache-aside layer before calling `GraphService.fetch_graph()` (`spoilerless/app/api/graph.py`, `spoilerless/app/cache/graph_cache.py`).
4. `GraphService` runs seven independent reads concurrently: series, nodes, structural edges, canonical/candidate claims, user relationships, sources, and evidence (`spoilerless/app/services/graph.py:51`).
5. Every story-sensitive query applies visibility predicates in Cypher, including each endpoint/provenance hop (`spoilerless/app/spoiler/filter.py`).
6. Visible claims become `GraphEdge` records with IDs of the form `{claim.id}:edge`; structural and user edges join the same response collection (`spoilerless/app/services/graph.py`).
7. `GraphCanvas` converts the trusted response into Cytoscape elements without applying a second spoiler filter (`frontend/src/components/graph/graphElements.ts`, `frontend/src/components/graph/GraphCanvas.tsx`).

### Chat → Retrieval Tool → LLM Path

1. `useChatMessages()` sends a POST request and parses `text/event-stream` chunks from `/messages/stream` (`frontend/src/hooks/useChatMessages.ts`, `frontend/src/api/chat.ts`).
2. The route resolves the authenticated `AppUser`, checks user-scoped session access, ensures progress, and returns an SSE response (`spoilerless/app/api/chat.py`).
3. `ChatService.answer_stream()` resolves persisted watch progress, loads boundary-visible history, persists the user message with a boundary snapshot, and invokes `RetrievalPipeline` (`spoilerless/app/services/chat.py`).
4. `RetrievalPipeline` offers exactly twelve typed tool schemas from the single `TOOL_SPECS` registry to the configured provider (honoring per-request `X-LLM-*` BYOK headers) and rejects unknown or invalid tool calls (`spoilerless/app/retrieval/pipeline.py`).
5. Tool execution injects `series_id`, `user_id`, and the server-resolved boundary; the model cannot supply those authority values or arbitrary Cypher (`spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/tools.py`).
6. Retrieved rows are deduplicated and bounded, then passed as delimited data to a final provider call with tools disabled (`spoilerless/app/retrieval/pipeline.py`).
7. Citations survive only if their IDs occur in this turn's retrieved set; invalid citations are stripped and an ungrounded completion falls back safely (`spoilerless/app/retrieval/pipeline.py`).
8. `ChatService` persists the assistant `ChatMessage` and emits a final envelope containing citations and graph-focus IDs (`spoilerless/app/services/chat.py`).

### Typed ChangeSet Mutation Path

1. A client proposes a Pydantic-discriminated operation list at `POST /api/series/{series_id}/change-sets` (`spoilerless/app/domain/change_set.py`, `spoilerless/app/api/change_set.py`).
2. `ChangeSetService.propose()` resolves persisted progress, validates every target for existence, series scope, and visibility, and converts prohibited canonical/candidate direct edits to `create_note` operations (`spoilerless/app/services/change_set.py`).
3. Proposal persists only a `ChangeSet` in `awaiting_confirmation`; it does not mutate target graph content (`spoilerless/app/repository/change_set.py`).
4. Confirm re-reads progress and targets inside one managed Neo4j write transaction, detects stale state, applies all operations via the table-driven `_APPLY_SPECS` dispatch (PROB-09/#67), marks status, and logs one `Revision` atomically; `WITH u, s` carried between MERGEs avoids the Neo4j 5.x 503 class (`spoilerless/app/repository/change_set.py`).
5. Reject changes only ChangeSet status. Revert supports create-shaped applies and writes a separate `Reverted` revision (`spoilerless/app/repository/change_set.py`).

**State Management:**
- Browser state is local React state and hooks; there is no router or global data store (`frontend/src/App.tsx`).
- `sessionStorage` is only a watch-progress loading cache; Neo4j is authoritative (`frontend/src/hooks/useWatchProgress.ts`, `spoilerless/app/repository/progress.py`).
- Users, sessions, notes/custom content, revisions, progress, chat sessions/messages, ChangeSets, and LLM settings are Neo4j-backed (`spoilerless/app/repository/`).
- Per-user in-flight chat generation limits are process-local module state and assume one worker (`spoilerless/app/services/chat.py:51`).

## Key Abstractions

**Visibility Boundary:**
- Purpose: Represent the highest episode order safe for the current user.
- Examples: `spoilerless/app/domain/user_content.py`, `spoilerless/app/services/progress.py`, `spoilerless/app/spoiler/filter.py`.
- Pattern: Server-resolved positive episode order injected into parameterized Cypher; hidden and absent resources share a generic not-found response where applicable.

**Claim Projection:**
- Purpose: Present evidence-backed `Claim` nodes as graph edges while retaining provenance detail.
- Examples: `spoilerless/app/domain/graph.py`, `spoilerless/app/services/graph.py`.
- Pattern: `subject_id → object_id` projection carrying `claim_id`; direct structural edges carry `claim_id = null`.

**Neo4jDatabase:**
- Purpose: Centralize the async driver and retryable query/transaction APIs.
- Examples: `spoilerless/app/graph/database.py`.
- Pattern: Construct/open/close in FastAPI lifespan; repositories receive the application-owned instance.

**Ontology:**
- Purpose: Validate node, relationship, and claim vocabulary and expose user-safe subsets.
- Examples: `spoilerless/app/graph/ontology.py`, `ontology/node_types.yaml`, `ontology/relation_types.yaml`, `ontology/claim_types.yaml`.
- Pattern: Versioned YAML loaded into an immutable application abstraction.

**Typed ChangeSet:**
- Purpose: Separate machine-proposed edits from explicitly confirmed, transactional graph mutations.
- Examples: `spoilerless/app/domain/change_set.py`, `spoilerless/app/services/change_set.py`, `spoilerless/app/repository/change_set.py`.
- Pattern: Propose → confirm/reject → optional guarded revert.

## Entry Points

**Backend application:**
- Location: `spoilerless/app/main.py`
- Triggers: `uv run uvicorn spoilerless.app.main:app --reload`.
- Responsibilities: Build FastAPI, register routers/middleware/handlers, own Neo4j and Redis lifecycle, install security/logging middleware, expose health.

**Database setup CLI:**
- Location: `spoilerless/app/graph/setup.py`
- Triggers: `uv run spoilerless-setup` from `pyproject.toml`.
- Responsibilities: Open Neo4j, validate ontology/seed, create constraints/indexes, seed content, audit visibility.

**Frontend application:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite through scripts in `frontend/package.json`.
- Responsibilities: Mount `App` under React strict mode.

## Architectural Constraints

- **Threading:** FastAPI and the Neo4j driver are asynchronous; graph reads use `asyncio.gather()` (`spoilerless/app/services/graph.py`). The `InMemorySessionRepository` test double uses a lock, while production sessions use Neo4j (`spoilerless/app/repository/session.py`).
- **Global state:** FastAPI's app state owns the database plus the Neo4j-backed session and share repositories; the Redis client is an `lru_cache` singleton (`spoilerless/app/main.py`, `spoilerless/app/cache/redis_client.py`). Settings are cached by `get_settings`; chat concurrency uses a module-level dictionary (`spoilerless/app/core/config.py`, `spoilerless/app/services/chat.py`).
- **Import behavior:** Most `__init__.py` files are empty or docstrings. `spoilerless/app/revisions/__init__.py` defines the revision repository and query at import time but performs no I/O. `spoilerless/app/api/graph.py` loads ontology-derived relationship allowlists during module import (`spoilerless/app/revisions/__init__.py`, `spoilerless/app/api/graph.py:28`).
- **Database lifecycle:** `Neo4jDatabase` has no driver side effect in its constructor; `open()` occurs in application lifespan or setup CLI (`spoilerless/app/graph/database.py`, `spoilerless/app/main.py`, `spoilerless/app/graph/setup.py`).
- **Schema evolution:** No migration framework is present. Idempotent DDL in `spoilerless/app/graph/seed.py` and `Neo4jSessionRepository` is the schema mechanism; run `spoilerless-setup` for a prepared database (`spoilerless/app/graph/seed.py`, `spoilerless/app/repository/session.py`, `pyproject.toml`).
- **Storage readiness:** Seed DDL covers seeded content, users, revisions, sessions, progress/chat indexes. It does not define explicit uniqueness constraints for `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`, or `AppSetting`, even though those repositories persist such nodes; `ShareToken` is the exception and gets explicit uniqueness constraints plus an expiry index (`spoilerless/app/graph/seed.py`, `spoilerless/app/graph/progress.py`, `spoilerless/app/graph/chat.py`, `spoilerless/app/graph/change_set.py`, `spoilerless/app/repository/settings.py`).
- **Auth boundary:** User-owned routes must resolve `CurrentUserDependency` and scope Cypher from `(:AppUser {id: $user_id})` (`spoilerless/app/api/deps.py`, `spoilerless/app/repository/`).

## Anti-Patterns

### Application-side spoiler filtering

**What happens:** A consumer fetches broad data and hides future items in Python, React, or prompt instructions.
**Why it's wrong:** The browser or LLM already receives the spoiler before presentation filtering.
**Do this instead:** Put every visibility predicate on every relevant query hop in `spoilerless/app/spoiler/filter.py`, `spoilerless/app/retrieval/tools.py`, or the owning data-access query module.

### Arbitrary LLM query or write access

**What happens:** Model text becomes Cypher or a direct graph mutation.
**Why it's wrong:** It bypasses server authority, ontology validation, spoiler boundaries, user confirmation, and revision logging.
**Do this instead:** Add typed retrieval tools in `spoilerless/app/retrieval/` or typed ChangeSet operations in `spoilerless/app/domain/change_set.py` and preserve the service/repository validation flow.

### Runtime logic in package initializers

**What happens:** Feature implementations accumulate in `__init__.py`, as the revision repository does in `spoilerless/app/revisions/__init__.py`.
**Why it's wrong:** It obscures module boundaries and makes imports less discoverable, even when no I/O runs.
**Do this instead:** Put new implementations in named modules and keep package initializers empty, declarative, or limited to explicit re-exports (`spoilerless/app/services/`, `spoilerless/app/repository/`).

## Error Handling

**Strategy:** Validate at Pydantic/FastAPI boundaries, use feature exceptions inside services/repositories, and translate them to generic structured HTTP errors.

**Patterns:**
- Use `{ "detail": { "code": "...", "message": "..." } }` via `spoilerless/app/core/errors.py`; `frontend/src/api/client.ts` normalizes this and FastAPI validation arrays.
- Install database and LLM exception handlers centrally in `spoilerless/app/main.py`.
- `ServiceUnavailable`/`AuthError`/`Neo4jError` map to 503 `DATABASE_UNAVAILABLE`; `ConstraintError` maps to 409 `CONSTRAINT_VIOLATION`; rate-limit rejection maps to 429 `TOO_MANY_REQUESTS` (`spoilerless/app/core/errors.py`).
- `ClientError` (invalid Cypher) is deliberately excluded from the 503 mapping — masking it would hide app bugs — so it surfaces as a plain 500 (`spoilerless/app/core/errors.py`).
- Make hidden, foreign, and missing user-scoped resources indistinguishable where disclosure would leak ownership or future content (`spoilerless/app/repository/chat.py`, `spoilerless/app/api/chat.py`).
- Emit structured terminal SSE error events after headers have been sent (`spoilerless/app/api/chat.py`, `frontend/src/api/chat.ts`).

## Cross-Cutting Concerns

**Logging:** No centralized application logging layer is present; avoid printing secrets or query internals. The setup CLI prints only aggregate counts (`spoilerless/app/graph/setup.py`).
**Validation:** Pydantic models validate HTTP and LLM-tool inputs; ontology and seed validators gate graph types/content (`spoilerless/app/domain/`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/graph/ontology.py`, `spoilerless/app/graph/seed.py`).
**Authentication:** Google ID tokens create hashed-token HttpOnly sessions; only the token hash is persisted in Neo4j (`spoilerless/app/services/auth.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/api/deps.py`).
**Secrets:** LLM API keys are write-only in the API contract and masked on reads; provider construction reads the full stored value only server-side (`spoilerless/app/services/settings.py`, `spoilerless/app/services/chat.py`).
**Provenance:** Canonical/candidate claims require source/evidence links; retrieval citations are checked against the current turn's retrieved IDs (`spoilerless/app/graph/seed.py`, `spoilerless/app/retrieval/pipeline.py`).

---

*Architecture analysis: 2026-08-12*
