---
last_mapped: 2026-08-14
focus: quality
last_mapped_commit: 5bd1641d7a9c44d693669d356ea602a23aa3664f
---
# Testing Patterns

**Analysis Date:** 2026-08-14

## Test Framework

**Backend runner:**
- Pytest `>=9.1.1` with pytest-asyncio `>=1.4.0`, HTTPX, and FastAPI `TestClient`, declared in `pyproject.toml`.
- Root config in `pyproject.toml` sets `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope = "module"`, and `testpaths = ["spoilerless/tests"]`; Python `>=3.13` is required.
- The tracked backend suite has 51 `test_*.py` files (~21.9k lines) plus `spoilerless/tests/conftest.py` and `spoilerless/tests/fixtures/`. There are no configured unit/integration markers.

**Frontend runner:**
- Vitest `^4.1.10`, Testing Library, jest-dom, user-event, and jsdom are declared in `frontend/package.json`.
- `frontend/vite.config.ts` sets `environment: 'jsdom'`, enables Vitest globals, and loads `frontend/src/test/setup.ts`.
- The live reliable run on 2026-08-14 passed 44 test files and 404 tests in ~29s. It also emits existing React `act(...)` warnings from several suites; passing status does not make those warnings a preferred pattern.

**Assertion libraries:**
- Backend uses plain pytest `assert`, `pytest.raises`, and parametrization in `spoilerless/tests/`.
- Frontend uses Vitest `expect` plus `@testing-library/jest-dom/vitest` matchers registered by `frontend/src/test/setup.ts`.

**Run commands:**
```bash
uv run pytest                                           # configured backend suite; run from repository root
uv run pytest spoilerless/tests/test_openapi_contract.py    # one backend file
uv run pytest spoilerless/tests/test_graph_api.py -k "graph_error_shapes"

uv run python scripts/run_phase10_backend_tests.py      # CANONICAL full backend suite: ephemeral Neo4j container
uv run python scripts/run_phase10_backend_tests.py --files \
    spoilerless/tests/test_graph_api.py spoilerless/tests/test_seed_idempotency.py
uv run python scripts/run_phase10_backend_tests.py --files ... -- -k "not slow"
uv run python scripts/run_backend_tests.py --list       # suite split into 11 named chunks
uv run python scripts/run_backend_tests.py --chunk graph # one chunk; serial total ~40m against live AuraDB
source scripts/env-local.sh                             # point backend tests at the local docker Neo4j

cd frontend
NODE_ENV=test CI=1 npm run test                         # reliable one-shot frontend suite
NODE_ENV=test npm run test                              # watch mode
NODE_ENV=test CI=1 npm run test -- src/App.test.tsx     # one frontend file
```
- Run backend tests from the repository root because some tests open root-relative artifacts under `data/` and `docs/`.
- Set `NODE_ENV=test` explicitly. An inherited `NODE_ENV=production` loads React production behavior and causes misleading `act`/empty-render failures despite Vitest mode being test.
- `scripts/run_phase10_backend_tests.py` is the canonical full-suite runner (NINETEENTH PASS, 2026-08-13, "retires the seven-red baseline"). It provisions a uniquely named `neo4j:2026.06.0-community` container (same image as docker-compose and CI) with a random password, random loopback ports, and no volume mounts; refuses fail-closed before creating anything (ambient `NEO4J_*`/`aura_*` overrides, remote/Aura hosts, developer-container port `7687`, running `spoilerless-neo4j`/`hdgraf-neo4j`, pre-existing container/volume with its name); proves the effective `Settings` (both alias families) resolve to the ephemeral target and that the database holds 0 nodes; seeds via `python -m spoilerless.app.graph.setup`; exports both alias families to children while stripping `PYTHONPATH`; and always tears down (`docker rm -f -v`) in a `finally`, verifying absence afterwards. Exit codes: 0 all green, 1 test failures, 2 forbidden-target/usage error. Its own fail-closed behavior is locked by `spoilerless/tests/test_phase10_test_runner.py` (18 mock-driven guard tests, no docker daemon).
- `scripts/run_backend_tests.py` splits the suite into 11 named chunks (see the chunk table in `docs/ops/runbook.md`; chunk 11 `phase10-viz` holds the five visualization/phase10 offline files). `assert_chunk_inventory_matches_disk()` asserts every `test_*.py` on disk is listed exactly once at startup. Parallel mode is SLOWER than serial against the shared AuraDB (connection contention) and is only useful against isolated Neo4j instances; the runner strips `PYTHONPATH` from child environments because the ambient shell can shadow the venv and break `import spoilerless`.

