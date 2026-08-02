---
last_mapped: 2026-08-02
focus: arch
last_mapped_commit: 0b4c83c8ca7c8c0004552cb55b53a5050978c30c
---
# Codebase Structure

**Analysis Date:** 2026-08-02

## Directory Layout

```text
hdgrafcehennemi/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route modules and dependencies
│   │   ├── core/            # Environment settings and error envelopes
│   │   ├── domain/          # Pydantic request/response/business contracts
│   │   ├── graph/           # Neo4j driver, Cypher, ontology, seed/setup
│   │   ├── llm/             # Provider adapters, prompts, safe fallbacks
│   │   ├── repository/      # Neo4j persistence and transaction boundary
│   │   ├── retrieval/       # GraphRAG tool schemas, execution, grounding
│   │   ├── revisions/       # Revision repository implementation
│   │   ├── services/        # Business workflow orchestration
│   │   ├── spoiler/         # Central spoiler-safe graph-read Cypher
│   │   └── main.py          # FastAPI application entry point
│   ├── scripts/             # Backend smoke command
│   └── tests/               # pytest backend suite
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
├── docker-compose.yml        # Neo4j service and persistent volumes
├── pyproject.toml            # Python package, setup CLI, pytest config
├── uv.lock                   # Locked Python dependency graph
├── README.md                 # Product and local-development overview
└── ROADMAP.md                # Canonical product scope; not implementation proof
```

## Directory Purposes

**`backend/app/api/`:**
- Purpose: Define the public FastAPI boundary.
- Contains: Ten router modules plus shared auth/database dependencies.
- Key files: `backend/app/api/deps.py`, `backend/app/api/graph.py`, `backend/app/api/chat.py`, `backend/app/api/change_set.py`.
- Placement rule: Add one route module per resource/feature and register its router in `backend/app/main.py`; keep business logic in `backend/app/services/`.

**`backend/app/core/`:**
- Purpose: Hold process-wide configuration and transport-level error policy.
- Contains: Pydantic settings and exception-handler/error-envelope helpers.
- Key files: `backend/app/core/config.py`, `backend/app/core/errors.py`.
- Placement rule: Put cross-feature configuration or HTTP error infrastructure here, not feature persistence.

**`backend/app/domain/`:**
- Purpose: Define strict contracts shared across backend layers.
- Contains: Pydantic models and enums for auth, graph, series, user content, extraction, revisions, progress, chat, ChangeSets, and settings.
- Key files: `backend/app/domain/graph.py`, `backend/app/domain/change_set.py`, `backend/app/domain/chat.py`.
- Placement rule: Add request/response/domain types here before wiring API/service/repository code; forbid extra fields when the existing contract does.

**`backend/app/services/`:**
- Purpose: Coordinate business workflows and enforce rules spanning repositories.
- Contains: Feature classes for series, graph, auth, progress, chat, ChangeSets, and settings.
- Key files: `backend/app/services/graph.py`, `backend/app/services/chat.py`, `backend/app/services/change_set.py`.
- Placement rule: Put orchestration here; do not call `tx.run()` from services when the transaction belongs in a repository callback.

**`backend/app/repository/`:**
- Purpose: Own user scoping, Neo4j commands, managed transactions, and row normalization.
- Contains: Users, sessions, user content, progress, chat, settings, and ChangeSet repositories.
- Key files: `backend/app/repository/user_content.py`, `backend/app/repository/change_set.py`, `backend/app/repository/session.py`.
- Placement rule: Add persistence code here and keep query constants in the owning `backend/app/graph/` module unless a tightly scoped repository query follows the established local pattern.

**`backend/app/graph/`:**
- Purpose: Provide graph infrastructure and feature-specific Cypher.
- Contains: Async driver lifecycle, ontology loading, seed/setup, candidate queries, progress/chat/ChangeSet queries.
- Key files: `backend/app/graph/database.py`, `backend/app/graph/ontology.py`, `backend/app/graph/seed.py`, `backend/app/graph/setup.py`.
- Placement rule: Add parameterized query modules by feature; interpolate only server-controlled labels/types selected from ontology allowlists.

