# Requirements: HD Graf Cehennemi — Prototype v0

**Defined:** 2026-07-28
**Canonical scope:** root `ROADMAP.md`, Prototype v0 milestones 1–8
**Core Value:** Backend-enforced watch progress lets users safely explore an evidence-backed narrative graph without spoilers.

All requirements below are pending until their acceptance evidence is executed. Existing scaffolds are brownfield inputs, not proof of completion.

## Prototype v0 Requirements

### Phase 1 — Backend Graph Foundation

- [x] **INFRA-01**: Neo4j, FastAPI, and React development services start locally and their Browser, Swagger, and app URLs are reachable.
- [x] **INFRA-02**: `/health` performs and reports a real Neo4j connectivity check, including unavailable behavior.
- [x] **INFRA-03**: Backend lifecycle, parameterized queries, managed transactions, and application-level Neo4j error handling are testable without import-time connection side effects.

#### Metadata Graph

- [x] **META-01**: A reliable, idempotent setup command creates uniqueness/existence constraints needed by Prototype v0.
- [x] **META-02**: Setup persists Dexter, S01E01–03, `PART_OF`, and `PRECEDES` with correct order and `visible_from_order` metadata.
- [x] **META-03**: `GET /api/series` and `GET /api/series/{series_id}/episodes` return the persisted series and three ordered episodes through serializable response models.

#### Spoiler-Aware Graph API

- [x] **API-01**: `GET /api/graph` requires series and watch-progress inputs and returns serializable nodes, edges, claims, and boundary metadata.
- [x] **API-02**: Cypher/data-access filtering enforces `visible_from_order` on nodes, relationships, claims, sources, and evidence before response construction.
- [x] **API-03**: Claim validity (`valid_from_order`/`valid_until_order`) is enforced independently from spoiler visibility and graph closure is preserved.
- [x] **API-04**: Boundary tests at orders 1, 2, and 3 prove future nodes, edges, claims, names, labels, evidence, and counts do not leak; invalid inputs have defined errors.

#### Evidence-Backed Manual Seed Graph

- [x] **SEED-01**: Manual Dexter S01E01–03 seed data defines selected Character and relationship/atomic Claim records with visibility, confidence, relationship effect, status, and validity metadata.
- [x] **SEED-02**: Source and EvidenceFragment records include episode references and locators (timestamp, page, or scene), plus retrieval metadata/content hashes where available.
- [x] **SEED-03**: Every seeded claim links to at least one EvidenceFragment and its Source, and setup remains idempotent after loading the complete graph.
- [x] **SEED-04**: Executed graph queries and API checks demonstrate a small evidence-backed network at each allowed episode boundary.

### Phase 2 — Polished Cytoscape Graph Experience

- [x] **UI-01**: The Vite starter is replaced by a React/TypeScript product layout that loads series, episodes, and graph data from the backend.
- [x] **UI-02**: A watch-progress selector confirms advancement before unlocking a later episode and safely refreshes the applied backend boundary.
- [x] **UI-03**: Cytoscape renders only returned nodes/edges and visibly updates as S01E01, S01E02, and S01E03 become allowed.
- [x] **UI-04**: Node and edge/claim detail views explain relationships and display linked source/evidence episode locators.
- [x] **UI-05**: Frontend build/lint/component checks and demo UX checks verify safe progress changes and absence of hidden-data rendering.

### Phase 3 — User Notes and Manual Editing

- [ ] **NOTE-01**: A UserNote model/API/UI lets a user create, read, update, and delete a note attached to a character or claim.
- [ ] **NOTE-02**: APIs and UI allow creating/editing user-owned custom nodes and relationships without mutating canonical knowledge.
- [ ] **NOTE-03**: Storage metadata and visual treatment clearly distinguish user-created content from canonical and candidate/automatic content.

### Phase 4 — Revision History and Revert

- [x] **REV-01**: An append-only Revision model logs claim creation/update/rejection, user corrections, manual graph edits, and relevant before/after values.
- [x] **REV-02**: A history panel displays prior values and the action/provenance behind each revision.
- [x] **REV-03**: Revert restores a selected prior value by creating a new revision and never deletes existing history; tests prove this behavior.

