import { Skeleton } from '@/components/ui/skeleton'
import { SpoilerGuard } from '@/components/ui/SpoilerGuard'

// Reused by CitationChip.tsx (06-09-PLAN.md Task 2) so claim/evidence citation
// accents are never redefined as a second, drifting hex literal — the exact
// same visual meaning ("this points at that Claims/Evidence card") applies to
// a citation chip as it does to these Claims-tab accent bars.
// 12-08: canonical home moved here from DetailPanel.tsx; DetailPanel keeps a
// re-export for CitationChip's existing import path.
export const CLAIM_ACCENT_COLOR = '#D946EF'

type ClaimsTabProps = {
  resolved: boolean
  claims: {
    id: string
    label: string
    visible_from_order: number
    predicate: string
    status: string
    confidence_level: string
  }[]
  visibleUntilOrder: number | null
}

// 12-08 (THERMO-P0-04): extracted verbatim from DetailPanel.tsx.
export function ClaimsTab({ resolved, claims, visibleUntilOrder }: ClaimsTabProps) {
  return (
    <div className="flex flex-col gap-2 overflow-y-auto px-4 pb-4 pt-2">
      {!resolved && <Skeleton className="h-16 w-full" />}
      {resolved && claims.length === 0 && (
        <p>No claims recorded for this node yet</p>
      )}
      {resolved &&
        claims.map((claim) => (
          <div
            key={claim.id}
            className="rounded-md border border-border p-2"
            style={{ borderLeft: `4px solid ${CLAIM_ACCENT_COLOR}` }}
          >
            <p className="font-medium break-words overflow-wrap-anywhere">
              <SpoilerGuard
                text={claim.label}
                revealedOrder={claim.visible_from_order}
                currentOrder={visibleUntilOrder}
              />
            </p>
            <p className="text-muted-foreground">
              {claim.predicate} · {claim.status} · {claim.confidence_level}
            </p>
          </div>
        ))}
    </div>
  )
}
