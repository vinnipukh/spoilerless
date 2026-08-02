---
title: Unify Chat and Settings header navigation controls
slug: unify-header-chat-settings
status: complete
date: 2026-08-02
---

# Summary

Chat and Settings header controls unified into one shared `HeaderNavAction`
component (`frontend/src/components/layout/HeaderNavAction.tsx`).

Root cause: Chat was a raw `<button>` with `h-11 rounded-md gap-1.5 text-sm
hover:bg-elevated` + `aria-pressed:bg-accent`; Settings was shadcn
`Button variant="ghost" size="sm"` = `h-7 rounded-[12px] gap-1 text-[0.8rem]
hover:bg-muted` with no pressed styling. Different height, radius, gap, font
size, hover token, pressed treatment.

Shared contract: `h-11 min-w-11 rounded-md px-2.5 gap-1.5 text-sm font-medium`,
icons normalized 16px via `[&_svg]:size-4`, label `hidden md:inline`,
`transition-colors`, focus-visible ring-2 ring-ring, `aria-pressed={active}`.
Inactive: transparent, `text-muted-foreground`, `hover:bg-elevated
hover:text-foreground`. Active: `bg-accent text-accent-foreground
hover:bg-accent/90`.

`ChatLauncher` now a thin chat-specific wrapper (Open/Close chat aria-label
semantics unchanged). Settings in App.tsx renders `HeaderNavAction` directly
(aria-label Settings/Back to graph, label Settings/Graph unchanged). Unused
`Button` import removed from App.tsx.

## Verification

- Frontend tests: 176/176 pass (25 files) via `NODE_ENV=test CI=1 npm run test`
- Lint: touched files clean (`eslint` exit 0); 28 pre-existing errors in
  untouched files (DetailPanel.tsx, GraphCanvas.tsx, useRevisions*, useNotes.ts,
  useChatSessions.ts, RevisionHistoryPanel.test.tsx)
- Typecheck + production build: `npm run build` (tsc -b && vite build) pass
- Existing App-level tests for chat toggle, settings toggle, and
  Back-to-graph flow unchanged and green

## Notes

- Visual diff (equal height/padding/radius) not screen-tested live; guaranteed
  by single shared class contract asserted in HeaderNavAction.test.tsx
  (BASE_CONTRACT_CLASSES: h-11, min-w-11, rounded-md, px-2.5, gap-1.5, text-sm,
  font-medium; active adds bg-accent/text-accent-foreground).
- Safe to commit: frontend-only, no behavior/routing/auth changes.
