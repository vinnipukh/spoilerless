---
last_mapped: 2026-08-02
focus: quality
last_mapped_commit: 0b4c83c8ca7c8c0004552cb55b53a5050978c30c
---
# Testing Patterns

**Analysis Date:** 2026-08-02

## Test Framework

**Backend runner:**
- Pytest `>=9.1.1` with pytest-asyncio `>=1.4.0`, HTTPX, and FastAPI `TestClient`, declared in `pyproject.toml`.
- Root config in `pyproject.toml` sets `asyncio_mode = "auto"` and `testpaths = ["backend/tests"]`; Python `>=3.13` is required.
- The tracked backend suite has 28 `test_*.py` files plus `backend/tests/conftest.py`. There are no configured unit/integration markers.

**Frontend runner:**
- Vitest `^4.1.10`, Testing Library, jest-dom, user-event, and jsdom are declared in `frontend/package.json`.
- `frontend/vite.config.ts` sets `environment: 'jsdom'`, enables Vitest globals, and loads `frontend/src/test/setup.ts`.
- The live reliable run on 2026-08-02 passed 24 test files and 173 tests. It also emitted existing React `act(...)` warnings from several suites; passing status does not make those warnings a preferred pattern.

**Assertion libraries:**
- Backend uses plain pytest `assert`, `pytest.raises`, and parametrization in `backend/tests/`.
- Frontend uses Vitest `expect` plus `@testing-library/jest-dom/vitest` matchers registered by `frontend/src/test/setup.ts`.

**Run commands:**
```bash
uv run pytest                                           # configured backend suite; run from repository root
uv run pytest backend/tests/test_openapi_contract.py    # one backend file
uv run pytest backend/tests/test_graph_api.py -k "graph_error_shapes"

cd frontend
NODE_ENV=test CI=1 npm run test                         # reliable one-shot frontend suite
NODE_ENV=test npm run test                              # watch mode
NODE_ENV=test CI=1 npm run test -- src/App.test.tsx     # one frontend file
```
- Run backend tests from the repository root because some tests open root-relative artifacts under `data/` and `docs/`.
- Set `NODE_ENV=test` explicitly. An inherited `NODE_ENV=production` loads React production behavior and causes misleading `act`/empty-render failures despite Vitest mode being test.

## Test File Organization

**Backend location and naming:**
- Keep tests in `backend/tests/`, named `test_*.py`, with functions/methods named `test_*`.
- `backend/tests/conftest.py` only configures import paths and default live-Neo4j environment variables. Most fixtures, fakes, helper builders, and cleanup live in the owning test module.
- Large integration-heavy suites include `backend/tests/test_chat_api.py` (1,055 lines) and `backend/tests/test_retrieval_tools.py` (912 lines).

**Frontend location and naming:**
- Colocate tests with source as `*.test.ts` or `*.test.tsx`, for example `frontend/src/api/chat.test.ts` and `frontend/src/components/settings/SettingsPage.test.tsx`.
- Keep shared payloads in `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts`; keep suite-wide DOM shims in `frontend/src/test/setup.ts`.
- The largest frontend test is `frontend/src/App.test.tsx` (595 lines), which exercises cross-component behavior with a substantial Cytoscape stub.

**Structure:**
```text
backend/tests/
├── conftest.py
├── test_<api-or-domain>.py
└── test_<repository-or-contract>.py

frontend/src/
├── App.test.tsx
├── api/*.test.ts
├── hooks/*.test.ts(x)
└── components/<feature>/*.test.tsx
```

## Test Structure

**Backend suite organization:**
```python
@pytest.fixture
def client(...) -> Iterator[TestClient]:
    with TestClient(_build_app(...), raise_server_exceptions=False) as client:
        yield client

@pytest.mark.parametrize("bad_url", [...])
def test_update_rejects_non_http_base_url(client, bad_url: str) -> None:
    response = client.put(...)
    assert response.status_code == 422, response.text
```
- Use Arrange/Act/Assert flow with direct status/body assertions, as in `backend/tests/test_settings_api.py`.
- Build minimal FastAPI applications and override dependencies when a router is the unit under test (`backend/tests/test_settings_api.py`).
- Use exact-set and shape assertions for closed contracts rather than partial presence checks (`backend/tests/test_openapi_contract.py`).
- Use `pytest.mark.parametrize` for boundary/security matrices, such as rejected base URL schemes in `backend/tests/test_settings_api.py`.
- Async tests may use `pytest.mark.asyncio`; `asyncio_mode = "auto"` also supports async fixtures and keeps async test/fixture work on the pytest loop.

