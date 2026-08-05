import { useEffect, useMemo, useRef, useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import type { GraphClaim, GraphNode } from '@/types/graph'
import type { EpisodeResponse } from '@/types/series'
import { TimelineEventRow } from './TimelineEventRow'

// FEAT-02 timeline view (UI-SPEC §10.4): a full-canvas chronological list of
// Event nodes from the ALREADY boundary-filtered graph payload (never a new
// data call — T-09-10-01). Events are sorted by visible_from_order then
// episode order (stable secondary: label) and grouped under sticky episode
// headers. Rows are keyboard-navigable (↑/↓/Enter) and selecting one routes
// through the existing onSelect path so the graph frames the node.

export type TimelineSelection = {
  id: string
  label: string
  nodeType: string
}

type Props = {
  nodes: GraphNode[]
  claims: GraphClaim[]
  episodes: EpisodeResponse[]
  selectedId: string | null
  onSelect: (selection: TimelineSelection) => void
}

type GroupedEvent = {
  node: GraphNode
  episode: EpisodeResponse | undefined
  claimsCount: number
}

function episodeCodeFor(event: GraphNode, episodes: EpisodeResponse[]): EpisodeResponse | undefined {
  if (event.episode_id) {
    return episodes.find((episode) => episode.id === event.episode_id)
  }
  return episodes.find((episode) => episode.episode_order === event.visible_from_order)
}

export function TimelineView({ nodes, claims, episodes, selectedId, onSelect }: Props) {
  const [activeIndex, setActiveIndex] = useState(0)

  const groups = useMemo(() => {
    const events = nodes
      .filter((node) => node.type === 'Event')
      .sort((a, b) => {
        const byVisibility = a.visible_from_order - b.visible_from_order
        if (byVisibility !== 0) return byVisibility
        const episodeA = episodeCodeFor(a, episodes)?.episode_order ?? Number.MAX_SAFE_INTEGER
        const episodeB = episodeCodeFor(b, episodes)?.episode_order ?? Number.MAX_SAFE_INTEGER
        const byEpisode = episodeA - episodeB
        if (byEpisode !== 0) return byEpisode
        return a.label.localeCompare(b.label)
      })

    const claimsByEntity = new Map<string, number>()
    for (const claim of claims) {
      claimsByEntity.set(claim.subject_id, (claimsByEntity.get(claim.subject_id) ?? 0) + 1)
      if (claim.object_id) {
        claimsByEntity.set(claim.object_id, (claimsByEntity.get(claim.object_id) ?? 0) + 1)
      }
    }

    const grouped: { key: string; code: string | null; episodeOrder: number; events: GroupedEvent[] }[] = []
    for (const node of events) {
      const episode = episodeCodeFor(node, episodes)
      const key = episode?.id ?? `order-${node.visible_from_order}`
      let group = grouped.find((g) => g.key === key)
      if (!group) {
        group = {
          key,
          code: episode?.code ?? `Order ${node.visible_from_order}`,
          episodeOrder: episode?.episode_order ?? node.visible_from_order,
          events: [],
        }
        grouped.push(group)
      }
      group.events.push({
        node,
        episode,
        claimsCount: claimsByEntity.get(node.id) ?? 0,
      })
    }
    return grouped
  }, [nodes, claims, episodes])

  const flatEvents = useMemo(
    () => groups.flatMap((group) => group.events.map((event) => ({ group, event }))),
    [groups],
  )

  const rowRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    if (flatEvents.length === 0) return
    rowRefs.current[activeIndex]?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex, flatEvents.length])

  if (flatEvents.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 p-8 text-center">
        <p className="font-heading text-base text-foreground">The timeline is empty</p>
        <p className="text-sm text-muted-foreground">
          Advance your watch progress to reveal more events.
        </p>
      </div>
    )
  }

  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => Math.min(index + 1, flatEvents.length - 1))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => Math.max(index - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const current = flatEvents[activeIndex]
      if (current) {
        onSelect({
          id: current.event.node.id,
          label: current.event.node.label,
          nodeType: current.event.node.type,
        })
      }
    }
  }

  let rowIndex = -1

  return (
    <div className="flex h-full flex-col" onKeyDown={handleKeyDown}>
      <ScrollArea className="h-full">
        <div className="border-l-2 border-border pl-4 ml-3 py-4 pr-4">
          {groups.map((group) => (
            <section key={group.key} aria-label={group.code ?? undefined}>
              <h3 className="sticky top-0 z-10 bg-background/90 py-2 font-heading text-sm text-muted-foreground backdrop-blur">
                {group.code}
              </h3>
              {group.events.map((event) => {
                rowIndex += 1
                const index = rowIndex
                const selected = selectedId === event.node.id || activeIndex === index
                return (
                  <div key={event.node.id} ref={(el) => { rowRefs.current[index] = el }}>
                    <TimelineEventRow
                      label={event.node.label}
                      episodeCode={event.episode?.code ?? null}
                      claimsCount={event.claimsCount}
                      selected={selected}
                      onSelect={() => {
                        setActiveIndex(index)
                        onSelect({
                          id: event.node.id,
                          label: event.node.label,
                          nodeType: event.node.type,
                        })
                      }}
                    />
                  </div>
                )
              })}
            </section>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
