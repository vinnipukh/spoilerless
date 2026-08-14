---
last_mapped: 2026-08-14
focus: arch
last_mapped_commit: 5bd1641
---
<!-- refreshed: 2026-08-14 (covers HEAD 5bd1641 plus uncommitted working-tree changes) -->
# Codebase Structure

**Analysis Date:** 2026-08-14

## Directory Layout

```text
hdgrafcehennemi/
├── spoilerless/
│   ├── app/
│   │   ├── api/             # FastAPI route modules and dependencies
│   │   ├── cache/           # Redis client singleton, graph + visualization cache
│   │   ├── core/            # Environment settings, error envelopes, token helpers
│   │   ├── domain/          # Pydantic request/response/business contracts
│   │   ├── graph/           # Neo4j driver, Cypher, ontology, labels, seed/setup
│   │   ├── llm/             # Provider adapters, prompts, safe fallbacks
│   │   ├── repository/      # Neo4j persistence and transaction boundary
│   │   ├── retrieval/       # GraphRAG tool registry, context sections, grounding
│   │   ├── revisions/       # Revision repository implementation
│   │   ├── services/        # Business workflow orchestration
│   │   ├── spoiler/         # Visibility policy and spoiler-safe graph-read Cypher
│   │   ├── static/          # Self-hosted character portrait assets (webp)
│   │   └── main.py          # FastAPI application entry point
│   ├── scripts/             # smoke.sh and zombie_sweep.py
│   └── tests/               # pytest backend suite (52 modules)
├── frontend/
│   ├── public/               # Vite-served static assets
│   ├── src/
│   │   ├── api/              # Typed REST and SSE clients (incl. projection fetches)
│   │   ├── assets/           # Imported images, including template residue
│   │   ├── components/       # Feature and UI React components
│   │   ├── hooks/            # Async data/state hooks + scene-state reducer
│   │   ├── lib/              # Shared frontend utilities incl. visualizationAdapter
│   │   ├── providers/        # Authentication context/provider/hook
│   │   ├── test/             # Vitest setup and shared fixtures
│   │   ├── types/            # TypeScript wire/UI contracts incl. VisualizationDTO
│   │   ├── App.tsx           # SPA composition and top-level state
│   │   └── main.tsx          # Browser mount entry
│   ├── package.json          # npm scripts and dependencies
│   └── vite.config.ts        # React/Tailwind/Vitest and `/api` proxy
├── data/dexter/
│   ├── metadata/             # Series and episode JSON
│   ├── seed/                 # Canonical graph JSON
│   └── test/                 # Extraction fixture JSON
├── ontology/                 # Versioned graph vocabulary YAML
├── docs/                     # Product/reference documentation
├── .planning/                # GSD state, milestones, research, codebase map
├── .github/workflows/         # GitHub Actions CI and release pipelines
├── docker-compose.yml        # Neo4j service and persistent volumes
├── render.yaml               # Render Blueprint (free-tier API web service)
├── pyproject.toml            # Python package, setup CLI, pytest config
├── uv.lock                   # Locked Python dependency graph
├── run_verification.py       # Root doc-claim verification (untracked)
├── run_doc_verification.py   # Root doc-claim verification (untracked)
├── verify_all_claims.py      # Root doc-claim verification (untracked)
├── verify_arch.py            # Root doc-claim verification (untracked)
├── LICENSE                   # MIT license
├── README.md                 # Product and local-development overview
└── ROADMAP.md                # Canonical product scope; not implementation proof
```

## Directory Purposes

