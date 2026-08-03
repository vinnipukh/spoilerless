import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EpisodeSelector } from './EpisodeSelector'
import type { EpisodeResponse } from '../../types/series'

function episode(order: number, overrides: Partial<EpisodeResponse> = {}): EpisodeResponse {
  return {
    id: `dexter_s01e0${order}`,
    series_id: 'series_dexter',
    season_number: 1,
    episode_number: order,
    episode_order: order,
    code: `S01E0${order}`,
    title: `Real Title ${order}`,
    visible_from_order: order,
    ...overrides,
  }
}

const episodes: EpisodeResponse[] = [
  episode(1),
  episode(2, { display_title: 'S01E02 — Episode 2', is_unlocked: false }),
  episode(3, { display_title: 'S01E03 — Episode 3', is_unlocked: false }),
]

describe('EpisodeSelector', () => {
  it('renders the server-masked display_title for locked episodes and the real title for unlocked ones', () => {
    render(
      <EpisodeSelector episodes={episodes} value={1} watchedThroughOrder={1} onSelect={vi.fn()} />,
    )

    // Unlocked episode keeps its real title.
    expect(screen.getAllByText(/Real Title 1/).length).toBeGreaterThan(0)
    // Locked episodes show the generic masked label, never the real title.
    expect(screen.getAllByText(/S01E02 — Episode 2/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/S01E03 — Episode 3/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/Real Title 2/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Real Title 3/)).not.toBeInTheDocument()
  })

  it('marks locked episodes with an explicit affordance + accessible text, not color alone (D-22)', () => {
    render(
      <EpisodeSelector episodes={episodes} value={1} watchedThroughOrder={1} onSelect={vi.fn()} />,
    )

    // Accessible "Locked" text for each locked episode.
    expect(screen.getAllByText('Locked').length).toBeGreaterThanOrEqual(2)
  })

  it('keeps locked episodes selectable so the unlock flow can start (D-22)', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <EpisodeSelector episodes={episodes} value={1} watchedThroughOrder={1} onSelect={onSelect} />,
    )

    const lockedPill = screen.getAllByText(/S01E02 — Episode 2/)[0]
    await user.click(lockedPill)

    expect(onSelect).toHaveBeenCalledWith(2)
  })

  it('shows the currently viewed episode as the selected value', () => {
    render(
      <EpisodeSelector episodes={episodes} value={2} watchedThroughOrder={2} onSelect={vi.fn()} />,
    )

    const selected = screen
      .getAllByRole('radio')
      .find((item) => item.getAttribute('data-state') === 'on')
    expect(selected?.textContent).toContain('S01E02')
  })
})
