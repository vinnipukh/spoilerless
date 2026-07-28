# HD Graf Cehennemi — Prototype v0 Roadmap

**Project:** HD Graf Cehennemi — Spoiler-Safe Narrative Knowledge Graph  
**Core Value:** Users can safely explore a TV series knowledge graph without ever seeing spoilers — the backend guarantees the frontend never receives data beyond their selected watch progress.  
**Project Mode:** mvp (Vertical MVP — each phase delivers an end-to-end user capability, not technical layers)  
**Granularity:** coarse  

---

## Phase 1: Backend Infrastructure & Seed Data

**Goal:** Fix backend architecture issues, stabilize Neo4j connection, create seed data pipeline, and seed the Dexter S01E01-03 character graph — delivering a working backend with verified connectivity, reliable seeding, and passing tests.

**Mode:** mvp

### Success Criteria

1. **Real health check** — `GET /health` returns actual Neo4j connection status (not a hardcoded string), distinguishing between "connected", "disconnected", and "unavailable".
2. **Reliable one-step seed** — `cd backend && uv run seed` creates all nodes (Series, Episode, Character, Claim, Source, EvidenceFragment) and relationships (PART_OF, PRECEDES, KNOWS, FAMILY_OF, KILLS, WORKS_WITH) without errors.
3. **Idempotent seeding** — Running the seed script twice produces exactly one copy of every node and relationship (conflict-free MERGE semantics).
4. **Testable architecture** — Lazy Neo4j driver initialization allows the test suite to run without a running Neo4j instance; all Cypher queries use parameterized `$param` placeholders and managed transactions via `execute_query`.
5. **Architecture hygiene** — Duplicate FastAPI app construction is removed; Neo4j driver errors return meaningful HTTP responses (502/503) rather than raw driver exceptions.

### Plans

#### Plan 1.1 — Fix Backend Architecture Issues
**Covers:** ARCH-01, ARCH-04, ARCH-05

- Refactor Neo4j driver from import-time singleton to lazy initialization via FastAPI lifespan (store on `app.state`).
- Remove duplicate FastAPI app construction in `main.py` — ensure single `FastAPI()` instance.
- Add exception handler middleware that catches `Neo4jDriverError`, `ServiceUnavailable`, etc., and maps to structured `HTTPException` responses (502 Bad Gateway, 503 Service Unavailable).
- Add application-level error response Pydantic model (`ErrorResponse` with `detail` and `error_code`).

#### Plan 1.2 — Real Neo4j Health Endpoint
**Covers:** INFRA-01

- Replace hardcoded "connected" response in health endpoint with actual driver connectivity check.
- Implement `GET /health` that returns:
  - `{"status": "connected", "database": "neo4j", "version": "..."}` when Neo4j is reachable
  - `{"status": "disconnected", "detail": "..."}` when driver is initialized but connection failed
  - `{"status": "unavailable", "detail": "..."}` when driver is not initialized
- Use `driver.verify_connectivity()` with a timeout.

#### Plan 1.3 — Parameterized Queries & Managed Transactions
**Covers:** ARCH-02, ARCH-03

- Audit all existing Cypher queries to ensure `$param` placeholders are used everywhere (no f-string interpolation).
- Refactor any `session.run()` calls in route handlers to use `execute_query` (Neo4j v6 default API) or managed `execute_read`/`execute_write` transactions.
- Establish repository-level helper functions for common query patterns.

#### Plan 1.4 — Create Seed Data Files
**Covers:** DATA-01, DATA-02, DATA-03, DATA-04

- **DATA-01:** Create `backend/seed/data/characters.json` — Dexter S01E01-03 character nodes (Dexter, Debra, Brian, Batista, LaGuerta, Doakes, Rita, Paul, Rudy, Masuka, Ice Truck Killer references). Each character has `id`, `name`, `description`, `aliases`, `visible_from_order`.
- **DATA-02:** Create `backend/seed/data/sources.json` — Source references (episode scripts with locators, transcript timestamps). Each source has `id`, `title`, `source_type`, `episode_id`, `locator`.
- **DATA-03:** Create `backend/seed/data/evidence_fragments.json` — Evidence linking claims to specific episode sources. Each fragment has `id`, `claim_id`, `source_id`, `locator`, `quote_excerpt`.
- **DATA-04:** Create `backend/seed/data/claims.json` — Character relationship claims (KNOWS, FAMILY_OF, KILLS, WORKS_WITH) with evidence links, `relationship_effect`, `confidence_level`, `visible_from_order`, `valid_from_order`, `valid_until_order`. Include at least one cross-episode claim and one claim with `visible_from_order=3` for spoiler testing.

