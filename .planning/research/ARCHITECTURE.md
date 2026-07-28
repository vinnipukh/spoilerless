# Architecture Research

**Domain:** Spoiler-Safe Narrative Knowledge Graph (TV Series)
**Researched:** 2026-07-28
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                              │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │   React SPA     │  │  Cytoscape.js   │  │  Spoiler Progress UI    │  │
│  │  (Vite + TS)    │  │  Graph Viz      │  │  Selector + Modal       │  │
│  └────────┬────────┘  └────────┬────────┘  └────────────┬────────────┘  │
│           │                    │                         │               │
├───────────┴────────────────────┴─────────────────────────┴───────────────┤
│                         API GATEWAY (FastAPI)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │                    SPOILER-AWARE QUERY LAYER                      │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │    │
│  │  │  Graph Query  │  │  Spoiler     │  │  Response Filter      │  │    │
│  │  │  Builder      │  │  Guard       │  │  (visible_from_order) │  │    │
│  │  └──────┬───────┘  └──────┬───────┘  └───────────┬───────────┘  │    │
│  │         │                  │                       │               │    │
│  └─────────┴──────────────────┴───────────────────────┴───────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                      DOMAIN / SERVICE LAYER                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Series   │  │ Character│  │ Claim    │  │ UserNote │  │ Revision │  │
│  │ Service  │  │ Service  │  │ Service  │  │ Service  │  │ Service  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
├───────┴──────────────┴──────────────┴──────────────┴──────────────┴──────┤
│                         DATA ACCESS LAYER                                │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │              Neo4j Python Driver Singleton                        │    │
│  │  (connection pool, session management, transaction lifecycle)     │    │
│  └──────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────┤
│                          DATA STORES                                     │
│  ┌──────────────────────┐  ┌────────────────────────────────────────┐   │
│  │   Neo4j Graph DB     │  │   Seed JSON Files                      │   │
│  │   (single source of  │  │   (data/dexter/metadata/, sources/,     │   │
│  │    truth)            │  │    seed/)                               │   │
│  └──────────────────────┘  └────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| Graph Query Builder | Constructs Cypher queries with spoiler-boundary filters appended to every MATCH | FastAPI service function parameterized by `visible_until_order` |
| Spoiler Guard | Validates that no query returns data beyond the user's `visible_until_order`; acts as safety net | Middleware or function decorator that post-processes query results |
| Response Filter | Applies `visible_from_order` filter on any query that wasn't pre-filtered at Cypher level | Utility function used in every graph route |
| Series/Episode Service | CRUD for structural nodes (Series, Season, Episode, Scene) and their PART_OF/PRECEDES edges | FastAPI route → Neo4j session → Cypher query |
| Character Service | CRUD for narrative nodes and character-relationship edges (KNOWS, KILLS, etc.) with spoiler gating | FastAPI route → Neo4j session → filtered Cypher |
| Claim Service | Atomic subject-predicate-object claims with evidence backing, status workflow, and temporal validity | FastAPI route → Neo4j session → Cypher with valid_from/valid_until filters |
| UserNote Service | User-created annotations attached to any graph node, stored separately from canonical data | FastAPI route → Neo4j session |
| Revision Service | Immutable log of every change (create, update, reject, revert) with actor and timestamp | FastAPI route → Neo4j session; Revision nodes stream from triggers |
| Neo4j Driver Singleton | Connection pool lifecycle (verify, session, close) | `Neo4jDatabase` class with `.driver` property, global singleton |
| Cytoscape.js Renderer | Interactive graph visualization with node/edge styling, layout, detail-on-click | React component using `react-cytoscapejs` |
| Spoiler Progress UI | Episode selector + spoiler confirmation modal that controls `visible_until_order` sent to backend | React state → query parameter on `/api/graph` |
| LLM Chat (future) | Conversational access over user-visible subgraph only — backend guardrail prevents out-of-bounds queries | Tool-based retrieval over filtered subgraph |

## Recommended Project Structure

