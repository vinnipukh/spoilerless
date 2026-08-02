# Phase 5: Future-Extraction Preparation — Context

**Gathered:** 2026-07-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 5 prepares the system to accept structured candidate claims from a future LLM-powered extractor *without* implementing extraction, automated source retrieval, or any LLM integration. It delivers the backend contracts, candidate claim APIs, review workflow, and source-connector interface needed so that a future Phase (post-v0) can plug in a real extractor without changing the core graph model.

This phase is **backend-only** — no React/Cytoscape frontend changes. The frontend currently renders `origin: "candidate"` nodes with dashed-border styling (courtesy of Phase 03.1's visual conventions) but has no review/approve/reject/edit UI. Building that UI is deferred to a future frontend workstream.

The phase fulfills requirements PREP-01 through PREP-05 from the canonical Prototype v0 scope, corresponding to root roadmap **Milestone 8 — Preparation for LLM extraction**.

### What This Phase Does

1. **Defines a versioned extraction-output JSON schema** (PREP-01) — a Pydantic model that represents atomic candidate claims with all metadata the extractor must produce.
2. **Creates a candidate claim write API** (PREP-02) that accepts structured candidates into `origin: "candidate"` storage, keeping them strictly separate from `canonical` and `user` content.
3. **Adds a review/resolution API** (PREP-03) supporting approve, reject, and edit actions on candidate claims, with every action revision-logged via Phase 4's existing `RevisionRepository`.
4. **Defines a source-connector interface** (PREP-04) — a Pydantic contract for source/evidence payloads, not a running service.
5. **Delivers a fixture-driven acceptance test** (PREP-05) that proves the complete flow: structured fixture → ingest → review → resolve — without invoking any LLM or external retrieval.

### What This Phase Does NOT Do

- No automated source ingestion, subtitle parsing, PDF extraction, podcast transcription, web scraping, or external retrieval.
- No LLM extraction pipeline — not even a mock LLM invocation.
- No LLM chat, graph-RAG, or retrieval-augmented generation.
- No frontend review UI (deferred to future phase).
- No changes to the existing `GraphNode`, `GraphEdge`, `GraphClaim`, `GraphSource`, `GraphEvidence`, or `GraphResponse` models — the graph model is already compatible.
- No new Neo4j node types — existing `Claim`, `Source`, `EvidenceFragment` labels are sufficient.

</domain>

<decisions>
## Implementation Decisions

### Extraction Schema Contract

- **D-01:** The extraction-output schema is a standalone Pydantic model (`ExtractionClaim`) defined under `backend/app/domain/extraction.py`. It represents one atomic candidate claim as an external extractor must output it, not a new Neo4j label.
- **D-02:** `ExtractionClaim` fields: `subject_id`, `predicate`, `object_id`, `claim_type` (ontology-validated), `confidence_level`, `relationship_effect`, `visible_from_order`, `valid_from_order`, `valid_until_order`, `evidence_text`, `evidence_locator`, `source_type`, `source_locator`, `episode_id`. Every field is required unless explicitly optional.
- **D-03:** The schema is versioned with a `schema_version` field (string, starting at `"0.1"`). Future extractors must declare which schema version they produce.
- **D-04:** The `ExtractionClaim` model uses strict Pydantic validation: extra fields forbidden, ontology validation via `Ontology.require_*()` methods, and episode/series existence validation at ingest time.
- **D-05:** The schema is published as a JSON Schema artifact (e.g., `docs/extraction-schema.json`) so that future extractor teams can validate their output before submission.

### Candidate Claim Storage

- **D-06:** Candidate claims are stored as standard `Claim` Neo4j nodes with `origin: "candidate"`. No new node type is needed — the Claim label already exists and the `Origin` enum already includes `candidate`.
- **D-07:** Ingested candidates automatically create corresponding `Source` and `EvidenceFragment` nodes (with `origin: "candidate"`) from the extraction payload. This mirrors how seed claims reference sources and evidence.
- **D-08:** Candidate claims enter with `status: "candidate"`. Only the review API (approve/reject/edit) can change this status.
- **D-09:** The core graph model (GraphNode, GraphEdge, GraphClaim, GraphResponse) needs zero changes — candidate claims already appear in `VISIBLE_CLAIMS_QUERY` via `claim.origin IN ['canonical', 'candidate']`.

### Candidate Ingest API (PREP-02)

- **D-10:** A single ingest endpoint accepts a list of `ExtractionClaim` payloads:
  `POST /api/series/{series_id}/candidates/ingest`
  Returns the created claim IDs plus any validation errors.
- **D-11:** Ingest is idempotent per extraction batch: each claim carries a deterministic candidate ID derived from the payload content (e.g., `extracted:{sha256_prefix}`). Re-ingesting the same payload upserts rather than duplicates.
- **D-12:** Ingest is a write operation that must succeed or fail atomically within a single Neo4j transaction per batch.
- **D-13:** The ingest endpoint accepts a `source` metadata block (extractor name, version, run timestamp) as part of the payload envelope, stored on the created Source node.

### Review/Resolution API (PREP-03)

- **D-14:** Three review actions, each a separate endpoint:
  - `POST /api/series/{series_id}/candidates/{claim_id}/approve` — sets `status: canonical` (or a configurable target status), logs revision.
  - `POST /api/series/{series_id}/candidates/{claim_id}/reject` — sets `status: rejected`, logs revision.
  - `PATCH /api/series/{series_id}/candidates/{claim_id}` — updates claim properties (edit), logs revision with before/after.
- **D-15:** Approve and reject each create exactly one `Revision` with action `Updated` and before/after snapshots (reusing Phase 4's `RevisionRepository.log_revision`).
- **D-16:** Edit (`PATCH`) allows changing any mutable claim field except `id`, `series_id`, `origin`, and `visible_from_order`. Changes are revision-logged.
- **D-17:** Only claims with `origin: "candidate"` can be approved, rejected, or edited through these endpoints. Canonical and user claims are never affected.
- **D-18:** A listing endpoint fetches all candidate claims for review:
  `GET /api/series/{series_id}/candidates?visible_until_order={order}`
  Returns candidate claims with their linked sources and evidence. Spoiler-filtered like all other graph data.
- **D-19:** A single-candidate GET endpoint:
  `GET /api/series/{series_id}/candidates/{claim_id}?visible_until_order={order}`
  Returns full candidate detail including sources and evidence fragments.

### Source-Connector Interface (PREP-04)

- **D-20:** The source-connector interface is a Pydantic model (`SourcePayload`), not a Python abstract base class or a running service. It defines the contract for what a source record looks like: `source_type`, `locator`, `retrieved_at`, `episode_id`, and optional `content_hash`.
- **D-21:** Similarly, `EvidencePayload` defines: `text`, `locator`, `episode_id`, `content_hash`.
- **D-22:** These payload models live alongside `ExtractionClaim` in `backend/app/domain/extraction.py`. They document the interface any future connector must implement.
- **D-23:** Future extractors will produce these payloads; Phase 5 only validates the shape and stores them. No HTTP client, file parser, or retrieval logic is implemented.

### Fixture-Driven Acceptance Test (PREP-05)

- **D-24:** A JSON fixture file `data/dexter/test/extraction_fixture.json` contains a small batch of structured `ExtractionClaim` payloads for Dexter S01E01.
- **D-25:** An integration test (`tests/test_candidate_ingest.py`) loads the fixture, POSTs it to the ingest endpoint, verifies claims/sources/evidence were created with `origin: "candidate"`, exercises approve/reject/edit, verifies revision logging, and proves the core graph model is unchanged.
- **D-26:** The test must also verify that ingested candidates appear in the spoiler-filtered graph response (`GET /api/graph`) at the correct visibility boundary and do not leak at earlier boundaries.
- **D-27:** The test must prove that candidates *cannot* become canonical without explicit approval — no Cypher MERGE or seed path can promote them.

### Error Contract

- **D-28:** All candidate endpoints reuse the existing error envelope from `backend/app/core/errors.py`: `{"detail": {"code": "...", "message": "..."}}`.
- **D-29:** New stable error codes: `invalid_extraction_payload` (422), `candidate_not_found` (404), `cannot_approve_non_candidate` (409), `cannot_reject_non_candidate` (409).
- **D-30:** Validation errors from the ingest endpoint return per-item error details in a structured errors array alongside successfully created IDs, so a batch ingest partially succeeds without losing the entire batch.

### File and Router Organization

- **D-31:** New extraction domain models under `backend/app/domain/extraction.py`.
- **D-32:** New candidate API routes under `backend/app/api/candidates.py`.
- **D-33:** New candidate persistence logic under `backend/app/graph/candidates.py` (or within `backend/app/services/` if following the GraphService pattern).
- **D-34:** Wire the candidate router in `backend/app/main.py`.
- **D-35:** Revision logging for approve/reject/edit actions lives inline in the candidate API route handlers, calling `RevisionRepository.log_revision` (same pattern as `backend/app/repository/user_content.py`).

### Integration with Existing Patterns

- **D-36:** Candidate ingest uses `Neo4jDatabase.execute_write` for atomic batch transactions — same pattern as user-content mutations.
- **D-37:** Spoiler filtering for candidate listing uses the same `visible_from_order` boundary parameter — no new boundary logic.
- **D-38:** Candidate claims appear in the existing `GET /api/series/{series_id}/graph` response automatically because `VISIBLE_CLAIMS_QUERY` already includes `claim.origin IN ['canonical', 'candidate']`.
- **D-39:** The existing `Revision` model and `RevisionRepository.log_revision` from Phase 4 are reused directly — no new revision model needed.

### Claude's Discretion

- Exact names of Pydantic model classes in `extraction.py` and `candidates.py`, provided they follow existing naming conventions.
- Exact structure of the extraction fixture file, provided it contains valid Dexter S01E01-visible and S01E02-invisible payloads.
- Exact partitioning of tests across `test_candidate_ingest.py`, `test_candidate_review.py`, etc., provided all PREP requirements have test coverage.
- Whether to add a Neo4j constraint on `origin` values (nice-to-have, not critical).
- Exact retry/batch-size limits for the ingest endpoint, if any.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Phase Requirements
- `ROADMAP.md` (root) — Canonical Prototype v0 scope, Milestone 8 (Preparation for LLM extraction), ontology direction, and exclusions.
- `.planning/PROJECT.md` — Brownfield facts, core value, constraints, five-phase delivery interpretation.
- `.planning/ROADMAP.md` — Phase 5 goal, requirements (PREP-01..05), dependencies, and success criteria.
- `.planning/REQUIREMENTS.md` — Exact Phase 5 requirement text:
  - **PREP-01**: A versioned extraction-output JSON schema represents atomic candidate claims, visibility/validity, confidence/effect, and evidence references.
  - **PREP-02**: Candidate claims are stored separately from canonical and user-created knowledge and cannot become canonical without review.
  - **PREP-03**: API/UI review supports approve, reject, and edit actions, with evidence visible and every action revision-logged.
  - **PREP-04**: A source-connector interface accepts normalized source/evidence payloads without implementing external retrieval or parsing.
  - **PREP-05**: A fixture-driven acceptance test proves structured candidates from a hypothetical future extractor can enter review and be resolved without changing the core graph model or invoking an LLM.

### Existing Backend Contract and Safety Baseline
- `backend/app/domain/graph.py` — `GraphClaim`, `GraphNode`, `GraphEdge`, `GraphResponse` models (no changes needed).
- `backend/app/domain/user_content.py` — `Origin` enum already includes `candidate` (D-06 satisfied by existing code).
- `backend/app/domain/revision.py` — `RevisionAction`, `RevisionResponse` (reuse for review logging).
- `backend/app/revisions/__init__.py` — `RevisionRepository.log_revision()` (reuse directly).
- `backend/app/core/errors.py` — `error_responses()`, `http_error()` (reuse for candidate endpoints).
- `backend/app/graph/database.py` — `Neo4jDatabase.execute_write` and `execute_query`.
- `backend/app/graph/ontology.py` — `Ontology.require_claim_type()`, `require_claim_status()`, `require_confidence_level()`, `require_relationship_type()` — validation for extraction payloads.
- `backend/app/api/graph.py` — Existing graph endpoint pattern, `GraphService` pattern.
- `backend/app/services/graph.py` — Existing service pattern for fetching graph data.
- `backend/app/spoiler/filter.py` — `VISIBLE_CLAIMS_QUERY` already includes `claim.origin IN ['canonical', 'candidate']` — candidate claims are already visible in the graph.
- `backend/app/main.py` — Router registration pattern.

### Existing Seed Data (for fixture inspiration)
- `data/dexter/seed/claims.json` — Existing canonical claim format.
- `data/dexter/seed/sources.json` — Existing source format.
- `data/dexter/seed/evidence_fragments.json` — Existing evidence format.
- `data/dexter/metadata/episodes.json` — Episode IDs for visibility derivation.

### Prior Phase Context
- `.planning/phases/04-revision-history-and-revert/04-CONTEXT.md` — D-16/D-19: Revision logging pattern in user-content write transactions; reuse for approve/reject/edit.
- `.planning/phases/04-revision-history-and-revert/04-SUMMARY.md` — `RevisionRepository.log_revision` takes optional `before`/`after` snapshots; same-transaction guarantee.
- `.planning/phases/01-backend-graph-foundation/01-CONTEXT.md` — D-12: Narrative claims use Claim nodes as provenance-rich source of truth; D-13: origin explicitly distinguishes canonical/candidate/user.
- `.planning/STATE.md` — Phase 4 complete; 146/146 backend tests; current project position.

</canonical_refs>

<code_context>
## Existing Code Insights

### Existing Origin Enum (already has `candidate`)
`backend/app/domain/user_content.py` lines 50–53:
```python
class Origin(StrEnum):
    CANONICAL = "canonical"
    CANDIDATE = "candidate"
    USER = "user"
```

The `candidate` origin is already declared and used in the existing `VISIBLE_CLAIMS_QUERY` spoiler filter. No enum changes needed.

### Existing Claim Model (already supports all fields)
`GraphClaim` in `backend/app/domain/graph.py` includes: `id`, `label`, `subject_id`, `predicate`, `object_id`, `claim_type`, `status`, `confidence_level`, `relationship_effect`, `visible_from_order`, `valid_from_order`, `valid_until_order`, `source_id`, `evidence_ids`, `origin`. All fields needed by candidate claims are present.

### Existing Spoiler Filter (already includes candidate claims)
`VISIBLE_CLAIMS_QUERY` in `backend/app/spoiler/filter.py` line 84:
```cypher
AND claim.origin IN ['canonical', 'candidate']
```
Candidate claims automatically participate in the spoiler-safe graph. No filter changes needed.

### Existing Revision System (reuse for review logging)
- `RevisionRepository.log_revision(tx, series_id, resource_type, resource_id, action, before, after, visible_from_order, created_at)` — reusable directly for approve/reject/edit.
- `RevisionAction.UPDATED` is the correct action for approve/reject (they change the claim's status field).
- Before/after snapshots follow the same `take_snapshot` pattern.

### Existing Error Contract
- `http_error(status_code, code, message)` — factory for stable error responses.
- `error_responses(404, 422, 503)` — decorator for OpenAPI documentation.
- New error codes for Phase 5 should follow the `snake_case` naming convention.

### Existing Seed Pattern
- Seed JSON files in `data/dexter/seed/` use deterministic namespaced IDs.
- The extraction fixture can follow the same structure for `origin: "candidate"` claims.
- Existing claims like `dexter:claim:s01e01:temporary_trust` already have `status: "candidate"` — so the `candidate` status value is already used in production data, validating the approach.

### Existing Graph Service Patterns
- `GraphService.fetch_graph()` in `backend/app/services/graph.py` — returns combined GraphResponse with nodes, edges, claims, sources, evidence.
- Candidate ingest should use `Neo4jDatabase.execute_write` for atomic batch creation.
- The review endpoints are simpler stateless operations that read-then-write within a single transaction.

### Integration Points
- `backend/app/main.py` — Register `candidates` router.
- `backend/app/domain/extraction.py` — New domain models for extraction schema and source connector interface.
- `backend/app/api/candidates.py` — All candidate ingest, list, get, approve, reject, edit routes.
- `backend/app/graph/candidates.py` — Candidate-specific Neo4j persistence (or extend `GraphService`).
- `data/dexter/test/extraction_fixture.json` — Fixture for PREP-05 acceptance test.
- `docs/extraction-schema.json` — Published JSON Schema artifact (optional but recommended).
- `backend/tests/test_candidate_ingest.py` — Integration tests for PREP-05.

### Reusable Assets
- `GraphService` — pattern for service-layer separation.
- `Neo4jDatabase.execute_write` — managed write transactions with rollback.
- `RevisionRepository.log_revision` — same-transaction revision logging.
- `Ontology.require_*()` methods — validation for ontology-constrained fields.
- `load_ontology()` — cached ontology allowlist.
- Existing test fixtures (`test_graph_api.py`, `test_revisions.py`) — patterns for test structure.

</code_context>

<specifics>
## Implementation Strategy

### Plan 05-01: Extraction schema + source-connector interface models
Files:
- `backend/app/domain/extraction.py` (new) — `ExtractionClaim`, `ExtractionBatchEnvelope`, `SourcePayload`, `EvidencePayload` Pydantic models with versioned schema field and ontology validation.
- `docs/extraction-schema.json` (new) — Published JSON Schema artifact exported from the Pydantic model.

### Plan 05-02: Candidate ingest API + candidate storage
Files:
- `backend/app/graph/candidates.py` (new) — CandidateRepository: `ingest_candidates(tx, ...)`, `get_candidate()`, `list_candidates()`.
- `backend/app/api/candidates.py` (new) — `POST /api/series/{series_id}/candidates/ingest` endpoint.
- `backend/app/main.py` (modify) — Register candidate router.
- `data/dexter/test/extraction_fixture.json` (new) — Fixture with S01E01-visible and S01E02-invisible candidate payloads.

### Plan 05-03: Review workflow (approve/reject/edit) + revision logging
Files:
- `backend/app/api/candidates.py` (extend) — `GET /.../candidates`, `GET /.../candidates/{id}`, `POST /.../candidates/{id}/approve`, `POST /.../candidates/{id}/reject`, `PATCH /.../candidates/{id}`.
- No new core model files — revision logging reuses `RevisionRepository.log_revision` directly.

### Plan 05-04: Integration tests + verification
Files:
- `backend/tests/test_candidate_ingest.py` (new) — PREP-01 schema validation, PREP-02 ingest and storage separation, PREP-03 approve/reject/edit + revision logging, PREP-04 source-connector contract validation, PREP-05 fixture-driven acceptance test.
- Full regression guard on existing 146+ tests.

### Key Design Principles

1. **The graph model does not change.** The existing Claim node with `origin: "candidate"` and the existing `VISIBLE_CLAIMS_QUERY` that includes `['canonical', 'candidate']` mean candidate claims flow through the exact same graph pipeline. Zero changes to `GraphNode`, `GraphEdge`, `GraphClaim`, `GraphResponse`, or the spoiler filter.

2. **Candidate isolation is enforced by API design, not just convention.** Only the ingest endpoint creates `origin: "candidate"` claims. Only the review endpoints can change candidate status. No generic user-content or seed path can touch candidates.

3. **Revision logging is non-negotiable.** Every approve, reject, and edit creates a `Revision` in the same transaction. This is proven by Phase 4's implementation.

4. **Fixtures prove the flow without an LLM.** The `extraction_fixture.json` file represents what a future extractor would output. The test POSTs it, verifies storage, exercises review, and asserts the graph model hasn't changed.

5. **No frontend in this phase.** However, the API contract must be clean enough for a future frontend agent to build a review UI against. Document every endpoint with OpenAPI summaries, constrained schemas, and error examples.

</specifics>

<deferred>
## Deferred Ideas

- Frontend review UI (candidate claim list, approve/reject/edit buttons in a review panel, evidence display) — required before overall Phase 5 can be marked full-stack complete, but explicitly out of scope for this backend-only phase.
- Actual LLM extraction pipeline, model clients, prompt templates, extraction agents, or any automated ingestion — post-v0.
- Automated source retrieval from OpenSubtitles, scripts/PDFs, podcasts, Fandom/IMDb/news, or external sites — post-v0.
- LLM chat, graph-RAG, retrieval tools, or spoiler-aware LLM guardrails — post-v0 (root milestone 9).
- Multi-user candidate review (per-user moderation queues, reviewer identities) — post-v0.
- Batch approve/reject or bulk candidate operations — defer unless planning proves they simplify the fixture test.
- Candidate diff view (comparing a candidate claim against similar canonical claims) — post-v0.
- Content deduplication beyond deterministic ID upserting (fuzzy matching, similarity scoring) — post-v0.

</deferred>

---

*Phase: 05-future-extraction-preparation*
*Context gathered: 2026-07-30*
