<!-- generated-by: gsd-doc-writer -->
# Testing

Spoilerless has a Python backend suite under `spoilerless/tests/` and a colocated React/TypeScript frontend suite under `frontend/src/`.

## Test frameworks and setup

### Backend

The backend uses:

- `pytest>=9.1.1`
- `pytest-asyncio>=1.4.0`
- `httpx>=0.28.1` and FastAPI's `TestClient` for HTTP tests
- `asyncio_mode = "auto"`
- `spoilerless/tests` as the configured pytest test path

These settings are defined in the root `pyproject.toml`. Python `>=3.13` is required.

Install the locked Python environment from the repository root:

```bash
uv sync --frozen
```

Many backend files are unit or contract tests, but the suite is not split into separately configured unit and integration groups. Files that instantiate `Neo4jDatabase`, call `setup_database()`, or use a live application `TestClient` connect to Neo4j. For a fresh local test database, use one coherent credential set and seed it before running those files:

```bash
source scripts/env-local.sh
docker compose up -d neo4j
uv run --project spoilerless python -m spoilerless.app.graph.setup
```

`scripts/env-local.sh` exports `NEO4J_URI=neo4j://localhost:7687`, username `neo4j`, password `hdgraf-local-password`, and database `neo4j`. Sourcing it **before** `docker compose up` also supplies that password to Compose. A container previously initialized with another password keeps the credential stored in `neo4j_data`; changing the shell variable does not reset an existing database.

Alternatively, provide the four `NEO4J_*` variables yourself and make them match the database you intend to test. `spoilerless/tests/conftest.py` does **not** create an isolated database or supply connection settings. It adds the repository root and `spoilerless/` to `sys.path`, so run backend commands from the repository root. This also avoids failures in tests that open repository-relative fixtures such as `data/dexter/test/extraction_fixture.json` and `docs/extraction-schema.json`.

**PYTHONPATH caveat:** any ambient `PYTHONPATH` that points at another package tree (for example, the Hermes agent terminal exports one that shadows the venv) breaks `import spoilerless`. Unset it before running pytest:

```bash
unset PYTHONPATH
```

### Frontend

The frontend uses Vitest `^4.1.10`, Testing Library (`@testing-library/react`, `@testing-library/jest-dom`), and `@testing-library/user-event`. `frontend/vite.config.ts` configures:

- the `jsdom` environment;
- global Vitest APIs;
- `frontend/src/test/setup.ts` as the setup file.

Install the committed dependency tree:

```bash
cd frontend
npm ci
```

The setup file registers jest-dom matchers and browser API shims needed by React 19, Radix components, and graph components, including pointer capture, `ResizeObserver`, and `matchMedia`.

## Running tests

### Backend commands

The complete configured backend suite is broad and includes live-Neo4j mutations. Run it only when the configured database is disposable or explicitly dedicated to tests. Against a fresh local docker Neo4j (`scripts/env-local.sh`), the full suite takes roughly 2 minutes and lands on the documented baseline of 584 passed / 7 failed:

```bash
unset PYTHONPATH && source scripts/env-local.sh && uv run pytest spoilerless/tests -q
```

Run one test file:

```bash
uv run pytest spoilerless/tests/test_user_content_models.py
```

Run a subset selected by name:

```bash
uv run pytest spoilerless/tests/test_graph_api.py -k "graph_error_shapes"
```

Run a single test function without using a `::` node selector:

```bash
uv run pytest spoilerless/tests/test_openapi_contract.py -k "test_validation_error_uses_stable_sanitized_envelope"
```

Useful pytest options can be appended to any command:

```bash
uv run pytest -x -v
```

There are no configured pytest marker groups such as `unit` or `integration`; select subsets by file path or `-k` expression.

**Chunked runner.** `scripts/run_backend_tests.py` splits the suite into 10 named chunks (core, domain-models, series-api, graph, change-set, candidates, auth, user-content, chat-llm, contract-ops), each test file appearing in exactly one chunk:

```bash
uv run python scripts/run_backend_tests.py            # all 10 chunks, sequential
uv run python scripts/run_backend_tests.py --list     # show chunk names and files
uv run python scripts/run_backend_tests.py --chunk 7  # one chunk by index
uv run python scripts/run_backend_tests.py --chunk auth,graph   # a few by name
uv run python scripts/run_backend_tests.py --chunk 7 -x -k foo  # extra pytest args
```

The runner strips `PYTHONPATH` from every child environment, so it works regardless of the ambient shell. It also supports `--parallel` (all selected chunks at once), but measured on the shared AuraDB, parallel is **slower** than serial due to connection contention — use parallel mode only against isolated Neo4j instances. Chunks that re-seed the graph or assert exact global node counts (`seed_idempotency`, `setup_schema_check`) should run alone before any parallel batch. Exit code is non-zero if any chunk fails.

