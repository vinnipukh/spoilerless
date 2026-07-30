import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
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
type CapturedElement = { data: Record<string, unknown> }
let capturedElements: CapturedElement[] = []
let capturedProps: Record<string, unknown> = {}

vi.mock('react-cytoscapejs', () => {
  console.log('[MOCK] factory called')
  function CytoscapeComponentStub(props: {
    elements: CapturedElement[]
    cy?: (cy: unknown) => void
    minZoom?: number
    maxZoom?: number
  }) {
    console.log('[MOCK] component rendered, elements:', props.elements?.length)
    capturedElements = props.elements
    capturedProps = { minZoom: props.minZoom, maxZoom: props.maxZoom }
    props.cy?.({
      on: () => {},
      container: () => null,
    })
    return <div data-testid="graph-canvas-stub" />
  }
  return { default: CytoscapeComponentStub }
})

function nodeElements(elements: CapturedElement[]) {
  return elements.filter((el) => !('source' in el.data))
}

function edgeElements(elements: CapturedElement[]) {
  return elements.filter((el) => 'source' in el.data)
}

describe('GraphCanvas', () => {
  it('renders exactly the S01E01 fixture node/edge counts (11 nodes, 6 edges)', () => {
    const { container } = render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)
    console.log('[TEST] container HTML:', container.innerHTML.substring(0, 200))
    console.log('[TEST] capturedElements length:', capturedElements.length)
    console.log('[TEST] capturedProps:', JSON.stringify(capturedProps))
    // Check for error boundary
    console.log('[TEST] body HTML:', document.body.innerHTML.substring(0, 500))

    expect(nodeElements(capturedElements)).toHaveLength(graphResponseS01E01.nodes.length)
    expect(nodeElements(capturedElements)).toHaveLength(11)
    expect(edgeElements(capturedElements)).toHaveLength(graphResponseS01E01.edges.length)
    expect(edgeElements(capturedElements)).toHaveLength(6)
  })

  it('renders exactly the S01E03 fixture node count (20 nodes) after a boundary change', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} seriesId="series:dexter" episodes={[]} />)

    expect(nodeElements(capturedElements)).toHaveLength(graphResponseS01E03.nodes.length)
    expect(nodeElements(capturedElements)).toHaveLength(20)
    expect(edgeElements(capturedElements)).toHaveLength(graphResponseS01E03.edges.length)
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
})
