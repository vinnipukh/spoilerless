# Plan 05-01 SUMMARY — Extraction schema + source-connector interface models

**Phase:** 05-future-extraction-preparation  
**Plan:** 05-01  
**Status:** ✅ Complete  
**Date:** 2026-07-30

## Deliverables

1. **`backend/app/domain/extraction.py`** (new) — Pydantic models:
   - `ExtractionClaim` — atomic candidate claim with ontology validation (claim_type, confidence_level), deterministic `candidate_id` property, `schema_version` field, `extra='forbid'`
   - `ExtractionBatchEnvelope` — batch wrapper with extractor metadata, min/max claim count constraints
   - `SourcePayload` — source-connector interface contract (PREP-04)
   - `EvidencePayload` — evidence-connector interface contract (PREP-04)

2. **`docs/extraction-schema.json`** (new) — Published JSON Schema artifact with all four model definitions (12,129 bytes)

## Verification Results

| Check | Status |
|-------|--------|
| Import models | ✅ |
| Valid claim creation with ontology-valid values | ✅ |
| Ontology rejection of bad claim_type | ✅ |
| Extra field rejection (`extra='forbid'`) | ✅ |
| Empty batch rejection (min_length=1) | ✅ |
| JSON Schema artifact valid with 4 definitions | ✅ |

## Design Decisions
- Removed `Ontology.require_relationship_type` validator for `relationship_effect` since the ontology's relationship types (e.g., `FAMILY_OF`, `PART_OF`) don't match effect semantics ("strengthens", "weakens", "neutral"). Field is stored as a plain string.
- Used `load_ontology()` to instantiate the `Ontology` dataclass (it's not a static-method class).
- Used `observed_event` claim type (valid per ontology YAML) instead of the plan's `character_relationship`.

## No Frontend Changes
`git diff --name-only -- frontend/` — empty ✅
