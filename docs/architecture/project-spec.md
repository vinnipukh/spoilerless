# Spoilerless — Authoritative Project Specification

> **Status vocabulary:** **implemented** describes the current repository; **prototype target** describes the original one-week vertical slice; **future direction** is architectural guidance, not a claim of implementation.
>
> This document is the canonical project and coding-agent specification after consolidation. Detailed implementation references remain in [ARCHITECTURE.md](../ARCHITECTURE.md), [API.md](../API.md), [DEVELOPMENT.md](../DEVELOPMENT.md), [TESTING.md](../TESTING.md), and [frontend-api-contract.md](../reference/frontend-api-contract.md).

## 1. Aim, prototype boundary, and current state

Spoilerless is a spoiler-aware, source-grounded television-series knowledge-graph application. It combines an Obsidian-like interactive graph for characters, events, locations, organizations, objects, claims, relationships, sources, evidence, notes, and revisions with an LLM chat that may use only graph data visible at the viewer's persisted watch progress.

The historical one-week prototype target was deliberately narrow:

- Dexter, Season 1, episodes S01E01–S01E03;
- Neo4j Community, FastAPI, React + TypeScript + Vite, Cytoscape.js;
- `uv` for Python dependencies and Docker Compose for local Neo4j;
- GSD through Hermes Agent as the development method;
- manually curated, validated JSON/YAML seed records rather than broad ingestion;
- a polished, visible, testable, source-grounded, spoiler-safe, demo-ready vertical slice rather than a production or maximum-breadth product.

The architecture the prototype set out to prove remains the project thesis:

```text
Curated episode data → source-grounded claims → Neo4j
→ backend spoiler filtering → interactive graph UI
→ LLM answers grounded in the visible subgraph
```

