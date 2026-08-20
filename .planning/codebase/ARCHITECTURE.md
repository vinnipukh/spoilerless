<!-- refreshed: 2026-08-20 -->
---
last_mapped: 2026-08-20
focus: arch
last_mapped_commit: 6256214f672d21e0c264a4910033fe02dc51da80
---

# Architecture

**Analysis Date:** 2026-08-20

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
│ FastAPI (`spoilerless/app/main.py`, 363 lines, `spoilerless/app/api/`)       │
│ BodySizeLimitMiddleware (413) → TrustedHostMiddleware → CORSMiddleware         │
│ routes → shared boundary resolver → domain validation → services → repos     │
│ Phase 11: fail-closed boundary + body/host/LLM-cost/cache-cardinality gates │
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                │                       │                                       
                ▼                       ▼                                       
┌──────────────────────────────────┐  ┌───────────────────────────────────────┐ 
│ Neo4j (`spoilerless/app/graph/`) │  │ Optional LLM (`spoilerless/app/llm/`)  │
│ data, users, state, settings    │  │ allowlisted GraphRAG tools only   │      
└──────────────────────────────────┘  └───────────────────────────────────────┘ 
```

The product is a three-part web application: a state-driven React SPA, an asynchronous FastAPI process, and Neo4j. The frontend and optional LLM receive only graph data that Cypher has already bounded by watch progress. Source-backed `Claim` nodes are projected into frontend graph edges by `GraphService`; structural relationships remain direct Neo4j relationships (`spoilerless/app/services/graph.py`, `spoilerless/app/spoiler/filter.py`).

The live API surface still contains 52 HTTP operations on 39 unique path templates. Eleven routers are assembled in `spoilerless/app/main.py`; `/health` (GET and HEAD) is defined on the application itself. In `development` the interactive docs remain at `/docs`/`/redoc`/`/openapi.json`; when `ENVIRONMENT=production` those three are disabled at construction time via `_docs_kwargs` (`spoilerless/app/main.py`).

Since the 2026-08-14 map (commit `5bd1641`), Phase 11 factored and hardened the spoilage/operational perimeter without adding new path templates:

- `spoilerless/app/api/boundary.py:resolve_effective_boundary()` (66 lines, D-01) is now the single fail-closed boundary resolver for every spoiler-sensitive read — anonymous readers fixed at order 1, authenticated readers without persisted progress fail closed to 1 (SEC-BE-001), others clamped via `spoilerless/app/spoiler/policy.py:effective_view_order`. `spoilerless/app/api/graph.py` now delegates graph GET there and keeps the `_resolve_effective_boundary = resolve_effective_boundary` alias so visualization/expand/path/export call sites are untouched (their inline 69-line resolver was deleted).
- `spoilerless/app/main.py` now fronts the ASGI stack with `BodySizeLimitMiddleware` (D-08, 413 `payload_too_large`) and `TrustedHostMiddleware` (allowlist from `ALLOWED_HOSTS` or `FRONTEND_ORIGINS` hosts), disables docs in production, and calls `warn_if_open_signup()` inside `lifespan`.
- `spoilerless/app/cache/graph_cache.py` now bounds visualization cache cardinality via `_focus_capacity_allows()` (FOCUS_SET_CAP=64, 3600s TTL, D-12) fronting `set_cached_visualization`.
- `spoilerless/app/retrieval/pipeline.py` now neutralizes exact context-delimiter tags in model answers (`_neutralize_answer_delimiters` over `CONTEXT_SECTIONS`), caps `ProposeChangesetInput.operations` at 20, caps `llm_max_tool_calls_per_round` (default 8), and thin-delegates `propose_changeset` to `ChangeSetService.propose_via_tool` (QUAL-02).
- `spoilerless/app/services/chat.py` adds a process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` (default 4, D-07) alongside the per-user slot.
- `spoilerless/app/services/rate_limit.py` becomes fail-closed in production (`rate_limit_fail_open is False` + `environment == "production"` surfaces 503 on Redis outage, SEC-DOS-001).
- `spoilerless/app/core/config.py` (209 lines) adds `environment`, `rate_limit_fail_open`, `allowed_hosts`, `max_body_size_bytes`, `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round` and local-defaults the Neo4j connection fields for one-command dev startup.
- On the frontend, `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines) + its `cytoscapeReconciler.test.ts` (91 lines) are now fully tracked; `GraphCanvas` stabilizes its imperative seam (`initialElementsRef`/`initialLayoutRef`, `useImperativeReconcileRef`, controlled/uncontrolled `mode`/`onModeChange`), and `frontend/vercel.json` carries a full security-header block (CSP, HSTS, nosniff, DENY, referrer-policy).

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| React composition root | Auth gate, series/progress selection, graph/detail/chat/settings state; four-tab narrative workspace in Full mode; now threads controlled graph mode | `frontend/src/App.tsx` |
| Typed frontend transport | Cookie-bearing JSON fetch and POST-based SSE parsing; `VITE_API_BASE_URL` prefix + `apiUrl()` image prefixing | `frontend/src/api/client.ts`, `frontend/src/api/chat.ts` |
| Frontend feature state | Async state machines for graph, progress, notes, revisions, chat | `frontend/src/hooks/` |
| Frontend scene state | Serializable scene-state reducer: active view, filters, selection, focus, camera, positions, expansions, timeline, Inspector (D-24: React owns scene) | `frontend/src/hooks/useSceneState.ts` |
| DTO→Cytoscape adapter | `toCytoscapeElements()` conversion of `VisualizationDTO` | `frontend/src/lib/visualizationAdapter.ts` |
| Cytoscape reconciler | Topology-aware imperative diffs inside `cy.batch()` (add incoming nodes, reparent shared nodes, rewire shared edges, remove stale, patch data, restore classes/selection/positions) | `frontend/src/components/graph/cytoscapeReconciler.ts` |
| Graph canvas | Cytoscape lifecycle, interaction wiring, controlled/uncontrolled mode seam; freezes declarative props after mount and delegates diffs to reconciler; now exposes `mode`/`onModeChange` and `useImperativeReconcileRef` guard | `frontend/src/components/graph/GraphCanvas.tsx` |
| FastAPI assembly | Lifespan-owned database, CORS, host/body middleware, handlers, routers, `/api/static` mount, docs gating | `spoilerless/app/main.py` |
| Host/body middleware | Pure-ASGI `BodySizeLimitMiddleware` (413) and `TrustedHostMiddleware` via `_trusted_hosts()` | `spoilerless/app/main.py:BodySizeLimitMiddleware`, `spoilerless/app/main.py:_trusted_hosts` |
| Shared boundary resolver | Single fail-closed `resolve_effective_boundary()` for every spoiler-sensitive read (D-01, SEC-BE-001) | `spoilerless/app/api/boundary.py` |
| HTTP boundary | Path/body/query validation, auth dependencies, response contracts; graph routes now delegate boundary to shared resolver | `spoilerless/app/api/` (esp. `spoilerless/app/api/graph.py:116-123`) |
| Repository error handlers | Central `install_repository_error_handlers()` registration | `spoilerless/app/api/exceptions.py`, `spoilerless/app/main.py` |
| Domain contracts | Strict Pydantic request/response models, typed ChangeSet union, hardened changeset cap | `spoilerless/app/domain/` (esp. `spoilerless/app/domain/change_set.py` capped at 20, `spoilerless/app/domain/extraction.py`) |
| Visualization DTO contracts | Versioned `VisualizationDTO`, six-view `VIEW_TYPES`, `EXPANSION_KEYS` allowlist, reference-closure validation | `spoilerless/app/domain/visualization.py` |
| Business orchestration | Graph, auth, progress, chat (now with process-wide semaphore), ChangeSet, series, settings workflows | `spoilerless/app/services/` |
| Visualization projection service | Boundary-checked, read-only projections and expansion deltas over complete safe `GraphResponse` + editorial event context | `spoilerless/app/services/visualization.py` |
| Persistence boundary | Neo4j-backed users, sessions, content, progress, chat, settings, ChangeSets, share tokens | `spoilerless/app/repository/` |
| Graph query modules | Feature-specific parameterized Cypher and database lifecycle | `spoilerless/app/graph/` |
| Spoiler-safe graph reads | Central graph-response Cypher with per-hop visibility, effective-boundary and derived-visibility rules | `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py`, `spoilerless/app/spoiler/visibility.py` |
| GraphRAG retrieval | Twelve typed tools in one `TOOL_SPECS` registry, shared context sections, citation + delimiter validation | `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/tools.py`, `spoilerless/app/retrieval/context.py` |
| LLM adapter | Gemini and OpenAI-compatible streaming providers and system prompts | `spoilerless/app/llm/provider.py`, `spoilerless/app/llm/system_prompt.py` |
| Revision log | Same-transaction append-only audit helpers; expanded wiring in 11-04 | `spoilerless/app/revisions/__init__.py` |
| Share-link access | Token-based read-only share views; hash-stored share tokens | `spoilerless/app/api/share.py`, `spoilerless/app/repository/share.py` |
| Redis integration | Redis-backed rate limiting (now fail-closed in prod) and cache-aside graph/visualization with focus-set cap | `spoilerless/app/services/rate_limit.py`, `spoilerless/app/cache/` (esp. `spoilerless/app/cache/graph_cache.py:_focus_capacity_allows`) |
| Graph bootstrap | Ontology validation, constraints/indexes, seed, visibility audit | `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/seed.py` |
| Static content | Self-hosted character portrait assets mounted at `/api/static` | `spoilerless/app/main.py`, `spoilerless/app/static/characters/` |

## Pattern Overview

**Overall:** Layered SPA + service/repository backend over a graph database, with a bounded tool-calling GraphRAG subsystem and a bounded presentation-projection layer over the safe graph read; Phase 11 adds a shared fail-closed boundary resolver and ASGI-level operational gates.

**Key Characteristics:**
- Use the normal dependency direction `api → services → repository → graph/database` with one exception: candidate review routes call `CandidateRepository` directly (`spoilerless/app/api/candidates.py` now passes through the shared boundary resolver but still owns its transaction orchestration).
- Every spoiler-sensitive route now resolves its effective boundary through `spoilerless/app/api/boundary.py:resolve_effective_boundary()` — anonymous fixed at 1, no-progress fail-closed to 1, persisted progress clamped via `effective_view_order`; every return is validated to a persisted episode or else 422.
- Keep request values parameterized in Cypher. Dynamic labels/relationship types must come from server-side ontology allowlists (`spoilerless/app/graph/ontology.py`, `spoilerless/app/retrieval/tools.py`).
- Enforce spoiler visibility during Neo4j access, never by filtering an already-returned result in React or Python (`spoilerless/app/spoiler/filter.py` and every call site of `resolve_effective_boundary`). Projections consume only already-safe rows.
- ASGI operational gates run before any route handler: `BodySizeLimitMiddleware` (header pre-check + streaming count, 413) and `TrustedHostMiddleware` (allowlist from `allowed_hosts` or `FRONTEND_ORIGINS`).
- LLM cost gates are server-owned: process-wide semaphore (`llm_max_concurrent_generations`, `spoilerless/app/services/chat.py`), per-round tool-call cap (`llm_max_tool_calls_per_round`, `spoilerless/app/retrieval/pipeline.py`), and per-turn changeset operation cap (20, same file).
- Content framing is server-owned: `spoilerless/app/retrieval/context.py:CONTEXT_SECTIONS` defines the 9-section order; `spoilerless/app/retrieval/pipeline.py:_neutralize_answer_delimiters` escapes exact delimiter tags in model answers so a forged `</sources>` cannot break context parsing.
- Keep frontend wire models aligned with backend domain models (`frontend/src/types/`, `spoilerless/app/domain/`).
- Freeze react-cytoscapejs's declarative `elements`/`layout` props after mount in `frontend/src/components/graph/GraphCanvas.tsx` and drive scene updates through the imperative reconciler (`frontend/src/components/graph/cytoscapeReconciler.ts`); layouts run through guarded imperative effects (D-22/D-24). The reconciler is now fully tracked with 91-line headless tests.
- Cache visualization projections with boundary/version/focus-aware keys; bound per-series focus-signature cardinality (FOCUS_SET_CAP=64) before storing — when the cap is hit compute-fresh but never store (`spoilerless/app/cache/graph_cache.py`). Expansion deltas remain uncached (T10-CACHE-06).

## Layers

**Frontend Presentation:**
- Purpose: Render authentication, graph exploration, detail/editing, revision, chat, and settings experiences.
- Location: `frontend/src/components/`
- Contains: Feature folders plus reusable shadcn/Radix primitives in `frontend/src/components/ui/`. Graph workspace adds `AnswerGraph.tsx`, `GraphFocusIndicator.tsx`, and the reconciler (`cytoscapeReconciler.ts` + `cytoscapeReconciler.test.ts`), plus controlled-mode aware `GraphCanvas.tsx`.
- Depends on: Hooks and types from `frontend/src/hooks/` and `frontend/src/types/`; projection scenes convert through `frontend/src/lib/visualizationAdapter.ts` and reconcile through `frontend/src/components/graph/cytoscapeReconciler.ts`.
- Used by: `frontend/src/App.tsx`.

**Frontend State and API:**
- Purpose: Hold browser state and convert typed actions into backend requests.
- Location: `frontend/src/hooks/`, `frontend/src/api/`, `frontend/src/providers/`
- Contains: Fetch state machines, Google-session context, JSON transport, manual SSE stream parsing, and the serializable scene-state reducer (`frontend/src/hooks/useSceneState.ts`). `GraphCanvas` now accepts `mode`/`onModeChange` so the SPA's workspace mode stays in lockstep with the canvas.
- Depends on: Browser Fetch API and contracts in `frontend/src/types/`.
- Used by: `frontend/src/App.tsx` and feature components.

**API Layer:**
- Purpose: Expose the 52-operation HTTP contract and translate domain/repository failures into stable envelopes; operational gates and spoiler-boundary centralization live here.
- Location: `spoilerless/app/api/` plus `spoilerless/app/main.py` middleware
- Contains: Eleven routers (auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, settings, share) plus the shared boundary resolver (`boundary.py`); `spoilerless/app/main.py` contributes `BodySizeLimitMiddleware`, `TrustedHostMiddleware`, CORS, and docs gating; `exceptions.py` installs repository error handlers.
- Depends on: `spoilerless/app/api/deps.py`, domain models, and service factories. Every spoiler-sensitive handler now depends on `spoilerless/app/api/boundary.py`.
- Used by: `spoilerless/app/main.py`.

**Domain Layer:**
- Purpose: Define validated transport and business shapes.
- Location: `spoilerless/app/domain/`
- Contains: Pydantic models and enums for auth, graph, series, user content, extraction, revisions, progress, chat, ChangeSets (now `operations: max_length=20`), settings (now validates base URL host/scheme), and the library-neutral visualization DTOs.
- Depends on: Pydantic and standard-library types.
- Used by: API, services, repositories, retrieval, and tests.

**Service Layer:**
- Purpose: Orchestrate multi-step business workflows without embedding HTTP concerns.
- Location: `spoilerless/app/services/`
- Contains: `GraphService`, `SeriesService`, `AuthService`, `ProgressService`, `ChatService` (now with process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` + `warn_if_open_signup`), `ChangeSetService` (now with `propose_via_tool` extraction for thin pipeline delegation), `SettingsService`, the Redis-backed rate limiter (`rate_limit.py`, now fail-closed in prod), and `VisualizationService` (still 1,173-line boundary-checked projections). `AuthService` still requires injected user/session repositories and a verifier — no silent fallback.
- Depends on: Domain models and repository/database abstractions.
- Used by: API dependencies in `spoilerless/app/api/`.

