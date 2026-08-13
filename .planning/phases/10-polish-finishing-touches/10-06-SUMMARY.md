---
phase: 10-polish-finishing-touches
plan: 06
subsystem: api
tags: [expansion, semantic-expansion, scene-state, undo, recovery, openapi, d-21, d-48]

# Dependency graph
requires:
  - phase: 10-polish-finishing-touches
    provides: 10-03 typed visualization route + OpenAPI inventory; 10-04 scene reducer + local-placement additions path
provides:
  - Allowlisted semantic expansion endpoint (7 keys, limit 1..25, uncached, OpenAPI 52/39)
  - Strict delta DTO (anchor + additions + edges, no hidden totals)
  - Expansion history in the scene reducer: Undo (newest-record pop), Collapse (per anchor), Back to Episode Overview
affects: [10-07 Answer Graph/focus, 10-08 benchmarks, 10-10 UAT]

# Actuals (#2632) — pairs with the plan's `estimate` (30000 tokens) on the same scale (chars/4 over the realized diff).
actuals:
  tokens: 14200
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Expansion route mirrors the visualization route envelope (shared boundary resolver, typed 404/422/503) but BYPASSES cache-aside entirely (T10-CACHE-06)
    - Strict delta projection: anchor always first and never counts against the limit; additions sorted by (reveal order, id) — deterministic bound
    - Edge surfacing restricted per expansion key (family → FAMILY_OF only) — a neighbor expansion never leaks other semantic families (D-21)
    - History-based undo: each ADD_EXPANSION carries an ExpansionRecord; UNDO pops the newest and removes exactly its additions

key-files:
  created: []
  modified:
    - spoilerless/app/api/graph.py
    - spoilerless/app/services/visualization.py
    - spoilerless/app/domain/visualization.py
    - spoilerless/tests/test_visualization_projection.py
    - spoilerless/tests/test_openapi_contract.py
    - spoilerless/tests/test_frontend_contract_doc.py
    - docs/reference/frontend-api-contract.md
    - frontend/src/api/graph.ts
    - frontend/src/hooks/useSceneState.ts
    - frontend/src/hooks/useSceneState.test.ts

key-decisions:
  - "Expansion is a READ route with the same envelope as visualization but zero caching in Phase 10 — every request resolves the safe boundary and current graph before projection (T10-CACHE-06)."
  - "Clues expand claims AND their supporting evidence (D-21); evidence expands evidence + sources; family/work/conflict/locations expand only their own edge family."
  - "Undo is history-based, not heuristic: the newest ExpansionRecord is popped and exactly its additions removed — untracked expansions are never guessed at (D-48)."
  - "Back to Episode Overview clears exploration layers (expansions/history/focus/temporary/selection) but preserves filters and camera (D-47/D-49)."

patterns-established:
  - "Pattern 1: expansion delta as a DTO — anchor + bounded additions + edges only; no groups/timeline/focus, no total/count/degree keys anywhere in the payload."
  - "Pattern 2: offline expansion route tests — stub graph service over checked-in fixtures; cache poisoning proves no cache get/set on any request tuple."
  - "Pattern 3: reducer-level recovery — undo/collapse/back-to-overview are pure state transitions with server-safe-id guards; the canvas layout policy is untouched."

requirements-completed: [VIZ-06]
coverage:
  - id: D1
    description: "Expansion endpoint contract — 7-key enum, limit 1..25, typed 404/422/503, shared boundary, OpenAPI 52/39"
    requirement: VIZ-06
    verification:
      - kind: integration
        ref: "spoilerless/tests/test_visualization_projection.py#test_expansion_route_family_validated_end_to_end"
        status: pass
      - kind: integration
        ref: "spoilerless/tests/test_visualization_projection.py#test_expansion_route_invalid_boundary_is_typed_422"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_openapi_contract.py#expansion inventory"
        status: pass
    human_judgment: false
  - id: D2
    description: "Deterministic delta projection for all seven keys with per-key edge restriction and no hidden totals"
    requirement: VIZ-06
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_expansion_all_seven_keys_return_deterministic_deltas"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_expansion_family_delta_exact_shape_and_no_hidden_totals"
        status: pass
    human_judgment: false
  - id: D3
    description: "Expansion never touches the cache for any request tuple (T10-CACHE-06)"
    requirement: VIZ-06
    verification:
      - kind: integration
        ref: "spoilerless/tests/test_visualization_projection.py#test_expansion_route_bypasses_cache_entirely"
        status: pass
    human_judgment: false
  - id: D4
    description: "Expansion history recovery — undo newest record, collapse per anchor, back-to-overview with filters/camera preserved"
    requirement: VIZ-06
    verification:
      - kind: unit
        ref: "frontend/src/hooks/useSceneState.test.ts#expansion history undoes the newest record exactly"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/useSceneState.test.ts#COLLAPSE_EXPANSION removes every record rooted at the anchor"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/useSceneState.test.ts#BACK_TO_OVERVIEW restores the bounded Story view"
        status: pass
    human_judgment: false

# Metrics
duration: 40min
completed: 2026-08-13
status: complete
---

# Phase 10: Polish & Finishing Touches Summary

**Allowlisted semantic expansion endpoint (7 keys, uncached bounded deltas, OpenAPI 52/39) with history-based undo/collapse/overview recovery in the scene reducer**

## Performance

