<!-- refreshed: 2026-08-26 -->
---
last_mapped: 2026-08-26
focus: arch
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---

# Codebase Structure

**Analysis Date:** 2026-08-26

## Directory Layout

```text
hdgrafcehennemi/
├── spoilerless/
│   ├── app/
│   │   ├── api/             # FastAPI routes, boundary resolver (require_boundary), deps
│   │   ├── cache/           # Redis singleton + graph/visualization cache (focus-set cap 64)
│   │   ├── core/            # Settings (209 lines), uppercase error envelopes, tokens
│   │   ├── domain/          # Pydantic contracts (change_set, user_content nullable user_id)
│   │   ├── graph/           # Neo4j driver, Cypher, ontology, single-query candidate ingest
│   │   ├── llm/             # Provider adapters (OpenAI/Gemini), prompts, system prompt
│   │   ├── repository/      # Neo4j persistence and transaction boundary
│   │   ├── retrieval/       # GraphRAG tool registry, delimiter-neutralized context
│   │   ├── revisions/       # Split package: repository.py, service.py, __init__.py
│   │   ├── services/        # Orchestration (GraphService, auth, chat, rate_limit, visualization/)
│   │   │   └── visualization/ # Decomposed package: service, views, expansion, focus, boundary
│   │   ├── spoiler/         # Visibility policy + spoiler-safe graph-read Cypher
│   │   ├── static/          # Self-hosted character portrait assets (webp)
│   │   └── main.py          # FastAPI entry point (363 lines: body/host middleware, docs gating)
│   ├── scripts/             # smoke.sh and zombie_sweep.py
│   └── tests/               # pytest backend suite (53 modules, 23.4k lines)
├── frontend/
│   ├── public/               # Vite-served static assets
│   ├── src/
│   │   ├── api/              # Typed REST and SSE clients (incl. projection/expansion)
│   │   ├── assets/           # Imported images
│   │   ├── components/       # Feature and UI React components
│   │   │   ├── auth/         # Login and authentication controls
│   │   │   ├── chat/         # Streaming chat panel and collapsible ChatSheet
│   │   │   ├── detail/       # Decomposed DetailPanel, CharacterPortrait, and tabs/
│   │   │   │   └── tabs/     # OverviewTab, ClaimsTab, EvidenceTab, NotesTab
│   │   │   ├── dialogs/      # CreateCustomNodeDialog, CreateRelationshipDialog
│   │   │   ├── graph/        # GraphCanvas, useCytoscapeLayout, cytoscapeReconciler
│   │   │   ├── layout/       # AppIcons, ResizableRail
│   │   │   ├── series/       # SeriesDashboard, SeriesSelect, EpisodeSelector
│   │   │   ├── share/        # ShareView and snapshot cards
│   │   │   └── ui/           # Reusable Radix/shadcn primitives
│   │   ├── hooks/            # useWorkspaceScene, useWorkspaceNavigation, useSceneState, etc.
│   │   ├── lib/              # Adapters, search index, byok, tokens/, and graph/ helpers
│   │   │   ├── graph/        # sceneElements.ts, positionCache.ts, highlight.ts
│   │   │   └── tokens/       # graphTokens.ts (centralized styling tokens)
│   │   ├── providers/        # Auth context/provider/hook
│   │   ├── test/             # Vitest setup and shared fixtures
│   │   ├── types/            # Wire/UI contracts aligned with backend domain models
│   │   ├── App.tsx           # Decomposed SPA composition (291 lines)
│   │   └── main.tsx          # Browser mount entry
│   ├── package.json          # npm scripts and dependencies
│   ├── vite.config.ts        # React/Tailwind/Vitest and /api proxy
│   └── vercel.json           # SPA rewrite + security headers (CSP, HSTS, nosniff, DENY)
├── data/dexter/
│   ├── metadata/             # Series and episode JSON
│   ├── seed/                 # Canonical graph JSON
│   └── test/                 # Extraction fixture JSON
├── ontology/                 # Versioned graph vocabulary YAML
├── docs/                     # Product/reference documentation
├── .planning/                # GSD state, milestones, research, codebase map
├── .agents/skills/hdgrafcehennemi/  # Project runbook + references
├── .github/workflows/         # GitHub Actions CI and release
├── docker-compose.yml        # Neo4j service (neo4j:2026.06.0-community)
├── render.yaml               # Render Blueprint (free-tier API)
├── pyproject.toml            # Python package, setup CLI, pytest config
├── uv.lock                   # Locked Python dependency graph
├── LICENSE                   # MIT license
├── README.md                 # Product and local-development overview
└── ROADMAP.md                # Canonical product roadmap and milestone tracking
```

