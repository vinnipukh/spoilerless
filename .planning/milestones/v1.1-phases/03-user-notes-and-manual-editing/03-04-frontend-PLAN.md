---
phase: 03-user-notes-and-manual-editing
plan: "01-frontend"
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/types/graph.ts
  - frontend/src/api/client.ts
  - frontend/src/api/series.ts
  - frontend/src/hooks/useNotes.ts
  - frontend/src/components/detail/DetailPanel.tsx
  - frontend/src/components/detail/DetailPanel.test.tsx
  - frontend/src/components/graph/graphStylesheet.ts
  - frontend/src/components/graph/GraphCanvas.tsx
  - frontend/src/App.tsx
autonomous: false
requirements:
  - NOTE-01
  - NOTE-02
  - NOTE-03
must_haves:
  truths:
    - "NOTE-01: User can create, read, update, and delete a note attached to a Character or Claim node via the detail panel UI"
    - "NOTE-02: User can create and edit custom nodes and relationships from the graph interface"
    - "NOTE-03: User-origin content is visually distinct from canonical/candidate content (dashed borders, 'user' badge)"
  prohibitions:
    - "Do not modify backend files — Phase 3 backend is already complete and verified"
    - "Do not break existing graph rendering, episode selection, or watch-progress flows"
    - "Do not add emoji icons — use Heroicons SVGs from the ui-ux-review skill's references"
---

<objective>
Wire Phase 3 frontend UI: notes panel, custom node/relationship creation, and origin-based visual distinction. The backend is already complete — this plan adds only frontend code.

Three work streams in Wave 1:
1. **Notes** — Add a "Notes" tab to DetailPanel with create/read/update/delete inline UI
2. **Custom content** — Add custom node creation controls and custom relationship creation from the graph
3. **Visual distinction** — Update graphStylesheet and GraphCanvas to render user-origin content with dashed borders and a "user" badge

This plan is VERIFY-INTERACTIVE: each task must be verified by the user before the next task starts.
</objective>

### UI/UX Constraints (apply to ALL tasks below)
- **No emoji icons** (Priority 4): All visual indicators use Heroicons SVG paths. Reference: `references/svg-icon-replacements.md` for copy-pasteable paths. Check mark → Heroicons Check SVG, X → Heroicons XMark SVG, Plus → Heroicons Plus SVG, Pencil → Heroicons PencilSquare SVG, Delete → Heroicons Trash SVG, Info → Heroicons InformationCircle SVG.
- **Touch targets ≥44×44px** (Priority 2): All interactive elements (buttons, dismiss targets, action links) must meet minimum touch size. Add `min-h-[44px] min-w-[44px]` or use DaisyUI `btn` class for custom elements. 8px minimum gap between targets.
- **Color not sole indicator** (Priority 1): Never convey information by color alone — pair with icon or text label. Verify text is readable without color cues.
- **Reduced motion** (Priority 7): If animations are added, include `@media (prefers-reduced-motion: reduce)` fallback. Prefer appear/disappear (no animation) as the simplest approach.
- **Accessibility** (Priority 1): Icon-only buttons must have `aria-label`. Keyboard tab order matches visual order. Use `role="alert"` for notification banners.
- **React 19 CJS act workaround** (from `react19-testing-workaround.md`): All new component tests must use `createRoot` + `flushSync` if they interact with React.act. Use `findByText`/`findByRole` (async) for Sheet content assertions — forced synchronous `getByText` returns empty `<div/>` under jsdom.
- **Stale closure avoidance** (from `react-patterns`): Event handlers registered in `useEffect` that reference values changing independently must use the ref-forwarded callback pattern.
- **Async data null-safety**: Use optional chaining (`data?.field`) for all render-time accesses to asynchronously-loaded data objects. The async gap between navigation and data fetch completion can leave the object stale or undefined.
- **Error state**: Empty states must show helpful message + action. Loading states show skeleton. Error states show message with retry option.
- **No new dangerouslySetInnerHTML**: Zero tolerance.

### Architecture Decisions

**Modal approach:** Use shadcn Sheet (already in the project) for note editing — inline in the DetailPanel tab, not a separate page. Custom node creation uses a small shadcn Dialog (already imported).

**API pattern:** Follow existing `apiFetch` pattern in `client.ts` — add note/custom-node/custom-relationship API functions in a new `api/userContent.ts` file.

**Hook pattern:** Follow existing `useGraph` pattern — `useNotes` hook fetches notes list and provides create/update/delete methods.

**Visual distinction pattern:** Existing `graphStylesheet.ts` has `origin: 'canonical'` as solid borders. Add dashed border for `origin === 'user'` via the function-style stylesheet values. No need for new CSS classes — Cytoscape stylesheet handles this natively.

---

### Wave 1 — Studies, Notes, Custom Nodes

