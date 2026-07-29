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

vi.mock('react-cytoscapejs', () => {
  function CytoscapeComponentStub(props: {
    elements: CapturedElement[]
    cy?: (cy: unknown) => void
  }) {
    capturedElements = props.elements
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
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} />)

    expect(nodeElements(capturedElements)).toHaveLength(graphResponseS01E01.nodes.length)
    expect(nodeElements(capturedElements)).toHaveLength(11)
    expect(edgeElements(capturedElements)).toHaveLength(graphResponseS01E01.edges.length)
    expect(edgeElements(capturedElements)).toHaveLength(6)
  })

  it('renders exactly the S01E03 fixture node count (20 nodes) after a boundary change', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} />)

    expect(nodeElements(capturedElements)).toHaveLength(graphResponseS01E03.nodes.length)
    expect(nodeElements(capturedElements)).toHaveLength(20)
    expect(edgeElements(capturedElements)).toHaveLength(graphResponseS01E03.edges.length)
  })

  it('maps every node to a data(nodeType), including Episode and Series (no default-ellipse fallthrough)', () => {
    render(<GraphCanvas graph={graphResponseS01E03} onSelect={() => {}} />)

    const nodes = nodeElements(capturedElements)
    expect(nodes.some((node) => node.data.nodeType === 'Episode')).toBe(true)
    expect(nodes.some((node) => node.data.nodeType === 'Series')).toBe(true)
  })

  it('never filters elements by visible_from_order (pure pass-through of the fetched GraphResponse)', () => {
    render(<GraphCanvas graph={graphResponseS01E01} onSelect={() => {}} />)

    const nodeIds = nodeElements(capturedElements).map((node) => node.data.id)
    expect(nodeIds).toEqual(expect.arrayContaining(graphResponseS01E01.nodes.map((node) => node.id)))
  })
})
