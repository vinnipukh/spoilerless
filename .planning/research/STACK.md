# Stack Research

**Domain:** Spoiler-Safe Narrative Knowledge Graph (Neo4j + FastAPI + React)
**Researched:** 2026-07-28
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|---|---|---|---|
| FastAPI | 0.140.7 | Backend REST API framework | Already in project. Async-first, Pydantic-native, auto OpenAPI docs. Ideal for Neo4j-backed APIs where async driver usage and request validation matter. |
| Neo4j Python Driver | 6.2.0+ | Graph database access | Already in project. Official driver with execute_query API, managed transactions, async support. The `execute_query` shorthand eliminates boilerplate vs. raw `session.run()`. |
| Neo4j (Database) | 2026-community | Graph database | Already in Docker Compose. Community edition is free, supports all needed features (constraints, indexes, Cypher). 2026 edition includes property type constraints and improved indexing. |
| Uvicorn | 0.51.0 | ASGI server | Already in project. Industry standard for FastAPI. Supports hot-reload, HTTP/1.1+WebSocket. For Windows, install `uvicorn[standard]` for `watchfiles` support during development. |
| React | 19.2.7 | Frontend UI framework | Already in project. Concurrent features, improved SSR, stable. Teams building interactive graph UIs prefer React's component model and ecosystem. |
| TypeScript | ~6.0.2 | Frontend type safety | Already in project. Strict mode enforced in tsconfig. TypeScript catches Cytoscape.js integration bugs (typed node/edge data) that plain JS would miss. |
| Vite | 8.1.1 | Frontend build tool | Already in project. Sub-second HMR, rolldown bundler for fast builds. Best-in-class DX for React+TypeScript development. |
| Cytoscape.js | 3.34.0 | Graph visualization | Already in project. Most mature JS graph viz library for complex interactive graphs (compound nodes, edge bundling, layouts, animations). D3.js is better for custom charting but worse for graph-traversal UIs. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---|---|---|---|
| Pydantic | 2.13.4 | Data validation & settings | Already in project. All API request/response models, settings loading. Pydantic v2 is 5-10x faster than v1. |
| pydantic-settings | 2.14.2 | Environment-based config | Already in project. Reads `.env` into `Settings` class with LRU cache. |
| python-dotenv | 1.2.2 | .env file loader | Already in project. Used by pydantic-settings and uvicorn. |
| @tanstack/react-query | ~5.x | Server state management | API client layer. Handles loading/error/caching for all FastAPI endpoints. Eliminates manual fetch/useEffect boilerplate, provides stale-while-revalidate caching for graph data, auto-refetch on spoiler boundary change. Zustand/Redux are overkill for this project since graph data is server-owned. |
| react-router-dom | ~7.x | Client-side routing | Navigation between graph view, notes view, revisions view, and settings. Lightweight, supports nested layouts. Avoids the complexity of full-blown state management for route-based views. |
| react-cytoscapejs | 2.0.0 | React Cytoscape.js wrapper | Already in project. Declarative Cytoscape.js integration for React. Provides `<CytoscapeComponent>` with typed props for elements, layout, stylesheet. |
| Vitest | ~3.x | Frontend test runner | Vite-native test runner (same transform pipeline). Faster than Jest, compatible with React Testing Library. Use `@testing-library/react` + `@testing-library/jest-dom` for component tests. |
| pytest | 9.1.1 | Backend test runner | Already in dev deps. Use with `httpx` (already in dev deps) as `TestClient` for async endpoint testing. |
| httpx | 0.28.1 | HTTP test client | Already in dev deps. FastAPI's recommended test client. Async-compatible. |
| pytest-asyncio | ~0.25.x | Async pytest support | Required to test async FastAPI endpoints and Neo4j queries. Pytest's default event loop doesn't support async fixtures without it. |
| PyYAML | 6.0.3 | Ontology file parsing | Already in project (transitive via uvicorn[standard]). For loading `ontology/*.yaml` files into Python dicts — used by seed scripts and graph validation. |
| @types/cytoscape | 3.21.9 | Cytoscape type definitions | Already in frontend dev deps. Provides typed element data, event handlers, layout options. |
| eslint | 10.6.0 | Frontend linting | Already in project. Use with `typescript-eslint` 8.62.0 (already installed) for catch-at-write-time type errors. |
| typescript-eslint | 8.62.0 | TypeScript ESLint rules | Already in frontend dev deps. Catches type-level errors during linting, not just at build time. |