```
hdgrafcehennemi/
├── backend/
│   ├── app/
│   │   ├── api/              # HTTP route handlers (routers)
│   │   │   ├── series.py     # /api/series endpoints
│   │   │   ├── graph.py      # /api/graph endpoint (spoiler-filtered)
│   │   │   ├── characters.py # /api/characters endpoints
│   │   │   ├── claims.py     # /api/claims endpoints
│   │   │   ├── notes.py      # /api/notes endpoints
│   │   │   └── revisions.py  # /api/revisions endpoints
│   │   ├── core/             # Config, lifespan, shared utilities
│   │   │   ├── config.py     # Pydantic settings (env-based)
│   │   │   └── dependencies.py # FastAPI dependency injection
│   │   ├── domain/           # Pydantic models (request/response)
│   │   │   ├── series.py     # SeriesResponse, EpisodeResponse
│   │   │   ├── character.py  # CharacterResponse
│   │   │   ├── claim.py      # ClaimResponse, ClaimCreate
│   │   │   ├── graph.py      # GraphResponse (nodes + edges)
│   │   │   ├── note.py       # UserNoteResponse/UserNoteCreate
│   │   │   └── revision.py   # RevisionResponse
│   │   ├── graph/            # Neo4j persistence
│   │   │   ├── database.py   # Neo4jDatabase singleton
│   │   │   ├── seed.py       # Graph seed script
│   │   │   └── queries.py    # Reusable Cypher query templates
│   │   ├── spoiler/          # Spoiler-boundary logic
│   │   │   ├── guard.py      # SpoilerGuard middleware/function
│   │   │   └── filter.py     # visible_from_order result filtering
│   │   ├── revisions/        # Revision tracking
│   │   │   ├── service.py    # Revision logging logic
│   │   │   └── models.py     # Revision Pydantic models
│   │   └── main.py           # FastAPI app, lifespan, CORS, router includes
│   ├── tests/                # Pytest test suite
│   │   ├── test_spoiler.py   # Spoiler boundary unit tests
│   │   ├── test_graph.py     # Graph endpoint tests
│   │   ├── test_claims.py    # Claim CRUD + filtering tests
│   │   └── conftest.py       # Test fixtures (Neo4j mock, test client)
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── api/              # API client layer
│       │   ├── client.ts     # fetch wrapper, base URL config
│       │   ├── series.ts     # /api/series calls
│       │   └── graph.ts      # /api/graph calls (with visible_until)
│       ├── components/       # Reusable UI components
│       │   ├── Layout.tsx    # Main app shell (header, sidebar, graph area)
│       │   ├── GraphCanvas.tsx   # Cytoscape.js wrapper component
│       │   ├── NodePanel.tsx     # Node detail panel
│       │   ├── EdgePanel.tsx     # Edge/claim detail panel
│       │   ├── ProgressSelector.tsx  # Episode progress dropdown
│       │   ├── SpoilerModal.tsx # Spoiler confirmation dialog
│       │   ├── NoteEditor.tsx  # User note create/edit form
│       │   └── RevisionTimeline.tsx # Revision history display
│       ├── hooks/            # Custom React hooks
│       │   ├── useGraph.ts   # Fetch and manage graph data
│       │   └── useProgress.ts # Manage visible_until_order state
│       ├── graph/            # Cytoscape.js configuration
│       │   ├── styles.ts     # Node/edge stylesheet
│       │   ├── layout.ts     # Graph layout configuration
│       │   └── events.ts     # Click/hover event handlers
│       ├── pages/            # Route-level page components
│       │   └── ViewerPage.tsx # Main graph viewer page
│       ├── App.tsx           # Root component
│       ├── main.tsx          # Entry point
│       └── index.css         # Global styles
│
├── ontology/                 # Domain ontology definitions
│   ├── node_types.yaml
│   ├── relation_types.yaml
│   └── claim_types.yaml
│
├── data/dexter/              # Seed data for Dexter prototype
│   ├── metadata/
│   │   ├── series.json
│   │   └── episodes.json
│   ├── characters.json       # Dexter S01E01-03 character data
│   ├── claims.json           # Atomic claims with evidence references
│   ├── sources.json          # Source/evidence fragment data
│   └── seed/                 # Full seed scripts
│
├── docs/                     # Documentation
│   ├── architecture.md
│   ├── spoiler-model.md
│   └── ontology.md
│
├── .planning/                # GSD planning artifacts
├── docker-compose.yml        # Neo4j container
├── .env.example
└── pyproject.toml
```

### Structure Rationale

