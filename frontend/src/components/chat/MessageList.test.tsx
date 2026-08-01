import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MessageList } from './MessageList'
import { claimCitation, evidenceCitation } from '../../test/fixtures/chatFixtures'
import type { ChatMessage } from '../../types/chat'

const userMessage: ChatMessage = {
  id: 'msg_user',
  role: 'user',
  content: 'Who is Dexter?',
  created_at: '2026-01-01T00:00:00Z',
  visible_until_order_snapshot: 1,
}

const assistantMessage: ChatMessage = {
  id: 'msg_assistant',
  role: 'assistant',
  content: 'Dexter Morgan works at Miami Metro.',
  created_at: '2026-01-01T00:00:05Z',
  visible_until_order_snapshot: 1,
}

describe('MessageList', () => {
  it('renders every message in order', () => {
    render(<MessageList messages={[userMessage, assistantMessage]} citations={[]} />)
    expect(screen.getByText('Who is Dexter?')).toBeInTheDocument()
    expect(screen.getByText('Dexter Morgan works at Miami Metro.')).toBeInTheDocument()
  })

  it('renders a streaming bubble with the partial text when streamingText is set', () => {
    render(<MessageList messages={[userMessage]} streamingText="Dexter Mor" citations={[]} />)
    expect(screen.getByText(/Dexter Mor/)).toBeInTheDocument()
  })

  it('renders no citation-chip row at all when there are zero citations', () => {
    const { container } = render(
      <MessageList messages={[userMessage, assistantMessage]} citations={[]} />,
    )
    expect(container.querySelectorAll('[aria-label="Show in graph"]')).toHaveLength(0)
  })

  it('renders one citation chip identically to many, with no special-case layout', () => {
    const { rerender } = render(
      <MessageList messages={[userMessage, assistantMessage]} citations={[claimCitation]} />,
    )
    expect(screen.getAllByRole('button', { name: 'Show in graph' })).toHaveLength(1)

    rerender(
      <MessageList
        messages={[userMessage, assistantMessage]}
        citations={[claimCitation, evidenceCitation]}
      />,
    )
    expect(screen.getAllByRole('button', { name: 'Show in graph' })).toHaveLength(2)
  })

  it('does not render citations while a streaming turn or failed turn is in progress', () => {
    const { rerender } = render(
      <MessageList
        messages={[userMessage, assistantMessage]}
        citations={[claimCitation]}
        streamingText="partial"
      />,
    )
    expect(screen.queryByRole('button', { name: 'Show in graph' })).not.toBeInTheDocument()

    rerender(
      <MessageList
        messages={[userMessage, assistantMessage]}
        citations={[claimCitation]}
        failedTurn={{ retryable: true, onRetry: vi.fn() }}
      />,
    )
    expect(screen.queryByRole('button', { name: 'Show in graph' })).not.toBeInTheDocument()
  })

  it('renders the failed-turn destructive assistant-slot bubble alongside the already-listed user message', () => {
    render(
      <MessageList
        messages={[userMessage]}
        citations={[]}
        failedTurn={{ retryable: true, onRetry: vi.fn() }}
      />,
    )
    // The user's own message is already in `messages` (useChatMessages
    // appends it optimistically on send) — FailedMessageBubble only adds
    // the destructive "no answer" slot, not a second copy of the question.
    expect(screen.getByText('Who is Dexter?')).toBeInTheDocument()
    expect(screen.getByText("Couldn't get a response. Retry?")).toBeInTheDocument()
  })
})
