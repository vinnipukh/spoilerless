---
phase: 10-polish-finishing-touches
plan: 02
subsystem: api
tags: [visualization, dto, projection, spoiler-policy, boundary, pydantic, spoiler-safe]

# Dependency graph
requires:
  - phase: 10-polish-finishing-touches
    provides: 10-01 safe S01E01/cumulative S01E02 fixtures, baseline tracer, Variant A decision at projection_version 1.0.0
  - phase: 09-feature-expansion-full-audit-remediation
    provides: graph/GraphRAG foundations, shared boundary semantics in spoiler policy
provides:
  - Versioned library-neutral VisualizationDTO models (metadata/nodes/edges/groups/timeline/focus) with reference closure
  - Production episode_overview projection service (Variant A) consuming complete safe GraphResponse
  - Shared fail-closed effective-boundary resolver for graph/projection/expansion/path/search/focus/restoration
  - Parametrized boundary/projection contract tests (hidden-data non-influence)
affects: [10-03 projection/cache plan, 10-04 adapter, 10-07 focus/restoration, 10-08 benchmarks, 10-10 UAT, T10-CACHE-02 cache plan]

# Actuals (#2632) — pairs with the plan's `estimate` (30000 tokens) on the same scale (chars/4 over the realized diff).
actuals:
  tokens: 16187
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Neutral DTO with versioned metadata contract (projection_version + effective_view_order ride every payload; T10-CACHE-02)
    - Shared pure boundary resolver (policy.resolve_effective_boundary) — one min(requested, watched) function for every read channel
    - Boundary-before-projection with hidden-row rejection (fail closed on any row above the effective boundary)
    - Human semantic edge classes replace raw Neo4j relation names; unmapped types fail closed (D-14)

key-files:
  created:
    - spoilerless/app/domain/visualization.py
    - spoilerless/app/services/visualization.py
    - spoilerless/tests/test_visualization_projection.py
  modified:
    - spoilerless/app/spoiler/policy.py
    - spoilerless/tests/test_spoiler_policy.py

key-decisions:
  - "Episode Overview projection implements the recorded 10-01 Variant A decision (characters + major Events) at projection_version 1.0.0; display_tier derives from safe editorial event tier (major=1 core, supporting=2, micro=3; characters=1 core; containers=2 supporting) pending the 10-03 display_tier source audit."
  - "Boundary enforcement centralized in policy.resolve_effective_boundary: one pure D-05 resolver for graph, projection, expansion-ready, path/search/focus/restoration inputs; missing progress fails closed to order 1 (PROB-04/#12) and no-progress requests use persisted view (PROB-09/#59). The projection service routes its boundary contract through it and rejects hidden rows before projection (T10-LEAK-02/T10-BOUND-02)."
  - "The DTO carries the effective order + projection version cache contract (T10-CACHE-02); no cache introduced in this plan."
  - "Raw Neo4j relation names never serialize in normal DTOs: human edge classes (family/work/knows/precedes/part_of/...) replace them and unmapped relationship types raise (fail closed, D-14)."
  - "Event metadata is bounded and fail-closed: participants/locations outside the safe node set are dropped (never guessed), events without a visibility order are refused, and non-major/undeclared events are timeline-only."

patterns-established:
  - "Pattern 1: versioned neutral DTO — metadata carries projection_version + effective_view_order so any future cache key and any consumer can verify boundary/version without new fields."
  - "Pattern 2: resolver-before-projection — project_episode_overview derives its boundary contract through the shared policy resolver and fails closed on any row not visible at the effective boundary."
  - "Pattern 3: bounded editorial event context — SafeEventContext (tier/participants/location) rides the safe payload pipeline; hidden or missing-visibility events are refused, and hidden participant/location refs are dropped with no observable DTO effect."

requirements-completed: [VIZ-01, VIZ-02]

