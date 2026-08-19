# TESTING.md baseline + doc-writer update facts (verified 2026-08-12)

> **SUPERSEDED 2026-08-14 — do NOT write the 584/7 baseline into docs.**
> PROBLEMS.md NINETEENTH PASS (2026-08-13) retired the seven-red baseline:
> zero known failures, re-verified live 08-14 (all 11 chunks pass on the
> guarded ephemeral runner, ~2 min; frontend 404 passed / 44 files).
> See `references/08-14-testing-doc-facts.md` for current verified facts.
> The 584/7 detail below is historical audit trail only — "never chase the 7"
> is no longer the rule; ANY failure is now a regression. The doc-contract
> reds listed below are fixed: `test_openapi_contract.py` now locks 39
> templates with typed deletes (not stale), and the frontend-contract
> doc-content test is green.

Session: GSD doc-writer `mode: update` on `docs/TESTING.md`. All facts below were
verified against live source AND by actually running the failing tests against the
local docker Neo4j (`hdgraf-neo4j` / `spoilerless-neo4j` container) — do the same
before trusting task-brief prose or the previous doc's claims.

## Canonical local-docker verify command (~2 min, baseline)
```bash
unset PYTHONPATH && source scripts/env-local.sh && uv run pytest spoilerless/tests -q
```
- `unset PYTHONPATH` is REQUIRED: the Hermes terminal exports PYTHONPATH pointing at
  the hermes-agent package dir, which shadows the venv and breaks `import spoilerless`
  (this is why `scripts/run_backend_tests.py` strips PYTHONPATH from child envs).
- Full-suite baseline: **584 passed / 7 failed** on a fresh local docker Neo4j.

## The documented baseline — "never chase the 7"
A green run means 584 passed with EXACTLY these 7 failing (all pre-existing,
documented in docs/PROBLEMS.md ELEVENTH PASS; not regressions):
- 3 doc-contract:
  - `test_frontend_contract_doc.py::test_document_has_examples_projection_rules_non_goals_and_pending_status`
    (doc-content markers test — RED. NOTE: `test_document_and_openapi_have_exact_locked_inventory`
    inside the same file is GREEN — the old TESTING.md prose claiming the file "locks the
    inventory" was only half right; running the file revealed the red doc-content test.)
  - `test_openapi_contract.py::test_user_route_openapi_has_exact_operations_and_templates`
    (stale: still asserts `len(schema["paths"]) == 32` vs the live 50 ops / 37 templates)
  - `test_openapi_contract.py::test_all_story_reads_graph_errors_health_and_deletes_are_fully_typed`
- 2 seed-image (`test_graph_api.py`): `test_graph_nodes_include_image_fields`,
  `TestSeedImageCuration::test_no_seed_image_for_resources_visible_above_order_one`
- 2 seed_idempotency constraint-name (`test_seed_idempotency.py`):
  `test_community_schema_creates_only_unique_and_index`,
  `test_constraints_visibility_and_provenance`

Any run that differs from this set (fewer failures, other failures) is a REAL
regression — investigate it; do not "fix" the 7.

## Technique: confirm the baseline empirically, don't trust the doc
The previous TESTING.md implied `test_frontend_contract_doc.py` was green; running
`uv run pytest spoilerless/tests/test_frontend_contract_doc.py spoilerless/tests/test_openapi_contract.py -q`
against live docker showed 3 failed / 9 passed. Use targeted `-k` runs of just the
suspected failing tests (fast, no full suite) to enumerate the exact baseline list
before writing the doc. Docker must be up (`docker ps` → `spoilerless-neo4j`).

## conftest.py shared infrastructure (verified line-by-line)
- `NoopGoogleVerifier` — shared no-op AuthService verifier (PROB-09/#77 follow-up,
  2026-08-11); AuthService requires a verifier, tests not exercising Google share it.
- `seed_live_database()` / `live_client` — one seeded main-app TestClient (module-level
  seed, ~12s per re-seed).
- `module_cleanup_fixture(queries)` / `cleanup_with_fresh_driver(queries)` — once-per-module
  teardown; `(query, params)` tuples supported; return value MUST bind to a module-level
  name or pytest never registers the fixture.
- `run_query(query, **params)` — fresh-driver probe (reliable read-after-write on AuraDB;
  shared-driver variant intermittently missed app-driver writes).
- `helper_db()` / `run_async(coro_factory)` — shared driver/loop for service probes.
- `bootstrap_scratch_series()` / `teardown_scratch_series()` — scratch :Series/:Episode +
  `origin='candidate'` residue + UserSeriesProgress cleanup on a fresh driver/loop.
- `_disable_rate_limiter` — autouse, patches `RateLimiter.__call__` to no-op (no live Redis).
- pytest-asyncio: `asyncio_mode = "auto"`, fixture/test loop scope both `module`
  (root `pyproject.toml`); Python >=3.13; `uv sync --frozen` installs.

## scripts/run_backend_tests.py (10 named chunks, verified)
- Chunks: core, domain-models, series-api, graph, change-set, candidates, auth,
  user-content, chat-llm, contract-ops — every test file appears exactly once.
- `--list`, `--chunk <index|name[,name]>`, `--parallel`, extra pytest args pass through.
- `--parallel` is SLOWER than serial on the shared AuraDB (connection contention);
  only use against isolated Neo4j. `seed_idempotency`/`setup_schema_check` chunks
  re-seed + assert exact counts — run them alone before any parallel batch.
- Strips PYTHONPATH from child envs → works from the Hermes terminal.

## Frontend suite (verified)
- `cd frontend && NODE_ENV=test CI=1 npx vitest run` → **333 passed / 40 files**
  (`npm run test -- --run` is the equivalent spelling). CI=1 forces non-watch.
- `NODE_ENV=test` matters: a leaked `NODE_ENV=production` loads React production
  behavior → misleading failures.
- Typecheck: `npm run build` (`tsc -b && vite build`) — the only typecheck entry point.
- No coverage threshold configured for either suite; no test:unit/integration/e2e scripts.

## CI (verified from .github/workflows/)
- `ci.yml` runs on `pull_request` only (push to main does NOT trigger it). Backend job:
  ephemeral `neo4j:2026.06.0-community` service + `uv run pytest` + pollution gate
  (asserts zero `series_scratch*`/`origin='candidate'` residue). Frontend job: `npm ci`,
  `npm run build`, `npm run lint`, `npm audit` — does NOT run the FE test suite.
- `release.yml`: workflow_dispatch promotion skeleton, runs no tests.

## OPEN VERIFICATION ITEM — RESOLVED 2026-08-14 (probe answered it)
TESTING.md and ci.yml both use `uv run --project spoilerless python -m spoilerless.app.graph.setup`,
and there is indeed NO `spoilerless/pyproject.toml` (root `pyproject.toml` IS the
`spoilerless` project, `name = "spoilerless"`). BUT the probe
`uv run --project spoilerless python -c "print(1)"` **succeeds** — uv resolves
the project from the parent directory. So the `--project spoilerless` form
WORKS; ci.yml's verbatim string is not a doc error. Canonical local form
remains `uv run python -m spoilerless.app.graph.setup` or `uv run spoilerless-setup`
(`spoilerless/app/graph/setup.py` `main()`, root `[project.scripts]`).
