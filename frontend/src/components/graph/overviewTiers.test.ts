import { describe, expect, it } from 'vitest'
import { displayTierFor, overviewProjection } from './overviewTiers'
import { graphResponseS01E01 } from '../../test/fixtures/graphResponse'
import type { GraphNode, GraphResponse } from '../../types/graph'

function node(
  id: string,
  type = 'Character',
  origin = 'canonical',
  visibleFromOrder = 1,
): GraphNode {
  return {
    id,
    type,
    label: id,
    visible_from_order: visibleFromOrder,
    origin,
    episode_id: null,
    image_url: null,
    image_source_url: null,
  }
}

function graph(nodes: GraphNode[], edges: GraphResponse['edges']): GraphResponse {
  return {
    series: { id: 's', title: 'S', slug: 's' },
    visible_until_order: 3,
    effective_view_order: 1,
    nodes,
    edges,
    claims: [],
    sources: [],
    evidence: [],
  }
}

describe('displayTierFor (semantic curation, never degree-based)', () => {
  it('matches live seed ids by suffix', () => {
    expect(displayTierFor(node('dexter:character:dexter_morgan'))).toBe(1)
    expect(displayTierFor(node('dexter:event:s01e01_doll_message'))).toBe(1)
    expect(displayTierFor(node('dexter:location:miami_metro'))).toBe(1)
  })

  it('matches short fixture ids by suffix', () => {
    expect(displayTierFor(node('char_dexter_morgan'))).toBe(1)
    expect(displayTierFor(node('char_debra_morgan'))).toBe(1)
    expect(displayTierFor(node('loc_miami_metro'))).toBe(1)
  })

  it('ranks supporting characters tier 2', () => {
    expect(displayTierFor(node('dexter:character:rudy_cooper'))).toBe(2)
    expect(displayTierFor(node('dexter:character:camilla_figg'))).toBe(2)
  })

  it('ranks uncurated background nodes tier 3', () => {
    expect(displayTierFor(node('dexter:character:officer_oliver'))).toBe(3)
    expect(displayTierFor(node('dexter:object:scalpel'))).toBe(3)
    expect(displayTierFor(node('dexter:event:s01e01_donut_run'))).toBe(3)
  })

  it('always shows user-origin nodes (tier 1) and structural anchors', () => {
    expect(displayTierFor(node('user:node:my_custom', 'Character', 'user'))).toBe(1)
    expect(displayTierFor(node('dexter_s01e01', 'Episode'))).toBe(1)
    expect(displayTierFor(node('series_dexter', 'Series'))).toBe(1)
  })
})

