# Phase 2: Polished Cytoscape Graph Experience - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 replaces the untouched Vite/React starter (`frontend/src/App.tsx`) with the real product UI: select Dexter (the only seeded series) → select the latest watched season/episode → confirm the watch-progress change → load the spoiler-safe graph from the existing `GET /api/series/{series_id}/graph` endpoint → render it in Cytoscape using the already-approved `02-UI-SPEC.md` visual language → let the user inspect a selected node or relationship in a detail panel → communicate loading/empty/error states clearly. It delivers requirements UI-01..UI-05 only.

No backend, Neo4j, or ontology changes. No authentication. No automatic extraction. No new API contract — the frontend consumes `GET /api/series`, `GET /api/series/{id}/episodes`, and `GET /api/series/{id}/graph?visible_until_order=N` exactly as they exist today; there is no persisted-progress endpoint, so watch progress is entirely client-held state re-sent on every graph fetch.

</domain>

<decisions>
## Implementation Decisions

### Startup and Progress State
- **D-01:** On load, show an explicit empty state — the user must deliberately pick the series, then pick an episode/watch-progress, before any `/graph` request fires. Do not auto-select Dexter + S01E01 on mount.
- **D-02:** The selected series and current `visible_until_order` persist in `sessionStorage` so a page refresh within the same tab restores the last state instead of resetting to empty. Restoring from `sessionStorage` on mount does **not** re-trigger the confirmation modal — the modal only fires on a live, in-session watch-progress change initiated by the user.
- **D-03:** The confirmation modal appears on **every** watch-progress change, not just forward advances — moving backward to re-watch an already-unlocked earlier episode also shows a confirmation step, not just forward unlocks. — **Reversibility:** reversible — purely a client-side gating condition, easy to narrow to forward-only later.

### Graph Rendering
- **D-04:** Add `cytoscape-cose-bilkent` as a new frontend dependency (`frontend/package.json` change) and register it (`cytoscape.use(coseBilkent)`), using `layout: 'cose-bilkent'` as the primary layout per `02-UI-SPEC.md`'s stated preference. Built-in `cose` remains an explicit fallback only if `cose-bilkent` proves unstable in practice during implementation — not a decision to build both paths up front.

### Selection and Detail Panel
- **D-05:** Structural edges (`PART_OF`, `PRECEDES` — no `claim_id`, not evidence-backed) are selectable, same as claim-backed narrative edges. Nothing on the canvas is inert to clicks.
- **D-06:** Structural edges open a distinct, tab-less minimal detail card — not the Overview/Claims/Evidence tabbed `Sheet` used for nodes and claim-backed edges. This is a second, simpler detail-panel layout (e.g., relationship type + the two connected node labels), signaling "not a narrative claim" rather than showing empty/disabled claim/evidence tabs.
- **D-07:** Nodes and claim-backed narrative edges (edges carrying a `claim_id`) both use the existing Overview/Claims/Evidence tabbed `Sheet` layout defined in `02-UI-SPEC.md`.

### API and State Boundary
- **D-08:** No backend/API contract changes of any kind. Use only the three existing endpoints. Watch progress is never persisted server-side in Phase 2 — every graph fetch resends the full `visible_until_order` computed from client state (see D-02).