- **backend/app/api/:** Separate routers per domain entity so each file has a single responsibility. Graph endpoint (`/api/graph`) is the composite endpoint that returns the full filtered graph for visualization.
- **backend/app/spoiler/:** Isolates spoiler-boundary logic into its own package because it's the central architectural invariant. Every new route that exposes graph data must route through this package. Having it be a dedicated package makes the invariant auditable and testable.
- **backend/app/domain/:** Pydantic models are kept separate from API routers to enable clean dependency injection — domain models can be imported by tests, services, and API layers without circular dependencies.
- **frontend/src/api/:** Frontend API calls are centralized so a single `client.ts` can inject the `visible_until_order` header/parameter on every request, making it impossible to forget the spoiler parameter at the component level.
- **frontend/src/graph/:** Cytoscape.js is complex enough to deserve its own directory for stylesheets, layout config, and event wiring. This also makes it easy to swap out cytoscape for another renderer later.
- **ontology/ at root:** The ontology YAML files define the domain vocabulary — they're shared conceptual artifacts, not code. Placing them at root signals they're as important as the code itself.

## Architectural Patterns

### Pattern 1: Parameterized Cypher Filtering

**What:** Every Cypher query that fetches graph data includes a `WHERE` clause parameterized by `visible_until_order`. The parameter is passed from the frontend as a query string, enforced at the backend API layer, and never defaults to a value that reveals all data.

**When to use:** For every read operation that returns character, claim, evidence, or user-note data.

**Trade-offs:**
- (+) Impossible to accidentally leak data past the user's boundary — the filter is in the query itself.
- (+) Single-pass filtering — Neo4j handles it at the database level, no post-processing needed for most cases.
- (-) Every query must manually include the filter. Easy to forget on a new route. Mitigate with a query builder function.
- (-) Complex for queries that join across multiple node types with different `visible_from_order` values (e.g., claims reference episodes).

**Example:**
```python
def get_visible_graph(series_id: str, visible_until_order: int) -> GraphResponse:
    query = """
    MATCH (n {series_id: $series_id})
    WHERE n.visible_from_order <= $visible_until_order
    OPTIONAL MATCH (n)-[r]->(m)
    WHERE r.visible_from_order <= $visible_until_order
      AND m.visible_from_order <= $visible_until_order
    RETURN n, r, m
    """
    with neo4j_db.driver.session(database=neo4j_db.database) as session:
        result = session.run(query, series_id=series_id, visible_until_order=visible_until_order)
        # transform records into GraphResponse
```

### Pattern 2: Atomic Claim + Evidence Fragments

**What:** Knowledge is modeled as atomic subject-predicate-object triples (Claims), each backed by one or more EvidenceFragments that point to a Source with locator metadata. Claims have a lifecycle (candidate → corroborated → canonical → disputed → rejected) and carry both `relationship_effect` (narrative strength) and `confidence_level` (system certainty) as orthogonal dimensions.

**When to use:** Every piece of non-structural knowledge about the narrative world.

**Trade-offs:**
- (+) Clean separation of "what we know" from "why we know it". Evidence can be audited independently.
- (+) Claims can be created by different actors (seed data, user, future LLM) and carry provenance.
- (-) Query complexity increases — retrieving a claim requires following SUPPORTED_BY edges to evidence and evidence edges to sources.
- (-) Requires a status workflow that adds state machinery.

**Example:**
```cypher
// Create a claim with evidence
MATCH (s:Character {id: $subject_id})
MATCH (o:Character {id: $object_id})
CREATE (c:Claim {
  id: $claim_id,
  subject_id: $subject_id,
  predicate: "KNOWS",
  object_id: $object_id,
  claim_type: "explicit_fact",
  status: "canonical",
  visible_from_order: 1,
  valid_from_order: 1,
  valid_until_order: null,
  confidence_level: "verified",
  relationship_effect: 0.3
})
CREATE (c)-[:SUPPORTED_BY]->(:EvidenceFragment {
  id: $evidence_id,
  source_id: $source_id,
  episode_id: $episode_id,
  locator_text: $locator_text,
  content_hash: $content_hash
})
CREATE (s)-[:KNOWS {visible_from_order: 1}]->(o)
```

### Pattern 3: Temporal Validity with visible_from_order / valid_until_order

**What:** Every node, relationship, and claim carries `visible_from_order` (when it becomes visible to the user) and optionally `valid_from_order` / `valid_until_order` (when it is narratively true). This handles both spoiler gating and narrative temporality (e.g., "Character A knows Character B" might be true from episode 3 onwards, but only becomes known to the viewer in episode 5).

