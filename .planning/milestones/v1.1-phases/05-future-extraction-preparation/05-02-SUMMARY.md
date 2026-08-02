---
phase: 05-future-extraction-preparation
plan: "02"
subsystem: api-persistence
status: complete
tags: [fastapi, neo4j, candidate, ingest, fixture]

requires:
  - phase: 05-future-extraction-preparation
    plan: "01"
    provides: ExtractionClaim, ExtractionBatchEnvelope models
  - phase: 01-backend-graph-foundation
    provides: Neo4jDatabase, execute_query, spoiler filtering
provides:
  - CandidateRepository with ingest_batch, get_candidate_claim, list_candidate_claims
  - POST /api/series/{series_id}/candidates/ingest endpoint
  - GET /api/series/{series_id}/candidates list endpoint
  - GET /api/series/{series_id}/candidates/{claim_id} detail endpoint
  - Router wired in main.py
  - data/dexter/test/extraction_fixture.json (3 Dexter claims)
  - PREP-02 (candidate storage isolation)
---

# Plan 05-02 — Candidate Ingest API

**Status:** Complete — committed `e528c89`
**Duration:** ~7 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | CandidateRepository | `backend/app/graph/candidates.py` |
| T2 | Ingest/list/get endpoints | `backend/app/api/candidates.py` |
| T3 | Router wiring | `backend/app/main.py` |
| T4 | Extraction fixture JSON | `data/dexter/test/extraction_fixture.json` |

## Key Outcomes

- `ingest_batch` uses `MERGE`-based idempotent upsert with deterministic SHA256-derived IDs
- `extracted:` ID prefix for claims, `extracted:source:` for sources, `extracted:evidence:` for evidence fragments
- All-or-nothing batch: single `execute_write` transaction for entire batch
- Claims stored as `:Claim` nodes with `origin: 'candidate'`
- Sources stored as `:Source` nodes
- Evidence stored as `:EvidenceFragment` nodes with `-[:SUPPORTED_BY]->(source)` and `<-[:HAS_EVIDENCE]-(claim)`
- Ingestion creates `-[:DERIVED_FROM]->(source)` relationships from sources to claims
- Fixture has 3 claims: 1 Dexter-KNOWNS-Debra (vfo=1), 1 Dexter-KILLS-Brian (vfo=1), 1 Debra-DISTRUSTS-Paul (vfo=2)
</per-file>
