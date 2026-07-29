import { useEffect, useState } from 'react'
import { getSeries } from '../api/series'
import type { SeriesResponse } from '../types/series'
import { ApiError } from '../api/client'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: SeriesResponse[] }

export function useSeries() {
  // No params, always fetches exactly once on mount — the initial state
  // itself represents "loading" so the effect never needs to call setState
  // synchronously before starting the fetch (react-hooks/set-state-in-effect).
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false
    getSeries()
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
  }, [])

  return state
}
