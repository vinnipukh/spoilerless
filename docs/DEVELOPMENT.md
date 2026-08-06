<!-- generated-by: gsd-doc-writer -->
# Development

This guide covers local development for the FastAPI/Neo4j backend and the React/TypeScript frontend. Run backend and repository-wide commands from the repository root unless a command explicitly changes into `frontend/`.

## Local setup

### Prerequisites

- Python `>=3.13` (declared in `pyproject.toml`)
- [uv](https://docs.astral.sh/uv/) for Python dependency and environment management
- Node.js `^20.19.0` or `>=22.12.0` (the engine range required by the installed Vite 8 toolchain)
- npm (the frontend has a committed `package-lock.json`)
- Docker Desktop or another Docker Compose implementation for local Neo4j
- Redis is optional for local development. `docker-compose.yml` only runs Neo4j; leaving `REDIS_URL` unset in `.env` disables the Redis-backed rate limiter and the graph response cache (`spoilerless/app/cache/`) without breaking anything else. See [CONFIGURATION.md](CONFIGURATION.md#rate-limiting--redis-cache) to enable them against Upstash or another Redis instance.

### Clone or fork

Clone the upstream repository directly:

```bash
git clone https://github.com/vinnipukh/hdgrafcehennemi.git
cd hdgrafcehennemi
```

If you plan to contribute through a fork, fork the repository on GitHub, clone your fork instead, and optionally retain the upstream repository as a remote:

```bash
git remote add upstream https://github.com/vinnipukh/hdgrafcehennemi.git
```

### Configure the backend and frontend

1. Create the single root environment file (PROB-30/#55 — one root `.env`, no
   per-package copies):

   ```bash
   cp .env.example .env
   ```

2. In `.env`, set `NEO4J_PASSWORD=hdgraf-local-password` to match `docker-compose.yml`. Set `GOOGLE_CLIENT_ID` if you need to sign in.
3. `VITE_GOOGLE_CLIENT_ID` also lives in the root `.env` (same Google OAuth client ID as `GOOGLE_CLIENT_ID`) — `frontend/vite.config.ts` loads the root `.env` via `envDir: '..'` and only exposes `VITE_`-prefixed vars to the browser. Keep `VITE_API_BASE_URL=/api` there too.
4. Do not commit the local environment file. See [CONFIGURATION.md](CONFIGURATION.md) for the complete setting reference.

### Install dependencies and initialize Neo4j

```bash
# Repository root
uv sync
docker compose up -d
uv run --project spoilerless python -m spoilerless.app.graph.setup

# Frontend dependencies
cd frontend
npm install
cd ..
```

`pyproject.toml` declares an `spoilerless-setup` console script, but this checkout is not installed as a package by the current uv environment, so the module invocation above is the reliable seed command.

### Start the development servers

Run the backend from the repository root:

```bash
uv run uvicorn spoilerless.app.main:app --reload
```

Run the frontend in a second terminal:

```bash
cd frontend
npm run dev
```

The backend serves on `http://localhost:8000`; Swagger UI is at `http://localhost:8000/docs`. Vite serves on `http://localhost:5173` and proxies `/api` to `http://127.0.0.1:8000` through `frontend/vite.config.ts`.

## Command reference

### Backend and repository commands

There is no separate Python build command or configured Python lint/format command. `uv sync` prepares the environment, and Uvicorn runs the source directly.

| Command | Description |
|---|---|
| `uv sync` | Create/update the uv environment from `pyproject.toml` and `uv.lock`, including the dev dependency group. |
| `uv lock --check` | Verify that `uv.lock` is consistent with `pyproject.toml`. |
| `docker compose up -d` | Start the local Neo4j service. |
| `uv run python -m spoilerless.app.graph.setup` | Create constraints/indexes and seed the graph. Requires Neo4j. |
| `uv run uvicorn spoilerless.app.main:app --reload` | Start the FastAPI development server with reload. |
| `uv run pytest` | Run the configured backend suite from the repository root. Some tests use the live Neo4j database. |
| `uv run pytest spoilerless/tests/test_openapi_contract.py` | Run one backend test file. |
| `uv run pytest spoilerless/tests/test_graph_api.py -k "graph_error_shapes"` | Run tests selected by name. |

Run pytest from the repository root. Some tests open root-relative files under `data/` and `docs/`, so changing the working directory to `spoilerless/` can produce misleading `FileNotFoundError` failures.

### Frontend scripts

All scripts in `frontend/package.json` are listed below.

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite development server. |
| `npm run build` | Run `tsc -b`, then create the production bundle with Vite in `frontend/dist/`. |
| `npm run lint` | Run ESLint across the frontend. |
| `npm run preview` | Serve the previously built production bundle locally. Run `npm run build` first. |
| `NODE_ENV=test CI=1 npm run test` | Run the Vitest suite once using the reliable test environment. |
| `NODE_ENV=test npm run test` | Run Vitest interactively in watch mode. |
| `NODE_ENV=test CI=1 npm run test -- src/components/detail/DetailPanel.test.tsx` | Run one frontend test file. |
| `NODE_ENV=test CI=1 npm run test -- -t "test name"` | Run frontend tests matching a name. |

Set `NODE_ENV=test` explicitly in Git Bash. If the shell inherited `NODE_ENV=production`, React can load production behavior and produce misleading Vitest failures. See [TESTING.md](TESTING.md) for the test-environment and shared-Neo4j precautions. Do not infer that the current checkout is green from this document; record the commands and results you actually run.

`npm run lint` is configured but may report existing React Hooks and TypeScript findings. Establish the current baseline and do not add new findings.

## Architecture and change workflows

### Backend layers and rationale

Keep dependencies flowing `spoilerless/app/api/` → `spoilerless/app/services/` → `spoilerless/app/repository/` or `spoilerless/app/graph/`. Shared Pydantic request/response contracts belong in `spoilerless/app/domain/`. This keeps HTTP concerns out of graph access, makes service policy testable, and keeps spoiler filtering at the query boundary rather than in presentation code.

`spoilerless/app/cache/` is a cross-cutting infrastructure module, not part of that request-handling chain. `spoilerless/app/cache/redis_client.py` exposes the one shared `redis.asyncio` client (`get_redis()`); `spoilerless/app/services/rate_limit.py` and `spoilerless/app/cache/graph_cache.py` both build on it. Routes call the cache/rate-limit helpers directly rather than going through the service layer. Both features are guarded on a non-empty `REDIS_URL` and fail open (never raise) on a Redis error, so Redis is a performance/protection layer, never a hard dependency. See [CONFIGURATION.md](CONFIGURATION.md#rate-limiting--redis-cache) for the full behavior.

When adding or changing an endpoint:

1. Add or update the domain model under `spoilerless/app/domain/`; preserve strict validation such as `extra="forbid"` where the surrounding contract uses it.
2. Add parameterized Cypher to the owning repository/graph module. Never interpolate client input into Cypher.
3. Put orchestration, authorization decisions, spoiler-boundary derivation, and conflict rules in the service layer.
4. Add the route under `spoilerless/app/api/` and register a new router in `spoilerless/app/main.py`.
5. Add focused tests. For story-sensitive reads, test visible data **and** forbidden future sentinels, hidden-versus-missing behavior, invalid boundaries, graph closure, and sanitized errors.
6. Keep the closed API inventory synchronized. `spoilerless/tests/test_frontend_contract_doc.py` currently locks 44 operations across 32 path templates; route changes require updates to that test, `spoilerless/tests/test_openapi_contract.py`, and `docs/frontend-api-contract.md`.
7. If the new/changed route writes graph content that `GET /api/series/{series_id}/graph` could return, call `await invalidate_series(series_id)` from `spoilerless/app/cache/graph_cache.py` after the write, following the existing pattern in `spoilerless/app/api/candidates.py`, `spoilerless/app/api/change_set.py`, and `spoilerless/app/api/user_content.py`. Invalidation is coarse (whole series) by design; do not try to target a single cache key.
8. If the new/changed route is a login, chat-send, or content-write style endpoint, add the matching dependency from `spoilerless/app/services/rate_limit.py` (`login_rate_limiter`, `chat_send_rate_limiter`, or `content_write_rate_limiter`) rather than inventing a new limiter instance.

The graph and GraphRAG paths must enforce `visible_from_order <= visible_until_order` before data reaches the frontend or model. Candidate review is the explicit exception: candidate list filtering is optional and candidate detail has no watch-boundary argument. Do not generalize that exception to other endpoints.

### Frontend contribution pattern

For a backend-facing feature, keep these layers synchronized:

1. Wire-format types in `frontend/src/types/`.
2. Fetch/streaming logic in `frontend/src/api/`; current clients use relative `/api` paths (the declared `VITE_API_BASE_URL` is not consumed).
3. Stateful orchestration in `frontend/src/hooks/` when behavior is reused or asynchronous.
4. UI in the relevant `frontend/src/components/` area, with integration wiring in `frontend/src/App.tsx` only when application state must coordinate it.
5. Colocated Vitest/Testing Library tests, plus an `App.test.tsx` integration test when props or behavior cross several component layers.

Graph mutation success paths use `useGraph.refresh()` for in-place data updates; `refetch()` is reserved for error recovery because it resets loading state and remounts the graph. Create flows that need to bring a new element into view must also clear stale chat focus and pass reveal IDs to `GraphCanvas`; a bare refresh can leave the item outside the active viewport. Preserve the `NODE_ENV=test` requirement and the browser shims in `frontend/src/test/setup.ts` when adding React/Radix/graph tests.

### Ontology, seed, chat, and ChangeSet changes

- Ontology labels and enums come from `ontology/node_types.yaml`, `ontology/relation_types.yaml`, and `ontology/claim_types.yaml`; do not invent an ad hoc relationship label. Coordinate ontology changes with seed validation, domain/frontend enums, graph styles, and tests.
- Seed records under `data/dexter/` need stable string IDs and correct visibility metadata. The setup module is idempotent by design, but it writes the configured Neo4j database; do not run it against irreplaceable data without a backup.
- Retrieval tools in `spoilerless/app/retrieval/tools.py` accept typed, allowlisted arguments and reuse the server-resolved spoiler boundary. Register tools in `spoilerless/app/retrieval/pipeline.py`; never expose free-form Cypher to the model.
- A new ChangeSet operation must remain a strict discriminated operation in `spoilerless/app/domain/change_set.py`, gain propose-time validation in `spoilerless/app/services/change_set.py`, transactional apply/revert behavior in `spoilerless/app/graph/change_set.py`, rendering in `frontend/src/components/chat/ChangeSetCard.tsx`, and confirmation/revision/protection tests.

## Code style

### Python

- Target Python `>=3.13` and use type annotations throughout backend code.
- Most backend modules use `from __future__ import annotations` and absolute imports such as `from spoilerless.app...`.
- Keep the dependency direction `api` → `services` → `repository`/`graph`; shared Pydantic contracts live in `spoilerless/app/domain/`.
- Keep Cypher parameterized. Bind values with `$parameters`; do not interpolate user-controlled values into query strings.
- Preserve the spoiler boundary at the data-access layer: story-sensitive reads must apply `visible_from_order <= $visible_until_order` and fail closed for hidden resources.
- `pyproject.toml` configures pytest only (`asyncio_mode = "auto"`, `testpaths = ["spoilerless/tests"]`). No Ruff, Black, isort, mypy, Pyright, or other Python lint/format configuration is committed.

### TypeScript and React

- `frontend/eslint.config.js` is the style configuration. It combines the recommended JavaScript and TypeScript ESLint rules with `eslint-plugin-react-hooks` and the Vite React Refresh rules; generated UI primitives under `src/components/ui/` have a narrow React Refresh exception.
- `frontend/tsconfig.app.json` targets ES2023, uses bundler module resolution and `react-jsx`, and enables unused-local, unused-parameter, erasable-syntax, and switch-fallthrough checks. It does not set TypeScript's `strict` option.
- `frontend/tsconfig.node.json` applies equivalent checks to `vite.config.ts` with NodeNext modules.
- Use the `@/` alias for imports rooted at `frontend/src/`; the alias is configured in TypeScript and Vite.
- Prefer functional React components and hooks. Colocate tests as `*.test.ts` or `*.test.tsx`.
- No Prettier, Biome, or EditorConfig configuration is committed, and `package.json` has no format script. Match surrounding files rather than claiming an automated formatter.

## Test and data safety

Backend integration tests use the same default local Neo4j database as the application. They can seed data, create scratch records, and clean records up during teardown.

- Do not point the test suite at a database containing irreplaceable data.
- Let fixtures finish their teardown; avoid interrupting tests that are mutating the live graph.
- Tests that change shared persistent settings must back up and restore the original value. `spoilerless/tests/test_settings_api.py` demonstrates this by preserving `:AppSetting {key: 'llm'}` and restoring it with a fresh driver/event loop.
- Use a context-managed FastAPI `TestClient` when a test accesses the async Neo4j driver so requests remain on one portal event loop.
- See [TESTING.md](TESTING.md) for framework details, test-writing patterns, and the complete safety guidance.

## Branch conventions

The default and only currently tracked branch is `main`.

No branch-naming convention is documented in a contribution guide or pull-request template. Recent merged history uses descriptive prefixes such as `feature/spoiler-safe-graphrag-agent`, `feature/google-auth`, and `fix/pages-build-and-landing-refresh`; these are observed examples, not an enforced policy.

Commit history commonly uses scoped prefixes such as `feat`, `fix`, `test`, `docs`, and `chore`, but no formal commit-message standard is documented.

## Pull request process

There is no committed `CONTRIBUTING.md` or `.github/PULL_REQUEST_TEMPLATE.md`, so the repository does not define required branch names, checklist items, or approvals. However, a GitHub Actions workflow (`ci.yml`) is configured to enforce automated PR gates.

For a pull request against `main`:

- Create a focused branch from an up-to-date `main`; use a descriptive name and follow the observed `feature/` or `fix/` style when it fits.
- Keep backend API, frontend types/clients, tests, and documentation synchronized. API inventory changes must also update the OpenAPI contract tests and `docs/frontend-api-contract.md`.
- Run the relevant focused backend tests first. Run the broad backend suite only against a disposable or explicitly test-only Neo4j database because it is not isolated from the configured database. Also run `NODE_ENV=test CI=1 npm run test` and `npm run build`; run `npm run lint` and ensure your change adds no new findings relative to the existing baseline.
- Push the branch and open a GitHub pull request targeting `main`. Describe the behavior change, database/configuration impact, and exact verification commands and results.
- Ensure the CI workflow passes. The workflow automatically runs backend tests against a clean Neo4j instance, verifies no database pollution occurs, and runs frontend builds, lints, and audits.
