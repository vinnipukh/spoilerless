import { MessageCircle } from 'lucide-react'

// Lives in AppShell's topBar slot (after EpisodeSelector, before the
// user/avatar cluster — App.tsx composes this, no structural change to
// AppShell.tsx itself). Copies GraphControls.tsx's icon-button + 44px
// touch-target convention (06-PATTERNS.md "ChatLauncher.tsx").
//
// `active` means "the panel is currently open AND in Chat mode" — the
// aria-label always toggles by that state (06-UI-SPEC.md Copywriting
// Contract: aria-label="Open chat"/"Close chat"), while the visible text
// label ("Chat") only renders at >=768px per the same contract row.
type Props = {
  active: boolean
  onClick: () => void
}

export function ChatLauncher({ active, onClick }: Props) {
  return (
    <button
      type="button"
      aria-label={active ? 'Close chat' : 'Open chat'}
      aria-pressed={active}
      onClick={onClick}
      className="flex h-11 min-w-11 items-center justify-center gap-1.5 rounded-md px-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring aria-pressed:bg-accent aria-pressed:text-accent-foreground"
    >
      <MessageCircle className="h-4 w-4" aria-hidden="true" />
      <span className="hidden md:inline">Chat</span>
    </button>
  )
}
