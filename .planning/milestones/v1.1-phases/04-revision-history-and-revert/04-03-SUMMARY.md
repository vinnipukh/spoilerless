---
phase: 04-revision-history-and-revert
plan: "03"
subsystem: tests
status: complete
tags: [pytest, integration, revision, revert, fastapi]

requires:
  - phase: 04-revision-history-and-revert
    plan: "02"
    provides: Revision API routes
provides:
  - Integration tests for revision logging, list/get, revert, spoiler boundaries, canonical isolation
  - 12 tests covering REV-01, REV-02, REV-03
---

# Plan 04-03 — Revision API Tests

**Status:** Complete — 12 integration tests passing
**Duration:** ~6 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | Comprehensive revision API tests | `backend/tests/test_revisions.py` |

## Test Coverage

| Requirement | Tests | What it proves |
|-------------|-------|---------------|
| REV-01 | 3 tests | Note/Node/Relationship lifecycle creates Created→Updated→Deleted revision sequence |
| REV-02 | 4 tests | List with filters, single get by ID, spoiler boundary (hidden=404), non-existent=404 |
| REV-03 | 3 tests | Revert updated note, revert deleted note (with REFERS_TO restoration), history preserved |
| Canonical isolation | 1 test | Revert on canonical resource returns 409 |
| Error handling | 1 test | Revert on CREATED revision returns 422 |

## Key Outcomes

- All tests use existing `user_content_client` fixture — no new fixture infrastructure
- Revert tests verify both content restoration AND new REVERTED revision creation (revision count grows)
- Spoiler boundary test confirms hidden revision returns same 404 envelope as non-existent revision
- All existing user-content tests remain green (regression barrier)
</per-file>
