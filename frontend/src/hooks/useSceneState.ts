// Serializable scene state reducer (D-24: "React state owns scene;
// Cytoscape changes apply through batched diffs"). One plain, JSON-safe
// state object per scene covering: active view, filters, selection, focus,
// camera, positions, expansions, timeline selection, Inspector state, and
// temporary restoration (Answer Graph, D-27).
//
// Safety contract (threat model T10-FOCUS-04):
// - The ENTIRE state is serializable: plain objects/arrays/numbers/strings/
//   null only (asserted by the JSON round-trip test). No functions, no DOM,
//   no cy references — so restoration can never smuggle scene authority.
// - Focus accepts only server-safe ids (T10-FOCUS-02: the backend rejects
//   hidden focus ids; this reducer mirrors the id charset so an unsafe
//   candidate is refused before it can enter scene state).
// - Camera/positions/expansions/timeline are presentation-only state:
//   dispatching them never triggers a fetch or a relayout (the canvas
//   decides layout policy, D-22/D-24/D-25).

import { useReducer, type Dispatch } from 'react'
import type { VisualizationDTO, VisualizationViewType } from '../types/graph'

export function isFilterEnabled(filters: Record<string, boolean>, key: string): boolean {
  return filters[key] !== false
}

export type SceneCamera = { zoom: number; pan: { x: number; y: number } }

export type ScenePosition = { x: number; y: number }

export type SceneSelection =
  | { kind: 'node' | 'edge'; id: string }
  | null

// Server-safe focus: ids only (never labels, never derived data). An empty
// array means "focus cleared".
export type SceneFocus = { nodeIds: string[]; edgeIds: string[] } | null

export type SceneInspector = { open: boolean; tab: string }

// 10-06 (D-21/D-48): one record per applied expansion — anchor, allowlisted
// key, and the addition ids it produced. Undo pops the newest record and
// removes exactly those additions (history-based restoration, never guess).
export type ExpansionRecord = {
  anchorId: string
  key: string
  additionIds: string[]
  dto?: VisualizationDTO
}

// Snapshot taken when a temporary scene (Answer Graph) opens, so closing it
// restores camera, selection, expansions, timeline, filters, and the active
// view EXACTLY (D-27/D-41).
export type TemporarySnapshot = {
  camera: SceneCamera | null
  selection: SceneSelection
  expansions: string[]
  timelineSelection: string[] | null
  nodeKindFilters: Record<string, boolean>
  edgeClassFilters: Record<string, boolean>
  activeView: VisualizationViewType
}

export type SceneTemporary = {
  kind: 'answer_graph'
  nodeIds: string[]
  snapshot: TemporarySnapshot
} | null

export type SceneState = {
  activeView: VisualizationViewType
  nodeKindFilters: Record<string, boolean>
  edgeClassFilters: Record<string, boolean>
  selection: SceneSelection
  focus: SceneFocus
  camera: SceneCamera | null
  positions: Record<string, ScenePosition>
  expansions: string[]
  expansionHistory: ExpansionRecord[]
  timelineSelection: string[] | null
  inspector: SceneInspector
  temporary: SceneTemporary
}

export type SceneAction =
  | { type: 'SET_VIEW'; view: VisualizationViewType }
  | { type: 'SET_NODE_KIND_FILTER'; kind: string; visible: boolean }
  | { type: 'SET_EDGE_CLASS_FILTER'; edgeClass: string; visible: boolean }
  | { type: 'SET_ALL_FILTERS'; visible: boolean }
  | { type: 'SELECT'; selection: SceneSelection }
  | { type: 'CLEAR_SELECTION' }
  | { type: 'SET_FOCUS'; nodeIds: string[]; edgeIds: string[] }
  | { type: 'CLEAR_FOCUS' }
  | { type: 'SET_CAMERA'; camera: SceneCamera }
  | { type: 'SET_POSITIONS'; positions: Record<string, ScenePosition> }
  | { type: 'ADD_EXPANSION'; nodeIds: string[]; record?: ExpansionRecord }
  | { type: 'UNDO_EXPANSION' }
  | { type: 'COLLAPSE_EXPANSION'; anchorId: string }
  | { type: 'REMOVE_EXPANSION'; nodeId: string }
  | { type: 'CLEAR_EXPANSIONS' }
  | { type: 'SET_TIMELINE_SELECTION'; nodeIds: string[] | null }
  | { type: 'SET_INSPECTOR'; open?: boolean; tab?: string }
  | { type: 'OPEN_TEMPORARY'; kind: 'answer_graph'; nodeIds: string[] }
  | { type: 'CLOSE_TEMPORARY' }
  | { type: 'RESET_VIEW' }
  | { type: 'BACK_TO_OVERVIEW' }