**`spoilerless/app/api/`:**
- Purpose: Define the public FastAPI boundary.
- Contains: Eleven router modules (auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, settings, share) plus shared auth/database dependencies (`deps.py`) and repository error-handler installation (`exceptions.py`). The graph router gained the Phase-10 projection routes `GET .../graph/visualization` and `GET .../graph/expand` (`spoilerless/app/api/graph.py`).
- Key files: `spoilerless/app/api/deps.py`, `spoilerless/app/api/graph.py`, `spoilerless/app/api/chat.py`, `spoilerless/app/api/change_set.py`, `spoilerless/app/api/share.py`, `spoilerless/app/api/exceptions.py`.
- Placement rule: Add one route module per resource/feature and register its router in `spoilerless/app/main.py`; keep business logic in `spoilerless/app/services/`.

**`spoilerless/app/core/`:**
- Purpose: Hold process-wide configuration and transport-level error policy.
- Contains: Pydantic settings, exception-handler/error-envelope helpers, and token generation (`spoilerless/app/core/tokens.py`).
- Key files: `spoilerless/app/core/config.py`, `spoilerless/app/core/errors.py`.
- Placement rule: Put cross-feature configuration or HTTP error infrastructure here, not feature persistence.

**`spoilerless/app/domain/`:**
- Purpose: Define strict contracts shared across backend layers.
- Contains: Pydantic models and enums for auth, graph, series, user content, extraction, revisions, progress, chat, ChangeSets, settings, and the library-neutral visualization DTOs (`visualization.py`: `VisualizationDTO`, `VIEW_TYPES`, `EXPANSION_KEYS`, `PROJECTION_VERSION`).
- Key files: `spoilerless/app/domain/graph.py`, `spoilerless/app/domain/change_set.py`, `spoilerless/app/domain/chat.py`, `spoilerless/app/domain/visualization.py`.
- Placement rule: Add request/response/domain types here before wiring API/service/repository code; forbid extra fields when the existing contract does.

**`spoilerless/app/services/`:**
- Purpose: Coordinate business workflows and enforce rules spanning repositories.
- Contains: Feature classes for series, graph, auth, progress, chat, ChangeSets, settings, Redis-backed rate limiting, and the Phase-10 `VisualizationService` (`visualization.py`, 1,173 lines) producing boundary-checked projections and expansion deltas from complete safe graph detail.
- Key files: `spoilerless/app/services/graph.py`, `spoilerless/app/services/chat.py`, `spoilerless/app/services/change_set.py`, `spoilerless/app/services/rate_limit.py`, `spoilerless/app/services/visualization.py`.
- Placement rule: Put orchestration here; do not call `tx.run()` from services when the transaction belongs in a repository callback.

**`spoilerless/app/repository/`:**
- Purpose: Own user scoping, Neo4j commands, managed transactions, and row normalization.
- Contains: Users, sessions, user content, progress, chat, settings, ChangeSet, and share-token repositories.
- Key files: `spoilerless/app/repository/user_content.py`, `spoilerless/app/repository/change_set.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`.
- Placement rule: Add persistence code here and keep query constants in the owning `spoilerless/app/graph/` module unless a tightly scoped repository query follows the established local pattern.

**`spoilerless/app/cache/`:**
- Purpose: Own the single Redis connection and the cache-aside graph/visualization response caches.
- Contains: `redis_client.py` (shared `redis.asyncio` singleton), `graph_cache.py` (boundary-aware graph keys plus Phase-10 visualization keys over series, effective order, user scope, view, projection version, and focus signature via `get_cached_visualization`/`set_cached_visualization`). Any Redis failure degrades to querying Neo4j.
- Key files: `spoilerless/app/cache/redis_client.py`, `spoilerless/app/cache/graph_cache.py`.
- Placement rule: Never construct a second `redis.asyncio` client; guard every Redis call on a non-empty `REDIS_URL`. Do not add caching to the expansion path (T10-CACHE-06).

**`spoilerless/app/graph/`:**
- Purpose: Provide graph infrastructure and feature-specific Cypher.
- Contains: Async driver lifecycle, ontology loading, seed/setup, candidate queries, label inventories, and progress/chat/ChangeSet queries.
- Key files: `spoilerless/app/graph/database.py`, `spoilerless/app/graph/ontology.py`, `spoilerless/app/graph/seed.py`, `spoilerless/app/graph/setup.py`.
- Placement rule: Add parameterized query modules by feature; interpolate only server-controlled labels/types selected from ontology allowlists.

