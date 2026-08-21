---
last_mapped: 2026-08-20
focus: quality
last_mapped_commit: 5ad68675e20b4c9b69e9b88335286b5e2f6f04fa
---
<!-- refreshed: 2026-08-20 -->
# Testing Patterns

**Analysis Date:** 2026-08-20

## Test Framework

**Backend runner:**
- Pytest `>=9.1.1` with pytest-asyncio `>=1.4.0`, HTTPX, and FastAPI `TestClient`, declared in `pyproject.toml`.
- Root config in `pyproject.toml` sets `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope`/`asyncio_default_test_loop_scope = "module"`, and `testpaths = ["spoilerless/tests"]`; Python `>=3.13` is required.
- The tracked backend suite now has **52 `test_*.py` files (~22.1k lines)** plus `spoilerless/tests/conftest.py` and `spoilerless/tests/fixtures/`. Phase 11 adds `spoilerless/tests/test_security_boundary.py` (316 lines, scratch series `series_scratch_boundary`). There are no configured unit/integration markers.

**Frontend runner:**
- Vitest `^4.1.10`, Testing Library, jest-dom, user-event, and jsdom are declared in `frontend/package.json`.
- `frontend/vite.config.ts` sets `environment: 'jsdom'`, enables Vitest globals, and loads `frontend/src/test/setup.ts`.
- The live reliable run on 2026-08-14 passed 44 test files and 404 tests in ~29s. It also emits existing React `act(...)` warnings from several suites; passing status does not make those warnings a preferred pattern. Phase 11 does not change the frontend runner; run frontend suites the same way.

**Assertion libraries:**
- Backend uses plain pytest `assert`, `pytest.raises`, and parametrization in `spoilerless/tests/`.
- Frontend uses Vitest `expect` plus `@testing-library/jest-dom/vitest` matchers registered by `frontend/src/test/setup.ts`.

