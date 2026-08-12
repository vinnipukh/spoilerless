---
last_mapped: 2026-08-12
focus: arch
last_mapped_commit: 1710d57db7c048a83299cadc072e0779f80f246d
---
# Codebase Structure

**Analysis Date:** 2026-08-12

## Directory Layout

```text
hdgrafcehennemi/
├── spoilerless/
│   ├── app/
│   │   ├── api/             # FastAPI route modules and dependencies
│   │   ├── cache/           # Redis client singleton and graph cache
│   │   ├── core/            # Environment settings, error envelopes, token helpers
│   │   ├── domain/          # Pydantic request/response/business contracts
│   │   ├── graph/           # Neo4j driver, Cypher, ontology, labels, seed/setup
│   │   ├── llm/             # Provider adapters, prompts, safe fallbacks
│   │   ├── repository/      # Neo4j persistence and transaction boundary
│   │   ├── retrieval/       # GraphRAG tool registry, context sections, grounding
│   │   ├── revisions/       # Revision repository implementation
│   │   ├── services/        # Business workflow orchestration
│   │   ├── spoiler/         # Visibility policy and spoiler-safe graph-read Cypher
│   │   └── main.py          # FastAPI application entry point
│   ├── scripts/             # smoke.sh and zombie_sweep.py
│   └── tests/               # pytest backend suite (46 modules)
├── frontend/
│   ├── public/               # Vite-served static assets
│   ├── src/
│   │   ├── api/              # Typed REST and SSE clients
│   │   ├── assets/           # Imported images, including template residue
│   │   ├── components/       # Feature and UI React components
│   │   ├── hooks/            # Async data/state hooks
│   │   ├── lib/              # Shared frontend utility functions
│   │   ├── providers/        # Authentication context/provider/hook
│   │   ├── test/             # Vitest setup and shared fixtures
│   │   ├── types/            # TypeScript wire/UI contracts
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
├── LICENSE                   # MIT license
├── README.md                 # Product and local-development overview
└── ROADMAP.md                # Canonical product scope; not implementation proof
```

## Directory Purposes

**`spoilerless/app/api/`:**
- Purpose: Define the public FastAPI boundary.
- Contains: Eleven router modules (auth, series, graph, user content, revisions, candidates, progress, chat, ChangeSets, settings, share) plus shared auth/database dependencies.
- Key files: `spoilerless/app/api/deps.py`, `spoilerless/app/api/graph.py`, `spoilerless/app/api/chat.py`, `spoilerless/app/api/change_set.py`, `spoilerless/app/api/share.py`.
- Placement rule: Add one route module per resource/feature and register its router in `spoilerless/app/main.py`; keep business logic in `spoilerless/app/services/`.

**`spoilerless/app/core/`:**
- Purpose: Hold process-wide configuration and transport-level error policy.
- Contains: Pydantic settings, exception-handler/error-envelope helpers, and token generation (`spoilerless/app/core/tokens.py`).
- Key files: `spoilerless/app/core/config.py`, `spoilerless/app/core/errors.py`.
- Placement rule: Put cross-feature configuration or HTTP error infrastructure here, not feature persistence.

**`spoilerless/app/domain/`:**
- Purpose: Define strict contracts shared across backend layers.
- Contains: Pydantic models and enums for auth, graph, series, user content, extraction, revisions, progress, chat, ChangeSets, and settings.
- Key files: `spoilerless/app/domain/graph.py`, `spoilerless/app/domain/change_set.py`, `spoilerless/app/domain/chat.py`.
- Placement rule: Add request/response/domain types here before wiring API/service/repository code; forbid extra fields when the existing contract does.

**`spoilerless/app/services/`:**
- Purpose: Coordinate business workflows and enforce rules spanning repositories.
- Contains: Feature classes for series, graph, auth, progress, chat, ChangeSets, settings, and Redis-backed rate limiting.
- Key files: `spoilerless/app/services/graph.py`, `spoilerless/app/services/chat.py`, `spoilerless/app/services/change_set.py`, `spoilerless/app/services/rate_limit.py`.
- Placement rule: Put orchestration here; do not call `tx.run()` from services when the transaction belongs in a repository callback.

**`spoilerless/app/repository/`:**
- Purpose: Own user scoping, Neo4j commands, managed transactions, and row normalization.
- Contains: Users, sessions, user content, progress, chat, settings, ChangeSet, and share-token repositories.
- Key files: `spoilerless/app/repository/user_content.py`, `spoilerless/app/repository/change_set.py`, `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`.
- Placement rule: Add persistence code here and keep query constants in the owning `spoilerless/app/graph/` module unless a tightly scoped repository query follows the established local pattern.

**`spoilerless/app/cache/`:**
- Purpose: Own the single Redis connection and the cache-aside graph response cache.
- Contains: `redis_client.py` (shared `redis.asyncio` singleton) and `graph_cache.py` (boundary-aware keys; any Redis failure degrades to querying Neo4j).
- Placement rule: Never construct a second `redis.asyncio` client; guard every Redis call on a non-empty `REDIS_URL`.

