---
phase: 12-post-hardening-remediation-and-code-quality
plan: 01
subsystem: api
tags: [pydantic, fastapi, privacy, user-content, regression-tests, neo4j]

# Dependency graph
requires:
  - phase: 11-spoiler-boundary-owner-scoping
    provides: owner-bound user content routes with D-02 `_shape_note_response` privacy scrubbing and `user_session` test fixtures
provides:
  - Nullable `user_id` on NoteResponse / CustomNodeResponse / CustomRelationshipResponse so non-owner reads serialize with `null` instead of raising 500 ValidationError
  - D-02 privacy regression tests covering anonymous, non-owner, owner and admin read paths
affects: [12-remaining-remediation-plans, verifier, uat]

# Actuals (#2632)
actuals:
  tokens: 3750
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Privacy-shaping regression tests reuse the hermetic second_series fixture so reads resolve at fail-closed boundary order 1 for anonymous/non-owner readers"

key-files:
  created: []
  modified:
    - spoilerless/tests/test_user_content_api.py

decisions:
  - "Task 1 skipped as already landed: e90a591 made user_id nullable on all three response models exactly per plan"
  - "Regression tests seed content on the isolated test-series:user-content fixture instead of the canonical dexter series"

patterns-established:
  - "_seed_owner_user_content/_read_all_user_content helpers centralize create-then-read flows for privacy assertions across roles"

requirements-completed: [THERMO-P0-01]

coverage:
  - id: D1
    description: "Nullable user_id on NoteResponse/CustomNodeResponse/CustomRelationshipResponse (non-owner reads return null, not 500)"
    requirement: THERMO-P0-01
    verification:
      - kind: integration
        ref: "spoilerless/tests/test_user_content_api.py#test_anonymous_user_content_reads_scrub_user_id"
        status: pass
      - kind: integration
        ref: "spoilerless/tests/test_user_content_api.py#test_non_owner_user_content_reads_scrub_user_id"
        status: pass
      - kind: integration
        ref: "spoilerless/tests/test_user_content_api.py#test_owner_and_admin_reads_preserve_user_id"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-02 scrubbing preserved: pre-existing suite green after regression-test addition"
    verification:
      - kind: integration
        ref: "pytest spoilerless/tests/test_user_content_api.py -q"
        status: pass
    human_judgment: false

# Metrics
duration: ~45min (incl. two full live-DB suite runs)
completed: 2026-08-26
status: complete
---

# Phase 12 Plan 01: P0 Blocker — Nullable user_id on User Content Responses Summary

**Anonymous and non-owner reads of notes/custom nodes/custom relationships now serialize with `user_id: null` instead of tripping a 500 Pydantic ValidationError, proven by role-matrix regression tests.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-26 (session start)
- **Completed:** 2026-08-26
- **Tasks:** 2/2
- **Files modified:** 1

## Accomplishments
- Confirmed Task 1's model change (`Identifier | None` on NoteResponse, CustomNodeResponse, CustomRelationshipResponse) was already present verbatim in HEAD via commit e90a591 — no edit needed.
- Added three regression tests to `spoilerless/tests/test_user_content_api.py` proving the D-02 contract end-to-end against the live Neo4j: anonymous reads → 200 + `user_id: None` on notes list/get, custom-node get, custom-relationship get; non-owner authenticated reads → same scrubbing; owner and admin reads → author `user_id` preserved.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update response models** — **no commit (deviation)**: change already landed in `e90a591` before this plan executed; verified field-by-field against the plan spec.
2. **Task 2: Privacy regression tests** - `2227712` (test)

**Plan metadata:** committed separately by the orchestrator convention as `docs(12-01): complete 12-01 plan summary`.

## Files Created/Modified
- `spoilerless/tests/test_user_content_api.py` — +125 lines: `_seed_owner_user_content` / `_read_all_user_content` helpers plus `test_anonymous_user_content_reads_scrub_user_id`, `test_non_owner_user_content_reads_scrub_user_id`, `test_owner_and_admin_reads_preserve_user_id`

## Decisions Made
- Skipped Task 1 edits because commit e90a591 already carried the exact planned signatures (default=None, PROB-02/#4 description text, examples) on all three models — documented as deviation rather than re-applying.
- Seeded probe content on the hermetic `second_series` fixture (`test-series:user-content`) rather than the canonical dexter series: anonymous/unauthenticated readers are fixed at boundary order 1 there (persisted episode at order 1), and cleanup is fully covered by existing fixtures.
- Related two user-owned nodes intra-series for the custom relationship (cross-series references are rejected with 404).

## Deviations from Plan

### Auto-fixed Issues

**1. Task 1 already landed in e90a591**
- **Found during:** Task 1 precondition check (per delegation context)
- **Issue:** All three response models already carried `user_id: Identifier | None = Field(default=None, ...)` with the plan's exact descriptions/examples
- **Fix:** No edit applied; verified line-by-line (NoteResponse L134, CustomNodeResponse L200, CustomRelationshipResponse L274)
- **Files modified:** none
- **Verification:** direct file inspection at HEAD
- **Committed in:** n/a (e90a591, pre-existing)

**2. [Rule 1 - Bug] First-draft relationship seeding used a cross-series target**
- **Found during:** Task 2 (first run of new tests)
- **Issue:** Relating a user-owned node to a canonical `dexter:*` character from `test-series:user-content` is rejected with 404 RESOURCE_NOT_FOUND (relationships are intra-series), so all three tests failed on setup
- **Fix:** Seed helper now creates a second user-owned node within the test series and relates the two
- **Files modified:** spoilerless/tests/test_user_content_api.py
- **Verification:** targeted `-k "scrub_user_id or preserve_user_id"` run: 3 passed
- **Committed in:** 2227712

---

**Total deviations:** 2 auto-handled (1 already-landed skip, 1 Rule 1 bug fix)
**Impact on plan:** Both were contained to test-seeding strategy and a no-op verification; no scope creep, no production code touched.

## Issues Encountered
- First full-file run exposed the cross-series 404 above; fixed and re-run green.
- A transient patching slip briefly duplicated an obj-delete assertion in the pre-existing owner-binding test; caught in diff review and restored byte-for-byte before committing — final diff vs HEAD is purely additive (+125/-0).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- THERMO-P0-01 schema-mismatch blocker is closed: non-owner reads can no longer 500.
- Remaining phase-12 plans (12-02..12-15) can proceed; STATE.md/ROADMAP.md intentionally untouched (orchestrator-owned).
