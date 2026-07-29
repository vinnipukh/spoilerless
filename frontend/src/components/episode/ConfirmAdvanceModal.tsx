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
  onConfirm: () => void
  onCancel: () => void
}

// Forward-direction copy is locked (02-UI-SPEC.md Copywriting Contract).
// Backward-direction copy is a Claude's-discretion addition (CONTEXT.md
// backward-copy variant) documented alongside the UI-SPEC table, since D-03
// extends confirmation to backward moves and the locked copy is forward-only.
export function ConfirmAdvanceModal({ open, direction, episodeCode, onConfirm, onCancel }: Props) {
  const title = direction === 'forward' ? `Unlock ${episodeCode}?` : `Rewatch ${episodeCode}?`
  const body =
    direction === 'forward'
      ? `You're about to see new characters, events, and relationships from ${episodeCode}. This can't be undone. Continue?`
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
            Yes, unlock episode
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