## Directory Purposes

**`spoilerless/app/api/`:**
- Purpose: Define the public FastAPI boundary and enforce spoiler/host/body gates before handlers.
- Contains: Route modules (auth, series, graph, user content, revisions, candidates, progress, chat, change sets, settings, share), shared boundary dependency (`boundary.py` with `resolve_effective_boundary` and `require_boundary`), dependency helpers (`deps.py`), and repository error-handler installation (`exceptions.py`).
- Key files: `spoilerless/app/api/boundary.py`, `spoilerless/app/api/deps.py`, `spoilerless/app/api/graph.py`, `spoilerless/app/api/candidates.py`, `spoilerless/app/api/user_content.py`, `spoilerless/app/api/revisions.py`.
- Placement rule: Add one route module per resource; register in `spoilerless/app/main.py`; use `require_boundary` dependency for spoiler-sensitive routes; keep business logic in `services/`.

**`spoilerless/app/core/`:**
- Purpose: Process-wide configuration and transport-level error policies.
- Contains: Pydantic `Settings` (`config.py`, 209 lines), exception handlers and uppercase error envelope registry (`errors.py`), token generation (`tokens.py`).
- Key files: `spoilerless/app/core/config.py`, `spoilerless/app/core/errors.py`.
- Placement rule: Cross-cutting configuration, environment resolution, and HTTP error envelopes belong here.

**`spoilerless/app/domain/`:**
- Purpose: Define strict contracts shared across backend layers.
- Contains: Pydantic models for auth, graph, series, user content (with nullable `user_id` on responses for privacy scrubbing), extraction, revisions, progress, chat, ChangeSets (`change_set.py` with `ProposeChangesetInput` and 20-op cap), settings (`settings.py` with 1.0s DNS timeout for SSRF validation), and visualization DTOs (`visualization.py`).
- Key files: `spoilerless/app/domain/user_content.py`, `spoilerless/app/domain/change_set.py`, `spoilerless/app/domain/visualization.py`, `spoilerless/app/domain/settings.py`.
- Placement rule: Define data contracts here before wiring endpoints. Keep request/response schemas aligned with frontend TypeScript interfaces.

**`spoilerless/app/services/`:**
- Purpose: Coordinate business workflows and domain orchestration across repositories.
- Contains: `GraphService` (`graph.py` facade), `AuthService` (`auth.py` with `warn_if_open_signup`), `ChatService` (`chat.py` with semaphore), `ChangeSetService` (`change_set.py`), `ProgressService` (`progress.py`), `RateLimiter` (`rate_limit.py` with lazy re-init), `RevisionService` (`revisions/service.py`), and `VisualizationProjectionService` in decomposed package `spoilerless/app/services/visualization/`.
- Key files: `spoilerless/app/services/graph.py`, `spoilerless/app/services/rate_limit.py`, `spoilerless/app/services/visualization/service.py`.
- Placement rule: Business orchestration and cross-repository coordination belong in services. Keep individual service modules focused under 300 lines.

**`spoilerless/app/services/visualization/` (decomposed package):**
- Purpose: Modular visualization projection, semantic expansion, focus calculation, and view builders.
- Contains: `service.py` (`VisualizationProjectionService`), `views.py` (view-specific projectors: overview, character network, plot threads, investigation, full), `expansion.py` (expansion deltas for 7 semantic keys), `focus.py` (GraphRAG focus subgraph), `boundary.py` (boundary validation), `node_builders.py` (node DTO formatting), `constants.py` (view limits, edge types, palettes), and `__init__.py`.
- Placement rule: Presentation projection logic belongs here. Do not re-merge into a monolithic file.

