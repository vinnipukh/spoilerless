# HD Graf Cehennemi — Prototype v0 Roadmap

**Canonical scope:** root `ROADMAP.md`, milestones 1–8
**Target:** Complete Dexter S01E01–03 demo story, not an API-only release
**Mode:** dependency-ordered Prototype v0 delivery
**Status:** Phase 1 complete and verified (9/9 truths, 13/13 tests, smoke 8/8); Phase 2 complete and verified (5/5 truths, 25/25 tests, 0 gaps); Phase 03.1 (visual overhaul) complete — UAT verified (16/16); Phase 3 complete — full-stack (Notes UI, custom nodes/relationships, origin distinction); Phase 4 complete — full-stack verified (5/5 plans, 146/146 backend, 13/13 frontend new tests)

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

**Plans:** 4/4 plans executed

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Dependencies, test infra & tracer slice: types/API client/hooks/sessionStorage-gated confirmation modal/minimal Cytoscape render/minimal detail panel, replacing the Vite starter end-to-end

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Graph canvas polish: cose-bilkent layout, full node-type/origin stylesheet, selection highlight/fade, loading/error/empty overlay states
- [x] 02-03-PLAN.md — Detail panel split: Overview/Claims/Evidence tabbed Sheet (nodes/claim-backed edges) vs. tab-less StructuralEdgeCard (structural edges)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-04-PLAN.md — Remaining component tests, tree-wide threat-mitigation grep audit, full-suite verification, and demo UAT

## Phase 3: User Notes and Manual Editing

**Goal:** Let the user add personal knowledge while preserving provenance and canonical data.

**Requirements:** NOTE-01, NOTE-02, NOTE-03
**Dependencies:** Phase 2

**Success criteria:** a note can be attached to a character/claim and shown in details; custom nodes/relationships can be created/edited; user content is stored and rendered distinctly from canonical/candidate content.

**Execution status:** Complete — full-stack. Backend (3/3 plans: 03-01, 03-02, 03-03) complete and verified independently. Frontend (03-04-frontend-PLAN.md) implemented: Notes tab in DetailPanel, custom node creation FAB, custom relationship dialog, user-origin visual distinction (dashed borders + "User" badge). All wired and build-clean.

**Verification:** `03-VERIFICATION.md` passed with 11/11 backend truths, 20/20 artifacts, 11/11 critical links, 28/28 decisions, 0 gaps. Frontend acceptance: Notes tab, custom node/relationship dialogs, origin-based visual distinction verified present in code.

**Wave 1**

- `03-01` — strict user-content models, shared error/OpenAPI contracts, and Wave-0 tests. **Complete 2026-07-29.**

**Wave 2**

- `03-02` — managed Neo4j writes, canonical-preserving setup, and all series-scoped note/custom-content CRUD operations. **Complete 2026-07-29.**

**Wave 3**

- `03-03` — spoiler-safe graph projection, setup preservation regressions, exact OpenAPI verification, and frontend contract handoff. **Complete and verified 2026-07-29.**

**Cross-cutting constraints:** preserve Phase 1 fail-closed spoiler filtering and graph closure; mutate only namespaced `origin=user` resources; keep canonical/candidate provenance mandatory; keep all frontend files untouched; do not mark overall Phase 3 complete from backend evidence alone.

### Phase 03.1: Frontend visual overhaul - cinematic graph exploration UI (INSERTED)

**Goal:** Turn the existing functional Cytoscape graph interface into a premium, cinematic, high-contrast graph exploration product — the graph as hero, colorful type-aware nodes and relationship-colored edges, a polished application shell/episode navigation, and a premium detail-panel inspector — frontend-only, with zero regression to auth, spoiler filtering, or existing Character/Claim/Evidence interactions.

**Requirements**: None — out-of-band UI/UX initiative requested directly on `feature/graph-visual-overhaul`; not mapped to a canonical Prototype v0 requirement ID (see `03.1-CONTEXT.md`). Traceability uses `03.1-CONTEXT.md` decision IDs D-01 through D-35 instead.
**Depends on:** Phase 2 (Polished Cytoscape Graph Experience — the UI this phase restyles)
**Plans:** 4 plans

Plans:
**Wave 1**

- [x] 03.1-01-PLAN.md — Graph canvas visual system: font/token foundation, relationshipStyles.ts edge-color module, tuned layout/zoom, full node/edge type coverage, candidate-status dashed edges, selection/hover overlay glow, background grid/glow, reduced motion
- [x] 03.1-02-PLAN.md — Detail panel restructure: Overview tab metadata rows, Claims/Evidence card accents, StructuralEdgeCard polish, responsive Sheet breakpoints

**Wave 2** *(blocked on 03.1-01 completion)*

- [x] 03.1-03-PLAN.md — App shell & episode navigation restyle: Space Grotesk wordmark, segmented episode control (with preserved Select fallback), SeriesSelect polish
- [x] 03.1-04-PLAN.md — Graph canvas overlays: collapsible legend + zoom/fit/reset controls

