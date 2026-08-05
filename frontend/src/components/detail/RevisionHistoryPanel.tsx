import { useCallback, useRef, useState } from 'react'
import { revertRevision } from '../../api/revisions'
import { useRevisions } from '../../hooks/useRevisions'
import type { RevisionResponse, RevisionAction } from '../../types/revision'
import { Skeleton } from '../ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'

type Props = {
  seriesId: string | null
  visibleUntilOrder: number | null
  resourceType: string | undefined
  resourceId: string | undefined
  onRefetchGraph?: () => void
}

// ── Action badge color map ──
const ACTION_STYLE: Record<RevisionAction, { bg: string; text: string; label: string }> = {
  Created:   { bg: 'bg-emerald-500/15', text: 'text-emerald-600 dark:text-emerald-400', label: 'Created' },
  Updated:   { bg: 'bg-amber-500/15',   text: 'text-amber-600 dark:text-amber-400',   label: 'Updated' },
  Deleted:   { bg: 'bg-red-500/15',     text: 'text-red-600 dark:text-red-400',       label: 'Deleted' },
  Reverted:  { bg: 'bg-blue-500/15',    text: 'text-blue-600 dark:text-blue-400',     label: 'Reverted' },
}

function formatUTCDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
    timeZone: 'UTC',
  }) + ' UTC'
}

export type DiffDetail = {
  field: string
  before: string
  after: string
}

// ── Diff summary: show which fields changed with before/after values ──
function diffFields(
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
): DiffDetail[] {
  if (!before && !after) return []
  if (!before && after) {
    return Object.entries(after).map(([k, v]) => ({
      field: k,
      before: '(none)',
      after: String(v ?? ''),
    }))
  }
  if (before && !after) {
    return Object.entries(before).map(([k, v]) => ({
      field: k,
      before: String(v ?? ''),
      after: '(none)',
    }))
  }
  const allKeys = new Set([...Object.keys(before!), ...Object.keys(after!)])
  const details: DiffDetail[] = []
  for (const k of allKeys) {
    const bv = JSON.stringify(before![k])
    const av = JSON.stringify(after![k])
    if (bv !== av) {
      details.push({
        field: k,
        before: String(before![k] ?? '(none)'),
        after: String(after![k] ?? '(none)'),
      })
    }
  }
  return details
}

