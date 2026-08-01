import { useCallback, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { SessionPicker } from './SessionPicker'
import { useChatSessions } from '../../hooks/useChatSessions'
import { useChatMessages } from '../../hooks/useChatMessages'
import { createChatSession, deleteChatSession } from '../../api/chat'

type Props = {
  seriesId: string | null
  seriesTitle: string
  currentEpisodeCode: string | null
}

function newestFirst<T extends { updated_at: string }>(sessions: T[]): T[] {
  return [...sessions].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
}

// Chat-mode content mounted by DetailPanel.tsx's Sheet (06-UI-SPEC.md "Chat &
// Panel Architecture"). Task 1 (06-09-PLAN.md) wires the session picker,
// series+episode badge, and the empty-state suggestion chips; Task 2 replaces
// the populated-session placeholder below with the real MessageList
// (streaming/citations/retry) plus the Send/Stop-generating input and the
// disabled-provider/transient-503 banners.
export function ChatPanel({ seriesId, seriesTitle, currentEpisodeCode }: Props) {
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

  const handleSuggestionClick = useCallback(
    (text: string) => {
      chatMessages.sendMessage(text)
    },
    [chatMessages],
  )

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

      {!hasMessages ? (
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
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      ) : (
        // MessageList mounts here (06-09-PLAN.md Task 2) with streaming text,
        // citations, retry, and the disabled-provider/transient-503 banners.
        <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
          {chatMessages.messages.map((message) => (
            <p key={message.id} className="text-sm">
              {message.content}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
