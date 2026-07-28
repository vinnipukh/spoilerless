# HD Graf Cehennemi — Project State

**Project:** HD Graf Cehennemi — Spoiler-Safe Narrative Knowledge Graph  
**Core Value:** Users can safely explore a TV series knowledge graph without ever seeing spoilers — the backend guarantees the frontend never receives data beyond their selected watch progress.  
**Target:** Dexter S01E01-03 prototype  
**Project Mode:** mvp (Vertical MVP)  
**Granularity:** coarse  

---

## Current Phase

| Field | Value |
|-------|-------|
| **Phase** | Phase 1: Backend Infrastructure & Seed Data |
| **Status** | Pending |
| **Mode** | mvp |
| **Deliverable** | Working backend with verified health endpoint, reliable seed script, seeded Dexter S01E01-03 graph, and passing tests |
| **Requirements** | INFRA-01, INFRA-02, DATA-01, DATA-02, DATA-03, DATA-04, ARCH-01, ARCH-02, ARCH-03, ARCH-04, ARCH-05, TEST-01, TEST-02 |

---

## Next Phase

| Field | Value |
|-------|-------|
| **Phase** | Phase 2: Spoiler-Gated Graph API |
| **Mode** | mvp |
| **Deliverable** | `GET /api/graph` with Cypher-level spoiler filtering, Neo4j constraints, Pydantic models, integration tests |
| **Requirements** | GRAPH-01, GRAPH-02, GRAPH-03, GRAPH-04, GRAPH-05, GRAPH-06, TEST-03, TEST-04 |
| **Dependencies** | Phase 1 complete (seed data, stable backend, working tests) |

---

## Quick Reference

- **ROADMAP.md** — Phase structure with goals, success criteria, and plans
- **REQUIREMENTS.md** — v1 requirements with traceability to phases
- **PROJECT.md** — Project context, key decisions, constraints
- **config.json** — Granularity=coarse, parallelization=true, model_profile=adaptive
- **research/SUMMARY.md** — Stack, features, architecture, pitfalls

---

## Phase History

| Phase | Description | Status | Completed |
|-------|-------------|--------|-----------|
| Phase 1 | Backend Infrastructure & Seed Data | Pending | — |
| Phase 2 | Spoiler-Gated Graph API | Pending | — |

---

*Last updated: 2026-07-28*
