// ⌘K command palette (FEAT-08 = FEAT-11.3 quick-switcher, plan 09-09).
// Dialog-style overlay: full-screen scrim, centered panel, groups
// "Jump to node" / "Switch episode" / "Actions". Node rows share the
// payload-local searchIndex with NodeSearch; episode rows route through the
// palette's `onRequestChange` prop, which App wires to watchProgress
// requestChange (PROB-31 semantics: locked episodes → unlock dialog, never
// a silent no-op); action rows open chat/timeline/settings/dashboard and
// trigger the export seam. Keyboard: ↑/↓/Enter/Esc.

import { Fragment, useEffect, useMemo, useRef, useState, type ComponentType } from 'react'
import {
  CalendarClock,
  Clapperboard,
  Command,
  Download,
  LayoutGrid,
  MessageSquare,
  Settings,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { GraphResponse } from '../../types/graph'
import type { EpisodeResponse } from '../../types/series'
import { searchIndex, type SearchResult } from '../../lib/searchIndex'
import { NodeSwatch } from '../graph/GraphLegend'
import { NODE_TYPES } from '../../lib/nodeTypes'
import { modLabel } from '../../hooks/useHotkey'

export type CommandPaletteSelection = {
  id: string
  label: string
  nodeType: string
}

type Icon = ComponentType<{ className?: string }>

type ActionDef = {
  id: string
  label: string
  icon: Icon
  run: () => void
}

// Narrowed node variant of the SearchResult union — rows are only ever built
// for `collection: 'nodes'` results (claims/notes filtered at build time), so
// the render path can read nodeType without re-narrowing (TS2339).
type NodeSearchResult = Extract<SearchResult, { collection: 'nodes' }>

type Row =
  | { group: 'node'; key: string; node: NodeSearchResult }
  | { group: 'episode'; key: string; episode: EpisodeResponse }
  | { group: 'action'; key: string; action: ActionDef }

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  graph: GraphResponse | null
  episodes: EpisodeResponse[]
  onSelectNode: (selection: CommandPaletteSelection) => void
  /** App wires this to watchProgress.requestChange — locked episodes route
   * to the unlock dialog per the PROB-31 fix (09-07). */
  onRequestChange: (episodeOrder: number) => void
  onOpenChat: () => void
  onOpenTimeline: () => void
  onOpenSettings: () => void
  onOpenDashboard: () => void
  onExportGraph: () => void
}

const GROUP_LABELS: Record<Row['group'], string> = {
  node: 'Jump to node',
  episode: 'Switch episode',
  action: 'Actions',
}

function swatchForType(nodeType: string) {
  return NODE_TYPES.find((meta) => meta.type === nodeType) ?? NODE_TYPES[NODE_TYPES.length - 1]
}

