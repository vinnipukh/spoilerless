<!-- generated-by: gsd-doc-writer -->
# Testing

HD Graf Cehennemi has a Python backend suite under `backend/tests/` and a colocated React/TypeScript frontend suite under `frontend/src/`.

## Test frameworks and setup

### Backend

The backend uses:

- `pytest>=9.1.1`
- `pytest-asyncio>=1.4.0`
- `httpx>=0.28.1` and FastAPI's `TestClient` for HTTP tests
- `asyncio_mode = "auto"`
- `backend/tests` as the configured pytest test path

These settings are defined in the root `pyproject.toml`. Python `>=3.13` is required.

Install the Python dependencies from the repository root:

```bash
uv sync
```

Many backend files are unit or contract tests, but integration tests connect to Neo4j. Start the repository's Neo4j service before running those tests:

```bash
docker compose up -d
```

`backend/tests/conftest.py` supplies these defaults unless the environment already overrides them:

```text
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=hdgraf-local-password
NEO4J_DATABASE=neo4j
```

The same file adds both the repository root and `backend/` to `sys.path`, so run backend commands from the repository root. This also avoids failures in tests that open repository-relative fixtures such as `data/dexter/test/extraction_fixture.json` and `docs/extraction-schema.json`.

### Frontend

The frontend uses Vitest `^4.1.10`, Testing Library, `@testing-library/jest-dom`, and `user-event`. `frontend/vite.config.ts` configures:

- the `jsdom` environment;
- global Vitest APIs;
- `frontend/src/test/setup.ts` as the setup file.

Install dependencies once:

```bash
cd frontend
npm install
```

The setup file registers jest-dom matchers and browser API shims needed by React 19, Radix components, and graph components, including pointer capture, `ResizeObserver`, and `matchMedia`.

## Running tests

### Backend commands

The complete configured backend suite is broad and includes live-Neo4j mutations. Run it only when the configured database is disposable or explicitly dedicated to tests:

```bash
uv run pytest
```

Run one test file:

```bash
uv run pytest backend/tests/test_openapi_contract.py
```

Run a subset selected by name:

```bash
uv run pytest backend/tests/test_graph_api.py -k "graph_error_shapes"
```

Run a single test function without using a `::` node selector:

```bash
uv run pytest backend/tests/test_openapi_contract.py -k "test_validation_error_uses_stable_sanitized_envelope"
```

Useful pytest options can be appended to any command:

```bash
uv run pytest -x -v
```

There are no configured pytest marker groups such as `unit` or `integration`; select subsets by file path or `-k` expression.

### Frontend commands

Use an explicit test environment and CI mode for a reliable one-shot full run:

```bash
cd frontend
NODE_ENV=test CI=1 npm run test
```

Setting `NODE_ENV=test` is important: a shell that retains `NODE_ENV=production` can load React's production behavior and cause misleading failures. This document does not claim the current suite passes; report the output of the run you perform.

Run one test file:

```bash
cd frontend
NODE_ENV=test CI=1 npm run test -- src/components/detail/DetailPanel.test.tsx
```

Run a subset by test name:

```bash
cd frontend
NODE_ENV=test CI=1 npm run test -- -t "renders the locked no-selection placeholder with no Tabs"
```

For interactive watch mode, omit `CI=1`:

```bash
cd frontend
NODE_ENV=test npm run test
```

The package defines only the `test` script (`vitest`); there are no separate `test:unit`, `test:integration`, or `test:e2e` scripts.

## Writing backend tests

- Name files `test_*.py` and test functions `test_*`.
- Use `pytest.mark.parametrize` for input and boundary matrices.
- Use `pytest.mark.asyncio` for async tests; `asyncio_mode = "auto"` also supports async fixtures.
- Prefer existing fakes for isolated service tests, such as `FakeUserRepo`, `FakeGoogleVerifier`, `InMemorySessionRepository`, and `FakeLLMProvider`.
- Use a context-managed `TestClient` when the app owns an async Neo4j driver so requests share one portal event loop.
- Keep spoiler-boundary assertions fail-closed: assert that hidden content is absent, not only that visible content is present.
- Add API inventory changes to both contract tests and `docs/frontend-api-contract.md`; `test_openapi_contract.py` and `test_frontend_contract_doc.py` enforce the API surface.