### Development Tools

| Tool | Purpose | Notes |
|---|---|---|
| uv | Python package & project manager | Already used. Much faster than pip+venv. `uv lock` generates deterministic locks, `uv run` replaces `python -m`. |
| Docker Compose | Neo4j container orchestration | Already set up in `docker-compose.yml`. Run `docker compose up -d neo4j` to start graph database. |
| Vite Dev Server | Frontend HMR development | Already configured. `npm run dev` from frontend/ starts on port 5173 with proxy to backend. |
| PyCharm Professional | IDE with Neo4j/Cypher support | Project was created in PyCharm. Graph database plugin provides Neo4j Browser-style Cypher console inside IDE. |

## Installation

```bash
# Backend (already set up via uv)
cd backend
uv sync

# Frontend (already set up)
cd frontend
npm install

# Start Neo4j
docker compose up -d neo4j

# Run backend dev server (from project root)
uv run uvicorn backend.app.main:app --reload --port 8000

# Run frontend dev server (separate terminal)
cd frontend && npm run dev

# Seed the database
uv run python -m backend.app.graph.seed

# Run backend tests
uv run pytest backend/tests -v

# Run frontend tests
cd frontend && npx vitest run
```

### New library installations

```bash
# Backend additions
uv add pyyaml               # if not already present explicitly
uv add --dev pytest-asyncio  # for testing async endpoints

# Frontend additions
cd frontend
npm install @tanstack/react-query@^5 react-router-dom@^7
npm install -D vitest@^3 @testing-library/react@^16 @testing-library/jest-dom@^6 @testing-library/user-event@^14 jsdom@^25
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|---|---|---|
| **Neo4j** | PostgreSQL + pgvector | When the primary query pattern is relational (lots of JOINs on known columns) rather than graph traversal. If you don't need variable-depth path queries (`MATCH (c:Character)-[:KNOWS*1..3]->(other)`), PG might suffice. For this project, graph traversal over character relationships is the core value. |
| **Neo4j** | SQLite + networkx (in-memory) | For a tiny prototype with no persistence requirements. SQLite can't express graph traversals natively; you'd load everything into memory. Breaks down above ~10K nodes. |
| **Cytoscape.js** | D3.js force-directed graph | When you need fully custom SVG rendering rather than an out-of-the-box graph canvas. D3 gives total control but requires building node/edge interaction from scratch. Cytoscape.js provides built-in node dragging, edge handling, compound nodes, layouts — exactly what this project needs. |
| **Cytoscape.js** | vis-network (vis.js) | When you need 3D-style force layout or simpler API. vis-network is easier to start with but has less customization (no compound nodes, limited edge styles). Cytoscape.js is more proven for narrative graph and ontology visualization. |
| **@tanstack/react-query** | Plain fetch + useState | For a micro-app with 1-2 endpoints. This project has ~8 data-fetching surfaces (series, episodes, graph, claims, notes, revisions, candidate claims, sources). React Query eliminates isLoading/error/refetch boilerplate per endpoint. |
| **@tanstack/react-query** | Zustand + fetch | When graph state is primarily client-authored (user-created nodes, notes). This project's state is server-owned (Neo4j is single source of truth) — React Query's cache-as-source-of-truth model is better than Zustand's in-memory store. |
| **react-router-dom** | No router (single-page graph view) | For v0 prototype, a router may seem unnecessary. But milestones include notes view, revisions view, and settings — all separate pages. Adding router early avoids technical debt of retrofitting navigation. |
| **pytest + httpx** | pytest + TestClient (sync) | When all endpoints are synchronous. Current backend uses sync Neo4j driver inside sync routes, so sync TestClient works now. But future milestones may add async routes (websocket for live graph updates), making async test fixtures necessary. |
| **Vitest** | Jest | When the project already has Jest config. This project has none, and Vitest's Vite-native config sharing is simpler. |
| **Tailwind CSS** | Plain CSS / CSS Modules | For the current project state (Vite scaffold with plain CSS), Tailwind would speed up UI development significantly. However, the root `index.html` uses inline CSS with a custom dark theme — either adopt that theme or rebuild from scratch. **Decision**: Adopt the dark theme from `index.html` as the design reference, use CSS Modules or Tailwind at the team's preference. |
| **react-cytoscapejs** | Raw Cytoscape.js + useRef | For maximum control over the Cytoscape instance lifecycle. react-cytoscapejs is a thin wrapper that handles mount/unmount. If performance tuning becomes necessary, drop the wrapper and manage the instance via ref. Start with the wrapper. |

## What NOT to Use

| Avoid | Why | Use Instead |
|---|---|---|
| **Redux / RTK** | Overkill for this project's state shape. Server state is managed by React Query; client state is spoiler boundary + UI state (~3 values). Redux adds 10x boilerplate. | **React `useContext`** for the spoiler boundary (the one global piece of client state) + **@tanstack/react-query** for all API-fetched data. |
| **SQLAlchemy + Alembic** | This project uses Neo4j, not SQL. SQLAlchemy brings ORM overhead, migration scripts, and a relational mindset that fights the graph data model. | **Neo4j Python Driver** direct Cypher queries. Pydantic handles serialization. |
| **GraphQL (Strawberry / Ariadne)** | Overengineering for a single-user prototype with 6-8 endpoints. GraphQL adds schema complexity, resolver orchestration, and N+1 query problems that don't exist with REST + Neo4j. | **FastAPI REST endpoints** returning Pydantic models. Each endpoint runs one or two Cypher queries — no GraphQL overhead. |
| **D3.js for graph visualization** | D3 is a general-purpose visualization library, not a graph library. Building node/edge interaction (drag, select, compound expand) from D3 primitives takes 5-10x the effort of Cytoscape.js. | **Cytoscape.js** with its built-in layout algorithms, edge handlers, compound nodes, and UI events. |
| **cron-based frontend state polling** | Graph data is refreshed when the user changes their spoiler boundary — this is event-driven, not time-driven. Polling wastes bandwidth and causes visual flicker. | **React Query `refetch()` on spoiler boundary change** — data is fetched once per boundary change and cached until the next change. |
| **WebSocket for real-time graph** | Unnecessary for v0. There's no multi-user collaboration, no live-streaming data, no server-push events. | **REST endpoints** called on user action. The graph data only changes when the user seeds data, edits, or changes their spoiler boundary. |
| **f-strings / .format() for Cypher queries** | SQL/Cypher injection risk and breaks query plan caching. Neo4j's query cache compiles plan for exact parameterized text; f-strings produce different text per call. | **`$param` placeholders** via `session.run(query, param=value)` or `driver.execute_query(..., param=value)`. |

## Stack Patterns by Variant

**If using async Neo4j driver (for websockets or high concurrency):**
- Use `AsyncGraphDatabase` instead of sync `GraphDatabase` — same API, all methods are `await`-able.
- Use `@asynccontextmanager` lifespan to `await driver.verify_connectivity()` on startup.
- Use `asyncio.gather()` for parallel graph queries (e.g., fetch nodes + edges + episodes simultaneously).
- **Current project uses sync driver.** Migrate to async only if a future milestone requires websocket-based live graph updates. The sync driver is simpler and sufficient for v0.

**If using React Query for data fetching (RECOMMENDED):**
- Create `frontend/src/api/client.ts` with a configured `fetch` wrapper or `axios` instance pointing to `http://localhost:8000/api`.
- Create `frontend/src/api/series.ts`, `frontend/src/api/graph.ts`, etc. with React Query hooks using `queryKey: ['series']`, `queryKey: ['graph', seriesId, visibleUntilOrder]`.
- Spoiler boundary state (`visible_until_order`) should be a React context value — when the user changes it, invalidate all graph queries: `queryClient.invalidateQueries({ queryKey: ['graph'] })`.
- Use `staleTime: 5 * 60 * 1000` for series/episode metadata (rarely changes), `staleTime: Infinity` for ontology data (never changes).
- Use `gcTime: 10 * 60 * 1000` for graph data to avoid re-fetching on tab switches.

