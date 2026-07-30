---
last_mapped: 2026-07-30
focus: arch
---

# Architecture

## Summary

HD Graf Cehennemi is a spoiler-safe narrative knowledge graph app for the Dexter S01E01–03 prototype. The backend is a FastAPI + Neo4j (async `neo4j` driver) application that stores series/episode structure plus an entity-claim-evidence-source graph, filtered at query time by a per-user "spoiler boundary" (`visible_until_order`). The frontend is a React + Vite SPA using Cytoscape.js (with `cytoscape-cose-bilkent` layout) for graph rendering, shadcn/ui + Tailwind for UI primitives, and Google Sign-In cookie-session auth. Prototype v0 (phases 1–4) shipped a full watch-progress-gated graph viewer with notes/custom-relationship editing and revision history; Phase 5 added a backend-only "future-extraction preparation" layer (ontology-validated candidate claims, ingest API, review/approve/reject/edit workflow) not yet wired to a frontend UI (Phase 05.1, about to be planned, will add that review UI).

## Backend Architecture

### Layers

- API layer: `backend/app/api/*.py`
  - `series.py` — series/episode listing.
  - `graph.py` — `GET /api/series/{series_id}/graph`, the main spoiler-filtered graph read endpoint.
  - `user_content.py` — notes, custom nodes, custom relationships (user-authored content).
  - `auth.py` — Google Sign-In verification, session cookie issuance, CSRF origin checks, logout.
  - `revisions.py` — list/get revisions, revert-to-snapshot.
  - `candidates.py` — ingest/list/get/approve/reject/edit candidate claims (Phase 5).
- Service layer: `backend/app/services/*.py`
  - `graph.py` (`GraphService`) — orchestrates parallel Cypher queries (`asyncio.gather`) and projects claims into graph edges.
  - `series.py`, `auth.py` (`AuthService`) — series lookups and Google credential verification.
- Domain schema layer: `backend/app/domain/*.py`
  - `series.py`, `graph.py` (nodes/edges/claims/sources/evidence response models), `user_content.py` (notes, custom nodes/relationships, shared `Identifier`/`PlainText`/`VisibilityOrder` types), `auth.py`, `revision.py` (`RevisionAction`, `RevisionResponse`), `extraction.py` (`ExtractionClaim`, `ExtractionBatchEnvelope`, `EvidencePayload`, `SourcePayload` — the extractor-output contract).
- Graph persistence layer: `backend/app/graph/database.py`
  - `Neo4jDatabase` owns driver lifecycle (`open`/`close`/`verify_connection`) and exposes `execute_query`/`execute_write` transaction helpers; `get_database` is the FastAPI dependency.
- Graph query/logic modules:
  - `backend/app/graph/ontology.py` — loads and validates `ontology/*.yaml` (node types, relationship types, claim types/statuses/confidence levels) into a frozen `Ontology` object; exposes `user_safe_relationship_types`/`user_safe_node_types` allowlists.
  - `backend/app/graph/candidates.py` (`CandidateRepository`) — ingest/list/get candidate claims; derives deterministic IDs via SHA-256 content hashing for idempotent ingest.
  - `backend/app/graph/seed.py` / `backend/app/graph/setup.py` — seed script and schema/constraint setup.
- Spoiler filter layer: `backend/app/spoiler/filter.py`
  - Centralizes every parameterized Cypher query used for fail-closed spoiler/temporal filtering (`NODES_QUERY`, `STRUCTURAL_EDGES_QUERY`, `VISIBLE_CLAIMS_QUERY`, `VISIBLE_USER_RELATIONSHIPS_QUERY`, `SOURCES_QUERY`, `EVIDENCE_QUERY`, `BOUNDARY_QUERY`). Every query requires `visible_from_order <= $visible_until_order` on all involved nodes/edges — the single enforcement point for spoiler safety.
- Revision layer: `backend/app/revisions/__init__.py` (`RevisionRepository`)
  - Append-only revision log. Static methods run inside caller-managed Neo4j write transactions (`log_revision`, `take_snapshot`, JSON (de)serialization of before/after state).
- Repository layer: `backend/app/repository/*.py`
  - `session.py` — `SessionRepository` abstraction with in-memory (dev) and Neo4j-backed implementations for auth sessions.
  - `user.py`, `user_content.py` — user and note/custom-node/custom-relationship persistence, raising `UserContentNotFound`/`UserContentConflict`/`UserContentValidationError`.
- Error handling layer: `backend/app/core/errors.py`
  - Single stable error envelope `{"detail": {"code", "message"}}`; `install_database_error_handlers` wires Neo4j exception types and `RequestValidationError` to sanitized 503/422 responses; `error_responses(*codes)` generates OpenAPI response docs.
