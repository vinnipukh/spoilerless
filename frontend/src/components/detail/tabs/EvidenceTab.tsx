import { Skeleton } from '@/components/ui/skeleton'

// Reused by CitationChip.tsx via DetailPanel's re-export — see ClaimsTab.
export const EVIDENCE_ACCENT_COLOR = '#FB923C'

type EvidenceTabProps = {
  resolved: boolean
  entries: {
    evidence: {
      id: string
      locator: string
      origin: string
    }
    sourceLabel: string
  }[]
}

// 12-08 (THERMO-P0-04): extracted verbatim from DetailPanel.tsx.
export function EvidenceTab({ resolved, entries }: EvidenceTabProps) {
  return (
    <div className="flex flex-col gap-2 overflow-y-auto px-4 pb-4 pt-2">
      {!resolved && <Skeleton className="h-16 w-full" />}
      {resolved && entries.length === 0 && (
        <p>No evidence recorded for this claim yet</p>
      )}
      {resolved &&
        entries.map(({ evidence, sourceLabel }) => (
          // 08-06+ (product owner): render evidence as CLAIMS-style
          // cards — bold title + muted metadata line, cards grow
          // naturally (no max-h-32 inner scroll; the panel scrolls
          // as a whole, matching the Claims tab).
          <div
            key={evidence.id}
            className="rounded-md border border-border p-2"
            style={{ borderLeft: `4px solid ${EVIDENCE_ACCENT_COLOR}` }}
          >
            <p className="font-medium break-words overflow-wrap-anywhere">
              Source: {sourceLabel} - {evidence.locator}
            </p>
            <p className="text-muted-foreground">{evidence.origin}</p>
          </div>
        ))}
    </div>
  )
}
