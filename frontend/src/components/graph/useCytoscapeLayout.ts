import cytoscape from 'cytoscape'
import type { VisualizationViewType } from '../../types/graph'
import { getCachedPositions, setCachedPositions } from './filterState'
import { autoZoomHold } from './autoZoomHold'
import type { GraphMode } from './overviewTiers'
import { layoutNameForView, layoutOptionsFor } from './layoutConfig'

// 12-08 (THERMO-P0-03): layout engine extracted verbatim from GraphCanvas.tsx
// — runLayout + localPlacementFor own the imperative Cytoscape layout
// lifecycle (cached-position application, local expansion placement, zoom
// floor) so the component only orchestrates.

// Reduced motion preference detected at module scope (no DOM access during SSR).
// The user's preference is captured once on first render — changing it mid-session
// would require a React state/hook, but <CytoscapeComponent> doesn't re-render on
// stylesheet changes anyway (it captures the ref once), so a static capture is
// appropriate.
export const prefersReducedMotion =
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

// 08-06+ (product owner): Overview's sparse layout makes cytoscape's fit
// zoom out so far the nodes look tiny. On layout completion, if the fit
// landed below this floor, zoom back in to it centered on the graph's
// bounding-box centre (the graph fills the screen; pan reveals the rest).
const OVERVIEW_MIN_ZOOM = 0.8

// react-cytoscapejs's own declarative `layout` prop re-applies a layout when
// the prop's shallow-diff (its `diff()` compares per-key VALUES) sees any
// change. layoutOptionsFor returns a fresh nodeRepulsion CLOSURE on every
// call, so passing it inline re-ran the layout (fit:true — the "auto
// zoom-out"!) on EVERY GraphCanvas re-render. The component memoizes the
// layout object so its reference is stable: react-cytoscapejs short-circuits
// on `prev === next` and leaves the viewport alone. runLayout below reflows
// imperatively on graph changes. Guarded so it never throws into an effect
// that a test double's fake `cy` (no real `.layout()` method) might pass in.
// 10-04 (D-22): expansion additions are placed LOCALLY (deterministic
// concentric ring around the existing scene's bounding-box centre) and
// merged into the stored presets — never a fresh global layout.
const LOCAL_PLACEMENT_RADIUS = 110

export function localPlacementFor(
  addedNodeIds: string[],
  cy: cytoscape.Core,
): Map<string, { x: number; y: number }> {
  let cx = 0
  let cyCenter = 0
  const els = typeof cy.elements === 'function' ? cy.elements() : null
  if (els && typeof els.boundingBox === 'function') {
    const bb = els.boundingBox()
    cx = bb.x1 + bb.w / 2
    cyCenter = bb.y1 + bb.h / 2
  }
  const placed = new Map<string, { x: number; y: number }>()
  addedNodeIds.forEach((id, i) => {
    const angle = (2 * Math.PI * i) / Math.max(addedNodeIds.length, 1)
    placed.set(id, {
      x: cx + LOCAL_PLACEMENT_RADIUS * Math.cos(angle),
      y: cyCenter + LOCAL_PLACEMENT_RADIUS * Math.sin(angle),
    })
  })
  return placed
}

