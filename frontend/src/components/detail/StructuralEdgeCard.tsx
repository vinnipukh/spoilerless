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
      <SheetContent side="right" showCloseButton={false} className="mt-0">
        <SheetHeader>
          <SheetTitle>{selected.edgeType}</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-2 px-4 pb-4 text-sm">
          <p>
            {sourceLabel} → {targetLabel}
          </p>
        </div>
      </SheetContent>
    </Sheet>
  )
}