## Test File Organization

**Backend location and naming:**
- Keep tests in `spoilerless/tests/`, named `test_*.py`, with functions/methods named `test_*`.
- `spoilerless/tests/conftest.py` configures import paths and Neo4j defaults, and hosts the shared `NoopGoogleVerifier`, an autouse rate-limiter-disable fixture, an autouse CSRF-default fixture, the `live_client`/`seed_live_database` pair, `cleanup_with_fresh_driver`/`module_cleanup_fixture` teardown factories, and `run_query`/`run_async` probe helpers. File-owned fakes and behavior fixtures still live in the owning test module.
- Checked-in offline fixtures live in `spoilerless/tests/fixtures/visualization/` (`s01e01_safe.json`, `s01e02_cumulative_safe.json`) — safe baselines containing only rows visible at their effective boundary; used by the offline visualization suites.
- Large integration-heavy suites include `spoilerless/tests/test_visualization_projection.py` (1,711 lines), `spoilerless/tests/test_chat_api.py` (1,300 lines), `spoilerless/tests/test_retrieval_tools.py` (1,280 lines), and `spoilerless/tests/test_graph_api.py` (1,268 lines, now including the `test_visualization_route_*` family).
- New domain families: `test_visualization_{baseline,projection,cache,graphrag}.py` (offline Phase 10 contract/baseline suites) and `test_phase10_{coverage_audit,test_runner}.py` (script-guard tests that load `scripts/` modules without executing them).

**Frontend location and naming:**
- Colocate tests with source as `*.test.ts` or `*.test.tsx`, for example `frontend/src/api/chat.test.ts` and `frontend/src/components/settings/SettingsPage.test.tsx`.
- Keep shared payloads in `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts`; keep suite-wide DOM shims in `frontend/src/test/setup.ts`.
- The largest frontend tests are `frontend/src/components/graph/GraphCanvas.test.tsx` (748 lines) and `frontend/src/App.test.tsx` (636+ lines, grown with Phase 10 projection/expansion wiring and visitor-flow coverage); the latter exercises cross-component behavior with a substantial Cytoscape stub.
- New pure-logic suites are small and behavior-focused: `frontend/src/lib/visualizationAdapter.test.ts` (exact data-key pinning), `frontend/src/hooks/useSceneState.test.ts` (JSON round-trip reducer), and `frontend/src/components/graph/cytoscapeReconciler.test.ts` (headless real cytoscape).

