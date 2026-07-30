# Milestones

## v1.0 Prototype v0 (Shipped: 2026-07-30)

**Phases completed:** 6 phases, 22 plans, 17 tasks

**Key accomplishments:**

- A lifespan-owned async Neo4j backend, ontology-validated deterministic Dexter evidence graph, and fail-closed spoiler-safe API proven across live episode boundaries
- React/Vite frontend now composes a real product layout (AppShell > SeriesSelect/EpisodeSelector > ConfirmAdvanceModal > GraphCanvas > DetailPanel) driven by a typed API client and a sessionStorage-backed watch-progress hook, replacing the Vite starter entirely and rendering the spoiler-safe graph from the verified Phase 1 backend in Cytoscape.
- Cytoscape canvas polish (cose-bilkent layout, full node-shape/origin-border stylesheet, tap-driven neighbor highlight/fade — inherited from a pre-existing WIP commit) plus this run's addition: GraphStatus.tsx loading/error/empty overlay states, a useGraph retry path, and a GraphCanvas.test.tsx boundary test proving element counts track the backend exactly at both S01E01 (11 nodes/6 edges) and S01E03 (20 nodes).
- Full Overview/Claims/Evidence tabbed DetailPanel (D-07) resolving claim/evidence/source data from the already-fetched GraphResponse, plus a distinct tab-less StructuralEdgeCard (D-06) for structural edges, with the branch decision centralized in exactly one place in App.tsx.
- Closed the remaining Nyquist coverage gaps (useWatchProgress hydration/corruption/no-op edge cases, ConfirmAdvanceModal copy variants), ran a tree-wide grep audit proving the phase's two highest-severity threat mitigations hold across all of frontend/src, and completed the Definition-of-Done conversational UAT against the live backend — finding and fixing a real cose-bilkent layout-thrashing bug and a missing dev-server API proxy along the way.
- Strict ontology-locked user-content schemas, stable sanitized FastAPI errors, and reusable Wave-0 test infrastructure without registering future CRUD routes
- Retry-safe managed Neo4j persistence and all 13 locked series-scoped note/custom-content operations with fail-closed visibility and canonical isolation
- API-owned user relationships now join the existing spoiler-safe graph exactly once as closed GraphEdge records, with preserved canonical provenance, setup isolation, and an executable 18-operation frontend handoff
- Notes tab, custom node/relationship dialogs, and origin-based visual distinction wired into the existing React + Cytoscape frontend.
- Complete — this is a planning artifact, not an executable plan
- Complete — verified via conversational UAT
- Complete — verified via conversational UAT
- Complete — verified via conversational UAT
- Complete — verified via conversational UAT
- Complete — revision model, persistence layer, and user-content integration
- Complete — three routes created and wired
- Complete — 12 integration tests passing
- Complete — types, API client, hook, tests
- Complete — History tab integrated into DetailPanel, 11 DetailPanel tests passing
- 2026-07-30
- Complete — committed `620aedf`
- Complete — committed `e528c89`
- Complete — code merged into candidates.py
- Complete

---
