import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SessionPicker } from './SessionPicker'
import type { ChatSession } from '../../types/chat'

const sessions: ChatSession[] = [
  {
    id: 'session_1',
    series_id: 'series_dexter',
    title: 'About Dexter',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
  {
    id: 'session_2',
    series_id: 'series_dexter',
    title: 'Relationships',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
]

describe('SessionPicker', () => {
  it('shows "No conversations yet" with the documented body when there are zero sessions', () => {
    render(
      <SessionPicker
        sessions={[]}
        activeSessionId={null}
        onSelect={vi.fn()}
        onNewConversation={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(screen.getByText('No conversations yet')).toBeInTheDocument()
    expect(
      screen.getByText('Ask a question below to start your first conversation.'),
    ).toBeInTheDocument()
  })

  it('shows a Skeleton placeholder while loading', () => {
    const { container } = render(
      <SessionPicker
        sessions={[]}
        activeSessionId={null}
        loading
        onSelect={vi.fn()}
        onNewConversation={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    expect(container.querySelectorAll('[data-slot="skeleton"]').length).toBeGreaterThan(0)
  })

  it('calls onNewConversation when "New conversation" is clicked', async () => {
    const user = userEvent.setup()
    const onNewConversation = vi.fn()
    render(
      <SessionPicker
        sessions={sessions}
        activeSessionId="session_1"
        onSelect={vi.fn()}
        onNewConversation={onNewConversation}
        onDelete={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('button', { name: 'Start new conversation' }))
    expect(onNewConversation).toHaveBeenCalledTimes(1)
  })

  it('lists sessions newest-first in the select dropdown with a delete action per row', async () => {
    const user = userEvent.setup()
    render(
      <SessionPicker
        sessions={sessions}
        activeSessionId="session_1"
        onSelect={vi.fn()}
        onNewConversation={vi.fn()}
        onDelete={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('combobox', { name: 'Select a conversation' }))

    const options = await screen.findAllByRole('option')
    expect(options[0]).toHaveTextContent('About Dexter')
    expect(options[1]).toHaveTextContent('Relationships')
    expect(screen.getAllByLabelText('Delete conversation')).toHaveLength(2)
  })

  it('opens the delete confirmation dialog and calls onDelete on confirm', async () => {
    const user = userEvent.setup()
    const onDelete = vi.fn()
    render(
      <SessionPicker
        sessions={sessions}
        activeSessionId="session_1"
        onSelect={vi.fn()}
        onNewConversation={vi.fn()}
        onDelete={onDelete}
      />,
    )

    await user.click(screen.getByRole('combobox', { name: 'Select a conversation' }))
    const [firstDelete] = screen.getAllByLabelText('Delete conversation')
    await user.click(firstDelete)

    expect(await screen.findByText('Delete this conversation?')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onDelete).toHaveBeenCalledWith('session_1')
  })
})
