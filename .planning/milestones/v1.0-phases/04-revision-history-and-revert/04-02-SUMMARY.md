---
phase: 04-revision-history-and-revert
plan: "02"
subsystem: api
status: complete
tags: [fastapi, openapi, revision, revert, neo4j]

requires:
  - phase: 04-revision-history-and-revert
    plan: "01"
    provides: Revision model, persistence layer, user-content revision logging
provides:
  - GET /api/series/{series_id}/revisions — list with resource_type/resource_id filters
  - GET /api/series/{series_id}/revisions/{revision_id} — single revision with spoiler boundary
  - POST /api/series/{series_id}/revisions/{revision_id}/revert — revert with new revision creation
  - Revision routes registered in main.py
---

# Plan 04-02 — Revision API Endpoints

**Status:** Complete — three routes created and wired
**Duration:** ~7 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | Create revision API routes | `backend/app/api/revisions.py` |
| T2 | Wire revision router into application | `backend/app/main.py` |

## Key Outcomes

- **List:** `GET .../revisions` returns most-recent-first, optional `resource_type`/`resource_id` query filters, spoiler-filtered by `visible_until_order`
- **Get:** `GET .../revisions/{revision_id}` returns single revision; 404 if hidden or missing
- **Revert:** `POST .../revisions/{revision_id}/revert` restores prior state:
  - UPDATED → SET properties from revision.before (preserving `visible_from_order` and `origin`)
  - DELETED → re-create node from revision.before with REFERS_TO relationship
  - Rejects CREATED (422), canonical/candidate (409), always creates new REVERTED revision
- All routes require `visible_until_order` spoiler boundary (422 if missing/invalid)
- All mutation paths run in same Neo4j transaction (D-03 compliance)

## Decisions

- Revert uses two separate Cypher paths (UPDATED vs DELETED) — cleaner than a single polymorphic query
- DELETED re-creation uses `CREATE` with explicit properties from `before` snapshot (no APOC dependency for prototype)
- Reverted resource gets `origin: 'user'` explicitly — ensures revert chain stays user-owned
</per-file>
