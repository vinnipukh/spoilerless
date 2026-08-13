import { useState } from 'react'
import { Filter, ChevronDown, CheckCheck, X } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { NODE_TYPES } from '@/lib/nodeTypes'
import { NodeSwatch } from './GraphLegend'
import { EDGE_TYPE_TO_FAMILY, FAMILY_HEX, type EdgeColorFamily } from './relationshipStyles'
import type { FilterState } from './filterState'

type Props = {
  filterState: FilterState
  onToggleNodeType: (type: string) => void
  onToggleEdgeFamily: (family: string) => void
  onSetAll: (enabled: boolean) => void
}

const EDGE_FAMILIES: { family: EdgeColorFamily; hex: string }[] = (() => {
  const families = new Set<EdgeColorFamily>(Object.values(EDGE_TYPE_TO_FAMILY))
  return Array.from(families).map((f) => ({
    family: f,
    hex: FAMILY_HEX[f],
  }))
})()

export function GraphFilterPanel({
  filterState,
  onToggleNodeType,
  onToggleEdgeFamily,
  onSetAll,
}: Props) {
  const [open, setOpen] = useState(false)

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="fixed top-20 left-1/2 -translate-x-1/2 z-[40] w-72 md:ml-[9.6rem]">
      {/* 08-06: on md+, the Filters pill sits beside the centered search
          bar, immediately right of it. NOTE: the pill is `fixed` (viewport
          coords) while the search bar is `absolute` inside the graph
          container, so top-20 is the correct row (top-4 hid the pill under
          the fixed header; top-16 read slightly high — 08-06). Bar is
          w-96 centered -> right edge at 50%+192px; the trigger is mx-auto
          in this w-72 container, so ml-[15.5rem] puts its center ~8px
          right of the bar's right edge. 260813-ftl: moved ~2.5cm left
          (ml-[9.6rem]) per user. Mobile keeps the old centered
          position. */}
      <CollapsibleTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="mx-auto flex h-8 items-center gap-1.5 rounded-full bg-card/95 px-3 text-xs text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground backdrop-blur-sm"
        >
          <Filter className="size-3.5" />
          <span>Filters</span>
          <ChevronDown className={`size-3 transition-transform ${open ? 'rotate-180' : ''}`} />
        </Button>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-2 rounded-lg border border-border bg-card p-3 shadow-md">
        {/* Node Types */}
        <div className="mb-3">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Node Types
          </div>
          <div className="flex flex-wrap gap-1.5">
            {NODE_TYPES.map((nt) => {
              const active = filterState.nodeTypes[nt.type] ?? true
              return (
                <button
                  key={nt.type}
                  type="button"
                  onClick={() => onToggleNodeType(nt.type)}
                  className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-opacity ${
                    active ? 'bg-muted text-foreground' : 'bg-muted/40 text-muted-foreground opacity-40'
                  }`}
                >
                  <NodeSwatch shape={nt.shape} color={nt.color} />
                  <span>{nt.type}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Edge Families */}
        <div className="mb-3">
          <div className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Relationships
          </div>
          <div className="flex flex-wrap gap-1.5">
            {EDGE_FAMILIES.map((ef) => {
              const active = filterState.edgeFamilies[ef.family] ?? true
              return (
                <button
                  key={ef.family}
                  type="button"
                  onClick={() => onToggleEdgeFamily(ef.family)}
                  className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-opacity ${
                    active ? 'bg-muted text-foreground' : 'bg-muted/40 text-muted-foreground opacity-40'
                  }`}
                >
                  <span className="inline-block size-2 rounded-full" style={{ backgroundColor: ef.hex }} />
                  <span>{ef.family}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Footer controls */}
        <div className="flex items-center justify-between border-t border-border pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => onSetAll(true)}
          >
            <CheckCheck className="mr-1 size-3" />
            All
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
            onClick={() => onSetAll(false)}
          >
            <X className="mr-1 size-3" />
            None
          </Button>
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
