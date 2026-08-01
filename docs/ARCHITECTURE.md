# HD Graf Cehennemi — Architecture Guide

> **Version:** 0.1.0
> **Last updated:** 2026-07-30
> **Project:** Spoiler-aware TV series knowledge graph

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture Layers](#2-architecture-layers)
3. [Layer-by-Layer Breakdown](#3-layer-by-layer-breakdown)
   - [3.1 Frontend (React + Cytoscape)](#31-frontend-react--cytoscape)
   - [3.2 API Layer (FastAPI)](#32-api-layer-fastapi)
   - [3.3 Service Layer](#33-service-layer)
   - [3.4 Repository & Database Layer](#34-repository--database-layer)
   - [3.5 Neo4j Graph Database](#35-neo4j-graph-database)
4. [Cross-Cutting Concerns](#4-cross-cutting-concerns)
   - [4.1 Spoiler-Aware Data Flow](#41-spoiler-aware-data-flow)
   - [4.2 The Claim Model](#42-the-claim-model)
   - [4.3 Ontology System](#43-ontology-system)
   - [4.4 Origin System](#44-origin-system)
   - [4.5 Authentication & Sessions](#45-authentication--sessions)
   - [4.6 Error Handling](#46-error-handling)
   - [4.7 Revision History](#47-revision-history)
   - [4.7.1 Append-only Revision extension](#471-append-only-revision-extension)
   - [4.8 GraphRAG-Lite Chat Pipeline](#48-graphrag-lite-chat-pipeline)
   - [4.9 ChangeSet Two-Stage Mutation Flow](#49-changeset-two-stage-mutation-flow)
   - [4.10 Spoiler-Safety Invariants](#410-spoiler-safety-invariants)
5. [Data Flow Examples](#5-data-flow-examples)
6. [Key Design Decisions](#6-key-design-decisions)
7. [Future Extensibility Points](#7-future-extensibility-points)

---

## 1. System Overview

HD Graf Cehennemi is a **spoiler-aware TV series knowledge graph** application. It lets users explore character relationships, events, locations, and narrative claims from a TV series — all filtered by how much of the series they've watched. The core architectural invariant is that **spoilery content is never transmitted to the client** if the user hasn't progressed far enough.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React 19 + Vite)               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌───────────┐ │
│  │ Series   │  │ Episode      │  │ GraphCanvas│  │ Detail    │ │
│  │ Select   │  │ Selector     │  │ (Cytoscape)│  │ Panel     │ │
│  └──────────┘  └──────────────┘  └───────────┘  └───────────┘ │
│                         │ http://localhost:5173                  │
│                         │ Vite proxy → :8000                    │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI + Uvicorn)                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  API Layer (backend/app/api/)                               ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐ ┌───────────┐ ││
│  │  │ series.py│ │graph.py  │ │auth.py   │ │user_content   │ │revisions │ ││
│  │  │          │ │          │ │          │ │.py            │ │.py       │ ││
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘ └───────────┘ ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Service Layer (backend/app/services/)                      ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐                    ││
│  │  │ series.py│ │graph.py  │ │auth.py   │                    ││
│  │  └──────────┘ └──────────┘ └──────────┘                    ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Repository Layer (backend/app/repository/)                 ││
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           ││
│  │  │ user.py     │ │session.py   │ │user_content │           ││
│  │  │ (Neo4j)     │ │(In-Memory)  │ │.py (Neo4j)  │           ││
│  │  └─────────────┘ └─────────────┘ └─────────────┘           ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Database Layer (backend/app/graph/)                        ││
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      ││
│  │  │database  │ │ontology  │ │seed.py   │ │setup.py  │      ││
│  │  │.py       │ │.py       │ │          │ │          │      ││
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                          │ bolt://localhost:7687
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Neo4j Community (Docker)                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Constraints, Indexes, Graph Nodes & Relationships          ││
│  │  Labels: Series, Episode, Character, Event, Location,       ││
│  │  Organization, Object, Claim, Source, EvidenceFragment,     ││
│  │  UserNote, AppUser                                          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Stack Summary

| Layer | Technology |
|---|---|
| Frontend | React 19, TypeScript 6, Vite 8, Cytoscape.js 3 + cose-bilkent |
| UI Library | Radix UI, shadcn/ui, Tailwind CSS 4, Lucide icons |
| Backend | Python 3.13, FastAPI 0.140+, Uvicorn |
| Database | Neo4j 2026 Community via Docker |
| Graph Driver | neo4j 6.2+ (async Python driver) |
| Auth | Google Sign-In (ID token verification via google-auth) |
| Container | Docker Compose |
| Package | uv (Python), npm (frontend) |

---

## 2. Architecture Layers

The backend follows a strict layered architecture with clear dependency direction:

```
┌──────────────────────┐
│      API Layer       │  ← HTTP handlers, routing, request validation
├──────────────────────┤
│    Domain Models     │  ← Pydantic schemas shared across layers
├──────────────────────┤
│   Service Layer      │  ← Business logic orchestration
├──────────────────────┤
│  Repository Layer    │  ← Data access abstraction
├──────────────────────┤
│  Database Layer      │  ← Neo4j driver, connection management
├──────────────────────┤
│  Spoiler Filter      │  ← Cypher queries with built-in visibility gating
│  (backend/app/spoiler)│
└──────────────────────┘
```

**Key rule:** Each layer depends only on the layer directly below it. Domain models are shared across all layers.

---

## 3. Layer-by-Layer Breakdown

### 3.1 Frontend (React + Cytoscape)

**Location:** `frontend/`

The frontend is a single-page application that renders an interactive knowledge graph using Cytoscape.js.

#### Directory Structure

```
frontend/src/
├── api/              # HTTP client layer
│   ├── client.ts     # Shared fetch wrapper with ApiError
│   ├── graph.ts      # GET /api/series/{id}/graph
│   └── series.ts     # GET /api/series, /api/series/{id}/episodes
├── components/
│   ├── detail/       # DetailPanel, StructuralEdgeCard
│   ├── episode/      # EpisodeSelector, SeriesSelect, ConfirmAdvanceModal
│   ├── graph/        # GraphCanvas, graphElements, graphStylesheet, GraphStatus
│   ├── layout/       # AppShell
│   └── ui/           # shadcn/ui primitives (alert, badge, button, card, etc.)
├── hooks/
│   ├── useGraph.ts       # Graph fetching with retry
│   ├── useWatchProgress.ts  # sessionStorage-backed watch progress
│   ├── useSeries.ts      # Series list fetching
│   └── useEpisodes.ts    # Episode list fetching
├── types/
│   ├── graph.ts      # Mirrors backend domain/graph.py
│   └── series.ts     # Mirrors backend domain/series.py
└── test/fixtures/    # Test data
```

#### Key Components

**`GraphCanvas.tsx`** — The core visualization component. Wraps `react-cytoscapejs` with:
- **cose-bilkent layout** as the primary graph layout algorithm (falls back to built-in `cose` on failure)
- Tap-driven selection: tapping a node highlights its closed neighborhood and dims everything else
- Hover tooltips for truncated labels
- Layout re-run on graph data change (episode boundary progression)

**`graphElements.ts`** — Pure function mapping `GraphResponse` → Cytoscape `ElementDefinition[]`. The backend has already applied the spoiler filter; this function never re-filters by `visible_from_order`.

**`graphStylesheet.ts`** — Full Cytoscape stylesheet mapping:
- Node types to shapes: Character → ellipse, Event → round-rectangle, Location → round-rectangle, Organization → diamond, Episode → tag, Series → star, UserNote → dashed round-rectangle
- Origin treatment: canonical nodes get solid borders, others get dashed
- Selection/fade: faded class at 0.25/0.15 opacity, selected-dominant with accent border

**`useWatchProgress.ts`** — sessionStorage-backed state machine with three states:
- `confirmedOrder` — the actual spoiler boundary
- `pendingChange` — an unconfirmed forward/backward jump (triggers confirmation modal)
- Hydration from sessionStorage on mount (no modal on page refresh)

**`App.tsx`** — Root component orchestrating:
- Series selection → episode list loading → watch progress state → graph fetching
- Centralized D-06/D-07 branch: routes structural edges to `StructuralEdgeCard` and claim-backed edges to `DetailPanel`
- Modal confirmation for watch-progress changes

#### Vite Configuration

The dev server proxies `/api` requests to the backend at `http://127.0.0.1:8000`, avoiding CORS issues during development.

---

### 3.2 API Layer (FastAPI)

**Location:** `backend/app/api/`

Nine route modules registering 42 HTTP operations across 31 unique path templates (plus `/health`). The authoritative locked inventory lives in [docs/frontend-api-contract.md](frontend-api-contract.md) and is verified by `backend/tests/test_openapi_contract.py` and `backend/tests/test_frontend_contract_doc.py`.

#### Route Inventory

| Module | Path | Methods | Purpose |
|---|---|---|---|
| `series.py` | `/api/series` | GET | List all series |
| `series.py` | `/api/series/{series_id}` | GET | Get one series |
| `series.py` | `/api/series/{series_id}/episodes` | GET | List episodes (no spoiler filter) |
| `graph.py` | `/api/series/{series_id}/graph` | GET | Spoiler-safe graph read |
| `user_content.py` | `/api/series/{series_id}/notes` | GET, POST | List/create user notes |
| `user_content.py` | `/api/series/{series_id}/notes/{note_id}` | GET, PATCH, DELETE | CRUD one note |
| `user_content.py` | `/api/series/{series_id}/custom-nodes` | POST | Create custom node |
| `user_content.py` | `/api/series/{series_id}/custom-nodes/{node_id}` | GET, PATCH, DELETE | CRUD one custom node |
| `user_content.py` | `/api/series/{series_id}/custom-relationships` | POST | Create custom relationship |
| `user_content.py` | `/api/series/{series_id}/custom-relationships/{relationship_id}` | GET, PATCH, DELETE | CRUD one relationship |
| `revisions.py` | `/api/series/{series_id}/revisions` | GET | List visible revisions |
| `revisions.py` | `/api/series/{series_id}/revisions/{revision_id}` | GET | Get one revision |
| `revisions.py` | `/api/series/{series_id}/revisions/{revision_id}/revert` | POST | Revert to a revision |
| `progress.py` | `/api/series/{series_id}/progress` | GET, POST | Read/update persisted watch progress |
| `chat.py` | `/api/series/{series_id}/chat/sessions` | GET, POST | List/create chat sessions |
| `chat.py` | `/api/series/{series_id}/chat/sessions/{session_id}` | GET, DELETE | Get/delete one session |
| `chat.py` | `/api/series/{series_id}/chat/sessions/{session_id}/messages` | POST | Non-streaming chat turn (fallback) |
| `chat.py` | `/api/series/{series_id}/chat/sessions/{session_id}/messages/stream` | POST | Streaming chat turn (SSE) |
| `change_set.py` | `/api/series/{series_id}/change-sets` | POST | Propose a ChangeSet (Stage 1) |
| `change_set.py` | `/api/series/{series_id}/change-sets/{change_set_id}/confirm` | POST | Confirm a ChangeSet (Stage 2) |
| `change_set.py` | `/api/series/{series_id}/change-sets/{change_set_id}/reject` | POST | Reject a ChangeSet |
| `change_set.py` | `/api/series/{series_id}/change-sets/{change_set_id}/revert` | POST | Revert an applied ChangeSet (Stage 3) |
| `candidates.py` | `/api/series/{series_id}/candidates` | GET | List candidate claims |
| `candidates.py` | `/api/series/{series_id}/candidates/ingest` | POST | Ingest extraction batch as candidates |
| `candidates.py` | `/api/series/{series_id}/candidates/{claim_id}` | GET, PATCH | Get/edit one candidate claim |
| `candidates.py` | `/api/series/{series_id}/candidates/{claim_id}/approve` | POST | Approve candidate → corroborated |
| `candidates.py` | `/api/series/{series_id}/candidates/{claim_id}/reject` | POST | Reject candidate |
| `auth.py` | `/api/auth/google` | POST | Google Sign-In |
| `auth.py` | `/api/auth/me` | GET | Current user from session |
| `auth.py` | `/api/auth/logout` | POST | Logout |
| `main.py` | `/health` | GET | Health check |

#### Architecture Pattern

Each route module follows a consistent pattern:
1. FastAPI `APIRouter` with prefix and tags
2. Typed dependencies via `Annotated` (FastAPI's `Depends` typing)
3. Constructor-injected services/repositories
4. Standard error envelope via `core/errors.py`
5. Pydantic domain models for request/response validation

#### Graph Route — The Critical Read Path

`GET /api/series/{series_id}/graph?visible_until_order=N`

This is the most architecturally significant endpoint. It:
1. Validates the series exists
2. Resolves the boundary against persisted episode orders
3. Delegates to `GraphService.fetch_graph()` which runs **7 concurrent Cypher queries**
4. Returns a closed-form `GraphResponse` containing all visible nodes, edges, claims, sources, and evidence

---

### 3.3 Service Layer

**Location:** `backend/app/services/`

Service classes encapsulate business logic:

#### `GraphService` (`graph.py`)
- Orchestrates the spoiler-safe graph read
- `fetch_graph()` runs 7 Cypher queries concurrently via `asyncio.gather()`:
  1. Series metadata
  2. Visible nodes (all types with `visible_from_order <= boundary`)
  3. Structural edges (PART_OF, PRECEDES, OCCURRED_IN)
  4. Visible claims (canonical + candidate, non-user-authored)
  5. Visible user-authored relationships
  6. Sources referenced by visible claims
  7. Evidence fragments backing visible claims
- **Projects claim edges:** Each visible claim is projected as a `GraphEdge` with `claim_id` set, linking subject→object with the claim's predicate as the edge type
- Assembles the complete `GraphResponse`

#### `SeriesService` (`series.py`)
- Thin wrapper: lists series, gets one series, lists episodes
- No spoiler filtering (episode metadata is not spoilery)

#### `AuthService` (`auth.py`)
- Google ID token verification via `ProductionGoogleVerifier` (injectable for tests)
- User upsert (create or update by `google_sub`)
- Session creation, retrieval, refresh, and revocation
- All session tokens are SHA-256 hashed before storage; raw tokens never persisted

#### `ProgressService` (`progress.py`)
- Resolves the persisted watch-progress boundary for a user + series from the graph (`(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)-[:FOR_SERIES]->(:Series)`)
- Server-authoritative: the frontend cannot raise `visible_until_order` through a request; missing progress fails safe (lowest boundary)
- Persists progress updates; decreasing progress is allowed and hides future-boundary chat messages (hide-not-delete)

#### `ChatService` (`chat.py`)
- Owns the GraphRAG-lite turn lifecycle: resolve boundary → load spoiler-filtered history → run the retrieval pipeline → stream the grounded answer back as SSE
- Persists every `ChatMessage` with a `visible_until_order_snapshot` equal to the boundary resolved at turn time, so later boundary decreases can hide (never delete) previously generated future-boundary messages
- Records a `ChangeSet` reference on the assistant message when the pipeline proposes one

#### `ChangeSetService` (`change_set.py`)
- Stage 1 **propose**: validates a typed operation list (13 operation types, Pydantic `extra="forbid"` discriminated union) against the ontology and the resolved boundary — no database write happens at propose time
- Stage 2 **confirm/apply**: applies the validated operations in a single Neo4j transaction, idempotent via `idempotency_key`, stale-safe via `visible_until_order_snapshot` comparison, and logs a `Revision` in the same transaction
- Stage 3 **revert**: restores the pre-apply state for create-shaped ChangeSets (well-defined delete); refuses when later unrelated changes conflict

---

### 3.4 Repository & Database Layer

**Location:** `backend/app/repository/`, `backend/app/graph/`

#### `Neo4jDatabase` (`graph/database.py`)

The central database abstraction:
- Lazy-initialized async Neo4j driver (no import-time side effects)
- `open()` / `close()` lifecycle managed by FastAPI lifespan
- `execute_query(query, **params)` — retryable read/write Cypher execution, returns `list[dict]`
- `execute_write(work, command)` — managed transaction wrapper for write operations
- `verify_connection()` — health check

#### `UserRepository` (`repository/user.py`)
- `upsert()` — MERGE on `google_sub`, sets all profile fields
- `get_by_id()` — lookup by application-local user ID
- Users stored as `(:AppUser)` nodes for future graph relationship linking

#### `InMemorySessionRepository` (`repository/session.py`)
- Sessions live outside Neo4j (ephemeral, in-memory)
- Token hashing via SHA-256; raw `secrets.token_urlsafe(48)` tokens
- Lazy expiry on read (no background sweep)
- Protocol-based design: swap for Redis/DB in production

#### `UserContentRepository` (`repository/user_content.py`)
- Manages notes, custom nodes, and custom relationships in Neo4j
- All queries are parameterized and stored as module-level constants
- Visibility is **derived from the target entity** (notes inherit target's `visible_from_order`, custom relationships use `MAX(source, target, episode)`)
- Validates namespacing (`user-note:`, `user-node:`, `user-rel:` prefixes)
- Ownership gated by `origin = 'user'`
- Delete protection: custom nodes with attached notes/claims return 409 conflict

---

### 3.5 Neo4j Graph Database

**Location:** Docker Compose, `backend/app/graph/seed.py`

#### Container

```yaml
services:
  neo4j:
    image: neo4j:2026-community
    ports: [7474:7474, 7687:7687]
    volumes: [neo4j_data, neo4j_logs, neo4j_import, neo4j_plugins]
```

#### Node Labels

| Group | Labels |
|---|---|
| Structural | `Series`, `Season`, `Episode`, `Scene` |
| Narrative | `Character`, `Location`, `Organization`, `Object`, `Event` |
| Knowledge | `Claim`, `Source`, `EvidenceFragment` |
| User | `UserNote` |
| System | `Revision`, `AppUser` |

#### Relationship Types

| Group | Types |
|---|---|
| Structural | `PART_OF`, `PRECEDES`, `OCCURRED_IN`, `LOCATED_IN` |
| Participation | `PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED` |
| Character | `KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS` |
| Provenance | `SUPPORTED_BY`, `CONTRADICTED_BY`, `DERIVED_FROM`, `REFERS_TO` |
| Revision | `CORRECTS`, `SUPERSEDES`, `REVERTS_TO` |

#### Constraints & Indexes

Created idempotently during `setup_database()`:
- Uniqueness constraints on `n.id` for every node label
- Range indexes on `visible_from_order` for all node labels
- Specific indexes on `series_id` for Episode, Character, Event, Location, Claim, Source, EvidenceFragment, Organization, Object, UserNote
- Composite index on `UserNote(series_id, target_type, target_id)`
- Index on `Episode.episode_order`

> **Note:** Property existence constraints require Neo4j Enterprise and are intentionally omitted. Null visibility is prevented through Pydantic validation, service-layer guards, and a post-seed integrity audit.

#### Seed Data

The `setup_database()` pipeline:
1. Load seed JSON from `data/dexter/` (series metadata, episodes, characters, events, locations, claims, sources, evidence fragments)
2. Validate against ontology (node types, relationship types, claim types, claim statuses, confidence levels, ID uniqueness, evidence completeness)
3. Create constraints and indexes
4. Upsert all nodes via `MERGE`
5. Create structural relationships (PART_OF, PRECEDES, OCCURRED_IN)
6. Create provenance relationships (SUPPORTED_BY, REFERS_TO)
7. Run visibility integrity audit

---

## 4. Cross-Cutting Concerns

### 4.1 Spoiler-Aware Data Flow

This is the **core architectural invariant** of the system. Spoiler filtering happens entirely on the backend — the frontend never receives data to hide.

#### The `visible_from_order` Mechanism

Every node, relationship, and claim in the graph carries a `visible_from_order` integer field. This represents the earliest episode order at which the entity is "visible" (i.e., no longer a spoiler).

The `visible_until_order` query parameter represents how far the user has watched. The backend's Cypher queries apply a universal filter:

```cypher
WHERE entity.visible_from_order <= $visible_until_order
```

#### Fail-Closed Design

- Missing, malformed, zero, negative, or non-persisted boundaries return **422** responses
- The boundary must match a persisted episode's `episode_order`
- Every entity in a query chain (claim → subject → object → evidence → source) must individually satisfy the visibility filter
- Hidden direct reads (e.g., `GET /notes/{id}` for a future note) return indistinguishable **404** responses
- Response collections contain no counts or metadata

#### Claim Temporal Validity

Claims can have optional `valid_from_order` and `valid_until_order` for time-bounded claims (e.g., a character's temporary allegiance):

```cypher
AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
```

#### The Spoiler Filter Module

**Location:** `backend/app/spoiler/filter.py`

Contains all parameterized Cypher queries as raw Python string constants. This module is intentionally isolated — it has no FastAPI or Pydantic dependencies. Every query is a closed form with `$series_id` and `$visible_until_order` parameters.

**Seven query families:**
1. `SERIES_LIST_QUERY` / `SERIES_BY_ID_QUERY` — no spoiler filter (metadata is public)
2. `SERIES_EPISODES_QUERY` — no spoiler filter (episode names/orders are public)
3. `NODES_QUERY` — all story nodes filtered by `visible_from_order`
4. `STRUCTURAL_EDGES_QUERY` — PART_OF/PRECEDES/OCCURRED_IN edges with filter on source, target, and edge
5. `VISIBLE_CLAIMS_QUERY` — claims with origin `canonical` or `candidate`, not `user_authored`; includes temporal validity
6. `VISIBLE_USER_RELATIONSHIPS_QUERY` — user-authored relationships with `claim_type = 'user_authored'` and `origin = 'user'`
7. `SOURCES_QUERY` / `EVIDENCE_QUERY` — provenance chain filtered on every hop

### 4.2 The Claim Model

Claims are the **core knowledge representation** in the system. A claim represents a statement about the narrative world.

#### Claim Structure

```
Claim {
  id: string             # e.g., "claim:dexter_kills_the_ice_truck_killer"
  label: string          # Human-readable summary
  subject_id: string     # ID of the subject node
  predicate: string      # Relationship type (e.g., "KILLS")
  object_id: string      # ID of the object node
  claim_type: string     # explicit_fact | observed_event | inferred_state |
                         # external_interpretation | user_authored
  status: string         # candidate | corroborated | canonical | disputed | rejected
  confidence_level: string  # low | medium | high | verified
  relationship_effect: float  # Numeric weight for visualization
  visible_from_order: int
  valid_from_order: int | null    # Temporal validity start
  valid_until_order: int | null   # Temporal validity end
  source_id: string
  evidence_ids: string[]
  origin: string         # canonical | candidate | user
}
```

#### Claim Provenance Chain

```
Claim ──SUPPORTED_BY──► EvidenceFragment ──REFERS_TO──► Source
  │                                                          
  └─────────────────────REFERS_TO───────────────────────────► Source
```

Every automatic claim requires:
1. At least one `EvidenceFragment` (linked by `SUPPORTED_BY`)
2. A `Source` (linked by `REFERS_TO`) that each evidence fragment also references
3. Evidence includes the actual text excerpt, locator, and content hash

#### User-Authored Claims (Custom Relationships)

User-created relationships are stored as `Claim` nodes with:
- `claim_type: 'user_authored'`
- `origin: 'user'`
- `id` prefixed with `user-rel:`
- No evidence or source requirement (the user is the authority)

They appear in the graph response as `GraphEdge`s via the `VISIBLE_USER_RELATIONSHIPS_QUERY`, not through the regular `VISIBLE_CLAIMS_QUERY`.

#### Origin Distinguishability

Automatic and user-created content must remain distinguishable:
- `origin: canonical` — curated, canonical data from seed
- `origin: candidate` — automatically extracted, awaiting review
- `origin: user` — user-created content

This is never collapsed into a boolean flag. The visual treatment differs: canonical gets solid borders, others get dashed.

### 4.3 Ontology System

**Location:** `ontology/` directory

The ontology is versioned via YAML files that define the graph's type system. Each file carries an `ontology_version: "0.1"` declaration.

#### `node_types.yaml`
```
structural: [Series, Season, Episode, Scene]
narrative: [Character, Location, Organization, Object, Event]
knowledge: [Claim, Source, EvidenceFragment]
user: [UserNote]
system: [Revision]
```

#### `relation_types.yaml`
```
structural: [PART_OF, PRECEDES, OCCURRED_IN, LOCATED_IN]
participation: [PARTICIPATED_IN, WITNESSED, CAUSED, AFFECTED, TARGETED, MENTIONED]
character: [KNOWS, FAMILY_OF, WORKS_WITH, TRUSTS, DISTRUSTS, HELPS, OPPOSES, THREATENS, ATTACKS, KILLS]
provenance: [SUPPORTED_BY, CONTRADICTED_BY, DERIVED_FROM, REFERS_TO]
revision: [CORRECTS, SUPERSEDES, REVERTS_TO]
```

#### `claim_types.yaml`
```
claim_types: [explicit_fact, observed_event, inferred_state, external_interpretation, user_authored]
claim_statuses: [candidate, corroborated, canonical, disputed, rejected]
confidence_levels: [low, medium, high, verified]
```

#### Runtime Validation (`graph/ontology.py`)

The `Ontology` dataclass is created by `load_ontology()` which reads all three YAML files, validates the version, and creates immutable type sets. It provides:
- `require_node_type()`, `require_relationship_type()`, `require_claim_type()` — validation methods that raise `OntologyValidationError`
- `user_safe_node_types` / `user_safe_relationship_types` — subset of types users can create
- Version-gated: mismatched `ontology_version` raises on load

### 4.4 Origin System

The `origin` field is a `StrEnum` with exactly three values: `canonical`, `candidate`, `user`.

- **`canonical`** — Curated, seed data; the authoritative ground truth
- **`candidate`** — Automatically extracted or suggested; not yet reviewed
- **`user`** — User-created content (notes, custom nodes, custom relationships)

Visual consequences:
- Canonical nodes get solid borders in the graph
- Non-canonical nodes (candidate, user) get dashed borders
- Custom relationship edges appear via their own query path

The frontend contract explicitly forbids branching on a `'curated'` string — the actual wire value is `'canonical'`.

### 4.5 Authentication & Sessions

#### Google Sign-In

1. Frontend initiates Google Sign-In with the Google Identity Services library
2. Google returns an ID token (JWT)
3. Frontend sends token to `POST /api/auth/google`
4. Backend verifies: signature, issuer (`accounts.google.com`), audience (`GOOGLE_CLIENT_ID`), expiration
5. User record upserted in Neo4j (keyed on Google's `sub` claim)
6. Session created with SHA-256-hashed token
7. HttpOnly, SameSite=Lax cookie set on response

#### Session Management

- Sessions stored in `InMemorySessionRepository` (memory-resident `dict`; swap for Redis in production)
- Token hash (SHA-256) stored server-side; raw 48-byte URL-safe token in cookie
- Configurable TTL (default: 7 days)
- Lazy expiry on read; no background sweep
- `GET /api/auth/me` reads cookie, validates session, refreshes TTL
- `POST /api/auth/logout` revokes session, clears cookie (always 204)

#### CSRF Strategy

- Baseline: `SameSite=Lax` on cookies
- State-changing requests require same-origin or configured CORS frontend origin
- Future: custom header check (`X-Requested-With`) as secondary defense

### 4.6 Error Handling

**Location:** `backend/app/core/errors.py`

Structured error envelope shared by all endpoints:

```json
{
  "detail": {
    "code": "series_not_found",
    "message": "Series not found."
  }
}
```

#### Stable Error Codes

| Status | Code | When |
|---|---|---|
| 401 | `unauthenticated` | No valid session |
| 401 | `authentication_failed` | Token verification failed |
| 401 | `auth_disabled` | Google auth not configured |
| 404 | `series_not_found` | Series lookup missed |
| 404 | `resource_not_found` | Hidden or absent resource |
| 409 | `resource_conflict` | Ownership violation or dependency |
| 422 | `invalid_request` | Validation failure |
| 422 | `invalid_visible_until_order` | Bad boundary value |
| 503 | `database_unavailable` | Neo4j unreachable |

#### Error Handler Installation

`install_error_handlers()` registers:
- `RequestValidationError` → 422 (sanitized, never exposes field names)
- `ConstraintError` → 409 (Neo4j constraint violation)
- `ServiceUnavailable`, `AuthError`, `ClientError`, `Neo4jError` → 503

Database error messages are intentionally generic — never leak Cypher, connection details, or database internals.

### 4.7 Revision History

**Location:** `backend/app/revisions/`

The `Revision` module provides a version history model. Revisions are Neo4j `(:Revision)` nodes.

**Status:** Backend fully integrated. Every user-content mutation (note create/update/delete, custom-node create/update/delete, custom-relationship create/update/delete) auto-creates a `Revision` record in the same Neo4j transaction. API routes:

| Route | Method | Purpose |
|-------|--------|---------|
| `GET /api/series/{series_id}/revisions` | GET | List visible revisions, most-recent-first, with optional `resource_type`/`resource_id` filters |
| `GET /api/series/{series_id}/revisions/{revision_id}` | GET | Get one revision (hidden revisions return 404) |
| `POST /api/series/{series_id}/revisions/{revision_id}/revert` | POST | Restore resource to the state captured in the revision. Creates a new `Reverted` revision — history never destroyed |

**Frontend:** History tab fully integrated. The `frontend/src/types/revision.ts` types, `frontend/src/api/revisions.ts` API client, and `frontend/src/hooks/useRevisions.ts` hook provide the data layer. The `RevisionHistoryPanel` component renders a History tab in `DetailPanel` with color-coded action badges (Created/Updated/Deleted/Reverted), diff summary chips, and a one-shot revert flow with confirmation dialog and toast feedback. Revert button only appears on `Updated` and `Deleted` revisions. All dialog buttons use inline Tailwind (no DaisyUI). (Plans 04-04, 04-05 executed.)

#### 4.7.1 Append-only Revision extension

The Revision model is **append-only**: no revision is ever deleted or mutated in place. Every user-content mutation creates a new `Revision` node capturing before/after JSON snapshots in the **same Neo4j transaction** as the mutation (via the `RevisionRepository.log_revision` pattern). Reverting restores the captured state by creating a *new* `Reverted` revision — history is never destroyed, so the full audit trail always reconstructs "what changed, when, and by whom."

ChangeSet applies extend this invariant: confirming a ChangeSet applies its operations and logs a single `Revision` in the same transaction (the ChangeSet response carries `revision_id`). Reverting an applied ChangeSet is itself a `Reverted` revision. The result is one coherent audit chain: `Revision → ChangeSet apply → Revision (Reverted)`.

---

## 4.8 GraphRAG-Lite Chat Pipeline

**Location:** `backend/app/retrieval/` (`pipeline.py`, `tools.py`), `backend/app/llm/` (`provider.py`, `system_prompt.py`), `backend/app/services/chat.py`

The chat feature is a **GraphRAG-lite** pipeline: the LLM answers questions by calling a small set of allowlisted retrieval tools against the spoiler-filtered graph, and every answer is grounded in citations that are validated against what was actually retrieved. The model never receives the raw graph — it only ever sees the filtered, bounded context the pipeline assembles for it.

```
Browser (React SPA, ChatPanel mounted inside DetailPanel's Chat mode)
  │
  │ 1. User types a question, ChatPanel calls POST .../messages/stream
  │    (fetch + ReadableStream reader; credentials: include for session cookie)
  ▼
FastAPI router: backend/app/api/chat.py
  │
  │ 2. require_current_user dependency resolves AppUser from session cookie
  ▼
ChatService (backend/app/services/chat.py)
  │
  │ 3. ProgressService.resolve(user_id, series_id) → visible_until_order
  │    (Neo4j read: (:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)-[:FOR_SERIES]->(:Series))
  │
  │ 4. ChatRepository loads recent, currently-visible ChatMessages for context
  │    (filtered by visible_until_order_snapshot <= resolved boundary — hide-not-delete)
  ▼
RetrievalPipeline (backend/app/retrieval/pipeline.py)
  │
  │ 5. LLMProvider.stream_chat(system_prompt, history, tools=ALLOWLISTED_TOOLS)
  │    → model requests tool calls (search_entities, get_neighborhood, get_claims, ...)
  ▼
Retrieval Tools (backend/app/retrieval/tools.py)
  │
  │ 6. Each tool independently re-derives visible_until_order from step 3 (never
  │    from model output), runs parameterized Cypher via Neo4jDatabase.execute_query,
  │    composing backend/app/spoiler/filter.py's existing visibility WHERE-clause pattern
  ▼
Neo4j (Community Edition, existing driver)
  │
  │ 7. Filtered rows return to the pipeline → context normalization (dedupe,
  │    prioritize direct evidence, bound size) → back to LLMProvider for the
  │    final answer, this time without tools
  ▼
Citation Validator (backend/app/retrieval/pipeline.py)
  │
  │ 8. Every claim_id/evidence_id/source_id the model cited is checked against
  │    the actual retrieved context set — anything not present is stripped
  ▼
ChatService persists ChatMessage (role=assistant, visible_until_order_snapshot=step-3 value,
  citations, graph_focus, change_set_id if a ChangeSet was proposed) via ChatRepository,
  inside the same transaction pattern as RevisionRepository.log_revision when a ChangeSet exists
  │
  │ 9. Final SSE event streamed to the browser: {message, citations, graph_focus, proposed_change_set}
  ▼
Browser: MessageBubble renders streamed text; CitationChip "Show in graph" calls
  GraphCanvas's focusedElementIds prop; ChangeSetCard renders Confirm/Reject,
  which POST to backend/app/api/change_set.py's confirm/reject endpoints (a second,
  separate request/response cycle — NOT part of the streaming response)
```

### Allowlisted-Retrieval-Tool Security Model

The pipeline exposes exactly **eleven** retrieval tools — nothing more. The model cannot call any other function, and it can never execute Cypher:

1. `search_entities` — keyword search over visible entities
2. `get_entity` — fetch one visible entity by ID
3. `get_neighborhood` — closed neighborhood of a visible entity
4. `find_path` — bounded path search between two visible entities
5. `get_timeline` — chronological visible events
6. `get_character_context` — bounded interpretation pack for one visible Character (character + most recent visible Events + relationships/claims/evidence/sources); the tool for future-looking, opinion, and motivation questions
7. `get_claims` — visible claims matching filters
8. `get_evidence` — evidence fragments backing visible claims
9. `get_sources` — sources referenced by visible claims
10. `get_current_visible_graph_summary` — aggregate summary of the visible graph
11. `get_user_notes` — the user's own visible notes

Each tool is a small async function that:

- **Takes only allowlisted, typed parameters** — never a free-text Cypher string or an unvalidated entity ID sourced directly from model output.
- **Re-derives `visible_until_order` from the already-resolved server value** passed down by the pipeline — never re-read from the model's tool-call arguments, so a prompt-injected "show me everything" cannot widen the boundary.
- **Issues parameterized Cypher** built the same way `spoiler/filter.py`'s constants are — label/relationship names selected only from server-side allowlists, values always bound as `$parameters`. No string interpolation of model-controlled text.

This is the same fail-closed discipline as the graph read path: a misconfigured or injected tool call can only ever see the current user's visible graph.

---

## 4.9 ChangeSet Two-Stage Mutation Flow

**Location:** `backend/app/api/change_set.py`, `backend/app/services/change_set.py`, `backend/app/repository/change_set.py`

The LLM **cannot write to the graph directly** — not through tool calls, not through any endpoint. All graph edits flow through a typed, two-stage ChangeSet protocol (plus an explicit third stage for revert):

```
Stage 1 — PROPOSE (POST /api/series/{series_id}/change-sets)
  Chat pipeline decides a write is warranted → builds a typed ChangeSet:
  { summary, operations: [create_node | update_node | delete_node |
    create_relationship | update_relationship | delete_relationship |
    create_claim | update_claim | delete_claim | attach_evidence |
    create_note | update_note | delete_note] }
  ├── Pydantic validates: operation_type must be one of the 13 literals,
  │   extra fields forbidden, at least one operation, ontology-valid labels/types
  ├── Boundary validated: targets must be visible, same-series, visibility derived
  │   server-side (never accepted from client), never above the resolved boundary
  ├── Canonical/candidate protection: mutation of canonical or candidate content
  │   is refused (create_note override pattern instead)
  └── NO database write occurs at propose time — status: awaiting_confirmation

Stage 2 — CONFIRM / APPLY (POST .../change-sets/{id}/confirm)  |  REJECT (POST .../reject)
  Confirm:
  ├── Ownership + status check (404 resource_not_found if missing/cross-user)
  ├── Staleness check: visible_until_order_snapshot vs current boundary → 409 changeset_stale
  ├── Idempotent: idempotency_key makes re-apply a no-op
  ├── Single Neo4j transaction: all operations apply or none do (rollback on error)
  └── Revision logged in the SAME transaction (revision_id on the applied ChangeSet)
  Reject:
  └── Marks the ChangeSet rejected; no database change; graph untouched

Stage 3 — REVERT (POST .../change-sets/{id}/revert, applied ChangeSets only)
  ├── Only create-shaped ChangeSets are revertible (pre-apply state = "did not exist")
  ├── Conflict guard: if a later unrelated change modified/removed a created resource,
  │   revert returns 409 rather than silently overwriting
  └── Creates a new Reverted revision — the audit chain stays append-only
```

The frontend renders the proposed ChangeSet as a preview card (per-operation summary lines, Before/After rows for updates, destructive banner when deletes are present) with explicit **Confirm changes** / **Reject** controls — the *only* UI path into the confirm/reject endpoints. Nothing in the streaming chat response applies a write.

---

## 4.10 Spoiler-Safety Invariants

These invariants are the phase's contract with the rest of the project — every one is enforced by backend code and locked by tests:

1. **The LLM never receives the full unfiltered graph.** The pipeline assembles context exclusively through the ten allowlisted retrieval tools, each of which runs the same visibility-gated Cypher as the graph read path, then dedupes and bounds the result (`LLM_MAX_CONTEXT_ITEMS`, `LLM_MAX_CONTEXT_CHARACTERS`).
2. **The LLM never receives future-episode data.** Every tool re-derives the user's resolved `visible_until_order` server-side and applies `visible_from_order <= boundary` on every hop (nodes, relationships, claims, evidence, sources). A hidden record behaves like a nonexistent one.
3. **The LLM never executes arbitrary Cypher.** There is no text-to-Cypher surface anywhere. The model's only actions are the ten allowlisted tool calls with typed, validated parameters; all Cypher is server-side constant templates with `$parameter` bindings.
4. **The LLM cannot directly mutate canonical or candidate content.** ChangeSet validation refuses mutation operations targeting `origin: canonical` or `origin: candidate` content — the pipeline substitutes a confirmable `create_note` annotation (the "Protected" refusal surfaced in the UI) instead.
5. **Writes require typed ChangeSets and explicit confirmation.** The model can only *propose*; a human must confirm through the ChangeSetCard's Confirm/Reject controls before any transaction touches the graph.
6. **Chat history is spoiler-filtered by the same boundary as the graph.** `ChatMessage` rows carry `visible_until_order_snapshot`; history loading filters `snapshot <= current boundary`, so hidden messages never enter the model's context.
7. **Lowering progress hides previously generated future-boundary messages without deleting them.** Messages remain persisted (and re-appear if progress advances again); they are simply excluded from history loading and session previews below the boundary.
8. **All graph content is treated as untrusted prompt data.** User notes, evidence text, labels, and any retrieved content are wrapped in strict delimiters with explicit instruction-ignore language (`SYSTEM_PROMPT_V1`); prompt-injection tests assert the malicious strings are contained verbatim inside the data sections and never interpreted as instructions.

---

## 5. Data Flow Examples

### Flow 1: User opens the app (Read Path)

```
User selects "Dexter" series
  │
  ▼
App.tsx sets selectedSeriesId = "series:dexter"
  │
  ├──► useEpisodes("series:dexter")
  │      │
  │      ▼
  │    GET /api/series/{series_id}/episodes
  │      │
  │      ▼
  │    SeriesService.list_episodes()
  │      │
  │      ▼
  │    Neo4j: MATCH (episode:Episode)-[:PART_OF]->(Series)
  │      │
  │      ▼
  │    Returns list of EpisodeResponse
  │
  └──► useGraph("series:dexter", visibleUntilOrder=1)
         │
         ▼
       GET /api/series/{series_id}/graph?visible_until_order=1
         │
         ▼
       GraphService.fetch_graph("series:dexter", 1)
         │
         ▼  (7 concurrent queries via asyncio.gather)
       ┌─────────────────────────────────────────────────────┐
       │ 1. SERIES_QUERY           → Series metadata         │
       │ 2. NODES_QUERY            → Nodes with vfo <= 1     │
       │ 3. STRUCTURAL_EDGES_QUERY → Edges with vfo <= 1     │
       │ 4. VISIBLE_CLAIMS_QUERY   → Claims visible at ep 1  │
       │ 5. VISIBLE_USER_RELS_QUERY→ User rels visible at 1  │
       │ 6. SOURCES_QUERY          → Sources for claims      │
       │ 7. EVIDENCE_QUERY         → Evidence for claims     │
       └─────────────────────────────────────────────────────┘
         │
         ▼
       GraphResponse assembled (claims projected to edges)
         │
         ▼
       graphToElements() → Cytoscape ElementDefinition[]
         │
         ▼
       GraphCanvas renders with cose-bilkent layout
```

### Flow 2: User advances watch progress

```
User selects "S01E05" in EpisodeSelector
  │
  ▼
useWatchProgress.requestChange("series:dexter", 5)
  │                     direction: "forward"
  ▼
ConfirmAdvanceModal opens (warning: you'll see spoilers for up to S01E05)
  │
  ├── User confirms
  │     │
  │     ▼
  │   useWatchProgress.confirmChange()
  │     │  sessionStorage.setItem("hdgraf.watchProgress", {seriesId, visibleUntilOrder: 5})
  │     ▼
  │   useGraph("series:dexter", 5) re-fetches with new boundary
  │     │
  │     ▼
  │   Entire Flow 1 repeats with visible_until_order=5
  │     New nodes/edges/claims become visible
  │
  └── User cancels
        │
        ▼
      watchProgress.cancelChange() → discards pending change
```

### Flow 3: User creates a note

```
User writes a note on a character node (e.g., "character:dexter")
  │
  ▼
POST /api/series/{series_id}/notes
  {
    "target_type": "Character",
    "target_id": "character:dexter",
    "content": "Remember this detail."
  }
  │
  ▼
UserContentRepository.create_note(series_id, payload)
  │
  ├── Validates: target exists in same series, visible_from_order >= 1
  ├── Generates: id = "user-note:{uuid4}", timestamps
  └── Neo4j:
        MATCH (target:Character {id: $target_id, series_id: $series_id})
        WHERE target.visible_from_order >= 1
        CREATE (note:UserNote {id: $id, ...})
        CREATE (note)-[:REFERS_TO {origin: 'user'}]->(target)
  │
  ▼
Response: NoteResponse with origin="user", visible_from_order inherited from target
```

---

## 6. Key Design Decisions

### D-01: Spoiler filtering at the database layer

**Decision:** All spoiler filtering happens in Cypher queries in `spoiler/filter.py`, not in application code after data retrieval.

**Rationale:** Fail-closed by default — if a query is misconfigured, no data leaks. The frontend never receives data it would need to hide. Performance: filtering at the database level avoids transferring and discarding large result sets.

### D-02: Visible `from`/`until` order on every entity

**Decision:** Every node, relationship, and claim carries its own `visible_from_order`. Claims also carry optional `valid_from_order` and `valid_until_order`.

**Rationale:** Fine-grained visibility control per entity, not per type. A season finale character has a different visibility than a pilot character. Temporal validity allows time-bounded claims (e.g., "character X is loyal to Y" during seasons 1-3 but not after).

### D-03: Claims projected as edges

**Decision:** Each visible claim is projected into a `GraphEdge` in the response (the edge carries `claim_id` referencing the source claim). Structural edges (`PART_OF`, `PRECEDES`, `OCCURRED_IN`) have `claim_id = null`.

**Rationale:** Single unified edge representation in the frontend. The `claim_id` field disambiguates narrative edges (backed by claims) from structural edges (graph topology). The `DetailPanel` renders claim-backed edges with claims/evidence tabs; `StructuralEdgeCard` handles topological edges.

### D-04: Seven concurrent queries for graph read

**Decision:** `GraphService.fetch_graph()` runs seven independent Cypher queries concurrently via `asyncio.gather()`, not one giant query.

**Rationale:** Each query targets different node labels and relationship patterns. A unified query would be exponentially more complex and harder to optimize. Concurrent execution minimizes latency without complex query engineering.

### D-05: Backend-only visibility authority

**Decision:** The frontend never checks `visible_from_order`. `graphToElements()` maps all received data to Cytoscape elements without any visibility filter.

**Rationale:** Eliminates the risk of frontend/backend visibility drift. If a node is in the response, it's safe to show. Contradictory proof: test fixtures verify the backend returns no node with `visible_from_order > visible_until_order`.

### D-06: sessionStorage for watch progress

**Decision:** Watch progress (current series, episode boundary) is stored in `sessionStorage`, not localStorage or server-side.

**Rationale:** Tab-scoped: each browser tab maintains independent progress. No server-side state for a client-side concern. Hydration on page refresh without re-prompting the user. The `pendingChange` → `confirmChange` workflow ensures deliberate forward jumps.

### D-07: Asynchronous graph fetching with retry

**Decision:** `useGraph` implements an explicit `refetch()` mechanism via a `retryToken` state counter, distinct from the `seriesId`/`visibleUntilOrder` dependency.

**Rationale:** Allows error recovery without changing the watch progress state. A broken network or transient server error gets a Retry button that re-issues the exact same request.

### D-08: Immutable PATCH contracts

**Decision:** PATCH routes accept only the mutable field (`content` for notes, `label` for custom nodes, `predicate` for custom relationships). Endpoints, origin, visibility, ownership are immutable.

**Rationale:** Prevents client-authoritative visibility manipulation. Simplifies server-side validation. The server owns all structural metadata; the client owns only content.

### D-09: Visibility derived from entity, not client

**Decision:** For creates, `visible_from_order` is derived from the referenced target entity (e.g., a note inherits the target's visibility), never accepted from the client.

**Rationale:** The client has no authority to set visibility. A note attached to a season-5 character is only visible to users who've reached season 5, regardless of what the client submits.

---

## 7. Future Extensibility Points

### 7.1 LLM-Powered Chat

**Delivered in Phase 06.** The GraphRAG-lite chat pipeline (see [4.8](#48-graphrag-lite-chat-pipeline)) is implemented: persisted watch progress, ten allowlisted retrieval tools, a streaming grounded-answer endpoint with validated citations, spoiler-filtered chat history, and a typed ChangeSet graph-editing flow (see [4.9](#49-changeset-two-stage-mutation-flow)). Natural extension points that remain:

- **Additional retrieval tools** — new allowlisted functions in `backend/app/retrieval/tools.py`, each following the fail-closed visibility pattern
- **Additional providers** — new implementations of the `LLMProvider` protocol in `backend/app/llm/provider.py` (only `openai_compatible` ships today)
- **Richer grounding** — e.g., multi-hop path explanations surfaced through the existing citation model

### 7.2 Auto-Extraction Pipeline

New content extraction from episode scripts/transcripts:
- **Claim extraction:** NLP → new `Claim` nodes with `origin: 'candidate'`
- **Relationship extraction:** New `Claim` nodes with relationship effects
- **Confidence scoring:** Uses existing `confidence_level` enum
- **Review workflow:** `claim_status` → `candidate` → `corroborated` → `canonical`
- **Integration point:** New repository methods in `UserContentRepository` pattern, new `ClaimRepository`, new service for bulk import

### 7.3 Revision History Integration

The `Revision` module is fully integrated into all user-content write paths. Every note, custom-node, and custom-relationship mutation auto-creates a `Revision` with before/after JSON snapshots in the same Neo4j transaction. A revert API restores prior state by creating a new `Reverted` revision — history is never destroyed.

What's been delivered:
- **History panel UI** — plans 04-04 (revision types, API client, hook) and 04-05 (DetailPanel History tab + revert UI) executed. The History tab shows action badges, diff summaries, and one-shot revert with confirmation dialog and toast.
- **Time-travel queries** (graph state at a given revision) — post-v0
- **Decision journaling** with author attribution — post-v0

### 7.4 Multi-Series Support

The architecture is already series-scoped (`series_id` on every node). Extending to additional TV series requires:
- New seed data directories (`data/{series_name}/`)
- Updated ontology (if the new series needs different relationship types)
- Query parameterization already handles multi-tenancy

### 7.5 Redis Session Store

The `InMemorySessionRepository` implements the `SessionRepository` protocol. Swapping to Redis for production:
- Create `RedisSessionRepository` satisfying the same protocol
- Session records already carry TTL, expiry, revocation fields
- Cookie contract unchanged

### 7.6 Real-Time Collaboration

The `UserNote` and user-created content model supports:
- WebSocket notification on content changes
- Revision history per note
- User attribution via the existing `AppUser` node model

### 7.7 Granular Ontology Evolution

The versioned ontology system supports:
- Non-breaking additions (new relationship types with `interface_version`)
- Migration scripts for breaking changes
- Forward-compatible seed data validation (skips unknown types with a warning)

---

## Appendices

### A. Quick Reference: Path Conventions

| Concept | Backend Path | Frontend Path |
|---|---|---|
| API routes | `backend/app/api/` | `frontend/src/api/` |
| Domain models | `backend/app/domain/` | `frontend/src/types/` |
| Tests | `backend/tests/` | `frontend/src/**/*.test.tsx` |
| Ontology | `ontology/` | — |
| Seed data | `data/dexter/` | — |

### B. Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `NEO4J_URI` | — | Neo4j connection URI |
| `NEO4J_USERNAME` | — | Neo4j username |
| `NEO4J_PASSWORD` | — | Neo4j password |
| `NEO4J_DATABASE` | `neo4j` | Target database name |
| `GOOGLE_CLIENT_ID` | `""` | Google OAuth client ID |
| `SESSION_COOKIE_NAME` | `session` | HttpOnly cookie name |
| `SESSION_TTL_SECONDS` | `604800` | Session lifetime (7 days) |
| `SESSION_COOKIE_SECURE` | `False` | Secure flag on cookie |
| `FRONTEND_ORIGINS` | `http://localhost:5173` | CORS allowed origins |

### C. Key Ports

| Service | Port |
|---|---|
| Frontend (Vite dev) | 5173 |
| Backend (Uvicorn) | 8000 |
| Neo4j HTTP | 7474 |
| Neo4j Bolt | 7687 |
