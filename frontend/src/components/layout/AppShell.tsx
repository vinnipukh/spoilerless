import type { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'

type Props = {
  topBar: ReactNode
  children: ReactNode
}

// Simple top-bar + content-area wrapper (Card/Separator primitives).
// Full layout polish is out of this plan's scope.
export function AppShell({ topBar, children }: Props) {
  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <Card size="sm" className="rounded-none">
        <div className="flex items-center gap-4 px-4">{topBar}</div>
      </Card>
      <Separator />
      <div className="relative flex-1 overflow-hidden">{children}</div>
    </div>
  )
}
