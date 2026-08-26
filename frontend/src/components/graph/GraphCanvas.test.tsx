import { beforeEach, describe, expect, it, vi } from 'vitest'
import { StrictMode, useMemo } from 'react'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GraphCanvas } from './GraphCanvas'
import { __resetAutoZoomStateForTests } from './autoZoomHold'
import { __resetPositionCacheForTests } from '../../lib/graph/positionCache'
import { graphResponseS01E01, graphResponseS01E03 } from '../../test/fixtures/graphResponse'
import type { VisualizationDTO } from '../../types/graph'

// 10-04: minimal neutral-DTO fixture (mirrors the 10-03 wire shape) for the
// visualization path — see the domain contract in
// spoilerless/app/domain/visualization.py.
function makeVisualizationDto(overrides: Partial<VisualizationDTO> = {}): VisualizationDTO {
  return {
    metadata: {
      projection_version: '1.0.0',
      view_type: 'episode_overview',
      series_id: 'series_dexter',
      series_title: 'Dexter',
      episode_order: 1,
      visible_until_order: 1,
      effective_view_order: 1,
    },
    nodes: [
      { id: 'char_dexter_morgan', kind: 'Character', label: 'Dexter Morgan', display_tier: 1, order: 1, episode_id: 'dexter_s01e01', image_url: null, image_source_url: null, origin: 'canonical' },
      { id: 'char_debra_morgan', kind: 'Character', label: 'Debra Morgan', display_tier: 1, order: 1, episode_id: 'dexter_s01e01', image_url: null, image_source_url: null, origin: 'canonical' },
      { id: 'event_first_kill', kind: 'Event', label: 'Dexter kills Mike Donovan', display_tier: 2, order: 1, episode_id: 'dexter_s01e01', image_url: null, image_source_url: null, origin: 'canonical' },
    ],
    edges: [
      { id: 'edge_family', source: 'char_dexter_morgan', target: 'char_debra_morgan', relation_class: 'Family', order: 1, claim_id: 'claim_1', origin: 'canonical' },
      { id: 'edge_occurred', source: 'char_dexter_morgan', target: 'event_first_kill', relation_class: 'Participated in', order: 1, claim_id: null, origin: 'canonical' },
    ],
    groups: [{ id: 'thread_main', label: 'Main plot', node_ids: ['char_dexter_morgan', 'char_debra_morgan'] }],
    timeline: [],
    focus: null,
    ...overrides,
  }
}

// 08-06: graphToElements prunes isolated (degree-0) nodes — these
// expectations mirror that topology filter: every CONNECTED fixture node
// must render, every isolated one must not. The pass-through guarantee
// (never filter by visible_from_order) is untouched by the prune.
const connectedNodeIds = (graph: typeof graphResponseS01E01): Set<string> => {
  const ids = new Set<string>()
  for (const edge of graph.edges) {
    ids.add(edge.source)
    ids.add(edge.target)
  }
  return ids
}

// react-cytoscapejs renders to a <canvas> with no real hit-testing under
// jsdom. This component test only needs to assert what GraphCanvas.tsx
// passes as its `elements` prop at each boundary (must_haves truth: element
// counts track the backend boundary exactly) — it doesn't need to exercise
// real tap/selection behavior (that's App.test.tsx's end-to-end scope). The
// stub captures the last-rendered `elements` prop and provides just enough
// of a fake `cy` surface (`on`, `container`, no `layout`) that GraphCanvas's
// real registration code (mouseover/mouseout/tap listeners, the `runLayout`
// effect guarded by `typeof cy.layout !== 'function'`) doesn't throw.
//
// 06-10: the fake `cy` also grows a minimal, persistent (across re-renders)
// element/class registry — `getElementById`/`collection`/`elements`/`fit` —
// so the new `focusedElementIds` effect (and, for the "tap still works after
// a focus update" truth, the pre-existing tap-to-select handlers) can be
// exercised against real class-application behavior, not just prop capture.
type CapturedElement = { data: Record<string, unknown> }
let capturedElements: CapturedElement[] = []
let capturedProps: Record<string, unknown> = {}

