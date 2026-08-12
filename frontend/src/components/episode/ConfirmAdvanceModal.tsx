import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import type { WatchProgressDirection } from '../../hooks/useWatchProgress'

type Props = {
  open: boolean
  direction: WatchProgressDirection
  episodeCode: string
  // The numeric episode order being unlocked — the forward copy states
  // "Episodes 1 through N will be considered watched" (D-06).
  episodeOrder?: number
  // Visitor (read-only) mode: the modal is a pure spoiler warning — the
  // "considered watched / can't be undone" copy is wrong for a visitor
  // (nothing persists), so forward moves get spoiler copy instead
  // (08-12: restore notification for visitor forward navigation).
  visitor?: boolean
  onConfirm: () => void
  onCancel: () => void
}

// Forward-direction copy is locked (02-UI-SPEC.md Copywriting Contract,
// D-06): unlocking Episode N marks Episodes 1 through N as watched.
// Backward-direction copy is a Claude's-discretion addition (CONTEXT.md
// backward-copy variant) — note the 07-03 view-only model means backward
// selections no longer open this modal (PROG-01); the branch is retained
// for direct-render compatibility.
export function ConfirmAdvanceModal({ open, direction, episodeCode, episodeOrder, visitor, onConfirm, onCancel }: Props) {
  const title = visitor
    ? `View ${episodeCode}?`
    : direction === 'forward'
      ? `Unlock ${episodeCode}?`
      : `Rewatch ${episodeCode}?`
  const body = visitor
    ? `You're about to view ${episodeCode}. Content beyond your current progress may contain spoilers. Your progress isn't saved in visitor mode. Continue?`
    : direction === 'forward'
      ? `Unlocking ${episodeCode} means Episodes 1 through ${episodeOrder ?? episodeCode} will be considered watched. This can't be undone. Continue?`
      : `You're about to move your watch progress back to ${episodeCode}. Continue?`

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onCancel()
      }}
    >
      <DialogContent className="border-warning/40">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{body}</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            className="bg-warning text-warning-foreground hover:bg-warning/80"
          >
            {visitor ? 'View episode' : 'Yes, unlock episode'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
