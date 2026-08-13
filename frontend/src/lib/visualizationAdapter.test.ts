// Pure-adapter contract tests (10-04 Task 1). These pin:
// - T10-LEAK-04: the adapter consumes ONLY serialized visible fields — the
//   exact-shape tests assert the emitted data-key set, so a hidden field
//   sneaking into the DTO cannot flow through to Cytoscape.
// - D-05: the adapter never filters (every node/edge passes through, even
//   with high `order` values).
// - D-14: technical labels (debugLabel) are absent outside debug mode.
// - Deterministic ids and order.
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ElementDefinition } from 'cytoscape'
import type { VisualizationDTO, VisualizationNode } from '../types/graph'
import {
  EDGE_DATA_KEYS,
  GROUP_DATA_KEYS,
  NODE_DATA_KEYS,
  toCytoscapeElements,
  toTimelineEvents,
} from './visualizationAdapter'

function makeDto(overrides: Partial<VisualizationDTO> = {}): VisualizationDTO {
  return {
    metadata: {
      projection_version: '1.0.0',
      view_type: 'episode_overview',
      series_id: 'series_dexter',
      series_title: 'Dexter',
      episode_order: 1,
      visible_until_order: 1,
      effective_view_order: 1,
    },
    nodes: [
      {
        id: 'char_dexter_morgan',
        kind: 'Character',
        label: 'Dexter Morgan',
        display_tier: 1,
        order: 1,
        episode_id: 'dexter_s01e01',
        image_url: '/api/static/characters/dexter_morgan.webp',
        image_source_url: null,
        origin: 'canonical',
      },
      {
        id: 'char_debra_morgan',
        kind: 'Character',
        label: 'Debra Morgan',
        display_tier: 1,
        order: 1,
        episode_id: 'dexter_s01e01',
        image_url: null,
        image_source_url: null,
        origin: 'canonical',
      },
      {
        id: 'event_first_kill',
        kind: 'Event',
        label: 'Dexter kills Mike Donovan',
        display_tier: 2,
        order: 1,
        episode_id: 'dexter_s01e01',
        image_url: null,
        image_source_url: null,
        origin: 'canonical',
      },
    ],
    edges: [
      {
        id: 'edge_family',
        source: 'char_dexter_morgan',
        target: 'char_debra_morgan',
        relation_class: 'Family',
        order: 1,
        claim_id: 'claim_1',
        origin: 'canonical',
      },
      {
        id: 'edge_occurred',
        source: 'char_dexter_morgan',
        target: 'event_first_kill',
        relation_class: 'Participated in',
        order: 1,
        claim_id: null,
        origin: 'canonical',
      },
    ],
    groups: [
      {
        id: 'thread_main',
        label: 'Main plot',
        node_ids: ['char_dexter_morgan', 'char_debra_morgan'],
      },
    ],
    timeline: [
      {
        id: 'event_first_kill',
        kind: 'event',
        label: 'Dexter kills Mike Donovan',
        episode_id: 'dexter_s01e01',
        episode_order: 1,
        order: 1,
        display_tier: 2,
        participant_ids: ['char_dexter_morgan'],
        location_id: 'loc_dexters_apartment',
        location_label: "Dexter's Apartment",
      },
    ],
    focus: null,
    ...overrides,
  }
}

const dataOf = (elements: ElementDefinition[], id: string): Record<string, unknown> => {
  const el = elements.find((e) => e.data.id === id)
  expect(el, `expected element ${id}`).toBeDefined()
  return el!.data as Record<string, unknown>
}

