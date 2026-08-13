// 10-07 (D-27/D-44): the temporary Answer Graph surface. Visibly labelled
// as temporary; closing it restores the exact prior scene through the
// snapshot captured by OPEN_TEMPORARY (reducer CLOSE_TEMPORARY). This
// component is presentation-only — it renders the safe focus ids the scene
// reducer already accepted (server-safe charset) and never derives data.
//
// Sanitized error/empty states: the caller passes a sanitized message only;
// internal backend error text is never rendered here.

type Props = {
  /** Server-safe focus node ids (already validated by the scene reducer). */
  nodeIds: string[]
  /** Sanitized, user-facing message; internal backend errors never reach here. */
  error?: string | null
  onClose: () => void
  onRetry?: () => void
}

export function AnswerGraph({ nodeIds, error, onClose, onRetry }: Props) {
  return (
    <section
      aria-label="Answer Graph"
      className="flex flex-col gap-3 rounded-lg border border-border bg-popover p-4 text-sm text-foreground"
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-base font-semibold text-foreground">Answer Graph</h3>
        <button
          type="button"
          aria-label="Close Answer Graph"
          onClick={onClose}
          className="inline-flex min-h-[44px] items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Close
        </button>
      </div>

      {error ? (
        <p role="status" className="text-muted-foreground">
          {error}
        </p>
      ) : nodeIds.length === 0 ? (
        <p className="text-muted-foreground">
          No focus resources are visible at the current boundary.
        </p>
      ) : (
        <>
          <p className="text-muted-foreground">
            Temporary focus from this answer. Close to restore your scene.
          </p>
          <ul className="list-disc pl-5 text-foreground" aria-label="Focused resources">
            {nodeIds.map((id) => (
              <li key={id}>{id}</li>
            ))}
          </ul>
        </>
      )}

      {error && onRetry && (
        <button
          type="button"
          aria-label="Retry Answer Graph"
          onClick={onRetry}
          className="inline-flex min-h-[44px] items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Retry
        </button>
      )}
    </section>
  )
}
