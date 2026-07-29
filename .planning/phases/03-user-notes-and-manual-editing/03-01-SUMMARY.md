---
phase: 03-user-notes-and-manual-editing
plan: "01"
subsystem: api
status: complete
tags: [fastapi, pydantic, openapi, validation, pytest, ontology]

requires:
  - phase: 01-backend-graph-foundation
    provides: Lifespan-owned Neo4j runtime, fail-closed graph API, graph closure, and sanitized database errors
provides:
  - Strict user-content request/response contracts with ontology-locked enums
  - Stable canonical/candidate/user origin typing across graph payloads
  - Sanitized shared validation/database error envelope and reusable OpenAPI declarations
  - Wave-0 model, OpenAPI, and live-integration test homes for Plans 03-02 and 03-03
affects: [03-02-user-content-persistence, 03-03-graph-integration, frontend-api-contract]

tech-stack:
  added: []
  patterns: [strict extra-forbid mutation models, ontology-drift assertions, stable typed error envelope, user-only integration cleanup]

key-files:
  created:
    - backend/app/domain/user_content.py
    - backend/tests/test_user_content_models.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_user_content_api.py
  modified:
    - backend/app/domain/graph.py
    - backend/app/core/errors.py

key-decisions:
  - "Keep public origin classification exactly canonical, candidate, or user and reuse it in every graph model without a parallel discriminator."
  - "Restrict note targets, custom node labels, and custom predicates with finite StrEnum contracts tested against the live ontology YAML."
  - "Make PATCH bodies single-field required contracts so empty bodies and explicit nulls fail validation without accepting immutable fields."
  - "Retain the existing installer name as a compatibility alias while installing both sanitized RequestValidationError and Neo4j handlers."

patterns-established:
  - "Public mutation contracts use ConfigDict(extra='forbid', str_strip_whitespace=True), bounded strings, and no arbitrary property maps."
  - "FastAPI validation failures return only detail.code/detail.message and never framework issue arrays or rejected values."
  - "Live user-content tests clean only origin=user resources and preserve canonical seed data."

requirements-completed:
  - NOTE-01
  - NOTE-02
  - NOTE-03

coverage:
  - id: D1
    description: "Strict note/custom-content models expose only locked fields, bounded values, and ontology-approved enum choices while preserving graph compatibility and closure."
    requirement: "NOTE-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_user_content_models.py (23 passed)"
        status: pass
      - kind: integration
        ref: "uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_graph_api.py -k 'model or dangling or ontology' (24 passed, 9 deselected)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A typed sanitized error envelope covers framework validation and Neo4j failures with reusable 404/409/422/503 OpenAPI declarations."
    requirement: "NOTE-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_openapi_contract.py (4 passed)"
        status: pass
      - kind: integration
        ref: "Task 03-01-02 selector (31 passed, 6 deselected)"
        status: pass
      - kind: other
        ref: "hermes-verify-yqc2c0fk.py (ad-hoc, exited 0 and deleted)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Wave-0 model, OpenAPI, and live user-content integration homes exist without skips, route stubs, or future route registration."
    requirement: "NOTE-02"
    verification:
      - kind: integration
        ref: "uv run pytest -q (40 passed)"
        status: pass
      - kind: other
        ref: "app.openapi() (openapi-ok, 5 existing path templates)"
        status: pass
    human_judgment: false

duration: 9 min
completed: 2026-07-29
---

# Phase 03 Plan 01: Contract and Wave-0 Foundation Summary

**Strict ontology-locked user-content schemas, stable sanitized FastAPI errors, and reusable Wave-0 test infrastructure without registering future CRUD routes**

## Performance

- **Duration:** 9 min
- **Started:** 2026-07-29T10:10:47Z
- **Completed:** 2026-07-29T10:20:30Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added strict note, custom-node, and custom-relationship request/response models with exact public allowlists, bounded plain text, immutable/server-owned field rejection, UTC timestamps, and positive visibility contracts.
- Stabilized graph `origin` as `canonical | candidate | user` while preserving existing graph field shapes, provenance-required claims, and `GraphResponse` closure enforcement.
- Centralized the exact `{"detail":{"code":"...","message":"..."}}` error envelope, sanitized framework validation and Neo4j handlers, and reusable typed OpenAPI 404/409/422/503 declarations.
- Created executable model/OpenAPI tests plus live Neo4j helper fixtures that clean only `origin=user`, manage a second series, compare hidden/missing responses, override database dependencies, and capture direct snapshots.

## Task Commits

Each task was committed atomically:

1. **Task 03-01-01: Create strict user-content models and ontology-locked public enums** — `8113d60` (feat)
2. **Task 03-01-02: Centralize the stable error contract and create Wave-0 contract/integration test homes** — `2bcb339` (feat)

## Files Created/Modified

