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
type Position = { x: number; y: number }
const MAX_CACHED_POSITION_KEYS = 20
const positionCache = new Map<string, Map<string, Position>>()

export function getCachedPositions(
  seriesId: string,
  visibleUntilOrder: number,
  mode: GraphMode,
): Map<string, Position> | undefined {
  const key = `${seriesId}:${visibleUntilOrder}:${mode}`
  return positionCache.get(key)
}

export function setCachedPositions(
  seriesId: string,
  visibleUntilOrder: number,
  positions: Map<string, Position>,
  mode: GraphMode,
) {
  const key = `${seriesId}:${visibleUntilOrder}:${mode}`
  positionCache.set(key, positions)
  if (positionCache.size > MAX_CACHED_POSITION_KEYS) {
    const oldest = positionCache.keys().next().value
    if (oldest !== undefined) positionCache.delete(oldest)
  }
}
