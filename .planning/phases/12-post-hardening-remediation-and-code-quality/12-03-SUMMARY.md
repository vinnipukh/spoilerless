---
phase: 12-post-hardening-remediation-and-code-quality
plan: 03
subsystem: spoilerless-graph-candidates
tags: [neo4j, cypher, performance, visibility, candidate-ingest]
requires:
  - "12-02"
provides:
  - "Single-roundtrip claim visibility resolution (_resolve_claim_visibility)"
affects:
  - "spoilerless candidate ingest performance (1 Cypher query per claim)"
tech-stack:
  added: []
  patterns:
    - "OPTIONAL MATCH projection for existence checks (null id ⇒ missing node)"
key-files:
  created: []
  modified:
    - spoilerless/app/graph/candidates.py
decisions:
  - "Existence validation moved into _VISIBILITY_PREPASS_QUERY projections (subject.id/object.id); separate subj_check/obj_check roundtrips deleted."
metrics:
  duration: "~6 min"
  completed: "2026-08-26"
status: complete
actuals:
  tokens: 1500
  tasks: 2
  commits: 2
---

# Phase 12 Plan 03: Consolidate Candidate Visibility Resolution Summary

Candidate claim visibility resolution now executes exactly ONE Cypher query per claim (was 3), preserving full node-existence validation via OPTIONAL MATCH id projections.

## What Was Done

### Task 1: Consolidate _VISIBILITY_PREPASS_QUERY (commit c9b09d5)
- `_VISIBILITY_PREPASS_QUERY` now projects `subject.id AS subject_id`, `object.id AS object_id` alongside `episode_order`, `subject_vfo`, `object_vfo`.
- `_resolve_claim_visibility` refactored to a single `tx.run(...).single()` call:
  - `row.get("episode_order") is None` → return None (missing/invalid episode).
  - `row.get("subject_id") is None or row.get("object_id") is None` → return None (missing subject/object node).
  - Separate `subj_check` / `obj_check` `tx.run` existence queries deleted entirely.
  - `endpoint_vfos = (subject_vfo, object_vfo)`; `current_progress` = max of non-None vfos else None.
  - Visibility remains server-derived through `derive_visible_from_order` (spoilerless/app/spoiler/visibility.py) — NOT bypassed.
- Also fixed latent falsy-filter bug while touching the expression: `max(v for v in endpoint_vfos if v)` → `if v is not None` (vfo 0 was previously dropped).

### Task 2: Validate candidate suites
- `pytest spoilerless/tests/test_candidate_ingest.py spoilerless/tests/test_candidate_review.py -q`
- **Result: 21 passed, 0 failed** in 107s against live shared Neo4j (`unset PYTHONPATH` + `.venv`).
- Verified behaviors: valid claims ingest with server-derived visibility; claims referencing non-existent subject/object are skipped; claims referencing non-existent episode are skipped.
- No pre-existing reds encountered; no pollution debt surfaced in this run.

## Deviations from Plan

None — plan executed exactly as written. (Docstring formatting cleanup on `_resolve_claim_visibility` was cosmetic only.)

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surface introduced.

## Performance Metrics

| Metric | Before | After |
|--------|--------|-------|
| Cypher roundtrips per claim | 3 | 1 |
| Existence check mechanism | 2 extra tx.run MATCHes | OPTIONAL MATCH id projection |

## Self-Check: PASSED

- [x] spoilerless/app/graph/candidates.py modified and committed (c9b09d5)
- [x] Candidate suites green: 21 passed
- [x] derive_visible_from_order still sole source of visibility derivation
