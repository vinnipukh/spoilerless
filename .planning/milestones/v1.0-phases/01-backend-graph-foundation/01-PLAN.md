---
phase: 01-backend-graph-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/main.py
  - backend/app/graph/database.py
  - backend/app/graph/seed.py
  - backend/app/graph/ontology.py
  - backend/app/graph/setup.py
  - backend/app/api/graph.py
  - backend/app/domain/graph.py
  - backend/app/core/errors.py
  - backend/app/spoiler/filter.py
  - backend/tests/conftest.py
  - backend/tests/test_graph_api.py
  - backend/tests/test_seed_idempotency.py
  - backend/scripts/smoke.sh
  - data/dexter/seed/characters.json
  - data/dexter/seed/events.json
  - data/dexter/seed/locations.json
  - data/dexter/seed/claims.json
  - data/dexter/seed/sources.json
  - data/dexter/seed/evidence_fragments.json
  - pyproject.toml
autonomous: false
requirements:
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
security_enforcement: true
asvs_level: 1

must_haves:
  truths:
    - Neo4j, FastAPI, and React services start locally and are reachable at expected URLs
    - /health performs a real Neo4j connectivity check (200 healthy, 503 unavailable)
    - Backend modules import without Neo4j connection side effects
    - Idempotent setup creates constraints and seeds Dexter S01E01-03 with evidence-backed graph
    - GET /api/series/{series_id}/graph?visible_until_order=N returns only spoiler-allowed data
    - Spoiler filtering happens in parameterized Cypher before response construction
    - Claims have temporal validity enforced independently from spoiler visibility
    - Graph closure: every returned edge's source/target appears in returned nodes
  artifacts:
    - backend/app/main.py - single FastAPI instance, lifespan-owned driver, real /health
    - backend/app/graph/database.py - lazy-initialized driver
    - backend/app/core/errors.py - centralized Neo4j-to-503 error mapping
    - backend/app/graph/ontology.py - YAML ontology validator
    - backend/app/graph/setup.py - idempotent full-graph seed command
    - backend/app/api/graph.py - spoiler-filtered graph endpoint
    - backend/app/domain/graph.py - Pydantic graph response models
    - backend/tests/test_graph_api.py - isolated + integration graph tests
    - backend/tests/test_seed_idempotency.py - double-seed idempotency tests
    - backend/scripts/smoke.sh - repeatable documented smoke command
    - data/dexter/seed/*.json - deterministic seed data (characters, events, locations, claims, sources, evidence)
  key_links:
    - FastAPI lifespan to Neo4j driver (health and DB-backed endpoints depend on it)
    - Graph endpoint to Spoiler-filtered Cypher queries (filtering must happen before response construction)
    - Seed command to Ontology validation (seed is rejected before Cypher if ontology does not allow types)
    - Tests to Running Neo4j instance (integration tests require live database)
    - Smoke command to All services running (single command verifies the entire stack)
---

<objective>
Consolidate Canonical Milestones 1–4 into a single executable backend foundation. The existing brownfield scaffold (FastAPI, Neo4j driver, seed script, metadata endpoints, ontology YAML, Docker Compose, and data fixtures) is preserved and hardened — not rebuilt. Phase 1 delivers:

1. A reliable local stack where FastAPI starts in degraded mode when Neo4j is unavailable and `/health` performs a real connectivity check.
2. An idempotent setup command that creates Neo4j constraints, validates against ontology YAML allowlists, and seeds Dexter Series + S01E01–03 Episode/Character/Event/Location/Claim/Source/EvidenceFragment records with deterministic namespaced IDs and `visible_from_order` metadata.
3. `GET /api/series`, `GET /api/series/{series_id}/episodes`, and `GET /api/series/{series_id}/graph` — the last being a spoiler-filtered endpoint that requires a validated `visible_until_order` parameter, enforces filtering in parameterized Cypher before response construction, and returns top-level `nodes`, `edges`, `claims`, `sources`, `evidence`, and boundary metadata.
4. Automated acceptance evidence: fast isolated tests, live-Neo4j integration tests, double-seed idempotency proof, spoiler-boundary tests at orders 1–3 with full JSON sentinel assertions, and one repeatable documented smoke command.

**No** server-side persisted watch progress, user notes, manual graph editing, revision history, candidate contracts, authentication, GraphQL, LLM, scraping, or extraction — these are deferred to Phase 3+ or post-v0.
</objective>

<execution_context>
@$HOME/AppData/Local/hermes/gsd-core/workflows/execute-plan.md
@$HOME/AppData/Local/hermes/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/01-backend-graph-foundation/01-CONTEXT.md
@backend/app/main.py
@backend/app/graph/database.py
@backend/app/graph/seed.py
@backend/app/api/series.py
@ontology/node_types.yaml
@ontology/relation_types.yaml
@ontology/claim_types.yaml
</context>

<tasks>

<task type="auto">
  <name>Task 1: Infrastructure & Lifecycle Hardening</name>
  <files>
    backend/app/main.py
    backend/app/graph/database.py
    backend/app/core/errors.py
  </files>
  <action>
    Fix the brownfield lifecycle so FastAPI starts without import-time Neo4j side effects, /health performs a real connectivity check, and database-backed endpoints return sanitized errors when Neo4j is unavailable. Preserve existing Docker Compose, Vite, and project structure.

    1. Fix duplicate FastAPI construction in backend/app/main.py (D-01, D-18): Remove the duplicated FastAPI() instance at approximately line 23. Keep existing CORS configuration, series router inclusion, and lifespan registration. Only one FastAPI() instance should exist.

    2. Convert driver to lifespan-owned dependency (D-03, D-18, D-20): Refactor backend/app/graph/database.py to replace the module-level neo4j_db = Neo4jDatabase() singleton with lazy initialization. Construct the driver inside the FastAPI lifespan and assign to app.state. Expose a get_driver() dependency so isolated tests never trigger a connection at import time. Keep GraphDatabase.driver() call lazy — no connect at import (D-20).

    3. Implement real /health endpoint (D-19, INFRA-02): Replace the hardcoded "database": "connected" with a real connectivity check using driver.verify_connectivity() or a lightweight Cypher (RETURN 1). Return {"status": "ok", "database": "connected", "service": "hdgrafcehennemi-backend"} with HTTP 200 on healthy. Catch connectivity failures and return {"status": "degraded", "database": "unavailable", "service": "hdgrafcehennemi-backend"} with HTTP 503. Swagger/OpenAPI must remain reachable even when Neo4j is unavailable (D-18).

    4. Add centralized Neo4j error mapping (D-20, D-09, INFRA-03): Create a middleware or exception handler in backend/app/core/errors.py that catches neo4j.exceptions.ServiceUnavailable, AuthError, ClientError and similar driver exceptions. Map them to HTTP 503 with sanitized body containing stable detail.code (e.g., "database_unavailable", "database_error") and safe detail.message (no URIs, credentials, or raw Cypher). Preserve existing HTTPException 404/422 for domain errors.

    5. Ensure development services remain executable (INFRA-01): Verify docker-compose up neo4j, uv run uvicorn, and cd frontend && npm run dev all work. Do NOT change docker-compose.yml, frontend scaffold, or project-level tooling (D-01, D-02).
  </action>
  <verify>
    <automated>pytest backend/tests/test_graph_api.py::test_error_responses -x -v 2>&1 | tail -20</automated>
    <automated>curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health</automated>
    <automated>python -c "from backend.app.graph.database import Neo4jDatabase; print('import ok')" 2>&1</automated>
  </verify>
  <done>
    FastAPI starts without Neo4j running; Swagger reachable at /docs; /health returns 200 when Neo4j is up and 503 when down; backend modules import without triggering a Neo4j connection; centralized error handler returns sanitized 503 for database failures.
  </done>
</task>

<task type="auto">
  <name>Task 2: Metadata Graph, Ontology Validation & Deterministic Seed</name>
  <files>
    backend/app/graph/ontology.py
    backend/app/graph/seed.py
    backend/app/graph/setup.py
    data/dexter/seed/characters.json
    data/dexter/seed/events.json
    data/dexter/seed/locations.json
    data/dexter/seed/claims.json
    data/dexter/seed/sources.json
    data/dexter/seed/evidence_fragments.json
    pyproject.toml
  </files>
  <action>
    Extend the existing idempotent seed script into a fully deterministic setup command that creates all required Neo4j constraints, validates every seeded value against the ontology YAML allowlists, and seeds Dexter S01E01-03 metadata plus a curated Character/Event/Location/Claim/Source/EvidenceFragment graph.

    1. Expand constraint and index creation (D-10, D-17, META-01): In backend/app/graph/seed.py or a new setup.py, extend create_constraints() to create uniqueness constraints for all Phase 1 node types: Series, Episode, Character, Event, Location, Claim, Source, EvidenceFragment. Add existence constraints on visible_from_order for every spoiler-sensitive type. Add indexes for visible_from_order, episode_order, series_id. All with IF NOT EXISTS for idempotency (D-15, D-17).

    2. Implement ontology validation (D-10): Add PyYAML via uv add pyyaml. Create backend/app/graph/ontology.py that loads ontology/node_types.yaml, ontology/relation_types.yaml, and ontology/claim_types.yaml into Python dicts. The seed module validates every node_type, relationship_type, claim_type, claim_status, and confidence_level against allowlists before executing Cypher. Ontology version "0.1" must match.

    3. Expand seed data for full Phase 1 graph (D-04, D-11, D-12, D-13, D-14, D-16, SEED-01, SEED-02, SEED-03): Preserve existing Series/Episode seeding. Add seed JSON files under data/dexter/seed/ for Characters (Dexter, Debra, Batista, LaGuerta, Doakes, Rita, Paul, Rudy/Brian, Harry), Events, Locations, Claims with evidence provenance, Sources, and EvidenceFragments. Every graph-visible record uses readable deterministic namespaced string IDs (D-11). Every Claim links to at least one EvidenceFragment via SUPPORTED_BY and to a Source via REFERS_TO (D-14). All seed bounded to S01E01-03 (D-16).

    4. Extend metadata endpoints (META-03): Verify GET /api/series and GET /api/series/{series_id}/episodes work against seeded data. Add GET /api/series/{series_id} endpoint if not present. All responses via Pydantic serializable models.

    5. Update pyproject.toml (D-02): Add pyyaml and pytest-asyncio via uv.
  </action>
  <verify>
    <automated>pytest backend/tests/test_seed_idempotency.py -x -v 2>&1 | tail -30</automated>
    <automated>curl -s http://127.0.0.1:8000/api/series | python -c "import sys,json; d=json.load(sys.stdin); assert len(d)>0; print(f'Series count: {len(d)}')"</automated>
    <automated>curl -s http://127.0.0.1:8000/api/series/series_dexter/episodes | python -c "import sys,json; d=json.load(sys.stdin); assert len(d)==3; print(f'Episodes: {len(d)}')"</automated>
  </verify>
  <done>
    Idempotent setup creates constraints for all Phase 1 types; ontology validation rejects undeclared types; seed creates deterministic graph with 1 Series, 3 Episodes, 9 Characters, Events, Locations, Claims/Sources/Evidence with provenance chains; metadata endpoints return data through Pydantic models.
  </done>
</task>

<task type="auto">
  <name>Task 3: Spoiler-Aware Graph API & Automated Acceptance Evidence</name>
  <files>
    backend/app/api/graph.py
    backend/app/domain/graph.py
    backend/app/spoiler/filter.py
    backend/tests/conftest.py
    backend/tests/test_graph_api.py
    backend/tests/test_seed_idempotency.py
    backend/scripts/smoke.sh
    pyproject.toml
  </files>
  <action>
    Build the core GET /api/series/{series_id}/graph endpoint with spoiler filtering, and provide comprehensive automated acceptance evidence.

    1. Implement GET /api/series/{series_id}/graph endpoint (API-01, D-05, D-06, D-07, D-08, D-09, D-12): Create backend/app/api/graph.py with prefix /api/series. Input validation: unknown series_id -> 404 with code "series_not_found"; missing/non-persisted visible_until_order -> 422 with code "invalid_visible_until_order". Cypher queries filter by visible_from_order for all node types, structural relationships, and provenance nodes. Claim temporal validity enforced independently (valid_from/valid_until). Response model per D-06: series, visible_until_order, nodes, edges, claims, sources, evidence. Graph closure enforced by Pydantic validator. All filtering in parameterized Cypher, not post-processing (API-02).

    2. Write tests (D-21, D-22, D-23, API-04, SEED-04): Isolated tests for error response shapes and model validation. Live-Neo4j integration tests for constraints, seed counts, idempotency (double-seed), spoiler boundaries at orders 1/2/3 with full-JSON sentinel assertions, claim validity enforcement, and graph closure.

    3. Create smoke command (D-24): backend/scripts/smoke.sh that verifies: Neo4j Browser, Swagger, React dev server, /health, series/episode APIs, seed execution, graph boundary at order 1 (no S01E02/03 sentinels), invalid order returns 422. Outputs pass/fail summary. Document in pyproject.toml scripts.

    4. Add pytest fixture infrastructure (D-21): backend/tests/conftest.py with test Neo4j fixture, seed fixture, and FastAPI TestClient with lifespan wiring.
  </action>
  <verify>
    <automated>pytest backend/tests/test_graph_api.py -x -v 2>&1 | tail -30</automated>
    <automated>pytest backend/tests/test_seed_idempotency.py -x -v 2>&1 | tail -30</automated>
    <automated>bash backend/scripts/smoke.sh 2>&1 | tail -20</automated>
    <automated>curl -s 'http://127.0.0.1:8000/api/series/series_dexter/graph?visible_until_order=1' | python -c "import sys,json; r=json.load(sys.stdin); assert len(r['nodes']) > 0; print(f'Graph nodes at order 1: {len(r[\"nodes\"])}')"</automated>
  </verify>
  <done>
    Graph endpoint returns filtered data by episode boundary; boundary tests at orders 1-3 prove no leakage; unknown series -> 404; invalid order -> 422; unavailable Neo4j -> 503; graph closure enforced; smoke command passes all checks; all automated tests pass.
  </done>
</task>

</tasks>

<threat_model>

**Security enforcement:** enabled
**ASVS Level:** 1 (essential)

### Data-access layer spoiler integrity

| Threat | Mitigation | ASVS Mapping |
|--------|-----------|--------------|
| **Spoiler leakage through response**: Future nodes, edges, claims, evidence, or metadata returned despite visible_until_order filter | Spoiler filtering enforced in parameterized Cypher before response construction (D-07, D-08). Response model validators enforce graph closure (every edge source/target in nodes array). Boundary tests with full-JSON sentinel assertions at orders 1, 2, 3 (D-23). | V1.1 Secure Input Handling |
| **Spoiler leakage through relationship traversal**: Native Neo4j relationship returned when one endpoint is hidden | All relationship queries filter by both direction endpoints' `visible_from_order` in Cypher WHERE clause. No `OPTIONAL MATCH` used for spoiler-boundary queries. | V1.5 Input Validation |
| **Spoiler leakage through claim validity bypass**: Claim returned when `valid_until_order < visible_until_order` | Claim visibility AND temporal validity are enforced independently in the same Cypher query (API-03). | V1.1 Secure Input Handling |
| **Spoiler leakage through error messages**: Error responses revealing future data existence, node IDs, or metadata | All errors use stable machine-readable `detail.code` and safe `detail.message` (D-09). Database failures mapped to sanitized 503 with no driver details, credentials, URIs, or Cypher (D-20). | V7.1 Error Handling |
| **Database authentication leakage**: Neo4j credentials or connection strings exposed in error responses or logs | Centralized exception handler catches driver exceptions and returns only sanitized 503 (Task 1). | V7.2 Credential Management |

### Input validation and boundary enforcement

| Threat | Mitigation | ASVS Mapping |
|--------|-----------|--------------|
| **Invalid `visible_until_order`**: Missing, non-numeric, or non-persisted episode order accepted | FastAPI type validation plus explicit Cypher lookup to verify the order exists for the given series (D-05, D-09). Returns 422. | V1.1 Input Validation |
| **Unknown `series_id`**: Non-existent series ID requested | Path parameter validated against database; 404 if absent (D-09). | V1.1 Input Validation |
| **Cypher injection**: Malicious input attempting Cypher injection via series_id or visible_until_order | All user-supplied values passed as Cypher parameters (`$series_id`, `$visible_until_order`), never interpolated (D-07, D-17). | V1.3 Injection Prevention |

### Seed and ontology integrity

| Threat | Mitigation | ASVS Mapping |
|--------|-----------|--------------|
| **Undeclared node/relationship types**: Seed data using types not in ontology YAML | Ontology validation rejects undeclared values before any Cypher executes (D-10). | V1.5 Input Validation |
| **Non-idempotent seed**: Rerunning seed creates duplicates or diverges state | MERGE by stable ID, converge seed-owned properties only, preserve user-origin content (D-15). Double-seed test proves exact invariants (D-22). | V1.8 Idempotency |
| **Missing `visible_from_order`**: Nodes seeded without spoiler protection | Existence constraints on `visible_from_order` for all spoiler-sensitive types (D-13, D-17). CI check enforces zero NULL values. | V1.5 Input Validation |

</threat_model>

---

## Verification

Each task below must produce captured runtime output, not scaffold presence or file listing.

### Task 1 verification
- [ ] `docker-compose up -d neo4j` starts successfully; Neo4j Browser reachable at `http://localhost:7474`
- [ ] FastAPI starts without Neo4j running; Swagger reachable at `http://127.0.0.1:8000/docs`
- [ ] `/health` returns `200` with `"database": "connected"` when Neo4j is up
- [ ] `/health` returns `503` with `"database": "unavailable"` when Neo4j is stopped
- [ ] Backend endpoints return sanitized 503 (not driver exception) when Neo4j is unavailable
- [ ] React dev server reachable at `http://localhost:5173`
- [ ] Module-level import of `backend.app.graph.database` does not trigger a connection (test isolation guarantee)
- [ ] No duplicate `FastAPI()` construction in `main.py`

### Task 2 verification
- [ ] `uv run python -m backend.app.graph.setup` creates uniqueness constraints for Series, Episode, Character, Event, Location, Claim, Source, EvidenceFragment
- [ ] Existence constraints on `visible_from_order` for all spoiler-sensitive types
- [ ] Ontology validation rejects a seed value with an undeclared node type
- [ ] Seed creates: 1 Series, 3 Episodes, ~9 Characters, 3+ Events, 4+ Locations, 8+ Claims, 3+ Sources, 8+ EvidenceFragment nodes
- [ ] Every seeded node has a deterministic namespaced string ID
- [ ] Every spoiler-sensitive node has `visible_from_order` set
- [ ] Every seeded Claim links to ≥1 EvidenceFragment and its Source
- [ ] `PART_OF` and `PRECEDES` relationships created between Series and Episodes
- [ ] `GET /api/series` returns `[{"id": "series_dexter", ...}]`
- [ ] `GET /api/series/series_dexter/episodes` returns 3 episodes in order

### Task 3 verification
- [ ] `GET /api/series/series_dexter/graph?visible_until_order=1` returns only S01E01-visible nodes, edges, claims, sources, evidence
- [ ] `GET /api/series/series_dexter/graph?visible_until_order=2` includes S01E01–02 data; excludes S01E03
- [ ] `GET /api/series/series_dexter/graph?visible_until_order=3` includes all data
- [ ] Each boundary test asserts: IDs, names, labels, edges, claims, evidence text/locators, and count signals in the full JSON response
- [ ] Claim temporal validity enforced independently: a claim with `valid_until_order=1` is excluded from order-2 response even if `visible_from_order=1`
- [ ] Graph closure: every returned edge's `source` and `target` appear in `nodes`
- [ ] Unknown series_id → 404 with `detail.code == "series_not_found"`
- [ ] Missing/non-persisted `visible_until_order` → 422 with `detail.code == "invalid_visible_until_order"`
- [ ] Database unavailable → 503 with `detail.code == "database_unavailable"`
- [ ] All automated tests pass (`uv run pytest`)
- [ ] Seed idempotency: running seed twice yields exact same node/relationship counts and graph response
- [ ] Smoke command (`bash backend/scripts/smoke.sh`) passes all checks with captured output

---

## Success Criteria

1. **INFRA-01**: `docker-compose up`, `uv run uvicorn`, and `npm run dev` produce reachable URLs (Browser, Swagger, React).
2. **INFRA-02**: `/health` performs a real Neo4j connectivity check; healthy returns 200, unavailable returns 503.
3. **INFRA-03**: Backend lifecycle does not require Neo4j at import time; modules can be imported in isolated tests without connection side effects; queries use managed transactions and parameters.
4. **META-01**: Idempotent setup command creates uniqueness/existence constraints for all Phase 1 node types.
5. **META-02**: Setup persists Dexter series, S01E01–03, `PART_OF`, and `PRECEDES` with correct `episode_order` and `visible_from_order`.
6. **META-03**: `GET /api/series` returns series; `GET /api/series/{id}/episodes` returns 3 ordered episodes through Pydantic models.
7. **API-01**: `GET /api/series/{series_id}/graph?visible_until_order=N` returns serializable nodes, edges, claims, sources, evidence, and boundary metadata.
8. **API-02**: Cypher WHERE clauses use `visible_from_order` filtering before response construction; no post-processing filtering.
9. **API-03**: Claim `valid_from_order`/`valid_until_order` enforced independently from `visible_from_order`; graph closure preserved.
10. **API-04**: Boundary tests at orders 1, 2, 3 prove no future leakage; invalid inputs return defined errors (404, 422).
11. **SEED-01**: Manual Dexter S01E01–03 seed includes Character, Event, Location, and Claim records with visibility, confidence, effect, status, and validity metadata.
12. **SEED-02**: Source and EvidenceFragment records include episode references, locators, retrieval metadata, and content hashes where available.
13. **SEED-03**: Every seeded Claim links to ≥1 EvidenceFragment and its Source; seed is idempotent.
14. **SEED-04**: Executed graph queries and smoke checks demonstrate an evidence-backed network at each episode boundary.

---

*Phase: 01-backend-graph-foundation*
*Plan created: 2026-07-29*
*Author: gsd-planner*
