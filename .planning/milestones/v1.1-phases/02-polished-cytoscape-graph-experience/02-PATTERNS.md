# Phase 2: Polished Cytoscape Graph Experience - Pattern Map

**Mapped:** 2026-07-29
**Files analyzed:** 20 (new) + 2 (modified)
**Analogs found:** 20 / 20 (all via shared UI-primitive conventions and backend domain shapes — no prior frontend app code exists to copy business-logic patterns from; this is a greenfield product layer over an already-themed shadcn scaffold)

## Context

This is a brownfield repo where the **frontend product code does not exist yet** — only the Vite starter (`App.tsx`) and a themed shadcn `ui/` primitive set. There are no prior controllers/services/hooks/api-clients in this codebase to copy CRUD/request-response patterns from. Consequently every "analog" below is one of:
1. An **installed shadcn primitive** (`components/ui/*`) — the conventions (import style, `cn()` usage, `data-slot` attributes, `React.ComponentProps<typeof Primitive>` typing) these new components must follow.
2. A **backend domain/Pydantic model** (`backend/app/domain/*.py`) — the field-for-field shape the new TypeScript types must mirror.
3. **02-UI-SPEC.md** / **02-RESEARCH.md** code examples — locked copy, color tokens, and verified wire-shapes/patterns (already vetted, safe to copy directly since no closer in-repo analog exists).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `frontend/src/types/graph.ts` | model (type-only) | transform | `backend/app/domain/graph.py` | exact (mirror) |
| `frontend/src/types/series.ts` | model (type-only) | transform | `backend/app/domain/series.py` | exact (mirror) |
| `frontend/src/types/cytoscape-cose-bilkent.d.ts` | config (ambient decl) | — | RESEARCH.md `## Standard Stack` note | exact (locked pattern) |
| `frontend/src/api/client.ts` (shared fetch helper + `ApiError`) | service | request-response | `backend/app/core/errors.py` (`{detail:{code,message}}` shape) | role-match |
| `frontend/src/api/series.ts` (`getSeries`, `getEpisodes`) | service | request-response | RESEARCH.md Pattern 1 (`api/graph.ts` example) | exact |
| `frontend/src/api/graph.ts` (`getGraph`) | service | request-response | RESEARCH.md Pattern 1 (`api/graph.ts` example) | exact |
| `frontend/src/hooks/useWatchProgress.ts` | hook (state+storage) | event-driven | none in-repo — new pattern; RESEARCH.md Pitfall 5 + Architecture diagram | no analog (see below) |
| `frontend/src/hooks/useSeries.ts` | hook (data fetch) | request-response | none in-repo — follow `api/series.ts` + standard `useEffect`+`useState` fetch hook shape | no analog (see below) |
| `frontend/src/hooks/useEpisodes.ts` | hook (data fetch) | request-response | same as `useSeries.ts` | no analog |
| `frontend/src/hooks/useGraph.ts` | hook (data fetch) | request-response | same as `useSeries.ts` | no analog |
| `frontend/src/components/layout/AppShell.tsx` | component (layout) | request-response | none — new; uses `Card`/`Separator` primitives | role-match (primitives) |
| `frontend/src/components/episode/SeriesSelect.tsx` | component | request-response | `frontend/src/components/ui/select.tsx` | exact |
| `frontend/src/components/episode/EpisodeSelector.tsx` | component | request-response | `frontend/src/components/ui/select.tsx` | exact |
| `frontend/src/components/episode/ConfirmAdvanceModal.tsx` | component | event-driven | `frontend/src/components/ui/dialog.tsx` | exact |
| `frontend/src/components/graph/GraphCanvas.tsx` | component (canvas wrapper) | streaming (canvas render) | RESEARCH.md Pattern 2 + Pattern 3 (Cytoscape mapping/highlight) | exact (only available pattern) |
| `frontend/src/components/graph/graphStylesheet.ts` | config | transform | 02-UI-SPEC.md `## Color` node-type/origin tables | exact (locked contract) |
| `frontend/src/components/graph/graphElements.ts` (mapping fn) | utility | transform | RESEARCH.md Pattern 2 code example | exact |
| `frontend/src/components/detail/DetailPanel.tsx` (tabbed Sheet, D-07) | component | request-response | `frontend/src/components/ui/sheet.tsx` + `frontend/src/components/ui/tabs.tsx` | exact |
| `frontend/src/components/detail/StructuralEdgeCard.tsx` (D-06) | component | request-response | `frontend/src/components/ui/sheet.tsx` (Header/Content only, no Tabs) | role-match |
| `frontend/src/components/graph/GraphEmptyState.tsx` / error/loading states | component | request-response | `frontend/src/components/ui/alert.tsx`, `frontend/src/components/ui/skeleton.tsx` | exact |
| `frontend/src/App.tsx` (rewritten) | component (root) | request-response | existing `frontend/src/App.tsx` (Vite starter, to be fully replaced) | exact (structure to remove) |
| `frontend/package.json` (modified — add deps) | config | — | current `frontend/package.json` | exact |
| `frontend/vite.config.ts` / `vitest.config.ts` (Wave 0 test infra) | config | — | none in-repo; RESEARCH.md Wave 0 Gaps list | no analog |

