# Phase 12 Plan 13 Summary: Unified Scene State Reducer

## Outcome Overview
Folded parallel `filterState` `useState`, `focusReducer` `useReducer`, `expansionRecords` `useState`, and module-level position cache into `useSceneState` as a SINGLE, unified reducer authority for filters, focus, and expansions across the graph canvas workspace.

## Key Changes
1. **Filters Unified**:
   - Retired `filterState` useState from `GraphCanvas.tsx` and hardcoded 4-family edge array `['CHARACTER', 'STRUCTURAL', 'EPISODE', 'USER']`.
   - `GraphCanvas.tsx` filter effect reads `scene.nodeKindFilters` and `scene.edgeClassFilters` with absent-key-visible semantics (`isFilterEnabled`).
   - Rewired `GraphFilterPanel.tsx` to accept `nodeKindFilters`, `edgeClassFilters`, and `dispatchScene`, dispatching `SET_NODE_KIND_FILTER`, `SET_EDGE_CLASS_FILTER`, and `SET_ALL_FILTERS`.
   - Seeded initial filters in `App.tsx` derived dynamically from `NODE_TYPES` and `EDGE_TYPE_TO_FAMILY`.

2. **Focus & Expansions Unified**:
   - Retired `focusReducer` useReducer from `GraphCanvas.tsx`. Focus reads from `scene.focus` and dispatches `SET_FOCUS` / `CLEAR_FOCUS`.
   - `applyFocusToCytoscape` imported directly from `src/lib/graph/highlight.ts`.
   - Retired `expansionRecords` useState from `useWorkspaceScene.ts`. `mergedVisualization` derives from `scene.expansionHistory` via `useMemo`.
   - Expansion actions (`ADD_EXPANSION`, `UNDO_EXPANSION`, `COLLAPSE_EXPANSION`) dispatched to `useSceneState`.

3. **Modules Relocated / Deleted**:
   - Created `frontend/src/lib/graph/positionCache.ts` with `getCachedPositions`, `setCachedPositions`, and `__resetPositionCacheForTests`.
   - Deleted `frontend/src/components/graph/filterState.ts` and `frontend/src/components/graph/focusReducer.ts`.

4. **Testing & Validation**:
   - Extended `useSceneState.test.ts` with `isFilterEnabled` (absent-key-visible) and non-null focus serializability assertions.
   - Vitest test suite ran: **44 test files passed, 405 tests passed (100% green)**.

## Verification
- `npm run test` (Vitest): 44/44 suites, 405/405 tests passed.
- No remaining imports of `filterState` or `focusReducer`.
- `useSceneState` is the sole state authority for filters, focus, and expansions.
