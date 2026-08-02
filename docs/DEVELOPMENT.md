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

1. Create local environment files:

   ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env.local
   ```

2. In `.env`, set `NEO4J_PASSWORD=hdgraf-local-password` to match `docker-compose.yml`. Set `GOOGLE_CLIENT_ID` if you need to sign in.
3. In `frontend/.env.local`, set `VITE_GOOGLE_CLIENT_ID` to the same Google OAuth client ID. Keep `VITE_API_BASE_URL=/api`.
4. Do not commit either local environment file. See [CONFIGURATION.md](CONFIGURATION.md) for the complete setting reference.

### Install dependencies and initialize Neo4j

```bash
# Repository root
uv sync
docker compose up -d
uv run python -m backend.app.graph.setup

# Frontend dependencies
cd frontend
npm install
cd ..
```

`pyproject.toml` declares an `hdgraf-setup` console script, but this checkout is not installed as a package by the current uv environment, so the module invocation above is the reliable seed command.

### Start the development servers

Run the backend from the repository root:

```bash
uv run uvicorn backend.app.main:app --reload
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
| `uv run python -m backend.app.graph.setup` | Create constraints/indexes and seed the graph. Requires Neo4j. |
| `uv run uvicorn backend.app.main:app --reload` | Start the FastAPI development server with reload. |
| `uv run pytest` | Run the configured backend suite from the repository root. Some tests use the live Neo4j database. |
| `uv run pytest backend/tests/test_openapi_contract.py` | Run one backend test file. |
| `uv run pytest backend/tests/test_graph_api.py -k "graph_error_shapes"` | Run tests selected by name. |

Run pytest from the repository root. Some tests open root-relative files under `data/` and `docs/`, so changing the working directory to `backend/` can produce misleading `FileNotFoundError` failures.

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

Set `NODE_ENV=test` explicitly in Git Bash. If the shell inherited `NODE_ENV=production`, React can load production behavior and produce misleading Vitest failures. The one-shot command above is aligned with [TESTING.md](TESTING.md) and was verified against the current suite.

The current checkout builds successfully, with Vite's large-chunk warning, and the frontend tests pass. `npm run lint` is configured but is not currently clean: it reports existing React Hooks and TypeScript findings. Treat the existing output as technical debt and do not add new lint errors.

## Code style

### Python

- Target Python `>=3.13` and use type annotations throughout backend code.
- Most backend modules use `from __future__ import annotations` and absolute imports such as `from backend.app...`.
- Keep the dependency direction `api` → `services` → `repository`/`graph`; shared Pydantic contracts live in `backend/app/domain/`.
- Keep Cypher parameterized. Bind values with `$parameters`; do not interpolate user-controlled values into query strings.
- Preserve the spoiler boundary at the data-access layer: story-sensitive reads must apply `visible_from_order <= $visible_until_order` and fail closed for hidden resources.
- `pyproject.toml` configures pytest only (`asyncio_mode = "auto"`, `testpaths = ["backend/tests"]`). No Ruff, Black, isort, mypy, Pyright, or other Python lint/format configuration is committed.

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
- Tests that change shared persistent settings must back up and restore the original value. `backend/tests/test_settings_api.py` demonstrates this by preserving `:AppSetting {key: 'llm'}` and restoring it with a fresh driver/event loop.
- Use a context-managed FastAPI `TestClient` when a test accesses the async Neo4j driver so requests remain on one portal event loop.
- See [TESTING.md](TESTING.md) for framework details, test-writing patterns, and the complete safety guidance.

## Branch conventions

The default and only currently tracked branch is `main`.

No branch-naming convention is documented in a contribution guide or pull-request template. Recent merged history uses descriptive prefixes such as `feature/spoiler-safe-graphrag-agent`, `feature/google-auth`, and `fix/pages-build-and-landing-refresh`; these are observed examples, not an enforced policy.

Commit history commonly uses scoped prefixes such as `feat`, `fix`, `test`, `docs`, and `chore`, but no formal commit-message standard is documented.

## Pull request process

There is no committed `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`, or GitHub Actions workflow, so the repository does not define required branch names, checklist items, approvals, or automated PR gates.

For a pull request against `main`:

- Create a focused branch from an up-to-date `main`; use a descriptive name and follow the observed `feature/` or `fix/` style when it fits.
- Keep backend API, frontend types/clients, tests, and documentation synchronized. API inventory changes must also update the OpenAPI contract tests and `docs/frontend-api-contract.md`.
- Run `uv run pytest`, `NODE_ENV=test CI=1 npm run test`, and `npm run build` before opening the PR. Run `npm run lint` and ensure your change adds no new findings relative to the existing baseline.
- Push the branch and open a GitHub pull request targeting `main`. Describe the behavior change, database/configuration impact, and exact verification commands and results.
- Because no CI workflow or review policy is configured, do not assume checks ran remotely; record local evidence and wait for repository-maintainer review before merging.
