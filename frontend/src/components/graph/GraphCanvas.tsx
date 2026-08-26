import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import CytoscapeComponent from 'react-cytoscapejs'
import type { GraphNode, GraphResponse, VisualizationDTO, VisualizationViewType } from '../../types/graph'
import type { EpisodeResponse } from '../../types/series'
import * as sceneElements from '../../lib/graph/sceneElements'
import { buildGraphStylesheet } from './graphStylesheet'
import type { GraphMode } from './overviewTiers'
import { autoZoomHold } from './autoZoomHold'
import { TooltipProvider } from '@/components/ui/tooltip'
import { NodeHoverCard } from './NodeHoverCard'
import { GraphLegend } from './GraphLegend'
import { GraphControls } from './GraphControls'
import { GraphFilterPanel } from './GraphFilterPanel'
import { GraphFocusIndicator } from './GraphFocusIndicator'
import { PathFinder, type PathPick } from './PathFinder'
import { fetchExportMarkdown, downloadMarkdownBlob } from '@/api/export'
import { renderGraphMarkdown, exportFilename } from '@/lib/exportMarkdown'
import { NODE_TYPES } from '@/lib/nodeTypes'
import { applyHighlight, applyFocusToCytoscape } from '@/lib/graph/highlight'
import { reconcileCytoscapeElements } from './cytoscapeReconciler'
// 12-08 (THERMO-P0-03): layout engine + create-node dialog extracted.
import { runLayout, prefersReducedMotion } from './useCytoscapeLayout'
import { CreateCustomNodeDialog } from '../dialogs/CreateCustomNodeDialog'
import { layoutNameForView, layoutOptionsFor } from './layoutConfig'
import {
  INITIAL_SCENE_STATE,
  isFilterEnabled,
  type SceneAction,
  type SceneState,
} from '../../hooks/useSceneState'

// 12-08: AUTO_ZOOM_HOLD_MS + layout engine live in ./useCytoscapeLayout.ts;
// the 20s interaction hold state itself remains in ./autoZoomHold.ts (module
// level by design — it must survive destructive unmount/remount cycles).
const AUTO_ZOOM_HOLD_MS = 20_000

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
  // FEAT-03 (09-07): ids of nodes/edges newly revealed by a forward episode
  // advance (UI-SPEC §10.5) — a transient 4000ms `.newly-revealed` glow,
  // then auto-clear via onNewlyRevealedDone. Optional/nullable like
  // focusedElementIds so every pre-existing caller (and GraphCanvas.test.tsx's
  // existing assertions) keeps compiling and rendering unmodified.
  newlyRevealedIds?: FocusedElementIds | null
  onNewlyRevealedDone?: () => void
  // 08-06 (product owner): events selected in the Timeline view — when
  // non-empty, the graph hides every node not participating in (or being)
  // one of the selected events, plus edges touching hidden nodes.
  timelineFilterIds?: string[]
  // FEAT-06 (09-11): path-finder mode toggle (driven from GraphControls).
  // While active, node taps route to the PathFinder instead of select.
  onPathModeChange?: (active: boolean) => void
  // FEAT-09 (09-12): read-only mode for ShareView — hides FAB/edit affordances
  readOnly?: boolean
  // FEAT-09 (09-12): Share snapshot link trigger (opens ShareDialog)
  onShareLink?: () => void
  // 08-06+ (product owner, presentation): starting graph mode. Overview
  // (default) shows the curated tier-1 + connector projection; Full shows
  // every spoiler-safe element.
  initialMode?: GraphMode
  // Optional controlled mode seam. App uses this to keep surrounding
  // navigation in lockstep with the canvas mode.
  mode?: GraphMode
  onModeChange?: (mode: GraphMode) => void
  // 10-04 (D-08/D-44): neutral VisualizationDTO for the Phase 10 projection
  // path. When set, the scene renders `sceneElements.fromVisualization(visualization)`
  // through the SAME stable Cytoscape lifecycle (batched element diffs,
  // stored preset positions); the legacy GraphResponse path stays untouched
  // when this prop is absent. Pass `null` while a view is loading to retain
  // the prior scene (the last non-null DTO is held) — no flashing blank
  // canvas and no instance recreation. The backend already applied the
  // spoiler boundary; this component never filters (D-05).
  visualization?: VisualizationDTO | null
  scene?: SceneState
  dispatchScene?: (action: SceneAction) => void
}



