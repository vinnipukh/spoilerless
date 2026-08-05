import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import type { SeriesResponse } from '@/types/series'
import { SeriesDashboard } from './SeriesDashboard'

vi.mock('@/api/series', () => ({
  getEpisodes: vi.fn(),
}))

import { getEpisodes } from '@/api/series'

const series: SeriesResponse[] = [
  { id: 'series_dexter', title: 'Dexter', slug: 'dexter' },
  { id: 'series_other', title: 'Other Show', slug: 'other' },
]

function renderDashboard(overrides: Partial<Parameters<typeof SeriesDashboard>[0]> = {}) {
  return render(
    <SeriesDashboard
      open
      onOpenChange={vi.fn()}
      series={series}
      selectedSeriesId="series_dexter"
      watchedThroughOrder={2}
      onOpenSeries={vi.fn()}
      {...overrides}
    />,
  )
}

describe('SeriesDashboard', () => {
  it('renders series cards with episode counts and progress', async () => {
    vi.mocked(getEpisodes).mockImplementation(async (id: string) =>
      id === 'series_dexter' ? [{ id: 'e1' }, { id: 'e2' }] as never : [{ id: 'e1' }] as never,
    )
    renderDashboard()
    expect(screen.getByText('Series')).toBeTruthy()
    expect(screen.getByText('Dexter')).toBeTruthy()
    expect(screen.getByText('Other Show')).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByText('2 episodes')).toBeTruthy()
      expect(screen.getByText('1 episodes')).toBeTruthy()
    })
  })

  it('marks the currently-open series with ring-accent and shows its progress', async () => {
    vi.mocked(getEpisodes).mockResolvedValue([{ id: 'e1' }, { id: 'e2' }] as never)
    renderDashboard()
    await waitFor(() => {
      expect(screen.getAllByText('2 episodes').length).toBe(2)
    })
    const dexterCard = screen.getByText('Dexter').closest('div')!.parentElement!
    expect(dexterCard.className).toContain('ring-accent')
    expect(screen.getByText('100% watched')).toBeTruthy() // 2/2 watched
  })

  it('Open series switches selection and closes through the callback', async () => {
    vi.mocked(getEpisodes).mockResolvedValue([] as never)
    const onOpenSeries = vi.fn()
    const onOpenChange = vi.fn()
    renderDashboard({ onOpenSeries, onOpenChange })
    fireEvent.click(screen.getByText('Other Show'))
    expect(onOpenSeries).toHaveBeenCalledWith('series_other')
  })

  it('renders the locked empty-state copy with no series', () => {
    vi.mocked(getEpisodes).mockResolvedValue([] as never)
    renderDashboard({ series: [] })
    expect(screen.getByText('No series available')).toBeTruthy()
    expect(screen.getByText('Add a series to get started.')).toBeTruthy()
  })

  it('keyboard navigation: ArrowDown + Enter opens the second card', async () => {
    vi.mocked(getEpisodes).mockResolvedValue([] as never)
    const onOpenSeries = vi.fn()
    renderDashboard({ onOpenSeries })
    fireEvent.keyDown(screen.getByText('Series').closest('div')!, { key: 'ArrowDown' })
    fireEvent.keyDown(screen.getByText('Series').closest('div')!, { key: 'Enter' })
    expect(onOpenSeries).toHaveBeenCalledWith('series_other')
  })
})