## Pattern Assignments

### `frontend/src/types/graph.ts` (model, transform)

**Analog:** `backend/app/domain/graph.py` (read in full above)

Mirror every field name and optionality exactly, including the verified wire quirks:
- `origin` is the literal string `"canonical"` in this project's data — **never** `"curated"` (RESEARCH.md Pitfall 1). Type as `origin: string` (or a union `'canonical' | 'automatic' | 'user'` for forward-compat), but branch UI logic on `'canonical'`.
- `GraphEdge.claim_id: string | null` — null/absent distinguishes structural (`PART_OF`/`PRECEDES`) from claim-backed edges (D-05/D-06/D-07 branch point).
- `GraphNode.type` includes `"Episode"` and `"Series"` in addition to `Character`/`Event`/`Location`/`Organization` — not just the narrative types (RESEARCH.md Pitfall 2). Must be represented in the type union/string and in `graphStylesheet.ts`.

```typescript
// backend/app/domain/graph.py:10-27 — field-for-field source of truth
export type GraphNode = {
  id: string
  type: string            // includes "Series" | "Episode" | "Character" | "Event" | "Location" (+ "Organization" per UI-SPEC)
  label: string
  visible_from_order: number
  origin: string           // literal "canonical" in this project's data
  episode_id: string | null
}

export type GraphEdge = {
  id: string
  source: string
  target: string
  type: string             // e.g. "PART_OF" | "PRECEDES" | "WORKS_WITH" | "FAMILY_OF" | "OCCURRED_IN"
  visible_from_order: number
  origin: string
  claim_id: string | null  // present only on claim-backed edges
}

export type GraphClaim = {
  id: string
  label: string
  subject_id: string
  predicate: string
  object_id: string
  claim_type: string
  status: string
  confidence_level: string
  relationship_effect: number
  visible_from_order: number
  valid_from_order: number | null
  valid_until_order: number | null
  source_id: string
  evidence_ids: string[]
  origin: string
}

export type GraphSource = {
  id: string
  label: string
  episode_id: string
  source_type: string
  locator: string
  retrieved_at: string
  visible_from_order: number
  origin: string
}

export type GraphEvidence = {
  id: string
  label: string
  episode_id: string
  source_id: string
  text: string
  locator: string
  content_hash: string
  visible_from_order: number
  origin: string
}

export type GraphResponse = {
  series: SeriesResponse
  visible_until_order: number
  nodes: GraphNode[]
  edges: GraphEdge[]
  claims: GraphClaim[]
  sources: GraphSource[]
  evidence: GraphEvidence[]
}
```

---

### `frontend/src/types/series.ts` (model, transform)

**Analog:** `backend/app/domain/series.py` (read in full above)

```typescript
// backend/app/domain/series.py:4-18
export type SeriesResponse = {
  id: string
  title: string
  slug: string
}

export type EpisodeResponse = {
  id: string
  series_id: string
  season_number: number
  episode_number: number
  episode_order: number
  code: string
  title: string
  visible_from_order: number
}
```

---

### `frontend/src/types/cytoscape-cose-bilkent.d.ts` (config, ambient declaration)

**Analog:** RESEARCH.md `## Standard Stack` (no upstream types exist — `@types/cytoscape-cose-bilkent` does not exist on the registry, confirmed `SLOP`/`does-not-exist`).