## Phase 4: Revision History and Revert

**Goal:** Make corrections inspectable and reversible without destroying history.

**Requirements:** REV-01, REV-02, REV-03
**Dependencies:** Phase 3

**Success criteria:** each covered edit/rejection/correction creates a revision; old values are visible; reverting appends a revision and preserves history; UI and automated checks demonstrate the flow.

**Plans:** 5/5 plans executed — full-stack complete (backend 146/146, frontend History tab + revert UI with 13 new tests)

**Wave 1**

- [x] 04-01-PLAN.md — Revision domain model, RevisionRepository, user-content integration, seed constraints

**Wave 2**

- [x] 04-02-PLAN.md — Revision API routes (list, get, revert) + revert business logic
- [x] 04-03-PLAN.md — Integration tests (lifecycle, filters, revert, spoiler, regression)

**Wave 3** (frontend)

- [x] 04-04-PLAN.md — Frontend data layer: types, API client, useRevisions hook, tests
- [x] 04-05-PLAN.md — History tab + revert UI in DetailPanel, component tests

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
| Phase 2 | Milestone 5 — frontend graph UI | UI-01..05 | 5 | Complete — verified |
| Phase 3 | Milestone 6 — notes/manual editing | NOTE-01..03 | 3 | Complete — full-stack |
| Phase 4 | Milestone 7 — revision history | REV-01..03 | 3 | Complete — full-stack verified |
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

### Phase 6: Spoiler-safe GraphRAG chat and graph-editing agent

**Goal:** Add a conversational interface where the authenticated user asks questions about the selected series and receives answers grounded only in graph data visible up to their persisted watch progress (backend-authoritative, never frontend-supplied), with clickable Claim/Evidence/Source citations and graph highlighting; support safe graph modification through a typed propose/confirm ChangeSet flow that never lets the LLM execute Cypher directly, preserves the canonical/candidate mutation invariant, and records every applied edit as an auditable revision.
**Requirements**: RAG-01..RAG-17
**Depends on:** Phase 3 (Notes/custom-content origin model this phase extends), Phase 4 (revision/audit model this phase extends)
**Plans:** 3/12 plans executed

**Success criteria:** the LLM never receives a raw Neo4j driver, unrestricted Cypher, or graph/chat content beyond the user's persisted `visible_until_order`; every retrieval and mutation tool is allowlisted, parameterized, and independently fail-closed; chat history obeys the same spoiler boundary (lowering progress hides future-boundary messages/citations without deleting them); citations are validated against retrieved context; user-origin ChangeSets apply transactionally with revision/audit metadata after explicit confirmation while `origin:canonical`/`origin:candidate` resources stay protected; existing graph/auth/Notes/revision/spoiler behavior has zero regression; backend + frontend automated test suites, lint, typecheck, and production build all pass; a documented manual acceptance checklist is executed before the branch is called safe to commit.

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Tracer: backend GraphRAG pipeline end-to-end (LLM provider, persisted progress, one retrieval tool, chat persistence, streaming answer with validated citation)

**Wave 2** *(blocked on 06-01)*

- [x] 06-02-PLAN.md — Remaining 8 retrieval tools + citation grounding + prompt-injection hardening
- [x] 06-03-PLAN.md — Watch-progress ownership/fail-closed hardening
- [ ] 06-04-PLAN.md — Chat persistence (hide-not-delete regression) + REST completeness

**Wave 3** *(blocked on Wave 2)*

- [ ] 06-05-PLAN.md — ChangeSet propose stage + canonical/candidate protection
- [ ] 06-08-PLAN.md — Frontend chat/progress/ChangeSet data layer (types, API clients, hooks)

**Wave 4** *(blocked on Wave 3)*

- [ ] 06-06-PLAN.md — ChangeSet confirm/apply, idempotency, revision audit
- [ ] 06-09-PLAN.md — Frontend chat UI (DetailPanel mode toggle, ChatLauncher, message list, citations)

**Wave 5** *(blocked on Wave 4)*

- [ ] 06-07-PLAN.md — ChangeSet revert
- [ ] 06-10-PLAN.md — Frontend watch-progress backend wiring + graph-focus sync

**Wave 6** *(blocked on Wave 5)*

- [ ] 06-11-PLAN.md — Frontend ChangeSetCard + post-apply graph refresh

**Wave 7** *(blocked on Wave 6)*

- [ ] 06-12-PLAN.md — Full regression, documentation, manual acceptance checklist (human checkpoint)

---
*Last updated: 2026-07-30 — Phase 03.1 (visual overhaul) complete UAT 16/16; Phase 3 full-stack (Notes UI + custom content); Phase 4 full-stack verified; 21/21 plans across 5 completed phases; Phase 5 pending

### Phase 05.1: Candidate review frontend UI - approve/reject/edit workflow deferred from Phase 5 (INSERTED)

**Goal:** [Urgent work - to be planned]
**Requirements**: TBD
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:

- [ ] TBD (run /gsd-plan-phase 05.1 to break down)
