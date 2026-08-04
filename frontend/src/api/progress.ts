import { apiFetch } from './client'

// Mirrors backend/app/domain/progress.py's UserSeriesProgressResponse
// field-for-field. Since the D-05 split (07-02) the record carries the
// watched/view split plus the policy-computed effective boundary;
// `visible_until_order` remains as the backward-compatible echo of the
// effective boundary (D-21).
export type UserSeriesProgress = {
  id: string
  user_id: string
  series_id: string
  visible_until_order: number
  watched_through_order: number
  view_as_of_order: number
  effective_view_order: number
  updated_at: string
}

export type ProgressUpdateOptions = {
  // Forward confirm: mark Episodes 1..N watched AND view them (D-06).
  watchedThroughOrder?: number
  // View-only change: move the temporary boundary without touching the
  // watched progress (PROG-01). Never exceeds watched_through_order.
  viewAsOfOrder?: number
}

export function getProgress(seriesId: string): Promise<UserSeriesProgress> {
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/progress`)
}

export function updateProgress(
  seriesId: string,
  visibleUntilOrder: number,
  options?: ProgressUpdateOptions,
): Promise<UserSeriesProgress> {
  // Backend ProgressUpdateRequest (domain/progress.py) forbids sending
  // visible_until_order AND watched_through_order together (422). Build the
  // body per intent: forward confirm → watched_through_order (+ optional
  // view_as_of_order); view-only → view_as_of_order ALONE (never the legacy
  // confirm alias — PROG-01); legacy plain confirm → visible_until_order.
  const body: Record<string, number> = {}
  if (options?.watchedThroughOrder != null) {
    body.watched_through_order = options.watchedThroughOrder
    if (options?.viewAsOfOrder != null) body.view_as_of_order = options.viewAsOfOrder
  } else if (options?.viewAsOfOrder != null) {
    body.view_as_of_order = options.viewAsOfOrder
  } else {
    body.visible_until_order = visibleUntilOrder
  }
  return apiFetch(`/api/series/${encodeURIComponent(seriesId)}/progress`, {
    method: 'POST',
    body,
  })
}
