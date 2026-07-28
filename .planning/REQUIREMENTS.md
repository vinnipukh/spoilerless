# Requirements: HD Graf Cehennemi — Prototype v0

**Defined:** 2026-07-28
**Canonical scope:** root `ROADMAP.md`, Prototype v0 milestones 1–8
**Core Value:** Backend-enforced watch progress lets users safely explore an evidence-backed narrative graph without spoilers.

All requirements below are pending until their acceptance evidence is executed. Existing scaffolds are brownfield inputs, not proof of completion.

## Prototype v0 Requirements

### Phase 1 — Local Infrastructure

- [ ] **INFRA-01**: Neo4j, FastAPI, and React development services start locally and their Browser, Swagger, and app URLs are reachable.
- [ ] **INFRA-02**: `/health` performs and reports a real Neo4j connectivity check, including unavailable behavior.
- [ ] **INFRA-03**: Backend lifecycle, parameterized queries, managed transactions, and application-level Neo4j error handling are testable without import-time connection side effects.

### Phase 2 — Metadata Graph

- [ ] **META-01**: A reliable, idempotent setup command creates uniqueness/existence constraints needed by Prototype v0.
- [ ] **META-02**: Setup persists Dexter, S01E01–03, `PART_OF`, and `PRECEDES` with correct order and `visible_from_order` metadata.
- [ ] **META-03**: `GET /api/series` and `GET /api/series/{series_id}/episodes` return the persisted series and three ordered episodes through serializable response models.

### Phase 3 — Spoiler-Aware Graph API

- [ ] **API-01**: `GET /api/graph` requires series and watch-progress inputs and returns serializable nodes, edges, claims, and boundary metadata.
- [ ] **API-02**: Cypher/data-access filtering enforces `visible_from_order` on nodes, relationships, claims, sources, and evidence before response construction.
- [ ] **API-03**: Claim validity (`valid_from_order`/`valid_until_order`) is enforced independently from spoiler visibility and graph closure is preserved.
- [ ] **API-04**: Boundary tests at orders 1, 2, and 3 prove future nodes, edges, claims, names, labels, evidence, and counts do not leak; invalid inputs have defined errors.

### Phase 4 — Evidence-Backed Manual Seed Graph

- [ ] **SEED-01**: Manual Dexter S01E01–03 seed data defines selected Character and relationship/atomic Claim records with visibility, confidence, relationship effect, status, and validity metadata.
- [ ] **SEED-02**: Source and EvidenceFragment records include episode references and locators (timestamp, page, or scene), plus retrieval metadata/content hashes where available.
- [ ] **SEED-03**: Every seeded claim links to at least one EvidenceFragment and its Source, and setup remains idempotent after loading the complete graph.
- [ ] **SEED-04**: Executed graph queries and API checks demonstrate a small evidence-backed network at each allowed episode boundary.

### Phase 5 — React/Cytoscape Exploration and Spoiler UX

- [ ] **UI-01**: The Vite starter is replaced by a React/TypeScript product layout that loads series, episodes, and graph data from the backend.
- [ ] **UI-02**: A watch-progress selector confirms advancement before unlocking a later episode and safely refreshes the applied backend boundary.
- [ ] **UI-03**: Cytoscape renders only returned nodes/edges and visibly updates as S01E01, S01E02, and S01E03 become allowed.
- [ ] **UI-04**: Node and edge/claim detail views explain relationships and display linked source/evidence episode locators.
- [ ] **UI-05**: Frontend build/lint/component checks and demo UX checks verify safe progress changes and absence of hidden-data rendering.

### Phase 6 — User Notes and Manual Editing

- [ ] **NOTE-01**: A UserNote model/API/UI lets a user create, read, update, and delete a note attached to a character or claim.
- [ ] **NOTE-02**: APIs and UI allow creating/editing user-owned custom nodes and relationships without mutating canonical knowledge.
- [ ] **NOTE-03**: Storage metadata and visual treatment clearly distinguish user-created content from canonical and candidate/automatic content.

### Phase 7 — Revision History and Revert

- [ ] **REV-01**: An append-only Revision model logs claim creation/update/rejection, user corrections, manual graph edits, and relevant before/after values.
- [ ] **REV-02**: A history panel displays prior values and the action/provenance behind each revision.
- [ ] **REV-03**: Revert restores a selected prior value by creating a new revision and never deletes existing history; tests prove this behavior.

### Phase 8 — Future-Extraction Preparation

- [ ] **PREP-01**: A versioned extraction-output JSON schema represents atomic candidate claims, visibility/validity, confidence/effect, and evidence references.
- [ ] **PREP-02**: Candidate claims are stored separately from canonical and user-created knowledge and cannot become canonical without review.
- [ ] **PREP-03**: API/UI review supports approve, reject, and edit actions, with evidence visible and every action revision-logged.
- [ ] **PREP-04**: A source-connector interface accepts normalized source/evidence payloads without implementing external retrieval or parsing.
- [ ] **PREP-05**: A fixture-driven acceptance test proves structured candidates from a hypothetical future extractor can enter review and be resolved without changing the core graph model or invoking an LLM.

## Post-v0 Requirements

- Automated retrieval/ingestion from OpenSubtitles, scripts/PDFs, podcasts, Fandom/IMDb/news, or external sites.
- Operational LLM extraction pipeline.
- Spoiler-aware LLM chat and graph-RAG tools (root milestone 9).
- Multi-user/authentication, collaboration, production deployment/public hosting, mobile/social features.

## Traceability

Each Prototype v0 requirement has exactly one primary phase assignment.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| INFRA-03 | Phase 1 | Pending |
| META-01 | Phase 2 | Pending |
| META-02 | Phase 2 | Pending |
| META-03 | Phase 2 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| API-03 | Phase 3 | Pending |
| API-04 | Phase 3 | Pending |
| SEED-01 | Phase 4 | Pending |
| SEED-02 | Phase 4 | Pending |
| SEED-03 | Phase 4 | Pending |
| SEED-04 | Phase 4 | Pending |
| UI-01 | Phase 5 | Pending |
| UI-02 | Phase 5 | Pending |
| UI-03 | Phase 5 | Pending |
| UI-04 | Phase 5 | Pending |
| UI-05 | Phase 5 | Pending |
| NOTE-01 | Phase 6 | Pending |
| NOTE-02 | Phase 6 | Pending |
| NOTE-03 | Phase 6 | Pending |
| REV-01 | Phase 7 | Pending |
| REV-02 | Phase 7 | Pending |
| REV-03 | Phase 7 | Pending |
| PREP-01 | Phase 8 | Pending |
| PREP-02 | Phase 8 | Pending |
| PREP-03 | Phase 8 | Pending |
| PREP-04 | Phase 8 | Pending |
| PREP-05 | Phase 8 | Pending |

**Coverage:** 30 Prototype v0 requirements; 30 mapped exactly once; 0 unmapped; 8 phases.

---
*Last updated: 2026-07-28 — reconciled to canonical root Prototype v0 milestones 1–8*
