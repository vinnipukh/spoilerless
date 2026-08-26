import { describe, expect, it } from 'vitest'
import { searchIndex } from './searchIndex'
import { graphResponseS01E01 } from '../test/fixtures/graphResponse'
import type { GraphResponse } from '../types/graph'
import type { NoteResponse } from '../types/userContent'

function note(overrides: Partial<NoteResponse> = {}): NoteResponse {
  return {
    id: 'note_1',
    series_id: 'series_dexter',
    target_type: 'Character',
    target_id: 'char_dexter_morgan',
    content: 'Dexter keeps a meticulous ritual before every kill.',
    origin: 'user',
    visible_from_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

const notes: NoteResponse[] = [note()]

function graphWithNodes(labels: string[]): GraphResponse {
  return {
    series: { id: 'series_x', title: 'X', slug: 'x' },
    visible_until_order: 1,
    effective_view_order: 1,
    nodes: labels.map((label, i) => ({
      id: `node_${i}`,
      type: 'Character',
      label,
      visible_from_order: 1,
      origin: 'canonical',
      episode_id: null,
      image_url: null,
      image_source_url: null,
    })),
    edges: [],
    claims: [],
    sources: [],
    evidence: [],
  }
}

describe('searchIndex', () => {
  it('returns [] for an empty or whitespace query (payload-local, no firehose)', () => {
    expect(searchIndex(graphResponseS01E01, notes, '')).toEqual([])
    expect(searchIndex(graphResponseS01E01, notes, '   ')).toEqual([])
  })

  it('matches node labels case-insensitively and tags results as nodes', () => {
    const results = searchIndex(graphResponseS01E01, notes, 'morgan')
    const nodeResults = results.filter((result) => result.collection === 'nodes')
    const labels = nodeResults.map((result) => result.label)
    expect(labels).toContain('Dexter Morgan')
    expect(labels).toContain('Debra Morgan')
    expect(nodeResults.every((result) => result.collection === 'nodes')).toBe(true)
    expect(nodeResults.every((result) => 'nodeType' in result)).toBe(true)
  })

  it('matches node ids as a secondary field', () => {
    // 'james_doakes' is a substring of the node id (char_james_doakes) but
    // of no node label in the fixture — a pure id hit.
    const results = searchIndex(graphResponseS01E01, notes, 'james_doakes')
    const nodeResults = results.filter((result) => result.collection === 'nodes')
    expect(nodeResults.some((result) => result.id === 'char_james_doakes')).toBe(true)
  })

  it('matches claims on label, predicate, and object label', () => {
    // predicate
    const byPredicate = searchIndex(graphResponseS01E01, notes, 'works_at', {
      collections: ['claims'],
    })
    expect(byPredicate.some((result) => result.collection === 'claims' && result.id === 'claim_1')).toBe(true)
    // object label
    const byObject = searchIndex(graphResponseS01E01, notes, 'miami metro', {
      collections: ['claims'],
    })
    expect(byObject.some((result) => result.collection === 'claims' && result.id === 'claim_1')).toBe(true)
    // label
    const byLabel = searchIndex(graphResponseS01E01, notes, 'sister', {
      collections: ['claims'],
    })
    expect(byLabel.some((result) => result.collection === 'claims' && result.id === 'claim_3')).toBe(true)
  })

  it('matches notes on content and resolves the anchor node label', () => {
    const results = searchIndex(graphResponseS01E01, notes, 'ritual', {
      collections: ['notes'],
    })
    expect(results).toHaveLength(1)
    expect(results[0]).toMatchObject({
      collection: 'notes',
      id: 'note_1',
      targetId: 'char_dexter_morgan',
      targetLabel: 'Dexter Morgan',
    })
  })

  it('caps results at 8 per collection', () => {
    const labels = Array.from({ length: 10 }, (_, i) => `Matchable Node ${i + 1}`)
    const graph = graphWithNodes(labels)
    const results = searchIndex(graph, [], 'matchable', { collections: ['nodes'] })
    expect(results).toHaveLength(8)
  })

  it('returns collections in nodes -> claims -> notes order with collection tags', () => {
    const results = searchIndex(graphResponseS01E01, notes, 'dexter')
    expect(results.length).toBeGreaterThan(0)
    const order = results.map((result) => result.collection)
    const firstNonNodes = order.findIndex((collection) => collection !== 'nodes')
    if (firstNonNodes !== -1) {
      // everything before the first non-node result is nodes
      expect(order.slice(0, firstNonNodes).every((collection) => collection === 'nodes')).toBe(true)
      // claims (if any) come before notes
      const firstNotes = order.indexOf('notes')
      const firstClaims = order.indexOf('claims')
      if (firstClaims !== -1 && firstNotes !== -1) {
        expect(firstClaims).toBeLessThan(firstNotes)
      }
    }
    expect(results.some((result) => result.collection === 'notes')).toBe(true)
  })

  it('honors the collections option', () => {
    const onlyClaims = searchIndex(graphResponseS01E01, notes, 'dexter', {
      collections: ['claims'],
    })
    expect(onlyClaims.length).toBeGreaterThan(0)
    expect(onlyClaims.every((result) => result.collection === 'claims')).toBe(true)
  })

  it('ranks exact label matches ahead of substring matches', () => {
    const graph = graphWithNodes(['Morgan', 'Morgana', 'Not A Match'])
    const results = searchIndex(graph, [], 'morgan', { collections: ['nodes'] })
    expect(results.map((result) => result.label)).toEqual(['Morgan', 'Morgana'])
  })
})
