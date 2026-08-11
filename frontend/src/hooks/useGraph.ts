import { useState } from 'react'
import { getGraph } from '../api/graph'
import type { GraphResponse } from '../types/graph'
import { useFetchState } from './useFetchState'

function canFetch(seriesId: string | null, visibleUntilOrder: number | null): boolean {
  return Boolean(seriesId) && visibleUntilOrder != null
}

export function useGraph(seriesId: string | null, visibleUntilOrder: number | null) {
  // Bumped by `refetch()` (GraphErrorState's Retry button) to re-issue the
  // last `getGraph(seriesId, visibleUntilOrder)` call — it sits IN the key,
  // so Retry re-enters the 'loading' state exactly like a boundary change.
  const [retryToken, setRetryToken] = useState(0)

  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}:${retryToken}`
  const enabled = canFetch(seriesId, visibleUntilOrder)

  // The shared hook's `refetch` IS the in-place refresh semantics (fetch,
  // no status flip — 06-11 ChangeSet-apply keeps the mounted graph visible
  // while fresh data arrives); useGraph's public `refetch` (Retry) is the
  // key-bumping one that re-enters 'loading'.
  const { refetch: refresh, ...state } = useFetchState<GraphResponse>(
    key,
    enabled,
    () => getGraph(seriesId!, visibleUntilOrder!),
  )

  function refetch() {
    setRetryToken((token) => token + 1)
  }

  return { ...state, refetch, refresh }
}
