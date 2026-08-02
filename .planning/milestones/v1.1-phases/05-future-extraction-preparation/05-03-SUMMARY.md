---
phase: 05-future-extraction-preparation
plan: "03"
subsystem: api-review
status: complete
tags: [fastapi, neo4j, review, approve, reject, edit, revision]

requires:
  - phase: 05-future-extraction-preparation
    plan: "02"
    provides: CandidateRepository, ingest/list/get endpoints
  - phase: 04-revision-history-and-revert
    provides: RevisionRepository.log_revision(), RevisionAction
provides:
  - POST /api/series/{series_id}/candidates/{claim_id}/approve — promotes candidate to canonical
  - POST /api/series/{series_id}/candidates/{claim_id}/reject — sets status to rejected
  - PATCH /api/series/{series_id}/candidates/{claim_id} — partial update with revision logging
  - PREP-03 (review workflow with revision logging)
---

# Plan 05-03 — Review Workflow

**Status:** Complete — code merged into candidates.py
**Duration:** ~4 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | Approve/reject/edit routes | `backend/app/api/candidates.py` |

## Key Outcomes

- **Approve:** Changes `origin: 'candidate' → 'canonical'` and `status: 'candidate' → 'corroborated'`; revision-logged with before/after snapshot
- **Reject:** Sets `status: 'candidate' → 'rejected'`; revision-logged
- **Edit (PATCH):** Partial field update via `SET {set_expr}` Cypher; revision-logged with before/after
- All mutations run in same Neo4j transaction via `execute_write(lambda tx, ...)` pattern
- Deterministic revision IDs: `sha256(f'action:{claim_id}:{timestamp}')[:12]`
- 6 routes total in candidate router (ingest, list, get, approve, reject, edit)
</per-file>
