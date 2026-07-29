import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import type { SelectedElement } from '../graph/GraphCanvas'

// Minimal, unified detail panel (no Tabs yet) — the Overview/Claims/Evidence
// tab split (D-07) and the separate tab-less StructuralEdgeCard (D-06) are
// Plan 03's scope. This plan renders the same single panel for both node and
// edge selections.
type Props = {
  selected: SelectedElement | null
}

export function DetailPanel({ selected }: Props) {
  return (
    <Sheet open modal={false}>
      <SheetContent side="right" showCloseButton={false} className="mt-0">
        <SheetHeader>
          <SheetTitle>
            {selected?.kind === 'node' ? selected.label : selected?.kind === 'edge' ? selected.edgeType : 'Details'}
          </SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-2 px-4 pb-4 text-sm">
          {!selected && <p>Select a node to see details.</p>}
          {selected?.kind === 'node' && <p>Type: {selected.nodeType}</p>}
          {selected?.kind === 'edge' && (
            <>
              <p>Type: {selected.edgeType}</p>
              <p>Source: {selected.source}</p>
              <p>Target: {selected.target}</p>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