**Run commands:**
```bash
uv run pytest                                           # configured backend suite; run from repository root
uv run pytest spoilerless/tests/test_openapi_contract.py    # one backend file
uv run pytest spoilerless/tests/test_graph_api.py -k "graph_error_shapes"
uv run pytest spoilerless/tests/test_security_boundary.py -q  # Phase 11 fail-closed boundary matrix

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
- `scripts/run_phase10_backend_tests.py` is the canonical full-suite runner (NINETEENTH PASS, 2026-08-13, "retires the seven-red baseline"). It provisions a uniquely named `neo4j:2026.06.0-community` container (same image as docker-compose and CI) with a random password, random loopback ports, and no volume mounts; refuses fail-closed before creating anything (ambient `NEO4J_*`/`aura_*` overrides, remote/Aura hosts, developer-container port `7687`, running `spoilerless-neo4j`/`hdgraf-neo4j`, pre-existing container/volume with its name); proves the effective `Settings` (both alias families) resolve to the ephemeral target and that the database holds 0 nodes; seeds via `python -m spoilerless.app.graph.setup`; exports both alias families to children while stripping `PYTHONPATH`; and always tears down (`docker rm -f -v`) in a `finally`, verifying absence afterwards. Exit codes: 0 all green, 1 test failures, 2 forbidden-target/usage error. Its own fail-closed behavior is locked by `spoilerless/tests/test_phase10_test_runner.py` (18 mock-driven guard tests, no docker daemon). Guarded runner is unchanged in Phase 11 except it is now also the gate for `test_security_boundary.py` scratch-series isolation.
- `scripts/run_backend_tests.py` splits the suite into 11 named chunks (see the chunk table in `docs/ops/runbook.md`; chunk 11 `phase10-viz` holds the five visualization/phase10 offline files — Phase 11 adds the security boundary suite to the inventory and `assert_chunk_inventory_matches_disk()` asserts every `test_*.py` on disk is listed exactly once at startup). Parallel mode is SLOWER than serial against the shared AuraDB (connection contention) and is only useful against isolated Neo4j instances; the runner strips `PYTHONPATH` from child environments because the ambient shell can shadow the venv and break `import spoilerless`.

## Test File Organization

**Backend location and naming:**
- Keep tests in `spoilerless/tests/`, named `test_*.py`, with functions/methods named `test_*`.
- `spoilerless/tests/conftest.py` configures import paths and Neo4j defaults, and hosts the shared `NoopGoogleVerifier`, an autouse rate-limiter-disable fixture, an autouse CSRF-default fixture, the `live_client`/`seed_live_database` pair, `cleanup_with_fresh_driver`/`module_cleanup_fixture` teardown factories, `run_query`/`run_async` probe helpers, and the scratch-series factories `bootstrap_scratch_series(series_id, episodes)` / `teardown_scratch_series(series_id)` used by `spoilerless/tests/test_security_boundary.py` to avoid touching `series_dexter`.
- Checked-in offline fixtures live in `spoilerless/tests/fixtures/visualization/` (`s01e01_safe.json`, `s01e02_cumulative_safe.json`) — safe baselines containing only rows visible at their effective boundary; used by the offline visualization suites.
- Large integration-heavy suites include `spoilerless/tests/test_visualization_projection.py` (1,711 lines), `spoilerless/tests/test_graph_api.py` (1,268–1,268 lines baseline + `test_visualization_route_*` family), `spoilerless/tests/test_auth.py` (1,166 lines), `spoilerless/tests/test_retrieval_tools.py` (1,350 lines), and `spoilerless/tests/test_chat_api.py` (1,302 lines).
- New domain families: `test_visualization_{baseline,projection,cache,graphrag}.py` (offline Phase 10 contract/baseline suites), `test_phase10_{coverage_audit,test_runner}.py` (script-guard tests), and **Phase 11 `test_security_boundary.py`** (fail-closed boundary matrix for tracer slice 11-01) plus updated `test_candidate_ingest.py` (+86 lines) and `test_candidate_review.py` (+31 lines) now exercising the unified resolver + pagination + rate-limit seams.

**Frontend location and naming:**
- Colocate tests with source as `*.test.ts` or `*.test.tsx`, for example `frontend/src/api/chat.test.ts` and `frontend/src/components/settings/SettingsPage.test.tsx`.
- Keep shared payloads in `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts`; keep suite-wide DOM shims in `frontend/src/test/setup.ts`.
- The largest frontend tests are `frontend/src/components/graph/GraphCanvas.test.tsx` (748 lines) and `frontend/src/App.test.tsx` (636+ lines, grown with Phase 10 projection/expansion wiring and visitor-flow coverage); the reconciler work stays in `frontend/src/components/graph/cytoscapeReconciler.test.ts` (headless real cytoscape).
- New pure-logic suites are small and behavior-focused: `frontend/src/lib/visualizationAdapter.test.ts` (exact data-key pinning), `frontend/src/hooks/useSceneState.test.ts` (JSON round-trip reducer), and `frontend/src/components/graph/cytoscapeReconciler.test.ts` (headless real cytoscape). Phase 11 adds no new frontend test files beyond verifying `vercel.json` CSP and client header hardening in existing suites.

**Structure:**
```text
spoilerless/tests/
├── conftest.py                         # shared fixtures + scratch-series factories
├── fixtures/visualization/             # checked-in safe JSON baselines
├── test_<api-or-domain>.py             # route/service/repository suites
├── test_visualization_*.py             # offline Phase 10 contract/baseline family
├── test_phase10_*.py                   # script-guard tests for scripts/ runners
└── test_security_boundary.py           # Phase 11 D-01 fail-closed boundary matrix

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
- Use Arrange/Act/Assert flow with direct status/body assertions, as in `spoilerless/tests/test_settings_api.py` and the new `spoilerless/tests/test_security_boundary.py` (anonymous → 1, no-record → 1, authenticated clamp → min(requested, view, watched), invalid episode order → 422 `INVALID_VISIBLE_UNTIL_ORDER`).
- Build minimal FastAPI applications and override dependencies when a router is the unit under test (`spoilerless/tests/test_settings_api.py`, `spoilerless/tests/test_visualization_projection.py` builds small apps such as `_expansion_app()`). Phase 11 boundary tests bootstrap a **scratch series** (`SCRATCH = "series_scratch_boundary"`, episodes 1–3 via `bootstrap_scratch_series`) and seed candidate claims at orders 1/3 plus late/mid characters, never touching `series_dexter`; teardown is via `teardown_scratch_series(SCRATCH)`.
- Use exact-set and shape assertions for closed contracts rather than partial presence checks (`spoilerless/tests/test_openapi_contract.py`, `spoilerless/tests/test_security_boundary.py` asserts the exact sanitized envelope and `ERROR_CODES` membership for new 413).
- Use `pytest.mark.parametrize` for boundary/security matrices: rejected base URL schemes in `spoilerless/tests/test_settings_api.py`, view-type matrices (`test_visualization_route_all_views_return_valid_dtos`), hidden-channel boundary influence (`test_hidden_channel_data_cannot_influence_effective_boundary`), and now the anonymous/no-record/clamp matrix in `spoilerless/tests/test_security_boundary.py`.
- Async tests may use `pytest.mark.asyncio`; `asyncio_mode = "auto"` also supports async fixtures and keeps async test/fixture work on the pytest loop. The security boundary module uses `scope="module"` for the scratch series fixture and `asyncio.run` to seed/clean on a fresh driver (matching the existing `live_client` pattern).
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
- Route the fetch stub by URL prefix with ordering comments: in `frontend/src/App.test.tsx` the `/graph/visualization` and `/graph/expand` branches are checked BEFORE the generic `/graph` branch, and `graphFetchCalls()` explicitly excludes the projection/expansion URLs so legacy count assertions stay accurate. Phase 11 CSP/header work is verified by asserting real response headers (not only UI), mirroring the chat SSE contract pattern.