**`spoilerless/app/spoiler/`:**
- Purpose: Isolate spoiler visibility rules and the core spoiler-safe graph response queries.
- Contains: Claim-visibility fragment builders and graph-response Cypher (`filter.py`), the effective-boundary rule (`policy.py`), and the single derived-visibility rule (`visibility.py`). `policy.py` also exposes `is_visible`/`resolve_effective_boundary`/`validate_visibility_order` reused by `VisualizationService`.
- Key files: `spoilerless/app/spoiler/filter.py`, `spoilerless/app/spoiler/policy.py`, `spoilerless/app/spoiler/visibility.py`.
- Placement rule: Put graph-response visibility changes here and enforce the boundary on every traversed story-sensitive entity.

**`spoilerless/app/retrieval/`:**
- Purpose: Expose a bounded, typed GraphRAG read surface to the LLM.
- Contains: Twelve retrieval tools registered in one `TOOL_SPECS` list, input models, a shared context-section registry, and citation validation.
- Key files: `spoilerless/app/retrieval/tools.py`, `spoilerless/app/retrieval/pipeline.py`, `spoilerless/app/retrieval/context.py`.
- Placement rule: Add a retrieval capability as a typed allowlisted tool, inject authority parameters server-side, and include its returned IDs in grounding validation.

**`spoilerless/app/llm/`:**
- Purpose: Isolate external model-provider behavior and prompt policy.
- Contains: `LLMProvider` protocol, Gemini/OpenAI-compatible adapters, localized fallbacks, and large system-prompt prose.
- Key files: `spoilerless/app/llm/provider.py`, `spoilerless/app/llm/fallbacks.py`, `spoilerless/app/llm/system_prompt.py`.
- Placement rule: Add provider implementations against `LLMProvider`; do not mix graph querying or writes into adapters. Treat `spoilerless/app/llm/system_prompt.py` as user-owned prompt content rather than ordinary refactor material.

**`spoilerless/app/revisions/`:**
- Purpose: Create append-only audit records inside caller-owned Neo4j transactions.
- Contains: `RevisionRepository`, snapshot/JSON helpers, and revision-create Cypher directly in `spoilerless/app/revisions/__init__.py`.
- Key files: `spoilerless/app/revisions/__init__.py`.
- Placement rule: Reuse `RevisionRepository.log_revision()` for mutations; put additional revision modules in named files rather than expanding the package initializer.

**`spoilerless/app/static/`:**
- Purpose: Serve self-hosted product images through the `/api/static` mount registered in `spoilerless/app/main.py`.
- Contains: Character portrait `.webp` files under `spoilerless/app/static/characters/`; seed `image_url` values are relative (`/api/static/characters/<id>.webp`) and pass the CSP `img-src 'self'` rule.
- Placement rule: Keep media referenced by seed content here (never external CDNs); add a file per asset and reference it with a relative URL.

**`spoilerless/tests/`:**
- Purpose: Verify backend contracts, graph boundaries, persistence, retrieval, prompt safety, ChangeSets, and Phase-10 visualization projections.
- Contains: 52 pytest modules and shared fixtures — including the `NoopGoogleVerifier` test double, scratch-series isolation helpers (`spoilerless/tests/conftest.py`), and `spoilerless/tests/fixtures/visualization/` (safe projection fixtures `s01e01_safe.json`, `s01e02_cumulative_safe.json`).
- Key files: `spoilerless/tests/test_graph_api.py` (1,268+ lines), `spoilerless/tests/test_retrieval_tools.py` (1,280), `spoilerless/tests/test_error_handlers.py`, `spoilerless/tests/test_google_verifier.py`, `spoilerless/tests/test_change_set_api.py`, `spoilerless/tests/test_visualization_projection.py` (1,711), `spoilerless/tests/test_visualization_baseline.py` (752), `spoilerless/tests/test_visualization_cache.py` (393), `spoilerless/tests/test_visualization_graphrag.py` (267), `spoilerless/tests/test_phase10_coverage_audit.py`, `spoilerless/tests/test_phase10_test_runner.py`.
- Placement rule: Add `test_<feature>.py` here; use dependency overrides/fake providers rather than external LLM calls.

