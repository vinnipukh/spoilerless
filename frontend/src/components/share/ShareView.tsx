import { useEffect, useState } from 'react'
import { ShieldAlert } from 'lucide-react'
import { getShareGraph } from '@/api/share'
import type { GraphResponse } from '@/types/graph'
import { GraphCanvas } from '@/components/graph/GraphCanvas'

type Props = {
  token: string
}

export function ShareView({ token }: Props) {
  const [graph, setGraph] = useState<GraphResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    getShareGraph(token)
      .then((res) => {
        if (!cancelled) {
          setGraph(res)
          setError(null)
        }
      })

      .catch((err) => {
        if (!cancelled) {
          setError(err.message || 'This snapshot link has expired or has been revoked.')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [token])

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Read-only minimal header */}
      <header className="flex h-14 items-center justify-between bg-card px-4 ring-1 ring-border z-10">
        <div className="flex items-center gap-3">
          <span className="font-heading text-2xl font-semibold">Spoilerless</span>
          <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
            Snapshot
          </span>
        </div>
        <a href="/" className="text-sm text-accent hover:underline">
          Open Spoilerless
        </a>
      </header>

      {/* Main body */}
      <main className="relative flex-1 overflow-hidden">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">Loading snapshot...</p>
          </div>
        ) : error || !graph ? (
          <div className="flex h-full items-center justify-center p-4">
            <div className="max-w-md w-full rounded-lg bg-card p-6 text-center space-y-4 ring-1 ring-border shadow-md">
              <ShieldAlert className="h-8 w-8 text-muted-foreground mx-auto" />
              <h2 className="font-heading text-xl font-semibold">
                This snapshot link has expired or has been revoked.
              </h2>
              <p className="text-sm text-muted-foreground">
                Ask the person who shared it for a fresh link.
              </p>
              <div>
                <a
                  href="/"
                  className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors min-h-[44px]"
                >
                  Open Spoilerless
                </a>
              </div>
            </div>
          </div>
        ) : (
          <div className="relative h-full w-full">
            <GraphCanvas
              graph={graph}
              seriesId={graph.series.id}
              episodes={[]}
              onSelect={() => {}}
              readOnly={true}
            />
            {/* Footer strip */}
            <div className="absolute bottom-0 left-0 right-0 z-20 bg-card/80 backdrop-blur px-4 py-2 text-xs text-muted-foreground border-t border-border flex items-center justify-between">
              <span>
                Snapshot created · visible through episode {graph.visible_until_order}
              </span>
              <span>Read-only snapshot</span>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
