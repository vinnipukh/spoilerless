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

  cy.batch(() => {
    cy.elements().removeClass('faded selected-dominant')

    if (!focusedId) return

    const target = cy.getElementById(focusedId)
    if (!target || target.length === 0) return

    target.addClass('selected-dominant')

    // 1-hop neighborhood elements (node + connected edges + connected neighbor nodes)
    const neighborhood = target.closedNeighborhood()
    const outside = cy.elements().difference(neighborhood)

    outside.addClass('faded')
  })
}
