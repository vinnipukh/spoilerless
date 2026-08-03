// Pure mapping from a fetched GraphResponse to Cytoscape ElementDefinition[].
//
// T-02-03 (Information Disclosure, threat_model): this function must read
// only fields already present on GraphResponse and must NEVER filter/exclude
// any node or edge by visible_from_order — the backend has already applied
// the spoiler-safe filter (Phase 1, verified). Re-filtering here would be a
// second, redundant (and drift-prone) visibility authority.
//
// D-16 layout rule (07-05): node sizing/degree/label styling must derive ONLY
// from GraphResponse fields the backend already boundary-filtered. Never
// re-derive a hidden degree/count client-side (e.g. from a totals field) —
// hidden counts are absent from the API by contract, so any frontend
// computation must consume only the filtered node/edge lists above.

import type { ElementDefinition } from 'cytoscape'
import type { GraphResponse } from '../../types/graph'

export function graphToElements(graph: GraphResponse): ElementDefinition[] {
  // Build a lookup so each edge can quickly find its claim (if any).
  const claimById = new Map(graph.claims.map((c) => [c.id, c]))

  const nodeElements: ElementDefinition[] = graph.nodes.map((node) => {
    // Only Character nodes ever carry a portrait — other node types must
    // never pick up the background-image selector even if a future node
    // happens to have image_url set. The `imageUrl` key is omitted entirely
    // (not set to null) when there is no portrait, so Cytoscape's `[imageUrl]`
    // existence selector only matches nodes that actually have one.
    const imageUrl = node.type === 'Character' ? node.image_url : null

    return {
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.type,
        origin: node.origin,
        ...(imageUrl ? { imageUrl } : {}),
      },
    }
  })

  const edgeElements: ElementDefinition[] = graph.edges.map((edge) => {
    const claim = edge.claim_id ? claimById.get(edge.claim_id) : undefined

    return {
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.type,
        edgeType: edge.type,
        origin: edge.origin,
        claimId: edge.claim_id,
        ...(claim ? { claimStatus: claim.status } : {}),
      },
    }
  })

  return [...nodeElements, ...edgeElements]
}
