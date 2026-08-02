# HD Graf Cehennemi — Development Guide

> **Version:** 0.1.0
> **Last updated:** 2026-07-29
> **Project:** Spoiler-aware TV series knowledge graph

---

## Table of Contents

1. [Prerequisites & Quick Start](#1-prerequisites--quick-start)
2. [Backend Development](#2-backend-development)
   - [Backend Structure](#21-backend-structure)
   - [Python Toolchain & Dependencies](#22-python-toolchain--dependencies)
   - [Key Backend Patterns](#23-key-backend-patterns)
   - [Adding a New Route (Backend)](#24-adding-a-new-route-backend)
   - [Running Backend Tests](#25-running-backend-tests)
   - [Test Patterns](#26-test-patterns)
3. [Frontend Development](#3-frontend-development)
   - [Frontend Structure](#31-frontend-structure)
   - [Tech Stack](#32-tech-stack)
   - [Adding a New Component](#33-adding-a-new-component)
   - [Running the Frontend](#34-running-the-frontend)
   - [Frontend Tests](#35-frontend-tests)
4. [Codebase Conventions](#4-codebase-conventions)
   - [Python Conventions](#41-python-conventions)
   - [TypeScript Conventions](#42-typescript-conventions)
   - [Import Paths](#43-import-paths)
   - [Ontology Management](#44-ontology-management)
   - [Spoiler Filtering Rules](#45-spoiler-filtering-rules)
   - [Worktree Workflow](#46-worktree-workflow)
5. [Common Workflows](#5-common-workflows)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Prerequisites & Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Neo4j)
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [Node.js](https://nodejs.org/) — v18 or later

### Quick Start

```bash
# 1. Clone and configure
git clone <repository-url>
cd hdgrafcehennemi
cp .env.example .env

# 2. Start Neo4j
docker compose up -d

# 3. Install Python dependencies and seed the database
uv sync
uv run hdgraf-setup

# 4. Start the backend (terminal 1)
uv run uvicorn backend.app.main:app --reload

# 5. Start the frontend (terminal 2)
cd frontend
npm install
npm run dev
```

The API docs (Swagger UI) open at `http://localhost:8000/docs`. The frontend opens at `http://localhost:5173`.

---

## 2. Backend Development

### 2.1 Backend Structure

```
backend/
├── app/
│   ├── api/              # FastAPI route handlers
│   │   ├── series.py     # Series & episode endpoints
│   │   ├── graph.py      # Spoiler-safe graph read endpoint
│   │   ├── user_content.py # Notes, custom nodes, custom relationships
│   │   └── auth.py       # Google OAuth sign-in / session
│   ├── core/             # Cross-cutting concerns
│   │   ├── config.py     # Pydantic Settings (env vars)
│   │   └── errors.py     # Structured error envelope & handlers
│   ├── domain/           # Pydantic models (shared across layers)
│   │   ├── series.py
│   │   ├── graph.py
│   │   ├── user_content.py
│   │   └── auth.py
│   ├── graph/            # Database & ontology layer
│   │   ├── database.py   # Neo4jDatabase class (async driver wrapper)
│   │   ├── ontology.py   # Ontology YAML loader & validator
│   │   ├── seed.py       # Seed data loader & integrity audit
│   │   └── setup.py      # CLI entry point: hdgraf-setup
│   ├── repository/       # Data access layer
│   │   ├── user.py       # User CRUD (Neo4j)
│   │   ├── session.py    # Session store (in-memory)
│   │   └── user_content.py # Notes, custom nodes, custom relationships
│   ├── services/         # Business logic orchestration
│   │   ├── series.py     # SeriesService
│   │   ├── graph.py      # GraphService (7 concurrent queries)
│   │   └── auth.py       # AuthService (Google token verification)
│   ├── spoiler/          # Spoiler-aware Cypher queries
│   │   └── filter.py     # Parameterized Cypher string constants
│   ├── revisions/        # Revision history (append-only log + revert logic)
│   │   └── __init__.py   # RevisionRepository (log_revision, take_snapshot)
│   └── main.py           # FastAPI app, lifespan, CORS, health check
└── tests/                # Backend tests (pytest)
    ├── conftest.py
    ├── test_graph_api.py
    ├── test_auth.py
    ├── test_user_content_api.py
    ├── test_user_content_models.py
    ├── test_user_content_repository.py
    ├── test_seed_idempotency.py
    ├── test_openapi_contract.py
    └── test_frontend_contract_doc.py
```

### 2.2 Python Toolchain & Dependencies

This project uses **uv** as the package manager. **Never use `pip`** — always use `uv sync` or `uv add`.

```bash
# Install all dependencies (including dev)
uv sync

# Add a new dependency
uv add package-name

# Add a dev dependency
uv add --dev package-name

# Run a CLI command within the virtualenv
uv run some-command
```

Dependencies are declared in `pyproject.toml` at the project root:

```toml
[project]
dependencies = [
    "fastapi>=0.140.7",
    "neo4j>=6.2.0",
    "pydantic-settings>=2.14.2",
    ...
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
    "pytest-asyncio>=1.4.0",
    "httpx>=0.28.1",
]
```

### 2.3 Key Backend Patterns

#### Layered Architecture

Dependencies flow strictly downward: **API → Service → Repository → Database**. Domain models are shared across all layers.

```
API Layer      (backend/app/api/)      — HTTP handlers, routing, request validation
    ↓
Service Layer  (backend/app/services/) — Business logic orchestration
    ↓
Repository     (backend/app/repository/) — Data access abstraction
    ↓
Database       (backend/app/graph/)     — Neo4j driver, connection management
    ↓
Spoiler Filter (backend/app/spoiler/)   — Cypher queries with built-in visibility gating
```

#### Neo4jDatabase (`backend/app/graph/database.py`)

The `Neo4jDatabase` class wraps the async Neo4j driver. It is **lazily initialized** (no import-time side effects) and managed by the FastAPI lifespan:

```python
# Dependency injection for routes
def get_database(request: Request) -> Neo4jDatabase:
    return request.app.state.neo4j

DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]
```

**`execute_query(query, **params)`** — Retryable read/write Cypher execution. Always use **parameterized queries** with the `**parameters` kwargs — never f-string or string interpolation.

**`execute_write(work, command)`** — Managed transaction wrapper for write operations. The `command` is created by the caller before entering the transaction (Neo4j may retry the work function).

#### Parameterized Cypher

All Cypher queries are **string constants** in `backend/app/spoiler/filter.py`. They use `$param` syntax for parameterization:

```python
NODES_QUERY = """
MATCH (node)
WHERE node.series_id = $series_id
  AND any(label IN labels(node) WHERE label IN $node_labels)
  AND node.visible_from_order <= $visible_until_order
RETURN node.id AS id, ...
"""
```

#### Spoiler Filtering in the Data-Access Layer

Every spoiler-sensitive entity carries a `visible_from_order` integer. The frontend sends a `visible_until_order` query parameter, and the **Cypher query filters at the database level** — the application code never receives data it would need to hide:

```python
WHERE entity.visible_from_order <= $visible_until_order
```

This is **fail-closed**: if a query is misconfigured, no data leaks. The `spoiler/filter.py` module is intentionally isolated — it has no FastAPI or Pydantic dependencies.

#### Pydantic Models (`backend/app/domain/`)

- Request/response validation via Pydantic v2 `BaseModel`
- `GraphResponse.enforce_graph_closure()` — a `@model_validator(mode="after")` that rejects dangling edges
- `VisibleUntilOrder` — a Pydantic type enforcing `gt=0` for the spoiler boundary
- `ConfigDict(extra="forbid")` used on critical models to reject unknown fields

#### Dependency Injection via `Depends()`

Services and repositories are injected through FastAPI's `Depends` mechanism:

```python
def get_graph_service(database: DatabaseDependency) -> GraphService:
    return GraphService(database)

GraphServiceDependency = Annotated[GraphService, Depends(get_graph_service)]
```

Error responses use a structured envelope:

```python
def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
```

### 2.4 Adding a New Route (Backend)

The standard pattern for adding a new endpoint:

#### Step 1: Domain Model

Create or extend a Pydantic model in `backend/app/domain/`:

```python
# backend/app/domain/my_feature.py
from pydantic import BaseModel


class MyFeatureResponse(BaseModel):
    id: str
    label: str
```

#### Step 2: Repository Logic

Add data access methods in `backend/app/repository/`:

```python
# backend/app/repository/my_feature.py
from backend.app.graph.database import Neo4jDatabase


class MyFeatureRepository:
    def __init__(self, database: Neo4jDatabase) -> None:
        self._database = database

    async def list_all(self, series_id: str) -> list[dict]:
        return await self._database.execute_query(
            "MATCH (n:MyLabel {series_id: $series_id}) RETURN n.id AS id, n.label AS label",
            series_id=series_id,
        )
```

#### Step 3: Service

Create a service in `backend/app/services/`:

```python
# backend/app/services/my_feature.py
from backend.app.domain.my_feature import MyFeatureResponse
from backend.app.repository.my_feature import MyFeatureRepository


class MyFeatureService:
    def __init__(self, repository: MyFeatureRepository) -> None:
        self._repository = repository

    async def get_all(self, series_id: str) -> list[MyFeatureResponse]:
        rows = await self._repository.list_all(series_id)
        return [MyFeatureResponse.model_validate(row) for row in rows]
```

#### Step 4: Route

Create a route file in `backend/app/api/`:

```python
# backend/app/api/my_feature.py
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.domain.my_feature import MyFeatureResponse
from backend.app.graph.database import Neo4jDatabase, get_database
from backend.app.repository.my_feature import MyFeatureRepository
from backend.app.services.my_feature import MyFeatureService
from backend.app.core.errors import error_responses

router = APIRouter(prefix="/api/series/{series_id}", tags=["my-feature"])
DatabaseDependency = Annotated[Neo4jDatabase, Depends(get_database)]


def get_service(database: DatabaseDependency) -> MyFeatureService:
    return MyFeatureService(MyFeatureRepository(database))


ServiceDependency = Annotated[MyFeatureService, Depends(get_service)]


@router.get("/my-features", response_model=list[MyFeatureResponse],
            responses=error_responses(404, 422, 503))
async def list_my_features(
    series_id: str,
    service: ServiceDependency,
) -> list[MyFeatureResponse]:
    return await service.get_all(series_id)
```

#### Step 5: Register in `main.py`

```python
from backend.app.api.my_feature import router as my_feature_router

# In app creation:
app.include_router(my_feature_router)
```

#### Step 6: Write Tests

Add tests in `backend/tests/` following the patterns in [Section 2.6](#26-test-patterns).

### 2.5 Running Backend Tests

```bash
# Run all backend tests
cd backend
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_graph_api.py

# Run a specific test function
uv run pytest tests/test_graph_api.py::test_graph_boundaries_have_full_json_sentinels

# Run with live database (make sure Neo4j is running)
uv run pytest -x --timeout=60

# Run a specific parametrized case
uv run pytest "tests/test_graph_api.py::test_graph_boundaries_have_full_json_sentinels[1-expected1-forbidden1]"
```

**Important:** Many tests require a running Neo4j instance. Start it first:

```bash
docker compose up -d
```

The test suite is organized into:

| Test File | Focus |
|-----------|-------|
| `test_graph_api.py` | Graph endpoint boundary tests, spoiler filtering, graph closure |
| `test_auth.py` | Google OAuth, session lifecycle, cookie attributes |
| `test_user_content_api.py` | Notes, custom nodes, custom relationships CRUD via API |
| `test_user_content_models.py` | Pydantic model validation for user content |
| `test_user_content_repository.py` | Repository-level tests (direct Neo4j access) |
| `test_seed_idempotency.py` | Seed data idempotency, constraints, null-visibility rejection |
| `test_openapi_contract.py` | OpenAPI schema contract: exact paths, methods, error shapes |
| `test_frontend_contract_doc.py` | Locked frontend API contract doc matches generated OpenAPI |

### 2.6 Test Patterns

#### FastAPI TestClient

Tests create a `TestClient` from the real `main_module.app`, with dependency overrides for faking external services:

```python
from fastapi.testclient import TestClient
import importlib

main_module = importlib.import_module("backend.app.main")

# Use the real app
with TestClient(main_module.app) as client:
    response = client.get("/health")
```

#### conftest.py Fixtures

`backend/tests/conftest.py` sets up `sys.path` and default environment variables:

```python
os.environ.setdefault("NEO4J_URI", "bolt://127.0.0.1:7687")
os.environ.setdefault("NEO4J_USERNAME", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "hdgraf-local-password")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")
```

#### Fixture Patterns

**Live database fixtures** seed real data and clean up after:

```python
@pytest.fixture
def live_client() -> Iterator[TestClient]:
    asyncio.run(_seed_live_database())
    with TestClient(main_module.app) as client:
        yield client
```

**Async database fixtures** for repository-level tests:

```python
@pytest_asyncio.fixture
async def live_database() -> AsyncIterator[Neo4jDatabase]:
    database = Neo4jDatabase()
    database.open()
    await database.verify_connection()
    try:
        yield database
    finally:
        await database.close()
```

**Fake service fixtures** for unit-testing routes without real Neo4j:

```python
class FakeUserRepo:
    async def upsert(self, google_sub, email, display_name, avatar_url):
        ...
```

**Module-scoped fixtures** for expensive operations (seed once per module):

```python
@pytest.fixture(scope="module")
def live_client() -> Iterator[TestClient]:
    _run(_with_database(_seed_and_clean))
    with TestClient(main_module.app) as client:
        yield client
```

#### Parametrized Boundary Tests

Spoiler boundary tests use `@pytest.mark.parametrize` to verify node/edge/claim counts at each episode boundary, with a `forbidden` list asserting no data leaks:

```python
@pytest.mark.parametrize(
    ("boundary", "expected", "forbidden"),
    [
        (1, {"nodes": 11, "edges": 6, "claims": 4, "sources": 1, "evidence": 3},
         ["dexter_s01e02", "S01E02", "Crocodile", ...]),
        ...
    ],
)
def test_graph_boundaries_have_full_json_sentinels(...):
    ...
    serialized = json.dumps(payload, sort_keys=True)
    for sentinel in forbidden:
        assert sentinel.lower() not in serialized.lower()
```

#### Hidden vs Missing Equivalence

Test that hidden resources (beyond the user's spoiler boundary) are indistinguishable from truly missing resources:

```python
def assert_hidden_matches_missing(hidden_response, missing_response):
    assert hidden_response.status_code == missing_response.status_code == 404
    assert hidden_response.json() == missing_response.json()
```

---

## 3. Frontend Development

### 3.1 Frontend Structure

```
frontend/src/
├── api/                    # HTTP client layer
│   ├── client.ts           # Shared fetch wrapper with ApiError
│   ├── graph.ts            # GET /api/series/{id}/graph
│   └── series.ts           # GET /api/series, /api/series/{id}/episodes
├── components/             # React components
│   ├── detail/             # DetailPanel, StructuralEdgeCard
│   ├── episode/            # EpisodeSelector, SeriesSelect, ConfirmAdvanceModal
│   ├── graph/              # GraphCanvas, graphElements, graphStylesheet, GraphStatus
│   ├── layout/             # AppShell
│   └── ui/                 # shadcn/ui primitives (alert, badge, button, card, etc.)
├── hooks/                  # Custom React hooks
│   ├── useGraph.ts
│   ├── useWatchProgress.ts # sessionStorage-backed watch progress state machine
│   ├── useSeries.ts
│   └── useEpisodes.ts
├── types/                  # TypeScript type definitions (mirrors backend domain/)
│   ├── graph.ts            # Mirrors backend/app/domain/graph.py
│   └── series.ts           # Mirrors backend/app/domain/series.py
├── lib/
│   └── utils.ts            # cn() utility (clsx + tailwind-merge)
├── test/
│   ├── fixtures/           # Test fixture data
│   │   └── graphResponse.ts
│   └── setup.ts            # Jest DOM matchers, jsdom stubs
├── App.tsx                 # Root component
├── App.css
├── index.css               # Tailwind CSS v4 entry
└── main.tsx                # React entry point
```

### 3.2 Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| TypeScript | ~6.0 | Type safety (strict mode) |
| Vite | 8 | Build tool & dev server |
| Vitest | 4 | Unit & component testing |
| Tailwind CSS | 4 | Utility-first styling |
| shadcn/ui | Radix Nova style | UI primitives |
| Cytoscape.js | 3 | Graph visualization |
| react-cytoscapejs | 2 | React wrapper for Cytoscape |
| cytoscape-cose-bilkent | 4 | Graph layout algorithm |
| @testing-library/react | 16 | Component testing |
| @testing-library/jest-dom | 7 | DOM matchers for Vitest |
| jsdom | 30 | DOM environment for tests |
| Lucide React | 1 | Icon library |

### 3.3 Adding a New Component

#### Step 1: Create the component file

Place it in the appropriate subdirectory under `components/`:

```tsx
// frontend/src/components/my-feature/MyFeaturePanel.tsx
import { useState } from 'react'

interface MyFeaturePanelProps {
  title: string
}

export function MyFeaturePanel({ title }: MyFeaturePanelProps) {
  const [open, setOpen] = useState(false)
  return (
    <div>
      <h2>{title}</h2>
      <button onClick={() => setOpen(!open)}>
        {open ? 'Close' : 'Open'}
      </button>
    </div>
  )
}
```

#### Step 2: Register in the component tree

Import and use the component in `App.tsx` or a parent component:

```tsx
import { MyFeaturePanel } from './components/my-feature/MyFeaturePanel'

// Inside App.tsx or wherever appropriate
<MyFeaturePanel title="My Feature" />
```

#### Step 3: Add types if needed

Extend `frontend/src/types/` with any new type definitions that mirror backend domain models.

#### Step 4: Write tests

```tsx
// frontend/src/components/my-feature/MyFeaturePanel.test.tsx
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MyFeaturePanel } from './MyFeaturePanel'

describe('MyFeaturePanel', () => {
  it('renders the title', () => {
    render(<MyFeaturePanel title="Hello" />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

### 3.4 Running the Frontend

```bash
# Development server (auto-reloads on changes)
cd frontend
npm run dev
# Opens at http://localhost:5173

# Production build
npm run build

# Run tests
npm test

# Run tests in watch mode
npx vitest

# Lint
npm run lint
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000` (configured in `vite.config.ts`), so no CORS issues during development.

### 3.5 Frontend Tests

Frontend tests use **Vitest** with `@testing-library/react`.

#### Test Configuration

Defined in `vite.config.ts`:

```typescript
test: {
  environment: 'jsdom',
  globals: true,
  setupFiles: ['./src/test/setup.ts'],
}
```

#### Test Setup (`frontend/src/test/setup.ts`)

- Imports `@testing-library/jest-dom/vitest` for DOM matchers
- Stubs `ResizeObserver` and pointer capture methods (missing in jsdom, required by shadcn/Radix primitives)

#### Component Test Pattern

```tsx
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

describe('ComponentName', () => {
  it('renders and responds to interaction', async () => {
    const onSelect = vi.fn()
    render(<ComponentName onSelect={onSelect} />)

    expect(screen.getByText('Expected Text')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button'))
    expect(onSelect).toHaveBeenCalledTimes(1)
  })
})
```

#### Graph Component Testing

Cytoscape components mock `react-cytoscapejs` to avoid real canvas rendering under jsdom:

```typescript
vi.mock('react-cytoscapejs', () => {
  function CytoscapeComponentStub(props) {
    capturedElements = props.elements
    props.cy?.({ on: () => {}, container: () => null })
    return <div data-testid="graph-canvas-stub" />
  }
  return { default: CytoscapeComponentStub }
})
```

#### Running Tests

```bash
# Run all frontend tests
cd frontend && npm test

# Run with UI
npx vitest --ui

# Run a specific test file
npx vitest src/components/graph/GraphCanvas.test.tsx
```

---

## 4. Codebase Conventions

### 4.1 Python Conventions

- **Python 3.13+** — all code must target 3.13+
- **FastAPI** — route handlers are async functions
- **Pydantic v2** — all domain models use `BaseModel` with type annotations
- **Neo4j Python Driver** — async (v6.2+), never sync driver
- **pytest** — all tests use pytest, never `unittest`
- **Type hints** — every function has full type annotations; use `from __future__ import annotations` at the top of every module
- **Error envelope** — all errors use `{"detail": {"code": "...", "message": "..."}}` format via `backend/app/core/errors.py`
- **`__init__.py`** — all packages have `__init__.py` (even if empty)

### 4.2 TypeScript Conventions

- **React 19** — functional components with hooks, no class components
- **TypeScript linting** — no `strict` flag is set in `tsconfig.app.json`; type safety relies on `noUnusedLocals`, `noUnusedParameters`, and `noFallthroughCasesInSwitch`
- **`@/` prefix** — all source imports use `@/` alias for `src/`
- **Types mirror backend** — `types/` directory mirrors `backend/app/domain/` field-for-field
- **No runtime visibility filtering** — frontend code must never check `visible_from_order`. If data is in the response, it's safe to render.

### 4.3 Import Paths

#### Python

All Python imports use **absolute paths from the project root**:

```python
# ✅ Correct
from backend.app.domain.graph import GraphResponse
from backend.app.graph.database import Neo4jDatabase
from backend.app.services.graph import GraphService

# ❌ Wrong
from ..domain.graph import GraphResponse  # No relative imports
from services.graph import GraphService  # No bare module names
```

#### TypeScript

All frontend imports use the `@/` prefix for `src/`:

```typescript
// ✅ Correct
import { GraphNode } from '@/types/graph'
import { useGraph } from '@/hooks/useGraph'
import { AppShell } from '@/components/layout/AppShell'

// ❌ Wrong
import { GraphNode } from '../../types/graph'
```

### 4.4 Ontology Management

The ontology defines the graph's type system and is **versioned via YAML files** in `ontology/`:

```
ontology/
├── node_types.yaml       # Structural, narrative, knowledge, user, system node types
├── relation_types.yaml   # Structural, participation, character, provenance, revision
└── claim_types.yaml      # Claim types, statuses, confidence levels
```

**When modifying the ontology:**

1. Edit the appropriate YAML file (increment `ontology_version` for breaking changes)
2. If adding new node labels, add uniqueness constraints in `backend/app/graph/seed.py` (`create_constraints()`)
3. Add seed data in `data/dexter/seed/` or `data/dexter/metadata/`
4. Update `NODE_LABELS` / `RELATIONSHIP_TYPES` tuples in `graph/seed.py` if adding new labels/types
5. Restart the backend (live ontology reload is not yet supported)

**Runtime validation:** `load_ontology()` validates YAML version, builds frozen `Ontology` dataclass. Seed validation calls `ontology.require_node_type()`, `ontology.require_relationship_type()`, etc.

### 4.5 Spoiler Filtering Rules

These are **hard constraints** on the codebase:

1. **Never bypass backend spoiler filtering in frontend code.** The frontend must not check `visible_from_order` on received data. If the data is in the response, the backend has deemed it safe.
2. **Never accept `visible_from_order` from the client.** The server derives visibility from the referenced entity (note inherits target's visibility, custom node inherits episode's visibility).
3. **All Cypher queries in `spoiler/filter.py`** must include the `visible_from_order <= $visible_until_order` filter.
4. **Hidden direct reads return 404**, indistinguishable from missing resources. No counts or metadata in responses.
5. **The spoiler boundary must match a persisted episode order.** Invalid, missing, zero, or negative boundaries return 422.
6. **`graphElements.ts`** maps all received data to Cytoscape elements without any visibility filter.

### 4.6 Worktree Workflow

Only the single primary worktree currently exists on disk (verify with `git worktree list`). All backend and frontend development happens directly in this checkout — there are no separate `backend-work` or `frontend-work` worktrees at this time. If parallel worktrees are introduced later, add them with `git worktree add <path> <branch>` and document the paths here.

---

## 5. Common Workflows

### Full Reset

```bash
# Stop and remove Neo4j data
docker compose down -v
docker compose up -d

# Re-seed
uv run hdgraf-setup

# Re-run tests
cd backend && uv run pytest -v
```

### Adding Seed Data for a New Episode

1. Add episode metadata to `data/dexter/metadata/` (JSON)
2. Add characters, events, locations, claims, sources, evidence to `data/dexter/seed/` (JSON)
3. Ensure all new entities have unique string IDs and correct `visible_from_order`
4. Ensure all claims have at least one `SUPPORTED_BY` EvidenceFragment and a `REFERS_TO` Source
5. Run `uv run hdgraf-setup` to re-seed
6. Update parametrized boundary tests in `test_graph_api.py` with new counts

### Adding a New Relationship Type

1. Add the type to the appropriate group in `ontology/relation_types.yaml`
2. If user-safe, add it to the `participation` or `character` group in `ontology/relation_types.yaml` — the `Ontology.user_safe_relationship_types` property in `backend/app/graph/ontology.py` computes the user-safe set by unioning those two YAML groups (there is no separate `user_safe_relationship_types` YAML group)
3. Add to `STRUCTURAL_EDGES_QUERY` or `VISIBLE_CLAIMS_QUERY` in `spoiler/filter.py` as appropriate
4. Update stylesheet in `frontend/src/components/graph/graphStylesheet.ts`
5. Update frontend types in `frontend/src/types/graph.ts` if needed

### Running Full Test Suite

```bash
# Backend
docker compose up -d  # Ensure Neo4j is running
cd backend && uv run pytest -v

# Frontend
cd frontend && npm test
```

---

## 6. Troubleshooting

### Neo4j Connection Issues

```bash
# Check if Neo4j is running
docker compose ps neo4j

# Check Neo4j logs
docker compose logs neo4j

# Test connectivity
curl http://localhost:7474
```

If the backend returns 503 on `/health`, ensure:
- Docker Desktop is running
- `docker compose up -d` has completed
- `NEO4J_PASSWORD` in `.env` matches `docker-compose.yml`

### Test Failures

```bash
# Backend: run with full traceback
cd backend && uv run pytest -v --tb=long

# Frontend: run with coverage
cd frontend && npx vitest --coverage
```

### Common Issues

| Issue | Solution |
|---|---|
| `uv run pytest` fails with `ServiceUnavailable` | Ensure Neo4j is running: `docker compose up -d` |
| `uv` not found | Install from https://docs.astral.sh/uv/ |
| `npm run dev` fails with port in use | Kill the Vite process or change port in `vite.config.ts` |
| Frontend returns 502 on `/api` calls | Ensure backend is running on port 8000 |
| Seed fails with `OntologyValidationError` | Check that `ontology_version` in YAML files matches expected version |
| Test assertion counts drift after adding seed data | Update expected counts in parametrized tests |

### Debugging Spoiler Filtering

To verify what data is visible at a given boundary:

```bash
curl "http://localhost:8000/api/series/series_dexter/graph?visible_until_order=1" | jq '.nodes | length'
curl "http://localhost:8000/api/series/series_dexter/graph?visible_until_order=1" | jq '.edges | length'
```

Compare counts across boundaries (order=1, order=2, order=3) to verify incremental visibility.

---

## 7. Newer Backend & Frontend Modules

> The structure trees in [2.1 Backend Structure](#21-backend-structure) and [3.1 Frontend Structure](#31-frontend-structure) predate several subsystems that now exist in the codebase (chat/retrieval, settings, candidates, ChangeSets). This section documents them additively without editing those trees — see [docs/ARCHITECTURE.md](ARCHITECTURE.md) sections 4.8–4.9 for the full data-flow design.

### 7.1 Additional Backend Modules

| Directory | New files | Purpose |
|---|---|---|
| `backend/app/api/` | `candidates.py`, `change_set.py`, `chat.py`, `progress.py`, `settings.py` | Candidate-claim review, ChangeSet propose/confirm/reject/revert, chat sessions & streaming, watch-progress persistence, LLM settings |
| `backend/app/domain/` | `extraction.py`, `change_set.py`, `chat.py`, `progress.py`, `revision.py`, `settings.py` | Pydantic contracts for the above (`ExtractionClaim`, `ExtractionBatchEnvelope`, `LLMSettingsResponse/Update`, etc.) |
| `backend/app/graph/` | `candidates.py`, `change_set.py`, `chat.py`, `progress.py` | Neo4j access for candidate ingest, ChangeSet apply/revert, chat message persistence, progress read/write |
| `backend/app/repository/` | `change_set.py`, `chat.py`, `progress.py`, `settings.py` | Repository layer for the same subsystems (`SettingsRepository`, `ChatRepository`, etc.) |
| `backend/app/services/` | `change_set.py`, `chat.py`, `progress.py`, `settings.py` | Service orchestration (`ChangeSetService`, `ChatService`, `ProgressService`, `SettingsService`) |
| `backend/app/retrieval/` (new top-level package) | `pipeline.py`, `tools.py` | GraphRAG-lite retrieval pipeline and the allowlisted retrieval tool functions |
| `backend/app/llm/` (new top-level package) | `provider.py`, `system_prompt.py`, `fallbacks.py` | `LLMProvider` protocol + `OpenAICompatibleProvider`, system prompt template, localized fallback text |

### 7.2 Additional Frontend Modules

| Directory | New files | Purpose |
|---|---|---|
| `frontend/src/components/chat/` | `ChatLauncher`, `ChatSheet`, `ChatPanel`, `MessageList`, `MessageBubble`, `CitationChip`, `SessionPicker`, `ChangeSetCard` (+ `.test.tsx` per component) | The chat UI: launcher button, slide-over sheet, streaming message list, citation chips that focus the graph, and the ChangeSet confirm/reject preview card |
| `frontend/src/components/settings/` | `SettingsPage.tsx` (+ test) | LLM provider configuration form (provider, model, base URL, API key, enable toggle, assistant language) |
| `frontend/src/components/auth/` | `LoginPage.tsx` | Google Sign-In entry screen |
| `frontend/src/providers/` (new top-level directory) | `AuthContext.ts`, `AuthProvider.tsx`, `useAuth.ts` | App-wide auth context wrapping the session-cookie flow; `useAuth()` throws if called outside `AuthProvider` |
| `frontend/src/hooks/` | `useChatMessages.ts`, `useChatSessions.ts`, `useNotes.ts`, `useRevisions.ts` (+ `.test.tsx`/`.test.ts` per hook) | Chat session/message state, notes CRUD, revision history |
| `frontend/src/api/` | `auth.ts`, `changeSet.ts`, `chat.ts`, `progress.ts`, `revisions.ts`, `settings.ts`, `userContent.ts` (+ `.test.ts` per client) | HTTP clients for each new subsystem |

### 7.3 Adding a Candidate-Extraction Ingest Source

The candidate pipeline lets a future extractor submit claims for review without touching canonical data. To add a new extractor/ingest path:

1. Produce an `ExtractionBatchEnvelope` (`backend/app/domain/extraction.py`) — `extractor_name`, `extractor_version`, `run_timestamp`, and 1-500 `ExtractionClaim` items. Each claim carries `schema_version`, subject/predicate/object, `claim_type` and `confidence_level` (both validated against the loaded ontology via `field_validator`), `visible_from_order`, evidence text/locator, and source type/locator.
2. `POST /api/series/{series_id}/candidates/ingest` hands the envelope to `CandidateRepository.ingest_batch()` (`backend/app/graph/candidates.py`), which runs one Neo4j write transaction per batch.
3. IDs are **deterministic**, derived by hashing normalized claim content (`_derive_candidate_id`, `_derive_source_id`, `_derive_evidence_id` — SHA-256 prefix), so re-ingesting the same extraction output is idempotent (`MERGE ... ON CREATE / ON MATCH`).
4. Ingested claims land with `origin: 'candidate'`, `status: 'candidate'` — visible in the graph but visually distinguished (dashed border) and excluded from canonical claim guarantees.
5. Review lifecycle: `GET /candidates` (list) → `GET/PATCH /candidates/{claim_id}` (inspect/edit) → `POST /candidates/{claim_id}/approve` (promotes to `corroborated`) or `POST /candidates/{claim_id}/reject`.
6. Add tests following `backend/tests/test_candidate_ingest.py` (batch ingest, idempotency) and `test_candidate_review.py` (approve/reject transitions).

### 7.4 Settings Management Pattern (Runtime LLM Configuration)

Unlike most configuration (env-var only, see [docs/CONFIGURATION.md](CONFIGURATION.md)), the LLM provider config is **runtime-editable and persisted in Neo4j**, with environment variables as the fallback. Reference implementation when adding a similar runtime-configurable setting:

- **Domain** (`backend/app/domain/settings.py`) — `LLMSettingsResponse` / `LLMSettingsUpdate` Pydantic models; `mask_api_key()` produces a display-safe form (e.g. `••••1234`) and the full key is never included in any response model.
- **Repository** (`backend/app/repository/settings.py`) — `SettingsRepository` persists a single `(:AppSetting {key: 'llm'})` node; reads/writes are plain `MERGE`/`SET`.
- **Service** (`backend/app/services/settings.py`) — `SettingsService` implements the precedence rule: stored Neo4j value wins per-field if present, otherwise falls back to the matching `LLM_*` environment variable/setting.
- **API** (`backend/app/api/settings.py`) — `GET /api/settings/llm` (masked key) and `PUT /api/settings/llm` (blank/omitted `api_key` keeps the previously stored key rather than clearing it); both require an authenticated session (`CurrentUserDependency`).
- **Frontend** — `frontend/src/api/settings.ts` + `frontend/src/types/settings.ts` + `frontend/src/components/settings/SettingsPage.tsx`. The load-on-mount `GET` is treated as best-effort: a failed load never blocks the form or the subsequent `PUT` — it only sets an informational error message and leaves the form with editable defaults.
- Add tests following `backend/tests/test_settings_api.py` (masking, precedence, partial-update key retention).

### 7.5 Chat / Retrieval Development Pattern

The chat feature (see [docs/ARCHITECTURE.md § 4.8](ARCHITECTURE.md#48-graphrag-lite-chat-pipeline)) has its own development pattern, distinct from the standard API/Service/Repository route pattern in [Section 2.4](#24-adding-a-new-route-backend):

- **`backend/app/llm/provider.py`** — `LLMProvider` is a `Protocol`; `OpenAICompatibleProvider` is the only shipped implementation. Adding a new provider means implementing the protocol (`stream_chat(...)`) and registering it in `SettingsService`'s provider dispatch — never adding a second HTTP client ad hoc inside `ChatService`.
- **`backend/app/retrieval/tools.py`** — Adding a new retrieval tool means writing a small async function that (a) accepts only allowlisted, typed parameters — never a free-text Cypher string, (b) re-derives `visible_until_order` from the value already resolved by the pipeline (never from tool-call arguments), and (c) issues parameterized Cypher built the same way as `spoiler/filter.py`. Register the new tool in the pipeline's allowlist in `backend/app/retrieval/pipeline.py`.
- **`backend/app/retrieval/pipeline.py`** — Orchestrates the tool-calling loop and the citation validator (strips any `claim_id`/`evidence_id`/`source_id` the model cited that wasn't actually present in retrieved context).
- **Streaming** — `POST .../messages/stream` returns Server-Sent Events; the frontend (`ChatPanel.tsx`) consumes it via `fetch` + a `ReadableStream` reader (not `EventSource`, since it needs `credentials: 'include'` for the session cookie). A non-streaming fallback endpoint (`POST .../messages`) exists for environments where SSE isn't viable.
- Add backend tests following `backend/tests/test_retrieval_tools.py` (per-tool visibility enforcement), `test_retrieval_pipeline.py` (citation validation, context bounding), `test_chat_api.py` / `test_chat_persistence.py` (session lifecycle, hide-not-delete on progress decrease), and `test_llm_provider.py` (provider protocol compliance).
- Add frontend tests following `ChatPanel.test.tsx` / `MessageList.test.tsx` (streaming render) and `useChatMessages.test.tsx` / `useChatSessions.test.tsx` (hook state).

### 7.6 ChangeSet Development Pattern

When adding a new ChangeSet operation type (see [docs/ARCHITECTURE.md § 4.9](ARCHITECTURE.md#49-changeset-two-stage-mutation-flow)):

1. Add the new operation literal to the discriminated union in `backend/app/domain/change_set.py` (extend, don't loosen — `extra="forbid"` must still reject unknown fields).
2. Implement the apply-time Cypher for the new operation in `backend/app/graph/change_set.py`, inside the same single-transaction apply path used by existing operations.
3. Add ontology/boundary validation for the new operation in `backend/app/services/change_set.py`'s propose-time validator (target must be visible, same-series, not canonical/candidate unless explicitly permitted).
4. Update `frontend/src/components/chat/ChangeSetCard.tsx` to render a summary line and Before/After rows for the new operation type.
5. Add tests following `backend/tests/test_change_set_api.py` (propose validation), `test_change_set_confirmation.py` (apply/reject/idempotency), `test_change_set_protection.py` (canonical/candidate refusal), and `test_change_set_revision.py` (revision logging + revert).