**When to use:** All graph elements that could contain spoilers.

**Trade-offs:**
- (+) Handles the distinction between "when the event happens" (valid_from) and "when the user learns about it" (visible_from). This is critical for mysteries, reveals, and backstories.
- (+) Null `valid_until_order` means "still valid" — no need for sentinel values.
- (-) Doubling the temporal fields adds conceptual complexity. For the v0 prototype, `valid_from_order` can be set equal to `visible_from_order` and `valid_until_order` can be null everywhere.
- (-) Queries with both bounds are more complex: `WHERE n.visible_from_order <= $visible_until_order AND (n.valid_until_order IS NULL OR n.valid_until_order >= $visible_until_order)`

**Example:**
```cypher
// Claim with temporal validity
MATCH (c:Claim {id: $claim_id})
WHERE c.visible_from_order <= $visible_until_order
  AND (c.valid_until_order IS NULL OR c.valid_until_order >= $visible_until_order)
RETURN c
```

### Pattern 4: Separated User and Canonical Content

**What:** User-created nodes, relationships, and notes are stored as separate node types (`UserNote`, custom user labels) with a `created_by_user` field. They are never merged into canonical entities. The frontend renders them with a distinct visual style.

**When to use:** Any feature where users contribute content that shouldn't overwrite curated data.

**Trade-offs:**
- (+) User additions can be toggled on/off, reverted, or rejected without touching canonical data.
- (+) Clear provenance — users can see what's canonical vs their own addition.
- (-) Graph queries must UNION or OR across canonical and user content, adding query complexity.
- (-) User-created nodes need their own `visible_from_order` enforcement.

**Example:**
```cypher
// Fetch both canonical and user-created nodes visible to user
MATCH (n)
WHERE (n:Character OR n:UserNote OR n:UserNode)
  AND n.series_id = $series_id
  AND n.visible_from_order <= $visible_until_order
RETURN n
```

### Pattern 5: Revision Log as Event Stream

**What:** Every mutation (claim create, update, status change, user correction, revert) writes an immutable `Revision` node linked to the affected entity via `CORRECTS`, `SUPERSEDES`, or `REVERTS_TO` edges. Revisions include the previous state snapshot, the actor, and a timestamp.

**When to use:** Any feature where data provenance and rollback matter.

**Trade-offs:**
- (+) Simple to implement — no Git-based graph versioning needed for prototype.
- (+) Revisions are nodes in the graph too, so they can be queried like any other entity.
- (-) Scales poorly for high-frequency mutations — every write is at least 1 extra node + 1 edge. Fine for prototype scope.
- (-) Revert requires re-materializing the previous state snapshot, which may reference entities that have since changed.

## Data Flow

### Request Flow

```
[Spoiler: visible_until_order=2]
    ↓
[Frontend: ProgressSelector] → sets visible_until_order in React state
    ↓
[Frontend: GraphCanvas mounts] → calls fetchGraph(series_id, visible_until_order)
    ↓
[Frontend: api/graph.ts] → GET /api/graph?series_id=dexter&visible_until_order=2
    ↓
[Backend: graph.py route] → receives parameters, extracts visible_until_order
    ↓
[Backend: SpoilerGuard] → validates visible_until_order is non-null and positive
    ↓
[Backend: Graph Query Builder] → constructs Cypher with WHERE filters
    ↓
[Backend: Neo4j session.run()] → executes parameterized query
    ↓
[Neo4j] → returns only nodes/edges with visible_from_order <= 2
    ↓
[Backend: Response Filter] → safety post-check: drop any result exceeding boundary
    ↓
[Backend: Response Transform] → maps to GraphResponse (nodes[] + edges[])
    ↓
[Frontend: GraphCanvas] → receives GraphResponse, renders with Cytoscape.js
```

### State Management

```
[React State]
    ↓ (useProgress hook)
[ProgressSelector] + [SpoilerModal]
    ↓ visible_until_order updated
[useGraph hook] → re-fetches /api/graph
    ↓
[Cytoscape.js] → updates graph elements (adds/removes nodes + edges)
    ↓
[NodePanel / EdgePanel] → selected entity detail from same GraphResponse
```

### Key Data Flows