type FakeCollection = {
  ids: string[]
  length: number
  connectedEdges: () => FakeCollection
  addClass: (cls: string) => FakeCollection
  removeClass: (cls: string) => FakeCollection
  merge: (other: FakeCollection) => FakeCollection
  difference: (other: FakeCollection) => FakeCollection
}

type FakeElementHandle = {
  id: () => string
  data: (field: string) => unknown
  addClass: (cls: string) => FakeElementHandle
  removeClass: (cls: string) => FakeElementHandle
  closedNeighborhood: () => FakeCollection
  connectedEdges: () => FakeCollection
  connectedNodes: () => FakeCollection
}

type Handler = (evt: unknown) => void

let registry: Map<string, Set<string>> = new Map()
let handlers: Record<string, Handler[]> = {}
let fitCalls: Array<{ ids: string[]; padding: unknown }> = []
// nodeId -> connected edge ids, built from the captured elements so the fake
// cy's `connectedEdges()` mirrors the real graph (label-visible assertions).
let edgeAdj: Map<string, string[]> = new Map()
// The fake cy instance handed to GraphCanvas via props.cy — background-tap
// simulations must pass this SAME object (the empty-tap handler checks
// `evt.target === cy`).
let capturedCy: unknown = null
// Layout spy: records the options each cy.layout() call receives (runLayout
// becomes reachable once the fake exposes `layout`) — plus the cy instance
// the layout ran on, so tests can assert the LIVE instance was refreshed
// (StrictMode double-mount produces a dead cy#1 and a live cy#2).
let layoutCalls: Array<{ fit: unknown; cy: unknown; name?: unknown }> = []

function resetFakeCytoscape() {
  registry = new Map()
  handlers = {}
  fitCalls = []
  edgeAdj = new Map()
  capturedCy = null
  layoutCalls = []
}

// Real cytoscape.js accepts a space-separated class list to addClass/
// removeClass (e.g. `cy.elements().removeClass('selected-dominant faded')`,
// exactly as GraphCanvas.tsx's tap handlers and the new focus effect both
// do) — split accordingly rather than treating the whole string as one class.
function splitClasses(cls: string): string[] {
  return cls.split(/\s+/).filter(Boolean)
}

function makeCollection(ids: string[]): FakeCollection {
  const collection: FakeCollection = {
    ids,
    length: ids.length,
    // Real cytoscape collections expose connectedEdges(); the focus effect
    // resolves focused nodes via getElementById (a 1-element collection) and
    // calls connectedEdges() on it — mirror that here from edgeAdj.
    connectedEdges: () => makeCollection(collection.ids.flatMap((id) => edgeAdj.get(id) ?? [])),
    addClass: (cls) => {
      for (const id of collection.ids) {
        for (const single of splitClasses(cls)) registry.get(id)?.add(single)
      }
      return collection
    },
    removeClass: (cls) => {
      for (const id of collection.ids) {
        for (const single of splitClasses(cls)) registry.get(id)?.delete(single)
      }
      return collection
    },
    // Mutating, per real cytoscape.js semantics (`eles.merge()` modifies the
    // calling collection and returns it — distinct from the immutable
    // `.union()`).
    merge: (other) => {
      for (const id of other.ids) {
        if (!collection.ids.includes(id)) collection.ids.push(id)
      }
      collection.length = collection.ids.length
      return collection
    },
    // Immutable, per real cytoscape.js semantics.
    difference: (other) => makeCollection(collection.ids.filter((id) => !other.ids.includes(id))),
  }
  return collection
}

function ensureRegistered(id: string) {
  if (!registry.has(id)) registry.set(id, new Set())
}

function classesFor(id: string): Set<string> {
  return registry.get(id) ?? new Set()
}

function allIds(): string[] {
  return [...registry.keys()]
}

function makeElementHandle(id: string, data: Record<string, unknown>): FakeElementHandle {
  const handle: FakeElementHandle = {
    id: () => id,
    data: (field) => data[field],
    addClass: (cls) => {
      for (const single of splitClasses(cls)) registry.get(id)?.add(single)
      return handle
    },
    removeClass: (cls) => {
      for (const single of splitClasses(cls)) registry.get(id)?.delete(single)
      return handle
    },
    closedNeighborhood: () => makeCollection([id]),
    connectedEdges: () => makeCollection(edgeAdj.get(id) ?? []),
    connectedNodes: () => makeCollection([]),
  }
  return handle
}

