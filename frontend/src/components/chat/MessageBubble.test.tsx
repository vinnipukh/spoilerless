import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FailedMessageBubble, MessageBubble, StreamingMessageBubble } from './MessageBubble'
import type { ChatMessage } from '../../types/chat'

const userMessage: ChatMessage = {
  id: 'msg_user',
  role: 'user',
  content: 'Who is Dexter?',
  created_at: new Date().toISOString(),
  visible_until_order_snapshot: 1,
}

const assistantMessage: ChatMessage = {
  id: 'msg_assistant',
  role: 'assistant',
  content: 'Dexter Morgan works at Miami Metro.',
  created_at: new Date().toISOString(),
  visible_until_order_snapshot: 1,
}

describe('MessageBubble', () => {
  it('renders a user message right-aligned without the assistant Sparkles icon', () => {
    const { container } = render(<MessageBubble message={userMessage} />)
    expect(screen.getByText('Who is Dexter?')).toBeInTheDocument()
    expect(container.querySelector('.items-end')).toBeInTheDocument()
    expect(container.querySelector('.lucide-sparkles')).not.toBeInTheDocument()
  })

  it('renders an assistant message left-aligned with the Sparkles icon', () => {
    const { container } = render(<MessageBubble message={assistantMessage} />)
    expect(screen.getByText('Dexter Morgan works at Miami Metro.')).toBeInTheDocument()
    expect(container.querySelector('.items-start')).toBeInTheDocument()
    expect(container.querySelector('.lucide-sparkles')).toBeInTheDocument()
  })

  it('wraps a very long assistant message within the bubble without truncation', () => {
    const longMessage: ChatMessage = {
      ...assistantMessage,
      content: 'A very long answer. '.repeat(80).trim(),
    }
    render(<MessageBubble message={longMessage} />)
    const bubble = screen.getByText(longMessage.content)
    expect(bubble).toHaveClass('whitespace-pre-wrap')
    expect(bubble).toHaveClass('break-words')
    expect(bubble.className).toContain('max-w-[85%]')
  })

  it('shows the full timestamp via a native title tooltip', () => {
    render(<MessageBubble message={assistantMessage} />)
    const timestamp = screen.getByTitle(new Date(assistantMessage.created_at).toLocaleString())
    expect(timestamp).toBeInTheDocument()
  })
})

describe('StreamingMessageBubble', () => {
  it('renders the accumulated partial text with a trailing pulsing indicator', () => {
    const { container } = render(<StreamingMessageBubble text="Dexter Morgan work" />)
    expect(screen.getByText(/Dexter Morgan work/)).toBeInTheDocument()
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})

describe('FailedMessageBubble', () => {
  it('renders the recoverable copy with a working Retry action', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    render(<FailedMessageBubble retryable onRetry={onRetry} />)

    expect(screen.getByText("Couldn't get a response. Retry?")).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders the non-retryable generic-failure copy with no Retry action', () => {
    render(<FailedMessageBubble retryable={false} onRetry={vi.fn()} />)

    expect(
      screen.getByText('Something went wrong answering that. Try rephrasing your question.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
  })
})
