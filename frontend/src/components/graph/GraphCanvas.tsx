import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import CytoscapeComponent from 'react-cytoscapejs'
import type { GraphResponse } from '../../types/graph'
import type { EpisodeResponse } from '../../types/series'
import { graphToElements } from './graphElements'
import { buildGraphStylesheet } from './graphStylesheet'
import { TooltipProvider } from '@/components/ui/tooltip'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { GraphLegend } from './GraphLegend'
import { GraphControls } from './GraphControls'
import { createCustomNode } from '../../api/userContent'
import type { CustomNodeType } from '../../types/userContent'

console.log('[GC-MODULE] GraphCanvas module loaded')

// Reduced motion preference detected at module scope (no DOM access during SSR).
// The user's preference is captured once on first render — changing it mid-session
// would require a React state/hook, but <CytoscapeComponent> doesn't re-render on
// stylesheet changes anyway (it captures the ref once), so a static capture is
// appropriate.
const prefersReducedMotion =
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// Registered once at module scope. `layoutName` defaults to 'cose-bilkent'
// (D-04's primary layout) and only falls back to the built-in 'cose' if the
// extension actually fails to register — not a preemptive dual-path switch
// (CONTEXT.md D-04 discretion note: only fall back on an actual caught
// build/runtime failure).
let layoutName: 'cose-bilkent' | 'cose' = 'cose-bilkent'
try {
  cytoscape.use(coseBilkent)
} catch (error) {
  console.error(
    'cytoscape-cose-bilkent failed to register; falling back to the built-in cose layout',
    error,
  )
  layoutName = 'cose'
}

function layoutOptionsFor(name: 'cose-bilkent' | 'cose') {
  const common = {
    fit: true,
    padding: 48,
    nodeRepulsion: 8000,
    idealEdgeLength: 100,
    edgeElasticity: 0.45,
    animate: prefersReducedMotion ? false : ('end' as const),
  }
  return name === 'cose-bilkent'
    ? { name: 'cose-bilkent', nodeDimensionsIncludeLabels: true, ...common }
    : { name: 'cose', ...common }
}

// react-cytoscapejs's own declarative `layout` prop only re-applies a layout
// when the prop's shallow-compared field values change (never true here,
// since every render passes literal-equal field values) — so it never
// re-lays-out purely because the *elements* changed (new episode boundary).
// This function is called imperatively instead, from an effect keyed on the
// `graph` object, so the canvas actually reflows on every boundary change.
// Guarded so it never throws into an effect that a test double's fake `cy`
// (no real `.layout()` method) might pass in.
function runLayout(cy: cytoscape.Core) {
  if (typeof cy.layout !== 'function') return
  try {
    cy.layout(layoutOptionsFor(layoutName)).run()
  } catch (error) {
    console.error(
      'cose-bilkent layout failed at runtime; falling back to the built-in cose layout',
      error,
    )
    layoutName = 'cose'
    try {
      cy.layout(layoutOptionsFor('cose')).run()
    } catch (fallbackError) {
      console.error('built-in cose layout also failed', fallbackError)
    }
  }
}

export type SelectedNode = {
  kind: 'node'
  id: string
  label: string
  nodeType: string
}

export type SelectedEdge = {
  kind: 'edge'
  id: string
  edgeType: string
  source: string
  target: string
}

export type SelectedElement = SelectedNode | SelectedEdge

type Props = {
  graph: GraphResponse
  onSelect: (element: SelectedElement | null) => void
  seriesId: string | null
  onRefetchGraph?: () => void
  episodes: EpisodeResponse[]
}

const ALLOWED_NODE_TYPES: { value: CustomNodeType; label: string }[] = [
  { value: 'Character', label: 'Character' },
  { value: 'Event', label: 'Event' },
  { value: 'Location', label: 'Location' },
  { value: 'Organization', label: 'Organization' },
  { value: 'Object', label: 'Object' },
]

