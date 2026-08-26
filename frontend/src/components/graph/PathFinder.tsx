import { useEffect, useRef, useState } from 'react'
import type cytoscape from 'cytoscape'
import { RotateCcw, X } from 'lucide-react'
import { findPath } from '@/api/graph'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { PathResponse } from '@/types/graph'

// FEAT-06 (09-11) path finder (UI-SPEC §10.8): a two-node selection mode.
// First pick marks .path-source, second pick marks .path-target, then POST
// /graph/path (server-resolved boundary); on a found path apply .on-path to
// the returned elements + .faded to everything else and cy.fit(path, 48).
// No path → the locked Alert copy verbatim. Clear/Esc exits mode. The mode
// never conflicts with tap-to-select: GraphCanvas routes node taps through
// `registerPickHandler` while the mode is active.

export type PathPick = { id: string; label: string }

type Props = {
  cyRef: React.RefObject<cytoscape.Core | null>
  seriesId: string | null
  onExit: () => void
  registerPickHandler: (handler: ((pick: PathPick) => void) | null) => void
}

type PathMode =
  | { status: 'pick-source' }
  | { status: 'pick-target' }
  | { status: 'loading' }
  | { status: 'result'; result: PathResponse }
  | { status: 'error' }

export function PathFinder({ cyRef, seriesId, onExit, registerPickHandler }: Props) {
  const [mode, setMode] = useState<PathMode>({ status: 'pick-source' })
  const [source, setSource] = useState<PathPick | null>(null)
  const [target, setTarget] = useState<PathPick | null>(null)
  const mountedRef = useRef(true)
  // Latest handlePick, so the registered handler never closes over stale
  // mode/source state.
  const handlePickRef = useRef<(pick: PathPick) => void>(() => {})

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.key === 'Escape') handleExit()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handlePick(pick: PathPick) {
    if (mode.status === 'pick-source') {
      setSource(pick)
      setMode({ status: 'pick-target' })
      return
    }
    if (mode.status === 'pick-target' && source) {
      setTarget(pick)
      void runPath(source, pick)
    }
  }
  handlePickRef.current = handlePick

  // Register our pick handler with GraphCanvas while mounted.
  useEffect(() => {
    registerPickHandler((pick) => handlePickRef.current(pick))
    return () => registerPickHandler(null)
  }, [registerPickHandler])

  async function runPath(from: PathPick, to: PathPick) {
    if (!seriesId) return
    setMode({ status: 'loading' })
    try {
      const result = await findPath(seriesId, {
        source_entity_id: from.id,
        target_entity_id: to.id,
        max_hops: 4,
      })
      if (!mountedRef.current) return
      setMode({ status: 'result', result })
      applyPathClasses(result)
    } catch {
      if (!mountedRef.current) return
      setMode({ status: 'error' })
    }
  }

  function applyPathClasses(result: PathResponse) {
    const cy = cyRef.current
    if (!cy || typeof cy.getElementById !== 'function' || typeof cy.collection !== 'function') {
      return
    }
    cy.elements().removeClass('on-path path-source path-target faded')
    if (!result.found) return

    const highlighted = cy.collection()
    for (const id of result.path) {
      const element = cy.getElementById(id)
      if (element && element.length > 0) {
        element.addClass('on-path')
        highlighted.merge(element)
      }
    }
    for (const id of result.edges) {
      const edge = cy.getElementById(id)
      if (edge && edge.length > 0) {
        edge.addClass('on-path')
        highlighted.merge(edge)
      }
    }
    if (source) {
      const sourceEl = cy.getElementById(source.id)
      if (sourceEl && sourceEl.length > 0) sourceEl.addClass('path-source')
    }
    if (target) {
      const targetEl = cy.getElementById(target.id)
      if (targetEl && targetEl.length > 0) targetEl.addClass('path-target')
    }
    cy.elements().difference(highlighted).addClass('faded')
    if (typeof cy.fit === 'function' && highlighted.length > 0) cy.fit(highlighted, 48)
  }

  function handleClear() {
    const cy = cyRef.current
    if (cy && typeof cy.elements === 'function') {
      cy.elements().removeClass('on-path path-source path-target faded')
    }
    setSource(null)
    setTarget(null)
    setMode({ status: 'pick-source' })
  }

  function handleExit() {
    handleClear()
    onExit()
  }

  const chipLabel = (() => {
    switch (mode.status) {
      case 'pick-source':
        return 'Select first node…'
      case 'pick-target':
        return 'Select second node…'
      case 'loading':
        return 'Finding path…'
      case 'result':
        if (!mode.result.found) return 'No path found'
        return `${mode.result.hops} hops · ${mode.result.path.length} nodes`
      case 'error':
        return 'Path request failed'
    }
  })()

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-[70] flex justify-center px-4">
      <div className="pointer-events-auto flex items-center gap-2 rounded-md bg-card px-3 py-2 shadow-sm ring-1 ring-border">
        <span className="text-sm font-medium">{chipLabel}</span>
        {(mode.status === 'result' || mode.status === 'error') && (
          <button
            type="button"
            aria-label="Clear path"
            title="Clear path selection"
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={handleClear}
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
        <button
          type="button"
          aria-label="Exit path finder"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onClick={handleExit}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      {mode.status === 'error' && (
        <div className="pointer-events-auto absolute top-14">
          <Alert variant="destructive">
            <AlertDescription>
              Could not find a path between those nodes. Try different nodes or a wider boundary.
            </AlertDescription>
          </Alert>
        </div>
      )}
    </div>
  )
}
