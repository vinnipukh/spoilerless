import { useEffect, useState } from 'react'
import { getGraph } from '../api/graph'
import type { GraphResponse } from '../types/graph'
import { ApiError } from '../api/client'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: GraphResponse }

function canFetch(seriesId: string | null, visibleUntilOrder: number | null): boolean {
  return Boolean(seriesId) && visibleUntilOrder != null
}

export function useGraph(seriesId: string | null, visibleUntilOrder: number | null) {
  // Bumped by `refetch()` (GraphErrorState's Retry button) to re-issue the
  // last `getGraph(seriesId, visibleUntilOrder)` call without changing the
  // series/order themselves.
  const [retryToken, setRetryToken] = useState(0)

  // Bumped by `refresh()` (06-11: a ChangeSet-apply's incremental graph
  // refresh) — re-issues the same getGraph call WITHOUT flipping the status
  // back to 'loading', so the currently-mounted graph stays visible while
  // the fresh data arrives and GraphCanvas is never unmounted/remounted.
  // Distinct from `refetch()`: `refetch` is for error recovery (the Retry
  // button re-enters the loading state), `refresh` is for in-place data
  // updates where a loading flash would be a destructive relayout.
  const [refreshToken, setRefreshToken] = useState(0)

  const [state, setState] = useState<State>(() =>
    canFetch(seriesId, visibleUntilOrder) ? { status: 'loading' } : { status: 'idle' },
  )

  // react-hooks/set-state-in-effect forbids an unconditional synchronous
  // setState at the top of an effect body, and react-hooks/refs forbids
  // reading/writing a ref during render. Resetting state when the
  // (seriesId, visibleUntilOrder, retryToken) key changes is instead done
  // here, during render, comparing against a *state* copy of the previous
  // key — React's documented "adjusting state when a prop changes" pattern —
  // so the effect below only ever sets 'success'/'error' from its async
  // callbacks. Including retryToken in the key means Retry re-enters the
  // 'loading' state the same way a genuine boundary change does. refreshToken
  // is deliberately EXCLUDED from this key: a `refresh()` must not flip to
  // 'loading' (it only re-runs the fetch effect, which shares this state).
  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}:${retryToken}`
  const [prevKey, setPrevKey] = useState(key)
  if (prevKey !== key) {
    setPrevKey(key)
    setState(canFetch(seriesId, visibleUntilOrder) ? { status: 'loading' } : { status: 'idle' })
  }

  useEffect(() => {
    if (!seriesId || visibleUntilOrder == null) return
    let cancelled = false
    getGraph(seriesId, visibleUntilOrder)
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data })
      })
      .catch((error) => {
        if (!cancelled) {
          setState({
            status: 'error',
            error: error instanceof ApiError ? error : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [seriesId, visibleUntilOrder, retryToken, refreshToken])

  function refetch() {
    setRetryToken((token) => token + 1)
  }

  function refresh() {
    setRefreshToken((token) => token + 1)
  }

  return { ...state, refetch, refresh }
}
