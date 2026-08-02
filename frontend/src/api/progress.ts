import { apiFetch } from './client'

// Mirrors backend/app/domain/progress.py's UserSeriesProgressResponse
// field-for-field. `visible_until_order` is never accepted anywhere else on
// the GraphRAG path — this is the only place a client may request a change,
// and the server always resolves the actual boundary from this persisted
// record (RAG-01).
export type UserSeriesProgress = {
  id: string
  user_id: string
  series_id: string
  visible_until_order: number
  updated_at: string
}

export function getProgress(seriesId: string): Promise<UserSeriesProgress> {
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/progress`)
}

export function updateProgress(
  seriesId: string,
  visibleUntilOrder: number,
): Promise<UserSeriesProgress> {
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/progress`, {
    method: 'POST',
    body: { visible_until_order: visibleUntilOrder },
  })
}