### Documented baseline: never chase the 7

The full-suite baseline is **584 passed / 7 failed** on a fresh local docker Neo4j. The 7 failures are documented pre-existing and are not regressions — do not chase them:

- 3 doc-contract:
  - `spoilerless/tests/test_frontend_contract_doc.py::test_document_has_examples_projection_rules_non_goals_and_pending_status`
  - `spoilerless/tests/test_openapi_contract.py::test_user_route_openapi_has_exact_operations_and_templates`
  - `spoilerless/tests/test_openapi_contract.py::test_all_story_reads_graph_errors_health_and_deletes_are_fully_typed`
- 2 seed-image:
  - `spoilerless/tests/test_graph_api.py::test_graph_nodes_include_image_fields`
  - `spoilerless/tests/test_graph_api.py::TestSeedImageCuration::test_no_seed_image_for_resources_visible_above_order_one`
- 2 seed_idempotency constraint-name:
  - `spoilerless/tests/test_seed_idempotency.py::test_community_schema_creates_only_unique_and_index`
  - `spoilerless/tests/test_seed_idempotency.py::test_constraints_visibility_and_provenance`

A green run means 584 passed with exactly these 7 failing. If a run differs from this baseline (fewer failures, different failures, or failures outside this list), that is a real regression and should be investigated.

### Frontend commands

Use Vitest's explicit run mode for a reliable one-shot full run:

```bash
cd frontend
NODE_ENV=test CI=1 npx vitest run
```

The current frontend suite is 333 passed across 40 files. Setting `NODE_ENV=test` is important: a shell that retains `NODE_ENV=production` can load React's production behavior and cause misleading failures. Setting `CI=1` additionally forces non-watch mode. The equivalent `npm` spelling of the same command is:

```bash
cd frontend
NODE_ENV=test npm run test -- --run
```

Run one test file:

```bash
cd frontend
NODE_ENV=test npx vitest run src/components/detail/DetailPanel.test.tsx
```

Run a subset by test name:

```bash
cd frontend
NODE_ENV=test npx vitest run -t "renders the locked no-selection placeholder with no Tabs"
```

For interactive watch mode, omit `run` and keep the env:

```bash
cd frontend
NODE_ENV=test npx vitest
```

TypeScript typechecking is part of the build script:

```bash
cd frontend
npm run build   # tsc -b && vite build
```

The package defines only the `test` script (`vitest`); there are no separate `test:unit`, `test:integration`, or `test:e2e` scripts. Frontend tests are colocated throughout `frontend/src/`, including `api/`, `components/`, `hooks/`, `lib/`, and the application-level `frontend/src/App.test.tsx`.

## Writing backend tests

- Name files `test_*.py` and test functions `test_*`.
- Use `pytest.mark.parametrize` for input and boundary matrices.
- Use `pytest.mark.asyncio` for async tests; `asyncio_mode = "auto"` also supports async fixtures.
- Prefer existing fakes for isolated service tests, such as `FakeUserRepo`, `FakeGoogleVerifier`, `InMemorySessionRepository`, and `FakeLLMProvider`.
- Use a context-managed `TestClient` when the app owns an async Neo4j driver so requests share one portal event loop.
- Keep spoiler-boundary assertions fail-closed: assert that hidden content is absent, not only that visible content is present.
- Add API inventory changes to both contract tests and `docs/frontend-api-contract.md`. `test_frontend_contract_doc.py` locks the live 50-operation, 37-template inventory; its `test_document_and_openapi_have_exact_locked_inventory` is green, while its doc-content test (`test_document_has_examples_projection_rules_non_goals_and_pending_status`) is part of the documented baseline failures. `test_openapi_contract.py` is an intended companion gate but is currently stale and red: it still expects 32 templates, omits the graph-path, export, and share templates, and assumes every DELETE response is 204 even though share-token revocation returns 200. Do not treat those two files as passing bounded gates until their assertions are updated.