**`spoilerless/app/revisions/` (split package):**
- Purpose: Append-only revision logging and safe ownership-checked revert.
- Contains: `repository.py` (`RevisionRepository`), `service.py` (`RevisionService`), and `__init__.py` facade re-exporting public API.
- Placement rule: Revision persistence lives in `repository.py`, business rules and ownership verification live in `service.py`.

**`spoilerless/app/repository/`:**
- Purpose: Neo4j commands, user scoping, managed transactions, and row normalization.
- Contains: Repositories for users, sessions, user content, progress, chat, settings, ChangeSets, share tokens.
- Key files: `spoilerless/app/repository/user_content.py`, `spoilerless/app/repository/change_set.py`, `spoilerless/app/repository/session.py`.
- Placement rule: Database queries and transaction management belong here. Keep query constants close to usage.

**`spoilerless/app/graph/`:**
- Purpose: Graph infrastructure, driver lifecycle, ontology, and feature Cypher.
- Contains: `database.py` (async driver lifecycle), `ontology.py`, `seed.py`, `setup.py`, `candidates.py` (candidate ingest with single-roundtrip Cypher checks).
- Key files: `spoilerless/app/graph/database.py`, `spoilerless/app/graph/candidates.py`, `spoilerless/app/graph/seed.py`.
- Placement rule: Core Cypher queries, seed setup, and graph database lifecycle belong here.

**`spoilerless/app/spoiler/`:**
- Purpose: Spoiler visibility policy and core graph-read Cypher fragments.
- Contains: `filter.py` (Cypher fragment builders), `policy.py` (`effective_view_order`, `is_visible`), `visibility.py` (derived visibility rules).
- Key files: `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py`.
- Placement rule: Visibility logic and boundary math belong here. Never relax visibility gating.

**`frontend/src/components/`:**
- Purpose: Feature components and UI elements decomposed by domain.
- Contains:
  - `auth/`: `LoginPage.tsx`
  - `chat/`: `ChatPanel.tsx`, `ChatSheet.tsx` (using `ResizableRail`), `ChatMessageList.tsx`
  - `detail/`: `DetailPanel.tsx` (180 lines), `CharacterPortrait.tsx`, `RevisionHistoryPanel.tsx`, and `tabs/` (`OverviewTab.tsx`, `ClaimsTab.tsx`, `EvidenceTab.tsx`, `NotesTab.tsx`)
  - `dialogs/`: `CreateCustomNodeDialog.tsx`, `CreateRelationshipDialog.tsx`
  - `graph/`: `GraphCanvas.tsx` (426 lines), `GraphFilterPanel.tsx`, `PathFinder.tsx`, `AnswerGraph.tsx`, `GraphFocusIndicator.tsx`, `useCytoscapeLayout.ts`, `cytoscapeReconciler.ts`
  - `layout/`: `AppIcons.tsx`, `ResizableRail.tsx`
  - `series/`: `SeriesDashboard.tsx`, `SeriesSelect.tsx`, `EpisodeSelector.tsx`
  - `share/`: `ShareView.tsx`
  - `ui/`: Reusable Radix/shadcn primitives (dialog, button, input, sheet, tabs, select, etc.)
- Placement rule: Keep components focused under 400 lines; extract sub-views into tabs or dialogs; isolate layout mechanics into custom hooks.

**`frontend/src/hooks/`:**
- Purpose: React custom hooks for state management and async data fetching.
- Contains: `useWorkspaceScene.ts` (scene orchestration, view fetching, expansion), `useWorkspaceNavigation.ts` (mode and tab navigation), `useSceneState.ts` (serializable scene reducer), `useGraph.ts`, `useWatchProgress.ts`, `useNotes.ts`, `useRevisions.ts`, `useCandidates.ts`, `useChatMessages.ts`, `useShareToken.ts`.
- Placement rule: Async workflows and multi-step UI state belong in custom hooks, not inline component bodies.

