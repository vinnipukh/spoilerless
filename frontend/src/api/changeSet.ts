import { apiFetch } from './client'
import type { ChangeSet, ChangeSetCreateRequest } from '../types/changeSet'

export function proposeChangeSet(
  seriesId: string,
  body: ChangeSetCreateRequest,
): Promise<ChangeSet> {
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/change-sets`, {
    method: 'POST',
    body,
  })
}

export function confirmChangeSet(seriesId: string, changeSetId: string): Promise<ChangeSet> {
  return apiFetch(
    `/api/series/${encodeURIComponent(seriesId)}/change-sets/${encodeURIComponent(changeSetId)}/confirm`,
    { method: 'POST' },
  )
}

export function rejectChangeSet(seriesId: string, changeSetId: string): Promise<ChangeSet> {
  return apiFetch(
    `/api/series/${encodeURIComponent(seriesId)}/change-sets/${encodeURIComponent(changeSetId)}/reject`,
    { method: 'POST' },
  )
}

export function revertChangeSet(seriesId: string, changeSetId: string): Promise<ChangeSet> {
  return apiFetch(
    `/api/series/${encodeURIComponent(seriesId)}/change-sets/${encodeURIComponent(changeSetId)}/revert`,
    { method: 'POST' },
  )
}
