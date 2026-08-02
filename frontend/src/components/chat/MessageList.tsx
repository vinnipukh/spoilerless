import { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble, StreamingMessageBubble, FailedMessageBubble, ThinkingBubble } from './MessageBubble'
import { CitationChip } from './CitationChip'
import { ChangeSetCard } from './ChangeSetCard'
import type { ChatMessage, Citation } from '../../types/chat'
import type { ChangeSet } from '../../types/changeSet'

export type FailedTurn = {
  retryable: boolean
  onRetry: () => void
}

type Props = {
  messages: ChatMessage[]
  streamingText?: string | null
  failedTurn?: FailedTurn | null
  citations: Citation[]
  onShowInGraph?: (citation: Citation) => void
  onOpenDetail?: (citation: Citation) => void
  // The last turn's proposed ChangeSet (06-11) — rendered as a
  // ChangeSetCard below the assistant message that proposed it, the same
  // "attached below the bubble" pattern as the citation-chip row.
  proposedChangeSet?: ChangeSet | null
  seriesId?: string | null
  onApplied?: (changeSet: ChangeSet) => void
}

// Auto-scrolls to the newest message on send/stream unless the user has
// manually scrolled up (06-UI-SPEC.md "Message list") — uses the shadcn
// scroll-area component (rather than a plain overflow-y-auto div) for its
// more predictable scroll-anchoring behavior during streaming appends.
export function MessageList({
  messages,
  streamingText,
  failedTurn,
  citations,
  onShowInGraph,
  onOpenDetail,
  proposedChangeSet,
  seriesId,
  onApplied,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)
  const [userScrolledUp, setUserScrolledUp] = useState(false)

  useEffect(() => {
    const viewport = containerRef.current?.querySelector<HTMLElement>('[data-slot="scroll-area-viewport"]')
    if (!viewport) return
    function handleScroll() {
      if (!viewport) return
      const distanceFromBottom = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
      setUserScrolledUp(distanceFromBottom > 48)
    }
    viewport.addEventListener('scroll', handleScroll)
    return () => viewport.removeEventListener('scroll', handleScroll)
  }, [])

  useEffect(() => {
    if (userScrolledUp) return
    bottomRef.current?.scrollIntoView({ block: 'end' })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, streamingText, failedTurn])

  const lastMessage = messages[messages.length - 1]
  const showCitations =
    streamingText == null && !failedTurn && lastMessage?.role === 'assistant' && citations.length > 0
  // The proposed ChangeSet rides the same "attached below the last assistant
  // bubble" slot as citations (06-UI-SPEC.md "Proposed-ChangeSet card": "the
  // same 'attached below the bubble' pattern as citations"), and is likewise
  // suppressed while a turn is streaming or has failed.
  const showChangeSet =
    streamingText == null && !failedTurn && lastMessage?.role === 'assistant' && proposedChangeSet != null

  return (
    <div ref={containerRef} className="min-h-0 flex-1">
      <ScrollArea className="h-full">
        <div className="flex flex-col gap-3 pr-2">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {showCitations && (
            <div className="flex flex-wrap gap-1.5 pl-9">
              {citations.map((citation, index) => (
                <CitationChip
                  key={`${citation.claim_id ?? citation.evidence_id ?? citation.source_id ?? 'citation'}-${index}`}
                  citation={citation}
                  onShowInGraph={onShowInGraph}
                  onOpenDetail={onOpenDetail}
                />
              ))}
            </div>
          )}

          {showChangeSet && proposedChangeSet && seriesId && (
            <div className="pl-9">
              <ChangeSetCard
                changeSet={proposedChangeSet}
                seriesId={seriesId}
                onApplied={onApplied}
              />
            </div>
          )}

          {streamingText != null && (
            <StreamingMessageBubble text={streamingText} />
          )}
          {streamingText === '' && <ThinkingBubble />}

          {failedTurn && (
            <FailedMessageBubble retryable={failedTurn.retryable} onRetry={failedTurn.onRetry} />
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  )
}
