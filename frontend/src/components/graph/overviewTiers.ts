// Overview-mode importance tiers + projection (08-06 presentation declutter).
//
// Tier assignment is SEMANTIC (curated seed content + structural types),
// deliberately NOT degree-based (product-owner constraint). The curated
// suffix sets cover the Dexter S01E01-03 seed; the matching rule is
// `id.endsWith(suffix)` so both the live seed ids (`dexter:character:...`)
// and the test-fixture short ids (`char_dexter_morgan`) resolve to the same
// entity without a second id table.
//
// display_tier (1 = important, 2 = supporting, 3 = detail):
//   - user-origin nodes are always tier 1 (never hide the user's own edits)
//   - Episode / Series are tier 1 (structural anchors)
//   - curated suffixes decide the rest
//
// Overview projection keeps tier-1 nodes plus REQUIRED connector nodes — a
// node whose removal would split two tier-1 nodes that were connected in the
// backend-filtered graph (exact articulation test, not a degree heuristic).
// Edges are kept only between kept nodes and deduped per (endpoint-pair,
// type) so repeated PARTICIPATED_IN / OCCURRED_IN connections collapse.

import type { GraphEdge, GraphNode, GraphResponse } from '../../types/graph'

export type GraphMode = 'overview' | 'full'

/** Tier 1 — important: main cast, case-arc events, anchor locations, signature objects. */
const TIER_1_SUFFIXES = new Set([
  // Characters — main cast
  'dexter_morgan',
  'debra_morgan',
  'rita_bennett',
  'angel_batista',
  'james_doakes',
  'maria_laguerta',
  'vince_masuka',
  'harry_morgan',
  'ice_truck_killer',
  'paul_bennett',
  // Events — the ice-truck case arc + pilot ritual beats
  's01e01_ice_truck_case',
  's01e01_donovan_kill',
  's01e01_second_body',
  's01e01_truck_encounter',
  's01e01_doll_message',
  's01e02_debra_transfer',
  's01e03_body_discovery',
  's01e01_seven_seas_arrive',
  // Locations — anchors
  'miami_metro',
  'dexter_apartment',
  'seven_seas_motel',
  'ice_rink',
  // Objects — the signature prop
  'blood_slide_box',
])

/** Tier 2 — supporting: shown in Overview only when required as connectors. */
const TIER_2_SUFFIXES = new Set([
  // Supporting characters
  'rudy_cooper',
  'camilla_figg',
  'thomas_matthews',
  'mike_donovan',
  // Supporting events
  's01e01_donovan_abduct',
  's01e01_trophy_box',
  's01e01_pool_examination',
  's01e01_bloodless_fascination',
  's01e01_truck_theory',
  's01e01_baywater_kill',
  's01e01_crab_festival',
  's01e01_rita_intimacy',
  // Supporting locations
  'miami',
  'rita_home',
  'cokehead_scene',
  'bay_harbor',
  'miami_crime_scene',
  // Supporting objects
  'm99',
  'wire_garrote',
  'power_saw',
  'refrigerated_truck',
  'severed_head',
  'doll_head',
  'harrys_code',
  'slice_of_life',
  // Supporting organizations
  'miami_metro_homicide',
])

export function displayTierFor(node: GraphNode): 1 | 2 | 3 {
  if (node.origin === 'user') return 1
  if (node.type === 'Episode' || node.type === 'Series') return 1
  // Suffix match (`id.endsWith(suffix)`): 'dexter:character:dexter_morgan'
  // and the fixture-short 'char_dexter_morgan' both end with
  // 'dexter_morgan', so live ids and test ids resolve to the same tier.
  for (const suffix of TIER_1_SUFFIXES) {
    if (node.id.endsWith(suffix)) return 1
  }
  for (const suffix of TIER_2_SUFFIXES) {
    if (node.id.endsWith(suffix)) return 2
  }
  return 3
}

export type OverviewProjection = {
  keptNodeIds: Set<string>
  keptEdges: GraphEdge[]
}

export function overviewProjection(graph: GraphResponse): OverviewProjection {
  const tier1 = new Set<string>()
  for (const node of graph.nodes) {
    if (displayTierFor(node) === 1) tier1.add(node.id)
  }

  const connectors = findConnectorNodes(graph, tier1)
  const keptNodeIds = new Set<string>([...tier1, ...connectors])

  // Keep edges whose endpoints are both kept; dedupe per (endpoint-pair,
  // type) — repeated PARTICIPATED_IN / OCCURRED_IN / PART_OF connections
  // collapse to a single edge.
  const seen = new Set<string>()
  const keptEdges: GraphEdge[] = []
  for (const edge of graph.edges) {
    if (!keptNodeIds.has(edge.source) || !keptNodeIds.has(edge.target)) continue
    const key =
      [edge.source, edge.target].sort().join('\u0000') + '\u0000' + edge.type
    if (seen.has(key)) continue
    seen.add(key)
    keptEdges.push(edge)
  }

  return { keptNodeIds, keptEdges }
}

/**
 * A connector is a node whose removal splits two tier-1 nodes that were
 * connected in the backend-filtered graph — the exact articulation test.
 * Chains of connectors (A--X--Y--B) all qualify because the check runs on
 * the full component minus the candidate, so alternate routes through other
 * non-tier-1 nodes are respected (a node on an alternate path is NOT
 * required and stays hidden).
 */
function findConnectorNodes(graph: GraphResponse, tier1: Set<string>): string[] {
  if (tier1.size < 2) return []

  const adj = new Map<string, Set<string>>()
  const link = (a: string, b: string) => {
    if (!adj.has(a)) adj.set(a, new Set())
    adj.get(a)!.add(b)
  }
  for (const edge of graph.edges) {
    link(edge.source, edge.target)
    link(edge.target, edge.source)
  }

  const allIds = new Set(graph.nodes.map((n) => n.id))

  const componentsOf = (nodeSet: Set<string>): Set<string>[] => {
    const comps: Set<string>[] = []
    const remaining = new Set(nodeSet)
    while (remaining.size > 0) {
      const start = remaining.values().next().value as string
      const seen = new Set([start])
      const stack = [start]
      while (stack.length > 0) {
        const u = stack.pop()!
        for (const v of adj.get(u) ?? []) {
          if (remaining.has(v) && !seen.has(v)) {
            seen.add(v)
            stack.push(v)
          }
        }
      }
      comps.push(seen)
      for (const id of seen) remaining.delete(id)
    }
    return comps
  }

  const connectors: string[] = []
  for (const comp of componentsOf(allIds)) {
    const compT1 = [...comp].filter((id) => tier1.has(id))
    if (compT1.length < 2) continue
    for (const n of comp) {
      if (tier1.has(n)) continue
      const sub = new Set(comp)
      sub.delete(n)
      const subComps = componentsOf(sub)
      const t1Comps = subComps.filter((c) => [...c].some((id) => tier1.has(id)))
      if (t1Comps.length >= 2) connectors.push(n)
    }
  }
  return connectors
}
