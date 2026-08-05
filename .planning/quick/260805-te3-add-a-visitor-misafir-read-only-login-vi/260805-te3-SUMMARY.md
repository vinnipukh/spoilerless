---
status: complete
date: 2026-08-05
quick_id: 260805-te3
slug: add-a-visitor-misafir-read-only-login-vi
---

# Quick Task 260805-te3: Visitor (Misafir) Read-Only Login

## Summary

Added a read-only visitor (misafir) login: the LoginPage now offers
"Continue as visitor" — browsing the graph without an account. Visitors can
view the graph, switch episodes/series (local-only boundary, never persisted),
use search/timeline/export/path-finder, but **cannot add nodes or notes** (or
anything else): every write affordance is hidden (create-node FAB, create
relationship, note add/edit/delete, chat, share-link creation) and the
backend independently 401s all anonymous writes (09-03 gating, unchanged).

## Files

- `frontend/src/providers/AuthContext.ts` — `{ status: 'visitor' }` +
  `enterVisitor` in the context contract.
- `frontend/src/providers/AuthProvider.tsx` — visitor state, sessionStorage
  persistence (`spoilerless.visitor`), logout/login clear the flag; a 200
  `/api/auth/me` always wins over the flag.
- `frontend/src/components/auth/LoginPage.tsx` — "Continue as visitor" button.
- `frontend/src/components/layout/AppShell.tsx` — Visitor badge + Sign in.
- `frontend/src/hooks/useWatchProgress.ts` — `{ persist: false }`: local-only
  `requestChange`, no-op `confirmChange`, skipped hydration GET.
- `frontend/src/App.tsx` — `isVisitor` wiring: `useWatchProgress({ persist: !isVisitor })`,
  GraphCanvas `readOnly`, chat launcher/sheet + palette chat row hidden,
  first-series auto-seed for visitors.
- `frontend/src/components/detail/DetailPanel.tsx` — `readOnly` prop hides
  Create Relationship + note writes; Notes tab → "Sign in to view and manage
  notes."; **TooltipProvider self-wrap** (Export Markdown tooltip crashed node
  selection — see fixes).
- `frontend/src/components/palette/CommandPalette.tsx` — `onOpenChat` optional,
  chat row hidden for visitors.
- Tests: `useWatchProgress.test.ts` (+3), `DetailPanel.test.tsx` (+2 readOnly,
  + renderPanel TooltipProvider helper), `App.test.tsx` (+1 visitor flow).

## Fixes landed (surfaced by this task's verification)

- **Production crash fixed**: `DetailPanel`'s Export Markdown `Tooltip`
  (09-11 FEAT-05) rendered with no `TooltipProvider` in the tree —
  selecting any node threw "Tooltip must be used within TooltipProvider".
  Self-contained provider added (same pattern as `GraphCanvas.tsx:531`).
  This was the root cause of 20 pre-existing test reds (DetailPanel 16,
  App 4) — all cured.

## Verification

- `npm run build` (tsc -b + vite build): **BUILD_EXIT=0**.
- Full frontend suite: **38/38 files, 288/288 tests green** (second
  consecutive full run; one SettingsPage timing flake observed in run 1,
  passes in isolation and in run 2 — unrelated to this task).
- Backend: zero changes (anonymous writes already 401 since 09-03).
- Commits: `73b87a7` (feature). Docs commit follows.

## Notes

- Visitor choice persists per browser tab session (sessionStorage); reload
  keeps visitor mode; "Sign in" exits it.
- Earlier graph-declutter work (GraphCanvas layout + simple-node dots) remains
  uncommitted in the working tree — separate concern, user-directed.
