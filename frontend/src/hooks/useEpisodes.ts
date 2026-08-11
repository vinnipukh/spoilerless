import { getEpisodes } from '../api/series'
import type { EpisodeResponse } from '../types/series'
import { useFetchState } from './useFetchState'

export function useEpisodes(seriesId: string | null, visibleUntilOrder?: number | null) {
  // Key includes the boundary so masked titles stay current when the view
  // changes (META-01 — masking is never client CSS; the effective order is
  // sent so the backend masks spoiler-sensitive titles server-side).
  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}`
  return useFetchState<EpisodeResponse[]>(
    key,
    Boolean(seriesId),
    () => getEpisodes(seriesId!, visibleUntilOrder ?? undefined),
  )
}
