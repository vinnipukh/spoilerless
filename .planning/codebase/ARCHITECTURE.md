<!-- refreshed: 2026-08-26 -->
---
last_mapped: 2026-08-26
focus: arch
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---

# Architecture

**Analysis Date:** 2026-08-26

## System Overview

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ React SPA (`frontend/src/`)                                                  │
│ App.tsx (291 lines) → useWorkspaceScene / useWorkspaceNavigation             │
│ → ResizableRail / AppIcons / GraphFilterPanel                                 │
│ → GraphCanvas (426 lines) [useCytoscapeLayout + cytoscapeReconciler]         │
│ → DetailPanel (180 lines) [OverviewTab, ClaimsTab, EvidenceTab, NotesTab]   │
│ → Scene conversion: sceneElements.ts + graphTokens.ts + positionCache.ts     │
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                                │ HTTP JSON / SSE, credentials included         
                ▼                       ▼                                       
┌──────────────────────────────────────────────────────────────────────────────┐
│ FastAPI (`spoilerless/app/main.py`, 363 lines, `spoilerless/app/api/`)       │
│ BodySizeLimitMiddleware (413) → TrustedHostMiddleware → CORSMiddleware         │
│ routes → require_boundary / resolve_effective_boundary → domain validation   │
│ services: GraphService facade / VisualizationService / RevisionService       │
│ RateLimiter (lazy re-init) / ChatService (semaphore + provider)              │
└───────────────┬───────────────────────┬──────────────────────────────────────┘
                │                       │                                       
                ▼                       ▼                                       
