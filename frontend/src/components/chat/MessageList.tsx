import { useEffect, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { MessageBubble, StreamingMessageBubble, FailedMessageBubble } from './MessageBubble'
import { CitationChip } from './CitationChip'
import type { ChatMessage, Citation } from '../../types/chat'

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

          {streamingText != null && <StreamingMessageBubble text={streamingText} />}

          {failedTurn && (
            <FailedMessageBubble retryable={failedTurn.retryable} onRetry={failedTurn.onRetry} />
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>
    </div>
  )
}
