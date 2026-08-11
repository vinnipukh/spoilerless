// Focus state machine only — the cytoscape application side lives in
// lib/graph/highlight.ts (PROB-09/#72).
export { applyFocusToCytoscape } from '../../lib/graph/highlight'

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