**Repository Layer:**
- Purpose: Own persistence commands, record normalization, ownership scoping, and managed transactions.
- Location: `spoilerless/app/repository/`
- Contains: Neo4j repositories for users, sessions, user content, progress, chat, settings, ChangeSet, and share tokens. Candidates repository (`spoilerless/app/graph/candidates.py`, 99-line Phase-11 hardening) is the candidate-review direct-use exception.
- Depends on: Query constants in `spoilerless/app/graph/`, `Neo4jDatabase`, and domain models.
- Used by: Services; candidate routes remain the direct-use exception but now pass through the shared boundary resolver first.

**Graph and Spoiler Layer:**
- Purpose: Own connection lifecycle, parameterized Cypher, ontology loading, and bootstrap operations.
- Location: `spoilerless/app/graph/`, `spoilerless/app/spoiler/`
- Contains: `Neo4jDatabase`, feature query modules, seed/setup, ontology validation, label inventories, and spoiler-safe graph queries. `spoilerless/app/spoiler/policy.py` exposes `is_visible`, `resolve_effective_boundary`, `effective_view_order` reused by both the new `spoilerless/app/api/boundary.py` resolver and `VisualizationService`.
- Depends on: Neo4j async driver, YAML/JSON content under `ontology/` and `data/dexter/`.
- Used by: Repositories, services, and the setup CLI.