**`frontend/src/api/`:**
- Purpose: Convert typed frontend operations to backend HTTP calls.
- Contains: One client module per backend feature, plus the shared fetch wrapper. `graph.ts` adds the Phase-10 `fetchVisualization()` and `fetchExpansion()` calls beside `getGraph()` and `findPath()`.
- Key files: `frontend/src/api/client.ts`, `frontend/src/api/chat.ts`, `frontend/src/api/changeSet.ts`, `frontend/src/api/graph.ts`.
- Placement rule: Add feature calls here; use `apiFetch()` for JSON and preserve `credentials: 'include'` in specialized streaming transports.

**`frontend/src/hooks/`:**
- Purpose: Encapsulate async state and feature-specific browser behavior.
- Contains: The shared `useFetchState` state machine, hooks for series, episodes, graph, progress, notes, revisions, chat sessions/messages, and the serializable graph-workspace scene reducer `useSceneState.ts` (view, filters, selection, focus, camera, positions, expansions, timeline, Inspector).
- Key files: `frontend/src/hooks/useFetchState.ts`, `frontend/src/hooks/useGraph.ts`, `frontend/src/hooks/useWatchProgress.ts`, `frontend/src/hooks/useChatMessages.ts`, `frontend/src/hooks/useChatSessions.ts`, `frontend/src/hooks/useSceneState.ts`.
- Placement rule: Put reusable fetch/state machines here and keep visual rendering in `frontend/src/components/`.

**`frontend/src/components/`:**
- Purpose: Render the product UI by feature.
- Contains: `auth/`, `chat/`, `detail/`, `episode/`, `graph/`, `layout/`, `palette/`, `series/`, `settings/`, `share/`, `timeline/`, and reusable `ui/` primitives. The `graph/` folder holds the canvas, controls, filter panel, legend, search, hover card, focus indicator, Answer Graph surface, layout config, stylesheets, the topology-aware reconciler (`cytoscapeReconciler.ts`), and co-located tests.
- Key files: `frontend/src/components/detail/DetailPanel.tsx`, `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/graph/cytoscapeReconciler.ts`, `frontend/src/components/graph/AnswerGraph.tsx`, `frontend/src/components/chat/ChatPanel.tsx`.
- Placement rule: Place domain components in their feature folder; add generic shadcn/Radix wrappers only to `frontend/src/components/ui/`.

**`frontend/src/lib/`:**
- Purpose: Hold non-visual frontend helpers, including the DTO→Cytoscape bridge.
- Contains: `visualizationAdapter.ts` (`toCytoscapeElements()` converts `VisualizationDTO` to element definitions, with co-located `visualizationAdapter.test.ts`), export-Markdown helpers, node-type maps, highlight logic, BYOK storage helpers, and graph filters.
- Placement rule: Put library-neutral conversion/utility code here; keep components visual and hooks stateful.

**`frontend/src/providers/` and `frontend/src/types/`:**
- Purpose: Provide cross-tree auth state and shared TypeScript contracts.
- Contains: Split auth context/provider/hook files and backend-mirroring interfaces, including the Phase-10 `VisualizationDTO`, `VisualizationViewType`, and `ExpansionKey` wire types in `frontend/src/types/graph.ts`.
- Key files: `frontend/src/providers/AuthProvider.tsx`, `frontend/src/providers/AuthContext.ts`, `frontend/src/types/graph.ts`, `frontend/src/types/changeSet.ts`, `frontend/src/types/share.ts`.
- Placement rule: Mirror wire-contract changes in `frontend/src/types/`; reserve providers for genuinely cross-tree state.