describe('toCytoscapeElements', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('emits deterministic ids in DTO order: groups, nodes, edges', () => {
    const elements = toCytoscapeElements(makeDto())
    expect(elements.map((el) => el.data.id)).toEqual([
      'group:thread_main',
      'char_dexter_morgan',
      'char_debra_morgan',
      'event_first_kill',
      'edge_family',
      'edge_occurred',
    ])
  })

  it('maps every DTO node to nodeType=kind with displayTier/order/origin/episodeId', () => {
    const elements = toCytoscapeElements(makeDto())
    const dexter = dataOf(elements, 'char_dexter_morgan')
    expect(dexter.nodeType).toBe('Character')
    expect(dexter.displayTier).toBe(1)
    expect(dexter.order).toBe(1)
    expect(dexter.origin).toBe('canonical')
    expect(dexter.episodeId).toBe('dexter_s01e01')
    const event = dataOf(elements, 'event_first_kill')
    expect(event.nodeType).toBe('Event')
    expect(event.displayTier).toBe(2)
  })

  it('maps DTO groups to compound parents and wires member nodes to them (D-36)', () => {
    const elements = toCytoscapeElements(makeDto())
    const parent = dataOf(elements, 'group:thread_main')
    expect(parent.isCluster).toBe(true)
    expect(parent.label).toBe('Main plot')
    expect(parent.groupId).toBe('thread_main')
    expect(dataOf(elements, 'char_dexter_morgan').parent).toBe('group:thread_main')
    expect(dataOf(elements, 'char_debra_morgan').parent).toBe('group:thread_main')
    // Non-member nodes get no parent key.
    expect(dataOf(elements, 'event_first_kill')).not.toHaveProperty('parent')
  })

  it('maps edges with the human relation class as label (D-14), never filtering', () => {
    const elements = toCytoscapeElements(makeDto())
    const edge = dataOf(elements, 'edge_family')
    expect(edge.label).toBe('Family')
    expect(edge.relationClass).toBe('Family')
    expect(edge.source).toBe('char_dexter_morgan')
    expect(edge.target).toBe('char_debra_morgan')
    expect(edge.claimId).toBe('claim_1')
  })

  it('NEVER filters nodes/edges by order — every DTO element passes through (D-05)', () => {
    const dto = makeDto()
    const hiddenLooking = dto.nodes.map((n) => ({ ...n, order: 999 }))
    const withHidden = makeDto({ nodes: hiddenLooking })
    const elements = toCytoscapeElements(withHidden)
    const ids = elements.map((el) => el.data.id)
    for (const node of hiddenLooking) expect(ids).toContain(node.id)
    expect(ids).toContain('edge_family')
    expect(ids).toContain('edge_occurred')
  })

  it('prefixes relative Character image_url with VITE_API_BASE_URL; omits imageUrl for non-Character kinds', () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.spoilerless.net')
    const elements = toCytoscapeElements(makeDto())
    expect(dataOf(elements, 'char_dexter_morgan').imageUrl).toBe(
      'https://api.spoilerless.net/api/static/characters/dexter_morgan.webp',
    )
    // Pictureless Character and Event nodes carry no imageUrl key.
    expect(dataOf(elements, 'char_debra_morgan')).not.toHaveProperty('imageUrl')
    expect(dataOf(elements, 'event_first_kill')).not.toHaveProperty('imageUrl')
  })

  it('exact-shape: node data contains ONLY the documented serialized keys (T10-LEAK-04)', () => {
    const elements = toCytoscapeElements(makeDto())
    const dexter = dataOf(elements, 'char_dexter_morgan')
    for (const key of Object.keys(dexter)) {
      expect(NODE_DATA_KEYS).toContain(key)
    }
    const debra = dataOf(elements, 'char_debra_morgan')
    for (const key of Object.keys(debra)) {
      expect(NODE_DATA_KEYS).toContain(key)
    }
  })

  it('exact-shape: edge and group data contain ONLY the documented keys', () => {
    const elements = toCytoscapeElements(makeDto())
    for (const key of Object.keys(dataOf(elements, 'edge_family'))) {
      expect(EDGE_DATA_KEYS).toContain(key)
    }
    for (const key of Object.keys(dataOf(elements, 'group:thread_main'))) {
      expect(GROUP_DATA_KEYS).toContain(key)
    }
  })

  it('a hidden field injected into the DTO never reaches Cytoscape data', () => {
    // Simulate a backend regression: an extra field riding on a node.
    const dto = makeDto()
    const poisoned: VisualizationNode = {
      ...dto.nodes[0]!,
      hidden_spoiler_field: 'spoiled!',
    } as unknown as VisualizationNode
    const elements = toCytoscapeElements(makeDto({ nodes: [poisoned, ...dto.nodes.slice(1)] }))
    expect(dataOf(elements, 'char_dexter_morgan')).not.toHaveProperty('hidden_spoiler_field')
  })

  it('technical labels (debugLabel) are hidden outside debug mode (D-14)', () => {
    const elements = toCytoscapeElements(makeDto())
    expect(dataOf(elements, 'char_dexter_morgan')).not.toHaveProperty('debugLabel')
    expect(dataOf(elements, 'edge_family')).not.toHaveProperty('debugLabel')
    expect(dataOf(elements, 'group:thread_main')).not.toHaveProperty('debugLabel')
  })

  it('debugLabels:true adds technical kind/relation labels for the Advanced explorer', () => {
    const elements = toCytoscapeElements(makeDto(), { debugLabels: true })
    expect(dataOf(elements, 'char_dexter_morgan').debugLabel).toBe('Character')
    expect(dataOf(elements, 'event_first_kill').debugLabel).toBe('Event')
    expect(dataOf(elements, 'edge_family').debugLabel).toBe('Family')
    expect(dataOf(elements, 'group:thread_main').debugLabel).toBe('thread_main')
  })
})

describe('toTimelineEvents', () => {
  it('passes through exactly the serialized timeline fields (typed React/CSS seam)', () => {
    const events = toTimelineEvents(makeDto())
    expect(events).toHaveLength(1)
    expect(events[0]).toEqual({
      id: 'event_first_kill',
      kind: 'event',
      label: 'Dexter kills Mike Donovan',
      episode_id: 'dexter_s01e01',
      episode_order: 1,
      order: 1,
      display_tier: 2,
      participant_ids: ['char_dexter_morgan'],
      location_id: 'loc_dexters_apartment',
      location_label: "Dexter's Apartment",
    })
  })

  it('exact-shape: timeline events carry no hidden fields', () => {
    const dto = makeDto()
    const poisoned = { ...dto.timeline[0]!, hidden_future_count: 7 }
    const events = toTimelineEvents(makeDto({ timeline: [poisoned as never] }))
    expect(events[0]).not.toHaveProperty('hidden_future_count')
    expect(Object.keys(events[0]!)).toEqual([
      'id',
      'kind',
      'label',
      'episode_id',
      'episode_order',
      'order',
      'display_tier',
      'participant_ids',
      'location_id',
      'location_label',
    ])
  })
})
