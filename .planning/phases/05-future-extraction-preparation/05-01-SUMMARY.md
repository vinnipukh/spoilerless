---
phase: 05-future-extraction-preparation
plan: "01"
subsystem: domain-models
status: complete
tags: [pydantic, extraction, json-schema, ontology]

requires:
  - phase: 01-backend-graph-foundation
    provides: Ontology type registry (node/relation/claim_types maps)
  - phase: 04-revision-history-and-revert
    provides: RevisionAction enum, RevisionRepository
provides:
  - ExtractionClaim Pydantic model with deterministic candidate_id (SHA-256)
  - ExtractionBatchEnvelope model with batch-level validation
  - SourcePayload and EvidencePayload models for source-connector interface
  - docs/extraction-schema.json (JSON Schema artifact, 4 definitions)
  - PREP-01 (versioned extraction schema) and PREP-04 (source-connector interface)
---

# Plan 05-01 — Extraction Schema Models

**Status:** Complete — committed `620aedf`
**Duration:** ~5 min

## Delivered

| Task | Description | Files |
|------|-------------|-------|
| T1 | Extraction Pydantic models | `backend/app/domain/extraction.py` |
| T2 | JSON Schema artifact | `docs/extraction-schema.json` |

## Key Outcomes

- `ExtractionClaim` fields: subject_id, subject_label, predicate, object_id, object_label, claim_type, status, confidence_level, visible_from_order, source, evidence, schema_version
- `Deterministic ID generation:` `candidate_id = sha256(series_id:subject_id:predicate:object_id:visible_from_order)[:24]` with `extracted:` prefix
- Ontology validation via `field_validator`s — rejects unknown claim_types, statuses, confidence_levels
- `extra='forbid'` on all models — strict payload validation
- Batch envelope validates `claims` is non-empty list
- JSON Schema published at `docs/extraction-schema.json` with all 4 definitions
</per-file>