**Structure:**
```text
spoilerless/tests/
├── conftest.py
├── fixtures/visualization/   # checked-in safe JSON baselines
├── test_<api-or-domain>.py
├── test_visualization_*.py   # offline Phase 10 contract/baseline family
└── test_phase10_*.py         # script-guard tests for scripts/ runners

frontend/src/
├── App.test.tsx
├── api/*.test.ts
├── hooks/*.test.ts(x)
├── lib/*.test.ts
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
- Use Arrange/Act/Assert flow with direct status/body assertions, as in `spoilerless/tests/test_settings_api.py`.
- Build minimal FastAPI applications and override dependencies when a router is the unit under test (`spoilerless/tests/test_settings_api.py`, `spoilerless/tests/test_visualization_projection.py` builds small apps such as `_expansion_app()` and wraps them in `TestClient` for route-level projection tests).
- Use exact-set and shape assertions for closed contracts rather than partial presence checks (`spoilerless/tests/test_openapi_contract.py`).
- Use `pytest.mark.parametrize` for boundary/security matrices, such as rejected base URL schemes in `spoilerless/tests/test_settings_api.py`, view-type matrices (`test_visualization_route_all_views_return_valid_dtos` in `spoilerless/tests/test_graph_api.py`), and hidden-channel boundary influence (`test_hidden_channel_data_cannot_influence_effective_boundary` in `spoilerless/tests/test_spoiler_policy.py`).
- Async tests may use `pytest.mark.asyncio`; `asyncio_mode = "auto"` also supports async fixtures and keeps async test/fixture work on the pytest loop.
- Offline visualization suites instantiate the production service once at module scope (`service = VisualizationProjectionService()`) and reuse it across tests; no live Neo4j, LLM, or retrieval calls exist anywhere in the runnable path.
- Script-guard tests load the script under test with `importlib.util.spec_from_file_location` and call its pure functions directly; no subprocess, no docker daemon, no live files (`spoilerless/tests/test_phase10_coverage_audit.py`, `spoilerless/tests/test_phase10_test_runner.py`).

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
- Scope queries when a surface gains new tabs: `App.test.tsx` wraps inspector assertions in `within(screen.getByRole('dialog'))` because the new top-level "Evidence" tab makes unscoped role queries ambiguous.
- Route the fetch stub by URL prefix with ordering comments: in `frontend/src/App.test.tsx` the `/graph/visualization` and `/graph/expand` branches are checked BEFORE the generic `/graph` branch, and `graphFetchCalls()` explicitly excludes the projection/expansion URLs so legacy count assertions stay accurate.

## Shared Test Infrastructure

**Backend:**
- `spoilerless/tests/conftest.py` inserts both the repository root and `spoilerless/` into `sys.path` and sets Neo4j defaults only when the environment does not already override them.
- Those defaults target `bolt://127.0.0.1:7687`, user `neo4j`, database `neo4j`; this is the same default local database used by the application, not an automatically isolated test database. `source scripts/env-local.sh` switches local runs to the docker Neo4j (`neo4j://localhost:7687`, `hdgraf-local-password`).
- The autouse `_disable_rate_limiter` fixture neutralizes the Redis-backed `RateLimiter` dependency for every test (no test starts a live Redis); the limiter's pure functions are unit-tested separately in `spoilerless/tests/test_rate_limit.py`.
- The autouse `_csrf_bypass_default` fixture defaults `FRONTEND_ORIGINS` to `"*"` (with `get_settings.cache_clear()`) so API tests without an Origin header pass the CSRF `verify_origin` guard; it is skipped for the `test_config` module whose production-safe-defaults assertions must see the pristine default. CSRF-specific tests override the variable themselves (monkeypatch restores it), and `test_auth.py` inventories every cookie-authenticated state-changing route for the guard (`test_every_cookie_authenticated_state_changing_route_has_csrf_guard`).

**Frontend:**
- `frontend/src/test/setup.ts` loads Vitest-aware jest-dom types/matchers.
- It installs a React 19 `React.act` compatibility fallback and jsdom shims for pointer capture, `scrollIntoView`, `ResizeObserver`, and `matchMedia`, needed by Radix/shadcn and graph components.
- Add suite-wide browser API shims to `frontend/src/test/setup.ts`, not to every component test. Keep `NODE_ENV=test`; the `React.act` fallback is not a substitute for a correct environment.

## Mocking

**Backend framework and patterns:**
- Use small hand-written fakes and in-memory repositories rather than broad patching. Examples include `FakeUserRepo` and `InMemorySessionRepository` in `spoilerless/tests/test_settings_api.py`, and provider/repository fakes in chat and retrieval suites.
- Override FastAPI dependencies through `app.dependency_overrides` when isolating routers, as in `spoilerless/tests/test_settings_api.py`.
- Stub HTTP transports/providers and record calls when testing LLM/SSE behavior; assert exact context and terminal event behavior in `spoilerless/tests/test_chat_api.py`, `spoilerless/tests/test_llm_provider.py`, and `spoilerless/tests/test_retrieval_pipeline.py`.
- Database stubs must return the exact row shape production code consumes; live repository tests are required when relationship direction or Cypher semantics are the behavior under test (`spoilerless/tests/test_session_repository.py`).
- Share fakes across modules in `spoilerless/tests/conftest.py`: `NoopGoogleVerifier` satisfies `AuthService`'s required verifier without touching Google (PROB-09/#77). When a required dependency is injected (no silent fallbacks), add one shared stub in conftest rather than per-file copies.
- Test fakes are also shared by importing across test modules: `spoilerless/tests/test_visualization_graphrag.py` reuses `_CallScriptedProvider`, `_StubDatabase`, and `_StubProgressService` from `spoilerless/tests/test_retrieval_pipeline.py` and `_load_fixture` from `spoilerless/tests/test_visualization_projection.py` instead of redefining them.
- Redis is faked with a small in-memory stand-in implementing the exact surface `graph_cache` uses (`get`/`setex`/`scan_iter`/`delete`/`incr`, byte values like the real client): `_FakeRedis` in `spoilerless/tests/test_visualization_cache.py`, enabled by monkeypatching `get_settings().redis_url` and `graph_cache.get_redis`. This is the documented 08-06 pattern from `spoilerless/tests/test_graph_api.py`.
- Script-guard tests monkeypatch the script's I/O seam: `FakeDocker` in `spoilerless/tests/test_phase10_test_runner.py` records calls and scripts responses by substring match, then `monkeypatch.setattr(runner, "_docker", fake)` drives provisioning/teardown paths without a daemon; teardown-always-runs behavior is asserted on both test-failure and provisioning-exception paths.

