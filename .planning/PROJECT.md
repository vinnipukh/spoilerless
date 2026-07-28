# HD Graf Cehennemi

## What This Is

A spoiler-safe narrative knowledge graph for TV series. Users browse characters, events, claims, and evidence — like an Obsidian-style second brain for a show — while a spoiler boundary hides everything beyond the last episode they've watched. The prototype starts with Dexter Season 1, Episodes 1–3.

The system fuses a Neo4j graph database (nodes: characters, episodes, claims, sources; edges: KNOWS, KILLS, PART_OF, etc.) with a FastAPI backend that enforces spoiler gating at the data-access layer, and a React + Cytoscape.js frontend for visual exploration.

## Core Value

Users can safely explore a TV series knowledge graph without ever seeing spoilers — the backend guarantees the frontend never receives data beyond their selected watch progress.

## Requirements

### Validated
<!-- Shipped and confirmed valuable via existing codebase. -->

- ✓ Neo4j database connection via Docker Compose — existing
- ✓ FastAPI backend scaffold with lifespan, CORS, health endpoint — existing
- ✓ Neo4j driver singleton with verify/close lifecycle — existing
- ✓ Pydantic settings via pydantic-settings from .env — existing
- ✓ Series and Episode Pydantic response models — existing
- ✓ `GET /api/series` endpoint — existing
- ✓ `GET /api/series/{series_id}/episodes` endpoint — existing
- ✓ Seed script: Neo4j constraints, series/episode MERGE, PART_OF and PRECEDES relationships — existing (unexecuted)
- ✓ Dexter metadata files (series.json, episodes.json for S01E01-03) — existing
- ✓ Ontology YAML files (node_types, relation_types, claim_types) — existing
- ✓ Vite + React + TypeScript + Cytoscape.js frontend scaffold — existing
- ✓ .env.example with Neo4j config — existing
- ✓ .gitignore — existing
- ✓ Docker Compose for Neo4j 2026-community — existing

### Active
<!-- Current prototype scope — building toward v0 demo. -->

- [ ] **INFRA-01**: Health endpoint actually verifies Neo4j connectivity (currently hardcoded "connected")
- [ ] **INFRA-02**: Seed script can be run as a reliable setup step
- [ ] **DATA-01**: Character, source, evidence, and claim seed files for Dexter S01E01 character network
- [ ] **DATA-02**: Seed script creates character/source/evidence/claim nodes and relationships
- [ ] **GRAPH-01**: Spoiler-aware graph endpoint `GET /api/graph?series_id=...&visible_until_order=N` that returns only nodes/relationships visible within the user's spoiler boundary
- [ ] **GRAPH-02**: Every node has a `visible_from_order` field; every relationship respects it
- [ ] **GRAPH-03**: `visible_from_order` and `valid_from_order`/`valid_until_order` on claims for temporal validity
- [ ] **UI-01**: Frontend replaces Vite starter with product layout
- [ ] **UI-02**: Episode progress selector with spoiler confirmation modal
- [ ] **UI-03**: Cytoscape.js graph rendering from backend data
- [ ] **UI-04**: Node detail panel (shows node info, claims, evidence links)
- [ ] **UI-05**: Edge/claim detail panel
- [ ] **NOTE-01**: UserNote model, CRUD endpoints, and frontend display
- [ ] **NOTE-02**: User-created nodes and relationships (custom additions to the graph)
- [ ] **REV-01**: Revision model that logs claim creation, updates, rejection, user corrections
- [ ] **REV-02**: Revision display panel and revert operation
- [ ] **LLM-01**: Candidate claim layer, review/approve/reject workflow, source connector interface
- [ ] **TEST-01**: Backend unit tests for spoiler boundaries, routes, seed
- [ ] **TEST-02**: Frontend lint, build, and basic component tests
- [ ] **CI-01**: GitHub Actions workflow for test/lint/build on push

### Out of Scope

<!-- Explicit boundaries from the existing roadmap. -->

- OpenSubtitles automation — deferred to post-v0
- Script PDF parsing — deferred to post-v0
- Podcast transcription — deferred to post-v0
- Fandom/IMDb/news ingestion — deferred to post-v0
- Full LLM extraction pipeline — deferred to post-v0
- Multi-user accounts — not needed for single-user prototype
- Production authentication — not needed for local prototype
- Deployment (Docker build, cloud hosting) — not needed for local prototype

## Context

The prototype is bootstrapped with a full codebase map, ontology, seed data, and scaffolded frontend/backend. The core graph model (Series → Episode → Character → Claim → Source/Evidence) is designed but not yet persisted. The spoiler-boundary model — every graph element carries a `visible_from_order` integer — is the central architectural invariant.

Static `index.html` at project root is a comprehensive product/demo prototype in Turkish. It functions as a design reference for the React frontend implementation but is NOT wired to any backend.

## Constraints

- **Spoiler safety**: Every node, claim, and relationship MUST carry a `visible_from_order` field. Backend MUST filter before returning data. LLM MUST never receive data beyond user's progress.
- **Provenance**: Every automatic claim MUST be backed by at least one EvidenceFragment with source, episode reference, and locator.
- **Separation**: User-created content and automatic/canonical content are stored separately and visually distinct.
- **Python >=3.13**: Required by pyproject.toml. Using uv for package management.
- **Neo4j 2026-community**: Docker Compose with Neo4j 2026; graph is the single source of truth.
- **Frontend**: Vite + React 19 + TypeScript + Cytoscape.js. TS strict mode and ESLint required.
- **No real auth**: Single-user local prototype; authentication is out of scope.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Neo4j as single source of truth | Graph-native storage suits the highly-connected data model; avoids dual SQL/graph mapping | ✓ Good |
| `visible_from_order` on every node | Enforces spoiler gating at the data layer — impossible to accidentally leak data | ✓ Good |
| Simplified revision log (not Git) | Prototype scope; Git-based graph versioning is excessive for v0 | — Pending |
| Separate user vs canonical content | Users can correct/add without corrupting curated data; clear provenance | ✓ Good |
| `relationship_effect` vs `confidence_level` | Two orthogonal dimensions: narrative strength vs system certainty | ✓ Good |

---
*Last updated: 2026-07-28 after GSD initialization*