```typescript
// No .d.ts to copy from in-repo (no other ambient module declarations exist yet).
// Minimal shape needed — a default export usable with cytoscape.use():
declare module 'cytoscape-cose-bilkent' {
  import type { Ext } from 'cytoscape'
  const ext: Ext
  export default ext
}
```

---

### `frontend/src/api/client.ts` + `frontend/src/api/series.ts` + `frontend/src/api/graph.ts` (service, request-response)

**Analog:** RESEARCH.md Pattern 1 (`api/graph.ts` example, already adapted to this project's verified error shape) + `backend/app/core/errors.py` (error envelope source of truth).

**Error shape to surface** (verified `backend/app/core/errors.py:24-27` — every error response is `{"detail": {"code": ..., "message": ...}}`, for both the 503 handler here and the 404/422 handlers in `backend/app/api/*.py`):

```typescript
// api/client.ts
export type ApiErrorDetail = { code: string, message: string }

export class ApiError extends Error {
  code: string
  constructor(detail: ApiErrorDetail) {
    super(detail.message)
    this.code = detail.code
  }
}

export async function apiFetch<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(body?.detail ?? { code: 'unknown_error', message: 'Request failed.' })
  }
  return res.json() as Promise<T>
}
```

```typescript
// api/graph.ts — copy directly from RESEARCH.md Pattern 1, using shared apiFetch
import { apiFetch } from './client'
import type { GraphResponse } from '../types/graph'

export function getGraph(seriesId: string, visibleUntilOrder: number): Promise<GraphResponse> {
  return apiFetch(`/api/series/${seriesId}/graph?visible_until_order=${visibleUntilOrder}`)
}
```

```typescript
// api/series.ts — same shape, two endpoints
import { apiFetch } from './client'
import type { SeriesResponse, EpisodeResponse } from '../types/series'

export function getSeries(): Promise<SeriesResponse[]> {
  return apiFetch('/api/series')
}

export function getEpisodes(seriesId: string): Promise<EpisodeResponse[]> {
  return apiFetch(`/api/series/${seriesId}/episodes`)
}
```

Error codes to handle generically (not just 404/422): `series_not_found` (404), `invalid_visible_until_order` (422), `database_unavailable` / `database_error` (503, from `backend/app/core/errors.py:18-19`).

---

### `frontend/src/hooks/useSeries.ts`, `useEpisodes.ts`, `useGraph.ts` (hook, request-response)

**No in-repo analog** — this is the first data-fetching hook layer in the project. Use the standard `useState`+`useEffect` fetch-hook shape, matching the `apiFetch`/`ApiError` pattern above for error surfacing, e.g.:

```typescript
// hooks/useGraph.ts — pattern to establish (no existing hook to copy)
import { useEffect, useState } from 'react'
import { getGraph } from '../api/graph'
import type { GraphResponse } from '../types/graph'
import { ApiError } from '../api/client'

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'error', error: ApiError }
  | { status: 'success', data: GraphResponse }

export function useGraph(seriesId: string | null, visibleUntilOrder: number | null) {
  const [state, setState] = useState<State>({ status: 'idle' })

  useEffect(() => {
    if (!seriesId || visibleUntilOrder == null) {
      setState({ status: 'idle' })
      return
    }
    let cancelled = false
    setState({ status: 'loading' })
    getGraph(seriesId, visibleUntilOrder)
      .then((data) => { if (!cancelled) setState({ status: 'success', data }) })
      .catch((error) => { if (!cancelled) setState({ status: 'error', error }) })
    return () => { cancelled = true }
  }, [seriesId, visibleUntilOrder])

  return state
}
```

`useSeries.ts` / `useEpisodes.ts` follow the identical `status`-union shape against `getSeries()` / `getEpisodes(seriesId)`.

---

### `frontend/src/hooks/useWatchProgress.ts` (hook, event-driven, sessionStorage)

**No in-repo analog.** Must satisfy D-02/D-03/RESEARCH Pitfall 5: hydration from `sessionStorage` on mount must NOT retrigger the confirmation modal; only live user-initiated changes do. Wrap `JSON.parse` in try/catch (Security Domain V5 requirement, RESEARCH.md line 518).

```typescript
// hooks/useWatchProgress.ts — pattern to establish
const STORAGE_KEY = 'hdgraf.watchProgress'

type Stored = { seriesId: string, visibleUntilOrder: number }

function readStored(): Stored | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (typeof parsed?.seriesId !== 'string' || !Number.isInteger(parsed?.visibleUntilOrder) || parsed.visibleUntilOrder < 1) {
      return null // corrupted/tampered — fall back to D-01 empty state
    }
    return parsed
  } catch {
    return null
  }
}

// Hydrate directly into state (no setter that opens the modal); only the
// user-facing "requestChange" handler below should trigger ConfirmAdvanceModal.
```

---

### `frontend/src/components/episode/SeriesSelect.tsx`, `EpisodeSelector.tsx` (component, request-response)

**Analog:** `frontend/src/components/ui/select.tsx` (read in full above — lines 1-191).

Copy the composition pattern used by every shadcn consumer of `Select`: `<Select><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem>...</SelectItem></SelectContent></Select>`. Use `data-slot` conventions already baked into the primitive; do not modify `ui/select.tsx` itself.

**Imports pattern** (`select.tsx:1-5`):
```typescript
import * as React from "react"
import { Select as SelectPrimitive } from "radix-ui"
import { cn } from "@/lib/utils"
import { ChevronDownIcon, CheckIcon, ChevronUpIcon } from "lucide-react"
```

Note per CONTEXT.md discretion: keep `SeriesSelect` a genuine interactive control even with only one option (Dexter) today.

---

### `frontend/src/components/episode/ConfirmAdvanceModal.tsx` (component, event-driven)

**Analog:** `frontend/src/components/ui/dialog.tsx` (read in full above — lines 1-169).

**Core pattern** (`dialog.tsx:10-33`, composition): `<Dialog open={...} onOpenChange={...}><DialogContent><DialogHeader><DialogTitle>...</DialogTitle><DialogDescription>...</DialogDescription></DialogHeader><DialogFooter>...</DialogFooter></DialogContent></Dialog>`.

**Locked copy** (02-UI-SPEC.md `## Copywriting Contract`, forward-advance case):
```
Title: "Unlock S01E0X?"
Body: "You're about to see new characters, events, and relationships from S01E0X. This can't be undone. Continue?"
Cancel button: "Cancel"
Confirm button: "Yes, unlock episode"
```
Per CONTEXT.md discretion, add a parallel backward-move copy variant (same warning-tinted visual treatment, same Cancel/confirm button pattern) — do not silently reuse forward-only copy for backward moves, and document the addition alongside 02-UI-SPEC.md's table rather than editing it in place without a note.

**Color:** use `--warning` (`#F59E0B`) per 02-UI-SPEC.md `## Color` — explicitly NOT `--destructive` (this is an intentional, reversible-in-spirit action, not a delete).

---

### `frontend/src/components/graph/GraphCanvas.tsx` (component, canvas render / streaming)

**Analog:** RESEARCH.md Pattern 2 (element mapping + registration) and Pattern 3 (selection highlight/fade) — both already adapted to this project's verified data (no closer in-repo analog exists; `react-cytoscapejs` is installed but unused so far).

**Core pattern** (RESEARCH.md lines 258-322, copy directly):
```typescript
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import CytoscapeComponent from 'react-cytoscapejs'

cytoscape.use(coseBilkent)

// elements mapping: nodeType from node.type (incl. "Episode"/"Series"), origin literal "canonical",
// claimId: edge.claim_id (null => structural edge => D-06 minimal card; non-null => D-07 tabbed Sheet)

<CytoscapeComponent
  elements={elements}
  layout={{ name: 'cose-bilkent', nodeDimensionsIncludeLabels: true, fit: true, padding: 24 }}
  stylesheet={graphStylesheet}
  cy={(cy) => { cyRef.current = cy }}
/>
```

**Selection highlight/fade** (RESEARCH.md lines 301-321) — wire `cy.on('tap', 'node', ...)` / `'edge'` / background-tap-to-clear handlers exactly as shown, satisfying "nothing on canvas is inert to clicks" (D-05).

**Fallback note:** `cose` (built-in) is an explicit fallback only on an actual build/runtime failure with `cose-bilkent` (D-04) — do not build both layout paths up front.

---

### `frontend/src/components/graph/graphStylesheet.ts` (config, transform)

**Analog:** 02-UI-SPEC.md `## Color` node-type/origin tables (lines 90-106) — this is the locked visual contract, copy directly, extended per RESEARCH.md Pitfall 2 for `Episode`/`Series`.

```
Shape by nodeType: Character=circle, Event=rounded-rectangle, Location=square/rounded-square,
                    Organization=diamond, UserNote=dashed-note (out of Phase-2 scope),
                    Episode=hexagon/tag (ADD — not in UI-SPEC table, coding-agent spec §9.1 suggestion),
                    Series=distinct shape e.g. star/large-rounded-rect (ADD — no suggestion anywhere;
                    planner/executor discretion per RESEARCH.md Open Question 1)
Border by origin:  canonical (wire value, NOT "curated")=solid border; automatic=standard+glyph (no
                    Phase-2 seed data); user=dashed (Phase-2 out of scope)
Idle fill: --muted (#131936) all types; selected fill lightens toward --card + --accent (#7C3AED) ring
Edge: --border idle / --secondary (#6366F1) hover-or-selected
```
Document the two added shapes (`Episode`, `Series`) as a Claude's-discretion addition to 02-UI-SPEC.md's table, per RESEARCH.md Open Question 1 recommendation — do not silently invent without a note.

---

### `frontend/src/components/detail/DetailPanel.tsx` (component, request-response, D-07)

**Analog:** `frontend/src/components/ui/sheet.tsx` (lines 1-146) composed with `frontend/src/components/ui/tabs.tsx`.

**Core pattern:** `<Sheet open={...}><SheetContent><SheetHeader><SheetTitle>{label}</SheetTitle></SheetHeader><Tabs defaultValue="overview"><TabsList>...Overview/Claims/Evidence...</TabsList><TabsContent value="overview">...</TabsContent>...</Tabs></SheetContent></Sheet>`.

**Locked copy** (02-UI-SPEC.md `## Copywriting Contract`):
```
No-selection placeholder: "Select a node to see details."
Tabs: "Overview" / "Claims" / "Evidence"
Evidence locator line: "Source: {source label} — {locator}" (e.g. "Source: S01E01 script — 00:12:34")
```
Partial-state coverage (02-UI-SPEC.md `## UI Considerations`, `partial` row): a node with zero linked claims/evidence must render a per-tab empty sub-state (e.g. "No claims recorded for this node yet"), not a blank panel.

Applies to both node selection and claim-backed edge selection (`edge.claim_id != null`) per D-07.

---

### `frontend/src/components/detail/StructuralEdgeCard.tsx` (component, request-response, D-06)

**Analog:** `frontend/src/components/ui/sheet.tsx` `SheetHeader`/`SheetContent` only (no `Tabs`) — a deliberately simpler, tab-less second layout.

Content: relationship type (`edge.type`, e.g. `PART_OF`/`PRECEDES`) + labels of the two connected nodes. Triggered when `edge.claim_id == null` (structural edge, D-05/D-06 branch).

---

### `frontend/src/components/graph/GraphEmptyState.tsx` / loading / error states (component)

**Analog:** `frontend/src/components/ui/alert.tsx` (error), `frontend/src/components/ui/skeleton.tsx` (loading) — both already installed; read their exports for `cn()`/`data-slot` conventions consistent with `sheet.tsx`/`dialog.tsx` above.

**Locked copy** (02-UI-SPEC.md `## Copywriting Contract`):
```
Empty heading: "Nothing revealed yet"
Empty body: "Advance your watch progress to unlock the story."
Error: "Couldn't load the graph. Check the backend connection and retry." + "Retry" button re-issuing the last /api/graph request
```

---

### `frontend/src/App.tsx` (rewritten, component root, request-response)

**Analog:** current `frontend/src/App.tsx` (Vite starter — read in full above, lines 1-123) — this is the file being fully replaced, not incrementally edited (per CONTEXT.md `<code_context>` Integration Points). Remove all starter markup/assets (`hero.png`, `react.svg`, `vite.svg`, `App.css` starter rules); compose `AppShell` + selectors + `GraphCanvas` + `DetailPanel`/`StructuralEdgeCard` per the RESEARCH.md project-structure diagram. Leave `frontend/src/main.tsx` wiring (explicit `.tsx` import extension) untouched.

---

### `frontend/package.json` (modified, config)

**Analog:** current `frontend/package.json` (read above). Add runtime dep `cytoscape-cose-bilkent`; add devDeps `@types/react-cytoscapejs`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, `jsdom`; add a `"test": "vitest"` script. Per RESEARCH.md Package Legitimacy Audit, `vitest`/`@testing-library/jest-dom`/`jsdom` are flagged `SUS` (heuristic false-positive, "too-new" on well-established packages) — planner must still insert `checkpoint:human-verify` before each install.

---

## Shared Patterns

### shadcn primitive composition convention
**Source:** `frontend/src/components/ui/sheet.tsx`, `dialog.tsx`, `select.tsx` (all read in full)
**Apply to:** every new component in `components/{episode,graph,detail,layout}/`
```typescript
import * as React from "react"
import { <Primitive> as <Name>Primitive } from "radix-ui"
import { cn } from "@/lib/utils"
```
All new leaf UI wrappers should use the `@/*` path alias (not relative `../../`), `data-slot="..."` attributes for styling hooks, and `cn(...)` for class merging — matching every installed `ui/*` file. New non-primitive components (`GraphCanvas`, `DetailPanel`, etc.) may use relative imports for sibling `api/`/`hooks/`/`types/` modules per the RESEARCH.md project-structure layout, but should still use `@/lib/utils` for `cn()`.

### API error handling
**Source:** `backend/app/core/errors.py:16-27` (verified `{detail:{code,message}}` shape, all three consumed error paths: 404 `series_not_found`, 422 `invalid_visible_until_order`, 503 `database_unavailable`/`database_error`)
**Apply to:** `api/client.ts`, all hooks, `GraphEmptyState`/error UI
```typescript
export type ApiErrorDetail = { code: string, message: string }
export class ApiError extends Error {
  code: string
  constructor(detail: ApiErrorDetail) { super(detail.message); this.code = detail.code }
}
```

### sessionStorage hydration guard (D-02, Pitfall 5)
**Source:** RESEARCH.md `## Common Pitfalls` Pitfall 5 (no in-repo precedent — first usage in project)
**Apply to:** `hooks/useWatchProgress.ts` only, but the try/catch-with-safe-fallback discipline should be the template for any future client-persisted state
```typescript
try {
  const parsed = JSON.parse(raw)
  // validate shape before trusting it
} catch {
  // fall back to D-01 empty state — never crash on mount
}
```

### Cytoscape origin/type branching
**Source:** RESEARCH.md Pitfall 1 + Pitfall 2 (verified live against running backend, not assumed)
**Apply to:** `graphElements.ts`, `graphStylesheet.ts`, `DetailPanel.tsx`, `StructuralEdgeCard.tsx`
```
Branch on literal 'canonical' (not 'curated'); handle nodeType 'Episode'/'Series' explicitly (not just Character/Event/Location/Organization); branch node/edge detail panel choice on edge.claim_id == null vs != null (D-05/D-06/D-07).
```

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `frontend/src/hooks/useWatchProgress.ts` | hook | event-driven | No prior client-state/sessionStorage hook exists in this project — first of its kind; built from RESEARCH.md pitfall guidance and D-02/D-03 rather than an existing analog |
| `frontend/src/hooks/useSeries.ts`, `useEpisodes.ts`, `useGraph.ts` | hook | request-response | No prior data-fetching hook layer exists — pattern established fresh from `api/*` + standard React fetch-hook shape, not copied from an existing hook |
| `frontend/vitest.config.ts`, `frontend/src/test/setup.ts` | config | — | No test infrastructure exists yet (RESEARCH.md "Wave 0 Gaps") — must be scaffolded from RESEARCH.md guidance, not copied from an existing config |

## Metadata

**Analog search scope:** `frontend/src/` (full tree — only 8 files existed pre-phase: `App.tsx`, `App.css`, `main.tsx`, `lib/utils.ts`, `components/ui/*` x10), `backend/app/domain/*.py`, `backend/app/core/errors.py`, `backend/app/api/*.py` (error shapes only)
**Files scanned:** 8 existing frontend files (all read in full) + 3 backend domain/error files (all read in full)
**Pattern extraction date:** 2026-07-29
