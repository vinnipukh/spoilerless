---
title: Unify Chat and Settings header navigation controls
slug: unify-header-chat-settings
status: in-progress
date: 2026-08-02
scope: frontend only
---

# Unify Chat and Settings header navigation controls

## Problem

Header topBar shows Chat and Settings as different design systems:

- Chat (`ChatLauncher.tsx`): raw `<button>`, `h-11` (44px), `rounded-md`,
  `gap-1.5`, `text-sm`, hover `hover:bg-elevated`, active `aria-pressed:bg-accent`.
- Settings (`App.tsx` inline): `Button variant="ghost" size="sm"` = `h-7` (28px),
  `rounded-[min(var(--radius-md),12px)]`, `gap-1`, `text-[0.8rem]`,
  hover `hover:bg-muted`, no pressed-state styling.

Mismatched height, radius, gap, font size, hover token, pressed treatment.

## Solution

Introduce one shared component `HeaderNavAction` (`components/layout/`):
icon + label + `active` + `ariaLabel` + `onClick`. Single class contract:

- `h-11 min-w-11 rounded-md px-2.5 gap-1.5 text-sm font-medium`
- icon normalized to 16px via `[&_svg]:size-4`
- inactive: `text-muted-foreground`, transparent bg, `hover:bg-elevated hover:text-foreground`
- active: `bg-accent text-accent-foreground` (+ `hover:bg-accent/90`)
- focus-visible ring-2 ring-ring, `aria-pressed` state exposure
- label `hidden md:inline` (existing responsive rule, both controls)

`ChatLauncher` becomes a thin chat-specific wrapper (keeps Open/Close chat
aria-label semantics). Settings button in `App.tsx` renders `HeaderNavAction`
directly (aria-label Back to graph/Settings, label Graph/Settings as today).

## Files

- add: `frontend/src/components/layout/HeaderNavAction.tsx`
- add: `frontend/src/components/layout/HeaderNavAction.test.tsx`
- edit: `frontend/src/components/chat/ChatLauncher.tsx` (wrapper)
- edit: `frontend/src/App.tsx` (settings control, remove unused `Button` import)

## Tests

- HeaderNavAction renders icon + label + accessible name, click fires onClick
- `aria-pressed` reflects active
- active/inactive share base size/typography contract; differ only in state classes
- existing ChatLauncher + App tests keep passing (aria-label names unchanged)

## Verify

- `NODE_ENV=test CI=1 npm run test` (frontend)
- `npm run lint`
- `npm run build` (tsc -b && vite build)
