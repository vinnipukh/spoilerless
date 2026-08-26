---
phase: 12-post-hardening-remediation-and-code-quality
plan: 02
subsystem: api
tags: [fastapi, neo4j, boundary, spoiler-policy, pytest]

# Dependency graph
requires:
  - phase: 11-spoiler-boundary-tracer (SEC-BE-001/002, D-01)
    provides: resolve_effective_boundary fail-closed resolver and boundary test scaffolding (scratch series + live-client fixtures)
provides:
  - Strictly-typed resolve_effective_boundary using core http_error envelope (THERMO-P3-04)
  - Single-authority boundary resolution on all user-content and revision read routes — no raw pre-clamp persistence checks (THERMO-P1-01)
  - Candidates read routes no longer execute duplicate boundary lookups; dead helper deleted (THERMO-P3-01)
  - Regression tests proving anonymous visible_until_order=999 clamps to order 1 across notes/revisions/custom-nodes
affects: [12-10 boundary require_boundary extraction, 12-11 revision module refactor, 12-15 structural cache invalidation]

# Actuals (#2632)
actuals:
  tokens: 3450   # chars/4 over realized diff (5 files, +95/-43)
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TYPE_CHECKING-only service imports to keep the shared boundary module free of runtime import cycles"

key-files:
  created: []
  modified:
    - spoilerless/app/api/boundary.py
    - spoilerless/app/api/user_content.py
    - spoilerless/app/api/revisions.py
    - spoilerless/app/api/candidates.py
    - spoilerless/tests/test_security_boundary.py

key-decisions:
  - "Removed only the API-layer premature _require_persisted_boundary calls; repository-internal validations of the ALREADY-CLAMPED effective value stay (defense in depth on a clamped arg, not an un-clamped raw check)."
  - "Deleted _require_resolved_boundary from candidates.py entirely — resolve_effective_boundary already performs the identical persisted-episode validation."
  - "Regression tests seed custom nodes with episode_id/created_at/updated_at matching scratch episodes so CustomNodeResponse validation passes."

patterns-established:
  - "Boundary invariant D-01/D-05: every spoiler-sensitive read route resolves ONLY via resolve_effective_boundary before hitting its repository."

requirements-completed: [THERMO-P1-01, THERMO-P3-01, THERMO-P3-04]  # REQUIRED

coverage:
  - id: D1
    description: "boundary.py strictly typed (GraphService/ProgressService via TYPE_CHECKING) and raises http_error instead of local _error helper"
    requirement: "THERMO-P3-04"
    verification:
      - kind: unit
        ref: "python -c import spoilerless.app.api.boundary (signature annotations == GraphService/ProgressService); full suite green"
        status: pass
    human_judgment: false
  - id: D2
    description: "user_content.py/revisions.py routes perform zero raw un-clamped boundary checks; every route resolves via resolve_effective_boundary only"
    requirement: "THERMO-P1-01"
    verification:
      - kind: integration
        ref: "spoilerless/tests/test_security_boundary.py#test_anonymous_notes_clamped_to_order_one"
        status: pass
      - kind: integration
        ref: "spoilerless/tests/test_security_boundary.py#test_anonymous_revisions_clamped_to_order_one"
        status: pass
    human_judgment: false
  - id: D3
    description: "candidates.py list/get endpoints no longer double-query the boundary; orphaned _require_resolved_boundary helper deleted"
    requirement: "THERMO-P3-01"
    verification:
      - kind: unit
        ref: "grep -rn '_require_resolved_boundary' spoilerless/app → 0 hits; candidates tests in test_security_boundary.py green"
        status: pass
    human_judgment: false
  - id: D4
    description: "Anonymous visible_until_order=999 clamps to order 1 (200 OK) on notes/revisions/custom-nodes; order-2 custom node returns 404 at clamped order 1"
    requirement: "THERMO-P1-01"
    verification:
      - kind: integration
        ref: "spoilerless/tests/test_security_boundary.py#test_anonymous_custom_node_clamped_to_order_one"
        status: pass
    human_judgment: false

# Metrics
duration: ~25min
completed: 2026-08-26
status: complete
---

# Plan 12-02 Summary: Boundary Verification Simplification, Invariant Enforcement & Type Hygiene

