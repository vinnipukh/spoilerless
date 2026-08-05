// Zero-dependency substring search index — the SINGLE search implementation
// behind node search (FEAT-01), notes & claims full-text search (FEAT-07),
// and the ⌘K command palette (FEAT-08, plan 09-09).
//
// Contract (UI-SPEC Registry Safety / plan 09-09):
//   - PURE function over payloads the frontend has ALREADY fetched and the
//     backend has ALREADY boundary-filtered (spoiler safety T-09-09-01):
//     no server call, no second filter implementation, no new endpoint.
//   - fuse.js is FORBIDDEN (SUS-flagged) — case-insensitive substring
//     matching only, zero deps.
//   - Pattern analog: graphElements.ts (pure transform over GraphResponse).
//
// Ranking is deterministic and payload-local: exact match (rank 0) →
// starts-with (rank 1) → earliest substring (2 + index), with secondary
// fields (node id, claim predicate/object, …) ranked strictly after label
// hits. Results are capped per collection (UI-SPEC §10.3: up to 8).

import type { GraphResponse } from '../types/graph'
import type { NoteResponse } from '../types/userContent'

export type SearchCollection = 'nodes' | 'claims' | 'notes'

export type SearchResult =
  | {
      collection: 'nodes'
      id: string
      label: string
      nodeType: string
    }
  | {
      collection: 'claims'
      id: string
      label: string
      subjectId: string
      subjectLabel: string
    }
  | {
      collection: 'notes'
      id: string
      label: string
      content: string
      targetId: string
      targetLabel: string
    }

export type SearchOptions = {
  /** Collections to include; defaults to all three. */
  collections?: SearchCollection[]
  /** Max results per collection; defaults to 8 (UI-SPEC §10.3). */
  limitPerCollection?: number
}

type Ranked = { result: SearchResult; rank: number }

/** Match-quality rank for one haystack field: exact (base) → starts-with
 * (base+1) → earliest substring (base+2+index). `null` = no match. */
function matchRank(haystack: string, needle: string, base = 0): number | null {
  const text = haystack.toLowerCase()
  if (text === needle) return base
  if (text.startsWith(needle)) return base + 1
  const index = text.indexOf(needle)
  return index === -1 ? null : base + 2 + index
}

function nodeById(graph: GraphResponse, id: string) {
  return graph.nodes.find((node) => node.id === id)
}

function labelFor(graph: GraphResponse, id: string): string {
  return nodeById(graph, id)?.label ?? id
}

function searchNodes(graph: GraphResponse, needle: string, limit: number): SearchResult[] {
  const ranked: Ranked[] = []
  for (const node of graph.nodes) {
    // Label is the primary searchable field; the node id is a secondary
    // match ranked strictly after any label hit (plan 09-09 Task 1).
    const rank =
      matchRank(node.label, needle) ?? matchRank(node.id, needle, 30)
    if (rank == null) continue
    ranked.push({
      rank,
      result: {
        collection: 'nodes',
        id: node.id,
        label: node.label,
        nodeType: node.type,
      },
    })
  }
  return sortAndLimit(ranked, limit)
}

function searchClaims(graph: GraphResponse, needle: string, limit: number): SearchResult[] {
  const ranked: Ranked[] = []
  for (const claim of graph.claims) {
    // UI-SPEC §10.9: substring over label, predicate, and object label.
    const objectLabel = labelFor(graph, claim.object_id)
    const rank =
      matchRank(claim.label, needle) ??
      matchRank(claim.predicate, needle, 10) ??
      matchRank(objectLabel, needle, 20)
    if (rank == null) continue
    ranked.push({
      rank,
      result: {
        collection: 'claims',
        id: claim.id,
        label: claim.label,
        subjectId: claim.subject_id,
        subjectLabel: labelFor(graph, claim.subject_id),
      },
    })
  }
  return sortAndLimit(ranked, limit)
}

function searchNotes(graph: GraphResponse, notes: NoteResponse[], needle: string, limit: number): SearchResult[] {
  const ranked: Ranked[] = []
  for (const note of notes) {
    // UI-SPEC §10.9: substring over note content; the row's secondary line
    // is the anchor node's label.
    const rank = matchRank(note.content, needle)
    if (rank == null) continue
    ranked.push({
      rank,
      result: {
        collection: 'notes',
        id: note.id,
        label: note.content,
        content: note.content,
        targetId: note.target_id,
        targetLabel: labelFor(graph, note.target_id),
      },
    })
  }
  return sortAndLimit(ranked, limit)
}

function sortAndLimit(ranked: Ranked[], limit: number): SearchResult[] {
  return ranked
    .sort(
      (a, b) =>
        a.rank - b.rank ||
        a.result.label.length - b.result.label.length ||
        a.result.label.localeCompare(b.result.label),
    )
    .slice(0, limit)
    .map((entry) => entry.result)
}

/** Search the already-fetched, already-boundary-filtered payload. Returns
 * up to `limitPerCollection` results per requested collection, in
 * collection order: nodes, claims, notes. An empty/whitespace query returns
 * `[]` (no server call, no empty-query firehose). */
export function searchIndex(
  graph: GraphResponse,
  notes: NoteResponse[],
  query: string,
  options: SearchOptions = {},
): SearchResult[] {
  const needle = query.trim().toLowerCase()
  if (!needle) return []
  const collections = options.collections ?? ['nodes', 'claims', 'notes']
  const limit = options.limitPerCollection ?? 8
  const results: SearchResult[] = []
  for (const collection of collections) {
    if (collection === 'nodes') results.push(...searchNodes(graph, needle, limit))
    else if (collection === 'claims') results.push(...searchClaims(graph, needle, limit))
    else results.push(...searchNotes(graph, notes, needle, limit))
  }
  return results
}