**`backend/app/spoiler/`:**
- Purpose: Isolate the core spoiler-safe graph response queries.
- Contains: Series, boundary, node, structural-edge, claim, source, and evidence Cypher constants.
- Key files: `backend/app/spoiler/filter.py`.
- Placement rule: Put graph-response visibility changes here and enforce the boundary on every traversed story-sensitive entity.

**`backend/app/retrieval/`:**
- Purpose: Expose a bounded, typed GraphRAG read surface to the LLM.
- Contains: Eleven retrieval functions, input models/tool schemas, context assembly, and citation validation.
- Key files: `backend/app/retrieval/tools.py`, `backend/app/retrieval/pipeline.py`.
- Placement rule: Add a retrieval capability as a typed allowlisted tool, inject authority parameters server-side, and include its returned IDs in grounding validation.

**`backend/app/llm/`:**
- Purpose: Isolate external model-provider behavior and prompt policy.
- Contains: `LLMProvider` protocol, Gemini/OpenAI-compatible adapters, localized fallbacks, and large system-prompt prose.
- Key files: `backend/app/llm/provider.py`, `backend/app/llm/fallbacks.py`, `backend/app/llm/system_prompt.py`.
- Placement rule: Add provider implementations against `LLMProvider`; do not mix graph querying or writes into adapters. Treat `backend/app/llm/system_prompt.py` as user-owned prompt content rather than ordinary refactor material.

**`backend/app/revisions/`:**
- Purpose: Create append-only audit records inside caller-owned Neo4j transactions.
- Contains: `RevisionRepository`, snapshot/JSON helpers, and revision-create Cypher directly in `backend/app/revisions/__init__.py`.
- Key files: `backend/app/revisions/__init__.py`.
- Placement rule: Reuse `RevisionRepository.log_revision()` for mutations; put additional revision modules in named files rather than expanding the package initializer.

**`backend/tests/`:**
- Purpose: Verify backend contracts, graph boundaries, persistence, retrieval, prompt safety, and ChangeSets.
- Contains: pytest modules and shared fixtures in `backend/tests/conftest.py`.
- Key files: `backend/tests/test_graph_api.py`, `backend/tests/test_retrieval_tools.py`, `backend/tests/test_chat_api.py`, `backend/tests/test_change_set_api.py`.
- Placement rule: Add `test_<feature>.py` here; use dependency overrides/fake providers rather than external LLM calls.

**`frontend/src/api/`:**
- Purpose: Convert typed frontend operations to backend HTTP calls.
- Contains: One client module per backend feature, plus the shared fetch wrapper.
- Key files: `frontend/src/api/client.ts`, `frontend/src/api/chat.ts`, `frontend/src/api/changeSet.ts`, `frontend/src/api/graph.ts`.
- Placement rule: Add feature calls here; use `apiFetch()` for JSON and preserve `credentials: 'include'` in specialized streaming transports.

**`frontend/src/hooks/`:**
- Purpose: Encapsulate async state and feature-specific browser behavior.
- Contains: Hooks for series, episodes, graph, progress, notes, revisions, and chat.
- Key files: `frontend/src/hooks/useGraph.ts`, `frontend/src/hooks/useWatchProgress.ts`, `frontend/src/hooks/useChatMessages.ts`.
- Placement rule: Put reusable fetch/state machines here and keep visual rendering in `frontend/src/components/`.

**`frontend/src/components/`:**
- Purpose: Render the product UI by feature.
- Contains: `auth/`, `chat/`, `detail/`, `episode/`, `graph/`, `layout/`, `settings/`, and reusable `ui/` primitives.
- Key files: `frontend/src/components/detail/DetailPanel.tsx`, `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/chat/ChatPanel.tsx`.
- Placement rule: Place domain components in their feature folder; add generic shadcn/Radix wrappers only to `frontend/src/components/ui/`.