1. **Initial Load:** App starts → fetches series list from `/api/series` → user selects series → fetches episodes from `/api/series/{id}/episodes` → user sets progress → fetches filtered graph from `/api/graph?visible_until_order=N`.

2. **Progress Update:** User selects a later episode → spoiler confirmation modal appears → user confirms → `visible_until_order` updated in state → graph re-fetched with new boundary → Cytoscape.js re-renders with newly visible elements.

3. **Claim Creation:** User fills claim form → POST `/api/claims` with subject, predicate, object, evidence reference → backend creates Claim node with appropriate `visible_from_order` → backend creates Revision node logging the action → frontend re-fetches graph.

4. **User Note:** User adds note to a character → POST `/api/notes` with target node ID, note text → backend creates `UserNote` node with `(:UserNote)-[:REFERS_TO]->(:Character)` → frontend displays note in NodePanel.

5. **Revision History:** User opens revision panel for a claim → GET `/api/revisions?target_id=claim_001` → backend traverses `(:Revision)-[CORRECTS|SUPERSEDES|REVERTS_TO]->(:Claim)` → returns ordered list of revisions → frontend renders timeline.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users (single series) | Current architecture — monolithic FastAPI, single Neo4j instance, no caching. Fine for prototype. |
| 1k-100k users (single series) | Add Redis cache for graph query results keyed by `(series_id, visible_until_order)`. Add connection pooling tuning in Neo4j driver. Consider read replicas for Neo4j. |
| 100k+ users (multi-series) | Split Neo4j by series (one graph per series or sharded). Add GraphQL layer for flexible querying. Consider CDN-cached static data (series metadata, episode lists). Event-driven claim ingestion via message queue. |

### Scaling Priorities

1. **First bottleneck:** Neo4j query performance under concurrent spoiler-filtered graph queries. Fix: Add Redis result caching with TTL by `(series_id, visible_until_order)` pair. Spoiler queries return the same results for the same boundary, making them ideal cache candidates.

2. **Second bottleneck:** Frontend load time for large graphs (1000+ nodes). Fix: Client-side pagination of graph data, incremental Cytoscape.js rendering, or level-of-detail collapsing (e.g., collapsed groups for minor characters).

## Anti-Patterns

### Anti-Pattern 1: Client-Side Spoiler Filtering

**What people do:** Send all graph data to the frontend and filter based on user progress in JavaScript.

**Why it's wrong:** The spoiler boundary is a security invariant, not a UI concern. Client-side filtering is trivially bypassable (browser DevTools, network inspection). The backend must enforce the boundary before data leaves the server.

**Do this instead:** Filter at the Cypher query level. The `/api/graph` endpoint accepts `visible_until_order` as a required parameter and never returns data past that boundary. The frontend never receives data it shouldn't see.

### Anti-Pattern 2: Leaking visible_from_order as a User-Configurable Field

**What people do:** Let users set `visible_from_order` arbitrarily per node via the API, allowing them to peek ahead.

**Why it's wrong:** `visible_from_order` is a property of the data, determined by curators/seed data, not user preference. Making it user-writable defeats the spoiler protection.

**Do this instead:** `visible_from_order` is set at data creation time (seed script, curation, LLM extraction) and is never user-writable. Users only control their own `visible_until_order` boundary, which is compared against the data's `visible_from_order`.

### Anti-Pattern 3: Putting Everything in One Endpoint

**What people do:** Create a single massive `/api/graph` endpoint that returns all node and relationship types, then have the frontend parse/filter by type.

**Why it's wrong:** Mixing structural metadata (series, episodes) with narrative data (characters, claims) and user data (notes) in one payload makes versioning, caching, and testing harder. It also forces the frontend to re-fetch everything when only one type changes.

**Do this instead:** Separate endpoints by domain: `/api/series` for structural, `/api/graph` for the filtered narrative subgraph, `/api/notes` for user content, `/api/revisions` for history. The frontend orchestrates what it needs.

### Anti-Pattern 4: Implicit visible_until_order Default

**What people do:** Default `visible_until_order` to MAX_VALUE or a sentinel that reveals all data when the frontend forgets to pass it.

**Why it's wrong:** A forgetful frontend silently spills all spoilers. The spoiler boundary should fail closed, not fail open.