**Retrieval and LLM Layer:**
- Purpose: Answer questions from bounded graph context without exposing arbitrary Cypher or direct writes.
- Location: `spoilerless/app/retrieval/`, `spoilerless/app/llm/`
- Contains: Twelve allowlisted retrieval tools in one `TOOL_SPECS` registry, tool schemas, the 9-section shared `CONTEXT_SECTIONS` registry (`spoilerless/app/retrieval/context.py`), `_neutralize_answer_delimiters()` and per-round/operation caps, citation validation, provider adapters, and prompt text. `propose_changeset` is now a thin delegation to the service.
- Depends on: Persisted progress (via `resolve_effective_boundary`'s call chain), Neo4j reads, stored/environment settings, and an external compatible LLM endpoint. The configured `llm_max_tool_calls_per_round` and `llm_max_concurrent_generations` are read once per turn/process startup from `spoilerless/app/core/config.py`.
- Used by: `ChatService` in `spoilerless/app/services/chat.py`.

## Data Flow

### Primary Graph Request Path

1. `AuthenticatedApp` passes the selected series and confirmed watch order to `useGraph()`, whose shared `useFetchState` machine keys on series plus visible order (`frontend/src/App.tsx`, `frontend/src/hooks/useGraph.ts`, `frontend/src/hooks/useFetchState.ts`).
2. `getGraph()` uses the shared cookie-bearing client to call `GET /api/series/{series_id}/graph?visible_until_order=N` (`frontend/src/api/graph.ts`, `frontend/src/api/client.ts`).
3. The request first passes `TrustedHostMiddleware` (Host allowlist) and `BodySizeLimitMiddleware` (413 if over `max_body_size_bytes`) in `spoilerless/app/main.py`.
4. The route verifies the series and calls the shared `resolve_effective_boundary(service, progress_service, series_id, user, visible_until_order)` — anonymous → 1, no-progress authenticated → 1, otherwise `min(requested, view_as_of, watched_through)` validated to a persisted episode or 422 (`spoilerless/app/api/boundary.py`, `spoilerless/app/api/graph.py:116-123`).
5. The cache-aside layer (`spoilerless/app/cache/graph_cache.py`) is checked with a key over the effective boundary + user scope before `GraphService.fetch_graph()` runs.
6. `GraphService` runs seven independent reads concurrently: series, nodes, structural edges, canonical/candidate claims, user relationships, sources, and evidence (`spoilerless/app/services/graph.py:51`).
7. Every story-sensitive query applies visibility predicates in Cypher, including each endpoint/provenance hop (`spoilerless/app/spoiler/filter.py`).
8. Visible claims become `GraphEdge` records with IDs of the form `{claim.id}:edge`; structural and user edges join the same response collection (`spoilerless/app/services/graph.py`).
9. `GraphCanvas` converts the trusted response into Cytoscape elements without applying a second spoiler filter (`frontend/src/components/graph/graphElements.ts`, `frontend/src/components/graph/GraphCanvas.tsx`).

### Visualization Projection Path (Phase 10, hardened in Phase 11)

1. `AuthenticatedApp` maps the active narrative tab/mode to a view type; in Overview mode no projection is fetched and the legacy scene renders (`frontend/src/App.tsx`).
2. `fetchVisualization()` calls `GET /api/series/{series_id}/graph/visualization?view=<view>&episode_order=N`; `fetchExpansion()` calls `GET /api/series/{series_id}/graph/expand?node_id=&expansion_key=&limit=` (`frontend/src/api/graph.ts`).
3. Each route resolves the effective boundary through `spoilerless/app/api/boundary.py` (same fail-closed rule as graph GET); the visualization cache is consulted with a key over (series, effective order, user scope, view, projection version, focus signature) before `VisualizationService` runs (`spoilerless/app/cache/graph_cache.py`). When `focus_ids` are present the set-cap guard `_focus_capacity_allows()` is checked — if the per-series set already holds 64 distinct signatures and this signature is new, the request is computed but never stored (bounded cardinality, D-12).
4. `VisualizationService` consumes only complete safe `GraphResponse` rows plus safe editorial event context; it refuses effective orders above the served boundary and rejects hidden rows rather than silently dropping them (D-05) (`spoilerless/app/services/visualization.py`).
5. The produced `VisualizationDTO` carries `projection_version` + `effective_view_order`; edges use human semantic classes, focus may only reference nodes present in the DTO, and reference closure is validated (`spoilerless/app/domain/visualization.py`).
6. Expansion deltas merge client-side into the base scene and are never cached server-side (T10-CACHE-06).
7. `toCytoscapeElements()` converts the DTO to element definitions; `GraphCanvas`'s `visualization` prop renders them through the stable Cytoscape lifecycle (`frontend/src/lib/visualizationAdapter.ts`, `frontend/src/components/graph/GraphCanvas.tsx`), now through the tracked reconciler.

### Cytoscape Scene Reconciliation (frontend, fully tracked)

1. `GraphCanvas` snapshots the first `elements`/`layout` values into `initialElementsRef`/`initialLayoutRef` and stops passing changing declarative props to `CytoscapeComponent`, so react-cytoscapejs never runs its id-only patcher or an uncontrolled global relayout (`frontend/src/components/graph/GraphCanvas.tsx`).
2. `useImperativeReconcileRef` gates the topology-aware path: real Cytoscape instances run `reconcileCytoscapeElements(cy, elements)` on every scene change, all inside `cy.batch()` — add incoming nodes, reparent shared nodes (`node.move`), rewire shared edges (`edge.move`), remove stale edges then stale nodes, add incoming edges, patch non-topology data keys, and restore classes/selection/positions (`frontend/src/components/graph/cytoscapeReconciler.ts`). Lightweight test adapters that expose only a partial `cy` surface retain declarative updates.
3. Compound→flat switches (legacy curated graph ↔ projection scenes) preserve shared element identity instead of cascade-deleting through obsolete parents — the failure mode of react-cytoscapejs's remove-first plan. Headless tests in `frontend/src/components/graph/cytoscapeReconciler.test.ts` cover identity, positions, selection, and compound→flat switches.
4. Layouts run through guarded imperative effects (`runLayout`) with fcose as primary and dagre for the investigation view (`frontend/src/components/graph/layoutConfig.ts`), now decoupled from declarative `layout` prop churn.
5. Controlled/uncontrolled mode seam: `GraphCanvas` accepts `mode`/`onModeChange`; `App.tsx` keeps workspace navigation in lockstep with the canvas mode via `handleModeChange` (`frontend/src/components/graph/GraphCanvas.tsx:mode` / `frontend/src/App.tsx`).

### Chat → Retrieval Tool → LLM Path (hardened)

1. `useChatMessages()` sends a POST and parses `text/event-stream` chunks from `/messages/stream` (`frontend/src/hooks/useChatMessages.ts`, `frontend/src/api/chat.ts`). Body is subject to the 413 gate.
2. The route checks `TrustedHostMiddleware`, verifies the authenticated `AppUser`, checks user-scoped session access, ensures progress (via the shared boundary resolver if a boundary is read), applies rate limiting (fail-closed 503 in production), and returns an SSE response (`spoilerless/app/api/chat.py`, `spoilerless/app/services/rate_limit.py`).
3. `ChatService.answer_stream()` acquires the process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` plus the per-user slot, resolves persisted watch progress, loads boundary-visible history, persists the user message with a boundary snapshot, and invokes `RetrievalPipeline` (`spoilerless/app/services/chat.py`).
4. `RetrievalPipeline` offers exactly twelve typed tool schemas from the single `TOOL_SPECS` registry to the configured provider (honoring per-request `X-LLM-*` BYOK headers) and rejects unknown or invalid tool calls; at most `llm_max_tool_calls_per_round` (default 8) are executed per round (`spoilerless/app/retrieval/pipeline.py`).
5. Tool execution injects `series_id`, `user_id`, and the server-resolved boundary; the model cannot supply those authority values or arbitrary Cypher (`spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/tools.py`). `propose_changeset` thin-delegates to `ChangeSetService.propose_via_tool()` which owns validation + persistence and caps operations at 20.
6. Retrieved rows are deduplicated and bounded, assembled into the 9-section context order defined by `spoilerless/app/retrieval/context.py:CONTEXT_SECTIONS`, then passed as delimited data to a final provider call with tools disabled (`spoilerless/app/retrieval/pipeline.py`).
7. Model answers are sanitized by `_neutralize_answer_delimiters()` — only the exact `<CONTEXT_SECTIONS>` / `</CONTEXT_SECTIONS>` shapes are escaped to `&lt;...&gt;`, so a forged `</sources>` cannot break section parsing while ordinary angle-bracket prose is preserved — then citation validation runs against this turn's retrieved ID set; invalid citations are stripped and ungrounded completion falls back safely (`spoilerless/app/retrieval/pipeline.py`).
8. `ChatService` persists the assistant `ChatMessage` and emits a final envelope containing citations and graph-focus IDs; the semaphore is released.

### Typed ChangeSet Mutation Path

1. A client proposes a Pydantic-discriminated operation list at `POST /api/series/{series_id}/change-sets` (`spoilerless/app/domain/change_set.py`, now `operations: max_length=20`, `spoilerless/app/api/change_set.py`). Body over `max_body_size_bytes` is rejected at the ASGI layer before decoding.
2. `ChangeSetService.propose()` (or `propose_via_tool` when called via the LLM tool) resolves persisted progress through the shared boundary, validates every target for existence, series scope, and visibility, and converts prohibited canonical/candidate direct edits to `create_note` operations (`spoilerless/app/services/change_set.py`).
3. Proposal persists only a `ChangeSet` in `awaiting_confirmation`; it does not mutate target graph content (`spoilerless/app/repository/change_set.py`).
4. Confirm re-reads progress and targets inside one managed Neo4j write transaction, detects stale state, applies all operations via the table-driven `_APPLY_SPECS` dispatch (PROB-09/#67), marks status, and logs one `Revision` atomically; `WITH u, s` carried between MERGEs avoids the Neo4j 5.x 503 class (`spoilerless/app/repository/change_set.py`).
5. Reject changes only ChangeSet status. Revert supports create-shaped applies and writes a separate `Reverted` revision (`spoilerless/app/repository/change_set.py`).

**State Management:**
- Browser state is local React state and hooks; no router or global data store (`frontend/src/App.tsx`). Graph workspace mode is now optionally controlled by the parent via `mode`/`onModeChange`.
- The graph scene is a serializable reducer: `frontend/src/hooks/useSceneState.ts` owns view, filters, selection, focus, camera, positions, expansions, timeline, Inspector state; camera/positions/expansions dispatches never trigger fetches or relayouts (D-24/D-25).
- `sessionStorage` is only a watch-progress loading cache; Neo4j is authoritative (`frontend/src/hooks/useWatchProgress.ts`, `spoilerless/app/repository/progress.py`).
- Users, sessions, notes/custom content, revisions, progress, chat sessions/messages, ChangeSets, and LLM settings are Neo4j-backed (`spoilerless/app/repository/`).
- Per-user in-flight chat generation limits are per-user module state plus a process-wide `asyncio.Semaphore(llm_max_concurrent_generations)` — still single-worker coordinated; cross-worker coordination remains an external concern.
- Focus signature set under `vizfocus:{series_id}` in Redis holds at most 64 distinct signatures per series (3600s TTL) to bound visualization cache cardinality; it is lazily populated inside `set_cached_visualization`.

## Key Abstractions

**Visibility Boundary:**
- Purpose: Represent the highest episode order safe for the current user.
- Examples: `spoilerless/app/api/boundary.py`, `spoilerless/app/spoiler/policy.py`, `spoilerless/app/domain/user_content.py`
- Pattern: Server-resolved positive episode order injected into parameterized Cypher via `resolve_effective_boundary()`; hidden and absent resources share a generic not-found response where applicable. Anonymous and no-progress authenticated readers both resolve to 1 (fail closed).

**Claim Projection:**
- Purpose: Present evidence-backed `Claim` nodes as graph edges while retaining provenance detail.
- Examples: `spoilerless/app/domain/graph.py`, `spoilerless/app/services/graph.py`
- Pattern: `subject_id → object_id` projection carrying `claim_id`; direct structural edges carry `claim_id = null`.

**Neo4jDatabase:**
- Purpose: Centralize the async driver and retryable query/transaction APIs.
- Examples: `spoilerless/app/graph/database.py`
- Pattern: Construct/open/close in FastAPI lifespan; repositories receive the application-owned instance.

**Ontology:**
- Purpose: Validate node, relationship, and claim vocabulary and expose user-safe subsets.
- Examples: `spoilerless/app/graph/ontology.py`, `ontology/node_types.yaml`, `ontology/relation_types.yaml`, `ontology/claim_types.yaml`
- Pattern: Versioned YAML loaded into an immutable application abstraction.

**Typed ChangeSet:**
- Purpose: Separate machine-proposed edits from explicitly confirmed, transactional graph mutations.
- Examples: `spoilerless/app/domain/change_set.py` (now `max_length=20`), `spoilerless/app/services/change_set.py:propose_via_tool`, `spoilerless/app/repository/change_set.py`
- Pattern: Propose (or `propose_via_tool` from LLM) → confirm/reject → optional guarded revert. The `operations` cap is now enforced at the domain layer.

**VisualizationDTO / Projection:**
- Purpose: Versioned, library-neutral presentation contract decoupled from both Neo4j and Cytoscape; safe by construction.
- Examples: `spoilerless/app/domain/visualization.py`, `spoilerless/app/services/visualization.py`, `frontend/src/types/graph.ts`
- Pattern: `metadata`/`nodes`/`edges`/`groups`/`timeline`/`focus` shape; edges carry semantic classes (never raw relation names); reference closure enforced at validation; `projection_version` + `effective_view_order` ride every DTO.

**Cytoscape Reconciler:**
- Purpose: Apply complete scene diffs imperatively while preserving element identity and runtime state.
- Examples: `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines, fully tracked) + `frontend/src/components/graph/cytoscapeReconciler.test.ts` (91 lines, headless tests)
- Pattern: Single `reconcileCytoscapeElements(cy, nextDefinitions)` inside `cy.batch()`; topology keys (`id`/`source`/`target`/`parent`) drive add/reparent/rewire/remove ordering; non-topology data is patched with removal of stale keys; runtime classes/selection/positions restored from pre-batch snapshot.

