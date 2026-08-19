# Quick task 260805-te3 — Visitor (Misafir) Read-Only Mode — detail + verification

Session: 2026-08-05. gsd-quick task, done INLINE (user preference: no
subagents). Task dir: `.planning/quick/260805-te3-add-a-visitor-misafir-read-only-login-vi/`
(PLAN.md + SUMMARY.md `status: complete`). **Status: COMPLETE — commits
`73b87a7` (feat, 11 files) + `e0d2a0d` (docs: PLAN/SUMMARY/STATE.md row).**

## Design (verified)

Backend already 401s every anonymous write (09-03, `0f3c388`): `user_content.py`,
`progress.py` (GET + POSTs), `change_set.py`, `chat.py`, `revisions.py`,
`candidates.py` all take `CurrentUserDependency`. All READ routes are anonymous:
`graph.py` GET graph / POST path / GET export, `series.py`. → visitor mode is
FRONTEND-ONLY enforcement + entry.

## File-by-file changes (committed)

- `frontend/src/providers/AuthContext.ts` — `AuthState` gains
  `{ status: 'visitor' }`; `AuthContextValue` gains `enterVisitor: () => void`.
- `frontend/src/providers/AuthProvider.tsx` — `enterVisitor()` sets visitor +
  sessionStorage `spoilerless.visitor='1'`; mount: `/me` AUTH_UNAUTHENTICATED
  + flag set → `visitor` (a 200 `/me` always wins); `login`/`logout` clear the
  flag. Reload keeps visitor mode (per tab session).
- `frontend/src/components/auth/LoginPage.tsx` — "Continue as visitor" outline
  button + "Browse the graph without an account — read-only." subtitle.
- `frontend/src/components/layout/AppShell.tsx` — optional `visitor` +
  `onSignIn` props: muted "Visitor" badge + "Sign in" button replace the
  account block.
- `frontend/src/hooks/useWatchProgress.ts` — `useWatchProgress({ persist })`
  (default true). `persist:false`: skip mount hydration GET; `requestChange`
  applies `{seriesId, viewAsOfOrder}` locally (never POST, never
  pendingChange/modal, returns true); `confirmChange` no-ops.
- `frontend/src/App.tsx` — `isVisitor`; `useWatchProgress({ persist: !isVisitor })`;
  auto-seed effect (visitor + no seriesId + series list loaded → select first
  series at order 1 via local `requestChange`, `visitorSeededRef` guard);
  GraphCanvas `readOnly={isVisitor}` + `onShareLink` undefined; ChatLauncher +
  ChatSheet + palette chat row hidden; AppShell `visitor`/`onSignIn={logout}`.
  (Note: added `useEffect` to the `import { useRef, useState }` line — the
  original App.tsx did NOT import useEffect; missing it = ReferenceError.)
- `frontend/src/components/detail/DetailPanel.tsx` — `readOnly?: boolean`:
  hides Create Relationship button, note add/edit/delete, and the whole Notes
  tab body degrades to "Sign in to view and manage notes." (GET /notes is
  auth-gated → error state would otherwise show). ALSO carries the
  TooltipProvider prod fix (below).
- `frontend/src/components/palette/CommandPalette.tsx` — `onOpenChat?` optional;
  chat action row only rendered when provided.

## Tests (pass counts from real runs)

- `useWatchProgress.test.ts` +3 (`persist:false`: local-only, no POST, no
  hydration, confirm no-op) → 3/3 ✓
- `App.test.tsx` +1 visitor flow (login → click "Continue as visitor" →
  Visitor badge, no "Open chat" button) → 1/1 ✓; whole file 16/16 after the
  TooltipProvider fix (was 4 red).
- `DetailPanel.test.tsx` +2 readOnly → whole file **20/20 ✓** (was 16 red).
- Full FE suite: 38/38 files, 288/288 tests, two consecutive runs. Run 1 had
  one SettingsPage "trims whitespace" timing flake (passes in isolation and
  in run 2) — inverse of the 09-07 rule: confirm a full-suite red with a
  second full run before chasing it.
- `npm run build` (tsc -b + vite): BUILD_EXIT=0. Backend: 0 files changed in
  `spoilerless/` (`git diff --name-only <base>..HEAD -- spoilerless/`).

## The TooltipProvider production crash (the big find — FIXED)

20 "pre-existing" reds (DetailPanel 16 + App 4) traced to ONE real bug:
`DetailPanel.tsx` renders a Radix `Tooltip` (Export Markdown button, FEAT-05)
on every selection, with NO `TooltipProvider` ancestor — GraphCanvas
self-wraps (`:531`) but DetailPanel is a sibling rendered by App. Radix throws
`Tooltip must be used within TooltipProvider` at runtime → **selecting any node
crashed the app in production**. The red tests were right.

- Fix (applied in `73b87a7`): DetailPanel's `<Sheet>` return is wrapped in
  `<TooltipProvider>` (GraphCanvas's self-wrap pattern). Cured all 20 reds
  (DetailPanel 16/16, App 16/16).
- Rule for future FE work: any component adding a Radix `Tooltip` must
  SELF-WRAP in `TooltipProvider` or be wrapped at App root — never rely on a
  sibling's provider. This Radix error in test output = real prod bug, fix
  the source; a test wrapper is defense-in-depth only.
- Test-side: `renderPanel = render(<TooltipProvider>…</TooltipProvider>)`
  helper replaced all 20 render sites. Watch out: `patch replace_all` misses
  `const { unmount } = render(` and multiline `render(\n <DetailPanel` forms
  — sweep those manually.

## Pre-existing-reds proof technique

Before blaming (or "fixing") unrelated suite reds, prove provenance:
`git stash push -- <paths>` → run the failing files → `git stash pop`. Same
failure count on the clean tree = pre-existing — but keep investigating
anyway: 2026-08-05's 20 reds were proven pre-existing via stash, THEN traced
to the real Tooltip bug (stash-proven pre-existing ≠ not worth fixing).

## gsd-quick on this repo

- `branch_name: null` in config → work on LOCAL main. Correct here: origin/main
  is a stale ancestor (63+ commits behind local) — NEVER fork quick-task
  branches off origin/HEAD in this repo; the workflow's #2916 rule assumes
  origin is current.
- `gsd-tools query init.quick "<desc>"` → quick_id/slug/task_dir (native
  `node "C:/Users/<user>/AppData/Local/hermes/gsd-core/bin/gsd-tools.cjs"` form,
  never `$HOME` — MSYS path trap). Executor commits code only; orchestrator's
  docs commit stages the quick dir + STATE.md explicitly (never
  `.planning/config.json` or the sibling's `.planning/tmp/*`).
