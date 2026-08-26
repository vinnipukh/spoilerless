# Phase 12 Plan 14: Unify Cytoscape Element Adapters Summary

## Overview

Unified the two Cytoscape element adapter branches (`graphToElements` and `toCytoscapeElements`) into one neutral `sceneElements.ts` module with a single explicit cluster policy function (`clusterFor`), per-source normalization (`fromGraph` and `fromVisualization`), and a shared internal enrichment step (`enrich`). Collapsed the adapter selection branch in `GraphCanvas.tsx` to directly invoke `sceneElements`, deleted the dead `subplot`/`cluster` cast from `graphElements.ts`, and preserved byte-identical exact data-key shapes pinned by `visualizationAdapter.test.ts` (T10-LEAK-04) and `graphElements.test.ts`.

## Changes Made

1. **Created `frontend/src/lib/graph/sceneElements.ts`**:
   - Defined `SceneElementDefinition`, `ToCytoscapeOptions`, `clusterFor`, `fromGraph`, and `fromVisualization`.
   - Exported exact data key constants (`NODE_DATA_KEYS`, `GROUP_DATA_KEYS`, `EDGE_DATA_KEYS`).
   - Implemented single explicit `clusterFor` function:
     - Visualization path (when `groups` list is present): maps 1:1 to DTO group membership (`group:` prefix). Ungrouped visualization nodes receive `null` (no episode bands added).
     - Graph path (when `groups` list is absent/undefined): maps to episode band `Ep #N` from `visible_from_order` (or fallback `Main`).
   - Added internal `enrich` step stripping undefined properties to maintain exact shape requirements.

2. **Updated `frontend/src/components/graph/graphElements.ts`**:
   - Removed dead `(node as Record<string, unknown>).subplot ?? .cluster` cast.
   - Delegated `graphToElements` to `sceneElements.fromGraph`.

3. **Updated `frontend/src/lib/visualizationAdapter.ts`**:
   - Delegated `toCytoscapeElements` to `sceneElements.fromVisualization`.
   - Re-exported data key constants from `sceneElements.ts`.

4. **Updated `frontend/src/components/graph/GraphCanvas.tsx`**:
   - Replaced direct imports of `graphToElements` and `toCytoscapeElements` with `* as sceneElements`.
   - Collapsed `elements` useMemo branch to invoke `sceneElements.fromVisualization` or `sceneElements.fromGraph`.

## Verification

- `sceneElements.ts` contains all required exports (`SceneElementDefinition`, `clusterFor`, `fromGraph`, `fromVisualization`).
- Dead `subplot`/`cluster` cast removed from `graphElements.ts`.
- Data-key shapes pinned in `visualizationAdapter.test.ts` and `graphElements.test.ts` remain strictly preserved with zero pin changes.
