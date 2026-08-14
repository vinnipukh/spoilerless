<!-- generated-by: gsd-doc-writer -->
# Contributing to HD Graf Cehennemi

Thank you for contributing to HD Graf Cehennemi (the "Spoilerless" application). This guide describes the repository's current setup, issue-ledger workflow, quality gates, and pull-request expectations. See [Getting Started](docs/GETTING-STARTED.md) for prerequisites and first-run instructions, and [Development](docs/DEVELOPMENT.md), [Testing](docs/TESTING.md), and [Architecture](docs/ARCHITECTURE.md) for deeper implementation guidance, with the [authoritative project specification](docs/architecture/project-spec.md) as reference. The canonical issue ledger is [docs/PROBLEMS.md](docs/PROBLEMS.md) — read it before starting work, and record your work in it (see "Issue Ledger and Contribution Workflow" below).

## Code of Conduct

Be respectful, inclusive, and constructive in issues, reviews, and other project discussions. The repository does not currently include a separate `CODE_OF_CONDUCT.md`.

## Issue Ledger and Contribution Workflow

The project tracks problems and fixes in `docs/PROBLEMS.md`, not only in GitHub issues:

- `docs/PROBLEMS.md` is the canonical issue ledger. Findings are worked in numbered passes (`SECOND PASS` through `NINETEENTH PASS`); **NINETEENTH PASS (2026-08-13) is current** — append a new `## <ORDINAL> PASS — <topic> (YYYY-MM-DD)` section rather than editing earlier ones. Earlier passes are the audit trail; do not rewrite or renumber them.
- Each problem is tracked by a number (`#61`, `#77`, ...). Each fix lands as **one atomic commit per problem number**, with the message referencing the ledger number as `PROB-09/#NN` — for example `fix(graph): single series-id source — switchSeries moves watch-progress series (PROB-09/#61)`.
- Documentation commits that record a pass use the form `docs(08-13): NINETEENTH PASS — <summary>`. A pass that fixes problems should be closed by updating the ledger, one commit per fix, plus a `docs(...)` commit for the pass notes.
- The full-suite baseline is **zero known failures** (see "Testing and Quality Gates") — never "fix" unrelated failures as part of another change, and any failure your change introduces is a regression.

## Before You Start

