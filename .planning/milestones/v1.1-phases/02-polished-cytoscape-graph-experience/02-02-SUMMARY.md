---
phase: 02-polished-cytoscape-graph-experience
plan: 02
subsystem: ui
tags: [cytoscape, cose-bilkent, react, vitest, react-testing-library, shadcn]

requires:
  - phase: 02-polished-cytoscape-graph-experience (Plan 01)
    provides: end-to-end select→confirm→fetch→render→inspect tracer (AppShell, SeriesSelect, EpisodeSelector, ConfirmAdvanceModal, GraphCanvas skeleton, DetailPanel, useGraph, Vitest+RTL infra)
provides:
  - cose-bilkent-driven Cytoscape canvas with a full node-type shape + origin-border stylesheet (including Episode/Series shapes not in the original design contract)
  - Tap-driven neighbor highlight/fade on nodes and edges (selected-dominant/faded/edge-active)
  - Loading/error/empty overlay states (GraphStatus.tsx) that fully replace the canvas per state, wired into App.tsx's useGraph status branch
  - useGraph refetch() so GraphErrorState's Retry re-issues the last graph fetch
  - A second GraphResponse fixture (visible_until_order=3, 20 nodes) and a GraphCanvas component test asserting element counts/types at both S01E01 and S01E03 boundaries
affects: [02-03 (detail panel tab/branch split), 02-04 (grep audit / spoiler-safety verification)]

tech-stack:
  added: []
  patterns:
    - "GraphStatus.tsx: one component per useGraph status (loading/error/empty), rendered as mutually exclusive branches in App.tsx so no state ever layers over the canvas"
    - "useGraph retry-token pattern: a retryToken folded into the same render-time 'key changed → reset to loading' comparison used for seriesId/visibleUntilOrder changes, so Retry re-enters 'loading' the same way a genuine boundary change does, without a separate imperative setState-in-effect path"

key-files:
  created:
    - frontend/src/components/graph/GraphStatus.tsx
    - frontend/src/components/graph/GraphCanvas.test.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/hooks/useGraph.ts
    - frontend/src/test/fixtures/graphResponse.ts
    - frontend/src/components/graph/GraphCanvas.tsx (pre-existing WIP commit bb2fbe6, inherited not re-done)
    - frontend/src/components/graph/graphStylesheet.ts (pre-existing WIP commit bb2fbe6, inherited not re-done)
    - .planning/phases/02-polished-cytoscape-graph-experience/02-UI-SPEC.md (pre-existing WIP commit bb2fbe6, inherited not re-done)

key-decisions:
  - "Task 1 (cose-bilkent layout, full stylesheet, selection highlight/fade) was already fully implemented in a prior manual WIP checkpoint commit (bb2fbe6) that landed before this executor run started. Verified against the plan's acceptance criteria rather than re-implemented from scratch: layout defaults to cose-bilkent with a caught-error-only fallback to cose; graphStylesheet.ts has distinct shapes for Character/Event/Location/Organization/UserNote/Episode/Series; origin='canonical' renders the solid border with no selector branching on the literal string 'curated'; GraphCanvas.tsx wires tap-driven selected-dominant/faded/edge-active classes on nodes and edges; 02-UI-SPEC.md's node-type table already has the Episode/Series discretion-addition rows. This executor run only performed Task 2."
  - "GraphErrorState's Retry re-issues the fetch via a retryToken folded into useGraph's existing render-time key-comparison reset pattern (not a new imperative effect), keeping the file's existing 'adjusting state when a prop changes' approach consistent and avoiding a fresh react-hooks/set-state-in-effect lint concern."
  - "App.tsx's idle status (before a series/episode is selected, D-01) also renders GraphEmptyState — the plan's locked empty-state copy is reused for both the true zero-node case and the pre-selection empty case, since both are '(no visible graph yet' and the Copywriting Contract defines only one empty-state string."

requirements-completed: [UI-03]

