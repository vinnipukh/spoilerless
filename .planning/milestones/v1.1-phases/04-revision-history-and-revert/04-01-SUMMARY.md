---
phase: 04-revision-history-and-revert
plan: "01"
subsystem: domain-persistence
status: complete
tags: [neo4j, revision, pydantic, fastapi, seed-data]

requires:
  - phase: 03-user-notes-and-manual-editing
    provides: User-content CRUD operations (note/node/relationship create/update/delete)
provides:
  - RevisionAction enum (Created, Updated, Deleted, Reverted)
  - RevisionResponse Pydantic model with JSON/datetime Neo4y compatibility field validators
  - RevisionRepository.log_revision() (append-only, same-transaction)
  - take_snapshot() helper for before/after state capture
  - Revision constraints in seed.py (id_unique, series_idx, resource_idx, created_idx)
  - All 9 user-content write callbacks log a Revision in the same Neo4j transaction
---

# Plan 04-01 — Revision Model & Persistence

**Status:** Complete — revision model, persistence layer, and user-content integration
**Duration:** ~8 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | Revision domain model | `backend/app/domain/revision.py` |
| T2 | Revision persistence + snapshot helpers | `backend/app/revisions/__init__.py` |
| T3 | Revision constraints in seed | `backend/app/graph/seed.py` |
| T4 | User-content revision logging integration | `backend/app/repository/user_content.py` |

## Key Outcomes

- `RevisionAction` enum covers all mutation types (Created, Updated, Deleted, Reverted)
- `RevisionResponse` uses `field_validator("before", "after", mode="before")` to parse JSON strings from Neo4j into dicts
- `field_validator("created_at", mode="before")` converts Neo4j `DateTime` to Python `datetime`
- `log_revision()` creates `:Revision` node with `-[:REVISES]->(resource)` in same transaction as the mutation
- `take_snapshot()` returns JSON-serialized dict of node properties (Neo4j rejects dict properties)
- Delete callbacks log revision *before* deletion (resource must exist for valid snapshot)
- All 9 user-content write paths log revisions: note create/update/delete, custom-node create/update/delete, custom-relationship create/update/delete

## Decisions

- `log_revision()` takes an explicit `tx` (Neo4j managed transaction) — caller passes the same transaction used for the mutation, guaranteeing atomicity
- `before` and `after` stored as JSON strings in Neo4j `nvarchar` properties (Neo4j Community does not support dict-typed properties)
- Delete revision logged before `MATCH (n) DETACH DELETE n` — snapshot taken first, then node deleted

