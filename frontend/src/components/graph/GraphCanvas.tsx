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
import { GraphFocusIndicator } from './GraphFocusIndicator'
import { createCustomNode } from '../../api/userContent'
import type { CustomNodeResponse, CustomNodeType } from '../../types/userContent'

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

// A chat-driven graph_focus target set (RAG-17) — externally-driven highlight
// request, distinct from the canvas's own internal tap-to-select mechanism.
export type FocusedElementIds = {
  nodeIds: string[]
  edgeIds: string[]
}

type Props = {
  graph: GraphResponse
  onSelect: (element: SelectedElement | null) => void
  seriesId: string | null
  onRefetchGraph?: () => void
  /** In-place graph refresh (useGraph's `refresh`) — preferred for
   * create/edit operations so the canvas updates without a destructive
   * loading unmount. */
  onRefreshGraph?: () => void
  episodes: EpisodeResponse[]
  // Externally-driven highlight (06-10-PLAN.md) — a chat citation's "Show in
  // graph" action, wired through App.tsx. Optional/nullable so every
  // pre-existing caller (and GraphCanvas.test.tsx's existing assertions)
  // keeps compiling and rendering unmodified.
  focusedElementIds?: FocusedElementIds | null
  onClearFocus?: () => void
  // Transient "reveal" of freshly created elements (new edge / new node):
  // re-frame the viewport on them + brief highlight, then auto-clear via
  // onRevealDone. Fixes newly created edges rendering out of view (e.g.
  // right of the viewport under the chat sheet).
  revealElementIds?: FocusedElementIds | null
  onRevealDone?: () => void
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
  onSuccess: (node: CustomNodeResponse) => void
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
      const created = await createCustomNode(seriesId, { node_type: nodeType, label: label.trim(), episode_id: episodeId })
      setLabel('')
      setNodeType('Character')
      onOpenChange(false)
      onSuccess(created)
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

export function GraphCanvas({
  graph,
  onSelect,
  seriesId,
  onRefetchGraph,
  onRefreshGraph,
  episodes,
  focusedElementIds = null,
  onClearFocus,
  revealElementIds = null,
  onRevealDone,
}: Props) {
  const elements = useMemo(() => graphToElements(graph), [graph])
  const wiredCyRef = useRef<cytoscape.Core | null>(null)
  const cyInstanceRef = useRef<cytoscape.Core | null>(null)
  const stylesheet = useMemo(() => buildGraphStylesheet(prefersReducedMotion), [])
  const [dialogOpen, setDialogOpen] = useState(false)
  // Locally-created custom node reveal (the dialog lives inside this
  // component; App-level reveals arrive via the `revealElementIds` prop).
  const [localReveal, setLocalReveal] = useState<FocusedElementIds | null>(null)
  // Pending reveal target (external prop wins over the local custom-node one).
  const revealTarget = revealElementIds ?? localReveal

  // Re-run the layout whenever a new graph is fetched — UNLESS an external
  // `focusedElementIds` is active, in which case the graph change is an
  // incremental refresh (06-11: a ChangeSet apply) that must NOT trigger the
  // destructive full relayout: the focus effect below already provides the
  // gentle `cy.fit(focused, 48)` re-frame (06-UI-SPEC.md "Applying a
  // ChangeSet"), and running cose-bilkent again would discard the user's
  // zoom/pan. Element data still updates in place; the layout re-runs on the
  // next non-focused graph change (e.g. a progress boundary change once the
  // focus has been cleared). The ref guard keeps focus clear/apply state
  // changes (which re-run this effect via `focusedElementIds` in the deps)
  // from ever re-laying-out an unchanged graph.
  const lastLayoutGraphRef = useRef<GraphResponse | null>(null)
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy) return
    if (lastLayoutGraphRef.current === graph) return
    lastLayoutGraphRef.current = graph
    // Skip the destructive full relayout while a reveal is pending too:
    // freshly created edges connect already-positioned nodes, and re-running
    // cose-bilkent would animate the nodes AFTER the reveal's cy.fit, undoing
    // the framing (the edge lands wherever the layout puts it — the user's
    // "new edges show up on the right" complaint).
    if (focusedElementIds || revealTarget) return
    runLayout(cy)
  }, [graph, focusedElementIds, revealTarget])

  // Apply/clear an externally-driven `graph_focus` highlight (RAG-17), keyed
  // on the `focusedElementIds` prop — the same "prop-driven effect" pattern
  // `useGraph.ts` already uses elsewhere. This is a genuinely new capability
  // (`cyInstanceRef` was never exposed outside this component before), and
  // extends rather than forks the existing internal `cy.on('tap', ...)`
  // handlers below: both mechanisms write to the same `.selected-dominant`/
  // `.faded` classes, and a manual tap after a `graph_focus` update simply
  // clears/reassigns them exactly as it always has (see the tap handlers'
  // own full `removeClass`/`addClass` sequence further down).
  //
  // Deliberate, documented supersession: `03.1-UI-SPEC.md`'s Performance
  // note states the `.selected-dominant` glow "applies to at most one node
  // at a time" — that constraint was written for continuous per-frame tap
  // selection, not a bounded, backend-size-limited `graph_focus` set
  // (06-UI-SPEC.md "Graph synchronization"). `graph_focus` may highlight
  // multiple nodes/edges simultaneously; documented here exactly as
  // 03.1-UI-SPEC.md documented its own hover-color supersession of Phase 2.
  //
  // Guarded via `typeof` checks (not a bare call) so a test double's fake
  // `cy` (GraphCanvas.test.tsx's stub only implements `on`/`container`) never
  // throws into this effect — the same defensive style `runLayout` already
  // uses for `cy.layout`.
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy) return
    if (
      typeof cy.elements !== 'function' ||
      typeof cy.getElementById !== 'function' ||
      typeof cy.collection !== 'function'
    ) {
      return
    }

    // Always start from a clean slate — clears whatever the previous
    // `focusedElementIds` value (or a manual tap) left behind, identically
    // to tapping empty canvas.
    cy.elements().removeClass('selected-dominant faded edge-active')

    if (!focusedElementIds) return

    const requestedIds = [...focusedElementIds.nodeIds, ...focusedElementIds.edgeIds]
    const focused = cy.collection()
    for (const id of requestedIds) {
      // A `graph_focus` reference to an element the frontend cannot resolve
      // in the currently-loaded graph (defensively, should be
      // architecturally impossible per RAG-08) is silently dropped rather
      // than causing a render error.
      const element = cy.getElementById(id)
      if (element && element.length > 0) focused.merge(element)
    }
    if (focused.length === 0) return

    focused.addClass('selected-dominant')
    cy.elements().difference(focused).addClass('faded')

    // Gentle re-frame on the focused subgraph — same 48px padding
    // convention GraphControls.tsx's fit-to-view button already uses, not a
    // hard viewport reset that would discard the user's zoom/pan.
    if (typeof cy.fit === 'function') cy.fit(focused, 48)
  }, [focusedElementIds])

  // Transient reveal of freshly created elements (new edge / custom node):
  // bring them into view and briefly highlight them, then auto-clear. Same
  // defensive typeof guards as the focus effect. Merges the external prop
  // and any local custom-node reveal.
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy || !revealTarget) return
    if (
      typeof cy.elements !== 'function' ||
      typeof cy.getElementById !== 'function' ||
      typeof cy.collection !== 'function' ||
      typeof cy.fit !== 'function'
    ) {
      return
    }

    cy.elements().removeClass('selected-dominant faded edge-active')
    const requestedIds = [...revealTarget.nodeIds, ...revealTarget.edgeIds]
    const revealed = cy.collection()
    for (const id of requestedIds) {
      const element = cy.getElementById(id)
      if (element && element.length > 0) revealed.merge(element)
    }
    if (revealed.length === 0) return

    revealed.addClass('selected-dominant edge-active')
    cy.elements().difference(revealed).addClass('faded')
    // Let the just-updated element data land before framing — the layout
    // effect above skips re-running while a reveal is pending, so this fit
    // is not undone by a layout animation.
    const frame = requestAnimationFrame(() => cy.fit(revealed, 60))

    const timer = window.setTimeout(() => {
      cy.elements().removeClass('selected-dominant faded edge-active')
      if (revealElementIds) onRevealDone?.()
      else setLocalReveal(null)
    }, 2200)
    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealTarget, revealElementIds])

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
        {focusedElementIds && (
          <GraphFocusIndicator
            count={focusedElementIds.nodeIds.length + focusedElementIds.edgeIds.length}
            onClear={() => onClearFocus?.()}
          />
        )}
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
          onSuccess={(node) => {
            // In-place refresh (no destructive loading unmount) then reveal
            // the freshly created node so it is framed on screen instead of
            // landing out of view.
            ;(onRefreshGraph ?? onRefetchGraph)?.()
            setLocalReveal({ nodeIds: [node.id], edgeIds: [] })
          }}
        />
        )}
      </div>
    </TooltipProvider>
  )
}
