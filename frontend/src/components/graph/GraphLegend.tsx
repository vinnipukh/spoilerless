import { useState } from 'react'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import {
  EDGE_TYPE_TO_FAMILY,
  FAMILY_HEX,
  type EdgeColorFamily,
} from './relationshipStyles'
import { ChevronDown } from 'lucide-react'
import { NODE_TYPES } from '@/lib/nodeTypes'

// --- Relationship-family metadata ---
type FamilyMeta = {
  family: EdgeColorFamily
  hex: string
  exampleTypes: string[]
}

const FAMILIES: FamilyMeta[] = (() => {
  const map = new Map<EdgeColorFamily, string[]>()
  for (const [edgeType, family] of Object.entries(EDGE_TYPE_TO_FAMILY)) {
    if (!map.has(family)) map.set(family, [])
    map.get(family)!.push(edgeType)
  }
  return Array.from(map.entries()).map(([family, types]) => ({
    family,
    hex: FAMILY_HEX[family],
    exampleTypes: types,
  }))
})()

// Edge types considered "forward-compatible" (zero-instance groups)
const FORWARD_COMPATIBLE_EDGE_TYPES = new Set([
  'LOCATED_IN',
  'CORRECTS',
  'SUPERSEDES',
  'REVERTS_TO',
])

// Exported for NodeSearch/CommandPalette search rows (plan 09-09) — same
// swatch the GraphLegend uses, so search rows and the legend agree visually.
export function NodeSwatch({ shape, color }: { shape: string; color: string }) {
  const base =
    'inline-block shrink-0 border border-white/10'
  switch (shape) {
    case 'ellipse':
      return (
        <span
          className={`${base} h-3.5 w-3.5 rounded-full`}
          style={{ backgroundColor: color }}
        />
      )
    case 'round-rect':
      return (
        <span
          className={`${base} h-3 w-3.5 rounded-sm`}
          style={{ backgroundColor: color }}
        />
      )
    case 'diamond':
      return (
        <span
          className={`${base} h-3 w-3 rotate-45`}
          style={{ backgroundColor: color }}
        />
      )
    case 'tag':
      return (
        <span
          className={`${base} h-3 w-3.5 rounded-r-full rounded-l-sm`}
          style={{ backgroundColor: color }}
        />
      )
    case 'star':
      return (
        <span
          className={`${base} h-3.5 w-3.5`}
          style={{
            backgroundColor: color,
            clipPath:
              'polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%)',
          }}
        />
      )
    default:
      return (
        <span
          className={`${base} h-3 w-3 rounded-sm`}
          style={{ backgroundColor: color }}
        />
      )
  }
}

function EdgeSwatch({ color }: { color: string }) {
  return (
    <span
      className="inline-block h-0.5 w-4 shrink-0 rounded-full"
      style={{ backgroundColor: color }}
    />
  )
}

export function GraphLegend() {
  const [open, setOpen] = useState(false)

  // Separate forward-compatible edge families
  const mainFamilies = FAMILIES.map((f) => ({
    ...f,
    exampleTypes: f.exampleTypes.filter(
      (t) => !FORWARD_COMPATIBLE_EDGE_TYPES.has(t),
    ),
  })).filter((f) => f.exampleTypes.length > 0)

  const forwardFamilies = FAMILIES.map((f) => ({
    ...f,
    exampleTypes: f.exampleTypes.filter((t) =>
      FORWARD_COMPATIBLE_EDGE_TYPES.has(t),
    ),
  })).filter((f) => f.exampleTypes.length > 0)

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className="fixed bottom-4 left-20 z-[60] max-w-56 pb-[env(safe-area-inset-bottom)]"
    >
      <CollapsibleTrigger
        aria-expanded={open}
        aria-label={open ? 'Hide legend' : 'Show legend'}
        className="flex cursor-pointer items-center gap-1.5 rounded-md bg-card px-2.5 py-1.5 text-xs text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring data-[state=open]:rounded-b-none"
      >
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-0' : '-rotate-90'}`}
        />
        Legend
      </CollapsibleTrigger>

      <CollapsibleContent className="max-h-56 overflow-y-auto rounded-md rounded-t-none bg-card p-3 text-xs shadow-sm ring-1 ring-border data-[state=closed]:hidden">
        {/* Node Types */}
        <div className="mb-3">
          <h4 className="mb-1.5 font-medium text-foreground">Node Types</h4>
          <ul className="space-y-1">
            {NODE_TYPES.map((nt) => (
              <li key={nt.type} className="flex items-center gap-2">
                <NodeSwatch shape={nt.shape} color={nt.color} />
                <span className="text-muted-foreground">{nt.type}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Relationships */}
        <div className="mb-3">
          <h4 className="mb-1.5 font-medium text-foreground">Relationships</h4>
          <ul className="space-y-1.5">
            {mainFamilies.map((f) => (
              <li key={f.family} className="flex items-center gap-2">
                <EdgeSwatch color={f.hex} />
                <span className="text-muted-foreground">
                  {f.exampleTypes.join(', ')}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Forward-compatible */}
        {forwardFamilies.length > 0 && (
          <div className="opacity-50">
            <h4 className="mb-1 font-medium text-foreground">
              Forward-compatible
            </h4>
            <ul className="space-y-1">
              {forwardFamilies.map((f) => (
                <li key={f.family} className="flex items-center gap-2">
                  <EdgeSwatch color={f.hex} />
                  <span className="text-muted-foreground">
                    {f.exampleTypes.join(', ')}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
