---
last_mapped: 2026-07-30
focus: arch
---

# Structure

## Top-Level Layout

- `pyproject.toml`, `uv.lock` — root Python project manifest/lockfile managed by uv.
- `backend/` — FastAPI backend, business logic, tests.
- `frontend/` — Vite React SPA.
- `ontology/` — YAML ontology definitions (`node_types.yaml`, `relation_types.yaml`, `claim_types.yaml`) — single source of truth for allowed graph types, loaded by `backend/app/graph/ontology.py`.
- `data/` — seed metadata, seed graph fixtures, and test extraction fixtures for Dexter.
- `docker-compose.yml` — local Neo4j (and related services) container definitions.
- `docs/` — project documentation (contract docs, etc.).
- `HD_GRAF_CEHENNEMI_CODING_AGENT_SPEC_V2.md`, `README.md`, `ROADMAP.md` — product/spec/roadmap docs at repo root.
- `index.html` — standalone static prototype page (pre-dates and is separate from `frontend/`); not part of the built React app.
- `main.py` — default PyCharm sample script; not connected to the app.
- `.env` / `.env.example` — Neo4j and app environment variables (`.env` git-ignored).
- `neo4j_data/`, `neo4j_logs/`, `neo4j_import/`, `neo4j_plugins/` — local Neo4j runtime directories, git-ignored.
- `.planning/` — GSD planning workspace (this document's location: `.planning/codebase/`).

## Backend Layout

`backend/app/` (all packages have `__init__.py` markers):

- `main.py` — FastAPI app construction, `lifespan`, CORS, `/health`, router registration (series, graph, user-content, auth, revisions, candidates).
- `api/`
  - `series.py` — `/api/series` list routes.
  - `graph.py` — `/api/series/{series_id}/graph` spoiler-filtered graph read.
  - `user_content.py` — notes, custom nodes, custom relationships.
  - `auth.py` — Google Sign-In, session, logout, CSRF origin verification.
  - `revisions.py` — list/get revisions, revert-to-snapshot.
  - `candidates.py` — candidate claim ingest/list/get/approve/reject/edit (Phase 5).
- `core/`
  - `config.py` — settings model and cached settings accessor (Neo4j connection, `FRONTEND_ORIGINS`).
  - `errors.py` — shared `{detail:{code,message}}` error envelope, `error_responses()` OpenAPI helper, Neo4j/validation exception handlers.
- `domain/`
  - `series.py` — `SeriesResponse`/`EpisodeResponse`.
  - `graph.py` — `GraphNode`, `GraphEdge`, `GraphClaim`, `GraphSource`, `GraphEvidence`, `GraphResponse`.
  - `user_content.py` — note/custom-node/custom-relationship request+response models, shared `Identifier`/`PlainText`/`VisibilityOrder`/`VisibleUntilOrder` types.
  - `auth.py` — `GoogleAuthRequest`, `UserPublic`, `UserResponse`.
  - `revision.py` — `RevisionAction` enum, `RevisionResponse`.
  - `extraction.py` — `ExtractionClaim`, `ExtractionBatchEnvelope`, `EvidencePayload`, `SourcePayload` (extractor-output contract; Phase 5).
- `graph/`
  - `database.py` — `Neo4jDatabase` driver wrapper (`open`/`close`/`verify_connection`/`execute_query`/`execute_write`), `get_database` FastAPI dependency.
  - `ontology.py` — loads/validates `ontology/*.yaml` into a frozen `Ontology`; exposes user-safe node/relationship allowlists.
  - `candidates.py` — `CandidateRepository`: deterministic content-hash IDs, ingest batch Cypher, list/get candidate claims.
  - `seed.py` — seed script loading `data/dexter/` fixtures.
  - `setup.py` — schema/constraint setup.
- `revisions/__init__.py` — `RevisionRepository`: append-only revision log (`log_revision`, `take_snapshot`, JSON before/after serialization). Static-method design for use inside caller-managed write transactions.
- `repository/`
  - `session.py` — `SessionRecord`, `SessionRepository` abstraction, in-memory and Neo4j-backed implementations for auth sessions.
  - `user.py` — user persistence.
  - `user_content.py` — `UserContentRepository` plus `UserContentNotFound`/`UserContentConflict`/`UserContentValidationError`.
- `services/`
  - `graph.py` — `GraphService`: parallel Cypher orchestration and claim→edge projection for the main graph read.
  - `series.py` — series lookups.
  - `auth.py` — `AuthService`, `GoogleTransportError`, `GoogleVerificationError`: Google credential verification.
- `spoiler/filter.py` — every parameterized read Cypher query enforcing spoiler/temporal visibility (`NODES_QUERY`, `STRUCTURAL_EDGES_QUERY`, `VISIBLE_CLAIMS_QUERY`, `VISIBLE_USER_RELATIONSHIPS_QUERY`, `SOURCES_QUERY`, `EVIDENCE_QUERY`, `BOUNDARY_QUERY`, `SERIES_QUERY`, plus series/episode list queries).
- `requirements.txt` — uv-exported pinned requirements with hashes (secondary to `pyproject.toml`/`uv.lock`).

`backend/tests/` — pytest suite, one file roughly per feature area: `conftest.py`, `test_auth.py`, `test_graph_api.py`, `test_revisions.py`, `test_revision_models.py`, `test_candidate_ingest.py`, `test_candidate_review.py`, `test_extraction_models.py`, `test_user_content_api.py`, `test_user_content_models.py`, `test_user_content_repository.py`, `test_seed_idempotency.py`, `test_openapi_contract.py`, `test_frontend_contract_doc.py`.

## Frontend Layout

- `frontend/package.json`, `frontend/package-lock.json` — npm scripts and dependencies (React, Vite, Cytoscape + `cytoscape-cose-bilkent`, `react-cytoscapejs`, Tailwind, shadcn/ui/Radix primitives, Vitest).
- `frontend/vite.config.ts`, `tsconfig.json`/`tsconfig.app.json`/`tsconfig.node.json`, `eslint.config.js` — build/type/lint config.
- `frontend/index.html` — Vite HTML entry for the React app.
- `frontend/src/main.tsx` — React root entry point.
- `frontend/src/App.tsx` — top-level component: `AuthProvider` → `AppContent` (login gate) → `AuthenticatedApp` (owns series/watch-progress/selection state and composes the main UI).
- `frontend/src/App.test.tsx` — top-level integration test.
- `frontend/src/components/`
  - `layout/AppShell.tsx` — header chrome + content area shell.
  - `auth/LoginPage.tsx` — Google Sign-In entry.
  - `episode/` — `SeriesSelect.tsx`, `EpisodeSelector.tsx`, `ConfirmAdvanceModal.tsx` (+ test).
  - `graph/` — `GraphCanvas.tsx` (+ test), `graphElements.ts` (+ test), `graphStylesheet.ts`, `relationshipStyles.ts` (+ test), `GraphLegend.tsx`, `GraphControls.tsx`, `GraphStatus.tsx`.
  - `detail/` — `DetailPanel.tsx` (+ test), `RevisionHistoryPanel.tsx` (+ test), `StructuralEdgeCard.tsx` (+ test).
  - `ui/` — shadcn/ui primitives: `alert`, `badge`, `button`, `card`, `collapsible`, `dialog`, `select`, `separator`, `sheet`, `skeleton`, `tabs`, `tooltip`.
- `frontend/src/hooks/` — `useSeries.ts`, `useEpisodes.ts`, `useGraph.ts`, `useWatchProgress.ts` (+ test), `useNotes.ts`, `useRevisions.ts` (+ test).
- `frontend/src/providers/` — `AuthContext.ts`, `AuthProvider.tsx`, `useAuth.ts`.
- `frontend/src/api/` — `client.ts` (shared `apiFetch`/`ApiError`), `series.ts`, `graph.ts`, `auth.ts`, `revisions.ts`, `userContent.ts`.
- `frontend/src/types/` — `graph.ts`, `series.ts`, `revision.ts`, `userContent.ts`, `auth.ts`, `cytoscape-cose-bilkent.d.ts` (ambient module declaration).
- `frontend/src/lib/utils.ts` — shared utilities (e.g. `cn` class-merge helper for shadcn/ui).
- `frontend/src/test/` — `setup.ts` (Vitest/RTL setup), `fixtures/graphResponse.ts` (shared graph fixture for tests).
- `frontend/src/index.css`, `frontend/src/App.css` — global theme/layout and component-level styles (Tailwind).
- `frontend/src/assets/` — local static assets.

## Data Layout

- `data/dexter/metadata/series.json`, `episodes.json` — series/episode metadata consumed by `backend/app/graph/seed.py`.
- `data/dexter/seed/` — full seed graph fixtures: `characters.json`, `events.json`, `locations.json`, `sources.json`, `evidence_fragments.json`, `claims.json`.
- `data/dexter/test/extraction_fixture.json` — sample `ExtractionBatchEnvelope` payload used by candidate-ingest tests.
- `backend/app/graph/seed.py` derives `PROJECT_ROOT` from its file path and expects this exact `data/dexter/` layout.
- `ontology/*.yaml` — not under `data/`; loaded via `backend/app/graph/ontology.py`'s `PROJECT_ROOT / "ontology"` path.

## Planning Layout

- `.planning/` — GSD planning workspace (STATE.md, MILESTONES.md, ROADMAP references, `milestones/` archive).
- `.planning/codebase/` — generated by the codebase mapping workflow (this document and its siblings: ARCHITECTURE.md, STACK.md, INTEGRATIONS.md, CONVENTIONS.md, TESTING.md, CONCERNS.md).

## Naming Conventions Observed

**Backend (Python):**
- Packages/modules: lowercase snake_case (`user_content.py`, `graph.py`).
- Pydantic models: `PascalCase` ending in `Response`/`Request`/`Create`/`Update` (`SeriesResponse`, `NoteCreate`, `EditCandidateRequest`).
- API router functions: action-noun verbs (`list_series`, `get_graph`, `approve_candidate`, `ingest_candidates`).
- Neo4j labels: `PascalCase` (`Series`, `Episode`, `Claim`, `EvidenceFragment`, `UserNote`).
- Neo4j relationship types: uppercase verbs (`PART_OF`, `PRECEDES`, `SUPPORTED_BY`, `REFERS_TO`, `OCCURRED_IN`).
- Domain/graph IDs: `type:slug` strings, e.g. `series_dexter`, `episode:dexter:s01e01`, `character:dexter`, `revision:{uuid}`, `extracted:{sha256_prefix}`, `user-rel:{...}`.
- Error codes: lowercase snake_case matching `^[a-z][a-z0-9_]*$` (`resource_not_found`, `invalid_extraction_payload`).

**Frontend (TypeScript/React):**
- Component files: `PascalCase.tsx` matching the exported component (`GraphCanvas.tsx`, `DetailPanel.tsx`).
- Non-component modules: `camelCase.ts` (`graphElements.ts`, `relationshipStyles.ts`, `useGraph.ts`).
- Hooks: `useXxx.ts` in `src/hooks/`, one hook per backend resource/concern, returning a `status`-tagged state object (`idle`/`loading`/`success`/`error`) with a `refetch`.
- Test files: co-located `Name.test.tsx`/`Name.test.ts` next to the module under test.
- Types: mirror backend Pydantic model names/shapes in `src/types/*.ts` (e.g. `GraphResponse`, `RevisionResponse`-equivalents).

## Where to Add New Code

**New backend API resource (e.g. Phase 05.1 candidate review support):**
- Route: new or extended file in `backend/app/api/` (existing `candidates.py` already covers ingest/approve/reject/edit — likely only additive changes here).
- Domain models: `backend/app/domain/` (reuse `extraction.py` for candidate shapes).
- Query logic: extend `backend/app/graph/candidates.py` or add a new repository module under `backend/app/graph/` or `backend/app/repository/`.
- Tests: `backend/tests/test_<feature>.py`, following the existing per-feature split.

**New frontend UI for candidate review (Phase 05.1 target):**
- New component directory under `frontend/src/components/` (e.g. `components/candidates/`), following the `detail/`/`graph/` pattern of one directory per feature area with co-located `.test.tsx` files.
- API client: new `frontend/src/api/candidates.ts` mirroring `revisions.ts`/`userContent.ts` (uses shared `apiFetch` from `client.ts`).
- Types: new `frontend/src/types/candidates.ts` mirroring `backend/app/domain/extraction.py` response shapes.
- Hook: new `frontend/src/hooks/useCandidates.ts` following the `status`-tagged pattern of `useRevisions.ts`.
- Wire into `AuthenticatedApp` (`frontend/src/App.tsx`) alongside existing `DetailPanel`/`RevisionHistoryPanel` composition, or as a new top-level view/tab.

**New graph node/relationship/claim type:**
- Declare it in `ontology/*.yaml` first — `backend/app/graph/ontology.py` validates all claim/node/relationship types against this file at load time.
- Add to `VISIBLE_NODE_LABELS`/`USER_RELATIONSHIP_TYPES` in `backend/app/api/graph.py` if it should render in the main graph.
- Add a visual mapping in `frontend/src/components/graph/relationshipStyles.ts` for edges, or extend `graphStylesheet.ts` for node styling.

**Shared utilities:**
- Backend: `backend/app/core/` for cross-cutting config/error concerns.
- Frontend: `frontend/src/lib/utils.ts` for generic helpers.

## Special Directories

**`ontology/`:**
- Purpose: YAML-declared allowlists for node types, relationship types, and claim types/statuses/confidence levels.
- Generated: No (hand-authored).
- Committed: Yes.

**`data/dexter/`:**
- Purpose: seed metadata, full seed graph fixtures, and a test extraction fixture for the Dexter S01E01–03 prototype.
- Generated: No (hand-authored/curated).
- Committed: Yes.

**`neo4j_data/`, `neo4j_logs/`, `neo4j_import/`, `neo4j_plugins/`:**
- Purpose: local Neo4j container runtime state (via `docker-compose.yml`).
- Generated: Yes.
- Committed: No (git-ignored).

**`index.html` (repo root):**
- Purpose: standalone static prototype page, separate from and not wired to `frontend/`.
- Generated: No.
- Committed: Yes, but not part of the build pipeline.

---

*Structure analysis: 2026-07-30*