- **Duration:** 40 min (executor built backend ~90%, orchestrator finished inline)
- **Started:** 2026-08-13 19:20
- **Completed:** 2026-08-13 19:50
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- `GET /api/series/{series_id}/graph/expand` — required node_id/expansion_key/positive episode_order, limit default 12 constrained 1..25, strict delta DTO (anchor + additions + edges, no totals/counts/degrees anywhere in the payload), typed 404/422/503 envelopes, shared boundary resolver, NO cache-aside (proven by poisoning tests)
- All seven keys concrete: family/work/conflict/locations/episode_events/clues/evidence; per-key edge restriction (family expansion surfaces only FAMILY_OF); clues include claims + supporting evidence; deterministic (reveal order, id) bounding
- Frontend: typed `fetchExpansion` API client; scene reducer expansion history — UNDO_EXPANSION (newest-record pop), COLLAPSE_EXPANSION (per anchor), BACK_TO_OVERVIEW (exploration cleared, filters/camera preserved)
- OpenAPI inventory 51→52 operations / 38→39 templates + contract doc updated (D-21/D-29)

## Task Commits

Each task was committed atomically:

1. **Task 1: expansion endpoint + delta projection** - `999bc30` (feat)
2. **Task 1: typed expansion API client** - `8ae9785` (feat)
3. **Task 2: expansion history + recovery actions** - `c4473b7` (feat)

**Plan metadata:** pending (SUMMARY + STATE.md + ROADMAP.md commit)

## Files Created/Modified
- `spoilerless/app/api/graph.py` - /graph/expand route, ExpansionKey enum, typed envelopes
- `spoilerless/app/services/visualization.py` - project_expansion + per-key edge maps + kind-aware addition projection
- `spoilerless/app/domain/visualization.py` - EXPANSION_KEYS, limit constants, expansion view-type prefix
- `spoilerless/tests/test_visualization_projection.py` - ~14 expansion tests + stub app
- `spoilerless/tests/test_openapi_contract.py`, `test_frontend_contract_doc.py` - inventory 52/39
- `docs/reference/frontend-api-contract.md` - expansion route section
- `frontend/src/api/graph.ts` - fetchExpansion typed client
- `frontend/src/hooks/useSceneState.ts` + test - ExpansionRecord, UNDO/COLLAPSE/BACK_TO_OVERVIEW

## Decisions Made
- Expansion bypasses the cache entirely in Phase 10 — correctness over latency for exploration deltas (T10-CACHE-06)
- Undo is record-based (never heuristic): the newest ExpansionRecord's additions are removed exactly (D-48)
- Additions dispatch by concrete domain type (GraphNode/GraphClaim/GraphEvidence/GraphSource) — claims/evidence carry no episode/media fields, so the shared _node() helper needs kind-aware tiers

## Deviations from Plan

### Auto-fixed Issues

**1. [Executable contract] additions map mixed node kinds**
- **Found during:** Task 1 verification (KeyError 'claim_1')
- **Issue:** the tier loop read additions from node_by_id, but claims/evidence/sources live in additions_by_id — and GraphClaim lacks type/episode_id fields the shared _node() helper assumes
- **Fix:** dispatch by isinstance (GraphClaim/GraphEvidence/GraphSource/GraphNode) with kind-aware tiers; getattr-based media fields already tolerate missing attributes
- **Files modified:** spoilerless/app/services/visualization.py
- **Verification:** 21 expansion tests pass
- **Committed in:** 999bc30

**2. [Executable contract] edge family leakage**
- **Found during:** Task 1 verification
- **Issue:** family/work deltas surfaced the KNOWS user-rel because the edge loop mapped ALL full-vocabulary edges between kept nodes
- **Fix:** per-key edge restriction via _EXPANSION_EDGE_TYPES — only the expansion's own semantic family surfaces (D-21)
- **Files modified:** spoilerless/app/services/visualization.py
- **Verification:** parametrized seven-key delta tests pass
- **Committed in:** 999bc30

**3. [Executable contract] clues did not include supporting evidence**
- **Found during:** Task 1 verification
- **Issue:** test contract expects clues = claims + their evidence; service added claims only
- **Fix:** evidence additions apply to both clues and evidence keys; sources remain evidence-key-only
- **Files modified:** spoilerless/app/services/visualization.py
- **Verification:** seven-key delta parametrize passes
- **Committed in:** 999bc30

**4. [Test contract] invalid-boundary test could not exercise the boundary**
- **Found during:** Task 1 verification
- **Issue:** anonymous users clamp to order 1 (PROB-04/#12), so episode_order=99 returned 200
- **Fix:** authenticated user + _ProgressRecord(2, 2) past the fixture max order → typed 422 INVALID_VISIBLE_UNTIL_ORDER
- **Files modified:** spoilerless/tests/test_visualization_projection.py
- **Verification:** boundary test passes
- **Committed in:** 999bc30

---

**Total deviations:** 4 auto-fixed (3 executable contract, 1 test contract)
**Impact on plan:** All fixes necessary for D-21 correctness; no scope creep.

## Issues Encountered
- Executor hit its tool cap with the backend ~90% built (4 known failures); orchestrator completed the fixes, the frontend leg, and Task 2 inline.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 10-07 GraphRAG focus can consume the expansion route and the Answer Graph entry point
- 10-08 benchmarks can measure expansion delta sizes against the D-09 caps
- 10-10 UAT: expansion/recovery flows ready for hands-on testing

---
*Phase: 10-polish-finishing-touches*
*Completed: 2026-08-13*
