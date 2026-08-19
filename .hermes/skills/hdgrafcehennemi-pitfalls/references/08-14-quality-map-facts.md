# 2026-08-14 Quality-Focus Codebase Map Snapshot (CONVENTIONS.md / TESTING.md)

Source: `.planning/codebase/CONVENTIONS.md` and `.planning/codebase/TESTING.md` refreshed 2026-08-14 at commit `5bd1641` (update run vs. 1710d57, 2026-08-12). These two map docs are the authoritative quality-focus reference for future plan/execute phases — read them instead of re-deriving.

## Live numbers (verified by running, not copied from old docs)

- Backend suite: 51 `spoilerless/tests/test_*.py` files, ~21.9k lines (was 45 / ~17.2k on 2026-08-12).
- Frontend suite: 44 test files, **404 tests passing**, ~29s (`NODE_ENV=test CI=1 npm run test` from `frontend/`).
- Lint: 0 errors, **21 warnings**, all `react-hooks/refs` (down from 39 on 08-12; e.g. `useImperativeReconcileRef.current` render-time read in `frontend/src/components/graph/GraphCanvas.tsx`).
- Chunk table: **11 chunks** in `docs/ops/runbook.md`; chunk 11 `phase10-viz` = `test_visualization_baseline.py`, `test_visualization_projection.py`, `test_visualization_cache.py`, `test_visualization_graphrag.py`, `test_phase10_test_runner.py`.
- `scripts/run_backend_tests.py` asserts chunk inventory at startup: `assert_chunk_inventory_matches_disk()` — every `test_*.py` listed exactly once.
- 584-pass / 7-failed local-docker baseline is **RETIRED** (NINETEENTH PASS, 2026-08-13). Canonical full backend suite = `uv run python scripts/run_phase10_backend_tests.py` (ephemeral `neo4j:2026.06.0-community` container, random password/ports, no volume mounts; fail-closed refusals: ambient `NEO4J_*`/`aura_*` overrides, remote/Aura hosts, dev port 7687, running `spoilerless-neo4j`/`hdgraf-neo4j`, pre-existing name; proves effective Settings + 0 nodes; seeds via `python -m spoilerless.app.graph.setup`; finally-guarded `docker rm -f -v`; exit codes 0/1/2). Guarded by 18 mock-driven tests in `test_phase10_test_runner.py` (`FakeDocker` + `monkeypatch.setattr(runner, "_docker", fake)`).

## New test families (Phase 10)

- **Offline visualization family** (`test_visualization_projection.py` 1711 lines, `_baseline.py` 752, `_cache.py` 393, `_graphrag.py` 267): NO live Neo4j / LLM / retrieval. Use checked-in safe fixtures in `spoilerless/tests/fixtures/visualization/` (`s01e01_safe.json`, `s01e02_cumulative_safe.json`), validated through real `GraphResponse.model_validate`. Module-scope `service = VisualizationProjectionService()`. Forbidden-vocabulary scans (`_FORBIDDEN_KEY_RE`, `_forbidden_metadata_keys`), raw-relation-name tuples (`_RAW_RELATION_NAMES`), `_FakeRedis` stand-in for the `viz:` cache. Baseline tracer constants are the single source of truth (`TARGET_MIN_NODES` etc.).
- **Script-guard suites** (`test_phase10_coverage_audit.py`, `test_phase10_test_runner.py`): load scripts in-process via `importlib.util.spec_from_file_location` — no subprocess/daemon/live files. Lock fail-closed parsing contracts (literal `PHASE10-COVERAGE` markers, exact header, 98 exact source ids), CLI exit codes via `tmp_path`, teardown-always-runs.
- Cross-module test-helper imports are sanctioned: `test_visualization_graphrag.py` imports `_CallScriptedProvider`/`_StubDatabase` from `test_retrieval_pipeline.py` and `_load_fixture` from `test_visualization_projection.py`.
- `test_graph_api.py` gained `test_visualization_route_*` family (DTO validation, anonymous clamp to order 1, focus 422s, cache-hit byte-for-byte vs miss, Redis failure still serves).
- `conftest.py` autouse `_csrf_bypass_default` fixture: sets `FRONTEND_ORIGINS=*` + `get_settings.cache_clear()`, skipped for `test_config` module.

## Frontend conventions added

- **Headless real cytoscape** for reconciler tests (`frontend/src/components/graph/cytoscapeReconciler.test.ts`): `cytoscape({ headless: true, styleEnabled: false, elements })`, assert identity/position/classes/selection/zoom/pan preservation, `cy.destroy()` per test. Do NOT stub cytoscape when compound-removal/edge-rewiring/identity is the behavior under test.
- **Exact-shape pinning**: `NODE_DATA_KEYS`/`EDGE_DATA_KEYS`/`GROUP_DATA_KEYS` `as const` in `frontend/src/lib/visualizationAdapter.ts`, pinned by `visualizationAdapter.test.ts` (hidden fields can't flow into Cytoscape).
- Serializable scene state reducer: `frontend/src/hooks/useSceneState.ts` (JSON-safe only, no `cy` refs, D-24); JSON round-trip test.
- `App.test.tsx`: typed `VisualizationDTO` fixtures mirroring `spoilerless/app/domain/visualization.py`; fetch-stub ordering (`/graph/visualization` + `/graph/expand` BEFORE generic `/graph`); `within(screen.getByRole('dialog'))` scoping (new Evidence tab makes unscoped queries ambiguous); `graphFetchCalls()` excludes projection URLs.
- Threat-model traceability IDs in module docstrings/comments: `T10-LEAK-*`, `T10-BOUND-*`, `T10-CACHE-*`, `T10-FOCUS-*`, `D-*`, `VIZ-*` — keep verbatim; trace to `.planning/phases/10-polish-finishing-touches/`.

## Gotchas

- **`PROBLEMS.md` is at `docs/PROBLEMS.md`, NOT the repo root.** Grepping `PROBLEMS.md` from root fails. Ledger = numbered PASS entries (up to TWENTIETH PASS, 2026-08-14); NINETEENTH PASS documents the baseline retirement, TWENTIETH PASS the docs-update sweep (~1,400 claims, 25 docs).
- Root claim-verification scripts (`run_verification.py`, `run_doc_verification.py`, `verify_all_claims.py`, `verify_arch.py`) are untracked one-off audit tooling: parse docs such as `docs/ARCHITECTURE.md`, write JSON to `.planning/tmp/verify-ARCHITECTURE.md.json`, hardcode an absolute Windows root, NOT in CI. `run_doc_verification.py` recorded 276/276 in SIXTEENTH PASS.
- `frontend/src/hooks/useSceneState.ts` reducer exists (340 lines) — scene state is reducer-owned; don't reintroduce per-component scene state.
