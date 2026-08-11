import { describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CommandPalette } from './CommandPalette'
import { useHotkey } from '../../hooks/useHotkey'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { EpisodeResponse } from '../../types/series'

function episode(order: number, title: string): EpisodeResponse {
  return {
    id: `dexter_s01e0${order}`,
    series_id: 'series_dexter',
    season_number: 1,
    episode_number: order,
    episode_order: order,
    code: `S01E0${order}`,
    title,
    visible_from_order: order,
  }
}

const episodes: EpisodeResponse[] = [
  episode(1, 'Dexter: Pilot'),
  episode(2, 'Crocodile'),
  episode(3, 'Popping Cherry'),
]

function renderPalette(props: Partial<Parameters<typeof CommandPalette>[0]> = {}) {
  const base = {
    open: true,
    onOpenChange: vi.fn(),
    graph: graphResponseS01E01,
    episodes,
    onSelectNode: vi.fn(),
    onRequestChange: vi.fn(),
    onOpenChat: vi.fn(),
    onOpenTimeline: vi.fn(),
    onOpenSettings: vi.fn(),
    onOpenDashboard: vi.fn(),
  }
  const merged = { ...base, ...props }
  return render(<CommandPalette {...merged} />)
}

describe('CommandPalette (FEAT-08 ⌘K)', () => {
  it('opens on ⌘K/Ctrl+K via the global hotkey', async () => {
    const user = userEvent.setup()
    function Harness() {
      const [open, setOpen] = useState(false)
      useHotkey('mod+k', () => setOpen((current) => !current))
      return (
        <CommandPalette
          open={open}
          onOpenChange={setOpen}
          graph={graphResponseS01E01}
          episodes={episodes}
          onSelectNode={vi.fn()}
          onRequestChange={vi.fn()}
          onOpenChat={vi.fn()}
          onOpenTimeline={vi.fn()}
          onOpenSettings={vi.fn()}
          onOpenDashboard={vi.fn()}
        />
      )
    }
    render(<Harness />)

    expect(screen.queryByRole('dialog', { name: 'Command palette' })).not.toBeInTheDocument()
    await user.keyboard('{Control>}k{/Control}')
    expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeInTheDocument()
  })

  it('filters node, episode, and action rows as you type', async () => {
    const user = userEvent.setup()
    renderPalette()

    // With an empty query: episodes + actions are listed; node results need
    // a query (searchIndex is payload-local and query-driven).
    expect(screen.queryByText('Jump to node')).not.toBeInTheDocument()
    expect(screen.getByText('Switch episode')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /S01E01 — Dexter: Pilot/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open chat' })).toBeInTheDocument()

    const input = screen.getByRole('textbox')
    await user.type(input, 'dex')
    // Node group appears, filtered to Dexter-matching rows; the episode row
    // "Dexter: Pilot" still matches; no action label contains 'dex'.
    expect(screen.getByText('Jump to node')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Dexter Morgan/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /S01E01 — Dexter: Pilot/ })).toBeInTheDocument()
    expect(screen.queryByText('Actions')).not.toBeInTheDocument()

    await user.clear(input)
    await user.type(input, 'chat')
    // Only the "Open chat" action row survives.
    expect(screen.getByRole('button', { name: 'Open chat' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /James Doakes/ })).not.toBeInTheDocument()
    expect(screen.queryByText('Switch episode')).not.toBeInTheDocument()
  })

  it('calls onRequestChange when Enter selects an episode row', async () => {
    const user = userEvent.setup()
    const onRequestChange = vi.fn()
    renderPalette({ onRequestChange })

    await user.type(screen.getByRole('textbox'), 'pilot')
    await user.keyboard('{Enter}')

    expect(onRequestChange).toHaveBeenCalledWith(1)
  })

  it('calls onSelectNode when Enter selects a node row', async () => {
    const user = userEvent.setup()
    const onSelectNode = vi.fn()
    renderPalette({ onSelectNode })

    await user.type(screen.getByRole('textbox'), 'doakes')
    await user.keyboard('{Enter}')

    expect(onSelectNode).toHaveBeenCalledWith({
      id: 'char_james_doakes',
      label: 'James Doakes',
      nodeType: 'Character',
    })
  })

  it('runs an action row and closes on click', async () => {
    const user = userEvent.setup()
    const onOpenChat = vi.fn()
    const onOpenChange = vi.fn()
    renderPalette({ onOpenChat, onOpenChange })

    await user.click(screen.getByRole('button', { name: 'Open chat' }))

    expect(onOpenChat).toHaveBeenCalledTimes(1)
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('closes on Escape', async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    renderPalette({ onOpenChange })

    await user.keyboard('{Escape}')
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it('renders the locked empty state when nothing matches', async () => {
    const user = userEvent.setup()
    renderPalette()

    await user.type(screen.getByRole('textbox'), 'zzzz')
    expect(screen.getByText('No matching commands')).toBeInTheDocument()
  })
})
