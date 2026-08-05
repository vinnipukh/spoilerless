<!-- generated-by: gsd-doc-writer -->
# Spoilerless — Architecture Guide

> **Project:** Spoiler-aware TV series knowledge graph
> **Prototype scope:** Dexter, Season 1, Episodes 1–3

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Component Diagram](#2-component-diagram)
3. [Directory Structure Rationale](#3-directory-structure-rationale)
4. [Layer-by-Layer Breakdown](#4-layer-by-layer-breakdown)
   - [4.1 Frontend (React + Cytoscape)](#41-frontend-react--cytoscape)
   - [4.2 API Layer (FastAPI)](#42-api-layer-fastapi)
   - [4.3 Service Layer](#43-service-layer)
   - [4.4 Repository & Database Layer](#44-repository--database-layer)
   - [4.5 Neo4j Graph Database](#45-neo4j-graph-database)
5. [Key Abstractions](#5-key-abstractions)
6. [Data Flow Examples](#6-data-flow-examples)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
   - [7.1 Spoiler-Aware Data Flow](#71-spoiler-aware-data-flow)
   - [7.2 The Claim Model](#72-the-claim-model)
   - [7.3 Ontology System](#73-ontology-system)
   - [7.4 Origin System](#74-origin-system)
   - [7.5 Authentication & Sessions](#75-authentication--sessions)
   - [7.6 Error Handling](#76-error-handling)
   - [7.7 Revision History](#77-revision-history)
   - [7.8 GraphRAG-Lite Chat Pipeline](#78-graphrag-lite-chat-pipeline)
   - [7.9 ChangeSet Two-Stage Mutation Flow](#79-changeset-two-stage-mutation-flow)
   - [7.10 Spoiler-Safety Invariants](#710-spoiler-safety-invariants)
   - [7.11 Settings System (User-Configurable LLM Provider)](#711-settings-system-user-configurable-llm-provider)
   - [7.12 Candidate Extraction & Review Workflow](#712-candidate-extraction--review-workflow)
   - [7.13 Role-Based Access Control (Admin Role)](#713-role-based-access-control-admin-role)
   - [7.14 Redis-Backed Rate Limiting and Graph Response Cache](#714-redis-backed-rate-limiting-and-graph-response-cache)
8. [Key Design Decisions](#8-key-design-decisions)
9. [Future Extensibility Points](#9-future-extensibility-points)
10. [Appendices](#10-appendices)

---

## 1. System Overview

Spoilerless is a **spoiler-aware TV series knowledge graph** application. It lets a signed-in user explore character relationships, events, locations, organizations, and narrative claims from a TV series — all filtered by how much of the series they've watched. Users can also attach notes, create custom nodes/relationships, and — when an LLM provider is configured — ask a spoiler-grounded chat agent questions about the graph.

The core architectural invariant is that **spoilery content is never transmitted to the client** (or to the LLM) unless the requester has already reached that point in the story. Spoiler-sensitive content nodes, relationships, and claims carry a `visible_from_order` field; system records such as users, sessions, progress, chat, ChangeSets, and settings do not universally carry it. Spoiler-aware reads filter content at the Cypher layer rather than after retrieval.

The system is a multi-series-capable web application composed of three deployable parts: a React single-page application, a FastAPI backend, and a Neo4j graph database running in Docker. Authentication scopes progress, chat, and ChangeSets to users, but ordinary notes, custom nodes, and custom relationships have no general `AppUser` ownership binding and are not isolated per user.

### Stack Summary

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript 6, Vite 8, Cytoscape.js 3 + cose-bilkent |
| UI Library | Radix UI, shadcn/ui, Tailwind CSS 4, Lucide icons |
| Backend | Python 3.13+, FastAPI 0.140+, Uvicorn, Pydantic v2 |
| Database | Neo4j 2026 Community (Docker Compose) |
| Graph driver | `neo4j` Python driver 6.2+ (async) |
| Auth | Google Sign-In (ID token verification via `google-auth`); `ADMIN_EMAILS`-derived `admin`/`user` role |
| LLM (optional) | OpenAI-compatible chat completions or Google Gemini REST |
| Cache / rate limiting (optional) | Upstash Redis via `redis.asyncio` + `pyrate-limiter` (`fastapi-limiter`'s successor) — disabled when `REDIS_URL` is empty |
| Package management | `uv` (Python), `npm` (frontend) |
| Orchestration | Docker Compose (Neo4j container only — backend/frontend run natively) |

---

## 2. Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend (React 19 + Vite, :5173)             │
│  AuthProvider → LoginPage / AppShell                              │
│   ┌──────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐  │
│   │ Series/  │ │ GraphCanvas  │ │ DetailPanel│ │ ChatPanel   │  │
│   │ Episode  │ │ (Cytoscape)  │ │ (claims/   │ │ (GraphRAG-  │  │
│   │ Select   │ │              │ │  history)  │ │  lite chat) │  │
│   └──────────┘ └──────────────┘ └────────────┘ └─────────────┘  │
│              Vite dev-server proxy: /api → http://127.0.0.1:8000 │
└─────────────────────────────────────────────────────────────────┘
                          │  fetch (credentials: include)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                Backend (FastAPI + Uvicorn, :8000)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ API Layer — spoilerless/app/api/                               │  │
│  │ series · graph · user_content · auth · revisions ·         │  │
│  │ candidates · progress · chat · change_set · settings       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Service Layer — spoilerless/app/services/                      │  │
│  │ SeriesService · GraphService · AuthService ·                │  │
│  │ ProgressService · ChatService · ChangeSetService ·          │  │
│  │ SettingsService                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Repository Layer — spoilerless/app/repository/                 │  │
│  │ UserRepository · SessionRepository (Neo4j) ·                │  │
│  │ UserContentRepository · ChangeSetRepository ·               │  │
│  │ ChatRepository · ProgressRepository · SettingsRepository    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Graph / Spoiler Layer — spoilerless/app/graph/, spoiler/        │  │
│  │ Neo4jDatabase · ontology.py · seed.py · setup.py ·           │  │
│  │ filter.py (parameterized, visibility-gated Cypher)          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ GraphRAG-lite (optional) — spoilerless/app/retrieval/, llm/     │  │
│  │ RetrievalPipeline · 11 allowlisted tools · LLMProvider      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Cache / Rate-Limit Layer (optional) — spoilerless/app/cache/,   │  │
│  │ services/rate_limit.py — one shared redis.asyncio client;    │  │
│  │ cache-aside for GET .../graph, RedisBucket rate limiters on  │  │
│  │ login/chat-send/content-write; no-op when REDIS_URL is empty │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │  bolt://localhost:7687        │ rediss://
                          ▼                                 ▼ (optional)
┌─────────────────────────────────────────────────────────────────┐   ┌──────────────┐
│              Neo4j 2026 Community (Docker, :7474 / :7687)         │   │ Upstash Redis│
│  Series, Season, Episode, Scene, Character, Location,             │   │ (rate limits,│
│  Organization, Object, Event, Claim, Source, EvidenceFragment,    │   │  graph cache)│
│  UserNote, Revision, AppUser, ChangeSet, ChatMessage, AppSetting  │   └──────────────┘
└─────────────────────────────────────────────────────────────────┘
```

The backend predominantly follows a layered architecture, but several API modules use repositories or transaction/data-access modules directly:

```
API Layer        ← HTTP handlers, routing, request validation
Domain Models     ← Pydantic schemas shared across all layers
Service Layer     ← business logic orchestration
Repository Layer  ← data-access abstraction
Database Layer    ← Neo4j driver, connection management
Spoiler Filter    ← parameterized Cypher with built-in visibility gating
```

**Intended dependency flow:** API → service → repository → database, while domain models (`spoilerless/app/domain/`) are imported across layers. The current code has explicit route-level deviations: `candidates.py` and `revisions.py` contain direct transaction/data-access logic, `user_content.py` constructs and calls `UserContentRepository` in handlers, and chat session handlers reach `ChatRepository` through `ChatService` while `chat.py` imports repository exceptions directly.

---

## 3. Directory Structure Rationale

```
spoilerless/
├── spoilerless/
│   └── app/
│       ├── api/            # Route handlers — one module per resource area
│       ├── cache/          # Optional Redis layer: redis_client.py (shared
│       │                    #   redis.asyncio singleton) and graph_cache.py
│       │                    #   (cache-aside for GET .../graph); both no-op
│       │                    #   when REDIS_URL is empty
│       ├── core/           # Settings (pydantic-settings) and error-envelope helpers
│       ├── domain/         # Pydantic models — the request/response contract
│       ├── graph/          # Neo4j driver, ontology loader, seed pipeline, candidate
│       │                    #   ingest, and feature Cypher constants (chat, change_set,
│       │                    #   progress) alongside spoiler/filter.py's graph reads
│       ├── llm/            # LLM provider abstraction, system prompts, fallback text
│       ├── repository/     # Data-access layer (Neo4j queries; session store — Neo4j
│       │                    #   by default, in-memory implementation for dev/tests)
│       ├── retrieval/      # GraphRAG-lite pipeline and allowlisted retrieval tools
│       ├── revisions/      # Revision (audit trail) domain module
│       ├── services/       # Business logic orchestration, one class per feature
│       │                    #   (rate_limit.py is a module of RateLimiter
│       │                    #   dependency instances, not a class-per-feature
│       │                    #   service)
│       ├── spoiler/        # Isolated, dependency-free spoiler-filter Cypher constants
│       └── main.py         # FastAPI app assembly, router registration, CORS, lifespan
│   └── tests/               # pytest suite (spoilerless/tests/, see pyproject.toml testpaths)
├── scripts/                 # zombie_sweep.py — dry-run-first cleanup of orphaned
│                            #   :AppUser rows and stale :Session nodes (PROB-22/#46)
├── frontend/
│   └── src/
│       ├── api/            # Typed fetch clients, one file per backend resource
│       ├── components/     # React components grouped by feature (graph, chat, auth, ...)
│       ├── hooks/           # Data-fetching and state hooks
│       ├── lib/             # searchIndex.ts (zero-dep substring search), byok.ts
│       ├── providers/       # React context providers (auth)
│       └── types/           # TypeScript types mirroring spoilerless/app/domain/*.py
├── data/dexter/             # Seed data for the Dexter S01E01–03 prototype
│   ├── metadata/            # Series and episode metadata
│   └── seed/                # Characters, claims, events, evidence, locations, sources
├── ontology/                 # Versioned YAML type system (node/relation/claim types)
├── docs/                     # Project documentation (this directory)
├── docker-compose.yml         # Neo4j container orchestration only
├── pyproject.toml             # Python project config, dependencies, pytest config
└── .env.example                # Environment variable template
```

The split between `data/` (content) and `ontology/` (schema) lets the seed pipeline validate every seeded entity against the type system before writing to Neo4j — a malformed seed file fails fast at `spoilerless-setup` time rather than producing an inconsistent graph. The backend's `api/ → services/ → repository/ → graph/` layering mirrors a conventional three-tier backend, with `spoiler/` singled out as its own directory specifically because the spoiler-filtering Cypher is the system's central invariant and is kept free of FastAPI/Pydantic imports so it can be unit-tested and audited in isolation.

---

## 4. Layer-by-Layer Breakdown

### 4.1 Frontend (React + Cytoscape)

**Location:** `frontend/`

A single-page application that renders an interactive knowledge graph using Cytoscape.js, gated behind Google Sign-In.

#### Directory Structure

```
frontend/src/
├── api/              # client.ts (fetch wrapper + ApiError; error normalization to
│                      #   INVALID_REQUEST / UNKNOWN_ERROR), graph.ts, series.ts,
│                      # auth.ts, revisions.ts, progress.ts, chat.ts, changeSet.ts,
│                      # settings.ts, userContent.ts
├── components/
│   ├── auth/          # LoginPage
│   ├── chat/           # ChatLauncher, ChatSheet, ChatPanel, SessionPicker,
│   │                    # MessageList/MessageBubble, CitationChip, ChangeSetCard
│   ├── detail/          # DetailPanel, StructuralEdgeCard, RevisionHistoryPanel
│   ├── episode/          # EpisodeSelector, SeriesSelect, ConfirmAdvanceModal
│   ├── graph/             # GraphCanvas, graphElements, graphStylesheet,
│   │                    # GraphControls, GraphLegend, GraphFocusIndicator,
│   │                    # GraphStatus, NodeSearch, PathFinder, relationshipStyles
│   ├── layout/             # AppShell
│   ├── palette/            # CommandPalette (⌘K)
│   ├── series/             # SeriesDashboard
│   ├── settings/            # SettingsPage
│   ├── timeline/            # TimelineView, TimelineEventRow
│   └── ui/                  # shadcn/ui primitives (button, card, dialog, alert, ...)
├── hooks/               # useGraph, useWatchProgress, useSeries, useEpisodes,
│                         # useNotes, useRevisions, useChatSessions, useChatMessages,
│                         # useHotkey
├── lib/                 # searchIndex.ts (zero-dep substring search behind node search,
│                         #   notes & claims search, and the ⌘K palette), byok.ts,
│                         #   nodeTypes.ts
├── providers/            # AuthContext, AuthProvider, useAuth
└── types/                # graph.ts, series.ts, revision.ts, settings.ts — mirror
                           # spoilerless/app/domain/*.py
```

#### Key Components

- **`GraphCanvas.tsx`** — wraps `react-cytoscapejs`. It attempts to register `cytoscape-cose-bilkent` at module load and uses it only when registration succeeds; registration failure selects built-in `cose`. Tapping a node highlights its closed neighborhood and dims the rest. A changed graph normally triggers layout, but layout is deliberately skipped while external focus or a newly-created-element reveal is active so refresh does not destroy zoom/pan or race the reveal fit.
- **`graphElements.ts`** — pure function mapping the backend `GraphResponse` to Cytoscape `ElementDefinition[]`. It performs **no** re-filtering by `visible_from_order` — the backend has already applied the spoiler filter, and the frontend trusts it completely.
- **`graphStylesheet.ts`** — maps node types to shapes (Character → ellipse, Event/Location → round-rectangle, Organization → diamond, Episode → tag, Series → star, UserNote → dashed round-rectangle) and origin to border style (canonical = solid, candidate/user = dashed).
- **`useWatchProgress.ts`** — watch-progress state machine with a `confirmedOrder` (the actual spoiler boundary) and a `pendingChange` (an unconfirmed jump that triggers a confirmation modal). The backend is authoritative: `sessionStorage` is used only as a loading-state cache, and on mount the hook reconciles the hydrated value against `GET /api/series/{id}/progress`, overriding it with the server record. `confirmChange()` awaits the `updateProgress()` backend write before committing local state (optimistically committing on transient network failure); hydrates from `sessionStorage` on mount so a page refresh never re-prompts.
- **`AuthProvider.tsx`** — on mount calls `GET /api/auth/me` to silently restore a session from the cookie; any auth error resolves to an `unauthenticated` state rather than surfacing an error banner.
- **`App.tsx` / `AppShell`** — a state-driven shell with **no router**: `view` is a `useState<'graph' | 'timeline' | 'settings'>('graph')` union, so the graph workspace, the timeline, and the settings page are plain state switches (entering settings unmounts the graph view, including the chat sheet). App orchestrates series selection → episode list loading → watch-progress state → graph fetching, wires `NodeSearch`/`CommandPalette` selections into the existing `graphFocus` path, and registers the `mod+k`/`/` hotkeys via `useHotkey`. Edge routing is intentionally three-way: claim-backed edges and claim-less `origin: "user"` edges open `DetailPanel`; only claim-less non-user edges open `StructuralEdgeCard`. Consequently, `claim_id: null` alone is not a structural-edge discriminator.
- **`NodeSearch.tsx`** — floating search bar over the canvas (FEAT-01/FEAT-07, plan 09-09); a mode `ToggleGroup` switches between node search and grouped notes & claims search. Both run payload-local through `lib/searchIndex.ts` — zero-dep substring matching, with fuse.js explicitly excluded. Selection reuses the existing `onSelect` → `DetailPanel` / `graphFocus` path — never a second selection mechanism.
- **`PathFinder.tsx`** — two-node selection mode (FEAT-06, plan 09-11) that POSTs `/api/series/{id}/graph/path` via `frontend/src/api/graph.ts` and renders the returned hop chain over the canvas.
- **`GraphControls.tsx` / `GraphLegend.tsx`** — zoom/fit/reset controls and a collapsible legend derived from `relationshipStyles.ts`'s edge-color families.
- **`CommandPalette.tsx`** — the ⌘K palette (FEAT-08, plan 09-09): a dialog overlay grouping "Jump to node" / "Switch episode" / "Actions". Node rows share `searchIndex` with `NodeSearch`; episode rows route through the `onRequestChange` prop (PROB-31 semantics — locked episodes open the unlock dialog, never a silent no-op); action rows switch views (timeline/settings/dashboard) and trigger the export seam.
- **`TimelineView.tsx` / `SeriesDashboard.tsx`** — the FEAT-02 timeline (full-canvas chronological list of visible `Event` nodes rendered from the already boundary-filtered graph payload, via `TimelineEventRow`) and the FEAT-04 series dashboard (episode-overview dialog).
- **`useHotkey.ts`** — global keyboard-shortcut hook (FEAT-08): one `window` `keydown` listener per combo (`mod+k`, `/`, `escape`) with cleanup and a ref-held handler; `{ skipWhenInputFocused: true }` stops `/` from hijacking typing.
- **`searchIndex.ts`** (`lib/`) — the single zero-dependency substring search implementation behind node search, notes & claims search, and the palette; a pure function over payloads the frontend has already fetched (and the backend has already boundary-filtered).

#### Vite Configuration

The dev server proxies `/api` requests to `http://127.0.0.1:8000`, avoiding CORS issues in local development.

---

### 4.2 API Layer (FastAPI)

**Location:** `spoilerless/app/api/`

Ten route modules registering **46 HTTP operations** (including `GET /health` in `main.py`) across roughly 34 unique path templates.

#### Route Inventory

| Module | Base path | Purpose |
|---|---|---|
| `series.py` | `/api/series` | List/get series, list episodes (no spoiler filter — metadata is public) |
| `graph.py` | `/api/series/{series_id}/graph`, `/graph/path`, `/export` | Spoiler-safe graph read (the critical read path), shortest visible path, Markdown export |
| `user_content.py` | `/api/series/{series_id}/notes`, `/custom-nodes`, `/custom-relationships` | CRUD for user notes, custom nodes, custom relationships |
| `revisions.py` | `/api/series/{series_id}/revisions` | List/get revisions, revert to a revision |
| `progress.py` | `/api/series/{series_id}/progress` | Read/persist a user's watch-progress boundary |
| `chat.py` | `/api/series/{series_id}/chat/sessions` | Chat session CRUD, non-streaming and streaming (SSE) chat turns |
| `change_set.py` | `/api/series/{series_id}/change-sets` | Propose / confirm / reject / revert a graph mutation |
| `candidates.py` | `/api/series/{series_id}/candidates` | Ingest, list, edit, approve, reject candidate claims |
| `auth.py` | `/api/auth` | Google Sign-In, current-user lookup, logout |
| `settings.py` | `/api/settings/llm` | Read/update the configurable LLM provider settings |
| `main.py` | `/health` | Service + database health check |

#### Architecture Pattern

Route modules consistently use FastAPI `APIRouter`s and Pydantic request/response models, but dependency and data-access patterns vary: most inject services or repositories, `user_content.py` constructs its repository inside handlers, and `candidates.py`/`revisions.py` include direct transaction or data-access logic.

#### Rate Limiting and Admin Gating

Three route groups carry an optional `RateLimiter` dependency (`spoilerless/app/services/rate_limit.py`; see [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache)): `POST /api/auth/google` (10/5min per IP), chat message send (20/min per user), and every `user_content.py` write route (30/min per user, falling back to IP). A separate, unrelated gate — `RequireAdminDependency` (see [7.13](#713-role-based-access-control-admin-role)) — requires the `admin` role on `candidates.py`'s approve/reject/edit routes, `change_set.py`'s confirm route, and both `settings.py` routes; propose/reject/revert on ChangeSets and ingest/list/get on candidates are intentionally not admin-gated.

#### Graph Route — The Critical Read Path

`GET /api/series/{series_id}/graph?visible_until_order=N` is the most architecturally significant endpoint. It validates the series exists, resolves the boundary against a persisted episode order, checks the Redis cache-aside layer (`spoilerless/app/cache/graph_cache.py`) keyed on `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`, and on a miss delegates to `GraphService.fetch_graph()` (which runs seven Cypher queries concurrently) before writing the result back to the cache with a 300-second TTL. It returns a closed-form `GraphResponse` containing every visible node, edge, claim, source, and evidence fragment. Caching is disabled (`get_cached_graph`/`set_cached_graph` are no-ops) whenever `REDIS_URL` is empty or Redis errors — the route always falls through to Neo4j rather than failing the request.

The locked operation inventory (method/path templates and response schemas) is maintained separately in [`docs/frontend-api-contract.md`](./frontend-api-contract.md); the OpenAPI spec generated by `spoilerless.app.main:app` is authoritative.

Two sibling routes added in plan 09-11 reuse the same spoiler-safe machinery. `POST /api/series/{series_id}/graph/path` (FEAT-06) finds the shortest visible path between two entities by executing the allowlisted `find_path` retrieval tool (the request's `max_hops` is clamped to the server ceiling `MAX_PATH_HOPS = 4`). `GET /api/series/{series_id}/export` (FEAT-05, D-11) returns the visible graph — or a single target node and its claims — rendered as Markdown (`text/markdown` with a `Content-Disposition: attachment` filename), assembled from the same `GraphService.fetch_graph()` response rather than a second filter implementation. Both resolve the effective boundary through the same `_resolve_effective_boundary` block the graph GET uses (anonymous readers fixed at order 1, authenticated readers clamped to persisted progress), so a client can never widen the spoiler window through either route.

---

### 4.3 Service Layer

**Location:** `spoilerless/app/services/`

- **`GraphService`** (`graph.py`) — orchestrates the spoiler-safe graph read. `fetch_graph()` runs 7 Cypher queries concurrently via `asyncio.gather()`: series metadata, visible nodes, structural edges, visible claims, visible user-authored relationships, sources, and evidence. Each visible claim is projected into a `GraphEdge` (subject → object, typed by predicate, carrying `claim_id`).
- **`SeriesService`** (`series.py`) — thin wrapper: lists series, gets one series, lists episodes. No spoiler filtering — episode metadata is not spoilery.
- **`AuthService`** (`auth.py`) — verifies Google ID tokens via an injectable `ProductionGoogleVerifier`, upserts users by `google_sub`, and manages session creation/retrieval/refresh/revocation. Session tokens are SHA-256 hashed before storage; raw tokens are never persisted.
- **`ProgressService`** (`progress.py`) — resolves the persisted watch-progress boundary for a user + series from the graph pattern `(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)-[:FOR_SERIES]->(:Series)`. `POST /progress` accepts a client-selected positive `visible_until_order` and persists it without checking for a matching `Episode`; `resolve()` raises `ProgressNotFoundError` when no record exists. `GET /progress` maps that absence to `404`, retrieval fails closed, and chat message paths separately create an order-1 record. Decreasing progress is allowed and hides (never deletes) future-boundary chat messages.
- **`ChatService`** (`chat.py`) — owns the GraphRAG-lite turn lifecycle: resolve boundary → load spoiler-filtered history → run the retrieval pipeline → stream the grounded answer back over SSE. Persists every `ChatMessage` with a `visible_until_order_snapshot` equal to the boundary resolved at turn time.
- **`ChangeSetService`** (`change_set.py`) — Stage 1 **propose** validates a typed operation list against the ontology and the resolved boundary, then persists an `awaiting_confirmation` ChangeSet draft and its linking relationships without mutating target graph content. Stage 2 **confirm/apply** applies the validated operations in a single Neo4j transaction, prevents replay by returning the stored result when the ChangeSet status is already `applied`, and logs a `Revision` in the same transaction; the random `idempotency_key` is generated only after mutation and is not checked for replay detection. Stage 3 **revert** restores pre-apply state for create-shaped ChangeSets.
- **`SettingsService`** (`settings.py`) — resolves the effective LLM configuration (stored graph value wins, `LLM_*` env settings are the fallback) and masks the API key on read.

`spoilerless/app/services/rate_limit.py` is not a class-per-feature service in this same sense — it defines the `RateLimiter` FastAPI dependency and the three module-level route-group instances described in [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache).

---

### 4.4 Repository & Database Layer

**Location:** `spoilerless/app/repository/`, `spoilerless/app/graph/`

- **`Neo4jDatabase`** (`graph/database.py`) — lazy-initialized async Neo4j driver with no import-time side effects; `open()`/`close()` lifecycle managed by the FastAPI `lifespan` context; `execute_query()` for retryable read/write Cypher returning `list[dict]`; `execute_write()` for managed-transaction writes; `verify_connection()` for the health check.
- **`UserRepository`** (`repository/user.py`) — `upsert()` (MERGE on `google_sub`), `get_by_id()`. Users are stored as `(:AppUser)` nodes.
- **`SessionRepository`** (`repository/session.py`) — a `SessionRepository` protocol with two implementations: `Neo4jSessionRepository` (the default, wired directly into `main.py`'s lifespan) persists sessions as `(:Session)` nodes linked via `(:AppUser)-[:HAS_SESSION]->(:Session)`, with uniqueness constraints on `id` and `token_hash` and an index on `expires_at` (created by the seed pipeline); `InMemorySessionRepository` is a plain-dictionary store with no synchronization, suitable only for single-process development and tests. Tokens are `secrets.token_urlsafe(48)`; only the SHA-256 hash is ever persisted; expired/revoked sessions are rejected lazily at read time (a periodic `DETACH DELETE` cleanup task is a documented TODO).
- **`UserContentRepository`** (`repository/user_content.py`) — manages notes, custom nodes, and custom relationships. Visibility is **derived from the target entity** (notes inherit the target's `visible_from_order`; custom relationships use `MAX(source, target, episode)`). It validates ID namespacing (`user-note:`, `user-node:`, `user-rel:` prefixes) and mutation queries gate on `origin = 'user'`, but these routes do not bind an authenticated owner ID, so content is not isolated per user. Deleting a custom node with attached notes/claims returns `409`.
- **`ChangeSetRepository`**, **`ChatRepository`**, **`SettingsRepository`** — the corresponding data-access layers for the ChangeSet, chat, and settings subsystems described in [7.9](#79-changeset-two-stage-mutation-flow), [7.8](#78-graphrag-lite-chat-pipeline), and [7.11](#711-settings-system-user-configurable-llm-provider).

A separate operator script, `spoilerless/scripts/zombie_sweep.py` (PROB-22/#46), sweeps orphaned `(:AppUser)` rows and stale `(:Session)` nodes — dry-run-first by default (`python -m spoilerless.scripts.zombie_sweep --dry-run` counts; `--execute` deletes).

---

### 4.5 Neo4j Graph Database

**Location:** Docker Compose, `spoilerless/app/graph/seed.py`

#### Container

```yaml
services:
  neo4j:
    image: neo4j:2026-community
    ports: ["7474:7474", "7687:7687"]
    volumes: [neo4j_data, neo4j_logs, neo4j_import, neo4j_plugins]
```

#### Node Labels

| Group | Labels |
|---|---|
| Structural | `Series`, `Season`, `Episode`, `Scene` |
| Narrative | `Character`, `Location`, `Organization`, `Object`, `Event` |
| Knowledge | `Claim`, `Source`, `EvidenceFragment` |
| User | `UserNote` |
| System | `Revision`, `AppUser`, `Session`, `UserSeriesProgress`, `ChatSession`, `ChangeSet`, `ChatMessage`, `AppSetting` |

#### Relationship Types

| Group | Types |
|---|---|
| Structural | `PART_OF`, `PRECEDES`, `OCCURRED_IN`, `LOCATED_IN` |
| Participation | `PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED` |
| Character | `KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS` |
| Provenance | `SUPPORTED_BY`, `CONTRADICTED_BY`, `DERIVED_FROM`, `REFERS_TO` |
| Revision | `CORRECTS`, `SUPERSEDES`, `REVERTS_TO` |
| System/application | `HAS_SESSION`, `HAS_PROGRESS`, `FOR_SERIES`, `HAS_CHAT_SESSION`, `IN_SERIES`, `HAS_MESSAGE`, `PROPOSED_CHANGE_SET`, `FOR_SESSION` |

#### Constraints & Indexes

Created idempotently by `setup_database()`: `id` uniqueness constraints for the 12 labels in `seed.py`'s `NODE_LABELS` plus `AppUser` and `Session` (with additional `google_sub`/`token_hash` constraints); `visible_from_order` indexes for those 12 seed labels only; selected `series_id` indexes for episode/content/revision labels plus separate progress/chat lookup indexes; a composite index on `UserNote(series_id, target_type, target_id)`; and an index on `Episode.episode_order`. `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`, and `AppSetting` do not receive universal `id`, visibility, and per-label `series_id` indexes.

> Property existence constraints require Neo4j Enterprise and are intentionally omitted. Null visibility is prevented through Pydantic validation, service-layer guards, and a post-seed integrity audit.

#### Seed Pipeline

The `setup_database()` pipeline (invoked via `uv run spoilerless-setup`, registered in `pyproject.toml` as the `spoilerless-setup` script) loads seed JSON from `data/dexter/`, validates it against the ontology (node types, relationship types, claim types/statuses/confidence levels, ID uniqueness, evidence completeness), creates constraints and indexes, upserts all nodes via `MERGE`, creates structural and provenance relationships, and runs a visibility integrity audit.

After seeding, `spoilerless/app/graph/setup.py`'s `_check_visibility_schema()` (PROB-20/#44) verifies that every seeded story node under `series_dexter` — `Character`, `Event`, `Location`, `Organization`, `Object`, `Claim`, `EvidenceFragment`, `Source` — carries a non-null `visible_from_order`; any null raises a `SCHEMA DRIFT` error and the setup exits 1, so a stale live database can never silently hide the missing visibility gate again (a live reseed remains an operator-gated step).

---

## 5. Key Abstractions

| Abstraction | Location | Purpose |
|---|---|---|
| `visible_from_order` filtering | `spoilerless/app/spoiler/filter.py` | The universal Cypher `WHERE` predicate applied to every story-sensitive entity; the system's single most important invariant |
| `Neo4jDatabase` | `spoilerless/app/graph/database.py` | Central async driver abstraction; all Cypher execution flows through `execute_query()`/`execute_write()` |
| `Ontology` | `spoilerless/app/graph/ontology.py` | Loads and validates the versioned YAML type system; exposes `require_node_type()`, `require_relationship_type()`, `require_claim_type()`, and the user-safe type subsets |
| `Claim` domain model | `spoilerless/app/domain/graph.py` | The atomic knowledge-representation unit — subject/predicate/object plus type, status, confidence, and provenance |
| `origin` enum | shared across `domain/` modules | Three-way `StrEnum` (`canonical` / `candidate` / `user`) distinguishing seed data, extracted-but-unreviewed data, and user-created data |
| `LLMProvider` protocol | `spoilerless/app/llm/provider.py` | Provider-agnostic streaming interface. Two concrete implementations are available: `OpenAICompatibleProvider` posts to `/chat/completions`; `GeminiProvider` translates messages/tools to Gemini content/function parts and posts to the `streamGenerateContent` action with SSE. Gemini's REST family uses `generateContent`/`streamGenerateContent` actions, not a chat-completions path. Availability does not imply either provider is active: `get_llm_provider()` selects the effective stored-over-env provider per request and rejects disabled/incomplete configuration. |
| `RetrievalPipeline` | `spoilerless/app/retrieval/pipeline.py` | Orchestrates allowlisted tool calls, context assembly, and citation validation for the GraphRAG-lite chat |
| `ChangeSetService` | `spoilerless/app/services/change_set.py` | The typed, two-stage (propose/confirm) protocol that is the only path through which the graph can be mutated by chat-driven writes |
| `RevisionRepository.log_revision` | `spoilerless/app/revisions/__init__.py` (used across services and repositories) | Shared pattern for writing an append-only before/after audit record in the same transaction as any content mutation |
| `require_admin` / `RequireAdminDependency` | `spoilerless/app/api/deps.py` | FastAPI dependency gate requiring `role == "admin"` (derived server-side from `ADMIN_EMAILS` at login); rejects with `403 FORBIDDEN` otherwise |
| `get_redis()` | `spoilerless/app/cache/redis_client.py` | The single shared, `lru_cache`-decorated `redis.asyncio` client; every Redis-backed feature imports it rather than constructing its own connection |
| `RateLimiter` | `spoilerless/app/services/rate_limit.py` | FastAPI dependency enforcing a per-window request count via a Redis-backed `pyrate-limiter` bucket; a no-op until `init_rate_limiter()` binds it (or when `REDIS_URL` is empty) |

---

## 6. Data Flow Examples

### Flow 1 — User opens the app (read path)

```
User selects "Dexter" series
  │
  ▼
App.tsx sets selectedSeriesId = "series_dexter"
  │
  ├──► useEpisodes("series_dexter") → GET /api/series/{id}/episodes
  │      → SeriesService.list_episodes() → Neo4j MATCH (Episode)-[:PART_OF]->(Series)
  │
  └──► useGraph("series_dexter", visibleUntilOrder=1)
         → GET /api/series/{id}/graph?visible_until_order=1
         → GraphService.fetch_graph("series_dexter", 1)
              (7 concurrent Cypher queries via asyncio.gather)
              1. SERIES_QUERY            → series metadata
              2. NODES_QUERY             → nodes with visible_from_order <= 1
              3. STRUCTURAL_EDGES_QUERY  → structural edges with visible_from_order <= 1
              4. VISIBLE_CLAIMS_QUERY    → claims visible at episode 1
              5. VISIBLE_USER_RELATIONSHIPS_QUERY → user relationships visible at 1
              6. SOURCES_QUERY           → sources referenced by visible claims
              7. EVIDENCE_QUERY          → evidence backing visible claims
         → GraphResponse assembled (claims projected to edges)
         → graphToElements() → Cytoscape ElementDefinition[]
         → GraphCanvas renders with the cose-bilkent layout
```

### Flow 2 — User advances watch progress

```
User selects "S01E03" in EpisodeSelector
  → useWatchProgress.requestChange("series_dexter", 3)  (direction: forward)
  → ConfirmAdvanceModal opens (warning: spoilers up to S01E03)
      confirm → confirmChange() → POST /api/series/{id}/progress (backend write,
             server-authoritative) → sessionStorage cache updated
             → useGraph re-fetches with visible_until_order=3 → Flow 1 repeats
      cancel  → cancelChange() discards the pending change
```

### Flow 3 — User creates a note

```
POST /api/series/{series_id}/notes { target_type, target_id, content }
  → UserContentRepository.create_note()
      validates the target exists in the same series and has visible_from_order >= 1
      generates id = "user-note:{uuid4}"
      Neo4j: MATCH target WHERE target.visible_from_order >= 1 (no request boundary is accepted or resolved)
             CREATE (:UserNote)-[:REFERS_TO {origin:'user'}]->(target)
  → Response: NoteResponse with origin="user", visible_from_order inherited from target
```

---

## 7. Cross-Cutting Concerns

### 7.1 Spoiler-Aware Data Flow

This is the **core architectural invariant** of the system. Spoiler filtering happens entirely on the backend — the frontend never receives data it would need to hide.

Story-sensitive content nodes, content relationships, and claims carry a `visible_from_order` integer: the earliest episode order at which the entity stops being a spoiler. System records and links such as `AppUser`, `Session`, `AppSetting`, `HAS_SESSION`, and progress/chat ownership relationships do not universally carry it. The `visible_until_order` query parameter represents how far the user has watched. Relevant spoiler-aware Cypher queries apply:

```cypher
WHERE entity.visible_from_order <= $visible_until_order
```

**Fail-closed design:** explicit graph and user-content read boundaries are positive and validated against a persisted episode before those queries run; malformed, zero, negative, or non-matching values return `422`. Persisted progress is a separate path: `POST /progress` stores any positive integer and `ProgressService.resolve()` returns it without an `Episode` lookup, so GraphRAG uses that stored integer directly. Every entity in a query chain (claim → subject → object → evidence → source) must individually satisfy the visibility filter. Direct reads of hidden resources (e.g. `GET /notes/{id}` for a future note) return an indistinguishable `404`.

Claims can additionally carry `valid_from_order`/`valid_until_order` for time-bounded facts (e.g. a temporary allegiance):

```cypher
AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
```

`spoilerless/app/spoiler/filter.py` holds the core graph-read spoiler queries as raw, parameterized Python string constants. Additional visibility-gated Cypher lives in `graph/candidates.py`, `graph/change_set.py`, `graph/chat.py`, `retrieval/tools.py`, `repository/user_content.py`, and `api/revisions.py`.

### 7.2 The Claim Model

Claims are the core knowledge-representation unit — a statement about the narrative world:

```
Claim {
  id, label, subject_id, predicate, object_id,
  claim_type: explicit_fact | observed_event | inferred_state |
              external_interpretation | user_authored,
  status: candidate | corroborated | canonical | disputed | rejected,
  confidence_level: low | medium | high | verified,
  relationship_effect: float,
  visible_from_order, valid_from_order, valid_until_order,
  source_id, evidence_ids, origin: canonical | candidate | user
}
```

Every automatic claim requires at least one `EvidenceFragment` (`SUPPORTED_BY`) and a `Source`, but the two ingest paths use different source-link topologies: seeded claims create `Claim-[:REFERS_TO]->Source` and store `EvidenceFragment.source_id` without an evidence-to-source relationship, while candidate ingest creates `EvidenceFragment-[:REFERS_TO]->Source` without a claim-to-source relationship. Evidence carries the actual text excerpt, locator, and content hash. User-authored relationships are stored as `Claim` nodes with `claim_type: 'user_authored'`, `origin: 'user'`, and an `id` prefixed `user-rel:` — they need no evidence or source, and are surfaced via `VISIBLE_USER_RELATIONSHIPS_QUERY` rather than `VISIBLE_CLAIMS_QUERY`.

### 7.3 Ontology System

**Location:** `ontology/` — `node_types.yaml`, `relation_types.yaml`, `claim_types.yaml`, each carrying an `ontology_version: "0.1"` declaration. `spoilerless/app/graph/ontology.py`'s `load_ontology()` reads all three files, validates the version, and produces an immutable `Ontology` dataclass with `require_node_type()`, `require_relationship_type()`, `require_claim_type()`, and `user_safe_node_types`/`user_safe_relationship_types` (the subset of types end users are allowed to create). A version mismatch raises on load.

### 7.4 Origin System

`origin` is a `StrEnum` with exactly three values: `canonical` (curated seed data — the authoritative ground truth), `candidate` (automatically extracted or suggested, not yet reviewed), and `user` (user-created content). Canonical nodes render with solid borders in the graph; candidate/user nodes render with dashed borders. This distinction is never collapsed into a boolean, and the frontend contract explicitly forbids branching on a `'curated'` string — the wire value is `'canonical'`.

### 7.5 Authentication & Sessions

1. The frontend initiates Google Sign-In via the Google Identity Services library and receives an ID token (JWT).
2. The token is sent to `POST /api/auth/google`.
3. The backend verifies signature, issuer (`accounts.google.com`), audience (`GOOGLE_CLIENT_ID`), and expiration.
4. If `ALLOWED_EMAILS` is non-empty, the verified email (case-insensitively) must be a member or the request is rejected with `403 AUTH_EMAIL_NOT_ALLOWED`; an empty allowlist permits any verified Google account.
5. `role` is derived server-side from `ADMIN_EMAILS` membership (`"admin"` if the verified email matches, `"user"` otherwise) — never read from the request — and the user record is upserted in Neo4j keyed on Google's `sub` claim, re-syncing `role` on every login so removing an email from `ADMIN_EMAILS` demotes that user on their next sign-in.
6. A session is created with a SHA-256-hashed token (persisted as a `(:Session)` node by `Neo4jSessionRepository`); an HttpOnly cookie is set on the response with `SameSite` taken from `SESSION_COOKIE_SAMESITE` (default `lax`, tunable per deployment).

`GET /api/auth/me` reads the cookie, validates the session, and refreshes its TTL (default 7 days, `SESSION_TTL_SECONDS`). `POST /api/auth/logout` revokes the session and always returns `204`. `POST /api/auth/google` also carries the `login_rate_limiter` dependency (10 requests / 5 minutes per IP; see [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache)) and the explicit `verify_origin` origin/referer dependency, which rejects a request presenting neither header (fail-closed) as well as a mismatched one with `403 AUTH_ORIGIN_NOT_ALLOWED`; `verify_origin` is attached only to `POST /api/auth/google`, not to logout or the other state-changing routes.

### 7.6 Error Handling

**Location:** `spoilerless/app/core/errors.py`. A structured error envelope used by the API endpoints, except `/health`'s `503` response, which returns the `HealthResponse` fields `status`, `database`, and `service`. Since 09-05 (PROB-09) all codes are canonical **UPPERCASE `SNAKE_CASE`** — the `ERROR_CODES` registry (33 codes) is validated by a Pydantic field validator that rejects unregistered or lowercase codes at startup; OpenAPI contract tests enforce the casing:

```json
{ "detail": { "code": "SERIES_NOT_FOUND", "message": "Series not found." } }
```

| Status | Code | When |
|---|---|---|
| 401 | `AUTH_UNAUTHENTICATED` | No valid session |
| 401 | `AUTH_INVALID_GOOGLE_CREDENTIAL` | Google token verification failed |
| 401 | `AUTH_DISABLED` | Google auth or session TTL not configured |
| 403 | `AUTH_EMAIL_NOT_ALLOWED` | Verified Google email not in a non-empty `ALLOWED_EMAILS` |
| 403 | `AUTH_ORIGIN_NOT_ALLOWED` | `Origin`/`Referer` missing or not in `FRONTEND_ORIGINS` (`POST /api/auth/google` only) |
| 403 | `FORBIDDEN` | `RequireAdminDependency` rejected a non-admin caller |
| 404 | `SERIES_NOT_FOUND` | Series lookup missed |
| 404 | `RESOURCE_NOT_FOUND` | Hidden or absent resource |
| 409 | `RESOURCE_CONFLICT` | Ownership violation or dependency |
| 422 | `INVALID_REQUEST` | Validation failure |
| 422 | `INVALID_VISIBLE_UNTIL_ORDER` | Bad boundary value |
| 429 | `TOO_MANY_REQUESTS` | A `RateLimiter`-gated route exceeded its window (login/chat-send/content-write) |
| 503 | `DATABASE_UNAVAILABLE` | Neo4j unreachable |

`install_database_error_handlers()` and `install_llm_error_handlers()` (installed in `main.py`) register handlers so validation, constraint, connectivity, and LLM-provider errors are translated into this envelope. Database error messages are intentionally generic — never leaking Cypher, connection details, or internals.

Since 09-05 (PROB-17) `main.py` also registers a `_security_headers_middleware` that stamps every response with `Content-Security-Policy` (default-src 'self', GIS script origins allowed), `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`; CORS is narrowed to an explicit method/header list (no wildcard with credentials).

### 7.7 Revision History

**Location:** `spoilerless/app/revisions/`. `Revision` is an append-only Neo4j `(:Revision)` node model: no revision is ever deleted or mutated in place. Every user-content mutation (note/custom-node/custom-relationship create, update, delete) auto-creates a `Revision` capturing before/after JSON snapshots in the **same Neo4j transaction** as the mutation. Reverting restores the captured state by creating a new `Reverted` revision, so history is never destroyed.

| Route | Method | Purpose |
|---|---|---|
| `/api/series/{series_id}/revisions` | GET | List visible revisions, most-recent-first, with optional `resource_type`/`resource_id` filters |
| `/api/series/{series_id}/revisions/{revision_id}` | GET | Get one revision (hidden revisions return 404) |
| `/api/series/{series_id}/revisions/{revision_id}/revert` | POST | Restore a resource to the state captured in the revision |

The frontend's History tab (part of `DetailPanel`) renders color-coded action badges (Created/Updated/Deleted/Reverted), diff-summary chips, and a one-shot revert flow with a confirmation dialog. The revert button appears only on `Updated` and `Deleted` revisions.

ChangeSet applies extend this same invariant: confirming a ChangeSet logs a single `Revision` in the same transaction it applies in (the ChangeSet response carries `revision_id`), and reverting an applied ChangeSet is itself a `Reverted` revision — one coherent audit chain across every mutation surface in the system.

### 7.8 GraphRAG-Lite Chat Pipeline

**Location:** `spoilerless/app/retrieval/` (`pipeline.py`, `tools.py`), `spoilerless/app/llm/` (`provider.py`, `system_prompt.py`), `spoilerless/app/services/chat.py`. Disabled by default (`LLM_ENABLED=false`); enabled by configuring an OpenAI-compatible or Gemini-compatible provider via environment variables or the Settings UI (see [7.11](#711-settings-system-user-configurable-llm-provider)).

The chat feature is **GraphRAG-lite**: the LLM answers questions by calling a small allowlisted set of retrieval tools against the spoiler-filtered graph, and any citations it supplies are validated against what was actually retrieved. A non-empty model answer with no citations can pass unchanged; fallback replacement occurs when supplied citations are all stripped or the content is empty. The model never receives the raw graph — only the filtered, bounded context the pipeline assembles.

```
Browser (ChatPanel, mounted by the independent right-side ChatSheet)
  │ 1. User submits a question → POST .../messages/stream (SSE, credentials: include)
  ▼
FastAPI router: spoilerless/app/api/chat.py
  │ 2. require_current_user resolves AppUser from the session cookie
  ▼
ChatService (spoilerless/app/services/chat.py)
  │ 3. ProgressService.resolve(user_id, series_id) → visible_until_order
  │ 4. ChatRepository loads recent, currently-visible ChatMessages for context
  ▼
RetrievalPipeline (spoilerless/app/retrieval/pipeline.py)
  │ 5. LLMProvider.stream_chat(system_prompt, history, tools=ALLOWLISTED_TOOLS)
  ▼
Retrieval Tools (spoilerless/app/retrieval/tools.py)
  │ 6. The pipeline passes the boundary resolved in step 3 to each tool (never
  │    from model output); tools run parameterized visibility-gated Cypher
  ▼
Neo4j
  │ 7. Filtered rows → context normalization (dedupe, bound size) → back to the
  │    LLMProvider for the final answer, this time without tools
  ▼
Citation Validator (spoilerless/app/retrieval/pipeline.py)
  │ 8. Every cited claim_id/evidence_id/source_id is checked against the actual
  │    retrieved context set — anything not present is stripped
  ▼
ChatService persists the ChatMessage (citations and graph_focus; no
  change_set_id integration) via ChatRepository
  │ 9. Final SSE event: {message, citations, graph_focus, proposed_change_set: null}
  ▼
Browser: MessageBubble renders streamed text; CitationChip "Show in graph" sets
  GraphCanvas's focusedElementIds; ChangeSetCard's Confirm/Reject buttons POST
  to change_set.py's confirm/reject endpoints — a separate request cycle
```

#### Allowlisted retrieval tools

The pipeline exposes exactly **eleven** retrieval tools defined in `spoilerless/app/retrieval/tools.py` — nothing more, and the model can never execute raw Cypher:

1. `search_entities` — keyword search over visible entities
2. `get_entity` — fetch one visible entity by ID
3. `get_neighborhood` — closed neighborhood of a visible entity
4. `find_path` — bounded path search between two visible entities
5. `get_timeline` — chronological visible events
6. `get_character_context` — bounded interpretation pack for one visible Character
7. `get_claims` — visible claims matching filters
8. `get_evidence` — evidence fragments backing visible claims
9. `get_sources` — sources referenced by visible claims
10. `get_current_visible_graph_summary` — aggregate summary of the visible graph
11. `get_user_notes` — the user's own visible notes

Each tool takes only allowlisted, typed parameters (never a free-text Cypher string or an unvalidated ID sourced from model output), re-derives `visible_until_order` from the server-resolved value, and issues parameterized Cypher built the same way `spoiler/filter.py`'s constants are — label/relationship names chosen only from server-side allowlists, values always bound as `$parameters`.

### 7.9 ChangeSet Two-Stage Mutation Flow

**Location:** `spoilerless/app/api/change_set.py`, `spoilerless/app/services/change_set.py`, `spoilerless/app/repository/change_set.py`. The LLM **cannot write to the graph directly**. Typed staged ChangeSet endpoints exist for separately submitted proposals, but the current chat/retrieval pipeline does not create or return them and always emits `proposed_change_set: null`:

```
Stage 1 — PROPOSE (POST /api/series/{series_id}/change-sets, not admin-gated)
  A typed ChangeSet: { summary, operations: [create_node | update_node |
  delete_node | create_relationship | update_relationship |
  delete_relationship | create_claim | update_claim | delete_claim |
  attach_evidence | create_note | update_note | delete_note] }
  ├── Pydantic validates: operation_type is one of 13 literals, extra fields
  │   forbidden, at least one operation, ontology-valid labels/types
  ├── Targets must be visible, same-series, visibility derived server-side
  ├── Direct mutation of canonical/candidate Character or Claim targets is
  │   replaced by a create_note annotation. Other protected target labels
  │   cannot be note targets and fail validation; user-origin targets retain
  │   the requested mutation.
  └── Persists the ChangeSet draft and linking relationships — status: awaiting_confirmation; target graph content is unchanged

Stage 2 — CONFIRM (POST .../confirm, admin-only) | REJECT (POST .../reject)
  Confirm: RequireAdminDependency (403 FORBIDDEN for a non-admin caller) →
  ownership/status check → staleness check (409 CHANGESET_STALE) →
  replay prevented by stored `status == 'applied'` (the post-apply random idempotency key is not checked) → single Neo4j transaction (all-or-nothing)
  → Revision logged in the same transaction → cache/graph_cache.invalidate_series()
  Reject: marks the ChangeSet rejected; no database change; not admin-gated

Stage 3 — REVERT (POST .../revert, applied ChangeSets only, not admin-gated)
  Only create-shaped ChangeSets are revertible; a conflict guard returns 409
  if a later unrelated change touched the created resource; creates a new
  Reverted revision
```

Only Stage 2's confirm step is admin-gated — the reasoning is that confirming is the step that actually applies an AI-proposed mutation to the shared canonical graph, so propose/reject/revert remain open to any authenticated user. The frontend renders a proposed ChangeSet as a preview card (per-operation summary, before/after rows for updates, a destructive banner when deletes are present) with explicit Confirm/Reject controls — the only UI path into the confirm/reject endpoints; a non-admin viewer's Confirm click surfaces the `403 FORBIDDEN` response.

### 7.10 Spoiler-Safety Invariants

1. **The LLM never receives the full unfiltered graph.** Context is assembled exclusively through the eleven allowlisted tools; `assemble_context` (`retrieval/pipeline.py`) dedupes by ID and bounds the result via `Settings.llm_max_context_items` / `Settings.llm_max_context_characters`.
2. **Retrieval applies the persisted progress integer as its spoiler boundary, with incomplete hop coverage in some queries.** The pipeline resolves it once server-side, but `GET_EVIDENCE_QUERY` and `GET_SOURCES_QUERY` do not visibility-gate the matched `Claim`, and `GRAPH_SUMMARY_COUNTS_QUERY` counts claims without gating their subject/object endpoints. The progress update path accepts any positive integer and does not verify that it matches an `Episode.episode_order`.
3. **The LLM never executes arbitrary Cypher.** There is no text-to-Cypher surface; every query is a server-side constant template with `$parameter` bindings.
4. **The LLM cannot directly mutate canonical or candidate content.** ChangeSet validation substitutes a note for protected Character/Claim mutations and rejects protected types that cannot accept notes; it never applies the requested direct mutation.
5. **ChangeSet endpoint writes require typed proposals and explicit confirmation.** `ChangeSetCard` can confirm a supplied proposal before target content is mutated, but the model/chat pipeline currently produces no proposal (`proposed_change_set` is always `null`).
6. **Chat history is spoiler-filtered by the same boundary as the graph.** `ChatMessage` rows carry `visible_until_order_snapshot`; history loading filters `snapshot <= current boundary`.
7. **Lowering progress hides — never deletes — previously generated future-boundary messages.** They re-appear if progress advances again.
8. **All graph content is treated as untrusted prompt data.** User notes, evidence text, and retrieved content are wrapped in strict delimiters with explicit instruction-ignore language in the system prompt.

### 7.11 Settings System (User-Configurable LLM Provider)

**Location:** `spoilerless/app/api/settings.py`, `spoilerless/app/services/settings.py`, `spoilerless/app/repository/settings.py`, `spoilerless/app/domain/settings.py`; `frontend/src/components/settings/SettingsPage.tsx`.

Lets an authenticated user configure the GraphRAG chat agent's LLM provider from the UI instead of only via `.env`. A single `(:AppSetting {key: 'llm'})` node holds the configuration as a JSON-serialized string. `SettingsService.get_llm()` resolves the *effective* configuration field-by-field: the stored graph value wins, the `LLM_*` environment settings are the fallback/bootstrap path.

**API key handling (write-only secret):** `GET /api/settings/llm` never returns the full key — only `api_key_configured: bool` and a masked form. On `PUT`, `null` or `""` keeps the previously stored key; whitespace-only input is truthy and is currently persisted rather than treated as blank. The full key never appears in any response model or log line. Both routes carry `RequireAdminDependency` — only a session whose `role == "admin"` (see [7.13](#713-role-based-access-control-admin-role)) may view or change the shared LLM provider configuration; any other authenticated user gets `403 FORBIDDEN`. The configuration itself remains a single shared global record, not a per-user one.

| Route | Method | Purpose |
|---|---|---|
| `/api/settings/llm` | GET | Effective LLM config, key masked |
| `/api/settings/llm` | PUT | Update provider/key/model/base_url/enabled/system_prompt_language |

Available provider implementations are `openai_compatible` and `gemini`; the configured active provider is resolved per request from a non-empty stored value, then `LLM_PROVIDER` (whose env default is `openai_compatible`). Separately, an omitted `provider` in the PUT request model defaults to `gemini` and is then stored. `enabled: false` makes message-generation endpoints return `503` (`LLM_DISABLED`), while chat session create/list/get/delete remain available; `system_prompt_language` (`english` default, or `turkish`) selects which system prompt variant the agent is given.

### 7.12 Candidate Extraction & Review Workflow

**Location:** `spoilerless/app/api/candidates.py`, `spoilerless/app/graph/candidates.py`, `spoilerless/app/domain/extraction.py`. This is the intake path for a future auto-extraction pipeline — the ingest side is implemented ahead of any actual extractor.

`ExtractionBatchEnvelope` wraps a list of `ExtractionClaim` entries, the payload shape an NLP/extraction process would submit via `POST /api/series/{series_id}/candidates/ingest`. Each claim carries subject/predicate/object, evidence text + locator, source type + locator, and episode context.

Candidate claims, their sources, and their evidence fragments derive deterministic IDs from a SHA-256 hash of their own content (subject:predicate:object:evidence_text:evidence_locator:episode_id for the claim; source locator for the source; evidence_text:evidence_locator:episode_id for the evidence). This makes re-ingesting the same extraction batch a no-op `MERGE` rather than creating duplicates.

**Layering deviation:** `candidates.py` calls `CandidateRepository` directly — there is no `CandidateService` — and approve/reject/edit handlers inline managed-transaction logic, calling `RevisionRepository.log_revision` in the mutation transaction. It is not the only API-layer bypass: `user_content.py` calls `UserContentRepository` directly, `revisions.py` performs direct database/transaction work, and chat session routing constructs `ChatService`, which owns `ChatRepository`, while `chat.py` imports repository exceptions.

```
POST .../candidates/ingest       → origin: candidate, status: candidate (idempotent MERGE); not admin-gated
GET  .../candidates               → list, optional visible_until_order filter; not admin-gated
GET  .../candidates/{id}          → one candidate claim; not admin-gated
PATCH .../candidates/{id}         → edit mutable fields (admin-only)
POST .../candidates/{id}/approve  → status: candidate → canonical (409 if origin isn't candidate) (admin-only)
POST .../candidates/{id}/reject   → status: candidate → rejected (admin-only)
```

`PATCH .../candidates/{id}`, `POST .../approve`, and `POST .../reject` all carry `RequireAdminDependency` — only a session with `role == "admin"` can edit, approve, or reject a candidate claim. Ingest and the two read routes carry no auth dependency at all, unchanged from before. Every approve/reject/edit call logs a `Revision` with before/after snapshots in the same transaction and invalidates the series' cached graph entries (`cache/graph_cache.invalidate_series()`), so candidate review participates in the same append-only audit trail as user-content and ChangeSet mutations.

### 7.13 Role-Based Access Control (Admin Role)

**Location:** `spoilerless/app/api/deps.py` (`require_admin`, `RequireAdminDependency`), `spoilerless/app/services/auth.py` (role derivation at login), `spoilerless/app/repository/user.py` (`role` persisted on the `(:AppUser)` node), `spoilerless/app/domain/auth.py` (`UserPublic.role: Literal["admin", "user"]`).

`role` is a two-value field — `"admin"` or `"user"` — assigned server-side at every login from `ADMIN_EMAILS` membership (a comma-separated, case-insensitive env allowlist), never accepted from the client or derived from any request body. `UserRepository.upsert()` re-syncs `role` on every login (`ON MATCH SET u.role = $role`), so removing an email from `ADMIN_EMAILS` demotes that user's role the next time they sign in — no database migration needed. Pre-migration `AppUser` records without a stored `role` default to `"user"` via `coalesce(u.role, 'user')` in `GET_USER_BY_ID_QUERY` and the `UserPublic` model's `default="user"`.

`require_admin` is a `CurrentUserDependency`-composed FastAPI dependency: it first resolves the authenticated user (`401 AUTH_UNAUTHENTICATED` if no valid session), then checks `user["role"] == "admin"`, raising `403 FORBIDDEN` otherwise. It currently gates exactly five routes: `candidates.py`'s `PATCH .../{id}`, `POST .../approve`, `POST .../reject`; `change_set.py`'s `POST .../confirm`; and both `settings.py` routes (`GET`/`PUT /api/settings/llm`). The rationale is consistent across all five: each is the step that commits AI-proposed or extracted content to the shared canonical graph, or mutates the shared LLM provider configuration, rather than merely reading or drafting.

Ordinary user-content, revision, progress, chat, and ChangeSet-propose/reject/revert routes remain open to any authenticated user — this RBAC layer does not implement per-user ownership or ordinary multi-tenant isolation (see [Normative follow-ups](#normative-follow-ups-planned-not-implemented)); it is a single admin/non-admin distinction layered on top of the existing session-cookie authentication from [7.5](#75-authentication--sessions).

### 7.14 Redis-Backed Rate Limiting and Graph Response Cache

**Location:** `spoilerless/app/cache/redis_client.py`, `spoilerless/app/cache/graph_cache.py`, `spoilerless/app/services/rate_limit.py`. Both features share the one `redis.asyncio` client returned by `get_redis()` (`lru_cache`-decorated, mirroring `core/config.py::get_settings()`) and are gated on a single setting, `REDIS_URL` (an Upstash-style `rediss://` TLS connection string). An empty `REDIS_URL` disables both features as a no-op — local development without Redis runs unthrottled and always queries Neo4j directly — rather than crashing startup or failing requests.

**Rate limiting** (`services/rate_limit.py`) — a `RateLimiter` FastAPI dependency class backed by `pyrate-limiter`'s `RedisBucket` (one atomic Redis-Lua-scripted ZSET per window, correct across multiple concurrently-running backend workers/instances). Three module-level instances gate three route groups:

| Instance | Route(s) | Limit | Window | Identifier |
|---|---|---|---|---|
| `login_rate_limiter` | `POST /api/auth/google` | 10 requests | 300s (5 min) | client IP |
| `chat_send_rate_limiter` | Chat message send (streaming and non-streaming) | 20 requests | 60s | authenticated user id |
| `content_write_rate_limiter` | Every `user_content.py` write route (notes, custom nodes, custom relationships — create/update/delete) | 30 requests | 60s | authenticated user id, falling back to IP (user-content routes gain no ownership dependency until a later phase) |

`rate_limit_identifier()` reads `request.state.user` (stamped by `require_current_user` — see [7.5](#75-authentication--sessions)) when present, else falls back to `request.client.host`. A request over the limit gets `429 TOO_MANY_REQUESTS` via the shared error envelope ([7.6](#76-error-handling)). `init_rate_limiter()` binds the Redis-backed `Limiter` to all three instances once, in `main.py`'s `lifespan()`, immediately after `database.open()`, guarded on non-empty `REDIS_URL`; until bound (or when unbound), every `RateLimiter.__call__()` is a no-op.

**Graph response cache** (`cache/graph_cache.py`) — a cache-aside layer in front of `GET /api/series/{series_id}/graph` only (see [4.2](#42-api-layer-fastapi)). Cache keys are `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}` with a 300-second TTL (`DEFAULT_GRAPH_TTL_SECONDS`); because the effective spoiler boundary is part of the key, a boundary change is always a correct cache miss with no explicit invalidation required. Content-changing routes that mutate a series' graph (`candidates.py`'s approve/reject/edit, `change_set.py`'s confirm, `user_content.py`'s custom-node/custom-relationship create/update) call `invalidate_series(series_id)` after a successful write, which coarsely deletes every cached entry for that series via `SCAN`+`DELETE` rather than attempting to re-derive which exact `(boundary, user)` combinations the write affected. Any Redis error on read or write is swallowed and treated as a cache miss/no-op — caching is a performance layer, never a hard dependency, and a Redis outage degrades every graph read back to always querying Neo4j directly.

---

## 8. Key Design Decisions

**D-01 — Spoiler filtering at the database layer.** Filtering happens in visibility-gated Cypher before retrieval. Core graph reads live in `spoiler/filter.py`; candidate, ChangeSet, chat, retrieval-tool, user-content, and revision modules also define spoiler-aware queries. This avoids transferring and then discarding hidden result sets.

**D-02 — Visibility boundaries on story-sensitive content.** Content nodes, content relationships, and claims carry `visible_from_order`; system/auth/session/progress/chat/ChangeSet/settings records do not universally carry it. Claims additionally carry optional `valid_from_order`/`valid_until_order` for time-bounded facts.

**D-03 — Claims projected as edges.** Visible canonical/candidate claims that survive the full claim/subject/object/evidence/source filters become `GraphEdge`s carrying `claim_id`. User-authored relationship Claims are emitted by a separate query as edge-only records with `claim_id: null`, but only when both endpoints satisfy the same series and visibility constraints used by node filtering. Structural edges also carry `claim_id: null`. The frontend therefore combines `claim_id` with `origin` when routing an edge.

**D-04 — Seven concurrent queries for the graph read.** `GraphService.fetch_graph()` runs seven independent Cypher queries via `asyncio.gather()` rather than one giant query, minimizing latency without complex query engineering.

**D-05 — Backend-only visibility authority.** The frontend never checks `visible_from_order`; `graphToElements()` maps all received data without filtering. If a node is in the response, it is safe to show.

**D-06 — Server-authoritative watch progress with `sessionStorage` as a loading-state cache.** The spoiler boundary is persisted in Neo4j (`(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)`); `sessionStorage` only caches the last-known value across refreshes and is reconciled against `GET /api/series/{id}/progress` on mount. `confirmChange()` awaits the backend write before committing local state (optimistic commit on transient failure), and the `pendingChange` → `confirmChange` workflow ensures deliberate forward jumps.

**D-07 — Asynchronous graph fetching with retry.** `useGraph` exposes an explicit `refetch()` via a `retryToken` counter distinct from the `seriesId`/`visibleUntilOrder` dependency, so a transient error gets a Retry button that re-issues the same request.

**D-08 — Immutable PATCH contracts.** PATCH routes accept only the mutable field (`content` for notes, `label` for custom nodes, `predicate` for custom relationships) — endpoints, origin, visibility, and ownership are immutable.

**D-09 — Visibility derived from entity, not client.** For creates, `visible_from_order` is derived from the referenced target entity, never accepted from the client — a note attached to a season-5 character is only visible to users who've reached season 5, regardless of what the client submits.

**D-10 — Admin role gates canonical-graph commits, not ordinary reads/writes.** `role` is a two-value, server-derived (`ADMIN_EMAILS`) field re-synced on every login. Only the routes that actually commit externally-sourced content to the shared canonical graph or mutate shared configuration — candidate approve/reject/edit, ChangeSet confirm, and both LLM settings routes — require it; propose/reject/revert on ChangeSets and ordinary user-content CRUD remain open to any authenticated user (see [7.13](#713-role-based-access-control-admin-role)).

**D-11 — Redis is optional infrastructure, never a hard dependency.** Rate limiting and the graph response cache both share one client, gate on a single `REDIS_URL` setting, and fail open (rate limiting) or fall through to Neo4j (caching) on any Redis error or absent configuration — a Redis outage degrades performance/throughput protection but never produces a request failure (see [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache)).

---

## 9. Future Extensibility Points

- **Additional retrieval tools** — new allowlisted functions in `spoilerless/app/retrieval/tools.py`, each following the fail-closed visibility pattern.
- **Additional LLM providers** — new implementations of the `LLMProvider` protocol in `spoilerless/app/llm/provider.py` (`gemini` and `openai_compatible` ship today).
- **Richer grounding** — e.g. multi-hop path explanations surfaced through the existing citation model.
- **Auto-extraction pipeline** — NLP-driven claim/relationship extraction feeding the existing candidate-review workflow ([7.12](#712-candidate-extraction--review-workflow)), reusing the `confidence_level` enum and `candidate → corroborated → canonical` status progression.
- **Multi-series support** — most story-content queries are parameterized by `series_id`, while global nodes such as `AppUser`, `Session`, and `AppSetting` are not series-scoped. The seed loader currently hardcodes `data/dexter/metadata`, `data/dexter/seed`, and fixed filenames, so adding a series requires generalizing or changing the seed-loading code as well as adding data (and updating the ontology if new types are needed).
- **Session cleanup** — `Neo4jSessionRepository` is already the default persistent store; the documented TODO is a periodic background task that `DETACH DELETE`s expired/revoked `(:Session)` nodes (they are currently only rejected lazily at read time).
- **Real-time collaboration** — a future extension could add WebSocket routes and content-change notifications; neither is implemented today, and current user-content records are not bound to an `AppUser` owner ID.
- **Ontology evolution** — the versioned ontology system supports declared additions, but unknown node, relationship, claim, status, or confidence types raise `OntologyValidationError` and fail seed validation rather than being skipped.

### Normative follow-ups (planned, not implemented)

- **Close retrieval-hop gaps:** every retrieval query should visibility-gate the matched Claim and every subject/object/source/evidence hop before returning rows or aggregate counts. The gaps listed in [7.10](#710-spoiler-safety-invariants) remain current implementation debt, not approved exceptions to the spoiler-safety requirement.
- **Make ownership and CSRF explicit (partially addressed):** candidate approve/reject/edit and ChangeSet confirm now require the `admin` role ([7.13](#713-role-based-access-control-admin-role)), but ordinary user-content and revision mutations still carry no authenticated owner binding — any signed-in user can edit/delete any other user's notes and custom content. A general server-side CSRF signal for cookie-authenticated state-changing routes (beyond `verify_origin` on `POST /api/auth/google`) also remains unimplemented; CORS alone is not that protection.
- **Unify candidate boundaries:** candidate list and direct-read routes should eventually resolve the same server-authoritative watch boundary as other story-sensitive reads; their optional/missing boundary behavior is a known exception today.
- **Scope shared settings (partially addressed):** `GET`/`PUT /api/settings/llm` are now admin-gated ([7.11](#711-settings-system-user-configurable-llm-provider)), closing the "any authenticated user" exposure, but the underlying `AppSetting` record is still a single shared global configuration rather than per-user, and the existing http(s)-scheme check on `base_url` does not prevent an admin from redirecting the shared provider to an attacker-controlled or private host.

---

## 10. Appendices

### A. Path Conventions

| Concept | Backend Path | Frontend Path |
|---|---|---|
| API routes | `spoilerless/app/api/` | `frontend/src/api/` |
| Domain models | `spoilerless/app/domain/` | `frontend/src/types/` |
| Tests | `spoilerless/tests/` | `frontend/src/**/*.test.tsx` |
| Ontology | `ontology/` | — |
| Seed data | `data/dexter/` | — |

### B. Environment Variables (selected)

| Variable | Default | Purpose |
|---|---|---|
| `NEO4J_URI` | — (required) | Neo4j connection URI |
| `NEO4J_USERNAME` | — (required) | Neo4j username |
| `NEO4J_PASSWORD` | — (required) | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Target database name |
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth client ID |
| `SESSION_COOKIE_NAME` | `session` | HttpOnly cookie name |
| `SESSION_TTL_SECONDS` | `604800` | Session lifetime (7 days) |
| `SESSION_COOKIE_SAMESITE` | `lax` | `SameSite` policy on the session cookie |
| `SESSION_COOKIE_SECURE` | `True` | Secure flag on the session cookie (set `false` for local HTTP dev) |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowed origins; also drives `verify_origin` CSRF checks |
| `ALLOWED_EMAILS` | `""` | Comma-separated sign-in allowlist; empty permits any verified Google account |
| `ADMIN_EMAILS` | `""` | Comma-separated allowlist granted the `admin` role at login (see [7.13](#713-role-based-access-control-admin-role)) |
| `REDIS_URL` | `""` | Upstash-style `rediss://` URL enabling rate limiting and the graph cache (see [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache)) |
| `LLM_ENABLED` | `False` | Enable the GraphRAG chat/retrieval endpoints |
| `LLM_PROVIDER` | `openai_compatible` | LLM provider implementation selector |

See [`docs/CONFIGURATION.md`](./CONFIGURATION.md) for the complete, authoritative reference.

### C. Key Ports

| Service | Port |
|---|---|
| Frontend (Vite dev) | 5173 |
| Backend (Uvicorn) | 8000 |
| Neo4j HTTP (Browser) | 7474 |
| Neo4j Bolt | 7687 |
