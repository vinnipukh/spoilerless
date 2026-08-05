import { useState } from 'react'
import { EyeOff } from 'lucide-react'
import { cn } from '@/lib/utils'

type Props = {
  /** The text to display (possibly spoiler-containing). */
  text: string
  /** The episode order in which this content is first revealed. */
  revealedOrder: number
  /** The user's current watch-progress boundary (visibleUntilOrder). */
  currentOrder: number | null
  className?: string
}

/**
 * Client-side spoiler guard: blurs/masks text whose `revealedOrder` exceeds
 * the user's current watch boundary (`currentOrder`).  Clicking the masked
 * area toggles a local reveal so the user can still inspect if they choose.
 *
 * When `revealedOrder <= currentOrder` (or manually revealed), the text
 * renders normally with word-break so long titles wrap cleanly inside their
 * container.
 */
export function SpoilerGuard({
  text,
  revealedOrder,
  currentOrder,
  className,
}: Props) {
  const [manualReveal, setManualReveal] = useState(false)

  // Safe to show: either within the watch boundary, or user clicked reveal
  const isSafe =
    manualReveal ||
    (currentOrder != null && revealedOrder <= currentOrder)

  if (isSafe) {
    return (
      <span
        className={cn('break-words', className)}
        style={{ overflowWrap: 'anywhere' }}
      >
        {text}
      </span>
    )
  }

  return (
    <button
      type="button"
      onClick={() => setManualReveal(true)}
      className={cn(
        'relative inline-flex items-center gap-1.5 rounded px-1 py-0.5 text-left',
        'cursor-pointer select-none transition-colors',
        'hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        className,
      )}
      aria-label="Reveal spoiler text"
      title="Click to reveal"
    >
      {/* Blurred text behind the overlay */}
      <span
        className="break-words text-foreground/80"
        style={{
          filter: 'blur(5px)',
          userSelect: 'none',
          WebkitUserSelect: 'none',
          overflowWrap: 'anywhere',
        }}
        aria-hidden="true"
      >
        {text}
      </span>
      {/* Gradient + icon overlay */}
      <span className="absolute inset-0 flex items-center justify-center rounded bg-gradient-to-r from-muted/70 via-muted/40 to-muted/70">
        <EyeOff className="h-3.5 w-3.5 text-muted-foreground" />
      </span>
    </button>
  )
}
