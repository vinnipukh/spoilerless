import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ChatPanel } from './ChatPanel'
import { emptyChatSession, chatSessionWithOneMessage } from '../../test/fixtures/chatFixtures'
import { ApiError } from '../../api/client'

vi.mock('../../api/chat', () => ({
  listChatSessions: vi.fn(),
  getChatSession: vi.fn(),
  createChatSession: vi.fn(),
  deleteChatSession: vi.fn(),
  streamMessage: vi.fn(),
}))

// Mocked at the hook level (rather than driving a full SSE round-trip
// through `streamMessage`) so the disabled-provider/transient-503/message-
// level error states can be asserted directly and independently — the
// underlying hook's own state-machine transitions are already covered by
// useChatMessages.test.tsx.
vi.mock('../../hooks/useChatMessages', () => ({
  useChatMessages: vi.fn(),
}))

import { listChatSessions, getChatSession, createChatSession } from '../../api/chat'
import { useChatMessages } from '../../hooks/useChatMessages'

function defaultChatMessagesReturn() {
  return {
    status: 'idle' as const,
    messages: [],
    citations: [],
    graphFocus: { node_ids: [], edge_ids: [] },
    proposedChangeSet: null,
    sendMessage: vi.fn(),
    stop: vi.fn(),
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useChatMessages).mockReturnValue(defaultChatMessagesReturn())
})

