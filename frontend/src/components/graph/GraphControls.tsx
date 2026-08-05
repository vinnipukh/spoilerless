import type cytoscape from 'cytoscape'
import { ZoomIn, ZoomOut, Maximize2, RotateCcw, Waypoints, Download, Share2, MousePointer2 } from 'lucide-react'
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip'

type Props = {
  cyRef: React.RefObject<cytoscape.Core | null>
  onReset: () => void
  pathModeActive?: boolean
  onPathModeChange?: (active: boolean) => void
  focusModeActive?: boolean
  onFocusModeChange?: (active: boolean) => void
  onExport?: () => void
  exporting?: boolean
  exported?: boolean
  onShareLink?: () => void
}

export function GraphControls({
  cyRef,
  onReset,
  pathModeActive = false,
  onPathModeChange,
  focusModeActive = false,
  onFocusModeChange,
  onExport,
  exported = false,
  onShareLink,
}: Props) {

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
    <div className="fixed bottom-20 left-4 z-[60] flex flex-col gap-2 pb-[env(safe-area-inset-bottom)]">
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

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Show path"
            className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-md shadow-sm ring-1 ring-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              pathModeActive
                ? 'bg-accent text-accent-foreground'
                : 'bg-card text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => onPathModeChange?.(!pathModeActive)}
          >
            <Waypoints className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">Show path</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-label="Toggle focus mode"
            className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-md shadow-sm ring-1 ring-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
              focusModeActive
                ? 'bg-accent text-accent-foreground'
                : 'bg-card text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => onFocusModeChange?.(!focusModeActive)}
          >
            <MousePointer2 className="h-4 w-4" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="left">Toggle focus mode</TooltipContent>
      </Tooltip>

      {onExport && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label="Export Markdown"
              className={`flex h-11 w-11 cursor-pointer items-center justify-center rounded-md bg-card shadow-sm ring-1 ring-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                exported ? 'text-accent' : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={onExport}
            >
              <Download className="h-4 w-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="left">{exported ? 'Exported' : 'Export Markdown'}</TooltipContent>
        </Tooltip>
      )}

      {onShareLink && (
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              aria-label="Share snapshot"
              className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-md bg-card text-muted-foreground shadow-sm ring-1 ring-border hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              onClick={onShareLink}
            >
              <Share2 className="h-4 w-4" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="left">Share snapshot</TooltipContent>
        </Tooltip>
      )}
    </div>
  )
}