**If adding user notes and manual editing (Milestone 6):**
- Add `frontend/src/api/notes.ts` with `useNotes(seriesId, episodeId)`, `useCreateNote()`, `useUpdateNote()`, `useDeleteNote()` hooks.
- Notes and user-created nodes are written to Neo4j via dedicated endpoints (`POST /api/notes`, `POST /api/graph/nodes`).
- After a mutation, invalidate the graph query: `queryClient.invalidateQueries({ queryKey: ['graph'] })`.

**If adding revision history (Milestone 7):**
- Add `GET /api/revisions?claim_id=claim_001` endpoint returning list of `Revision` objects.
- Frontend shows revision list in a side panel. React Query `useRevisions(claimId)` with `staleTime: 0` (revisions change when user edits).
- Revert is a `POST /api/revisions/{revision_id}/revert` that replays the previous state.

**If adding LLM extraction pipeline (Milestone 8+):**
- Keep LLM extraction as a background task in FastAPI, not in the request-response cycle.
- The source connector interface defined in the ontology (`Source`, `EvidenceFragment` nodes) should remain the boundary — LLM output maps to `Claim` nodes with `SUPPORTED_BY` relationships to `EvidenceFragment` nodes.
- All LLM-produced claims start as `candidate` status — no user-facing data appears without review.

