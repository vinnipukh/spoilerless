---
phase: 03-user-notes-and-manual-editing
plan: "03"
subsystem: api-graph-contract
tags: [fastapi, neo4j, spoiler-safety, openapi, documentation, pytest]

requires:
  - phase: 03-user-notes-and-manual-editing
    plan: "02"
    provides: Managed user-content persistence and all 13 locked CRUD operations
  - phase: 01-backend-graph-foundation
    provides: Evidence-backed canonical graph, persisted boundaries, graph closure, and deterministic setup
provides:
  - Spoiler-safe GraphEdge-only projection for API-owned user relationships
  - Explicitly disjoint canonical/candidate provenance and user projection branches
  - Setup preservation coverage for exact canonical and origin=user layers
  - Executable frontend handoff matching 18 OpenAPI operations over 11 templates
  - Backend acceptance evidence for NOTE-01, NOTE-02, and NOTE-03

affects: [frontend-work, phase-02-ui, phase-03-frontend-acceptance, revision-history]

tech-stack:
  added: []
  patterns: [disjoint graph projection branches, endpoint-rematched closure, canonical-user layer snapshots, executable markdown contract]

key-files:
  created:
    - backend/tests/test_frontend_contract_doc.py
    - docs/frontend-api-contract.md
  modified:
    - backend/app/api/graph.py
    - backend/app/spoiler/filter.py
    - backend/tests/test_graph_api.py
    - backend/tests/test_openapi_contract.py
    - backend/tests/test_seed_idempotency.py

key-decisions:
  - "Project API-owned user relationship Claim storage only as the existing GraphEdge shape, with its public user-rel ID and no GraphClaim/GraphSource/GraphEvidence representation."
  - "Keep canonical/candidate evidence traversal mandatory and positively origin-scoped instead of relaxing provenance for user content."
  - "Treat the handoff inventory as executable data: exact operation tuples and path templates must equal generated OpenAPI."
  - "Record the backend slice as 3/3 verified while preserving Phase 2, frontend visual acceptance, and overall Phase 03 as pending."

patterns-established:
  - "User relationship projection requires origin=user, claim_type=user_authored, user-rel namespace, exact server allowlist, positive record visibility, same-series endpoints, and positive endpoint visibility."
  - "Setup preservation tests snapshot canonical and user layers independently before and after repeated setup."
  - "Frontend handoff tables are parsed by pytest and compared set-for-set with app.openapi()."

requirements-completed:
  - NOTE-01
  - NOTE-02
  - NOTE-03

coverage:
  - id: D1
    description: "Visible API-owned custom relationships project exactly once through GraphEdge with endpoint closure and never enter claim/source/evidence collections."
    requirement: "NOTE-02"
    verification:
      - kind: integration
        ref: "backend/tests/test_graph_api.py#test_user_relationship_projection_is_edge_only_closed_and_fail_closed"
        status: pass
      - kind: integration
        ref: "C:/Users/arhan/AppData/Local/Temp/hermes-verify-03-03.py endpoint-rematch probe (exited 0 and removed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Canonical/candidate claims retain mandatory source/evidence provenance, independent validity, hidden-data exclusion, and deterministic closed responses at orders 1, 2, and 3."
    requirement: "NOTE-03"
    verification:
      - kind: integration
        ref: "uv run pytest -q backend/tests/test_graph_api.py backend/tests/test_openapi_contract.py (18 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Repeated setup preserves exact 41-node/26-relationship canonical semantics and surviving origin=user records while deleted user resources stay absent."
    requirement: "NOTE-01"
    verification:
      - kind: integration
        ref: "backend/tests/test_seed_idempotency.py#test_setup_preserves_user_layer_and_deleted_resources_stay_deleted"
        status: pass
      - kind: other
        ref: "uv run python -m backend.app.graph.setup twice (41 nodes, 26 relationships each)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The frontend handoff and generated OpenAPI expose exactly 18 locked operations over 11 templates with origin, boundary, errors, compatibility, non-goals, and pending-status rules."
    requirement: "NOTE-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_frontend_contract_doc.py (3 passed within 10-test OpenAPI/document run)"
        status: pass
      - kind: other
        ref: "app.openapi() exact inventory and required graph-boundary assertion (openapi-ok)"
        status: pass
    human_judgment: false
  - id: D5
    description: "All Phase 03 backend contracts, persistence, graph projection, and documentation checks operate together without frontend or prohibited-scope changes."
    requirement: "NOTE-01"
    verification:
      - kind: integration
        ref: "uv run pytest -q (87 passed)"
        status: pass
      - kind: other
        ref: "git diff/frontend/prohibited-scope checks (scope-ok)"
        status: pass
    human_judgment: false