### Phase 5 — Future-Extraction Preparation

- [ ] **PREP-01**: A versioned extraction-output JSON schema represents atomic candidate claims, visibility/validity, confidence/effect, and evidence references.
- [ ] **PREP-02**: Candidate claims are stored separately from canonical and user-created knowledge and cannot become canonical without review.
- [ ] **PREP-03**: API/UI review supports approve, reject, and edit actions, with evidence visible and every action revision-logged.
- [ ] **PREP-04**: A source-connector interface accepts normalized source/evidence payloads without implementing external retrieval or parsing.
- [ ] **PREP-05**: A fixture-driven acceptance test proves structured candidates from a hypothetical future extractor can enter review and be resolved without changing the core graph model or invoking an LLM.

## Post-v0 Requirements

- Automated retrieval/ingestion from OpenSubtitles, scripts/PDFs, podcasts, Fandom/IMDb/news, or external sites.
- Operational LLM extraction pipeline.
- ~~Spoiler-aware LLM chat and graph-RAG tools (root milestone 9)~~ — broken out below as Phase 6 (RAG-01..17).
- Multi-user/authentication, collaboration, production deployment/public hosting, mobile/social features.

## Phase 6 Requirements — Spoiler-Safe GraphRAG Chat and Graph-Editing Agent (Milestone 9, Post-v0)

**Defined:** 2026-07-30
**Scope:** root `ROADMAP.md` milestone 9 ("LLM chat, later phase"), expanded per `06-PRD-SOURCE.md` to include structured graph-editing via typed ChangeSets. Out of canonical-scope for the v0 30-requirement table above; tracked separately since it opens a new milestone rather than extending Prototype v0.

#### Authoritative Watch Progress & Spoiler-Safe Retrieval

- [x] **RAG-01**: A persisted per-user, per-series watch-progress record (not a frontend-supplied parameter) is the sole source of `visible_until_order` for every GraphRAG request; the existing `/api/series/{id}/graph` endpoint and chat retrieval use compatible visibility semantics.
- [ ] **RAG-02**: An explicit allowlisted set of typed backend retrieval tools (entity search/get, neighborhood, path, timeline, claims, evidence, sources, graph summary, user notes) each independently re-enforce user ownership, series scope, `visible_from_order` filtering, bounded depth/result counts, and fail-closed behavior; no tool accepts user- or model-provided Cypher.
- [ ] **RAG-03**: Hidden/future graph resources behave as nonexistent through every tool, error path, and citation — no leakage via counts, path existence, timing, or metadata.

#### LLM Orchestration

- [ ] **RAG-04**: A backend-only LLM provider abstraction (OpenAI-compatible, env-configured, `LLM_ENABLED` gate) supports a deterministic fake provider for tests, timeout handling, bounded retries, and distinguishes provider failures (503) from auth failures; no API key reaches the frontend or logs.
- [ ] **RAG-05**: A deterministic retrieval → spoiler-filtered context → LLM answer → citation-validation → graph-focus pipeline bounds tool-call rounds and context size; the LLM never receives a raw Neo4j driver or unrestricted schema-to-Cypher capability.
- [ ] **RAG-06**: A versioned system prompt establishes spoiler-safety and tool-only access, and treats all graph-sourced text (Notes/Claims/Evidence/Sources/chat history) as untrusted data; tests prove injected instructions embedded in graph content are not obeyed.

#### Grounded Answers

- [ ] **RAG-07**: Every factual answer carries citations (claim/evidence/source references) validated against retrieved context; hallucinated or hidden-record citations are rejected; insufficient-evidence questions receive an explicit uncertainty answer instead of an invented one.
- [ ] **RAG-08**: Future-content questions never confirm or deny the existence, name, or count of a hidden entity or relationship.

#### Chat Persistence

- [x] **RAG-09**: Persistent per-user `ChatSession`/`ChatMessage` records store the exact `visible_until_order` used to generate each assistant message; messages generated above the user's current boundary are excluded from API responses, previews, titles, and LLM conversation memory — without being deleted.
- [x] **RAG-10**: Series-scoped chat REST endpoints (create/list/get/delete session, post message, stream) enforce authenticated ownership, generic 404s for inaccessible sessions, bounded input/history length, and a structured streaming final event (message/citations/graph_focus/proposed ChangeSet) with no chain-of-thought or provider diagnostics exposed.

