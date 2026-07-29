import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { EpisodeResponse } from '../../types/series'

type Props = {
  episodes: EpisodeResponse[]
  value: number | null
  onSelect: (episodeOrder: number) => void
  disabled?: boolean
}

export function EpisodeSelector({ episodes, value, onSelect, disabled }: Props) {
  return (
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
  )
}
