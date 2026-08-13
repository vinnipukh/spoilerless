---
phase: 260813-wyp
plan: 01
quick_id: 260813-wyp
description: "Make the Story Event Timeline rail horizontally resizable: drag its left edge leftwards to widen so long event text is visible (custom pointer handle + keyboard support, no new dependencies)"
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/App.tsx
  - frontend/src/App.test.tsx
autonomous: true

estimate:
  tokens: 14000
  raw_tokens: 10000
  tasks: 2
  confidence: high

must_haves:
  truths:
    - Dragging the Event Timeline rail's left edge leftwards widens the rail in real time via pointer events (no new dependencies); the right edge stays pinned to the viewport right.
    - The rail width is clamped to 240px..min(640px, 60vw); ArrowLeft/ArrowRight on the focused handle adjusts the width by 16px steps.
    - The handle is an accessible separator (role="separator", aria-orientation="vertical", aria-label "Resize Event Timeline"), keyboard-focusable (tabIndex 0) with a visible focus ring, and a 44px-wide hit target.
    - The rail keeps hidden lg:flex, shrink-0, overflow-hidden, and border-l border-border; width changes are instant (no width transition/animation, no emoji, no new deps).
  artifacts:
    - frontend/src/App.tsx — EventTimelineRail component owning timelineWidth state plus the drag/keyboard handle (replaces the inline w-80 aside)
    - frontend/src/App.test.tsx — resize-handle tests inside the four-tab narrative hierarchy describe
  key_links:
    - App.tsx:774-795 (inline w-80 aside) -> EventTimelineRail (style={{ width }} replaces w-80) -> left-edge separator handle
    - ChatSheet.tsx:123-143 (role="separator" left-edge handle precedent + jsdom pointer-capture guard, ChatSheet.tsx:60-97) -> ChatSheet.test.tsx:37-69 (fireEvent.pointerDown/Move/Up drag-test pattern)
    - App.test.tsx:702-711 (four-tab describe + renderGraphWorkspace harness) -> new tests appended before the describe closes (line 810)
---

<objective>
Make the Story Event Timeline rail horizontally resizable by dragging its LEFT edge leftwards (wider) or rightwards (narrower), with keyboard support, implemented with a custom pointer-event handle — no new dependencies.

Purpose: the rail is fixed at w-80 (320px, App.tsx:777), so long event labels/text clip. The user wants to widen it on demand by dragging its left edge; the right edge stays pinned to the viewport (the rail is the last child of the graph-workspace flex row, App.tsx:657-797).

Output: an EventTimelineRail component in App.tsx (width state default 320px, clamp 240..min(640, 60vw), pointerdown/move/up drag on a role="separator" handle, ArrowLeft/ArrowRight ±16px keyboard steps, 44px hit target, visible focus ring), plus App.test.tsx coverage. Files touched: frontend/src/App.tsx and frontend/src/App.test.tsx ONLY.
</objective>

<context>
Verified against current source (2026-08-13, branch main):

