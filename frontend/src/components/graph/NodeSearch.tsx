// FEAT-01 node search & jump + FEAT-07 notes & claims full-text search
// (plan 09-09). Floating search bar top-center over the canvas; a mode
// ToggleGroup switches between node search and grouped notes & claims
// search. Selection reuses the EXISTING selection path — `onSelect` opens
// DetailPanel exactly like a canvas tap, and App routes the row to the
// existing graphFocus mechanism (GraphCanvas's focus effect:
// cy.getElementById + .selected-dominant + fade + cy.fit(node, 48)) — never
// a second selection implementation (plan 09-09 NO-SECOND-SELECTION-
// MECHANISM).
//
// All matching is payload-local via lib/searchIndex.ts over the ALREADY
// boundary-filtered graph payload + raw notes — no fetch, no endpoint, no
// new spoiler surface (T-09-09-01, NO-NEW-SPOILER-SURFACE).

import { Fragment, useMemo, useState } from 'react'
import { FileText, Scale, Search } from 'lucide-react'
import { ToggleGroup } from 'radix-ui'
import { cn } from '@/lib/utils'
import type { GraphResponse } from '../../types/graph'
import type { NoteResponse } from '../../types/userContent'
import { searchIndex, type SearchCollection, type SearchResult } from '../../lib/searchIndex'
import { NodeSwatch } from './GraphLegend'
import { NODE_TYPES } from '@/lib/nodeTypes'

export type NodeSearchSelection = {
  id: string
  label: string
  nodeType: string
}

type Props = {
  graph: GraphResponse
  notes: NoteResponse[]
  onSelect: (selection: NodeSearchSelection) => void
  /** App-registered ref so the global '/' hotkey can focus this input. */
  inputRef?: React.RefObject<HTMLInputElement | null>
}

type Mode = 'nodes' | 'notes-claims'

const GROUP_LABELS: Record<SearchCollection, string> = {
  nodes: 'Nodes',
  claims: 'Claims',
  notes: 'Notes',
}

function swatchForType(nodeType: string) {
  return NODE_TYPES.find((meta) => meta.type === nodeType) ?? NODE_TYPES[NODE_TYPES.length - 1]
}

