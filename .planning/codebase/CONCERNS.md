---
last_mapped: 2026-07-28
focus: concerns
---

# Concerns

## Summary

The codebase is early-stage and prototype-heavy. The biggest risks are startup fragility around Neo4j, drift between the static product prototype and the scaffolded React app, and missing tests/CI.

## Backend Concerns

### Duplicate FastAPI App Construction

`backend/app/main.py` constructs `app = FastAPI(...)` twice with the same title/version/lifespan. The second assignment replaces the first object. This is harmless in the current file because middleware/routes are added after the second assignment, but it is confusing and should be removed before adding more app setup.

### Import-Time Neo4j Driver Creation

`backend/app/graph/database.py` creates `neo4j_db = Neo4jDatabase()` at module import time. Because `Neo4jDatabase.__init__()` reads settings and creates the driver immediately, tests or CLI tooling can fail before they have a chance to override configuration.

### Startup Requires Live Neo4j

`backend/app/main.py` calls `neo4j_db.verify_connection()` during FastAPI lifespan startup. This is good for fail-fast production behavior, but it can make local development and tests brittle without a documented Neo4j startup path.

### No Docker Compose or Setup Script

The repository ignores local Neo4j runtime folders but does not include a `docker-compose.yml` or equivalent setup command for starting Neo4j. New developers must infer setup from `.env.example` and dependencies.

### Direct Database Access in Routes

`backend/app/api/series.py` opens Neo4j sessions directly in route handlers. This is simple, but it will make testing, mocking, and transaction/error handling harder as features grow.

### Limited Error Handling

The episode route returns a 404 if no episodes are found, but database connectivity/query errors are not translated into application-level responses.

## Frontend Concerns

### React App Still Scaffolded

`frontend/src/App.tsx` still renders Vite starter content and imports React/Vite logos. It does not yet implement the `HD Graf Cehennemi` product UI or call backend APIs.

### Static Prototype Drift

Root `index.html` contains a rich static product prototype with graph UI concepts, spoiler controls, and citation panels. This may drift from the actual React implementation unless it is treated as a reference and migrated deliberately.

### Cytoscape Installed but Unused

`frontend/package.json` includes `cytoscape` and `react-cytoscapejs`, but no checked-in component uses them yet. This indicates planned graph visualization, not implemented functionality.

## Product/Data Concerns

### Minimal Seed Data

`data/dexter/metadata/episodes.json` only includes three episodes. The current graph can validate episode listing, but it cannot yet validate broader spoiler-aware knowledge graph behavior.

### Spoiler Model Not Implemented Yet

The backend only stores `visible_from_order` on episodes. There is no checked-in graph model yet for characters, events, claims, sources, or episode-bounded visibility rules.

### LLM/Citation Claims Are Not Implemented Yet

The landing page promises LLM-supported, source-cited graph information, but the backend has no LLM provider integration, source store, ingestion pipeline, or citation API yet.

## Testing/Quality Concerns

- No visible backend tests.
- No frontend test runner beyond lint/build.
- No visible CI configuration.
- No project README with setup and verification instructions.
- Root `main.py` is still the PyCharm sample and should probably be removed if unrelated.

## Security Notes

- `.env` is ignored and `.env.example` uses placeholders; no real secrets were read or documented.
- Avoid committing local Neo4j runtime directories; `.gitignore` already excludes them.
- Future LLM/API integrations should add secret handling before provider keys are introduced.
