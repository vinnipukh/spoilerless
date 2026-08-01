import type cytoscape from 'cytoscape'
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from 'lucide-react'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'

type Props = {
  cyRef: React.RefObject<cytoscape.Core | null>
  onReset: () => void
}

export function GraphControls({ cyRef, onReset }: Props) {
  function zoomIn() {
    const cy = cyRef.current
    if (!cy) return
    cy.zoom({
      level: cy.zoom() * 1.2,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    })
  }

  function zoomOut() {
    const cy = cyRef.current
    if (!cy) return
    cy.zoom({
      level: cy.zoom() / 1.2,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    })
  }

  function fitGraph() {
    const cy = cyRef.current
    if (!cy) return
    cy.fit(undefined, 48)
  }

  return (
    <div className="fixed bottom-20 left-4 z-[60] flex flex-col gap-2">
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Zoom in"
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-md bg-card text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={zoomIn}
          >
            <ZoomIn className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">Zoom in</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Zoom out"
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-md bg-card text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={zoomOut}
          >
            <ZoomOut className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">Zoom out</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Fit graph to view"
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-md bg-card text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={fitGraph}
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">Fit graph to view</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Reset zoom"
            className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-md bg-card text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            onClick={onReset}
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">Reset zoom</TooltipContent>
      </Tooltip>
    </div>
  )
}
