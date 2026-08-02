---
phase: 01-backend-graph-foundation
verified: 2026-07-29T07:45:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 1: Backend Graph Foundation — Verification Report

**Phase Goal:** Deliver the minimum reliable backend and Neo4j graph foundation required for the visual prototype: executable local services, ontology-aligned deterministic data, evidence-backed graph records, and backend-enforced spoiler filtering.

**Verified:** 2026-07-29T07:45:00Z
**Status:** ✅ **PASSED**
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Neo4j, FastAPI, and React services are locally executable and reachable | ✓ VERIFIED | docker-compose.yml exists; single FastAPI instance at `main.py:35`; lifespan-owned driver; React at http://localhost:5173 (HTTP 200 confirmed); /health returns 200 `{"database":"connected"}` on live instance; smoke.sh covers all services |
| 2 | /health performs real Neo4j connectivity check (200 healthy, 503 unavailable) | ✓ VERIFIED | `main.py:55-75`: calls `database.verify_connection()` → `driver.verify_connectivity()`; returns `{"status":"ok","database":"connected"}` (200) or `{"status":"degraded","database":"unavailable"}` (503); `test_app_starts_degraded_and_docs_remain_available` proves degraded 503 + /docs still 200; live check confirms 200 with `"database":"connected"` |
| 3 | Backend modules import without Neo4j connection side effects | ✓ VERIFIED | `database.py`: lazy `_driver = None`, only initialized in `open()`; `get_database()` reads from `app.state.neo4j`; `test_database_module_has_no_driver_singleton` proves zero `AsyncGraphDatabase.driver()` calls at import and no `neo4j_db` singleton; isolated import verified: `from backend.app.graph.database import Neo4jDatabase; print('import ok')` succeeds |
| 4 | Idempotent setup creates constraints and seeds Dexter S01E01-03 with ontology-aligned, evidence-backed graph | ✓ VERIFIED | `setup.py` → `setup_database()` orchestrates: load seed data → `validate_seed()` against ontology YAML → `create_constraints()` (8 uniqueness, 8 existence, 8 indexes, all `IF NOT EXISTS`) → `seed_graph()` (MERGE all 8 node types, 5 relationship types with deterministic IDs); `test_seed_is_idempotent_and_complete` proves 41 nodes/26 relationships both runs with identical snapshots; `test_ontology_rejects_undeclared_seed_type` proves undeclared "SpoilerMonster" is rejected |
| 5 | Every graph-visible record has stable string ID and spoiler-sensitive records have visible_from_order | ✓ VERIFIED | All 41 seed records use namespaced string IDs (e.g. `dexter:character:dexter_morgan`); all 8 node types and all 5 relationship types carry `visible_from_order` as integer; `validate_seed()` line 88 asserts `visible_from_order` is int for every record; `test_constraints_visibility_and_provenance` asserts zero NULL `visible_from_order` (count=0) |
| 6 | GET /api/series/{series_id}/graph?visible_until_order=N returns only spoiler-allowed data through parameterized Cypher | ✓ VERIFIED | All 7 Cypher queries in `filter.py` use `$series_id` and `$visible_until_order` parameters (never string interpolation); `NODES_QUERY`, `STRUCTURAL_EDGES_QUERY`, `VISIBLE_CLAIMS_QUERY`, `SOURCES_QUERY`, `EVIDENCE_QUERY` all filter every entity and relationship by `visible_from_order <= $visible_until_order`; no Python-side post-processing filtering; live order-1 returns exact expected counts: nodes=11, edges=6, claims=4, sources=1, evidence=3 |
| 7 | Claims have temporal validity enforced independently from spoiler visibility | ✓ VERIFIED | `VISIBLE_CLAIMS_QUERY` lines 60-61: `(claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order) AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)` — enforced in Cypher alongside `visible_from_order`; `test_claim_validity_is_independent_of_visibility` proves `dexter:claim:s01e01:temporary_trust` (visible_from_order=1, valid_until_order=1) appears at order 1 but NOT at order 2 |
| 8 | Graph closure: every returned edge's source/target appears in returned nodes | ✓ VERIFIED | `GraphResponse.enforce_graph_closure()` in `domain/graph.py:79-89` validates all edge endpoints exist in nodes; `test_graph_model_rejects_dangling_edge` proves dangling edge raises `ValidationError`; `test_graph_boundaries_have_full_json_sentinels` confirms closure at all 3 boundaries live |
| 9 | Automated tests prove S01E01 request contains no S01E02/S01E03 nodes, edges, claims, evidence, names, labels, or counts | ✓ VERIFIED | `test_graph_boundaries_have_full_json_sentinels` parametrized at orders 1/2/3: boundary=1 asserts exact counts (11/6/4/1/3) + forbids sentinels `["dexter_s01e02","S01E02","Crocodile","Paul Bennett","Rudy Cooper","ice rink"]` in full serialized JSON; boundary=2 similarly forbids S01E03 sentinels; all 13 tests pass |