export const INITIAL_SCENE_STATE: SceneState = {
  activeView: 'episode_overview',
  nodeKindFilters: {},
  edgeClassFilters: {},
  selection: null,
  focus: null,
  camera: null,
  positions: {},
  expansions: [],
  expansionHistory: [],
  timelineSelection: null,
  inspector: { open: false, tab: 'overview' },
  temporary: null,
}

// T10-FOCUS-04: the same safe-id charset the backend uses for resource ids.
// Anything else (whitespace, quotes, non-ASCII, empty) is refused.
const SERVER_SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9:_-]*$/

export function isServerSafeId(id: string): boolean {
  return SERVER_SAFE_ID.test(id)
}

function allSafe(ids: string[]): boolean {
  return ids.every((id) => isServerSafeId(id))
}

function takeSnapshot(state: SceneState): TemporarySnapshot {
  return {
    camera: state.camera,
    selection: state.selection,
    expansions: [...state.expansions],
    timelineSelection: state.timelineSelection,
    nodeKindFilters: { ...state.nodeKindFilters },
    edgeClassFilters: { ...state.edgeClassFilters },
    activeView: state.activeView,
  }
}

export function sceneReducer(state: SceneState, action: SceneAction): SceneState {
  switch (action.type) {
    case 'SET_VIEW':
      return { ...state, activeView: action.view }

    case 'SET_NODE_KIND_FILTER':
      return {
        ...state,
        nodeKindFilters: {
          ...state.nodeKindFilters,
          [action.kind]: action.visible,
        },
      }

    case 'SET_EDGE_CLASS_FILTER':
      return {
        ...state,
        edgeClassFilters: {
          ...state.edgeClassFilters,
          [action.edgeClass]: action.visible,
        },
      }

    case 'SET_ALL_FILTERS': {
      const nodeKindFilters: Record<string, boolean> = {}
      for (const key of Object.keys(state.nodeKindFilters)) {
        nodeKindFilters[key] = action.visible
      }
      const edgeClassFilters: Record<string, boolean> = {}
      for (const key of Object.keys(state.edgeClassFilters)) {
        edgeClassFilters[key] = action.visible
      }
      return { ...state, nodeKindFilters, edgeClassFilters }
    }

    case 'SELECT':
      return { ...state, selection: action.selection }

    case 'CLEAR_SELECTION':
      return { ...state, selection: null }

    case 'SET_FOCUS':
      // Reject unsafe state: a focus may only carry server-safe ids.
      if (!allSafe(action.nodeIds) || !allSafe(action.edgeIds)) return state
      return {
        ...state,
        focus: { nodeIds: [...action.nodeIds], edgeIds: [...action.edgeIds] },
      }

    case 'CLEAR_FOCUS':
      return { ...state, focus: null }

    case 'SET_CAMERA':
      return { ...state, camera: action.camera }

    case 'SET_POSITIONS':
      // Batched position merge (D-22: stored preset positions + local
      // additions; never a global relayout trigger).
      return { ...state, positions: { ...state.positions, ...action.positions } }

    case 'ADD_EXPANSION': {
      if (!allSafe(action.nodeIds)) return state
      if (action.record && !allSafe(action.record.additionIds)) return state
      const seen = new Set(state.expansions)
      for (const id of action.nodeIds) seen.add(id)
      return {
        ...state,
        expansions: [...seen],
        expansionHistory: action.record
          ? [...state.expansionHistory, action.record]
          : state.expansionHistory,
      }
    }

    case 'UNDO_EXPANSION': {
      // History-based restoration (D-48): pop the newest record and remove
      // exactly its additions. Expansions applied without a record are
      // unaffected (they were not history-tracked).
      const history = state.expansionHistory
      if (history.length === 0) return state
      const undone = history[history.length - 1]
      const removed = new Set(undone.additionIds)
      return {
        ...state,
        expansionHistory: history.slice(0, -1),
        expansions: state.expansions.filter((id) => !removed.has(id)),
      }
    }

    case 'COLLAPSE_EXPANSION': {
      // Remove every history record rooted at the anchor plus its additions.
      const keptHistory = state.expansionHistory.filter(
        (record) => record.anchorId !== action.anchorId,
      )
      const removed = new Set<string>()
      for (const record of state.expansionHistory) {
        if (record.anchorId === action.anchorId) {
          for (const id of record.additionIds) removed.add(id)
        }
      }
      return {
        ...state,
        expansionHistory: keptHistory,
        expansions: state.expansions.filter((id) => !removed.has(id)),
      }
    }

    case 'REMOVE_EXPANSION':
      return {
        ...state,
        expansions: state.expansions.filter((id) => id !== action.nodeId),
      }

    case 'CLEAR_EXPANSIONS':
      return { ...state, expansions: [], expansionHistory: [] }

    case 'SET_TIMELINE_SELECTION':
      return {
        ...state,
        timelineSelection: action.nodeIds ? [...action.nodeIds] : null,
      }

    case 'SET_INSPECTOR':
      return {
        ...state,
        inspector: {
          open: action.open ?? state.inspector.open,
          tab: action.tab ?? state.inspector.tab,
        },
      }

    case 'OPEN_TEMPORARY': {
      // Reject unsafe state: temporary node sets are server-safe ids only.
      if (!allSafe(action.nodeIds)) return state
      return {
        ...state,
        temporary: {
          kind: action.kind,
          nodeIds: [...action.nodeIds],
          snapshot: takeSnapshot(state),
        },
      }
    }

    case 'CLOSE_TEMPORARY': {
      if (!state.temporary) return state
      // Restore the snapshot captured when the temporary scene opened
      // (D-27/D-41): camera, selection, expansions, timeline, filters, and
      // the active view — the exact scene state, never derived data.
      const { snapshot } = state.temporary
      return {
        ...state,
        temporary: null,
        camera: snapshot.camera,
        selection: snapshot.selection,
        expansions: [...snapshot.expansions],
        timelineSelection: snapshot.timelineSelection,
        nodeKindFilters: { ...snapshot.nodeKindFilters },
        edgeClassFilters: { ...snapshot.edgeClassFilters },
        activeView: snapshot.activeView,
      }
    }

    case 'RESET_VIEW':
      // Exploration recovery (D-49): expansions, focus, and temporary state
      // clear; the view, filters, and camera stay.
      return {
        ...state,
        expansions: [],
        expansionHistory: [],
        focus: null,
        temporary: null,
      }

    case 'BACK_TO_OVERVIEW':
      // "Back to Episode Overview" recovery: bounded Story view restored,
      // exploration layers (expansions/focus/temporary) cleared, filters and
      // camera preserved (D-47: views do not silently reset Filters).
      return {
        ...state,
        activeView: 'episode_overview',
        expansions: [],
        expansionHistory: [],
        focus: null,
        temporary: null,
        selection: null,
      }

    default:
      return state
  }
}

export function useSceneState(
  initial: Partial<SceneState> = {},
): [SceneState, Dispatch<SceneAction>] {
  return useReducer(sceneReducer, {
    ...INITIAL_SCENE_STATE,
    ...initial,
  })
}