#### Plan 1.5 — Reliable Seed Script
**Covers:** INFRA-02

- Refactor `backend/seed/seed.py` to be a reliable single-entry-point script.
- Load and validate all JSON seed files before writing to Neo4j.
- Create Neo4j constraints for all node types (Series, Episode, Character, Claim, Source, EvidenceFragment) — ensure `visible_from_order` has an existence constraint.
- Use `MERGE` semantics for idempotent creation.
- Create relationships: `PART_OF` (Character→Episode, Episode→Series), `PRECEDES` (Episode→Episode), `KNOWS`, `FAMILY_OF`, `KILLS`, `WORKS_WITH` (Character→Character), `SUPPORTED_BY` (Claim→EvidenceFragment), `FROM_SOURCE` (EvidenceFragment→Source).
- Print post-seed summary (node counts per label, relationship counts per type).
- Exit with non-zero code on failure.

#### Plan 1.6 — Backend Tests
**Covers:** TEST-01, TEST-02

- **TEST-01:** Write `pytest` tests for `GET /health`:
  - Returns `{"status": "connected"}` when Neo4j is running
  - Returns `{"status": "disconnected"}` or `{"status": "unavailable"}` when Neo4j is not running
  - HTTP 200 in all cases (always returns a health report, never 500)
- **TEST-02:** Write tests for seed script idempotency:
  - Mock fixture creates all node types
  - Running seed twice yields same node count
  - `MERGE` operations don't duplicate
  - Verify constraint satisfaction after seed

---

## Phase 2: Spoiler-Gated Graph API

**Goal:** Build `GET /api/graph` endpoint with Cypher-level spoiler filtering, Neo4j constraints for all node types, Pydantic response models, and integration tests — delivering the central architectural invariant that powers spoiler-safe graph exploration.

**Mode:** mvp

### Success Criteria

1. **Spoiler boundary enforced** — `GET /api/graph?series_id=dexter&visible_until_order=1` returns only nodes/relationships visible within Episode 1's boundary. Nodes with `visible_from_order=2` or `visible_from_order=3` are excluded.
2. **Cypher-level filtering** — Every graph query includes `WHERE n.visible_from_order <= $visible_until_order` in Cypher; no post-processing filtering in Python.
3. **Constraints active** — Neo4j existence constraints enforce `visible_from_order` on all node types; `SHOW CONSTRAINTS` confirms constraints for Series, Episode, Character, Claim, Source, EvidenceFragment.
4. **Clean Pydantic models** — Graph endpoint returns `GraphResponse` with `nodes` and `edges` arrays of serializable dicts (never raw Neo4j `Node`/`Relationship` objects). Graph closure invariant holds: every edge's `source` and `target` ID appears in the `nodes` array.
5. **Integration-tested** — Tests validate correct data at multiple progress thresholds (`visible_until_order=1`, `=2`, `=3`, missing params).

### Plans

#### Plan 2.1 — Neo4j Constraints for All Types
**Covers:** GRAPH-05

- Add constraint creation to the seed script (or a dedicated migration) for every node type:
  - `Series`: existence constraint on `id`, `visible_from_order`
  - `Episode`: existence constraint on `id`, `visible_from_order`, `order`
  - `Character`: existence constraint on `id`, `visible_from_order`
  - `Claim`: existence constraint on `id`, `visible_from_order`, `valid_from_order`
  - `Source`: existence constraint on `id`, `visible_from_order`
  - `EvidenceFragment`: existence constraint on `id`, `visible_from_order`
- Add uniqueness constraints on node `id` properties per label.
- Add assertion step in seed script that verifies all constraints post-creation.

#### Plan 2.2 — Pydantic Response Models
**Covers:** GRAPH-06

- Create `GraphNodeResponse` Pydantic model with: `id`, `label` (node type string), `properties` (serializable dict of all user-facing fields, excluding internal metadata).
- Create `GraphEdgeResponse` Pydantic model with: `id`, `source` (node ID), `target` (node ID), `label` (relationship type), `properties` (serializable dict).
- Create `GraphResponse` Pydantic model with: `nodes` (list of `GraphNodeResponse`), `edges` (list of `GraphEdgeResponse`), `meta` (series info, applied boundary).
- Add Pydantic model validator on `GraphResponse` to enforce graph closure invariant: every edge's `source` and `target` must have a matching node in `nodes`.
- Ensure no Neo4j `Node`/`Relationship` objects leak through — serialize to dicts before returning.

#### Plan 2.3 — Spoiler-Aware Graph Endpoint
**Covers:** GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04

- Implement `GET /api/graph` FastAPI route with required query parameters:
  - `series_id: str` — series identifier (e.g., "dexter")
  - `visible_until_order: int` — user's watch progress (episode order number)