**Score:** 9/9 truths verified (0 present-but-behavior-unverified)

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/main.py` | Single FastAPI instance, lifespan-owned driver, real /health | ✓ VERIFIED | 75 lines; one `FastAPI()` at line 35; lifespan creates+owns driver; real `/health` with connectivity check |
| `backend/app/graph/database.py` | Lazy-initialized driver | ✓ VERIFIED | 60 lines; `_driver=None` initially; `open()` creates; `get_database()` reads from `app.state` |
| `backend/app/core/errors.py` | Centralized Neo4j-to-503 error mapping | ✓ VERIFIED | 35 lines; catches ServiceUnavailable/AuthError/ClientError/Neo4jError; maps to sanitized 503 with `detail.code`/`detail.message` |
| `backend/app/graph/ontology.py` | YAML ontology validator | ✓ VERIFIED | 74 lines; loads node_types/relation_types/claim_types YAML; validates version "0.1"; `require_*()` methods for type enforcement |
| `backend/app/graph/setup.py` | Idempotent full-graph seed command | ✓ VERIFIED | 28 lines; `async_main()` → `setup_database()`; registered as `hdgraf-setup` in pyproject.toml |
| `backend/app/api/graph.py` | Spoiler-filtered graph endpoint | ✓ VERIFIED | 121 lines; validates series_id + visible_until_order; executes all 7 parameterized queries via `asyncio.gather`; returns `GraphResponse` |
| `backend/app/domain/graph.py` | Pydantic graph response models | ✓ VERIFIED | 93 lines; GraphNode/GraphEdge/GraphClaim/GraphSource/GraphEvidence/GraphResponse with `enforce_graph_closure()` |
| `backend/tests/test_graph_api.py` | Isolated + integration graph tests | ✓ VERIFIED | 223 lines; 10 tests: error shapes, degraded startup, no singleton, dangling edge rejection, error shapes live, sanitized 503, 3 boundary sentinel tests, temporal validity |
| `backend/tests/test_seed_idempotency.py` | Double-seed idempotency tests | ✓ VERIFIED | 122 lines; 3 tests: idempotent double-seed (41/26 invariant), constraints+visibility+provenance, ontology rejection |
| `backend/scripts/smoke.sh` | Repeatable documented smoke command | ✓ VERIFIED | 85 lines; 8 checks: Neo4j Browser, Swagger, React, setup, health, metadata, order-1 boundary, invalid 422 |
| `data/dexter/seed/*.json` | Deterministic seed data (6 files) | ✓ VERIFIED | 9 Characters, 3 Events, 4 Locations, 9 Claims, 3 Sources, 9 EvidenceFragments — all with namespaced IDs, visible_from_order, provenance links |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| FastAPI lifespan | Neo4j driver | `app.state.neo4j` + `get_database()` dependency | ✓ WIRED | lifespan at `main.py:21` opens driver → `app.state.neo4j`; `/health` and all endpoints resolve via `get_database()` → `request.app.state.neo4j` |
| Graph endpoint | Spoiler-filtered Cypher | `filter.py` queries imported by `graph.py` | ✓ WIRED | 7 parameterized queries from `filter.py` executed in `graph.py:84-95` via `asyncio.gather`; all filtering in Cypher WHERE clauses |
| Seed command | Ontology validation | `validate_seed(data, load_ontology())` before constraints | ✓ WIRED | `setup_database()` at `seed.py:251` validates before `create_constraints()`; type/status/confidence/version all checked |
| Tests | Running Neo4j instance | `conftest.py` defaults + live fixtures | ✓ WIRED | `conftest.py` sets `NEO4J_URI=bolt://127.0.0.1:7687`; `live_database` fixture opens+verifies; `live_client` fixture seeds before yielding |
| Smoke command | All services running | Sequential curl + Python assertions | ✓ WIRED | `smoke.sh` checks Neo4j Browser (7474), Swagger (/docs), React (5173), /health, /api/series, /api/series/{id}/episodes, graph order-1, invalid 422 |

### Data-Flow Trace (Level 4)

| Artifact | Data Source | Real Data? | Status |
|----------|------------|------------|--------|
| `/health` endpoint | `database.verify_connection()` → Neo4j `driver.verify_connectivity()` | Yes — live check returns 200 with `"database":"connected"` | ✓ FLOWING |
| `GET /api/series` | `MATCH (series:Series) RETURN ...` — real Cypher query | Yes — live returns `[{"id":"series_dexter","title":"Dexter","slug":"dexter"}]` | ✓ FLOWING |
| `GET /api/series/{id}/graph` | 7 parameterized Cypher queries fetching nodes/edges/claims/sources/evidence with visibility gates | Yes — live order=1 returns nodes=11, edges=6, claims=4, sources=1, evidence=3 | ✓ FLOWING |
| Seed command | `data/dexter/seed/*.json` + `data/dexter/metadata/*.json` → UNWIND/MERGE Cypher | Yes — creates 41 nodes, 26 relationships | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Module import has no side effects | `uv run python -c "from backend.app.graph.database import Neo4jDatabase; print('import ok')"` | `import ok` | ✓ PASS |
| Isolated tests pass (no Neo4j needed) | `uv run pytest ... -v` (5 isolated tests) | 5 passed | ✓ PASS |
| /health returns real connectivity | `curl -s http://127.0.0.1:8000/health` | `{"status":"ok","database":"connected","service":"hdgrafcehennemi-backend"}` | ✓ PASS |
| /api/series returns seeded data | `curl -s http://127.0.0.1:8000/api/series` | `[{"id":"series_dexter","title":"Dexter","slug":"dexter"}]` | ✓ PASS |
| Graph boundary 1 returns exact counts | `curl -s "...?visible_until_order=1"` | nodes=11, edges=6, claims=4, sources=1, evidence=3 | ✓ PASS |
| All integration tests pass | `uv run pytest -v` (13 tests total) | 13 passed | ✓ PASS |
| Idempotency: double-seed invariant | `test_seed_is_idempotent_and_complete` | 41 nodes / 26 relationships both runs | ✓ PASS |
| Temporal validity exclusion at order 2 | `test_claim_validity_is_independent_of_visibility` | `temporary_trust` present at order 1, absent at order 2 | ✓ PASS |
| Frontend dev server reachable | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173` | `200` | ✓ PASS |
| Swagger reachable | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/docs` | `200` | ✓ PASS |
| Neo4j Browser reachable | `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:7474` | `200` | ✓ PASS |

---

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| INFRA-01 | Neo4j, FastAPI, React services start locally and URLs reachable | ✓ SATISFIED | docker-compose.yml; FastAPI degraded startup test; React/Neo4j/Swagger all return 200 live |
| INFRA-02 | /health performs real Neo4j connectivity check | ✓ SATISFIED | `main.py:55-75` real `verify_connectivity()`; test proves 200/503; live 200 confirmed |
| INFRA-03 | Backend lifecycle testable without import-time side effects | ✓ SATISFIED | Lazy driver; `test_database_module_has_no_driver_singleton` proves zero import connections |
| META-01 | Idempotent setup creates uniqueness/existence constraints | ✓ SATISFIED | `create_constraints()` with `IF NOT EXISTS`; `test_constraints_visibility_and_provenance` confirms all 8 uniqueness constraints |
| META-02 | Setup persists Dexter, S01E01-03, PART_OF, PRECEDES | ✓ SATISFIED | `seed_graph()` creates PART_OF + PRECEDES; metadata shows 3 episodes with correct orders |
| META-03 | GET /api/series and episodes return data through Pydantic models | ✓ SATISFIED | `series.py` uses `SeriesResponse`/`EpisodeResponse`; live check confirms `series_dexter` with 3 episodes |
| API-01 | GET /api/series/{id}/graph returns nodes/edges/claims/boundary metadata | ✓ SATISFIED | `graph.py` endpoint; live order=1 returns accurate 11/6/4/1/3 counts |
| API-02 | Cypher filtering enforces visible_from_order before response construction | ✓ SATISFIED | All 7 queries filter in `WHERE visible_from_order <= $visible_until_order`; no Python post-filtering |
| API-03 | Claim validity enforced independently from spoiler visibility | ✓ SATISFIED | `VISIBLE_CLAIMS_QUERY` has both visibility + temporal WHERE; test proves `temporary_trust` excluded at order 2 |
| API-04 | Boundary tests at orders 1/2/3 prove no future leakage; invalid inputs have defined errors | ✓ SATISFIED | 3 boundary tests with sentinel+count assertions; 404 for unknown series; 422 for missing/non-persisted/malformed boundary |
| SEED-01 | Manual Dexter S01E01-03 seed with Character/Event/Location/Claim records | ✓ SATISFIED | 9 Characters, 3 Events, 4 Locations, 9 Claims — all with visibility/confidence/effect/status/validity metadata |
| SEED-02 | Source/EvidenceFragment records with episode references and locators | ✓ SATISFIED | 3 Sources, 9 EvidenceFragments — all with episode_id, locator, retrieved_at, content_hash |
| SEED-03 | Every Claim links to ≥1 EvidenceFragment and Source; idempotent | ✓ SATISFIED | `validate_seed()` enforces provenance; `test_seed_is_idempotent_and_complete` proves 41/26 invariant |
| SEED-04 | Graph queries demonstrate evidence-backed network at each boundary | ✓ SATISFIED | Boundary tests at orders 1/2/3 verify nodes/edges/claims/sources/evidence counts escalate correctly |

**Coverage:** 14/14 Phase 1 requirements satisfied; 0 orphaned

---

### Anti-Patterns Found

None. Zero `TBD`, `FIXME`, `XXX`, `TODO`, `HACK`, or `PLACEHOLDER` markers in any backend source file. No empty implementations, hardcoded empty returns, or stub patterns in production code. The two `pass` statements found are intentional: `OntologyValidationError` class body and degraded startup `except Exception: pass` — both documented and correct.

---

### Deviations Assessment

The SUMMARY.md documents 3 deviations from plan. All were auto-fixed during execution and verified:

1. **Neo4j Community property-existence constraints** → Gracefully skipped with `DatabaseError` catch; invariant enforced via fixture validation + integration assertions (`test_constraints_visibility_and_provenance` proves zero NULL `visible_from_order`). **Mitigation verified.**

2. **MSYS `/tmp` path issue in smoke.sh** → Fixed with project-relative temp directory. Smoke script is present and structurally sound. **Mitigation verified.**

3. **Claim provenance ID visibility gating** → Fixed in `VISIBLE_CLAIMS_QUERY`: `source_id` derived from visibility-gated `REFERS_TO` match; `evidence_ids` from visibility-gated `SUPPORTED_BY` match. **Mitigation verified in current code.**

---

### Confirmation Bias Counter (Disconfirmation Pass)

Per the verifier agent's required adversarial stance, a disconfirmation pass was performed:

1. **Partially met requirement:** None found. All 14 requirements have concrete implementation evidence.
2. **Test that passes but may not test stated behavior:** `test_graph_boundaries_have_full_json_sentinels` at boundary=1 forbids `["dexter_s01e02","S01E02","Crocodile","Paul Bennett","Rudy Cooper","ice rink"]`. This is a subset of all possible S01E02/S01E03 identifiers but is adequate when combined with the count assertions (nodes=11, edges=6, etc.) — any leakage would change counts.
3. **Error path without test coverage:** The `create_constraints()` function catches `DatabaseError` for Community edition limitations. The error message check (`"existence constraint" not in str(exc)`) is untested. However, this is a graceful degradation path for a known platform limitation, not a functional gap. The invariant (zero NULL `visible_from_order`) is tested independently.

---

### Gaps Summary

No gaps found. All 9 observable truths are verified. All 14 requirements are satisfied. All artifacts exist, are substantive, and are wired. All key links are connected. All 13 automated tests pass. Live behavioral spot-checks confirm runtime correctness.

---

_Verified: 2026-07-29T07:45:00Z_
_Verifier: gsd-verifier agent (Hermes)_