**Frontend framework and patterns:**
- Use `vi.mock` for API modules, `vi.mocked(...)` for typed controls, `vi.fn()` for callbacks/fetch, and `vi.stubGlobal` for browser globals.
- Mock transport at the narrowest useful boundary. `frontend/src/api/chat.test.ts` replaces `globalThis.fetch` to assert URL, method, credentials, body, SSE chunking, malformed frames, errors, EOF, and cancellation.
- Mock API modules for component behavior, as in `frontend/src/components/settings/SettingsPage.test.tsx`; do not assert only that a mocked client received a payload when the backend contract itself is the risk.
- Stub `react-cytoscapejs` under jsdom for graph interaction tests. Preserve the real test stub's event-handler registry when writing probes; a no-op `cy.on` produces false conclusions in `frontend/src/App.test.tsx` and `frontend/src/components/graph/GraphCanvas.test.tsx` scenarios.
- NEW — for reconciler logic, use the REAL cytoscape headless instead of the stub: `cytoscape({ headless: true, styleEnabled: false, elements })` in `frontend/src/components/graph/cytoscapeReconciler.test.ts` exercises actual compound-removal and edge-rewiring semantics. Assert identity preservation (same element instance, parent, position, classes, selection, zoom, pan) and `cy.destroy()` at the end of each test.

**What not to mock:**
- Do not mock OpenAPI generation or contract documentation parsing; `spoilerless/tests/test_openapi_contract.py` and `spoilerless/tests/test_frontend_contract_doc.py` intentionally lock the real API inventory.
- Do not replace Neo4j with a fake when verifying Cypher relationship direction, transaction behavior, spoiler filtering, or persistence round trips; use scoped live-DB integration tests.
- Do not use render-body counters as mount counters in graph tests; re-renders increment them. Assert persistent DOM/loading behavior and spy on the actual layout operation instead.
- Do not stub cytoscape when compound-parent removal, edge rewiring, or element identity is the behavior under test; use a headless real instance as in `frontend/src/components/graph/cytoscapeReconciler.test.ts`.
- Do not start docker or a live database to test the guarded runner itself; `spoilerless/tests/test_phase10_test_runner.py` and `spoilerless/tests/test_phase10_coverage_audit.py` are mock-driven by contract.

## Fixtures and Factories

**Backend test data:**
- Keep file-owned fixtures near the tests they serve. `spoilerless/tests/test_settings_api.py` defines the live database fixture, app/client builders, authentication helper, and user/session fakes locally.
- Generate collision-resistant scratch identifiers with `uuid4()` and scope cleanup to those identifiers, as in `spoilerless/tests/test_session_repository.py`.
- Use repository-root fixture files only from root-invoked pytest; extraction and contract suites refer to `data/` and `docs/` paths.
- Checked-in safe baselines live in `spoilerless/tests/fixtures/visualization/`: `s01e01_safe.json` and `s01e02_cumulative_safe.json` contain only rows visible at their effective boundary plus explicit episode/projection-version metadata. Load them through `_load_fixture(name)` (`spoilerless/tests/test_visualization_projection.py`) or `load_fixture(name)` (`spoilerless/tests/test_visualization_baseline.py`) and validate through real `GraphResponse.model_validate` — never through a mock seam.
- Keep the baseline tracer's numeric targets as module constants that serve as the single source of truth: `TARGET_MIN_NODES`, `TARGET_MAX_NODES`, `HARD_MAX_NODES`, `PREFERRED_MAX_EDGES`, `HARD_MAX_EDGES` in `spoilerless/tests/test_visualization_baseline.py`.