**Scene State Reducer:**
- Purpose: Own all serializable graph-workspace state so React (not Cytoscape) is the scene authority.
- Examples: `frontend/src/hooks/useSceneState.ts`
- Pattern: JSON-safe state object; focus ids mirror the server charset so unsafe candidates are refused before entering scene state (T10-FOCUS-04). Supports controlled mode via `mode`/`onModeChange`.

**Body/Host Gates:**
- Purpose: Reject oversized bodies and untrusted hosts before any domain logic runs.
- Examples: `spoilerless/app/main.py:BodySizeLimitMiddleware`, `spoilerless/app/main.py:TrustedHostMiddleware`, `spoilerless/app/main.py:_trusted_hosts()`
- Pattern: Pure-ASGI body streaming count with early header check + `BodyTooLarge` signal → 413 envelope; `TrustedHostMiddleware` allowlist from `ALLOWED_HOSTS` or `FRONTEND_ORIGINS` hosts.

## Entry Points

**Backend application:**
- Location: `spoilerless/app/main.py` (363 lines)
- Triggers: `uv run uvicorn spoilerless.app.main:app --reload` (or `uv run --project` / `render.yaml` build).
- Responsibilities: Build FastAPI, register `BodySizeLimitMiddleware` + `TrustedHostMiddleware` + CORS, install handlers, register routers, mount `/api/static`, own Neo4j and Redis lifecycle, disable docs in production, emit `warn_if_open_signup` at startup.

