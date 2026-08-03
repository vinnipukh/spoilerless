import { apiFetch } from './client'
import type { SeriesResponse, EpisodeResponse } from '../types/series'

export function getSeries(): Promise<SeriesResponse[]> {
  return apiFetch('/api/series')
}

export function getEpisodes(seriesId: string, visibleUntilOrder?: number): Promise<EpisodeResponse[]> {
  const query = visibleUntilOrder != null ? `?visible_until_order=${visibleUntilOrder}` : ''
  return apiFetch(`/api/series/${seriesId}/episodes${query}`)
}
