import { apiFetch } from './client'
import type { SeriesResponse, EpisodeResponse } from '../types/series'

export function getSeries(): Promise<SeriesResponse[]> {
  return apiFetch('/api/series')
}

export function getEpisodes(seriesId: string): Promise<EpisodeResponse[]> {
  return apiFetch(`/api/series/${seriesId}/episodes`)
}