**Database setup CLI:**
- Location: `spoilerless/app/graph/setup.py`
- Triggers: `uv run spoilerless-setup` from `pyproject.toml`.
- Responsibilities: Open Neo4j, validate ontology/seed, create constraints/indexes, seed content, audit visibility.

**Frontend application:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite through scripts in `frontend/package.json`.
- Responsibilities: Mount `App` under React strict mode.

## Architectural Constraints

- **Threading:** FastAPI and the Neo4j driver are asynchronous; graph reads use `asyncio.gather()` (`spoilerless/app/services/graph.py`). `InMemorySessionRepository` test double uses a lock; production sessions use Neo4j. Chat generation is now also gated by a process-wide `asyncio.Semaphore` (`spoilerless/app/services/chat.py`).
- **Global state:** FastAPI's app state owns the database plus Neo4j-backed session/share repositories; Redis client is an `lru_cache` singleton (`spoilerless/app/main.py`, `spoilerless/app/cache/redis_client.py`). Settings are cached by `get_settings`; chat concurrency uses module-level state + semaphore (`spoilerless/app/core/config.py`, `spoilerless/app/services/chat.py`). Focus signature set is global Redis state bounded per series.
- **Import behavior:** Most `__init__.py` files are empty/docstrings. `spoilerless/app/revisions/__init__.py` defines the revision repository but performs no I/O; its 11-04 delta expands revision wiring. `spoilerless/app/api/graph.py:28` loads ontology allowlists at import time and now imports `resolve_effective_boundary`.
- **Database lifecycle:** `Neo4jDatabase` has no driver side effect in constructor; `open()` occurs in lifespan or setup CLI (`spoilerless/app/graph/database.py`, `spoilerless/app/main.py`, `spoilerless/app/graph/setup.py`).
- **Schema evolution:** No migration framework. Idempotent DDL in `spoilerless/app/graph/seed.py` + `Neo4jSessionRepository` is the schema mechanism; run `spoilerless-setup` for a prepared database.
- **Storage readiness:** Seed DDL covers seeded content, users, revisions, sessions, progress/chat indexes. It does not define explicit uniqueness for `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`, or `AppSetting`; `ShareToken` is the exception with uniqueness + expiry index plus open-signup warning wiring.
- **Auth boundary:** User-owned routes must resolve `CurrentUserDependency` and scope Cypher from `(:AppUser {id: $user_id})` (`spoilerless/app/api/deps.py`, `spoilerless/app/repository/`).
- **Graph rendering:** react-cytoscapejs's declarative `elements`/`layout` props are frozen after mount via `initialElementsRef`/`initialLayoutRef`; every scene update flows through `reconcileCytoscapeElements()` and layouts run through guarded imperative effects (`frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/cytoscapeReconciler.ts`, `frontend/src/components/graph/layoutConfig.ts`). Lightweight test adapters skip reconciler via `useImperativeReconcileRef`.
- **Projection safety:** Projections consume only complete safe graph detail; boundary-before-projection refuses effective orders above the served boundary and rejects (never silently drops) hidden rows; raw relation names never appear in DTOs; focus ids must reference nodes present in the DTO; expansion deltas never cached; per-series focus signature set bounded to 64 in Redis before caching (`spoilerless/app/services/visualization.py`, `spoilerless/app/domain/visualization.py`, `spoilerless/app/cache/graph_cache.py:_focus_capacity_allows`).
- **Static content:** Character portraits are self-hosted (`spoilerless/app/static/characters/`, served at `/api/static`); `image_url` seed values are relative and pass the CSP `img-src 'self'` rule. `frontend/vercel.json` now also hardens CSP at the edge.
- **Body/host gating:** All routes inherit `BodySizeLimitMiddleware` (413 `payload_too_large`, checked before JSON decoding) and `TrustedHostMiddleware` (Host validation against `ALLOWED_HOSTS` or `FRONTEND_ORIGINS` hosts).
- **LLM cost gating:** `llm_max_tool_calls_per_round` (default 8, `spoilerless/app/retrieval/pipeline.py`) and `llm_max_concurrent_generations` (default 4, `spoilerless/app/services/chat.py`) and `operations max_length=20` (domain) are hard caps; they are not client-tunable.
- **Docs posture:** `ENVIRONMENT=production` disables `/docs`/`/redoc`/`/openapi.json` at app construction time; `ENVIRONMENT` must be set before process start (Render dashboard env, not `render.yaml`).

