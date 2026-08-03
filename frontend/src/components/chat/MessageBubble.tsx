import { RotateCw, Sparkles } from 'lucide-react'
import type { ChatMessage } from '../../types/chat'

// Reduced-motion preference detected at module scope (no DOM access during
// SSR) — same pattern GraphCanvas.tsx already uses for its own animations.
const prefersReducedMotion =
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function formatRelativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return `${Math.round(diffHr / 24)}d ago`
}

function Timestamp({ iso }: { iso: string }) {
  return (
    <span
      className="px-1 text-xs font-semibold text-muted-foreground"
      title={new Date(iso).toLocaleString()}
    >
      {formatRelativeTime(iso)}
    </span>
  )
}

// User bubble: --elevated surface, right-aligned (06-UI-SPEC.md "Message
// list"). Assistant bubble: --card surface, left-aligned, Sparkles icon.
export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
      <div className={`flex items-end gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {!isUser && (
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary/20 text-secondary"
            aria-hidden="true"
          >
            <Sparkles className="h-4 w-4" />
          </div>
        )}
        <div
          className={`min-w-[35%] max-w-[85%] rounded-lg px-4 py-2 text-sm whitespace-pre-wrap break-words ${
            isUser ? 'bg-elevated' : 'bg-card'
          } text-foreground`}
        >
          {message.content}
        </div>
      </div>
      <Timestamp iso={message.created_at} />
    </div>
  )
}

// A streaming-in-progress assistant bubble: accumulated partial text plus a
// trailing pulsing indicator (reduced-motion-aware).
export function StreamingMessageBubble({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-1 items-start">
      <div className="flex items-end gap-2">
        <div
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary/20 text-secondary"
          aria-hidden="true"
        >
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="min-w-[35%] max-w-[85%] rounded-lg bg-card px-4 py-2 text-sm whitespace-pre-wrap break-words text-foreground">
          {text}
          <span
            className={`ml-0.5 inline-block h-3 w-1.5 align-middle bg-muted-foreground/70 ${
              prefersReducedMotion ? '' : 'animate-pulse'
            }`}
            aria-hidden="true"
          />
        </div>
      </div>
    </div>
  )
}

// Shown while a turn is generating but no text has streamed yet (the
// pipeline's tool rounds can take many seconds before the first delta) —
// without this, the user sees nothing and may resend, which is what caused
// the spurious concurrent-slot errors.
export function ThinkingBubble() {
  return (
    <div className="flex flex-col gap-1 items-start">
      <div className="flex items-end gap-2">
        <div
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-secondary/20 text-secondary"
          aria-hidden="true"
        >
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="flex items-center gap-1.5 rounded-lg bg-card px-4 py-2.5 text-sm text-muted-foreground">
          <span className="size-1.5 animate-pulse rounded-full bg-current motion-reduce:animate-none" />
          <span className="size-1.5 animate-pulse rounded-full bg-current motion-reduce:animate-none [animation-delay:150ms]" />
          <span className="size-1.5 animate-pulse rounded-full bg-current motion-reduce:animate-none [animation-delay:300ms]" />
          <span className="sr-only">Thinking</span>
        </div>
      </div>
    </div>
  )
}

// A failed turn's assistant-slot bubble: the user's own question is already
// rendered as a normal MessageBubble (useChatMessages appends it
// optimistically on send, 06-09 fix) — this only renders the
// destructive-accented "no answer" slot alongside it. Only `retryable`
// failures render the Retry action (06-UI-SPEC.md Copywriting Contract:
// "Couldn't get a response. Retry?" vs. the generic non-retryable copy with
// no Retry action).
export function FailedMessageBubble({
  retryable,
  onRetry,
}: {
  retryable: boolean
  onRetry: () => void
}) {
  return (
    <div className="min-w-[35%] max-w-[85%] rounded-lg border-l-4 border-destructive bg-card px-4 py-2 text-sm text-foreground">
      <p>
        {retryable
          ? "Couldn't get a response. Retry?"
          : 'Something went wrong answering that. Try rephrasing your question.'}
      </p>
      {retryable && (
        <button
          type="button"
          className="mt-2 inline-flex min-h-[44px] items-center gap-1.5 rounded-md bg-destructive/10 px-2.5 py-1.5 text-xs font-medium text-destructive transition-colors hover:bg-destructive/20"
          onClick={onRetry}
        >
          <RotateCw className="h-3.5 w-3.5" aria-hidden="true" />
          Retry
        </button>
      )}
    </div>
  )
}
