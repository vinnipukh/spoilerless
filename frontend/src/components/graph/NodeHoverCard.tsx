import { useEffect, useState } from 'react'
import type { GraphClaim, GraphNode } from '@/types/graph'

type Props = {
  node: GraphNode | null
  claims?: GraphClaim[]
  position: { x: number; y: number } | null
  onDismiss: () => void
}

export function NodeHoverCard({ node, claims = [], position, onDismiss }: Props) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!node || !position) return

    const timer = setTimeout(() => {
      setVisible(true)
    }, 120)

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onDismiss()
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      clearTimeout(timer)
      setVisible(false)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [node, position, onDismiss])

  if (!node || !position || !visible) return null

  const firstClaim = claims.find((c) => c.subject_id === node.id || c.object_id === node.id)

  return (
    <div
      className="pointer-events-none fixed z-[70] hidden w-56 rounded-md bg-card p-3 shadow-sm ring-1 ring-border md:block"
      style={{
        left: `${position.x + 12}px`,
        top: `${position.y}px`,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-foreground truncate">{node.label}</span>
        <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          {node.type}
        </span>
      </div>
      {node.visible_from_order != null && (
        <div className="mt-1 text-xs text-muted-foreground">
          Revealed in Episode #{node.visible_from_order}
        </div>
      )}
      {firstClaim && (
        <div className="mt-2 text-xs text-muted-foreground line-clamp-2 italic">
          "{firstClaim.label}"
        </div>
      )}
    </div>
  )
}
