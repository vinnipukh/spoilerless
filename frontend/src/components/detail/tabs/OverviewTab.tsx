import { SpoilerGuard } from '@/components/ui/SpoilerGuard'
import type { GraphNode } from '../../../types/graph'

type OverviewTabProps = {
  selectedKind: 'node' | 'edge'
  selectedNode?: GraphNode
  activeClaim?:
    | {
        predicate: string
        claim_type: string
        status: string
        confidence_level: string
      }
    | undefined
  selectedEdge?: { source: string; target: string } | undefined
  nodeLabel: (id: string) => string
  relevantClaimsCount: number
  notesCount: number
  visibleUntilOrder: number | null
  readOnly: boolean
  onOpenRelDialog: () => void
}

// 12-08 (THERMO-P0-04): extracted verbatim from DetailPanel.tsx — the entity
// metadata grid, quick actions, and the claim-less user-edge summary.
export function OverviewTab({
  selectedKind,
  selectedNode,
  activeClaim,
  selectedEdge,
  nodeLabel,
  relevantClaimsCount,
  notesCount,
  visibleUntilOrder,
  readOnly,
  onOpenRelDialog,
}: OverviewTabProps) {
  return (
    <div className="flex flex-col gap-1 overflow-y-auto px-4 pb-4 pt-2">
      {selectedKind === 'node' && selectedNode && (
        /* Fix 1: CSS Grid with fixed label column prevents text collision.
           word-break + overflow-wrap ensure long values wrap cleanly. */
        <dl className="grid grid-cols-[minmax(110px,130px)_1fr] gap-x-3 gap-y-1.5 text-xs">
          <dt className="text-muted-foreground shrink-0">Node Type</dt>
          <dd className="font-medium break-words overflow-wrap-anywhere">{selectedNode.type}</dd>

          <dt className="text-muted-foreground shrink-0">Name</dt>
          <dd className="font-medium break-words overflow-wrap-anywhere">
            <SpoilerGuard
              text={selectedNode.label}
              revealedOrder={selectedNode.visible_from_order}
              currentOrder={visibleUntilOrder}
            />
          </dd>

          <dt className="text-muted-foreground shrink-0">Origin</dt>
          <dd className="break-words overflow-wrap-anywhere">
            {selectedNode.origin === 'user' ? (
              <span className="inline-flex items-center gap-1 rounded border-2 border-dashed border-primary/50 px-1.5 py-0.5 text-xs font-medium">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-3 w-3" aria-hidden="true">
                  <path d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                </svg>
                User
              </span>
            ) : (
              <span className="text-muted-foreground text-xs">{selectedNode.origin}</span>
            )}
          </dd>

          <dt className="text-muted-foreground shrink-0">Revealed in</dt>
          <dd className="font-medium break-words overflow-wrap-anywhere">
            {selectedNode.visible_from_order != null
              ? `Episode #${selectedNode.visible_from_order}`
              : '-'}
          </dd>

          {selectedNode.episode_id && (
            <>
              <dt className="text-muted-foreground shrink-0">Episode ID</dt>
              <dd className="font-medium break-words overflow-wrap-anywhere">{selectedNode.episode_id}</dd>
            </>
          )}

          <dt className="text-muted-foreground shrink-0">Claims count</dt>
          <dd className="font-medium">{relevantClaimsCount}</dd>

          <dt className="text-muted-foreground shrink-0">Notes count</dt>
          <dd className="font-medium">{notesCount}</dd>

          {selectedNode.image_source_url && (
            <>
              <dt className="text-muted-foreground shrink-0">Image source</dt>
              <dd className="font-medium">
                <a
                  href={selectedNode.image_source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline hover:text-primary/80"
                >
                  Source link
                </a>
              </dd>
            </>
          )}
        </dl>
      )}
      {selectedKind === 'node' && selectedNode && !readOnly && (
        <button
          type="button"
          className="mt-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors min-h-[44px]"
          onClick={onOpenRelDialog}
          aria-label="Create relationship"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-4 w-4" aria-hidden="true">
            <path d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244" />
          </svg>
          Create Relationship
        </button>
      )}
      {selectedKind === 'edge' && activeClaim && (
        <dl className="grid grid-cols-[minmax(110px,130px)_1fr] gap-x-3 gap-y-1.5 text-xs">
          <dt className="text-muted-foreground shrink-0">Relationship</dt>
          <dd className="break-words overflow-wrap-anywhere">{activeClaim.predicate}</dd>

          <dt className="text-muted-foreground shrink-0">Claim Type</dt>
          <dd className="break-words overflow-wrap-anywhere">{activeClaim.claim_type}</dd>

          <dt className="text-muted-foreground shrink-0">Status</dt>
          <dd className="break-words overflow-wrap-anywhere">{activeClaim.status}</dd>

          <dt className="text-muted-foreground shrink-0">Confidence</dt>
          <dd className="break-words overflow-wrap-anywhere">{activeClaim.confidence_level}</dd>
        </dl>
      )}
      {selectedKind === 'edge' && !activeClaim && selectedEdge && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2 rounded-md border border-border p-3">
            <span>{nodeLabel(selectedEdge.source)}</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true">
              <path d="M5 12h14"></path>
              <path d="m12 5 7 7-7 7"></path>
            </svg>
            <span>{nodeLabel(selectedEdge.target)}</span>
          </div>
          <p className="text-xs text-muted-foreground">
            User-created relationship (origin: user).
          </p>
        </div>
      )}
    </div>
  )
}