- **SpoilerGuard validation:**
  - Raise 400 if either parameter is missing
  - Raise 404 if series_id doesn't match any series
  - Raise 400 if `visible_until_order < 1`
- **Cypher query design:**
  - Match all nodes with `visible_from_order <= $visible_until_order` AND `series_id = $series_id`
  - Match all relationships where BOTH source AND target nodes pass the visible_from_order filter (three-way filter: source node, relationship, target node all checked)
  - Filter claims using both `visible_from_order` and `valid_from_order`/`valid_until_order` temporal window
  - Use explicit `WHERE` clauses — never `OPTIONAL MATCH` for spoiler-boundary filtering (avoids partial relationship metadata leak)
- **Response construction:**
  - Serialize all returned nodes/relationships to `GraphNodeResponse`/`GraphEdgeResponse`
  - Run graph closure invariant validator before returning
  - Include `visible_until_order` in response `meta` for frontend validation

#### Plan 2.4 — Integration Tests
**Covers:** TEST-03, TEST-04

- **TEST-03:** Spoiler boundary integration tests:
  - Seed graph with test data at multiple `visible_from_order` values
  - `visible_until_order=1`: verify only Episode-1-scoped nodes returned
  - `visible_until_order=2`: verify Episode 1 + 2 nodes returned, Episode 3 excluded
  - `visible_until_order=3`: verify all data returned
  - Assert no hidden data leaks in edges (verify edge source/target are always in returned nodes)
  - Assert claim `valid_until_order` filtering works correctly
- **TEST-04:** Parameter validation tests:
  - Missing `series_id` → 400
  - Missing `visible_until_order` → 400
  - `visible_until_order=0` → 400
  - Nonexistent `series_id` → 404
  - Invalid types → 422 (Pydantic validation)

---

## Requirements Coverage

| Requirement | Phase | Description |
|-------------|-------|-------------|
| INFRA-01 | Phase 1 | Health endpoint verifies actual Neo4j connectivity |
| INFRA-02 | Phase 1 | Seed script runnable as reliable one-step setup |
| DATA-01 | Phase 1 | Character seed file for Dexter S01E01-03 |
| DATA-02 | Phase 1 | Source seed file with episode/locator references |
| DATA-03 | Phase 1 | Evidence seed file linking claims to sources |
| DATA-04 | Phase 1 | Claim seed file with character relationships |
| GRAPH-01 | Phase 2 | Spoiler-aware `GET /api/graph` endpoint |
| GRAPH-02 | Phase 2 | `visible_from_order` on every seeded node |
| GRAPH-03 | Phase 2 | `valid_from_order`/`valid_until_order` on claims |
| GRAPH-04 | Phase 2 | Cypher-level filtering (no Python post-processing) |
| GRAPH-05 | Phase 2 | Neo4j constraints for all node types |
| GRAPH-06 | Phase 2 | Pydantic response models for graph endpoint |
| ARCH-01 | Phase 1 | Lazy Neo4j driver initialization for testability |
| ARCH-02 | Phase 1 | Parameterized `$param` Cypher queries everywhere |
| ARCH-03 | Phase 1 | Managed transactions via `execute_query` |
| ARCH-04 | Phase 1 | Remove duplicate FastAPI app construction |
| ARCH-05 | Phase 1 | Error handling: Neo4j errors → HTTP responses |
| TEST-01 | Phase 1 | Health endpoint tests with/without Neo4j |
| TEST-02 | Phase 1 | Seed script idempotency tests |
| TEST-03 | Phase 2 | Graph endpoint spoiler boundary integration tests |
| TEST-04 | Phase 2 | Graph endpoint parameter validation tests |

**Coverage:** 21 v1 requirements — 13 in Phase 1, 8 in Phase 2 — 100% mapped ✓

---

## Known Risks & Mitigations

| Risk | Phase | Likelihood | Mitigation |
|------|-------|------------|------------|
| Neo4j 2026 community features differ from docs | Phase 1 | Low | Pin version in docker-compose; test with actual container |
| Cypher spoiler leak via relationship traversal | Phase 2 | High | Three-way filter (source node, rel, target node); add Pydantic graph closure validator |
| `visible_from_order` drift (NULL values) | Phase 2 | Medium | Existence constraints on all node types; CI check for NULLs |
| Seed data quality insufficient for compelling demo | Phase 1 | Medium | Design seed data to demonstrate multi-episode spoiler gating visually |
| Import-time driver breaks tests | Phase 1 | High | Refactor to lazy init before any test work |

---

*Roadmap created: 2026-07-28*  
*Project mode: mvp*  
*Granularity: coarse*