**Frontend test data:**
- Reuse `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts` for large shared shapes.
- Define small, behavior-specific factories beside tests (`progressRecord` in `frontend/src/hooks/useWatchProgress.test.ts`, `mockFetchJson`/`mockStreamResponse` in `frontend/src/api/chat.test.ts`, `makeDto(overrides)` in `frontend/src/lib/visualizationAdapter.test.ts`).
- Keep fixture counts synchronized with exact graph assertions; changes to a shared graph fixture can legitimately require count updates in graph/App tests.
- Type Phase 10 fixture objects against the real `VisualizationDTO` type and mirror the backend shape: `vizFixture`/`expansionFixture` in `frontend/src/App.test.tsx` are typed `VisualizationDTO` (from `frontend/src/types/graph.ts`) and mirror `spoilerless/app/domain/visualization.py` (D-08/D-29), with a comment noting the mirrored contract.

## Live Neo4j Safety

- Treat backend integration tests as destructive-capable operations against a shared live Neo4j database. Never point them at irreplaceable data, and do not interrupt mutation-heavy runs during fixture teardown.
- Global persistent data such as `:AppSetting {key: 'llm'}` must be backed up before a test and restored afterward. `spoilerless/tests/test_settings_api.py` reads the prior value, permits deterministic mutation, then `MERGE`s the original value back; it deletes only when no node existed before the test.
- Session/auth integration records must use unique scratch owners/IDs and narrowly delete only the test-owned `:AppUser`/`:Session` subgraph, as in `spoilerless/tests/test_session_repository.py`. Never use an unconditional global `MATCH (s:Session) DETACH DELETE s` cleanup.
- Scratch graph integration fixtures must use dedicated series/entity IDs and delete only those records; `spoilerless/tests/test_retrieval_tools.py` demonstrates series-scoped setup/teardown.
- Context-manage synchronous `TestClient` when requests use the async Neo4j driver. The `with TestClient(...)` pattern in `spoilerless/tests/test_settings_api.py` keeps requests on one portal event loop and avoids pooled-driver cross-loop crashes.
- Sync fixture backup/teardown must create a fresh `Neo4jDatabase`/driver inside the coroutine passed to `asyncio.run`; do not reuse the app/TestClient driver on the teardown loop. Async tests can share their async fixture's loop and driver.
- Let generator fixtures reach teardown. After an interrupted live-DB run, re-establish a known seeded state before trusting broad-suite results.
- The 584-pass/7-failed local-docker baseline is RETIRED (NINETEENTH PASS, 2026-08-13): all seven reds were root-caused and fixed (3 doc-contract via the 10-03/10-06 OpenAPI inventory updates, 2 seed-image via the 08-12 self-hosted portrait restore, 2 constraint-name engine-tolerant on `neo4j:2026.06.0-community`), with no assertion weakened. The canonical full-suite command is now `uv run python scripts/run_phase10_backend_tests.py`, which refuses to run while the local docker Neo4j (`spoilerless-neo4j`/`hdgraf-neo4j`) is live and always destroys its ephemeral container. The offline visualization suites never touch a database at all — checked-in safe fixtures only.
- The runner seeds its ephemeral target through the real `python -m spoilerless.app.graph.setup` module, so CI-equivalent seed idempotency is exercised on every full run.

## Coverage

**Requirements:** None enforced.
- Backend `pyproject.toml` has no pytest-cov dependency, coverage options, or fail-under threshold.
- Frontend `frontend/vite.config.ts` has no Vitest coverage block, and `frontend/package.json` has no coverage provider or coverage script.
- There is currently no supported repository coverage command; do not invent a threshold or claim coverage percentage from test counts.
- Coverage is instead enforced structurally: the Phase 10 closeout machine-readable table in `scripts/verify_phase10_coverage.py` (literal `PHASE10-COVERAGE` markers, exact header, 98 exact source ids) maps every requirement id to an artifact-or-test with evidence refs, and its fail-closed parsing contract is locked by `spoilerless/tests/test_phase10_coverage_audit.py` (duplicate/missing/extra/malformed rows, empty fields, and self-referencing evidence all rejected).

## Test Types

