import { useRef } from 'react'
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import CytoscapeComponent from 'react-cytoscapejs'
import type { GraphResponse } from '../../types/graph'
import { graphToElements } from './graphElements'

// Registered once at module scope for Plan 02 (cose-bilkent layout swap +
// full type/origin stylesheet are out of this plan's scope — this plan only
// registers the extension and uses the built-in 'cose' layout as the thin,
// correct-but-minimal tracer implementation).
cytoscape.use(coseBilkent)

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

const stylesheet = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
    },
  },
  {
    selector: 'edge',
    style: {
      label: 'data(label)',
    },
  },
]

export function GraphCanvas({ graph, onSelect }: Props) {
  const elements = graphToElements(graph)
  const wiredRef = useRef(false)

  return (
    <CytoscapeComponent
      elements={elements}
      layout={{ name: 'cose', fit: true, padding: 24 }}
      stylesheet={stylesheet}
      style={{ width: '100%', height: '100%' }}
      cy={(cy) => {
        // react-cytoscapejs re-invokes this callback on every render with the
        // same underlying cy instance in this project's usage pattern; guard
        // so listeners are only attached once per mounted instance (D-05:
        // nothing on the canvas is inert to clicks — full neighbor
        // highlight/fade is Plan 02's scope).
        if (wiredRef.current) return
        wiredRef.current = true

        cy.on('tap', 'node', (evt) => {
          const node = evt.target
          onSelect({
            kind: 'node',
            id: node.id(),
            label: node.data('label'),
            nodeType: node.data('nodeType'),
          })
        })

        cy.on('tap', 'edge', (evt) => {
          const edge = evt.target
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
            onSelect(null)
          }
        })
      }}
    />
  )
}
