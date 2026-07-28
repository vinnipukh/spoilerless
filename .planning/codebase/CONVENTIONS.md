---
last_mapped: 2026-07-28
focus: quality
---

# Conventions

## Python Style

- Python code uses type annotations for functions and return values.
- Imports are grouped as standard library, third-party, then local imports.
- FastAPI route handlers return typed Pydantic model lists, e.g. `list[SeriesResponse]`.
- Pydantic models are defined as simple `BaseModel` classes in domain modules.
- Field validation uses `pydantic.Field`, as in `EpisodeResponse` integer fields with `ge=1`.
- Settings are centralized in `backend/app/core/config.py` and cached with `functools.lru_cache`.
- Neo4j access currently uses direct session handling inside route functions rather than a repository/service abstraction.

## Backend API Patterns

- Routers are created with `APIRouter(prefix=..., tags=...)`.
- Routes use plain synchronous functions.
- Cypher queries are written inline as triple-quoted strings inside route handlers.
- Neo4j query parameters are passed separately to `session.run()` where needed.
- `HTTPException` is used for route-level errors; the existing 404 message in `backend/app/api/series.py` is Turkish.

## Configuration Patterns

- Environment settings are read from `.env` via `pydantic-settings`.
- `.env` and `.env.*` are ignored, while `.env.example` remains tracked.
- Local examples use Neo4j default username/database and placeholder password.

## Frontend Style

- React code uses function components and hooks.
- TypeScript/React source uses single quotes and no semicolons.
- `frontend/src/main.tsx` imports `App` with the explicit `.tsx` extension, allowed by `tsconfig.app.json`.
- CSS uses modern nested syntax in `frontend/src/App.css` and media queries nested inside selectors.
- The Vite app still follows starter component structure.

## TypeScript Strictness

`frontend/tsconfig.app.json` enables:

- `noUnusedLocals`
- `noUnusedParameters`
- `erasableSyntaxOnly`
- `noFallthroughCasesInSwitch`
- `verbatimModuleSyntax`
- `moduleResolution: bundler`
- `jsx: react-jsx`

These settings will reject unused imports/variables and some non-erasable TypeScript constructs.

## Linting

`frontend/eslint.config.js` uses ESLint flat config with:

- `@eslint/js` recommended rules.
- `typescript-eslint` recommended rules.
- `eslint-plugin-react-hooks` recommended rules.
- `eslint-plugin-react-refresh` Vite rules.
- Browser globals via `globals.browser`.

## Git Hygiene

`.gitignore` deliberately excludes local runtime artifacts:

- Python caches and virtual environments.
- Node modules and frontend build output.
- `.env` variants except `.env.example`.
- Neo4j local data/log/plugins/import directories.
- IDE folders.

## Documentation Conventions

No project README or architecture docs are visible yet. GSD planning docs under `.planning/` should become the main source of project context until product docs are created.
