// Scene reducer contract tests (10-04 Task 1, D-24/D-27, T10-FOCUS-04).
// Proves the scene state is fully serializable, tracks every scene slice
// (view, filters, selection, focus, camera, positions, expansions, timeline,
// Inspector, temporary restoration), and REFUSES unsafe focus/temporary ids.
import { describe, expect, it } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import {
  INITIAL_SCENE_STATE,
  sceneReducer,
  useSceneState,
  type SceneState,
} from './useSceneState'

describe('useSceneState', () => {
  it('initial state is the serializable default scene', () => {
    const { result } = renderHook(() => useSceneState())
    expect(result.current[0]).toEqual(INITIAL_SCENE_STATE)
    // D-24: React owns the scene — the whole state must survive a JSON
    // round-trip (no functions, no cy references, no DOM).
    const revived = JSON.parse(JSON.stringify(result.current[0])) as SceneState
    expect(revived).toEqual(result.current[0])
  })

  it('SET_VIEW switches the active view', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'SET_VIEW', view: 'investigation' }))
    expect(result.current[0].activeView).toBe('investigation')
  })

  it('filters toggle per kind/class and SET_ALL_FILTERS flips everything', () => {
    const { result } = renderHook(() => useSceneState({ nodeKindFilters: { Character: true, Event: true } }))
    act(() => result.current[1]({ type: 'SET_NODE_KIND_FILTER', kind: 'Event', visible: false }))
    expect(result.current[0].nodeKindFilters).toEqual({ Character: true, Event: false })
    act(() => result.current[1]({ type: 'SET_EDGE_CLASS_FILTER', edgeClass: 'Family', visible: false }))
    expect(result.current[0].edgeClassFilters).toEqual({ Family: false })
    act(() => result.current[1]({ type: 'SET_ALL_FILTERS', visible: true }))
    expect(result.current[0].nodeKindFilters).toEqual({ Character: true, Event: true })
    expect(result.current[0].edgeClassFilters).toEqual({ Family: true })
  })

  it('selection sets and clears without touching any other slice', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'SELECT', selection: { kind: 'node', id: 'char_dexter_morgan' } }))
    expect(result.current[0].selection).toEqual({ kind: 'node', id: 'char_dexter_morgan' })
    act(() => result.current[1]({ type: 'CLEAR_SELECTION' }))
    expect(result.current[0].selection).toBeNull()
  })

  it('SET_FOCUS accepts server-safe ids only; unsafe ids are refused (T10-FOCUS-04)', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'SET_FOCUS', nodeIds: ['char_dexter_morgan'], edgeIds: ['edge_1'] }))
    expect(result.current[0].focus).toEqual({ nodeIds: ['char_dexter_morgan'], edgeIds: ['edge_1'] })
    act(() => result.current[1]({ type: 'SET_FOCUS', nodeIds: ['bad id!'], edgeIds: [] }))
    expect(result.current[0].focus).toEqual({ nodeIds: ['char_dexter_morgan'], edgeIds: ['edge_1'] })
    act(() => result.current[1]({ type: 'CLEAR_FOCUS' }))
    expect(result.current[0].focus).toBeNull()
  })

  it('camera and positions are presentation-only state (never a fetch/relayout trigger)', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'SET_CAMERA', camera: { zoom: 1.5, pan: { x: 10, y: -20 } } }))
    expect(result.current[0].camera).toEqual({ zoom: 1.5, pan: { x: 10, y: -20 } })
    act(() =>
      result.current[1]({ type: 'SET_POSITIONS', positions: { a: { x: 1, y: 2 } } }),
    )
    act(() =>
      result.current[1]({ type: 'SET_POSITIONS', positions: { b: { x: 3, y: 4 } } }),
    )
    // Batched merge — both entries persist.
    expect(result.current[0].positions).toEqual({ a: { x: 1, y: 2 }, b: { x: 3, y: 4 } })
  })

  it('expansions add (deduped), remove, and clear; unsafe ids are refused', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'ADD_EXPANSION', nodeIds: ['loc_miami_metro', 'loc_miami_metro'] }))
    act(() => result.current[1]({ type: 'ADD_EXPANSION', nodeIds: ['char_rita_bennett'] }))
    expect(result.current[0].expansions).toEqual(['loc_miami_metro', 'char_rita_bennett'])
    act(() => result.current[1]({ type: 'ADD_EXPANSION', nodeIds: ['bad id!'] }))
    expect(result.current[0].expansions).toEqual(['loc_miami_metro', 'char_rita_bennett'])
    act(() => result.current[1]({ type: 'REMOVE_EXPANSION', nodeId: 'loc_miami_metro' }))
    expect(result.current[0].expansions).toEqual(['char_rita_bennett'])
    act(() => result.current[1]({ type: 'CLEAR_EXPANSIONS' }))
    expect(result.current[0].expansions).toEqual([])
  })

  it('expansion history undoes the newest record exactly; unsafe records refused (D-48)', () => {
    const { result } = renderHook(() => useSceneState())
    act(() =>
      result.current[1]({
        type: 'ADD_EXPANSION',
        nodeIds: ['char_debra_morgan'],
        record: { anchorId: 'char_dexter_morgan', key: 'family', additionIds: ['char_debra_morgan'] },
      }),
    )
    act(() =>
      result.current[1]({
        type: 'ADD_EXPANSION',
        nodeIds: ['char_angel_batista'],
        record: { anchorId: 'char_dexter_morgan', key: 'work', additionIds: ['char_angel_batista'] },
      }),
    )
    expect(result.current[0].expansions).toEqual(['char_debra_morgan', 'char_angel_batista'])

    // Unsafe record ids never enter state.
    act(() =>
      result.current[1]({
        type: 'ADD_EXPANSION',
        nodeIds: ['bad id'],
        record: { anchorId: 'char_dexter_morgan', key: 'family', additionIds: ['bad id'] },
      }),
    )
    expect(result.current[0].expansions).toEqual(['char_debra_morgan', 'char_angel_batista'])

    // Undo pops the newest (work) record — only its additions disappear.
    act(() => result.current[1]({ type: 'UNDO_EXPANSION' }))
    expect(result.current[0].expansions).toEqual(['char_debra_morgan'])
    expect(result.current[0].expansionHistory).toEqual([
      { anchorId: 'char_dexter_morgan', key: 'family', additionIds: ['char_debra_morgan'] },
    ])

    act(() => result.current[1]({ type: 'UNDO_EXPANSION' }))
    expect(result.current[0].expansions).toEqual([])
    // No-op when history is empty.
    act(() => result.current[1]({ type: 'UNDO_EXPANSION' }))
    expect(result.current[0].expansions).toEqual([])
  })

  it('COLLAPSE_EXPANSION removes every record rooted at the anchor', () => {
    const { result } = renderHook(() => useSceneState())
    const record = (key: string, additionIds: string[]) => ({
      type: 'ADD_EXPANSION' as const,
      nodeIds: additionIds,
      record: { anchorId: 'char_dexter_morgan', key, additionIds },
    })
    act(() => result.current[1](record('family', ['char_debra_morgan'])))
    act(() => result.current[1](record('work', ['char_angel_batista'])))
    act(() =>
      result.current[1]({
        type: 'ADD_EXPANSION',
        nodeIds: ['loc_miami_metro'],
        record: { anchorId: 'char_debra_morgan', key: 'locations', additionIds: ['loc_miami_metro'] },
      }),
    )

    act(() => result.current[1]({ type: 'COLLAPSE_EXPANSION', anchorId: 'char_dexter_morgan' }))
    expect(result.current[0].expansions).toEqual(['loc_miami_metro'])
    expect(result.current[0].expansionHistory).toEqual([
      { anchorId: 'char_debra_morgan', key: 'locations', additionIds: ['loc_miami_metro'] },
    ])
  })

  it('BACK_TO_OVERVIEW restores the bounded Story view, keeps filters and camera (D-47/D-49)', () => {
    const { result } = renderHook(() =>
      useSceneState({ nodeKindFilters: { Character: false } }),
    )
    act(() => result.current[1]({ type: 'SET_VIEW', view: 'investigation' }))
    act(() => result.current[1]({ type: 'SET_CAMERA', camera: { zoom: 1.5, pan: { x: 1, y: 2 } } }))
    act(() => result.current[1]({ type: 'ADD_EXPANSION', nodeIds: ['char_debra_morgan'] }))
    act(() => result.current[1]({ type: 'SET_FOCUS', nodeIds: ['char_dexter_morgan'], edgeIds: [] }))
    act(() => result.current[1]({ type: 'SELECT', selection: { kind: 'node', id: 'char_dexter_morgan' } }))

    act(() => result.current[1]({ type: 'BACK_TO_OVERVIEW' }))
    const state = result.current[0]
    expect(state.activeView).toBe('episode_overview')
    expect(state.expansions).toEqual([])
    expect(state.expansionHistory).toEqual([])
    expect(state.focus).toBeNull()
    expect(state.selection).toBeNull()
    expect(state.nodeKindFilters).toEqual({ Character: false })
    expect(state.camera).toEqual({ zoom: 1.5, pan: { x: 1, y: 2 } })
  })

  it('timeline selection and Inspector state are tracked', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'SET_TIMELINE_SELECTION', nodeIds: ['event_first_kill'] }))
    expect(result.current[0].timelineSelection).toEqual(['event_first_kill'])
    act(() => result.current[1]({ type: 'SET_TIMELINE_SELECTION', nodeIds: null }))
    expect(result.current[0].timelineSelection).toBeNull()
    act(() => result.current[1]({ type: 'SET_INSPECTOR', open: true, tab: 'evidence' }))
    expect(result.current[0].inspector).toEqual({ open: true, tab: 'evidence' })
    act(() => result.current[1]({ type: 'SET_INSPECTOR', tab: 'sources' }))
    expect(result.current[0].inspector).toEqual({ open: true, tab: 'sources' })
  })

  it('OPEN_TEMPORARY snapshots the scene; CLOSE_TEMPORARY restores it exactly (D-27)', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'SET_CAMERA', camera: { zoom: 2, pan: { x: 5, y: 6 } } }))
    act(() => result.current[1]({ type: 'SELECT', selection: { kind: 'node', id: 'char_dexter_morgan' } }))
    act(() => result.current[1]({ type: 'ADD_EXPANSION', nodeIds: ['char_rita_bennett'] }))
    act(() => result.current[1]({ type: 'SET_TIMELINE_SELECTION', nodeIds: ['event_first_kill'] }))

    act(() => result.current[1]({ type: 'OPEN_TEMPORARY', kind: 'answer_graph', nodeIds: ['char_ice_truck_killer'] }))
    expect(result.current[0].temporary?.kind).toBe('answer_graph')
    expect(result.current[0].temporary?.snapshot.camera).toEqual({ zoom: 2, pan: { x: 5, y: 6 } })

    // Scene state changes while the Answer Graph is open...
    act(() => result.current[1]({ type: 'SET_CAMERA', camera: { zoom: 0.5, pan: { x: 0, y: 0 } } }))
    act(() => result.current[1]({ type: 'SELECT', selection: null }))
    act(() => result.current[1]({ type: 'CLEAR_EXPANSIONS' }))
    act(() => result.current[1]({ type: 'SET_TIMELINE_SELECTION', nodeIds: null }))

    // ...and CLOSE_TEMPORARY restores the pre-Answer-Graph scene.
    act(() => result.current[1]({ type: 'CLOSE_TEMPORARY' }))
    const state = result.current[0]
    expect(state.temporary).toBeNull()
    expect(state.camera).toEqual({ zoom: 2, pan: { x: 5, y: 6 } })
    expect(state.selection).toEqual({ kind: 'node', id: 'char_dexter_morgan' })
    expect(state.expansions).toEqual(['char_rita_bennett'])
    expect(state.timelineSelection).toEqual(['event_first_kill'])
  })

  it('OPEN_TEMPORARY refuses unsafe node ids (restoration can never leak hidden state)', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'OPEN_TEMPORARY', kind: 'answer_graph', nodeIds: ['unsafe id'] }))
    expect(result.current[0].temporary).toBeNull()
  })

  it('CLOSE_TEMPORARY without an open temporary is a no-op', () => {
    const { result } = renderHook(() => useSceneState())
    act(() => result.current[1]({ type: 'CLOSE_TEMPORARY' }))
    expect(result.current[0]).toEqual(INITIAL_SCENE_STATE)
  })

  it('RESET_VIEW clears expansions/focus/temporary but keeps view, filters, and camera (D-49)', () => {
    const { result } = renderHook(() =>
      useSceneState({
        activeView: 'investigation',
        camera: { zoom: 1.2, pan: { x: 1, y: 1 } },
      }),
    )
    act(() => result.current[1]({ type: 'ADD_EXPANSION', nodeIds: ['a'] }))
    act(() => result.current[1]({ type: 'SET_FOCUS', nodeIds: ['b'], edgeIds: [] }))
    act(() => result.current[1]({ type: 'SET_NODE_KIND_FILTER', kind: 'Event', visible: false }))
    act(() => result.current[1]({ type: 'RESET_VIEW' }))
    const state = result.current[0]
    expect(state.expansions).toEqual([])
    expect(state.focus).toBeNull()
    expect(state.temporary).toBeNull()
    expect(state.activeView).toBe('investigation')
    expect(state.camera).toEqual({ zoom: 1.2, pan: { x: 1, y: 1 } })
    expect(state.nodeKindFilters).toEqual({ Event: false })
  })

  it('unknown actions return the state unchanged (reducer purity)', () => {
    const state = sceneReducer(INITIAL_SCENE_STATE, { type: 'NOPE' } as never)
    expect(state).toBe(INITIAL_SCENE_STATE)
  })
})
