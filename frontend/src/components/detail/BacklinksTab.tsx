import { ListTree } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { GraphResponse } from '@/types/graph'
import type { NoteResponse } from '@/types/userContent'
import type { SelectedElement } from '../graph/GraphCanvas'

type Props = {
  selectedElement: SelectedElement | null
  graph: GraphResponse | null
  userNotes: NoteResponse[]
  onSelectNode: (nodeId: string) => void
}

export function BacklinksTab({
  selectedElement,
  graph,
  userNotes,
  onSelectNode,
}: Props) {
  if (!selectedElement || selectedElement.kind !== 'node' || !graph) {
    return (
      <div className="p-4 text-center text-xs text-muted-foreground">
        Select a node to view backlinks.
      </div>
    )
  }

  const targetId = selectedElement.id

  // Incoming edges: edges targeting the selected node
  const incomingEdges = graph.edges.filter((e) => e.target === targetId)
  const nodeById = new Map(graph.nodes.map((n) => [n.id, n]))

  // Note mentions: user notes that contain the node label as substring
  const nodeLabel = selectedElement.label
  const mentioningNotes = userNotes.filter(
    (n) => n.content && n.content.toLowerCase().includes(nodeLabel.toLowerCase()),
  )

  const hasBacklinks = incomingEdges.length > 0 || mentioningNotes.length > 0

  if (!hasBacklinks) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <ListTree className="mb-2 size-8 text-muted-foreground/50" />
        <p className="text-sm font-medium text-muted-foreground">No backlinks yet</p>
        <p className="mt-1 text-xs text-muted-foreground/75">
          Nothing else points to this node.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4 p-4">
      {incomingEdges.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Incoming Connections ({incomingEdges.length})
          </h4>
          <div className="space-y-1.5">
            {incomingEdges.map((edge) => {
              const sourceNode = nodeById.get(edge.source)
              const sourceLabel = sourceNode?.label ?? edge.source
              return (
                <div
                  key={edge.id}
                  className="flex items-center justify-between gap-2 rounded-md border border-border bg-card p-2 text-xs shadow-sm"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      {edge.type}
                    </span>
                    <span className="truncate font-medium text-foreground">
                      {sourceLabel}
                    </span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 text-xs"
                    onClick={() => onSelectNode(edge.source)}
                  >
                    Open
                  </Button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {mentioningNotes.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Mentioned in Notes ({mentioningNotes.length})
          </h4>
          <div className="space-y-1.5">
            {mentioningNotes.map((note) => (
              <div
                key={note.id}
                className="rounded-md border border-border bg-card p-2 text-xs shadow-sm"
              >
                <div className="font-medium text-muted-foreground">
                  Mentioned in note
                </div>
                <div className="mt-1 text-foreground line-clamp-2">
                  {note.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
