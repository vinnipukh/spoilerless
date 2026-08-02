import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

// Single shared control for the AppShell topBar navigation actions (Chat,
// Settings). Both destinations render through this component so they share
// one visual contract: identical height, padding, radius, typography, icon
// size, icon-to-label gap, hover/focus/pressed behavior. The only
// difference between them is the active/inactive state — inactive is a
// transparent text-muted button with a subtle hover tint; active uses the
// app's `bg-accent` emphasis (same convention the old ChatLauncher used
// via `aria-pressed:bg-accent`).
//
// `ariaLabel` is caller-provided because each control's accessible name
// changes with its state ("Open chat"/"Close chat", "Settings"/"Back to
// graph"). `aria-pressed` mirrors `active` for state exposure.
type Props = {
  icon: ReactNode
  label: string
  ariaLabel: string
  active: boolean
  onClick: () => void
}

export function HeaderNavAction({ icon, label, ariaLabel, active, onClick }: Props) {
  return (
    <button
      type="button"
      aria-label={ariaLabel}
      aria-pressed={active}
      onClick={onClick}
      className={cn(
        'inline-flex h-11 min-w-11 shrink-0 items-center justify-center gap-1.5 rounded-md px-2.5 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors outline-none select-none hover:bg-elevated hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring [&_svg]:size-4 [&_svg]:shrink-0',
        active && 'bg-accent text-accent-foreground hover:bg-accent/90'
      )}
    >
      {icon}
      <span className="hidden md:inline">{label}</span>
    </button>
  )
}
