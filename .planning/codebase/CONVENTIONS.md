---
last_mapped: 2026-08-14
focus: quality
last_mapped_commit: 5bd1641d7a9c44d693669d356ea602a23aa3664f
---
# Coding Conventions

**Analysis Date:** 2026-08-14

## Naming Patterns

**Files:**
- Use `snake_case.py` for backend modules and keep layers in `spoilerless/app/api/`, `spoilerless/app/services/`, `spoilerless/app/repository/`, and `spoilerless/app/domain/`; examples are `spoilerless/app/api/settings.py` and `spoilerless/app/services/settings.py`.
- Use PascalCase filenames for React components, such as `frontend/src/components/settings/SettingsPage.tsx`, and camelCase filenames for hooks, API clients, and utilities, such as `frontend/src/hooks/useGraph.ts` and `frontend/src/api/client.ts`.
- Colocate frontend tests as `*.test.ts` or `*.test.tsx`; place backend tests in `spoilerless/tests/test_*.py`.
- Newer backend suites group by domain family with a shared prefix: `test_visualization_*.py` (`test_visualization_projection.py`, `test_visualization_baseline.py`, `test_visualization_cache.py`, `test_visualization_graphrag.py`) and `test_phase10_*.py` (`test_phase10_coverage_audit.py`, `test_phase10_test_runner.py`).
- Checked-in offline fixtures live in a domain directory under `spoilerless/tests/fixtures/<domain>/`, e.g. `spoilerless/tests/fixtures/visualization/s01e01_safe.json` and `s01e02_cumulative_safe.json`.

**Functions:**
- Use Python `snake_case` for functions and methods (`get_llm_settings`, `execute_query`) and prefix private helpers with `_`, as in `_validate_base_url` in `spoilerless/app/domain/settings.py`.
- Use TypeScript/React `camelCase` for functions and callbacks (`apiFetch`, `handleCreateNote`) and the `useX` prefix for hooks (`useGraph`) in `frontend/src/hooks/`.
- Name Python tests `test_<behavior>` and frontend tests with behavior-focused `it('...')` text; examples are in `spoilerless/tests/test_openapi_contract.py` and `frontend/src/components/settings/SettingsPage.test.tsx`.
- Prefix route-level test families with the route name: `test_visualization_route_*` in `spoilerless/tests/test_graph_api.py` covers the `/graph/visualization` and `/graph/expand` endpoints end to end.

**Variables:**
- Use Python `snake_case`; module constants are uppercase (`SERVICE_NAME` in `spoilerless/app/main.py`, `DEFAULT_GEMINI_BASE_URL` in `spoilerless/app/domain/settings.py`).
- Use TypeScript `camelCase`; immutable fixture-like values use descriptive lower camel case (`defaultSettings` in `frontend/src/components/settings/SettingsPage.test.tsx`).
- Prefix intentionally unused FastAPI dependencies/arguments with `_`, such as `_user` in `spoilerless/app/api/settings.py` and `_rate_limit: Annotated[None, Depends(login_rate_limiter)]` in `spoilerless/app/api/auth.py`.

**Types:**
- Use PascalCase for Python classes/Pydantic models (`SettingsService`, `LLMSettingsResponse`) and TypeScript types/components (`ApiErrorDetail`, `SettingsPage`).
- Model frontend async state with discriminated unions keyed by `status`, as demonstrated by `State` in `frontend/src/hooks/useGraph.ts`.
- Prefer literal unions for closed vocabularies: Python uses `Literal[...]` in `spoilerless/app/domain/settings.py`; TypeScript uses string-literal fields in `frontend/src/types/`.
- Pin emitted data-key vocabularies with `as const` arrays at module scope and export them for tests: `NODE_DATA_KEYS`, `EDGE_DATA_KEYS`, `GROUP_DATA_KEYS` in `frontend/src/lib/visualizationAdapter.ts`.

## Code Style

**Python formatting:**
- Target Python `>=3.13` as declared in `pyproject.toml`; use modern annotations (`str | None`, `list[...]`, `dict[...]`) throughout `spoilerless/app/`.
- Start backend modules with `from __future__ import annotations`; this is the dominant pattern in `spoilerless/app/graph/database.py`, `spoilerless/app/core/errors.py`, and tests.
- Match surrounding four-space indentation and generally Black-like wrapping, but no Black, Ruff, isort, mypy, Pyright, or other Python formatter/linter/type-check configuration is committed in `pyproject.toml`.
- Use explicit return types on public functions and async methods, as in `spoilerless/app/services/settings.py` and `spoilerless/app/api/settings.py`.

