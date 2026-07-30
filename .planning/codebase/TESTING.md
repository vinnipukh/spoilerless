---
last_mapped: 2026-07-30
focus: quality
---

# Testing

## Current Status

Both backend and frontend now have substantial automated test suites. Backend tests are Neo4j-integration tests run against a live local instance (no mocking of the database); frontend tests are Vitest + Testing Library component/hook tests run under jsdom.

## Backend Test Tooling

- Runner: `pytest` (`backend/pyproject.toml` / root `pyproject.toml` dev group: `pytest>=9.1.1`, `httpx>=0.28.1`).
- Client: `fastapi.testclient.TestClient`, imported per test module.
- Test files: `backend/tests/*.py` (13 modules), covering auth, candidate ingest/review, extraction models, frontend contract doc, graph API, OpenAPI contract, revision models/behavior, seed idempotency, user-content models/API/repository.

**Run commands:**
```bash
cd backend && python -m pytest              # all tests
cd backend && python -m pytest tests/test_revisions.py -v   # single module
```

## Test Bootstrap (`backend/tests/conftest.py`)

- Inserts `backend/` and the repo root onto `sys.path` so both `backend.app.*` and `backend.tests.*` import paths resolve regardless of working directory.
- Sets default env vars via `os.environ.setdefault(...)` before any app import: `NEO4J_URI=bolt://127.0.0.1:7687`, `NEO4J_USERNAME=neo4j`, `NEO4J_PASSWORD=hdgraf-local-password`, `NEO4J_DATABASE=neo4j`.
- **Tests require a real, running local Neo4j instance** — there is no in-memory or mocked graph driver. `setup_database(database)` (from `backend/app/graph/seed.py`) reseeds canonical data at the start of relevant fixtures.

## Fixture Patterns

**Live client fixture** (module-scoped, shared across many test files):
```python
@pytest.fixture(scope="module")
def live_client() -> Iterator[TestClient]:
    asyncio.run(_seed_live_database())
    main_module = importlib.import_module("backend.app.main")
    with TestClient(main_module.app) as client:
        yield client
```
`_seed_live_database()` opens a `Neo4jDatabase()`, calls `verify_connection()`, runs `setup_database(database)`, then closes. See `backend/tests/test_candidate_ingest.py`, `backend/tests/test_user_content_api.py`.

**User-content client fixture** (`backend/tests/test_user_content_api.py`, reused by `backend/tests/test_revisions.py` via direct import): builds on `live_client`, adds per-test cleanup of `origin: 'user'` nodes and `Revision` nodes before/after each test via Cypher `DETACH DELETE` queries (`USER_ONLY_CLEANUP_QUERY`, `REVISION_CLEANUP_QUERY`). This keeps canonical seed data stable across the whole suite while giving each test a clean slate for user-authored content.

**Cross-module fixture reuse:** `backend/tests/test_revisions.py` and `backend/tests/test_candidate_review.py` import fixtures and helpers directly from `backend/tests/test_user_content_api.py` (e.g. `user_content_client`, `live_client`, `direct_database_snapshot`, `override_database`, `second_series`, `assert_hidden_matches_missing`) rather than duplicating setup — treat `test_user_content_api.py` as the shared fixture module for user-content-adjacent tests.

