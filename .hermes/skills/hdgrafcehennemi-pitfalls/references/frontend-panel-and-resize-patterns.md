# Frontend panel & resize patterns (verified 2026-08-13, quick tasks 260813-wyp + 260813-fil)

## Settings-style control panels (user preference)
User asked: "make the filters part more like settings (the ui)". The SettingsPage visual
language (frontend/src/components/settings/SettingsPage.tsx) is the house style for any
control panel:

- Card container: `rounded-lg border border-border bg-card p-4 shadow-md` (floating panels)
  or `Card max-w-lg` (full pages).
- Header: `font-heading` title + one-line `text-xs text-muted-foreground` subtitle; ghost
  action buttons (All/None, Back) sized `min-h-11 px-2 text-xs`.
- Sections: `Separator` (ui/separator) between groups; section labels `text-sm font-medium`.
- Rows: label + control, `flex min-h-11 items-center justify-between gap-3 py-2 border-b
  border-border/60 last:border-b-0` — 44px rows per ui-ux-review Priority 2.
- Toggles: inline `role="switch"` button (NO new dependency; no Radix switch in ui/):
  `h-6 w-11 rounded-full border` track (`bg-primary` when on, `bg-muted` off), knob
  `size-[18px] rounded-full bg-background shadow translate-x-[22px]|translate-x-[3px]`,
  `aria-checked` + `aria-label="<Label> visible"`, focus ring
  `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`.
  See GraphFilterPanel.tsx `FilterSwitch`.
- Scrollable panels: `max-h-[calc(100vh-9rem)] overflow-y-auto overscroll-contain` on the
  dropdown content (keeps trigger visible; 15+ rows overflow otherwise).

Tests (GraphFilterPanel.test.tsx): open trigger → assert `role="heading"`, one
`getByRole('switch', { name: 'X visible' })` per option with `aria-checked` true; toggle
calls handler; All/None call `onSetAll(true/false)`; disabled filter reflects
`aria-checked="false"`.

## Left-edge drag-resize handle (sanctioned in-repo precedent: ChatSheet.tsx ~110-150)
The Event Timeline rail resize (260813-wyp) copies ChatSheet's drag pattern:
- Handle inside the panel's left edge: `role="separator" aria-orientation="vertical"
  aria-label="Resize ..." tabIndex={0}`, `cursor-ew-resize`, 44px hit target (w-4 with a
  centered `h-10 w-1 rounded-full bg-border` grabber), focus-visible ring.
- Pointer events: pointerdown → `setPointerCapture` → document pointermove (clamp) →
  pointerup. jsdom guard identical to ChatSheet.test.tsx (~line 37-69) for testability.
- Keyboard: ArrowLeft −16 / ArrowRight +16 (clamped).
- Clamp: `min 240`, `max min(640, Math.round(window.innerWidth * 0.6))` (jsdom 1024 →
  614.4 — bake that into test expectations).
- Width in React state applied via `style={{ width }}`; NO width transition (instant drag).
- Tests: role/aria assertions; fireEvent.pointerDown/Move/Up sequence changes width;
  ArrowRight on focused handle widens.

## Quick UX-change delivery protocol (user-driven, mid-phase)
Small user-requested UI changes ("can you make X...", "can you add Y") → implement INLINE
(fast, no gsd-quick subagents needed for one-file changes), then:
1. `feat`/`style` commit with the day's quick-id prefix (e.g. `style(260813-fil): ...`).
2. New test file if the component had none (test the behavior, not the classes).
3. Verify: focused vitest + `npm run build`, then the focused offline pytest (verification
   tracker only credits pytest — see phase10-execution-pitfalls).
4. Add a row to `.planning/STATE.md` `## Quick Tasks Completed` (id | description | date |
   commits | dir or —) and commit docs.
5. Tell the user it's live on the running vite dev server (HMR) — they test hands-on.
6. If the user retracts mid-request ("nevermind, chat button will be there"), stop, leave
   the tree untouched, no commit — do not half-implement.