`spoilerless/tests/conftest.py` contains shared import-path setup, scratch-series helpers, and an autouse `_disable_rate_limiter` fixture that patches `RateLimiter.__call__` to a no-op so rate-limited routes are testable without a live Redis. It does not configure Neo4j credentials. Since the 2026-08-10 suite-time pass it also hosts the shared test infrastructure (see `docs/PROBLEMS.md` SEVENTH PASS), extended in the 2026-08-11 ELEVENTH PASS with the shared `NoopGoogleVerifier` (PROB-09/#77 follow-up — `AuthService` requires a verifier, and tests that never exercise Google verification share this one no-op):

- `seed_live_database()` / `live_client` — one seeded main-app TestClient definition (was copy-pasted in six files).
- `module_cleanup_fixture(queries)` / `cleanup_with_fresh_driver(queries)` — per-test second-driver cleanup moved to once-per-module teardown; `(query, params)` tuples supported. The factory's return value MUST be bound to a module-level name (e.g. `_cleanup_after_module = module_cleanup_fixture(...)`) or pytest never registers the fixture.
- `run_query(query, **params)` — fresh-driver probe helper (reliable read-after-write on AuraDB; a shared-driver variant intermittently missed app-driver writes).
- `helper_db()` / `run_async(coro_factory)` — shared driver/loop for service-level probes (chat/progress).
- `bootstrap_scratch_series(series_id, episode_orders)` / `teardown_scratch_series(series_id)` — idempotently create and remove the scratch `:Series`/`:Episode` nodes plus all `origin='candidate'` residue and `UserSeriesProgress` rows, on a fresh driver/loop so they are safe inside sync TestClient tests.
- `NoopGoogleVerifier` — shared no-op `AuthService` verifier for tests that never call Google.
- `pytest-asyncio` is configured with `asyncio_default_fixture_loop_scope = "module"` / `asyncio_default_test_loop_scope = "module"` so module-scoped async database fixtures are safe (one loop per file).

Most other fixtures and helper functions are local to the test file that owns them. Examples include live database/client fixtures, in-memory authentication repositories, HTTP transport stubs, SSE parsers, and fixture-payload builders.

### Live Neo4j safety

Backend integration tests are not automatically isolated from the application's default `neo4j` database. Several tests seed data, create scratch records, or delete records during cleanup. Do not run the backend integration suite against a Neo4j database containing irreplaceable data, and do not interrupt a run during fixture cleanup.

When a test changes persistent user configuration, preserve and restore the previous value rather than deleting it unconditionally. `test_settings_api.py` demonstrates the required pattern: it backs up the existing `:AppSetting {key: 'llm'}` value, performs the test, then restores that value with a fresh driver and event loop. Scratch fixtures such as those in `test_retrieval_tools.py` create records under a dedicated series ID and delete that series in teardown.

`test_candidate_ingest.py` and `test_candidate_review.py` use a scratch-series pattern. They create dedicated `series_scratch_candidates` / `series_scratch_review` series via `bootstrap_scratch_series()` in `conftest.py`, and `teardown_scratch_series()` runs from `finally` on a fresh driver/event loop. Teardown removes the scratch series, its progress rows, and all `origin='candidate'` nodes. These files no longer write candidate data into `series_dexter`, but their global candidate cleanup is another reason not to run them against a shared or valuable database.

Treat the default test configuration as a **shared-live-database hazard**, not as an isolated test container:

- Prefer unit/contract files that do not open Neo4j, or target one live test file with `-k`, before considering the broad suite.
- Point integration runs at a disposable Neo4j database or back up anything that must survive. Tests consume the same `NEO4J_*` settings as the application; `conftest.py` does not redirect them to a test-only database.
- Run live-database files sequentially, and never launch two concurrent pytest processes against the same database. No xdist configuration is present, and scratch cleanup, seed setup, and shared settings restoration are not designed for concurrent workers or concurrent test runs against the same database (the chunked runner's `--parallel` mode exists only for isolated Neo4j instances).
- Let teardown complete. An interrupted run can leave sessions, progress, candidate, ChangeSet, or scratch-series records behind and make later results order/state dependent.
- If a run was interrupted, assume the database may be dirty. Inspect and back it up before any cleanup or reseed; `spoilerless.app.graph.setup` writes the configured graph and is not a substitute for a backup.
- Tests that open the application with its async driver should use `with TestClient(...)` so all requests share one portal loop. Teardown that needs a different loop should open a fresh driver, as `test_settings_api.py` does.

## Spoiler-safety and API contract tests

For every new spoiler-sensitive read, test both sides of the boundary: visible records are present, future IDs/labels/count hints are absent from the serialized response, dangling edges are impossible, invalid/non-persisted boundaries fail, and hidden direct reads are indistinguishable from missing resources. The graph boundary patterns live in `spoilerless/tests/test_graph_api.py`; user-content boundary behavior lives in `spoilerless/tests/test_user_content_api.py`; retrieval/tool isolation lives in `spoilerless/tests/test_retrieval_tools.py` and `spoilerless/tests/test_retrieval_pipeline.py`.

The HTTP surface is a closed inventory. Adding, removing, or changing a route requires synchronized edits to:

- `spoilerless/tests/test_openapi_contract.py`;
- `spoilerless/tests/test_frontend_contract_doc.py` (`EXPECTED_OPERATIONS`, template and count assertions);
- `docs/frontend-api-contract.md` (one exact `(method, path)` row per operation).

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Root-relative fixture `FileNotFoundError` | pytest was run from `spoilerless/` | Re-run from the repository root. |
| `ModuleNotFoundError: spoilerless` under the Hermes terminal | Ambient `PYTHONPATH` shadows the venv | `unset PYTHONPATH` before the pytest/uv command, or use `scripts/run_backend_tests.py`. |
| Many unrelated live-DB failures after an aborted run | Shared Neo4j contains partial fixture state | Stop; inspect/backup the database, then clean or reseed only with explicit data-loss awareness. Re-run a focused file before blaming source. |
| `test_seed_idempotency.py` fails with a relationship/node mismatch | The disposable test DB was not clean, or an interrupted/concurrent run left user/candidate records behind. | Stop concurrent runs and inspect the configured database. On a disposable local DB, run the setup module and retry the focused file; never use reseeding as a substitute for backing up valuable data. |
| Exactly 7 failures matching the documented baseline | Not a regression — the documented pre-existing baseline | Do not chase them; they are expected (see "Documented baseline"). |
| Any failure count or set different from the 7-failure baseline | Likely a real regression from source changes | Investigate the new failure; the 7-name list above is the only accepted baseline. |
| React renders an empty container or many Testing Library lookups fail | `NODE_ENV=production` leaked into Vitest | Re-run with `NODE_ENV=test CI=1 npx vitest run`. |
| `toBeInTheDocument` is missing | Wrong jest-dom entry/setup | Keep `@testing-library/jest-dom/vitest` in `frontend/src/test/setup.ts`. |
| Pointer capture, `ResizeObserver`, `matchMedia`, or `React.act` fails | Required jsdom shim is absent | Add a suite-wide shim to `frontend/src/test/setup.ts`, not per test. |
| Cytoscape click/focus test does nothing | Stub does not preserve/register handlers or collection behavior | Follow the stateful stubs in `frontend/src/App.test.tsx` and `frontend/src/components/graph/GraphCanvas.test.tsx`. |

## Writing frontend tests

- Colocate tests with source files and name them `*.test.ts` or `*.test.tsx`.
- Import test APIs from `vitest` and use Testing Library's `render`, `renderHook`, `screen`, and `waitFor`.
- Prefer `userEvent.setup()` for user interactions and role/name queries for assertions.
- Reset shared browser and mock state in `beforeEach`/`afterEach`; existing suites use `sessionStorage.clear()`, `vi.stubGlobal`, `vi.mock`, `vi.clearAllMocks()`, and `vi.unstubAllGlobals()` as appropriate.
- Reuse data from `frontend/src/test/fixtures/chatFixtures.ts` and `frontend/src/test/fixtures/graphResponse.ts` instead of duplicating large payloads.
- Stub `react-cytoscapejs` when testing graph behavior under jsdom; existing `App.test.tsx` and `GraphCanvas.test.tsx` show the event-handler and collection stubs.
- Put suite-wide DOM/browser shims in `frontend/src/test/setup.ts`, not in every test file.

## Coverage requirements

No coverage threshold is configured for either suite.

| Suite | Threshold |
|---|---:|
| Backend lines, branches, functions, statements | None configured |
| Frontend lines, branches, functions, statements | None configured |

The backend configuration has no `pytest-cov` or `--cov-fail-under` setting. The frontend has no Vitest coverage configuration or coverage provider dependency, so a coverage command is not currently part of the supported test workflow.

## CI integration

The repository uses GitHub Actions (`.github/workflows/ci.yml`) to run checks on `pull_request` events only. A direct push to `main` does not trigger this CI workflow. The manually dispatched `release.yml` is currently a promotion skeleton and does not run either test suite.

### Backend

The backend suite runs in CI on Ubuntu using `uv` against an ephemeral Neo4j service container (`neo4j:2026.06.0-community`). The workflow executes:
- Schema setup: `uv run --project spoilerless python -m spoilerless.app.graph.setup`
- The test suite: `uv run pytest`
- A pollution gate: an automated check to ensure no scratch-series or candidate-origin residue is left in the database.

### Frontend

The frontend CI job performs build, lint, and audit steps (`npm ci`, `npm run build`, `npm run lint`, `npm audit --audit-level=high`), but it does **not** execute the frontend test suite. Ensure you run frontend tests locally before submitting changes.