- `backend/app/domain/user_content.py` — Strict enums, request models, PATCH contracts, typed responses, examples, bounds, and UTC validation.
- `backend/app/domain/graph.py` — Shared `Origin` typing for nodes, edges, claims, sources, and evidence while retaining closure.
- `backend/app/core/errors.py` — Typed errors, exact runtime envelope, sanitized validation/database handlers, and reusable response declarations.
- `backend/tests/test_user_content_models.py` — Schema, immutable-field, enum/ontology-drift, bounds, compatibility, and closure tests.
- `backend/tests/test_openapi_contract.py` — Reusable error-envelope and OpenAPI-reference assertions with foundation tests.
- `backend/tests/test_user_content_api.py` — Wave-0 live TestClient, user-only cleanup, second-series, hidden/missing, override, and snapshot helpers.

## Decisions Made

- Used conservative limits of 4,000 characters for note content, 200 for labels, and 255 for stable identifiers to mitigate unbounded payloads without adding rich text or arbitrary maps.
- Used required single-field PATCH models rather than optional nullable fields; this rejects `{}` and explicit `null` while keeping the public mutation surface minimal.
- Kept user relationship responses `GraphEdge`-compatible and independent from provenance-required `GraphClaim`; no evidence rules were weakened.
- Preserved `install_database_error_handlers` as a compatibility alias so unchanged `backend/app/main.py` receives the complete shared handler set without route or lifespan changes.

## Deviations from Plan

None - plan executed exactly as written.

## Security Notes

- **Spoofing/ownership:** strict extra-forbid request models reject IDs, series, origin, visibility, timestamps, endpoint replacement, and parallel discriminators.
- **Cypher-shape tampering:** custom node/predicate enums are finite and drift-tested against narrative plus participation/character ontology groups; structural, provenance, and revision predicates are excluded.
- **Information disclosure:** validation/database responses expose only stable code/message fields; tests and ad-hoc verification confirm rejected values, credentials, and Cypher text do not leak.
- **Denial of service:** plain text, labels, and identifiers are stripped, non-empty, and length-bounded; arbitrary property dictionaries are absent.
- No HIGH threat remained unmitigated in this contract/Wave-0 scope.

## Issues Encountered

- The first two ad-hoc verification attempts could not import the repository package because a script launched from Windows `%TEMP%` receives that directory as `sys.path[0]`, and MSYS `PYTHONPATH` did not translate for the native interpreter. The final OS-safe tempfile inserted the native repository root explicitly, exited 0 with `hermes-ad-hoc-verification-ok`, and was deleted. This affected only the temporary verification harness, not repository code.
- The existing third-party Starlette/httpx deprecation warning remained unchanged in every TestClient run.

## Verification Evidence

### Task 03-01-01

- `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_graph_api.py -k 'model or dangling or ontology'` → **24 passed, 9 deselected, 1 warning in 0.70s**.
- Additional `uv run pytest -q backend/tests/test_graph_api.py` → **10 passed, 1 warning in 2.46s**.
- `git diff --check` → **passed**.

### Task 03-01-02

- `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_openapi_contract.py backend/tests/test_graph_api.py -k 'error or validation or model or dangling or degraded'` → **31 passed, 6 deselected, 1 warning in 1.08s**.
- Explicit database/degraded selection → **3 passed, 1 warning in 1.11s**.
- Python compile check for errors/OpenAPI/API test-home files → **passed**.
- Disabled-test marker search over Wave-0 user-content tests → **0 matches**.
- `git diff --check` → **passed**.

### Plan Verification

- `uv run pytest -q backend/tests/test_user_content_models.py backend/tests/test_openapi_contract.py` → **27 passed, 1 warning in 0.57s**.
- `uv run pytest -q backend/tests/test_graph_api.py` → **10 passed, 1 warning in 2.09s**.
- `uv run pytest -q` → **40 passed, 1 warning in 2.89s**.
- `uv run python -c "from backend.app.main import app; ..."` → **openapi-ok; path-templates=5**.
- `git diff --check` plus committed-range no-frontend/no-out-of-scope assertions → **diff-scope-ok**.
- Ad-hoc `hermes-verify-yqc2c0fk.py` → **hermes-ad-hoc-verification-ok**, exit 0; temporary file deleted.

## User Setup Required

None - no external service configuration or new dependency is required.

## Next Phase Readiness

- Plan 03-02 can consume the strict contracts, error helpers, and Wave-0 live fixtures to implement managed Neo4j writes and all 13 CRUD routes.
- Plan 03-03 has not begun. Only the five existing path templates remain registered.
- This is an out-of-sequence backend slice: Phase 2 remains pending, frontend integration/visual distinction remains pending in `frontend-work`, and overall Phase 03 is **not complete**.

## Self-Check: PASSED

- All four created files and both modified contract files exist.
- Task commits `8113d60` and `2bcb339` are present in git history.
- Both exact task selectors, all plan-level commands, the full 40-test suite, OpenAPI generation, degraded startup, and the ad-hoc validation guard passed.
- No frontend, route-registration, persistence, ingestion, LLM, queue, vector, revision, ORM, or ontology-expansion file changed.
- Plans 03-02 and 03-03 were not started; overall Phase 03 and frontend acceptance remain pending.

---
*Phase: 03-user-notes-and-manual-editing*
*Completed: 2026-07-29*