// The node types the custom-node dialog may create — derived from the
// NODE_TYPES registry in lib/nodeTypes.ts (PROB-09 #81), not a second
// inline list. 12-08: the dialog itself moved to
// components/dialogs/CreateCustomNodeDialog.tsx.

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
  newlyRevealedIds = null,
  onNewlyRevealedDone,
  timelineFilterIds,
  onPathModeChange,
  readOnly = false,
  onShareLink,
  initialMode = 'overview',
  mode: controlledMode,
  onModeChange,
  visualization = null,
  scene = INITIAL_SCENE_STATE,
  dispatchScene = () => {},
}: Props) {

  const [internalMode, setInternalMode] = useState<GraphMode>(initialMode)
  const mode = controlledMode ?? internalMode
  const handleModeChange = useCallback((nextMode: GraphMode) => {
    if (controlledMode === undefined) setInternalMode(nextMode)
    onModeChange?.(nextMode)
  }, [controlledMode, onModeChange])
  // PROB-09/#75: the cy event callbacks are registered once per cy instance
  // and would close over the mount-time `graph` forever. Keep a ref synced to
  // the latest payload so the hover card reads fresh data after an in-place
  // `refresh()` (a stale closure showed first-render labels and missed newly
  // added nodes).
  const graphRef = useRef(graph)
  useEffect(() => {
    graphRef.current = graph
  }, [graph])

  // 10-04 (D-44): the visualization path holds the LAST non-null DTO so a
  // loading/error `null` prop retains the prior scene instead of flashing a
  // blank canvas or swapping to the full graph.
  // 260814-viz: `undefined` (the legacy callers never pass the prop) is the
  // EXPLICIT leave-projection signal — the DTO hold is dropped so Story /
  // Advanced render the legacy GraphResponse scene again (user content
  // exists only there). `null` still means "loading, retain".
  const lastVisualizationRef = useRef<VisualizationDTO | null>(null)
  let activeVisualization: VisualizationDTO | null
  if (visualization === undefined) {
    lastVisualizationRef.current = null
    activeVisualization = null
  } else {
    if (visualization) lastVisualizationRef.current = visualization
    activeVisualization = visualization ?? lastVisualizationRef.current
  }

  const elements = useMemo(() => {
    return activeVisualization
      ? sceneElements.fromVisualization(activeVisualization, {
          // D-14: technical labels (raw kind/relation vocabulary) appear only
          // in the Advanced/Full debug explorer.
          debugLabels: activeVisualization.metadata.view_type === 'full',
        })
      : sceneElements.fromGraph(graph, mode)
  }, [activeVisualization, graph, mode])

  // Keep react-cytoscapejs's declared element prop stable after mount. Its
  // id-only patcher removes obsolete compound parents before detaching shared
  // children, so a compound -> flat scene switch cascade-removes shared
  // nodes and then throws while adding their edges. The topology-aware
  // reconciler below owns every subsequent scene update instead.
  const initialElementsRef = useRef(elements)

  // D-22/D-24: additions (expansion, new custom node) are detected as NEW
  // node ids vs the previous render — runLayout gives them local placement
  // instead of a random global relayout. Edges and group/cluster parents are
  // never "added nodes".
  const prevElementIdsRef = useRef<Set<string> | null>(null)
  const addedNodeIds = useMemo(() => {
    const prev = prevElementIdsRef.current
    if (!prev) return []
    return elements
      .filter((el) => {
        const data = el.data ?? {}
        return !('source' in data) && !('target' in data) && !prev.has(String(data.id))
      })
      .map((el) => String(el.data?.id))
  }, [elements])
  useEffect(() => {
    prevElementIdsRef.current = new Set(elements.map((el) => String(el.data?.id)))
  }, [elements])
  // Memoized declarative startup layout. react-cytoscapejs starts this before
  // invoking its `cy` callback; that callback waits for this layoutstop and
  // then performs the same forced layout + fit as Refresh graph. Keeping the
  // object stable prevents incidental parent renders from starting layouts.
  // The task view selects the engine (D-25: investigation → dagre LR).
  const layoutView = activeVisualization?.metadata.view_type ?? null
  const layout = useMemo(
    () =>
      layoutOptionsFor(
        layoutNameForView(layoutView as VisualizationViewType | null),
        prefersReducedMotion,
        mode,
        false,
      ),
    [mode, layoutView],
  )
  // Layout changes are applied by the guarded imperative effect below. A
  // changing declarative prop would make react-cytoscapejs run an additional
  // uncontrolled global layout during each narrative-tab switch.
  const initialLayoutRef = useRef(layout)
  // 08-06+ (product owner): timestamp of the last touch anywhere in the app
  // (document-level capture) — stored at MODULE level so the 20s hold
  // survives the destructive unmount/remount that every graph refetch does.
  // NEGATIVE_INFINITY = never touched this mount → the first layout always
  // fits normally.
  useEffect(() => {
    const onTouch = () => {
      autoZoomHold.lastTouchAt = performance.now()
    }
    document.addEventListener('pointerdown', onTouch, true)
    return () => document.removeEventListener('pointerdown', onTouch, true)
  }, [])
  const wiredCyRef = useRef<cytoscape.Core | null>(null)
  const cyInstanceRef = useRef<cytoscape.Core | null>(null)
  // Unit-test adapters and lightweight embedders may expose only the small cy
  // surface needed for interaction tests. They cannot run the topology-aware
  // reconciler, so retain declarative element updates for those adapters.
  const useImperativeReconcileRef = useRef(true)
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy || !useImperativeReconcileRef.current) return
    reconcileCytoscapeElements(cy, elements)
  }, [elements])
  const stylesheet = useMemo(() => buildGraphStylesheet(prefersReducedMotion), [])
  const [dialogOpen, setDialogOpen] = useState(false)
  // Locally-created custom node reveal (the dialog lives inside this
  // component; App-level reveals arrive via the `revealElementIds` prop).
  const [localReveal, setLocalReveal] = useState<FocusedElementIds | null>(null)
  // Pending reveal target (external prop wins over the local custom-node one).
  const revealTarget = revealElementIds ?? localReveal
  // 08-06: previous timeline event filter — tracks entry/exit so stale
  // `.filtered-out` classes are cleared when the filter is removed.
  const prevTimelineFilter = useRef<string[]>([])
  const [pathMode, setPathMode] = useState(false)
  const pathPickHandlerRef = useRef<((pick: PathPick) => void) | null>(null)
  // Mirrors `pathMode` for the cy tap handlers (registered once at mount —
  // they must read the live value, never the mount-time closure).
  const pathModeRef = useRef(false)
  useEffect(() => {
    pathModeRef.current = pathMode
  }, [pathMode])

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
  const lastLayoutModeRef = useRef<GraphMode>(mode)
  // 10-04: the visualization DTO is a first-class layout trigger alongside
  // the graph — a new DTO (episode switch, expansion payload) re-enters
  // runLayout exactly like a graph change, but through the view-scoped
  // position cache (shared characters stay stable, D-23).
  const lastLayoutVizRef = useRef<VisualizationDTO | null>(null)
  // 08-10 (product owner): the dedupe guard is keyed to the cy INSTANCE,
  // not just the graph. StrictMode's dev double-mount (and any real
  // remount, e.g. the destructive loading unmount) creates a NEW cy while
  // the refs above survive — the old "already laid out" check would then
  // skip runLayout on the LIVE canvas, leaving only the declarative
  // fit:false layout at the default zoom-1 origin ("diagonal" graph on
  // open). A fresh cy therefore counts as a fresh graph: force the full
  // layout + fit, exactly like the Refresh graph button.
  const lastLayoutCyRef = useRef<cytoscape.Core | null>(null)
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy) return
    const cyChanged = lastLayoutCyRef.current !== cy
    lastLayoutCyRef.current = cy
    const graphChanged =
      lastLayoutGraphRef.current !== graph || lastLayoutVizRef.current !== activeVisualization || cyChanged
    const modeChanged = lastLayoutModeRef.current !== mode
    if (!graphChanged && !modeChanged) return
    if (graphChanged) {
      lastLayoutGraphRef.current = graph
      lastLayoutVizRef.current = activeVisualization
    }
    if (modeChanged) lastLayoutModeRef.current = mode
    // Skip the destructive full relayout while a reveal is pending too:
    // freshly created edges connect already-positioned nodes, and re-running
    // the layout would animate the nodes AFTER the reveal's cy.fit, undoing
    // the framing (the edge lands wherever the layout puts it — the user's
    // "new edges show up on the right" complaint).
    if (focusedElementIds || revealTarget) return
    // A mode switch re-runs with forceRelayout (different node set + spacing
    // constants); a graph change reuses the cached positions per mode. A
    // recent touch (within AUTO_ZOOM_HOLD_MS) suppresses the auto zoom-out
    // on graph-change-driven layouts — the view must not yank while the
    // user is working.
    const suppressAutoZoom =
      performance.now() - autoZoomHold.lastTouchAt < AUTO_ZOOM_HOLD_MS
    runLayout(
      cy,
      seriesId,
      graph.visible_until_order,
      modeChanged || cyChanged,
      mode,
      suppressAutoZoom,
      (activeVisualization?.metadata.view_type ?? null) as VisualizationViewType | null,
      addedNodeIds,
    )
  }, [graph, focusedElementIds, revealTarget, seriesId, mode, activeVisualization, addedNodeIds])

  // Launch refresh is registered from the cy callback below. It deliberately
  // waits for react-cytoscapejs's startup layout to STOP before invoking the
  // button-equivalent runLayout(force=true). Starting both layouts together
  // races them; refreshing before the first settles reproduces the diagonal.
  const launchRefreshCyRef = useRef<cytoscape.Core | null>(null)

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
  // The shared applyHighlight helper (lib/graph/highlight.ts, PROB-09/#72)
  // guards against a test double's fake `cy` (GraphCanvas.test.tsx's stub
  // only implements `on`/`container`) internally — same defensive style
  // `runLayout` uses for `cy.layout`.
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy) return
    applyHighlight(
      cy,
      focusedElementIds ?? { nodeIds: [], edgeIds: [] },
      {
        labelEdges: true,
        fadeOthers: true,
        fit: 48,
        clearClasses: ['selected-dominant', 'faded', 'edge-active', 'label-visible'],
      },
    )
  }, [focusedElementIds])

  // Transient reveal of freshly created elements (new edge / custom node):
  // bring them into view and briefly highlight them, then auto-clear. Same
  // defensive typeof guards as the focus effect. Merges the external prop
  // and any local custom-node reveal.
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy || !revealTarget) return

    const revealed = applyHighlight(
      cy,
      revealTarget,
      {
        classes: ['selected-dominant', 'edge-active'],
        fadeOthers: true,
        clearClasses: ['selected-dominant', 'faded', 'edge-active', 'label-visible'],
      },
    )
    if (!revealed || revealed.length === 0) return
    // Let the just-updated element data land before framing — the layout
    // effect above skips re-running while a reveal is pending, so this fit
    // is not undone by a layout animation.
    const frame = requestAnimationFrame(() => {
      if (typeof cy.fit === 'function') cy.fit(revealed, 60)
    })

    const timer = window.setTimeout(() => {
      cy.elements().removeClass('selected-dominant faded edge-active label-visible')
      if (revealElementIds) onRevealDone?.()
      else setLocalReveal(null)
    }, 2200)
    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealTarget, revealElementIds])

  // FEAT-03 (09-07): transient glow on elements newly revealed by a forward
  // episode advance (UI-SPEC §10.5). Applies `.newly-revealed` (stylesheet:
  // overlay #7C3AED at 0.45, padding 10) for 4000ms then auto-clears — a
  // pure additive glow: no layout re-run (the same defensive guards the
  // reveal effect uses) and no fade of other elements. Under
  // prefers-reduced-motion the glow is static (0ms stylesheet transitions,
  // no pulse animation).
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy || !newlyRevealedIds) return

    // A second advance replaces the first glow — never leave the class on
    // elements that are no longer in the new set.
    const revealed = applyHighlight(
      cy,
      newlyRevealedIds,
      { classes: ['newly-revealed'], clearClasses: ['newly-revealed'] },
    )
    if (!revealed || revealed.length === 0) return

    let cancelled = false

    // 2-cycle pulse (UI-SPEC §10.5: overlay-opacity 0.45→0.15→0.45 over
    // 4000ms). Timeout-scheduled animate steps (cytoscape's collection
    // typings expose `promiseOn`, not `promise`, so no promise chaining);
    // guarded so a test double's fake cy (no `.animate`) degrades to the
    // static glow, and reduced motion skips the pulse entirely.
    const pulseTimers: number[] = []
    if (!prefersReducedMotion && typeof revealed.animate === 'function') {
      const pulseSteps = [
        { opacity: 0.15, at: 0 },
        { opacity: 0.45, at: 1000 },
        { opacity: 0.15, at: 2000 },
        { opacity: 0.45, at: 3000 },
      ]
      for (const step of pulseSteps) {
        pulseTimers.push(
          window.setTimeout(() => {
            if (cancelled) return
            revealed.animate({ style: { 'overlay-opacity': step.opacity }, duration: 1000, easing: 'ease-in-out' })
          }, step.at),
        )
      }
    }

    const timer = window.setTimeout(() => {
      revealed.removeClass('newly-revealed')
      onNewlyRevealedDone?.()
    }, 4000)
    return () => {
      cancelled = true
      for (const pulseTimer of pulseTimers) window.clearTimeout(pulseTimer)
      window.clearTimeout(timer)
    }
    // onNewlyRevealedDone is an inline App arrow (fresh identity per render);
    // including it would re-run this effect (and reset the 4000ms timer) on
    // every App re-render — the reveal effect excludes onRevealDone the same
    // way.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newlyRevealedIds])

  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy || typeof cy.nodes !== 'function') return
    const updateFilters = () => {
      // Node-kind filters (reads scene.nodeKindFilters with absent key = visible).
      for (const [nodeKind, visible] of Object.entries(scene.nodeKindFilters)) {
        const nodes = cy.nodes(`[nodeType="${nodeKind}"]`)
        if (nodes && typeof nodes.removeClass === 'function') {
          if (visible !== false) nodes.removeClass('filtered-out')
          else nodes.addClass('filtered-out')
        }
      }
      // Edge-class filters (reads scene.edgeClassFilters with absent key = visible).
      for (const [edgeClass, visible] of Object.entries(scene.edgeClassFilters)) {
        const edges = cy.edges(`[edgeType="${edgeClass}"],[relationClass="${edgeClass}"]`)
        if (edges && typeof edges.removeClass === 'function') {
          if (visible !== false) edges.removeClass('filtered-out')
          else edges.addClass('filtered-out')
        }
      }
      // Timeline event filter (08-06): when events are selected in the
      // Timeline view, hide every node that is not one of the selected
      // events and not connected to one, plus edges touching hidden nodes.
      // Runs on both entering AND leaving the filter so stale classes are
      // cleared. Guarded by getElementById so the jsdom fake cy (which
      // lacks it) skips this pass in unit tests.
      const prevFilter = prevTimelineFilter.current
      const nextFilter = timelineFilterIds ?? []
      const hadFilter = prevFilter.length > 0
      const hasFilter = nextFilter.length > 0
      if ((hasFilter || hadFilter) && typeof cy.getElementById === 'function') {
        const kept = new Set<string>(nextFilter)
        if (hasFilter) {
          for (const edge of graph.edges) {
            if (kept.has(edge.source) || kept.has(edge.target)) {
              kept.add(edge.source)
              kept.add(edge.target)
            }
          }
        }
        for (const node of graph.nodes) {
          const el = cy.getElementById(node.id)
          if (hasFilter && !kept.has(node.id)) el?.addClass('filtered-out')
          else el?.removeClass('filtered-out')
        }
        for (const edge of graph.edges) {
          const el = cy.getElementById(edge.id)
          if (hasFilter && (!kept.has(edge.source) || !kept.has(edge.target))) {
            el?.addClass('filtered-out')
          } else {
            el?.removeClass('filtered-out')
          }
        }
      }
      prevTimelineFilter.current = nextFilter
    }
    if (typeof cy.batch === 'function') cy.batch(updateFilters)
    else updateFilters()
  }, [scene.nodeKindFilters, scene.edgeClassFilters, timelineFilterIds, graph])

  const focusedNodeId = scene.focus?.nodeIds[0] ?? null
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (cy && focusedNodeId != null) {
      applyFocusToCytoscape(cy, focusedNodeId)
    }
  }, [focusedNodeId])

  const [hoveredNodeInfo, setHoveredNodeInfo] = useState<{ node: GraphNode; pos: { x: number; y: number } } | null>(null)

  return (
    <TooltipProvider>
      <div className="relative h-full w-full graph-canvas-backdrop">
        <NodeHoverCard
          node={hoveredNodeInfo?.node ?? null}
          claims={graph.claims}
          position={hoveredNodeInfo?.pos ?? null}
          onDismiss={() => setHoveredNodeInfo(null)}
        />
        <CytoscapeComponent
          elements={useImperativeReconcileRef.current ? initialElementsRef.current : elements}
          layout={useImperativeReconcileRef.current ? initialLayoutRef.current : layout}
          stylesheet={stylesheet}
          style={{ width: '100%', height: '100%' }}
          minZoom={0.3}
          maxZoom={2.5}
          cy={(cy) => {
            cyInstanceRef.current = cy
            useImperativeReconcileRef.current =
              typeof cy.elements === 'function' &&
              typeof cy.elements().map === 'function' &&
              typeof cy.nodes === 'function' &&
              typeof cy.edges === 'function' &&
              typeof cy.add === 'function' &&
              typeof cy.remove === 'function' &&
              typeof cy.batch === 'function'

            if (wiredCyRef.current === cy) return
            wiredCyRef.current = cy

            if (launchRefreshCyRef.current !== cy) {
              launchRefreshCyRef.current = cy
              // Mark this instance/graph as handled so the parent effect does
              // not launch a competing layout while startup is still running.
              lastLayoutCyRef.current = cy
              lastLayoutGraphRef.current = graph
              lastLayoutVizRef.current = activeVisualization
              const refreshAfterStartup = () => {
                if (cyInstanceRef.current === cy) {
                  runLayout(
                    cy,
                    seriesId,
                    graph.visible_until_order,
                    true,
                    mode,
                    false,
                    (activeVisualization?.metadata.view_type ?? null) as VisualizationViewType | null,
                    [],
                  )
                }
              }
              if (typeof cy.one === 'function') cy.one('layoutstop', refreshAfterStartup)
              else queueMicrotask(refreshAfterStartup)
            }

            cy.on('mouseover', 'node', (evt) => {
              cy.container()?.setAttribute('title', evt.target.data('label'))
              evt.target.addClass('hovered')
              evt.target.connectedEdges().addClass('hovered')

              const nodeId = evt.target.id()
              const matchedNode = graphRef.current.nodes.find((n) => n.id === nodeId)
              if (matchedNode) {
                const renderedPos = evt.target.renderedPosition()
                const containerRect = cy.container()?.getBoundingClientRect()
                const x = (containerRect?.left ?? 0) + renderedPos.x
                const y = (containerRect?.top ?? 0) + renderedPos.y
                setHoveredNodeInfo({ node: matchedNode, pos: { x, y } })
              }
            })
            cy.on('mouseout', 'node', (evt) => {
              cy.container()?.removeAttribute('title')
              evt.target.removeClass('hovered')
              evt.target.connectedEdges().removeClass('hovered')
              setHoveredNodeInfo(null)
            })
            cy.on('mouseover', 'edge', (evt) => {
              evt.target.addClass('hovered')
            })
            cy.on('mouseout', 'edge', (evt) => {
              evt.target.removeClass('hovered')
            })

            cy.on('tap', 'node', (evt) => {
              const node = evt.target
              // FEAT-06 (09-11): while path mode is active, node taps become
              // path picks (first/second endpoint) — never tap-to-select.
              if (pathModeRef.current) {
                pathPickHandlerRef.current?.({
                  id: node.id(),
                  label: node.data('label'),
                })
                return
              }
              dispatchScene({ type: 'SET_FOCUS', nodeIds: [node.id()], edgeIds: [] })
              const neighborhood = node.closedNeighborhood()
              cy.elements().difference(neighborhood).addClass('faded')
              neighborhood.removeClass('faded')
              cy.elements().removeClass('selected-dominant edge-active label-visible')
              node.addClass('selected-dominant')
              // 08-06+: selecting a node reveals its incident edge labels
              // (stylesheet `edge.label-visible`).
              node.connectedEdges().addClass('label-visible')
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
              cy.elements().removeClass('selected-dominant edge-active label-visible')
              edge.addClass('edge-active')
              onSelect({
                kind: 'edge',
                id: edge.id(),
                edgeType: edge.data('edgeType') ?? edge.data('relationClass'),
                source: edge.data('source'),
                target: edge.data('target'),
              })
            })

            cy.on('tap', (evt) => {
              if (evt.target === cy) {
                dispatchScene({ type: 'CLEAR_FOCUS' })
                // FEAT-06 (09-11): an empty-canvas tap during path mode
                // clears the mode entirely (Clear/Esc/empty-tap exits).
                if (pathModeRef.current) {
                  setPathMode(false)
                  onPathModeChange?.(false)
                }
                cy.elements().removeClass('faded selected-dominant edge-active on-path path-source path-target label-visible')
                onSelect(null)
              }
            })

            // 08-06+ (product owner): remember the user's viewport so a held
            // remount (graph refetch within the 20s interaction window) can
            // restore it instead of dropping to the fresh cy's default.
            cy.on('viewport', () => {
              if (typeof cy.zoom === 'function' && typeof cy.pan === 'function') {
                const p = cy.pan()
                autoZoomHold.lastViewport = { zoom: cy.zoom(), pan: { x: p.x, y: p.y } }
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
        {pathMode && (
          <PathFinder
            cyRef={cyInstanceRef}
            seriesId={seriesId}
            onExit={() => {
              setPathMode(false)
              onPathModeChange?.(false)
            }}
            registerPickHandler={(handler) => {
              pathPickHandlerRef.current = handler
            }}
          />
        )}
        <GraphFilterPanel
          nodeKindFilters={scene.nodeKindFilters}
          edgeClassFilters={scene.edgeClassFilters}
          dispatchScene={dispatchScene}
        />
        <GraphLegend />
        <GraphControls
          cyRef={cyInstanceRef}
          mode={mode}
          onModeChange={handleModeChange}
          onReset={() => {
            const cy = cyInstanceRef.current
            if (cy) runLayout(cy, seriesId, graph.visible_until_order, true, mode)
          }}
          pathModeActive={pathMode}
          onPathModeChange={(active) => {
            setPathMode(active)
            onPathModeChange?.(active)
          }}
          onExport={async () => {
            if (!seriesId) return
            try {
              const { text, filename } = await fetchExportMarkdown(
                seriesId,
                graph.visible_until_order,
              )
              downloadMarkdownBlob(text, filename)
            } catch {
              const text = renderGraphMarkdown(graph)
              const filename = exportFilename(graph)
              downloadMarkdownBlob(text, filename)
            }
          }}
          onShareLink={readOnly ? undefined : onShareLink}
        />

        {/* Floating Create Custom Node button — opens dialog (hidden in read-only mode) */}
        {!readOnly && (
          <button
            type="button"
            className="absolute bottom-4 left-65 z-[40] flex items-center justify-center rounded-full bg-primary p-3 text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors min-h-[44px] min-w-[44px]"
            onClick={() => setDialogOpen(true)}
            aria-label="Create custom node"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="h-5 w-5" aria-hidden="true">
              <path d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </button>
        )}
        {!readOnly && dialogOpen && (
          <CreateCustomNodeDialog
            open={dialogOpen}
            onOpenChange={setDialogOpen}
            seriesId={seriesId}
            episodes={episodes}
            onSuccess={(node) => {
              ;(onRefreshGraph ?? onRefetchGraph)?.()
              setLocalReveal({ nodeIds: [node.id], edgeIds: [] })
            }}
          />
        )}

      </div>
    </TooltipProvider>
  )
}
