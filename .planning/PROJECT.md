# HD Graf Cehennemi

## What This Is

A spoiler-safe narrative knowledge graph for TV series. Prototype v0 covers Dexter Season 1, Episodes 1–3 and lets a user explore source-backed narrative knowledge, control the visible episode boundary, add personal knowledge, and inspect/revert revisions.

Root `ROADMAP.md` is the canonical product-scope source. These `.planning` artifacts translate its Prototype v0 milestones 1–8 into executable phases without narrowing that scope.

## Core Value

Users can safely explore a TV-series knowledge graph without seeing information beyond their selected watch progress because filtering occurs in the backend before data reaches the frontend or any future LLM.

## Brownfield Baseline (Facts, Not Completion Claims)

The repository contains:

- Docker Compose configuration for Neo4j 2026 Community and `.env.example`.
- A FastAPI scaffold, CORS/lifespan wiring, a Neo4j driver wrapper, and a health route. The health response is currently hardcoded and is not evidence of a live database check.
- Series/Episode response models and series/episode routes.
- A seed script for constraints, Series/Episode nodes, `PART_OF`, and `PRECEDES`; it exists but is documented as unexecuted, so persistence and idempotency are not verified.
- Dexter S01E01–03 metadata and ontology YAML files.
- A Vite/React/TypeScript/Cytoscape scaffold. Scaffold presence is not a completed product UI.
- A root static `index.html` product/demo reference that is not connected to the backend.

No file-presence statement above marks runtime behavior verified or a Prototype v0 milestone complete.

## Prototype v0 Scope (Active)

- Local Neo4j/FastAPI/React infrastructure with real health and runnable, idempotent setup verification.
- Dexter Series and S01E01–03 Episode metadata graph, ordering relationships, and metadata endpoints.
- A manually curated Character/Claim/Source/EvidenceFragment seed graph with episode locators and spoiler visibility metadata.
- A spoiler-aware graph API that filters nodes, relationships, claims, evidence, labels, names, and counts at the data-access layer.
- A React + TypeScript + Cytoscape graph experience with series/episode loading, watch-progress selection, confirmation before advancing, graph exploration, details, and evidence display.
- User notes plus creation/editing of custom nodes and relationships, kept distinguishable from canonical/automatic content.
- A simplified append-only revision history for creations, edits, rejections, corrections, history inspection, and revert-as-a-new-revision.
- Preparation for future extraction: structured extraction JSON contract, candidate claims, human review/approve/reject/edit workflow, and a source-connector interface. This preparation accepts structured candidates but does not run an LLM or automated ingestion.
- Tests and acceptance checks for spoiler boundaries, provenance, revision behavior, setup, and user-facing UX.

## Post-v0 Scope

- Operational automated ingestion/extraction from OpenSubtitles, scripts/PDFs, podcasts, Fandom/IMDb/news, or other external sites.
- LLM extraction and LLM chat/retrieval.
- Multi-user accounts, production authentication, collaboration, deployment/public hosting, mobile/social features.

## Constraints

- **Spoiler safety:** every exposed graph element carries `visible_from_order`; the backend filters before returning data. Hidden names, labels, evidence, and aggregate counts must not leak.
- **Provenance:** automatic/candidate claims require EvidenceFragments with source, episode, locator, retrieval metadata, and content hash where possible. Manually curated seed claims are evidence-backed.
- **Separation:** canonical, candidate/automatic, and user-created content are represented and displayed distinctly.
- **Temporal semantics:** confidence and relationship effect remain separate; claims can use validity bounds independently of spoiler visibility.
- **History:** edits and reverts append revisions; history is not destroyed.
- **Local stack:** Neo4j, FastAPI/Pydantic, React 19 + TypeScript + Vite + Cytoscape.js; Python packaging through `uv`.
- **No real auth:** Prototype v0 is a single-user local experience.

## Key Decisions

| Decision | Rationale | Status |
|----------|-----------|--------|
| Root `ROADMAP.md` defines Prototype v0 | Prevent planning documents from narrowing the canonical demo | Active |
| Neo4j is the graph source of truth | Graph-native storage fits connected narrative data | Existing direction; runtime verification pending |
| Backend/data-access spoiler filtering | Downstream clients must never receive future data | Required, pending verification |
| Evidence-backed atomic claims | Users can understand why knowledge exists | Required |
| Separate user/candidate/canonical content | Preserves provenance and supports correction | Required |
| Simplified revision log | Meets v0 history/revert needs without Git-like graph versioning | Pending |
| Extraction contracts before extraction automation | Keeps the model extensible while actual extraction remains post-v0 | Required |

---
*Last updated: 2026-07-28 — reconciled to canonical root Prototype v0 milestones 1–8*