**`data/dexter/` and `ontology/`:**
- Purpose: Supply deterministic prototype content and the accepted graph vocabulary.
- Contains: JSON metadata/seed/fixtures and YAML node/relation/claim definitions.
- Key files: `data/dexter/metadata/episodes.json`, `data/dexter/seed/claims.json`, `ontology/relation_types.yaml`.
- Placement rule: Add content under a series-specific data directory and update ontology only for legitimate new graph types; validate through `spoilerless/app/graph/seed.py`.

**Root doc-verification scripts (untracked):**
- Purpose: Verify claims in `docs/ARCHITECTURE.md` against the live repository (file existence, dependency versions, code patterns).
- Contains: `run_verification.py` (420 lines), `run_doc_verification.py` (429), `verify_all_claims.py` (418), and `verify_arch.py` (68) — standalone scripts that parse the doc line-by-line, evaluate each claim with a check function, and emit a pass/fail list with the expected vs. actual value. They hard-code the repo root (`C:\Users\arhan\PycharmProjects\hdgrafcehennemi`) and are not part of the Python package.
- Placement rule: Extend these scripts when adding claim-bearing statements to `docs/ARCHITECTURE.md`; they are workspace tooling, not package code.

## Key File Locations

**Entry Points:**
- `spoilerless/app/main.py`: Production FastAPI ASGI application.
- `spoilerless/app/graph/setup.py`: `spoilerless-setup` database bootstrap CLI.
- `frontend/src/main.tsx`: React browser mount.
- `frontend/src/App.tsx`: Product composition root; state-driven graph/settings navigation; Overview vs. Full narrative workspace (`graphMode`).

**Configuration:**
- `pyproject.toml`: Python version/dependencies, CLI registration, pytest path.
- `frontend/package.json`: npm development/build/lint/test scripts (adds `cytoscape-dagre` 4.0.0 and `@types/cytoscape-dagre`).
- `frontend/vite.config.ts`: React/Tailwind plugins, `@` alias, `/api` proxy, Vitest setup.
- `frontend/tsconfig.app.json`: Frontend TypeScript compiler settings.
- `docker-compose.yml`: Neo4j container/volume configuration.
- `render.yaml`: Render Blueprint for the free-tier API web service (auto-deploy on push).
- `.github/workflows/ci.yml` and `.github/workflows/release.yml`: GitHub Actions CI and release pipelines.
- `LICENSE`: MIT license (Spoilerless Team).
- `.env.example`, `frontend/.env.example`: Configuration templates; do not put secrets in tracked files.

**Core Logic:**
- `spoilerless/app/spoiler/filter.py`: Canonical spoiler-safe graph-read queries.
- `spoilerless/app/services/graph.py`: Concurrent graph assembly and claim-edge projection.
- `spoilerless/app/services/visualization.py`: Boundary-checked visualization projections and expansion deltas (Phase 10).
- `spoilerless/app/domain/visualization.py`: Library-neutral `VisualizationDTO` contract, view vocabulary, expansion allowlist.
- `spoilerless/app/cache/graph_cache.py`: Cache-aside graph and visualization responses with boundary/version/focus-aware keys.
- `spoilerless/app/retrieval/pipeline.py`: GraphRAG orchestration, context bounds, grounding.
- `spoilerless/app/retrieval/tools.py`: Allowlisted Neo4j retrieval operations.
- `spoilerless/app/repository/change_set.py`: Transactional ChangeSet apply/reject/revert via the table-driven `_APPLY_SPECS` dispatch.
- `spoilerless/app/api/share.py`: Token-based read-only share links.
- `frontend/src/hooks/useSceneState.ts`: Serializable graph-workspace scene reducer (D-24).
- `frontend/src/lib/visualizationAdapter.ts`: `VisualizationDTO` → Cytoscape element conversion.
- `frontend/src/components/graph/cytoscapeReconciler.ts`: Topology-aware imperative scene reconciliation.
- `frontend/src/components/detail/DetailPanel.tsx`: Main inspector/editing surface.
- `frontend/src/components/graph/GraphCanvas.tsx`: Cytoscape rendering and interaction.