**Do this instead:** Require `visible_until_order` as a mandatory query parameter with no default. Return a 400 error if absent. In the queried Cypher, the absence of a valid boundary parameter should cause the query to return zero results.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Neo4j (Docker) | Native Cypher via neo4j Python driver | Driver singleton with connection pool; Docker healthcheck for startup ordering |
| Frontend (Vite dev) | CORS-enabled HTTP on localhost:5173 | CORS midleware configured in `main.py` |
| Future: LLM Provider | Tool-based retrieval over filtered subgraph; API key in environment | Backend guardrail prevents LLM from querying beyond user progress |
| Future: Subtitle/Script Ingestion | File parser → structured JSON → seed script → Neo4j MERGE | Each extracted claim gets a Source + EvidenceFragment node |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| API routers ↔ Domain models | Pydantic serialization/deserialization | FastAPI auto-validates request/response against models |
| API routers ↔ Neo4j | Cypher queries via `neo4j_db.driver.session()` | Current pattern; consider repository layer if query complexity grows |
| Spoiler package ↔ Graph queries | `visible_until_order` parameter injection | The spoiler package owns the filtering logic; graph queries call into it |
| Frontend ↔ Backend | HTTP JSON via `fetch()` | `visible_until_order` sent as query parameter on every graph-related request |
| Seed scripts ↔ Neo4j | Direct session with MERGE operations | Run independently, not part of app lifecycle |

## Build Order with Dependency Implications

### Phase 1: Stabilize Infrastructure (M1)
- Fix duplicate FastAPI app construction in `main.py`
- Fix health endpoint to actually verify Neo4j connectivity
- Ensure Docker Compose + seed script are reliable
- **Depends on:** Nothing
- **Unlocks:** All subsequent development

### Phase 2: Character/Claim/Source Graph Seed (M3 + M4)
- Create character seed data for S01E01-03
- Create source and evidence fragment seed data
- Extend seed script to create character nodes, claim nodes with SUPPORTED_BY relationships
- Add `visible_from_order` to all new nodes
- **Depends on:** Phase 1 (stable Neo4j)
- **Unlocks:** Spoiler endpoint testing, frontend graph rendering

### Phase 3: Spoiler-Aware Graph Endpoint (M3)
- Build `GET /api/graph?series_id=&visible_until_order=N`
- Implement Parameterized Cypher Filtering pattern
- Build SpoilerGuard validation layer
- Add post-query response filter as safety net
- Unit tests: verify S01E01 boundary excludes S01E02-03 data
- **Depends on:** Phase 2 (data to filter)
- **Critical path:** This is the core invariant. Must be built and tested before any frontend work.

### Phase 4: Frontend Graph UI (M5)
- Replace Vite starter with product layout
- Build ProgressSelector + SpoilerModal
- Build GraphCanvas with Cypress.js
- Build NodePanel + EdgePanel detail panels
- Wire all to backend endpoints
- **Depends on:** Phase 3 (working API to consume)
- **Unlocks:** Visible demo

### Phase 5: User Notes + Manual Editing (M6)
- UserNote model and CRUD endpoints
- User-created node/relationship endpoints
- Separate visual style for user content
- **Depends on:** Phase 4 (frontend exists to extend)

### Phase 6: Revision History (M7)
- Revision model with state snapshots
- Log claims mutations
- Revision display panel
- Revert operation
- **Depends on:** Phase 5 (user edits to record)

### Phase 7: Tests + CI (M8)
- Backend unit tests for spoiler boundaries, all routes
- Frontend lint and build checks
- GitHub Actions workflow
- **Depends on:** Phases 1-6 (code to test)
- **Note:** Start writing tests alongside Phase 3 — don't wait until Phase 7

## Sources

- Neo4j Cypher Manual — graph query patterns and best practices: https://neo4j.com/docs/cypher-manual/current/
- FastAPI Dependency Injection — service layer patterns: https://fastapi.tiangolo.com/tutorial/dependencies/
- Cytoscape.js Documentation — graph visualization API: https://js.cytoscape.org/
- React + Cytoscape Integration — react-cytoscapejs patterns
- Domain-Driven Design (Evans) — aggregate/entity boundaries informing domain model separation
- Event Sourcing Pattern — informing revision log design

---
*Architecture research for: Spoiler-Safe Narrative Knowledge Graph (HD Graf Cehennemi)*
*Researched: 2026-07-28*
