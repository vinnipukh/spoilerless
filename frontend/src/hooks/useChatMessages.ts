import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getChatSession, streamMessage } from '../api/chat'
import type { ChatMessage, Citation, GraphFocus, MessageResponseEnvelope } from '../types/chat'
import type { ChangeSet } from '../types/changeSet'

// Extends useGraph.ts's discriminated fetch-status state machine with a
// `streaming` variant carrying the in-progress accumulated text — the
// message list itself, and the last turn's citations/graph_focus/
// proposed_change_set, are tracked separately since they persist across
// status transitions (a new streaming turn shouldn't clear prior messages).
type Status =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'streaming'; streamingText: string }
  | { status: 'success' }
  | { status: 'error'; error: ApiError }

function canFetch(seriesId: string | null, sessionId: string | null): boolean {
  return Boolean(seriesId) && Boolean(sessionId)
}

const EMPTY_GRAPH_FOCUS: GraphFocus = { node_ids: [], edge_ids: [] }

export function useChatMessages(seriesId: string | null, sessionId: string | null) {
  const [status, setStatus] = useState<Status>(() =>
    canFetch(seriesId, sessionId) ? { status: 'loading' } : { status: 'idle' },
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [citations, setCitations] = useState<Citation[]>([])
  const [graphFocus, setGraphFocus] = useState<GraphFocus>(EMPTY_GRAPH_FOCUS)
  const [proposedChangeSet, setProposedChangeSet] = useState<ChangeSet | null>(null)

  const key = `${seriesId ?? ''}:${sessionId ?? ''}`
  const [prevKey, setPrevKey] = useState(key)
  if (prevKey !== key) {
    setPrevKey(key)
    setStatus(canFetch(seriesId, sessionId) ? { status: 'loading' } : { status: 'idle' })
    setMessages([])
    setCitations([])
    setGraphFocus(EMPTY_GRAPH_FOCUS)
    setProposedChangeSet(null)
  }

  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!seriesId || !sessionId) return
    let cancelled = false
    getChatSession(seriesId, sessionId)
      .then((detail) => {
        if (!cancelled) {
          setMessages(detail.messages)
          setStatus({ status: 'success' })
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setStatus({
            status: 'error',
            error: error instanceof ApiError ? error : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [seriesId, sessionId])

  const sendChatMessage = useCallback(
    (content: string) => {
      if (!seriesId || !sessionId) return
      const controller = new AbortController()
      abortControllerRef.current = controller
      setStatus({ status: 'streaming', streamingText: '' })

      // Optimistically append the user's own message immediately. The
      // backend persists it before the assistant's reply streams, but the
      // `done` envelope only ever carries the assistant's message — without
      // this, a just-sent question would never render until the next full
      // `getChatSession` refetch (06-09 fix: a chat UI where the sent
      // question disappears is broken by definition, Rule 1). The
      // placeholder id/snapshot are superseded by the real persisted values
      // whenever the session is next refetched.
      setMessages((prev) => [
        ...prev,
        {
          id: `pending-user-${Date.now()}`,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
          visible_until_order_snapshot: 0,
        },
      ])

      streamMessage(
        seriesId,
        sessionId,
        content,
        {
          onTextDelta: (delta) => {
            setStatus((prev) =>
              prev.status === 'streaming'
                ? { status: 'streaming', streamingText: prev.streamingText + delta }
                : { status: 'streaming', streamingText: delta },
            )
          },
          onDone: (envelope: MessageResponseEnvelope) => {
            setMessages((prev) => [...prev, envelope.message])
            setCitations(envelope.citations)
            setGraphFocus(envelope.graph_focus)
            setProposedChangeSet(envelope.proposed_change_set)
            setStatus({ status: 'success' })
          },
          onError: (error) => {
            setStatus({ status: 'error', error: new ApiError(error) })
          },
        },
        controller.signal,
      ).catch((error) => {
        // An AbortError from `stop()` is expected — the caller already
        // decided to cancel, so it must not surface as an error state (and,
        // by being caught here, never becomes an unhandled rejection). It
        // must still transition `status` off 'streaming' — otherwise the
        // Stop button and Thinking/Streaming bubble (both driven solely by
        // `status` in ChatPanel.tsx/MessageList.tsx) stay stuck forever even
        // though the fetch has genuinely been aborted (G-06-4).
        if (controller.signal.aborted) {
          setStatus({ status: 'success' })
          return
        }
        setStatus({
          status: 'error',
          error: error instanceof ApiError ? error : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
        })
      })
    },
    [seriesId, sessionId],
  )

  const stop = useCallback(() => {
    abortControllerRef.current?.abort()
  }, [])

  return {
    ...status,
    messages,
    citations,
    graphFocus,
    proposedChangeSet,
    sendMessage: sendChatMessage,
    stop,
  }
}
