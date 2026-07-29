import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import CytoscapeComponent from 'react-cytoscapejs'
import type { GraphResponse } from '../../types/graph'
import { graphToElements } from './graphElements'
import { graphStylesheet } from './graphStylesheet'

// Registered once at module scope. `layoutName` defaults to 'cose-bilkent'
// (D-04's primary layout) and only falls back to the built-in 'cose' if the
// extension actually fails to register — not a preemptive dual-path switch
// (CONTEXT.md D-04 discretion note: only fall back on an actual caught
// build/runtime failure).
let layoutName: 'cose-bilkent' | 'cose' = 'cose-bilkent'
try {
  cytoscape.use(coseBilkent)
} catch (error) {
  console.error(
    'cytoscape-cose-bilkent failed to register; falling back to the built-in cose layout',
    error,
  )
  layoutName = 'cose'
}

function layoutOptionsFor(name: 'cose-bilkent' | 'cose') {
  return name === 'cose-bilkent'
    ? { name: 'cose-bilkent', nodeDimensionsIncludeLabels: true, fit: true, padding: 24 }
    : { name: 'cose', fit: true, padding: 24 }
}

// react-cytoscapejs's own declarative `layout` prop only re-applies a layout
// when the prop's shallow-compared field values change (never true here,
// since every render passes literal-equal field values) — so it never
// re-lays-out purely because the *elements* changed (new episode boundary).
// This function is called imperatively instead, from an effect keyed on the
// `graph` object, so the canvas actually reflows on every boundary change.
// Guarded so it never throws into an effect that a test double's fake `cy`
// (no real `.layout()` method) might pass in.
function runLayout(cy: cytoscape.Core) {
  if (typeof cy.layout !== 'function') return
  try {
    cy.layout(layoutOptionsFor(layoutName)).run()
  } catch (error) {
    console.error(
      'cose-bilkent layout failed at runtime; falling back to the built-in cose layout',
      error,
    )
    layoutName = 'cose'
    try {
      cy.layout(layoutOptionsFor('cose')).run()
    } catch (fallbackError) {
      console.error('built-in cose layout also failed', fallbackError)
    }
  }
}

export type SelectedNode = {
  kind: 'node'
  id: string
  label: string
  nodeType: string
}

export type SelectedEdge = {
  kind: 'edge'
  id: string
  edgeType: string
  source: string
  target: string
}

export type SelectedElement = SelectedNode | SelectedEdge

type Props = {
  graph: GraphResponse
  onSelect: (element: SelectedElement | null) => void
}

export function GraphCanvas({ graph, onSelect }: Props) {
  const elements = graphToElements(graph)
  // Tracks which real `cy` instance tap/hover listeners have already been
  // wired onto — react-cytoscapejs re-invokes the `cy` callback prop on
  // every render with the SAME underlying instance in this project's usage
  // pattern, so listeners must only be attached once per actual instance
  // (comparing the instance itself, not a boolean, correctly re-wires if a
  // genuinely new instance ever appears).
  const wiredCyRef = useRef<cytoscape.Core | null>(null)
  const cyInstanceRef = useRef<cytoscape.Core | null>(null)

  // Re-run the layout whenever a new graph is fetched (episode boundary
  // change) so newly-added nodes/edges are actually positioned rather than
  // left wherever Cytoscape defaults new elements to.
  useEffect(() => {
    const cy = cyInstanceRef.current
    if (!cy) return
    runLayout(cy)
  }, [graph])

  return (
    <CytoscapeComponent
      elements={elements}
      layout={layoutOptionsFor(layoutName)}
      stylesheet={graphStylesheet}
      style={{ width: '100%', height: '100%' }}
      cy={(cy) => {
        cyInstanceRef.current = cy

        if (wiredCyRef.current === cy) return
        wiredCyRef.current = cy

        // Long-label assumption (02-02-PLAN.md Open Assumption): the
        // stylesheet truncates node labels with a single-line ellipsis; the
        // full text surfaces via the browser's native tooltip by toggling a
        // `title` attribute on the canvas container while hovering a node.
        cy.on('mouseover', 'node', (evt) => {
          cy.container()?.setAttribute('title', evt.target.data('label'))
        })
        cy.on('mouseout', 'node', () => {
          cy.container()?.removeAttribute('title')
        })
        cy.on('mouseover', 'edge', (evt) => {
          evt.target.addClass('hovered')
        })
        cy.on('mouseout', 'edge', (evt) => {
          evt.target.removeClass('hovered')
        })

        // Selection-driven neighbor highlight/fade (02-RESEARCH.md Pattern
        // 3, D-05 "nothing is inert to clicks").
        cy.on('tap', 'node', (evt) => {
          const node = evt.target
          const neighborhood = node.closedNeighborhood()
          cy.elements().difference(neighborhood).addClass('faded')
          neighborhood.removeClass('faded')
          cy.elements().removeClass('selected-dominant edge-active')
          node.addClass('selected-dominant')
          onSelect({
            kind: 'node',
            id: node.id(),
            label: node.data('label'),
            nodeType: node.data('nodeType'),
          })
        })

        cy.on('tap', 'edge', (evt) => {
          const edge = evt.target
          const neighborhood = edge.connectedNodes().union(edge)
          cy.elements().difference(neighborhood).addClass('faded')
          neighborhood.removeClass('faded')
          cy.elements().removeClass('selected-dominant edge-active')
          edge.addClass('edge-active')
          onSelect({
            kind: 'edge',
            id: edge.id(),
            edgeType: edge.data('edgeType'),
            source: edge.data('source'),
            target: edge.data('target'),
          })
        })

        cy.on('tap', (evt) => {
          if (evt.target === cy) {
            cy.elements().removeClass('faded selected-dominant edge-active')
            onSelect(null)
          }
        })
      }}
    />
  )
}