**`frontend/src/lib/`:**
- Purpose: Shared utility functions, adapters, design tokens, and search indices.
- Contains: `visualizationAdapter.ts`, `byok.ts`, `searchIndex.ts`, `nodeTypes.ts`, `tokens/graphTokens.ts` (centralized design tokens), `graph/sceneElements.ts` (element construction), `graph/positionCache.ts` (layout coordinates cache), `graph/highlight.ts`.
- Placement rule: Pure functions, formatters, tokens, and data adapters belong in `lib/`.

## Key File Locations

| File | Purpose | Lines |
|------|---------|-------|
| `frontend/src/App.tsx` | Decomposed SPA composition root | 291 |
| `frontend/src/hooks/useWorkspaceScene.ts` | Workspace scene orchestration | 217 |
| `frontend/src/components/graph/GraphCanvas.tsx` | Decomposed Cytoscape canvas container | 426 |
| `frontend/src/components/graph/useCytoscapeLayout.ts` | Cytoscape layout lifecycle hook | 197 |
| `frontend/src/components/graph/cytoscapeReconciler.ts` | Declarative-to-imperative Cytoscape diffing | 126 |
| `frontend/src/components/detail/DetailPanel.tsx` | Decomposed detail inspector panel | 180 |
| `frontend/src/lib/graph/sceneElements.ts` | Unified Cytoscape element builder | 242 |
| `frontend/src/lib/tokens/graphTokens.ts` | Centralized graph styling tokens | 57 |
| `spoilerless/app/main.py` | FastAPI application entry point and middleware | 363 |
| `spoilerless/app/api/boundary.py` | Central fail-closed spoiler boundary resolver | 74 |
| `spoilerless/app/services/graph.py` | GraphService facade for reads & invalidation | 51 |
| `spoilerless/app/services/visualization/service.py` | Visualization projection service entry | 180 |
| `spoilerless/app/services/rate_limit.py` | Resilient Redis-backed rate limiter | 165 |
| `spoilerless/app/revisions/service.py` | Revision management and revert service | 203 |
| `spoilerless/app/graph/candidates.py` | Candidate extraction Cypher queries | 290 |

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **Frontend God-File Decomposition:**
  - Monolithic `App.tsx` (~900 lines) decomposed into `App.tsx` (291 lines), `useWorkspaceScene.ts`, `useWorkspaceNavigation.ts`, `AppIcons.tsx`, `ResizableRail.tsx`.
  - Monolithic `GraphCanvas.tsx` (~700 lines) decomposed into `GraphCanvas.tsx` (426 lines), `useCytoscapeLayout.ts`, `CreateCustomNodeDialog.tsx`.
  - Monolithic `DetailPanel.tsx` (~750 lines) decomposed into `DetailPanel.tsx` (180 lines), `tabs/OverviewTab.tsx`, `tabs/ClaimsTab.tsx`, `tabs/EvidenceTab.tsx`, `tabs/NotesTab.tsx`, `CharacterPortrait.tsx`, `CreateRelationshipDialog.tsx`.
- **New Frontend Helper Packages:**
  - `frontend/src/lib/graph/sceneElements.ts` (242 lines) and `frontend/src/lib/graph/positionCache.ts` (37 lines).
  - `frontend/src/lib/tokens/graphTokens.ts` (57 lines).
- **Backend Modularization:**
  - Monolithic `spoilerless/app/services/visualization.py` (1,173 lines) broken into `spoilerless/app/services/visualization/` package (8 modules).
  - Monolithic `spoilerless/app/revisions/__init__.py` (341 lines) split into `repository.py`, `service.py`, and `__init__.py`.
  - Added `spoilerless/app/services/graph.py` facade.
  - Enhanced `spoilerless/app/api/boundary.py` with `require_boundary` dependency.
- **Removed Legacy / Dead Files:**
  - `frontend/src/components/graph/filterState.ts` and `frontend/src/components/graph/focusReducer.ts` removed (superseded by `useSceneState.ts` and `sceneElements.ts`).

---

*Structure analysis: 2026-08-26*
