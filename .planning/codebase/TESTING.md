---
last_mapped: 2026-07-28
focus: quality
---

# Testing

## Current Status

There are no visible test files in the checked-in project at mapping time. The manifests include test tooling, but no backend or frontend test suites are currently present.

## Backend Test Tooling

`pyproject.toml` defines a dev dependency group with:

- `pytest>=9.1.1`
- `httpx>=0.28.1`

These are appropriate for FastAPI testing with `TestClient`/HTTPX-backed clients, but no `tests/` directory or `test_*.py` files are visible.

## Backend Test Considerations

Current backend design has a few implications for future tests:

- `backend/app/graph/database.py` creates `neo4j_db` at import time.
- `backend/app/main.py` imports that singleton and verifies connectivity during app lifespan startup.
- Route functions in `backend/app/api/series.py` directly open Neo4j sessions.

For reliable unit tests, future work should either:

1. Introduce a dependency injection boundary for graph access, or
2. Patch/replace `neo4j_db` carefully in tests before importing/running the app, or
3. Run integration tests against a real test Neo4j instance.

## Frontend Test Tooling

`frontend/package.json` includes no test script. Existing scripts are:

- `npm run dev` — Vite dev server.
- `npm run build` — `tsc -b && vite build`.
- `npm run lint` — ESLint.
- `npm run preview` — Vite preview.

No Vitest, React Testing Library, Playwright, or Cypress dependencies are present.

## Frontend Quality Gates Available Today

The practical frontend verification commands today are:

- `npm run lint` from `frontend/`.
- `npm run build` from `frontend/`.

The build includes TypeScript project build and Vite bundling.

## Manual Verification Targets

Current manually verifiable behaviors:

- Backend `/health` returns service status after Neo4j startup succeeds.
- Backend `/api/series` lists seeded series records.
- Backend `/api/series/{series_id}/episodes` lists seeded episodes or returns 404 when no records are found.
- Frontend Vite app renders starter content.
- Root `index.html` renders a static product landing/demo page.

## Testing Gaps

- No automated tests for Neo4j seed behavior.
- No automated tests for route response shapes or 404 behavior.
- No automated tests for CORS configuration.
- No frontend component tests.
- No end-to-end tests that verify the graph visualization/product flow.
- No CI workflow runs lint/build/test on push.
