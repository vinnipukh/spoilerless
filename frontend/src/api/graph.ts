import { apiFetch } from './client'
import type { GraphResponse } from '../types/graph'

export function getGraph(seriesId: string, visibleUntilOrder: number): Promise<GraphResponse> {
  return apiFetch(`/api/series/${seriesId}/graph?visible_until_order=${visibleUntilOrder}`)
}