describe('ChatPanel', () => {
  it('renders the empty-state heading/body/three suggestion chips when there is no session', async () => {
    vi.mocked(listChatSessions).mockResolvedValue([])

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E02" />)

    expect(await screen.findByRole('heading', { name: 'Ask about Dexter' })).toBeInTheDocument()
    expect(
      screen.getByText("Ask about characters, relationships, or events you've watched so far."),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Who have I met so far?' })).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Summarize the story up to S01E02.' }),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Are there any tense relationships?' })).toBeInTheDocument()
  })

  it('renders the empty-state for a session that itself has zero messages', async () => {
    vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
    vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

    expect(await screen.findByRole('heading', { name: 'Ask about Dexter' })).toBeInTheDocument()
  })

  it('shows the session picker "No conversations yet" empty state with zero sessions', async () => {
    vi.mocked(listChatSessions).mockResolvedValue([])

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

    expect(await screen.findByText('No conversations yet')).toBeInTheDocument()
    expect(
      screen.getByText('Ask a question below to start your first conversation.'),
    ).toBeInTheDocument()
  })

  it('renders the series + watched-episode badge', async () => {
    vi.mocked(listChatSessions).mockResolvedValue([])

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E02" />)

    expect(await screen.findByText('Dexter · up to S01E02')).toBeInTheDocument()
  })

  it('renders the initial chat history for a session with existing messages (not the empty state)', async () => {
    vi.mocked(listChatSessions).mockResolvedValue([chatSessionWithOneMessage.session])
    vi.mocked(getChatSession).mockResolvedValue(chatSessionWithOneMessage)
    vi.mocked(useChatMessages).mockReturnValue({
      ...defaultChatMessagesReturn(),
      status: 'success',
      messages: chatSessionWithOneMessage.messages,
    })

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

    expect(await screen.findByText('Who is Dexter?')).toBeInTheDocument()
    expect(
      screen.getByText('Dexter Morgan works at Miami Metro Police Department.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Ask about Dexter' })).not.toBeInTheDocument()
  })

  it('"New conversation" creates a session and switches the active session to it', async () => {
    const user = userEvent.setup()
    vi.mocked(listChatSessions).mockResolvedValue([])
    vi.mocked(createChatSession).mockResolvedValue({
      id: 'session_new',
      series_id: 'series_dexter',
      title: '',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    })

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

    expect(await screen.findByText('No conversations yet')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Start new conversation' }))

    expect(createChatSession).toHaveBeenCalledWith('series_dexter', '')
    // useChatMessages is mocked at module level, so we can't observe the
    // real hook re-binding to the new session id here — that data-flow is
    // covered by useChatSessions.test.tsx/useChatMessages.test.tsx; this
    // asserts ChatPanel's own responsibility: calling createChatSession
    // with the right arguments when "New conversation" is clicked.
  })

  it('clicking "Stop generating" calls the hook\'s stop() function', async () => {
    const user = userEvent.setup()
    vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
    vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)
    const stop = vi.fn()
    vi.mocked(useChatMessages).mockReturnValue({
      ...defaultChatMessagesReturn(),
      status: 'streaming',
      streamingText: 'partial',
      stop,
    })

    render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

    await user.click(await screen.findByRole('button', { name: 'Stop generating' }))
    expect(stop).toHaveBeenCalledTimes(1)
  })

  describe('streaming / error states (Task 2)', () => {
    it('swaps Send for Stop-generating while streaming', async () => {
      vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
      vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)
      vi.mocked(useChatMessages).mockReturnValue({
        ...defaultChatMessagesReturn(),
        status: 'streaming',
        streamingText: 'Dexter Morgan work',
      })

      render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

      expect(await screen.findByText(/Dexter Morgan work/)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Stop generating' })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Send message' })).not.toBeInTheDocument()
    })

    it('shows the disabled-provider banner with distinct copy from the transient-503 banner, and disables the input', async () => {
      vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
      vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)
      vi.mocked(useChatMessages).mockReturnValue({
        ...defaultChatMessagesReturn(),
        status: 'error',
        error: new ApiError({ code: 'LLM_DISABLED', message: 'Chat is disabled.' }),
      })

      render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

      expect(await screen.findByText('Chat is turned off')).toBeInTheDocument()
      expect(
        screen.getByText("The assistant isn't available right now. Ask an administrator to enable it."),
      ).toBeInTheDocument()
      expect(screen.queryByText('The assistant is temporarily unavailable.')).not.toBeInTheDocument()
      expect(screen.getByPlaceholderText('Chat is unavailable')).toBeDisabled()
    })

    it('shows the transient-503 banner with distinct copy from the disabled-provider banner, with a Retry action', async () => {
      vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
      vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)
      vi.mocked(useChatMessages).mockReturnValue({
        ...defaultChatMessagesReturn(),
        status: 'error',
        error: new ApiError({ code: 'LLM_PROVIDER_UNAVAILABLE', message: 'Provider unavailable.' }),
      })

      render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

      expect(await screen.findByText('The assistant is temporarily unavailable.')).toBeInTheDocument()
      expect(screen.queryByText('Chat is turned off')).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Retry' })).toBeInTheDocument()
    })

    it('renders a recoverable message-level failure with a working Retry that re-sends the same content', async () => {
      const user = userEvent.setup()
      vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
      vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)
      const sendMessage = vi.fn()
      // First render: idle/empty (the empty-state suggestion chips render).
      // After the user sends a message, ChatPanel re-renders (local
      // draft/pendingContent state changes) and picks up this second,
      // already-failed return value — standing in for useChatMessages
      // itself transitioning streaming -> error after the real send call
      // (covered independently by useChatMessages.test.tsx).
      vi.mocked(useChatMessages)
        .mockReturnValueOnce(defaultChatMessagesReturn())
        .mockReturnValue({
          ...defaultChatMessagesReturn(),
          status: 'error',
          error: new ApiError({ code: 'LLM_TIMEOUT', message: 'Timed out.' }),
          messages: [
            {
              id: 'pending-user-1',
              role: 'user',
              content: 'What happened?',
              created_at: '2026-01-01T00:00:00Z',
              visible_until_order_snapshot: 0,
            },
          ],
          sendMessage,
        })

      render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

      await user.type(screen.getByLabelText('Chat message'), 'What happened?')
      await user.click(screen.getByRole('button', { name: 'Send message' }))

      expect(await screen.findByText("Couldn't get a response. Retry?")).toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Retry' }))
      expect(sendMessage).toHaveBeenCalledWith('What happened?')
    })

    it('renders the non-retryable generic-failure copy with no Retry for an unrecognized error code', async () => {
      vi.mocked(listChatSessions).mockResolvedValue([emptyChatSession.session])
      vi.mocked(getChatSession).mockResolvedValue(emptyChatSession)
      vi.mocked(useChatMessages).mockReturnValue({
        ...defaultChatMessagesReturn(),
        status: 'error',
        error: new ApiError({ code: 'unknown_error', message: 'Request failed.' }),
        messages: [
          {
            id: 'pending-user-1',
            role: 'user',
            content: 'What happened?',
            created_at: '2026-01-01T00:00:00Z',
            visible_until_order_snapshot: 0,
          },
        ],
      })

      render(<ChatPanel seriesId="series_dexter" seriesTitle="Dexter" currentEpisodeCode="S01E01" />)

      expect(
        await screen.findByText('Something went wrong answering that. Try rephrasing your question.'),
      ).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument()
    })
  })
})