## Anti-Patterns

### Application-side spoiler filtering

**What happens:** A consumer fetches broad data and hides future items in Python, React, or prompt instructions.
**Why it's wrong:** The browser or LLM already receives the spoiler before presentation filtering.
**Do this instead:** Put every visibility predicate on every relevant query hop via `spoilerless/app/spoiler/filter.py` and enforce it through the single `spoilerless/app/api/boundary.py:resolve_effective_boundary()` call in every spoiler-sensitive route; projections must consume only already-safe rows (`spoilerless/app/services/visualization.py`).

### Arbitrary LLM query or write access

**What happens:** Model text becomes Cypher or a direct graph mutation.
**Why it's wrong:** It bypasses server authority, ontology validation, spoiler boundaries, user confirmation, and revision logging.
**Do this instead:** Add typed retrieval tools in `spoilerless/app/retrieval/` or typed ChangeSet operations in `spoilerless/app/domain/change_set.py` (now `max_length=20`) and preserve the service/repository validation flow. The model's `propose_changeset` call thin-delegates to `ChangeSetService.propose_via_tool` which enforces the server-resolved boundary and ownership checks.

### Runtime logic in package initializers

**What happens:** Feature implementations accumulate in `__init__.py`, as the revision repository does in `spoilerless/app/revisions/__init__.py`.
**Why it's wrong:** It obscures module boundaries and makes imports less discoverable, even when no I/O runs.
**Do this instead:** Put new implementations in named modules and keep package initializers empty, declarative, or limited to explicit re-exports. The 11-04 revision wiring delta is still tolerated as incremental; prefer a named `spoilerless/app/revisions/repository.py` for the next feature.

