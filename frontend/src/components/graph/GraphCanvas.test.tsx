import { beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { GraphCanvas } from './GraphCanvas'
import { graphResponseS01E01, graphResponseS01E03 } from '../../test/fixtures/graphResponse'

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

function resetFakeCytoscape() {
  registry = new Map()
  handlers = {}
  fitCalls = []
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
    connectedEdges: () => makeCollection([]),
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
  function CytoscapeComponentStub(props: {
    elements: CapturedElement[]
    cy?: (cy: unknown) => void
    minZoom?: number
    maxZoom?: number
  }) {
    capturedElements = props.elements
    capturedProps = { minZoom: props.minZoom, maxZoom: props.maxZoom }
    for (const el of props.elements) ensureRegistered(el.data.id as string)

    const fakeCy = {
      on: (event: string, selectorOrHandler: unknown, maybeHandler?: Handler) => {
        const selector = typeof selectorOrHandler === 'string' ? selectorOrHandler : undefined
        const handler = (maybeHandler ?? selectorOrHandler) as Handler
        const key = selector ? `${event}:${selector}` : event
        handlers[key] = handlers[key] ?? []
        handlers[key].push(handler)
      },
      container: () => null,
      elements: () => makeCollection(allIds()),
      getElementById: (id: string) => makeCollection(registry.has(id) ? [id] : []),
      collection: () => makeCollection([]),
      fit: (elements: FakeCollection, padding: unknown) => {
        fitCalls.push({ ids: elements?.ids ?? [], padding })
      },
    }
    props.cy?.(fakeCy)

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
})

describe('GraphCanvas', () => {
  it('renders elements corresponding to the S01E01 fixture node and edge ids', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

    const renderedNodeIds = nodeElements(capturedElements).map((n) => n.data.id)
    const renderedEdgeIds = edgeElements(capturedElements).map((e) => e.data.id)

    expect(graphResponseS01E01.nodes.every((n) => renderedNodeIds.includes(n.id))).toBe(true)
    expect(graphResponseS01E01.edges.every((e) => renderedEdgeIds.includes(e.id))).toBe(true)
  })

  it('renders elements corresponding to the S01E03 fixture after a boundary change', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

    const renderedNodeIds = nodeElements(capturedElements).map((n) => n.data.id)
    expect(graphResponseS01E03.nodes.every((n) => renderedNodeIds.includes(n.id))).toBe(true)
  })

  it('maps every node to a data(nodeType), including Episode and Series (no default-ellipse fallthrough)', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

    const nodes = nodeElements(capturedElements)
    expect(nodes.some((node) => node.data.nodeType === 'Episode')).toBe(true)
    expect(nodes.some((node) => node.data.nodeType === 'Series')).toBe(true)
  })

  it('never filters elements by visible_from_order (pure pass-through of the fetched GraphResponse)', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

    const nodeIds = nodeElements(capturedElements).map((node) => node.data.id)
    expect(nodeIds).toEqual(expect.arrayContaining(graphResponseS01E01.nodes.map((node) => node.id)))
  })

  it('passes minZoom={0.3} and maxZoom={2.5} to CytoscapeComponent', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

    expect(capturedProps.minZoom).toBe(0.3)
    expect(capturedProps.maxZoom).toBe(2.5)
  })

  it('includes claimStatus in edge data for edges with a claim', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

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
    const { container } = render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

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
})
