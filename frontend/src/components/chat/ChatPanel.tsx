import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Send, Square } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { SessionPicker } from './SessionPicker'
import { MessageList } from './MessageList'
import { useChatSessions } from '../../hooks/useChatSessions'
import { useChatMessages } from '../../hooks/useChatMessages'
import { createChatSession, deleteChatSession } from '../../api/chat'
import type { ApiError } from '../../api/client'
import type { Citation } from '../../types/chat'

type Props = {
  seriesId: string | null
  seriesTitle: string
  currentEpisodeCode: string | null
  onShowInGraph?: (citation: Citation) => void
  onOpenDetail?: (citation: Citation) => void
}

function newestFirst<T extends { updated_at: string }>(sessions: T[]): T[] {
  return [...sessions].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
}

// Classifies a send-turn ApiError into the four distinct UI treatments the
// Copywriting Contract requires: the two page-level provider banners
// (LLM_DISABLED / LLM_PROVIDER_UNAVAILABLE — known, named infra states) vs. a
// per-turn failed-message bubble for anything else, itself split into
// "recoverable" (any other LLM_-prefixed error — assumed transient/worth
// retrying) vs. "non-retryable" (an opaque/unrecognized error, including the
// hook's own `unknown_error` catch-all fallback for a non-ApiError
// exception — retrying identical content is unlikely to help).
type ChatErrorKind = 'disabled' | 'provider-unavailable' | 'recoverable' | 'non-retryable'

function classifyChatError(error: ApiError): ChatErrorKind {
  if (error.code === 'LLM_DISABLED') return 'disabled'
  if (error.code === 'LLM_PROVIDER_UNAVAILABLE') return 'provider-unavailable'
  if (error.code.startsWith('LLM_')) return 'recoverable'
  return 'non-retryable'
}

