import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'

/**
 * Shared keyed fetch state machine (PROB-09/#73).
 *
 * The idle|loading|error|success machine + key/prevKey render reset +
 * stale-response guard that used to be hand-copied in every fetch hook.
 * A key change resets to loading (or idle when disabled) and re-fetches;
 * a stale response (key changed mid-flight, or a newer run superseded it)
 * is dropped via a run-id guard.
 */

export type FetchState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: T }

export function useFetchState<T>(
  key: string,
  enabled: boolean,
  fetcher: () => Promise<T>,
): FetchState<T> & { refetch: () => void } {
  const [state, setState] = useState<FetchState<T>>(() =>
    enabled ? { status: 'loading' } : { status: 'idle' },
  )

  const [prevKey, setPrevKey] = useState(key)
  if (prevKey !== key) {
    setPrevKey(key)
    setState(enabled ? { status: 'loading' } : { status: 'idle' })
  }

  // Sync the ref from an effect, never from the render body: a render-time
  // write is a stale-ref correctness bug under React 19 double-render
  // (react-hooks/refs).
  const fetchKeyRef = useRef(key)
  useEffect(() => {
    fetchKeyRef.current = key
  }, [key])

  const fetcherRef = useRef(fetcher)
  useEffect(() => {
    fetcherRef.current = fetcher
  })

  // Monotonic run id: only the newest run may write state. Supersedes the
  // per-effect `cancelled` cleanup flag — a key change OR a newer refetch
  // (e.g. useGraph's in-place refresh) drops the in-flight response.
  const runIdRef = useRef(0)

  const refetch = useCallback(() => {
    if (!enabled) return
    const runId = ++runIdRef.current
    fetcherRef.current()
      .then((data) => {
        if (runId === runIdRef.current && fetchKeyRef.current === key) {
          setState({ status: 'success', data })
        }
      })
      .catch((error) => {
        if (runId === runIdRef.current && fetchKeyRef.current === key) {
          setState({
            status: 'error',
            error:
              error instanceof ApiError
                ? error
                : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
          })
        }
      })
  }, [enabled, key])

  useEffect(() => {
    if (!enabled) return
    refetch()
  }, [refetch, enabled])

  return { ...state, refetch }
}