**`frontend/src/providers/` and `frontend/src/types/`:**
- Purpose: Provide cross-tree auth state and shared TypeScript contracts.
- Contains: Split auth context/provider/hook files and backend-mirroring interfaces.
- Key files: `frontend/src/providers/AuthProvider.tsx`, `frontend/src/providers/AuthContext.ts`, `frontend/src/types/graph.ts`, `frontend/src/types/changeSet.ts`.
- Placement rule: Mirror wire-contract changes in `frontend/src/types/`; reserve providers for genuinely cross-tree state.

**`data/dexter/` and `ontology/`:**
- Purpose: Supply deterministic prototype content and the accepted graph vocabulary.
- Contains: JSON metadata/seed/fixtures and YAML node/relation/claim definitions.
- Key files: `data/dexter/metadata/episodes.json`, `data/dexter/seed/claims.json`, `ontology/relation_types.yaml`.
- Placement rule: Add content under a series-specific data directory and update ontology only for legitimate new graph types; validate through `backend/app/graph/seed.py`.

## Key File Locations

**Entry Points:**
- `backend/app/main.py`: Production FastAPI ASGI application.
- `backend/app/graph/setup.py`: `hdgraf-setup` database bootstrap CLI.
- `frontend/src/main.tsx`: React browser mount.
- `frontend/src/App.tsx`: Product composition root; state-driven graph/settings navigation.

**Configuration:**
- `pyproject.toml`: Python version/dependencies, CLI registration, pytest path.
- `frontend/package.json`: npm development/build/lint/test scripts.
- `frontend/vite.config.ts`: React/Tailwind plugins, `@` alias, `/api` proxy, Vitest setup.
- `frontend/tsconfig.app.json`: Frontend TypeScript compiler settings.
- `docker-compose.yml`: Neo4j container/volume configuration.
- `.env.example`, `frontend/.env.example`: Configuration templates; do not put secrets in tracked files.

**Core Logic:**
- `backend/app/spoiler/filter.py`: Canonical spoiler-safe graph-read queries.
- `backend/app/services/graph.py`: Concurrent graph assembly and claim-edge projection.
- `backend/app/retrieval/pipeline.py`: GraphRAG orchestration, context bounds, grounding.
- `backend/app/retrieval/tools.py`: Allowlisted Neo4j retrieval operations.
- `backend/app/repository/change_set.py`: Transactional ChangeSet apply/reject/revert.
- `frontend/src/components/detail/DetailPanel.tsx`: Main inspector/editing surface.
- `frontend/src/components/graph/GraphCanvas.tsx`: Cytoscape rendering and interaction.

**Testing:**
- `backend/tests/conftest.py`: Backend fixtures and app/database overrides.
- `backend/tests/test_openapi_contract.py`: API operation/contract verification.
- `frontend/src/test/setup.ts`: jsdom/Vitest global setup.
- `frontend/src/test/fixtures/`: Shared typed frontend fixtures.
- `frontend/src/**/*.test.ts`, `frontend/src/**/*.test.tsx`: Co-located frontend tests.

**Documentation and Planning:**
- `README.md`: Active product/setup overview.
- `docs/ARCHITECTURE.md`: High-level architecture context; verify against source.
- `docs/frontend-api-contract.md`: Frontend-facing API contract.
- `ROADMAP.md`: Canonical long-term scope; checkbox state is not current implementation evidence.
- `.planning/STATE.md`: GSD milestone state and accumulated decisions.

## Naming Conventions

