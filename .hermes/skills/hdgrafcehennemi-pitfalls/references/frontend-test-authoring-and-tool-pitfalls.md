# Frontend test-authoring & tool pitfalls (260813-wyp, EventTimelineRail)

Lessons from quick task 260813-wyp (resizable Event Timeline rail, App.tsx drag/keyboard
handle + App.test.tsx coverage). Applies to any React+vitest+jsdom work in this repo.

## user-event v14 click does not focus handles that preventDefault on pointerdown

`user.click(handle)` does NOT focus a `tabIndex={0}` element whose `onPointerDown`
calls `event.preventDefault()` (jsdom): the click's focus step is suppressed, so
`user.keyboard('{ArrowRight}')` targets `document.body` and the width never changes.

- First symptom: keyboard assertion fails showing the PRE-key width (`width: 320px`
  when 336px expected) while the drag tests pass — the handler itself is fine.
- Fix: `handle.focus()` before `user.keyboard(...)`. Deterministic and still exercises
  the real `onKeyDown` handler. (The 260813-wyp plan prescribed `user.click(handle)`;
  that works only in a real browser, not jsdom.)
- The pointer-drag pattern (`fireEvent.pointerDown/Move/Up` with `{ clientX, pointerId: 1 }`)
  is unaffected — it drives React's pointer handlers directly.

## Hermes patch-tool block insertion re-indents inserted lines

Replacing a multi-line anchor (e.g. `</AppShell>\n  )\n}\n\nfunction AppContent() {`)
can return inserted lines offset by the matched anchor line's indentation (observed +4
in App.tsx at the module-level insertion point). The result is syntactically valid but
cosmetically wrong (declaration at 4-space indent, body at 2).

- Always re-read the inserted region after a large patch.
- Fix with a uniform de-indent via execute_code: detect CRLF vs LF first, split on the
  detected newline, strip N leading spaces from the exact line range, rejoin with the
  same newline. Never rewrite the whole file (line endings + encoding must stay intact).
- Alternative for surgical insertions (import lines, test blocks): do them in
  execute_code with exact-match `str.replace` + count assertions instead of the patch
  tool — full control over indentation and no fuzzy-match surprises.

## Fractional clamp widths match toHaveStyle — do not round

Clamp math `min(640, window.innerWidth * 0.6)` at jsdom's default innerWidth 1024 gives
614.4; `toHaveStyle({ width: '614.4px' })` passes as-is. Plan/test numbers were baked to
614.4 — do NOT round the clamp (e.g. `Math.round`) to make tests look cleaner; it breaks
the documented expectation and the plan's intent notes.

## hermes verify / pytest on frontend-only changes

`hermes verify --detect-only` in this repo detects the BACKEND recipe
(FastAPI: `test: ["pytest"]`, `start: uvicorn main:app:8000`). For frontend-only changes:

- The sanctioned verify chain is: focused vitest
  (`NODE_ENV=test CI=1 npm --prefix frontend test -- --run <file>`), then
  `npm --prefix frontend run build` (tsc -b), then the full vitest suite.
- Redirecting `hermes verify` to a frontend recipe via `.hermes/environment.json` is a
  protected-file write (requires user consent) — do not attempt it silently from a
  subagent; report the blocker instead. Backend pytest is a ~40-min serial suite against
  a shared live Neo4j/AuraDB and verifies nothing about React changes.
