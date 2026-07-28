---
last_mapped: 2026-07-28
focus: tech
---

# Integrations

## Summary

The codebase currently has one real backend integration: Neo4j. The frontend and static prototype do not yet call backend APIs in checked-in React code. The static `index.html` is self-contained and does not integrate with services.

## Neo4j

### Configuration

Neo4j connection settings are modeled in `backend/app/core/config.py`:

- `neo4j_uri`
- `neo4j_username`
- `neo4j_password`
- `neo4j_database`, defaulting to `neo4j`

The settings class uses `pydantic-settings` with `.env` loading enabled. `.env` is gitignored; `.env.example` documents local placeholder values such as `neo4j://localhost:7687` and `change-me`.

### Driver Ownership

`backend/app/graph/database.py` defines `Neo4jDatabase`, which:

- Reads settings during object initialization.
- Creates a `neo4j.GraphDatabase.driver` with basic auth.
- Exposes `.driver` and `.database` properties.
- Verifies connectivity via `verify_connection()`.
- Closes the driver via `close()`.

The module instantiates a global `neo4j_db = Neo4jDatabase()` at import time.

### FastAPI Lifespan

`backend/app/main.py` verifies Neo4j connectivity during app startup through the FastAPI lifespan hook and closes the driver on shutdown. This means missing environment variables or unavailable Neo4j can fail at import/startup time rather than lazily on the first request.

### Query Usage

`backend/app/api/series.py` uses direct Cypher queries for read endpoints:

- `MATCH (series:Series)` for listing series.
- `MATCH (episode:Episode)-[:PART_OF]->(series:Series {id: $series_id})` for listing episodes.

`backend/app/graph/seed.py` uses Cypher for setup:

- Creates unique constraints for `Series.id` and `Episode.id`.
- `MERGE`s a series and episodes from JSON metadata.
- Creates `PART_OF` relationships.
- Creates `PRECEDES` relationships between consecutive episodes.

## Browser/API Integration

The backend enables CORS for `http://localhost:5173` in `backend/app/main.py`, implying the intended local frontend origin is the Vite dev server.

The checked-in React app in `frontend/src/App.tsx` does not currently fetch from `/api/series` or any backend URL. It still renders Vite starter content.

## External Web Links

`frontend/src/App.tsx` links to public Vite/React/GitHub/Discord/X/Bluesky resources from the scaffolded template. These are not product integrations.

## Missing or Not Yet Present

- No authentication provider integration.
- No LLM provider integration in backend code yet, despite the landing page describing LLM-assisted graph information.
- No citation/source ingestion integration yet.
- No Docker Compose or managed Neo4j setup file checked in.
- No frontend API client abstraction yet.
