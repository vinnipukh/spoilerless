// 10-07 (D-28/D-41): the Evidence Chain — the layered Claim → Evidence →
// Source read for the Evidence tab. Claims/Evidence/Sources stay in the
// Inspector where permitted; nothing here mounts on the default Episode
// Overview. "Show in graph" is ALWAYS an explicit user action — the chain
// never pushes selection into the main story graph on its own.
//
// Sanitized error states only: the caller passes a sanitized message; this
// component renders no internal backend error text.

import type { GraphResponse } from '../../types/graph'

type Props = {
  graph: GraphResponse
  focusIds: string[]
  /** Sanitized user-facing error; internal backend text never reaches here. */
  error?: string | null
  onShowInGraph: (nodeId: string) => void
  onRetry?: () => void
}

export function EvidenceChain({
  graph,
  focusIds,
  error,
  onShowInGraph,
  onRetry,
}: Props) {
  const focusSet = new Set(focusIds)
  const claims = graph.claims.filter(
    (claim) => focusSet.has(claim.id) || focusSet.has(claim.subject_id) || focusSet.has(claim.object_id),
  )
  const evidence = graph.evidence.filter((entry) =>
    claims.some((claim) => claim.evidence_ids.includes(entry.id)),
  )
  const sources = graph.sources.filter((source) =>
    evidence.some((entry) => entry.source_id === source.id),
  )

  return (
    <section
      aria-label="Evidence Chain"
      className="flex flex-col gap-4 rounded-lg border border-border bg-popover p-4 text-sm text-foreground"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-foreground">Evidence Chain</h3>
        <p className="text-xs text-muted-foreground">
          Claim → Evidence → Source
        </p>
      </div>

      {error ? (
        <p role="status" className="text-muted-foreground">
          {error}
        </p>
      ) : (
        <ol className="flex list-none flex-col gap-3">
          {claims.map((claim) => (
            <li key={claim.id} className="rounded-md border border-border bg-card p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="font-medium text-foreground">{claim.label}</span>
                <button
                  type="button"
                  aria-label={`Show ${claim.label} in graph`}
                  onClick={() => onShowInGraph(claim.id)}
                  className="inline-flex min-h-[44px] shrink-0 items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Show in graph
                </button>
              </div>
              <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-muted-foreground">
                {evidence
                  .filter((entry) => claim.evidence_ids.includes(entry.id))
                  .map((entry) => (
                    <li key={entry.id}>
                      <span className="text-foreground">{entry.text}</span>
                      {(() => {
                        const source = sources.find((s) => s.id === entry.source_id)
                        return source ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            — {source.label}
                          </span>
                        ) : null
                      })()}
                    </li>
                  ))}
              </ul>
            </li>
          ))}
          {claims.length === 0 && (
            <li className="text-muted-foreground">
              No claims are visible at the current boundary.
            </li>
          )}
        </ol>
      )}

      {error && onRetry && (
        <button
          type="button"
          aria-label="Retry Evidence Chain"
          onClick={onRetry}
          className="inline-flex min-h-[44px] items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Retry
        </button>
      )}
    </section>
  )
}
