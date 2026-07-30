import { apiFetch } from './client'
import type { RevisionResponse } from '../types/revision'

export function getRevisions(
  seriesId: string,
  visibleUntilOrder: number,
  resourceType?: string,
  resourceId?: string,
): Promise<RevisionResponse[]> {
  let url = `/api/series/${encodeURIComponent(seriesId)}/revisions?visible_until_order=${visibleUntilOrder}`
  if (resourceType) url += `&resource_type=${encodeURIComponent(resourceType)}`
  if (resourceId) url += `&resource_id=${encodeURIComponent(resourceId)}`
  return apiFetch<RevisionResponse[]>(url)
}

export function getRevision(
  seriesId: string,
  revisionId: string,
  visibleUntilOrder: number,
): Promise<RevisionResponse> {
  return apiFetch<RevisionResponse>(
    `/api/series/${encodeURIComponent(seriesId)}/revisions/${encodeURIComponent(revisionId)}?visible_until_order=${visibleUntilOrder}`,
  )
}

export function revertRevision(
  seriesId: string,
  revisionId: string,
  visibleUntilOrder: number,
): Promise<RevisionResponse> {
  return apiFetch<RevisionResponse>(
    `/api/series/${encodeURIComponent(seriesId)}/revisions/${encodeURIComponent(revisionId)}/revert?visible_until_order=${visibleUntilOrder}`,
    { method: 'POST' },
  )
}