- Configuration layer: `backend/app/core/config.py`
  - Reads Neo4j connection settings and `FRONTEND_ORIGINS` from environment/`.env` via a cached settings accessor.

### Request Flow (graph read)

1. Client calls `GET /api/series/{series_id}/graph?visible_until_order=N` (`backend/app/api/graph.py`).
2. Route resolves `GraphService` via DI, fetches series metadata, and validates the boundary against a persisted episode (`resolve_boundary`).
3. `GraphService.fetch_graph` runs seven Cypher queries concurrently (`asyncio.gather`) against `backend/app/spoiler/filter.py`, covering series, nodes, structural edges, visible claims, visible user-authored relationships, sources, and evidence.
4. Claims are converted into projected `GraphEdge` objects (`id={claim.id}:edge`) alongside structural and user edges.
5. Pydantic models in `backend/app/domain/graph.py` shape the unified `GraphResponse` (nodes, edges, claims, sources, evidence).

### Candidate Review Flow (Phase 5, backend-only)

1. A future extractor (or test fixture) POSTs an `ExtractionBatchEnvelope` to `/api/series/{series_id}/candidates/ingest` (`backend/app/api/candidates.py`).
2. `CandidateRepository.ingest_batch` (`backend/app/graph/candidates.py`) derives deterministic IDs (SHA-256 of normalized content) for `Source`, `EvidenceFragment`, and `Claim` nodes so repeated ingests are idempotent; each claim is created with `origin: 'candidate'`, `status: 'candidate'`.
3. Reviewers call `GET .../candidates` / `.../candidates/{claim_id}` to inspect pending claims, then `POST .../{claim_id}/approve` (flips `status` to `canonical`), `POST .../{claim_id}/reject` (`status: rejected`), or `PATCH .../{claim_id}` to edit mutable fields.
4. Every approve/reject/edit writes a `RevisionAction.UPDATED` revision via `RevisionRepository.log_revision` inside the same write transaction, capturing before/after snapshots.
5. Approved candidates (`origin: candidate`, `status: canonical`) become visible through the normal `VISIBLE_CLAIMS_QUERY` (`claim.origin IN ['canonical', 'candidate']`) once their `visible_from_order` boundary is reached — no separate promotion into a different node type.

### Startup Flow

1. FastAPI `lifespan` (`backend/app/main.py`) creates a `Neo4jDatabase` from settings, opens the driver, and attaches it plus a `Neo4jSessionRepository` to `app.state`.
2. `verify_connection()` runs at startup; failure is swallowed intentionally — `/health` reports live connectivity (`status: degraded`, `database: unavailable`) rather than crashing the process.
3. Six routers are mounted: series, graph, user-content, auth, revisions, candidates.
4. CORS is configured from `FRONTEND_ORIGINS`; `install_database_error_handlers` wires the shared error envelope.
5. Shutdown calls `database.close()`.

## Graph Data Model

Node labels (from `ontology/node_types.yaml`, enforced by `backend/app/graph/ontology.py`): `Series`, `Episode`, `Character`, `Event`, `Location`, `Organization`, `Object`, plus internal `Claim`, `Source`, `EvidenceFragment`, `Revision`, `UserNote`, `Session`, `User` nodes.

Structural relationships: `(:Episode)-[:PART_OF]->(:Series)`, `(:Episode)-[:PRECEDES]->(:Episode)`, `(:Event)-[:OCCURRED_IN]->(:Location|:Episode)`.

Claim-centric model (the primary knowledge representation):
- `Claim` nodes carry `subject_id`/`predicate`/`object_id` (a reified edge), `claim_type`, `status` (`candidate`/`canonical`/`rejected`), `confidence_level`, `relationship_effect`, `origin` (`canonical`/`candidate`/`user`), and temporal validity (`valid_from_order`/`valid_until_order`) plus `visible_from_order` for spoiler gating.
- `(:Claim)-[:SUPPORTED_BY]->(:EvidenceFragment)` and `(:Claim)-[:REFERS_TO]->(:Source)` connect every non-user claim to its textual evidence and source.
- User-authored relationships are also `Claim` nodes with `origin: 'user'`, `claim_type: 'user_authored'`, and IDs prefixed `user-rel:`; they are filtered through a separate query (`VISIBLE_USER_RELATIONSHIPS_QUERY`) restricted to an ontology-declared allowlist of relationship types (`user_safe_relationship_types`).
- `UserNote` nodes attach to any node via `(:UserNote)-[:REFERS_TO]->(target)`.
- `Revision` nodes are an append-only audit log (`resource_type`, `resource_id`, `action`, JSON `before`/`after` snapshots, `visible_from_order`) — not part of the visible graph projection.