- Search existing GitHub issues (https://github.com/vinnipukh/hdgrafcehennemi/issues) and pull requests before opening a duplicate.
- Keep a contribution focused. Discuss large scope changes before implementing them, especially new infrastructure, ingestion pipelines, data-model changes, or changes to spoiler-safety rules.
- Never commit credentials, `.env` files, database exports, copyrighted scripts/subtitles, or provider API keys.
- Use a disposable or explicitly test-only Neo4j database for integration tests. The backend suite is not automatically isolated from the database named by your `NEO4J_*` settings; the Phase 10 guarded runner provisions its own ephemeral container (see "Testing and Quality Gates").
- When tests touch the live/graph database, follow the live-Neo4j hygiene rules: back up `:AppSetting` and `:Session` nodes before any test that can touch them and restore them in teardown (a documented incident wiped the operator's stored LLM API key), never touch real user rows (a fixture teardown once deleted real watch progress), and keep all fixture data in `series_scratch*` series or `origin='candidate'` scope so the suite leaves zero residue (CI enforces this).

A useful bug report includes a minimal reproduction, expected and actual behavior, relevant logs with secrets removed, the affected browser/OS/runtime versions, and the exact command that failed.

## Repository Layout

| Path | Purpose |
|---|---|
| `spoilerless/app/api/` | FastAPI routes and HTTP dependencies |
| `spoilerless/app/domain/` | Pydantic request and response contracts |
| `spoilerless/app/services/` | Business rules and orchestration |
| `spoilerless/app/repository/` | Neo4j-backed application repositories |
| `spoilerless/app/graph/` | Neo4j driver, seed/setup code, and graph data access |
| `spoilerless/app/spoiler/` | Visibility policy and spoiler-filtered queries |
| `spoilerless/app/retrieval/`, `spoilerless/app/llm/` | Allowlisted GraphRAG retrieval and LLM providers |
| `spoilerless/tests/` | Backend pytest suite |
| `frontend/src/api/`, `frontend/src/types/` | Frontend API clients and wire types |
| `frontend/src/components/`, `frontend/src/hooks/` | React UI and stateful hooks |
| `frontend/src/**/*.test.ts(x)` | Colocated Vitest/Testing Library tests |
| `data/dexter/` | Curated prototype seed data |
| `ontology/` | Versioned node, relationship, and claim vocabularies |
| `docs/` | Generated and maintained documentation, including the `PROBLEMS.md` issue ledger |

## Development Setup

See [Getting Started](docs/GETTING-STARTED.md) for prerequisites and first-run instructions, [Development](docs/DEVELOPMENT.md) for the full local development setup, and [Testing](docs/TESTING.md) for the complete test reference. The essentials:

### Prerequisites

- Python `>=3.13` (the repository pins `3.13` in `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- Node.js `^22.22.2`, `^24.15.0`, or `>=26.0.0`; CI uses Node 24
- npm and the committed `frontend/package-lock.json`
- Docker Desktop or another Docker Compose implementation for local Neo4j

### Install and initialize

Run backend and repository-wide commands from the repository root:

```bash
git clone https://github.com/vinnipukh/hdgrafcehennemi.git
cd hdgrafcehennemi
cp .env.example .env
uv sync --frozen
docker compose up -d neo4j
uv run --project spoilerless python -m spoilerless.app.graph.setup
cd frontend
npm ci --include=dev
```

`npm ci --include=dev` is required on this repo's dev host: a global `omit=dev` npm setting is active (`npm config get omit` → `dev`), so a plain `npm ci` skips devDependencies and vitest, Testing Library, and jsdom end up missing. `npm install --include=dev` works equally well.

For local Vite proxying, blank or remove `VITE_API_BASE_URL=/api` from the copied `.env`: frontend call sites already include `/api`, so that template value would produce `/api/api/...` URLs. The Compose container takes its password from `NEO4J_PASSWORD` (fallback `change-me`), while `scripts/env-local.sh` pins `hdgraf-local-password` — create the container with `NEO4J_PASSWORD=hdgraf-local-password docker compose up -d` (or set it in root `.env` before first `up`) so one database serves both the app and the test suite. On this machine the legacy `hdgraf-neo4j` container (created with the env-local credentials) can be restored with `docker start hdgraf-neo4j`.

Start the two development servers in separate terminals:

```bash
# Repository root
uv run uvicorn spoilerless.app.main:app --reload

# frontend/
npm run dev
```

The API and Swagger UI run at `http://localhost:8000` and `http://localhost:8000/docs`; Vite runs at `http://localhost:5173`.

## Coding and Architecture Rules

### Backend

- Use absolute `spoilerless.app...` imports and type annotations. No Python formatter, linter, or static type checker is currently configured; match surrounding code.
- Keep the normal dependency direction `api` → `services` → `repository`/`graph`, with shared contracts in `domain`.
- Parameterize Cypher values. Never interpolate user- or model-controlled input into query strings, and keep dynamic labels/predicates behind server-owned ontology allowlists.
- Enforce spoiler filtering in backend data access, before content reaches the browser or LLM. Story-sensitive reads must fail closed and apply the applicable `visible_from_order <= visible_until_order` boundary. Candidate-review list and detail reads also require `visible_until_order`, resolve it against a persisted episode, and filter to that boundary.
- Preserve the public origin vocabulary: `canonical`, `candidate`, and `user`.
- Meaningful mutations must preserve revision history; a revert appends history rather than erasing it.
- Graph writes that can affect `GET /api/series/{series_id}/graph` must invalidate that series through the existing graph-cache helper after the write commits.
- Extend `ontology/*.yaml` deliberately instead of inventing ad hoc node or relationship types.
- `spoilerless/app/llm/system_prompt.py` prose is **user-owned**: never edit the prompt text. Refactors may touch the file only to re-export names or move generated pieces (for example the context delimiters), leaving every prose line byte-identical.

### Frontend

- Use functional React components and hooks, the `@/` source alias, and the existing feature directories.
- Keep wire types, API client calls, hooks, components, and integration wiring synchronized.
- Colocate tests as `*.test.ts` or `*.test.tsx`; use Testing Library role/name queries and `userEvent` for interactions.
- The frontend may present or further narrow already-safe data, but it must never become the spoiler-security boundary.
- Style with Tailwind tokens and inline styles per the existing shadcn/Radix conventions — **no DaisyUI**. Preserve accessible labels, keyboard behavior, and browser shims in `frontend/src/test/setup.ts`.

### API changes

The HTTP surface is treated as a closed inventory (currently 52 operations over 39 path templates). Adding, removing, or changing a route requires synchronized updates to:

- `spoilerless/tests/test_frontend_contract_doc.py` — locks the live 52-operation, 39-template inventory
- `spoilerless/tests/test_openapi_contract.py` — locks the same 39-template surface with fully typed operations (every `DELETE` typed as 204 no-content or 200-with-body)
- `docs/reference/frontend-api-contract.md` — one exact `(method, path)` row per operation
- affected frontend types/clients and focused backend/frontend tests

Both contract tests are green members of the zero-failure baseline.

## Testing and Quality Gates

### Backend

Prepare the test environment once per shell for focused runs against local docker Neo4j (agent/Hermes terminals export `PYTHONPATH`, which shadows the venv and changes results — unset it):

```bash
unset PYTHONPATH
source scripts/env-local.sh   # local docker Neo4j: neo4j / hdgraf-local-password on localhost:7687
```

Run focused, database-free gates first:

```bash
uv run pytest spoilerless/tests/test_frontend_contract_doc.py
uv run pytest spoilerless/tests/test_user_content_models.py
```

The complete configured suite is broad and mutates a live graph, so it must never be pointed at a shared or valuable database — do not run unguarded `pytest` against the shared/live Neo4j database. The **only supported full-suite entrypoint** is the Phase 10 guarded runner, which provisions its own ephemeral `neo4j:2026.06.0-community` container (random credentials and loopback-only ports, no volume mounts) and always tears it down:

```bash
unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py --all
```

The runner refuses, fail-closed (exit 2, before creating anything): ambient `NEO4J_*`/`aura_*` connection overrides, remote/Aura URIs, port `:7687` (the docker-compose developer container), the running developer containers `spoilerless-neo4j`/`hdgraf-neo4j`, and pre-existing containers/volumes with its generated name — so do not `source scripts/env-local.sh` for it. It strips `PYTHONPATH` for children and verifies the container is gone after teardown.

The documented baseline is **zero known failures** on the ephemeral container (all 11 chunks pass in about two minutes). The historical "584 passed / 7 failed" baseline is retired: the doc-contract, seed-image, and constraint-name failures were fixed by the Phase 10 inventory updates (52 operations / 39 templates, locked by both contract tests), the self-hosted portrait restore, and engine-tolerant assertions. **Any failure now is a real regression** and must be explained by your diff.

The suite mixes unit, contract, and live-Neo4j integration tests without marker groups. `spoilerless/tests/conftest.py` supplies import-path and scratch-series helpers but does not redirect Neo4j or provide credentials. Run live-database files sequentially and let fixture teardown finish; never run concurrent pytest processes against the same database. Follow the live-Neo4j hygiene rules from "Before You Start": tests must leave no `series_scratch*` or `origin='candidate'` residue, and must back up/restore `:AppSetting`/`:Session` nodes and avoid real user rows when they touch them.

Every spoiler-sensitive change needs both positive and negative coverage: visible data is returned, future data and indirect hints are absent, hidden and missing resources are indistinguishable where required, and returned edges never reference hidden endpoints.

### Frontend

From `frontend/`, run:

```bash
NODE_ENV=test CI=1 npm run test -- --run
npm run build
npm run lint
```

`npm run test` without `--run` starts Vitest watch mode. Set `NODE_ENV=test` explicitly because an inherited production value can cause misleading React test failures; `CI=1` gives stable run semantics (the full frontend suite currently passes 404 tests across 44 files). `npm run build` is the canonical TypeScript check (`tsc -b`) as well as the Vite production build; `npm run lint` runs ESLint (flat config in `frontend/eslint.config.js`).

### Continuous integration

`.github/workflows/ci.yml` runs on pull requests only:

- **Backend:** `uv sync --frozen`, graph setup, the full pytest suite against an ephemeral Neo4j service, and a database-pollution gate (fails if any `series_scratch*` or `origin='candidate'` residue remains).
- **Frontend:** `npm ci`, `npm run build`, `npm run lint`, and `npm audit --audit-level=high`.

The workflow does **not** run Vitest, so a green pull request does not replace the required local frontend test run. A direct push to `main` does not trigger this CI workflow. `.github/workflows/release.yml` is a manually dispatched promotion skeleton and does not run either test suite; releases are gated on CI passing per `docs/DEPLOYMENT.md`.

## Branches, Commits, and the Issue Ledger

Create a focused branch from an up-to-date `main`. A fork is appropriate for external contributors; collaborators may use a repository branch. There is no enforced branch-name policy or pull-request template. Descriptive names such as `feature/...` or `fix/...` fit the observed history.

Commit style is one atomic commit per problem, with a conventional-style prefix (`feat`, `fix`, `refactor`, `test`, `docs`) and an optional scope; the message references the ledger problem number:

```text
fix(graph): single series-id source — switchSeries moves watch-progress series (PROB-09/#61)
refactor(repos): one row normalizer, one run_single, one tokens module (PROB-09/#68)
docs(08-13): NINETEENTH PASS — guarded ephemeral-container runner retires the seven-red baseline
```

Do not bundle multiple problem numbers into one commit — keep the ledger and the history in one-to-one correspondence, and record each pass in `docs/PROBLEMS.md` (see "Issue Ledger and Contribution Workflow"). Keep commits reviewable, avoid unrelated formatting churn, and do not commit generated build output or local environment/database files.

## Pull Request Checklist

Before opening a pull request:

1. Rebase or merge the latest `main` and confirm the branch contains only intended changes.
2. Add focused tests for behavior changes and regression tests for bug fixes.
3. Run the relevant focused backend tests (against local docker Neo4j after `unset PYTHONPATH && source scripts/env-local.sh`) and, when safe, the full backend suite via the guarded runner (`unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py --all`); the baseline is zero known failures — any failure must be explained by your diff.
4. Run frontend Vitest (`NODE_ENV=test CI=1`), build, and lint for frontend changes.
5. Update API contracts (`spoilerless/tests/test_frontend_contract_doc.py`, `spoilerless/tests/test_openapi_contract.py`, `docs/reference/frontend-api-contract.md`), configuration examples, and user-facing documentation when behavior changes.
6. Update `docs/PROBLEMS.md` with the pass and problem-number entries for your fixes.
7. Review `git diff` for credentials, personal data, database artifacts, debug logging, and accidental unrelated files.

In the pull request, describe:

- the problem and the implemented behavior;
- spoiler-safety, authentication/authorization, data migration, and configuration effects;
- the exact verification commands run and their results;
- screenshots or recordings for visible UI changes;
- known limitations or follow-up work.

Open the pull request against `main` and resolve all applicable CI failures before requesting final review.

## Reporting Issues

Report bugs and feature requests at https://github.com/vinnipukh/hdgrafcehennemi/issues (no issue templates are committed). Include:

- a minimal reproduction, with the exact command or click path;
- expected and actual behavior;
- relevant logs with secrets removed and the affected browser/OS/runtime versions;
- for audit-grade findings (security, data-model, test-infrastructure), append a numbered pass to `docs/PROBLEMS.md` instead of only filing an issue — the ledger is the authoritative record the maintainers work from.