// ── Revert confirm dialog ──
function RevertConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  reverting,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  onConfirm: () => void
  reverting: boolean
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Revert this change?</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          This will restore the previous state and create a new Reverted revision.
          The existing history is preserved.
        </p>
        <div className="flex items-center justify-end gap-2 pt-2">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors min-h-[44px] disabled:opacity-50"
            onClick={() => onOpenChange(false)}
            disabled={reverting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors min-h-[44px] disabled:opacity-50"
            onClick={onConfirm}
            disabled={reverting}
          >
            {reverting ? 'Reverting…' : 'Revert'}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ── Single revision row ──
function RevisionItem({
  revision,
  onRevert,
  revertingId,
}: {
  revision: RevisionResponse
  onRevert: (rev: RevisionResponse) => void
  revertingId: string | null
}) {
  const style = ACTION_STYLE[revision.action]
  const changed = diffFields(revision.before, revision.after)
  const isRevertable = revision.action === 'Updated' || revision.action === 'Deleted'

  return (
    <div className="rounded-md border border-border p-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${style.bg} ${style.text}`}>
            {style.label}
          </span>
          <span className="text-[11px] text-muted-foreground">
            {formatUTCDate(revision.created_at)}
          </span>
        </div>
        {isRevertable && (
          <button
            type="button"
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium text-foreground hover:bg-muted transition-colors disabled:opacity-50 min-h-[32px]"
            onClick={() => onRevert(revision)}
            disabled={revertingId === revision.id}
            aria-label={`Revert ${revision.action.toLowerCase()} revision`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-3.5 w-3.5" aria-hidden="true">
              <path d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
            </svg>
            {revertingId === revision.id ? 'Reverting…' : 'Revert'}
          </button>
        )}
      </div>
      {revision.resource_type !== 'Unknown' && (
        <p className="mt-1 text-[11px] text-muted-foreground">
          {revision.resource_type} · {revision.resource_id.slice(0, 24)}…
        </p>
      )}
      {changed.length > 0 && (
        <div className="mt-1.5 space-y-1">
          {changed.map((diff, i) => (
            <div key={i} className="rounded bg-muted/60 p-1.5 text-xs font-mono">
              <span className="font-medium text-foreground">{diff.field}:</span>{' '}
              <span className="text-muted-foreground">Before: {diff.before}</span>{' '}
              <span className="text-foreground font-semibold">→ After: {diff.after}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Client-side filter: check if a revision involves the selected resource ──
function isRevisionRelatedTo(
  revision: RevisionResponse,
  resourceType: string | undefined,
  resourceId: string | undefined,
): boolean {
  if (!resourceId) return true  // no filter — show all
  // For claims: exact resource match (already filtered server-side)
  if (resourceType === 'Claim') return true
  // For nodes: show revisions where the resource IS the node, or where
  // the node appears as target/source in the before/after snapshot
  if (revision.resource_id === resourceId) return true
  const snapshots = [revision.before, revision.after].filter(Boolean) as Record<string, unknown>[]
  for (const snap of snapshots) {
    if (snap.target_id === resourceId) return true
    if (snap.source === resourceId) return true
    if (snap.target === resourceId) return true
  }
  return false
}

// ── Main panel ──
export function RevisionHistoryPanel({ seriesId, visibleUntilOrder, resourceType, resourceId, onRefetchGraph }: Props) {
  // For claim edges, use exact resource filter (fast path). For nodes,
  // fetch all series revisions and client-side filter (catches notes
  // targeting this node, custom relationships involving this node, etc.).
  const isExactMatch = resourceType === 'Claim'
  const revisionsState = useRevisions({
    seriesId,
    visibleUntilOrder,
    resourceType: isExactMatch ? resourceType : undefined,
    resourceId: isExactMatch ? resourceId : undefined,
  })

  // Client-side filter for node history
  const relatedRevisions = !isExactMatch && revisionsState.status === 'success'
    ? revisionsState.data.filter((rev) => isRevisionRelatedTo(rev, resourceType, resourceId))
    : revisionsState.status === 'success' ? revisionsState.data : []
  const [revertingId, setRevertingId] = useState<string | null>(null)
  const [confirmRev, setConfirmRev] = useState<RevisionResponse | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const showToast = useCallback((msg: string) => {
    setToast(msg)
    clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3000)
  }, [])

  const handleRevertConfirm = useCallback(async () => {
    if (!confirmRev || !seriesId || visibleUntilOrder == null) return
    const revId = confirmRev.id
    setRevertingId(revId)
    setConfirmRev(null)
    try {
      await revertRevision(seriesId, revId, visibleUntilOrder)
      showToast('Revision reverted successfully')
      revisionsState.refetch()
      // Delay graph refetch so the toast is visible before the panel
      // re-renders (graph goes through loading → success transition)
      setTimeout(() => onRefetchGraph?.(), 800)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to revert revision'
      showToast(msg)
    } finally {
      setRevertingId(null)
    }
  }, [confirmRev, seriesId, visibleUntilOrder, revisionsState, onRefetchGraph, showToast])

  // ── Loading state ──
  if (revisionsState.status === 'loading') {
    return (
      <div className="flex flex-col gap-2 pt-2">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-3/4" />
      </div>
    )
  }

  // ── Error state ──
  if (revisionsState.status === 'error') {
    return (
      <div className="rounded-md border border-destructive/20 bg-destructive/5 p-3 text-xs text-destructive mt-2">
        Failed to load revision history.
      </div>
    )
  }

  // ── Empty state ──
  if (revisionsState.status === 'success' && relatedRevisions.length === 0) {
    return (
      <p className="text-xs text-muted-foreground py-2">
        {resourceType === 'Claim'
          ? 'No revision history for this claim.'
          : 'No revision history for this item. Create or edit notes, custom nodes, or relationships to see changes here.'}
      </p>
    )
  }

  // ── Revision list ──
  return (
    <div className="flex flex-col gap-2 pt-2">
      {toast && (
        <div className="rounded-md bg-muted px-3 py-2 text-xs text-foreground" role="alert">
          {toast}
        </div>
      )}

      <div className="flex flex-col gap-2 max-h-[40vh] overflow-y-auto">
        {relatedRevisions.map((rev) => (
          <RevisionItem
            key={rev.id}
            revision={rev}
            onRevert={setConfirmRev}
            revertingId={revertingId}
          />
        ))}
      </div>

      <RevertConfirmDialog
        open={confirmRev !== null}
        onOpenChange={(v) => { if (!v) setConfirmRev(null) }}
        onConfirm={handleRevertConfirm}
        reverting={revertingId !== null && revertingId === confirmRev?.id}
      />
    </div>
  )
}