**`spoilerless/app/graph/`:**
- Purpose: Provide graph infrastructure and feature-specific Cypher.
- Contains: Async driver lifecycle, ontology loading, seed/setup, candidate queries, label inventories, and progress/chat/ChangeSet queries.
- Key files: `spoilerless/app/graph/database.py`, `spoilerless/app/graph/ontology.py`, `spoilerless/app/graph/seed.py`, `spoilerless/app/graph/setup.py`.
- Placement rule: Add parameterized query modules by feature; interpolate only server-controlled labels/types selected from ontology allowlists.

**`spoilerless/app/spoiler/`:**
- Purpose: Isolate spoiler visibility rules and the core spoiler-safe graph response queries.
- Contains: Claim-visibility fragment builders and graph-response Cypher (`filter.py`), the effective-boundary rule (`policy.py`), and the single derived-visibility rule (`visibility.py`).
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

**`spoilerless/tests/`:**
- Purpose: Verify backend contracts, graph boundaries, persistence, retrieval, prompt safety, and ChangeSets.
- Contains: 46 pytest modules and shared fixtures — including the `NoopGoogleVerifier` test double and scratch-series isolation helpers — in `spoilerless/tests/conftest.py`.
- Key files: `spoilerless/tests/test_graph_api.py` (1,268 lines), `spoilerless/tests/test_retrieval_tools.py` (1,280), `spoilerless/tests/test_error_handlers.py`, `spoilerless/tests/test_google_verifier.py`, `spoilerless/tests/test_change_set_api.py`.
- Placement rule: Add `test_<feature>.py` here; use dependency overrides/fake providers rather than external LLM calls.

**`frontend/src/api/`:**
- Purpose: Convert typed frontend operations to backend HTTP calls.
- Contains: One client module per backend feature, plus the shared fetch wrapper.
- Key files: `frontend/src/api/client.ts`, `frontend/src/api/chat.ts`, `frontend/src/api/changeSet.ts`, `frontend/src/api/graph.ts`.
- Placement rule: Add feature calls here; use `apiFetch()` for JSON and preserve `credentials: 'include'` in specialized streaming transports.

**`frontend/src/hooks/`:**
- Purpose: Encapsulate async state and feature-specific browser behavior.
- Contains: The shared `useFetchState` state machine plus hooks for series, episodes, graph, progress, notes, revisions, chat sessions, and chat messages.
- Key files: `frontend/src/hooks/useFetchState.ts`, `frontend/src/hooks/useGraph.ts`, `frontend/src/hooks/useWatchProgress.ts`, `frontend/src/hooks/useChatMessages.ts`, `frontend/src/hooks/useChatSessions.ts`.
- Placement rule: Put reusable fetch/state machines here and keep visual rendering in `frontend/src/components/`.

**`frontend/src/components/`:**
- Purpose: Render the product UI by feature.
- Contains: `auth/`, `chat/`, `detail/`, `episode/`, `graph/`, `layout/`, `palette/`, `series/`, `settings/`, `share/`, `timeline/`, and reusable `ui/` primitives.
- Key files: `frontend/src/components/detail/DetailPanel.tsx`, `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/chat/ChatPanel.tsx`.
- Placement rule: Place domain components in their feature folder; add generic shadcn/Radix wrappers only to `frontend/src/components/ui/`.

**`frontend/src/providers/` and `frontend/src/types/`:**
- Purpose: Provide cross-tree auth state and shared TypeScript contracts.
- Contains: Split auth context/provider/hook files and backend-mirroring interfaces.
- Key files: `frontend/src/providers/AuthProvider.tsx`, `frontend/src/providers/AuthContext.ts`, `frontend/src/types/graph.ts`, `frontend/src/types/changeSet.ts`, `frontend/src/types/share.ts`.
- Placement rule: Mirror wire-contract changes in `frontend/src/types/`; reserve providers for genuinely cross-tree state.

**`data/dexter/` and `ontology/`:**
- Purpose: Supply deterministic prototype content and the accepted graph vocabulary.
- Contains: JSON metadata/seed/fixtures and YAML node/relation/claim definitions.
- Key files: `data/dexter/metadata/episodes.json`, `data/dexter/seed/claims.json`, `ontology/relation_types.yaml`.
- Placement rule: Add content under a series-specific data directory and update ontology only for legitimate new graph types; validate through `spoilerless/app/graph/seed.py`.

## Key File Locations

**Entry Points:**
- `spoilerless/app/main.py`: Production FastAPI ASGI application.
- `spoilerless/app/graph/setup.py`: `spoilerless-setup` database bootstrap CLI.
- `frontend/src/main.tsx`: React browser mount.
- `frontend/src/App.tsx`: Product composition root; state-driven graph/settings navigation.