┌──────────────────────────────────┐  ┌───────────────────────────────────────┐ 
│ Neo4j (`spoilerless/app/graph/`) │  │ Optional LLM (`spoilerless/app/llm/`)  │
│ data, users, state, settings     │  │ allowlisted GraphRAG tools only        │
│ single-query candidate visibility│  │ SSRF bounded (1s DNS) + cost caps     │
└──────────────────────────────────┘  └───────────────────────────────────────┘ 
```

The product is a three-tier web application: a decomposed state-driven React SPA, an asynchronous modular FastAPI backend, and Neo4j. The frontend and optional LLM receive only graph data that Cypher has already bounded by watch progress. Source-backed `Claim` nodes are projected into frontend graph edges by `GraphService`; structural relationships remain direct Neo4j relationships (`spoilerless/app/services/graph.py`, `spoilerless/app/spoiler/filter.py`).

The live API surface contains 52 HTTP operations on 39 unique path templates across eleven routers assembled in `spoilerless/app/main.py`; `/health` (GET and HEAD) is defined on the application itself. In `development` the interactive docs remain at `/docs`/`/redoc`/`/openapi.json`; when `ENVIRONMENT=production` those three are disabled at construction time via `_docs_kwargs`.

Phase 12 eliminated architectural technical debt, decomposed monolithic god-files, and consolidated subsystems:

- **Frontend Architectural Decomposition:**
  - `frontend/src/App.tsx` was reduced from ~900 lines to 291 lines, extracting scene coordination into `useWorkspaceScene.ts`, workspace navigation into `useWorkspaceNavigation.ts`, layout rails into `ResizableRail.tsx`, and icon primitives into `AppIcons.tsx`.
  - `frontend/src/components/graph/GraphCanvas.tsx` was reduced from ~700 lines to 426 lines by isolating Cytoscape layout lifecycle management into `useCytoscapeLayout.ts` and node creation into `CreateCustomNodeDialog.tsx`.
  - `frontend/src/components/detail/DetailPanel.tsx` was reduced from ~750 lines to 180 lines by breaking tab bodies into `OverviewTab.tsx`, `ClaimsTab.tsx`, `EvidenceTab.tsx`, `NotesTab.tsx`, `CharacterPortrait.tsx`, and relationship creation into `CreateRelationshipDialog.tsx`.
  - Element conversion is consolidated into `frontend/src/lib/graph/sceneElements.ts` (242 lines), with design tokens standardized in `frontend/src/lib/tokens/graphTokens.ts` and layout positions preserved across transitions via `positionCache.ts`.
- **Backend Modularization & Decomposition:**
  - The monolithic 1,173-line `spoilerless/app/services/visualization.py` was decomposed into the package `spoilerless/app/services/visualization/` (`service.py`, `views.py`, `expansion.py`, `focus.py`, `boundary.py`, `node_builders.py`, `constants.py`, `__init__.py`).
  - `spoilerless/app/revisions/__init__.py` was split into `repository.py` (141 lines), `service.py` (203 lines), and a clean facade `__init__.py`.
  - `spoilerless/app/services/graph.py` introduces `GraphService` as a centralized facade for visible graph reads (`read_visible_graph`) and cache invalidation.
  - `spoilerless/app/api/boundary.py` provides `require_boundary` dependency injection for typed route boundary resolution.
- **Security & Reliability Remediations:**
  - `NoteResponse`, `CustomNodeResponse`, and `CustomRelationshipResponse` have `user_id: Optional[str] = None` to support privacy-scrubbed reads without Pydantic validation errors (THERMO-P0-01).
  - Candidate claim visibility checks in `spoilerless/app/graph/candidates.py` were consolidated into a single Cypher roundtrip per claim (THERMO-P2-03).
  - SSRF base URL validation in `spoilerless/app/domain/settings.py` now bounds DNS resolution to a 1.0s timeout with `asyncio.wait_for` (THERMO-P2-02).
  - `RateLimiter` in `spoilerless/app/services/rate_limit.py` implements resilient lazy re-initialization to recover from transient startup Redis outages, registering uppercase error codes (THERMO-P2-04, THERMO-P3-03).
  - Frontend CSP in `vercel.json` and `index.html` and backend `TrustedHostMiddleware` permit `https://api.spoilerless.net` and `https://*.onrender.com` (THERMO-P1-02, THERMO-P2-01).

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| React composition root | Auth gate, series/progress selection, layout assembly; delegates scene state to hooks | `frontend/src/App.tsx` (291 lines) |
| Workspace scene hook | Owns scene transitions, view fetching, expansion state, and graph refresh | `frontend/src/hooks/useWorkspaceScene.ts` (217 lines) |
| Workspace navigation hook | Workspace mode (`overview`/`full`) and active tab state | `frontend/src/hooks/useWorkspaceNavigation.ts` (50 lines) |
| Resizable rail | Reusable horizontal draggable/keyboard-resizable layout rail | `frontend/src/components/layout/ResizableRail.tsx` (143 lines) |
| Icon primitives | Centralized SVG iconography for app navigation, tabs, and actions | `frontend/src/components/layout/AppIcons.tsx` (74 lines) |
| Graph canvas | Cytoscape container, interaction events, imperative mode synchronization | `frontend/src/components/graph/GraphCanvas.tsx` (426 lines) |
| Cytoscape layout hook | Manages fcose/dagre/cose-bilkent layout runs, debouncing, and layout cleanup | `frontend/src/components/graph/useCytoscapeLayout.ts` (197 lines) |
| Cytoscape reconciler | Topology-aware imperative diffing inside `cy.batch()` | `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines) |
| Scene elements adapter | Converts `VisualizationDTO` and `GraphResponse` into Cytoscape elements | `frontend/src/lib/graph/sceneElements.ts` (242 lines) |
| Graph design tokens | Centralized node sizes, colors, shapes, badge styles, and 44px touch targets | `frontend/src/lib/tokens/graphTokens.ts` (57 lines) |
| Position cache | Preserves node layout coordinates across view switches and expansions | `frontend/src/lib/graph/positionCache.ts` (37 lines) |
| Detail inspector panel | Collapsible inspector container hosting tabbed views | `frontend/src/components/detail/DetailPanel.tsx` (180 lines) |
| Overview tab | Character and event summary, relationships, and metadata | `frontend/src/components/detail/tabs/OverviewTab.tsx` (152 lines) |
| Claims tab | Lists atomic claims supporting selected node or structural edge | `frontend/src/components/detail/tabs/ClaimsTab.tsx` (49 lines) |
| Evidence tab | Displays evidence fragments, locators, and source citations | `frontend/src/components/detail/tabs/EvidenceTab.tsx` (45 lines) |
| Notes tab | User note authoring, editing, deletion, and target association | `frontend/src/components/detail/tabs/NotesTab.tsx` (235 lines) |
| Character portrait | Portrait renderer with fallback initials and API URL prefixing | `frontend/src/components/detail/CharacterPortrait.tsx` (78 lines) |
| Node creation dialog | Dialog for creating user custom nodes with label selection | `frontend/src/components/dialogs/CreateCustomNodeDialog.tsx` (130 lines) |
| Relationship creation dialog | Dialog for creating user custom relationships with numeric episode order | `frontend/src/components/dialogs/CreateRelationshipDialog.tsx` (167 lines) |
| FastAPI assembly | Lifespan database/rate-limiter, CORS, host/body middleware, routers, docs gating | `spoilerless/app/main.py` (363 lines) |
| Host/body middleware | Pure-ASGI `BodySizeLimitMiddleware` (413) and `TrustedHostMiddleware` | `spoilerless/app/main.py` |
| Shared boundary resolver | Fail-closed `resolve_effective_boundary()` and `require_boundary` dependency | `spoilerless/app/api/boundary.py` |
| Graph service facade | Consolidates visible graph reads and cache invalidation across services | `spoilerless/app/services/graph.py` |
| Visualization projection package | Modular projection, expansion, focus, and boundary pipeline | `spoilerless/app/services/visualization/` (8 modules) |
| Revision service & repo | Append-only revision logging and safe ownership-checked revert | `spoilerless/app/revisions/` (`service.py`, `repository.py`) |
| Rate limiter service | Resilient Redis-backed rate limiting with lazy re-init | `spoilerless/app/services/rate_limit.py` |
| Candidate ingest & review | Extraction staging with single-roundtrip Cypher checks and pagination | `spoilerless/app/graph/candidates.py`, `spoilerless/app/api/candidates.py` |
| Spoiler filter & policy | Core Cypher visibility fragments and pure effective-boundary math | `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py` |
| GraphRAG retrieval | Twelve typed tools, delimiter-neutralized 9-section context assembly | `spoilerless/app/retrieval/` (`pipeline.py`, `tools.py`, `context.py`) |

## Pattern Overview

**Overall:** Layered SPA + service/repository backend over a graph database, with a bounded tool-calling GraphRAG subsystem and a modular presentation-projection layer over the safe graph read; fail-closed boundary enforcement and ASGI-level operational gates protect the perimeter.

**Key Characteristics:**
- Normal dependency direction `api → services → repository → graph/database` with `GraphService` facade acting as the centralized coordinator for graph reads and cache invalidation.
- Every spoiler-sensitive route resolves its effective boundary through `resolve_effective_boundary()` / `require_boundary` (`spoilerless/app/api/boundary.py`) — anonymous and no-record readers clamp to 1, authenticated readers with progress clamp to `min(requested, view_as_of, watched_through)` via `spoilerless/app/spoiler/policy.py:effective_view_order`.
- Candidate claim visibility checks execute in a single consolidated Cypher query per claim, validating subject/object/episode visibility in one roundtrip.
- Request bodies are size-bounded (1 MiB default, 413 `PAYLOAD_TOO_LARGE`) at the pure-ASGI layer; host validation permits configured frontend origins and Render wildcard domains.
- Rate limiting is Redis-backed and resilient: failures at startup do not crash the app, but trigger lazy re-initialization on incoming requests. In production, Redis outage surfaces as 503 `RATE_LIMIT_UNAVAILABLE`.
- React god-components are decomposed into focused single-responsibility modules: container components (`App.tsx`, `GraphCanvas.tsx`, `DetailPanel.tsx`) stay under 450 lines and delegate to custom hooks (`useWorkspaceScene`, `useCytoscapeLayout`) and dedicated tab/dialog components.
- Imperative Cytoscape mutations use declarative-to-imperative reconciliation (`cytoscapeReconciler.ts`) within `cy.batch()`, with element construction unified in `sceneElements.ts` and style tokens centralized in `graphTokens.ts`.

## Layers

**Frontend Presentation:**
- Purpose: Render authentication, graph exploration, detail/editing, revision, chat, and settings experiences.
- Location: `frontend/src/components/`
- Contains: Feature folders, UI primitives under `frontend/src/components/ui/`, decomposed detail tabs under `frontend/src/components/detail/tabs/`, dialogs under `frontend/src/components/dialogs/`, layout components under `frontend/src/components/layout/`, and the Cytoscape canvas in `frontend/src/components/graph/`.
- Depends on: Hooks (`frontend/src/hooks/`), design tokens (`frontend/src/lib/tokens/graphTokens.ts`), element adapters (`frontend/src/lib/graph/sceneElements.ts`), and types (`frontend/src/types/`).
- Used by: `frontend/src/App.tsx`.

**Frontend State and API:**
- Purpose: Hold browser state and convert typed actions into backend requests.
- Location: `frontend/src/hooks/`, `frontend/src/api/`, `frontend/src/providers/`
- Contains: Fetch state machines, Google-session context, JSON transport, manual SSE stream parsing, workspace scene management (`useWorkspaceScene.ts`), workspace navigation (`useWorkspaceNavigation.ts`), and Cytoscape layout management (`useCytoscapeLayout.ts`).
- Depends on: Browser Fetch API and contracts in `frontend/src/types/`.
- Used by: `frontend/src/App.tsx` and feature components.

**API Layer:**
- Purpose: Expose the 52-operation HTTP contract and translate domain/repository failures into stable envelopes; operational gates and spoiler-boundary centralization live here.
- Location: `spoilerless/app/api/` plus `spoilerless/app/main.py` middleware
- Contains: Eleven router modules, shared boundary dependency (`boundary.py`), shared auth/database deps (`deps.py`), repository error-handler installation (`exceptions.py`), `BodySizeLimitMiddleware`, `TrustedHostMiddleware`, CORS, and docs gating.
- Depends on: Domain models and service facades (`GraphService`, `ProgressService`, `AuthService`, `RevisionService`, `ChangeSetService`).
- Used by: `spoilerless/app/main.py`.

**Domain Layer:**
- Purpose: Define strict contracts shared across backend layers.
- Location: `spoilerless/app/domain/`
- Contains: Pydantic models for auth, graph, series, user content (with nullable `user_id`), extraction, revisions, progress, chat, ChangeSets (`change_set.py` with `ProposeChangesetInput` and 20-op cap), settings (with 1s DNS timeout for SSRF validation), and visualization DTOs (`visualization.py`).
- Depends on: Standard library and Pydantic.
- Used by: API, service, and repository layers.

**Service Layer:**
- Purpose: Coordinate business workflows and enforce rules spanning repositories.
- Location: `spoilerless/app/services/`
- Contains: `GraphService` (`graph.py`), `VisualizationProjectionService` (`visualization/` package), `AuthService` (`auth.py` with `warn_if_open_signup`), `ChatService` (`chat.py`), `ChangeSetService` (`change_set.py`), `ProgressService` (`progress.py`), `RateLimiter` (`rate_limit.py`), and `RevisionService` (`revisions/service.py`).
- Depends on: Repositories, domain models, cache, and spoiler policy.
- Used by: API layer and background pipelines.

**Persistence Layer:**
- Purpose: Own user scoping, Neo4j commands, managed transactions, and row normalization.
- Location: `spoilerless/app/repository/`, `spoilerless/app/revisions/repository.py`, `spoilerless/app/graph/candidates.py`
- Contains: Repositories for users, sessions, user content, progress, chat, settings, ChangeSets, share tokens, revisions, and candidate graph writes.
- Depends on: Neo4j database driver and Cypher query constants.
- Used by: Service layer.

**Graph & Spoiler Policy Layer:**
- Purpose: Provide database driver lifecycle, ontology validation, seed management, Cypher visibility fragments, and pure boundary math.
- Location: `spoilerless/app/graph/`, `spoilerless/app/spoiler/`
- Contains: `database.py`, `ontology.py`, `seed.py`, `setup.py`, `filter.py`, `policy.py`, and `visibility.py`.
- Depends on: Neo4j driver and PyYAML.
- Used by: Repositories, services, and API boundary.

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **Decomposed Monolithic Frontend Files:**
  - `App.tsx` reduced from ~900 lines to 291 lines; extracted `useWorkspaceScene`, `useWorkspaceNavigation`, `ResizableRail`, and `AppIcons`.
  - `GraphCanvas.tsx` reduced from ~700 lines to 426 lines; extracted `useCytoscapeLayout` and `CreateCustomNodeDialog`.
  - `DetailPanel.tsx` reduced from ~750 lines to 180 lines; extracted `OverviewTab`, `ClaimsTab`, `EvidenceTab`, `NotesTab`, `CharacterPortrait`, and `CreateRelationshipDialog`.
- **Consolidated Adapters & Standardized Tokens:**
  - `sceneElements.ts` created to unify Cytoscape element generation across projections and legacy scenes.
  - `graphTokens.ts` created to centralize color tokens, node dimensions, border widths, and 44px touch targets.
  - `positionCache.ts` created to preserve coordinates during scene transitions.
- **Decomposed Backend Modules:**
  - `spoilerless/app/services/visualization.py` (1,173 lines) decomposed into package `spoilerless/app/services/visualization/` with 8 focused modules.
  - `spoilerless/app/revisions/__init__.py` (341 lines) split into `repository.py`, `service.py`, and `__init__.py`.
  - `spoilerless/app/services/graph.py` facade introduced for visible graph reads and cache invalidations.
  - `spoilerless/app/api/boundary.py` gained `require_boundary` dependency.
- **Security & Resilience Hardening:**
  - Privacy-scrubbed responses (`NoteResponse`, `CustomNodeResponse`, `CustomRelationshipResponse`) updated with `user_id: Optional[str] = None`.
  - Candidate ingest visibility check consolidated into single Cypher query per claim.
  - SSRF DNS resolution bounded to 1.0s timeout.
  - RateLimiter implemented lazy re-initialization on startup Redis outages, registering uppercase error codes.
  - CSP and TrustedHost configured for Render production origins.

---

*Architecture analysis: 2026-08-26*