- Rail markup: App.tsx:774-795 — `<aside aria-label="Event Timeline" className="hidden w-80 shrink-0 flex-col overflow-hidden border-l border-border lg:flex">` wrapping `<TimelineView ... showHeading />` with 8 props (nodes, claims, episodes, selectedId, onSelect, filteredIds, onToggleFilter, onClearFilter). Rendered only when `topTab === 'story' && storyMode === 'event_timeline'`, as the LAST child of the flex row — so the right edge is inherently pinned; changing only the width shifts only the left edge. The 10-05 comment block above it (lines 768-773, D-17/D-38) must stay verbatim.
- IN-REPO PRECEDENT (copy this, do not invent a new pattern): ChatSheet.tsx:123-143 renders a left-edge resize handle — `role="separator"`, `aria-orientation="vertical"`, `aria-label="Resize chat panel"`, `cursor-ew-resize`, `touch-none`, `focus-visible:ring-2 focus-visible:ring-ring`, inner grabber `h-10 w-1 rounded-full bg-border/70` — driven by onPointerDown/Move/Up/Cancel with `event.preventDefault()` + `setPointerCapture` in try/catch (jsdom does not implement pointer capture; ChatSheet.tsx:60-97). Its tests (ChatSheet.test.tsx:30-69) drive drags with `fireEvent.pointerDown(handle, { clientX, pointerId: 1 })` / pointerMove / pointerUp and assert `toHaveStyle({ width: '...px' })`; jsdom innerWidth is 1024 by default (ChatSheet.test.tsx:26-27).
- What THIS task adds over the ChatSheet precedent: (a) width state lives in the RAIL — a local component that mounts/unmounts with the conditional, so the width resets naturally on mode switch (task brief: no persistence needed, no localStorage); (b) keyboard support — ChatSheet's handle has NO tabIndex/onKeyDown; ours must be focusable and step ±16px on ArrowLeft/ArrowRight; (c) 44px-wide hit target (w-11) instead of ChatSheet's 16px (w-4) — the ui-ux-review 44px min hit target (Priority 1) governs; (d) NO width transition of any kind (simplest compliance with "no animation during drag" + prefers-reduced-motion); the grabber color snaps via conditional classes, no transition-colors.
- Drag math (delta-based — robust in browsers AND jsdom): pointerdown records `{ x: clientX, width: currentWidth }`; each pointermove sets `width = startWidth + (startX - clientX)` — moving the pointer LEFT (startX > clientX) widens. Clamp: `Math.max(240, Math.min(Math.min(640, window.innerWidth * 0.6), w))`. jsdom innerWidth 1024 → max clamp = 614.4. Keyboard: `clamp(width ∓ 16)`.
- App.tsx imports: line 1 is `import { useEffect, useRef, useState } from 'react'` — NO cn util, NO ReactNode, NO useCallback. So: extend line 1 with `type ReactNode`; do NOT use cn (concatenate class strings); plain functions, no useCallback. `function AppContent()` is at line 841, `function App()` at 868 — the new component goes just above AppContent.
- Test harness: App.test.tsx — four-tab describe at line 702; `renderGraphWorkspace()` (703-711) renders `<App />` with authenticated auth state + seeded sessionStorage watchProgress and waits for `graph-canvas-stub`; the rail is found via `screen.findByRole('complementary', { name: 'Event Timeline' })` and inner elements via `within(rail)` (lines 722-738 precedent). The existing tests (especially 722-738 and 782-809) must stay untouched. testing-library import at line 5 is `import { render, screen, waitFor, within } from '@testing-library/react'` — fireEvent is NOT imported yet and IS required for pointer tests; userEvent IS available for the keyboard test. New tests go after line 809, still inside the describe (closes line 810).
- Constraints honored: NO new dependencies (react-resizable-panels prohibited — project no-new-registry rule + 10-05 plan prohibition; the ChatSheet pattern is the sanctioned in-repo implementation); D-20 `hidden lg:flex` (desktop/tablet only) unchanged; no emoji in the handle UI; TimelineView untouched (its root is `flex h-full flex-col`, TimelineView.tsx:130 — wrapping it in `<div className="min-w-0 flex-1">{children}</div>` inside a `flex h-full min-h-0` row preserves height/scroll; the aside keeps overflow-hidden).
- Commit discipline (repo rule): atomic commits with explicit `git add <paths>` only (never -A, never .planning); code commit and test commit separate; push after green; branch main.
</context>

<tasks>