**Direct DB mutation for setup:** tests use `direct_database_snapshot(query, **params)` to mutate graph state outside the API (e.g. flipping a resource's `origin` to `'canonical'` to test the 409 revert-canonical path) — see `TestRevertCanonicalResource` in `backend/tests/test_revisions.py`.

**Fixture data files:** JSON fixtures for extraction/candidate tests live under `data/dexter/test/` (e.g. `data/dexter/test/extraction_fixture.json`), loaded via a `@pytest.fixture` that opens and `json.load`s the file (`backend/tests/test_candidate_ingest.py`).

## Test Structure & Naming

- Test classes group related behavior and carry a docstring naming the requirement(s) under test, e.g.:
  ```python
  class TestRevertCanonicalResource:
      """Prove D-11: reverting a canonical resource returns 409."""
      def test_revert_canonical_resource_returns_409(self, user_content_client): ...
  ```
- One test method per class is common for focused scenarios; broader classes (`TestRevisionListFilters`) hold multiple assertions in one flow.
- Helper functions prefixed `_` (e.g. `_create_note`, `_list_revisions`, `_get_revision`, `_revert_revision`, `_find_revision` in `backend/tests/test_revisions.py`) wrap repeated HTTP calls to keep test bodies readable.
- A `TestExistingTestsStillPass` regression-guard class pattern is used to signal — via docstring, not runtime re-execution — that a new test module's changes did not break a related module's existing suite.

## Assertions & Response Contracts

- Assertions check both HTTP status code and JSON body shape/values directly on `response.json()`.
- Error assertions check the structured code, not just status: `resp.json()["detail"]["code"] == "cannot_revert_create"`.
- `backend/tests/test_openapi_contract.py` and `backend/tests/test_frontend_contract_doc.py` guard the API's OpenAPI schema and any frontend-facing contract documentation against drift.

## Frontend Test Tooling

- Runner: Vitest (`frontend/package.json` devDependency `vitest ^4.1.10`), environment `jsdom`, globals enabled, configured inline in `frontend/vite.config.ts` under `test: {...}`.
- Libraries: `@testing-library/react ^16.3.2`, `@testing-library/jest-dom ^7.0.0` (imported via the `/vitest` subpath for typed matchers), `@testing-library/user-event ^14.6.1`.
- Test files: 9 files across `frontend/src/` — `App.test.tsx`, `components/detail/DetailPanel.test.tsx`, `components/detail/RevisionHistoryPanel.test.tsx`, `components/detail/StructuralEdgeCard.test.tsx`, `components/episode/ConfirmAdvanceModal.test.tsx`, `components/graph/GraphCanvas.test.tsx`, `components/graph/graphElements.test.ts`, `components/graph/relationshipStyles.test.ts`, `hooks/useRevisions.test.tsx`, `hooks/useWatchProgress.test.ts`.

**Run commands:**
```bash
cd frontend && npm run test          # vitest (watch by default)
cd frontend && npx vitest run        # single run, CI mode
cd frontend && npx vitest run <path> # single file
```

## Frontend Test Setup (`frontend/src/test/setup.ts`)

Loaded via `vite.config.ts`'s `test.setupFiles`. Handles environment gaps between jsdom and the real browser APIs shadcn/Radix components need:

- Imports `@testing-library/jest-dom/vitest` (not the bare `jest-dom` entry) so `toBeInTheDocument()` etc. type-check under Vitest's `Assertion` interface with `tsc -b`.
- **React 19 `act()` workaround:** React 19.2.x canary doesn't export `React.act`; `react-dom/test-utils` expects it. Setup polyfills `(React as any).act = (fn) => fn()` if missing. This import must come after the jest-dom import for Vitest's module graph to process correctly.
- Polyfills `Element.prototype.hasPointerCapture/setPointerCapture/releasePointerCapture` and `scrollIntoView` — needed for Radix `Select`/`Dialog`/`Sheet` interaction under jsdom.
- Polyfills `globalThis.ResizeObserver` with a no-op class.
- Polyfills `window.matchMedia` — `GraphCanvas.tsx` calls it at module scope to detect `prefers-reduced-motion`; jsdom does not implement it.

## Component/Hook Test Patterns

**Simple render + query (Testing Library):**
```typescript
import { render, screen } from '@testing-library/react'
render(<StructuralEdgeCard selected={selected} nodes={graphResponseS01E01.nodes} />)
expect(screen.getByRole('heading', { name: 'PART_OF' })).toBeInTheDocument()
expect(screen.queryByRole('tablist')).not.toBeInTheDocument()
```
See `frontend/src/components/detail/StructuralEdgeCard.test.tsx`.

**Hook tests use `ReactDOM.flushSync` + manual root management instead of `@testing-library/react-hooks`/`renderHook`:**
```typescript
function render(ui: React.ReactElement) {
  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = ReactDOMClient.createRoot(container)
  ReactDOM.flushSync(() => { root.render(ui) })
  return { container, root }
}
```
A `TestComp` wrapper function component calls the hook and stashes its return value in an outer `let captured: any = null`, which the test then asserts on. State transitions are awaited with `await vi.waitFor(() => expect(captured.status).toBe('success'))`. Always call `root.unmount()` at the end of each test. See `frontend/src/hooks/useRevisions.test.tsx`.

**Mocking the API layer:** `vi.mock('../api/revisions', () => ({ getRevisions: vi.fn() }))` at module top, then `vi.mocked(getRevisions).mockResolvedValue([...])` / `.mockRejectedValue(new Error(...))` per test. `beforeEach` resets: `document.body.innerHTML = ''; vi.clearAllMocks()` plus a default safe mock so unrelated async effects don't throw.

**Fixtures:** shared graph-response test fixtures live in `frontend/src/test/fixtures/` (e.g. `frontend/src/test/fixtures/graphResponse.ts`, imported as `graphResponseS01E01`).

## Frontend Quality Gates

```bash
cd frontend && npm run lint     # ESLint
cd frontend && npm run build    # tsc -b && vite build
cd frontend && npm run test     # vitest
```

## Manual Verification Targets

- `/health` returns service status after Neo4j startup succeeds.
- Graph rendering behaviors not covered by component tests (visual layout, animation) — verify by running the app (see `run` skill) and inspecting Cytoscape canvas interactions.
- Candidate review UI workflows are planned (Phase 05.1) but not yet built; once built they will need both automated coverage and manual UAT per the existing revision/notes pattern.

## Testing Gaps

- No CI workflow currently runs lint/build/test on push (no `.github/workflows/` present at last check — verify before assuming CI exists).
- Backend tests depend on a live local Neo4j instance; there is no fast in-memory/unit-test path for pure business logic that avoids network round-trips.
- No end-to-end (Playwright/Cypress) tests exercising the full frontend-against-real-backend flow.
- `test_extraction_models.py` and `test_candidate_review.py` cover the Phase 5 candidate/extraction backend; the upcoming Phase 05.1 candidate-review frontend UI has no test coverage yet — new components should follow the colocated `Component.test.tsx` + Testing Library pattern above.

---

*Testing analysis: 2026-07-30*
