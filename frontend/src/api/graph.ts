import { apiFetch } from './client'
import type {
  GraphResponse,
  PathResponse,
  VisualizationDTO,
  VisualizationViewType,
} from '../types/graph'

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

// Phase 10 (10-04, D-29): typed task-view call for the neutral visualization
// projection. `view` is the D-29 vocabulary; `episodeOrder` is the required
// positive boundary (same resolution/clamp semantics as visible_until_order);
// repeated `focus_id` values are accepted only for `graphrag_focus` (backend
// caps at 20 distinct ids) and are omitted for every other view. The backend
// enforces the spoiler boundary before projection — this client never filters.
export function fetchVisualization(
  seriesId: string,
  view: VisualizationViewType,
  episodeOrder: number,
  focusIds?: string[],
): Promise<VisualizationDTO> {
  const params = new URLSearchParams({
    view,
    episode_order: String(episodeOrder),
  })
  for (const id of focusIds ?? []) {
    params.append('focus_id', id)
  }
  return apiFetch(`/api/series/${seriesId}/graph/visualization?${params.toString()}`)
}

// 10-06 (D-21): allowlisted semantic expansion — returns a strict DTO delta
// (anchor + additions + edges, no totals). The backend enforces the boundary
// and the limit (1..25); the client sends only the allowlisted key enum.
export type ExpansionKey =
  | 'family'
  | 'work'
  | 'conflict'
  | 'episode_events'
  | 'clues'
  | 'locations'
  | 'evidence'

export function fetchExpansion(
  seriesId: string,
  nodeId: string,
  expansionKey: ExpansionKey,
  episodeOrder: number,
  limit?: number,
): Promise<VisualizationDTO> {
  const params = new URLSearchParams({
    node_id: nodeId,
    expansion_key: expansionKey,
    episode_order: String(episodeOrder),
  })
  if (limit !== undefined) params.set('limit', String(limit))
  return apiFetch(`/api/series/${seriesId}/graph/expand?${params.toString()}`)
}