`backend/tests/conftest.py` contains shared path and Neo4j environment setup, plus an autouse `_disable_rate_limiter` fixture that patches `RateLimiter.__call__` to a no-op so rate-limited routes are testable without a live Redis. Most other fixtures and helper functions are local to the test file that owns them. Examples include live database/client fixtures, in-memory authentication repositories, HTTP transport stubs, SSE parsers, and fixture-payload builders.

### Live Neo4j safety

Backend integration tests are not automatically isolated from the application's default `neo4j` database. Several tests seed data, create scratch records, or delete records during cleanup. Do not run the backend integration suite against a Neo4j database containing irreplaceable data, and do not interrupt a run during fixture cleanup.

When a test changes persistent user configuration, preserve and restore the previous value rather than deleting it unconditionally. `test_settings_api.py` demonstrates the required pattern: it backs up the existing `:AppSetting {key: 'llm'}` value, performs the test, then restores that value with a fresh driver and event loop. Scratch fixtures such as those in `test_retrieval_tools.py` create records under a dedicated series ID and delete that series in teardown.

`test_candidate_ingest.py` and `test_candidate_review.py` are a known exception to that pattern: they write `Claim` and `EvidenceFragment` records onto the seeded `series_dexter` series and do not delete them in teardown. Running those files leaves extra rows on the shared database, which can make `test_seed_idempotency.py`'s exact-count assertions (e.g. relationship counts) fail on a later run against the same database even though the seed logic itself is correct. If `test_seed_idempotency.py` fails with a count mismatch, re-seed against a disposable database or run it before the candidate test files rather than treating the mismatch as a seed-logic bug.

Treat the default test configuration as a **shared-live-database hazard**, not as an isolated test container:

- Prefer unit/contract files that do not open Neo4j, or target one live test file with `-k`, before considering the broad suite.
- Point integration runs at a disposable Neo4j database or back up anything that must survive. The defaults in `conftest.py` are the same local host, credentials, and database commonly used by the application.
- Let teardown complete. An interrupted run can leave sessions, progress, candidate, ChangeSet, or scratch-series records behind and make later results order/state dependent.
- If a run was interrupted, assume the database may be dirty. Inspect and back it up before any cleanup or reseed; `backend.app.graph.setup` writes the configured graph and is not a substitute for a backup.
- Tests that open the application with its async driver should use `with TestClient(...)` so all requests share one portal loop. Teardown that needs a different loop should open a fresh driver, as `test_settings_api.py` does.

## Spoiler-safety and API contract tests

For every new spoiler-sensitive read, test both sides of the boundary: visible records are present, future IDs/labels/count hints are absent from the serialized response, dangling edges are impossible, invalid/non-persisted boundaries fail, and hidden direct reads are indistinguishable from missing resources. The graph boundary patterns live in `backend/tests/test_graph_api.py`; user-content boundary behavior lives in `backend/tests/test_user_content_api.py`; retrieval/tool isolation lives in `backend/tests/test_retrieval_tools.py` and `backend/tests/test_retrieval_pipeline.py`.

The HTTP surface is a closed inventory. Adding, removing, or changing a route requires synchronized edits to:

- `backend/tests/test_openapi_contract.py`;
- `backend/tests/test_frontend_contract_doc.py` (`EXPECTED_OPERATIONS`, template and count assertions);
- `docs/frontend-api-contract.md` (one exact `(method, path)` row per operation).

## Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Root-relative fixture `FileNotFoundError` | pytest was run from `backend/` | Re-run from the repository root. |
| Many unrelated live-DB failures after an aborted run | Shared Neo4j contains partial fixture state | Stop; inspect/backup the database, then clean or reseed only with explicit data-loss awareness. Re-run a focused file before blaming source. |
| `test_seed_idempotency.py` fails with a relationship/node count mismatch | `test_candidate_ingest.py`/`test_candidate_review.py` left extra `Claim`/`EvidenceFragment` rows on `series_dexter` from an earlier run | Re-seed against a disposable database, or run `test_seed_idempotency.py` before the candidate test files rather than after them. |
| React renders an empty container or many Testing Library lookups fail | `NODE_ENV=production` leaked into Vitest | Re-run with `NODE_ENV=test CI=1`. |
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

No CI test workflow is configured. The repository has no `.github/workflows/` directory, so pushes and pull requests do not automatically run pytest or Vitest. Record local results before submitting changes; use a disposable/test-only Neo4j database for the broad backend suite.