export function NodeSearch({ graph, notes, onSelect, inputRef }: Props) {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<Mode>('nodes')
  const [focused, setFocused] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  // FEAT-01 mode searches only nodes; FEAT-07 mode searches claims + notes
  // and groups them under sticky "Claims"/"Notes" headers (UI-SPEC §10.9).
  const results = useMemo(
    () =>
      searchIndex(graph, notes, query, {
        collections: mode === 'nodes' ? ['nodes'] : ['claims', 'notes'],
        limitPerCollection: 8,
      }),
    [graph, notes, query, mode],
  )

  // Group spans over the flat result list (contiguous same-collection runs)
  // so the sticky group headers render once per collection without mutating
  // state during render.
  const groupSpans = useMemo(() => {
    const spans: { collection: SearchCollection; start: number; end: number }[] = []
    let start = 0
    for (let i = 1; i <= results.length; i++) {
      if (i === results.length || results[i].collection !== results[i - 1].collection) {
        spans.push({ collection: results[start].collection, start, end: i })
        start = i
      }
    }
    return spans
  }, [results])

  const open = focused && query.trim().length > 0

  function select(result: SearchResult) {
    if (result.collection === 'nodes') {
      onSelect({ id: result.id, label: result.label, nodeType: result.nodeType })
    } else if (result.collection === 'claims') {
      // Claim row → open the claim's subject node (the existing
      // handleOpenDetail-style selection path, UI-SPEC §10.9).
      const subject = graph.nodes.find((node) => node.id === result.subjectId)
      onSelect({ id: result.subjectId, label: result.subjectLabel, nodeType: subject?.type ?? '' })
    } else {
      // Note row → open the note's anchor node (UI-SPEC §10.9).
      const target = graph.nodes.find((node) => node.id === result.targetId)
      onSelect({ id: result.targetId, label: result.targetLabel, nodeType: target?.type ?? '' })
    }
    setFocused(false)
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (results.length > 0) setActiveIndex((index) => Math.min(index + 1, results.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const result = results[activeIndex]
      if (result) select(result)
    } else if (event.key === 'Escape') {
      event.preventDefault()
      setFocused(false)
      event.currentTarget.blur()
    }
  }

  const rowBase = cn(
    'flex w-full items-center gap-2 px-3 py-2 text-left text-sm min-h-[44px] cursor-pointer',
    'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
  )

  return (
    <div className="absolute left-1/2 top-4 z-[55] w-72 -translate-x-1/2 md:w-96">
      <div className="flex items-center rounded-md bg-card p-1 shadow-sm ring-1 ring-border">
        {/* Mode toggle — EpisodeSelector pill contract (UI-SPEC §10.9):
            rounded-lg bg-muted p-0.5 track, active bg-accent. */}
        <ToggleGroup.Root
          type="single"
          value={mode}
          onValueChange={(next) => {
            if (next) {
              setMode(next as Mode)
              setActiveIndex(0)
            }
          }}
          className="inline-flex items-center gap-0.5 rounded-lg bg-muted p-0.5"
        >
          <ToggleGroup.Item
            value="nodes"
            className="inline-flex items-center justify-center rounded-md px-2.5 py-1 text-xs font-medium transition-colors hover:bg-elevated data-[state=on]:bg-accent data-[state=on]:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Nodes
          </ToggleGroup.Item>
          <ToggleGroup.Item
            value="notes-claims"
            className="inline-flex items-center justify-center rounded-md px-2.5 py-1 text-xs font-medium transition-colors hover:bg-elevated data-[state=on]:bg-accent data-[state=on]:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Notes & Claims
          </ToggleGroup.Item>
        </ToggleGroup.Root>
        <Search className="ml-2 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value)
            setActiveIndex(0)
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={handleKeyDown}
          aria-label={mode === 'nodes' ? 'Search nodes' : 'Search notes and claims'}
          placeholder={mode === 'nodes' ? 'Search nodes…' : 'Search notes & claims…'}
          className="w-full min-h-[44px] bg-transparent px-2 py-2 text-sm placeholder:text-muted-foreground focus:outline-none"
        />
      </div>

      {open && (
        <div className="absolute left-0 right-0 top-full z-[56] mt-1 max-h-80 overflow-y-auto rounded-md bg-popover shadow-sm ring-1 ring-border">
          {results.length === 0 ? (
            // Locked copy (UI-SPEC Copywriting Contract — FEAT-01/07/08
            // empty state), verbatim including the curly quotes.
            <div className="px-3 py-6 text-center">
              <p className="text-sm text-foreground">No nodes match “{query}”</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Try a different name, or search Notes & Claims.
              </p>
            </div>
          ) : (
            groupSpans.map((span) => (
              <Fragment key={span.collection}>
                <div className="sticky top-0 z-10 bg-popover px-3 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {GROUP_LABELS[span.collection]}
                </div>
                {results.slice(span.start, span.end).map((result, offset) => {
                  const flatIndex = span.start + offset
                  const active = flatIndex === activeIndex
                  return (
                    <button
                      key={result.id}
                      type="button"
                      onMouseDown={(event) => {
                        // onMouseDown (not onClick) so the row wins the
                        // race against the input's onBlur closing the
                        // dropdown.
                        event.preventDefault()
                        select(result)
                      }}
                      className={cn(rowBase, active && 'bg-accent/20')}
                    >
                      {result.collection === 'nodes' && (
                        <>
                          <NodeSwatch
                            shape={swatchForType(result.nodeType).shape}
                            color={swatchForType(result.nodeType).color}
                          />
                          <span className="truncate">{result.label}</span>
                          <kbd className="ml-auto shrink-0 rounded border border-border bg-muted px-1 text-xs text-muted-foreground">
                            {result.nodeType}
                          </kbd>
                        </>
                      )}
                      {result.collection === 'claims' && (
                        <>
                          <Scale className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <span className="flex min-w-0 flex-1 flex-col items-start">
                            <span className="w-full truncate">{result.label}</span>
                            <span className="w-full truncate text-xs text-muted-foreground">
                              {result.subjectLabel}
                            </span>
                          </span>
                        </>
                      )}
                      {result.collection === 'notes' && (
                        <>
                          <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <span className="flex min-w-0 flex-1 flex-col items-start">
                            <span className="w-full truncate">{result.content}</span>
                            <span className="w-full truncate text-xs text-muted-foreground">
                              {result.targetLabel}
                            </span>
                          </span>
                        </>
                      )}
                    </button>
                  )
                })}
              </Fragment>
            ))
          )}
        </div>
      )}
    </div>
  )
}
