// Loading/error/empty overlay states for the graph canvas region. Each of
// these fully REPLACES the Cytoscape canvas for its render (never layers
// alongside it) per 02-UI-SPEC.md's UI Considerations table (loading/error/
// empty rows) and this plan's `GraphCanvas to GraphStatus` key_link.

import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

// `/api/graph` in-flight overlay (UI-SPEC UI Considerations - loading/canvas+selector).
export function GraphLoadingState() {
  return (
    <div className="flex h-full flex-col gap-4 p-6" data-testid="graph-loading-state">
      <Skeleton className="h-6 w-40" />
      <Skeleton className="h-6 w-64" />
      <Skeleton className="flex-1 w-full" />
    </div>
  )
}

type GraphErrorStateProps = {
  onRetry: () => void
}

// `/api/graph` fetch failure (UI-SPEC UI Considerations - error/canvas+selector).
// Copy is locked verbatim in 02-UI-SPEC.md's Copywriting Contract.
export function GraphErrorState({ onRetry }: GraphErrorStateProps) {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <Alert variant="destructive" className="max-w-md">
        <AlertTitle>Couldn&apos;t load the graph. Check the backend connection and retry.</AlertTitle>
        <AlertDescription>
          <Button onClick={onRetry} size="sm" className="mt-2 w-fit" variant="outline">
            Retry
          </Button>
        </AlertDescription>
      </Alert>
    </div>
  )
}

// Zero-node graph response (UI-SPEC UI Considerations - empty). No numeric
// node-count copy is rendered here — the locked heading/body is the entire
// empty-state contract (02-02-PLAN.md must_haves truth).
export function GraphEmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
      <h2 className="text-lg font-semibold">Nothing revealed yet</h2>
      <p className="text-sm text-muted-foreground">
        Advance your watch progress to unlock the story.
      </p>
    </div>
  )
}
