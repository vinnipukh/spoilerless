# Spoilerless — Authoritative Roadmap

> **Maintenance note:** This is the canonical roadmap after consolidation. Update status here when implementation changes; do not revive the root roadmap as a competing status source. Normative invariants and future ingestion rules live in [PROJECT-SPEC.md](architecture/project-spec.md).

## 0. Project summary and status legend

Spoilerless is a spoiler-safe narrative knowledge graph for television series. Its prototype content boundary is Dexter Season 1, S01E01–S01E03. Users browse a source-grounded graph, control a watch-progress boundary, add personal content, inspect revisions, and optionally chat with an LLM over only the allowed subgraph.

The long-term product combines manual editing, source-backed automatic extraction, spoiler-aware filtering, evidence/provenance, revision history, human review, and GraphRAG.

Status terms in this roadmap:

- **Complete:** implemented in the current repository; this does not imply production readiness.
- **Partially complete:** a useful layer exists, but acceptance is incomplete or a documented exception remains.
- **Future:** aspirational; do not infer implementation.
- Checked tasks represent repository implementation. Corrected route/status notes explain where the historical wording became stale.

## 1. Core principles

1. **Spoiler safety at data access.** Backend/retrieval filtering happens before data reaches the frontend or LLM. Story records use `visible_from_order`; claims also honor validity windows. Candidate list and detail reads require a resolved spoiler boundary and fail closed (422) when it is omitted or unresolved.
2. **Automatic knowledge is source-backed.** Every automatic candidate needs evidence with source type/locator, episode, precise locator, retrieval metadata, and preferably a content hash.
3. **Origins remain separate.** Canonical show metadata, candidate extraction, user notes/nodes/relationships, and corrections stay distinguishable through `canonical|candidate|user`.
4. **Confidence is not relationship effect.** `confidence_level` describes certainty; `relationship_effect` describes the asserted relationship dimension. Do not collapse them.
5. **History is append-only in meaning.** Edits, extraction review decisions, corrections, and reversions create revisions. Revert appends a new revision instead of destroying prior records.
6. **Ontology and Cypher are constrained.** Types come from versioned YAML; user/model values are parameterized and never become unrestricted query text.