function simulateTap(kind: 'node' | 'edge', id: string) {
  const el = capturedElements.find((element) => element.data.id === id)
  if (!el) throw new Error(`no captured element for id ${id}`)
  const target = makeElementHandle(id, el.data)
  handlers[`tap:${kind}`]?.forEach((h) => h({ target }))
}

function simulateBackgroundTap(fakeCy: unknown) {
  handlers['tap']?.forEach((h) => h({ target: fakeCy }))
}

vi.mock('react-cytoscapejs', () => {
  // 08-10: real react-cytoscapejs hands the SAME cy instance to props.cy on
  // every update and a NEW one on remount (StrictMode double-mount
  // included) — GraphCanvas's per-cy layout guard keys on that identity.
  // Memoize per mount so the fake mirrors the real instance lifecycle.
  function makeFakeCy() {
    const oneHandlers: Record<string, Handler[]> = {}
    const fakeCy = {
      on: (event: string, selectorOrHandler: unknown, maybeHandler?: Handler) => {
        const selector = typeof selectorOrHandler === 'string' ? selectorOrHandler : undefined
        const handler = (maybeHandler ?? selectorOrHandler) as Handler
        const key = selector ? `${event}:${selector}` : event
        handlers[key] = handlers[key] ?? []
        handlers[key].push(handler)
      },
      one: (event: string, handler: Handler) => {
        oneHandlers[event] = oneHandlers[event] ?? []
        oneHandlers[event].push(handler)
      },
      emitOne: (event: string) => {
        const pending = oneHandlers[event] ?? []
        oneHandlers[event] = []
        pending.forEach((handler) => handler({ target: fakeCy }))
      },
      container: () => null,
      elements: () => makeCollection(allIds()),
      getElementById: (id: string) => makeCollection(registry.has(id) ? [id] : []),
      collection: () => makeCollection([]),
      fit: (elements: FakeCollection, padding: unknown) => {
        fitCalls.push({ ids: elements?.ids ?? [], padding })
      },
      // 08-06+ auto-zoom-hold: runLayout is reachable once `layout` exists —
      // record the options (esp. `fit`) so the suppression is assertable.
      layout: (opts: Record<string, unknown>) => {
        layoutCalls.push({ fit: opts.fit, cy: fakeCy, name: opts.name })
        return { one: () => {}, run: () => {} }
      },
    }
    return fakeCy
  }
  function CytoscapeComponentStub(props: {
    elements: CapturedElement[]
    cy?: (cy: unknown) => void
    minZoom?: number
    maxZoom?: number
    layout?: unknown
  }) {
    capturedElements = props.elements
    capturedProps = { minZoom: props.minZoom, maxZoom: props.maxZoom, layout: props.layout }
    for (const el of props.elements) ensureRegistered(el.data.id as string)
    edgeAdj = new Map()
    for (const el of props.elements) {
      const data = el.data as Record<string, unknown>
      if (typeof data.source === 'string' && typeof data.target === 'string') {
        const edgeId = data.id as string
        const src = data.source
        const tgt = data.target
        edgeAdj.set(src, [...(edgeAdj.get(src) ?? []), edgeId])
        edgeAdj.set(tgt, [...(edgeAdj.get(tgt) ?? []), edgeId])
      }
    }

    const fakeCy = useMemo(() => makeFakeCy(), [])
    props.cy?.(fakeCy)
    ;(fakeCy as { emitOne: (event: string) => void }).emitOne('layoutstop')
    capturedCy = fakeCy

    return (
      <div data-testid="graph-canvas-stub">
        {props.elements.map((el) => (
          <div key={el.data.id as string} data-testid={`graph-element-${el.data.id}`} />
        ))}
        <div data-testid="graph-canvas-background" onClick={() => simulateBackgroundTap(fakeCy)} />
      </div>
    )
  }
  return { default: CytoscapeComponentStub }
})

function nodeElements(elements: CapturedElement[]) {
  return elements.filter((el) => !('source' in el.data))
}

function edgeElements(elements: CapturedElement[]) {
  return elements.filter((el) => 'source' in el.data)
}