export function CommandPalette({
  open,
  onOpenChange,
  graph,
  episodes,
  onSelectNode,
  onRequestChange,
  onOpenChat,
  onOpenTimeline,
  onOpenSettings,
  onOpenDashboard,
  onExportGraph,
}: Props) {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)

  // Reset the query + cursor when the palette closes (the "adjust state
  // when a prop changes" render pattern, same as useGraph.ts).
  if (!open && (query !== '' || activeIndex !== 0)) {
    setQuery('')
    setActiveIndex(0)
  }

  // Autofocus the input each time the palette opens.
  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // Action rows are static; filtering happens against the query below.
  const actions: ActionDef[] = useMemo(
    () => [
      { id: 'chat', label: 'Open chat', icon: MessageSquare, run: onOpenChat },
      { id: 'timeline', label: 'Open timeline', icon: CalendarClock, run: onOpenTimeline },
      { id: 'settings', label: 'Open settings', icon: Settings, run: onOpenSettings },
      { id: 'dashboard', label: 'Open dashboard', icon: LayoutGrid, run: onOpenDashboard },
      { id: 'export', label: 'Export graph', icon: Download, run: onExportGraph },
    ],
    [onOpenChat, onOpenTimeline, onOpenSettings, onOpenDashboard, onExportGraph],
  )

  const needle = query.trim().toLowerCase()

  const rows: Row[] = useMemo(() => {
    const next: Row[] = []
    if (graph) {
      const nodeResults = searchIndex(graph, [], query, {
        collections: ['nodes'],
        limitPerCollection: 8,
      })
      for (const result of nodeResults) {
        // Narrow the SearchResult union to the node variant (claims/notes
        // are never requested here — the palette shares the FEAT-01/07
        // index for the "Jump to node" group only).
        if (result.collection !== 'nodes') continue
        next.push({ group: 'node', key: `node:${result.id}`, node: result })
      }
    }
    const matchedEpisodes = needle
      ? episodes.filter((episode) => {
          const title = episode.display_title ?? episode.title
          return episode.code.toLowerCase().includes(needle) || title.toLowerCase().includes(needle)
        })
      : episodes
    for (const episode of matchedEpisodes) {
      next.push({ group: 'episode', key: `episode:${episode.id}`, episode })
    }
    const matchedActions = actions.filter((action) => action.label.toLowerCase().includes(needle))
    for (const action of matchedActions) {
      next.push({ group: 'action', key: `action:${action.id}`, action })
    }
    return next
  }, [graph, episodes, actions, query, needle])

  if (!open) return null

  function select(row: Row) {
    if (row.group === 'node') {
      onSelectNode({
        id: row.node.id,
        label: row.node.label,
        nodeType: row.node.nodeType,
      })
    } else if (row.group === 'episode') {
      onRequestChange(row.episode.episode_order)
    } else {
      row.action.run()
    }
    onOpenChange(false)
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (rows.length > 0) setActiveIndex((index) => Math.min(index + 1, rows.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const row = rows[activeIndex]
      if (row) select(row)
    } else if (event.key === 'Escape') {
      event.preventDefault()
      onOpenChange(false)
    }
  }

  // Group spans over the flat row list → one sticky header per group.
  const groupSpans: { group: Row['group']; start: number; end: number }[] = []
  let start = 0
  for (let i = 1; i <= rows.length; i++) {
    if (i === rows.length || rows[i].group !== rows[i - 1].group) {
      groupSpans.push({ group: rows[start].group, start, end: i })
      start = i
    }
  }

  const rowBase = cn(
    'flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm min-h-[44px] cursor-pointer',
    'hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
  )

  return (
    <div
      className="fixed inset-0 z-[70] flex items-start justify-center bg-background/80 backdrop-blur"
      onMouseDown={(event) => {
        // Clicking the scrim (not the panel) closes the palette.
        if (event.target === event.currentTarget) onOpenChange(false)
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="mt-24 w-full max-w-lg rounded-lg bg-card shadow-sm ring-1 ring-border"
      >
        <div className="flex items-center border-b border-border">
          <Command className="ml-3 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setActiveIndex(0)
            }}
            onKeyDown={handleKeyDown}
            aria-label="Command palette"
            placeholder="Type a command or search…"
            className="w-full min-h-[44px] bg-transparent px-3 py-2.5 text-sm placeholder:text-muted-foreground focus:outline-none"
          />
          <kbd className="mr-3 hidden shrink-0 rounded border border-border bg-muted px-1 text-xs text-muted-foreground sm:inline">
            {modLabel()}K
          </kbd>
        </div>

        <div className="max-h-96 overflow-y-auto p-1">
          {rows.length === 0 ? (
            // Locked copy (UI-SPEC Copywriting Contract — command palette empty).
            <div className="px-3 py-8 text-center text-sm text-muted-foreground">
              No matching commands
            </div>
          ) : (
            groupSpans.map((span) => (
              <Fragment key={span.group}>
                <div className="px-3 py-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  {GROUP_LABELS[span.group]}
                </div>
                {rows.slice(span.start, span.end).map((row, offset) => {
                  const flatIndex = span.start + offset
                  const active = flatIndex === activeIndex
                  return (
                    <button
                      key={row.key}
                      type="button"
                      onMouseDown={(event) => {
                        event.preventDefault()
                        select(row)
                      }}
                      className={cn(rowBase, active && 'bg-accent/20')}
                    >
                      {row.group === 'node' && (
                        <>
                          <NodeSwatch
                            shape={swatchForType(row.node.nodeType).shape}
                            color={swatchForType(row.node.nodeType).color}
                          />
                          <span className="truncate">{row.node.label}</span>
                          <kbd className="ml-auto shrink-0 rounded border border-border bg-muted px-1 text-xs text-muted-foreground">
                            {row.node.nodeType}
                          </kbd>
                        </>
                      )}
                      {row.group === 'episode' && (
                        <>
                          <Clapperboard className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <span className="truncate">
                            {row.episode.code} — {row.episode.display_title ?? row.episode.title}
                          </span>
                          <kbd className="ml-auto shrink-0 rounded border border-border bg-muted px-1 text-xs text-muted-foreground">
                            {row.episode.code}
                          </kbd>
                        </>
                      )}
                      {row.group === 'action' && (
                        <>
                          <row.action.icon className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <span className="truncate">{row.action.label}</span>
                        </>
                      )}
                    </button>
                  )
                })}
              </Fragment>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