## Shared Test Infrastructure

**Backend:**
- `spoilerless/tests/conftest.py` inserts both the repository root and `spoilerless/` into `sys.path` and sets Neo4j defaults only when the environment does not already override them.
- Those defaults target `bolt://127.0.0.1:7687`, user `neo4j`, database `neo4j`; this is the same default local database used by the application, not an automatically isolated test database. `source scripts/env-local.sh` switches local runs to the docker Neo4j (`neo4j://localhost:7687`, `hdgraf-local-password`). The guarded runner proves the ephemeral target instead.
- The autouse `_disable_rate_limiter` fixture neutralizes the Redis-backed `RateLimiter` dependency for every test (no test starts a live Redis); the limiter's pure functions are unit-tested separately in `spoilerless/tests/test_rate_limit.py`. Phase 11 keeps this no-op but the limiter itself is now environment-aware (production + `rate_limit_fail_open=false` → 503 instead of no-op; each behavior has a test in `spoilerless/tests/test_rate_limit.py`).
- The autouse `_csrf_bypass_default` fixture defaults `FRONTEND_ORIGINS` to `"*"` (with `get_settings.cache_clear()`) so API tests without an Origin header pass the CSRF `verify_origin` guard; it is skipped for the `test_config` module whose production-safe-defaults assertions must see the pristine default.
- Scratch-series helpers (`bootstrap_scratch_series` / `teardown_scratch_series`) create a disposable `Series` + `Episode` subgraph (episodes are `visibility-ordered`, `Series.id` is the foreign key every read scopes to) and are now the sanctioned pattern for any test that must add rows without risking the audit that `setup_database()` runs over `series_dexter` (see `spoilerless/tests/test_candidate_ingest.py` Phase 11 migration from `SERIES_ID = "series_dexter"` to scratch, and `spoilerless/tests/test_security_boundary.py`'s `SCRATCH = "series_scratch_boundary"`).

**Frontend:**
- `frontend/src/test/setup.ts` loads Vitest-aware jest-dom types/matchers.
- It installs a React 19 `React.act` compatibility fallback and jsdom shims for pointer capture, `scrollIntoView`, `ResizeObserver`, and `matchMedia`, needed by Radix/shadcn and graph components.
- Add suite-wide browser API shims to `frontend/src/test/setup.ts`, not to every component test. Keep `NODE_ENV=test`; the `React.act` fallback is not a substitute for a correct environment. Phase 11 CSP work lives in `frontend/vercel.json`, not in setup.

## Mocking

**Backend framework and patterns:**
- Use small hand-written fakes and in-memory repositories rather than broad patching. Examples include `FakeUserRepo` and `InMemorySessionRepository` in `spoilerless/tests/test_settings_api.py`, and provider/repository fakes in chat and retrieval suites.
- Override FastAPI dependencies through `app.dependency_overrides` when isolating routers, as in `spoilerless/tests/test_settings_api.py`.
- Stub HTTP transports/providers and record calls when testing LLM/SSE behavior; assert exact context and terminal event behavior in `spoilerless/tests/test_chat_api.py`, `spoilerless/tests/test_llm_provider.py`, and `spoilerless/tests/test_retrieval_pipeline.py`. Phase 11 caps the retrieval pipeline to `llm_max_tool_calls_per_round` (default 8) and the chat service to `llm_max_concurrent_generations` (semaphore 4) — stub the provider, not the guard.
- Database stubs must return the exact row shape production code consumes; live repository tests are required when relationship direction or Cypher semantics are the behavior under test (`spoilerless/tests/test_session_repository.py`).
- Share fakes across modules in `spoilerless/tests/conftest.py`: `NoopGoogleVerifier` satisfies `AuthService`'s required verifier without touching Google (PROB-09/#77). When a required dependency is injected (no silent fallbacks), add one shared stub in conftest rather than per-file copies. Phase 11 adds `_ScratchBoundarySeeds` helpers inside `spoilerless/tests/test_security_boundary.py` (module-scoped helpers `_seed_claims_and_character`, explicit `MERGE` for `Claim`/`Character` with deterministic scratch IDs).
- Test fakes are also shared by importing across test modules: `spoilerless/tests/test_visualization_graphrag.py` reuses `_CallScriptedProvider`, `_StubDatabase`, and `_StubProgressService` from `spoilerless/tests/test_retrieval_pipeline.py` and `_load_fixture` from `spoilerless/tests/test_visualization_projection.py` instead of redefining them.
- Redis is faked with a small in-memory stand-in implementing the exact surface `graph_cache` uses (`get`/`setex`/`scan_iter`/`delete`/`incr`, byte values like the real client): `_FakeRedis` in `spoilerless/tests/test_visualization_cache.py`, enabled by monkeypatching `get_settings().redis_url` and `graph_cache.get_redis`. Phase 11 extends this to `spoilerless/tests/test_rate_limit.py`'s `FakeLimiter` / `_FakeRedis` for the fail-closed vs fail-open matrix (empty `REDIS_URL` → always no-op; `ENVIRONMENT=production` + `rate_limit_fail_open=False` → 503 on `limiter.try_acquire_async` exception).
- Script-guard tests monkeypatch the script's I/O seam: `FakeDocker` in `spoilerless/tests/test_phase10_test_runner.py` records calls and scripts responses by substring match, then `monkeypatch.setattr(runner, "_docker", fake)` drives provisioning/teardown paths without a daemon; teardown-always-runs behavior is asserted on both test-failure and provisioning-exception paths.

**Frontend framework and patterns:**
- Use `vi.mock` for API modules, `vi.mocked(...)` for typed controls, `vi.fn()` for callbacks/fetch, and `vi.stubGlobal` for browser globals.
- Mock transport at the narrowest useful boundary. `frontend/src/api/chat.test.ts` replaces `globalThis.fetch` to assert URL, method, credentials, body, SSE chunking, malformed frames, errors, EOF, and cancellation.
- Mock API modules for component behavior, as in `frontend/src/components/settings/SettingsPage.test.tsx`; do not assert only that a mocked client received a payload when the backend contract itself is the risk. Phase 11 header work (`vercel.json` CSP, `client.ts` header hardening) is better covered by a real `TestClient` header assertion than a mocked-API shape check — when a FE↔BE contract bug ships green, check whether the FE test mocked the API client and asserted the buggy payload (see `references/chat-422-empty-title-08-01.md`).
- Stub `react-cytoscapejs` under jsdom for graph interaction tests. Preserve the real test stub's event-handler registry when writing probes; a no-op `cy.on` produces false conclusions in `frontend/src/App.test.tsx` and `frontend/src/components/graph/GraphCanvas.test.tsx` scenarios.
- For reconciler logic, use the REAL cytoscape headless instead of the stub: `cytoscape({ headless: true, styleEnabled: false, elements })` in `frontend/src/components/graph/cytoscapeReconciler.test.ts` exercises actual compound-removal and edge-rewiring semantics. Assert identity preservation (same element instance, parent, position, classes, selection, zoom, pan) and `cy.destroy()` at the end of each test.

**What not to mock:**
- Do not mock OpenAPI generation or contract documentation parsing; `spoilerless/tests/test_openapi_contract.py` and `spoilerless/tests/test_frontend_contract_doc.py` intentionally lock the real API inventory. Phase 11 adds `413 PAYLOAD_TOO_LARGE` to that inventory.
- Do not replace Neo4j with a fake when verifying Cypher relationship direction, transaction behavior, spoiler filtering, or persistence round trips; use scoped live-DB integration tests. The security boundary suite is explicitly live-DB (scratch series + `live_client` + real `ProgressService`).
- Do not use render-body counters as mount counters in graph tests; re-renders increment them. Assert persistent DOM/loading behavior and spy on the actual layout operation instead.
- Do not stub cytoscape when compound-parent removal, edge rewiring, or element identity is the behavior under test; use a headless real instance as in `frontend/src/components/graph/cytoscapeReconciler.test.ts`.
- Do not start docker or a live database to test the guarded runner itself; `spoilerless/tests/test_phase10_test_runner.py` and `spoilerless/tests/test_phase10_coverage_audit.py` are mock-driven by contract. The same applies to `spoilerless/tests/test_rate_limit.py`'s fail-closed matrix — drive it through the in-memory fakes.

## Fixtures and Factories

**Backend test data:**
- Keep file-owned fixtures near the tests they serve. `spoilerless/tests/test_settings_api.py` defines the live database fixture, app/client builders, authentication helper, and user/session fakes locally.
- Generate collision-resistant scratch identifiers with `uuid4()` and scope cleanup to those identifiers, as in `spoilerless/tests/test_session_repository.py`. For graph-read isolation prefer the `bootstrap_scratch_series` helper (episodes 1–3) demonstrated by `spoilerless/tests/test_security_boundary.py`; deterministic scratch IDs (`extracted:boundary:order1`, `scratch:boundary:late_char`, `scratch:boundary:mid_char`) are visible only at their own `visible_from_order` (boundary clamp proof).
- Use repository-root fixture files only from root-invoked pytest; extraction and contract suites refer to `data/` and `docs/` paths.
- Checked-in safe baselines live in `spoilerless/tests/fixtures/visualization/`: `s01e01_safe.json` and `s01e02_cumulative_safe.json` contain only rows visible at their effective boundary plus explicit episode/projection-version metadata. Load them through `_load_fixture(name)` (`spoilerless/tests/test_visualization_projection.py`) or `load_fixture(name)` (`spoilerless/tests/test_visualization_baseline.py`) and validate through real `GraphResponse.model_validate` — never through a mock seam.
- Keep the baseline tracer's numeric targets as module constants that serve as the single source of truth: `TARGET_MIN_NODES`, `TARGET_MAX_NODES`, `HARD_MAX_NODES`, `PREFERRED_MAX_EDGES`, `HARD_MAX_EDGES` in `spoilerless/tests/test_visualization_baseline.py`.
- For new graph surface tests, seed the scratch series' `origin`/`label` explicitly (`s.origin='canonical'`, `e.origin='canonical'`, `e.label = coalesce(e.label, e.title, e.code)`) as in `spoilerless/tests/test_security_boundary.py: _seed_claims_and_character`; `NODES_QUERY` validates `origin == 'canonical'` and the adapter expects a label.

**Frontend test data:**
- Reuse `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts` for large shared shapes.
- Define small, behavior-specific factories beside tests (`progressRecord` in `frontend/src/hooks/useWatchProgress.test.ts`, `mockFetchJson`/`mockStreamResponse` in `frontend/src/api/chat.test.ts`, `makeDto(overrides)` in `frontend/src/lib/visualizationAdapter.test.ts`).
- Keep fixture counts synchronized with exact graph assertions; changes to a shared graph fixture can legitimately require count updates in graph/App tests.
- Type Phase 10 fixture objects against the real `VisualizationDTO` type and mirror the backend shape: `vizFixture`/`expansionFixture` in `frontend/src/App.test.tsx` are typed `VisualizationDTO` (from `frontend/src/types/graph.ts`) and mirror `spoilerless/app/domain/visualization.py` (D-08/D-29), with a comment noting the mirrored contract.

## Live Neo4j Safety

- Treat backend integration tests as destructive-capable operations against a shared live Neo4j database. Never point them at irreplaceable data, and do not interrupt mutation-heavy runs during fixture teardown.
- Global persistent data such as `:AppSetting {key: 'llm'}` must be backed up before a test and restored afterward. `spoilerless/tests/test_settings_api.py` reads the prior value, permits deterministic mutation, then `MERGE`s the original value back; it deletes only when no node existed before the test.
- Session/auth integration records must use unique scratch owners/IDs and narrowly delete only the test-owned `:AppUser`/`:Session` subgraph, as in `spoilerless/tests/test_session_repository.py`. Never use an unconditional global `MATCH (s:Session) DETACH DELETE s` cleanup.
- Scratch graph integration fixtures must use dedicated series/entity IDs and delete only those records; `spoilerless/tests/test_retrieval_tools.py` demonstrates series-scoped setup/teardown and `spoilerless/tests/test_security_boundary.py` demonstrates the canonical scratch-series pattern (`SCRATCH = "series_scratch_boundary"` + `teardown_scratch_series(SCRATCH)`).
- Context-manage synchronous `TestClient` when requests use the async Neo4j driver. The `with TestClient(...)` pattern in `spoilerless/tests/test_settings_api.py` keeps requests on one portal event loop and avoids pooled-driver cross-loop crashes.
- Sync fixture backup/teardown must create a fresh `Neo4jDatabase`/driver inside the coroutine passed to `asyncio.run`; do not reuse the app/TestClient driver on the teardown loop. Async tests can share their async fixture's loop and driver. The security boundary suite follows the fresh-driver `asyncio.run(_seed_claims_and_character())` pattern on top of `bootstrap_scratch_series`.
- Let generator fixtures reach teardown. After an interrupted live-DB run, re-establish a known seeded state before trusting broad-suite results.
- The 584-pass/7-failed local-docker baseline is RETIRED (NINETEENTH PASS, 2026-08-13): all seven reds were root-caused and fixed (3 doc-contract via the 10-03/10-06 OpenAPI inventory updates, 2 seed-image via the 08-12 self-hosted portrait restore, 2 constraint-name engine-tolerant on `neo4j:2026.06.0-community`), with no assertion weakened. The canonical full-suite command is now `uv run python scripts/run_phase10_backend_tests.py`, which refuses to run while the local docker Neo4j (`spoilerless-neo4j`/`hdgraf-neo4j`) is live and always destroys its ephemeral container. The offline visualization suites never touch a database at all — checked-in safe fixtures only. Phase 11 keeps the same contract: its new integration suite is guard-runner-compatible (scratch series, 0 residue, `_FakeRedis` where Redis is involved).

## Coverage

**Requirements:** None enforced.
- Backend `pyproject.toml` has no pytest-cov dependency, coverage options, or fail-under threshold.
- Frontend `frontend/vite.config.ts` has no Vitest coverage block, and `frontend/package.json` has no coverage provider or coverage script.
- There is currently no supported repository coverage command; do not invent a threshold or claim coverage percentage from test counts.
- Coverage is instead enforced structurally: the Phase 10 closeout machine-readable table in `scripts/verify_phase10_coverage.py` (literal `PHASE10-COVERAGE` markers, exact header, 98 exact source ids) maps every requirement id to an artifact-or-test with evidence refs, and its fail-closed parsing contract is locked by `spoilerless/tests/test_phase10_coverage_audit.py` (duplicate/missing/extra/malformed rows, empty fields, and self-referencing evidence all rejected). Phase 11 replaces this with `SECURITY_TEST_PLAN.md` traceability; `spoilerless/tests/test_security_boundary.py` docstrings cite `SECURITY_TEST_PLAN §1.1/1.4/1.5` per test.

## Test Types

**Unit tests:**
- Domain/model validation, pure helpers, error shaping, API client parsing, graph style/element conversion, and hook state behavior are covered in files such as `spoilerless/tests/test_user_content_models.py`, `spoilerless/tests/test_openapi_contract.py`, `spoilerless/tests/test_error_handlers.py`, `spoilerless/tests/test_spoiler_policy.py`, `frontend/src/api/chat.test.ts`, and `frontend/src/hooks/useWatchProgress.test.ts`.
- The PROB-09 wave added focused unit suites: `spoilerless/tests/test_google_verifier.py`, `spoilerless/tests/test_main_lifespan.py`, `spoilerless/tests/test_rate_limit.py`, `spoilerless/tests/test_ontology.py`, `spoilerless/tests/test_series_service.py`, `spoilerless/tests/test_setup_schema_check.py`, `spoilerless/tests/test_share_api.py`, `spoilerless/tests/test_spoiler_policy.py`, and `spoilerless/tests/test_s01e01_enrichment.py`.
- The Phase 10 wave added offline visualization unit/contract suites (no live Neo4j, no LLM, no retrieval): `spoilerless/tests/test_visualization_projection.py` (exact DTO shape, stable IDs, 0/1/many payloads, schema validation and reference closure, omission of `PARTICIPATED_IN`/`OCCURRED_IN`, human edge classes only), `spoilerless/tests/test_visualization_baseline.py` (checked-in fixtures → real `GraphResponse` validation → boundary assertion → baseline metrics → Variant A/B projections → `build_evidence()`), `spoilerless/tests/test_visualization_cache.py` (key dimensions, miss/hit round-trip, stale-metadata rejection, poisoning resistance, no-op when Redis disabled, Redis error degradation), and `spoilerless/tests/test_visualization_graphrag.py` (pure `build_graphrag_focus` classifier).
- Phase 11 adds small pure unit suites: `effective_view_order`/`resolve_effective_boundary` in `spoilerless/tests/test_spoiler_policy.py`, `_sanitized_validation_errors` in `spoilerless/tests/test_error_handlers.py`, `TrustedHost` derivation and `BodySizeLimitMiddleware` (Content-Length + chunked + 413 envelope) in `spoilerless/tests/test_main_lifespan.py` / `spoilerless/tests/test_security_boundary.py`, and the rate-limit fail-closed matrix in `spoilerless/tests/test_rate_limit.py` (empty `REDIS_URL` → neutralized via `conftest`, production fail-open → warning + return, production fail-closed → 503).
- Script-guard unit suites: `spoilerless/tests/test_phase10_coverage_audit.py` and `spoilerless/tests/test_phase10_test_runner.py` load `scripts/verify_phase10_coverage.py` and `scripts/run_phase10_backend_tests.py` in-process and lock their fail-closed contracts, CLI exit codes, chunk inventory (`test_chunk_inventory_covers_every_test_file_exactly_once`), and teardown guarantees. They remain applicable; Phase 11 does not replace them but adds the boundary suite to the chunk inventory gate.

**Integration tests:**
- FastAPI router/service flows, live Neo4j repositories, graph retrieval, progress/settings persistence, and change-set/chat flows live throughout `spoilerless/tests/`. Phase 11 extends the candidate surface (`spoilerless/tests/test_candidate_ingest.py` now seeds via scratch series, asserts `invalidate_series` after ingest, and covers pagination `limit/after_created_at/after_id` + rate limiting; `spoilerless/tests/test_candidate_review.py` covers the unified resolver clamp).
- `spoilerless/tests/test_graph_api.py` gained the `test_visualization_route_*` family: validated DTOs end to end, all views return valid DTOs (parametrized), 404/422 shapes, anonymous clamping to order one, authenticated clamping by progress, focus-id rejection for non-focus views, GraphRAG focus 422s and caps, cache-hit byte-for-byte equality with a miss, Redis-failure still serving, and preservation of legacy `/graph` route behavior. The boundary-specific assertions are now shared with `spoilerless/tests/test_security_boundary.py`'s `live_client` tracer (anonymous 401→ fixed 1 via `resolve_effective_boundary`, no-record 1, clamp via real `ProgressService`).
- `spoilerless/tests/test_security_boundary.py` (Phase 11, 11-01 tracer) is the dedicated live-DB boundary probe: `SCRATCH = "series_scratch_boundary"` with episodes 1–3, claims at orders 1/3, late/mid characters at 3/2; `live_client` seeds via real `setup_database` + `Neo4jDatabase.open()`; assertions mirror `SECURITY_TEST_PLAN.md §1.1/1.4/1.5` (anonymous → 1, no-record → 1, clamp → `min(requested, view_as_of, watched_through)`, invalid order → 422 `INVALID_VISIBLE_UNTIL_ORDER`); never touches `series_dexter`.
- `frontend/src/App.test.tsx` provides broad component integration with mocked network/graph-renderer boundaries, now including visitor detail-inspector read-only assertions and the above-boundary spoiler-warning modal regression test.

**Contract tests:**
- `spoilerless/tests/test_openapi_contract.py` locks exact OpenAPI paths, operations, response models, boundaries, and sanitized errors (now includes `413 PAYLOAD_TOO_LARGE`).
- `spoilerless/tests/test_frontend_contract_doc.py` locks `docs/reference/frontend-api-contract.md` against the route inventory. API changes must update runtime routes, OpenAPI expectations, documentation expectations, and the contract document together. Phase 11 candidate pagination (`limit`, `after_created_at`, `after_id`) and body-size/CSP header docs must be reflected here.
- `spoilerless/tests/test_visualization_projection.py` locks the neutral `VisualizationDTO` contract (D-08/D-10 Variant A): exact shape, stable IDs, deterministic output, forbidden-key vocabulary, raw-relation-name exclusion, and the projection-version metadata contract.
- `spoilerless/tests/test_phase10_coverage_audit.py` locks the `PHASE10-COVERAGE` machine-readable table contract (literal markers, exact header, exact 98-id inventory).
- `frontend/src/lib/visualizationAdapter.test.ts` pins the emitted data-key set per element kind so a hidden field cannot silently flow into Cytoscape data.
- `spoilerless/tests/test_spoiler_policy.py` + `spoilerless/tests/test_error_handlers.py` pin the policy and sanitized-error contracts that Phase 11 hardens.

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
- Keep operations that share a driver on one event loop; use a fresh driver for a separate `asyncio.run` cleanup loop. The security boundary suite's `asyncio.run(_seed_claims_and_character())` + fresh `Neo4jDatabase().open()` + `await db.verify_connection()` pattern is the canonical fresh-loop seeding.

**Scratch-series isolation (Phase 11):**
```python
# spoilerless/tests/test_security_boundary.py
SCRATCH = "series_scratch_boundary"
bootstrap_scratch_series(SCRATCH, (1, 2, 3))
# ... seed candidate claims at 1/3, characters at 2/3 ...
teardown_scratch_series(SCRATCH)  # MATCH (n {series_id: $sid}) DETACH DELETE n
```
- Use `conftest.bootstrap_scratch_series` for any new graph-surface test that adds rows; it creates `Series` + `Episode` scaffolding with `origin='canonical'` so `NODES_QUERY`'s label/origin checks pass. Never seed net-new constraints or touch `series_dexter` from a non-audit test.

**Offline fixture pipeline (visualization baselines):**
```python
# spoilerless/tests/test_visualization_baseline.py
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "visualization"
FIXTURE_FILES = ("s01e01_safe.json", "s01e02_cumulative_safe.json")

def load_fixture(name: str) -> dict[str, Any]:
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)
```

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

**Security-boundary testing (Phase 11):**
```python
# spoilerless/tests/test_security_boundary.py — DB-probe, not a stub
async def test_anonymous_fixed_at_order_one(live_client: TestClient) -> None:
    resp = live_client.get(f"/api/series/{SCRATCH}/graph?visible_until_order=999")
    assert resp.status_code == 200  # inside resolver it's clamped to 1 before graph read
    # the late_char (visible_from_order=3) is absent

async def test_authenticated_no_record_fixed_at_one(live_client: TestClient, user_without_progress) -> None: ...
async def test_authenticated_clamps_to_min_requested_view_watched(...) -> None: ...
async def test_invalid_order_returns_422_with_registered_code(...) -> None: ...
```

**Error testing:**
```python
response = client.post("/items", json={"count": 0, "unexpected": secret})
assert response.status_code == 422
assert response.json() == {
    "detail": {"code": "invalid_request", "message": "Request validation failed."}
}
assert secret not in response.text
# Phase 11 adds the 413 path:
response = client.post("/api/series/x/candidates", content=b"x" * (max_body_size_bytes + 1))
assert response.status_code == 413
assert response.json() == {"detail": {"code": "payload_too_large", "message": "Request body too large."}}
assert secret not in response.text  # bodies are not echoed
```
- Assert status, stable machine code, sanitized message, and non-disclosure, as in `spoilerless/tests/test_openapi_contract.py`. New codes like `PAYLOAD_TOO_LARGE` must be in `spoilerless/app/core/errors.py: ERROR_CODES` and `_ERROR_SPECS`.
- Frontend API tests should assert that non-2xx responses become `ApiError` with backend code/message intact and that malformed/early-ended SSE never leaves streaming state stuck (`frontend/src/api/chat.test.ts`).

## Build, Lint, and CI Gates

- `frontend/package.json` defines `npm run build` as `tsc -b && vite build`; there is no separate Python build command.
- `npm run lint` passes on the live 2026-08-14 run: 0 errors and 21 warnings (all `react-hooks/*` warnings per `frontend/eslint.config.js`). Phase 11 keeps this contract; `frontend/vercel.json` CSP is not linted.
- `.github/workflows/ci.yml` runs on every PR: backend pytest against a service-container Neo4j pinned to `neo4j:2026.06.0-community` (seed then suite, plus a DB-pollution gate asserting zero `series_scratch`/`origin='candidate'` residue — Phase 11's `series_scratch_boundary` is covered by the `series_scratch%` wildcard), and a frontend job (Node 24, `npm ci`, build, lint, `npm audit`). `.github/workflows/release.yml` is a staged-promotion skeleton gated on the CI workflow. The pollution gate will catch the new scratch series if leaked.
- Before submitting changes, run the relevant backend tests, `NODE_ENV=test CI=1 npm run test`, `npm run build`, and `npm run lint`. For a full backend run use `uv run python scripts/run_phase10_backend_tests.py`; the old 584/7 local-docker baseline no longer applies (retired 2026-08-13). Include `spoilerless/tests/test_security_boundary.py` in targeted boundary verification (it needs a live DB, so use the guarded runner or a scratch-isolated local run).
- `scripts/verify_phase10_coverage.py` and the root claim-verification scripts (`run_verification.py`, `run_doc_verification.py`, `verify_all_claims.py`, `verify_arch.py`) are manual audit tooling, not CI gates; their results feed the `docs/PROBLEMS.md` PASS ledger. Phase 11 traces via `SECURITY_TEST_PLAN.md` / `SECURITY_AUDIT.md` instead of `PHASE10-COVERAGE`.

---

*Testing analysis: 2026-08-20*