# Coverage metadata (#1602) — one entry per shipped deliverable.
coverage:
  - id: D1
    description: "Versioned library-neutral VisualizationDTO models (metadata/nodes/edges/groups/timeline/focus) with reference closure and focus contract"
    requirement: VIZ-01
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_episode_overview_s01e01_exact_shape"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_dto_rejects_invalid_display_tier_and_orders"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_dto_rejects_dangling_edges"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_focus_contract_rejects_hidden_focus_id"
        status: pass
    human_judgment: false
  - id: D2
    description: "Production episode_overview projection service (Variant A) over complete safe GraphResponse: stable IDs, 0/1/many payloads, human edge classes, no raw relation names, bounded timeline metadata, hard caps, GraphRAG-independent source detail"
    requirement: VIZ-01
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_episode_overview_s01e02_cumulative_exact_shape"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_serialized_dto_contains_no_raw_relation_names"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_projection_is_deterministic"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_projection_ignores_evidence_and_source_rows"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_hard_caps_enforced"
        status: pass
    human_judgment: false
  - id: D3
    description: "Shared fail-closed effective-boundary resolver (policy.resolve_effective_boundary) used by projection inputs; every unsafe requested order clamped or rejected, missing visibility fails closed, sanitized errors"
    requirement: VIZ-02
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_spoiler_policy.py#test_resolve_effective_boundary_matrix"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_spoiler_policy.py#test_resolve_effective_boundary_rejects_invalid_orders"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_spoiler_policy.py#test_resolve_effective_boundary_errors_are_sanitized"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_hidden_node_rejected_before_projection"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_missing_event_visibility_fails_closed"
        status: pass
    human_judgment: false
  - id: D4
    description: "Parametrized D-06 contract: hidden nodes/groups/counts/degrees/layout/search/path/focus/restoration state cannot influence boundary or DTO shape/counts/groups/topology/ranking/path/focus/restoration fields"
    requirement: VIZ-02
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_spoiler_policy.py#test_hidden_channel_data_cannot_influence_effective_boundary"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_hidden_participants_and_location_cannot_influence_timeline"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_visualization_projection.py#test_clamped_request_projects_safe_dto_metadata"
        status: pass
    human_judgment: false

# Metrics
duration: 43min
completed: 2026-08-13
status: complete
---

# Phase 10 Plan 2: Neutral Visualization DTO & Effective Boundary Summary

**Versioned library-neutral VisualizationDTO models and a Variant A episode_overview projection service, with boundary-before-projection centralized in a shared fail-closed resolver**

## Performance