**Current implementation:** the repository now contains the original graph slice plus Google sign-in and server-side sessions, persisted watch progress, user content, revisions, candidate ingestion/review APIs, GraphRAG chat and retrieval tools, settings, confirmable ChangeSets, and share links. The generated OpenAPI document contains 50 method/path operations over 37 path templates, including the export and share routes now registered in `spoilerless/app/main.py`. Chat is optional and disabled unless configured. Candidate-review reads are no longer a spoiler-boundary exception: both candidate list and candidate detail call `_require_resolved_boundary` in `spoilerless/app/api/candidates.py`, so an omitted or nonpersisted episode order returns 422 and the repository read is boundary-filtered. Several production concerns remain unresolved; see [Current gaps](#13-current-gaps-and-scope-boundaries) and [ROADMAP.md](../ROADMAP.md).

### 1.1 Delivery boundary and extension discipline

The original seed path was and remains:

```text
Manual curation → validated seed records → idempotent Neo4j setup
→ spoiler-filtered API
```

The presence of `Source`, `EvidenceFragment`, `Claim`, extraction contracts, or `origin: candidate` does **not** authorize an agent to build an automatic ingestion platform. The current code accepts structured candidate batches and supports review, but it does not download, parse, or extract from subtitles/scripts.

The long-term path is:

```text
Subtitle/script scene → constrained extraction → schema validation
→ entity resolution → candidate claims + evidence → human review
→ canonical graph publication
```

Keep clean extension points, but do not add placeholder frameworks, background queues, model clients, vector stores, or ingestion services merely to appear extensible. Scope changes require explicit approval.

## 2. Two equal product sides

### 2.1 Interactive second-brain graph

The intended experience lets a user:

- explore characters and relationships and inspect events, locations, episodes, claims, sources, and evidence;
- select a node or claim-backed relationship and understand why it exists;
- add notes and user-created nodes/relationships;
- distinguish canonical, candidate, and user-origin content;
- inspect revisions and revert supported changes.

The current frontend implements a Cytoscape graph, progress selection and advance confirmation, a left-side detail inspector, source/evidence metadata, user content, revision display, a right-side chat sheet, and settings. Source locators are currently plain text; the public detail UI does not provide navigable source links.

### 2.2 Spoiler-aware GraphRAG chat

Questions such as “What is Dexter's relationship with Debra so far?” must be answered only from the boundary-visible graph. A viewer at S01E01 must not receive S01E02/S01E03 facts, names, metadata, counts, indirect hints, or retrieval context.

The safe design is constrained GraphRAG, not unrestricted model-authored Cypher:

```text
Question → allowlisted retrieval tool selection → parameterized Cypher
→ spoiler-filtered context → evidence-grounded answer + structured citations
```

The system prompt and runtime must require the model to:

- use only supplied graph context;
- avoid unsupported inference and future episodes;
- cite retrieved claim/evidence/source identifiers;
- say when the available graph does not support an answer.

**Implemented:** chat resolves the boundary from persisted user progress; server-owned tool arguments inject `series_id` and `visible_until_order`; retrieval is bounded and allowlisted; citations are validated against the current turn's retrieved IDs. No retrieval tool accepts raw Cypher. See [ARCHITECTURE.md §7.8](../ARCHITECTURE.md#78-graphrag-lite-chat-pipeline) and [API.md, Chat](../API.md#chat).

## 3. Non-negotiable architecture invariants

These rules may not be weakened without explicit user approval.

### 3.1 Backend spoiler filtering

Future story data must be filtered before it reaches the frontend or LLM; sending all data and hiding it with CSS or prompting the model not to spoil is forbidden. Presentation code may filter an already-safe response, but it is not the security boundary.

The same rule covers nodes, edges, claims, evidence, sources, search, autocomplete, degree/count metadata, hidden labels, episode metadata, graph layout metadata, character appearance counts, retrieval context, and error behavior. Hidden and missing resources should be indistinguishable where a boundary applies. Do not reproduce IMDb-style leaks such as total appearance counts.

**Candidate reads require a resolved boundary:** `GET /api/series/{series_id}/candidates` and `GET /api/series/{series_id}/candidates/{claim_id}` both declare `visible_until_order` and invoke `_require_resolved_boundary` in `spoilerless/app/api/candidates.py` — an omitted or nonpersisted episode order returns 422, and the repository read is boundary-filtered so above-boundary detail reads as missing. Treat any weakening of this as a documented gap, not precedent for new endpoints. Boundary behavior by route is specified in [frontend-api-contract.md](../reference/frontend-api-contract.md#spoiler-boundary-and-fail-closed-reads).

### 3.2 Episode-order visibility and narrative time

Never compare episode codes lexicographically. Every spoiler-sensitive story record must have a positive integer `visible_from_order`, and visibility is:

```text
record.visible_from_order <= viewer_boundary
```

`episode_order`/`visible_until_order` is the boundary coordinate. Claims can also carry:

- `valid_from_order`: when the state becomes true in the story;
- `valid_until_order`: when it ceases to be true;
- `visible_from_order`: when the viewer is allowed to discover it.

Discovery and narrative validity are different. A state may begin in episode 2 but become knowable only in episode 3. The main graph queries in `spoilerless/app/spoiler/filter.py` gate the matched Claim and its validity window, but the retrieval evidence/source lookups (`GET_EVIDENCE_QUERY`, `GET_SOURCES_QUERY`, `EVIDENCE_FOR_CLAIMS_QUERY`, `SOURCES_FOR_CLAIMS_QUERY` in `spoilerless/app/retrieval/tools.py`) gate the `SUPPORTED_BY`/`REFERS_TO` relationship and the evidence/source node visibility without gating the matched Claim's own `visible_from_order` or `valid_from_order`/`valid_until_order`. Null visibility must fail closed; setup includes a visibility-integrity audit because Neo4j Community lacks the required property-existence constraint.

### 3.3 Provenance and evidence

Every automatically extracted claim must attach at least one local evidence fragment and a source. Evidence should preserve an episode and precise locator (timestamp, page, scene, or equivalent), source type/locator, retrieval metadata, and a content hash when possible. A model is not a source of truth.

The public application must not republish complete copyrighted scripts or subtitles. Manually curated source references are valid for the prototype. Current canonical seed validation rejects claims with missing source/evidence references; user-authored relationship claims are a separate origin and may lack evidence.

### 3.4 Origin and correction semantics

The public origin vocabulary is exactly:

```text
canonical | candidate | user
```

Do not reintroduce stale `curated`/`automatic` public values or parallel flags such as `is_custom`. Candidate extraction, canonical show data, user notes/content, and user corrections must remain distinguishable. A correction must not silently overwrite the source record; use a user-owned override/proposal or an auditable review transition.

### 3.5 Revision history, not destructive history

Full event sourcing was not required for the prototype, but meaningful mutations must append revision records with resource identity, action, before/after state, actor/ownership context where available, time, and visibility. Revert must create a new revision rather than deleting history. Current revisions use `Created`, `Updated`, `Deleted`, and `Reverted`; supported ChangeSet application/revert also logs revisions. Hard deletion of current user-owned resources does not erase the revision record.

### 3.6 Versioned ontology

Node, relationship, claim type, claim status, and confidence values come from:

- [`ontology/node_types.yaml`](../../ontology/node_types.yaml)
- [`ontology/relation_types.yaml`](../../ontology/relation_types.yaml)
- [`ontology/claim_types.yaml`](../../ontology/claim_types.yaml)

Agents must not invent predicates dynamically. If no relationship fits, record an unresolved candidate and propose an intentional ontology change. Preserve the correct spelling `OCCURRED_IN`, never `OCCURED_IN`.

### 3.7 Stable IDs, constraints, deterministic writes, and safe Cypher

- Public resources use stable string IDs; never expose Neo4j internal element IDs as API identity.
- Setup creates uniqueness constraints and visibility/lookup indexes for graph and application nodes.
- Seed and candidate ingestion must be deterministic/idempotent; rerunning must not create uncontrolled duplicates.
- Never concatenate user/model input into Cypher. Bind values as parameters and keep labels/predicates behind server-owned ontology allowlists.
- Neo4j remains the canonical graph store.

The current setup command is:

```bash
uv run --project spoilerless python -m spoilerless.app.graph.setup
```

See [DEVELOPMENT.md](../DEVELOPMENT.md) for contributor commands and [ARCHITECTURE.md](../ARCHITECTURE.md) for current storage/query details.

## 4. Ontology and atomic-claim semantics

Ontology v0.1 defines:

- structural nodes: `Series`, `Season`, `Episode`, `Scene`;
- narrative nodes: `Character`, `Location`, `Organization`, `Object`, `Event`;
- knowledge nodes: `Claim`, `Source`, `EvidenceFragment`;
- user/system nodes: `UserNote`, `Revision`;
- structural relationships: `PART_OF`, `PRECEDES`, `OCCURRED_IN`, `LOCATED_IN`;
- participation relationships: `PARTICIPATED_IN`, `WITNESSED`, `CAUSED`, `AFFECTED`, `TARGETED`, `MENTIONED`;
- character relationships: `KNOWS`, `FAMILY_OF`, `WORKS_WITH`, `TRUSTS`, `DISTRUSTS`, `HELPS`, `OPPOSES`, `THREATENS`, `ATTACKS`, `KILLS`;
- provenance relationships: `SUPPORTED_BY`, `CONTRADICTED_BY`, `DERIVED_FROM`, `REFERS_TO`;
- revision relationships: `CORRECTS`, `SUPERSEDES`, `REVERTS_TO`;
- claim types: `explicit_fact`, `observed_event`, `inferred_state`, `external_interpretation`, `user_authored`;
- statuses: `candidate`, `corroborated`, `canonical`, `disputed`, `rejected`;
- confidence levels: `low`, `medium`, `high`, `verified`.

A Claim represents one atomic assertion with stable subject, predicate, object, temporal visibility/validity, status, confidence, origin, ontology version, and provenance. Treat only `canonical` or `corroborated` status as accepted truth. `relationship_effect` (what the relationship does/how strong it is) is separate from `confidence_level` (how certain the system is). Do not pretend arbitrary decimal confidence is scientifically calibrated; prefer an ontology level plus explanation. The committed YAML files and [ARCHITECTURE.md §7.2–7.4](../ARCHITECTURE.md#72-the-claim-model) are the detailed reference.

Not every ontology type must be exposed in the prototype UI, but the model must remain compatible with the versioned ontology.

## 5. Backend and API obligations

Keep the backend small, direct, and layered rather than adding enterprise abstractions. The original suggested route sketch has been superseded by the real series-scoped API. In particular, the graph route is:

```text
GET /api/series/{series_id}/graph?visible_until_order={positive persisted episode order}
```

not the stale `/api/graph?series_id=...` example. The graph response includes `series`, `visible_until_order`, `nodes`, `edges`, `claims`, `sources`, and `evidence`; each returned edge is closed over returned nodes. Health must verify Neo4j connectivity, not return a hard-coded connected value.

The generated OpenAPI document is the machine-readable contract. See [API.md](../API.md) for all current auth, series, graph, user-content, revision, candidate, progress, chat, ChangeSet, and settings routes. Every endpoint must use parameterized Cypher and preserve applicable visibility, ownership, and fail-closed rules.

## 6. Frontend and UX requirements

Graph appearance is a primary requirement, not an incidental default Cytoscape view.

- Give node types a distinguishable visual language (for example circles for characters, rounded rectangles for events, compact/hexagonal episode nodes, square locations, diamond organizations, and note/dashed styling for user content).
- Give canonical, candidate/system, and user origins distinct visual treatment; user content should be clearly recognizable.
- Make selection visually dominant, keep immediate neighbors highlighted, fade unrelated nodes, and reveal edge labels on hover/selection.
- Use a left-side inspector for claims, evidence, plain-text source locators, notes, and revisions; the current chat occupies an independent right-side sheet.
- Show the active episode boundary and require explicit confirmation before advancing progress.
- Use an appropriate layout such as `cose-bilkent` when stable and keep narrative graphs intentionally legible. The historical target was roughly 8–15 visible nodes per episode rather than 50 noisy nodes.
- Every graph element must derive from the backend response; the frontend must not manufacture a second graph representation or become the spoiler boundary.

Current frontend behavior and exact types are documented in [ARCHITECTURE.md §4.1](../ARCHITECTURE.md#41-frontend-react--cytoscape) and [frontend-api-contract.md](../reference/frontend-api-contract.md).

## 7. GraphRAG constraints

A real graph-backed answer path is required, but a large GraphRAG framework is not. The current allowlisted tool layer is the intended pattern:

- server, never model, supplies `series_id`, user identity, and visibility boundary;
- every tool applies its own boundary and validity filters to the nodes and relationships it returns; the evidence/source lookups accept claim IDs and gate the associated `SUPPORTED_BY`/`REFERS_TO` relationship and the evidence/source node, but do not re-apply Claim visibility or validity predicates to the matched Claim itself (see [§3.2](#32-episode-order-visibility-and-narrative-time));
- traversal depth, path hops, search/result counts, and context size are bounded server-side;
- relationship labels and node labels come from allowlists;
- no unrestricted text-to-Cypher or raw query parameter;
- retrieved context is deduplicated and citation validation is limited to IDs retrieved for that turn;
- answers include structured citations and graph focus, or explicitly state insufficient evidence.

Any future retrieval enhancement—vector, hybrid, community summaries—must preserve these controls rather than bypass them.

## 8. Testing obligations

Spoiler tests are mandatory. At minimum, tests must prove:

- S01E01 graph, search, errors, counts, evidence, and retrieval cannot expose S01E02/S01E03 information;
- hidden and missing direct reads are indistinguishable where required;
- invalid/nonpersisted episode orders fail validation;
- edges never reference hidden endpoints;
- claim validity windows and evidence/source visibility are enforced;
- LLM tools cannot override persisted progress and future claims do not enter context;
- automated/candidate claims require provenance;
- seed and ingestion reruns are idempotent;
- Cypher values are parameterized;
- edits append revisions, old values remain inspectable, and revert appends rather than erases;
- users can understand evidence, distinguish origins, and advance progress safely.

Every new spoiler-sensitive endpoint needs tests. See [TESTING.md](../TESTING.md) for current pytest/Vitest commands, patterns, and the warning that integration tests use live local Neo4j.

## 9. Future automated knowledge-graph ingestion architecture

This section is **future direction**. The implemented `spoilerless/app/domain/extraction.py` contracts and candidate review routes prepare an interface; there is no running extractor or source parser.

### 9.1 Authority and pipeline

Sources, ontology, schema validation, and human review remain authoritative. Never write raw model output directly to the canonical graph.

```text
Scene-sized source fragment → constrained structured extraction
→ strict validation → canonical entity linking → candidate claims
→ evidence attachment → human approval/rejection → publication
```

### 9.2 Small source units

Process scene-sized or subtitle-window-sized fragments, not whole episodes or seasons. Compose fragment candidate graphs into episode and season graphs. This keeps timestamps/page references precise, makes retries inspectable, reduces prompt cost, simplifies resolution, and naturally inherits the episode spoiler boundary. A future scene input needs stable series/episode/scene/source IDs, episode order, text, and optional time/page locators.

### 9.3 Ontology-constrained, structured output

Extraction must return strict Pydantic/JSON-Schema-compatible objects, never prose parsed by heuristics. Entities include mention, proposed ontology type, and optional canonical hint; relations include source mention, allowlisted predicate, target mention, explicitness, confidence, and nonempty local evidence. Validation failure must prevent partial Neo4j writes.

The extraction prompt must prohibit prior series knowledge, later events, hidden identities, unsupported motives/relationships, and non-ontology labels. This is independent of backend spoiler filtering; both protections are necessary.

### 9.4 Canonical entity resolution

Resolve aliases to stable entities but do not blindly accept the top similarity result. Ambiguous mentions enter manual review or remain unresolved. Historical thresholds such as 0.90 auto-link / 0.70 review were illustrative placeholders and must be calibrated on real project data before use.

### 9.5 Candidate claims and human review

Automatic extraction creates evidence-backed candidate claims, not immediate canonical edges. Review must support comparing source and extraction, linking/creating entities, changing predicates, approving/rejecting, recording correction reasons, and preserving original extraction in revision history. Approved facts may be materialized as edges or projected from approved Claim nodes, but automatic content must remain distinguishable.

The current API implements candidate ingest, list/get, edit, approve, and reject, with deterministic IDs and revision logging. It does not implement extraction, entity linking, source fetching, or the full review UI.

### 9.6 Possible future service boundary

If scope is approved, a small `spoilerless/app/ingestion/` package may separate schemas, extractor, entity linker, claim builder, review repository, and orchestration pipeline. This is illustrative, not a mandate to create empty modules. The pipeline should validate before linking, build candidates with inherited visibility/provenance, save to review storage, and remain reprocessable without duplicates.

### 9.7 Deliberately rejected shortcuts

Do not use:

- raw LLM output as canonical Neo4j data;
- free-form relationship labels;
- blind top-similarity entity linking;
- whole-season prompts;
- NetworkX as a required production intermediary;
- evidence-free inferred claims;
- automatic overwrite of canonical/curated data;
- model facts unsupported by the supplied source.

NetworkX remains acceptable for offline analysis/experiments; Neo4j remains canonical.

### 9.8 Future ingestion definition of done

Automatic ingestion is not complete until:

1. scene-sized fragments process deterministically;
2. output passes a strict schema;
3. entity and relation types are ontology-constrained;
4. every candidate claim has source evidence;
5. ambiguous links enter review;
6. the model cannot publish canonical facts directly;
7. approval/correction creates revisions;
8. spoiler visibility is inherited from the source episode;
9. tests prevent later-episode material from entering earlier retrieval;
10. reprocessing does not create uncontrolled duplicates.

## 10. Historical prototype execution plan

The original one-week order is retained as historical rationale, not as current work status:

1. ontology, deterministic S01E01–03 data, constraints/indexes, series/episode/graph API;
2. real frontend integration, Cytoscape rendering, selection and detail panel;
3. concentrated visual polish, node styles, neighbor highlighting, edge filtering, episode selector and confirmation;
4. Claim/Source/Evidence detail and provenance display;
5. filtered GraphRAG chat and reliable demo questions;
6. notes, basic revisions, empty/loading/error UX;
7. spoiler tests, fixes, README/architecture/screenshots/demo preparation.

Current completion and remaining work are tracked in [ROADMAP.md](../ROADMAP.md).

## 11. Coding-agent operating instructions

Before changing the repository:

1. Inspect the current tree and verify claims against source/tests/manifests.
2. Preserve working configuration and the existing stack.
3. Use `uv`, `pyproject.toml`, and `uv.lock`; use npm for the existing frontend.
4. Do not create a second frontend/backend, migrate away from Neo4j, add GraphQL, or introduce a large framework without an actual requirement.
5. Keep modules small/readable and prefer explicit code over speculative abstraction.
6. Prefer a smaller working implementation over a larger incomplete architecture.
7. Make every task independently demonstrable.
8. Add a test for every spoiler-sensitive endpoint and preserve fail-closed behavior.
9. Keep every automated claim traceable to evidence.
10. Derive every frontend graph element from backend data.
11. Document future ideas rather than silently implementing them.
12. Keep API, frontend contract/types, tests, and documentation synchronized.

## 12. Prototype definition of done

The prototype target is satisfied when a reviewer can:

1. open Dexter Season 1 and set progress to S01E01;
2. see a polished graph containing only S01E01-visible information;
3. select a character or relationship and inspect claim/source evidence;
4. attempt to advance, see explicit spoiler confirmation, confirm, and see newly visible graph elements;
5. add a personal note and distinguish it from canonical/candidate content;
6. inspect revision history for supported edits;
7. ask about a visible relationship and receive a Neo4j/evidence-grounded answer;
8. verify the same question at S01E01 leaks no S01E02/S01E03 information.

This is a technically honest proof of the architecture, not a claim that the system is a complete production product. Operational acceptance evidence and unresolved gaps belong in [ROADMAP.md](../ROADMAP.md).

## 13. Current gaps and scope boundaries

Implemented preparation must not be confused with the following incomplete or future work:

- automated OpenSubtitles/script PDF ingestion, podcast transcription, IMDb/Fandom/news ingestion;
- LLM entity/relation extraction and automatic alias/entity resolution;
- candidate-review expansion beyond the current API workflow and a full review UI;
- navigable source links in the public detail UI (current locators are plain text);
- multi-user authorization/ownership across currently unauthenticated user-content, revision, and candidate routes;
- authentication expansion beyond Google sign-in and session cookies;
- a general CSRF strategy for all state-changing cookie-authenticated routes;
- vector search, advanced hybrid retrieval, community detection;
- production deployment architecture, Kubernetes, and a release/deployment pipeline; CI itself is configured — `.github/workflows/ci.yml` runs a pull_request workflow with backend Neo4j setup/pytest and DB-pollution checks plus frontend build/lint/audit jobs, while the release workflow is only a promotion skeleton;
- full event sourcing, automatic ontology evolution, calibrated confidence scoring;
- multi-series breadth, actor appearance counts, mobile, and social features.

The authoritative maintenance backlog and research direction are in [ROADMAP.md](../ROADMAP.md). Preserve these boundaries unless scope is explicitly changed.