Every node/edge type carries `visible_from_order` and `origin`. The spoiler boundary (`visible_until_order`) is the sole gating mechanism, enforced identically across all six read queries in `backend/app/spoiler/filter.py` (fail-closed: an unfiltered node/edge is never returned).

## Frontend Architecture

### Component Tree (top to bottom)

- `frontend/src/main.tsx` — React root, renders `App` in `StrictMode`.
- `frontend/src/App.tsx` — wraps `AuthProvider` around `AppContent`, which renders `LoginPage` (unauthenticated) or `AuthenticatedApp`. `AuthenticatedApp` owns top-level state (selected series, watch progress, selected graph element) and composes `AppShell` + `SeriesSelect`/`EpisodeSelector` (top bar) + `ConfirmAdvanceModal` + graph status states + `GraphCanvas` + `DetailPanel`/`StructuralEdgeCard`.
- `frontend/src/components/layout/AppShell.tsx` — page chrome: header bar (title, user avatar/logout, `topBar` slot) plus a full-height content area for the graph canvas and detail panel.
- `frontend/src/components/episode/` — `SeriesSelect.tsx`, `EpisodeSelector.tsx` (watch-progress picker), `ConfirmAdvanceModal.tsx` (confirms spoiler-boundary jumps).
- `frontend/src/components/graph/` — Cytoscape rendering layer:
  - `GraphCanvas.tsx` — wraps `react-cytoscapejs`, registers `cytoscape-cose-bilkent` (falls back to built-in `cose` on registration/runtime failure), imperatively re-runs layout on graph-object change (declarative `layout` prop doesn't re-trigger on data-only changes), renders `GraphLegend` and `GraphControls` overlays, and a create-custom-node dialog.
  - `graphElements.ts` — pure transform from `GraphResponse` to Cytoscape node/edge element definitions.
  - `graphStylesheet.ts` — builds the Cytoscape stylesheet (node/edge visual rules) consuming `relationshipStyles.ts`.
  - `relationshipStyles.ts` — edge-type → color-family → hex mapping (two-level indirection: `EDGE_TYPE_TO_FAMILY` then `FAMILY_HEX`) driving both canvas edge colors and the legend.
  - `GraphLegend.tsx` — renders the color-family legend derived from `relationshipStyles.ts`.
  - `GraphControls.tsx` — zoom/fit/layout controls overlay.
  - `GraphStatus.tsx` — `GraphLoadingState`, `GraphErrorState`, `GraphEmptyState` presentational states.
- `frontend/src/components/detail/` — selection detail surfaces:
  - `DetailPanel.tsx` — shadcn `Sheet`-based side panel for a selected node/claim-edge; tabbed (`Tabs`) view including notes (via `useNotes`), character portrait with graceful image-load fallback, and embeds `RevisionHistoryPanel`.
  - `RevisionHistoryPanel.tsx` — lists/reverts revisions for the selected resource (Phase 4).
  - `StructuralEdgeCard.tsx` — lightweight card for structural (non-claim) edges, shown instead of `DetailPanel` when the selected edge has no `claim_id`.
- `frontend/src/components/auth/LoginPage.tsx` — Google Sign-In entry point.
- `frontend/src/components/ui/` — shadcn/ui primitives (`button`, `card`, `dialog`, `sheet`, `tabs`, `select`, `tooltip`, `skeleton`, `badge`, `alert`, `collapsible`, `separator`).

### State and Data Flow

- `frontend/src/providers/AuthProvider.tsx` + `AuthContext.ts` + `useAuth.ts` — cookie-session auth state machine (`loading`/`authenticated`/`unauthenticated`/`error`), gates the entire app tree.
- `frontend/src/hooks/` — one hook per resource, each wrapping `frontend/src/api/*.ts` fetch calls in a `status`-tagged state shape (`idle`/`loading`/`success`/`error`) with a `refetch`:
  - `useSeries.ts`, `useEpisodes.ts` — series/episode lists.
  - `useGraph.ts` — the graph fetch keyed on `(seriesId, visibleUntilOrder)`; drives the primary render.
  - `useWatchProgress.ts` — client-persisted (localStorage-backed) spoiler boundary with pending-change confirmation flow (`requestChange`/`confirmChange`/`cancelChange`), used to gate `useGraph`'s boundary parameter.
  - `useNotes.ts` — per-node note CRUD.
  - `useRevisions.ts` — revision list/get/revert for `RevisionHistoryPanel`.
- `frontend/src/api/client.ts` — shared `apiFetch<T>` wrapper: always sends `credentials: 'include'`, throws `ApiError` mirroring the backend's `{detail:{code,message}}` envelope.
- `frontend/src/api/*.ts` (`series.ts`, `graph.ts`, `auth.ts`, `revisions.ts`, `userContent.ts`) — one module per backend router, typed against `frontend/src/types/*.ts`.
- `frontend/src/types/*.ts` — TypeScript mirrors of backend Pydantic response models (`graph.ts`, `series.ts`, `revision.ts`, `userContent.ts`, `auth.ts`).

### Rendering / Interaction Flow

1. `AuthenticatedApp` selects a series and resolves a confirmed spoiler boundary via `useWatchProgress`.
2. `useGraph(seriesId, confirmedOrder)` fetches `GET /api/series/{id}/graph` and returns a `GraphResponse`.
3. `GraphCanvas` converts the response to Cytoscape elements (`graphElements.ts`), applies the stylesheet (`graphStylesheet.ts` + `relationshipStyles.ts`), and runs the `cose-bilkent` layout imperatively on every graph-object change.
4. Selecting a node or edge calls `onSelect`, setting `selectedElement` in `AuthenticatedApp`, which conditionally renders `StructuralEdgeCard` (structural edge, no `claim_id`) or `DetailPanel` (node or claim edge) — including its Notes tab and `RevisionHistoryPanel`.
5. Advancing the episode selector triggers `ConfirmAdvanceModal` before `watchProgress.confirmChange()` updates the boundary and re-triggers `useGraph`.

## Component Boundaries

- Backend and frontend are separate directories with independent dependency manifests (`pyproject.toml`/`uv.lock` for backend, `frontend/package.json`/`package-lock.json` for frontend).
- Backend exposes only HTTP JSON endpoints under `/api/*` plus `/health`; it owns all graph persistence and spoiler enforcement — the frontend never runs Cypher.
- Ontology (`ontology/*.yaml`) is the single source of truth for allowed node/relationship/claim types, loaded and validated only by the backend (`backend/app/graph/ontology.py`); the frontend's `relationshipStyles.ts` mapping is a separate, manually maintained visual concern, not generated from the ontology.
- Seed and test fixture data (`data/dexter/`) is consumed only by backend seed/test code, never by the frontend.
- Auth sessions are HttpOnly cookies validated server-side (`backend/app/repository/session.py`); the frontend never reads or stores the session token directly.
- Phase 5's candidate/extraction API (`backend/app/api/candidates.py`, `backend/app/domain/extraction.py`) has no frontend consumer yet — it is reachable only via direct HTTP calls (tests, future connectors). This is the gap Phase 05.1 fills.

## Anti-Patterns / Notable Design Choices

- **Inline Cypher, no ORM**: All queries are hand-written parameterized Cypher strings centralized in `backend/app/spoiler/filter.py` (reads) and per-repository modules (writes). This is intentional for auditability of spoiler-filtering logic but means every new node/edge type requires manually replicating the `visible_from_order` guard.
- **Fail-closed spoiler filtering**: Every visibility-sensitive query independently re-applies `visible_from_order <= $visible_until_order` on all matched nodes/edges rather than relying on a single upstream filter — a deliberate defense-in-depth pattern, not duplication to remove.
- **Claims-as-edges projection**: Graph edges are not one-to-one with Neo4j relationships; canonical/candidate claims are projected into synthetic `GraphEdge` objects (`id={claim.id}:edge`) at the service layer (`backend/app/services/graph.py`), while structural and user-authored relationships map directly to Neo4j relationship types.
- **Degraded startup**: The backend intentionally does not fail FastAPI startup if Neo4j is unreachable; `/health` reports `degraded` instead. New features that assume a live DB at import time will break this contract.

## Cross-Cutting Concerns

**Error handling:** One stable envelope `{"detail": {"code", "message"}}` (`backend/app/core/errors.py`) shared by all routers; the frontend's `ApiError` (`frontend/src/api/client.ts`) is a direct mirror.

**Spoiler enforcement:** Centralized exclusively in `backend/app/spoiler/filter.py`; there is no client-side spoiler filtering — the frontend renders exactly what the backend returns for the current boundary.

**Revisions/audit:** Every mutating write (notes, custom nodes/relationships, candidate approve/reject/edit) logs a `Revision` node via `RevisionRepository.log_revision` inside the same Neo4j write transaction as the mutation, enabling `POST .../revisions/{id}/revert`.

**Auth:** Google Sign-In credential verification (`backend/app/services/auth.py`) plus server-side session records (`backend/app/repository/session.py`), CSRF-guarded via Origin/Referer checks (`verify_origin` in `backend/app/api/auth.py`) on state-changing auth routes, `SameSite=Lax` cookies.

---

*Architecture analysis: 2026-07-30*
