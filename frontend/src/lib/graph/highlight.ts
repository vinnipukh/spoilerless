import type cytoscape from 'cytoscape'

/**
 * Highlight helpers — the single implementation behind the four class
 * juggling copies that used to live in GraphCanvas effects + focusReducer
 * (PROB-09/#72).
 *
 * Every caller does the same thing: clear stale classes, resolve the
 * requested ids against the live graph (unknown ids silently dropped —
 * RAG-08), add the highlight classes, optionally fade everything outside
 * the set, optionally fit the viewport. One helper, four call sites.
 */

export type HighlightRequest = {
  nodeIds: string[]
  edgeIds: string[]
}

export type HighlightOptions = {
  /** Classes added to the highlighted set (default: ['selected-dominant']). */
  classes?: string[]
  /** Also add `label-visible` to focused edges and edges incident to focused nodes. */
  labelEdges?: boolean
  /**
   * Fade everything outside the highlighted set. Pass a function to fade a
   * custom complement (e.g. `elements().difference(target.closedNeighborhood())`
   * — the tap-selection "fade all but my neighborhood" behavior).
   */
  fadeOthers?: boolean | ((cy: cytoscape.Core, highlighted: cytoscape.CollectionReturnValue) => cytoscape.CollectionReturnValue)
  /** Classes cleared from ALL elements first (default: classes + faded + label-visible). */
  clearClasses?: string[]
  /** Fit padding; omit to skip the fit entirely. */
  fit?: number
}

function guard(cy: cytoscape.Core): boolean {
  return (
    typeof cy.elements === 'function' &&
    typeof cy.getElementById === 'function' &&
    typeof cy.collection === 'function'
  )
}

/** Resolve the requested ids to a cytoscape collection (missing ids dropped). */
export function resolveHighlightElements(
  cy: cytoscape.Core,
  request: HighlightRequest,
): cytoscape.CollectionReturnValue {
  const resolved = cy.collection()
  for (const id of [...request.nodeIds, ...request.edgeIds]) {
    const element = cy.getElementById(id)
    if (element && element.length > 0) resolved.merge(element)
  }
  return resolved
}

/** Clear the given classes from every element (empty list = no-op). */
export function clearHighlightClasses(
  cy: cytoscape.Core,
  classes: string[],
): void {
  if (classes.length === 0) return
  if (typeof cy.elements === 'function') cy.elements().removeClass(classes.join(' '))
}

/**
 * Apply a highlight: clear stale classes, resolve the requested elements,
 * add the highlight classes, optionally reveal incident-edge labels, fade
 * the rest, and (optionally) fit the viewport with the given padding.
 * Returns the resolved collection (for deferred fits / pulse timers), or an
 * empty collection when nothing resolved. A no-op on unresolvable ids.
 */
export function applyHighlight(
  cy: cytoscape.Core,
  request: HighlightRequest,
  options: HighlightOptions = {},
): cytoscape.CollectionReturnValue | undefined {
  if (!guard(cy)) return undefined

  const {
    classes = ['selected-dominant'],
    labelEdges = false,
    fadeOthers = false,
    clearClasses = [...classes, 'faded', 'label-visible'],
    fit,
  } = options

  clearHighlightClasses(cy, clearClasses)

  const highlighted = resolveHighlightElements(cy, request)
  if (highlighted.length === 0) return highlighted

  highlighted.addClass(classes.join(' '))
  if (labelEdges) {
    for (const nodeId of request.nodeIds) {
      const el = cy.getElementById(nodeId)
      if (el && el.length > 0 && typeof el.connectedEdges === 'function') {
        el.connectedEdges().addClass('label-visible')
      }
    }
    for (const edgeId of request.edgeIds) {
      const el = cy.getElementById(edgeId)
      if (el && el.length > 0) el.addClass('label-visible')
    }
  }
  if (typeof fadeOthers === 'function') {
    fadeOthers(cy, highlighted).addClass('faded')
  } else if (fadeOthers) {
    cy.elements().difference(highlighted).addClass('faded')
  }
  if (fit !== undefined && typeof cy.fit === 'function') {
    cy.fit(highlighted, fit)
  }
  return highlighted
}

/**
 * Single-node focus (search/palette jump path). Fades everything outside
 * the focused node's closed neighborhood — the tap-selection convention —
 * via the custom-complement form of `fadeOthers`. Replaces the old
 * focusReducer.ts implementation (PROB-09/#72).
 */
export function applyFocusToCytoscape(cy: cytoscape.Core, focusedId: string | null): void {
  if (!cy) return
  const apply = () => {
    if (focusedId == null) {
      applyHighlight(cy, { nodeIds: [], edgeIds: [] })
      return
    }
    applyHighlight(
      cy,
      { nodeIds: [focusedId], edgeIds: [] },
      {
        labelEdges: true,
        fadeOthers: (c, highlighted) => {
          const target = c.getElementById(focusedId)
          if (!target || target.length === 0 || typeof target.closedNeighborhood !== 'function') {
            return c.elements().difference(highlighted)
          }
          return c.elements().difference(target.closedNeighborhood())
        },
      },
    )
  }
  if (typeof cy.batch === 'function') cy.batch(apply)
  else apply()
}
