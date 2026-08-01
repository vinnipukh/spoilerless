import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ChatPanel } from './ChatPanel'
import { emptyChatSession } from '../../test/fixtures/chatFixtures'

vi.mock('../../api/chat', () => ({
  listChatSessions: vi.fn(),
  getChatSession: vi.fn(),
  createChatSession: vi.fn(),
  deleteChatSession: vi.fn(),
  streamMessage: vi.fn(),
}))

import { listChatSessions, getChatSession } from '../../api/chat'

beforeEach(() => {
  vi.clearAllMocks()
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
})
