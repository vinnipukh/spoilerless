import { useCallback, useState } from 'react'
import { cn } from '@/lib/utils'

// 12-08 (THERMO-P2-05): unified pointer-capture drag-rail primitive. One
// implementation of the pointer down/move/up dance (with the jsdom fallback
// for environments without setPointerCapture), keyboard arrow stepping, and
// double-click reset — consumed by both resizable surfaces (chat sheet width,
// event timeline height) instead of duplicated drag math.
type Props = {
  /** Accessible label for the separator handle. */
  label: string
  /** Which edge the rail sits on — determines cursor and resize math. */
  orientation: 'vertical' | 'horizontal'
  /**
   * Compute the next dimension from the pointer event. Receives the raw
   * clientX/clientY so each consumer owns its own clamping and anchoring
   * (right-edge rails subtract from innerWidth; bottom-edge rails from
   * innerHeight).
   */
  onResize: (dimension: number | null, point: { x: number; y: number }) => void
  onResizeStart?: () => void
  onResizeEnd?: (point: { x: number; y: number }) => void
  onDoubleClick?: () => void
  className?: string
  children?: React.ReactNode
}

export function ResizableRail({
  label,
  orientation,
  onResize,
  onResizeStart,
  onResizeEnd,
  onDoubleClick,
  className,
  children,
}: Props) {
  const [dragging, setDragging] = useState(false)

  const onPointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      try {
        event.currentTarget.setPointerCapture(event.pointerId)
      } catch {
        // jsdom does not implement pointer capture — drag still works via
        // the pointer events dispatched directly on the handle.
      }
      setDragging(true)
      onResizeStart?.()
    },
    [onResizeStart],
  )

  const handlePoint = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => ({
      x: event.clientX,
      y: event.clientY,
    }),
    [],
  )

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!dragging) return
      const point = handlePoint(event)
      onResize(null, point)
    },
    [dragging, handlePoint, onResize],
  )

  const endDrag = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!dragging) return
      setDragging(false)
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId)
      }
      onResizeEnd?.(handlePoint(event))
    },
    [dragging, handlePoint, onResizeEnd],
  )

  return (
    <div
      role="separator"
      aria-orientation={orientation}
      aria-label={label}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onDoubleClick={onDoubleClick}
      onKeyDown={(event) => {
        // Keyboard step resizing (260813-wyp parity): arrows nudge by 16px.
        const step = 16
        const point = {
          x: orientation === 'vertical' ? window.innerWidth - step : 0,
          y: orientation === 'horizontal' ? window.innerHeight - step : 0,
        }
        if (orientation === 'vertical') {
          if (event.key === 'ArrowLeft') {
            event.preventDefault()
            onResize(window.innerWidth - step, point)
          } else if (event.key === 'ArrowRight') {
            event.preventDefault()
            onResize(window.innerWidth + step, point)
          } else {
            return
          }
        } else {
          if (event.key === 'ArrowUp') {
            event.preventDefault()
            onResize(window.innerHeight - step, point)
          } else if (event.key === 'ArrowDown') {
            event.preventDefault()
            onResize(window.innerHeight + step, point)
          } else {
            return
          }
        }
      }}
      className={cn(
        'group absolute z-10 flex touch-none items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-ring',
        orientation === 'vertical'
          ? 'inset-y-0 -left-2 w-4 cursor-ew-resize'
          : 'inset-x-0 -top-2 h-4 cursor-ns-resize',
        className,
      )}
    >
      {children ?? (
        <span
          className={cn(
            'rounded-full bg-border/70 transition-colors',
            orientation === 'vertical' ? 'h-10 w-1' : 'h-1 w-10',
            dragging ? 'bg-primary' : 'hover:bg-primary/60',
          )}
        />
      )}
    </div>
  )
}
