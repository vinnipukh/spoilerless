import { useState } from 'react'
import { Filter, ChevronDown, CheckCheck, X } from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
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

// Settings-style toggle (260813): role=switch row control, 44px hit target,
// visible focus ring, no new dependency.
function FilterSwitch({
  checked,
  label,
  onCheckedChange,
}: {
  checked: boolean
  label: string
  onCheckedChange: (next: boolean) => void
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onCheckedChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
        checked ? 'border-primary bg-primary' : 'border-border bg-muted'
      }`}
    >
      <span
        aria-hidden="true"
        className={`inline-block size-[18px] rounded-full bg-background shadow transition-transform ${
          checked ? 'translate-x-[22px]' : 'translate-x-[3px]'
        }`}
      />
    </button>
  )
}

export function GraphFilterPanel({
  filterState,
  onToggleNodeType,
  onToggleEdgeFamily,
  onSetAll,
}: Props) {
  const [open, setOpen] = useState(false)

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="fixed top-20 left-1/2 -translate-x-1/2 z-[40] w-80 md:ml-[21.4rem]">
      {/* 08-06: on md+, the Filters pill sits beside the centered search
          bar, immediately right of it. NOTE: the pill is `fixed` (viewport
          coords) while the search bar is `absolute` inside the graph
          container, so top-20 is the correct row (top-4 hid the pill under
          the fixed header; top-16 read slightly high — 08-06). Bar is
          w-96 centered -> right edge at 50%+192px; the trigger is mx-auto
          in this w-72 container, so ml-[15.5rem] puts its center ~8px
          right of the bar's right edge. 260813-ftl: +5cm right of the
          original position (ml-[21.4rem]) per user. Mobile keeps the old
          centered position. */}
      <CollapsibleTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="mx-auto flex min-h-[44px] h-8 items-center gap-1.5 rounded-full bg-card/95 px-3 text-xs text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground backdrop-blur-sm"
        >
          <Filter className="size-3.5" />
          <span>Filters</span>
          <ChevronDown className={`size-3 transition-transform ${open ? 'rotate-180' : ''}`} />
        </Button>
      </CollapsibleTrigger>

      {/* 260813: settings-style panel — card header + labeled rows with
          switches (mirrors SettingsPage's form language), Separator between
          sections, ghost All/None actions in the header. */}
      <CollapsibleContent className="mt-2 rounded-lg border border-border bg-card p-4 shadow-md">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="font-heading text-base text-foreground">Graph Filters</h2>
            <p className="text-xs text-muted-foreground">
              Control which node and relationship types appear in the scene.
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="min-h-11 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => onSetAll(true)}
            >
              <CheckCheck className="mr-1 size-3" />
              All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="min-h-11 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => onSetAll(false)}
            >
              <X className="mr-1 size-3" />
              None
            </Button>
          </div>
        </div>

        <Separator className="my-3" />

        {/* Node Types */}
        <div className="flex flex-col">
          <div className="mb-1 text-sm font-medium text-foreground">Node types</div>
          {NODE_TYPES.map((nt) => {
            const active = filterState.nodeTypes[nt.type] ?? true
            return (
              <div
                key={nt.type}
                className="flex min-h-11 items-center justify-between gap-3 border-b border-border/60 py-2 last:border-b-0"
              >
                <span className="flex min-w-0 items-center gap-2 text-sm text-foreground">
                  <NodeSwatch shape={nt.shape} color={nt.color} />
                  <span className="truncate">{nt.type}</span>
                </span>
                <FilterSwitch
                  checked={active}
                  label={`${nt.type} visible`}
                  onCheckedChange={() => onToggleNodeType(nt.type)}
                />
              </div>
            )
          })}
        </div>

        <Separator className="my-3" />

        {/* Edge Families */}
        <div className="flex flex-col">
          <div className="mb-1 text-sm font-medium text-foreground">Relationships</div>
          {EDGE_FAMILIES.map((ef) => {
            const active = filterState.edgeFamilies[ef.family] ?? true
            return (
              <div
                key={ef.family}
                className="flex min-h-11 items-center justify-between gap-3 border-b border-border/60 py-2 last:border-b-0"
              >
                <span className="flex min-w-0 items-center gap-2 text-sm text-foreground">
                  <span className="inline-block size-2 shrink-0 rounded-full" style={{ backgroundColor: ef.hex }} />
                  <span className="truncate">{ef.family}</span>
                </span>
                <FilterSwitch
                  checked={active}
                  label={`${ef.family} visible`}
                  onCheckedChange={() => onToggleEdgeFamily(ef.family)}
                />
              </div>
            )
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}