## Version Compatibility

| Package A | Compatible With | Notes |
|---|---|---|
| fastapi 0.140.7 | neo4j 6.2.0, pydantic 2.13.4, uvicorn 0.51.0 | Verified in current project. FastAPI 0.140.x requires Pydantic 2.x. |
| neo4j 6.2.0 | Python >=3.10 | Python 3.13 (used in project) is supported by neo4j 6.2+. Driver v6 uses Rust-ext for performance. |
| react-cytoscapejs 2.0.0 | cytoscape 3.34.0, react 19.x | react-cytoscapejs 2.0 was built for React 18 but works with React 19. No breaking changes reported. |
| @tanstack/react-query 5.x | React 19.x | Fully compatible. v5 uses the new `useQuery` signature (`({ queryKey, queryFn })`). |
| react-router-dom 7.x | React 19.x, Vite 8.x | v7 works with React 19. Framework mode (loaders/actions) is optional; use library mode for this project. |
| vitest 3.x | vite 8.x, @testing-library/react 16.x | Vitest 3 released alongside Vite 8. Configure via `test: { environment: 'jsdom' }` in vite.config.ts. |
| pytest 9.1.1 | pytest-asyncio 0.25.x, httpx 0.28.1 | pytest-asyncio 0.25 supports pytest 9.x. Use `asyncio_mode = "auto"` in `pytest.ini`. |
| typescript-eslint 8.62.0 | typescript ~6.0.2, eslint 10.6.0 | typescript-eslint v8 supports TypeScript 6.x. The `@typescript-eslint` flat config (`eslint.config.js`) is already set up. |
| PyYAML 6.0.3 | Python >=3.6 | Works with CPython 3.13. CLoader is available for faster YAML parsing on large ontology files. |

## Sources

- [FastAPI official docs](https://fastapi.tiangolo.com/) — confirm async patterns, lifespan, middleware, CORS config
- [Neo4j Python Driver v6 manual](https://neo4j.com/docs/python-manual/current/) — driver lifecycle, execute_query API, async patterns
- [Neo4j Data Modeling Guide](https://neo4j.com/docs/getting-started/data-modeling/guide-data-modeling/) — node/relationship naming conventions, intermediate nodes, property type constraints
- [Neo4j 2026.02 Cypher Manual — Constraint and Index Reference](https://neo4j.com/docs/cypher-manual/current/constraints/) — constraint syntax, property type constraints, relationship property indexes
- [Cytoscape.js v3 docs](https://js.cytoscape.org/) — element data format, layout algorithms (cose-bilkent, concentric, breadthfirst), compound nodes, edge bundling
- [react-cytoscapejs GitHub](https://github.com/plotly/react-cytoscapejs) — wrapper API, event handling, lifecycle
- [TanStack React Query v5 docs](https://tanstack.com/query/v5/docs/framework/react/overview) — query keys, cache invalidation, mutations, staleTime/gcTime semantics
- [React Router v7 docs — Library Mode](https://reactrouter.com/start/library/installation) — declarative routing, nested layouts, URL params for spoiler state
- [Vitest v3 config reference](https://vitest.dev/config/) — vite.config.ts integration, jsdom environment, coverage options
- [pytest-asyncio v0.25 docs](https://pytest-asyncio.readthedocs.io/) — asyncio_mode, async fixtures, event loop scoping
- [Project codebase analysis](.planning/codebase/ARCHITECTURE.md) — existing backend layer structure, concerns about duplicate app construction, startup fragility, missing tests

---

*Stack research for: HD Graf Cehennemi — spoiler-safe narrative knowledge graph*
*Researched: 2026-07-28*