**Testing:**
- `spoilerless/tests/conftest.py`: Backend fixtures, the shared `NoopGoogleVerifier`, and scratch-series isolation helpers.
- `spoilerless/tests/test_openapi_contract.py`: API operation/contract verification.
- `spoilerless/tests/test_visualization_projection.py`: 1,711-line projection contract suite.
- `frontend/src/test/setup.ts`: jsdom/Vitest global setup.
- `frontend/src/test/fixtures/`: Shared typed frontend fixtures.
- `frontend/src/components/graph/cytoscapeReconciler.test.ts`: Headless-Cytoscape reconciler tests (identity, position, selection, compound→flat switches).
- `frontend/src/**/*.test.ts`, `frontend/src/**/*.test.tsx`: Co-located frontend tests.

**Documentation and Planning:**
- `README.md`: Active product/setup overview.
- `docs/ARCHITECTURE.md`: High-level architecture context; verify against source (root `verify_*.py` scripts audit its claims).
- `docs/reference/frontend-api-contract.md`: Frontend-facing API contract.
- `ROADMAP.md`: Canonical long-term scope; checkbox state is not current implementation evidence.
- `.planning/STATE.md`: GSD milestone state and accumulated decisions.

## Naming Conventions

**Files:**
- Python modules use lowercase snake case: `spoilerless/app/services/change_set.py`.
- React component files use PascalCase: `frontend/src/components/chat/ChangeSetCard.tsx`.
- Hooks use `use<Name>.ts`/`.tsx`: `frontend/src/hooks/useChatMessages.ts`.
- Frontend API/type modules use lower camel case where the feature name is compound: `frontend/src/api/changeSet.ts`.
- Pure non-component modules use camelCase: `frontend/src/components/graph/cytoscapeReconciler.ts`, `frontend/src/lib/visualizationAdapter.ts`.
- Tests use `test_<feature>.py` in Python and `<subject>.test.ts(x)` beside frontend code.

**Directories:**
- Backend directories represent architectural layers: `spoilerless/app/services/`, `spoilerless/app/repository/`.
- Frontend component directories represent product features: `frontend/src/components/graph/`, `frontend/src/components/chat/`.
- Seed content is series-scoped: `data/dexter/`.

## Where to Add New Code

**New backend HTTP feature:**
- Domain contracts: `spoilerless/app/domain/<feature>.py`.
- Route handler: `spoilerless/app/api/<feature>.py`, registered in `spoilerless/app/main.py`.
- Business orchestration: `spoilerless/app/services/<feature>.py`.
- Persistence: `spoilerless/app/repository/<feature>.py` and parameterized Cypher in `spoilerless/app/graph/<feature>.py`.
- Tests: `spoilerless/tests/test_<feature>.py`.

**New spoiler-sensitive read:**
- Primary graph response query: `spoilerless/app/spoiler/filter.py`.
- GraphRAG-only read: typed function/query in `spoilerless/app/retrieval/tools.py`, then schema/executor registration in `spoilerless/app/retrieval/pipeline.py`.
- Tests: `spoilerless/tests/test_graph_api.py` or `spoilerless/tests/test_retrieval_tools.py`.
- Requirement: Apply `visible_from_order <= $visible_until_order` to every traversed node/relationship/provenance element before returning rows.

