import { useCallback, useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { ChatPanel } from './ChatPanel'
import type { Citation } from '../../types/chat'
import type { ChangeSet } from '../../types/changeSet'

type Props = {
  open: boolean
  onClose: () => void
  seriesId: string | null
  seriesTitle: string
  currentEpisodeCode: string | null
  onShowInGraph?: (citation: Citation) => void
  onOpenDetail?: (citation: Citation) => void
  onChangeSetApplied?: (changeSet: ChangeSet) => void
}

const MIN_WIDTH = 320
// Keep at least this much room for the graph / left inspector.
const MIN_SIDEBAR_SPACE = 360
const WIDTH_STORAGE_KEY = 'chatSheetWidth'

function initialWidth(): number | null {
  try {
    const stored = localStorage.getItem(WIDTH_STORAGE_KEY)
    const parsed = stored ? Number.parseInt(stored, 10) : Number.NaN
    return Number.isFinite(parsed) && parsed >= MIN_WIDTH ? parsed : null
  } catch {
    return null
  }
}

// The chat surface as its own right-side Sheet, independent of the inspector
// panel (which lives on the left). Both can be open at once, so node info and
// the chat are visible simultaneously. ChatPanel stays content-only (its own
// tests render it standalone); this wrapper owns the Sheet chrome only.
//
// The panel is resizable: dragging its left edge (the separator handle) pulls
// the chat wider or narrower, clamped to a sane range. The chosen width
// persists across sessions via localStorage; double-click the handle to
// restore the default responsive width.
export function ChatSheet({
  open,
  onClose,
  seriesId,
  seriesTitle,
  currentEpisodeCode,
  onShowInGraph,
  onOpenDetail,
  onChangeSetApplied,
}: Props) {
  const [width, setWidth] = useState<number | null>(initialWidth)
  const [dragging, setDragging] = useState(false)

  const onPointerDown = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    event.preventDefault()
    try {
      event.currentTarget.setPointerCapture(event.pointerId)
    } catch {
      // jsdom does not implement pointer capture — drag still works via the
      // pointer events dispatched directly on the handle.
    }
    setDragging(true)
  }, [])

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!dragging) return
      const maxWidth = Math.max(MIN_WIDTH, window.innerWidth - MIN_SIDEBAR_SPACE)
      const next = Math.min(Math.max(window.innerWidth - event.clientX, MIN_WIDTH), maxWidth)
      setWidth(next)
    },
    [dragging],
  )

  const onPointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      setDragging(false)
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId)
      }
      if (width != null) {
        try {
          localStorage.setItem(WIDTH_STORAGE_KEY, String(width))
        } catch {
          // Storage unavailable (private mode) — resize still works for the
          // session, just doesn't persist.
        }
      }
    },
    [width],
  )

  const resetWidth = useCallback(() => {
    setWidth(null)
    try {
      localStorage.removeItem(WIDTH_STORAGE_KEY)
    } catch {
      // ignore
    }
  }, [])

  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()} modal={false}>
      <SheetContent
        side="right"
        showCloseButton={false}
        // Coexist with the left inspector sheet (see DetailPanel.tsx — same
        // DismissableLayer focus-outside rationale). Close is driven by the
        // ChatLauncher toggle (onClose), never by outside interaction/Escape.
        onInteractOutside={(event) => event.preventDefault()}
        onEscapeKeyDown={(event) => event.preventDefault()}
        className={cn(
          'mt-0 max-sm:!inset-x-0 max-sm:!bottom-0 max-sm:!top-auto max-sm:!h-auto max-sm:!w-full max-sm:!border-t max-sm:!border-l-0 max-sm:max-h-[75vh] lg:max-w-[560px] xl:max-w-[640px]',
        )}
        style={width ? { width, maxWidth: width } : undefined}
      >
        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize chat panel"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onDoubleClick={resetWidth}
          className={cn(
            'absolute inset-y-0 -left-2 z-10 hidden w-4 cursor-ew-resize touch-none items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-ring lg:flex',
            dragging && 'cursor-ew-resize',
          )}
        >
          <span
            className={cn(
              'h-10 w-1 rounded-full bg-border/70 transition-colors',
              dragging ? 'bg-primary' : 'hover:bg-primary/60',
            )}
          />
        </div>
        <SheetHeader>
          <SheetTitle className="truncate">Chat</SheetTitle>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-2 px-4 pb-4 text-sm">
          <ChatPanel
            seriesId={seriesId}
            seriesTitle={seriesTitle}
            currentEpisodeCode={currentEpisodeCode}
            onShowInGraph={onShowInGraph}
            onOpenDetail={onOpenDetail}
            onApplied={onChangeSetApplied}
          />
        </div>
      </SheetContent>
    </Sheet>
  )
}
