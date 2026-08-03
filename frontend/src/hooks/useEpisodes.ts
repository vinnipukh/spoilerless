import { useEffect, useState } from 'react'
import { getEpisodes } from '../api/series'
import type { EpisodeResponse } from '../types/series'
import { ApiError } from '../api/client'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: EpisodeResponse[] }

export function useEpisodes(seriesId: string | null, visibleUntilOrder?: number | null) {
  const [state, setState] = useState<State>(() => (seriesId ? { status: 'loading' } : { status: 'idle' }))

  // react-hooks/set-state-in-effect forbids an unconditional synchronous
  // setState at the top of an effect body, and react-hooks/refs forbids
  // reading/writing a ref during render. Resetting state when `seriesId`
  // changes is instead done here, during render, comparing against a
  // *state* copy of the previous value — React's documented "adjusting
  // state when a prop changes" pattern — so the effect below only ever
  // sets 'success'/'error' from its async callbacks.
  const [prevSeriesId, setPrevSeriesId] = useState(seriesId)
  if (prevSeriesId !== seriesId) {
    setPrevSeriesId(seriesId)
    setState(seriesId ? { status: 'loading' } : { status: 'idle' })
  }

  useEffect(() => {
    if (!seriesId) return
    let cancelled = false
    // The effective view order is sent so the backend masks spoiler-sensitive
    // titles server-side (META-01 — masking is never client CSS).
    getEpisodes(seriesId, visibleUntilOrder ?? undefined)
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
    // Refetch when the view boundary changes so masked titles stay current
    // (META-01) — seriesId change resets via the render-time key above.
  }, [seriesId, visibleUntilOrder])

  return state
}
