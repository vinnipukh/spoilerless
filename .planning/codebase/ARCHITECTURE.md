---
last_mapped: 2026-07-28
focus: arch
---

# Architecture

## Summary

The repository is a prototype for a spoiler-controlled, source-backed TV-series knowledge graph. The current architecture is a thin FastAPI backend over Neo4j plus a separate React/Vite frontend scaffold. A static root `index.html` holds a fuller visual/product prototype that is not yet wired to the React app.

## Backend Architecture

### Layers

- API layer: `backend/app/api/series.py`
  - Defines HTTP routes and translates Neo4j records to Pydantic response models.
- Domain schema layer: `backend/app/domain/series.py`
  - Defines `SeriesResponse` and `EpisodeResponse` models.
- Graph persistence layer: `backend/app/graph/database.py`
  - Owns driver creation, connectivity verification, and driver closing.
- Graph seed layer: `backend/app/graph/seed.py`
  - Loads JSON fixture data and writes initial graph nodes/relationships.
- Configuration layer: `backend/app/core/config.py`
  - Reads Neo4j settings from environment or `.env`.

### Request Flow

1. A browser/client calls an endpoint mounted from `backend/app/main.py`.
2. The series router in `backend/app/api/series.py` handles the request.
3. The route opens a Neo4j session using `neo4j_db.driver.session(database=neo4j_db.database)`.
4. The route runs an inline Cypher query.
5. Each returned record is converted with `record.data()`.
6. Pydantic response models in `backend/app/domain/series.py` shape the response.

### Startup Flow

1. Importing `backend/app/graph/database.py` creates the global Neo4j driver.
2. FastAPI startup calls `neo4j_db.verify_connection()` via the lifespan hook in `backend/app/main.py`.
3. Shutdown calls `neo4j_db.close()`.

## Graph Data Model

Current graph concepts from `backend/app/graph/seed.py` and `backend/app/api/series.py`:

- `Series` node with `id`, `title`, and `slug`.
- `Episode` node with `id`, `series_id`, season/episode/order fields, `code`, `title`, and `visible_from_order`.
- `(:Episode)-[:PART_OF]->(:Series)` relationship.
- `(:Episode)-[:PRECEDES]->(:Episode)` relationship for episode order.

The spoiler boundary is represented only as `visible_from_order` on episodes so far. There is no checked-in entity/claim/source graph model yet.

## Frontend Architecture

- `frontend/src/main.tsx` creates a React root and renders `App` in `StrictMode`.
- `frontend/src/App.tsx` is still scaffold-like and renders local assets plus Vite links.
- `frontend/src/index.css` and `frontend/src/App.css` define the starter layout and styles.
- `frontend/package.json` includes Cytoscape dependencies, indicating planned graph visualization, but `App.tsx` does not use Cytoscape yet.

## Static Landing Prototype

Root `index.html` is a complete static page with product copy, visual graph UI styling, spoiler-progress controls, detail panels, and citation/source UI concepts. It functions as a design/prototype artifact separate from the React frontend.

## Component Boundaries

- Backend and frontend are separate directories with separate dependency manifests.
- Backend exposes HTTP JSON endpoints and directly owns graph persistence.
- Frontend currently has no API boundary implementation.
- Seed data is file-based JSON under `data/dexter/metadata/`, consumed only by the backend seed script.

## Build Order Implications

A practical build order is:

1. Stabilize backend app construction and Neo4j startup behavior.
2. Expand graph schema and seed data beyond series/episodes.
3. Add frontend API client and replace scaffold UI with product UI.
4. Integrate Cytoscape graph rendering.
5. Add spoiler-gating rules and source-backed claims.