**New visualization projection view:**
- View constant: add to `VIEW_TYPES` in `spoilerless/app/domain/visualization.py` (keep `PROJECTION_VERSION` in sync with checked-in fixtures).
- Projection logic: add a projection function in `spoilerless/app/services/visualization.py` consuming only complete safe `GraphResponse` rows (D-05).
- Route wiring: extend the `VisualizationView` enum in `spoilerless/app/api/graph.py`; extend `get_cached_visualization`/`set_cached_visualization` key construction in `spoilerless/app/cache/graph_cache.py` if the view should cache.
- Frontend: view mapping in `frontend/src/App.tsx` (`activeView`), element conversion in `frontend/src/lib/visualizationAdapter.ts`, scene handling in `frontend/src/hooks/useSceneState.ts`.
- Tests: `spoilerless/tests/test_visualization_projection.py` (contract), `spoilerless/tests/test_visualization_cache.py`, `spoilerless/tests/test_visualization_baseline.py`.

**New semantic expansion key:**
- Add the key to the `EXPANSION_KEYS` allowlist in `spoilerless/app/domain/visualization.py` (D-21) and mirror it in `frontend/src/App.tsx` (`EXPANSION_KEYS`). The expansion path stays uncached (T10-CACHE-06); keep the hard `EXPANSION_MAX_LIMIT` cap.

**New graph mutation:**
- User-driven CRUD: owning repository under `spoilerless/app/repository/`, with same-transaction revision logging through `spoilerless/app/revisions/__init__.py`.
- Agent-proposed mutation: operation model in `spoilerless/app/domain/change_set.py`, validation in `spoilerless/app/services/change_set.py`, transaction implementation in `spoilerless/app/repository/change_set.py`, and Cypher in `spoilerless/app/graph/change_set.py`.
- Frontend confirmation: `frontend/src/components/chat/ChangeSetCard.tsx` and `frontend/src/api/changeSet.ts`.

**New frontend feature:**
- Wire types: `frontend/src/types/<feature>.ts`.
- Transport: `frontend/src/api/<feature>.ts`.
- State: `frontend/src/hooks/use<Feature>.ts` when reusable or asynchronous; graph-workspace state belongs in the `frontend/src/hooks/useSceneState.ts` reducer.
- UI: `frontend/src/components/<feature>/`.
- Composition: connect at the narrowest owner; top-level view/state belongs in `frontend/src/App.tsx` only when it spans features.
- Tests: co-locate `<subject>.test.ts(x)` with implementation or use shared fixtures in `frontend/src/test/fixtures/`.

**New Cytoscape scene behavior:**
- Pure diffing/reconciliation logic: `frontend/src/components/graph/cytoscapeReconciler.ts` (or a co-located named module) with headless-Cytoscape tests in `frontend/src/components/graph/cytoscapeReconciler.test.ts`; keep `frontend/src/components/graph/GraphCanvas.tsx` for component glue.
- Layout policy: `frontend/src/components/graph/layoutConfig.ts` (fcose default, dagre for investigation view; `cytoscape-dagre` is registered there).
- Styling: `frontend/src/components/graph/graphStylesheet.ts` and `frontend/src/components/graph/relationshipStyles.ts` (semantic `relationClass` colors live in `RELATION_CLASS_TO_FAMILY`).

**New shared frontend primitive:**
- Generic UI wrapper: `frontend/src/components/ui/`.
- Non-visual helper: `frontend/src/lib/`.
- Cross-feature wire/UI type: `frontend/src/types/`.

**New series content:**
- Content: `data/<series>/metadata/` and `data/<series>/seed/`.
- Vocabulary: `ontology/` only when the type system changes.
- Bootstrap integration: extend the series-specific assumptions currently in `spoilerless/app/graph/seed.py`.
- Portraits: add `.webp` under `spoilerless/app/static/characters/` and reference via relative `/api/static/...` URLs.

**Database schema change:**
- Add idempotent constraints/indexes to `spoilerless/app/graph/seed.py` and cover setup/idempotency in `spoilerless/tests/test_seed_idempotency.py`.
- No migration directory/framework exists; treat setup DDL as the executable schema record and document any data backfill explicitly.

