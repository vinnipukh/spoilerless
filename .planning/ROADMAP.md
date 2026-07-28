# HD Graf Cehennemi — Prototype v0 Roadmap

**Canonical scope:** root `ROADMAP.md`, milestones 1–8
**Target:** Complete Dexter S01E01–03 demo story, not an API-only release
**Mode:** dependency-ordered Prototype v0 delivery
**Status:** all phases pending; brownfield scaffolds are inputs, not verified completion

## Phase 1: Local Infrastructure

**Goal:** Establish executable local Neo4j/FastAPI/React services and trustworthy runtime health.

**Requirements:** INFRA-01, INFRA-02, INFRA-03
**Dependencies:** None

**Success criteria:** Browser, Swagger, and React URLs are exercised; `/health` reports actual database state; backend lifecycle/error/query patterns are testable and verified rather than inferred from scaffold files.

## Phase 2: Metadata Graph

**Goal:** Reliably persist and serve Dexter plus ordered S01E01–03 metadata.

**Requirements:** META-01, META-02, META-03
**Dependencies:** Phase 1

**Success criteria:** idempotent setup creates constraints, one Series, three Episodes, `PART_OF` and `PRECEDES`; the canonical metadata query returns one series/three episodes; metadata endpoints return persisted ordered data.

## Phase 3: Spoiler-Aware Graph API

**Goal:** Enforce the central spoiler boundary at data access before graph data reaches a client.

**Requirements:** API-01, API-02, API-03, API-04
**Dependencies:** Phase 2

**Success criteria:** boundary 1 excludes all S01E02/03 data; thresholds 1–3 are tested; hidden labels, names, evidence, and counts do not leak; every edge closes over returned nodes; invalid input behavior is verified.

## Phase 4: Evidence-Backed Manual Seed Graph

**Goal:** Provide the source-linked Dexter narrative graph needed by the Prototype v0 demo.

**Requirements:** SEED-01, SEED-02, SEED-03, SEED-04
**Dependencies:** Phases 2–3

**Success criteria:** selected Characters and atomic Claims for S01E01–03 are manually curated; every claim has episode-located evidence and a source; full seeding is idempotent; executed queries/API checks show evidence-backed networks at each boundary.

## Phase 5: React/Cytoscape Exploration and Spoiler UX

**Goal:** Deliver the usable graph exploration flow from the root demo story.

**Requirements:** UI-01, UI-02, UI-03, UI-04, UI-05
**Dependencies:** Phases 3–4

**Success criteria:** the user selects Dexter and S01E01, sees only allowed Cytoscape elements, opens character/claim details and evidence, receives confirmation before advancing, and sees newly unlocked data after confirmation; frontend checks pass.

## Phase 6: User Notes and Manual Editing

**Goal:** Let the user add personal knowledge while preserving provenance and canonical data.

**Requirements:** NOTE-01, NOTE-02, NOTE-03
**Dependencies:** Phase 5

**Success criteria:** a note can be attached to a character/claim and shown in details; custom nodes/relationships can be created/edited; user content is stored and rendered distinctly from canonical/candidate content.

## Phase 7: Revision History and Revert

**Goal:** Make corrections inspectable and reversible without destroying history.

**Requirements:** REV-01, REV-02, REV-03
**Dependencies:** Phase 6

**Success criteria:** each covered edit/rejection/correction creates a revision; old values are visible; reverting appends a revision and preserves history; UI and automated checks demonstrate the flow.

## Phase 8: Future-Extraction Preparation

**Goal:** Accept and review future extractor output without implementing extraction or an LLM.

**Requirements:** PREP-01, PREP-02, PREP-03, PREP-04, PREP-05
**Dependencies:** Phases 4 and 7

**Success criteria:** a versioned structured fixture enters a separate candidate layer through stable contracts, evidence is reviewable, approve/reject/edit is revision-logged, and the graph model needs no change. No automated source ingestion, extraction model, or LLM is run.

## Prototype v0 Release Gate

Prototype v0 is complete only when all eight phases have executed evidence and the root demo can be performed end-to-end: open app; choose Dexter/S01E01; inspect only allowed source-backed knowledge; confirm progress advancement; see newly unlocked elements; add a note; edit a claim; inspect history/revert. Preparation contracts must accept fixture candidates. File presence or scaffold status alone cannot pass a gate.

## Post-v0

Actual source retrieval/parsing/ingestion, operational LLM extraction, and LLM chat/graph-RAG (root milestone 9) remain post-v0, along with auth, multi-user collaboration, and deployment.

## Requirements Coverage

| Phase | Canonical milestone/capability | Requirements | Count | Status |
|-------|--------------------------------|--------------|------:|--------|
| Phase 1 | Milestone 1 — local infrastructure | INFRA-01..03 | 3 | Pending |
| Phase 2 | Milestone 2 — metadata graph | META-01..03 | 3 | Pending |
| Phase 3 | Milestone 3 — spoiler-aware API | API-01..04 | 4 | Pending |
| Phase 4 | Milestone 4 — manual seed graph | SEED-01..04 | 4 | Pending |
| Phase 5 | Milestone 5 — frontend graph UI | UI-01..05 | 5 | Pending |
| Phase 6 | Milestone 6 — notes/manual editing | NOTE-01..03 | 3 | Pending |
| Phase 7 | Milestone 7 — revision history | REV-01..03 | 3 | Pending |
| Phase 8 | Milestone 8 — extraction preparation | PREP-01..05 | 5 | Pending |

**Coverage:** 30/30 Prototype v0 requirements mapped once across 8/8 phases; 0 unmapped.

## Risks and Controls

| Risk | Control |
|------|---------|
| Relationship traversal leaks future facts | Filter both endpoints and relationship/claim/evidence metadata in Cypher; test response text and counts |
| Seed/provenance quality weakens demo | Require episode-located EvidenceFragment per seeded claim and inspect the displayed rationale |
| Scaffolds mistaken for finished work | Keep phases pending until commands and acceptance checks execute |
| User edits blur canonical truth | Separate ownership/origin in model and visual design; revision-log mutations |
| Preparation expands into extraction | Use fixtures/contracts only; keep connectors non-operational in v0 |

---
*Last updated: 2026-07-28 — reconciled to canonical root Prototype v0 milestones 1–8*