**Frontend suite organization:**
```typescript
vi.mock('@/api/settings', () => ({
  getLLMSettings: vi.fn(),
  updateLLMSettings: vi.fn(),
}))

afterEach(() => vi.clearAllMocks())

describe('SettingsPage', () => {
  it('saves provider + api key via PUT', async () => {
    const user = userEvent.setup()
    render(<SettingsPage onBack={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: 'Save settings' }))
    expect(updateLLMSettings).toHaveBeenCalledWith(expect.objectContaining(...))
  })
})
```
- Prefer behavior-focused `describe`/`it` suites, Testing Library rendering, accessible role/name queries, and `userEvent.setup()`.
- Use `findBy*` or `waitFor` for async UI changes; wrap direct hook state transitions in `act`, as in `frontend/src/hooks/useWatchProgress.test.ts`.
- Reset shared state in `beforeEach`/`afterEach` with `sessionStorage.clear()`, `vi.clearAllMocks()`, `vi.restoreAllMocks()`, and global unstubbing as appropriate.

## Shared Test Infrastructure

**Backend:**
- `backend/tests/conftest.py` inserts both the repository root and `backend/` into `sys.path` and sets Neo4j defaults only when the environment does not already override them.
- Those defaults target `bolt://127.0.0.1:7687`, user `neo4j`, database `neo4j`; this is the same default local database used by the application, not an automatically isolated test database.

**Frontend:**
- `frontend/src/test/setup.ts` loads Vitest-aware jest-dom types/matchers.
- It installs a React 19 `React.act` compatibility fallback and jsdom shims for pointer capture, `scrollIntoView`, `ResizeObserver`, and `matchMedia`, needed by Radix/shadcn and graph components.
- Add suite-wide browser API shims to `frontend/src/test/setup.ts`, not to every component test. Keep `NODE_ENV=test`; the `React.act` fallback is not a substitute for a correct environment.

## Mocking

**Backend framework and patterns:**
- Use small hand-written fakes and in-memory repositories rather than broad patching. Examples include `FakeUserRepo` and `InMemorySessionRepository` in `backend/tests/test_settings_api.py`, and provider/repository fakes in chat and retrieval suites.
- Override FastAPI dependencies through `app.dependency_overrides` when isolating routers, as in `backend/tests/test_settings_api.py`.
- Stub HTTP transports/providers and record calls when testing LLM/SSE behavior; assert exact context and terminal event behavior in `backend/tests/test_chat_api.py`, `backend/tests/test_llm_provider.py`, and `backend/tests/test_retrieval_pipeline.py`.
- Database stubs must return the exact row shape production code consumes; live repository tests are required when relationship direction or Cypher semantics are the behavior under test (`backend/tests/test_session_repository.py`).

**Frontend framework and patterns:**
- Use `vi.mock` for API modules, `vi.mocked(...)` for typed controls, `vi.fn()` for callbacks/fetch, and `vi.stubGlobal` for browser globals.
- Mock transport at the narrowest useful boundary. `frontend/src/api/chat.test.ts` replaces `globalThis.fetch` to assert URL, method, credentials, body, SSE chunking, malformed frames, errors, EOF, and cancellation.
- Mock API modules for component behavior, as in `frontend/src/components/settings/SettingsPage.test.tsx`; do not assert only that a mocked client received a payload when the backend contract itself is the risk.
- Stub `react-cytoscapejs` under jsdom for graph interaction tests. Preserve the real test stub's event-handler registry when writing probes; a no-op `cy.on` produces false conclusions in `frontend/src/App.test.tsx` and `frontend/src/components/graph/GraphCanvas.test.tsx` scenarios.

**What not to mock:**
- Do not mock OpenAPI generation or contract documentation parsing; `backend/tests/test_openapi_contract.py` and `backend/tests/test_frontend_contract_doc.py` intentionally lock the real API inventory.
- Do not replace Neo4j with a fake when verifying Cypher relationship direction, transaction behavior, spoiler filtering, or persistence round trips; use scoped live-DB integration tests.
- Do not use render-body counters as mount counters in graph tests; re-renders increment them. Assert persistent DOM/loading behavior and spy on the actual layout operation instead.

## Fixtures and Factories

**Backend test data:**
- Keep file-owned fixtures near the tests they serve. `backend/tests/test_settings_api.py` defines the live database fixture, app/client builders, authentication helper, and user/session fakes locally.
- Generate collision-resistant scratch identifiers with `uuid4()` and scope cleanup to those identifiers, as in `backend/tests/test_session_repository.py`.
- Use repository-root fixture files only from root-invoked pytest; extraction and contract suites refer to `data/` and `docs/` paths.

**Frontend test data:**
- Reuse `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts` for large shared shapes.
- Define small, behavior-specific factories beside tests (`progressRecord` in `frontend/src/hooks/useWatchProgress.test.ts`, `mockFetchJson`/`mockStreamResponse` in `frontend/src/api/chat.test.ts`).
- Keep fixture counts synchronized with exact graph assertions; changes to a shared graph fixture can legitimately require count updates in graph/App tests.

## Live Neo4j Safety

