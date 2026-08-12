# Documentation Index

> **Structure convention (2026-08-12 restructure):** docs are grouped by
> *lifecycle*, not by date or version. Thematic lowercase-kebab filenames —
> never `backend_refactor_03.md`-style names. Canonical GSD docs keep their
> uppercase names and fixed paths; only their grouping changed here.

## Stability classes — what gets updated when

| Class | Docs | Update rule |
|---|---|---|
| **Generated / test-locked** | `reference/frontend-api-contract.md`, `API.md` | Never hand-edit counts or inventories — the contract tests (`test_frontend_contract_doc.py`, `test_openapi_contract.py`) lock them against the live OpenAPI surface. Regenerate from `app.openapi()` when the surface changes. |
| **Decision records** | `architecture/*` (project-spec, spoiler-*), `ARCHITECTURE.md` | Written once at design time; changed only when the decision itself changes (not per refactor). Per-change noise goes to `PROBLEMS.md`, not here. |
| **Snapshots** | `reference/backend-modules.md`, `reference/frontend-components.md` | Point-in-time module maps. Dated; **verify against the live tree before trusting** (they are not regenerated automatically). |
| **Living process** | `ops/runbook.md`, `DEPLOYMENT.md`, `PROBLEMS.md`, `ROADMAP.md` | Incident history, operator procedures, the numbered problem ledger, and the roadmap — appended to as reality changes; existing sections are not rewritten per commit. |
| **Ideas** | `ideas/*` | Brainstorm backlog; no status until scoped against `architecture/project-spec.md` invariants. |

## Group layout

### docs/guides/ — how to work
- [GETTING-STARTED.md](GETTING-STARTED.md) — first-run setup, local stack
- [DEVELOPMENT.md](DEVELOPMENT.md) — dev loop, layout, pitfalls

### docs/reference/ — facts that mirror code
- [API.md](API.md) — backend HTTP surface (50 ops / 37 templates)
- [frontend-api-contract.md](reference/frontend-api-contract.md) — backend↔frontend contract (test-locked)
- [CONFIGURATION.md](CONFIGURATION.md) — env/config reference
- [backend-modules.md](reference/backend-modules.md) — backend module map (snapshot)
- [frontend-components.md](reference/frontend-components.md) — frontend component map (snapshot)

### docs/architecture/ — stable decisions
- [ARCHITECTURE.md](ARCHITECTURE.md) — system architecture + design decisions
- [project-spec.md](architecture/project-spec.md) — non-negotiable invariants
- [spoiler-threat-model.md](architecture/spoiler-threat-model.md) — leak-channel inventory
- [spoiler-terminology.md](architecture/spoiler-terminology.md) — locked vocabulary
- [spoiler-deferred-design.md](architecture/spoiler-deferred-design.md) — deferred spoiler features

### docs/ops/ — operations
- [DEPLOYMENT.md](DEPLOYMENT.md) — deploy recipes, Render notes
- [runbook.md](ops/runbook.md) — incident detection/diagnosis/rollback + deploy-crash post-mortem

### docs/ — root (ledger + backlog)
- [PROBLEMS.md](PROBLEMS.md) — the numbered problem ledger (81 findings, pass history); **"Still open" section = the live open-work list**
- [ROADMAP.md](ROADMAP.md) — authoritative roadmap / backlog

### docs/ideas/ — brainstorm
- [feature-ideas.md](ideas/feature-ideas.md) — unscoped ideas
- [feature-research.md](ideas/feature-research.md) — per-idea dependencies + affected files

### docs/internship-report/ — academic deliverable (not project docs)
