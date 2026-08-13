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
import type { VisualizationViewType } from '../types/graph'

export type SceneCamera = { zoom: number; pan: { x: number; y: number } }

export type ScenePosition = { x: number; y: number }

export type SceneSelection =
  | { kind: 'node' | 'edge'; id: string }
  | null

// Server-safe focus: ids only (never labels, never derived data). An empty
// array means "focus cleared".
export type SceneFocus = { nodeIds: string[]; edgeIds: string[] } | null

export type SceneInspector = { open: boolean; tab: string }

// Snapshot taken when a temporary scene (Answer Graph) opens, so closing it
// restores camera, selection, expansions, and timeline state (D-27).
export type TemporarySnapshot = {
  camera: SceneCamera | null
  selection: SceneSelection
  expansions: string[]
  timelineSelection: string[] | null
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
  | { type: 'ADD_EXPANSION'; nodeIds: string[] }
  | { type: 'REMOVE_EXPANSION'; nodeId: string }
  | { type: 'CLEAR_EXPANSIONS' }
  | { type: 'SET_TIMELINE_SELECTION'; nodeIds: string[] | null }
  | { type: 'SET_INSPECTOR'; open?: boolean; tab?: string }
  | { type: 'OPEN_TEMPORARY'; kind: 'answer_graph'; nodeIds: string[] }
  | { type: 'CLOSE_TEMPORARY' }
  | { type: 'RESET_VIEW' }

export const INITIAL_SCENE_STATE: SceneState = {
  activeView: 'episode_overview',
  nodeKindFilters: {},
  edgeClassFilters: {},
  selection: null,
  focus: null,
  camera: null,
  positions: {},
  expansions: [],
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
      const seen = new Set(state.expansions)
      for (const id of action.nodeIds) seen.add(id)
      return { ...state, expansions: [...seen] }
    }

    case 'REMOVE_EXPANSION':
      return {
        ...state,
        expansions: state.expansions.filter((id) => id !== action.nodeId),
      }

    case 'CLEAR_EXPANSIONS':
      return { ...state, expansions: [] }

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
      // (D-27): camera, selection, expansions, timeline state.
      const { snapshot } = state.temporary
      return {
        ...state,
        temporary: null,
        camera: snapshot.camera,
        selection: snapshot.selection,
        expansions: [...snapshot.expansions],
        timelineSelection: snapshot.timelineSelection,
      }
    }

    case 'RESET_VIEW':
      // Exploration recovery (D-49): expansions, focus, and temporary state
      // clear; the view, filters, and camera stay.
      return {
        ...state,
        expansions: [],
        focus: null,
        temporary: null,
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
