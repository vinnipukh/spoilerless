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
//
// D-16 media rule (07-06): image PRESENCE must never drive layout/sizing — a
// node with a portrait and one without are positioned and sized identically,
// so an above-boundary image (masked to null by the backend) can never be
// inferred from layout. The `imageUrl` data key below feeds ONLY the
// background-image selector in graphStylesheet.ts; it never affects node
// dimensions, degree, or position.

import type { ElementDefinition } from 'cytoscape'
import type { GraphEdge, GraphResponse } from '../../types/graph'
import { overviewProjection, type GraphMode } from './overviewTiers'

export function graphToElements(
  graph: GraphResponse,
  mode: GraphMode = 'full',
): ElementDefinition[] {
  // 08-06+ (product owner, presentation): Overview mode renders a curated
  // ~25-45 node projection (tier-1 + required connectors, deduped edges);
  // Full mode renders every spoiler-safe node/edge the backend returned.
  // Both modes consume ONLY the backend-filtered lists — Overview's tiering
  // is semantic curation, never a second visible_from_order authority.
  let nodes = graph.nodes
  let edges: GraphEdge[] = graph.edges
  if (mode === 'overview') {
    const projection = overviewProjection(graph)
    nodes = graph.nodes.filter((n) => projection.keptNodeIds.has(n.id))
    edges = projection.keptEdges
  }

  // 08-05 user-directed Obsidian-style declutter: any node WITHOUT a portrait
  // AND with < 3 edges (degree computed from the mode's edge list
  // only — the D-16 layout rule above permits any computation that consumes
  // only the filtered node/edge lists, never hidden totals) is stamped
  // `simple` and rendered as a small neutral dot by graphStylesheet.ts.
  //
  // NOTE — intentional D-16 media-rule deviation (user-directed 2026-08-05):
  // D-16 forbade image PRESENCE from driving node sizing so a masked
  // (above-boundary) portrait could never be inferred from layout. The
  // product owner explicitly overrode this: pictureless nodes are now
  // visibly smaller. Revisit if spoiler-inference ever becomes a live
  // concern (e.g. a portrait mask feature).
  const degree = new Map<string, number>()
  for (const edge of edges) {
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1)
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1)
  }

  // 08-06 (product owner): isolated nodes — zero edges in the mode's edge
  // list — are dropped from the view. They render as noise with no
  // connections. The backend has already applied the spoiler-safe
  // visible_from_order filter; this is a pure topology decision over the
  // already-filtered lists (D-16 layout rule permits any computation that
  // consumes only the filtered node/edge lists).
  const connected = new Set<string>()
  for (const edge of edges) {
    connected.add(edge.source)
    connected.add(edge.target)
  }

  // Build a lookup so each edge can quickly find its claim (if any).
  const claimById = new Map(graph.claims.map((c) => [c.id, c]))

  // Derive cluster parents (PROB-32 / D-03):
  // Compound parent key = subplot/cluster tag if present, else episode band from visible_from_order
  const clusters = new Map<string, string>()

  const nodeElements: ElementDefinition[] = nodes
    .filter((node) => connected.has(node.id))
    .map((node) => {
    // Only Character nodes ever carry a portrait — other node types must
    // never pick up the background-image selector even if a future node
    // happens to have image_url set. The `imageUrl` key is omitted entirely
    // (not set to null) when there is no portrait, so Cytoscape's `[imageUrl]`
    // existence selector only matches nodes that actually have one.
    const imageUrl = node.type === 'Character' ? node.image_url : null
    const simple = !imageUrl && (degree.get(node.id) ?? 0) < 3

    // Derive cluster key
    const rawCluster =
      (node as Record<string, unknown>).subplot ??
      (node as Record<string, unknown>).cluster
    const clusterKey = rawCluster
      ? String(rawCluster)
      : node.visible_from_order != null
        ? `Ep #${node.visible_from_order}`
        : 'Main'
    const clusterId = `cluster:${clusterKey}`

    if (!clusters.has(clusterId)) {
      clusters.set(clusterId, clusterKey)
    }

    return {
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.type,
        origin: node.origin,
        parent: clusterId,
        ...(simple ? { simple: true } : {}),
        ...(imageUrl ? { imageUrl } : {}),
      },
    }
  })

  // Emit compound parent elements
  const parentElements: ElementDefinition[] = Array.from(clusters.entries()).map(
    ([id, label]) => ({
      data: {
        id,
        label,
        isCluster: true,
        // 08-05 (product owner): the Episode-1 band occupies ~3x the layout
        // area in FULL mode. The stylesheet turns this into a bigger cluster
        // box via padding on the `Ep #1` parent (graphStylesheet.ts).
        // 08-06+ (product owner): Overview mode does NOT inflate the box —
        // with only the curated nodes inside it, 300px of padding is dead
        // space that makes the whole view zoom out. The base 24px padding
        // keeps the episode-band framing without the empty expanse.
        ...(mode === 'full' && label === 'Ep #1' ? { areaScale: 3 } : {}),
      },
    }),
  )

  const edgeElements: ElementDefinition[] = edges.map((edge) => {
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

  return [...parentElements, ...nodeElements, ...edgeElements]
}