### Claude's Discretion
- Exact frontend file/component structure (`api/`, `types/`, `hooks/`, `components/{layout,episode,graph,detail}/` as proposed during discussion) — no objection was raised; treat as the intended direction, not a hard lock the planner must reproduce verbatim.
- Exact confirmation-modal copy for **backward** (rewatch) moves. `02-UI-SPEC.md`'s locked copy ("Unlock S01E0X?" / "You're about to see new characters, events, and relationships from S01E0X.") is written for forward-only advances. Since D-03 extends confirmation to backward moves too, the planner/executor must add a backward-move copy variant (same warning-tinted visual treatment, Cancel/confirm button pattern) alongside — not replacing — the existing Copywriting Contract table in `02-UI-SPEC.md`, rather than silently diverging from the locked contract.
- The precise trigger condition for falling back from `cose-bilkent` to `cose` (D-04) is left to the executor's judgment — only fall back on an actual build/runtime failure encountered with the package, not preemptively.
- Series selector stays a genuine interactive `Select` control even though only one series (Dexter) exists today — consistent with D-01's explicit-empty-state choice and forward compatibility with future series.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Phase Requirements
- `ROADMAP.md` (root) — Canonical Prototype v0 product scope, ontology direction, milestones 1–8, one-week execution order (§13), and the Definition of Done demo script (§15) that Phase 2 must support end-to-end for the graph portion.
- `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md` §9 — Frontend visual language, node/origin styling, interaction recommendations, and Cytoscape element mapping example. §8 — Backend API contract shapes. §3.1 — Spoiler filtering must remain backend-authoritative; the frontend must never reintroduce it as a security boundary.
- `.planning/PROJECT.md` — Brownfield facts, core value, constraints, five-phase delivery interpretation.
- `.planning/ROADMAP.md` — Phase 2 goal, requirements (UI-01..05), dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` — Exact Phase 2 requirement text and traceability.

### UI Design Contract (locked visual/copy decisions — do not re-derive)
- `.planning/phases/02-polished-cytoscape-graph-experience/02-UI-SPEC.md` — MANDATORY. Locks the shadcn/Tailwind `radix-nova` dark-theme design system, spacing scale, typography scale, full color palette (including node-type shape mapping and origin border treatment), the complete copywriting contract (empty/error/modal/tab strings), and UI-state coverage (empty/loading/error/populated/partial covered; overflow and long-text held as backstop/unresolved with documented defaults). Checker sign-off checkboxes in the file are currently unchecked, but the content itself is the locked contract for this phase — planner should treat it as final unless a checker re-run flags a specific dimension.

### Backend API Contract (existing, not to be changed)
- `backend/app/api/series.py` — `GET /api/series`, `GET /api/series/{series_id}`, `GET /api/series/{series_id}/episodes`.
- `backend/app/api/graph.py` — `GET /api/series/{series_id}/graph?visible_until_order=N`; 404 `series_not_found`, 422 `invalid_visible_until_order`.
- `backend/app/domain/graph.py` — `GraphNode`, `GraphEdge`, `GraphClaim`, `GraphSource`, `GraphEvidence`, `GraphResponse` shapes the frontend TypeScript types must mirror exactly.
- `backend/app/domain/series.py` — `SeriesResponse`, `EpisodeResponse` shapes.
- `backend/app/core/errors.py` — `{detail: {code, message}}` error shape used by `database_unavailable` / `database_error` (503) responses; the frontend error state must handle this shape generically, not just the 404/422 cases.

### Prior Phase Context
- `.planning/phases/01-backend-graph-foundation/01-CONTEXT.md` — D-05/D-06/D-09: the graph endpoint is intentionally stateless (`visible_until_order` is a query parameter, not persisted server-side); D-06 confirms the response already carries everything Phase 2 needs for detail panels without new endpoints.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/components.json` + `frontend/src/components/ui/*`: 10 shadcn components already installed and themed (`button`, `card`, `dialog`, `select`, `badge`, `separator`, `skeleton`, `alert`, `sheet`, `tabs`) — use these rather than introducing a second component set.
- `frontend/src/lib/utils.ts`: existing `cn()` class-merge helper.
- `cytoscape` + `react-cytoscapejs` + `@types/cytoscape`: already installed; only `cytoscape-cose-bilkent` (D-04) is missing.

### Established Patterns
- TypeScript/React source uses single quotes and no semicolons (per `.planning/codebase/CONVENTIONS.md`); `tsconfig.app.json` enables strict flags (`noUnusedLocals`, `noUnusedParameters`, `verbatimModuleSyntax`, etc.) that will reject unused imports.
- Backend error responses consistently use `{detail: {code, message}}` — the frontend API client should surface both fields, not just a generic message.

### Integration Points
- `frontend/src/App.tsx` / `frontend/src/App.css`: current Vite-starter content (logos, counter button) to be fully replaced, not incrementally edited.
- `frontend/src/main.tsx`: React root entry, imports `App` with explicit `.tsx` extension — leave this wiring pattern intact.
- No API client, hooks, or types directory exists yet — this phase creates them from scratch against the contract in `<canonical_refs>` above.

</code_context>

<specifics>
## Specific Ideas

- The coding-agent spec's Definition of Done (§15) demo script should work end-to-end for the graph portion: open Dexter → set progress to S01E01 → view a graph containing only S01E01 data → click a character/relationship → inspect claim and evidence → attempt to move to S01E02 → see the confirmation modal → confirm and observe newly visible nodes/relationships.
- Target graph density is 8–15 visible nodes per episode (coding-agent spec §9.1) — the `cose-bilkent` layout choice (D-04) should keep this readable, matching `02-UI-SPEC.md`'s "populated" state expectation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 2 scope. (`UserNote` dashed-border node styling and `automatic`-origin system-indicator glyphs are already deferred to Phases 3 and 5 respectively by `02-UI-SPEC.md` itself, not new deferrals from this discussion.)

</deferred>

---

*Phase: 02-polished-cytoscape-graph-experience*
*Context gathered: 2026-07-29*