**Unit tests:**
- Domain/model validation, pure helpers, error shaping, API client parsing, graph style/element conversion, and hook state behavior are covered in files such as `spoilerless/tests/test_user_content_models.py`, `spoilerless/tests/test_openapi_contract.py`, `frontend/src/api/chat.test.ts`, and `frontend/src/hooks/useWatchProgress.test.ts`.
- The PROB-09 wave added focused unit suites: `spoilerless/tests/test_error_handlers.py`, `spoilerless/tests/test_google_verifier.py`, `spoilerless/tests/test_main_lifespan.py`, `spoilerless/tests/test_rate_limit.py`, `spoilerless/tests/test_ontology.py`, `spoilerless/tests/test_series_service.py`, `spoilerless/tests/test_setup_schema_check.py`, `spoilerless/tests/test_share_api.py`, `spoilerless/tests/test_spoiler_policy.py`, and `spoilerless/tests/test_s01e01_enrichment.py`.
- The Phase 10 wave added offline visualization unit/contract suites (no live Neo4j, no LLM, no retrieval): `spoilerless/tests/test_visualization_projection.py` (exact DTO shape, stable IDs, 0/1/many payloads, schema validation and reference closure, omission of `PARTICIPATED_IN`/`OCCURRED_IN` and the participation family, human edge classes only, GraphRAG-independent source detail), `spoilerless/tests/test_visualization_baseline.py` (checked-in fixtures → real `GraphResponse` validation → boundary assertion → baseline metrics → Variant A/B projections → `build_evidence()`), `spoilerless/tests/test_visualization_cache.py` (key dimensions, miss/hit round-trip, stale-metadata rejection, poisoning resistance, no-op when Redis disabled, Redis error degradation), and `spoilerless/tests/test_visualization_graphrag.py` (pure `build_graphrag_focus` classifier, micro-Event focus substitution, `FakeLLM` end-to-end proving visual bounds never reduce retrieval).
- Script-guard unit suites: `spoilerless/tests/test_phase10_coverage_audit.py` and `spoilerless/tests/test_phase10_test_runner.py` load `scripts/verify_phase10_coverage.py` and `scripts/run_phase10_backend_tests.py` in-process and lock their fail-closed contracts, CLI exit codes, chunk inventory (`test_chunk_inventory_covers_every_test_file_exactly_once`), and teardown guarantees.
- Frontend pure-logic suites: `frontend/src/lib/visualizationAdapter.test.ts` (exact-shape pinning of `NODE_DATA_KEYS`/`EDGE_DATA_KEYS`/`GROUP_DATA_KEYS`, D-05 no-filtering, D-14 debug labels), `frontend/src/hooks/useSceneState.test.ts` (JSON round-trip serializability, expansion undo, focus charset safety), and `frontend/src/components/graph/cytoscapeReconciler.test.ts` (headless real cytoscape identity/reparent/rewire/viewport preservation).

**Integration tests:**
- FastAPI router/service flows, live Neo4j repositories, graph retrieval, progress/settings persistence, and change-set/chat flows live throughout `spoilerless/tests/`.
- `spoilerless/tests/test_graph_api.py` gained the `test_visualization_route_*` family: validated DTOs end to end, all views return valid DTOs (parametrized), 404/422 shapes, anonymous clamping to order one, authenticated clamping by progress, focus-id rejection for non-focus views, GraphRAG focus 422s and caps, cache-hit byte-for-byte equality with a miss, Redis-failure still serving, and preservation of legacy `/graph` route behavior.
- `frontend/src/App.test.tsx` provides broad component integration with mocked network/graph-renderer boundaries, now including visitor detail-inspector read-only assertions and the above-boundary spoiler-warning modal regression test.

**Contract tests:**
- `spoilerless/tests/test_openapi_contract.py` locks exact OpenAPI paths, operations, response models, boundaries, and sanitized errors.
- `spoilerless/tests/test_frontend_contract_doc.py` locks `docs/reference/frontend-api-contract.md` against the route inventory. API changes must update runtime routes, OpenAPI expectations, documentation expectations, and the contract document together.
- `spoilerless/tests/test_visualization_projection.py` locks the neutral `VisualizationDTO` contract (D-08/D-10 Variant A): exact shape, stable IDs, deterministic output, forbidden-key vocabulary, raw-relation-name exclusion, and the projection-version metadata contract.
- `spoilerless/tests/test_phase10_coverage_audit.py` locks the `PHASE10-COVERAGE` machine-readable table contract (literal markers, exact header, exact 98-id inventory).
- `frontend/src/lib/visualizationAdapter.test.ts` pins the emitted data-key set per element kind so a hidden field cannot silently flow into Cytoscape data.

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

