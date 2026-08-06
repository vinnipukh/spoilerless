// 08-06+ (product owner): module-level auto-zoom-hold interaction state.
//
// The canvas unmounts on every graph refetch (destructive loading unmount),
// so per-component state (useRef/useState) would lose the 20s "no auto
// zoom-out after touch" hold on each remount. This module survives remounts;
// GraphCanvas.tsx reads/writes it and the reset hook exists for tests only.
//
// `lastViewport` is what a held remount restores — a fresh cy otherwise
// starts at the default zoom-1 origin.

export const autoZoomHold = {
  lastTouchAt: Number.NEGATIVE_INFINITY,
  lastViewport: { zoom: 1, pan: { x: 0, y: 0 } },
}

/** Test-only: clear the module-level interaction state between tests. */
export function __resetAutoZoomStateForTests() {
  autoZoomHold.lastTouchAt = Number.NEGATIVE_INFINITY
}
