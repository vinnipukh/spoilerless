# HD Graf Cehennemi — Roadmap

## Milestones

- ✅ **v1.0 Prototype v0** — Phases 1–5 (+ 03.1, 05.1 inserted) (shipped 2026-07-30)
- ✅ **v1.1 MVP** — Phases 1–6 (+ 03.1, 05.1 inserted) (shipped 2026-08-02, supersedes v1.0 — adds Phase 6 GraphRAG chat)
- 🔄 **v1.2 Spoiler-Safety Hardening** — Phase 7 (in planning 2026-08-02)

## Phases

<details>
<summary>✅ v1.1 MVP (Phases 1–6, + 03.1, 05.1) — SHIPPED 2026-08-02</summary>

- [x] Phase 1: Backend Graph Foundation (1/1 plan) — completed 2026-07-28
- [x] Phase 2: Polished Cytoscape Graph Experience (4/4 plans) — completed 2026-07-29
- [x] Phase 03.1: Frontend visual overhaul — cinematic graph exploration UI (4/4 plans, inserted) — completed 2026-07-29
- [x] Phase 3: User Notes and Manual Editing (4/4 plans, full-stack) — completed 2026-07-29
- [x] Phase 4: Revision History and Revert (5/5 plans) — completed 2026-07-30
- [x] Phase 5: Future-Extraction Preparation (4/4 plans) — completed 2026-07-30
- [x] Phase 05.1: Candidate review frontend UI — approve/reject/edit workflow (inserted) — completed 2026-07-30
- [x] Phase 6: Spoiler-safe GraphRAG chat and graph-editing agent (13/13 plans) — completed 2026-08-02

</details>

<details>
<summary>🔄 v1.2 Spoiler-Safety Hardening (Phase 7) — IN PLANNING</summary>

- [ ] Phase 7: Spoiler-Safety Hardening (8/8 plans planned) — planned 2026-08-02

#### Phase 7: Spoiler-Safety Hardening

**Goal:** Separate watched progress from the temporary view boundary, centralize the `visible_from_order` policy (fail-closed), and close indirect leak channels — episode metadata, search/autocomplete, counts, media, chat/GraphRAG, and graph edits — on the existing stack.
Requirements: PROG-01–04, VIS-01–05, META-01–03, SEARCH-01–02, MEDIA-01–02, CHAT-01–03, EDIT-01–02, DOCS-01–02
Success criteria:
1. User can view an earlier already-watched episode without lowering progress; graph and chat show only boundary-safe data; returning restores eligible content
2. Future episode titles, synopses, runtimes, and images never appear in any API response (backend-masked)
3. Hidden entities, aliases, counts, and relationships behave like nonexistent in search, autocomplete, aggregates, and graph layout
4. GraphRAG and ChangeSets operate on the effective boundary; stale later-boundary ChangeSets fail closed
5. Threat-model doc + regression matrix cover every direct/indirect leak class with enforcement layer and test coverage

Plans: 07-01 audit + threat model + domain design · 07-02 progress migration + boundary service + API · 07-03 metadata gating + frontend UX · 07-04 relationship/provenance/Cypher hardening · 07-05 search/aggregate leak protection · 07-06 media safety · 07-07 chat/GraphRAG/ChangeSet integration · 07-08 regression + browser acceptance + docs

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|-----------------|--------|-----------|
| 1. Backend Graph Foundation | v1.0/v1.1 | 1/1 | Complete | 2026-07-28 |
| 2. Polished Cytoscape Graph Experience | v1.0/v1.1 | 4/4 | Complete | 2026-07-29 |
| 03.1 Frontend visual overhaul | v1.0/v1.1 | 4/4 | Complete | 2026-07-29 |
| 3. User Notes and Manual Editing | v1.0/v1.1 | 4/4 | Complete | 2026-07-29 |
| 4. Revision History and Revert | v1.0/v1.1 | 5/5 | Complete | 2026-07-30 |
| 5. Future-Extraction Preparation | v1.0/v1.1 | 4/4 | Complete | 2026-07-30 |
| 05.1 Candidate review frontend UI | v1.0/v1.1 | — | Complete | 2026-07-30 |
| 6. Spoiler-safe GraphRAG chat and graph-editing agent | v1.1 | 13/13 | Complete | 2026-08-02 |
| 7. Spoiler-Safety Hardening | v1.2 | 8/8 | Planned | 2026-08-02 |

Full phase details archived at `.planning/milestones/v1.1-ROADMAP.md` and `.planning/milestones/v1.1-phases/` (supersedes the earlier `.planning/milestones/v1.0-ROADMAP.md` archive, which predates Phase 6).

---
*Last updated: 2026-08-02 — v1.2 Spoiler-Safety Hardening started (Phase 7 in planning)*
