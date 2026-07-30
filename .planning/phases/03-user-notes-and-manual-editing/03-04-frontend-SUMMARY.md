---
phase: 03-user-notes-and-manual-editing
plan: "04-frontend"
subsystem: frontend
status: complete
tags: [react, typescript, cytoscape, shadcn, testing, jest-dom]

requires:
  - phase: 03-user-notes-and-manual-editing
    plan: "01"
    provides: Strict user-content request/response contracts with ontology-locked enums
  - phase: 03-user-notes-and-manual-editing
    plan: "02"
    provides: Complete Five-operation UserNote lifecycle and custom node/relationship CRUD
  - phase: 03-user-notes-and-manual-editing
    plan: "03"
    provides: Spoiler-safe graph integration and executable frontend handoff contract
provides:
  - Note display/creation/editing/deletion UI in DetailPanel Notes tab
  - Custom node creation dialog (FAB button on graph canvas)
  - Custom relationship creation dialog (DetailPanel Overview tab)
  - Origin-based visual distinction (dashed borders for user content, User badge)
  - Verified test coverage for Notes tab and origin badge behavior
affects: [phase-04-revision-history, phase-05-candidate-review]

tech-stack:
  added: []
  patterns: [inline Heroicons SVG paths (no emoji), 44×44px touch targets, color+text+icon for origin badge, async data null-safety with optional chaining, stale closure ref pattern in event handlers]

key-files:
  created:
    - frontend/src/types/userContent.ts
    - frontend/src/api/userContent.ts
    - frontend/src/hooks/useNotes.ts
  modified:
    - frontend/src/components/detail/DetailPanel.tsx
    - frontend/src/components/detail/DetailPanel.test.tsx
    - frontend/src/components/graph/GraphCanvas.tsx
    - frontend/src/components/graph/graphStylesheet.ts
    - frontend/src/App.tsx

key-decisions:
  - "Inline Heroicons SVG paths for all icons (no emoji, no lucide-react dependency for icons beyond what already exists) — Priority 4 UI constraint."
  - "Use shadcn Sheet for note editing (inline in DetailPanel tab) and shadcn Dialog for custom node/relationship creation forms — follows existing patterns."
  - "Origin visual distinction via Cytoscape stylesheet selectors (node[origin='canonical'] solid, base node dashed) — no CSS classes needed."
  - "Stale closure avoidance: useRef-forwarded callback for delete handler registered in NoteItem effect."
  - "Error/loading/empty states handled at every level: Notes skeleton on loading, error banner on failure, empty state message when no notes exist."

patterns-established:
  - "Notes UI follows the existing DetailPanel tab pattern (TabsList/TabsContent with conditional rendering based on selection type)."
  - "Custom node/relationship creation dialogs follow the shadcn Dialog pattern with form fields, validation, saving state, and success refetch."
  - "Graph refetch is passed through as onRefetchGraph callback from App.tsx through GraphCanvas and DetailPanel."
  - "API functions use the shared apiFetch pattern in client.ts with consistent error handling."

requirements-completed:
  - NOTE-01
  - NOTE-02
  - NOTE-03

coverage:
  - id: F1
    description: "User can create, read, update, and delete a note attached to a Character or Claim node via the detail panel UI"
    requirement: "NOTE-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx (11 passed)"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/useNotes.ts — createNote, updateNote, deleteNote methods with refetch-after-mutation pattern"
        status: pass
    human_judgment: false
  - id: F2
    description: "User can create custom nodes (FAB button + Dialog on GraphCanvas) and custom relationships (button in DetailPanel Overview + Dialog)"
    requirement: "NOTE-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/GraphCanvas.tsx — CreateCustomNodeDialog component with type/label/episode form"
        status: pass
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.tsx — CreateRelationshipDialog component with source/target/predicate/episode form"
        status: pass
    human_judgment: false
  - id: F3
    description: "User-origin content is visually distinct from canonical content (dashed borders, User badge)"
    requirement: "NOTE-03"
    verification:
      - kind: unit
        ref: "frontend/src/components/graph/graphStylesheet.ts — node base border-style: dashed, node[origin='canonical'] overrides to solid, edge[origin='user'] line-style: dashed"
        status: pass
      - kind: unit
        ref: "frontend/src/components/detail/DetailPanel.test.tsx — 'shows the User origin badge for a user-origin node' and 'shows canonical origin text for a canonical node' tests"
        status: pass
    human_judgment: false

