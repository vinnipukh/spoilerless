---
last_mapped: 2026-08-12
focus: quality
last_mapped_commit: 1710d57db7c048a83299cadc072e0779f80f246d
---
# Coding Conventions

**Analysis Date:** 2026-08-12

## Naming Patterns

**Files:**
- Use `snake_case.py` for backend modules and keep layers in `spoilerless/app/api/`, `spoilerless/app/services/`, `spoilerless/app/repository/`, and `spoilerless/app/domain/`; examples are `spoilerless/app/api/settings.py` and `spoilerless/app/services/settings.py`.
- Use PascalCase filenames for React components, such as `frontend/src/components/settings/SettingsPage.tsx`, and camelCase filenames for hooks, API clients, and utilities, such as `frontend/src/hooks/useGraph.ts` and `frontend/src/api/client.ts`.
- Colocate frontend tests as `*.test.ts` or `*.test.tsx`; place backend tests in `spoilerless/tests/test_*.py`.

**Functions:**
- Use Python `snake_case` for functions and methods (`get_llm_settings`, `execute_query`) and prefix private helpers with `_`, as in `_validate_base_url` in `spoilerless/app/domain/settings.py`.
- Use TypeScript/React `camelCase` for functions and callbacks (`apiFetch`, `handleCreateNote`) and the `useX` prefix for hooks (`useGraph`) in `frontend/src/hooks/`.
- Name Python tests `test_<behavior>` and frontend tests with behavior-focused `it('...')` text; examples are in `spoilerless/tests/test_openapi_contract.py` and `frontend/src/components/settings/SettingsPage.test.tsx`.

**Variables:**
- Use Python `snake_case`; module constants are uppercase (`SERVICE_NAME` in `spoilerless/app/main.py`, `DEFAULT_GEMINI_BASE_URL` in `spoilerless/app/domain/settings.py`).
- Use TypeScript `camelCase`; immutable fixture-like values use descriptive lower camel case (`defaultSettings` in `frontend/src/components/settings/SettingsPage.test.tsx`).
- Prefix intentionally unused FastAPI dependencies/arguments with `_`, such as `_user` in `spoilerless/app/api/settings.py` and `_rate_limit: Annotated[None, Depends(login_rate_limiter)]` in `spoilerless/app/api/auth.py`.

**Types:**
- Use PascalCase for Python classes/Pydantic models (`SettingsService`, `LLMSettingsResponse`) and TypeScript types/components (`ApiErrorDetail`, `SettingsPage`).
- Model frontend async state with discriminated unions keyed by `status`, as demonstrated by `State` in `frontend/src/hooks/useGraph.ts`.
- Prefer literal unions for closed vocabularies: Python uses `Literal[...]` in `spoilerless/app/domain/settings.py`; TypeScript uses string-literal fields in `frontend/src/types/`.

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
- The live lint run on 2026-08-12 reports 0 errors and 39 warnings, all `react-hooks/refs` (render-time ref reads) in files including `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/detail/DetailPanel.tsx`, and revision tests. The gate now passes; keep the warning count from growing and do not introduce new error-class findings.

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
- Catch only expected failures when a safe fallback exists. `SettingsRepository.get_llm()` returns `None` for malformed stored JSON in `spoilerless/app/repository/settings.py`; startup intentionally catches connection failure so `/health` can report degraded state in `spoilerless/app/main.py`.
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

**Docstrings/JSDoc:**
- Use module/class/function docstrings for backend contracts and non-obvious behavior (`spoilerless/app/core/errors.py`, `spoilerless/app/services/settings.py`).
- JSDoc/TSDoc is sparse in the frontend; prefer precise inline comments around lifecycle and compatibility behavior, as in `frontend/src/hooks/useGraph.ts` and `frontend/src/api/client.ts`.

## Function Design

**Size:**
- Keep API handlers thin: inject dependencies, delegate to services, and return typed models, as in `spoilerless/app/api/settings.py`.
- Put persistence serialization and Cypher in repositories (`spoilerless/app/repository/settings.py`), effective-value/business rules in services (`spoilerless/app/services/settings.py`), and validation/contracts in domain models (`spoilerless/app/domain/settings.py`).
- Frontend hooks own asynchronous state transitions, API modules own transport, and components own rendering/interactions; examples are `frontend/src/hooks/useGraph.ts`, `frontend/src/api/client.ts`, and `frontend/src/components/settings/SettingsPage.tsx`.

**Parameters:**
- Prefer dependency injection and typed constructor parameters in backend services/repositories. FastAPI dependency aliases use `Annotated[..., Depends(...)]` in `spoilerless/app/api/settings.py`.
- Prefer typed props objects and callback props for React components; avoid `any` except narrow compatibility shims such as the documented React 19 fallback in `frontend/src/test/setup.ts`.

**Return values:**
- Backend functions return Pydantic models or explicit typed dictionaries/lists; repository reads use `None` for absence and services resolve defaults.
- Frontend API functions return `Promise<T>`; hooks return discriminated state plus named actions (`refetch`, `refresh`) in `frontend/src/hooks/useGraph.ts`.

## Module Design

**Exports:**
- Backend modules expose routers, services, repositories, models, and named helpers; layer imports should flow `api` → `services` → `repository`/`graph`, with shared contracts in `spoilerless/app/domain/`.
- Frontend uses named exports for application functions/components and default exports mainly where libraries/tooling expect them (for example Vite config and some generated UI patterns).

**Barrel files:**
- `spoilerless/app/**/__init__.py` files are mostly package markers; imports generally target concrete modules rather than broad barrels.
- The frontend has no general barrel-index convention; import concrete modules to keep dependencies explicit.

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

**Avoid:**
- Do not place business logic or Cypher in FastAPI route functions; follow `spoilerless/app/api/settings.py` through `spoilerless/app/services/settings.py` to `spoilerless/app/repository/settings.py`.
- Do not expose full API keys, validation input, or raw database exceptions; use the masking and error helpers in `spoilerless/app/domain/settings.py` and `spoilerless/app/core/errors.py`.
- Do not use `refetch()` for successful in-place graph mutations when `refresh()` is intended; the distinction in `frontend/src/hooks/useGraph.ts` prevents destructive loading/unmount cycles.
- Do not introduce unconditional state writes in effects, render-time ref mutation, or `any`; these are already the dominant live ESLint debt and should not spread.

---

*Convention analysis: 2026-08-12*
