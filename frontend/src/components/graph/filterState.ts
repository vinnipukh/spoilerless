import type { GraphMode } from './overviewTiers'

type NodeTypesFilterState = Record<string, boolean>
type EdgeFamiliesFilterState = Record<string, boolean>

export type FilterState = {
  nodeTypes: NodeTypesFilterState
  edgeFamilies: EdgeFamiliesFilterState
}

export function initialFilterState(nodeTypes: string[], edgeFamilies: string[]): FilterState {
  const nodeTypesMap: NodeTypesFilterState = {}
  for (const t of nodeTypes) {
    nodeTypesMap[t] = true
  }

  const edgeFamiliesMap: EdgeFamiliesFilterState = {}
  for (const f of edgeFamilies) {
    edgeFamiliesMap[f] = true
  }

  return {
    nodeTypes: nodeTypesMap,
    edgeFamilies: edgeFamiliesMap,
  }
}

export function toggleNodeType(state: FilterState, type: string): FilterState {
  return {
    ...state,
    nodeTypes: {
      ...state.nodeTypes,
      [type]: !state.nodeTypes[type],
    },
  }
}

export function toggleEdgeFamily(state: FilterState, family: string): FilterState {
  return {
    ...state,
    edgeFamilies: {
      ...state.edgeFamilies,
      [family]: !state.edgeFamilies[family],
    },
  }
}

export function setAllFilters(state: FilterState, enabled: boolean): FilterState {
  const nodeTypes: NodeTypesFilterState = {}
  for (const k of Object.keys(state.nodeTypes)) {
    nodeTypes[k] = enabled
  }

  const edgeFamilies: EdgeFamiliesFilterState = {}
  for (const k of Object.keys(state.edgeFamilies)) {
    edgeFamilies[k] = enabled
  }

  return { nodeTypes, edgeFamilies }
}

// Position Cache keyed by `${seriesId}:${visibleUntilOrder}:${mode}` — mode
// is part of the key because Overview and Full render different node sets
// and must not share cached positions. Bounded (PROB-09/#74): the
// per-episode-advance entries used to accumulate forever; the Map's
// insertion order makes the oldest entry the eviction candidate.
//
// 10-04 (D-23): the visualization path passes an explicit `viewKey` (e.g.
// `viz:episode_overview`), which REPLACES the whole key. Positions then
// persist across episode switches for the same view — shared characters stay
// mostly stable when the user changes episode (D-23), and scene keys still
// separate views (T10-CACHE-04: stale scene state never crosses views).
type Position = { x: number; y: number }
const MAX_CACHED_POSITION_KEYS = 20
const positionCache = new Map<string, Map<string, Position>>()

export function getCachedPositions(
  seriesId: string,
  visibleUntilOrder: number,
  mode: GraphMode,
  viewKey?: string,
): Map<string, Position> | undefined {
  const key = viewKey ? `${seriesId}:${viewKey}` : `${seriesId}:${visibleUntilOrder}:${mode}`
  return positionCache.get(key)
}

export function setCachedPositions(
  seriesId: string,
  visibleUntilOrder: number,
  positions: Map<string, Position>,
  mode: GraphMode,
  viewKey?: string,
) {
  const key = viewKey ? `${seriesId}:${viewKey}` : `${seriesId}:${visibleUntilOrder}:${mode}`
  positionCache.set(key, positions)
  if (positionCache.size > MAX_CACHED_POSITION_KEYS) {
    const oldest = positionCache.keys().next().value
    if (oldest !== undefined) positionCache.delete(oldest)
  }
}

// Test seam mirroring __resetAutoZoomStateForTests (autoZoomHold.ts): the
// module-level cache persists across renders, so focused suites reset it in
// beforeEach.
export function __resetPositionCacheForTests() {
  positionCache.clear()
}