export function runLayout(
  cy: cytoscape.Core,
  seriesId?: string | null,
  visibleUntilOrder?: number | null,
  forceRelayout: boolean = false,
  mode: GraphMode = 'full',
  suppressAutoZoom: boolean = false,
  // 10-04 (D-23): the visualization view doubles as the positions scene key
  // (`viz:episode_overview`, ...). Stored presets then persist across
  // episode switches for the same view (shared characters stay stable) and
  // never cross views (T10-CACHE-04).
  view: VisualizationViewType | null = null,
  // 10-04 (D-22): ids of nodes added since the last render. With stored
  // presets present these get LOCAL concentric placement merged into the
  // cache — a global layout never re-runs for additions.
  addedNodeIds: string[] = [],
) {
  if (typeof cy.layout !== 'function') return

  const sceneKey = view ? `viz:${view}` : undefined

  // 08-06+ (product owner): while the user is actively interacting (touched
  // the screen within AUTO_ZOOM_HOLD_MS), graph-change-driven layouts must
  // NOT yank the viewport — run without fit and skip the zoom floor so the
  // view stays exactly where the user left it. Explicit view actions
  // (forceRelayout: mode switch / refresh graph) always re-fit.
  const holdView = suppressAutoZoom && !forceRelayout
  if (holdView && typeof cy.zoom === 'function' && typeof cy.pan === 'function') {
    // A destructive remount created a fresh cy at the default zoom-1 origin
    // — restore the user's last viewport so the held view survives it (this
    // also covers the cached-positions early return below).
    cy.zoom(autoZoomHold.lastViewport.zoom)
    cy.pan({ ...autoZoomHold.lastViewport.pan })
  }

  if (!forceRelayout && seriesId) {
    const cached = sceneKey
      ? getCachedPositions(seriesId, 0, mode, sceneKey)
      : visibleUntilOrder != null
        ? getCachedPositions(seriesId, visibleUntilOrder, mode)
        : undefined
    if (cached && cached.size > 0) {
      const applyPos = () => {
        if (typeof cy.getElementById === 'function') {
          for (const [nodeId, pos] of cached.entries()) {
            const node = cy.getElementById(nodeId)
            if (node && node.length > 0 && typeof node.position === 'function') {
              node.position(pos)
            }
          }
        }
        // D-22: additions get local placement, never a global relayout.
        if (addedNodeIds.length > 0) {
          const placed = localPlacementFor(addedNodeIds, cy)
          for (const [nodeId, pos] of placed.entries()) {
            const node = cy.getElementById(nodeId)
            if (node && node.length > 0 && typeof node.position === 'function') {
              node.position(pos)
            }
          }
          const merged = new Map(cached)
          for (const [nodeId, pos] of placed.entries()) merged.set(nodeId, pos)
          if (sceneKey) setCachedPositions(seriesId, 0, merged, mode, sceneKey)
          else if (visibleUntilOrder != null) {
            setCachedPositions(seriesId, visibleUntilOrder, merged, mode)
          }
        }
      }
      if (typeof cy.batch === 'function') cy.batch(applyPos)
      else applyPos()
      return
    }
  }

  try {
    const l = cy.layout(
      layoutOptionsFor(
        layoutNameForView(view),
        prefersReducedMotion,
        mode,
        !holdView,
      ),
    )
    if (seriesId && (visibleUntilOrder != null || sceneKey) && typeof l.one === 'function') {
      l.one('layoutstop', () => {
        const map = new Map<string, { x: number; y: number }>()
        cy.nodes().forEach((n) => {
          map.set(n.id(), n.position())
        })
        if (sceneKey) setCachedPositions(seriesId, 0, map, mode, sceneKey)
        else if (visibleUntilOrder != null) {
          setCachedPositions(seriesId, visibleUntilOrder, map, mode)
        }
        // Zoom floor (Overview only): fit zoomed out too far on the sparse
        // layout — lift the view back to OVERVIEW_MIN_ZOOM, anchored on the
        // graph centre (model-coordinate `position` keeps the anchor fixed).
        // Guarded for test fakes (no zoom/boundingBox). Skipped while the
        // user's 20s interaction hold is active.
        if (
          !holdView &&
          mode === 'overview' &&
          typeof cy.zoom === 'function'
        ) {
          const els = typeof cy.elements === 'function' ? cy.elements() : null
          const bb =
            els && typeof els.boundingBox === 'function' ? els.boundingBox() : null
          if (bb && cy.zoom() < OVERVIEW_MIN_ZOOM) {
            cy.zoom({
              level: OVERVIEW_MIN_ZOOM,
              position: {
                x: bb.x1 + bb.w / 2,
                y: bb.y1 + bb.h / 2,
              },
            })
          }
        }
      })
    }
    l.run()
  } catch (error) {
    console.error(
      'cose-bilkent layout failed at runtime; falling back to the built-in cose layout',
      error,
    )
    try {
      cy.layout(
        layoutOptionsFor('cose', prefersReducedMotion, mode, !holdView),
      ).run()
    } catch (fallbackError) {
      console.error('built-in cose layout also failed', fallbackError)
    }
  }
}
