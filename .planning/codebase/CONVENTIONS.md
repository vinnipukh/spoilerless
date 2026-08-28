---
last_mapped: 2026-08-26
focus: quality
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---
<!-- refreshed: 2026-08-26 -->
# Coding Conventions

**Analysis Date:** 2026-08-26

## Naming Patterns

**Files:**
- Use `snake_case.py` for backend modules and keep layers in `spoilerless/app/api/`, `spoilerless/app/services/`, `spoilerless/app/repository/`, and `spoilerless/app/domain/`; examples are `spoilerless/app/api/settings.py`, `spoilerless/app/services/graph.py`, and `spoilerless/app/api/boundary.py`.
- Package decompositions use subdirectories with `__init__.py`: `spoilerless/app/services/visualization/` (`service.py`, `views.py`, `expansion.py`, `focus.py`, `boundary.py`, `node_builders.py`, `constants.py`) and `spoilerless/app/revisions/` (`repository.py`, `service.py`, `__init__.py`).
- Use PascalCase filenames for React components: `frontend/src/components/settings/SettingsPage.tsx`, decomposed tabs in `frontend/src/components/detail/tabs/OverviewTab.tsx`, dialogs in `frontend/src/components/dialogs/CreateCustomNodeDialog.tsx`, and layout primitives in `frontend/src/components/layout/ResizableRail.tsx`.
- Use camelCase filenames for hooks, API clients, tokens, and utilities: `frontend/src/hooks/useWorkspaceScene.ts`, `frontend/src/components/graph/useCytoscapeLayout.ts`, `frontend/src/lib/tokens/graphTokens.ts`, and `frontend/src/lib/graph/sceneElements.ts`.
- Colocate frontend tests as `*.test.ts` or `*.test.tsx`; place backend tests in `spoilerless/tests/test_*.py`.
- Backend suites group by domain family: `test_visualization_*.py`, `test_security_boundary.py`, `test_revisions.py`, `test_rate_limit.py`, `test_share_api.py`.
- Checked-in offline fixtures live in `spoilerless/tests/fixtures/<domain>/`.

**Functions:**
- Use Python `snake_case` for functions and methods (`resolve_effective_boundary`, `require_boundary`, `read_visible_graph`, `execute_query`) and prefix private helpers with `_`, as in `_validate_base_url` in `spoilerless/app/domain/settings.py` and `_sanitize_validation_errors` in `spoilerless/app/core/errors.py`.
- Use TypeScript/React `camelCase` for functions and callbacks (`apiFetch`, `handleCreateNote`, `toCytoscapeElements`) and the `useX` prefix for custom hooks (`useWorkspaceScene`, `useWorkspaceNavigation`, `useCytoscapeLayout`, `useSceneState`).
- Name Python tests `test_<behavior>` and frontend tests with behavior-focused `it('...')` text.
- Prefix route-level test families with the route name: `test_boundary_*` in `spoilerless/tests/test_security_boundary.py`, `test_revisions_*` in `spoilerless/tests/test_revisions.py`.

**Variables:**
- Use Python `snake_case`; module constants are uppercase (`SERVICE_NAME` in `spoilerless/app/main.py`, `FOCUS_SET_CAP` in `spoilerless/app/cache/graph_cache.py`, `RATE_LIMIT_UNAVAILABLE` / `PAYLOAD_TOO_LARGE` in `spoilerless/app/core/errors.py`).
- Use TypeScript `camelCase`; immutable constants use uppercase or descriptive camelCase (`GRAPH_NODE_TYPES`, `graphTokens` in `frontend/src/lib/tokens/graphTokens.ts`).
- Prefix intentionally unused FastAPI dependencies/arguments with `_`, such as `_rate_limit: Annotated[None, Depends(content_write_rate_limiter)]`.