<task type="auto">
  <name>Task 1: EventTimelineRail component — width state + left-edge drag/keyboard handle (App.tsx)</name>
  <files>frontend/src/App.tsx</files>
  <action>
    [imports] App.tsx:1 — extend to `import { useEffect, useRef, useState, type ReactNode } from 'react'` (ReactNode is needed by the new component; do NOT import cn or useCallback — neither exists in this file).

    [new component] Define a module-level local component `EventTimelineRail` just above `function AppContent()` (line 841):

    ```
    const TIMELINE_MIN_WIDTH = 240
    const TIMELINE_MAX_WIDTH = 640
    const TIMELINE_WIDTH_STEP = 16

    function clampTimelineWidth(width: number) {
      return Math.max(TIMELINE_MIN_WIDTH, Math.min(Math.min(TIMELINE_MAX_WIDTH, window.innerWidth * 0.6), width))
    }

    function EventTimelineRail({ children }: { children: ReactNode }) {
      const [timelineWidth, setTimelineWidth] = useState(320)
      const [dragging, setDragging] = useState(false)
      const dragStart = useRef<{ x: number; width: number } | null>(null)

      const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
        event.preventDefault()
        try {
          event.currentTarget.setPointerCapture(event.pointerId)
        } catch {
          // jsdom does not implement pointer capture — drag still works via the
          // pointer events dispatched directly on the handle (ChatSheet.tsx:60-69).
        }
        dragStart.current = { x: event.clientX, width: timelineWidth }
        setDragging(true)
      }

      const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
        if (!dragStart.current) return
        setTimelineWidth(clampTimelineWidth(dragStart.current.width + (dragStart.current.x - event.clientX)))
      }

      const onPointerUp = (event: React.PointerEvent<HTMLDivElement>) => {
        dragStart.current = null
        setDragging(false)
        try {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId)
          }
        } catch {
          // jsdom (mirrors ChatSheet.tsx:81-86)
        }
      }

      const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        if (event.key === 'ArrowLeft') {
          event.preventDefault()
          setTimelineWidth((width) => clampTimelineWidth(width - TIMELINE_WIDTH_STEP))
        } else if (event.key === 'ArrowRight') {
          event.preventDefault()
          setTimelineWidth((width) => clampTimelineWidth(width + TIMELINE_WIDTH_STEP))
        }
      }

      return (
        <aside
          aria-label="Event Timeline"
          style={{ width: timelineWidth }}
          className="hidden shrink-0 flex-col overflow-hidden border-l border-border lg:flex"
        >
          <div className="flex h-full min-h-0">
            <div
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize Event Timeline"
              aria-keyshortcuts="ArrowLeft ArrowRight"
              tabIndex={0}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
              onKeyDown={onKeyDown}
              className="group flex w-11 shrink-0 cursor-ew-resize touch-none select-none items-center justify-center outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <span
                className={
                  'h-12 w-0.5 rounded-full bg-border group-hover:bg-foreground/40' +
                  (dragging ? ' bg-primary' : '')
                }
              />
            </div>
            <div className="min-w-0 flex-1">{children}</div>
          </div>
        </aside>
      )
    }
    ```

    [replace the rail block] At App.tsx:774-795 replace the inline `<aside ...>...</aside>` with:

    ```
    {topTab === 'story' && storyMode === 'event_timeline' && (
      <EventTimelineRail>
        <TimelineView
          nodes={graphState.status === 'success' ? graphState.data.nodes : []}
          claims={graphState.status === 'success' ? graphState.data.claims : []}
          episodes={episodes}
          selectedId={selectedElement?.kind === 'node' ? selectedElement.id : null}
          onSelect={handleTimelineSelect}
          filteredIds={timelineFilterIds}
          onToggleFilter={(id) =>
            setTimelineFilterIds((prev) =>
              prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
            )
          }
          onClearFilter={() => setTimelineFilterIds([])}
          showHeading
        />
      </EventTimelineRail>
    )}
    ```

    The TimelineView props must be byte-identical to today — only the wrapper changes. Keep the 10-05 comment block above it (lines 768-773) verbatim.

    Intent notes (do not deviate without updating Task 2's expectations):
    - `w-80` is REMOVED from the aside className — replaced by `style={{ width: timelineWidth }}`. Never both.
    - The handle is `w-11` = 44px wide: the ui-ux-review 44px min hit target governs over the "w-4" hint in the task brief (w-4 = 16px fails Priority 1; ChatSheet's 16px handle is the older precedent). The strip is full-height inside the h-full row → 44px × full-height hit target.
    - `cursor-ew-resize` (horizontal resize; ChatSheet precedent) — NOT col-resize.
    - NO width transition/animation anywhere (aside has none; grabber has no transition-colors — colors snap). Simplest compliance with "no animated width during drag" and prefers-reduced-motion.
    - `hidden lg:flex`, `shrink-0`, `overflow-hidden`, `border-l border-border` all preserved (D-20 desktop/tablet only). Right edge stays pinned (aside is the flex row's last child).
    - State resets naturally: EventTimelineRail mounts/unmounts with the conditional → width resets to 320 on mode switch. No localStorage.
    - No new dependencies; no emoji; no changes to TimelineView, ChatSheet, or any other file.

    Commit atomically (code-only): `git add frontend/src/App.tsx` then commit with `feat(260813-wyp): resizable Event Timeline rail with drag + keyboard handle` — explicit path only, never `git add -A`, never stage .planning files.
  </action>
  <verify>
    <automated>NODE_ENV=test CI=1 npm --prefix frontend test -- --run src/App.test.tsx && npm --prefix frontend run build</automated>
  </verify>
  <done>
    EventTimelineRail defined and wired; aside width driven by style={{ width: timelineWidth }} (default 320); separator handle present with role/aria-label/aria-orientation/tabIndex, 44px w-11 strip, cursor-ew-resize, focus-visible ring; drag math = startWidth + (startX - clientX) clamped to [240, min(640, 60vw)]; ArrowLeft/ArrowRight step ±16px; existing App.test.tsx suite still passes (no tests modified yet); `npm --prefix frontend run build` (tsc -b) clean.
  </done>
</task>

<task type="auto">
  <name>Task 2: App.test.tsx — resize-handle coverage (render/aria, keyboard, drag, clamps)</name>
  <files>frontend/src/App.test.tsx</files>
  <action>
    [import] App.test.tsx:5 — add fireEvent: `import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'`.

    [tests] Append 4 tests INSIDE the four-tab describe (after the last test, which ends at line 809, before the describe closes at line 810). Reuse renderGraphWorkspace; each test opens the rail with `await user.click(screen.getByRole('tab', { name: 'Event Timeline' }))`, then `const rail = await screen.findByRole('complementary', { name: 'Event Timeline' })` and `const handle = within(rail).getByRole('separator', { name: 'Resize Event Timeline' })`. Do NOT touch the existing tests (especially lines 722-738 and 782-809).

    1. "renders the rail with an accessible resize handle": expect rail toHaveStyle({ width: '320px' }); expect handle toHaveAttribute('aria-orientation', 'vertical'); expect handle toHaveAttribute('aria-keyshortcuts', 'ArrowLeft ArrowRight'); expect handle toHaveAttribute('tabindex', '0').

    2. "keyboard arrows resize the timeline rail by 16px steps": `await user.click(handle)` (focuses it), then `await user.keyboard('{ArrowRight}')` → expect rail toHaveStyle({ width: '336px' }); then `await user.keyboard('{ArrowLeft}')` → '320px'; `await user.keyboard('{ArrowLeft}')` → '304px'.

    3. "dragging the left edge leftwards widens the rail": `fireEvent.pointerDown(handle, { clientX: 700, pointerId: 1 })`; `fireEvent.pointerMove(handle, { clientX: 500, pointerId: 1 })` → width = 320 + (700 - 500) = 520 → expect rail toHaveStyle({ width: '520px' }); `fireEvent.pointerUp(handle, { clientX: 500, pointerId: 1 })`.

    4. "rail width clamps to [240, min(640, 60vw)]": drag right (narrow): pointerDown clientX 700 → pointerMove clientX 800 → 320 - 100 = 220 → clamped → expect '240px'; then drag left (wide): pointerDown clientX 700 → pointerMove clientX 300 → 320 + 400 = 720 → clamped to min(640, 0.6 * 1024 = 614.4) → expect '614.4px'; pointerUp after each drag. (jsdom innerWidth defaults to 1024 — ChatSheet.test.tsx:26-27 precedent; do not redefine it.)

    These tests are RED if Task 1's handle is absent (getByRole('separator', { name: 'Resize Event Timeline' }) throws) or the math changes (toHaveStyle mismatch) — real regression coverage, same shape as ChatSheet.test.tsx:37-69.

    Commit atomically (test-only): `git add frontend/src/App.test.tsx` then commit with `test(260813-wyp): resize-handle coverage for Event Timeline rail` — explicit path only, never `git add -A`, never stage .planning files.
  </action>
  <verify>
    <automated>NODE_ENV=test CI=1 npm --prefix frontend test -- --run src/App.test.tsx && npm --prefix frontend run build && NODE_ENV=test CI=1 npm --prefix frontend test</automated>
  </verify>
  <done>
    4 new tests pass in the focused run; the FULL frontend suite (NODE_ENV=test CI=1 npm --prefix frontend test) and `npm --prefix frontend run build` are green; no existing test was modified; no production files in this commit.
  </done>
</task>

</tasks>

<verification>
- NODE_ENV=test CI=1 npm --prefix frontend test -- --run src/App.test.tsx — focused App suite (Tasks 1 + 2)
- NODE_ENV=test CI=1 npm --prefix frontend test — full frontend suite (Task 2; catches describe-scope/mock bleed)
- npm --prefix frontend run build — tsc -b typecheck gate (test-file TS errors only surface here — 09-07 lesson: run the build yourself before closing)
- Manual spot check (optional): npm --prefix frontend run dev — Story → Event Timeline on a wide viewport; drag the rail's left edge leftwards → rail widens past 320px and long event text becomes visible; ArrowLeft/ArrowRight on the focused handle steps 16px; switch to Episode Overview and re-open Event Timeline → width back to 320px; focus ring visible on keyboard focus.
</verification>

<success_criteria>
- The Event Timeline rail's left edge drags horizontally: leftwards widens (up to min(640px, 60vw)), rightwards narrows (down to 240px); right edge pinned; width changes are instant with no animation.
- Keyboard: focused handle + ArrowRight/ArrowLeft adjusts width by 16px steps with a visible focus ring; handle is a 44px-wide role="separator" with aria-label "Resize Event Timeline" and aria-orientation="vertical".
- No new dependencies, no emoji, no width transitions; files touched: frontend/src/App.tsx + frontend/src/App.test.tsx only.
- Change is 2 atomic commits (code, tests) on main; focused + full frontend suites and the production build are green; no existing test modified.
</success_criteria>
