# Local dev runbook — verified commands (2026-08-12 GETTING-STARTED.md pass)

Verified against repo source + smoke tests while updating docs/GETTING-STARTED.md.
Use these forms; older notes and README lines may show the stale `--project spoilerless` variant.

## Backend / seed / tests (run from repo root)
- Backend: `unset PYTHONPATH && source scripts/env-local.sh && uv run uvicorn spoilerless.app.main:app --reload`
- Seed: `uv run python -m spoilerless.app.graph.setup` (module form; the `spoilerless-setup`
  entry point is NOT installed — pyproject.toml has `[project.scripts]` but no `[build-system]` /
  `tool.uv.package`, so `uv sync` skips entry points).
- Backend tests: `unset PYTHONPATH && source scripts/env-local.sh && uv run pytest spoilerless/tests`
  (592 tests collected; `testpaths` set in pyproject.toml).
- Frontend tests: `cd frontend && NODE_ENV=test CI=1 npx vitest run` (vitest 4, jsdom env,
  setupFiles `./src/test/setup.ts`).
- Never `backend.app.main:app` — import root is `spoilerless` since the 09-01 rename.
- README quick-start (~line 195) still shows `uv run --project spoilerless python -m ...` —
  plain `uv run` from root resolves the root pyproject (name `spoilerless`) and is the verified form.

## scripts/env-local.sh semantics — the #1 local-setup trap
- Exports `NEO4J_URI=neo4j://localhost:7687`, `NEO4J_USERNAME=neo4j`,
  `NEO4J_PASSWORD=hdgraf-local-password`, `NEO4J_DATABASE=neo4j`.
- Shell vars outrank `.env` for BOTH Compose interpolation (`${NEO4J_PASSWORD:-change-me}`)
  and pydantic-settings (`env_file=".env"`).
- Must be sourced BEFORE `docker compose up` so the container is created with
  `hdgraf-local-password`. `NEO4J_AUTH` is fixed at container creation — recreating with
  `docker compose up -d` after changing the password does NOT update an existing database
  (credential persists in the bind-mounted `./neo4j_data`).
- Backend config (`spoilerless/app/core/config.py`): reads `.env` relative to CWD;
  `neo4j_uri`/`neo4j_username`/`neo4j_password` are REQUIRED (no defaults);
  `session_cookie_secure` defaults True.

## Compose facts (current)
- `docker-compose.yml`: image `neo4j:2026.06.0-community`, `container_name: spoilerless-neo4j`,
  healthcheck (wget spider on :7474) → `docker compose up -d --wait neo4j` works.
- Older notes / task-context blocks may say `neo4j:5-community` / container `hdgraf-neo4j` —
  STALE (that container still runs locally but is not what compose declares); repo is truth.

## Auth facts
- `GOOGLE_CLIENT_ID` vs `VITE_GOOGLE_CLIENT_ID`: backend raises RuntimeError at startup only
  when BOTH are set and differ (`verify_google_client_id_equality`, PROB-30/#55).
- Seed ids: `series_dexter`, `dexter_s01e01` … `dexter_s01e03` (`data/dexter/metadata/*.json`).

## Doc-writer / verification notes
- When updating GSD docs for this repo, verify every command against source first; a
  `<doc_assignment>` project_context can carry stale infrastructure facts (container/image
  names above). `<!-- VERIFY: ... -->` markers only for truly external claims (e.g. Google
  Cloud Console steps).
- Windows/MSYS quirk: repo-wide content searches via search_files/rg may fail with an IO
  error on `/c/...` paths — fall back to `grep -rn` via terminal (worked reliably).
