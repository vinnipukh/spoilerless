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
   - [7.15 Shareable View Snapshots](#715-shareable-view-snapshots)
   - [7.16 Deployment Topology](#716-deployment-topology)
8. [Key Design Decisions](#8-key-design-decisions)
9. [Future Extensibility Points](#9-future-extensibility-points)
10. [Appendices](#10-appendices)

---

## 1. System Overview

Spoilerless is a **spoiler-aware TV series knowledge graph** application. It lets users explore character relationships, events, locations, organizations, and narrative claims from a TV series — all filtered by how much of the series they have watched. Users can attach notes, create custom nodes/relationships, share tokenized read-only graph snapshots, and — when an LLM provider is configured — ask a spoiler-grounded chat agent questions about the graph.

The core architectural policy is to filter spoilery content in Cypher before it reaches the client or LLM. Spoiler-sensitive nodes, relationships, and claims carry `visible_from_order`; system records such as users, sessions, progress, chat, ChangeSets, share tokens, and settings do not universally carry it. The primary graph, episode, export, and GraphRAG paths resolve or clamp a server-side effective boundary. Enforcement is not yet uniform: anonymous candidate reads accept any persisted episode order, user-content/revision reads accept any positive order, share creation accepts any persisted episode order, and several retrieval queries have incomplete hop coverage (see [7.10](#710-spoiler-safety-invariants)).

The system is a multi-series-capable web application. Production is split across a Vercel-hosted React SPA, a Render-hosted FastAPI service, Neo4j AuraDB, and optional Upstash Redis. Docker Compose provisions Neo4j only for local development. Authentication scopes progress, chat, ChangeSets, user-content writes, revision reverts, candidate ingest, and share-link management; owner checks protect user-created resources, while selected canonical-graph and shared-settings mutations require the `admin` role.

### Stack Summary

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript 6, Vite 8, Cytoscape.js 3 + cose-bilkent / fcose |
| UI Library | Radix UI, shadcn/ui, Tailwind CSS 4, Lucide icons |
| Backend | Python 3.13+, FastAPI 0.140+, Uvicorn, Pydantic v2 |
| Database | Neo4j AuraDB in production; Neo4j `2026.06.0-community` via Docker Compose locally |
| Graph driver | `neo4j` Python driver 6.2+ (async) |
| Auth | Google Sign-In (ID token verification via `google-auth`); `ADMIN_EMAILS`-derived `admin`/`user` role |
| LLM (optional) | OpenAI-compatible chat completions or Google Gemini REST |
| Cache / rate limiting (optional) | Upstash Redis via `redis.asyncio` + `pyrate-limiter` (installed through `fastapi-limiter>=0.2.0`) — disabled when `REDIS_URL` is empty |
| Package management | `uv` (Python), `npm` (frontend) |
| Deployment | Vercel (SPA), Render (FastAPI), AuraDB (Neo4j), optional Upstash Redis; Docker Compose is local-only |

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
│   ┌──────────┐ ┌──────────────┐ ┌────────────┐                  │
│   │ Share    │ │ TimelineView │ │ Settings   │                  │
│   │ Dialog   │ │              │ │ Page       │                  │
│   └──────────┘ └──────────────┘ └────────────┘                  │
│              Vite dev-server proxy: /api → http://127.0.0.1:8000 │
└─────────────────────────────────────────────────────────────────┘
                          │  fetch (credentials: include)
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                Backend (FastAPI + Uvicorn, :8000)                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ API Layer — spoilerless/app/api/                               │  │
│  │ series · graph · user_content · auth · revisions ·         │  │
│  │ candidates · progress · chat · change_set · settings ·    │  │
│  │ share                                                     │  │
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
│  │ ChatRepository · ProgressRepository · SettingsRepository ·  │  │
│  │ ShareRepository (Neo4j)                                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Graph / Spoiler Layer — spoilerless/app/graph/, spoiler/   │  │
│  │ Neo4jDatabase · labels.py (NODE_LABELS/STORY_LABELS) ·     │  │
│  │ ontology.py · seed.py · setup.py · filter.py               │  │
│  │ (visible_claim_where()/claim_projection() fragments,       │  │
│  │  BOUNDARY_QUERY)                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ GraphRAG-lite (optional) — spoilerless/app/retrieval/, llm/│  │
│  │ RetrievalPipeline · TOOL_SPECS registry (12 tools) ·       │  │
│  │ context.py (CONTEXT_SECTIONS) · LLMProvider                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Cache / Rate-Limit Layer (optional) — spoilerless/app/cache/,   │  │
│  │ services/rate_limit.py — one shared redis.asyncio client;    │  │
│  │ cache-aside for GET .../graph, RedisBucket rate limiters on  │  │
│  │ login/chat-send/content-write; no-op when REDIS_URL is empty │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                          │  Neo4j/Bolt                    │ rediss://
                          ▼                                 ▼ (optional)
┌─────────────────────────────────────────────────────────────────┐   ┌──────────────┐
│  Neo4j AuraDB (production) / 2026.06.0 Community (local Docker)    │   │ Upstash Redis│
│  Series, Season, Episode, Scene, Character, Location,             │   │ (rate limits,│
│  Organization, Object, Event, Claim, Source, EvidenceFragment,    │   │  graph cache)│
│  UserNote, Revision, AppUser, ChangeSet, ChatMessage, AppSetting, │   └──────────────┘
│  ShareToken                                                     │
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

**Intended dependency flow:** API → service → repository → database, while domain models (`spoilerless/app/domain/`) are imported across layers. The current code has a few route-level deviations: `user_content.py` constructs and calls `UserContentRepository` in handlers, and `share.py` interacts directly with `ShareRepository` (no service layer). The former `candidates.py`/`revisions.py` route closures were moved into repository methods (`CandidateRepository.approve_claim`/`reject_claim`/`edit_claim`, `revisions.revert_revision_work`) in the PROB-09 #60 refactor — those routes now build a command and delegate.

---

## 3. Directory Structure Rationale

```
./
├── spoilerless/
│   ├── app/
│   │   ├── api/            # Route handlers — one module per resource area (11 route modules)
│   │   ├── cache/          # Shared Redis client and cache-aside graph cache; optional/no-op
│   │   ├── core/           # pydantic-settings configuration, error-envelope helpers, token generation/hashing
│   │   ├── domain/         # Pydantic request/response contracts
│   │   ├── graph/          # Neo4j driver, label inventories, ontology/seed/setup, candidate/feature Cypher
│   │   ├── llm/            # Provider abstraction, system prompts, fallback text
│   │   ├── repository/     # Neo4j data access (plus in-memory session/share test implementations)
│   │   ├── retrieval/      # GraphRAG-lite pipeline, ToolSpec tool registry, context-section registry
│   │   ├── revisions/      # Revision repository/audit-trail implementation
│   │   ├── services/       # Business orchestration and rate-limit dependencies
│   │   ├── spoiler/        # Visibility queries, policy, and derived-visibility rules
│   │   └── main.py         # FastAPI assembly, middleware, router registration, lifespan
│   ├── scripts/            # zombie_sweep.py operator cleanup utility
│   └── tests/              # pytest suite (configured by root pyproject.toml)
├── frontend/
│   └── src/
│       ├── api/            # Typed fetch clients, one file per backend resource (including share.ts)
│       ├── components/     # React components grouped by feature (graph, chat, auth, share, detail, ...)
│       ├── hooks/           # Data-fetching and state hooks
│       ├── lib/             # searchIndex.ts (zero-dep substring search), byok.ts, exportMarkdown.ts, graph/highlight.ts
│       ├── providers/       # React context providers (auth)
│       └── types/           # TypeScript types mirroring spoilerless/app/domain/*.py
├── data/dexter/             # Seed data for the Dexter S01E01–03 prototype
│   ├── metadata/            # Series and episode metadata
│   └── seed/                # Characters, claims, events, evidence, locations, sources
├── ontology/                 # Versioned YAML type system (node/relation/claim types)
├── docs/                     # Project documentation (this directory)
├── docker-compose.yml         # Local-only Neo4j container
├── render.yaml                 # Render backend blueprint
├── pyproject.toml             # Python project config, dependencies, pytest config
└── .env.example                # Shared backend/Vite environment template
```

The split between `data/` (content) and `ontology/` (schema) lets the seed pipeline validate every seeded entity against the type system before writing to Neo4j — a malformed seed file fails fast at `spoilerless-setup` time rather than producing an inconsistent graph. The backend's `api/ → services/ → repository/ → graph/` layering mirrors a conventional three-tier backend, with `spoiler/` singled out as its own directory specifically because the spoiler-filtering Cypher is the system's central invariant and is kept free of FastAPI/Pydantic imports so it can be unit-tested and audited in isolation.

---

## 4. Layer-by-Layer Breakdown

### 4.1 Frontend (React + Cytoscape)

**Location:** `frontend/`

A single-page application that renders an interactive knowledge graph using Cytoscape.js. Authenticated users get persistence and write features; the explicit `visitor` auth state provides anonymous, read-only graph browsing with local-only episode selection.

#### Directory Structure

```
frontend/src/
├── api/              # client.ts (fetch wrapper + ApiError; error normalization to
│                      #   INVALID_REQUEST / UNKNOWN_ERROR), graph.ts, series.ts,
│                      # auth.ts, revisions.ts, progress.ts, chat.ts, changeSet.ts,
│                      # share.ts, userContent.ts, export.ts
├── components/
│   ├── auth/          # LoginPage
│   ├── chat/           # ChatLauncher, ChatSheet, ChatPanel, SessionPicker,
│   │                    # MessageList/MessageBubble, CitationChip, ChangeSetCard
│   ├── detail/          # DetailPanel, BacklinksTab, StructuralEdgeCard, RevisionHistoryPanel
│   ├── episode/          # EpisodeSelector, SeriesSelect, ConfirmAdvanceModal
│   ├── graph/             # GraphCanvas, graphElements, graphStylesheet,
│   │                    # GraphControls, GraphLegend, GraphFocusIndicator, GraphFilterPanel,
│   │                    # GraphStatus, NodeHoverCard, NodeSearch, PathFinder,
│   │                    # relationshipStyles, layoutConfig, overviewTiers, filterState,
│   │                    # autoZoomHold, focusReducer
│   ├── layout/             # AppShell, HeaderNavAction
│   ├── palette/            # CommandPalette (⌘K)
│   ├── series/             # SeriesDashboard
│   ├── settings/            # SettingsPage
│   ├── share/               # ShareDialog, ShareView
│   ├── timeline/            # TimelineView, TimelineEventRow
│   └── ui/                  # shadcn/ui primitives and SpoilerGuard wrapper
├── hooks/               # useFetchState (shared fetch state machine), useGraph,
│                         # useWatchProgress, useSeries, useEpisodes, useNotes,
│                         # useRevisions, useChatSessions, useChatMessages, useHotkey
├── lib/                 # searchIndex.ts (zero-dep substring search behind node search,
│                         #   notes & claims search, and the ⌘K palette), byok.ts,
│                         #   nodeTypes.ts, exportMarkdown.ts, utils.ts, graph/highlight.ts
├── providers/            # AuthContext.ts, AuthProvider.tsx, useAuth.ts
└── types/                # graph.ts, series.ts, revision.ts, settings.ts, share.ts — mirror
                           # spoilerless/app/domain/*.py
```

#### Key Components

- **`GraphCanvas.tsx`** — wraps `react-cytoscapejs`. `layoutConfig.ts` registers fCoSE and cose-bilkent, selects fCoSE by default, and falls back to built-in `cose` after a runtime layout failure. The canvas supports curated Overview and complete Full projections, cached positions keyed by series/boundary/mode, filters, focus/reveal framing, and an interaction hold that suppresses automatic re-fitting for 20 seconds. A newly mounted Cytoscape instance runs a fresh fitted layout; the **Refresh graph** control forces the same relayout/fit path. The 20-second interaction hold lives at module scope (`autoZoomHold.ts`) because `App` keeps the last-known-good graph mounted across refetches. All highlight paths — search selection, ⌘K jump focus, and the reveal pulse — route through the single `applyHighlight()` in `lib/graph/highlight.ts` (clear stale classes → resolve elements → add classes → optional edge-label reveal, fade, and fit).
- **`graphElements.ts`** — pure function mapping the backend `GraphResponse` to Cytoscape `ElementDefinition[]`. It performs **no** re-filtering by `visible_from_order` — the backend has already applied the spoiler filter, and the frontend trusts it completely.
- **`graphStylesheet.ts`** — maps node types to shapes (Character → ellipse, Event/Location → round-rectangle, Organization → diamond, Episode → tag, Series → star, UserNote → dashed round-rectangle) and origin to border style (canonical = solid, candidate/user = dashed).
- **`useWatchProgress.ts`** — maintains separate `watchedThroughOrder` and `viewAsOfOrder` values; the legacy `confirmedOrder` return value aliases the effective current view. Already-watched selections issue an awaited view-only progress update, while selections above the watched boundary create `pendingChange` for confirmation. `sessionStorage` is an optimistic/loading cache reconciled with `GET /progress`; a user interaction wins over a late hydration response. `confirmChange()` awaits `POST /progress`, but deliberately keeps an optimistic local value if that write fails. With `{persist: false}` (visitor mode), all progress changes stay local and no progress API is called.
- **`AuthProvider.tsx`** — on mount calls `GET /api/auth/me` to restore a cookie session; otherwise it can resolve to `unauthenticated` or the sessionStorage-backed `visitor` state. Visitor mode hides chat and write affordances and keeps episode progress local.
- **`App.tsx` / `AppShell`** — a state-driven shell: `view` is a `useState<'graph' | 'timeline' | 'settings'>('graph')` union, so the graph workspace, the timeline, and the settings page are plain state switches (entering settings unmounts the graph view, including the chat sheet). App orchestrates series selection → episode list loading → watch-progress state → graph fetching, wires `NodeSearch`/`CommandPalette` selections into the existing `graphFocus` path, and registers hotkeys via `useHotkey`. The graph stays mounted once a payload has loaded: `activeGraph` is the latest successful `GraphResponse` (a ref holds the last-known-good while refetching), and loading/error render as an overlay above it — first-load failures show full-screen `GraphLoadingState`/`GraphErrorState` instead. Edge routing is three-way: claim-backed edges and claim-less `origin: "user"` edges open `DetailPanel`; only claim-less non-user edges open `StructuralEdgeCard`. Consequently, `claim_id: null` alone is not a structural-edge discriminator.
- **`NodeSearch.tsx`** — floating search bar over the canvas; a mode `ToggleGroup` switches between node search and grouped notes & claims search. Both run payload-local through `lib/searchIndex.ts` — zero-dep substring matching, with fuse.js explicitly excluded. Selection reuses the existing `onSelect` → `DetailPanel` / `graphFocus` path.
- **`PathFinder.tsx`** — two-node selection mode that POSTs `/api/series/{id}/graph/path` via `frontend/src/api/graph.ts` and renders the returned hop chain over the canvas.
- **`ShareDialog.tsx` / `ShareView.tsx`** — `ShareDialog` lets signed-in users generate and manage 30-day tokenized snapshot links for their current view; `ShareView` renders a read-only graph canvas for unauthenticated recipients accessing `/share/{token}`.
- **`GraphControls.tsx` / `GraphLegend.tsx`** — zoom/fit/reset controls and a collapsible legend derived from `relationshipStyles.ts`'s edge-color families.
- **`CommandPalette.tsx`** — the ⌘K palette: a dialog overlay grouping "Jump to node" / "Switch episode" / "Actions". Node rows share `searchIndex` with `NodeSearch`; episode rows route through the `onRequestChange` prop (locked episodes open the unlock dialog, never a silent no-op); action rows switch views (timeline/settings/dashboard) and trigger export.
- **`TimelineView.tsx` / `SeriesDashboard.tsx`** — the timeline view (full-canvas chronological list of visible `Event` nodes rendered from the boundary-filtered graph payload, via `TimelineEventRow`) and the series dashboard (episode-overview dialog).
- **`useHotkey.ts`** — global keyboard-shortcut hook: one `window` `keydown` listener per combo (`mod+k`, `/`, `escape`) with cleanup and a ref-held handler; `{ skipWhenInputFocused: true }` stops `/` from hijacking typing.
- **`useFetchState<T>`** (`hooks/useFetchState.ts`) — the shared `idle | loading | error | success` fetch-state machine with key-change reset and a monotonic run-id stale-response guard; `useGraph`, `useEpisodes`, `useNotes`, `useRevisions`, `useSeries`, and `useChatSessions` all build on it.
- **`searchIndex.ts`** (`lib/`) — the single zero-dependency substring search implementation behind node search, notes & claims search, and the palette; a pure function over payloads the frontend has already fetched (and the backend has already boundary-filtered).

#### Vite Configuration

The dev server proxies `/api` requests to `http://127.0.0.1:8000`. `vite.config.ts` sets `envDir: '..'`, so the frontend and backend read the root environment file. Production clients prefix requests with `VITE_API_BASE_URL`; `frontend/vercel.json` rewrites SPA paths to `/index.html` and does not proxy `/api`.

---

### 4.2 API Layer (FastAPI)

**Location:** `spoilerless/app/api/`

Eleven route modules registering **51 HTTP operations** (including `GET /health` and `HEAD /health` in `main.py`) across **37 unique path templates**.

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
| `share.py` | `/api/share` | Create, read token snapshot graph, list, and revoke share links |
| `main.py` | `/health` | Service + database health check (GET and HEAD handlers) |

#### Architecture Pattern

Route modules consistently use FastAPI `APIRouter`s and Pydantic request/response models, but dependency and data-access patterns vary: most inject services or repositories, `user_content.py` constructs its repository inside handlers, and `share.py` interacts directly with `ShareRepository`. Candidate-review and revert transaction logic lives in the repository layer (`CandidateRepository.approve_claim`/`reject_claim`/`edit_claim`, `revisions.revert_revision_work`).

#### Rate Limiting and Admin Gating

Three route groups carry an optional `RateLimiter` dependency (`spoilerless/app/services/rate_limit.py`; see [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache)): `POST /api/auth/google` (10/5min per IP), both chat message routes (20/min per user), and every `user_content.py` write route (30/min per user). `RequireAdminDependency` additionally gates candidate approve/reject/edit, ChangeSet confirm, and both server-side settings routes. Candidate ingest requires an authenticated user but not an admin; candidate list/get remain anonymous boundary-gated reads. All ChangeSet routes require authentication, with only confirm requiring admin.

#### Graph Route — The Critical Read Path

`GET /api/series/{series_id}/graph?visible_until_order=N` is the most architecturally significant endpoint. Anonymous callers are fixed to order 1. For an authenticated caller, the requested value is first validated as a persisted episode order — the single `BOUNDARY_QUERY` episode-boundary check in `spoiler/filter.py`, shared with candidate reads and share creation — and then clamped against persisted `view_as_of_order`/`watched_through_order`. The route checks the Redis cache-aside layer (`graph:{series_id}:{effective_boundary}:{user_id or 'anon'}`), and on a miss delegates to `GraphService.fetch_graph()` (seven concurrent Cypher queries) before caching the result for 300 seconds. `GraphResponse` carries `visible_until_order`, `effective_view_order`, and the visible nodes, edges, claims, sources, and evidence. Empty or failing Redis always falls through to Neo4j.

The locked operation inventory (method/path templates and response schemas) is maintained separately in [`docs/reference/frontend-api-contract.md`](./reference/frontend-api-contract.md); the OpenAPI spec generated by `spoilerless.app.main:app` is authoritative.

Two sibling routes reuse the same spoiler-safe machinery. `POST /api/series/{series_id}/graph/path` executes the allowlisted `find_path` tool with `max_hops` constrained to 1–4. Its request model contains source ID, target ID, and `max_hops` but **no episode boundary**; per PROB-09/#59 the handler resolves the effective boundary from persisted progress alone — never from the `MAX_PATH_HOPS` hop constant — so an authenticated reader's real progress applies and a user with no progress record fails closed to order 1. `GET /api/series/{series_id}/export` accepts `visible_until_order` and renders the full visible graph—or one target and its claims—as Markdown from `GraphService.fetch_graph()`. Export therefore follows the shared boundary block as intended; the path route shares the same resolver.

---

### 4.3 Service Layer

**Location:** `spoilerless/app/services/`

- **`GraphService`** (`graph.py`) — orchestrates the spoiler-safe graph read. `fetch_graph(series_id, visible_until_order, node_labels, user_relationship_types, effective_view_order=None)` runs seven Cypher queries concurrently: series metadata, nodes, structural edges, canonical/candidate claims, user-authored relationships, sources, and evidence. Claims are projected into `GraphEdge`s; node rows also pass through `filter_public_metadata()` before validation so spoiler-sensitive media fields are removed at the effective view boundary.
- **`SeriesService`** (`series.py`) — lists series, gets one series, and lists episodes. `list_episodes(series_id, effective_view_order=None)` passes episode rows through `mask_episode_metadata()` when a boundary is supplied; the API resolves anonymous order 1 or an authenticated effective progress boundary before returning titles/unlock state. The boundary-free form remains for internal/backward-compatible callers.
- **`AuthService`** (`auth.py`) — verifies Google ID tokens via an injectable `GoogleTokenVerifier`, upserts users by `google_sub`, and manages session creation/retrieval/revocation. Its constructor requires explicit `session_repo` and `verifier` arguments — there are no silent fallbacks to in-memory or production defaults, so a missing dependency is a loud wiring bug. Valid reads update `last_seen_at` through `SessionRepository.refresh()` but do not extend `expires_at`. Session tokens are SHA-256 hashed via `core/tokens.py` before storage; raw tokens are never persisted.
- **`ProgressService`** (`progress.py`) — resolves per-user progress from `(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)-[:FOR_SERIES]->(:Series)`. The persisted model separates `watched_through_order` from `view_as_of_order`; `resolve()` returns `effective_view_order`. `upsert()` accepts keyword-only `watched_through_order`, `view_as_of_order`, and the legacy `visible_until_order` alias, validates both selected orders against the series' persisted episodes, enforces `1 <= view <= watched`, and preserves the watched boundary for view-only changes. Missing records map to `404`; chat creates an order-1 record on first send.
- **`ChatService`** (`chat.py`) — owns the GraphRAG-lite turn lifecycle: resolve boundary → load spoiler-filtered history → run the retrieval pipeline → stream the grounded answer back over SSE. Persists every `ChatMessage` with a `visible_until_order_snapshot` equal to the boundary resolved at turn time.
- **`ChangeSetService`** (`change_set.py`) — Stage 1 **propose** validates a typed operation list against the ontology and the resolved boundary — per-target visibility checks run concurrently via `asyncio.gather` (each is an independent single-row read) — then persists an `awaiting_confirmation` ChangeSet draft and its linking relationships without mutating target graph content. Stage 2 **confirm/apply** applies the validated operations in a single Neo4j transaction, prevents replay by returning the stored result when the ChangeSet status is already `applied`, and logs a `Revision` in the same transaction; the random `idempotency_key` is generated only after mutation and is not checked for replay detection. Stage 3 **revert** restores pre-apply state for create-shaped ChangeSets.
- **`SettingsService`** (`settings.py`) — retains an admin-only server-side fallback configuration (`:AppSetting` wins over `LLM_*` env values and keys are masked on read). The current frontend Settings page does not call this API: it stores BYOK provider/key/base URL/model in browser `localStorage`, and chat requests send them as `X-LLM-*` headers. `get_llm_provider()` uses non-blank BYOK headers exclusively for that request; otherwise it falls back to stored/env configuration.

`spoilerless/app/services/rate_limit.py` is not a class-per-feature service in this same sense — it defines the `RateLimiter` FastAPI dependency and the three module-level route-group instances described in [7.14](#714-redis-backed-rate-limiting-and-graph-response-cache).

---

### 4.4 Repository & Database Layer

**Location:** `spoilerless/app/repository/`, `spoilerless/app/graph/`

- **`Neo4jDatabase`** (`graph/database.py`) — lazy-initialized async driver with `open()`/`close()` managed by FastAPI lifespan, `execute_query(query, **parameters) -> list[dict[str, Any]]`, managed `execute_write(work, command)`, and `verify_connection()`. TLS Aura URIs (`neo4j+s://`/`bolt+s://`) are normalized to their plain scheme plus `encrypted=True` and `TrustCustomCAs(certifi.where())`; pool size is 50 with 30-second connect and 60-second liveness timeouts. It also defines the shared `neo4j_row_to_python()` row-normalization helper (Neo4j temporal types → ISO-8601 strings) and the `run_single()` run-single-raise pattern that every repository composes — previously byte-identical per-module copies.
- **`UserRepository`** (`repository/user.py`) — `upsert()` (MERGE on `google_sub`), `get_by_id()`. Users are stored as `(:AppUser)` nodes.
- **`SessionRepository`** (`repository/session.py`) — a `SessionRepository` protocol with two implementations: `Neo4jSessionRepository` (the default, wired directly into `main.py`'s lifespan) persists sessions as `(:Session)` nodes linked via `(:AppUser)-[:HAS_SESSION]->(:Session)`, with uniqueness constraints on `id` and `token_hash` and an index on `expires_at` (created by the seed pipeline); `InMemorySessionRepository` is a plain-dictionary store with no synchronization, suitable for development and tests. Tokens come from `core/tokens.py`'s `generate_token(48)`; only the `hash_token()` SHA-256 hash is ever persisted. Periodic background sweep task in `main.py`'s `lifespan` (`sweep_expired()`) deletes expired/revoked `(:Session)` nodes every hour.
- **`ShareRepository`** (`repository/share.py`) — a `ShareRepository` protocol with `Neo4jShareRepository` and `InMemoryShareRepository` implementations. Persists share tokens on `(:ShareToken)` nodes linked via `(:AppUser)-[:CREATED_SHARE]->(:ShareToken)`. Stores SHA-256 token hashes (via `core/tokens.py`), series ID, boundary, created_at, and 30-day default `expires_at`. Cleaned up periodically alongside sessions by `sweep_expired()` in `main.py`'s lifespan loop.
- **`UserContentRepository`** (`repository/user_content.py`) — manages notes, custom nodes, and custom relationships. Notes inherit their target boundary; custom nodes derive it from the selected episode; custom relationships use the maximum of source, target, and episode orders through the shared `spoiler/visibility.py` rule. Creates bind `user_id`/`created_by`; updates/deletes require the owner unless the actor is admin, and legacy rows without an owner fail closed to admin-only. Reads are boundary-filtered but intentionally public, so ownership is a mutation boundary rather than read isolation. Deleting a custom node with dependent content returns `409`.
- **`ChangeSetRepository`**, **`ChatRepository`**, **`SettingsRepository`** — the corresponding data-access layers for ChangeSets, chat, and settings.

A separate operator script, `spoilerless/scripts/zombie_sweep.py`, sweeps orphaned `(:AppUser)` rows and stale `(:Session)` nodes — dry-run-first by default (`python -m spoilerless.scripts.zombie_sweep --dry-run` counts; `--execute` deletes).

---

### 4.5 Neo4j Graph Database

**Location:** `spoilerless/app/graph/seed.py`; AuraDB in production and Docker Compose locally

#### Container

```yaml
services:
  neo4j:
    image: neo4j:2026.06.0-community
    container_name: spoilerless-neo4j
    ports: ["127.0.0.1:7474:7474", "127.0.0.1:7687:7687"]
    volumes: [./neo4j_data:/data, ./neo4j_logs:/logs, ./neo4j_import:/import, ./neo4j_plugins:/plugins]
```

#### Node Labels

| Group | Labels |
|---|---|
| Structural | `Series`, `Season`, `Episode`, `Scene` |
| Narrative | `Character`, `Location`, `Organization`, `Object`, `Event` |
| Knowledge | `Claim`, `Source`, `EvidenceFragment` |
| User | `UserNote` |
| System | `Revision`, `AppUser`, `Session`, `UserSeriesProgress`, `ChatSession`, `ChangeSet`, `ChatMessage`, `AppSetting`, `ShareToken` |

#### Relationship Types

| Group | Types |
|---|---|
| Structural | `PART_OF`, `PRECEDES`, `OCCURRED_IN`, `LOCATED_IN` |
| Participation | `PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED` |
| Character | `KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS` |
| Provenance | `SUPPORTED_BY`, `CONTRADICTED_BY`, `DERIVED_FROM`, `REFERS_TO` |
| Revision | `CORRECTS`, `SUPERSEDES`, `REVERTS_TO` |
| System/application | `HAS_SESSION`, `HAS_PROGRESS`, `FOR_SERIES`, `HAS_CHAT_SESSION`, `IN_SERIES`, `HAS_MESSAGE`, `PROPOSED_CHANGE_SET`, `FOR_SESSION`, `CREATED_SHARE` |

#### Constraints & Indexes

Created idempotently by `setup_database()`: `id` uniqueness constraints for the 12 labels in `graph/labels.py`'s `NODE_LABELS` plus `AppUser`, `Session`, and `ShareToken` (with additional `google_sub`/`token_hash` constraints); `visible_from_order` indexes for those 12 seed labels; selected `series_id` indexes for episode/content/revision labels plus separate progress/chat lookup indexes; a composite index on `UserNote(series_id, target_type, target_id)`; an index on `Episode.episode_order`; and an index on `ShareToken.expires_at`. `UserSeriesProgress`, `ChatSession`, `ChatMessage`, `ChangeSet`, and `AppSetting` do not receive universal `id`, visibility, and per-label `series_id` indexes.

> Property existence constraints require Neo4j Enterprise and are intentionally omitted. Null visibility is prevented through Pydantic validation, service-layer guards, and a post-seed integrity audit.

#### Seed Pipeline

The `setup_database()` pipeline loads seed JSON from `data/dexter/`, validates it against the ontology (node types, relationship types, claim types/statuses/confidence levels, ID uniqueness, evidence completeness), creates constraints and indexes, upserts all nodes via `MERGE`, creates structural and provenance relationships, and runs a visibility integrity audit. `pyproject.toml` declares `spoilerless-setup = "spoilerless.app.graph.setup:main"`; the directly importable/module form is `uv run python -m spoilerless.app.graph.setup`.

After seeding, `spoilerless/app/graph/setup.py` runs `_check_visibility_schema()` over `graph/labels.py`'s `STORY_LABELS` set — `Character`, `Event`, `Location`, `Organization`, `Object`, `Claim`, `EvidenceFragment`, and `Source` nodes under `series_dexter`. A null `visible_from_order` raises `SCHEMA DRIFT` and exits non-zero.

---

## 5. Key Abstractions

| Abstraction | Location | Purpose |
|---|---|---|
| `visible_from_order` filtering | `spoilerless/app/spoiler/filter.py` | The core graph-read Cypher predicate for story-sensitive entities; filter.py also exposes the shared `visible_claim_where()` / `claim_projection()` fragments (composed by graph reads and retrieval tools) and `BOUNDARY_QUERY`, the single persisted-episode-order check |
| `Neo4jDatabase` | `spoilerless/app/graph/database.py` | Central async driver abstraction; all Cypher execution flows through `execute_query()`/`execute_write()` |
| `Ontology` | `spoilerless/app/graph/ontology.py` | Loads and validates the versioned YAML type system; exposes `require_node_type()`, `require_relationship_type()`, `require_claim_type()`, and the user-safe type subsets |
| `Claim` domain model | `spoilerless/app/domain/graph.py` | The atomic knowledge-representation unit — subject/predicate/object plus type, status, confidence, and provenance |
| `origin` enum | shared across `domain/` modules | Three-way `StrEnum` (`canonical` / `candidate` / `user`) distinguishing seed data, extracted-but-unreviewed data, and user-created data |
| `LLMProvider` protocol | `spoilerless/app/llm/provider.py` | Provider-agnostic streaming interface. Two concrete implementations are available: `OpenAICompatibleProvider` posts to `/chat/completions`; `GeminiProvider` translates messages/tools to Gemini content/function parts and posts to `streamGenerateContent` action with SSE |
| `RetrievalPipeline` | `spoilerless/app/retrieval/pipeline.py` | Orchestrates allowlisted tool calls (via the `TOOL_SPECS` registry), context assembly (in `CONTEXT_SECTIONS` order), and citation validation for the GraphRAG-lite chat |
| `ToolSpec` / `TOOL_SPECS` | `spoilerless/app/retrieval/pipeline.py` | The single allowlisted-tool registry — name, description, Pydantic `input_model`, async `executor`, optional `result_bucket`, `requires_user`/`requires_chat_session` flags — from which provider tool schemas (`TOOL_SCHEMAS`) are derived and dispatches resolve via `_TOOL_SPECS_BY_NAME`; replaces the three parallel tables |
| `CONTEXT_SECTIONS` | `spoilerless/app/retrieval/context.py` | Single source of truth for the RAG context layout (fixed section order + delimiter tags), consumed by both `assemble_context` and `llm/system_prompt.py` |
| `neo4j_row_to_python` / `run_single` | `spoilerless/app/graph/database.py` | Shared Neo4j row normalization (temporal types → ISO-8601 strings) and run-single-raise pattern every repository composes |
| `hash_token` / `generate_token` | `spoilerless/app/core/tokens.py` | The single token generation + SHA-256 hashing pair used by the session and share repositories |
| `NODE_LABELS` / `STORY_LABELS` | `spoilerless/app/graph/labels.py` | Server-owned label inventories: the 12 seed labels and the 8 visibility-audited story labels |
| `ChangeSetService` | `spoilerless/app/services/change_set.py` | The typed, two-stage (propose/confirm) protocol that is the only path through which the graph can be mutated by chat-driven writes |
| `RevisionRepository.log_revision` | `spoilerless/app/revisions/__init__.py` (used across services and repositories) | Shared pattern for writing an append-only before/after audit record in the same transaction as any content mutation |
| `ShareRepository` | `spoilerless/app/repository/share.py` | Manages hashed, 30-day snapshot share tokens (`:ShareToken`) for token-gated, unauthenticated graph reads |
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
App.tsx / useWatchProgress selects series "series_dexter" and a view order
  │
  ├──► useEpisodes("series_dexter") → GET /api/series/{id}/episodes
  │      → SeriesService.list_episodes() → Neo4j MATCH (Episode)-[:PART_OF]->(Series)
  │
  └──► useGraph("series_dexter", visibleUntilOrder=1)
         → GET /api/series/{id}/graph?visible_until_order=1
         → route resolves anonymous order 1 or authenticated effective progress
         → GraphService.fetch_graph("series_dexter", effective_order,
              node_labels, user_relationship_types, effective_view_order)
              (7 concurrent Cypher queries via asyncio.gather)
              1. SERIES_QUERY            → series metadata
              2. NODES_QUERY             → nodes <= effective order
              3. STRUCTURAL_EDGES_QUERY  → structural edges <= effective order
              4. VISIBLE_CLAIMS_QUERY    → claims visible at effective order
              5. VISIBLE_USER_RELATIONSHIPS_QUERY → visible user relationships
              6. SOURCES_QUERY           → sources referenced by visible claims
              7. EVIDENCE_QUERY          → evidence backing visible claims
         → GraphResponse assembled (claims projected to edges)
         → graphToElements() → Cytoscape ElementDefinition[]
         → GraphCanvas renders with layout
```

### Flow 2 — User advances watch progress

```
User selects "S01E03" in EpisodeSelector
  → useWatchProgress.requestChange("series_dexter", 3)
  ├─ if 3 <= watchedThroughOrder:
  │    POST /progress {view_as_of_order: 3} (view-only; watched boundary unchanged)
  ├─ if 3 is above watchedThroughOrder:
  │    ConfirmAdvanceModal opens
  │      confirm → POST /progress
  │        {watched_through_order: 3, view_as_of_order: 3}
  │      cancel → discard pendingChange
  └─ visitor mode: local view update only; no modal and no network write
  → useGraph re-fetches at confirmedOrder (= current effective view)
```

### Flow 3 — User creates a note

```
POST /api/series/{series_id}/notes { target_type, target_id, content }
  → UserContentRepository.create_note(series_id, user_id, request)
      validates target exists in the same series and has visible_from_order >= 1
      generates id = "user-note:{uuid4}"
      Neo4j: MATCH target WHERE target.visible_from_order >= 1
             CREATE (:UserNote {user_id: $user_id, ...})-[:REFERS_TO {origin:'user'}]->(target)
  → Response: NoteResponse with origin="user", visible_from_order inherited from target
```

### Flow 4 — User shares a view snapshot

```
Authenticated user clicks "Share View" in topBar
  → ShareDialog opens → POST /api/share { series_id: "series_dexter", visible_until_order: 3 }
      → ShareRepository.create() creates (:ShareToken) with token_hash and 30-day TTL
      → Returns raw token and URL `/share/{token}`
Recipient opens link `/share/{token}`
  → App renders ShareView component (unauthenticated)
  → GET /api/share/{token}/graph
      → ShareRepository.get_by_raw_token() validates hash and expiration
      → GraphService.fetch_graph(series_id, visible_until_order) executes exact spoiler-safe read
      → Returns GraphResponse for read-only Cytoscape rendering
```

---

## 7. Cross-Cutting Concerns

### 7.1 Spoiler-Aware Data Flow

This is the **core architectural invariant** of the system. Spoiler filtering happens entirely on the backend — the frontend never receives data it would need to hide.

Story-sensitive content nodes, content relationships, and claims carry a `visible_from_order` integer: the earliest episode order at which the entity stops being a spoiler. System records and links such as `AppUser`, `Session`, `AppSetting`, `ShareToken`, `HAS_SESSION`, `CREATED_SHARE`, and progress/chat ownership relationships do not universally carry it. The `visible_until_order` query parameter represents how far the user has watched. Relevant spoiler-aware Cypher queries apply:

```cypher
WHERE entity.visible_from_order <= $visible_until_order
```

**Fail-closed design:** graph, export, candidate, progress-write, and share-create boundaries are resolved against persisted episode orders. Progress writes validate `watched_through_order` and `view_as_of_order`, and GraphRAG consumes the computed effective view. User-content and revision read routes are a narrower exception: their `Boundary` alias enforces only a positive integer and their Cypher applies that value directly. Direct reads of hidden resources (for example a future note) return the same `404` as a missing resource. The graph's claim/source/evidence queries gate each matched hop; some retrieval-tool queries have the narrower gaps recorded in [7.10](#710-spoiler-safety-invariants).

Claims can additionally carry `valid_from_order`/`valid_until_order` for time-bounded facts (e.g. a temporary allegiance):

```cypher
AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
```

`spoilerless/app/spoiler/filter.py` holds the core graph-read spoiler queries as raw, parameterized Python string constants and exports the shared `visible_claim_where()` / `claim_projection()` Cypher fragments (one definition, seven call sites — the single spoiler-drift hotspot for claim selection) plus `BOUNDARY_QUERY`, the one persisted-episode-order check behind graph/export/candidate/share-create boundary validation. Additional visibility-gated Cypher lives in `graph/candidates.py`, `graph/change_set.py`, `graph/chat.py`, `retrieval/tools.py` (which composes the fragments), `repository/user_content.py`, and `api/revisions.py`.

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

1. The frontend initiates Google Sign-In via the Google Identity Services library using `VITE_GOOGLE_CLIENT_ID` (a build-time env value the backend requires to equal `GOOGLE_CLIENT_ID`) and receives an ID token (JWT).
2. The token is sent to `POST /api/auth/google` as `GoogleAuthRequest.credential`.
3. The backend verifies signature, issuer (`accounts.google.com`), audience (`GOOGLE_CLIENT_ID`), and expiration.
4. If `ALLOWED_EMAILS` is non-empty, the verified email (case-insensitively) must be a member or the request is rejected with `403 AUTH_EMAIL_NOT_ALLOWED`; an empty allowlist permits any verified Google account.
5. `role` is derived server-side from `ADMIN_EMAILS` membership (`"admin"` if the verified email matches, `"user"` otherwise) — never read from the request — and the user record is upserted in Neo4j keyed on Google's `sub` claim, re-syncing `role` on every login so removing an email from `ADMIN_EMAILS` demotes that user on their next sign-in.
6. A session is created with a SHA-256-hashed token (persisted as a `(:Session)` node by `Neo4jSessionRepository`); an HttpOnly cookie is set on the response with `SameSite` taken from `SESSION_COOKIE_SAMESITE` (default `lax`, tunable per deployment).

`GET /api/auth/me` reads the cookie, validates fixed expiry, and updates only `last_seen_at`; there is no slide-on-read. `POST /api/auth/logout` revokes the session, clears the cookie, and returns `204`. Both Google login and logout carry the explicit `verify_origin` dependency, which rejects a missing, malformed, or mismatched `Origin`/`Referer` with `403 AUTH_ORIGIN_NOT_ALLOWED`; login additionally carries the 10-per-5-minute IP limiter. Other state-changing routes rely on cookie policy and CORS and do not attach this origin dependency.

### 7.6 Error Handling

**Location:** `spoilerless/app/core/errors.py`. A structured error envelope used by the API endpoints, except `/health`'s `503` response, which returns the `HealthResponse` fields `status`, `database`, and `service`. All codes are canonical **UPPERCASE `SNAKE_CASE`** — the `ERROR_CODES` registry (32 error codes) is validated by a Pydantic field validator that rejects unregistered or lowercase codes at startup; OpenAPI contract tests enforce the casing:

```json
{ "detail": { "code": "SERIES_NOT_FOUND", "message": "Series not found." } }
```

| Status | Code | When |
|---|---|---|
| 401 | `AUTH_UNAUTHENTICATED` | No valid session |
| 401 | `AUTH_INVALID_GOOGLE_CREDENTIAL` | Google token verification failed |
| 401 | `AUTH_DISABLED` | Google auth or session TTL not configured |
| 403 | `AUTH_EMAIL_NOT_ALLOWED` | Verified Google email not in a non-empty `ALLOWED_EMAILS` |
| 403 | `AUTH_ORIGIN_NOT_ALLOWED` | `Origin`/`Referer` missing or not in `FRONTEND_ORIGINS` (Google login and logout) |
| 403 | `FORBIDDEN` | `RequireAdminDependency` rejected a non-admin caller |
| 404 | `SERIES_NOT_FOUND` | Series lookup missed |
| 404 | `RESOURCE_NOT_FOUND` | Hidden or absent resource |
| 404 | `TOKEN_NOT_FOUND` | Invalid, expired, or revoked share token |
| 409 | `RESOURCE_CONFLICT` | Resource state/dependency conflict (cross-owner mutations use `403 FORBIDDEN`) |
| 422 | `INVALID_REQUEST` | Validation failure |
| 422 | `INVALID_VISIBLE_UNTIL_ORDER` | Bad boundary value |
| 429 | `TOO_MANY_REQUESTS` | A `RateLimiter`-gated route exceeded its window (login/chat-send/content-write) |
| 503 | `DATABASE_UNAVAILABLE` | Neo4j unreachable |

`install_database_error_handlers()` and `install_llm_error_handlers()` (installed in `main.py`) register handlers so validation, constraint, connectivity, and LLM-provider errors are translated into this envelope. Database error messages are intentionally generic — never leaking Cypher, connection details, or internals.

`main.py` registers a `_security_headers_middleware` that stamps every response with `Content-Security-Policy` (default-src 'self', GIS script origins allowed), `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`; CORS is narrowed to an explicit method/header list (no wildcard with credentials).

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

**Location:** `spoilerless/app/retrieval/` (`pipeline.py`, `tools.py`), `spoilerless/app/llm/` (`provider.py`, `system_prompt.py`), `spoilerless/app/services/chat.py`. The server-side fallback is disabled by default (`LLM_ENABLED=false`) and can be configured through environment variables or the admin-only settings API. A chat request carrying a complete browser BYOK header set constructs a request-scoped provider even when that shared fallback is disabled (see [7.11](#711-settings-system-user-configurable-llm-provider)).

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
  │ 5. LLMProvider.stream_chat(system_prompt, history, tools=TOOL_SCHEMAS  (derived from the TOOL_SPECS registry))
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
ChatService persists the ChatMessage (citations and graph_focus) via ChatRepository
  │ 9. Final SSE event: {message, citations, graph_focus, proposed_change_set}
  ▼
Browser: MessageBubble renders streamed text; CitationChip "Show in graph" sets
  GraphCanvas's focusedElementIds; ChangeSetCard's Confirm/Reject buttons POST
  to change_set.py's confirm/reject endpoints — a separate request cycle
```

#### Allowlisted retrieval tools

The pipeline exposes exactly **twelve** allowlisted tools, declared as a single `TOOL_SPECS` registry in `retrieval/pipeline.py`: each `ToolSpec` binds a name, description, Pydantic `input_model`, async `executor`, and an optional `result_bucket` (plus `requires_user` / `requires_chat_session` flags) — replacing the three parallel tables that previously had to be edited in lockstep. Eleven read tools live in `spoilerless/app/retrieval/tools.py`; the twelfth is the typed `propose_changeset` executor registered in `pipeline.py`. Provider-facing `TOOL_SCHEMAS` are derived from the registry, and `_execute_tool_call` dispatches from `_TOOL_SPECS_BY_NAME`. The model can never execute raw Cypher:

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
12. `propose_changeset` — validates a closed `ChangeSetOperation` union and calls `ChangeSetService.propose()`; it persists only an `awaiting_confirmation` draft, not target-graph mutations

Tool arguments are Pydantic-validated and may include model-supplied IDs, search terms, and `allowed_entity_types`; the latter is intersected with the server's `STORY_NODE_LABELS` allowlist before becoming the bound `allowed_labels`. The model never supplies raw Cypher, series IDs, user IDs, session IDs, or visibility boundaries. The pipeline injects server-owned `series_id`, `user_id`, `chat_session_id`, and `visible_until_order`; read tools use parameterized Cypher and server allowlists, while `propose_changeset` delegates typed operations to the service layer. Tools flagged `requires_user` or `requires_chat_session` (user notes, proposal) receive the authenticated context kwargs the read-only tools never see.

### 7.9 ChangeSet Two-Stage Mutation Flow

**Location:** `spoilerless/app/api/change_set.py`, `spoilerless/app/services/change_set.py`, `spoilerless/app/repository/change_set.py`, and the `propose_changeset` tool in `retrieval/pipeline.py`. The LLM **cannot mutate target graph content directly**: it may create a typed, user/session-scoped draft through `ChangeSetService.propose()`, which is returned as `proposed_change_set` for review. Only a later admin-gated confirm request applies operations.

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

The Stage 1 create query (`graph/change_set.py`'s `CHANGE_SET_CREATE_QUERY`) carries both `MERGE`'d anchors forward with an explicit `WITH u, s` before matching the chat session — the fix that eliminated the local Neo4j 5.x `503` failure class (a bare `MATCH` after `MERGE` without carrying the bound identifiers), so the create path no longer needs a workaround on community edition.

Only Stage 2's confirm step is admin-gated — the reasoning is that confirming is the step that actually applies an AI-proposed mutation to the shared canonical graph, so propose/reject/revert remain open to any authenticated user. The frontend renders a proposed ChangeSet as a preview card (per-operation summary, before/after rows for updates, a destructive banner when deletes are present) with explicit Confirm/Reject controls — the only UI path into the confirm/reject endpoints; a non-admin viewer's Confirm click surfaces the `403 FORBIDDEN` response.

### 7.10 Spoiler-Safety Invariants

1. **The LLM never receives the full unfiltered graph.** Context is assembled through the eleven read tools; the twelfth tool creates only a typed ChangeSet draft. `assemble_context` dedupes by ID and bounds the result via `Settings.llm_max_context_items` / `Settings.llm_max_context_characters`.
2. **Retrieval applies persisted effective progress, with incomplete hop coverage in two tool queries.** Progress writes validate persisted episode orders and `ProgressService.resolve()` returns the effective split boundary. Claim-selecting retrieval queries now compose the shared `visible_claim_where()` / `claim_projection()` fragments from `spoiler/filter.py`; `GET_EVIDENCE_QUERY` and `GET_SOURCES_QUERY` remain the two queries that still do not visibility-gate the matched `Claim`. `GRAPH_SUMMARY_COUNTS_QUERY`, by contrast, gates each counted claim and requires visible subject and object endpoints through `EXISTS` subqueries.
3. **The LLM never executes arbitrary Cypher.** There is no text-to-Cypher surface; every query is a server-side constant template with `$parameter` bindings.
4. **The LLM cannot directly mutate canonical or candidate content.** ChangeSet validation substitutes a note for protected Character/Claim mutations and rejects protected types that cannot accept notes; it never applies the requested direct mutation.
5. **ChangeSet writes require typed proposals and explicit confirmation.** The model may call `propose_changeset`, but that writes only a draft. The final envelope carries the draft to `ChangeSetCard`; an explicit, admin-authorized confirm request is the separate transaction that mutates target content.
6. **Chat history is spoiler-filtered by the same boundary as the graph.** `ChatMessage` rows carry `visible_until_order_snapshot`; history loading filters `snapshot <= current boundary`.
7. **Lowering progress hides — never deletes — previously generated future-boundary messages.** They re-appear if progress advances again.
8. **All graph content is treated as untrusted prompt data.** User notes, evidence text, and retrieved content are wrapped in strict delimiters with explicit instruction-ignore language in the system prompt.

### 7.11 Settings System (User-Configurable LLM Provider)

**Location:** `spoilerless/app/api/settings.py`, `spoilerless/app/services/settings.py`, `spoilerless/app/repository/settings.py`, `spoilerless/app/domain/settings.py`; `frontend/src/components/settings/SettingsPage.tsx`.

Two configuration paths coexist. The active frontend Settings page is BYOK: provider, key, base URL, and model are stored only in browser `localStorage` (`spoilerless:byok-llm-settings`) and sent on chat requests as `X-LLM-*` headers. Separately, the backend retains admin-only `GET`/`PUT /api/settings/llm`; a single `(:AppSetting {key: 'llm'})` JSON record overrides `LLM_*` environment defaults when a request has no BYOK key.

**API key handling:** the BYOK key is browser-held and sent only as a request header to the backend; request logging explicitly excludes `X-LLM-*`. The server-side fallback API never returns its full key—only `api_key_configured` and a mask. On `PUT`, blank input keeps an existing key but is rejected when no key is stored; non-blank values are stripped. Both fallback routes require admin and the record is global, not per-user.

| Route | Method | Purpose |
|---|---|---|
| `/api/settings/llm` | GET | Effective LLM config, key masked |
| `/api/settings/llm` | PUT | Update provider/key/model/base_url/enabled/system_prompt_language |

Provider protocols are `gemini` and OpenAI-compatible. The `vllm` and `ollama` selectors are accepted as scaffolding and currently route through `OpenAICompatibleProvider`. For requests without BYOK headers, stored settings override environment defaults and `enabled: false` yields `503 LLM_DISABLED`; a non-blank BYOK key bypasses the stored/env enabled switch and constructs a request-scoped provider. Chat session CRUD remains available independently. The stored `system_prompt_language` (`english` or `turkish`) still selects the prompt used for the turn.

### 7.12 Candidate Extraction & Review Workflow

**Location:** `spoilerless/app/api/candidates.py`, `spoilerless/app/graph/candidates.py`, `spoilerless/app/domain/extraction.py`. This is the intake path for an extraction pipeline.

`ExtractionBatchEnvelope` wraps a list of `ExtractionClaim` entries, the payload shape an NLP/extraction process would submit via `POST /api/series/{series_id}/candidates/ingest`. Each claim carries subject/predicate/object, evidence text + locator, source type + locator, and episode context.

Candidate claims, their sources, and their evidence fragments derive deterministic IDs from a SHA-256 hash of their own content (subject:predicate:object:evidence_text:evidence_locator:episode_id for the claim; source locator for the source; evidence_text:evidence_locator:episode_id for the evidence). This makes re-ingesting the same extraction batch a no-op `MERGE` rather than creating duplicates.

**Layering deviation:** `candidates.py` calls `CandidateRepository` directly — there is no `CandidateService`. The approve/reject/edit transaction logic lives in `CandidateRepository.approve_claim`/`reject_claim`/`edit_claim`, which call `RevisionRepository.log_revision` in the same mutation transaction (PROB-09 #60). Other API-layer bypasses include `user_content.py`, `share.py`, and `revisions.py` (revert runs `revisions.revert_revision_work` via `database.execute_write` — a repository-module work function, not a route closure).

```
POST .../candidates/ingest       → authenticated (not admin-only); origin/status candidate; idempotent MERGE
GET  .../candidates               → list; required persisted-episode boundary; anonymous
GET  .../candidates/{id}          → one claim; required persisted-episode boundary; anonymous
PATCH .../candidates/{id}         → edit mutable fields (admin-only)
POST .../candidates/{id}/approve  → status: candidate → canonical (409 if origin isn't candidate) (admin-only)
POST .../candidates/{id}/reject   → status: candidate → rejected (admin-only)
```

`PATCH .../candidates/{id}`, `POST .../approve`, and `POST .../reject` carry `RequireAdminDependency`. Ingest carries `CurrentUserDependency`; list/get remain anonymous but require a persisted-episode boundary. Every approve/reject/edit call logs the acting admin's ID in a `Revision` in the same transaction, returns the actual persisted revision ID, and invalidates the series graph cache.

### 7.13 Role-Based Access Control (Admin Role)

**Location:** `spoilerless/app/api/deps.py` (`require_admin`, `RequireAdminDependency`), `spoilerless/app/services/auth.py` (role derivation at login), `spoilerless/app/repository/user.py` (`role` persisted on the `(:AppUser)` node), `spoilerless/app/domain/auth.py` (`UserPublic.role: Literal["admin", "user"]`).

`role` is a two-value field — `"admin"` or `"user"` — assigned server-side at every login from `ADMIN_EMAILS` membership (a comma-separated, case-insensitive env allowlist), never accepted from the client or derived from any request body. `UserRepository.upsert()` re-syncs `role` on every login (`ON MATCH SET u.role = $role`), so removing an email from `ADMIN_EMAILS` demotes that user's role the next time they sign in — no database migration needed. Pre-migration `AppUser` records without a stored `role` default to `"user"` via `coalesce(u.role, 'user')` in `GET_USER_BY_ID_QUERY` and the `UserPublic` model's `default="user"`.

`require_admin` is a `CurrentUserDependency`-composed FastAPI dependency: it first resolves the authenticated user (`401 AUTH_UNAUTHENTICATED` if no valid session), then checks `user["role"] == "admin"`, raising `403 FORBIDDEN` otherwise. It gates six routes: `candidates.py`'s `PATCH .../{id}`, `POST .../approve`, `POST .../reject`; `change_set.py`'s `POST .../confirm`; and both `settings.py` routes (`GET`/`PUT /api/settings/llm`). The rationale across all six is that each is the step that commits externally-sourced content to the shared canonical graph, or mutates the shared LLM provider configuration.

Ordinary user-content writes, revision reverts, progress, chat, share management, candidate ingest, and ChangeSet propose/reject/revert remain available to any authenticated user. This is not an absence of ownership controls: user-content updates/deletes and revision reverts enforce owner-or-admin, chat/progress/ChangeSets are user-scoped, and share revoke enforces creator-or-admin. Public graph, series, candidate, revision, and user-content reads are boundary-gated rather than owner-private.

### 7.14 Redis-Backed Rate Limiting and Graph Response Cache

**Location:** `spoilerless/app/cache/redis_client.py`, `spoilerless/app/cache/graph_cache.py`, `spoilerless/app/services/rate_limit.py`. Both features share the one `redis.asyncio` client returned by `get_redis()` (`lru_cache`-decorated, mirroring `core/config.py::get_settings()`) and are gated on a single setting, `REDIS_URL` (production uses an Upstash `rediss://` TLS URL). An empty `REDIS_URL` disables both features as a no-op — local development without Redis runs unthrottled and always queries Neo4j directly — rather than crashing startup or failing requests.

**Rate limiting** (`services/rate_limit.py`) — a `RateLimiter` FastAPI dependency class backed by `pyrate-limiter`'s `RedisBucket` (one atomic Redis-Lua-scripted ZSET per window, correct across multiple concurrently-running backend workers/instances). Three module-level instances gate three route groups:

| Instance | Route(s) | Limit | Window | Identifier |
|---|---|---|---|---|
| `login_rate_limiter` | `POST /api/auth/google` | 10 requests | 300s (5 min) | client IP |
| `chat_send_rate_limiter` | Chat message send (streaming and non-streaming) | 20 requests | 60s | authenticated user id |
| `content_write_rate_limiter` | Every `user_content.py` write route (notes, custom nodes, custom relationships — create/update/delete) | 30 requests | 60s | authenticated user id, falling back to IP |

`rate_limit_identifier()` reads `request.state.user` (stamped by `require_current_user`) when present, else falls back to `request.client.host`. A request over the limit gets `429 TOO_MANY_REQUESTS` via the shared error envelope. `init_rate_limiter()` binds the Redis-backed `Limiter` to all three instances once, in `main.py`'s `lifespan()`, immediately after `database.open()`, guarded on non-empty `REDIS_URL`; until bound (or when unbound), every `RateLimiter.__call__()` is a no-op.

**Graph response cache** (`cache/graph_cache.py`) — a cache-aside layer in front of `GET /api/series/{series_id}/graph` and `GET /api/share/{token}/graph`. Cache keys are `graph:{series_id}:{effective_boundary}:{user_id or 'anon'}` with a 300-second TTL (`DEFAULT_GRAPH_TTL_SECONDS`); because the effective spoiler boundary is part of the key, a boundary change is always a correct cache miss with no explicit invalidation required. Content-changing routes that mutate a series' graph (`candidates.py`'s approve/reject/edit, `change_set.py`'s confirm, `user_content.py`'s custom-node/custom-relationship create/update) call `invalidate_series(series_id)` after a successful write, which coarsely deletes every cached entry for that series via `SCAN`+`DELETE` rather than attempting to re-derive which exact `(boundary, user)` combinations the write affected. Any Redis error on read or write is swallowed and treated as a cache miss/no-op — caching is a performance layer, never a hard dependency, and a Redis outage degrades every graph read back to always querying Neo4j directly.

### 7.15 Shareable View Snapshots

**Location:** `spoilerless/app/api/share.py`, `spoilerless/app/repository/share.py`, `spoilerless/app/domain/share.py`, `frontend/src/api/share.ts`, `frontend/src/components/share/ShareDialog.tsx`, `frontend/src/components/share/ShareView.tsx`.

Allows signed-in users to share tokenized, read-only snapshots of their current graph view (series ID + visible episode boundary) with unauthenticated recipients.

- **Token Security:** Raw share tokens are generated via `secrets.token_urlsafe(32)`. Only the SHA-256 hash (`token_hash`) is stored in Neo4j on `(:ShareToken)` nodes linked via `(:AppUser)-[:CREATED_SHARE]->(:ShareToken)`.
- **Expiration & Revocation:** Share links carry a default TTL of 30 days (`expires_at`). Users can view their active created share links (`GET /api/share`) and explicitly revoke them (`DELETE /api/share/{token}`). Expired or revoked share tokens are automatically purged by a background `sweep_expired()` task running in `main.py`'s lifespan loop every hour.
- **Spoiler Safety Invariant:** When an unauthenticated client requests `GET /api/share/{token}/graph`, the backend validates token presence, hash, and expiration, and then delegates directly to `GraphService.fetch_graph()` with the exact `visible_until_order` bound to the token record. The recipient receives only the spoiler-filtered graph payload for that snapshot boundary — no session cookie is required, and no data beyond the snapshot boundary can be requested through the token.
- **Creation boundary:** `POST /api/share` validates that the submitted boundary is a persisted episode order, but it does not compare that order with the creator's persisted watch progress. The token faithfully freezes the submitted valid order; callers—not a server-side progress clamp—currently define which valid episode becomes the snapshot.

### 7.16 Deployment Topology

Production topology is defined partly in-repo and partly by hosted-service configuration:

```text
Browser ──https──> Vercel static SPA (frontend/, app.spoilerless.net)
   │                    └─ VITE_API_BASE_URL (build time)
   └──── credentials-included HTTPS / SSE ──> Render FastAPI (render.yaml)
                                                    │
                                                    ├─ neo4j+s:// ──> Neo4j AuraDB
                                                    └─ rediss:// ──> Upstash Redis (optional)
```

`render.yaml` builds with `uv sync --frozen` and starts `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`. `frontend/vercel.json` supplies only the SPA catch-all rewrite. Cloudflare/custom-domain and hosted database/Redis settings are operator-managed rather than encoded as executable infrastructure in this repository. Locally, Vite runs on 5173, proxies `/api` to Uvicorn on 8000, and the loopback-bound Compose container exposes Neo4j HTTP/Bolt on 7474/7687.

---

## 8. Key Design Decisions

**D-01 — Spoiler filtering at the database layer.** Filtering happens in visibility-gated Cypher before retrieval. Core graph reads live in `spoiler/filter.py`; candidate, ChangeSet, chat, retrieval-tool, user-content, and revision modules also define spoiler-aware queries. This avoids transferring and then discarding hidden result sets.

**D-02 — Visibility boundaries on story-sensitive content.** Content nodes, content relationships, and claims carry `visible_from_order`; system/auth/session/progress/chat/ChangeSet/share/settings records do not universally carry it. Claims additionally carry optional `valid_from_order`/`valid_until_order` for time-bounded facts.

**D-03 — Claims projected as edges.** Visible canonical/candidate claims that survive the full claim/subject/object/evidence/source filters become `GraphEdge`s carrying `claim_id`. User-authored relationship Claims are emitted by a separate query as edge-only records with `claim_id: null`, but only when both endpoints satisfy the same series and visibility constraints used by node filtering. Structural edges also carry `claim_id: null`. The frontend therefore combines `claim_id` with `origin` when routing an edge.

**D-04 — Seven concurrent queries for the graph read.** `GraphService.fetch_graph()` runs seven independent Cypher queries via `asyncio.gather()` rather than one giant query, minimizing latency without complex query engineering.

**D-05 — Backend-only visibility authority.** The frontend never checks `visible_from_order`; `graphToElements()` maps all received data without filtering. If a node is in the response, it is safe to show.

**D-06 — Split watch progress with an optimistic client cache.** Neo4j persists both the highest confirmed `watched_through_order` and temporary `view_as_of_order`; the effective spoiler view is their minimum. `sessionStorage` caches only the effective view and is reconciled against `GET /progress`. Forward unlocks are confirmed and persisted, already-watched choices are view-only writes, and visitor mode is intentionally local-only. The hook keeps an optimistic local value if a confirm write fails, so persistence is normally server-authoritative but not a hard prerequisite for the immediate UI transition.

**D-07 — Asynchronous graph fetching with retry.** `useGraph` exposes an explicit `refetch()` via a `retryToken` counter distinct from the `seriesId`/`visibleUntilOrder` dependency, so a transient error gets a Retry button that re-issues the same request.

**D-08 — Immutable PATCH contracts.** PATCH routes accept only the mutable field (`content` for notes, `label` for custom nodes, `predicate` for custom relationships) — endpoints, origin, visibility, and ownership are immutable.

**D-09 — Visibility derived from entity, not client.** For creates, `visible_from_order` is derived from the referenced target entity, never accepted from the client — a note attached to a season-5 character is only visible to users who've reached season 5, regardless of what the client submits.

**D-10 — Authentication, ownership, and admin are distinct boundaries.** `role` is server-derived from `ADMIN_EMAILS`. Candidate review, ChangeSet confirm, and shared fallback settings require admin; candidate ingest and ordinary mutations require authentication; owner-or-admin checks protect user-content changes, revision reverts, and share revocation. Public reads are spoiler-boundary gated rather than user-private.

**D-11 — Redis is optional infrastructure when unconfigured, but failure handling differs by feature.** Rate limiting and the graph response cache share one client and gate on a single `REDIS_URL` setting; with an empty value, rate limiting remains unbound and cache operations are skipped. Graph-cache Redis exceptions are swallowed and reads fall through to Neo4j. Once Redis is configured, however, `init_rate_limiter()` startup failures and `try_acquire_async()` request-time failures are not caught locally and can propagate.

**D-12 — Tokenized shareable graph snapshots.** Share links allow authenticated users to share a read-only snapshot of their graph view. Raw tokens are never persisted (only SHA-256 hashes are stored), expired or revoked tokens return 404, and reads reuse the exact server-side spoiler filter without exposing interactive session features.

**D-13 — One ToolSpec registry for retrieval tools.** `retrieval/pipeline.py`'s `TOOL_SPECS` (name, description, Pydantic `input_model`, async `executor`, optional `result_bucket`, and `requires_user`/`requires_chat_session` flags) replaces the three parallel tables that previously had to stay in lockstep. Provider-facing `TOOL_SCHEMAS` are derived from the registry, dispatches resolve through `_TOOL_SPECS_BY_NAME`, and executors land rows in their declared bucket so accumulation never shape-sniffs.

**D-14 — One context-section registry, two consumers.** `retrieval/context.py`'s `CONTEXT_SECTIONS` (and derived `CONTEXT_DELIMITERS`) is the single fixed-order contract for the RAG context layout: `assemble_context` renders sections in its order and `llm/system_prompt.py` imports the delimiter names — the cross-file "keep in sync" duplication is gone.

**D-15 — Shared infrastructure helpers.** `neo4j_row_to_python()` + `run_single()` (`graph/database.py`), `hash_token()`/`generate_token()` (`core/tokens.py`), and `NODE_LABELS`/`STORY_LABELS` (`graph/labels.py`) replace byte-identical per-module copies of row normalization, run-single-raise, token hashing, and label inventories.

**D-16 — The last-known-good graph stays mounted.** `App` keeps the most recent successful `GraphResponse` mounted; refetch and boundary loads render a loading/error overlay above it instead of unmounting the canvas and forcing a full relayout (first-load failures still show full-screen states).

**D-17 — One highlight path.** `lib/graph/highlight.ts`'s `applyHighlight()` unifies search selection, ⌘K jump focus, and reveal-pulse highlighting: clear stale classes → resolve ids → add classes → optional edge-label reveal, fade, and fit — replacing duplicated per-feature class manipulation.

**D-18 — Concurrent ChangeSet target validation.** `_validate_and_protect` gathers the independent per-target visibility reads with `asyncio.gather` instead of running them serially.

**D-19 — One persisted-episode-order check.** `BOUNDARY_QUERY` in `spoiler/filter.py` is the single episode-boundary validation shared by the graph, export, candidate, and share-create paths. Separately, `CHANGE_SET_CREATE_QUERY`'s explicit `WITH u, s` eliminated the local Neo4j 5.x `503` failure class in the ChangeSet create path.

---

## 9. Future Extensibility Points

- **Additional retrieval tools** — new allowlisted functions in `spoilerless/app/retrieval/tools.py` registered as `ToolSpec`s in `retrieval/pipeline.py`'s `TOOL_SPECS`, each following the fail-closed visibility pattern.
- **Additional LLM providers** — new implementations of the `LLMProvider` protocol in `spoilerless/app/llm/provider.py` (`gemini` and `openai_compatible` ship today).
- **Richer grounding** — e.g. multi-hop path explanations surfaced through the existing citation model.
- **Auto-extraction pipeline** — NLP-driven claim/relationship extraction feeding the existing candidate-review workflow and reusing the `confidence_level` enum. Today review transitions directly from `candidate` to `canonical` on approval or to `rejected` on rejection; a staged `candidate → corroborated → canonical` progression would be future work.
- **Multi-series support** — most story-content queries are parameterized by `series_id`. `AppUser`, `Session`, and `AppSetting` are global application records; `ShareToken` is globally addressable by token but stores `series_id` and a boundary for one series snapshot. The seed loader currently loads dataset files from `data/dexter/`, so adding a series requires generalizing seed-loading paths as well as adding data (and updating the ontology if new types are needed).
- **Cleanup scaling** — session/share cleanup already runs hourly in the FastAPI lifespan; a future deployment with multiple workers could move this periodic work to a dedicated scheduler.
- **Real-time collaboration** — a future extension could add WebSocket routes and content-change notifications.
- **Ontology evolution** — the versioned ontology system supports declared additions, but unknown node, relationship, claim, status, or confidence types raise `OntologyValidationError` and fail seed validation rather than being skipped.

### Normative follow-ups (planned, not implemented)

- **Close retrieval-hop gaps:** every retrieval query should visibility-gate the matched Claim and every subject/object/source/evidence hop before returning rows or aggregate counts.
- **Expand CSRF coverage:** login and logout validate `Origin`/`Referer`, but other cookie-authenticated state-changing routes do not attach that dependency; CORS and SameSite are the remaining controls on those paths.
- **Unify read boundaries:** candidate reads now require a persisted-episode boundary, while user-content/revision reads accept any positive integer and graph/export clamp authenticated users to progress. A single server-authoritative resolver would remove these route-family differences.
- **Decouple pathfinding from hop count:** `/graph/path` currently uses `MAX_PATH_HOPS` as its requested episode order because `PathRequest` has no boundary field. Resolve the view independently from `max_hops` before treating it as equivalent to graph/export.
- **Scope shared settings:** `GET`/`PUT /api/settings/llm` are admin-gated, closing the unauthenticated exposure, but the underlying `AppSetting` record is still a single shared global configuration rather than per-user, and the existing http(s)-scheme check on `base_url` does not prevent an admin from redirecting the shared provider to an external host.

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
| `VITE_GOOGLE_CLIENT_ID` | `""` | Frontend Google OAuth client ID (browser build); backend startup validates it equals `GOOGLE_CLIENT_ID` |
| `SESSION_COOKIE_NAME` | `session` | HttpOnly cookie name |
| `SESSION_TTL_SECONDS` | `604800` | Session lifetime (7 days) |
| `SESSION_COOKIE_SAMESITE` | `lax` | `SameSite` policy on the session cookie |
| `SESSION_COOKIE_SECURE` | `True` | Secure flag on the session cookie (set `false` for local HTTP dev) |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowed origins; also drives `verify_origin` CSRF checks |
| `ALLOWED_EMAILS` | `""` | Comma-separated sign-in allowlist; empty permits any verified Google account |
| `ADMIN_EMAILS` | `""` | Comma-separated allowlist granted the `admin` role at login |
| `REDIS_URL` | `""` | Redis URL enabling rate limiting and graph cache; production uses an Upstash `rediss://` URL |
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