duration: 28 min
completed: 2026-07-29
status: backend-complete-overall-pending
---

# Phase 03 Plan 03: Spoiler-Safe Graph Projection and Frontend Contract Summary

**API-owned user relationships now join the existing spoiler-safe graph exactly once as closed GraphEdge records, with preserved canonical provenance, setup isolation, and an executable 18-operation frontend handoff**

## Performance

- **Duration:** 28 min
- **Started:** 2026-07-29T11:03:32Z
- **Completed:** 2026-07-29T11:31:51Z
- **Tasks:** 2
- **Files created:** 2
- **Files modified:** 5 implementation/test/doc files plus validation and tracking metadata

## Accomplishments

- Added an explicitly separate user-relationship projection that requires API ownership markers, the exact ontology participation/character allowlist, positive persisted visibility, and visible same-series endpoints before emitting one GraphEdge.
- Positively restricted canonical/candidate claim, source, and evidence branches so both evidence-free non-user claims and evidence-bearing user-authored claims cannot cross representations.
- Replaced the graph boundary parser with a required positive integer OpenAPI parameter while retaining persisted-order validation, sanitized errors, deterministic ordering, and response closure.
- Proved repeated setup preserves the exact canonical layer and complete surviving user layer, does not resurrect deleted user resources, and keeps schema objects idempotent.
- Published and executable-tested the complete backend-to-frontend contract: exactly 18 operation tuples over 11 path templates, full schemas/statuses/errors/boundaries/examples/compatibility notes/non-goals, and explicit pending UI/overall-phase status.

## Task Commits

1. **03-03-01: Project visible custom content through the existing spoiler-safe graph contract** — `8544258`
2. **03-03-02: Prove setup preservation and publish the backend/frontend contract handoff** — `9069d83`

## Files Created/Modified

- `backend/app/api/graph.py` — Required positive boundary, Organization/Object nodes, separate allowlisted user-edge query, typed responses, and GraphEdge assembly.
- `backend/app/spoiler/filter.py` — Positive canonical/candidate provenance guards and the closed `VISIBLE_USER_RELATIONSHIPS_QUERY`.
- `backend/tests/test_graph_api.py` — User projection, five node labels, endpoint visibility, unsafe predicate, missing visibility, serialization sentinel, closure, and cross-branch regressions.
- `backend/tests/test_openapi_contract.py` — Required story-read boundaries, graph error models, typed health responses, and 204 body checks.
- `backend/tests/test_seed_idempotency.py` — Independent canonical/user snapshots, repeated setup preservation, evidence exemption, schema singleton, and deletion non-resurrection checks.
- `backend/tests/test_frontend_contract_doc.py` — Exact document/OpenAPI operation/template comparison and stable handoff marker assertions.
- `docs/frontend-api-contract.md` — Authoritative backend handoff for routes, schemas, statuses, errors, examples, origins, boundaries, compatibility corrections, limitations, non-goals, and pending frontend work.
- `.planning/phases/03-user-notes-and-manual-editing/03-VALIDATION.md` — Executed Plan 03-03 evidence and green task status.
- `.planning/STATE.md` and `.planning/ROADMAP.md` — Backend 3/3 completion with overall Phase 03 explicitly pending frontend acceptance.