function CreateCustomNodeDialog({
  open,
  onOpenChange,
  seriesId,
  episodes,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  seriesId: string | null
  episodes: EpisodeResponse[]
  onSuccess: () => void
}) {
  const [nodeType, setNodeType] = useState<CustomNodeType>('Character')
  const [label, setLabel] = useState('')
  const [episodeId, setEpisodeId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Default to the highest visible episode
  useEffect(() => {
    if (!episodeId && episodes.length > 0) {
      const highest = episodes.reduce((a, b) => (a.episode_order > b.episode_order ? a : b))
      setEpisodeId(highest.id)
    }
  }, [episodes, episodeId])

  const handleCreate = useCallback(async () => {
    if (!seriesId || !label.trim()) return
    setSaving(true)
    setError('')
    try {
      await createCustomNode(seriesId, { node_type: nodeType, label: label.trim(), episode_id: episodeId })
      setLabel('')
      setNodeType('Character')
      onOpenChange(false)
      onSuccess()
    } catch (err: any) {
      setError(err?.message ?? 'Failed to create node.')
    } finally {
      setSaving(false)
    }
  }, [seriesId, nodeType, label, episodeId, onOpenChange, onSuccess])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Create Custom Node</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3 py-2">
          {/* Node type */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="node-type" className="text-xs font-medium">Node Type</label>
            <select
              id="node-type"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] [color-scheme:dark]"
              value={nodeType}
              onChange={(e) => setNodeType(e.target.value as CustomNodeType)}
            >
              {ALLOWED_NODE_TYPES.map((nt) => (
                <option key={nt.value} value={nt.value}>{nt.label}</option>
              ))}
            </select>
          </div>
          {/* Label */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="node-label" className="text-xs font-medium">Label</label>
            <input
              id="node-label"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px]"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Enter node label..."
              maxLength={255}
            />
          </div>
          {/* Episode */}
          <div className="flex flex-col gap-1.5">
            <label htmlFor="node-episode" className="text-xs font-medium">Episode</label>
            <select
              id="node-episode"
              className="w-full rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[44px] [color-scheme:dark]"
              value={episodeId}
              onChange={(e) => setEpisodeId(e.target.value)}
            >
              {episodes.map((ep) => (
                <option key={ep.id} value={ep.id}>{ep.code} — {ep.title}</option>
              ))}
            </select>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md px-3 py-1.5 text-xs font-medium hover:bg-muted transition-colors min-h-[44px] disabled:opacity-50"
              onClick={() => onOpenChange(false)}
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors min-h-[44px] disabled:opacity-50"
              onClick={handleCreate}
              disabled={saving || !label.trim()}
            >
              {saving ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function GraphCanvas({ graph, onSelect, seriesId, onRefetchGraph, episodes }: Props) {
  console.log('[GC] GraphCanvas render called')
  const elements = useMemo(() => graphToElements(graph), [graph])
  const wiredCyRef = useRef<cytoscape.Core | null>(null)
  const cyInstanceRef = useRef<cytoscape.Core | null>(null)
  const stylesheet = useMemo(() => buildGraphStylesheet(prefersReducedMotion), [])
  const [dialogOpen, setDialogOpen] = useState(false)

  // Re-run the layout whenever a new graph is fetched.
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy) return
    runLayout(cy)
  }, [graph])

  return (
    <TooltipProvider>
      <div className="relative h-full w-full graph-canvas-backdrop">
        <CytoscapeComponent
          elements={elements}
          layout={layoutOptionsFor(layoutName)}
          stylesheet={stylesheet}
          style={{ width: '100%', height: '100%' }}
          minZoom={0.3}
          maxZoom={2.5}
          cy={(cy) => {
            cyInstanceRef.current = cy

            if (wiredCyRef.current === cy) return
            wiredCyRef.current = cy

            cy.on('mouseover', 'node', (evt) => {
              cy.container()?.setAttribute('title', evt.target.data('label'))
              evt.target.addClass('hovered')
              evt.target.connectedEdges().addClass('hovered')
            })
            cy.on('mouseout', 'node', (evt) => {
              cy.container()?.removeAttribute('title')
              evt.target.removeClass('hovered')
              evt.target.connectedEdges().removeClass('hovered')
            })
            cy.on('mouseover', 'edge', (evt) => {
              evt.target.addClass('hovered')
            })
            cy.on('mouseout', 'edge', (evt) => {
              evt.target.removeClass('hovered')
            })

            cy.on('tap', 'node', (evt) => {
              const node = evt.target
              const neighborhood = node.closedNeighborhood()
              cy.elements().difference(neighborhood).addClass('faded')
              neighborhood.removeClass('faded')
              cy.elements().removeClass('selected-dominant edge-active')
              node.addClass('selected-dominant')
              onSelect({
                kind: 'node',
                id: node.id(),
                label: node.data('label'),
                nodeType: node.data('nodeType'),
              })
            })

            cy.on('tap', 'edge', (evt) => {
              const edge = evt.target
              const neighborhood = edge.connectedNodes().union(edge)
              cy.elements().difference(neighborhood).addClass('faded')
              neighborhood.removeClass('faded')
              cy.elements().removeClass('selected-dominant edge-active')
              edge.addClass('edge-active')
              onSelect({
                kind: 'edge',
                id: edge.id(),
                edgeType: edge.data('edgeType'),
                source: edge.data('source'),
                target: edge.data('target'),
              })
            })

            cy.on('tap', (evt) => {
              if (evt.target === cy) {
                cy.elements().removeClass('faded selected-dominant edge-active')
                onSelect(null)
              }
            })
          }}
        />
        <GraphLegend />
        <GraphControls
          cyRef={cyInstanceRef}
          onReset={() => {
            const cy = cyInstanceRef.current
            if (cy) runLayout(cy)
          }}
        />
        {/* Floating Create Custom Node button — opens dialog */}
        <button
          type="button"
          className="absolute bottom-4 left-65 z-[60] flex items-center justify-center rounded-full bg-primary p-3 text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors min-h-[44px] min-w-[44px]"
          onClick={() => setDialogOpen(true)}
          aria-label="Create custom node"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden="true">
            <path d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
        </button>
        {dialogOpen && (
        <CreateCustomNodeDialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          seriesId={seriesId}
          episodes={episodes}
          onSuccess={() => onRefetchGraph?.()}
        />
        )}
      </div>
    </TooltipProvider>
  )
}