coverage:
  - id: D1
    description: "GraphCanvas renders only backend-returned nodes/edges (pure pass-through, no visible_from_order filtering) and re-renders with the new element set at each episode boundary"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#renders exactly the S01E01 fixture node/edge counts (11 nodes, 6 edges)"
        status: pass
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#renders exactly the S01E03 fixture node count (20 nodes) after a boundary change"
        status: pass
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#never filters elements by visible_from_order (pure pass-through of the fetched GraphResponse)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every node type (Character/Event/Location/Episode/Series) has an explicit non-default Cytoscape shape; origin='canonical' renders the solid-border treatment; no selector branches on the literal string 'curated'"
    requirement: "UI-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.test.tsx#maps every node to a data(nodeType), including Episode and Series (no default-ellipse fallthrough)"
        status: pass
      - kind: other
        ref: "frontend/src/components/graph/graphStylesheet.ts static inspection: distinct shape selectors for Character/Event/Location/Organization/UserNote/Episode/Series; single origin selector on the literal 'canonical'"
        status: pass
    human_judgment: true
    rationale: "Shape choice, visual distinctness, and border rendering are best confirmed by looking at the actual rendered canvas (UAT), not just selector presence in the stylesheet source."
  - id: D3
    description: "Tap-to-fade neighbor highlighting works on both nodes and structural/claim-backed edges (D-05 'nothing is inert to clicks')"
    requirement: "UI-03"
    verification:
      - kind: e2e
        ref: "frontend/src/App.test.tsx#runs select -> confirm -> fetch -> render -> inspect end-to-end (clicks a rendered node, asserts DetailPanel updates; clicks background, asserts DetailPanel resets)"
        status: pass
    human_judgment: true
    rationale: "The App.test.tsx stub exercises the tap handler wiring but fakes the Cytoscape collection chain (closedNeighborhood/difference/union) rather than real fade/dominant CSS class rendering — visual confirmation of the fade/highlight effect itself needs a human looking at the running canvas."
  - id: D4
    description: "Loading/error/empty overlay states each fully replace the canvas (never layer alongside it) with the locked copy, and Retry re-issues the last graph fetch"
    requirement: "UI-03"
    verification:
      - kind: other
        ref: "frontend/src/App.tsx static inspection: mutually exclusive if-blocks keyed on graphState.status (loading/error/success-empty/success-populated/idle), each rendering exactly one of GraphLoadingState/GraphErrorState/GraphEmptyState/(GraphCanvas+DetailPanel)"
        status: pass
    human_judgment: true
    rationale: "No automated test exercises a forced fetch-error or a genuinely empty success response through App.tsx yet (App.test.tsx's fetch stub always returns the S01E01 fixture on success); the locked copy, Retry button wiring, and visual non-overlap are verified by code inspection here and should be UAT-confirmed against the real backend at phase gate."

duration: 45min
completed: 2026-07-29
status: complete
---

# Phase 2 Plan 02: Polished Cytoscape Graph Experience — Stylesheet, Layout, Overlay States Summary

**Cytoscape canvas polish (cose-bilkent layout, full node-shape/origin-border stylesheet, tap-driven neighbor highlight/fade — inherited from a pre-existing WIP commit) plus this run's addition: GraphStatus.tsx loading/error/empty overlay states, a useGraph retry path, and a GraphCanvas.test.tsx boundary test proving element counts track the backend exactly at both S01E01 (11 nodes/6 edges) and S01E03 (20 nodes).**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-07-29
- **Tasks:** 2 (Task 1 inherited from prior WIP commit bb2fbe6, verified not re-done; Task 2 executed and committed this run)
- **Files modified this run:** 5 (2 created, 3 modified)

## Accomplishments

- Verified Task 1's cose-bilkent layout, full node-type/origin stylesheet (including the Episode=tag/Series=star discretion additions), and tap-driven selection highlight/fade were already correctly implemented in commit `bb2fbe6` — matched against every acceptance criterion in 02-02-PLAN.md Task 1 rather than assumed.
- Added `GraphStatus.tsx` exporting `GraphLoadingState`, `GraphErrorState`, `GraphEmptyState` — each fully replaces the canvas region for its state (Skeleton-based loading overlay, Alert-based error with a working Retry button, and the locked "Nothing revealed yet" empty state).
- Wired `App.tsx` to branch on `useGraph`'s full status set (`idle`/`loading`/`error`/`success` with zero vs. populated nodes) instead of a single ternary that only distinguished success vs. everything else — the previous hardcoded inline empty-state markup is now the shared `GraphEmptyState` component.
- Added `refetch()` to `useGraph` via a `retryToken` folded into the existing render-time key-reset pattern, so `GraphErrorState`'s Retry button re-issues the exact last `getGraph(seriesId, visibleUntilOrder)` call.
- Extended `frontend/src/test/fixtures/graphResponse.ts` with `graphResponseS01E03` (20 nodes: 9 Character, 3 Event, 4 Location, 3 Episode, 1 Series — the verified live S01E03 counts from 02-RESEARCH.md Pitfall 3).
- Created `frontend/src/components/graph/GraphCanvas.test.tsx`: mounts `GraphCanvas` directly with a mocked `react-cytoscapejs`, asserting exactly 11 node + 6 edge elements at the S01E01 fixture, exactly 20 node elements at the S01E03 fixture, at least one `Episode` and one `Series` `nodeType`, and that no element is dropped or added beyond the fixture's own node/edge lists (pass-through, no `visible_from_order` filtering).