## Decisions Made

- Used the stored `user-rel:*` Claim ID directly as the GraphEdge ID and left `claim_id` null, preserving the public custom-relationship identity without implying a provenance-backed GraphClaim representation.
- Passed the exact ontology-derived participation/character predicate set as a server parameter; request data cannot broaden query shape or predicate classes.
- Kept endpoint visibility rematching in Cypher even though create-time visibility is conservatively derived, so later endpoint state cannot produce a dangling or premature edge.
- Left `.planning/REQUIREMENTS.md` NOTE items pending because each requirement includes UI/visual acceptance; only the backend plan slice is recorded complete.

## Deviations from Plan

None - plan executed exactly as written.

## Security Notes

- **Spoofing/classification:** the user branch requires all ownership/classification markers and the exact namespace; evidence does not grant user records access to canonical collections.
- **Tampering/query broadening:** the predicate set is loaded from the server ontology and passed as a parameter; canonical evidence traversals remain mandatory and do not use optional provenance.
- **Information disclosure:** required persisted boundaries, positive record/endpoint visibility, hidden-equals-missing responses, no count metadata, direct JSON sentinels, and source/evidence isolation are automated.
- **Integrity/availability:** Cypher and Pydantic both enforce closure; setup preserves user records and deterministic canonical records; deleted user resources remain absent.
- No HIGH security finding remained after execution.

## Issues Encountered

- The first graph fixture query retained one row per `UNWIND` element before creating a unique Source, producing an intra-query uniqueness conflict. Adding `WITH DISTINCT` made the fixture singular; the focused regression and exact task command then passed.
- The existing third-party Starlette/httpx deprecation warning remained unchanged.

## User Setup Required

None - no new dependency, credential, fixture, or external-service configuration was added.

## Test Evidence

- Task 03-03-01 exact command: **18 passed, 1 warning**.
- Task 03-03-02 exact command: **58 passed, 1 warning**.
- User-content models: **23 passed**.
- OpenAPI plus executable handoff document: **10 passed, 1 warning**.
- User-content API: **33 passed, 1 warning**.
- Graph plus seed preservation: **15 passed, 1 warning**.
- Full suite: **87 passed, 1 unchanged warning in 14.85s**.
- Setup command twice: **41 nodes, 26 relationships** on each run.
- Exact generated OpenAPI check: **openapi-ok; 18 operations; 11 path templates; graph boundary required integer with exclusive minimum 0**.
- Ad-hoc OS-temp endpoint-rematch probe: **hermes-ad-hoc-endpoint-rematch-ok**; the script was removed and cleanup was confirmed.
- `git diff --check`, frontend diff/status, and prohibited subsystem checks: **scope-ok**.

## Next Phase Readiness

- The Phase 03 backend slice is complete and verified across Plans 03-01, 03-02, and 03-03.
- `frontend-work` can consume `docs/frontend-api-contract.md` and generated OpenAPI for React/Cytoscape integration and distinct visual treatment.
- Phase 2, frontend acceptance for NOTE-01/NOTE-02/NOTE-03, and overall Phase 03 completion remain pending.
- Root `ROADMAP.md` remains canonical and unchanged.

## Self-Check: PASSED

- Task commits `8544258` and `9069d83` exist and contain only their owned task files.
- Both created files and all five modified implementation/test files exist.
- Every task, focused, full-suite, setup, OpenAPI, ad-hoc, diff, frontend, and scope command produced the recorded result.
- GraphEdge-only projection, canonical provenance, endpoint closure, setup preservation, deletion semantics, and exact handoff inventory have executable coverage.
- Backend tracking says 3/3 verified while Phase 2, frontend visual acceptance, and overall Phase 03 remain pending.

---
*Phase: 03-user-notes-and-manual-editing*
*Completed: 2026-07-29*