### Letting the rendering library own scene diffs

**What happens:** Declarative element props are passed to react-cytoscapejs on every scene change; its id-only patcher removes obsolete compound parents before detaching shared children.
**Why it's wrong:** Compound→flat scene switches cascade-delete shared nodes and then throw while adding edges that reference the deleted ids.
**Do this instead:** Freeze the declarative props at mount (`initialElementsRef`/`initialLayoutRef`) and apply all diffs through the topology-aware `reconcileCytoscapeElements()` in `frontend/src/components/graph/cytoscapeReconciler.ts`, covered by headless tests in `frontend/src/components/graph/cytoscapeReconciler.test.ts`.

### Client-controlled spoiler boundary

**What happens:** A route trusts a client-supplied `visible_until_order` without clamping it to persisted progress or without failing closed for anonymous/no-progress callers.
**Why it's wrong:** A spoofed order can leak future content; an anonymous caller could probe episode ids above boundary 1.
**Do this instead:** Call `resolve_effective_boundary()` in every spoiler-sensitive handler and let it validate the result to a persisted episode — never hand-roll `min(...)` in the handler.

### Client-tunable LLM cost gates

**What happens:** Tool-call limits or generation concurrency are taken from request payload.
**Why it's wrong:** The LLM or a malicious client can drive unbounded spend or starvation.
**Do this instead:** Keep caps server-owned in `spoilerless/app/core/config.py` and read them once per turn/process — `llm_max_tool_calls_per_round`, `llm_max_concurrent_generations`, and `operations max_length=20`.