**Three parallel tasks** — Notes UI, Custom Node/Relationship UI, Visual Distinction. Each can proceed independently since they modify different files.

#### Task 1: Notes Tab in DetailPanel

**Files to create/modify:**
- **NEW** `frontend/src/types/userContent.ts` — TypeScript types matching backend `NoteResponse`, `NoteCreate`, `NoteUpdate`
- **NEW** `frontend/src/api/userContent.ts` — API functions for notes CRUD
- **NEW** `frontend/src/hooks/useNotes.ts` — Hook for fetching/creating/updating/deleting notes
- **MODIFY** `frontend/src/components/detail/DetailPanel.tsx` — Add "Notes" tab to the Tabs component
- **MODIFY** `frontend/src/components/detail/DetailPanel.test.tsx` — Test the new Notes tab

**Detailed steps:**

1. **Create `frontend/src/types/userContent.ts`:**
```ts
// Mirrors backend/app/domain/user_content.py field-for-field
export type NoteResponse = {
  id: string
  series_id: string
  target_type: 'Character' | 'Claim'
  target_id: string
  content: string
  origin: string
  visible_from_order: number
  created_at: string
  updated_at: string
}

export type NoteCreate = {
  target_type: 'Character' | 'Claim'
  target_id: string
  content: string
}

export type NoteUpdate = {
  content: string
}
```

2. **Create `frontend/src/api/userContent.ts`:**
- `getNotes(seriesId, visibleUntilOrder, targetType?, targetId?)` → `GET /api/series/{seriesId}/notes?visible_until_order=N&target_type=T&target_id=ID`
- `createNote(seriesId, body: NoteCreate)` → `POST /api/series/{seriesId}/notes`
- `updateNote(seriesId, noteId, body: NoteUpdate)` → `PATCH /api/series/{seriesId}/notes/{noteId}`
- `deleteNote(seriesId, noteId)` → `DELETE /api/series/{seriesId}/notes/{noteId}`

3. **Create `frontend/src/hooks/useNotes.ts`:**
- Accept `seriesId` and `visibleUntilOrder`, `targetType`, `targetId`
- Fetch notes on mount + refetch on dependency change
- Expose `createNote`, `updateNote`, `deleteNote` methods that call the API then refetch
- Follow the same state machine pattern as `useGraph` (`idle | loading | error | success`)

4. **Modify `frontend/src/components/detail/DetailPanel.tsx`:**
- Add `selectedNoteIds: string[]` to graph data (notes for the selected node)
- Add "Notes" tab to TabsList:
  ```tsx
  <TabsTrigger value="notes">Notes</TabsTrigger>
  ```
- Add `TabsContent` for "notes" with:
  - List of existing notes (content text + edit/delete buttons)
  - "Add Note" form at the top (inline textarea + submit button)
  - Loading skeleton, empty state ("No notes yet — add one above")
  - Inline edit (clicking edit replaces the note text with an inline textarea + save/cancel)
  - Delete confirmation (simple "Delete?" confirm button, then execute)

5. **Wire notes into selection:**
- When a node is selected, filter notes by `target_id === selected.id`
- Show notes only for the currently selected node or edge's claim

**Verification:** `npm run test -- --run src/components/detail/DetailPanel.test.tsx`

---

#### Task 2: Custom Node/Relationship UI

**Files to create/modify:**
- **MODIFY** `frontend/src/types/userContent.ts` — Add CustomNodeResponse, CustomRelationshipResponse types
- **MODIFY** `frontend/src/api/userContent.ts` — Add custom node/relationship API functions
- **MODIFY** `frontend/src/components/graph/GraphCanvas.tsx` — Add context menu or floating action for creating custom nodes
- **MODIFY** `frontend/src/App.tsx` — Wire custom node/relationship state and refetch after creation

**Detailed steps:**

1. **Add types to `frontend/src/types/userContent.ts`:**
```ts
export type CustomNodeType = 'Character' | 'Event' | 'Location' | 'Organization' | 'Object'

export type CustomNodeCreate = {
  node_type: CustomNodeType
  label: string
  episode_id: string
}

export type CustomNodeResponse = {
  id: string
  series_id: string
  label: string
  node_type: string
  episode_id: string
  visible_from_order: number
  origin: string
  created_at: string
  updated_at: string
}

export type CustomRelationshipCreate = {
  source_id: string
  target_id: string
  predicate: string
  episode_id: string
}

export type CustomRelationshipUpdate = {
  predicate: string
}

export type CustomRelationshipResponse = {
  id: string
  series_id: string
  source: string
  target: string
  type: string
  visible_from_order: number
  origin: string
  episode_id: string
  created_at: string
  updated_at: string
}
```