#### Safe Graph-Editing Agent

- [x] **RAG-11**: A typed `ChangeSet` propose/confirm flow lets the assistant construct graph mutations only through a Pydantic discriminated-union operation set (create/update/delete node, relationship, claim, note, evidence attach); the LLM never executes a write directly.
- [ ] **RAG-12**: The backend validates every ChangeSet operation server-side (ontology labels/predicates, series scope, current visibility, server-derived `visible_from_order` not exceeding progress, `origin:user` assignment) before applying it as one transaction, rolling back entirely on failure, and preventing idempotency-key replay.
- [x] **RAG-13**: `origin:canonical` and `origin:candidate` resources remain non-mutable by the assistant; requested edits to them produce a user-origin note/override proposal instead of a silent write, matching the existing origin-protection invariant from Phase 3.
- [ ] **RAG-14**: Destructive or multi-element ChangeSets require explicit frontend confirmation (the chat message itself is not confirmation); confirmation re-validates current user/progress/origin/version, and a ChangeSet whose snapshot boundary exceeds the user's since-lowered progress becomes non-applicable.
- [ ] **RAG-15**: Every applied ChangeSet is recorded as an auditable Revision (extending the existing Phase 4 revision model) with before/after state and no secrets/tokens stored; user-origin changes support revert.

#### Frontend Chat & Graph Sync

- [x] **RAG-16**: A chat interface integrated into the existing graph workspace (Inspector/Chat modes or resizable split) supports streaming, citations with "show in graph", proposed-change preview/confirm/reject cards, and a disabled-provider state — without displaying raw tool calls, Cypher, or hidden metadata.
- [ ] **RAG-17**: Answering a question with `graph_focus` highlights/dims the relevant existing Cytoscape nodes/edges without destroying the user's view; applying a ChangeSet refreshes only affected graph data preserving episode filtering, images, and layout stability; lowering progress immediately hides graph/chat/citation content beyond the new boundary and invalidates unsafe draft ChangeSets.

**Phase 6 traceability:**

| Requirement | Phase | Status |
|-------------|-------|--------|
| RAG-01..RAG-17 | Phase 6 | Pending |

**Coverage:** 17 Phase 6 requirements; 17 mapped exactly once; 0 unmapped; tracked outside the Prototype v0 30/30 table above.

## Traceability

Each Prototype v0 requirement has exactly one primary phase assignment.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| META-01 | Phase 1 | Complete |
| META-02 | Phase 1 | Complete |
| META-03 | Phase 1 | Complete |
| API-01 | Phase 1 | Complete |
| API-02 | Phase 1 | Complete |
| API-03 | Phase 1 | Complete |
| API-04 | Phase 1 | Complete |
| SEED-01 | Phase 1 | Complete |
| SEED-02 | Phase 1 | Complete |
| SEED-03 | Phase 1 | Complete |
| SEED-04 | Phase 1 | Complete |
| UI-01 | Phase 2 | Complete |
| UI-02 | Phase 2 | Complete |
| UI-03 | Phase 2 | Complete |
| UI-04 | Phase 2 | Complete |
| UI-05 | Phase 2 | Complete |
| NOTE-01 | Phase 3 | Pending |
| NOTE-02 | Phase 3 | Pending |
| NOTE-03 | Phase 3 | Pending |
| REV-01 | Phase 4 | Pending |
| REV-02 | Phase 4 | Pending |
| REV-03 | Phase 4 | Pending |
| PREP-01 | Phase 5 | Pending |
| PREP-02 | Phase 5 | Pending |
| PREP-03 | Phase 5 | Pending |
| PREP-04 | Phase 5 | Pending |
| PREP-05 | Phase 5 | Pending |

**Coverage:** 30 Prototype v0 requirements; 30 mapped exactly once; 0 unmapped; 5 delivery phases covering 8 canonical milestones.

---
*Last updated: 2026-07-29 — rebaselined into five vertical delivery phases while preserving all canonical Prototype v0 requirements*
