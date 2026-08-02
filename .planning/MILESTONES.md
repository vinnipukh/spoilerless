# Milestones

## v1.0 MVP (Shipped: 2026-08-02)

**Phases completed:** 8 phases, 35 plans, 47 tasks

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
- Complete — RED `87ff5c5`, GREEN `9dd5ffc`, contracts `624851b`, injection tests `b1920dd`
- Complete — T1 RED `4418d09` / GREEN `5c3bff1`, T2 RED `9e1ba49` / GREEN `0ab6b4d`, T3 RED `7d8e428` / GREEN `c8c11c1`
- Verified 06-01's progress API already enforced Cypher-level ownership and generic 404s, then fixed a real ProgressNotFoundError-to-raw-500 gap in the chat message endpoints and retrieval pipeline that would have broken RAG-01's fail-closed guarantee for any user who never set watch progress.
- Verified the RAG-09 Episode-3-then-Episode-1 hide-not-delete regression end-to-end against real Neo4j, added `DELETE /api/series/{series_id}/chat/sessions/{session_id}` with generic ownership 404s, a per-user bounded concurrent-generation counter with disconnect-safe release, and Turkish-language/count-leakage guarantees — plus the mandatory same-commit contract-inventory updates.
- Typed ChangeSet discriminated-union propose endpoint with server-side ontology/visibility validation and transparent canonical/candidate override-proposal substitution — zero graph-target mutation.
- Transactional ChangeSet apply — single Neo4j write transaction with full rollback, server-derived origin/creator/visible_from_order, idempotency-key-safe replay, and stale-snapshot rejection when progress has been lowered since propose.
- Minimal, safe revert for ChangeSet-originated changes — deletes every resource a create-shaped ChangeSet applied, logs a new Reverted Revision without ever editing the original, and conflicts (409) rather than silently overwrites a later, unrelated change.
- Typed frontend data layer for chat/progress/ChangeSet consumption — apiFetch-routed CRUD clients, a dedicated cancellable SSE streaming client, discriminated-status-union hooks, and a reusable chat fixture module — the foundation 06-09..11's chat/graph-editing UI builds on.
- DetailPanel's Sheet becomes genuinely collapsible for the first time in this codebase (stateful open + Inspector/Chat mode toggle), with a full streaming chat surface — session picker, message bubbles, citation chips, retry, and disabled-provider/transient-503 banners — mounted as its Chat-mode content.
- `useWatchProgress` now persists/hydrates through the backend progress endpoint (RAG-01 complete on the frontend); `GraphCanvas` gained its first externally-driven prop (`focusedElementIds`) plus a `GraphFocusIndicator` overlay, wired end-to-end from a chat citation's "Show in graph"/chip-body click through `App.tsx`, including automatic stale-focus clearing on a progress decrease (RAG-17).
- `ChangeSetCard` is the sole UI-initiated write surface in the phase — propose-time preview with before/after rows, destructive banner, and Confirm/Reject controls wired exclusively to `confirmChangeSet`/`rejectChangeSet`; applying a ChangeSet refreshes the graph incrementally (no destructive relayout, no remount) and reuses 06-10's `focusedElementIds` to focus the newly-created resource; canonical/candidate-edit refusals render an honest Protected badge (RAG-14/RAG-16/RAG-17 frontend half).
- Full regression green (with documented pre-existing exceptions), all PRD §19 documentation surfaces updated, and the 20-item Manual Acceptance Matrix prepared with automated evidence — awaiting the human live-browser gate before the phase can be called complete (PRD §22).
- `useChatMessages.ts`'s aborted-stream catch branch now sets `status: 'success'` instead of no-oping, so the Stop button and Thinking/Streaming bubble clear immediately after a user clicks Stop.

---

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
