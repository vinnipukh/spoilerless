import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { SeriesResponse } from '../../types/series'

type Props = {
  series: SeriesResponse[]
  value: string | null
  onSelect: (seriesId: string) => void
}

export function SeriesSelect({ series, value, onSelect }: Props) {
  return (
    <Select value={value ?? ''} onValueChange={onSelect}>
      <SelectTrigger aria-label="Series" className="font-medium">
        <SelectValue placeholder="Select a series" />
      </SelectTrigger>
      <SelectContent>
        {series.map((item) => (
          <SelectItem key={item.id} value={item.id} className="py-1.5">
            {item.title}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
