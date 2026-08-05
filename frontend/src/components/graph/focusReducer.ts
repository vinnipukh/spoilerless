import type cytoscape from 'cytoscape'

export type FocusState = {
  focusedId: string | null
}

export type FocusAction =
  | { type: 'FOCUS_NODE'; id: string }
  | { type: 'CLEAR_FOCUS' }

export function initialFocusState(): FocusState {
  return { focusedId: null }
}

export function focusReducer(state: FocusState, action: FocusAction): FocusState {
  switch (action.type) {
    case 'FOCUS_NODE':
      return { focusedId: action.id }
    case 'CLEAR_FOCUS':
      return { focusedId: null }
    default:
      return state
  }
}

export function applyFocusToCytoscape(cy: cytoscape.Core, focusedId: string | null) {
  if (!cy) return

  const apply = () => {
    if (typeof cy.elements === 'function') {
      cy.elements().removeClass('faded selected-dominant')
    }

    if (!focusedId || typeof cy.getElementById !== 'function') return

    const target = cy.getElementById(focusedId)
    if (!target || target.length === 0) return

    if (typeof target.addClass === 'function') {
      target.addClass('selected-dominant')
    }

    if (typeof target.closedNeighborhood === 'function' && typeof cy.elements === 'function') {
      const neighborhood = target.closedNeighborhood()
      if (neighborhood && typeof cy.elements().difference === 'function') {
        const outside = cy.elements().difference(neighborhood)
        if (outside && typeof outside.addClass === 'function') {
          outside.addClass('faded')
        }
      }
    }
  }

  if (typeof cy.batch === 'function') {
    cy.batch(apply)
  } else {
    apply()
  }
}
