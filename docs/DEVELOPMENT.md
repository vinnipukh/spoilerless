<!-- generated-by: gsd-doc-writer -->
# Development

This guide covers local development for the FastAPI/Neo4j backend and the React/TypeScript frontend. Run backend and repository-wide commands from the repository root unless a command explicitly changes into `frontend/`.

Backend code lives under `spoilerless/app/` (packages `api/`, `domain/`, `graph/`, `repository/`, `retrieval/`, `services/`, `llm/`, `core/`, `spoiler/`, `revisions/`, plus the cross-cutting `cache/`), with the FastAPI application assembled in `spoilerless/app/main.py`. The import root is `spoilerless.app.*` — the codebase was renamed from `backend/` to `spoilerless/` (2026-08-05), so do not reintroduce `backend.app.*` imports or paths.

## Local setup

### Prerequisites

- Python `>=3.13` (declared in `pyproject.toml`; `.python-version` pins `3.13`)
- [uv](https://docs.astral.sh/uv/) for Python dependency and environment management
- Node.js `^22.22.2`, `^24.15.0`, or `>=26.0.0`. Vite 8 itself accepts older versions, but the committed `jsdom@30.0.1` lockfile dependency imposes this stricter range; CI uses Node 24.
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

1. Create the root environment file (PROB-30/#55 — runtime configuration is
   loaded from this file):

   ```bash
   cp .env.example .env
   ```

2. The template's `NEO4J_PASSWORD=change-me` matches the fallback in `docker-compose.yml`. If you choose another password, use the same value in the root `.env` before creating the container — and note that the test environment pins its own password (see the next section). Set `GOOGLE_CLIENT_ID` if you need to sign in.
3. `VITE_GOOGLE_CLIENT_ID` also lives in the root `.env` (same Google OAuth client ID as `GOOGLE_CLIENT_ID`) — `frontend/vite.config.ts` loads the root `.env` via `envDir: '..'` and only exposes `VITE_`-prefixed vars to the browser. The committed `frontend/.env.example` is a frontend-specific reference template retained for deployment guidance; Vite ignores package-local env files because `envDir` points to the repository root, so do not copy it to `frontend/.env`. **Blank or remove the root template's `VITE_API_BASE_URL=/api` for local development:** API call sites (`frontend/src/api/client.ts`, `chat.ts`, `export.ts`) already include `/api`, so `/api` as a prefix produces `/api/api/...`. Use an origin such as `https://api.example.com` only when the backend is hosted separately.
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

`pyproject.toml` declares an `spoilerless-setup` console script, but this checkout is not installed as a package by the current uv environment, so the module invocation above is the reliable seed command. CI uses the same `uv run --project spoilerless python -m spoilerless.app.graph.setup` form; the project file itself lives at the repository root.

The compose file pins `neo4j:2026.06.0-community` (the same tag CI uses) and names the container `spoilerless-neo4j`. Its `NEO4J_AUTH` falls back to the template password `change-me`, **but the test environment pins a different password**: `scripts/env-local.sh` exports `NEO4J_PASSWORD=hdgraf-local-password`, so a container created with the fallback password will reject test connections. Create the container with the test password so one local DB serves both the app and the test suite:

```bash
NEO4J_PASSWORD=hdgraf-local-password docker compose up -d
```

(or set `NEO4J_PASSWORD=hdgraf-local-password` in the root `.env` before the first `up`). On this machine the fast test loop historically used the pre-existing `hdgraf-neo4j` container (neo4j:5-community, created with the env-local.sh credentials — see the ELEVENTH PASS note in `docs/PROBLEMS.md`); after a reboot, `docker start hdgraf-neo4j` brings it back without Compose.

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
| `docker compose up -d` | Start the local Neo4j service (see the password note under Local setup). |
| `uv run --project spoilerless python -m spoilerless.app.graph.setup` | Create constraints/indexes and seed the graph. Requires Neo4j. This is the form used by CI and the repository docs. |
| `uv run uvicorn spoilerless.app.main:app --reload` | Start the FastAPI development server with reload. |
| `source scripts/env-local.sh && unset PYTHONPATH && uv run pytest` | Run the configured backend suite (`testpaths = ["spoilerless/tests"]` in root `pyproject.toml`) against the local docker Neo4j. |
| `uv run pytest spoilerless/tests/test_openapi_contract.py` | Run one backend test file. |
| `uv run pytest spoilerless/tests/test_graph_api.py -k "graph_error_shapes"` | Run tests selected by name. |

Run pytest from the repository root. Some tests open root-relative files under `data/` and `docs/`, so changing the working directory to `spoilerless/` can produce misleading `FileNotFoundError` failures.

`scripts/env-local.sh` exports `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` for the local docker container; source it before backend test runs that need the graph. **Unset `PYTHONPATH` in the same command**: host or agent shells can inject a site-packages path that outranks the interpreter `uv run` selected, so imports resolve from the wrong environment. If imports resolve outside the project `.venv`, inspect `uv run python -c "import sys; print(sys.executable); print(sys.path)"` before changing any dependency.

The full suite mixes unit, contract, and live-Neo4j integration tests without marker groups. Prefer focused files first; run the broad suite only against the local docker database or an explicitly disposable one (see Test and data safety). CI runs the full suite against a fresh Neo4j service.

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

Set `NODE_ENV=test` explicitly in Git Bash. If the shell inherited `NODE_ENV=production`, React can load production behavior and produce misleading Vitest failures. `CI=1` forces the non-watch, single-run mode (`--run` is the equivalent flag). See [TESTING.md](TESTING.md) for the test-environment and shared-Neo4j precautions. Do not infer that the current checkout is green from this document; record the commands and results you actually run.

`npm run build` is the canonical TypeScript check as well as the production build: plain `tsc --noEmit` on the solution tsconfig skips the referenced projects, so test-file type errors surface only in `tsc -b`.

`npm run lint` is configured and currently exits successfully with no warnings or errors. The ESLint configuration keeps three React Hooks rules and test-file `no-explicit-any` at warning severity; preserve the clean output rather than treating those warning-level rules as permission to add findings.

## Architecture and change workflows

### Backend layers and rationale

Keep dependencies flowing `spoilerless/app/api/` → `spoilerless/app/services/` → `spoilerless/app/repository/` or `spoilerless/app/graph/`. Shared Pydantic request/response contracts belong in `spoilerless/app/domain/`. This keeps HTTP concerns out of graph access, makes service policy testable, and keeps spoiler filtering at the query boundary rather than in presentation code.

`spoilerless/app/cache/` is a cross-cutting infrastructure module, not part of that request-handling chain. `spoilerless/app/cache/redis_client.py` exposes the one shared `redis.asyncio` client (`get_redis()`); `spoilerless/app/services/rate_limit.py` and `spoilerless/app/cache/graph_cache.py` both build on it. Routes call the cache/rate-limit helpers directly rather than going through the service layer. Both features are disabled when `REDIS_URL` is empty. Graph-cache reads, writes, and invalidation catch Redis errors and fail open to Neo4j, but rate limiting is not fully fail-open: errors from `RedisBucket.init()` during startup or `limiter.try_acquire_async()` during a request can propagate. See [CONFIGURATION.md](CONFIGURATION.md#rate-limiting--redis-cache) for the full behavior.

When adding or changing an endpoint:

1. Add or update the domain model under `spoilerless/app/domain/`; preserve strict validation such as `extra="forbid"` where the surrounding contract uses it.
2. Add parameterized Cypher to the owning repository/graph module. Never interpolate client input into Cypher.
3. Put orchestration, authorization decisions, spoiler-boundary derivation, and conflict rules in the service layer.
4. Add the route under `spoilerless/app/api/` and register a new router in `spoilerless/app/main.py`.
5. Add focused tests. For story-sensitive reads, test visible data **and** forbidden future sentinels, hidden-versus-missing behavior, invalid boundaries, graph closure, and sanitized errors.
6. Keep the closed API inventory synchronized. `spoilerless/tests/test_frontend_contract_doc.py` currently locks 50 operations across 37 path templates; route changes require updates to that test and [frontend-api-contract.md](frontend-api-contract.md). `spoilerless/tests/test_openapi_contract.py` is currently **stale** — it still asserts 32 path templates rather than the live 37 and assumes every `DELETE` returns 204 — so update it as part of the next route-contract change, but do not cite it as a passing gate until it is synchronized (CONTRIBUTING.md "API changes" states the same).
7. If the new/changed route writes graph content that `GET /api/series/{series_id}/graph` could return, call `await invalidate_series(series_id)` from `spoilerless/app/cache/graph_cache.py` after the write, following the existing pattern in `spoilerless/app/api/candidates.py`, `spoilerless/app/api/change_set.py`, and `spoilerless/app/api/user_content.py`. Invalidation is coarse (whole series) by design; do not try to target a single cache key.
8. If the new/changed route is a login, chat-send, or content-write style endpoint, add the matching dependency from `spoilerless/app/services/rate_limit.py` (`login_rate_limiter`, `chat_send_rate_limiter`, or `content_write_rate_limiter`) rather than inventing a new limiter instance.

The graph and GraphRAG paths must enforce `visible_from_order <= visible_until_order` before data reaches the frontend or model. Both candidate list and candidate detail reads also require `visible_until_order`; the server returns 422 when it is omitted or does not identify a persisted episode order for the series, and the repository applies the resolved boundary to candidate visibility.

### Frontend contribution pattern

For a backend-facing feature, keep these layers synchronized:

1. Wire-format types in `frontend/src/types/`.
2. Fetch/streaming logic in `frontend/src/api/`; `client.ts`, `chat.ts`, and `export.ts` prepend `VITE_API_BASE_URL` (empty by default) to paths that already begin with `/api`.
3. Stateful orchestration in `frontend/src/hooks/` when behavior is reused or asynchronous.
4. UI in the relevant `frontend/src/components/` area, with integration wiring in `frontend/src/App.tsx` only when application state must coordinate it.
5. Colocated Vitest/Testing Library tests, plus an `App.test.tsx` integration test when props or behavior cross several component layers.

Graph mutation success paths use `useGraph.refresh()` for in-place data updates; `refetch()` is reserved for error recovery because it resets loading state and remounts the graph. Create flows that need to bring a new element into view must also clear stale chat focus and pass reveal IDs to `GraphCanvas`; a bare refresh can leave the item outside the active viewport. Preserve the `NODE_ENV=test` requirement and the browser shims in `frontend/src/test/setup.ts` when adding React/Radix/graph tests.

The current frontend baseline is React `^19.2.7`, TypeScript `~6.0.2`, Vite `^8.1.1`, Vitest `^4.1.10`, Tailwind CSS `^4.3.3`, Cytoscape `^3.34.0`, and jsdom `^30.0.1`. Read `frontend/package.json` rather than copying versions into new package declarations; `package-lock.json` is the reproducible install source used by CI (`npm ci`).

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
- `pyproject.toml` configures pytest only (`pytest>=9.1.1`, `pytest-asyncio>=1.4.0`, `asyncio_mode = "auto"`, `testpaths = ["spoilerless/tests"]`). No Ruff, Black, isort, mypy, Pyright, or other Python lint/format configuration is committed, so `uv lint`/`uv fmt` have nothing to run; follow the conventions above by hand.

### TypeScript and React

- `frontend/eslint.config.js` is the style configuration. It combines the recommended JavaScript and TypeScript ESLint rules with `eslint-plugin-react-hooks` and the Vite React Refresh rules; generated UI primitives under `src/components/ui/` have a narrow React Refresh exception.
- `frontend/tsconfig.app.json` targets ES2023, uses bundler module resolution and `react-jsx`, and enables unused-local, unused-parameter, erasable-syntax, and switch-fallthrough checks. It does not set TypeScript's `strict` option.
- `frontend/tsconfig.node.json` applies equivalent checks to `vite.config.ts` with NodeNext modules.
- Use the `@/` alias for imports rooted at `frontend/src/`; the alias is configured in TypeScript and Vite.
- Prefer functional React components and hooks. Colocate tests as `*.test.ts` or `*.test.tsx`.
- No Prettier, Biome, or EditorConfig configuration is committed, and `package.json` has no format script. Match surrounding files rather than claiming an automated formatter.

## Test and data safety

Backend integration tests use the same default local Neo4j database as the application. They can seed data, create scratch records, and clean records up during teardown.

- Point tests at the local docker Neo4j (`source scripts/env-local.sh && unset PYTHONPATH && uv run pytest ...`) unless you deliberately target the shared AuraDB instance (credentials `aura_username`/`aura_password` in the root `.env`). **Never run the suite concurrently against the shared AuraDB** — overlapping suites corrupt each other's fixtures and the seed audit; the ELEVENTH PASS in `docs/PROBLEMS.md` ran entirely on the local docker container for this reason.
- Do not point the test suite at a database containing irreplaceable data.
- Let fixtures finish their teardown; avoid interrupting tests that are mutating the live graph. An aborted full run leaves residue that breaks later seed-idempotency/candidate tests; reseed (`uv run --project spoilerless python -m spoilerless.app.graph.setup`) before the next full run.
- Tests that change shared persistent settings must back up and restore the original value. `spoilerless/tests/test_settings_api.py` demonstrates this by preserving `:AppSetting {key: 'llm'}` and restoring it with a fresh driver/event loop.
- Use a context-managed FastAPI `TestClient` when a test accesses the async Neo4j driver so requests remain on one portal event loop.
- See [TESTING.md](TESTING.md) for framework details, test-writing patterns, and the complete safety guidance.

## GSD workflow conventions

Development follows the GSD (Git. Ship. Done.) planning workflow used in this repository:

- Planning artifacts live under `.planning/` — `ROADMAP.md`, `STATE.md`, `phases/` (current: `08-production-deployment-automated-ci-cd`, `09-feature-expansion-full-audit-remediation`), and `milestones/`. Phase work is executed from the plan files in the phase directories, and each executed phase produces a verification summary.
- **`docs/PROBLEMS.md` is the canonical issue ledger** — findings and fixes are tracked there in numbered passes instead of a GitHub issue tracker (ELEVENTH PASS, 2026-08-11, is the newest). Read it before claiming anything about deployment readiness or known-issue state, and check the newest pass for current paths — early passes cite the old `backend/app/...` layout.
- Commits are atomic: one focused change per commit, with explicit staging (never `git add .`). House style uses scoped, conventional-style prefixes (`feat(...)`, `fix(...)`, `test(...)`, `docs(...)`); GSD plan execution additionally uses dated RED/GREEN/SUMMARY markers such as `test(06-02): ...`, `feat(06-02): ...`, `docs(06): ...`.
- Never stage `.planning/config.json` (it is tracked but sits perpetually dirty — check `git status --short` before staging). Do not commit `.env`, local database artifacts, or build output.
- The house expectation is to commit and push finished, verified changes immediately rather than accumulating uncommitted work.

## Branch conventions

`main` is the default branch and the only branch advertised by the `origin` remote. [CONTRIBUTING.md](../CONTRIBUTING.md#branches-and-commits) documents the house conventions:

- Create a focused branch from an up-to-date `main`. External contributors work from a fork; collaborators may use a repository branch. There is no enforced branch-name policy or pull-request template, but descriptive names such as `feature/...` or `fix/...` fit the observed history (`feature/spoiler-safe-graphrag-agent`, `feature/google-auth`, `feature/character-images`, `feature/graph-visual-overhaul`, `fix/pages-build-and-landing-refresh`).
- Commits commonly use concise conventional-style prefixes — `feat`, `fix`, `test`, `docs` — optionally scoped (`feat(graph): add visible path highlighting`). This is an observed house style rather than a mechanically enforced standard; keep commits reviewable and avoid unrelated churn.

This checkout additionally has a local `quick/dexter-s01e01-enrichment` branch; that is local state, not a contributor requirement.

## Pull request process

Contribution guidance is provided in [CONTRIBUTING.md](../CONTRIBUTING.md). There is no committed `.github/PULL_REQUEST_TEMPLATE.md`, so the repository does not define required PR template checklists or approvals; CONTRIBUTING.md's "Pull Request Checklist" documents the expected process, and a GitHub Actions workflow (`ci.yml`) enforces automated PR gates.

For a pull request against `main`:

- Create a focused branch from an up-to-date `main`; use a descriptive name and follow the observed `feature/` or `fix/` style when it fits.
- Keep backend API, frontend types/clients, tests, and documentation synchronized. API inventory changes must also update the OpenAPI contract tests and `docs/frontend-api-contract.md` (see the staleness note under Architecture and change workflows).
- Run the relevant focused backend tests first. Run the broad backend suite only against a disposable or explicitly test-only Neo4j database because it is not isolated from the configured database. Also run `NODE_ENV=test CI=1 npm run test` and `npm run build`; run `npm run lint` and preserve its current zero-warning, zero-error result.
- Push the branch and open a GitHub pull request targeting `main`. Describe the behavior change, spoiler-safety and auth/data-migration effects, database/configuration impact, and the exact verification commands and results.
- Ensure the CI workflow passes. `ci.yml` runs **on pull requests only** — a direct push to `main` does not trigger it. The backend job runs `uv sync --frozen`, graph setup, the full pytest suite against an ephemeral Neo4j service, and a database-pollution gate that fails if any `series_scratch*` or `origin='candidate'` residue remains. The frontend job runs `npm ci`, `npm run build`, `npm run lint`, and `npm audit --audit-level=high`. CI does **not** run Vitest, so a green pull request does not replace the required local frontend test run.
