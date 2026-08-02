---
status: complete
phase: 05-future-extraction-preparation
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md, 05-04-SUMMARY.md
started: 2026-07-30T16:14:00.000Z
updated: 2026-07-30T16:20:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. Extraction schema rejects invalid payloads
expected: POST malformed payload returns 422 with error code
result: pass

### 2. Ingest fixture creates candidate claims
expected: POST fixture returns 200 with 3 extracted: IDs
result: pass

### 3. Ingest is idempotent
expected: Same IDs returned on re-ingest, no errors
result: pass

### 4. List shows ingested candidates
expected: GET /candidates returns 3 claims
result: pass

### 5. Get single candidate by ID
expected: GET /candidates/{id} returns full claim detail
result: pass

### 6. Approve a candidate claim
expected: POST approve returns status: "canonical", revision logged
result: pass

### 7. Reject a candidate claim
expected: POST reject returns status: "rejected", revision logged
result: pass

### 8. Edit a candidate claim
expected: PATCH updates field, returns status: "edited", revision logged
result: pass

### 9. Non-existent candidate returns 404
expected: GET/POST on nonexistent ID returns 404 with candidate_not_found
result: pass

### 10. Spoiler filtering hides future candidates
expected: vfo=2 claim hidden at boundary=1, visible at boundary=3
result: pass

### 11. All 32 automated tests pass
expected: pytest — 32/32 pass
result: pass

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

*(none)*
