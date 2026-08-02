---
phase: 01-backend-graph-foundation
plan: 01
subsystem: api
tags: [fastapi, neo4j, asyncio, spoiler-gating, pytest, docker]

requires: []
provides:
  - Lifespan-owned async Neo4j driver with degraded startup and real health checks
  - Ontology-validated deterministic Dexter S01E01-03 evidence graph seed
  - Fail-closed spoiler-safe graph API with independent claim temporal validity
  - Automated boundary, idempotency, error-shape, graph-closure, and smoke acceptance evidence
affects: [phase-02-polished-cytoscape-graph-experience, graph-api, seed-data]

tech-stack:
  added: [PyYAML, pytest-asyncio]
  patterns: [application-owned async driver, parameterized Cypher gating, deterministic UNWIND seed, Pydantic graph closure]

key-files:
  created:
    - backend/app/api/graph.py
    - backend/app/domain/graph.py
    - backend/app/graph/ontology.py
    - backend/app/graph/setup.py
    - backend/app/spoiler/filter.py
    - backend/scripts/smoke.sh
  modified:
    - backend/app/main.py
    - backend/app/graph/database.py
    - backend/app/graph/seed.py
    - backend/app/api/series.py
    - backend/tests/test_graph_api.py
    - backend/tests/test_seed_idempotency.py

key-decisions:
  - "Own one AsyncGraphDatabase driver in FastAPI lifespan while allowing degraded startup so documentation remains reachable without Neo4j."
  - "Require visible_until_order and enforce node, relationship, claim, source, and evidence visibility in parameterized Cypher before response construction."
  - "Keep visible_from_order mandatory in deterministic fixtures and tests when Neo4j Community cannot enforce property-existence constraints."
  - "Derive claim source and evidence IDs only from visibility-gated provenance relationships instead of returning denormalized claim properties."

patterns-established:
  - "Fail-closed graph access: a persisted positive episode boundary is mandatory for every graph response."
  - "Dual temporal semantics: visible_from_order controls disclosure while valid_from_order/valid_until_order controls narrative truth."
  - "Graph closure: every returned edge endpoint must exist in the returned node collection."

requirements-completed:
  - INFRA-01
  - INFRA-02
  - INFRA-03
  - META-01
  - META-02
  - META-03
  - API-01
  - API-02
  - API-03
  - API-04
  - SEED-01
  - SEED-02
  - SEED-03
  - SEED-04

coverage:
  - id: D1
    description: "Local Neo4j, FastAPI, and React runtime with real connected/degraded health behavior"
    requirement: "INFRA-01"
    verification:
      - kind: e2e
        ref: "bash backend/scripts/smoke.sh (8/8 checks)"
        status: pass
      - kind: integration
        ref: "Neo4j stop/start health verification (503 degraded, then 200 connected)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Ontology-validated deterministic and idempotent Dexter S01E01-03 evidence graph"
    requirement: "SEED-03"
    verification:
      - kind: integration
        ref: "backend/tests/test_seed_idempotency.py (3 passed)"
        status: pass
      - kind: integration
        ref: "uv run python -m backend.app.graph.setup twice (41 nodes, 26 relationships both runs)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Fail-closed spoiler-safe graph endpoint with temporal claim filtering and graph closure"
    requirement: "API-03"
    verification:
      - kind: integration
        ref: "backend/tests/test_graph_api.py (10 passed)"
        status: pass
      - kind: e2e
        ref: "Live boundaries 1/2/3 returned [11,6,4,1,3], [15,10,5,2,5], and [20,16,8,3,8] with closed edges"
        status: pass
    human_judgment: false
  - id: D4
    description: "Stable sanitized 404, 422, and 503 error contracts"
    requirement: "API-04"
    verification:
      - kind: integration
        ref: "backend/tests/test_graph_api.py#error and unavailable database tests"
        status: pass
      - kind: e2e
        ref: "Live unknown-series 404, missing/non-persisted-boundary 422, database-down health 503"
        status: pass
    human_judgment: false

duration: 24 min
completed: 2026-07-29
status: complete
---

# Phase 1 Plan 01: Backend Graph Foundation Summary

**A lifespan-owned async Neo4j backend, ontology-validated deterministic Dexter evidence graph, and fail-closed spoiler-safe API proven across live episode boundaries**

## Performance

- **Duration:** 24 min
- **Started:** 2026-07-29T06:48:32Z
- **Completed:** 2026-07-29T07:12:27Z
- **Tasks:** 3
- **Files modified:** 22

## Accomplishments

- Replaced import-time Neo4j state with one lifespan-owned async driver, degraded startup, real health checks, and sanitized database errors.
- Seeded an ontology-validated, deterministic 41-node/26-relationship Dexter S01E01-03 graph with complete claim-to-source/evidence provenance and idempotent setup.
- Added a parameterized Cypher graph endpoint that fails closed on missing/invalid boundaries, independently enforces claim validity, and guarantees graph closure.
- Added 13 passing automated tests plus an 8/8 live smoke command covering services, metadata, setup, spoiler sentinels, and invalid boundaries.

## Task Commits

Each task was committed atomically:

1. **Task 1: Infrastructure & Lifecycle Hardening** - `6462cdf` (feat)
2. **Task 2: Metadata Graph, Ontology Validation & Deterministic Seed** - `d4c6dac` (feat)
3. **Task 3: Spoiler-Aware Graph API & Automated Acceptance Evidence** - `4a043e7` (feat)
   - **Task 3 provenance hardening** - `4035c2d` (feat)

## Files Created/Modified

