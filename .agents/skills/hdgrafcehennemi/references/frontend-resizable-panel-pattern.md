# Frontend resizable-panel pattern (validated 260813-wyp)

Canonical in-repo implementation for a horizontally resizable panel with a custom left-edge drag handle — **ChatSheet.tsx**. Copy it for any new resizable panel; do NOT add react-resizable-panels (project no-new-registry rule; 10-05 plan prohibition).

## ChatSheet.tsx — the precedent
- Handle markup (lines 123-143): left-edge strip `role="separator" aria-orientation="vertical" aria-label="Resize chat panel"`, `cursor-ew-resize`, `touch-none`, `focus-visible:ring-2 focus-visible:ring-ring`, inner grabber `<span className="h-10 w-1 rounded-full bg-border/70 ..." />`.
- Drag handlers (lines 60-97): `onPointerDown` → `event.preventDefault()` + `setPointerCapture` inside try/catch ("jsdom does not implement pointer capture"), `onPointerMove` recomputes width from `clientX`, `onPointerUp` releases capture (guarded by `hasPointerCapture`), `onPointerCancel={onPointerUp}`.
- ChatSheet persists width to localStorage (`chatSheetWidth`) and double-click resets (lines 87-106) — ONLY if persistence is wanted; 260813-wyp's rail deliberately has none (state resets on unmount via a local component).

## Test pattern (ChatSheet.test.tsx:30-69)
- Drive the drag with `fireEvent.pointerDown(handle, { clientX, pointerId: 1 })` → `pointerMove` → `pointerUp` dispatched on the handle element itself; assert `toHaveStyle({ width: '624px' })`.
- jsdom `innerWidth` defaults to 1024; ChatSheet.test.tsx:26-27 re-asserts it via `Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1024 })`.

## 260813-wyp additions (Event Timeline rail in App.tsx)
- Delta drag math: `width = startWidth + (startX - clientX)` — pointer LEFT widens; clamp `[240, min(640, 0.6 * innerWidth)]` (jsdom: max 614.4). Keyboard ArrowLeft/Right step ±16px via `tabIndex={0}` + `onKeyDown` — ChatSheet's handle has NO keyboard support; ours must add it.
- 44px min hit target (ui-ux-review Priority 1): use `w-11` (44px). ChatSheet's `w-4` (16px) is the older, non-compliant precedent. A task brief saying "w-4 … 44px hit target" is internally contradictory — the 44px rule governs; flag the deviation in the plan.
- NO width transitions at all (no `transition-colors` on the grabber; colors snap via conditional classes) — simplest compliance with "no animated width during drag" + prefers-reduced-motion.
- Width state lives in a local component that mounts/unmounts with the render conditional → resets naturally on mode switch (no persistence needed).
- App.tsx specifics: no `cn`/`useCallback`/`ReactNode` imports exist — extend line 1 (`import { useEffect, useRef, useState, type ReactNode } from 'react'`), concatenate class strings, plain functions.

## App.test.tsx integration-test facts (four-tab describe, line 702)
- `renderGraphWorkspace()` (703-711): `currentAuthState = 'authenticated'` + seed sessionStorage `spoilerless.watchProgress` + `render(<App />)` + `await findByTestId('graph-canvas-stub')`.
- Rail found via `screen.findByRole('complementary', { name: 'Event Timeline' })`; inner elements via `within(rail)`.
- The @testing-library/react import (line 5) has NO `fireEvent` — add it for pointer tests; `userEvent` already imported for keyboard tests.

## Verification commands (canonical for frontend tasks)
- Focused: `NODE_ENV=test CI=1 npm --prefix frontend test -- --run src/App.test.tsx`
- Gate: `npm --prefix frontend run build` (tsc -b — test-file TS errors only surface here, 09-07 lesson)
- Full suite: `NODE_ENV=test CI=1 npm --prefix frontend test`