**Offline fixture pipeline (visualization baselines):**
```python
# spoilerless/tests/test_visualization_baseline.py
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visualization"
FIXTURE_FILES = ("s01e01_safe.json", "s01e02_cumulative_safe.json")

def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)
```
- Pipeline: checked-in JSON fixture → `GraphResponse.model_validate` (real validation + closure) → effective-boundary assertion via `spoilerless.app.spoiler.policy` → baseline metrics → projections → `build_evidence()`. No mock seam anywhere in the runnable path.

**Script-guard testing (no daemon, no live files):**
```python
# spoilerless/tests/test_phase10_test_runner.py
runner = _load_module("run_phase10_backend_tests", SCRIPTS_DIR / "run_phase10_backend_tests.py")

def test_teardown_runs_when_tests_fail_and_verifies_absence(monkeypatch) -> None:
    fake = FakeDocker([("docker run", target.name, 0), ("docker rm", target.name, 0), ...])
    monkeypatch.setattr(runner, "_docker", fake)
    monkeypatch.setattr(runner, "_run_tests", lambda args, env: 1)  # tests FAIL
    assert runner.run(_args()) == 1
    assert any(c[:2] == ["docker", "rm"] for c in fake.calls), "teardown must run docker rm"
```

**Frontend async testing:**
```typescript
const user = userEvent.setup()
render(<SettingsPage onBack={vi.fn()} />)
await user.click(await screen.findByRole('button', { name: 'Save settings' }))
expect(updateLLMSettings).toHaveBeenCalled()
```
- Prefer observable user behavior and accessible queries. Use `renderHook`, `act`, and `waitFor` for hook transitions in `frontend/src/hooks/useWatchProgress.test.ts`.

**Headless cytoscape testing (reconciler):**
```typescript
// frontend/src/components/graph/cytoscapeReconciler.test.ts
const cy = cytoscape({ headless: true, styleEnabled: false, elements: legacyOverview })
reconcileCytoscapeElements(cy, characterNetwork)
expect(cy.getElementById(dexterId)[0]).toBe(identity)   // identity preserved
expect(cy.getElementById(dexterId).position()).toEqual({ x: 42, y: 84 })
expect(cy.zoom()).toBe(1.4)
cy.destroy()
```

**Error testing:**
```python
response = client.post("/items", json={"count": 0, "unexpected": secret})
assert response.status_code == 422
assert response.json() == {
    "detail": {"code": "invalid_request", "message": "Request validation failed."}
}
assert secret not in response.text
```
- Assert status, stable machine code, sanitized message, and non-disclosure, as in `spoilerless/tests/test_openapi_contract.py`.
- Frontend API tests should assert that non-2xx responses become `ApiError` with backend code/message intact and that malformed/early-ended SSE never leaves streaming state stuck (`frontend/src/api/chat.test.ts`).

## Build, Lint, and CI Gates

- `frontend/package.json` defines `npm run build` as `tsc -b && vite build`; there is no separate Python build command.
- `npm run lint` passes on the live 2026-08-14 run: 0 errors, 21 warnings (all `react-hooks/refs`). Keep the count from growing; treat warnings as the only allowed baseline.
- `.github/workflows/ci.yml` runs on every PR: backend pytest against a service-container Neo4j pinned to `neo4j:2026.06.0-community` (seed then suite, plus a DB-pollution gate asserting zero `series_scratch`/`origin='candidate'` residue), and a frontend job (Node 24, `npm ci`, build, lint, `npm audit`). `.github/workflows/release.yml` is a staged-promotion skeleton gated on the CI workflow.
- Before submitting changes, run the relevant backend tests, `NODE_ENV=test CI=1 npm run test`, `npm run build`, and `npm run lint`. For a full backend run use `uv run python scripts/run_phase10_backend_tests.py`; the old 584/7 local-docker baseline no longer applies (retired 2026-08-13).
- `scripts/verify_phase10_coverage.py` and the root claim-verification scripts (`run_verification.py`, `run_doc_verification.py`, `verify_all_claims.py`, `verify_arch.py`) are manual audit tooling, not CI gates; their results feed the `docs/PROBLEMS.md` PASS ledger.

---

*Testing analysis: 2026-08-14*