**Doc-claim verification (root):**
- Extend `verify_arch.py` / `verify_all_claims.py` / `run_doc_verification.py` / `run_verification.py` when adding factual claims to `docs/ARCHITECTURE.md`; they hard-code the repo root and are untracked workspace tooling.

## Source Inventory and Hotspots

- Python: 131 files, ~39,364 lines across `spoilerless/` (78 app / 52 tests / 1 script), excluding untracked root scripts.
- Root doc-verification scripts (untracked): `run_verification.py` (420), `run_doc_verification.py` (429), `verify_all_claims.py` (418), `verify_arch.py` (68).
- TSX: 82 files, 15,061 lines.
- TypeScript: 69 files, 7,943 lines (all `.ts` except `.d.ts`, including `.test.ts`).
- Phase-10 projection orchestration is concentrated in `spoilerless/app/services/visualization.py` (1,173 lines).
- Retrieval orchestration is concentrated in `spoilerless/app/retrieval/pipeline.py` (1,102 lines).
- Prompt policy is concentrated in `spoilerless/app/llm/system_prompt.py` (827 lines) and is user-owned prose.
- Transactional ChangeSet persistence is concentrated in `spoilerless/app/repository/change_set.py` (850 lines); apply dispatch is table-driven (`_APPLY_SPECS`).
- The main frontend inspector is `frontend/src/components/detail/DetailPanel.tsx` (1,049 lines).
- Cytoscape interaction/rendering is concentrated in `frontend/src/components/graph/GraphCanvas.tsx` (1,120 lines) with fcose as the primary layout and dagre for the investigation view; scene diffs live in the small dedicated reconciler `frontend/src/components/graph/cytoscapeReconciler.ts` (126 lines).
- The projection contract suite is `spoilerless/tests/test_visualization_projection.py` (1,711 lines).
- Add focused named modules around these hotspots rather than extending them when a concern has a clean boundary.

## Special Directories and Residue

**`.planning/`:**
- Purpose: GSD project state, milestone artifacts, research, and generated codebase maps.
- Generated: Partly.
- Committed: Yes.
- Rule: Codebase mapping outputs belong only in `.planning/codebase/`.

**`.hermes/`:**
- Purpose: Local Hermes agent skills/configuration for this workspace.
- Generated: Partly.
- Committed: No (untracked).
- Rule: Not product code; ignore for build/test concerns.

**Root `verify_*.py` scripts:**
- Purpose: Claim-level verification of `docs/ARCHITECTURE.md` against the repository.
- Generated: No.
- Committed: No (untracked).
- Rule: Workspace tooling; do not import from the Python package.

**`frontend/dist/`:**
- Purpose: Vite production build output.
- Generated: Yes.
- Committed: Workspace-dependent; never edit by hand.

**`neo4j_data/`, `neo4j_logs/`, `neo4j_import/`, `neo4j_plugins/`:**
- Purpose: Docker-mounted Neo4j runtime volumes/directories.
- Generated: Yes.
- Committed: Treat as runtime state, not source.

**Root `index.html`:**
- Purpose: 58 KB stale duplicate of the frontend entry; the active entry is `frontend/index.html`.
- Generated: Template residue.
- Committed: Present at repository root.
- Rule: Vite serves from `frontend/`; do not edit the root copy.

**Root `scripts/`:**
- Purpose: Local development helpers (`run_backend_tests.py`, `env-local.sh`, `sweep_error_codes_09_05.sh`) outside the Python package.
- Generated: No.
- Committed: Yes.
- Rule: Run the ASGI app as `spoilerless.app.main:app`; keep package code under `spoilerless/`.

**`frontend/src/assets/react.svg` and `frontend/src/assets/vite.svg`:**
- Purpose: Scaffold assets with no architectural role in the application.
- Generated: Template residue.
- Committed: Present under frontend assets.

---

*Structure analysis: 2026-08-14*
