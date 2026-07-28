# Requirements: HD Graf Cehennemi — Prototype v0

**Defined:** 2026-07-28
**Core Value:** Users can safely explore a TV series knowledge graph without ever seeing spoilers — the backend guarantees the frontend never receives data beyond their selected watch progress.

## v1 Requirements

Requirements for initial prototype release. Focus: Core graph API + spoiler gating first (backend-heavy), frontend UI deferred after API is proven.

### Infrastructure & Seed

- [ ] **INFRA-01**: Health endpoint verifies actual Neo4j connectivity (currently hardcoded "connected"), returning database status
- [ ] **INFRA-02**: Seed script can be run as a reliable one-step setup (`cd backend && uv run seed`) that creates constraints, nodes, and relationships
- [ ] **DATA-01**: Character seed file (JSON) with Dexter S01E01 character nodes (Dexter, Debra, Brian, Batista, LaGuerta, etc.)
- [ ] **DATA-02**: Source seed file with known source references (episode scripts, transcript timestamps)
- [ ] **DATA-03**: Evidence seed file linking claims to specific episode/locator evidence
- [ ] **DATA-04**: Claim seed file with Dexter S01E01 character relationships (KNOWS, FAMILY_OF, KILLS, WORKS_WITH) with evidence links

### Spoiler-Gated Graph API

- [ ] **GRAPH-01**: Spoiler-aware graph endpoint `GET /api/graph?series_id=...&visible_until_order=N` that returns nodes, relationships, and claims within the user's spoiler boundary
- [ ] **GRAPH-02**: Every seeded node has a `visible_from_order` field; every relationship and claim respects it
- [ ] **GRAPH-03**: Claims carry `valid_from_order` and `valid_until_order` for temporal validity
- [ ] **GRAPH-04**: `visible_from_order` filtering is enforced at the Cypher level — never post-processed in Python
- [ ] **GRAPH-05**: Neo4j constraints for all node types (Series, Episode, Character, Claim, Source, EvidenceFragment)
- [ ] **GRAPH-06**: Pydantic response models for graph endpoint (nodes, edges as serializable dicts — never raw Neo4j Node/Relationship objects)

### Backend Architecture

- [ ] **ARCH-01**: Neo4j driver uses lazy initialization (not import-time singleton) to support testability
- [ ] **ARCH-02**: Cypher queries use parameterized `$param` placeholders everywhere (already done in existing code)
- [ ] **ARCH-03**: Neo4j session access uses `execute_query` (v6 default API) or `execute_read/execute_write` managed transactions instead of inline `session.run()` in route handlers
- [ ] **ARCH-04**: Duplicate FastAPI app construction in `main.py` removed
- [ ] **ARCH-05**: Error handling translates Neo4j errors into application-level HTTP responses

### Testing & Verification

- [ ] **TEST-01**: Health endpoint returns correct status with and without Neo4j running
- [ ] **TEST-02**: Seed script idempotent (running twice doesn't duplicate nodes)
- [ ] **TEST-03**: Graph endpoint returns correct data when `visible_until_order=1` (excludes S01E02/S01E03 content)
- [ ] **TEST-04**: Graph endpoint returns 400 for missing required query parameters

## v2 Requirements

Deferred to future release after core graph API + spoiler gating is proven.

### Frontend Graph UI

- **UI-01**: Frontend replaces Vite starter with product layout
- **UI-02**: Episode progress selector with spoiler confirmation modal
- **UI-03**: Cytoscape.js graph rendering from backend graph endpoint
- **UI-04**: Node detail panel (character info, claims, evidence links)
- **UI-05**: Edge/claim detail panel

### User Content & Editing

- **NOTE-01**: UserNote model, CRUD endpoints, and frontend display
- **NOTE-02**: User-created nodes and relationships (custom additions)

### Revision History

- **REV-01**: Revision model logging claim creation, updates, rejection, corrections
- **REV-02**: Revision display panel and revert operation

### LLM Preparation

- **LLM-01**: Candidate claim layer, review/approve/reject workflow, source connector interface

### Full Test Suite

- **TEST-v2-01**: Backend unit tests for all routes, spoiler boundaries, seed
- **TEST-v2-02**: Frontend component tests
- **CI-01**: GitHub Actions workflow for test/lint/build on push

## Out of Scope

Explicitly excluded for prototype v0.

| Feature | Reason |
|---------|--------|
| Multi-user accounts & auth | Single-user local prototype; auth overhead irrelevant |
| Real-time collaborative editing | WebSocket sync + CRDT enormous complexity for zero current need |
| Live LLM chat | LLM must be spoiler-gated at retrieval layer — Milestone 9 for a reason |
| Automated scraping pipeline | Maintenance burden, legal ambiguity, data quality varies |
| Mobile app / push notifications | Desktop web-first prototype; mobile UX is separate project |
| Social features (comments, likes, sharing) | Content moderation, spoiler leakage through comments |
| Public hosting / deployment | Local-only prototype; spoiler safety undermined by public access |
| Auto-magic graph layout | Ship with Cose layout; add switching as power-user option later |
| Individual spoiler tags on elements | Systematic episode-boundary spoiler gating is superior |

## Traceability

Updated during roadmap creation — all 21 v1 requirements mapped to Phase 1 or Phase 2.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INFRA-01 | Phase 1 | Pending |
| INFRA-02 | Phase 1 | Pending |
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| GRAPH-01 | Phase 2 | Pending |
| GRAPH-02 | Phase 2 | Pending |
| GRAPH-03 | Phase 2 | Pending |
| GRAPH-04 | Phase 2 | Pending |
| GRAPH-05 | Phase 2 | Pending |
| GRAPH-06 | Phase 2 | Pending |
| ARCH-01 | Phase 1 | Pending |
| ARCH-02 | Phase 1 | Pending |
| ARCH-03 | Phase 1 | Pending |
| ARCH-04 | Phase 1 | Pending |
| ARCH-05 | Phase 1 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 1 | Pending |
| TEST-03 | Phase 2 | Pending |
| TEST-04 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-28*
*Last updated: 2026-07-28 — traceability mapped to roadmap phases*
