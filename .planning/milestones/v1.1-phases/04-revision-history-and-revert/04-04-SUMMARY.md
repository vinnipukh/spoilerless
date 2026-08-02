---
phase: 04-revision-history-and-revert
plan: "04"
subsystem: frontend-data-layer
status: complete
tags: [typescript, react, api-client, hook, test]

requires:
  - phase: 04-revision-history-and-revert
    plan: "02"
    provides: Revision API endpoints
  - phase: 03-user-notes-and-manual-editing
    plan: "01-frontend"
    provides: useNotes hook pattern, api/client.ts, types/graph.ts
provides:
  - RevisionResponse, RevisionAction TS types
  - getRevisions, getRevision, revertRevision API client functions
  - useRevisions hook (idle/loading/error/success states, refetch support)
  - 6 hook unit tests
---

# Plan 04-04 — Frontend Revision Data Layer

**Status:** Complete — types, API client, hook, tests
**Duration:** ~5 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | Revision TypeScript types | `frontend/src/types/revision.ts` |
| T2 | Revision API client functions | `frontend/src/api/revisions.ts` |
| T3 | useRevisions hook | `frontend/src/hooks/useRevisions.ts` |
| T4 | Hook unit tests | `frontend/src/hooks/useRevisions.test.tsx` |

## Key Outcomes

- `RevisionAction` TS enum mirrors backend `RevisionAction` (Created/Updated/Deleted/Reverted)
- `RevisionResponse` TS type mirrors backend's `RevisionResponse` fields (id, series_id, resource_type, resource_id, action, before, after, created_at, visible_from_order)
- API client exports `getRevisions(seriesId, visibleUntilOrder, resourceType?, resourceId?)`, `getRevision(seriesId, revisionId, visibleUntilOrder)`, `revertRevision(seriesId, revisionId, visibleUntilOrder)`
- `useRevisions` hook follows `useNotes` pattern: keyed by `(seriesId, visibleUntilOrder, resourceType, resourceId)`, idle/loading/error/success state machine, returns `refetch()` for parent-triggered refresh
- 6 tests: loading state, success with data, empty list, error handling, refetch, key-based re-fetch

## Decisions

- Hook returns `refetch()` (not automatic polling) — parent (DetailPanel) explicitly calls refetch after revert succeeds
- Key includes resource_type + resource_id so switching selection automatically re-fetches correct revisions
</per-file>
