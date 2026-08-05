import { apiFetch } from './client'
import type { GraphResponse, PathResponse } from '../types/graph'

export function getGraph(seriesId: string, visibleUntilOrder: number): Promise<GraphResponse> {
  return apiFetch(`/api/series/${seriesId}/graph?visible_until_order=${visibleUntilOrder}`)
}

// FEAT-06 (09-11): shortest visible path between two entities. The backend
// resolves the boundary server-side and caps max_hops at MAX_PATH_HOPS.
export function findPath(
  seriesId: string,
  body: { source_entity_id: string; target_entity_id: string; max_hops: number },
): Promise<PathResponse> {
  return apiFetch(`/api/series/${seriesId}/graph/path`, {
    method: 'POST',
    body,
  })
}
