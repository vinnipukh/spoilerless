import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { listChatSessions } from '../api/chat'
import type { ChatSession } from '../types/chat'

// Copies useGraph.ts's discriminated fetch-status state machine
// (idle | loading | success | error) for the session-list state.
type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error'; error: ApiError }
  | { status: 'success'; data: ChatSession[] }

function canFetch(seriesId: string | null): boolean {
  return Boolean(seriesId)
}

export function useChatSessions(seriesId: string | null) {
  const [state, setState] = useState<State>(() =>
    canFetch(seriesId) ? { status: 'loading' } : { status: 'idle' },
  )

  // Resetting state when seriesId changes follows useGraph.ts's/useNotes.ts's
  // "adjusting state when a prop changes" pattern (compares against a state
  // copy of the previous key during render, not inside an effect).
  const key = seriesId ?? ''
  const [prevKey, setPrevKey] = useState(key)
  if (prevKey !== key) {
    setPrevKey(key)
    setState(canFetch(seriesId) ? { status: 'loading' } : { status: 'idle' })
  }

  const fetchKeyRef = useRef(key)
  // Sync the ref from an effect, never from the render body: a render-time
  // write is a stale-ref correctness bug under React 19 double-render
  // (react-hooks/refs). Declared BEFORE the fetch effect below so the ref is
  // updated before a key-change fetch fires.
  useEffect(() => {
    fetchKeyRef.current = key
  }, [key])

  const fetchSessions = useCallback(() => {
    if (!seriesId) return
    listChatSessions(seriesId)
      .then((data) => {
        if (fetchKeyRef.current === key) {
          setState({ status: 'success', data })
        }
      })
      .catch((error) => {
        if (fetchKeyRef.current === key) {
          setState({
            status: 'error',
            error: error instanceof ApiError ? error : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
          })
        }
      })
  }, [seriesId, key])

  useEffect(() => {
    if (!seriesId) return
    fetchSessions()
  }, [fetchSessions, seriesId])

  return {
    status: state.status,
    sessions: state.status === 'success' ? state.data : [],
    error: state.status === 'error' ? state.error : null,
    refetch: fetchSessions,
  }
}
