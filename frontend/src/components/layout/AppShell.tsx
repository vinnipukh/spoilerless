import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Command } from 'lucide-react'
import type { User } from '@/types/auth'
import { HeaderNavAction } from './HeaderNavAction'
import { modLabel } from '@/hooks/useHotkey'

type Props = {
  user?: User
  onLogout?: () => void
  topBar: ReactNode
  children: ReactNode
  /** FEAT-08 (09-09): AppShell's ⌘K palette trigger (Command icon, topBar
   * contract — UI-SPEC §10.10). */
  onOpenPalette?: () => void
}

const avatarUrl = (user?: User): string | null => {
  return user?.avatar_url && user.avatar_url.length > 0 ? user.avatar_url : null
}

// Inline SVG user icon for fallback avatar
function UserIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="size-4 shrink-0"
    >
      <circle cx="12" cy="8" r="4" />
      <path d="M4 20c0-4 3.2-6 8-6s8 2 8 6" />
    </svg>
  )
}

export function AppShell({ user, onLogout, topBar, children, onOpenPalette }: Props) {
  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* z-[60] keeps the header above the always-open Details sheet (fixed, z-50, inset-y-0 right-0), which otherwise covers the account/logout controls */}
      <Card size="sm" className="relative z-[60] rounded-none">
        <div className="flex items-center justify-between gap-4 px-4">
          <div className="flex min-w-0 items-center gap-4">
            <h1 className="font-heading text-2xl">Spoilerless</h1>
            {topBar}
          </div>
          {onOpenPalette && (
            <HeaderNavAction
              icon={<Command className="size-4 shrink-0" />}
              label={`${modLabel()}K`}
              ariaLabel="Open command palette"
              active={false}
              onClick={onOpenPalette}
            />
          )}
          {user && (
            <div className="flex items-center gap-3 shrink-0 hover:bg-elevated">
              <span className="hidden sm:inline text-sm text-muted-foreground">
                {user.display_name}
              </span>
              {avatarUrl(user) ? (
                <img
                  src={avatarUrl(user)!}
                  alt={user.display_name}
                  className="size-7 rounded-full object-cover"
                  loading="lazy"
                />
              ) : (
                <div className="size-7 rounded-full bg-muted flex items-center justify-center">
                  <UserIcon />
                </div>
              )}
              {onLogout && (
                <Button variant="ghost" size="sm" onClick={onLogout} type="button">
                  Logout
                </Button>
              )}
            </div>
          )}
        </div>
      </Card>
      <Separator />
      <div className="relative flex-1 overflow-hidden">{children}</div>
    </div>
  )
}
