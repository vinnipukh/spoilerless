import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ChatSheet } from './ChatSheet'

// ChatPanel mounts on open and calls the chat API client via useChatSessions
// — stub it so the sheet renders without hitting a real/undefined `fetch`.
vi.mock('../../api/chat', () => ({
  listChatSessions: vi.fn().mockResolvedValue([]),
  getChatSession: vi.fn(),
  createChatSession: vi.fn(),
  deleteChatSession: vi.fn(),
  streamMessage: vi.fn(),
}))

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  seriesId: 'series_dexter',
  seriesTitle: 'Dexter',
  currentEpisodeCode: 'S01E01',
}

describe('ChatSheet', () => {
  beforeEach(() => {
    localStorage.clear()
    // jsdom default viewport: 1024px wide.
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })
  })

  it('renders the chat sheet with a resize handle on the left edge', async () => {
    render(<ChatSheet {...defaultProps} />)

    expect(await screen.findByRole('heading', { name: 'Chat' })).toBeInTheDocument()
    expect(screen.getByRole('separator', { name: 'Resize chat panel' })).toBeInTheDocument()
  })

  it('resizes the panel when the handle is dragged left', async () => {
    render(<ChatSheet {...defaultProps} />)

    const handle = screen.getByRole('separator', { name: 'Resize chat panel' })
    const dialog = screen.getByRole('dialog')

    // Drag from x=800 to x=400 → width = innerWidth(1024) - 400 = 624px.
    fireEvent.pointerDown(handle, { clientX: 800, pointerId: 1 })
    fireEvent.pointerMove(handle, { clientX: 400, pointerId: 1 })
    fireEvent.pointerUp(handle, { clientX: 400, pointerId: 1 })

    expect(dialog).toHaveStyle({ width: '624px' })
    // The chosen width persists for the next session.
    expect(localStorage.getItem('chatSheetWidth')).toBe('624')
  })

  it('clamps the width to a sane range and restores the default on double-click', async () => {
    render(<ChatSheet {...defaultProps} />)

    const handle = screen.getByRole('separator', { name: 'Resize chat panel' })
    const dialog = screen.getByRole('dialog')

    // Drag far beyond the viewport → clamped to innerWidth - 360 = 664.
    fireEvent.pointerDown(handle, { clientX: 1000, pointerId: 1 })
    fireEvent.pointerMove(handle, { clientX: -2000, pointerId: 1 })
    fireEvent.pointerUp(handle, { clientX: -2000, pointerId: 1 })
    expect(dialog).toHaveStyle({ width: '664px' })

    // Double-click the handle resets to the default responsive width.
    fireEvent.doubleClick(handle)
    expect(dialog).not.toHaveStyle({ width: '664px' })
    expect(localStorage.getItem('chatSheetWidth')).toBeNull()
  })
})
