# Phase 1: Backend Graph Foundation - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the minimum reliable backend and Neo4j graph foundation needed for the polished Cytoscape prototype. It preserves and improves the working brownfield stack rather than rebuilding it: local Neo4j/FastAPI/React runtime, real database health, ontology-aligned constraints and deterministic Dexter S01E01–03 seed data, metadata endpoints, an evidence-backed spoiler-filtered graph endpoint, and executable acceptance evidence. Phase 2 should be able to focus almost entirely on visual product polish.

The phase consolidates canonical milestones 1–4 and requirements INFRA-01..03, META-01..03, API-01..04, and SEED-01..04. Authentication, extraction/LLM features, user editing/history, and frontend product implementation remain outside this phase.

</domain>

<decisions>
## Implementation Decisions

### Delivery and Brownfield Constraints
- **D-01:** Preserve the existing working repository and local setup; inspect and adapt current modules instead of rebuilding the project from scratch.
- **D-02:** Use Python 3.13 with `uv` and root `pyproject.toml` for backend dependency and command management; do not introduce a competing Python package workflow.
- **D-03:** Keep the implementation intentionally small and direct: a limited number of clear database/repository, service, API, seed, and test modules; no repository-pattern ceremony or event sourcing.
- **D-04:** Phase 1 graph scope is Series, Episode, Character, Event, Location, Claim, Source, EvidenceFragment, and only the structural/narrative relationships needed for Dexter S01E01–03. `UserNote` implementation remains in Phase 3 unless a passive schema reference is unavoidable.

### Spoiler Boundary and API Contract
- **D-05:** `GET /api/series/{series_id}/graph` requires a stateless `visible_until_order` query parameter. The value must match a persisted `Episode.episode_order` for that series; do not persist watch progress or clamp invalid values in Phase 1.
- **D-06:** The graph response contains top-level `series`, `visible_until_order`, `nodes`, `edges`, `claims`, `sources`, and `evidence` collections. References use stable string IDs so Phase 2 can build node/edge detail panels without new provenance endpoints.
- **D-07:** Spoiler filtering happens in parameterized Neo4j/data-access queries before response construction. React must never receive future metadata and hide it with CSS.
- **D-08:** Filtering uses numeric `episode_order`, not episode-code string comparison. It applies to nodes, structural relationships, projected narrative edges, claims, sources, evidence, labels, names, locators, and derived counts; every returned edge must close over returned nodes.
- **D-09:** Unknown `series_id` returns `404`; missing, malformed, or non-persisted `visible_until_order` returns `422`. Errors expose stable `detail.code` plus a safe `detail.message`.

### Graph, Ontology, and Provenance
- **D-10:** `ontology/node_types.yaml`, `ontology/relation_types.yaml`, and `ontology/claim_types.yaml` version 0.1 are authoritative allowlists. Seed validation rejects undeclared values; ontology changes must be explicit, documented, and versioned rather than introduced silently in Cypher.
- **D-11:** Every graph-visible seeded entity, claim, source, evidence fragment, native relationship that is serialized, and projected edge uses a readable deterministic namespaced string ID.
- **D-12:** Structural topology such as `PART_OF`, `PRECEDES`, `OCCURRED_IN`, and `LOCATED_IN` uses native Neo4j relationships. Evidence-backed narrative facts use `Claim` nodes as the single provenance-rich source of truth; the API derives Cytoscape-ready narrative edges from visible claims and includes `claim_id`.
- **D-13:** Every spoiler-sensitive node, relationship, claim, source, and evidence record has `visible_from_order`. Canonical/system, candidate/automatic, and future user-created content remain distinguishable through explicit origin/ownership metadata.
- **D-14:** Every curated Claim links to at least one EvidenceFragment and Source. Evidence contains a short curated excerpt or faithful paraphrase, exact `episode_id`, a precise timestamp/scene/page locator as available, source and retrieval metadata, and a content hash where possible.

### Deterministic Seed Behavior
- **D-15:** The seed command performs non-destructive seed-owned upserts: `MERGE` by stable ID, converge seed-owned properties and required relationships to fixture values, and preserve any future `origin=user` content. A destructive database reset is not the normal seed path.
- **D-16:** Seed data is deterministic and limited to Dexter S01E01–S01E03. Do not include later spoilers, long transcript dumps, or actor episode counts.
- **D-17:** Required uniqueness/existence constraints and useful indexes are created idempotently before data writes; all values are passed as Cypher parameters.

### Runtime Health and Error Handling
- **D-18:** FastAPI starts in degraded mode when Neo4j is unavailable. Driver construction/ownership and close behavior belong to application lifespan/dependency boundaries, not import-time connection side effects.
- **D-19:** `/health` performs a real connectivity check: healthy database returns `200`; unavailable database returns sanitized `503` while Swagger remains reachable for diagnosis.
- **D-20:** All database-backed endpoints map Neo4j availability failures to sanitized `503` responses without exposing raw driver exceptions, credentials, connection URIs, or Cypher.

