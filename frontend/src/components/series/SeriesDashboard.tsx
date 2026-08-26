import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { getEpisodes } from '@/api/series'
import { cn } from '@/lib/utils'
import type { SeriesResponse } from '@/types/series'

// FEAT-04 series dashboard (UI-SPEC §10.6): a Dialog listing all available
// series as cards with episode count, progress bar, and an "Open series"
// button. The currently-open series card gets ring-accent. Episode counts
// are fetched once per open (lazy, bounded — the count is the only datum
// used; titles stay server-side masked per D-08). "Open series" reuses the
// caller's existing setSelectedSeriesId + progress flow — never a second
// boundary mechanism (T-09-10-02).

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  series: SeriesResponse[]
  selectedSeriesId: string | null
  watchedThroughOrder: number | null
  onOpenSeries: (seriesId: string) => void
}

type SeriesCard = {
  id: string
  title: string
  episodeCount: number | null
}

export function SeriesDashboard({
  open,
  onOpenChange,
  series,
  selectedSeriesId,
  watchedThroughOrder,
  onOpenSeries,
}: Props) {
  const [counts, setCounts] = useState<Record<string, number | null>>({})
  const [activeIndex, setActiveIndex] = useState(0)
  // THERMO-P3-10: keyboard navigation must keep the active card in view —
  // ref per rendered card, scrolled into view whenever activeIndex changes.
  const cardRefs = useRef<Array<HTMLDivElement | null>>([])

  useEffect(() => {
    cardRefs.current[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  // Lazy, bounded: fetch episode counts for every series once per dialog
  // open. The fetch is kicked off in the effect but the synchronous reset is
  // avoided (react-hooks/set-state-in-effect) by keying state on `open`.
  useEffect(() => {
    if (!open) return
    let cancelled = false
    Promise.all(
      series.map(async (item) => {
        try {
          const episodes = await getEpisodes(item.id)
          return { id: item.id, count: episodes.length }
        } catch {
          return { id: item.id, count: null }
        }
      }),
    ).then((results) => {
      if (cancelled) return
      setCounts(Object.fromEntries(results.map((r) => [r.id, r.count])))
    })
    return () => {
      cancelled = true
    }
  }, [open, series])

  const cards: SeriesCard[] = useMemo(
    () =>
      [...series]
        .sort((a, b) => a.title.localeCompare(b.title))
        .map((item) => ({ id: item.id, title: item.title, episodeCount: counts[item.id] ?? null })),
    [series, counts],
  )

  function handleKeyDown(event: React.KeyboardEvent) {
    if (cards.length === 0) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, cards.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const current = cards[activeIndex]
      if (current) onOpenSeries(current.id)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" onKeyDown={handleKeyDown}>
        <DialogHeader>
          <DialogTitle className="font-heading text-xl">Series</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          {cards.length === 0 && (
            <div className="flex flex-col items-center gap-2 p-8 text-center">
              <p className="font-heading text-base text-foreground">No series available</p>
              <p className="text-sm text-muted-foreground">Add a series to get started.</p>
            </div>
          )}
          {cards.map((item, index) => {
            const active = item.id === selectedSeriesId
            const episodeCount = item.episodeCount ?? 0
            const watched = active ? watchedThroughOrder ?? 0 : 0
            const percent =
              episodeCount > 0 ? Math.min(100, Math.round((watched / episodeCount) * 100)) : 0
            return (
              <div
                key={item.id}
                ref={(el) => { cardRefs.current[index] = el }}
                className={cn(
                  'flex cursor-pointer flex-col gap-2 rounded-lg bg-card p-4 ring-1 ring-border outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring',
                  active && 'ring-accent',
                  index === activeIndex && 'bg-accent/10'
                )}
                onClick={() => onOpenSeries(item.id)}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="truncate font-heading text-base">{item.title}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {item.episodeCount === null ? '—' : `${episodeCount} episodes`}
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${percent}%` }}
                  />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs text-muted-foreground">
                    {percent}% watched
                  </span>
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      onOpenSeries(item.id)
                    }}
                    className="min-h-[44px] rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    Open series
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}