**TypeScript/React formatting:**
- Match the existing no-semicolon, single-quote style visible in `frontend/src/api/client.ts` and `frontend/src/hooks/useGraph.ts`; no automated formatter is configured.
- `frontend/tsconfig.app.json` targets ES2023, uses bundler resolution and `react-jsx`, and enforces unused locals/parameters, erasable syntax, and switch fallthrough checks. It does not enable TypeScript `strict`.
- Use functional components and hooks. Keep reusable UI primitives under `frontend/src/components/ui/` and application components under feature directories in `frontend/src/components/`.
- No Prettier, Biome, or EditorConfig is committed, and `frontend/package.json` has no format script; preserve local style rather than claiming formatter enforcement.

**Linting:**
- Run `npm run lint` from `frontend/`; `frontend/eslint.config.js` combines recommended JavaScript, TypeScript, React Hooks, and Vite React Refresh rules.
- Generated-style primitives under `frontend/src/components/ui/` alone disable `react-refresh/only-export-components`, because they colocate component and CVA exports.
- The live lint run on 2026-08-14 reports 0 errors and 21 warnings, all `react-hooks/refs` (render-time ref reads) in files including `frontend/src/components/graph/GraphCanvas.tsx` (e.g. the `useImperativeReconcileRef.current` read at the `layout` prop) and revision tests. The count dropped from 39 (2026-08-12) as reconciler/visualization work landed; keep the warning count from growing and do not introduce new error-class findings.

## Import Organization

**Python order:**
1. `from __future__ import annotations`.
2. Standard-library imports (`asyncio`, `json`, `typing`, `uuid`).
3. Third-party imports (`fastapi`, `neo4j`, `pydantic`, `pytest`).
4. Absolute project imports rooted at `spoilerless.app`, as in `spoilerless/app/api/settings.py`.

**TypeScript order:**
1. Framework/tool or package imports (`react`, `vitest`, Testing Library).
2. Application modules and components.
3. Type-only imports with `import type`, as in `frontend/src/hooks/useGraph.ts`.
- Both relative imports and the `@/` source alias exist. Prefer `@/` for cross-feature imports (`frontend/src/components/settings/SettingsPage.test.tsx`) and short relative imports within a feature (`frontend/src/api/chat.test.ts`). The alias is configured in `frontend/tsconfig.app.json` and `frontend/vite.config.ts`.

## Error Handling

