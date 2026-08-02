---
last_mapped: 2026-08-02
focus: arch
last_mapped_commit: 0b4c83c8ca7c8c0004552cb55b53a5050978c30c
---
<!-- refreshed: 2026-08-02 -->
# Architecture

**Analysis Date:** 2026-08-02

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ React SPA (`frontend/src/`)                                         │
│ App/Auth providers → hooks → typed API clients → feature components │
└───────────────────────────────┬──────────────────────────────────────┘
                                │ HTTP JSON / SSE, credentials included
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│ FastAPI (`backend/app/main.py`, `backend/app/api/`)                  │
│ routes → domain validation → services → repositories / graph queries│
└───────────────┬───────────────────────────────┬──────────────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────────┐  ┌────────────────────────────────────┐
│ Neo4j (`backend/app/graph/`) │  │ Optional LLM (`backend/app/llm/`) │
│ data, users, state, settings │  │ allowlisted GraphRAG tools only   │
└──────────────────────────────┘  └────────────────────────────────────┘
```

The product is a three-part web application: a state-driven React single-page application, an asynchronous FastAPI process, and Neo4j. The frontend and optional LLM receive only graph data that Cypher has already bounded by watch progress. Source-backed `Claim` nodes are projected into frontend graph edges by `GraphService`; structural relationships remain direct Neo4j relationships (`backend/app/services/graph.py`, `backend/app/spoiler/filter.py`).

The live API surface contains 44 HTTP operations on 32 unique path templates. Ten routers are assembled in `backend/app/main.py`; `/health` is defined on the application itself (`backend/app/api/`, `backend/app/main.py`).

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| React composition root | Authentication gate, series/progress selection, graph/detail/chat/settings state | `frontend/src/App.tsx` |
| Typed frontend transport | Cookie-bearing JSON fetch and POST-based SSE parsing | `frontend/src/api/client.ts`, `frontend/src/api/chat.ts` |
| Frontend feature state | Async state machines for graph, progress, notes, revisions, and chat | `frontend/src/hooks/` |
| FastAPI assembly | Lifespan-owned database driver, CORS, handlers, router registration | `backend/app/main.py` |
| HTTP boundary | Path/body/query validation, auth dependencies, response contracts | `backend/app/api/` |
| Domain contracts | Strict Pydantic request/response models and typed ChangeSet union | `backend/app/domain/` |
| Business orchestration | Graph, auth, progress, chat, ChangeSet, series, and settings workflows | `backend/app/services/` |
| Persistence boundary | Neo4j-backed users, sessions, content, progress, chat, settings, ChangeSets | `backend/app/repository/` |
| Graph query modules | Feature-specific parameterized Cypher and database lifecycle | `backend/app/graph/` |
| Spoiler-safe graph reads | Central graph-response Cypher with per-hop visibility predicates | `backend/app/spoiler/filter.py` |
| GraphRAG retrieval | Eleven typed tools, context bounds, citation validation | `backend/app/retrieval/pipeline.py`, `backend/app/retrieval/tools.py` |
| LLM adapter | Gemini and OpenAI-compatible streaming providers and system prompts | `backend/app/llm/provider.py`, `backend/app/llm/system_prompt.py` |
| Revision log | Same-transaction append-only audit helpers | `backend/app/revisions/__init__.py` |
| Graph bootstrap | Ontology validation, constraints/indexes, seed, visibility audit | `backend/app/graph/setup.py`, `backend/app/graph/seed.py` |

## Pattern Overview

**Overall:** Layered SPA + service/repository backend over a graph database, with a bounded tool-calling GraphRAG subsystem.

**Key Characteristics:**
- Use the normal backend dependency direction `api → services → repository → graph/database`; shared Pydantic contracts in `backend/app/domain/` may be imported by all layers.
- Keep request values parameterized in Cypher. Dynamic labels or relationship types must come from server-side ontology allowlists (`backend/app/graph/ontology.py`, `backend/app/retrieval/tools.py`).
- Enforce spoiler visibility during Neo4j access, never by filtering an already-returned result in React or Python (`backend/app/spoiler/filter.py`, `backend/app/graph/chat.py`, `backend/app/retrieval/tools.py`).
- Keep frontend wire models aligned with backend domain models (`frontend/src/types/`, `backend/app/domain/`).
- Candidate review is the deliberate layering exception: routes call `CandidateRepository` directly and own transaction orchestration (`backend/app/api/candidates.py`, `backend/app/graph/candidates.py`).

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
- Purpose: Expose the 44-operation HTTP contract and translate domain/repository failures into stable envelopes.
- Location: `backend/app/api/`
- Contains: `APIRouter` modules for auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, and settings.
- Depends on: `backend/app/api/deps.py`, domain models, and service factories.
- Used by: `backend/app/main.py`.

**Domain Layer:**
- Purpose: Define validated transport and business shapes.
- Location: `backend/app/domain/`
- Contains: Pydantic models, enums, discriminated ChangeSet operations, and response envelopes.
- Depends on: Pydantic and standard-library types.
- Used by: API, services, repositories, retrieval, and tests.

**Service Layer:**
- Purpose: Orchestrate multi-step business workflows without embedding HTTP concerns.
- Location: `backend/app/services/`
- Contains: `GraphService`, `SeriesService`, `AuthService`, `ProgressService`, `ChatService`, `ChangeSetService`, and `SettingsService`.
- Depends on: Domain models and repository/database abstractions.
- Used by: API dependencies in `backend/app/api/`.

**Repository Layer:**
- Purpose: Own persistence commands, record normalization, ownership scoping, and managed transactions.
- Location: `backend/app/repository/`
- Contains: Neo4j repositories for users, sessions, user content, progress, chat, settings, and ChangeSets.
- Depends on: Query constants in `backend/app/graph/`, `Neo4jDatabase`, and domain models.
- Used by: Services; candidate routes are the direct-use exception.

**Graph and Spoiler Layer:**
- Purpose: Own connection lifecycle, parameterized Cypher, ontology loading, and bootstrap operations.
- Location: `backend/app/graph/`, `backend/app/spoiler/`
- Contains: `Neo4jDatabase`, feature query modules, seed/setup, ontology validation, and spoiler-safe graph queries.
- Depends on: Neo4j async driver, YAML/JSON content under `ontology/` and `data/dexter/`.
- Used by: Repositories, services, and the setup CLI.

**Retrieval and LLM Layer:**
- Purpose: Answer questions from bounded graph context without exposing arbitrary Cypher or direct writes.
- Location: `backend/app/retrieval/`, `backend/app/llm/`
- Contains: Eleven allowlisted retrieval tools, tool schemas, context assembly, citation validation, provider adapters, and prompt text.
- Depends on: Persisted progress, Neo4j reads, stored/environment settings, and an external compatible LLM endpoint.
- Used by: `ChatService` in `backend/app/services/chat.py`.

## Data Flow

### Primary Graph Request Path

1. `AuthenticatedApp` passes the selected series and confirmed watch order to `useGraph()` (`frontend/src/App.tsx:47`, `frontend/src/hooks/useGraph.ts:16`).
2. `getGraph()` uses the shared cookie-bearing client to call `GET /api/series/{series_id}/graph?visible_until_order=N` (`frontend/src/api/graph.ts`, `frontend/src/api/client.ts:32`).
3. The route verifies the series and resolves `N` to a persisted episode before calling `GraphService.fetch_graph()` (`backend/app/api/graph.py:51`).
4. `GraphService` runs seven independent reads concurrently: series, nodes, structural edges, canonical/candidate claims, user relationships, sources, and evidence (`backend/app/services/graph.py:50`).
5. Every story-sensitive query applies visibility predicates in Cypher, including each endpoint/provenance hop (`backend/app/spoiler/filter.py`).
6. Visible claims become `GraphEdge` records with IDs of the form `{claim.id}:edge`; structural and user edges join the same response collection (`backend/app/services/graph.py:86`).
7. `GraphCanvas` converts the trusted response into Cytoscape elements without applying a second spoiler filter (`frontend/src/components/graph/graphElements.ts`, `frontend/src/components/graph/GraphCanvas.tsx`).

### Chat → Retrieval Tool → LLM Path

1. `useChatMessages()` sends a POST request and parses `text/event-stream` chunks from `/messages/stream` (`frontend/src/hooks/useChatMessages.ts:70`, `frontend/src/api/chat.ts:69`).
2. The route resolves the authenticated `AppUser`, checks user-scoped session access, ensures progress, and returns an SSE response (`backend/app/api/chat.py:183`).
3. `ChatService.answer_stream()` resolves persisted watch progress, loads boundary-visible history, persists the user message with a boundary snapshot, and invokes `RetrievalPipeline` (`backend/app/services/chat.py:211`).
4. `RetrievalPipeline` offers exactly eleven typed tool schemas to the configured provider and rejects unknown or invalid tool calls (`backend/app/retrieval/pipeline.py:510`).
5. Tool execution injects `series_id`, `user_id`, and the server-resolved boundary; the model cannot supply those authority values or arbitrary Cypher (`backend/app/retrieval/pipeline.py:657`, `backend/app/retrieval/tools.py`).
6. Retrieved rows are deduplicated and bounded, then passed as delimited data to a final provider call with tools disabled (`backend/app/retrieval/pipeline.py:734`).
7. Citations survive only if their IDs occur in this turn's retrieved set; invalid citations are stripped and an ungrounded completion falls back safely (`backend/app/retrieval/pipeline.py:815`).
8. `ChatService` persists the assistant `ChatMessage` and emits a final envelope containing citations and graph-focus IDs (`backend/app/services/chat.py:279`).

### Typed ChangeSet Mutation Path

1. A client proposes a Pydantic-discriminated operation list at `POST /api/series/{series_id}/change-sets` (`backend/app/domain/change_set.py`, `backend/app/api/change_set.py:66`).
2. `ChangeSetService.propose()` resolves persisted progress, validates every target for existence, series scope, and visibility, and converts prohibited canonical/candidate direct edits to `create_note` operations (`backend/app/services/change_set.py:154`).
3. Proposal persists only a `ChangeSet` in `awaiting_confirmation`; it does not mutate target graph content (`backend/app/repository/change_set.py:210`).
4. Confirm re-reads progress and targets inside one managed Neo4j write transaction, detects stale state, applies all operations, marks status, and logs one `Revision` atomically (`backend/app/repository/change_set.py:236`, `backend/app/repository/change_set.py:396`).
5. Reject changes only ChangeSet status. Revert supports create-shaped applies and writes a separate `Reverted` revision (`backend/app/repository/change_set.py:267`, `backend/app/repository/change_set.py:276`).

**State Management:**
- Browser state is local React state and hooks; there is no router or global data store (`frontend/src/App.tsx`).
- `sessionStorage` is only a watch-progress loading cache; Neo4j is authoritative (`frontend/src/hooks/useWatchProgress.ts`, `backend/app/repository/progress.py`).
- Users, sessions, notes/custom content, revisions, progress, chat sessions/messages, ChangeSets, and LLM settings are Neo4j-backed (`backend/app/repository/`).
- Per-user in-flight chat generation limits are process-local module state and assume one worker (`backend/app/services/chat.py:42`).

## Key Abstractions

**Visibility Boundary:**
- Purpose: Represent the highest episode order safe for the current user.
- Examples: `backend/app/domain/user_content.py`, `backend/app/services/progress.py`, `backend/app/spoiler/filter.py`.
- Pattern: Server-resolved positive episode order injected into parameterized Cypher; hidden and absent resources share a generic not-found response where applicable.

**Claim Projection:**
- Purpose: Present evidence-backed `Claim` nodes as graph edges while retaining provenance detail.
- Examples: `backend/app/domain/graph.py`, `backend/app/services/graph.py`.
- Pattern: `subject_id → object_id` projection carrying `claim_id`; direct structural edges carry `claim_id = null`.

**Neo4jDatabase:**
- Purpose: Centralize the async driver and retryable query/transaction APIs.
- Examples: `backend/app/graph/database.py`.
- Pattern: Construct/open/close in FastAPI lifespan; repositories receive the application-owned instance.

**Ontology:**
- Purpose: Validate node, relationship, and claim vocabulary and expose user-safe subsets.
- Examples: `backend/app/graph/ontology.py`, `ontology/node_types.yaml`, `ontology/relation_types.yaml`, `ontology/claim_types.yaml`.
- Pattern: Versioned YAML loaded into an immutable application abstraction.

**Typed ChangeSet:**
- Purpose: Separate machine-proposed edits from explicitly confirmed, transactional graph mutations.
- Examples: `backend/app/domain/change_set.py`, `backend/app/services/change_set.py`, `backend/app/repository/change_set.py`.
- Pattern: Propose → confirm/reject → optional guarded revert.

## Entry Points

**Backend application:**
- Location: `backend/app/main.py`
- Triggers: `uv run uvicorn backend.app.main:app --reload`.
- Responsibilities: Build FastAPI, register routers/middleware/handlers, own Neo4j lifecycle, expose health.

**Database setup CLI:**
- Location: `backend/app/graph/setup.py`
- Triggers: `uv run hdgraf-setup` from `pyproject.toml`.
- Responsibilities: Open Neo4j, validate ontology/seed, create constraints/indexes, seed content, audit visibility.

**Frontend application:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite through scripts in `frontend/package.json`.
- Responsibilities: Mount `App` under React strict mode.

## Architectural Constraints

- **Threading:** FastAPI and the Neo4j driver are asynchronous; graph reads use `asyncio.gather()`. The in-memory session repository uses a lock, while production sessions use Neo4j (`backend/app/services/graph.py`, `backend/app/repository/session.py`).
- **Global state:** FastAPI's app state owns the database and production session repository. Settings are cached by `get_settings`; chat concurrency uses a module-level dictionary (`backend/app/main.py`, `backend/app/core/config.py`, `backend/app/services/chat.py`).
- **Import behavior:** Most `__init__.py` files are empty or docstrings. `backend/app/revisions/__init__.py` defines the revision repository and query at import time but performs no I/O. `backend/app/api/graph.py` loads ontology-derived relationship allowlists during module import (`backend/app/revisions/__init__.py`, `backend/app/api/graph.py:28`).
- **Database lifecycle:** `Neo4jDatabase` has no driver side effect in its constructor; `open()` occurs in application lifespan or setup CLI (`backend/app/graph/database.py`, `backend/app/main.py`, `backend/app/graph/setup.py`).
- **Schema evolution:** No migration framework is present. Idempotent DDL in `backend/app/graph/seed.py` and `Neo4jSessionRepository` is the schema mechanism; run `hdgraf-setup` for a prepared database (`backend/app/graph/seed.py`, `backend/app/repository/session.py`, `pyproject.toml`).
- **Storage readiness:** Seed DDL covers seeded content, users, revisions, sessions, progress/chat indexes. It does not define explicit uniqueness constraints for `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`, or `AppSetting`, even though those repositories persist such nodes (`backend/app/graph/seed.py`, `backend/app/graph/progress.py`, `backend/app/graph/chat.py`, `backend/app/graph/change_set.py`, `backend/app/repository/settings.py`).
- **Auth boundary:** User-owned routes must resolve `CurrentUserDependency` and scope Cypher from `(:AppUser {id: $user_id})` (`backend/app/api/deps.py`, `backend/app/repository/`).

## Anti-Patterns

### Application-side spoiler filtering

**What happens:** A consumer fetches broad data and hides future items in Python, React, or prompt instructions.
**Why it's wrong:** The browser or LLM already receives the spoiler before presentation filtering.
**Do this instead:** Put every visibility predicate on every relevant query hop in `backend/app/spoiler/filter.py`, `backend/app/retrieval/tools.py`, or the owning data-access query module.

### Arbitrary LLM query or write access

**What happens:** Model text becomes Cypher or a direct graph mutation.
**Why it's wrong:** It bypasses server authority, ontology validation, spoiler boundaries, user confirmation, and revision logging.
**Do this instead:** Add typed retrieval tools in `backend/app/retrieval/` or typed ChangeSet operations in `backend/app/domain/change_set.py` and preserve the service/repository validation flow.

### Runtime logic in package initializers

**What happens:** Feature implementations accumulate in `__init__.py`, as the revision repository does in `backend/app/revisions/__init__.py`.
**Why it's wrong:** It obscures module boundaries and makes imports less discoverable, even when no I/O runs.
**Do this instead:** Put new implementations in named modules and keep package initializers empty, declarative, or limited to explicit re-exports (`backend/app/services/`, `backend/app/repository/`).

## Error Handling

**Strategy:** Validate at Pydantic/FastAPI boundaries, use feature exceptions inside services/repositories, and translate them to generic structured HTTP errors.

**Patterns:**
- Use `{ "detail": { "code": "...", "message": "..." } }` via `backend/app/core/errors.py`; `frontend/src/api/client.ts` normalizes this and FastAPI validation arrays.
- Install database and LLM exception handlers centrally in `backend/app/main.py`.
- Make hidden, foreign, and missing user-scoped resources indistinguishable where disclosure would leak ownership or future content (`backend/app/repository/chat.py`, `backend/app/api/chat.py`).
- Emit structured terminal SSE error events after headers have been sent (`backend/app/api/chat.py`, `frontend/src/api/chat.ts`).

## Cross-Cutting Concerns

**Logging:** No centralized application logging layer is present; avoid printing secrets or query internals. The setup CLI prints only aggregate counts (`backend/app/graph/setup.py`).
**Validation:** Pydantic models validate HTTP and LLM-tool inputs; ontology and seed validators gate graph types/content (`backend/app/domain/`, `backend/app/retrieval/pipeline.py`, `backend/app/graph/ontology.py`, `backend/app/graph/seed.py`).
**Authentication:** Google ID tokens create hashed-token HttpOnly sessions; only the token hash is persisted in Neo4j (`backend/app/services/auth.py`, `backend/app/repository/session.py`, `backend/app/api/deps.py`).
**Secrets:** LLM API keys are write-only in the API contract and masked on reads; provider construction reads the full stored value only server-side (`backend/app/services/settings.py`, `backend/app/services/chat.py`).
**Provenance:** Canonical/candidate claims require source/evidence links; retrieval citations are checked against the current turn's retrieved IDs (`backend/app/graph/seed.py`, `backend/app/retrieval/pipeline.py`).

---

*Architecture analysis: 2026-08-02*
