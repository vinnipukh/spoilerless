# HD Graf Cehennemi — Prototype v0 Roadmap

**Canonical scope:** root `ROADMAP.md`, milestones 1–8
**Target:** Complete Dexter S01E01–03 demo story, not an API-only release
**Mode:** dependency-ordered Prototype v0 delivery
**Status:** Phase 1 complete and verified (9/9 truths, 13/13 tests, smoke 8/8); Phase 2 pending

## Phase 1: Backend Graph Foundation

**Goal:** Deliver the minimum reliable backend and Neo4j graph foundation required for the visual prototype: executable local services, ontology-aligned deterministic data, evidence-backed graph records, and backend-enforced spoiler filtering.

**Requirements:** INFRA-01, INFRA-02, INFRA-03, META-01, META-02, META-03, API-01, API-02, API-03, API-04, SEED-01, SEED-02, SEED-03, SEED-04
**Dependencies:** None

**Success criteria:** Neo4j, FastAPI, and React development services remain executable; `/health` reports real Neo4j state; a deterministic idempotent command creates required constraints and seeds Dexter S01E01–03 metadata plus a small ontology-aligned Character/Event/Location/Claim/Source/EvidenceFragment graph; every graph-visible record has a stable string ID and every spoiler-sensitive record has `visible_from_order`; metadata and graph endpoints use parameterized Cypher and return only data allowed by validated `episode_order`; automated tests prove an S01E01 request contains no S01E02/S01E03 nodes, edges, claims, evidence, names, labels, or counts.

## Phase 2: Polished Cytoscape Graph Experience

**Goal:** Turn the verified backend graph foundation into a polished visual prototype centered on the Cytoscape exploration flow.

**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05
**Dependencies:** Phase 1

**Success criteria:** the user selects Dexter and S01E01, sees only allowed Cytoscape elements, opens character/claim details and evidence, receives confirmation before advancing, and sees newly unlocked data after confirmation; frontend checks pass.

## Phase 3: User Notes and Manual Editing

**Goal:** Let the user add personal knowledge while preserving provenance and canonical data.

**Requirements:** NOTE-01, NOTE-02, NOTE-03
**Dependencies:** Phase 2

**Success criteria:** a note can be attached to a character/claim and shown in details; custom nodes/relationships can be created/edited; user content is stored and rendered distinctly from canonical/candidate content.

**Backend execution status:** Complete and verified in `backend-work` — Plans `03-01`, `03-02`, and `03-03` are complete (3/3). This does not complete Phase 3: Phase 2, frontend integration, and distinct visual treatment remain pending in `frontend-work`.

**Wave 1**

- `03-01` — strict user-content models, shared error/OpenAPI contracts, and Wave-0 tests. **Complete 2026-07-29.**

**Wave 2**

- `03-02` — managed Neo4j writes, canonical-preserving setup, and all series-scoped note/custom-content CRUD operations. **Complete 2026-07-29.**

**Wave 3**

- `03-03` — spoiler-safe graph projection, setup preservation regressions, exact OpenAPI verification, and frontend contract handoff. **Complete and verified 2026-07-29.**

**Cross-cutting constraints:** preserve Phase 1 fail-closed spoiler filtering and graph closure; mutate only namespaced `origin=user` resources; keep canonical/candidate provenance mandatory; keep all frontend files untouched; do not mark overall Phase 3 complete from backend evidence alone.

## Phase 4: Revision History and Revert

**Goal:** Make corrections inspectable and reversible without destroying history.

**Requirements:** REV-01, REV-02, REV-03
**Dependencies:** Phase 3

**Success criteria:** each covered edit/rejection/correction creates a revision; old values are visible; reverting appends a revision and preserves history; UI and automated checks demonstrate the flow.

## Phase 5: Future-Extraction Preparation

**Goal:** Accept and review future extractor output without implementing extraction or an LLM.

**Requirements:** PREP-01, PREP-02, PREP-03, PREP-04, PREP-05
**Dependencies:** Phases 1 and 4

**Success criteria:** a versioned structured fixture enters a separate candidate layer through stable contracts, evidence is reviewable, approve/reject/edit is revision-logged, and the graph model needs no change. No automated source ingestion, extraction model, or LLM is run.

## Prototype v0 Release Gate

Prototype v0 is complete only when all five delivery phases have executed evidence and all eight canonical root-roadmap milestones are covered. The root demo must run end-to-end: open app; choose Dexter/S01E01; inspect only allowed source-backed knowledge; confirm progress advancement; see newly unlocked elements; add a note; edit a claim; inspect history/revert. Preparation contracts must accept fixture candidates. File presence or scaffold status alone cannot pass a gate.

## Post-v0

Actual source retrieval/parsing/ingestion, operational LLM extraction, and LLM chat/graph-RAG (root milestone 9) remain post-v0, along with auth, multi-user collaboration, and deployment.

## Requirements Coverage

| Phase | Canonical milestone/capability | Requirements | Count | Status |
|-------|--------------------------------|--------------|------:|--------|
| Phase 1 | Milestones 1–4 — infrastructure, metadata, spoiler-aware API, manual seed graph | INFRA-01..03, META-01..03, API-01..04, SEED-01..04 | 14 | Complete — verified |
| Phase 2 | Milestone 5 — frontend graph UI | UI-01..05 | 5 | Pending |
| Phase 3 | Milestone 6 — notes/manual editing | NOTE-01..03 | 3 | Backend slice complete/verified (3/3); overall pending frontend |
| Phase 4 | Milestone 7 — revision history | REV-01..03 | 3 | Pending |
| Phase 5 | Milestone 8 — extraction preparation | PREP-01..05 | 5 | Pending |

**Coverage:** 30/30 Prototype v0 requirements mapped once across 5 delivery phases covering 8/8 canonical milestones; 0 unmapped.

## Risks and Controls

| Risk | Control |
|------|---------|
| Relationship traversal leaks future facts | Filter both endpoints and relationship/claim/evidence metadata in Cypher; test response text and counts |
| Seed/provenance quality weakens demo | Require episode-located EvidenceFragment per seeded claim and inspect the displayed rationale |
| Scaffolds mistaken for finished work | Keep phases pending until commands and acceptance checks execute |
| User edits blur canonical truth | Separate ownership/origin in model and visual design; revision-log mutations |
| Preparation expands into extraction | Use fixtures/contracts only; keep connectors non-operational in v0 |

---
*Last updated: 2026-07-29 — Phase 3 backend Plans 03-01 through 03-03 complete and verified; Phase 2 and Phase 3 frontend acceptance remain pending; canonical root Prototype v0 milestones 1–8 preserved*