**Backend patterns:**
- Expose one sanitized JSON envelope, `{detail: {code, message}}`, through helpers and exception handlers in `spoilerless/app/core/errors.py`; do not leak rejected input, database internals, or secrets.
- Raise domain/API failures with `http_error(...)` or dedicated exceptions and install handlers at the application boundary in `spoilerless/app/main.py`.
- Validate request contracts with strict Pydantic models (`ConfigDict(extra="forbid")`) and `Field`/`field_validator`, as in `spoilerless/app/domain/settings.py`.
- Catch only expected failures when a safe fallback exists. `SettingsRepository.get_llm()` returns `None` for malformed stored JSON in `spoilerless/app/repository/settings.py`; startup intentionally catches connection failure so `/health` can report degraded state in `spoilerless/app/main.py`. The visualization cache degrades to bypass when Redis fails (`spoilerless/tests/test_visualization_cache.py` locks T-08-06-02: a cache failure must never surface as a request failure).
- Keep Cypher values parameterized (`$key`, `$value`) at the repository boundary in `spoilerless/app/repository/settings.py`; never interpolate user-controlled values into queries.
- Require wiring at construction time: `AuthService.__init__` takes `session_repo` and `verifier` with no silent fallbacks (`spoilerless/app/services/auth.py`), so missing dependency wiring fails loudly at resolution instead of degrading at runtime (PROB-09/#77).

**Frontend patterns:**
- Route JSON requests through `apiFetch<T>` in `frontend/src/api/client.ts`; it includes credentials, normalizes backend/FastAPI validation errors into `ApiError`, handles 204, and falls back to `unknown_error` for malformed error responses.
- In hooks, convert unknown failures to `ApiError` and expose explicit state rather than throwing during render, as in `frontend/src/hooks/useGraph.ts`.
- Use cancellation flags in async effects to prevent stale state updates after dependency changes or unmount (`frontend/src/hooks/useGraph.ts`).
- Treat SSE completion and failure as explicit terminal events; `frontend/src/api/chat.ts` also converts premature EOF into `stream_ended` rather than leaving UI state hanging.

## Logging

**Framework:** No dedicated logging framework is configured in `spoilerless/app/` or `frontend/src/`.

**Patterns:**
- Do not log secrets or raw provider keys; response contracts deliberately mask keys in `spoilerless/app/domain/settings.py`.
- Keep diagnostic output out of normal source unless it is intentional. Current test infrastructure contains console noise in `frontend/src/test/setup.ts`, and graph/test diagnostics exist in `frontend/src/components/graph/GraphCanvas.tsx` and its tests; do not copy these as a general logging pattern.
- Backend startup health failures are converted to degraded state without logging in `spoilerless/app/main.py`; new operational logging should remain sanitized and structured if introduced.

## Comments

**When to comment:**
- Explain non-obvious lifecycle, safety, security, or compatibility constraints rather than restating syntax. Strong examples include cross-loop Neo4j teardown notes in `spoilerless/tests/test_settings_api.py`, SSRF scope in `spoilerless/app/domain/settings.py`, and refresh-versus-refetch semantics in `frontend/src/hooks/useGraph.ts`.
- Preserve comments that document spoiler boundaries, retry purity, or browser/jsdom shims; these encode correctness constraints in `spoilerless/app/graph/database.py` and `frontend/src/test/setup.ts`.
- Keep comments synchronized with implementation. Treat comments as context, not proof; for example, verify schema/constraint claims against current seed code and tests before repeating them.
- Tag safety contracts and behavior guarantees with threat-model and requirement IDs (`T10-LEAK-*`, `T10-BOUND-*`, `T10-CACHE-*`, `T10-FOCUS-*`, `D-*`, `VIZ-*`, `PROB-*`). These appear in module docstrings and header comments of `spoilerless/tests/test_visualization_projection.py`, `frontend/src/lib/visualizationAdapter.ts`, and `frontend/src/hooks/useSceneState.ts`, and trace to `.planning/phases/10-polish-finishing-touches/` plans; keeping the IDs verbatim makes closeout evidence auditable.
- Date-prefix significant frontend changes inline (`// 260814-viz: ...`) when a route/behavior family was introduced in one pass, as in `frontend/src/App.test.tsx`; this mirrors the PASS-ledger convention in `docs/PROBLEMS.md`.

**Docstrings/JSDoc:**
- Use module/class/function docstrings for backend contracts and non-obvious behavior (`spoilerless/app/core/errors.py`, `spoilerless/app/services/settings.py`).
- Newer offline suites open with long contract docstrings that name the plan/task IDs, the safety contract, and what the module does NOT touch ("No live Neo4j, no LLM, no retrieval calls"), as in `spoilerless/tests/test_visualization_projection.py` and `spoilerless/tests/test_phase10_test_runner.py`.
- JSDoc/TSDoc is sparse in the frontend; prefer precise inline comments around lifecycle and compatibility behavior, as in `frontend/src/hooks/useGraph.ts` and `frontend/src/api/client.ts`. New pure modules (`frontend/src/lib/visualizationAdapter.ts`, `frontend/src/hooks/useSceneState.ts`, `frontend/src/components/graph/cytoscapeReconciler.ts`) carry JSDoc on their main exports documenting the contract and the threat model.

## Function Design

**Size:**
- Keep API handlers thin: inject dependencies, delegate to services, and return typed models, as in `spoilerless/app/api/settings.py`.
- Put persistence serialization and Cypher in repositories (`spoilerless/app/repository/settings.py`), effective-value/business rules in services (`spoilerless/app/services/settings.py`), and validation/contracts in domain models (`spoilerless/app/domain/settings.py`).
- Frontend hooks own asynchronous state transitions, API modules own transport, and components own rendering/interactions; examples are `frontend/src/hooks/useGraph.ts`, `frontend/src/api/client.ts`, and `frontend/src/components/settings/SettingsPage.tsx`.
- Keep runner/script logic separable: pure, unit-testable helpers (target generation, refusal classification, child env, docker args) are separated from I/O in `scripts/run_phase10_backend_tests.py`, and the docker shim `_docker` is a module attribute so guard tests can `monkeypatch.setattr` it.
- Model scene state as one serializable reducer (`frontend/src/hooks/useSceneState.ts`): plain JSON-safe values only, no `cy` references, no DOM; Cytoscape changes apply through batched diffs, and dispatching presentation-only state never triggers a fetch or relayout.

**Parameters:**
- Prefer dependency injection and typed constructor parameters in backend services/repositories. FastAPI dependency aliases use `Annotated[..., Depends(...)]` in `spoilerless/app/api/settings.py`.
- Prefer typed props objects and callback props for React components; avoid `any` except narrow compatibility shims such as the documented React 19 fallback in `frontend/src/test/setup.ts`.

**Return values:**
- Backend functions return Pydantic models or explicit typed dictionaries/lists; repository reads use `None` for absence and services resolve defaults.
- Frontend API functions return `Promise<T>`; hooks return discriminated state plus named actions (`refetch`, `refresh`) in `frontend/src/hooks/useGraph.ts`.
- Scripts return process exit codes through `main(argv) -> int` (0 green, 1 test failures, 2 forbidden-target/usage error) as in `scripts/run_phase10_backend_tests.py` and `scripts/verify_phase10_coverage.py`.

## Module Design

**Exports:**
- Backend modules expose routers, services, repositories, models, and named helpers; layer imports should flow `api` → `services` → `repository`/`graph`, with shared contracts in `spoilerless/app/domain/`.
- Frontend uses named exports for application functions/components and default exports mainly where libraries/tooling expect them (for example Vite config and some generated UI patterns).
- Tests may import fakes/helpers from other test modules instead of duplicating them: `spoilerless/tests/test_visualization_graphrag.py` reuses `_CallScriptedProvider`/`_StubDatabase`/`_StubProgressService` from `spoilerless/tests/test_retrieval_pipeline.py` and `_load_fixture` from `spoilerless/tests/test_visualization_projection.py`. Shared production fakes still belong in `spoilerless/tests/conftest.py`.

**Barrel files:**
- `spoilerless/app/**/__init__.py` files are mostly package markers; imports generally target concrete modules rather than broad barrels.
- The frontend has no general barrel-index convention; import concrete modules to keep dependencies explicit.

## Documentation Verification

- `docs/PROBLEMS.md` is the canonical issue ledger; every sweep is a numbered PASS entry (up to TWENTIETH PASS, 2026-08-14) that records verification evidence, root causes, and commit hashes. Fixes cite the pass, and historical audit-trail entries are left untouched per ledger convention.
- Root-level one-off claim-verification scripts (`run_verification.py`, `run_doc_verification.py`, `verify_all_claims.py`, `verify_arch.py`) parse canonical docs such as `docs/ARCHITECTURE.md`, check file-path/dependency claims line by line, and write JSON results to `.planning/tmp/verify-ARCHITECTURE.md.json`. `docs/PROBLEMS.md` SIXTEENTH PASS records `run_doc_verification.py` at 276/276 claims passing. These scripts hardcode an absolute Windows repo root, are untracked, and are not part of CI — treat them as one-off audit tooling, not repeatable gates.
- Machine-readable document contracts use literal marker blocks: `scripts/verify_phase10_coverage.py` reads the coverage table only between the literal `PHASE10-COVERAGE` start/end markers with an exact header and a fixed inventory of 98 exact source ids, and its parsing contract is locked by `spoilerless/tests/test_phase10_coverage_audit.py`.

## Reusable Patterns and Anti-Patterns

**Use:**
- Strict input models + sanitized error envelopes (`spoilerless/app/domain/settings.py`, `spoilerless/app/core/errors.py`).
- Parameterized Cypher and JSON serialization at the Neo4j repository boundary (`spoilerless/app/repository/settings.py`).
- Explicit async state unions and cancellation cleanup (`frontend/src/hooks/useGraph.ts`).
- `@/` alias for cross-feature frontend dependencies and colocated behavioral tests.
- Single registry tables for closed operation sets: `TOOL_SPECS` (`spoilerless/app/retrieval/tools.py`), `CONTEXT_SECTIONS` (`spoilerless/app/retrieval/context.py`), `_APPLY_SPECS` table-driven change-set dispatch (`spoilerless/app/repository/change_set.py`), `NODE_LABELS` (`spoilerless/app/graph/labels.py`) — add a row, not a branch.
- Shared Cypher fragments and helpers instead of copy-paste: `visible_claim_where`/`claim_projection` (`spoilerless/app/spoiler/filter.py`), `neo4j_row_to_python`/`run_single` (`spoilerless/app/graph/database.py`), token helpers (`spoilerless/app/core/tokens.py`), shared `_walk_visible_claims` BFS (`spoilerless/app/retrieval/tools.py`).
- Label-agnostic queries: probe `labels(node)` against a closed literal set rather than label-variant query maps (`spoilerless/app/repository/user_content.py`).
- Cross-engine Cypher portability: keep an explicit `WITH` between `MERGE` and `MATCH`; Neo4j 5 rejects the omission (42N24) while AuraDB tolerates it (`spoilerless/app/repository/change_set.py`).
- Resolve spoiler boundaries server-side: candidate reads require a boundary that resolves against a persisted episode (`_require_resolved_boundary` in `spoilerless/app/api/candidates.py`); above-boundary claims read as missing.
- Frontend: one shared `useFetchState` async-state machine and one `applyHighlight` cytoscape helper instead of per-hook/per-component copies (`frontend/src/hooks/useFetchState.ts`, `frontend/src/lib/graph/highlight.ts`).
- Threat-model-tagged safety contracts at module heads for anything touching visibility, caching, or focus (`spoilerless/tests/test_visualization_*.py`, `frontend/src/lib/visualizationAdapter.ts`, `frontend/src/hooks/useSceneState.ts`).
- Exact-shape pinning: emit a fixed, documented data-key set per element kind and pin it in tests, so a hidden field sneaking into the DTO cannot flow through to Cytoscape (`NODE_DATA_KEYS`/`EDGE_DATA_KEYS`/`GROUP_DATA_KEYS` in `frontend/src/lib/visualizationAdapter.ts`).
- Batched element reconciliation that preserves identity and runtime state: `reconcileCytoscapeElements` in `frontend/src/components/graph/cytoscapeReconciler.ts` snapshots classes/selection/position/zoom/pan, detaches or reparents shared nodes and rewires shared edges before removing stale topology, and applies everything inside `cy.batch(...)` so compound removal cannot cascade-delete shared elements.
- Fail-closed tooling: `scripts/run_phase10_backend_tests.py` refuses every forbidden target (ambient `NEO4J_*`/`aura_*` overrides, remote/Aura hosts, the developer-container port, running developer containers, pre-existing container/volume names) before creating anything, proves the effective `Settings` resolve to the ephemeral target with 0 nodes, exports both alias families to children, strips `PYTHONPATH`, and always tears down (`docker rm -f -v`) in a `finally`.
- Offline safety-first test data: checked-in "safe" JSON fixtures that contain only rows visible at their effective boundary, with forbidden-vocabulary scans (`_FORBIDDEN_KEY_RE`, `_forbidden_metadata_keys` in `spoilerless/tests/test_visualization_baseline.py`) and raw-relation-name/forbidden-key tuples (`_RAW_RELATION_NAMES`, `_FORBIDDEN_DTO_KEYS` in `spoilerless/tests/test_visualization_projection.py`).

**Avoid:**
- Do not place business logic or Cypher in FastAPI route functions; follow `spoilerless/app/api/settings.py` through `spoilerless/app/services/settings.py` to `spoilerless/app/repository/settings.py`.
- Do not expose full API keys, validation input, or raw database exceptions; use the masking and error helpers in `spoilerless/app/domain/settings.py` and `spoilerless/app/core/errors.py`.
- Do not use `refetch()` for successful in-place graph mutations when `refresh()` is intended; the distinction in `frontend/src/hooks/useGraph.ts` prevents destructive loading/unmount cycles.
- Do not introduce unconditional state writes in effects, render-time ref mutation, or `any`; these are already the dominant live ESLint debt and should not spread.
- Do not let ambient connection env vars from either alias family (`NEO4J_*` or `aura_*`) reach guarded test runs; the phase10 runner refuses overrides and strips `PYTHONPATH` from child environments.
- Do not serialize raw Neo4j relation names, hidden-field vocabulary (`hidden`, `count`, `total`, `degree`, `restoration`), or group totals into visualization payloads (D-06/D-14); the forbidden-vocabulary and raw-relation assertions in `spoilerless/tests/test_visualization_*.py` enforce this.
- Do not hold `cy` instances or DOM in scene state; state must stay JSON-safe so restoration can never smuggle scene authority (`frontend/src/hooks/useSceneState.ts`).

---

*Convention analysis: 2026-08-14*