**Configuration:**
- `pyproject.toml`: Python version/dependencies, CLI registration, pytest path.
- `frontend/package.json`: npm development/build/lint/test scripts.
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
- `spoilerless/app/retrieval/pipeline.py`: GraphRAG orchestration, context bounds, grounding.
- `spoilerless/app/retrieval/tools.py`: Allowlisted Neo4j retrieval operations.
- `spoilerless/app/repository/change_set.py`: Transactional ChangeSet apply/reject/revert via the table-driven `_APPLY_SPECS` dispatch.
- `spoilerless/app/api/share.py`: Token-based read-only share links.
- `spoilerless/app/cache/graph_cache.py`: Cache-aside graph responses with boundary-aware keys.
- `frontend/src/components/detail/DetailPanel.tsx`: Main inspector/editing surface.
- `frontend/src/components/graph/GraphCanvas.tsx`: Cytoscape rendering and interaction.

**Testing:**
- `spoilerless/tests/conftest.py`: Backend fixtures, the shared `NoopGoogleVerifier`, and scratch-series isolation helpers.
- `spoilerless/tests/test_openapi_contract.py`: API operation/contract verification.
- `frontend/src/test/setup.ts`: jsdom/Vitest global setup.
- `frontend/src/test/fixtures/`: Shared typed frontend fixtures.
- `frontend/src/**/*.test.ts`, `frontend/src/**/*.test.tsx`: Co-located frontend tests.

**Documentation and Planning:**
- `README.md`: Active product/setup overview.
- `docs/ARCHITECTURE.md`: High-level architecture context; verify against source.
- `docs/reference/frontend-api-contract.md`: Frontend-facing API contract.
- `ROADMAP.md`: Canonical long-term scope; checkbox state is not current implementation evidence.
- `.planning/STATE.md`: GSD milestone state and accumulated decisions.

## Naming Conventions

**Files:**
- Python modules use lowercase snake case: `spoilerless/app/services/change_set.py`.
- React component files use PascalCase: `frontend/src/components/chat/ChangeSetCard.tsx`.
- Hooks use `use<Name>.ts`/`.tsx`: `frontend/src/hooks/useChatMessages.ts`.
- Frontend API/type modules use lower camel case where the feature name is compound: `frontend/src/api/changeSet.ts`.
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

**New graph mutation:**
- User-driven CRUD: owning repository under `spoilerless/app/repository/`, with same-transaction revision logging through `spoilerless/app/revisions/__init__.py`.
- Agent-proposed mutation: operation model in `spoilerless/app/domain/change_set.py`, validation in `spoilerless/app/services/change_set.py`, transaction implementation in `spoilerless/app/repository/change_set.py`, and Cypher in `spoilerless/app/graph/change_set.py`.
- Frontend confirmation: `frontend/src/components/chat/ChangeSetCard.tsx` and `frontend/src/api/changeSet.ts`.

**New frontend feature:**
- Wire types: `frontend/src/types/<feature>.ts`.
- Transport: `frontend/src/api/<feature>.ts`.
- State: `frontend/src/hooks/use<Feature>.ts` when reusable or asynchronous.
- UI: `frontend/src/components/<feature>/`.
- Composition: connect at the narrowest owner; top-level view/state belongs in `frontend/src/App.tsx` only when it spans features.
- Tests: co-locate `<subject>.test.ts(x)` with implementation or use shared fixtures in `frontend/src/test/fixtures/`.

**New shared frontend primitive:**
- Generic UI wrapper: `frontend/src/components/ui/`.
- Non-visual helper: `frontend/src/lib/`.
- Cross-feature wire/UI type: `frontend/src/types/`.

**New series content:**
- Content: `data/<series>/metadata/` and `data/<series>/seed/`.
- Vocabulary: `ontology/` only when the type system changes.
- Bootstrap integration: extend the series-specific assumptions currently in `spoilerless/app/graph/seed.py`.

**Database schema change:**
- Add idempotent constraints/indexes to `spoilerless/app/graph/seed.py` and cover setup/idempotency in `spoilerless/tests/test_seed_idempotency.py`.
- No migration directory/framework exists; treat setup DDL as the executable schema record and document any data backfill explicitly.

## Source Inventory and Hotspots

- Python: 122 files, 32,332 lines across tracked and workspace source/test/tooling files (75 app / 46 tests / 1 script).
- TSX: 79 files, 13,257 lines.
- TypeScript: 65 files, 6,239 lines.
- Retrieval orchestration is concentrated in `spoilerless/app/retrieval/pipeline.py` (969 lines).
- Prompt policy is concentrated in `spoilerless/app/llm/system_prompt.py` (827 lines) and is user-owned prose.
- Transactional ChangeSet persistence is concentrated in `spoilerless/app/repository/change_set.py` (850 lines); apply dispatch is table-driven (`_APPLY_SPECS`).
- The main frontend inspector is `frontend/src/components/detail/DetailPanel.tsx` (1,001 lines).
- Cytoscape interaction/rendering is concentrated in `frontend/src/components/graph/GraphCanvas.tsx` (909 lines) with fcose as the primary layout.
- Add focused named modules around these hotspots rather than extending them when a concern has a clean boundary.

## Special Directories and Residue

**`.planning/`:**
- Purpose: GSD project state, milestone artifacts, research, and generated codebase maps.
- Generated: Partly.
- Committed: Yes.
- Rule: Codebase mapping outputs belong only in `.planning/codebase/`.

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

*Structure analysis: 2026-08-12*
