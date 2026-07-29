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
  const [state, setState] = useState<State>(() =>
    canFetch(seriesId, visibleUntilOrder) ? { status: 'loading' } : { status: 'idle' },
  )

  // react-hooks/set-state-in-effect forbids an unconditional synchronous
  // setState at the top of an effect body, and react-hooks/refs forbids
  // reading/writing a ref during render. Resetting state when the
  // (seriesId, visibleUntilOrder) key changes is instead done here, during
  // render, comparing against a *state* copy of the previous key — React's
  // documented "adjusting state when a prop changes" pattern — so the
  // effect below only ever sets 'success'/'error' from its async callbacks.
  const key = `${seriesId ?? ''}:${visibleUntilOrder ?? ''}`
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
  }, [seriesId, visibleUntilOrder])

  return state
}
