import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

// FEAT-02 timeline event row (UI-SPEC §10.4): left dot, label, episode
// badge, claims count. A button so it is keyboard-accessible (44px min
// touch target). Selection state shows the filled dot + accent ring.
// 08-06: a trailing checkbox (sibling, not nested) toggles the event into
// the graph's timeline filter — independent of row selection.
type Props = {
  label: string
  episodeCode: string | null
  claimsCount: number
  selected: boolean
  onSelect: () => void
  filtered?: boolean
  onToggleFilter?: () => void
}

export function TimelineEventRow({
  label,
  episodeCode,
  claimsCount,
  selected,
  onSelect,
  filtered = false,
  onToggleFilter,
}: Props) {
  return (
    <div className="group flex w-full items-center gap-1 rounded-md">
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          'flex min-h-[44px] w-full items-center gap-3 rounded-md px-2 py-1.5 text-left text-sm transition-colors outline-none select-none hover:bg-elevated focus-visible:ring-2 focus-visible:ring-ring',
          selected && 'bg-accent/10'
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            'size-2.5 shrink-0 rounded-full bg-accent',
            selected && 'ring-2 ring-accent ring-offset-2 ring-offset-background'
          )}
        />
        <span className="min-w-0 flex-1 truncate font-medium">{label}</span>
        {episodeCode && (
          <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
            {episodeCode}
          </span>
        )}
        <span className="shrink-0 text-xs text-muted-foreground">
          {claimsCount} {claimsCount === 1 ? 'claim' : 'claims'}
        </span>
      </button>
      {onToggleFilter && (
        <button
          type="button"
          role="checkbox"
          aria-checked={filtered}
          aria-label={`Filter graph by ${label}`}
          onClick={onToggleFilter}
          className={cn(
            'flex size-8 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring',
            filtered && 'text-accent'
          )}
        >
          <span
            className={cn(
              'flex size-5 items-center justify-center rounded border transition-colors',
              filtered
                ? 'border-accent bg-accent text-accent-foreground'
                : 'border-border opacity-60 group-hover:opacity-100'
            )}
          >
            {filtered && <Check className="size-3" />}
          </span>
        </button>
      )}
    </div>
  )
}
