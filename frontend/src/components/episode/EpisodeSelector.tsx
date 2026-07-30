import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ToggleGroup } from 'radix-ui'
import { cn } from '@/lib/utils'
import type { EpisodeResponse } from '../../types/series'

type Props = {
  episodes: EpisodeResponse[]
  value: number | null
  onSelect: (episodeOrder: number) => void
  disabled?: boolean
}

export function EpisodeSelector({ episodes, value, onSelect, disabled }: Props) {
  return (
    <>
      {/* Segmented/pill control — visible at md+ */}
      <ToggleGroup.Root
        type="single"
        value={value != null ? String(value) : ''}
        onValueChange={(next) => {
          if (next) onSelect(Number(next))
        }}
        disabled={disabled}
        className="hidden md:inline-flex items-center gap-0.5 rounded-lg bg-muted p-0.5 overflow-x-auto flex-nowrap [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
      >
        {episodes.map((episode) => (
          <ToggleGroup.Item
            key={episode.id}
            value={String(episode.episode_order)}
            disabled={disabled}
            className={cn(
              'inline-flex items-center justify-center rounded-md px-2.5 py-1 text-sm font-medium transition-colors',
              'hover:bg-elevated',
              'data-[state=on]:bg-accent data-[state=on]:text-accent-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              'disabled:pointer-events-none disabled:opacity-50',
            )}
          >
            <span>{episode.code}</span>
            <span className="hidden lg:inline"> — {episode.title}</span>
          </ToggleGroup.Item>
        ))}
      </ToggleGroup.Root>

      {/* Original Select — visible only below md, kept in DOM for test compatibility */}
      <div className="md:hidden">
        <Select
          value={value != null ? String(value) : ''}
          onValueChange={(next) => onSelect(Number(next))}
          disabled={disabled}
        >
          <SelectTrigger aria-label="Watch progress">
            <SelectValue placeholder="Watch progress" />
          </SelectTrigger>
          <SelectContent>
            {episodes.map((episode) => (
              <SelectItem key={episode.id} value={String(episode.episode_order)}>
                {episode.code} — {episode.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </>
  )
}