describe('overviewProjection', () => {
  it('keeps the connector node bridging two tier-1 nodes', () => {
    const result = overviewProjection(
      graph(
        [
          node('char_dexter_morgan'),
          node('char_debra_morgan'),
          node('dexter:event:s01e01_cold_body_lunch'), // tier 3 bridge between them
        ],
        [
          { id: 'e1', source: 'char_dexter_morgan', target: 'dexter:event:s01e01_cold_body_lunch', type: 'PARTICIPATED_IN', visible_from_order: 1, origin: 'canonical', claim_id: null },
          { id: 'e2', source: 'dexter:event:s01e01_cold_body_lunch', target: 'char_debra_morgan', type: 'PARTICIPATED_IN', visible_from_order: 1, origin: 'canonical', claim_id: null },
        ],
      ),
    )
    expect(result.keptNodeIds.has('char_dexter_morgan')).toBe(true)
    expect(result.keptNodeIds.has('char_debra_morgan')).toBe(true)
    // The event is the ONLY path between the siblings → required connector.
    expect(result.keptNodeIds.has('dexter:event:s01e01_cold_body_lunch')).toBe(true)
    expect(result.keptEdges.map((e) => e.id)).toEqual(['e1', 'e2'])
  })

  it('does NOT keep a node on an alternate route (not required)', () => {
    // Dexter--X--Debra AND Dexter--Y--Debra: neither X nor Y is required.
    const result = overviewProjection(
      graph(
        [
          node('char_dexter_morgan'),
          node('char_debra_morgan'),
          node('x'),
          node('y'),
        ],
        [
          { id: 'e1', source: 'char_dexter_morgan', target: 'x', type: 'KNOWS', visible_from_order: 1, origin: 'canonical', claim_id: null },
          { id: 'e2', source: 'x', target: 'char_debra_morgan', type: 'KNOWS', visible_from_order: 1, origin: 'canonical', claim_id: null },
          { id: 'e3', source: 'char_dexter_morgan', target: 'y', type: 'TRUSTS', visible_from_order: 1, origin: 'canonical', claim_id: null },
          { id: 'e4', source: 'y', target: 'char_debra_morgan', type: 'TRUSTS', visible_from_order: 1, origin: 'canonical', claim_id: null },
        ],
      ),
    )
    expect(result.keptNodeIds.has('x')).toBe(false)
    expect(result.keptNodeIds.has('y')).toBe(false)
  })

  it('drops a tier-3 leaf even when it touches a tier-1 hub', () => {
    const result = overviewProjection(
      graph(
        [
          node('char_dexter_morgan'),
          node('dexter:object:scalpel'), // tier 3 leaf
        ],
        [
          { id: 'e1', source: 'char_dexter_morgan', target: 'dexter:object:scalpel', type: 'USES', visible_from_order: 1, origin: 'canonical', claim_id: null },
        ],
      ),
    )
    expect(result.keptNodeIds.has('dexter:object:scalpel')).toBe(false)
    expect(result.keptEdges).toHaveLength(0)
  })

  it('dedupes repeated (endpoint-pair, type) edges', () => {
    const result = overviewProjection(
      graph(
        [node('char_dexter_morgan'), node('dexter:location:miami_metro')],
        [
          { id: 'e1', source: 'char_dexter_morgan', target: 'dexter:location:miami_metro', type: 'OCCURRED_IN', visible_from_order: 1, origin: 'canonical', claim_id: null },
          { id: 'e2', source: 'char_dexter_morgan', target: 'dexter:location:miami_metro', type: 'OCCURRED_IN', visible_from_order: 2, origin: 'canonical', claim_id: null },
          { id: 'e3', source: 'dexter:location:miami_metro', target: 'char_dexter_morgan', type: 'OCCURRED_IN', visible_from_order: 3, origin: 'canonical', claim_id: null },
        ],
      ),
    )
    expect(result.keptEdges).toHaveLength(1)
    expect(result.keptEdges[0]?.id).toBe('e1')
  })

  it('keeps distinct edge types between the same pair', () => {
    const result = overviewProjection(
      graph(
        [node('char_dexter_morgan'), node('char_debra_morgan')],
        [
          { id: 'e1', source: 'char_dexter_morgan', target: 'char_debra_morgan', type: 'FAMILY_OF', visible_from_order: 1, origin: 'canonical', claim_id: null },
          { id: 'e2', source: 'char_dexter_morgan', target: 'char_debra_morgan', type: 'KNOWS', visible_from_order: 1, origin: 'user', claim_id: null },
        ],
      ),
    )
    expect(result.keptEdges.map((e) => e.id)).toEqual(['e1', 'e2'])
  })

  it('keeps user-origin nodes even when uncurated', () => {
    const result = overviewProjection(
      graph(
        [node('char_dexter_morgan'), node('my-custom-char', 'Character', 'user')],
        [
          { id: 'e1', source: 'char_dexter_morgan', target: 'my-custom-char', type: 'KNOWS', visible_from_order: 1, origin: 'user', claim_id: null },
        ],
      ),
    )
    expect(result.keptNodeIds.has('my-custom-char')).toBe(true)
  })

  it('projects the S01E01 fixture to the curated overview subset', () => {
    const result = overviewProjection(graphResponseS01E01)
    // Tier-1 fixture ids (suffix match) + Episode/Series anchors. rita_bennett
    // is curated main-cast → kept by the projection (the canvas later drops
    // her as isolated — zero edges in the fixture).
    for (const id of [
      'char_dexter_morgan',
      'char_debra_morgan',
      'char_angel_batista',
      'char_rita_bennett',
      'loc_miami_metro',
      'dexter_s01e01',
      'series_dexter',
    ]) {
      expect(result.keptNodeIds.has(id)).toBe(true)
    }
    // Tier-3 fixture ids stay hidden.
    for (const id of ['event_first_kill', 'loc_dexters_apartment']) {
      expect(result.keptNodeIds.has(id)).toBe(false)
    }
    // User-origin edge between kept nodes survives.
    expect(result.keptEdges.some((e) => e.id === 'user-rel:test-1')).toBe(true)
  })
})