- **Duration:** 43 min
- **Started:** 2026-08-13T14:20:00Z
- **Completed:** 2026-08-13T15:03:21Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- Versioned neutral DTO contract (D-08) in `spoilerless/app/domain/visualization.py`: `VisualizationMetadata` (projection_version 1.0.0 + view_type + series + episode_order + visible/effective orders — the T10-CACHE-02 cache contract), `VisualizationNode` (kind/display_tier/order/episode-safe image fields), `VisualizationEdge` (human relation_class + claim_id evidence ref), `VisualizationGroup`, `TimelineItem` (bounded participants/location), optional `VisualizationFocus`, and `SafeEventContext` editorial input. Reference closure rejects dangling edges, out-of-DTO group members, and hidden focus IDs at validation.
- Production `VisualizationProjectionService.project_episode_overview` (Variant A, D-10): consumes complete safe `GraphResponse` + safe event context only; keeps characters + major Events + containers; omits `PARTICIPATED_IN`/`OCCURRED_IN`/`LOCATED_IN` and the participation family (D-13); maps narrative/structural edges to human classes (D-14) with unmapped types failing closed; timeline ordered by reveal/publication order (D-35/D-38); display_tier 1/2/3 from safe editorial tier (D-15); D-09 hard caps enforced; input immutability proven.
- Shared fail-closed resolver `policy.resolve_effective_boundary(requested, watched, view)` (D-05): one pure function for graph, projection, expansion-ready, path/search/focus/restoration inputs; no progress → boundary 1 (PROB-04/#12); persisted view when no request (PROB-09/#59); sanitized `InvalidVisibilityOrder`. The projection service routes its boundary contract through it (resolver-before-projection).
- Parametrized contract tests: 33 new policy tests (resolver matrix, invalid-order rejection, sanitized errors, D-06 channel invariance across graph/projection/expansion/path/search/focus/restoration) + 8 new projection tests (hidden node/edge/event rejection, missing visibility fails closed, hidden participants/locations dropped with zero DTO effect, clamped-request metadata) — all on checked-in fixtures, no Neo4j, no LLM.

## Task Commits

Each task was committed atomically:

1. **Task 1: Trace one safe graph read into VisualizationDTO** - `ba46ec2` (feat(10-02): add versioned neutral VisualizationDTO and episode_overview projection)
2. **Task 2: Centralize and test effective-boundary enforcement** - `c0af899` (feat(10-02): centralize effective-boundary enforcement via shared resolver)

**Plan metadata:** committed as `docs(10-02): complete neutral DTO and effective-boundary plan` (SUMMARY + STATE.md + ROADMAP.md; hash reported in the executor completion notes)

## Files Created/Modified

- `spoilerless/app/domain/visualization.py` - Versioned neutral DTO models + SafeEventContext + bounds/version constants
- `spoilerless/app/services/visualization.py` - VisualizationProjectionService (episode_overview projection, resolve_boundary)
- `spoilerless/tests/test_visualization_projection.py` - 31 contract tests (fixture shapes, 0/1/many, schema, omissions, stable IDs, GraphRAG independence, boundary/focus)
- `spoilerless/app/spoiler/policy.py` - Added `resolve_effective_boundary` shared resolver (+`__all__`, module docstring)
- `spoilerless/tests/test_spoiler_policy.py` - 33 new resolver/channel-invariance tests

## Decisions Made

- Implemented the recorded 10-01 Variant A decision; DTO/version constants must stay in sync with the frozen fixtures (enforced by contract tests).
- Centralized boundary enforcement in one pure resolver rather than per-route logic; the API route rewire to the resolver is deferred to 10-03 (out of this plan's file scope; existing routes already compute the same min rule).
- Edge labels are human semantic classes; unknown relationship types raise instead of being labeled or dropped silently — new ontology types require an audit (D-14).
- Event metadata is bounded: hidden participants/locations are dropped, missing-visibility events are refused, non-major events are timeline-only (Variant A).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Two test-expectation corrections during Task 1 (implementation behaved as designed): (1) timeline items sharing a reveal order sort by stable id (`event_micro` before `event_supporting`), and (2) `edge_12` is omitted from the S01E02 DTO because its `loc_miami_metro` endpoint is not kept in the overview — matching the 10-01 measured Variant A edge set (7 edges). No production code change was needed; expectations were aligned with the deterministic contract.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for **10-03 (projection/cache plan)**: the DTO carries the projection_version + effective order cache contract (T10-CACHE-02), the projection service is the reusable consumer of the shared resolver, and the API routes can now be rewired to `resolve_effective_boundary`.
- VIZ-01/VIZ-02 not marked Complete in REQUIREMENTS.md — shared-ID gate (#2388): 10-03 also declares them and has no SUMMARY yet; they flip Complete when the last declaring plan finishes.
- 10-03/10-08 must still audit the real `display_tier` source (currently the safe editorial event tier + deterministic defaults) before ship.

---
*Phase: 10-polish-finishing-touches*
*Completed: 2026-08-13*

## Self-Check: PASSED

- All 5 plan files exist on disk (DTO models, projection service, projection contract tests, policy resolver + policy tests, this summary).
- Both task commits exist: `ba46ec2` (Task 1), `c0af899` (Task 2).
- Task 1 `<verify>` re-run on committed state: `uv run pytest spoilerless/tests/test_visualization_projection.py -q` → 31 passed.
- Task 2 `<verify>` re-run on committed state: `uv run pytest spoilerless/tests/test_spoiler_policy.py spoilerless/tests/test_visualization_projection.py -q` → 83 passed.
- No regression: `spoilerless/tests/test_visualization_baseline.py` (14) and `test_spoiler_policy.py` (19) pre-existing tests still green; existing `test_spoiler_policy.py` tests untouched semantics.
- Plan-level `<verification>`: DTO contract reviewed against D-04..D-06, D-08, D-12..D-15, D-35..D-37 (versioned metadata + effective order contract, hidden-row rejection, human edge classes, bounded event metadata, reveal-order timeline, no hidden totals/degree/restoration fields); VIZ-01/VIZ-02 blocked from REQUIREMENTS.md by the shared-ID gate (#2388, sibling 10-03).
- No live Neo4j, no live users, no `series_dexter`, no LLM access used; all tests fixture/in-memory only.
- Metadata commit `8ab6649` (docs(10-02): complete neutral DTO and effective-boundary plan) contains exactly SUMMARY.md + STATE.md + ROADMAP.md; pre-existing dirty/untracked files were not committed.