## Error Handling

**Strategy:** Validate at Pydantic/FastAPI boundaries, enforce ASGI body/host gates before handlers, use feature exceptions inside services/repositories, and translate them to generic structured HTTP errors.

**Patterns:**
- Use `{ "detail": { "code": "...", "message": "..." } }` via `spoilerless/app/core/errors.py`; `frontend/src/api/client.ts` normalizes this and FastAPI validation arrays. New code: `payload_too_large` (413, D-08) from `BodySizeLimitMiddleware`; `rate_limit_unavailable` (503, SEC-DOS-001) from `RateLimitService` when production Redis is unavailable and `rate_limit_fail_open is False`.
- Gate body/host before handlers: `BodySizeLimitMiddleware` emits 413 `payload_too_large` without touching route logic; `TrustedHostMiddleware` emits 400 on disallowed Host.
- Install database, LLM, and repository exception handlers centrally in `spoilerless/app/main.py` (`install_database_error_handlers`, `install_llm_error_handlers`, `install_repository_error_handlers` from `spoilerless/app/api/exceptions.py`).
- `ServiceUnavailable`/`AuthError`/`Neo4jError` map to 503 `DATABASE_UNAVAILABLE`; `ConstraintError` maps to 409 `CONSTRAINT_VIOLATION`; rate-limit rejection maps to 429 `TOO_MANY_REQUESTS` (or 503 when fail-closed) (`spoilerless/app/core/errors.py`, `spoilerless/app/services/rate_limit.py`).
- `ClientError` (invalid Cypher) is deliberately excluded from the 503 mapping — masking it would hide app bugs — so it surfaces as plain 500 (`spoilerless/app/core/errors.py`).
- Make hidden, foreign, and missing user-scoped resources indistinguishable where disclosure would leak ownership or future content (`spoilerless/app/repository/chat.py`, `spoilerless/app/api/chat.py`).
- Sanitize errors that become model-visible: `_neutralize_answer_delimiters()` keeps tool-result framing intact and exception handlers in `spoilerless/app/services/change_set.py:propose_via_tool` expose only the exception type, never paths/hostnames/parameter values.
- Emit structured terminal SSE error events after headers have been sent (`spoilerless/app/api/chat.py`, `frontend/src/api/chat.ts`); body-size rejection happens before SSE starts, so it never leaks as an in-stream error.

## Cross-Cutting Concerns

**Logging:** No centralized application logging layer is present; avoid printing secrets or query internals. The setup CLI prints only aggregate counts (`spoilerless/app/graph/setup.py`). Startup warning `warn_if_open_signup` runs once in `lifespan` and is intentionally not noisy per-request.
**Validation:** Pydantic models validate HTTP and LLM-tool inputs (now including `operations max_length=20` and settings base-URL host/scheme); ontology and seed validators gate graph types/content; visualization DTO validation enforces reference closure; context delimiter validation escapes exact section tags in answers (`spoilerless/app/domain/`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/graph/ontology.py`, `spoilerless/app/graph/seed.py`, `spoilerless/app/domain/visualization.py`).
**Authentication:** Google ID tokens create hashed-token HttpOnly sessions; only the token hash is persisted in Neo4j (`spoilerless/app/services/auth.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/api/deps.py`). Origin validation still checks `Origin`/`Referer` against `FRONTEND_ORIGINS`.
**Rate limiting:** Redis-backed when `REDIS_URL` is set; fail-closed in production when `REDIS_URL` is set but Redis is unreachable (503 `rate_limit_unavailable` instead of silent pass-through) — gated by `ENVIRONMENT=production` + `rate_limit_fail_open is False` (`spoilerless/app/services/rate_limit.py`).
**Body/Host:** `max_body_size_bytes` (1 MiB) and `allowed_hosts` (or derived from `FRONTEND_ORIGINS`) are validated via `Settings` and enforced by ASGI middleware before any domain code.
**Secrets:** LLM API keys are write-only in the API contract and masked on reads; provider construction reads the full stored value only server-side (`spoilerless/app/services/settings.py`, `spoilerless/app/services/chat.py`). Captured tool-result exceptions expose only the exception type.
**Provenance:** Canonical/candidate claims require source/evidence links; retrieval citations are checked against the current turn's retrieved IDs; projection DTOs carry `projection_version` + `effective_view_order` so a cached DTO can never cross a boundary; focus signature set bounds prevents cache-key enumeration (`spoilerless/app/graph/seed.py`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/domain/visualization.py`, `spoilerless/app/cache/graph_cache.py`).

---

*Architecture analysis: 2026-08-20*
