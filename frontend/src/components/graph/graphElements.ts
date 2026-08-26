// Pure mapping from a fetched GraphResponse to Cytoscape ElementDefinition[].
// Delegate module for backward compatibility — delegates to sceneElements.ts (Plan 12-14).
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
// inferred from layout. The `imageUrl` data key feeds ONLY the
// background-image selector in graphStylesheet.ts; it never affects node
// dimensions, degree, or position.

import type { ElementDefinition } from 'cytoscape'
import type { GraphResponse } from '../../types/graph'
import type { GraphMode } from './overviewTiers'
import { fromGraph } from '../../lib/graph/sceneElements'

export function graphToElements(
  graph: GraphResponse,
  mode: GraphMode = 'full',
): ElementDefinition[] {
  return fromGraph(graph, mode)
}