See [PROJECT-SPEC.md §3](architecture/project-spec.md#3-non-negotiable-architecture-invariants) for the complete normative rules.

## 2. Prototype scope: original target versus current product

### Original Prototype v0 scope

- one series/season and three episodes;
- Neo4j, FastAPI, React/TypeScript, Cytoscape.js;
- series/episode metadata and a spoiler-filtered graph API;
- manual seed data, source/evidence display, progress selector and spoiler confirmation;
- basic notes and revision history.

The original out-of-scope list included automatic subtitle/script/podcast/web ingestion, an extraction pipeline, LLM chat, multi-user accounts, production authentication, and deployment. This was a **prototype boundary**, not a permanent prohibition.

### Current implemented expansion

The repository now also includes:

- Google ID-token sign-in, HttpOnly server-side sessions, and authenticated progress;
- user notes and custom graph nodes/relationships;
- revisions and supported revert flows;
- extraction schemas plus candidate ingest/list/get/edit/approve/reject APIs;
- optional spoiler-aware GraphRAG chat, bounded allowlisted retrieval, structured citations, SSE, and chat persistence;
- LLM settings and confirmable/rejectable/revertible ChangeSets.

This expansion does not mean automatic extraction, full multi-user authorization, production deployment, or all review UX is complete.

## 3. Current stack and repository shape

```text
Frontend: React + TypeScript + Vite + Cytoscape.js
Backend:  FastAPI + Neo4j Python Driver + Pydantic
Database: Neo4j Community via Docker Compose
Packages: uv (Python), npm (frontend)
```

The historical planned tree has become a layered implementation under `spoilerless/app/{api,core,domain,graph,llm,repository,retrieval,revisions,services,spoiler}`, `spoilerless/tests`, `frontend/src/{api,components,hooks,types}`, `ontology/`, and `data/dexter/{metadata,seed,test}`. The actual current structure and rationale are authoritative in [ARCHITECTURE.md](ARCHITECTURE.md#3-directory-structure-rationale).

## 4. Ontology and atomic claim baseline

Ontology v0.1 remains committed in `ontology/node_types.yaml`, `ontology/relation_types.yaml`, and `ontology/claim_types.yaml`. It defines structural/narrative/knowledge/user/system nodes; structural, participation, character, provenance, and revision relationships; five claim types; five statuses; and four confidence levels.

A Claim is one atomic assertion with stable subject/predicate/object, visibility and optional validity window, origin, status, confidence, relationship effect, creator/provenance, and ontology version. Only `canonical` or `corroborated` status should be treated as accepted truth. See [PROJECT-SPEC.md §4](architecture/project-spec.md#4-ontology-and-atomic-claim-semantics) and [ARCHITECTURE.md §7.2–7.4](ARCHITECTURE.md#72-the-claim-model).

## 5. Prototype milestones and acceptance status

### Milestone 1 — Local infrastructure

**Status: Complete in source/configuration.** Runtime URL acceptance still depends on starting local services with valid configuration.

- [x] Create repository.
- [x] Configure Neo4j with Docker Compose.
- [x] Create FastAPI backend and Vite frontend.
- [x] Create `.env.example`, ontology files, and Dexter metadata.
- [x] Implement a real Neo4j connectivity health check.
- [x] Implement series/episode seed setup.
- [x] Implement initial API routes.

Acceptance:

- Neo4j Browser: `http://localhost:7474` after Compose startup.
- Swagger: `http://127.0.0.1:8000/docs` after backend startup.
- Frontend: `http://localhost:5173` after Vite startup.
- `GET /health` reports live database connectivity and can return 503/degraded.

Operational instructions: [GETTING-STARTED.md](GETTING-STARTED.md).

### Milestone 2 — Metadata graph

**Status: Complete.**

- [x] Create uniqueness constraints/indexes for Series, Episode, and later graph/application node types.
- [x] Seed Dexter and S01E01–S01E03.
- [x] Create `PART_OF` and `PRECEDES` relationships.
- [x] Implement `GET /api/series`.
- [x] Implement `GET /api/series/{series_id}` and `/episodes`.

Acceptance: the seeded graph contains one Dexter series with three ordered episodes. Seed code and idempotency tests are in `spoilerless/app/graph/seed.py` and `spoilerless/tests/test_seed_idempotency.py`.

### Milestone 3 — Spoiler-aware graph endpoint

**Status: Complete for the graph route; candidate list/detail reads enforce the same resolved spoiler boundary.**

- [x] Define `GraphResponse`.
- [x] Require positive integer visibility on seeded story nodes/claims and audit null visibility.
- [x] Implement the actual route `GET /api/series/{series_id}/graph?visible_until_order=1`.
- [x] Filter nodes, edges, claims, sources, and evidence in the backend and close edges over visible endpoints.
- [x] Test spoiler boundaries and error shapes.

Historical correction: `/api/graph?series_id=series_dexter&visible_until_order=1` was a planned route that was never implemented; the series-scoped route above supersedes it and is complete.

Acceptance: boundary 1 returns no S01E02/S01E03 story information. Detailed contract: [API.md](API.md#series-episodes-health-and-graph).

### Milestone 4 — Manual seed graph

**Status: Complete.**

- [x] Create character, event, location, source, evidence, and claim seed files.
- [x] Seed the small Dexter network.
- [x] Attach relationship claims to source/evidence records.
- [x] Validate ontology, stable IDs, visibility, endpoints, and provenance before setup.

Acceptance: the graph response can supply series/episodes, selected narrative nodes, visible claims, and source/evidence references to the frontend. Current source locators are metadata/plain text, not guaranteed navigable links.

### Milestone 5 — Frontend graph UI

**Status: Complete for the current prototype experience.**

- [x] Replace the Vite starter screen and implement the main application shell.
- [x] Fetch real series, episodes, progress, and graph data.
- [x] Add progress selection and advance confirmation.
- [x] Render and style the graph with Cytoscape.js.
- [x] Add node and edge/claim detail views.
- [x] Display claims, evidence, and source metadata/locators.
- [x] Add neighbor/focus interactions and distinct user-origin treatment.

Historical correction: the root checklist called this “Display evidence links.” The current UI displays evidence and source locators, but does not render navigable source links. Link rendering remains backlog work if suitable rights-safe URLs are available.

Acceptance: a user can choose watched progress and see only the graph returned for that boundary. Frontend behavior is covered by colocated Vitest tests.

### Milestone 6 — User notes and manual editing

**Status: Complete for current API/UI scope; user-content mutations are authenticated and owner-bound (admin bypass).**

- [x] Implement `UserNote` contracts and CRUD.
- [x] Implement custom node CRUD.
- [x] Implement custom relationship CRUD.
- [x] Derive visibility server-side and visually separate user origin.
- [x] Surface notes and relationship creation in the detail experience.

Acceptance: users can add a note to a Character or Claim and inspect it in the detail panel; custom content can appear in the graph. All user-content mutation routes require an authenticated session and enforce stored `user_id` ownership with an admin bypass (anonymous 401; cross-owner 403).

### Milestone 7 — Revision history

**Status: Complete for supported user-content, candidate, and ChangeSet operations; not full event sourcing.**

- [x] Create revision model/repository and visibility-aware routes.
- [x] Log supported create, update, delete, candidate review, and correction operations.
- [x] Display revisions in the frontend.
- [x] Implement supported simple revision revert.
- [x] Preserve history by appending a `Reverted` revision.

Acceptance: a user can inspect prior snapshots for supported edits and perform supported reverts. Limitations and conflict behavior are documented in [API.md](API.md#revisions).

### Milestone 8 — Preparation for LLM extraction

**Status: Partially complete by design: contracts and review boundary exist; extraction does not.**

- [x] Define strict extraction output/batch schemas.
- [x] Define source/evidence payload contracts (the “source connector interface,” not a running connector).
- [x] Add deterministic candidate IDs and candidate Claim storage.
- [x] Implement candidate ingest, list/get, edit, approve, and reject.
- [x] Log review transitions as revisions.
- [ ] Implement source fetching/parsing.
- [ ] Implement LLM extraction and canonical entity resolution.
- [ ] Implement a complete human review UI.

Acceptance achieved: a future extractor can submit structured candidate claims without changing the core Claim model. Acceptance not claimed: automatic source-to-graph ingestion. See [PROJECT-SPEC.md §9](architecture/project-spec.md#9-future-automated-knowledge-graph-ingestion-architecture).

### Milestone 9 — Spoiler-aware LLM chat

**Status: Complete for the optional configured prototype path.**

- [x] Implement server-bound spoiler-aware retrieval tools.
- [x] Implement relationship, neighborhood/path, timeline, evidence/source, and supporting retrieval operations.
- [x] Generate source-cited answers and graph focus.
- [x] Prevent the model from choosing series/progress or issuing raw Cypher.
- [x] Persist user-owned sessions/messages and support SSE.
- [x] Add prompt-injection, citation, boundary, persistence, and provider tests.

Acceptance: when enabled/configured, chat answers from graph data visible at persisted progress and returns structured citations. Chat being disabled by default is configuration state, not missing implementation. See [ARCHITECTURE.md §7.8](ARCHITECTURE.md#78-graphrag-lite-chat-pipeline).

### Milestone 10 — Authentication, settings, and guarded changes (post-original roadmap)

**Status: Implemented prototype capabilities with known hardening gaps.**

- [x] Google ID-token verification and AppUser upsert.
- [x] Opaque HttpOnly server-side sessions and authenticated `/me`/logout.
- [x] Per-user watch progress, chat ownership, settings, and ChangeSet ownership.
- [x] Two-stage ChangeSet proposal/confirmation with transactional application, rejection, replay protection, and bounded revert support.
- [x] Apply consistent authentication/ownership to user-content, revision, and candidate mutations. (Corrected 2026-08-10: shipped — user-content mutations and candidate ingest require `CurrentUserDependency` with owner-scoped enforcement and admin bypass; candidate review routes require `RequireAdminDependency`; settings routes are admin-gated.)
- [ ] Add comprehensive CSRF protection for cookie-authenticated state changes.
- [ ] Define production authorization roles/policy if multi-user deployment is approved.

## 6. Prototype demo and definition of done

The canonical demo remains:

1. open the app and select Dexter;
2. set S01E01 progress and show only boundary-visible nodes/claims;
3. inspect a character or relationship and its source-backed claims/evidence;
4. advance toward S01E02 through explicit spoiler confirmation;
5. observe newly unlocked graph elements;
6. add a note and distinguish user origin;
7. inspect revision history for a supported change;
8. with chat configured, ask a visible relationship question and inspect citations;
9. repeat at S01E01 and verify there is no S01E02/S01E03 leak.

This is a polished, technically honest architecture proof, not production completion. The original demo also listed direct claim editing; current candidate edit/review is an API workflow and ChangeSets can propose guarded changes, but a comprehensive candidate-review UI is not claimed.

## 7. Evaluation and acceptance obligations

### Spoiler safety

- S01E01 graph/search/retrieval cannot expose S01E02/S01E03 nodes, labels, names, counts, claims, or evidence.
- Hidden and missing resources share fail-closed responses on boundary-aware routes.
- LLM tools cannot override persisted progress.
- Candidate list and detail reads require a resolved spoiler boundary and fail closed (422) when it is omitted or invalid; above-boundary detail reads are indistinguishable from missing (404).

### Source and provenance

- Every automatic/candidate claim has evidence.
- Evidence includes episode and precise locator; source includes stable type/locator and retrieval metadata when available.
- The public UI avoids republishing copyrighted scripts/subtitles.

### Revision integrity

- Supported edits create revisions; previous values remain inspectable.
- Revert appends a revision and does not erase history.
- Conflicts fail rather than overwrite later changes.

### UX

- Users can understand why a relationship exists.
- Users can distinguish canonical/candidate/user content.
- Progress changes are explicit and safe.
- Graph density and styling remain readable rather than default/noisy.

Testing commands and live-Neo4j safety are in [TESTING.md](TESTING.md).

## 8. Known gaps and unresolved risks

1. **Authorization:** Google Sign-In, HttpOnly session cookies, and `admin` role-based access control for settings, candidates, and ChangeSets shipped in Phase 8/9 (PROB-18/PROB-19/AUTH-01); per-user owner isolation for ordinary notes/custom nodes/relationships also shipped — user-created content carries `user_id`, and cross-owner mutations are rejected with 403 (admin bypass). Residual: a read/privacy policy for owner-scoped content is not yet defined.
2. **CSRF:** Origin verification via `verify_origin` dependency guards authentication POST routes; additional CSRF token checks for non-auth cookie routes remain a future hardening goal.
3. **Source navigation:** detail UI shows plain-text source metadata/locators, not navigable source links.
4. **Automatic ingestion:** no subtitle/script downloader, parser, extractor, entity linker, or production review pipeline exists.
5. **Review UI:** candidate workflow is API-level; comprehensive human review UX remains future work.
6. **Production operations:** deployment architecture is repository-declared (`render.yaml` backend service, `frontend/vercel.json` SPA rewrites, [DEPLOYMENT.md](DEPLOYMENT.md)) and PR CI is configured (`.github/workflows/ci.yml`: dedicated Neo4j service, seed, full pytest, DB-residue gate, frontend build/lint/audit — pull-request trigger only). Live operator/platform production state, push-triggered CI, and release enforcement (`.github/workflows/release.yml` remains a non-enforcing skeleton) are still incomplete.
7. **Testing isolation:** backend integration tests use live local Neo4j and require careful cleanup. **Suite-time gap (SEVENTEENTH PASS, 2026-08-12):** the `live_client` fixture is function-scoped and re-runs the full `setup_database` per test (~4.6s local seed + TestClient lifespan boot ≈ 10s/test; measured: `test_progress_api.py` 26 tests / 260s) — the full green suite is ~42 min even on local docker. The EIGHTH PASS "<8m met (2:01)" figure was measured on the stale `hdgraf-neo4j` (5-community) container with 35 failing tests that fast-failed before doing work — never a green-suite benchmark; `bacd536` (08-11) later made those tests pass (full work per test), which is why green wall-time is back to ~40 min. **Task:** module/session-scoped seed + read-only client (the DRY conftest comment at `conftest.py:163` documents the earlier attempt broke `get_database` state — needs the per-module shared client to be resurrected without that breakage), targeting sub-10-min green local runs. See `docs/ops/runbook.md` §Backend Tests.
8. **ChangeSet/revision breadth:** revert is intentionally bounded; this is not full event sourcing.
9. **Confidence semantics:** extraction `relationship_effect` remains loosely typed; thresholds/calibration are not academically validated.

## 9. Future milestone/backlog direction

### Near-term hardening

- make candidate reads boundary-required and fail closed — **shipped** (candidate list/detail require a resolved persisted-episode boundary and fail closed with 422 when it is omitted or invalid);
- apply consistent authenticated ownership/authorization to user content, revisions, candidates, and settings-sensitive mutations — **shipped** (user-content mutations and candidate ingest require an authenticated session; user-content owner checks with admin bypass; candidate review and settings routes admin-gated);
- add CSRF defenses appropriate to cookie-authenticated deployment;
- reconcile frontend/backend type mismatches and keep OpenAPI/contract tests locked;
- add rights-safe navigable source links only when locators are valid URLs and copyright constraints are respected;
- CI test isolation is shipped (per-job Neo4j service + DB-residue gate in `.github/workflows/ci.yml`); local integration tests still share the live local Neo4j instance;
- production-readiness deployment: manifests are declared (`render.yaml`, `frontend/vercel.json`, `docs/DEPLOYMENT.md`), but release enforcement and live operator/platform state remain incomplete.

### Ingestion research and implementation

- process scene/subtitle-window inputs deterministically;
- implement strict ontology-constrained extraction without prior-knowledge leakage;
- build calibrated canonical entity resolution with unresolved/manual-review paths;
- extend the review UI while preserving candidate origin and revision history;
- inherit source episode visibility and prove reprocessing idempotency;
- evaluate vector/hybrid retrieval only after it can preserve the same spoiler boundary.

### Product feature ideas (brainstorm, unscoped)

Ungrouped, unscoped user-facing feature ideas — graph UX, chat, provenance, collaboration, multi-series, provider UX — live in [FEATURE-IDEAS.md](ideas/feature-ideas.md). None of it carries roadmap status until explicitly scoped against [PROJECT-SPEC.md §3](architecture/project-spec.md#3-non-negotiable-architecture-invariants).

### Deliberately later product breadth

- full OpenSubtitles/script/podcast/IMDb/Fandom/news ingestion;
- multi-series support and calibrated ontology evolution;
- production multi-user permissions, mobile, and social features;
- community detection or large-scale graph analytics;
- Kubernetes or other deployment complexity only when justified;
- never add actor/character appearance counts that leak future participation.

## 10. Research and academic direction

The project can be framed as:

> A spoiler-aware, provenance-backed narrative knowledge graph with human-in-the-loop correction and constrained GraphRAG.

Potential contributions:

- spoiler-aware graph retrieval and fail-closed metadata behavior;
- temporal visibility modeling distinct from narrative validity;
- atomic, evidence-backed claim graphs;
- provenance-aware GraphRAG with turn-local citation validation;
- human-in-the-loop narrative extraction/editing;
- revision-controlled personal media knowledge bases;
- evaluation methods for prior-knowledge leakage and episode-boundary contamination.

Future academic claims require empirical evaluation; placeholder linking thresholds and qualitative confidence labels must not be presented as calibrated results.

## 11. Roadmap maintenance rules

- Update task status only with source/test evidence.
- Preserve the distinction between implemented prototype capability and production readiness.
- Never mark extraction, review UI, deployment, or authorization complete because an interface/schema exists.
- Keep real route shapes synchronized with [API.md](API.md) and [frontend-api-contract.md](reference/frontend-api-contract.md).
- Put normative invariant changes in [PROJECT-SPEC.md](architecture/project-spec.md) and link them here.
- Preserve known exceptions until the implementation and tests close them.