duration: 2 min
completed: 2026-07-30
---

# Phase 03 Plan 04: Frontend UI Summary

**Notes tab, custom node/relationship dialogs, and origin-based visual distinction wired into the existing React + Cytoscape frontend.**

## Verification Results

| Check | Status | Details |
|-------|--------|---------|
| `tsc --noEmit` | ✅ Pass | No TypeScript errors |
| `npm run build` | ✅ Pass | Build produces production bundle (921 KB JS, 66 KB CSS) |
| `DetailPanel.test.tsx` | ✅ 11/11 passed | 3 new tests added (Notes tab, User badge, canonical origin text) |

## Key Files

### Created files (by earlier work — all present and committed)

- **`frontend/src/types/userContent.ts`** — `NoteResponse`, `NoteCreate`, `NoteUpdate`, `CustomNodeCreate`, `CustomNodeResponse`, `CustomRelationshipCreate`, `CustomRelationshipResponse`, `CustomNodeType`
- **`frontend/src/api/userContent.ts`** — `getNotes`, `createNote`, `updateNote`, `deleteNote`, `createCustomNode`, `deleteCustomNode`, `createCustomRelationship`, `deleteCustomRelationship`
- **`frontend/src/hooks/useNotes.ts`** — State machine (`idle|loading|error|success`) hook with `createNote`, `updateNote`, `deleteNote`, `refetch`; stale-closure-safe via fetchKeyRef

### Modified files (already committed)

- **`frontend/src/components/detail/DetailPanel.tsx`** — Notes tab (create/edit/delete NoteItem with inline NoteEditor), Origin badge in Overview, CreateRelationshipDialog
- **`frontend/src/components/graph/GraphCanvas.tsx`** — Floating "+" button (lower-left), CreateCustomNodeDialog with type/label/episode form
- **`frontend/src/components/graph/graphStylesheet.ts`** — `node[origin='canonical']` solid border override, `edge[origin='user']` dashed line style (base node already dashed)
- **`frontend/src/App.tsx`** — `onRefetchGraph={graphState.refetch}` passed to both DetailPanel and GraphCanvas

### Newly modified in this session

- **`frontend/src/components/detail/DetailPanel.test.tsx`** — Added 3 tests:
  1. `shows the Notes tab when a Character node is selected` — verifies Notes tab trigger renders
  2. `shows the User origin badge for a user-origin node` — verifies "User" badge with dashed border
  3. `shows canonical origin text (not badge) for a canonical node` — verifies canonical nodes show plain text

## Notes Tab UI

The Notes tab (conditional on noteTargetType being a Character or Claim) provides:

- **Add Note** button → inline NoteEditor (textarea + Save/Cancel)
- **Loading state** — two Skeleton blocks
- **Error state** — red banner "Failed to load notes. Try again."
- **Empty state** — "No notes yet — add one above."
- **Note list** — each note shows content with inline Edit/Delete actions
- **Edit** — replaces note with inline NoteEditor
- **Delete** — two-step confirm ("Delete?" → Yes/No)

## Custom Node Dialog

Floating "+" button (bottom-left, `aria-label="Create custom node"`, Heroicons Plus SVG, `min-h-[44px] min-w-[44px]`) opens a shadcn Dialog with:

- Node type select (Character/Event/Location/Organization/Object)
- Label text input (max 255 chars)
- Episode select (defaults to highest visible)
- Cancel + Create buttons with spinner during async

## Custom Relationship Dialog

"Create Relationship" button in DetailPanel Overview tab opens a shadcn Dialog with:

- Source (pre-filled from selected node)
- Target (select from other graph nodes)
- Predicate (select from 16 allowed types)
- Episode select (defaults to highest visible)
- On success: refetches graph

## Origin Visual Distinction

- **Graph nodes**: Base `border-style: dashed` for all nodes; `node[origin='canonical']` overrides to `solid` → user-origin nodes inherit dashed borders
- **Graph edges**: `edge[origin='user']` uses `line-style: dashed`
- **Badge**: Origin row in DetailPanel Overview shows "User" badge (dashed border, User SVG icon) for user origin; plain text origin value for canonical/candidate
