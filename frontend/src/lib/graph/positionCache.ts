import type { GraphMode } from '../../components/graph/overviewTiers'

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
