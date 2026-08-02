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

Run the complete configured backend suite from the repository root:

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

This exact command was verified against the current suite. Setting `NODE_ENV=test` is important: a shell that retains `NODE_ENV=production` can load React's production behavior and cause misleading failures.

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

`backend/tests/conftest.py` contains only shared path and Neo4j environment setup. Most fixtures and helper functions are local to the test file that owns them. Examples include live database/client fixtures, in-memory authentication repositories, HTTP transport stubs, SSE parsers, and fixture-payload builders.

### Live Neo4j safety

Backend integration tests are not automatically isolated from the application's default `neo4j` database. Several tests seed data, create scratch records, or delete records during cleanup. Do not run the backend integration suite against a Neo4j database containing irreplaceable data, and do not interrupt a run during fixture cleanup.

When a test changes persistent user configuration, preserve and restore the previous value rather than deleting it unconditionally. `test_settings_api.py` demonstrates the required pattern: it backs up the existing `:AppSetting {key: 'llm'}` value, performs the test, then restores that value with a fresh driver and event loop. Scratch fixtures such as those in `test_retrieval_tools.py` create records under a dedicated series ID and delete that series in teardown.

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

No CI test workflow is configured. The repository has no `.github/workflows/` directory, so pushes and pull requests do not automatically run pytest or Vitest. Run both full-suite commands locally before submitting changes.