## Task Commits

1. **Task 1: cose-bilkent layout, full stylesheet, and selection highlight/fade** — `bb2fbe6` (feat) — pre-existing manual WIP checkpoint commit, landed before this executor run was dispatched. Verified, not re-committed.
2. **Task 2: Loading/error/empty overlay states and boundary component test** — `81239af` (feat)

**Plan metadata:** (this commit, `docs(02-02): complete plan`)

## Files Created/Modified

- `frontend/src/components/graph/GraphStatus.tsx` — `GraphLoadingState`/`GraphErrorState`/`GraphEmptyState`, each replacing the canvas region for its state
- `frontend/src/components/graph/GraphCanvas.test.tsx` — boundary element-count/nodeType component test (11/6 at order 1, 20 at order 3, Episode+Series present, no client-side filtering)
- `frontend/src/App.tsx` — full `useGraph` status branch (loading/error/empty/populated/idle) replacing the previous success-vs-everything-else ternary
- `frontend/src/hooks/useGraph.ts` — added `retryToken` state and `refetch()`, both folded into the existing key-comparison "reset on change" pattern
- `frontend/src/test/fixtures/graphResponse.ts` — added `graphResponseS01E03` (20-node fixture)
- `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/graphStylesheet.ts`, `.planning/phases/02-polished-cytoscape-graph-experience/02-UI-SPEC.md` — inherited from pre-existing WIP commit `bb2fbe6`, verified against this plan's Task 1 acceptance criteria, not modified further this run

## Decisions Made

- Task 1 was fully covered by a prior WIP commit; rather than duplicating work, this run verified each acceptance criterion directly against the committed code (layout fallback logic, stylesheet selectors, origin literal, UI-SPEC table rows) before proceeding to Task 2. See `key-decisions` in frontmatter for the specific verification points.
- `useGraph`'s Retry mechanism reuses the file's existing render-time "key changed → reset to loading" pattern (adding `retryToken` to the same key string) rather than introducing a new imperative `setState` call inside the effect, keeping the file's established React-hooks-lint-safe approach consistent.
- `App.tsx`'s pre-selection `idle` status also renders `GraphEmptyState` (same locked copy as the true zero-node case) since 02-UI-SPEC.md's Copywriting Contract defines only one empty-state string and D-01's "no auto-fetch on mount" behavior produces the same user-facing situation.

## Deviations from Plan

None beyond the pre-existing WIP commit noted above (which was disclosed up front by the dispatching orchestrator, not discovered mid-run) — Task 2 was executed exactly as specified in 02-02-PLAN.md.

## Issues Encountered

- An initial `useGraph.ts` edit included a defensive `eslint-disable-next-line react-hooks/exhaustive-deps` comment that `npm run lint` flagged as an unused-directive warning (the dependency array was already correct without it). Removed the comment; `npm run lint` then exited clean with 0 warnings/errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UI-03 is satisfied: the canvas uses the locked visual language (cose-bilkent layout, full node-type shapes including Episode/Series, origin border treatment, tap-driven highlight/fade) instead of Cytoscape defaults, and a passing automated test proves element counts track the backend boundary exactly at both S01E01 and S01E03.
- Loading/error/empty states are wired and mutually exclusive with the canvas, ready for Plan 03's detail-panel tab/branch split (D-06/D-07) to build on top of the same `useGraph`/`GraphCanvas` contract without further changes to this plan's surface.
- `npm run test -- --run` (7/7 tests), `npm run build`, and `npm run lint` all exit 0 as of this plan's final commit.
- Deferred to phase-gate UAT (per `human_judgment: true` coverage rows above): visual confirmation of node shapes/origin borders on the real running canvas, the fade/highlight visual effect itself, and exercising `GraphErrorState`/`GraphLoadingState` against a genuinely failing/slow backend request.

---
*Phase: 02-polished-cytoscape-graph-experience*
*Completed: 2026-07-29*

## Self-Check: PASSED

All created files and commit hashes verified present on disk / in git log.
