# Phase 2: Polished Cytoscape Graph Experience - Research

**Researched:** 2026-07-29
**Domain:** React/TypeScript frontend — Cytoscape.js graph visualization, shadcn/Tailwind UI, client-held spoiler-progress state against an existing FastAPI backend
**Confidence:** HIGH (stack/versions verified live against installed `node_modules`, npm registry, and the running local backend; MEDIUM on general Cytoscape UX patterns from web search; LOW/ASSUMED flagged explicitly below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** On load, show an explicit empty state — the user must deliberately pick the series, then pick an episode/watch-progress, before any `/graph` request fires. Do not auto-select Dexter + S01E01 on mount.
- **D-02:** The selected series and current `visible_until_order` persist in `sessionStorage` so a page refresh within the same tab restores the last state instead of resetting to empty. Restoring from `sessionStorage` on mount does **not** re-trigger the confirmation modal — the modal only fires on a live, in-session watch-progress change initiated by the user.
- **D-03:** The confirmation modal appears on **every** watch-progress change, not just forward advances — moving backward to re-watch an already-unlocked earlier episode also shows a confirmation step, not just forward unlocks. — **Reversibility:** reversible — purely a client-side gating condition, easy to narrow to forward-only later.
- **D-04:** Add `cytoscape-cose-bilkent` as a new frontend dependency (`frontend/package.json` change) and register it (`cytoscape.use(coseBilkent)`), using `layout: 'cose-bilkent'` as the primary layout per `02-UI-SPEC.md`'s stated preference. Built-in `cose` remains an explicit fallback only if `cose-bilkent` proves unstable in practice during implementation — not a decision to build both paths up front.
- **D-05:** Structural edges (`PART_OF`, `PRECEDES` — no `claim_id`, not evidence-backed) are selectable, same as claim-backed narrative edges. Nothing on the canvas is inert to clicks.
- **D-06:** Structural edges open a distinct, tab-less minimal detail card — not the Overview/Claims/Evidence tabbed `Sheet` used for nodes and claim-backed edges. This is a second, simpler detail-panel layout (e.g., relationship type + the two connected node labels), signaling "not a narrative claim" rather than showing empty/disabled claim/evidence tabs.
- **D-07:** Nodes and claim-backed narrative edges (edges carrying a `claim_id`) both use the existing Overview/Claims/Evidence tabbed `Sheet` layout defined in `02-UI-SPEC.md`.
- **D-08:** No backend/API contract changes of any kind. Use only the three existing endpoints. Watch progress is never persisted server-side in Phase 2 — every graph fetch resends the full `visible_until_order` computed from client state (see D-02).

### Claude's Discretion

- Exact frontend file/component structure (`api/`, `types/`, `hooks/`, `components/{layout,episode,graph,detail}/` as proposed during discussion) — no objection was raised; treat as the intended direction, not a hard lock the planner must reproduce verbatim.
- Exact confirmation-modal copy for **backward** (rewatch) moves. `02-UI-SPEC.md`'s locked copy ("Unlock S01E0X?" / "You're about to see new characters, events, and relationships from S01E0X.") is written for forward-only advances. Since D-03 extends confirmation to backward moves too, the planner/executor must add a backward-move copy variant (same warning-tinted visual treatment, Cancel/confirm button pattern) alongside — not replacing — the existing Copywriting Contract table in `02-UI-SPEC.md`, rather than silently diverging from the locked contract.
- The precise trigger condition for falling back from `cose-bilkent` to `cose` (D-04) is left to the executor's judgment — only fall back on an actual build/runtime failure encountered with the package, not preemptively.
- Series selector stays a genuine interactive `Select` control even though only one series (Dexter) exists today — consistent with D-01's explicit-empty-state choice and forward compatibility with future series.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within Phase 2 scope. (`UserNote` dashed-border node styling and `automatic`-origin system-indicator glyphs are already deferred to Phases 3 and 5 respectively by `02-UI-SPEC.md` itself, not new deferrals from this discussion.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| UI-01 | The Vite starter is replaced by a React/TypeScript product layout that loads series, episodes, and graph data from the backend. | See `## Architecture Patterns` (project structure, API client) and confirmed live shapes of `GET /api/series`, `GET /api/series/{id}/episodes` in `## Code Examples` |
| UI-02 | A watch-progress selector confirms advancement before unlocking a later episode and safely refreshes the applied backend boundary. | See D-01/D-02/D-03 handling in `## Architecture Patterns` → State Management, and `## Common Pitfalls` (sessionStorage restore vs. modal retrigger) |
| UI-03 | Cytoscape renders only returned nodes/edges and visibly updates as S01E01, S01E02, and S01E03 become allowed. | See `## Standard Stack` (cytoscape-cose-bilkent), `## Package Legitimacy Audit`, live node/edge counts per boundary in `## Code Examples`, and the **origin value mismatch** pitfall (`canonical` vs. spec's `curated`) |
| UI-04 | Node and edge/claim detail views explain relationships and display linked source/evidence episode locators. | See `GraphClaim`/`GraphSource`/`GraphEvidence` field inventory in `## Code Examples`, D-06/D-07 tabbed-vs-minimal panel split |
| UI-05 | Frontend build/lint/component checks and demo UX checks verify safe progress changes and absence of hidden-data rendering. | See `## Validation Architecture` and `## Environment Availability` |
</phase_requirements>

## Summary

Phase 2 is a frontend-only build against an already-running, already-verified backend (`GET /api/series`, `GET /api/series/{series_id}/episodes`, `GET /api/series/{series_id}/graph?visible_until_order=N` are all live and healthy on `localhost:8000` at research time). The stack is already scaffolded: React 19 + Vite 8 + TypeScript 6 + Tailwind v4 + shadcn (10 components installed, `radix-nova` dark theme locked in `02-UI-SPEC.md`) + `cytoscape` 3.34.0 + `react-cytoscapejs` 2.0.0. The only new runtime dependency this phase adds is `cytoscape-cose-bilkent` (D-04), which is a legitimate, long-established, officially-maintained package (`cytoscape` GitHub org, 10.7M weekly downloads, published 2019, peer-compatible with the installed `cytoscape@3.34.0`).

Two verified findings materially change how the plan should be written, both discovered by hitting the live backend and reading its seed data directly rather than trusting the design docs:

1. **The wire value for node/edge/claim/source/evidence `origin` is `"canonical"`, never `"curated"`.** `02-UI-SPEC.md`'s origin border-treatment table and the coding-agent spec's own TypeScript type both say `"curated" | "automatic" | "user"`. Every live API response and every seed JSON file in `data/dexter/seed/` uses `"canonical"`. Code that branches on `origin === 'curated'` will silently never match — the plan must branch on `'canonical'` (treating it as the Phase-2-relevant equivalent of "curated" solid-border treatment) and should flag this naming drift back into `02-UI-SPEC.md` rather than re-deriving a different value.
2. **The returned node set includes `Episode` and `Series` node types**, not just `Character`/`Event`/`Location`/`Organization`. The backend's `VISIBLE_NODE_LABELS` explicitly queries `["Series", "Episode", "Character", "Event", "Location"]`, and `PART_OF`/`PRECEDES` structural edges require `Episode`/`Series` nodes to exist in the node list (the API enforces graph closure — dangling edges are a 500-class validation error). `02-UI-SPEC.md`'s node-type shape table has no entry for `Episode` or `Series`. The plan must add a shape/style for both (e.g., hexagon/tag-like per the coding-agent spec's own §9.1 suggestion for `Episode`, plus something equivalently distinct for `Series`), or the canvas will render two untyped node types with browser-default Cytoscape styling — directly undermining UI-03's "must not look like default Cytoscape output" intent.

**Primary recommendation:** Build a thin `api/` client (typed `fetch` wrappers, no new HTTP library), a `hooks/` layer for graph/episode data + `sessionStorage`-backed progress state, and `components/{layout,episode,graph,detail}/` per the discretion note — reuse the 10 already-installed shadcn primitives, add only `cytoscape-cose-bilkent` as a runtime dependency, and add a Vitest + React Testing Library test layer (currently absent) to satisfy UI-05's "component checks" requirement.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Series/episode/graph data fetching | Browser / Client (SPA) | API / Backend (data source) | No SSR in this stack (plain Vite SPA); all fetches happen client-side against the existing FastAPI backend |
| Spoiler filtering (which nodes/edges/claims are visible) | API / Backend | — | Backend-authoritative by non-negotiable project rule (coding-agent spec §3.1); frontend must never reintroduce this as a security boundary |
| Watch-progress state (`visible_until_order`) | Browser / Client | — | No persisted-progress endpoint exists (D-08); state lives in React state + `sessionStorage` only, per D-02 |
| Confirmation-before-advance gating | Browser / Client | — | Purely a UX gate around the client's own next `/graph` fetch; not a security control |
| Graph rendering (Cytoscape canvas, layout, styling) | Browser / Client | — | `cytoscape` + `react-cytoscapejs` run entirely in-browser against the already-filtered payload |
| Detail panel (node/claim/structural-edge inspection) | Browser / Client | — | Renders fields already present in the fetched `GraphResponse`; no additional network round trip per node click |
| CORS / origin allowlist | API / Backend | — | `backend/app/main.py` hardcodes `allow_origins=["http://localhost:5173"]`; frontend dev server must run on that exact origin or the demo will fail with CORS errors, not app bugs |

## Standard Stack

### Core (already installed — verified against `frontend/package.json` and live `node_modules`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `react` / `react-dom` | ^19.2.7 | UI runtime | Already scaffolded [VERIFIED: frontend/package.json] |
| `vite` | ^8.1.1 | Build/dev server | Already scaffolded [VERIFIED: frontend/package.json] |
| `typescript` | ~6.0.2 | Language | Already scaffolded, strict flags enabled [VERIFIED: frontend/tsconfig.app.json] |
| `cytoscape` | ^3.34.0 | Graph engine | Already installed, per coding-agent spec §9 [VERIFIED: frontend/package.json] |
| `react-cytoscapejs` | ^2.0.0 | React wrapper for Cytoscape | Already installed; standard React binding for Cytoscape.js [VERIFIED: npm view — peer `cytoscape: ^3.2.19`, `react: >=15.0.0`, both satisfied] |
| `@types/cytoscape` | ^3.21.9 | TS types for `cytoscape` | Already installed [VERIFIED: frontend/package.json] |
| shadcn (`button`, `card`, `dialog`, `select`, `badge`, `separator`, `skeleton`, `alert`, `sheet`, `tabs`) | via `radix-ui` ^1.6.7 meta-package | Component library, locked visual system | Already installed and themed per `02-UI-SPEC.md` [VERIFIED: frontend/src/components/ui/*] |
| `tailwindcss` / `@tailwindcss/vite` | ^4.3.3 | Styling engine | Already installed, CSS-first `@theme` config [VERIFIED: frontend/package.json] |
| `lucide-react` | ^1.27.0 | Icons | Already installed, used by shadcn components (e.g. `XIcon` in `sheet.tsx`) [VERIFIED: frontend/src/components/ui/sheet.tsx] |

### New dependency required by this phase (D-04)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `cytoscape-cose-bilkent` | 4.1.0 (latest) | Force-directed layout tuned for compound/small narrative graphs | Locked by D-04; official `cytoscape` GitHub org extension, peer-compatible with installed `cytoscape@3.34.0` (`peerDependencies: { cytoscape: "^3.2.0" }`) [VERIFIED: npm view + package-legitimacy check] |

**No TypeScript types exist for `cytoscape-cose-bilkent`** — `npm view cytoscape-cose-bilkent types` returns nothing, and `@types/cytoscape-cose-bilkent` **does not exist on the npm registry** (`package-legitimacy check` returned `SLOP` / `does-not-exist` when this name was probed defensively). The plan must have the executor add a local ambient module declaration (e.g. `frontend/src/types/cytoscape-cose-bilkent.d.ts` with `declare module 'cytoscape-cose-bilkent'`) rather than trying to install a types package that isn't real. [VERIFIED: npm registry]

**`react-cytoscapejs` also ships no bundled TypeScript types** (`node_modules/react-cytoscapejs/package.json` has no `types`/`typings` field). `@types/react-cytoscapejs` **does exist** on DefinitelyTyped (v1.2.6, published 2025-10-10, OK verdict, ~24.6k weekly downloads) and should be added as a `devDependency` for typed `CytoscapeComponent` props. [VERIFIED: npm view + package-legitimacy check]

### Supporting (recommended additions for this phase — test tooling)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `vitest` | 4.1.10 | Test runner (Vite-native) | UI-05 requires "component checks"; no test runner exists today. Peer-compatible with installed `vite@^8.0.0` (`peerDependencies.vite: "^6.0.0 \|\| ^7.0.0 \|\| ^8.0.0"`) [VERIFIED: npm view] |
| `@testing-library/react` | 16.3.2 | Component render/interaction testing | Peer-compatible with React 19 (`peerDependencies.react: "^18.0.0 \|\| ^19.0.0"`) [VERIFIED: npm view] |
| `@testing-library/jest-dom` | 7.0.0 | DOM matcher assertions | Standard companion to RTL |
| `@testing-library/user-event` | 14.6.1 | Realistic user interaction simulation (clicks, select changes) | For simulating episode-selector changes and modal confirm/cancel clicks |
| `jsdom` | 30.0.1 | DOM environment for Vitest | Required test environment for React component tests outside a real browser |

**No mocking library (e.g. MSW) is recommended for this phase** — see Package Legitimacy Audit below. Given only 3 fetch call sites and no complex request matching needs, hand-write a small typed `fetch` stub (`vi.fn()` returning canned `GraphResponse`/`SeriesResponse`/`EpisodeResponse` JSON) rather than adding a mocking framework. This also matches the coding-agent spec's own stated philosophy: "avoid unnecessary enterprise abstractions" (§8).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-written `fetch` wrappers in `api/` | TanStack Query / SWR | Adds caching/retry/dedup machinery the phase doesn't need (3 read-only endpoints, no pagination, no background refetch); would be scope creep against D-08's "no new API contract" minimalism. Plain `fetch` + custom hooks is the better fit here. |
| Vitest + RTL | Playwright / Cypress e2e | Full browser e2e would better exercise the literal demo script (§15) end-to-end, but adds a much heavier tool and CI dependency for a Prototype v0 phase; UI-05's "demo UX checks" can instead be satisfied by `gsd-verify-work` conversational UAT plus targeted RTL component tests, deferring full e2e to a later phase if needed. |
| `cytoscape-cose-bilkent` | Built-in `cose` layout | D-04 already locks `cose-bilkent` as primary, `cose` as fallback-on-failure only (not built up front) |
| Hand-written `fetch` stubs in tests | MSW (`msw`) | MSW's current registry-checked version failed the legitimacy gate on this run (`too-new` + `suspicious-postinstall` — see audit below); the phase's data-fetching surface is small enough that hand-written stubs avoid the dependency entirely |

**Installation:**
```bash
cd frontend
npm install cytoscape-cose-bilkent
npm install -D @types/react-cytoscapejs vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

**Version verification:** All versions above were confirmed live via `npm view <package> version` against the real npm registry during this research session (2026-07-29), not from training-data recall — the installed stack (React 19, Vite 8, TypeScript 6) is itself already ahead of common training-data-era version numbers, so any recalled version would likely be stale.

## Package Legitimacy Audit

| Package | Registry | Age (published) | Weekly Downloads | Source Repo | Verdict | Disposition |
|---------|----------|------------------|-------------------|-------------|---------|-------------|
| `cytoscape-cose-bilkent` | npm | 2019-09-09 (this major; project itself since 2015) | 10,747,093 | `github.com/cytoscape/cytoscape.js-cose-bilkent` | OK | Approved — locked by D-04 |
| `@types/react-cytoscapejs` | npm | 2025-10-10 | 24,612 | `github.com/DefinitelyTyped/DefinitelyTyped` | OK | Approved (devDependency) |
| `@types/cytoscape-cose-bilkent` | npm | — | — | none | SLOP (`does-not-exist`) | REMOVED — do not attempt to install; use a local `.d.ts` ambient declaration instead |
| `vitest` | npm | 2026-07-06 | 82,309,790 | `github.com/vitest-dev/vitest` | SUS (`too-new`) | Flagged — planner must add `checkpoint:human-verify` before install |
| `@testing-library/react` | npm | 2026-01-19 | 49,288,028 | `github.com/testing-library/react-testing-library` | OK | Approved |
| `@testing-library/jest-dom` | npm | 2026-07-20 | 55,557,051 | `github.com/testing-library/jest-dom` | SUS (`too-new`) | Flagged — planner must add `checkpoint:human-verify` before install |
| `@testing-library/user-event` | npm | 2025-01-21 | 43,256,496 | `github.com/testing-library/user-event` | OK | Approved |
| `jsdom` | npm | 2026-07-29 (today) | 85,867,485 | `github.com/jsdom/jsdom` | SUS (`too-new`) | Flagged — planner must add `checkpoint:human-verify` before install |
| `msw` | npm | 2026-07-08 | 19,354,686 | `github.com/mswjs/msw` | SLOP (`too-new`, `suspicious-postinstall`) | REMOVED — not recommended for this phase; use hand-written fetch stubs instead (see Alternatives Considered) |

**Packages removed due to `[SLOP]` verdict:** `@types/cytoscape-cose-bilkent` (does not exist — use local ambient declaration), `msw` (flagged `too-new` + `suspicious-postinstall` by the legitimacy gate; not required for this phase's small fetch surface, so simply not recommended rather than substituted)
**Packages flagged as suspicious `[SUS]`:** `vitest`, `@testing-library/jest-dom`, `jsdom` — all three are extremely high-download, long-established, canonically-sourced packages (their GitHub repos are the actual upstream projects, not lookalikes); the `too-new` signal here reflects a recent version *release* on an actively-maintained package, not package novelty. The planner should still insert a `checkpoint:human-verify` task before installing each, per protocol, but this is very likely a heuristic false-positive rather than a real slopsquat risk — human verification should be quick (confirm the npm page matches the linked GitHub org).

*Note: `cytoscape`, `react-cytoscapejs`, `@types/cytoscape`, `radix-ui`, `tailwindcss`, `lucide-react`, and all shadcn-installed components were NOT re-audited here because they are already installed and running in the project (verified directly from `frontend/package.json` and `node_modules`, not newly discovered) — the legitimacy gate applies to newly-introduced packages, not already-vetted brownfield dependencies.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (React SPA)                          │
│                                                                       │
│  1. Mount → empty state (D-01)                                      │
│     │                                                                │
│     ├─(sessionStorage has prior state?)──► restore series+order,    │
│     │                                       skip confirmation (D-02) │
│     │                                                                │
│  2. User selects Series → GET /api/series ─────────────────┐        │
│  3. User selects Episode → GET /api/series/{id}/episodes   │        │
│     │                                                        │        │
│  4. User changes watch progress                             │        │
│     │                                                        │        │
│     ▼                                                        │        │
│  ┌─────────────────────┐   forward OR backward (D-03)       │        │
│  │ Confirmation Modal   │───► Cancel → no fetch, no state    │        │
│  │ (Dialog, warning     │        change                      │        │
│  │  color per UI-SPEC)  │───► Confirm → commit new           │        │
│  └─────────────────────┘        visible_until_order to       │        │
│     │                            sessionStorage + state      │        │
│     ▼                                                        ▼        │
│  5. GET /api/series/{id}/graph?visible_until_order=N ───────────────┼──► FastAPI backend
│     │                                                                │   (spoiler filter,
│     ▼                                                                │    already verified
│  6. Map GraphResponse → Cytoscape elements                           │    Phase 1)
│     (nodes/edges typed per backend/app/domain/graph.py)              │
│     │                                                                │
│     ▼                                                                │
│  7. cytoscape.use(coseBilkent); layout: 'cose-bilkent'               │
│     render on <CytoscapeComponent>                                   │
│     │                                                                │
│     ├─ click node ──► Sheet: Overview/Claims/Evidence tabs (D-07)    │
│     ├─ click claim-backed edge (has claim_id) ──► same tabbed Sheet  │
│     └─ click structural edge (PART_OF/PRECEDES, no claim_id) ──►     │
│              minimal tab-less detail card (D-06)                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
frontend/src/
├── api/                 # typed fetch wrappers: getSeries(), getEpisodes(id), getGraph(id, order)
├── types/                # GraphNode/GraphEdge/GraphClaim/... mirroring backend/app/domain/*.py exactly
│   └── cytoscape-cose-bilkent.d.ts   # ambient module declaration (no upstream types exist)
├── hooks/                # useSeries(), useEpisodes(seriesId), useGraph(seriesId, order), useWatchProgress()
├── components/
│   ├── layout/           # AppShell, top bar (series/episode display)
│   ├── episode/          # EpisodeSelector (Select), ConfirmAdvanceModal (Dialog)
│   ├── graph/            # GraphCanvas (CytoscapeComponent wrapper), graph→cytoscape element mapping, stylesheet
│   └── detail/           # DetailPanel (Sheet, Overview/Claims/Evidence tabs), StructuralEdgeCard (minimal, no tabs)
├── lib/
│   └── utils.ts          # existing cn() helper — reuse, do not duplicate
├── App.tsx               # replaces Vite starter content (UI-01)
└── main.tsx               # leave existing wiring intact
```

### Pattern 1: Typed API client over the existing endpoints

**What:** Small, explicit `fetch` wrapper functions — one per endpoint — that parse the `{detail:{code,message}}` error shape generically and return typed success payloads.
**When to use:** All three data fetches (series, episodes, graph).
**Example:**
```typescript
// api/graph.ts
// Types mirror backend/app/domain/graph.py exactly (verified against live /api/series/{id}/graph response)
export type GraphNode = {
  id: string
  type: string
  label: string
  visible_from_order: number
  origin: string          // wire value is "canonical" in this project, NOT "curated" — see Common Pitfalls
  episode_id: string | null
}

export type GraphEdge = {
  id: string
  source: string
  target: string
  type: string
  visible_from_order: number
  origin: string
  claim_id: string | null   // present only on claim-backed edges (D-07); null/absent on structural edges (D-05/D-06)
}

export type ApiError = { code: string, message: string }

export class GraphApiError extends Error {
  code: string
  constructor(detail: ApiError) {
    super(detail.message)
    this.code = detail.code
  }
}

export async function getGraph(seriesId: string, visibleUntilOrder: number): Promise<GraphResponse> {
  const url = `/api/series/${seriesId}/graph?visible_until_order=${visibleUntilOrder}`
  const res = await fetch(url)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new GraphApiError(body?.detail ?? { code: 'unknown_error', message: 'Request failed.' })
  }
  return res.json() as Promise<GraphResponse>
}
```
*(Source: backend/app/domain/graph.py, backend/app/api/graph.py, backend/app/core/errors.py — verified 404/422/503 shapes live via curl during this research session.)*

### Pattern 2: Cytoscape element mapping + registration

**What:** Register `cose-bilkent` once at module load, map `GraphResponse.nodes`/`edges` to Cytoscape `elements`, keep `nodeType`/`origin`/`claimId` as `data()` fields for stylesheet selectors.
**When to use:** `components/graph/GraphCanvas.tsx`.
**Example:**
```typescript
// Source: coding-agent-spec §9.2 pattern, adapted to this project's actual origin value
import cytoscape from 'cytoscape'
import coseBilkent from 'cytoscape-cose-bilkent'
import CytoscapeComponent from 'react-cytoscapejs'

cytoscape.use(coseBilkent)

const elements = [
  ...graph.nodes.map((node) => ({
    data: {
      id: node.id,
      label: node.label,
      nodeType: node.type,       // includes "Character" | "Event" | "Location" | "Episode" | "Series" — verified live
      origin: node.origin,       // "canonical" in this project's data, not "curated"
    },
  })),
  ...graph.edges.map((edge) => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.type,
      claimId: edge.claim_id,     // null on structural edges — use to branch D-06 vs D-07 panel
      origin: edge.origin,
    },
  })),
]

<CytoscapeComponent
  elements={elements}
  layout={{ name: 'cose-bilkent', nodeDimensionsIncludeLabels: true, fit: true, padding: 24 }}
  stylesheet={graphStylesheet}
  cy={(cy) => { cyRef.current = cy }}
/>
```
*(Source: react-cytoscapejs README pattern [CITED: npmjs.com/package/react-cytoscapejs, github.com/plotly/react-cytoscapejs] cross-checked with coding-agent spec §9.2)*

### Pattern 3: Selection-driven highlight/fade (neighbor emphasis)

**What:** On node tap, compute `node.closedNeighborhood()`, add a highlight class to it, add a faded class to everything else; on edge tap (either structural or claim-backed), highlight just that edge and its two endpoints.
**When to use:** Satisfies coding-agent spec §9.1's "Selected node becomes visually dominant. Immediate neighbors remain highlighted. Unrelated nodes fade." recommendation, and gives D-05's "nothing is inert to clicks" a visible effect for structural edges too.
**Example:**
```typescript
// Source: general Cytoscape.js core API pattern [CITED: js.cytoscape.org, github.com/cytoscape/cytoscape.js issues #842/#969 — cross-checked via WebSearch]
cy.on('tap', 'node', (evt) => {
  const node = evt.target
  const neighborhood = node.closedNeighborhood()
  cy.elements().difference(neighborhood).addClass('faded')
  neighborhood.removeClass('faded')
  node.addClass('selected-dominant')
})

cy.on('tap', 'edge', (evt) => {
  const edge = evt.target
  cy.elements().difference(edge.connectedNodes().union(edge)).addClass('faded')
  edge.connectedNodes().union(edge).removeClass('faded')
})

cy.on('tap', (evt) => {
  if (evt.target === cy) {
    cy.elements().removeClass('faded selected-dominant')
  }
})
```

### Anti-Patterns to Avoid

- **Re-deriving spoiler filtering client-side:** Never filter nodes/edges by `visible_from_order` in the frontend as a security measure — the backend already does this (Phase 1, verified). The frontend may safely assume everything returned is meant to be shown.
- **Hardcoding `origin === 'curated'`:** The actual wire value is `'canonical'`. Copy the shape/border logic from `02-UI-SPEC.md`'s intent (solid border for canonical/curated seed data) but switch on the real string.
- **Treating all node `type`s as one of the 5 shapes in `02-UI-SPEC.md`'s table:** `Episode` and `Series` are real, rendered node types (not filtered out server-side) with no assigned shape in the current design contract — the plan must add them, not drop them from the canvas or leave them unstyled.
- **Using `dangerouslySetInnerHTML` for any evidence/claim text:** All detail-panel text (labels, evidence `text`, locators) should render through normal JSX text interpolation, which React auto-escapes. There is no legitimate need for raw HTML here.
- **Persisting raw, unvalidated `sessionStorage` JSON without a parse guard:** `JSON.parse` on a corrupted/tampered `sessionStorage` value should not crash the app on mount — wrap in try/catch and fall back to the D-01 empty state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Force-directed graph layout | Custom physics/layout algorithm | `cytoscape-cose-bilkent` (D-04) | Layout quality for small narrative graphs is exactly what this extension is tuned for; hand-rolling a layout is high-effort, low-value duplication |
| Neighbor highlight/fade on selection | Custom DOM overlay tracking | Cytoscape core `.closedNeighborhood()` + CSS-selector-based style classes | Cytoscape's own selector/class system already handles this efficiently on the canvas; no need for parallel DOM state |
| Accessible modal/dialog/sheet/tabs primitives | Custom `<div>`-based modal/tab implementations | Already-installed shadcn `Dialog`, `Sheet`, `Tabs` (Radix-based, `data-slot` pattern) | Radix primitives already handle focus trapping, escape-to-close, ARIA roles — reinventing this is both wasted effort and a worse accessibility outcome |
| Client-side request/response validation of trusted-origin JSON | Hand-written deep validators for every fetch response | TypeScript types mirroring `backend/app/domain/*.py` + trust the same-project, CORS-locked-down backend (no external/untrusted data source in Phase 2) | Given the backend is same-repo, CORS-restricted to one dev origin, and has zero external inputs feeding it in Phase 2, a runtime schema validator (e.g. zod) would be defensible engineering discipline but is not required to meet UI-01..05; keep as a documented option, not a mandate, to avoid scope creep beyond D-08's "no new API contract" minimalism |

**Key insight:** Everything genuinely hard about this phase (spoiler-safe filtering, evidence-claim data model) is already solved server-side and verified in Phase 1. The frontend's job is presentation and interaction polish over an already-correct payload — resist the temptation to add a second filtering/validation layer that duplicates backend logic.

## Common Pitfalls

### Pitfall 1: `origin` field naming mismatch between design docs and actual data

**What goes wrong:** Code written to match `02-UI-SPEC.md`'s table (`origin === 'curated'` → solid border) silently never triggers, because the real value everywhere in this project is `'canonical'`.
**Why it happens:** `02-UI-SPEC.md` and the coding-agent spec's example TypeScript type both use `curated` as a placeholder term; the actual Phase 1 seed data and backend (`backend/app/graph/seed.py`, `data/dexter/seed/*.json`, spoiler filter Cypher) all set `origin: "canonical"`.
**How to avoid:** Branch UI logic on the literal string `'canonical'` (verified live from `GET /api/series/series_dexter/graph`). Treat `'canonical'` as this project's "solid border, no glyph" origin value; keep `automatic`/`user` handling forward-compatible for Phases 3/5 since those origin values don't yet exist in seed data.
**Warning signs:** If every node/edge on the canvas renders with the same (default/dashed) border regardless of origin, this is the mismatch manifesting.

### Pitfall 2: Missing shape mapping for `Episode`/`Series` node types

**What goes wrong:** The graph canvas includes `Episode` and `Series` nodes (verified: `visible_until_order=1` returns 1 `Episode` + 1 `Series` node alongside 6 `Character`/1 `Event`/2 `Location`; `visible_until_order=3` returns 3 `Episode` + 1 `Series` node). `02-UI-SPEC.md`'s node-type shape table only covers `Character`/`Event`/`Location`/`Organization`/`UserNote`. Without an explicit style rule, these nodes fall through to Cytoscape's plain default (a bare ellipse), undermining UI-03's visual-language requirement.
**Why it happens:** The design contract was written focused on narrative content types; the structural scaffold (`PART_OF`/`PRECEDES` between `Episode`↔`Series`↔`Episode`) requires those node types to exist in the response for graph closure (`GraphResponse.enforce_graph_closure` rejects dangling edges), but nobody assigned them a shape.
**How to avoid:** Add explicit stylesheet rules for `nodeType === 'Episode'` (hexagon or compact tag shape, per coding-agent spec §9.1's own suggestion) and `nodeType === 'Series'` (a distinct shape, e.g. a larger rounded rectangle or star to signal "root" — planner's/executor's discretion, not locked by CONTEXT.md) before considering UI-03 complete.
**Warning signs:** Two default-ellipse nodes appear on every graph view regardless of episode order.

### Pitfall 3: Node count target excludes structural scaffold nodes

**What goes wrong:** The coding-agent spec's "8–15 visible nodes per episode" target (§9.1) is easy to read as "the layout should stay readable at roughly that count" — but live data shows 11 total nodes at S01E01 (6 Character + 1 Event + 2 Location + 1 Episode + 1 Series) and 20 total nodes at S01E03 (9 Character + 3 Event + 4 Location + 3 Episode + 1 Series), already exceeding the upper bound once structural nodes are included.
**Why it happens:** The target was written before the exact seed data volume was finalized in Phase 1; Series/Episode scaffold nodes accumulate (one more `Episode` node unlocks per boundary) alongside narrative content.
**How to avoid:** Tune `cose-bilkent` layout parameters (e.g., `idealEdgeLength`, `nodeRepulsion`) for readability up to ~20 nodes rather than assuming the target caps out at 15; treat the 8–15 figure as directional, not a hard per-episode ceiling to enforce in code.
**Warning signs:** Layout becomes visually cluttered specifically at the S01E03 boundary during manual testing.

### Pitfall 4: CORS origin mismatch between Vite dev server and backend allowlist

**What goes wrong:** `backend/app/main.py` hardcodes `allow_origins=["http://localhost:5173"]`. If the Vite dev server ever starts on a different port (e.g., 5173 already in use, causing Vite to auto-increment to 5174), every fetch will fail with a CORS error that looks like an app bug rather than a config mismatch.
**Why it happens:** No `server.port` is pinned in `frontend/vite.config.ts`; Vite's default port is currently 5173 but is not guaranteed if the port is occupied.
**How to avoid:** During implementation/testing, confirm the dev server is actually serving on port 5173 (already confirmed running there at research time) before debugging fetch failures as application logic bugs.
**Warning signs:** `TypeError: Failed to fetch` / browser console CORS errors on every API call despite the backend being reachable directly via curl/Swagger.

### Pitfall 5: `sessionStorage` restore incorrectly re-triggers the confirmation modal

**What goes wrong:** A naive implementation ties the confirmation modal to "watch-progress state changed," which would also fire when `sessionStorage`-restored state hydrates React state on mount (a `useState`/`useEffect` "change" from empty→restored looks identical to a live user-initiated change).
**Why it happens:** D-02 explicitly requires the modal to fire only on live, user-initiated changes — this needs a deliberate guard (e.g., an initialization flag, or comparing "previous confirmed order" set once during hydration before any change-detection effect runs), not the naive "state changed → show modal" wiring.
**How to avoid:** Distinguish "hydrating from storage" from "user changed the selector" as two explicitly different code paths — e.g., hydrate state directly without going through the same setter/handler that opens the confirmation dialog.
**Warning signs:** Confirmation modal appears immediately on page refresh even when the user made no new selection.

## Code Examples

### Verified live API shapes (fetched from running backend, 2026-07-29)

```typescript
// GET /api/series
// [{"id":"series_dexter","title":"Dexter","slug":"dexter"}]

// GET /api/series/series_dexter/episodes
// [
//   {"id":"dexter_s01e01","series_id":"series_dexter","season_number":1,"episode_number":1,
//    "episode_order":1,"code":"S01E01","title":"Dexter","visible_from_order":1},
//   {"id":"dexter_s01e02", ... "code":"S01E02","title":"Crocodile","visible_from_order":2},
//   {"id":"dexter_s01e03", ... "code":"S01E03","title":"Popping Cherry","visible_from_order":3}
// ]

// GET /api/series/series_dexter/graph?visible_until_order=1
// nodes: 11 (Character:6, Event:1, Location:2, Episode:1, Series:1)
// edges: 6 (types seen: OCCURRED_IN, PART_OF, WORKS_WITH, FAMILY_OF)
// claims: 4 (one has status:"candidate", valid_until_order:1 — demonstrates claim-validity boundary)
// sources: 1, evidence: 3 — evidence `text` fields are short single sentences (no overflow case in current seed data)

// Error shapes (verified via curl):
// 422 invalid_visible_until_order: {"detail":{"code":"invalid_visible_until_order","message":"visible_until_order must identify a persisted episode order."}}
// 404 series_not_found:            {"detail":{"code":"series_not_found","message":"Series not found."}}
```

### Detail panel field inventory (from `GraphClaim`/`GraphSource`/`GraphEvidence`, verified live)

```typescript
// A claim (Overview/Claims tab content, D-07):
// { id, label, subject_id, predicate, object_id, claim_type, status,
//   confidence_level, relationship_effect, visible_from_order,
//   valid_from_order, valid_until_order, source_id, evidence_ids, origin }
// Example live values: claim_type: "explicit_fact"|"observed_event"|"inferred_state"
//                       status: "canonical"|"corroborated"|"candidate"
//                       confidence_level: "verified"|"high"|"medium"
//                       relationship_effect: 0.2–0.9 (float)

// Evidence (Evidence tab, copy per UI-SPEC: "Source: {source label} — {locator}"):
// { id, label, episode_id, source_id, text, locator, content_hash, visible_from_order, origin }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `@radix-ui/react-*` per-primitive packages | Single `radix-ui` meta-package (v1.6.7) with `import { Dialog as SheetPrimitive } from "radix-ui"` | Already reflected in this project's installed shadcn output | Planner/executor should follow the same single-import pattern already used in `frontend/src/components/ui/sheet.tsx`/`tabs.tsx`, not reintroduce per-primitive imports |
| Tailwind `tailwind.config.js` | Tailwind v4 CSS-first `@theme inline` config (no JS config file) | Already reflected in this project (`frontend/src/index.css`) | Do not create a `tailwind.config.*` file; add new design tokens (if any) to the existing CSS `@theme` block |

**Deprecated/outdated:** N/A for this phase — no deprecated APIs identified in the locked stack.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Shape choice for `Episode` node type (hexagon/tag) and for `Series` node type (unspecified) is a reasonable placeholder, not a locked visual decision | Common Pitfalls #2, Architecture Patterns | Low — purely cosmetic; easy to adjust once a human reviews the rendered canvas; not a functional risk |
| A2 | A runtime schema validator (zod) is not required for Phase 2 given the same-origin, CORS-locked, same-repo backend | Don't Hand-Roll | Low-Medium — if the backend response shape ever drifts without a corresponding frontend type update, a malformed field could reach the UI as `undefined` rather than failing fast; acceptable for Prototype v0 scope per D-08's "no new API contract" framing, but should be reconsidered before Phase 3+ opens up user-editable content |
| A3 | Full Playwright/Cypress e2e is not required to satisfy UI-05; Vitest + RTL component tests plus `gsd-verify-work` conversational UAT are sufficient | Alternatives Considered, Validation Architecture | Medium — if the plan-checker or a future reviewer interprets "demo UX checks" as requiring automated e2e, this assumption would need revisiting; flagged here for discuss-phase/plan-phase to confirm if not already implicit in UI-05's phrasing |
| A4 | `vitest`, `@testing-library/jest-dom`, and `jsdom`'s `SUS` legitimacy verdicts are heuristic false-positives (recent-version-publish detection on well-established, high-download packages) rather than genuine slopsquat risk | Package Legitimacy Audit | Low if correct, High if wrong — per protocol, planner must still gate each behind `checkpoint:human-verify` regardless of this assessment |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **What shape should the `Series` node type use on the canvas?**
   - What we know: `Episode` has a coding-agent-spec-suggested shape (hexagon/tag-like, §9.1); `Series` has no suggestion anywhere in any design doc, yet it renders as a real node on every graph view (exactly 1 per response, the root of the `PART_OF` chain).
   - What's unclear: Whether `Series` should be visually prominent (it's the graph "root") or visually minimized/de-emphasized (it's rarely the focus of narrative exploration).
   - Recommendation: Planner should pick a simple, distinct shape (e.g., a filled star or large rounded rectangle) and note it as a Claude's-discretion addition to `02-UI-SPEC.md`'s node-type table, consistent with how D-04's backward-copy variant was handled (documented alongside, not silently invented).

2. **Should `Episode`/`Series` structural nodes count toward the "8–15 visible nodes" readability target, or be visually de-prioritized (e.g., smaller, muted) so the narrative content dominates the visual field?**
   - What we know: They are unavoidably present in the returned graph (closure requirement) and are already selectable per D-05.
   - What's unclear: Whether "narrative graph" in the coding-agent spec's target language was meant to exclude scaffold nodes.
   - Recommendation: Treat as a layout-tuning question for cose-bilkent parameters (e.g., smaller `idealEdgeLength` weight or grouping) rather than an exclusion — excluding them would violate D-05/graph-closure expectations.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Node.js | Frontend build/dev/test tooling | ✓ | v24.18.0 | — |
| npm | Package installation | ✓ | 11.16.0 | — |
| Backend API (`localhost:8000`) | All three consumed endpoints | ✓ (running, `/health` returns `{"status":"ok","database":"connected"}`) | — | — |
| Neo4j (`localhost:7687`/`7474`) | Backend's data source | ✓ (verified via `/health` and direct bolt-routing query, `neo4j_version: "2026.06.0"`, community edition) | 2026.06.0 | — |
| Vite dev server (`localhost:5173`) | Frontend serving + CORS allowlist match | ✓ (already running, serving `index.html`) | — | — |
| Docker | Local Neo4j container (per `docker-compose.yml`) | ✓ | 29.4.0 | — |
| System `python` | Not required for this frontend-only phase | Python 3.11.15 present, but root `pyproject.toml` declares `>=3.13` | 3.11.15 (system) | Backend appears to run today regardless (health-checked live), likely via a `uv`-managed interpreter (`uv.lock` present) rather than system `python`; not a Phase 2 blocker since no backend changes are made, but flagged in case a future phase needs to invoke `python` directly |

**Missing dependencies with no fallback:** None — all dependencies needed for this phase are present and the full stack (backend + Neo4j + frontend dev server) was confirmed live and healthy at research time.
**Missing dependencies with fallback:** System `python` version mismatch (3.11.15 vs. declared `>=3.13`) noted above; does not block this frontend-only phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest 4.1.10 + @testing-library/react 16.3.2 (none currently installed — Wave 0 gap) |
| Config file | none — see Wave 0 gaps below |
| Quick run command | `npm run test -- --run <file>` (once configured) |
| Full suite command | `npm run test -- --run` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| UI-01 | App renders series/episode/graph data instead of Vite starter | component | `npm run test -- --run src/App.test.tsx` | ❌ Wave 0 |
| UI-02 | Confirmation modal blocks/allows progress change; sessionStorage restore does not retrigger modal | component (RTL + user-event) | `npm run test -- --run src/components/episode/ConfirmAdvanceModal.test.tsx` | ❌ Wave 0 |
| UI-03 | Cytoscape renders only returned nodes/edges; graph updates across boundaries | component (mount `GraphCanvas` with fixture `GraphResponse`, assert element counts/types) | `npm run test -- --run src/components/graph/GraphCanvas.test.tsx` | ❌ Wave 0 |
| UI-04 | Detail panel shows correct fields for node vs. claim-edge vs. structural-edge selection | component | `npm run test -- --run src/components/detail/DetailPanel.test.tsx` | ❌ Wave 0 |
| UI-05 | Build/lint pass; demo flow works end-to-end | build/lint (existing) + manual/conversational UAT | `npm run build && npm run lint` (already exist) | ✅ existing scripts |

### Sampling Rate
- **Per task commit:** targeted `npm run test -- --run <changed-file-test>` + `npm run lint`
- **Per wave merge:** `npm run build && npm run lint && npm run test -- --run`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `vitest.config.ts` (or Vitest config inside `vite.config.ts`) — test environment `jsdom`, globals enabled
- [ ] `frontend/src/test/setup.ts` — imports `@testing-library/jest-dom` matchers
- [ ] `package.json` `"test"` script — `vitest`
- [ ] Fixture data — a small hand-written `GraphResponse` fixture (mirroring the live S01E01 shape captured in `## Code Examples` above) for component tests, since no test infra or fixtures currently exist
- [ ] `checkpoint:human-verify` tasks before installing `vitest`, `@testing-library/jest-dom`, `jsdom` (per Package Legitimacy Audit `SUS` verdicts)

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | No | No authentication exists or is introduced in Phase 2 (explicitly out of scope per `<domain>` boundary) |
| V3 Session Management | No | `sessionStorage` usage here is UI-state persistence, not an authentication session |
| V4 Access Control | No | Backend enforces all visibility; frontend has no access-control decisions to make |
| V5 Input Validation | Yes | TypeScript types mirroring `backend/app/domain/graph.py`/`series.py`; render all user-facing text (labels, evidence text, locators) via normal JSX interpolation (React auto-escapes), never `dangerouslySetInnerHTML`; wrap `sessionStorage` JSON parsing in try/catch with a safe fallback to the D-01 empty state |
| V6 Cryptography | No | No cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| Reflected/stored XSS via evidence/claim text rendered into the detail panel | Tampering | Rely on React's default JSX text-node escaping; explicitly avoid `dangerouslySetInnerHTML` anywhere in `components/detail/` |
| Malformed/tampered `sessionStorage` value crashing the app on mount | Denial of Service (client-side) | Defensive `JSON.parse` in try/catch; validate shape (e.g., `visible_until_order` is a positive integer, `series_id` is a non-empty string) before trusting it, falling back to D-01 empty state on any failure |
| Frontend accidentally reintroducing spoiler filtering as a security boundary | Information Disclosure (inverse — over-restriction) / Tampering (if bypassed) | Never filter by `visible_from_order` client-side as a security control; the backend is authoritative (non-negotiable project rule, coding-agent spec §3.1) — client-side filtering, if ever added for presentation polish, must be understood as cosmetic only |
| CORS misconfiguration exposing the API to unintended origins | Spoofing | Out of scope for Phase 2 (no backend changes per D-08); note the existing hardcoded single-origin allowlist (`http://localhost:5173`) as-is |

## Sources

### Primary (HIGH confidence)
- Live backend (`localhost:8000`) — `GET /health`, `GET /api/series`, `GET /api/series/{id}/episodes`, `GET /api/series/{id}/graph?visible_until_order={1,3}` — actual response shapes, node/edge/claim counts, origin values, error shapes, all fetched directly during this research session (2026-07-29).
- `backend/app/domain/graph.py`, `backend/app/domain/series.py`, `backend/app/api/graph.py`, `backend/app/api/series.py`, `backend/app/core/errors.py`, `backend/app/main.py` — read directly.
- `data/dexter/seed/characters.json`, `data/dexter/seed/events.json`, `backend/app/graph/seed.py` — grepped directly for `origin` field values.
- `frontend/package.json`, `frontend/src/components/ui/sheet.tsx`, `frontend/src/components/ui/tabs.tsx`, `frontend/vite.config.ts` — read directly.
- `npm view <package> version|peerDependencies|types` for `cytoscape-cose-bilkent`, `react-cytoscapejs`, `@types/react-cytoscapejs`, `@types/cytoscape-cose-bilkent`, `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`, `msw` — run live against the npm registry during this session.
- `gsd-tools query package-legitimacy check` — run for all newly-recommended packages (see audit table).

### Secondary (MEDIUM confidence)
- WebSearch (verified/cross-checked against official npm/GitHub pages in the same result set): react-cytoscapejs `CytoscapeComponent` API pattern [CITED: npmjs.com/package/react-cytoscapejs, github.com/plotly/react-cytoscapejs], Cytoscape.js core neighbor-highlight/fade pattern [CITED: js.cytoscape.org, github.com/cytoscape/cytoscape.js issues #842/#969], `cytoscape-cose-bilkent` layout option names (`nodeRepulsion`, `idealEdgeLength`, `quality`) [CITED: npmjs.com/package/cytoscape-cose-bilkent, github.com/cytoscape/cytoscape.js-cose-bilkent].

### Tertiary (LOW confidence)
- None — all claims above were either directly tool-verified or cross-checked WebSearch results against an official source in the same query.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version number and peer-dependency claim was confirmed live via `npm view` or direct file reads, not training-data recall.
- Architecture: HIGH for data shapes/pitfalls (verified against the live running backend); MEDIUM for general Cytoscape UX interaction patterns (WebSearch, cross-checked against official sources).
- Pitfalls: HIGH — the `origin` naming mismatch and missing `Episode`/`Series` shape mapping were discovered by directly querying the live API and reading seed data, not inferred.

**Research date:** 2026-07-29
**Valid until:** 2026-08-12 (30 days — stable brownfield stack; re-verify sooner if `frontend/package.json` or the backend's `data/dexter/seed/` files change before planning begins)
