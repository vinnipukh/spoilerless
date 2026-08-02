import { MessageCircle } from 'lucide-react'
import { HeaderNavAction } from '@/components/layout/HeaderNavAction'

// Lives in AppShell's topBar slot (after EpisodeSelector, before the
// user/avatar cluster — App.tsx composes this, no structural change to
// AppShell.tsx itself). Renders through the shared HeaderNavAction control
// so it shares one visual contract with the Settings toggle; this wrapper
// only owns the chat-specific aria-label semantics (06-UI-SPEC.md
// Copywriting Contract: aria-label="Open chat"/"Close chat").
//
// `active` means "the panel is currently open AND in Chat mode" — the
// aria-label always toggles by that state, while the visible text label
// ("Chat") only renders at >=768px per the same contract row.
type Props = {
  active: boolean
  onClick: () => void
}

export function ChatLauncher({ active, onClick }: Props) {
  return (
    <HeaderNavAction
      icon={<MessageCircle aria-hidden="true" />}
      label="Chat"
      ariaLabel={active ? 'Close chat' : 'Open chat'}
      active={active}
      onClick={onClick}
    />
  )
}