**Types:**
- Use PascalCase for Python classes/Pydantic models (`GraphService`, `VisualizationProjectionService`, `NoteResponse`, `CustomNodeResponse`) and TypeScript types/components (`VisualizationDTO`, `DetailPanelProps`, `SceneState`).
- Model frontend async state with discriminated unions keyed by `status` (e.g. `State` in `frontend/src/hooks/useGraph.ts` and `useRevisions.ts`).
- Prefer literal unions for closed vocabularies: Python uses `Literal[...]` in `spoilerless/app/domain/visualization.py`; TypeScript uses string-literal types in `frontend/src/types/`.
- Pin emitted data-key vocabularies with `as const` arrays at module scope: `NODE_DATA_KEYS`, `EDGE_DATA_KEYS`, `GROUP_DATA_KEYS` in `frontend/src/lib/visualizationAdapter.ts`.
- Error codes use `UPPER_SNAKE_CASE` and must be registered in `ERROR_CODES` in `spoilerless/app/core/errors.py` (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`, `INVALID_VISIBLE_UNTIL_ORDER`, `UNAUTHORIZED`, `FORBIDDEN`, etc.).

## Code Style

**Python formatting:**
- Target Python `>=3.13` as declared in `pyproject.toml`; use modern type annotations (`str | None`, `list[...]`, `dict[...]`) throughout `spoilerless/app/`.
- Start backend modules with `from __future__ import annotations`.
- Maintain clean layer boundaries: keep individual modules focused and under 300–400 lines.
- Use explicit return types on public functions and async methods.

**TypeScript/React formatting:**
- Match the existing no-semicolon, single-quote style across `frontend/src/`.
- Keep component files under a strict 450-line maintainability ceiling: extract tab contents into `components/<feature>/tabs/`, dialogs into `components/dialogs/`, and layout primitives into `components/layout/`.
- Isolate complex lifecycles into dedicated custom hooks (`useWorkspaceScene.ts`, `useCytoscapeLayout.ts`).
- Avoid render-phase `setState` or DOM side-effects; manage state transitions cleanly via event handlers or effect hooks with explicit dependency arrays.
- Standardize on 44px minimum touch targets for interactive elements using `graphTokens.ts` and Tailwind classes.

**Linting:**
- Run `npm run lint` from `frontend/`; `frontend/eslint.config.js` enforces TypeScript, React Hooks, and Vite Refresh rules with 0 errors.
- Keep the warning baseline clean and stable.

## Import Organization

**Python order:**
1. `from __future__ import annotations`.
2. Standard-library imports (`asyncio`, `json`, `typing`, `uuid`).
3. Third-party imports (`fastapi`, `neo4j`, `pydantic`, `pytest`).
4. Absolute project imports rooted at `spoilerless.app`, as in `from spoilerless.app.services.graph import GraphService`.

**TypeScript order:**
1. Framework/package imports (`react`, `cytoscape`, `lucide-react`, `vitest`).
2. Application components and UI primitives (`@/components/...`).
3. Hooks and utilities (`@/hooks/...`, `@/lib/...`).
4. Type-only imports with `import type`.

## Architectural Conventions

**1. God-File Prevention & Component Decomposition:**
- Never create or maintain monolithic components exceeding 500 lines.
- Container components (`App.tsx`, `GraphCanvas.tsx`, `DetailPanel.tsx`) delegate to custom hooks for logic and extract presentational tabs/dialogs into dedicated modules.
- Reusable UI primitives (e.g. `ResizableRail.tsx`, `AppIcons.tsx`) are colocated in `components/layout/`.

**2. Centralized Design System & Tokens:**
- Centralize styling constants, color palettes, node dimensions, border widths, and layout metrics in `frontend/src/lib/tokens/graphTokens.ts`.
- Avoid hardcoded hex colors and magic numbers in component styles; consume semantic tokens or Tailwind utility classes.

**3. Fail-Closed Boundary Resolution:**
- Every spoiler-sensitive endpoint resolves the visible episode boundary through `resolve_effective_boundary()` / `require_boundary` in `spoilerless/app/api/boundary.py`.
- Anonymous and progress-less requests clamp to episode 1; authenticated requests clamp to `min(requested, view_as_of, watched_through)`.
- Never trust caller-supplied boundary parameters directly.

**4. Service Facades & Subpackage Organization:**
- High-level services coordinate domain logic across repositories. Use `GraphService` (`spoilerless/app/services/graph.py`) as the facade for visible graph reads and cache invalidation.
- Complex subsystems are decomposed into subpackages with explicit module responsibilities (`spoilerless/app/services/visualization/`, `spoilerless/app/revisions/`).

**5. Cypher Query Efficiency:**
- Avoid query amplification. Consolidate related existence and visibility checks into single Cypher transactions (as implemented in `spoilerless/app/graph/candidates.py`).

## Error Handling

**Backend patterns:**
- Expose sanitized JSON envelopes: `{detail: {code, message}}`.
- All error codes must be uppercase and registered in `ERROR_CODES` in `spoilerless/app/core/errors.py`.
- `RateLimiter` implements lazy re-initialization on startup connection blips; in production with `rate_limit_fail_open=false`, Redis outage returns `503 RATE_LIMIT_UNAVAILABLE`.
- Request validation logs drop raw `input`/`ctx` data via `_sanitized_validation_errors` (SEC-LOG-001).
- Enforce request body limits at the ASGI layer via `BodySizeLimitMiddleware` (413 `PAYLOAD_TOO_LARGE`).

**Frontend patterns:**
- Route API requests through `apiFetch<T>` in `frontend/src/api/client.ts`.
- Display actionable error states in UI panels; differentiate rate-limit 429 errors from server busy / outage errors.
- Support safe fallbacks and empty states across tabs and dialogs.

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **Frontend Component Decomposition Conventions:** Established strict 450-line maintainability ceiling; container decomposition pattern into custom hooks (`useWorkspaceScene`, `useCytoscapeLayout`) and dedicated tab/dialog components.
- **Design Tokens Standardization:** Adopted `graphTokens.ts` for centralized node/edge styling and 44px touch targets.
- **Backend Subpackage Decomposition:** Replaced monolithic services with structured subpackages (`visualization/`, `revisions/`) keeping individual files under 300 lines.
- **Boundary Injection Pattern:** Standardized on `require_boundary` FastAPI dependency for spoiler-sensitive routes.
- **Uppercase Error Code Registration:** Ensured all error codes (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`) are uppercase and registered in `ERROR_CODES`.

---

*Conventions audit: 2026-08-26*
