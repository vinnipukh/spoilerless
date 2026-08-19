# Phase 10 verify-command quick reference (hdgrafcehennemi)

Learned while executing phase 10 (polish-finishing-touches), 2026-08-13.
Complements `phase10-execution-pitfalls.md` and `plan-10-09-ephemeral-test-runner.md`.

## Test-infra facts that bite

- **`uv run pytest` has NO `--timeout` flag** (pytest-timeout not installed in the
  uv env). The old memory-era command used `.venv/Scripts/python.exe -m pytest
  ... --timeout=120` — that flag errors out under `uv run pytest`.
- **Broad `-k` filters can hang the run**: `-k "boundary or variant or bound"`
  matches live-DB tests in `test_graph_api.py` (per-test reseed) → 300s+ timeout.
  Safe pattern: run the OFFLINE files unfiltered (all fast, <2s: projection,
  spoiler_policy, baseline, cache, graphrag, openapi_contract,
  frontend_contract_doc) and use ONLY the plan's exact `-k` expression on the
  route files (e.g. `-k "visualization or projection or cache or exact_operations
  or locked_inventory"` — 39 passed ~30-100s).
- **Full backend suite**: ONLY `unset PYTHONPATH && uv run python
  scripts/run_phase10_backend_tests.py --all` — ephemeral Neo4j 2026.06.0
  container, 11 chunks, ~90s wall, teardown verified. It refuses the developer
  container `spoilerless-neo4j`, remote/Aura URIs, ambient `NEO4J_*`/`aura_*`
  overrides, and pre-existing container names. Guard tests:
  `uv run pytest spoilerless/tests/test_phase10_test_runner.py -q` (18 tests).
- **Fast offline backend evidence set** (used constantly mid-phase):
  `pytest test_visualization_projection.py test_spoiler_policy.py
  test_visualization_baseline.py test_visualization_cache.py
  test_visualization_graphrag.py test_openapi_contract.py
  test_frontend_contract_doc.py -q` → ~110-150 passed in seconds.

## Frontend

- `NODE_ENV=test CI=1 npm --prefix frontend test -- --run <files>`; full suite
  42-43 files / ~390 tests in ~20-70s. Typecheck = `npm --prefix frontend run build`.
- Local npm config `omit=dev` — after any node_modules re-sync run
  `npm --prefix frontend install --include=dev` or vitest goes missing.
- `hermes verify` auto-detects a backend-only recipe (pytest/uvicorn:8000) and
  never exercises `.tsx` diffs; redirecting via `.hermes/environment.json` is
  blocked (protected file). Use the plan's own verify chain as evidence and say so.

## Orchestration cadence (phase-10 pattern)

- Executors cap at ~50 tool calls. Dispatch prompts MUST say "COMMIT EARLY" and
  demand a precise handoff at cap. Plan for 1-2 executor waves then inline
  completion: 10-03..10-09 all needed orchestrator inline finishing.
- Docker Desktop on this host: daemon often down; `cmd //c start` of the exe
  fails silently — launch `"C:\Program Files\Docker\Docker\Docker Desktop.exe"`
  directly in background and poll `docker info` (takes ~1 min to come up).
