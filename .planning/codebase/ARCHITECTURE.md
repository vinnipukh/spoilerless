---
last_mapped: 2026-08-14
focus: arch
last_mapped_commit: 5bd1641
---
<!-- refreshed: 2026-08-14 (covers HEAD 5bd1641 plus uncommitted working-tree changes) -->
# Architecture

**Analysis Date:** 2026-08-14

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ React SPA (`frontend/src/`)                                                  │
│ App/Auth providers → hooks → typed API clients → feature components          │
│ graph workspace: useSceneState → visualizationAdapter → GraphCanvas           │
│   → react-cytoscapejs (frozen props) + cytoscapeReconciler (imperative diffs)│
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                                │ HTTP JSON / SSE, credentials included         
                ▼                       ▼                                       
┌──────────────────────────────────────────────────────────────────────────────┐
│ FastAPI (`spoilerless/app/main.py`, `spoilerless/app/api/`)                  │
│ routes → domain validation → services → repositories / graph queries         │
│ Phase 10: visualization projections + expansion deltas over safe graph rows  │
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                │                       │                                       
                ▼                       ▼                                       
┌──────────────────────────────────┐  ┌───────────────────────────────────────┐ 
│ Neo4j (`spoilerless/app/graph/`) │  │ Optional LLM (`spoilerless/app/llm/`)  │
│ data, users, state, settings    │  │ allowlisted GraphRAG tools only   │      
└──────────────────────────────────┘  └───────────────────────────────────────┘ 
```

The product is a three-part web application: a state-driven React single-page application, an asynchronous FastAPI process, and Neo4j. The frontend and optional LLM receive only graph data that Cypher has already bounded by watch progress. Source-backed `Claim` nodes are projected into frontend graph edges by `GraphService`; structural relationships remain direct Neo4j relationships (`spoilerless/app/services/graph.py`, `spoilerless/app/spoiler/filter.py`).

The live API surface contains 52 HTTP operations on 39 unique path templates. Eleven routers are assembled in `spoilerless/app/main.py`; `/health` (GET and HEAD) is defined on the application itself (`spoilerless/app/api/`, `spoilerless/app/main.py`).

Since the 2026-08-12 map (commit `1710d57`), Phase 10 added a bounded presentation-projection layer between `GraphService` and the SPA:

- `GET /api/series/{series_id}/graph/visualization` serves versioned, library-neutral `VisualizationDTO` projections (six view types) produced only from complete safe `GraphResponse` rows — never from hidden rows (D-05) — with semantic relation classes instead of raw Neo4j names (D-14).
- `GET /api/series/{series_id}/graph/expand` serves allowlisted semantic expansion deltas (D-21); this path is intentionally uncached (T10-CACHE-06).
- Projections are cache-aside in Redis with boundary/version/focus-aware keys (`spoilerless/app/cache/graph_cache.py`).
- On the frontend, the graph canvas renders through a topology-aware imperative reconciler (`frontend/src/components/graph/cytoscapeReconciler.ts`) because react-cytoscapejs's declarative id-only patcher cascade-deletes shared nodes on compound→flat scene switches (legacy curated graph ↔ projection scenes). `GraphCanvas` freezes the declarative `elements`/`layout` props after mount and applies every scene update through the reconciler (`frontend/src/components/graph/GraphCanvas.tsx`).
- Character portraits are self-hosted under `spoilerless/app/static/characters/` and served from a `/api/static` mount (never external CDNs; CSP `img-src 'self'`).

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| React composition root | Authentication gate, series/progress selection, graph/detail/chat/settings state; four-tab narrative workspace in Full mode | `frontend/src/App.tsx` |
| Typed frontend transport | Cookie-bearing JSON fetch and POST-based SSE parsing | `frontend/src/api/client.ts`, `frontend/src/api/chat.ts` |
| Frontend feature state | Async state machines for graph, progress, notes, revisions, and chat | `frontend/src/hooks/` |
| Frontend scene state | Serializable scene-state reducer: active view, filters, selection, focus, camera, positions, expansions, timeline, Inspector (D-24: React state owns scene) | `frontend/src/hooks/useSceneState.ts` |
| DTO→Cytoscape adapter | `toCytoscapeElements()` conversion of `VisualizationDTO` into element definitions | `frontend/src/lib/visualizationAdapter.ts` |
| Cytoscape reconciler | Topology-aware imperative scene diffs (add incoming nodes, reparent shared nodes, rewire shared edges, remove stale, patch data, restore classes/selection/positions) inside `cy.batch()` | `frontend/src/components/graph/cytoscapeReconciler.ts` |
| Graph canvas | Cytoscape lifecycle, interaction wiring, controlled/uncontrolled mode seam; freezes declarative props after mount and delegates diffs to the reconciler | `frontend/src/components/graph/GraphCanvas.tsx` |
| FastAPI assembly | Lifespan-owned database driver, CORS, handlers, router registration, `/api/static` mount | `spoilerless/app/main.py` |
| HTTP boundary | Path/body/query validation, auth dependencies, response contracts | `spoilerless/app/api/` |
| Repository error handlers | Central `install_repository_error_handlers()` registration for repository-layer failures | `spoilerless/app/api/exceptions.py`, `spoilerless/app/main.py` |
| Domain contracts | Strict Pydantic request/response models and typed ChangeSet union | `spoilerless/app/domain/` |
| Visualization DTO contracts | Versioned `VisualizationDTO` (metadata/nodes/edges/groups/timeline/focus), six-view `VIEW_TYPES` vocabulary, `EXPANSION_KEYS` allowlist, reference-closure validation | `spoilerless/app/domain/visualization.py` |
| Business orchestration | Graph, auth, progress, chat, ChangeSet, series, and settings workflows | `spoilerless/app/services/` |
| Visualization projection service | Boundary-checked, read-only projections and expansion deltas over complete safe `GraphResponse` + safe editorial event context | `spoilerless/app/services/visualization.py` |
| Persistence boundary | Neo4j-backed users, sessions, content, progress, chat, settings, ChangeSets | `spoilerless/app/repository/` |
| Graph query modules | Feature-specific parameterized Cypher and database lifecycle | `spoilerless/app/graph/` |
| Spoiler-safe graph reads | Central graph-response Cypher with per-hop visibility predicates, plus the effective-boundary and derived-visibility rules | `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py`, `spoilerless/app/spoiler/visibility.py` |
| GraphRAG retrieval | Twelve typed tools in one `TOOL_SPECS` registry, shared context sections, citation validation | `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/tools.py`, `spoilerless/app/retrieval/context.py` |
| LLM adapter | Gemini and OpenAI-compatible streaming providers and system prompts | `spoilerless/app/llm/provider.py`, `spoilerless/app/llm/system_prompt.py` |
| Revision log | Same-transaction append-only audit helpers | `spoilerless/app/revisions/__init__.py` |
| Share-link access | Token-based read-only share views; hash-stored share tokens | `spoilerless/app/api/share.py`, `spoilerless/app/repository/share.py` |
| Redis integration | Redis-backed rate limiting and cache-aside graph/visualization responses | `spoilerless/app/services/rate_limit.py`, `spoilerless/app/cache/` |
| Graph bootstrap | Ontology validation, constraints/indexes, seed, visibility audit | `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/seed.py` |
| Static content | Self-hosted character portrait assets mounted at `/api/static` | `spoilerless/app/main.py`, `spoilerless/app/static/characters/` |

## Pattern Overview

**Overall:** Layered SPA + service/repository backend over a graph database, with a bounded tool-calling GraphRAG subsystem and a bounded presentation-projection layer over the safe graph read.

**Key Characteristics:**
- Use the normal backend dependency direction `api → services → repository → graph/database`; shared Pydantic contracts in `spoilerless/app/domain/` may be imported by all layers.
- Keep request values parameterized in Cypher. Dynamic labels or relationship types must come from server-side ontology allowlists (`spoilerless/app/graph/ontology.py`, `spoilerless/app/retrieval/tools.py`).
- Enforce spoiler visibility during Neo4j access, never by filtering an already-returned result in React or Python (`spoilerless/app/spoiler/filter.py`, `spoilerless/app/graph/chat.py`, `spoilerless/app/retrieval/tools.py`).
- Keep frontend wire models aligned with backend domain models (`frontend/src/types/`, `spoilerless/app/domain/`).
- Candidate review is the deliberate layering exception: routes call `CandidateRepository` directly and own transaction orchestration (`spoilerless/app/api/candidates.py`, `spoilerless/app/graph/candidates.py`).
- Freeze react-cytoscapejs's declarative `elements`/`layout` props after mount in `frontend/src/components/graph/GraphCanvas.tsx` and drive scene updates through the imperative reconciler (`frontend/src/components/graph/cytoscapeReconciler.ts`); layouts run through guarded imperative effects (D-22/D-24).
- Serve visualization projections from complete safe graph detail only — boundary-before-projection in `spoilerless/app/services/visualization.py`, never from hidden rows (D-05); expansion deltas are uncached (T10-CACHE-06).

## Layers

**Frontend Presentation:**
- Purpose: Render authentication, graph exploration, detail/editing, revision, chat, and settings experiences.
- Location: `frontend/src/components/`
- Contains: Feature folders plus reusable shadcn/Radix primitives in `frontend/src/components/ui/`. The graph workspace adds `AnswerGraph.tsx`, `GraphFocusIndicator.tsx`, and the reconciler (`cytoscapeReconciler.ts` + headless `cytoscapeReconciler.test.ts`).
- Depends on: Hooks and shared types from `frontend/src/hooks/` and `frontend/src/types/`; projection scenes convert through `frontend/src/lib/visualizationAdapter.ts` and reconcile through `frontend/src/components/graph/cytoscapeReconciler.ts`.
- Used by: `frontend/src/App.tsx`.

**Frontend State and API:**
- Purpose: Hold browser state and convert typed actions into backend requests.
- Location: `frontend/src/hooks/`, `frontend/src/api/`, `frontend/src/providers/`
- Contains: Fetch state machines, Google-session context, JSON transport, manual SSE stream parsing, and the serializable scene-state reducer (`frontend/src/hooks/useSceneState.ts`).
- Depends on: Browser Fetch API and contracts in `frontend/src/types/`.
- Used by: `frontend/src/App.tsx` and feature components.

**API Layer:**
- Purpose: Expose the 52-operation HTTP contract and translate domain/repository failures into stable envelopes.
- Location: `spoilerless/app/api/`
- Contains: `APIRouter` modules for auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, settings, and share; the graph router also carries the Phase-10 projection routes (`GET .../graph/visualization`, `GET .../graph/expand`) and `exceptions.py` installs repository error handlers.
- Depends on: `spoilerless/app/api/deps.py`, domain models, and service factories.
- Used by: `spoilerless/app/main.py`.

**Domain Layer:**
- Purpose: Define validated transport and business shapes.
- Location: `spoilerless/app/domain/`
- Contains: Pydantic models, enums, discriminated ChangeSet operations, response envelopes, and the library-neutral visualization DTOs (`visualization.py`).
- Depends on: Pydantic and standard-library types.
- Used by: API, services, repositories, retrieval, and tests.

**Service Layer:**
- Purpose: Orchestrate multi-step business workflows without embedding HTTP concerns.
- Location: `spoilerless/app/services/`
- Contains: `GraphService`, `SeriesService`, `AuthService`, `ProgressService`, `ChatService`, `ChangeSetService`, `SettingsService`, the Redis-backed rate limiter (`rate_limit.py`), and `VisualizationService` (`visualization.py`, 1,173 lines) which projects safe graph detail into DTOs and expansion deltas. `AuthService` requires injected user/session repositories and a verifier — no silent fallback (PROB-09/#77).
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
- Contains: `Neo4jDatabase`, feature query modules, seed/setup, ontology validation, label inventories (`labels.py`), and spoiler-safe graph queries. `spoilerless/app/spoiler/policy.py` exposes the effective-boundary helpers (`is_visible`, `resolve_effective_boundary`) reused by the visualization service.
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

### Visualization Projection Path (Phase 10)

1. `AuthenticatedApp` maps the active narrative tab/mode to a view type; in Overview mode no projection is fetched and the legacy scene renders (`frontend/src/App.tsx`).
2. `fetchVisualization()` calls `GET /api/series/{series_id}/graph/visualization?view=<view>&episode_order=N`; `fetchExpansion()` calls `GET /api/series/{series_id}/graph/expand?node_id=&expansion_key=&limit=` for user-triggered semantic expansions (`frontend/src/api/graph.ts`).
3. The route resolves the effective boundary and view; the visualization cache is consulted with a key over (series, effective order, user scope, view, projection version, focus signature) before `VisualizationService` runs (`spoilerless/app/api/graph.py`, `spoilerless/app/cache/graph_cache.py`).
4. `VisualizationService` consumes only complete safe `GraphResponse` rows plus safe editorial event context; it refuses effective orders above the served boundary and rejects hidden rows rather than silently dropping them (D-05) (`spoilerless/app/services/visualization.py`).
5. The produced `VisualizationDTO` carries `projection_version` + `effective_view_order`; edges use human semantic classes, focus may only reference nodes present in the DTO, and reference closure is validated (T10-CACHE-02/T10-FOCUS-02) (`spoilerless/app/domain/visualization.py`).
6. Expansion deltas merge client-side into the base scene and are never cached server-side (T10-CACHE-06).
7. `toCytoscapeElements()` converts the DTO to element definitions; `GraphCanvas`'s `visualization` prop renders them through the stable Cytoscape lifecycle (`frontend/src/lib/visualizationAdapter.ts`, `frontend/src/components/graph/GraphCanvas.tsx`).

### Cytoscape Scene Reconciliation (frontend)

1. `GraphCanvas` snapshots the first `elements`/`layout` values into refs and stops passing changing declarative props to `CytoscapeComponent`, so react-cytoscapejs never runs its id-only patcher or an uncontrolled global relayout (`frontend/src/components/graph/GraphCanvas.tsx`).
2. A guarded effect calls `reconcileCytoscapeElements(cy, elements)` on every scene change, all inside `cy.batch()`: add incoming nodes, reparent shared nodes (`node.move`), rewire shared edges (`edge.move`), remove stale edges then stale nodes, add incoming edges, patch non-topology data keys, and restore classes/selection/positions (`frontend/src/components/graph/cytoscapeReconciler.ts`).
3. Compound→flat switches (legacy curated graph ↔ projection scenes) preserve shared element identity instead of cascade-deleting through obsolete parents — the failure mode of react-cytoscapejs's remove-first plan.
4. Layouts run through guarded imperative effects (`runLayout`) with fcose as the primary layout and dagre for the Evidence/investigation view (`frontend/src/components/graph/layoutConfig.ts`).
5. Unit-test adapters that expose only a partial `cy` surface skip the reconciler and fall back to declarative updates (`useImperativeReconcileRef` gate in `frontend/src/components/graph/GraphCanvas.tsx`).

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
- The graph scene itself is a serializable reducer: `frontend/src/hooks/useSceneState.ts` owns view, filters, selection, focus, camera, positions, expansions, timeline, and Inspector state; camera/positions/expansions dispatches never trigger fetches or relayouts (D-24/D-25).
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

**VisualizationDTO / Projection:**
- Purpose: Versioned, library-neutral presentation contract decoupled from both Neo4j and Cytoscape; safe by construction.
- Examples: `spoilerless/app/domain/visualization.py`, `spoilerless/app/services/visualization.py`, `frontend/src/types/graph.ts`.
- Pattern: `metadata`/`nodes`/`edges`/`groups`/`timeline`/`focus` shape; edges carry semantic classes (never raw relation names); reference closure enforced at validation; `projection_version` + `effective_view_order` ride every DTO.

**Cytoscape Reconciler:**
- Purpose: Apply complete scene diffs imperatively while preserving element identity and runtime state.
- Examples: `frontend/src/components/graph/cytoscapeReconciler.ts` (tested headless in `cytoscapeReconciler.test.ts`).
- Pattern: Single `reconcileCytoscapeElements(cy, nextDefinitions)` inside `cy.batch()`; topology keys (`id`/`source`/`target`/`parent`) drive add/reparent/rewire/remove ordering; non-topology data is patched with removal of stale keys.

**Scene State Reducer:**
- Purpose: Own all serializable graph-workspace state so React (not Cytoscape) is the scene authority.
- Examples: `frontend/src/hooks/useSceneState.ts`.
- Pattern: JSON-safe state object; focus ids mirror the server charset so unsafe candidates are refused before entering scene state (T10-FOCUS-04).

## Entry Points

**Backend application:**
- Location: `spoilerless/app/main.py`
- Triggers: `uv run uvicorn spoilerless.app.main:app --reload`.
- Responsibilities: Build FastAPI, register routers/middleware/handlers, own Neo4j and Redis lifecycle, install security/logging middleware, expose health, mount `/api/static`, install database/LLM/repository error handlers.

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
- **Graph rendering:** react-cytoscapejs's declarative `elements`/`layout` props are frozen after mount; every scene update flows through `reconcileCytoscapeElements()` and layouts run through guarded imperative effects (`frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/cytoscapeReconciler.ts`, `frontend/src/components/graph/layoutConfig.ts`).
- **Projection safety:** Projections consume only complete safe graph detail; boundary-before-projection refuses effective orders above the served boundary and rejects (never silently drops) hidden rows; raw Neo4j relation names never appear in DTOs; focus ids must reference nodes present in the DTO; expansion deltas are never cached (`spoilerless/app/services/visualization.py`, `spoilerless/app/domain/visualization.py`, `spoilerless/app/cache/graph_cache.py`).
- **Static content:** Character portraits are self-hosted (`spoilerless/app/static/characters/`, served at `/api/static`); `image_url` seed values are relative and pass the CSP `img-src 'self'` rule — no external image CDNs (PROBLEMS #28).

## Anti-Patterns

### Application-side spoiler filtering

**What happens:** A consumer fetches broad data and hides future items in Python, React, or prompt instructions.
**Why it's wrong:** The browser or LLM already receives the spoiler before presentation filtering.
**Do this instead:** Put every visibility predicate on every relevant query hop in `spoilerless/app/spoiler/filter.py`, `spoilerless/app/retrieval/tools.py`, or the owning data-access query module; projections must consume only already-safe rows (`spoilerless/app/services/visualization.py`).

### Arbitrary LLM query or write access

**What happens:** Model text becomes Cypher or a direct graph mutation.
**Why it's wrong:** It bypasses server authority, ontology validation, spoiler boundaries, user confirmation, and revision logging.
**Do this instead:** Add typed retrieval tools in `spoilerless/app/retrieval/` or typed ChangeSet operations in `spoilerless/app/domain/change_set.py` and preserve the service/repository validation flow.

### Runtime logic in package initializers

**What happens:** Feature implementations accumulate in `__init__.py`, as the revision repository does in `spoilerless/app/revisions/__init__.py`.
**Why it's wrong:** It obscures module boundaries and makes imports less discoverable, even when no I/O runs.
**Do this instead:** Put new implementations in named modules and keep package initializers empty, declarative, or limited to explicit re-exports (`spoilerless/app/services/`, `spoilerless/app/repository/`).

### Letting the rendering library own scene diffs

**What happens:** Declarative element props are passed to react-cytoscapejs on every scene change; its id-only patcher removes obsolete compound parents before detaching shared children.
**Why it's wrong:** Compound→flat scene switches (legacy curated graph ↔ projection scenes) cascade-delete shared nodes and then throw while adding edges that reference the deleted ids.
**Do this instead:** Freeze the declarative props at mount and apply all diffs through the topology-aware `reconcileCytoscapeElements()` in `frontend/src/components/graph/cytoscapeReconciler.ts`, covered by headless tests in `frontend/src/components/graph/cytoscapeReconciler.test.ts`.

## Error Handling

**Strategy:** Validate at Pydantic/FastAPI boundaries, use feature exceptions inside services/repositories, and translate them to generic structured HTTP errors.

**Patterns:**
- Use `{ "detail": { "code": "...", "message": "..." } }` via `spoilerless/app/core/errors.py`; `frontend/src/api/client.ts` normalizes this and FastAPI validation arrays.
- Install database, LLM, and repository exception handlers centrally in `spoilerless/app/main.py` (`install_database_error_handlers`, `install_llm_error_handlers`, `install_repository_error_handlers` from `spoilerless/app/api/exceptions.py`).
- `ServiceUnavailable`/`AuthError`/`Neo4jError` map to 503 `DATABASE_UNAVAILABLE`; `ConstraintError` maps to 409 `CONSTRAINT_VIOLATION`; rate-limit rejection maps to 429 `TOO_MANY_REQUESTS` (`spoilerless/app/core/errors.py`).
- `ClientError` (invalid Cypher) is deliberately excluded from the 503 mapping — masking it would hide app bugs — so it surfaces as a plain 500 (`spoilerless/app/core/errors.py`).
- Make hidden, foreign, and missing user-scoped resources indistinguishable where disclosure would leak ownership or future content (`spoilerless/app/repository/chat.py`, `spoilerless/app/api/chat.py`).
- Emit structured terminal SSE error events after headers have been sent (`spoilerless/app/api/chat.py`, `frontend/src/api/chat.ts`).

## Cross-Cutting Concerns

**Logging:** No centralized application logging layer is present; avoid printing secrets or query internals. The setup CLI prints only aggregate counts (`spoilerless/app/graph/setup.py`).
**Validation:** Pydantic models validate HTTP and LLM-tool inputs; ontology and seed validators gate graph types/content; visualization DTO validation enforces reference closure (`spoilerless/app/domain/`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/graph/ontology.py`, `spoilerless/app/graph/seed.py`, `spoilerless/app/domain/visualization.py`).
**Authentication:** Google ID tokens create hashed-token HttpOnly sessions; only the token hash is persisted in Neo4j (`spoilerless/app/services/auth.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/api/deps.py`).
**Secrets:** LLM API keys are write-only in the API contract and masked on reads; provider construction reads the full stored value only server-side (`spoilerless/app/services/settings.py`, `spoilerless/app/services/chat.py`).
**Provenance:** Canonical/candidate claims require source/evidence links; retrieval citations are checked against the current turn's retrieved IDs; projection DTOs carry `projection_version` + `effective_view_order` so a cached DTO can never cross a boundary (`spoilerless/app/graph/seed.py`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/domain/visualization.py`).

---

*Architecture analysis: 2026-08-14*
