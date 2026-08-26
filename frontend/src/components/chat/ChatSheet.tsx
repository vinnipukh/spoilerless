import { useCallback, useState } from 'react'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { cn } from '@/lib/utils'
import { ChatPanel } from './ChatPanel'
import type { Citation } from '../../types/chat'
import type { ChangeSet } from '../../types/changeSet'

import { ErrorBoundary } from '../ErrorBoundary'
import { ResizableRail } from '../layout/ResizableRail'

type Props = {
  open: boolean
  onClose: () => void
  seriesId: string | null
  seriesTitle: string
  currentEpisodeCode: string | null
  viewAsOfOrder?: number | null
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
// The panel is resizable via the shared ResizableRail primitive (12-08,
// THERMO-P2-05): dragging its left edge pulls the chat wider or narrower,
// clamped to a sane range. Width persists across sessions; double-click the
// handle restores the default responsive width. Arrow keys nudge ±16px.
export function ChatSheet({
  open,
  onClose,
  seriesId,
  seriesTitle,
  currentEpisodeCode,
  viewAsOfOrder,
  onShowInGraph,
  onOpenDetail,
  onChangeSetApplied,
}: Props) {
  const [width, setWidth] = useState<number | null>(initialWidth)

  const clampWidth = useCallback((nextWidth: number | null) => {
    if (nextWidth == null) return null
    const maxWidth = Math.max(MIN_WIDTH, window.innerWidth - MIN_SIDEBAR_SPACE)
    return Math.min(Math.max(nextWidth, MIN_WIDTH), maxWidth)
  }, [])

  const handleResizeFromPointer = useCallback(
    (_dimension: number | null, point: { x: number; y: number }) => {
      setWidth(clampWidth(window.innerWidth - point.x))
    },
    [clampWidth],
  )

  const persistWidth = useCallback(() => {
    setWidth((current) => {
      if (current != null) {
        try {
          localStorage.setItem(WIDTH_STORAGE_KEY, String(current))
        } catch {
          // Storage unavailable (private mode) — resize still works for the
          // session, just doesn't persist.
        }
      }
      return current
    })
  }, [])

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
        <ResizableRail
          label="Resize chat panel"
          orientation="vertical"
          onResize={handleResizeFromPointer}
          onResizeEnd={persistWidth}
          onDoubleClick={resetWidth}
          className="hidden lg:flex"
        />
        <SheetHeader>
          <SheetTitle className="truncate">Chat</SheetTitle>
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-2 px-4 pb-4 text-sm">
          <ErrorBoundary fallbackTitle="Chat unavailable" fallbackMessage="An error occurred rendering the chat panel.">
            <ChatPanel
              seriesId={seriesId}
              seriesTitle={seriesTitle}
              currentEpisodeCode={currentEpisodeCode}
              viewAsOfOrder={viewAsOfOrder}
              onShowInGraph={onShowInGraph}
              onOpenDetail={onOpenDetail}
              onApplied={onChangeSetApplied}
            />
          </ErrorBoundary>
        </div>
      </SheetContent>
    </Sheet>
  )
}