**All spoiler-sensitive read routes now resolve their boundary through exactly one fail-closed call — anonymous `visible_until_order=999` clamps to order 1 (200) instead of 422, candidate reads lost their duplicate boundary Cypher roundtrip, and `resolve_effective_boundary` is strictly typed.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-26T08:48Z (approx)
- **Completed:** 2026-08-26T09:13Z
- **Tasks:** 3/3 completed
- **Files modified:** 5

## Accomplishments
- `resolve_effective_boundary` is now strictly typed (`service: GraphService`, `progress_service: ProgressService` under `TYPE_CHECKING`) and uses the stable `core.errors.http_error` envelope; bespoke `_error` helper removed.
- All 6 premature `_require_persisted_boundary(series_id, visible_until_order)` calls removed (4 in `user_content.py`: list_notes/get_note/get_custom_node/get_custom_relationship; 2 in `revisions.py`: list_revisions/get_revision). Each route now resolves ONLY via `resolve_effective_boundary` and passes the clamped `effective` downstream.
- Both redundant `_require_resolved_boundary(graph_service, series_id, effective)` calls removed from candidates `list_candidates`/`get_candidate` and the now-unreferenced helper deleted.
- 3 new regression tests lock the invariant: anonymous 999 → 200 (clamped order 1) on `/notes` and `/revisions`; custom node at order 2 → 404 at clamped order 1 while order-1 node stays visible.

## Task Commits

Each task was committed atomically:

1. **Task 1: Clean up boundary resolver types and error helper** - `55e73a0` (feat)
2. **Task 2: Remove premature un-clamped boundary checks and duplicate queries** - `9eca8dd` (feat)
3. **Task 3: Add boundary clamping tests for all user content and revision routes** - `c66eb0c` (test)

**Plan metadata:** docs commit follows this summary.

## Files Created/Modified
- `spoilerless/app/api/boundary.py` — TYPE_CHECKING imports for GraphService/ProgressService; parameter annotations; `http_error` replaces `_error`
- `spoilerless/app/api/user_content.py` — 4 raw pre-clamp checks deleted; routes resolve via `resolve_effective_boundary` only
- `spoilerless/app/api/revisions.py` — 2 raw pre-clamp checks deleted; same single-resolver pattern
- `spoilerless/app/api/candidates.py` — 2 redundant post-resolution boundary re-checks deleted; `_require_resolved_boundary` helper removed
- `spoilerless/tests/test_security_boundary.py` — `_seed_custom_node`/`_delete_custom_nodes` helpers + 3 clamping regression tests (scratch series, full teardown)

## Decisions Made
- Repository-layer `_require_persisted_boundary` internals (`repository/user_content.py` get_note/list_notes/_custom_read) were intentionally LEFT in place: they validate the already-clamped `effective` argument passed by the routes, not the raw query param, so they are defense-in-depth rather than the THERMO-P1-01 defect. Removing them was outside this plan's declared file scope.
- Test seeds write `episode_id = {SCRATCH}:episode:{order}` plus `created_at`/`updated_at` datetimes so seeded nodes satisfy `CustomNodeResponse` validation exactly like production-created nodes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Test-seeded custom nodes failed response validation**
- **Found during:** Task 3 (regression tests)
- **Issue:** Nodes seeded with only label/visible_from_order lacked `created_at`/`updated_at`/`episode_id`, so `CustomNodeResponse.model_validate` raised pydantic ValidationError (500) instead of exercising the clamp path.
- **Fix:** Seed helper now sets realistic `episode_id` (scratch episode ids from conftest bootstrap) and datetime stamps.
- **Files modified:** `spoilerless/tests/test_security_boundary.py`
- **Verification:** full `test_security_boundary.py` run green (9 passed)
- **Committed in:** `c66eb0c`

---

**Total deviations:** 1 auto-fixed (Rule 3)
**Impact on plan:** No scope creep — fix confined to new test seeding code.

## Issues Encountered
- Plan's cited line numbers had drifted slightly (e.g., candidates checks at 199/245 not 192/237; revisions used `UserContentRepository(database)` directly rather than `_repository(database)`). Resolved by grepping identifiers at HEAD as the task instructions directed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for 12-10 (require_boundary extraction): the single-resolver pattern is now uniformly enforced across all read routes, giving a clean seam for the shared guard extraction.
- Note for 12-06/12-11: repository-internal `_require_persisted_boundary` remains as clamped-input defense-in-depth; if a later plan removes it, it must replace it inside the repository layer, not the API layer.