**Files:**
- Python modules use lowercase snake case: `backend/app/services/change_set.py`.
- React component files use PascalCase: `frontend/src/components/chat/ChangeSetCard.tsx`.
- Hooks use `use<Name>.ts`/`.tsx`: `frontend/src/hooks/useChatMessages.ts`.
- Frontend API/type modules use lower camel case where the feature name is compound: `frontend/src/api/changeSet.ts`.
- Tests use `test_<feature>.py` in Python and `<subject>.test.ts(x)` beside frontend code.

**Directories:**
- Backend directories represent architectural layers: `backend/app/services/`, `backend/app/repository/`.
- Frontend component directories represent product features: `frontend/src/components/graph/`, `frontend/src/components/chat/`.
- Seed content is series-scoped: `data/dexter/`.

## Where to Add New Code

**New backend HTTP feature:**
- Domain contracts: `backend/app/domain/<feature>.py`.
- Route handler: `backend/app/api/<feature>.py`, registered in `backend/app/main.py`.
- Business orchestration: `backend/app/services/<feature>.py`.
- Persistence: `backend/app/repository/<feature>.py` and parameterized Cypher in `backend/app/graph/<feature>.py`.
- Tests: `backend/tests/test_<feature>.py`.

**New spoiler-sensitive read:**
- Primary graph response query: `backend/app/spoiler/filter.py`.
- GraphRAG-only read: typed function/query in `backend/app/retrieval/tools.py`, then schema/executor registration in `backend/app/retrieval/pipeline.py`.
- Tests: `backend/tests/test_graph_api.py` or `backend/tests/test_retrieval_tools.py`.
- Requirement: Apply `visible_from_order <= $visible_until_order` to every traversed node/relationship/provenance element before returning rows.

**New graph mutation:**
- User-driven CRUD: owning repository under `backend/app/repository/`, with same-transaction revision logging through `backend/app/revisions/__init__.py`.
- Agent-proposed mutation: operation model in `backend/app/domain/change_set.py`, validation in `backend/app/services/change_set.py`, transaction implementation in `backend/app/repository/change_set.py`, and Cypher in `backend/app/graph/change_set.py`.
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
- Bootstrap integration: extend the series-specific assumptions currently in `backend/app/graph/seed.py`.

**Database schema change:**
- Add idempotent constraints/indexes to `backend/app/graph/seed.py` and cover setup/idempotency in `backend/tests/test_seed_idempotency.py`.
- No migration directory/framework exists; treat setup DDL as the executable schema record and document any data backfill explicitly.

## Source Inventory and Hotspots

- Python: 93 files, 22,793 lines across tracked and workspace source/test/tooling files.
- TSX: 57 files, 8,754 lines.
- TypeScript: 43 files, 3,169 lines.
- Retrieval orchestration is concentrated in `backend/app/retrieval/pipeline.py` (853 lines).
- Prompt policy is concentrated in `backend/app/llm/system_prompt.py` (837 lines) and is user-owned prose.
- Transactional ChangeSet persistence is concentrated in `backend/app/repository/change_set.py` (816 lines).
- The main frontend inspector is `frontend/src/components/detail/DetailPanel.tsx` (797 lines).
- Cytoscape interaction/rendering is concentrated in `frontend/src/components/graph/GraphCanvas.tsx` (530 lines).
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

**`frontend/README.md`:**
- Purpose: Vite scaffold documentation, not HD Graf Cehennemi architecture.
- Generated: Template residue.
- Committed: Present in the frontend root.
- Rule: Use root `README.md` and `docs/` for product documentation; do not infer active design from `frontend/README.md`.

**Root `main.py`:**
- Purpose: PyCharm sample script unrelated to the ASGI application.
- Generated: IDE template residue.
- Committed: Present at repository root.
- Rule: Run `backend.app.main:app`; do not add backend behavior to root `main.py`.

**`frontend/src/assets/react.svg` and `frontend/src/assets/vite.svg`:**
- Purpose: Scaffold assets with no architectural role in the application.
- Generated: Template residue.
- Committed: Present under frontend assets.

---

*Structure analysis: 2026-08-02*