- Treat backend integration tests as destructive-capable operations against a shared live Neo4j database. Never point them at irreplaceable data, and do not interrupt mutation-heavy runs during fixture teardown.
- Global persistent data such as `:AppSetting {key: 'llm'}` must be backed up before a test and restored afterward. `backend/tests/test_settings_api.py` reads the prior value, permits deterministic mutation, then `MERGE`s the original value back; it deletes only when no node existed before the test.
- Session/auth integration records must use unique scratch owners/IDs and narrowly delete only the test-owned `:AppUser`/`:Session` subgraph, as in `backend/tests/test_session_repository.py`. Never use an unconditional global `MATCH (s:Session) DETACH DELETE s` cleanup.
- Scratch graph integration fixtures must use dedicated series/entity IDs and delete only those records; `backend/tests/test_retrieval_tools.py` demonstrates series-scoped setup/teardown.
- Context-manage synchronous `TestClient` when requests use the async Neo4j driver. The `with TestClient(...)` pattern in `backend/tests/test_settings_api.py` keeps requests on one portal event loop and avoids pooled-driver cross-loop crashes.
- Sync fixture backup/teardown must create a fresh `Neo4jDatabase`/driver inside the coroutine passed to `asyncio.run`; do not reuse the app/TestClient driver on the teardown loop. Async tests can share their async fixture's loop and driver.
- Let generator fixtures reach teardown. After an interrupted live-DB run, re-establish a known seeded state before trusting broad-suite results.

## Coverage

**Requirements:** None enforced.
- Backend `pyproject.toml` has no pytest-cov dependency, coverage options, or fail-under threshold.
- Frontend `frontend/vite.config.ts` has no Vitest coverage block, and `frontend/package.json` has no coverage provider or coverage script.
- There is currently no supported repository coverage command; do not invent a threshold or claim coverage percentage from test counts.

## Test Types

**Unit tests:**
- Domain/model validation, pure helpers, error shaping, API client parsing, graph style/element conversion, and hook state behavior are covered in files such as `backend/tests/test_user_content_models.py`, `backend/tests/test_openapi_contract.py`, `frontend/src/api/chat.test.ts`, and `frontend/src/hooks/useWatchProgress.test.ts`.

**Integration tests:**
- FastAPI router/service flows, live Neo4j repositories, graph retrieval, progress/settings persistence, and change-set/chat flows live throughout `backend/tests/`.
- `frontend/src/App.test.tsx` provides broad component integration with mocked network/graph-renderer boundaries.

**Contract tests:**
- `backend/tests/test_openapi_contract.py` locks exact OpenAPI paths, operations, response models, boundaries, and sanitized errors.
- `backend/tests/test_frontend_contract_doc.py` locks `docs/frontend-api-contract.md` against the route inventory. API changes must update runtime routes, OpenAPI expectations, documentation expectations, and the contract document together.

**E2E tests:**
- No browser E2E framework such as Playwright or Cypress is configured. Frontend integration runs under jsdom; backend live-DB tests are not full browser-to-database E2E tests.

## Common Patterns

**Async backend testing:**
```python
@pytest.mark.asyncio
async def test_repository_roundtrip(database: Neo4jDatabase) -> None:
    repo = Neo4jSessionRepository(database)
    token = await repo.create(test_user_id, ttl_seconds=3600)
    record = await repo.get(token)
    assert record is not None
```
- Keep operations that share a driver on one event loop; use a fresh driver for a separate `asyncio.run` cleanup loop.

**Frontend async testing:**
```typescript
const user = userEvent.setup()
render(<SettingsPage onBack={vi.fn()} />)
await user.click(await screen.findByRole('button', { name: 'Save settings' }))
expect(updateLLMSettings).toHaveBeenCalled()
```
- Prefer observable user behavior and accessible queries. Use `renderHook`, `act`, and `waitFor` for hook transitions in `frontend/src/hooks/useWatchProgress.test.ts`.

**Error testing:**
```python
response = client.post("/items", json={"count": 0, "unexpected": secret})
assert response.status_code == 422
assert response.json() == {
    "detail": {"code": "invalid_request", "message": "Request validation failed."}
}
assert secret not in response.text
```
- Assert status, stable machine code, sanitized message, and non-disclosure, as in `backend/tests/test_openapi_contract.py`.
- Frontend API tests should assert that non-2xx responses become `ApiError` with backend code/message intact and that malformed/early-ended SSE never leaves streaming state stuck (`frontend/src/api/chat.test.ts`).

## Build, Lint, and CI Gates

- `frontend/package.json` defines `npm run build` as `tsc -b && vite build`; there is no separate Python build command.
- `npm run lint` is configured but the live 2026-08-02 run is not clean: 28 errors, 0 warnings. Treat this as a pre-existing baseline and require no new lint findings.
- No `.github/workflows/` files are tracked, and no other committed CI workflow was detected. Pytest, Vitest, lint, and build are local responsibilities rather than automated PR gates.
- Before submitting changes, run the relevant backend tests, `NODE_ENV=test CI=1 npm run test`, `npm run build`, and compare `npm run lint` against the existing baseline.

---

*Testing analysis: 2026-08-02*
