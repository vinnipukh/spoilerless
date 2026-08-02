import { ArrowRight } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import type { SelectedEdge } from '../graph/GraphCanvas'
import type { GraphNode } from '../../types/graph'

// Distinct, tab-less minimal detail card (D-06) for structural edges
// (PART_OF/PRECEDES — claim_id is null). No Tabs, no Claims/Evidence
// content — signals "not a narrative claim" rather than showing
// empty/disabled claim/evidence tabs. App.tsx's centralized branch (Task 2)
// is the only place that decides whether a selected edge renders here or in
// the tabbed DetailPanel.
type Props = {
  selected: SelectedEdge
  nodes: GraphNode[]
}

function resolveLabel(nodes: GraphNode[], id: string): string {
  return nodes.find((node) => node.id === id)?.label ?? id
}

export function StructuralEdgeCard({ selected, nodes }: Props) {
  const sourceLabel = resolveLabel(nodes, selected.source)
  const targetLabel = resolveLabel(nodes, selected.target)

  return (
    <Sheet open modal={false}>
      <SheetContent
        side="left"
        showCloseButton={false}
        className="mt-0 max-sm:!inset-x-0 max-sm:!bottom-0 max-sm:!top-auto max-sm:!h-auto max-sm:max-h-[70vh] max-sm:!w-full max-sm:!border-t max-sm:!border-l-0 lg:max-w-md"
      >
        <SheetHeader>
          <SheetTitle>{selected.edgeType}</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-2 px-4 pb-4 text-sm">
          <div className="flex items-center gap-2 rounded-md border border-border p-3">
            <span>{sourceLabel}</span>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span>{targetLabel}</span>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
