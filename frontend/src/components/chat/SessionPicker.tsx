import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Skeleton } from '@/components/ui/skeleton'
import type { ChatSession } from '../../types/chat'

type Props = {
  sessions: ChatSession[]
  activeSessionId: string | null
  loading?: boolean
  onSelect: (sessionId: string) => void
  onNewConversation: () => void
  onDelete: (sessionId: string) => void
}

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const diffMin = Math.round(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.round(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return `${Math.round(diffHr / 24)}d ago`
}

// Compact session selector (06-UI-SPEC.md "Session picker (compact, not a
// full session-list page)"): reuses the existing shadcn Select (current
// session title, opens to list past sessions newest-first) plus a "New
// conversation" icon button. Each row's delete icon mirrors NoteItem's
// existing hover/focus-reveal micro-pattern in DetailPanel.tsx; the actual
// destructive confirmation is a Dialog matching ConfirmAdvanceModal's
// Cancel/Confirm shape, per the Copywriting Contract's "Delete session" row.
export function SessionPicker({
  sessions,
  activeSessionId,
  loading,
  onSelect,
  onNewConversation,
  onDelete,
}: Props) {
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const pendingDeleteSession = sessions.find((session) => session.id === pendingDeleteId) ?? null

  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <Skeleton className="h-8 flex-1" />
        <Skeleton className="h-8 w-8 shrink-0" />
      </div>
    )
  }

  const sortedSessions = [...sessions].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  )
  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? null

  return (
    <div className="flex flex-col gap-2">
      {sessions.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-3 text-center">
          <p className="text-sm font-medium">No conversations yet</p>
          <p className="text-xs text-muted-foreground">
            Ask a question below to start your first conversation.
          </p>
        </div>
      ) : (
        <Select value={activeSessionId ?? ''} onValueChange={onSelect}>
          <SelectTrigger aria-label="Select a conversation" className="w-full min-w-0" size="sm">
            {/* Explicit children (rather than the shadcn default bare
                <SelectValue />) opt out of Radix's "mirror the selected
                SelectItemText into the trigger" portal behavior — that
                portal would otherwise clone this row's whole children
                (including the hover-reveal delete button) into the
                trigger, duplicating it and leaving an inert,
                pointer-events:none copy behind. */}
            <SelectValue placeholder="Select a conversation">
              {activeSession ? activeSession.title || 'Untitled conversation' : undefined}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {sortedSessions.map((session) => (
              <SelectItem key={session.id} value={session.id}>
                <span className="group flex w-full items-center justify-between gap-2">
                  <span className="truncate">{session.title || 'Untitled conversation'}</span>
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <span className="text-[0.7rem]">{relativeTime(session.updated_at)}</span>
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label="Delete conversation"
                      className="opacity-0 transition-opacity group-hover:opacity-100 hover:text-destructive focus:opacity-100"
                      onPointerDown={(event) => event.stopPropagation()}
                      onPointerUp={(event) => {
                        // Radix Select commits the item selection on
                        // `pointerup` for mouse input (not `click`) — this
                        // must be intercepted here too, or clicking the
                        // delete icon also selects the row underneath it.
                        event.stopPropagation()
                      }}
                      onClick={(event) => {
                        event.stopPropagation()
                        setPendingDeleteId(session.id)
                      }}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.stopPropagation()
                          event.preventDefault()
                          setPendingDeleteId(session.id)
                        }
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    </span>
                  </span>
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      <button
        type="button"
        aria-label="Start new conversation"
        onClick={onNewConversation}
        className="inline-flex min-h-[44px] items-center justify-center gap-1.5 self-start rounded-md bg-secondary px-3 py-1.5 text-xs font-medium text-secondary-foreground transition-colors hover:bg-secondary/80"
      >
        <Plus className="h-4 w-4" aria-hidden="true" />
        New conversation
      </button>

      <Dialog
        open={pendingDeleteId != null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null)
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete this conversation?</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            This removes {pendingDeleteSession ? `"${pendingDeleteSession.title || 'Untitled conversation'}"` : 'it'} from
            your conversation list. This can&apos;t be undone.
          </p>
          <DialogFooter>
            <button
              type="button"
              className="inline-flex min-h-[44px] items-center justify-center rounded-md border border-border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-muted"
              onClick={() => setPendingDeleteId(null)}
            >
              Keep conversation
            </button>
            <button
              type="button"
              className="inline-flex min-h-[44px] items-center justify-center rounded-md bg-destructive/10 px-3 py-1.5 text-xs font-medium text-destructive transition-colors hover:bg-destructive/20"
              onClick={() => {
                if (pendingDeleteId) onDelete(pendingDeleteId)
                setPendingDeleteId(null)
              }}
            >
              Delete
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
