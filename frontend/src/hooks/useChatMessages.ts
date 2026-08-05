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

export function useChatMessages(
  seriesId: string | null,
  sessionId: string | null,
  visibleUntilOrder?: number | null,
) {
  const [status, setStatus] = useState<Status>(() =>
    canFetch(seriesId, sessionId) ? { status: 'loading' } : { status: 'idle' },
  )
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [citations, setCitations] = useState<Citation[]>([])
  const [graphFocus, setGraphFocus] = useState<GraphFocus>(EMPTY_GRAPH_FOCUS)
  const [proposedChangeSet, setProposedChangeSet] = useState<ChangeSet | null>(null)

  // The backend get_session_detail filters messages by the CURRENT effective
  // boundary (CHAT-02): include the view in the key so a view-only change
  // re-fetches — above-boundary messages disappear on earlier-view and
  // reappear on return, without destroying the session (D-12).
  const key = `${seriesId ?? ''}:${sessionId ?? ''}:${visibleUntilOrder ?? ''}`
  const [prevKey, setPrevKey] = useState(key)
  // Guards the initial getChatSession fetch below against a send that races
  // ahead of it — see sendStartedRef.
  const sendStartedRef = useRef(false)
  if (prevKey !== key) {
    setPrevKey(key)
    setStatus(canFetch(seriesId, sessionId) ? { status: 'loading' } : { status: 'idle' })
    setMessages([])
    setCitations([])
    setGraphFocus(EMPTY_GRAPH_FOCUS)
    setProposedChangeSet(null)
    // sendStartedRef is reset in an effect below (react-hooks/refs: no ref
    // writes during render).
  }

  // Reset the send guard when the session key changes — declared BEFORE the
  // fetch effect so it runs first (effects run in declaration order) and a
  // key-change fetch never sees a stale true.
  useEffect(() => {
    sendStartedRef.current = false
  }, [key])

  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!seriesId || !sessionId) return
    let cancelled = false
    getChatSession(seriesId, sessionId)
      .then((detail) => {
        // A freshly created session's own mount races the queued first-turn
        // send (ChatPanel.tsx's handleSend->queuedSend flush): both fire off
        // the same render. If the send already started streaming by the
        // time this resolves, applying the (necessarily message-less) fetch
        // result would stomp the in-progress/optimistic turn back to
        // 'success' with an empty list — the exact "chat breaks on the
        // first message only" bug, since a second message never races an
        // unchanged sessionId's mount effect.
        if (!cancelled && !sendStartedRef.current) {
          setMessages(detail.messages)
          setStatus({ status: 'success' })
        }
      })
      .catch((error) => {
        if (!cancelled && !sendStartedRef.current) {
          setStatus({
            status: 'error',
            error: error instanceof ApiError ? error : new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
          })
        }
      })
    return () => {
      cancelled = true
    }
  }, [seriesId, sessionId, visibleUntilOrder])

  const sendChatMessage = useCallback(
    (content: string) => {
      if (!seriesId || !sessionId) return
      sendStartedRef.current = true
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