2. **Add API functions to `frontend/src/api/userContent.ts`:**
- `createCustomNode(seriesId, body: CustomNodeCreate)` → `POST /api/series/{seriesId}/custom-nodes`
- `deleteCustomNode(seriesId, nodeId)` → `DELETE /api/series/{seriesId}/custom-nodes/{nodeId}`
- `createCustomRelationship(seriesId, body: CustomRelationshipCreate)` → `POST /api/series/{seriesId}/custom-relationships`
- `deleteCustomRelationship(seriesId, relId)` → `DELETE /api/series/{seriesId}/custom-relationships/{relId}`

3. **Add "Create Custom Node" action to GraphCanvas:**
- Use a floating (+) button at bottom-left of the graph (above GraphLegend)
- Clicking opens a small shadcn Dialog with:
  - Node type select (Character/Event/Location/Organization/Object)
  - Label text input
  - Episode select (from current series episodes, default: current highest visible)
  - Cancel + Create buttons
- On successful creation: refetch the graph

4. **Add "Create Relationship" action:**
- In the DetailPanel for a node, add a "Create Relationship" button
- Opens a shadcn Dialog with:
  - Source (pre-filled to selected node)
  - Target (searchable select of other nodes)
  - Predicate (select from allowed types)
  - Episode (default: current boundary)
- On successful creation: refetch the graph

5. **Wire refetch in App.tsx:**
- Pass `graphState.refetch` to DetailPanel and GraphCanvas
- On successful custom node/relationship creation, call `graphState.refetch()`

**UI/UX rules (apply here):**
- The "+" button for custom nodes: `aria-label="Create custom node"`, Heroicons Plus SVG, `min-h-[44px] min-w-[44px]`
- Dialog uses shadcn Dialog component (already imported)
- Form fields have visible labels, not placeholder-only
- Submit button shows spinner during async operation

**Verification:** Manual — create a custom node and a custom relationship, verify they appear in the graph.

---

#### Task 3: Visual Distinction for User Content

**Files to modify:**
- **MODIFY** `frontend/src/components/graph/graphStylesheet.ts` — Add user-origin styling
- **MODIFY** `frontend/src/components/detail/DetailPanel.tsx` — Show origin badge on user content

**Detailed steps:**

1. **Modify `frontend/src/components/graph/graphStylesheet.ts`:**
- The `buildGraphStylesheet` function has a section for `origin` at line ~44 with a comment `// origin (no automatic/user data exists yet — Phases 3/5 scope);`
- Add a function-style stylesheet entry that detects `origin === 'user'`:
```ts
// User-origin nodes: dashed border, subtle background tint
{
  selector: 'node[origin = "user"]',
  style: {
    'border-style': 'dashed',
    'border-width': 2,
    'background-opacity': 0.85,
  },
},
{
  selector: 'edge[origin = "user"]',
  style: {
    'line-style': 'dashed',
  },
},
```

- Add the `line-style` property to the user origin edges

2. **Add origin badge to DetailPanel:**
- In the Overview tab, after "Node Type" / "Name", add "Origin" row
- If origin is "user", show a small "User" badge (dashed border, subtle background)
- Use styled `<span>` with `border-dashed border-2 border-primary/50 rounded px-1.5 py-0.5 text-xs font-medium`

**UI/UX rules (apply here):**
- "User" badge: color + text + icon (not color alone)
- Badge uses Heroicons User SVG icon + text

**Verification:** Manual — create a custom node and verify it appears in the graph with dashed borders.

---

#### Task 4: Update Existing Tests

**Files to modify:**
- **MODIFY** `frontend/src/components/detail/DetailPanel.test.tsx` — Add Notes tab test assertions

**Tests to write:**
- Notes tab renders when a node is selected
- Notes tab shows empty state when no notes exist
- Note list shows note content for existing notes
- User-origin badge renders with correct styling

**Verification:**
```bash
npm run test -- --run src/components/detail/DetailPanel.test.tsx
npm run build
```

---

### Verification Sequence (run after ALL tasks complete)

1. **Build check:**
```bash
npm run build
```

2. **Existing tests:**
```bash
npm run test -- --run
```

3. **Demo UAT:** User tests:
- Select a Character node → Notes tab visible → Create note → Note appears in list
- Edit note → Content updates inline
- Delete note → Note removed from list
- Click "+" on graph → Custom node dialog → Create → New node appears with dashed border
- Select a node → "Create Relationship" → Dialog → Create → New edge appears with dashed line
- Verify user content has "User" badge, canonical content does not

4. **UI audit:**
- All interactive elements ≥44×44px (check with devtools)
- No emoji in toasts/buttons/labels (grep for emoji patterns in modified files)
- Reduced motion: `prefers-reduced-motion: reduce` doesn't break layout
- Error states: network failure shows message, not crash
- Edge cases: empty notes list, very long note content, rapid create/delete
