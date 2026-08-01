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

// The chat surface as its own right-side Sheet, independent of the inspector
// panel (which lives on the left). Both can be open at once, so node info and
// the chat are visible simultaneously. ChatPanel stays content-only (its own
// tests render it standalone); this wrapper owns the Sheet chrome only.
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
          'mt-0 max-sm:!inset-x-0 max-sm:!bottom-0 max-sm:!top-auto max-sm:!h-auto max-sm:!w-full max-sm:!border-t max-sm:!border-l-0 max-sm:max-h-[75vh] lg:max-w-[420px] xl:max-w-[480px]',
        )}
      >
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