### Verification Contract
- **D-21:** Use fast isolated API/repository tests for lifecycle, error mapping, validation, and response shaping plus focused live-Neo4j integration tests for constraints, Cypher behavior, seeding, and spoiler filtering.
- **D-22:** Prove idempotency by running the seed command twice against the same test database and asserting exact stable IDs, per-type node/relationship counts, uniqueness, preserved properties, and unchanged graph-response content.
- **D-23:** Test spoiler boundaries 1, 2, and 3 with deterministic future-only sentinels. Assertions scan the complete serialized JSON for forbidden future IDs, names, labels, edges, claims, evidence text/locators, and count signals—not only node visibility fields.
- **D-24:** Provide one repeatable documented smoke command, in addition to automated tests, that verifies Neo4j Browser, Swagger/OpenAPI, React dev URL, `/health`, metadata endpoints, seed execution, and graph boundaries. Completion requires captured runtime output, not scaffold/file presence.

### Claude's Discretion
- Exact names and boundaries of the small backend modules, provided import-time side effects are removed and dependencies remain testable.
- Exact number of curated Characters, Events, Locations, and Claims, provided all three episodes have meaningful boundary sentinels and Phase 2 receives a visually useful small graph.
- Exact safe English backend error messages; stable machine-readable codes and HTTP statuses are locked.
- Exact locator type per evidence fragment based on available source material, while episode association and precise locator value remain mandatory.
- Additional indexes beyond required uniqueness/existence constraints when justified by the concrete graph queries.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Product Scope and Phase Requirements
- `ROADMAP.md` — Canonical Prototype v0 product scope, ontology direction, milestones 1–8, exclusions, and demo story. Planning artifacts must not narrow it.
- `.planning/PROJECT.md` — Brownfield facts, core value, constraints, and the five-phase vertical delivery interpretation.
- `.planning/ROADMAP.md` — Rebaselined five-phase dependency order; Phase 1 consolidates canonical milestones 1–4.
- `.planning/REQUIREMENTS.md` — Exact Phase 1 requirement set and 30/30 one-to-one traceability.

### Ontology v0.1
- `ontology/node_types.yaml` — Authoritative node-type allowlist and ontology version.
- `ontology/relation_types.yaml` — Authoritative structural, participation, character, provenance, and revision relationship allowlists.
- `ontology/claim_types.yaml` — Authoritative claim types, statuses, and confidence levels.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `docker-compose.yml`: Existing Neo4j Community service, persisted local volumes, Browser/Bolt ports, and healthcheck; preserve the working service rather than replacing it.
- `backend/app/core/config.py`: Existing Neo4j settings boundary and `.env` integration.
- `backend/app/graph/seed.py`: Existing metadata JSON loading, idempotent constraint syntax, `MERGE`-based Series/Episode seed, and `PRECEDES` construction to extend rather than discard.
- `backend/app/api/series.py`: Existing parameterized episode query and Pydantic response path for `GET /api/series` and episode listing.
- `data/dexter/metadata/series.json` and `data/dexter/metadata/episodes.json`: Existing deterministic Dexter metadata fixtures.

### Established Patterns
- FastAPI routes return Pydantic response models, while Neo4j records are currently converted through `record.data()`.
- Neo4j settings are environment-backed; `.env` remains local and `.env.example` documents required values.
- Cypher already uses parameters for series lookup and seed payloads; new graph queries must retain this property.
- React/Vite runs separately at `http://localhost:5173`; Phase 1 preserves reachability but does not replace the frontend scaffold.

### Integration Points
- `backend/app/main.py`: Currently constructs `FastAPI` twice, imports a global database object, verifies Neo4j during startup, and hardcodes `/health`; this is the main lifecycle/health correction point.
- `backend/app/graph/database.py`: Currently creates `GraphDatabase.driver` in a module-level singleton; this must become lazily owned/injectable so imports and isolated tests do not connect.
- `backend/app/api/series.py`: Extend the router or add a small graph router/service while preserving existing metadata endpoints.
- `backend/app/graph/seed.py`: Expand into the deterministic ontology-validated setup/seed command and maintain idempotency.
- `pyproject.toml`: Add any Phase 1 dependencies/dev tooling here and execute through `uv`.

</code_context>

<specifics>
## Specific Ideas

- Target graph shape is Cytoscape-ready: each node has at least `id`, `type`, `label`, `visible_from_order`, and `origin`; each projected narrative edge has `id`, `source`, `target`, `type`, `visible_from_order`, and `claim_id`.
- The backend should make Phase 2 primarily a visual implementation effort by returning complete spoiler-safe provenance in one graph payload.
- Preserve the user's confirmed working local Neo4j, FastAPI, and Vite setup; improvements must not break existing run commands without documented replacements.
- The delivery window is one week, so prioritize executable vertical behavior and runtime evidence over abstractions.

</specifics>

<deferred>
## Deferred Ideas

- Server-side persisted watch progress — unnecessary for the single-user local Phase 1 contract; Phase 2 sends the selected validated order.
- `UserNote` behavior, user-created nodes/relationships, and visual ownership treatment — Phase 3.
- Revision history and revert — Phase 4.
- Candidate extraction contracts and review workflow — Phase 5.
- Authentication, GraphQL, vector search, GraphRAG, scraping, PDF parsing, external ingestion, operational extraction, and LLM integration — post-v0 or explicitly later phases.

</deferred>

---

*Phase: 01-backend-graph-foundation*
*Context gathered: 2026-07-29*
