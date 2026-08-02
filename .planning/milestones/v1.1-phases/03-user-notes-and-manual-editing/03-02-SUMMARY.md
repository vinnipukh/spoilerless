---
phase: 03-user-notes-and-manual-editing
plan: "02"
subsystem: api-database
tags: [fastapi, neo4j, managed-transactions, openapi, pytest, spoiler-safety]

requires:
  - phase: 03-user-notes-and-manual-editing
    plan: "01"
    provides: Strict user-content models, shared sanitized errors, and Wave-0 test homes
  - phase: 01-backend-graph-foundation
    provides: Lifespan-owned Neo4j driver, persisted episode boundaries, canonical seed, and fail-closed graph baseline
provides:
  - Managed retry-safe Neo4j writes and closed ontology-backed query selection
  - Complete five-operation UserNote lifecycle with target-derived spoiler visibility
  - Complete CRUD for five user node types and sixteen user relationship predicates
  - Exact 18-operation OpenAPI inventory across 11 path templates
  - Canonical-preserving idempotent schema setup for user content

affects: [03-03-graph-projection, frontend-api-contract, frontend-work]

tech-stack:
  added: []
  patterns: [pre-generated managed-write commands, static Cypher maps, namespaced ownership, persisted-boundary validation, hidden-equals-missing]

key-files:
  created:
    - backend/app/api/user_content.py
    - backend/app/graph/user_content.py
    - backend/tests/test_user_content_repository.py
  modified:
    - backend/app/api/series.py
    - backend/app/graph/database.py
    - backend/app/graph/ontology.py
    - backend/app/graph/seed.py
    - backend/app/main.py
    - backend/tests/test_user_content_api.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_seed_idempotency.py

key-decisions:
  - "Generate namespaced IDs and UTC timestamps before entering Neo4j managed transaction callbacks so driver retries reuse identical command values."
  - "Select labels and note target types only through server-owned enum-keyed Cypher maps; all public values remain parameters."
  - "Represent user-authored relationships as origin=user Claim nodes with user-rel IDs and derive visibility from the persisted episode and both endpoints."
  - "Require a persisted positive episode boundary before every story-sensitive direct or collection read and make missing visibility fail closed."

patterns-established:
  - "Mutation ownership matches series_id, origin=user, expected label/representation, and user resource namespace in one managed transaction."
  - "User-content reads rematch visible targets/endpoints before projection and expose no hidden count metadata."
  - "Hard delete affects only the exact API-owned resource; custom nodes return resource_in_use when notes or user relationships depend on them."

requirements-completed:
  - NOTE-01
  - NOTE-02
  - NOTE-03

coverage:
  - id: D1
    description: "Managed writes, closed ontology groups, and canonical-preserving schema setup are retry-safe, parameterized, and idempotent."
    requirement: "NOTE-01"
    verification:
      - kind: unit
        ref: "backend/tests/test_user_content_repository.py (6 passed)"
        status: pass
      - kind: integration
        ref: "backend/tests/test_seed_idempotency.py with setup run twice"
        status: pass
      - kind: other
        ref: "hermes-verify-03-02.py setup-preservation probe (exited 0 and deleted)"
        status: pass
    human_judgment: false
  - id: D2
    description: "All five UserNote operations enforce same-series Character/Claim attachment, derived visibility, typed responses, and note-only hard deletion."
    requirement: "NOTE-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_user_content_api.py (33 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "All eight custom node/relationship operations enforce the five node types, sixteen predicates, ownership, endpoint closure, conflicts, and hard deletion."
    requirement: "NOTE-02"
    verification:
      - kind: integration
        ref: "task 03-02-03 selector (31 passed, 8 deselected)"
        status: pass
      - kind: integration
        ref: "backend/tests/test_user_content_api.py and backend/tests/test_openapi_contract.py (39 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The transport contract exposes exactly 18 method/path operations over 11 templates with typed success/error responses and required positive boundaries."
    requirement: "NOTE-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_openapi_contract.py -k 'user_route or health or series' (2 passed, 4 deselected)"
        status: pass
      - kind: other
        ref: "app.openapi() exact template and operation assertion (openapi-ok)"
        status: pass
    human_judgment: false

duration: 40 min
completed: 2026-07-29
status: complete
---

# Phase 03 Plan 02: Managed Persistence and User-Content CRUD Summary

**Retry-safe managed Neo4j persistence and all 13 locked series-scoped note/custom-content operations with fail-closed visibility and canonical isolation**

## Performance

- **Duration:** 40 min
- **Started:** 2026-07-29T10:21:00Z
- **Completed:** 2026-07-29T11:00:59Z
- **Tasks:** 3
- **Files modified:** 11 implementation/test files plus validation, state, roadmap, and this summary

## Accomplishments

- Added database-scoped `execute_write` delegation, immutable pre-retry commands, named ontology groups, static Cypher query maps, and user-content constraints/indexes without changing manual seed ingestion.
- Delivered create/list/direct-read/content-update/hard-delete UserNote routes with exactly one same-series Character or Claim attachment, target-derived visibility, persisted boundaries, deterministic arrays, and hidden-equals-missing behavior.
- Delivered CRUD for all five custom node types and all sixteen participation/character predicates, including endpoint closure, max-derived visibility, immutable ownership fields, in-use conflicts, and canonical/candidate isolation.
- Published the exact 18 operations across 11 OpenAPI templates with typed health, series, success, delete, and stable 404/409/422/503 contracts.

## Task Commits

