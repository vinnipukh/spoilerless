# Phase 09 Plan 11 Summary — Relationship Finder & Markdown Export (FEAT-05, FEAT-06)

## Overview

Plan 11 implemented the relationship finder (FEAT-06) and Markdown export (FEAT-05) features end-to-end across backend and frontend, sharing the same spoiler-safe read path (`fetch_graph`), thin API routes, and Cytoscape canvas framing affordances.

- **Backend:** `POST /api/series/{series_id}/graph/path` (allowlisted `find_path` executor with server-resolved boundary, capped `max_hops=4`) and `GET /api/series/{series_id}/export` (rendering Markdown directly from `fetch_graph`).
- **Frontend PathFinder (FEAT-06):** Two-node path mode overlay chip ("Select first node…", "Select second node…", "4 hops · 5 nodes", no-path Alert), `.on-path`/`.path-source`/`.path-target` Cytoscape styling with `.faded` backdrop and `cy.fit(path, 48)` framing.
- **Frontend Markdown Export (FEAT-05):** Zero-dep Blob download via `URL.createObjectURL` for per-resource export (ghost button in `DetailPanel` header) and whole-graph export (Download icon button in `GraphControls` bottom-left stack). Pure client-side assembler `exportMarkdown.ts` provided as offline fallback.

---

## Tasks Completed

| Task | Description | Status | Commit |
|------|-------------|--------|--------|
| Task 1 | Backend routes — Markdown export (`GET /export`) + shortest path (`POST /graph/path`) | Completed | `feat(09-11): export Markdown + shortest-path routes (FEAT-05/06 backend)` (`231f724`) |
| Task 2 | PathFinder mode (FEAT-06 frontend) — two-node selection + Cytoscape highlight | Completed | `feat(09-11): path finder mode (FEAT-06)` (`a602d14`) |
| Task 3 | Markdown export frontend (FEAT-05) — buttons + zero-dep Blob download | Completed | `feat(09-11): Markdown export UI + Blob download (FEAT-05)` (`da125a4`) |

---

## Verification & Key Invariants

1. **Backend Tests:**
   - `uv run pytest spoilerless/tests/test_graph_api.py -k "path or export" -v`: 6/6 passed cleanly (`test_path_route_finds_shortest_visible_path`, `test_path_route_unconnected_pair_returns_no_path`, `test_path_route_rejects_max_hops_above_ceiling`, `test_export_returns_markdown_with_visible_content`, `test_export_target_id_renders_resource_section`, `test_export_unknown_series_returns_404`).
2. **Frontend Tests & Build:**
   - `npm run test -- src/components/graph/PathFinder.test.tsx`: 5/5 passed.
   - `npm run test -- src/api/export.test.ts`: 5/5 passed.
   - `npm run build`: Success (0 TypeScript errors).
   - `npm run lint`: Success (0 ESLint errors, 0 warnings).

3. **Key Invariants & Constraints Enforced:**
   - **NO-FORKED-FILTER:** Both new backend routes resolve effective boundaries server-side using the exact same `_resolve_effective_boundary` helper and read graph state via `fetch_graph` — zero duplicate filtering code paths.
   - **NO-PDF:** Markdown only; zero new dependencies added (no `jspdf`, no `fuse.js`).
   - **NO-LIVE-LLM:** `POST /graph/path` invokes the allowlisted BFS executor directly without an LLM tool loop.

---

## Artifacts Produced / Modified

- `spoilerless/app/api/graph.py` — `POST /graph/path` and `GET /export` endpoints.
- `spoilerless/tests/test_graph_api.py` — Contract tests for path finding and Markdown export.
- `frontend/src/types/graph.ts` — `PathResponse` type definition.
- `frontend/src/api/graph.ts` — `findPath` client API helper.
- `frontend/src/api/export.ts` — `fetchExportMarkdown` and `downloadMarkdownBlob` client helpers.
- `frontend/src/lib/exportMarkdown.ts` — Client-side fallback Markdown renderer and filename slugifier.
- `frontend/src/components/graph/PathFinder.tsx` — Two-node selection overlay component.
- `frontend/src/components/graph/graphStylesheet.ts` — Styles for `.path-source`, `.path-target`, and `.on-path`.
- `frontend/src/components/graph/GraphCanvas.tsx` — Path-mode tap handlers and export handler integration.
- `frontend/src/components/graph/GraphControls.tsx` — "Show path" (Waypoints icon) and "Export Markdown" (Download icon) buttons.
- `frontend/src/components/detail/DetailPanel.tsx` — Per-resource "Export Markdown" header button.
- `frontend/src/components/graph/PathFinder.test.tsx` — Unit test suite for PathFinder mode.
- `frontend/src/api/export.test.ts` — Unit test suite for export API and Blob downloader.
