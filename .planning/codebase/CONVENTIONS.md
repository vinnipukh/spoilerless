---
last_mapped: 2026-07-30
focus: quality
---

# Conventions

## Python Style

- Every module starts with `from __future__ import annotations`.
- Full type annotations on function signatures and return values throughout `backend/app/`.
- Imports are grouped stdlib, third-party, then local (`backend.app.*`) — see `backend/app/api/candidates.py`.
- Pydantic models use `BaseModel` with `ConfigDict(extra="forbid")` for strict request/response contracts (`backend/app/core/errors.py`, `backend/app/domain/extraction.py`).
- `Annotated[...]` + `Depends(...)` is the standard pattern for FastAPI dependencies and path/query params, e.g. `SeriesId = Annotated[Identifier, Path(description=...)]` in `backend/app/api/candidates.py`.
- Domain-specific typed IDs (`Identifier`) live in `backend/app/domain/user_content.py` and are reused across routers instead of raw `str`.
- Settings are centralized in `backend/app/core/config.py`, cached with `functools.lru_cache`.
- Repository classes wrap Neo4j access per resource type, e.g. `CandidateRepository` (`backend/app/graph/candidates.py`), `RevisionRepository` (`backend/app/revisions.py`) — constructed with `Neo4jDatabase` injected via `get_database`. This supersedes the earlier pattern of opening sessions directly inside route handlers.
- Cypher queries are written as triple-quoted string constants or private helper functions returning query text (e.g. `_read_claim_query()` in `backend/app/api/candidates.py`), not inlined ad hoc in every handler.
- Module-level query constants in test/repo code use `SCREAMING_SNAKE_CASE` (e.g. `USER_ONLY_CLEANUP_QUERY`, `SECOND_SERIES_SETUP_QUERY` in `backend/tests/test_user_content_api.py`).
- Async functions (`async def`) are used for all Neo4j-touching route handlers and repository methods; sync helpers stay sync.

## Backend API Patterns

- Routers: `APIRouter(prefix="/api/series/{series_id}/<resource>", tags=[...])` — one router per resource under `backend/app/api/` (`series.py`, `graph.py`, `revisions.py`, `candidates.py`, `user_content.py`, `auth.py`).
- Errors use the shared envelope from `backend/app/core/errors.py`: `http_error(status_code, code, message)` raises `HTTPException` with `detail={"code": ..., "message": ...}`; `error_responses(404, 409, ...)` documents them in OpenAPI via a route's `responses=` kwarg.
- Error `code` strings are `snake_case`, validated by `ErrorDetail.code` pattern `^[a-z][a-z0-9_]*$` (e.g. `cannot_revert_create`, `cannot_revert_canonical`, `resource_not_found`, `invalid_request`, `database_unavailable`).
- Global exception handlers are installed once via `install_error_handlers(app)` in `backend/app/main.py`, covering `RequestValidationError`, `ConstraintError`, and Neo4j `ServiceUnavailable`/`AuthError`/`ClientError`/`Neo4jError` — individual routes should raise `http_error(...)` rather than reinventing error envelopes.
- Spoiler-boundary pattern: read routes accept a `visible_until_order` query param; write routes stamp resources with `visible_from_order`. Resources hidden by the boundary return 404 identical to genuinely missing resources — see `TestRevisionSpoilerBoundary` in `backend/tests/test_revisions.py` and the `assert_hidden_matches_missing` helper in `backend/tests/test_user_content_api.py`.
- Resource IDs are prefixed strings encoding type/origin, e.g. `extracted:<hash>` for candidate claims (`backend/app/api/candidates.py`), `revision:<id>` for revisions, `user-note:<id>` for notes.
- An `origin` field (`"canonical"` | `"user"` | `"candidate"`) marks provenance on graph nodes/relationships and gates mutation — e.g. reverting a resource whose `origin` is `"canonical"` returns 409 `cannot_revert_canonical`.

## Configuration Patterns

- Environment settings read from `.env` via `pydantic-settings`; `.env`/`.env.*` are ignored, `.env.example` is tracked.
- Test bootstrap (`backend/tests/conftest.py`) sets `NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD`/`NEO4J_DATABASE` env defaults via `os.environ.setdefault(...)` before app import, and inserts `backend/` and repo root onto `sys.path` so `backend.app.*` and `backend.tests.*` imports resolve.

## Frontend Style

- React function components + hooks throughout; no class components.
- TypeScript/React source uses single quotes and no semicolons.
- Component tests are colocated next to the implementation: `Foo.tsx` + `Foo.test.tsx` in the same directory (e.g. `frontend/src/components/detail/StructuralEdgeCard.tsx` / `.test.tsx`, `frontend/src/components/graph/GraphCanvas.tsx` / `.test.tsx`).
- Custom hooks live in `frontend/src/hooks/` (`useRevisions.ts`, `useWatchProgress.ts`), each with a colocated `.test.tsx`/`.test.ts`.
- API client functions live in `frontend/src/api/` (e.g. `frontend/src/api/revisions.ts`) and are the sole place `fetch` is called; hooks and components call these functions and mock them in tests via `vi.mock('../api/...')`.
- Domain types live in `frontend/src/types/` (e.g. `frontend/src/types/revision.ts`) and are imported with `import type { ... }` (required by `verbatimModuleSyntax`).
- shadcn/ui + Radix primitives (`Select`, `Dialog`, `Sheet`, `Tabs`) are used for interactive UI; Tailwind utility classes for styling, no CSS modules.
- Path alias `@` resolves to `frontend/src` (configured in `frontend/vite.config.ts` and `tsconfig.app.json`).
- `frontend/src/main.tsx` imports `App` with explicit `.tsx` extension, permitted by `tsconfig.app.json`.

## TypeScript Strictness

`frontend/tsconfig.app.json` enables:

- `noUnusedLocals`
- `noUnusedParameters`
- `erasableSyntaxOnly`
- `noFallthroughCasesInSwitch`
- `verbatimModuleSyntax`
- `moduleResolution: bundler`
- `jsx: react-jsx`

These settings reject unused imports/variables and some non-erasable TypeScript constructs. `verbatimModuleSyntax` means type-only imports must use `import type { ... }`.

## Linting

`frontend/eslint.config.js` uses ESLint flat config with:

- `@eslint/js` recommended rules.
- `typescript-eslint` recommended rules.
- `eslint-plugin-react-hooks` recommended rules.
- `eslint-plugin-react-refresh` Vite rules.
- Browser globals via `globals.browser`.

## Git Hygiene

`.gitignore` excludes:

- Python caches and virtual environments.
- Node modules and frontend build output.
- `.env` variants except `.env.example`.
- Neo4j local data/log/plugins/import directories.
- IDE folders.

## Documentation Conventions

No project README or architecture docs beyond GSD planning. `.planning/` (`STATE.md`, `MILESTONES.md`, `milestones/`, `codebase/`) is the source of truth for project context and decisions. Domain behavior (spoiler boundary, origin provenance, revision lifecycle, candidate ingest) is documented inline via test class/docstring references to requirement IDs (e.g. `REV-01`, `REV-02`, `REV-03`, `PREP-02`, `PREP-05`, `D-09`, `D-11`, `D-14`) rather than in separate prose docs — grep test files for a requirement ID to find its behavioral spec.

---

*Convention analysis: 2026-07-30*