beforeEach(() => {
  resetFakeCytoscape()
  // The module-level interaction state survives component remounts (by
  // design, for the 20s hold) — clear it so tests are isolated.
  __resetAutoZoomStateForTests()
  // 10-04: the position cache is module-level too (stored presets, D-23) —
  // clear it so layout/stability tests are isolated.
  __resetPositionCacheForTests()
})

describe('GraphCanvas', () => {
  it('renders elements corresponding to the S01E01 fixture node and edge ids', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    const renderedNodeIds = nodeElements(capturedElements).map((n) => n.data.id)
    const renderedEdgeIds = edgeElements(capturedElements).map((e) => e.data.id)

    const connected = connectedNodeIds(graphResponseS01E01)
    expect(
      graphResponseS01E01.nodes
        .filter((n) => connected.has(n.id))
        .every((n) => renderedNodeIds.includes(n.id)),
    ).toBe(true)
    expect(
      graphResponseS01E01.nodes
        .filter((n) => !connected.has(n.id))
        .every((n) => !renderedNodeIds.includes(n.id)),
    ).toBe(true)
    expect(graphResponseS01E01.edges.every((e) => renderedEdgeIds.includes(e.id))).toBe(true)
  })

  it('renders elements corresponding to the S01E03 fixture after a boundary change', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    const renderedNodeIds = nodeElements(capturedElements).map((n) => n.data.id)
    const connected = connectedNodeIds(graphResponseS01E03)
    expect(
      graphResponseS01E03.nodes
        .filter((n) => connected.has(n.id))
        .every((n) => renderedNodeIds.includes(n.id)),
    ).toBe(true)
  })

  it('maps every node to a data(nodeType), including Episode and Series (no default-ellipse fallthrough)', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    const nodes = nodeElements(capturedElements)
    expect(nodes.some((node) => node.data.nodeType === 'Episode')).toBe(true)
    expect(nodes.some((node) => node.data.nodeType === 'Series')).toBe(true)
  })

  it('never filters elements by visible_from_order (pure pass-through of the fetched GraphResponse)', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    const nodeIds = nodeElements(capturedElements).map((node) => node.data.id)
    // The pass-through guarantee is about visible_from_order (never filtered
    // client-side); the 08-06 isolated-node prune is topology-only and must
    // not remove connected nodes.
    const connected = connectedNodeIds(graphResponseS01E01)
    expect(nodeIds).toEqual(
      expect.arrayContaining(
        graphResponseS01E01.nodes.filter((n) => connected.has(n.id)).map((node) => node.id),
      ),
    )
  })

  it('passes minZoom={0.3} and maxZoom={2.5} to CytoscapeComponent', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    expect(capturedProps.minZoom).toBe(0.3)
    expect(capturedProps.maxZoom).toBe(2.5)
  })

  it('includes claimStatus in edge data for edges with a claim', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    // edge_4 (FAMILY_OF, claim_id='claim_3', status='canonical') should have claimStatus='canonical'
    const edge4 = edgeElements(capturedElements).find((e) => e.data.id === 'edge_4')
    expect(edge4).toBeDefined()
    expect(edge4!.data.claimStatus).toBe('canonical')

    // edge_6 (OCCURRED_IN, claim_id='claim_4', status='candidate') should have claimStatus='candidate'
    const edge6 = edgeElements(capturedElements).find((e) => e.data.id === 'edge_6')
    expect(edge6).toBeDefined()
    expect(edge6!.data.claimStatus).toBe('candidate')

    // edge_1 (PART_OF, claim_id=null) should NOT have claimStatus
    const edge1 = edgeElements(capturedElements).find((e) => e.data.id === 'edge_1')
    expect(edge1).toBeDefined()
    expect(edge1!.data.claimStatus).toBeUndefined()
  })

  it('renders within a graph-canvas-backdrop wrapper div', () => {
    const { container } = render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

    const backdrop = container.querySelector('.graph-canvas-backdrop')
    expect(backdrop).toBeTruthy()
  })

  describe('focusedElementIds (06-10, RAG-17)', () => {
    it('applies .selected-dominant to every named node/edge and .faded to everything else', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={null}
        />,
      )

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={{ nodeIds: ['char_dexter_morgan', 'char_angel_batista'], edgeIds: ['edge_1'] }}
        />,
      )

      expect(classesFor('char_dexter_morgan').has('selected-dominant')).toBe(true)
      expect(classesFor('char_angel_batista').has('selected-dominant')).toBe(true)
      expect(classesFor('edge_1').has('selected-dominant')).toBe(true)
      expect(classesFor('char_debra_morgan').has('faded')).toBe(true)
      expect(classesFor('char_dexter_morgan').has('faded')).toBe(false)
    })

    it('clears .selected-dominant/.faded from all elements when focusedElementIds transitions to null', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={{ nodeIds: ['char_dexter_morgan'], edgeIds: [] }}
        />,
      )
      expect(classesFor('char_dexter_morgan').has('selected-dominant')).toBe(true)
      expect(classesFor('char_debra_morgan').has('faded')).toBe(true)

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={null}
        />,
      )

      expect(classesFor('char_dexter_morgan').has('selected-dominant')).toBe(false)
      expect(classesFor('char_debra_morgan').has('faded')).toBe(false)
    })

    it('calls cy.fit with the focused elements and the same padding=48 GraphControls.tsx uses', () => {
      render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={{ nodeIds: ['char_dexter_morgan'], edgeIds: [] }}
        />,
      )

      expect(fitCalls).toHaveLength(1)
      expect(fitCalls[0]?.padding).toBe(48)
      expect(fitCalls[0]?.ids).toEqual(['char_dexter_morgan'])
    })

    it('silently drops a focusedElementIds reference that does not resolve to any rendered element (no throw)', () => {
      expect(() =>
        render(
          <GraphCanvas
            graph={graphResponseS01E01}
            onSelect={() => {}}
            seriesId="series:dexter"
            episodes={[]}
            focusedElementIds={{ nodeIds: ['char_dexter_morgan', 'node_does_not_exist'], edgeIds: [] }}
          />,
        ),
      ).not.toThrow()

      expect(classesFor('char_dexter_morgan').has('selected-dominant')).toBe(true)
    })

    it('does not break tap-to-select: a direct tap on a third node still works immediately after a focusedElementIds update', () => {
      const onSelect = vi.fn()
      render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={onSelect}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={{ nodeIds: ['char_dexter_morgan', 'char_angel_batista'], edgeIds: [] }}
        />,
      )

      expect(classesFor('char_debra_morgan').has('faded')).toBe(true)

      simulateTap('node', 'char_debra_morgan')

      expect(onSelect).toHaveBeenCalledWith({
        kind: 'node',
        id: 'char_debra_morgan',
        label: 'Debra Morgan',
        nodeType: 'Character',
      })
      expect(classesFor('char_debra_morgan').has('selected-dominant')).toBe(true)
    })
  })

  describe('GraphFocusIndicator (06-10, RAG-17)', () => {
    it('renders "Highlighting {N}" only when a focus is active, with a working Clear action', async () => {
      const user = userEvent.setup()
      const onClearFocus = vi.fn()
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={null}
          onClearFocus={onClearFocus}
        />,
      )

      expect(screen.queryByText(/Highlighting/)).not.toBeInTheDocument()

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={{ nodeIds: ['char_dexter_morgan', 'char_angel_batista'], edgeIds: ['edge_1'] }}
          onClearFocus={onClearFocus}
        />,
      )

      expect(screen.getByText('Highlighting 3')).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: 'Clear' }))
      expect(onClearFocus).toHaveBeenCalledTimes(1)
    })
  })

  describe('newlyRevealedIds (FEAT-03, 09-07)', () => {
    it('applies .newly-revealed to every named node/edge and auto-clears after 4000ms', () => {
      vi.useFakeTimers()
      try {
        const onNewlyRevealedDone = vi.fn()
        const { rerender } = render(
          <GraphCanvas
            graph={graphResponseS01E01}
            onSelect={() => {}}
            seriesId="series:dexter"
            episodes={[]}
            newlyRevealedIds={null}
          />,
        )

        rerender(
          <GraphCanvas
            graph={graphResponseS01E01}
            onSelect={() => {}}
            seriesId="series:dexter"
            episodes={[]}
            newlyRevealedIds={{ nodeIds: ['char_dexter_morgan'], edgeIds: ['edge_1'] }}
            onNewlyRevealedDone={onNewlyRevealedDone}
          />,
        )

        expect(classesFor('char_dexter_morgan').has('newly-revealed')).toBe(true)
        expect(classesFor('edge_1').has('newly-revealed')).toBe(true)
        // Purely additive glow — elements outside the revealed set are
        // untouched (no .faded, no .selected-dominant side effects).
        expect(classesFor('char_debra_morgan').has('newly-revealed')).toBe(false)
        expect(classesFor('char_debra_morgan').has('faded')).toBe(false)

        act(() => {
          vi.advanceTimersByTime(4000)
        })

        expect(classesFor('char_dexter_morgan').has('newly-revealed')).toBe(false)
        expect(classesFor('edge_1').has('newly-revealed')).toBe(false)
        expect(onNewlyRevealedDone).toHaveBeenCalledTimes(1)
      } finally {
        vi.useRealTimers()
      }
    })

    it('a second advance replaces the first glow and never re-runs the layout', () => {
      vi.useFakeTimers()
      try {
        const { rerender } = render(
          <GraphCanvas
            graph={graphResponseS01E01}
            onSelect={() => {}}
            seriesId="series:dexter"
            episodes={[]}
            newlyRevealedIds={{ nodeIds: ['char_dexter_morgan'], edgeIds: [] }}
          />,
        )
        expect(classesFor('char_dexter_morgan').has('newly-revealed')).toBe(true)

        rerender(
          <GraphCanvas
            graph={graphResponseS01E01}
            onSelect={() => {}}
            seriesId="series:dexter"
            episodes={[]}
            newlyRevealedIds={{ nodeIds: ['char_angel_batista'], edgeIds: [] }}
          />,
        )
        expect(classesFor('char_dexter_morgan').has('newly-revealed')).toBe(false)
        expect(classesFor('char_angel_batista').has('newly-revealed')).toBe(true)

        // FEAT-03 must not re-run the layout: the glow effect never calls
        // cy.fit/cy.layout — fitCalls stays empty (GraphControls/runLayout
        // are the only fit/layout callers in this test harness).
        expect(fitCalls).toHaveLength(0)
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('Overview/Full modes (08-06+ presentation declutter)', () => {
    it('defaults to Overview: the curated subset, not every element', () => {
      render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

      const renderedNodeIds = nodeElements(capturedElements).map((n) => n.data.id)
      const renderedEdgeIds = edgeElements(capturedElements).map((e) => e.data.id)

      // Tier-1 fixture nodes render; tier-3 detail is hidden.
      for (const id of ['char_dexter_morgan', 'char_debra_morgan', 'char_angel_batista', 'loc_miami_metro', 'dexter_s01e01', 'series_dexter']) {
        expect(renderedNodeIds).toContain(id)
      }
      for (const id of ['event_first_kill', 'char_rita_bennett', 'char_james_doakes', 'char_ice_truck_killer']) {
        expect(renderedNodeIds).not.toContain(id)
      }
      // The user edge between kept nodes survives; the edge to the dropped
      // event does not.
      expect(renderedEdgeIds).toContain('user-rel:test-1')
      expect(renderedEdgeIds).not.toContain('edge_6')
    })

    it('switching to Full restores every element', async () => {
      const user = userEvent.setup()
      render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="overview" />)

      expect(nodeElements(capturedElements).map((n) => n.data.id)).not.toContain('event_first_kill')

      await user.click(screen.getByRole('button', { name: 'Full mode' }))

      const renderedNodeIds = nodeElements(capturedElements).map((n) => n.data.id)
      const renderedEdgeIds = edgeElements(capturedElements).map((e) => e.data.id)
      expect(renderedNodeIds).toContain('event_first_kill')
      expect(renderedEdgeIds).toContain('edge_6')
    })

    it('selecting a node reveals its incident edge labels; empty-tap clears them', () => {
      render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

      simulateTap('node', 'char_dexter_morgan')
      // edge_2 (dexter -> miami_metro) and edge_6 (dexter -> event) are both
      // incident to Dexter → labels visible.
      expect(classesFor('edge_2').has('label-visible')).toBe(true)
      expect(classesFor('edge_6').has('label-visible')).toBe(true)
      // An unrelated edge (edge_5, debra -> miami_metro) stays label-less.
      expect(classesFor('edge_5').has('label-visible')).toBe(false)

      simulateBackgroundTap(capturedCy)
      expect(classesFor('edge_2').has('label-visible')).toBe(false)
    })

    it('external focus (focusedElementIds) reveals labels for focused edges', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={null}
        />,
      )

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={{ nodeIds: ['char_dexter_morgan'], edgeIds: ['edge_1'] }}
        />,
      )

      expect(classesFor('edge_1').has('label-visible')).toBe(true)
      // Dexter's incident edges get labels through the node side of the focus.
      expect(classesFor('edge_2').has('label-visible')).toBe(true)
      expect(classesFor('edge_5').has('label-visible')).toBe(false)

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          focusedElementIds={null}
        />,
      )
      expect(classesFor('edge_1').has('label-visible')).toBe(false)
      expect(classesFor('edge_2').has('label-visible')).toBe(false)
    })
  })

  describe('auto zoom hold after touch (08-06+)', () => {
    it('lays out with fit:true when the screen has not been touched', () => {
      render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)

      expect(layoutCalls.length).toBeGreaterThan(0)
      expect(layoutCalls[layoutCalls.length - 1]?.fit).toBe(true)
    })

    it('a pointerdown within 20s suppresses the fit on the next graph-change layout', () => {
      const { rerender } = render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)
      expect(layoutCalls[layoutCalls.length - 1]?.fit).toBe(true)

      // User touches the screen anywhere — the listener is document-level.
      document.dispatchEvent(new Event('pointerdown'))

      // A graph change (new object identity) re-runs the layout; the recent
      // touch holds the viewport (fit:false, no auto zoom-out).
      rerender(
        <GraphCanvas graph={{ ...graphResponseS01E01 }} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />,
      )
      expect(layoutCalls[layoutCalls.length - 1]?.fit).toBe(false)
    })

    it('a mode switch still forces fit (explicit view action bypasses the hold)', async () => {
      const user = userEvent.setup()
      render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="overview" />)

      // Clicking the toggle both touches the screen AND changes the mode —
      // forceRelayout (mode switch) wins over the 20s hold.
      await user.click(screen.getByRole('button', { name: 'Full mode' }))

      expect(layoutCalls[layoutCalls.length - 1]?.fit).toBe(true)
    })

    it('keeps the CytoscapeComponent layout prop reference stable across graph-change re-renders (no per-render re-fit)', () => {
      const { rerender } = render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />)
      const first = capturedProps.layout
      // The declarative prop never fits — the post-layout launch refresh and
      // runLayout are the single fit authority.
      expect((first as { fit?: unknown }).fit).toBe(false)

      // A graph change re-renders — the memoized layout object must be the
      // SAME reference, or react-cytoscapejs re-runs the layout (the auto
      // zoom-out after interactions).
      rerender(
        <GraphCanvas graph={{ ...graphResponseS01E01 }} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />,
      )
      expect(capturedProps.layout).toBe(first)
    })

    it('rebuilds the layout prop only when the mode changes', async () => {
      const user = userEvent.setup()
      const { rerender } = render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="overview" />)
      const overviewLayout = capturedProps.layout

      rerender(
        <GraphCanvas graph={{ ...graphResponseS01E01 }} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="overview" />,
      )
      expect(capturedProps.layout).toBe(overviewLayout)

      await user.click(screen.getByRole('button', { name: 'Full mode' }))
      expect(capturedProps.layout).not.toBe(overviewLayout)
    })
  })

  describe('fresh cy instance auto-refresh (08-10)', () => {
    it('a remounted canvas (StrictMode double-mount) gets an automatic fitted layout on the LIVE cy', () => {
      // The app mounts GraphCanvas under <StrictMode> (main.tsx) — React's
      // dev double-mount destroys cy#1 and creates cy#2. The old guard
      // (graph-only dedupe) skipped runLayout on cy#2 → only the declarative
      // fit:false layout ran → the "diagonal" open view the user had to fix
      // by hand. The per-cy guard must force a fit:true layout on the LIVE
      // instance (the one props.cy last handed over).
      render(
        <StrictMode>
          <GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} initialMode="full" />
        </StrictMode>,
      )

      const lastCall = layoutCalls[layoutCalls.length - 1]
      expect(lastCall?.fit).toBe(true)
      expect(lastCall?.cy).toBe(capturedCy)
    })
  })

  describe('visualization DTO path (10-04, D-08/D-23/D-44)', () => {
    it('renders the neutral DTO through the adapter with deterministic ids (groups, nodes, edges)', () => {
      render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto()}
        />,
      )

      const ids = capturedElements.map((el) => el.data.id)
      expect(ids).toEqual([
        'group:thread_main',
        'char_dexter_morgan',
        'char_debra_morgan',
        'event_first_kill',
        'edge_family',
        'edge_occurred',
      ])
      const dexter = capturedElements.find((el) => el.data.id === 'char_dexter_morgan')!
      expect(dexter.data.nodeType).toBe('Character')
      expect(dexter.data.parent).toBe('group:thread_main')
      const edge = capturedElements.find((el) => el.data.id === 'edge_family')!
      expect(edge.data.label).toBe('Family')
    })

    it('never filters DTO elements client-side — high-order nodes still render (D-05)', () => {
      const dto = makeVisualizationDto({
        nodes: makeVisualizationDto().nodes.map((n) => ({ ...n, order: 999 })),
      })
      render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={dto}
        />,
      )

      const ids = capturedElements.map((el) => el.data.id)
      for (const node of dto.nodes) expect(ids).toContain(node.id)
      for (const edge of dto.edges) expect(ids).toContain(edge.id)
    })

    it('keeps the SAME Cytoscape instance across visualization re-renders (stable scene, D-24)', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto()}
        />,
      )
      const firstCy = capturedCy

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto({ metadata: { ...makeVisualizationDto().metadata, episode_order: 2 } })}
        />,
      )

      expect(capturedCy).toBe(firstCy)
    })

    it('retains the prior scene while a new view is loading (visualization=null) — no flash, no relayout', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto()}
        />,
      )
      const beforeIds = capturedElements.map((el) => el.data.id)
      const layoutCallsBefore = layoutCalls.length

      // Loading: the parent passes null; the canvas holds the last DTO.
      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={null}
        />,
      )

      expect(capturedElements.map((el) => el.data.id)).toEqual(beforeIds)
      expect(layoutCalls.length).toBe(layoutCallsBefore)
    })

    it('passes debugLabels only for the Advanced/full view (technical labels hidden elsewhere, D-14)', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto()}
        />,
      )
      expect(capturedElements.find((el) => el.data.id === 'char_dexter_morgan')?.data).not.toHaveProperty('debugLabel')

      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto({ metadata: { ...makeVisualizationDto().metadata, view_type: 'full' } })}
        />,
      )
      expect(capturedElements.find((el) => el.data.id === 'char_dexter_morgan')?.data.debugLabel).toBe('Character')
    })

    it('routes investigation to left-to-right dagre; other views stay fcose (D-25)', () => {
      const { rerender } = render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto({
            metadata: { ...makeVisualizationDto().metadata, view_type: 'investigation' },
          })}
        />,
      )

      // Declarative startup layout (react-cytoscapejs prop) is dagre LR…
      expect(capturedProps.layout).toMatchObject({ name: 'dagre', rankDir: 'LR' })
      // …and the imperative runLayout (Refresh-graph path) also picked dagre.
      expect(layoutCalls[layoutCalls.length - 1]?.name).toBe('dagre')

      // Switching to a story view returns to the force-directed engine.
      rerender(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto()}
        />,
      )
      expect(capturedProps.layout).toMatchObject({ name: 'fcose' })
      expect(layoutCalls[layoutCalls.length - 1]?.name).toBe('fcose')
    })

    it('selection/focus on the visualization path never re-runs the layout (D-22)', () => {
      render(
        <GraphCanvas
          graph={graphResponseS01E01}
          onSelect={() => {}}
          seriesId="series:dexter"
          episodes={[]}
          visualization={makeVisualizationDto()}
        />,
      )
      const layoutCallsBefore = layoutCalls.length

      simulateTap('node', 'char_dexter_morgan')
      expect(layoutCalls.length).toBe(layoutCallsBefore)
    })
  })
})
