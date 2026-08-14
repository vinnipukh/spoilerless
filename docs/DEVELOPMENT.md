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
- Redis is optional for local development. `docker-compose.yml` only runs Neo4j; leaving `REDIS_URL` unset in `.env` disables the Redis-backed rate limiter, the graph response cache, and the visualization projection cache (`spoilerless/app/cache/`) without breaking anything else. See [CONFIGURATION.md](CONFIGURATION.md#rate-limiting--redis-cache) to enable them against Upstash or another Redis instance.

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
npm install --include=dev
cd ..
```

`pyproject.toml` declares an `spoilerless-setup` console script, but this checkout is not installed as a package by the current uv environment, so the module invocation above is the reliable seed command. CI uses the same `uv run --project spoilerless python -m spoilerless.app.graph.setup` form; the project file itself lives at the repository root.

Use `npm install --include=dev` (or `npm ci`, which installs everything from the lockfile) rather than a bare `npm install`: this machine's global `npm config set omit=dev` makes plain `npm install` silently skip devDependencies — including Vitest, ESLint, and TypeScript — which surfaces as missing binaries later. On a machine without that global setting, plain `npm install` is fine. <!-- VERIFY: the global `omit=dev` npm setting is operator-machine state observed on this machine, not a repository or CI setting -->

The compose file pins `neo4j:2026.06.0-community` (the same tag CI uses) and names the container `spoilerless-neo4j`. Its `NEO4J_AUTH` falls back to the template password `change-me`, **but the test environment pins a different password**: `scripts/env-local.sh` exports `NEO4J_PASSWORD=hdgraf-local-password`, so a container created with the fallback password will reject test connections. Create the container with the test password so one local DB serves both the app and the test suite:

```bash
NEO4J_PASSWORD=hdgraf-local-password docker compose up -d
```

(or set `NEO4J_PASSWORD=hdgraf-local-password` in the root `.env` before the first `up`). Note that the guarded full-suite runner (see [Test and data safety](#test-and-data-safety)) refuses to run while `spoilerless-neo4j` or the legacy `hdgraf-neo4j` container is running — stop them before a full-suite run.

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
| `source scripts/env-local.sh && unset PYTHONPATH && uv run pytest spoilerless/tests/<file>` | Run focused backend test files against the local docker Neo4j (configured suite: `testpaths = ["spoilerless/tests"]` in root `pyproject.toml`). |
| `uv run python scripts/run_phase10_backend_tests.py` | Run the **full** backend suite in 11 chunks against a disposable ephemeral Neo4j container (fail-closed guard; see Test and data safety). |
| `uv run python scripts/run_phase10_backend_tests.py --files spoilerless/tests/test_graph_api.py` | Run selected test files on the ephemeral guarded target instead of all chunks. |
| `uv run pytest spoilerless/tests/test_graph_api.py -k "graph_error_shapes"` | Run tests selected by name (database-free or against local docker). |

Run pytest from the repository root. Some tests open root-relative files under `data/` and `docs/`, so changing the working directory to `spoilerless/` can produce misleading `FileNotFoundError` failures.

`scripts/env-local.sh` exports `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, and `NEO4J_DATABASE` for the local docker container; source it before backend test runs that need the graph. **Unset `PYTHONPATH` in the same command**: host or agent shells can inject a site-packages path that outranks the interpreter `uv run` selected, so imports resolve from the wrong environment. If imports resolve outside the project `.venv`, inspect `uv run python -c "import sys; print(sys.executable); print(sys.path)"` before changing any dependency.

The full suite mixes unit, contract, and live-Neo4j integration tests without marker groups (the only declared pytest marker is `benchmark`, for the in-memory visualization benchmark harness). The full suite now runs **only** through `scripts/run_phase10_backend_tests.py`, which provisions its own disposable container and refuses shared/live targets — do not run the broad suite against local docker or AuraDB (see Test and data safety). CI runs the full suite against a fresh Neo4j service.

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

`npm run lint` is configured and is expected to exit successfully with no warnings or errors. <!-- VERIFY: `npm run lint` exits successfully with no warnings or errors (runtime state, not verifiable from source) --> The ESLint configuration keeps three React Hooks rules and test-file `no-explicit-any` at warning severity; preserve the clean output rather than treating those warning-level rules as permission to add findings.

## Architecture and change workflows

### Backend layers and rationale

Keep dependencies flowing `spoilerless/app/api/` → `spoilerless/app/services/` → `spoilerless/app/repository/` or `spoilerless/app/graph/`. Shared Pydantic request/response contracts belong in `spoilerless/app/domain/`. This keeps HTTP concerns out of graph access, makes service policy testable, and keeps spoiler filtering at the query boundary rather than in presentation code.

`spoilerless/app/cache/` is a cross-cutting infrastructure module, not part of that request-handling chain. `spoilerless/app/cache/redis_client.py` exposes the one shared `redis.asyncio` client (`get_redis()`); `spoilerless/app/services/rate_limit.py` and `spoilerless/app/cache/graph_cache.py` both build on it. Routes call the cache/rate-limit helpers directly rather than going through the service layer. All three features are disabled when `REDIS_URL` is empty. Graph-cache and visualization-cache reads, writes, and invalidation catch Redis errors and fail open to Neo4j; rate limiting is fully fail-open in both paths: errors from `RedisBucket.init()` during startup and `limiter.try_acquire_async()` during a request are caught, logged, and degrade to a no-op rather than propagating (PROB-23, SEVENTEENTH PASS). See [CONFIGURATION.md](CONFIGURATION.md#rate-limiting--redis-cache) for the full behavior.

The graph cache now covers both `GET /api/series/{series_id}/graph` and the Phase 10 typed visualization projection `GET /api/series/{series_id}/graph/visualization` (both live in `spoilerless/app/api/graph.py`). Cache keys embed the effective spoiler boundary and the requesting user, so a boundary change alone always misses correctly; `invalidate_series()` is the explicit coarse-grained invalidation for writes at a fixed boundary. Visualization keys additionally carry view type and projection version, and cached DTOs are re-validated against their metadata on read, so a stale or poisoned entry is never served. `GET /api/series/{series_id}/graph/expand` (allowlisted semantic expansion) is also defined in `spoilerless/app/api/graph.py`.

When adding or changing an endpoint:

1. Add or update the domain model under `spoilerless/app/domain/`; preserve strict validation such as `extra="forbid"` where the surrounding contract uses it.
2. Add parameterized Cypher to the owning repository/graph module. Never interpolate client input into Cypher.
3. Put orchestration, authorization decisions, spoiler-boundary derivation, and conflict rules in the service layer.
4. Add the route under `spoilerless/app/api/` and register a new router in `spoilerless/app/main.py`.
5. Add focused tests. For story-sensitive reads, test visible data **and** forbidden future sentinels, hidden-versus-missing behavior, invalid boundaries, graph closure, and sanitized errors.
6. Keep the closed API inventory synchronized. The OpenAPI surface is currently locked at **52 operations over 39 path templates** by `spoilerless/tests/test_frontend_contract_doc.py` and `spoilerless/tests/test_openapi_contract.py` (both assert the full path/method sets and the exact counts); route changes require updates to both tests and to [frontend-api-contract.md](reference/frontend-api-contract.md). The two tests are synchronized with each other and with the live app — keep them that way.
7. If the new/changed route writes graph content that `GET /api/series/{series_id}/graph` or the visualization projection could return, call `await invalidate_series(series_id)` from `spoilerless/app/cache/graph_cache.py` after the write, following the existing pattern in `spoilerless/app/api/candidates.py`, `spoilerless/app/api/change_set.py`, and `spoilerless/app/api/user_content.py`. Invalidation is coarse (whole series) by design; do not try to target a single cache key.
8. If the new/changed route is a login, chat-send, or content-write style endpoint, add the matching dependency from `spoilerless/app/services/rate_limit.py` (`login_rate_limiter`, `chat_send_rate_limiter`, or `content_write_rate_limiter`) rather than inventing a new limiter instance.
9. If the new/changed route is a state-changing route authenticated by cookie, declare the shared CSRF origin guard — `CsrfGuardDependency` from `spoilerless/app/api/deps.py` (re-exported by `api/auth.py`), conventionally injected as `_csrf` — so `Origin`/`Referer` is validated against `FRONTEND_ORIGINS` and requests with neither header fail closed (403 `AUTH_ORIGIN_NOT_ALLOWED`). `SameSite=Lax` on the session cookie is complementary, not sufficient.

The graph and GraphRAG paths must enforce `visible_from_order <= visible_until_order` before data reaches the frontend or model. Both candidate list and candidate detail reads also require `visible_until_order`; the server returns 422 when it is omitted or does not identify a persisted episode order for the series, and the repository applies the resolved boundary to candidate visibility.

### Frontend contribution pattern

For a backend-facing feature, keep these layers synchronized:

1. Wire-format types in `frontend/src/types/`.
2. Fetch/streaming logic in `frontend/src/api/`; `client.ts`, `chat.ts`, and `export.ts` prepend `VITE_API_BASE_URL` (empty by default) to paths that already begin with `/api`.
3. Stateful orchestration in `frontend/src/hooks/` when behavior is reused or asynchronous.
4. UI in the relevant `frontend/src/components/` area, with integration wiring in `frontend/src/App.tsx` only when application state must coordinate it.
5. Colocated Vitest/Testing Library tests, plus an `App.test.tsx` integration test when props or behavior cross several component layers.

Graph mutation success paths use `useGraph.refresh()` for in-place data updates; `refetch()` is reserved for error recovery because it resets loading state and remounts the graph. Create flows that need to bring a new element into view must also clear stale chat focus and pass reveal IDs to `GraphCanvas`; a bare refresh can leave the item outside the active viewport. Preserve the `NODE_ENV=test` requirement and the browser shims in `frontend/src/test/setup.ts` when adding React/Radix/graph tests.

The Phase 10 visualization redesign keeps Cytoscape element mutation behind the reconciler module `frontend/src/components/graph/cytoscapeReconciler.ts` (consumed by `GraphCanvas.tsx`): it diffs incoming wire data against the live cytoscape state so layout runs, style updates, and element removal happen only when the underlying data actually changed. Keep new graph features wired through the reconciler rather than mutating cytoscape instances directly, and exercise the layout engines (dagre, fcose, cose-bilkent) that drive the projection views.

The current frontend baseline is React `^19.2.7`, TypeScript `~6.0.2`, Vite `^8.1.1`, Vitest `^4.1.10`, Tailwind CSS `^4.3.3`, Cytoscape `^3.34.0` (with the dagre, fcose, and cose-bilkent layout packages), and jsdom `^30.0.1`. Read `frontend/package.json` rather than copying versions into new package declarations; `package-lock.json` is the reproducible install source used by CI (`npm ci`).

### Ontology, seed, chat, and ChangeSet changes

- Ontology labels and enums come from `ontology/node_types.yaml`, `ontology/relation_types.yaml`, and `ontology/claim_types.yaml`; do not invent an ad hoc relationship label. Coordinate ontology changes with seed validation, domain/frontend enums, graph styles, and tests.
- Seed records under `data/dexter/` need stable string IDs and correct visibility metadata. The setup module is idempotent by design, but it writes the configured Neo4j database; do not run it against irreplaceable data without a backup.
- Retrieval tools in `spoilerless/app/retrieval/tools.py` accept typed, allowlisted arguments and reuse the server-resolved spoiler boundary. Register tools in `spoilerless/app/retrieval/pipeline.py`; never expose free-form Cypher to the model.
- Chat supports two LLM providers through `spoilerless/app/llm/provider.py`: `openai_compatible` (the default; `vllm` and `ollama` are scaffolding that route through the same OpenAI-compatible provider) and `gemini` (Google's REST API with `x-goog-api-key` auth, where `base_url` is optional). Provider resolution is request-scoped in `spoilerless/app/services/chat.py`: `X-LLM-*` request headers (`X-LLM-Api-Key`, `X-LLM-Provider`, `X-LLM-Base-URL`, `X-LLM-Model`) enable bring-your-own-key and are never persisted or logged; without them, persisted `:AppSetting {key: 'llm'}` values win, with the `LLM_*` environment variables as the fallback tier. A disabled provider maps to HTTP 503 `LLM_DISABLED`; an unconfigured or failing provider maps to 503 `LLM_PROVIDER_UNAVAILABLE`.
- A new ChangeSet operation must remain a strict discriminated operation in `spoilerless/app/domain/change_set.py`, gain propose-time validation in `spoilerless/app/services/change_set.py`, transactional apply/revert behavior in `spoilerless/app/graph/change_set.py`, rendering in `frontend/src/components/chat/ChangeSetCard.tsx`, and confirmation/revision/protection tests.

## Code style

### Python

- Target Python `>=3.13` and use type annotations throughout backend code.
- Most backend modules use `from __future__ import annotations` and absolute imports such as `from spoilerless.app...`.
- Keep the dependency direction `api` → `services` → `repository`/`graph`; shared Pydantic contracts live in `spoilerless/app/domain/`.
- Keep Cypher parameterized. Bind values with `$parameters`; do not interpolate user-controlled values into query strings.
- Preserve the spoiler boundary at the data-access layer: story-sensitive reads must apply `visible_from_order <= $visible_until_order` and fail closed for hidden resources.
- `pyproject.toml` configures pytest only (`pytest>=9.1.1`, `pytest-asyncio>=1.4.0`, `asyncio_mode = "auto"` with module-scoped asyncio loops, `testpaths = ["spoilerless/tests"]`, plus a `benchmark` marker for the in-memory visualization benchmark harness). No Ruff, Black, isort, mypy, Pyright, or other Python lint/format configuration is committed, so `uv lint`/`uv fmt` have nothing to run; follow the conventions above by hand.

### TypeScript and React

- `frontend/eslint.config.js` is the style configuration. It combines the recommended JavaScript and TypeScript ESLint rules with `eslint-plugin-react-hooks` and the Vite React Refresh rules; generated UI primitives under `src/components/ui/` have a narrow React Refresh exception.
- `frontend/tsconfig.app.json` targets ES2023, uses bundler module resolution and `react-jsx`, and enables unused-local, unused-parameter, erasable-syntax, and switch-fallthrough checks. It does not set TypeScript's `strict` option.
- `frontend/tsconfig.node.json` applies equivalent checks to `vite.config.ts` with NodeNext modules.
- Use the `@/` alias for imports rooted at `frontend/src/`; the alias is configured in TypeScript and Vite.
- Prefer functional React components and hooks. Colocate tests as `*.test.ts` or `*.test.tsx`.
- No Prettier, Biome, or EditorConfig configuration is committed, and `package.json` has no format script. Match surrounding files rather than claiming an automated formatter.

## Test and data safety

Backend integration tests use a live Neo4j database. They can seed data, create scratch records, and clean records up during teardown.

- **Full suite:** run it only through the guarded runner — `uv run python scripts/run_phase10_backend_tests.py`. It provisions a uniquely named, ephemeral `neo4j:2026.06.0-community` container (random password, random loopback ports, no volume mounts), runs the 11-chunk suite against it, and always removes the container and its volumes. It is fail-closed: it refuses ambient `NEO4J_*`/`aura_*` overrides (so do **not** source `scripts/env-local.sh` first), remote/Aura URIs, the developer container port and the running `spoilerless-neo4j`/`hdgraf-neo4j` containers, and any pre-existing container or volume with its generated name; it also proves the effective `Settings` resolve to the ephemeral target and that the target holds 0 nodes before testing. `--files ...` runs selected files on the same guarded target. Exit codes: 0 all green, 1 test failures, 2 forbidden target/usage error. This runner retired the old seven-red local-docker baseline (NINETEENTH PASS in `docs/PROBLEMS.md`).
- **Focused tests:** database-free files run with plain `uv run pytest spoilerless/tests/<file>`. Files that touch the graph run against the local docker Neo4j with `source scripts/env-local.sh && unset PYTHONPATH && uv run pytest spoilerless/tests/<file>`. **Never run the suite concurrently against the shared AuraDB** (credentials `aura_username`/`aura_password` in the root `.env`) — overlapping suites corrupt each other's fixtures and the seed audit.
- Do not point any test run at a database containing irreplaceable data.
- Let fixtures finish their teardown; avoid interrupting tests that are mutating the live graph. An aborted full run leaves residue that breaks later seed-idempotency/candidate tests; reseed (`uv run --project spoilerless python -m spoilerless.app.graph.setup`) before the next full run.
- Tests that change shared persistent settings must back up and restore the original value. `spoilerless/tests/test_settings_api.py` demonstrates this by preserving `:AppSetting {key: 'llm'}` and restoring it with a fresh driver/event loop.
- Use a context-managed FastAPI `TestClient` when a test accesses the async Neo4j driver so requests remain on one portal event loop.
- See [TESTING.md](TESTING.md) for framework details, test-writing patterns, and the complete safety guidance.

## GSD workflow conventions

Development follows the GSD (Git. Ship. Done.) planning workflow used in this repository:

- Planning artifacts live under `.planning/` — `ROADMAP.md`, `STATE.md`, `PROJECT.md`, and `milestones/` holding per-milestone archives (`v1.1-phases`, `v1.2-phases`, `v1.3-phases`, each with its own `-REQUIREMENTS.md`/`-ROADMAP.md`). The current milestone, v1.3 (Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign, 11/11 plans), was completed and verified 2026-08-14; `.planning/quick/` holds the quick-task ledger used for smaller dated workstreams.
- **`docs/PROBLEMS.md` is the canonical issue ledger** — findings and fixes are tracked there in numbered passes instead of a GitHub issue tracker (NINETEENTH PASS, 2026-08-13, is the newest: the guarded ephemeral-container runner and the retirement of the seven-red baseline). Read it before claiming anything about deployment readiness or known-issue state, and check the newest pass for current paths — early passes cite the old `backend/app/...` layout.
- Commits are atomic: one focused change per commit, with explicit staging (never `git add .`). House style uses scoped, conventional-style prefixes (`feat(...)`, `fix(...)`, `test(...)`, `docs(...)`); GSD plan execution additionally uses dated markers such as `test(06-02): ...`, `docs(10-09): ...`, and quick-task prefixes like `feat(260814-viz): ...`.
- Never stage `.planning/config.json` (it is tracked but sits perpetually dirty — check `git status --short` before staging). Do not commit `.env`, local database artifacts, or build output.
- The house expectation is to commit and push finished, verified changes immediately rather than accumulating uncommitted work.

## Branch conventions

`main` is the default branch and the only branch advertised by the `origin` remote. [CONTRIBUTING.md](../CONTRIBUTING.md#branches-commits-and-the-issue-ledger) documents the house conventions:

- Create a focused branch from an up-to-date `main`. External contributors work from a fork; collaborators may use a repository branch. There is no enforced branch-name policy or pull-request template, but descriptive names such as `feature/...` or `fix/...` fit the observed history (`feature/spoiler-safe-graphrag-agent`, `feature/google-auth`, `feature/character-images`, `feature/graph-visual-overhaul`, `fix/pages-build-and-landing-refresh`).
- Commits commonly use concise conventional-style prefixes — `feat`, `fix`, `test`, `docs` — optionally scoped (`feat(graph): add visible path highlighting`). This is an observed house style rather than a mechanically enforced standard; keep commits reviewable and avoid unrelated churn.

## Pull request process

Contribution guidance is provided in [CONTRIBUTING.md](../CONTRIBUTING.md). There is no committed `.github/PULL_REQUEST_TEMPLATE.md`, so the repository does not define required PR template checklists or approvals; CONTRIBUTING.md's "Pull Request Checklist" documents the expected process, and a GitHub Actions workflow (`ci.yml`) enforces automated PR gates.

For a pull request against `main`:

- Create a focused branch from an up-to-date `main`; use a descriptive name and follow the observed `feature/` or `fix/` style when it fits.
- Keep backend API, frontend types/clients, tests, and documentation synchronized. API inventory changes must update the OpenAPI contract tests (`test_frontend_contract_doc.py` and `test_openapi_contract.py`) and `docs/reference/frontend-api-contract.md` (see the closed-inventory note under Architecture and change workflows).
- Run the relevant focused backend tests first. Run the full backend suite via the guarded ephemeral runner (`uv run python scripts/run_phase10_backend_tests.py`), never against the shared AuraDB or a database with irreplaceable data. Also run `NODE_ENV=test CI=1 npm run test` and `npm run build`; run `npm run lint` and preserve its current zero-warning, zero-error result.
- Push the branch and open a GitHub pull request targeting `main`. Describe the behavior change, spoiler-safety and auth/data-migration effects, database/configuration impact, and the exact verification commands and results.
- Ensure the CI workflow passes. `ci.yml` runs **on pull requests only** — a direct push to `main` does not trigger it. The backend job runs `uv sync --frozen`, graph setup, the full pytest suite against an ephemeral Neo4j service, and a database-pollution gate that fails if any `series_scratch*` or `origin='candidate'` residue remains. The frontend job runs `npm ci`, `npm run build`, `npm run lint`, and `npm audit --audit-level=high`. CI does **not** run Vitest, so a green pull request does not replace the required local frontend test run.
