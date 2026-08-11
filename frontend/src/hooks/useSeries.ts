import { getSeries } from '../api/series'
import type { SeriesResponse } from '../types/series'
import { useFetchState } from './useFetchState'

export function useSeries() {
  // No params — fetches exactly once on mount; the constant key never
  // changes, so the shared machine never resets or re-fetches.
  return useFetchState<SeriesResponse[]>('series', true, () => getSeries())
}
