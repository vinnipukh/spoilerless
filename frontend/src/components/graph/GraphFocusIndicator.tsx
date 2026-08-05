// Canvas overlay pill announcing an active chat-driven `graph_focus`
// highlight (RAG-17). Same `bg-card`/`ring-border`/`text-xs`/`rounded-md`/
// `shadow-sm` visual treatment as GraphLegend.tsx's collapsed trigger pill,
// positioned `fixed top-4 left-4 z-[60]` — the one unclaimed canvas-overlay
// corner (bottom-left: GraphLegend + Create Custom Node FAB + GraphControls;
// top-right: intentionally left clear per 06-UI-SPEC.md
// "Spacing Scale" exceptions).
//
// The inline "Clear" text action copies NoteItem's (DetailPanel.tsx) inline
// Edit/Delete text-button micro-pattern rather than inventing a new one.
type Props = {
  count: number
  onClear: () => void
}

export function GraphFocusIndicator({ count, onClear }: Props) {
  return (
    <div className="fixed top-4 left-4 z-[60] flex items-center gap-2 rounded-md bg-card px-2.5 py-1.5 text-xs text-muted-foreground shadow-sm ring-1 ring-border">
      <span>Highlighting {count}</span>
      <button
        type="button"
        className="font-medium text-muted-foreground transition-colors hover:text-foreground"
        onClick={onClear}
      >
        Clear
      </button>
    </div>
  )
}