// Chat-mode content mounted by DetailPanel.tsx's Sheet (06-UI-SPEC.md "Chat &
// Panel Architecture"). Session picker, series+episode badge, and the
// empty-state suggestion chips (Task 1); streaming/citations/retry via
// MessageList plus the Send/Stop-generating input and the disabled-provider/
// transient-503 banners (Task 2).
export function ChatPanel({ seriesId, seriesTitle, currentEpisodeCode, onShowInGraph, onOpenDetail }: Props) {
  const sessionsState = useChatSessions(seriesId)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  // Default-select the most recently updated session once the list loads —
  // an in-memory convenience only (never sessionStorage/localStorage), so a
  // fresh page load still starts from App.tsx's own default state, not a
  // persisted chat session choice. Adjusted during render (comparing a state
  // copy of the previous session-id set), copying useGraph.ts's/useNotes.ts's
  // established "adjust state when a key changes" pattern rather than an
  // unconditional setState-in-effect (06-PATTERNS.md).
  const sessionsKey =
    sessionsState.status === 'success' ? sessionsState.sessions.map((session) => session.id).join(',') : null
  const [prevSessionsKey, setPrevSessionsKey] = useState(sessionsKey)
  if (prevSessionsKey !== sessionsKey) {
    setPrevSessionsKey(sessionsKey)
    if (sessionsState.status === 'success') {
      const stillValid = activeSessionId && sessionsState.sessions.some((session) => session.id === activeSessionId)
      if (!stillValid) {
        setActiveSessionId(sessionsState.sessions.length > 0 ? newestFirst(sessionsState.sessions)[0].id : null)
      }
    }
  }

  const chatMessages = useChatMessages(seriesId, activeSessionId)

  const [draft, setDraft] = useState('')
  const [pendingContent, setPendingContent] = useState<string | null>(null)
  // A message queued to send once a brand-new session (created on-demand
  // from the empty state, see handleSend below) becomes the active session
  // — useChatMessages is bound to `activeSessionId` at render time, so a
  // just-created session's hook instance only exists starting next render.
  const [queuedSend, setQueuedSend] = useState<string | null>(null)

  // Clear the retry target once the turn resolves; flush a queued send once
  // its target session becomes active (both adjusted during render, same
  // "compare previous key" pattern as above).
  const [prevChatStatus, setPrevChatStatus] = useState(chatMessages.status)
  if (prevChatStatus !== chatMessages.status) {
    setPrevChatStatus(chatMessages.status)
    if (chatMessages.status === 'success') setPendingContent(null)
  }

  // A ref (not state) one-shot guard — mutating a ref inside an effect is
  // the documented-safe way to avoid re-flushing the same queued send for a
  // session id already handled, without an extra setState-in-effect call
  // (react-hooks/set-state-in-effect only inspects setState, not ref writes).
  const flushedForSessionRef = useRef<string | null>(null)
  useEffect(() => {
    if (!queuedSend || !activeSessionId) return
    if (flushedForSessionRef.current === activeSessionId) return
    flushedForSessionRef.current = activeSessionId
    chatMessages.sendMessage(queuedSend)
    // Only re-run when the queued content or its target session changes —
    // `chatMessages` is a fresh object every render by design (useGraph.ts's
    // established hook-return shape), including it would refire this effect
    // every render without changing behavior.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queuedSend, activeSessionId])

  const handleNewConversation = useCallback(async () => {
    if (!seriesId || creating) return
    setCreating(true)
    try {
      const session = await createChatSession(seriesId, '')
      setActiveSessionId(session.id)
      sessionsState.refetch()
    } catch {
      // Creation failures leave the current session untouched; the button
      // remains available to retry (no distinct error UI required by the
      // UI-SPEC for this specific action).
    } finally {
      setCreating(false)
    }
  }, [seriesId, creating, sessionsState])

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      if (!seriesId) return
      try {
        await deleteChatSession(seriesId, sessionId)
        if (activeSessionId === sessionId) setActiveSessionId(null)
        sessionsState.refetch()
      } catch {
        // Deletion failure leaves the session list unchanged; user can retry.
      }
    },
    [seriesId, activeSessionId, sessionsState],
  )

  // Sending while no session is active yet (the very first message of a
  // fresh chat, per the empty-state's "Ask a question below to start your
  // first conversation" promise) transparently creates one first, then
  // queues the content to flush once that session's own message hook mounts.
  const handleSend = useCallback(
    async (content: string) => {
      const trimmed = content.trim()
      if (!trimmed || !seriesId) return
      setDraft('')

      if (!activeSessionId) {
        try {
          const session = await createChatSession(seriesId, '')
          setActiveSessionId(session.id)
          sessionsState.refetch()
          setPendingContent(trimmed)
          setQueuedSend(trimmed)
        } catch {
          // Session creation failed — nothing queued, draft is restored so
          // the user doesn't lose what they typed.
          setDraft(trimmed)
        }
        return
      }

      setPendingContent(trimmed)
      chatMessages.sendMessage(trimmed)
    },
    [seriesId, activeSessionId, chatMessages, sessionsState],
  )

  const handleRetry = useCallback(() => {
    if (pendingContent) chatMessages.sendMessage(pendingContent)
  }, [pendingContent, chatMessages])

  const handleSubmit = useCallback(
    (event: FormEvent) => {
      event.preventDefault()
      handleSend(draft)
    },
    [draft, handleSend],
  )

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        handleSend(draft)
      }
    },
    [draft, handleSend],
  )

  const errorKind: ChatErrorKind | null =
    chatMessages.status === 'error' ? classifyChatError(chatMessages.error) : null
  const isStreaming = chatMessages.status === 'streaming'
  const providerDisabled = errorKind === 'disabled'
  const providerUnavailable = errorKind === 'provider-unavailable'
  const messageFailed = errorKind === 'recoverable' || errorKind === 'non-retryable'
  const hasMessages = chatMessages.messages.length > 0

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <SessionPicker
        sessions={sessionsState.sessions}
        activeSessionId={activeSessionId}
        loading={sessionsState.status === 'loading'}
        onSelect={setActiveSessionId}
        onNewConversation={handleNewConversation}
        onDelete={handleDeleteSession}
      />

      <Badge variant="outline" className="w-fit">
        {seriesTitle}
        {currentEpisodeCode ? ` · up to ${currentEpisodeCode}` : ''}
      </Badge>

      {providerDisabled && (
        <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3">
          <h4 className="font-heading text-base font-semibold">Chat is turned off</h4>
          <p className="text-xs text-muted-foreground">
            The assistant isn&apos;t available right now. Ask an administrator to enable it.
          </p>
        </div>
      )}

      {providerUnavailable && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-destructive/20 bg-destructive/5 p-3">
          <p className="text-xs text-foreground">The assistant is temporarily unavailable.</p>
          <button
            type="button"
            onClick={handleRetry}
            className="min-h-[44px] shrink-0 rounded-md bg-destructive/10 px-3 py-1.5 text-xs font-medium text-destructive transition-colors hover:bg-destructive/20"
          >
            Retry
          </button>
        </div>
      )}

      {!hasMessages && !isStreaming ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 py-8 text-center">
          <h3 className="font-heading text-lg font-semibold">Ask about {seriesTitle}</h3>
          <p className="max-w-xs text-sm text-muted-foreground">
            Ask about characters, relationships, or events you&apos;ve watched so far.
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {[
              'Who have I met so far?',
              `Summarize the story up to ${currentEpisodeCode ?? 'now'}.`,
              'Are there any tense relationships?',
            ].map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                className="min-h-[44px] rounded-full border border-border px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
                onClick={() => handleSend(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <MessageList
          messages={chatMessages.messages}
          streamingText={isStreaming ? chatMessages.streamingText : null}
          failedTurn={messageFailed ? { retryable: errorKind === 'recoverable', onRetry: handleRetry } : null}
          citations={chatMessages.citations}
          onShowInGraph={onShowInGraph}
          onOpenDetail={onOpenDetail}
        />
      )}

      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            providerDisabled ? 'Chat is unavailable' : `Ask about ${currentEpisodeCode ?? 'now'} and earlier…`
          }
          disabled={providerDisabled}
          aria-label="Chat message"
          rows={1}
          className="min-h-[44px] flex-1 resize-none"
        />
        {isStreaming ? (
          <button
            type="button"
            aria-label="Stop generating"
            onClick={() => chatMessages.stop()}
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-md bg-destructive/10 px-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/20"
          >
            <Square className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">Stop generating</span>
          </button>
        ) : (
          <button
            type="submit"
            aria-label="Send message"
            disabled={providerDisabled || !draft.trim()}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md bg-primary text-primary-foreground transition-colors hover:bg-primary/80 disabled:pointer-events-none disabled:opacity-50"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </form>
    </div>
  )
}
