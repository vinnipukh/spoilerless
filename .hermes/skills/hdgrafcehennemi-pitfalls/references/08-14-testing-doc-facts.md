# 08-14 testing doc facts (verified during docs/TESTING.md update)

All verified live 2026-08-14 by actually running both suites.

## Backend baseline: zero known failures (CONFIRMED live)
- PROBLEMS.md NINETEENTH PASS (2026-08-13) retired the 584/7 "seven-red" baseline:
  3 doc-contract reds fixed by the 10-03/10-06 OpenAPI inventory updates, 2
  seed-image reds by the 08-12 self-hosted portrait restore (order-1
  `/api/static/` portraits allowed, above-order-1 must not), 2 constraint-name
  reds by engine-tolerant assertions in `test_seed_idempotency.py`.
- Re-ran `unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py`
  on 08-14: **all 11 chunks PASS** (115.4s wall), teardown verified (container +
  anonymous volumes removed). Docker was idle (no `spoilerless-neo4j` /
  `hdgraf-neo4j` running) so the runner's fail-closed guard accepted the run.
- `test_openapi_contract.py` is **NOT stale anymore** — task-brief claims that
  it "still asserts 32 paths / every DELETE is 204" are THEMSELVES stale. Live
  file locks the 39-template inventory (`assert len(schema["paths"]) == 39`),
  the full (method, path) inventory, typed deletes (204-no-content OR
  200-with-body for share-token revocation), and uppercase error-code registry
  gates. Its own comment says "instead of the stale 45-op/32-path set".
- `test_frontend_contract_doc.py`: `len(documented) == len(generated) == 52`,
  `len(EXPECTED_TEMPLATES) == 39`; the doc-content test
  `test_document_has_examples_projection_rules_non_goals_and_pending_status`
  is a green member of the zero-failure baseline (contract doc refreshed
  TWELFTH PASS).

## Frontend: 404 passed / 44 files
- `cd frontend && NODE_ENV=test CI=1 npx vitest run` → 44 files, 404 tests
  passed (was 333/40 on 08-12), ~29s.
- 44 colocated test files, `*.test.ts` / `*.test.tsx`, e.g.
  `components/graph/cytoscapeReconciler.test.ts`,
  `lib/visualizationAdapter.test.ts`, `hooks/useSceneState.test.ts`,
  `lib/byok.test.ts`, `components/share/ShareView.test.tsx`.

## Host quirks (with fixes)
- **Global npm `omit=dev` is active** on this machine (`npm config get omit` →
  `dev`; no `.npmrc` in repo or `~`). Plain `npm ci` skips devDependencies →
  vitest / Testing Library / jsdom missing. Install with
  `npm ci --include=dev` (or `npm install --include=dev`).
- `uv run --project spoilerless python -c "..."` **WORKS** despite no
  `spoilerless/pyproject.toml` (uv resolves the project from the parent
  directory), so ci.yml's verbatim `uv run --project spoilerless python -m
  spoilerless.app.graph.setup` is NOT a doc error. Canonical local form stays
  `uv run python -m spoilerless.app.graph.setup` / `uv run spoilerless-setup`.

## conftest.py additions since the 08-12 baseline
- `_csrf_bypass_default` — autouse, sets `FRONTEND_ORIGINS=*` so API tests
  need no Origin header; CSRF-specific tests override the setting themselves;
  skipped for the `test_config` module (production-defaults assertion needs
  the pristine env).
- `test_phase10_test_runner.py` has exactly 18 mock-driven guard tests
  (matches NINETEENTH PASS "18 mock-driven guard tests").

## Other confirmed facts
- No `pytest-timeout` configured → no `--timeout` flag for `uv run pytest`; no
  pytest-cov / coverage threshold in root pyproject.toml; no coverage config
  in the `frontend/vite.config.ts` test block (jsdom, globals, setupFiles).
- pytest config lives only in root `pyproject.toml` (no pytest.ini/tox.ini/
  setup.cfg): asyncio_mode auto, fixture+test loop scope module,
  testpaths `spoilerless/tests`.
- CI: `ci.yml` triggers on `pull_request` only; backend job = ephemeral
  `neo4j:2026.06.0-community` service + `uv run pytest` + scratch/candidate
  pollution gate; frontend job = npm ci / build / lint / audit (does NOT run
  FE tests). `release.yml` = workflow_dispatch skeleton, runs no tests.
- Chunked runner: 11 chunks (core, domain-models, series-api, graph,
  change-set, candidates, auth, user-content, chat-llm, contract-ops,
  phase10-viz); inventory gate asserts every `test_*.py` appears exactly once;
  `seed_idempotency` (graph chunk) / `setup_schema_check` (core chunk) tests
  re-seed → run chunks 1 and 4 alone before any `--parallel` batch.