- `backend/app/graph/database.py` - Lazy application-owned async driver and database-qualified query API.
- `backend/app/main.py` - Single FastAPI application, lifespan ownership, routers, and real health response.
- `backend/app/graph/ontology.py` - YAML ontology allowlist loader and validators.
- `backend/app/graph/seed.py` - Idempotent constraints, indexes, deterministic nodes, and semantic relationships.
- `backend/app/api/graph.py` - Required-boundary spoiler-safe graph endpoint.
- `backend/app/spoiler/filter.py` - Parameterized Cypher visibility and temporal filtering.
- `backend/app/domain/graph.py` - Serializable graph contracts and closure validation.
- `backend/tests/test_graph_api.py` - Boundary, temporal validity, closure, and sanitized-error acceptance tests.
- `backend/tests/test_seed_idempotency.py` - Double-seed, schema, provenance, and ontology tests.
- `backend/scripts/smoke.sh` - Repeatable full-stack runtime smoke checks.
- `data/dexter/seed/*.json` - Deterministic Character, Event, Location, Claim, Source, and EvidenceFragment fixtures.

## Decisions Made

- Used `AsyncGraphDatabase` because FastAPI endpoints and lifespan are asynchronous; one driver is shared through application state and always closed at shutdown.
- Kept the application available in degraded mode so `/docs` remains reachable while `/health` accurately returns 503 when Neo4j is unavailable.
- Performed all spoiler and temporal filtering in parameterized Cypher, then used Pydantic only for serialization and graph-closure enforcement.
- Used semantic deterministic IDs and uniqueness constraints for every MERGE target before seeding.

## Deviations from Plan

### Auto-fixed Issues

**1. Neo4j Community does not support property-existence constraints**
- **Found during:** Task 2 setup execution
- **Issue:** `REQUIRE n.visible_from_order IS NOT NULL` failed on the configured Community image.
- **Fix:** Retained rerunnable existence DDL for supported editions, skipped only the documented Community unsupported error, and enforced the invariant through fixture validation plus integration assertions.
- **Files modified:** `backend/app/graph/seed.py`, `backend/tests/test_seed_idempotency.py`
- **Verification:** Full test suite passed; every spoiler-sensitive seeded node and relationship was checked for an integer visibility boundary.
- **Committed in:** `d4c6dac`

**2. Native Windows tools could not consume MSYS `/tmp` paths in the smoke script**
- **Found during:** Task 3 smoke verification
- **Issue:** Native curl/Python failed to write/read files addressed through MSYS temporary paths.
- **Fix:** Used a project-relative temporary directory and shell redirection, shared consistently by Bash, curl, and `uv run python`.
- **Files modified:** `backend/scripts/smoke.sh`
- **Verification:** `bash backend/scripts/smoke.sh` completed with `SMOKE PASS: 8/8 checks passed`.
- **Committed in:** `4a043e7`

**3. Claim payload provenance IDs were not independently visibility-gated**
- **Found during:** Task 3 Neo4j non-negotiables review
- **Issue:** The claim query gated claims and endpoints but returned denormalized `claim.source_id` and `claim.evidence_ids`, allowing provenance identifiers to bypass their own visibility boundary if fixture visibility diverged.
- **Fix:** Matched `REFERS_TO` and `SUPPORTED_BY` provenance paths in the claim query, gated both relationships and both provenance nodes, and derived returned IDs only from those matched visible records.
- **Files modified:** `backend/app/spoiler/filter.py`
- **Verification:** `uv run pytest` completed with 13 passed; boundary 1/2/3 counts, visibility, validity, and closure remained stable; smoke completed 8/8.
- **Committed in:** `4035c2d`

---

**Total deviations:** 3 auto-fixed issues (one edition limitation, one MSYS portability defect, one spoiler-boundary hardening)
**Impact on plan:** All fixes were required for runtime portability or the locked fail-closed disclosure invariant; no product-scope expansion occurred.

## Issues Encountered

The first executor exhausted its tool-call budget and the continuation executor stopped after the MSYS-path failure. The orchestrator independently verified the durable commits, corrected/validated the smoke path, reran all canonical tests and live checks, and completed the atomic plan closeout.

## Verification Evidence

- `uv run pytest -v` → **13 passed, 1 third-party deprecation warning**.
- `bash backend/scripts/smoke.sh` → **8/8 checks passed**.
- Live graph boundaries:
  - Order 1 → nodes 11, edges 6, claims 4, sources 1, evidence 3.
  - Order 2 → nodes 15, edges 10, claims 5, sources 2, evidence 5.
  - Order 3 → nodes 20, edges 16, claims 8, sources 3, evidence 8.
  - Every returned edge endpoint appeared in the returned node collection.
- Live errors → unknown series 404; missing/non-persisted boundary 422.
- Database outage → `/health` returned sanitized 503 degraded response and the graph endpoint returned sanitized `503 database_unavailable`; Swagger remained 200; after restart Neo4j became healthy and `/health` returned 200 connected.
- Setup executed repeatedly with **41 nodes and 26 relationships**.

## User Setup Required

None - local Docker Compose and project commands use the existing repository configuration.

## Next Phase Readiness

The backend graph contract and deterministic seed are ready for Phase 2 Cytoscape integration. Phase-level verifier review remains the final GSD gate before Phase 1 is marked complete.

## Self-Check: PASSED

- Key created files exist on disk.
- Task commits `6462cdf`, `d4c6dac`, `4a043e7`, and `4035c2d` are present in git history.
- `uv run pytest` passed 13/13 tests after the final provenance hardening.
- `bash backend/scripts/smoke.sh` passed 8/8 checks after the final provenance hardening.
- Live boundaries 1/2/3, invalid/missing boundary, unknown series, database outage, service reachability, and recovery were exercised with real runtime output.

---
*Phase: 01-backend-graph-foundation*
*Completed: 2026-07-29*
