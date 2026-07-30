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
- Spoiler-aware LLM chat and graph-RAG tools (root milestone 9).
- Multi-user/authentication, collaboration, production deployment/public hosting, mobile/social features.

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