1. **03-02-01: Managed-write infrastructure, ontology groups, schema, and repository fakes** — `171d95d`
2. **03-02-02: Spoiler-safe UserNote lifecycle** — `94e50b2`
3. **03-02-03: Custom-content CRUD and complete transport contract** — `dcd4d4a`

## Files Created/Modified

- `backend/app/graph/database.py` — Narrow async managed-write hook using one lifespan-owned driver.
- `backend/app/graph/ontology.py` — Preserved named groups and exact user-safe node/relationship subsets.
- `backend/app/graph/seed.py` — Idempotent UserNote/Organization/Object constraints and visibility/series/target indexes.
- `backend/app/graph/user_content.py` — FastAPI-free commands, static parameterized queries, atomic callbacks, ownership, boundary, and CRUD behavior.
- `backend/app/api/user_content.py` — Thin typed router for the exact five note, four custom-node, and four custom-relationship operations.
- `backend/app/api/series.py` — Added summaries and declared 404/503 responses without changing paths or fields.
- `backend/app/main.py` — Registered user-content routes and typed health 200/503 responses while preserving lifespan/CORS/degraded startup.
- `backend/tests/test_user_content_repository.py` — Fake session/transaction evidence for delegation, retries, forwarding, static selection, and early rejection.
- `backend/tests/test_user_content_api.py` — Live note/custom-content CRUD, visibility, ownership, conflict, deletion, and unavailable-database coverage.
- `backend/tests/test_openapi_contract.py` — Exact operation/template inventory and response/schema assertions.
- `backend/tests/test_seed_idempotency.py` — Expanded uniqueness-constraint expectations for new user-content labels.

## Decisions Made

- User-created relationships remain Claim nodes rather than direct dynamic Neo4j relationships; predicate stays a parameter and Plan 03-03 can project them into GraphEdge-compatible output safely.
- Static maps may contain server-authored label text, but no request value ever interpolates a label, predicate, property key, or query fragment.
- Setup adds schema only and never adds, updates, deletes, or resurrects `origin=user` records.
- Frontend behavior and existing graph projection remain owned by later work; this plan exposes storage/API behavior only.

## Deviations from Plan

None - plan executed exactly as written.

## Security Notes

- **Spoofing/ownership:** mutations require the expected namespace, series, representation, and `origin=user`; canonical/candidate records remain unchanged.
- **Tampering/injection:** public values are parameters, public property maps are absent, explicit SET clauses are used, and query shape comes only from closed enum-keyed maps.
- **TOCTOU/retries:** validation and compound mutation occur in one managed callback; IDs/timestamps are generated once before possible callback retry.
- **Information disclosure:** story-sensitive reads first require persisted boundaries, rematch visible targets/endpoints, return no totals, and use identical hidden/missing 404 envelopes.
- **Integrity/deletion:** notes delete only their API-owned attachment and note; in-use custom nodes return 409; custom relationships delete only their user-authored Claim representation.
- No HIGH threat remained open in Plan 03-02 scope.

## Issues Encountered

- The first delegated coding process could not launch Codex's Windows sandbox helper. Retrying with the documented process-isolated `danger-full-access` mode succeeded; every resulting diff was independently reviewed and tested before commit.
- The first Task 03-02-03 pass added production routes but no matching selected tests, causing pytest exit 5. A focused continuation added the required live/OpenAPI tests and fixed exposed behavior; the exact selector then passed 31 tests.
- The existing third-party Starlette/httpx deprecation warning remained unchanged.

## User Setup Required

None - no dependency, credential, or external-service configuration was added.

## Test Evidence

### Per-task gates

- Task 03-02-01 exact command: **6 repository tests passed; 4 selected model/live schema tests passed, 22 deselected**.
- Task 03-02-02 exact selector: **2 note tests passed**; the completed API file later passed **33 tests**.
- Task 03-02-03 exact selector: **31 passed, 8 deselected**.
- `git diff --check` passed before each atomic task commit.

### Plan gates

- Models: **23 passed**.
- Repository: **6 passed**.
- User-content API: **33 passed**.
- OpenAPI health/series/user-route selector: **2 passed, 4 deselected**.
- Existing graph plus seed idempotency: **13 passed**.
- Full suite: **81 passed, 1 unchanged warning in 10.60s**.
- Setup command twice: **41 nodes, 26 relationships** after each run.
- OpenAPI executable assertion: **11 templates, 18 operations**.
- Scope checks: diff/status contain no frontend or prohibited subsystem changes.
- Ad-hoc OS-temp preservation probe: setup retained a synthetic `origin=user` Object, printed `hermes-ad-hoc-setup-preservation-ok`, cleaned the marker, exited 0, and the script was deleted.

## Next Phase Readiness

- Plan 03-03 can add the explicitly disjoint user-authored graph projection and frontend contract handoff using these stable persistence and transport contracts.
- Phase 2, frontend integration/distinct visual treatment, and overall Phase 03 remain pending.
- No Plan 03-03 source file was modified here.

## Self-Check: PASSED

- All three task commits exist and each exact task verification command passed.
- All created files exist; OpenAPI reports exactly 18 operations over 11 templates.
- Full suite, repeat setup, persisted-user preservation probe, diff checks, and no-frontend checks passed.
- `backend/app/api/graph.py` and `backend/app/spoiler/filter.py` remain untouched by this plan.
- Overall Phase 03 is not marked complete.

---
*Phase: 03-user-notes-and-manual-editing*
*Completed: 2026-07-29*
