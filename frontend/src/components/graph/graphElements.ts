// Pure mapping from a fetched GraphResponse to Cytoscape ElementDefinition[].
//
// T-02-03 (Information Disclosure, threat_model): this function must read
// only fields already present on GraphResponse and must NEVER filter/exclude
// any node or edge by visible_from_order — the backend has already applied
// the spoiler-safe filter (Phase 1, verified). Re-filtering here would be a
// second, redundant (and drift-prone) visibility authority.

import type { ElementDefinition } from 'cytoscape'
import type { GraphResponse } from '../../types/graph'

export function graphToElements(graph: GraphResponse): ElementDefinition[] {
  const nodeElements: ElementDefinition[] = graph.nodes.map((node) => ({
    data: {
      id: node.id,
      label: node.label,
      nodeType: node.type,
      origin: node.origin,
    },
  }))

  const edgeElements: ElementDefinition[] = graph.edges.map((edge) => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.type,
      edgeType: edge.type,
      origin: edge.origin,
      claimId: edge.claim_id,
    },
  }))

  return [...nodeElements, ...edgeElements]
}
