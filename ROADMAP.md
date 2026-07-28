# HD Graf Cehennemi — Prototype Roadmap

## 0. Project Summary

**HD Graf Cehennemi** is a spoiler-safe narrative knowledge graph system for TV series.

The prototype focuses on **Dexter Season 1, Episodes 1–3**. The system stores characters, episodes, events, claims, relationships, evidence fragments, user notes, and revision history in a graph database. Users can browse the graph like an Obsidian-style second brain while controlling their visible spoiler boundary by selecting the last episode they have watched.

The long-term goal is to combine:

- manual graph editing,
- source-backed automatic extraction from subtitles and scripts,
- spoiler-aware graph filtering,
- source-linked evidence,
- version history,
- and LLM chat over only the allowed subgraph.

---

## 1. Core Design Principles

### 1.1 Spoiler safety is enforced at the data-access layer

The LLM and frontend must never receive data beyond the user’s selected watch progress.

Bad approach:

```text
Send all data to the LLM and ask it not to spoil.
```

Correct approach:

```text
Filter graph data in the backend before it reaches the frontend or LLM.
```

Every node, claim, relationship, and evidence fragment must have a `visible_from_order` field.

### 1.2 All automatic knowledge must be source-backed

No automatic claim enters the graph without evidence.

Each claim should connect to at least one `EvidenceFragment`, which points to:

- source type,
- source URL or locator,
- episode,
- timestamp/page/scene reference,
- retrieval metadata,
- and content hash when possible.

### 1.3 User-created knowledge is separate from automatic knowledge

The system must distinguish between:

- canonical show metadata,
- automatically extracted candidate claims,
- user notes,
- user-created nodes,
- and user corrections.

### 1.4 Confidence is not relationship strength

Example:

```text
Character A strongly distrusts Character B.
```

This has two separate dimensions:

- `relationship_effect`: how strong the relationship is,
- `confidence_level`: how confident the system is in that claim.

### 1.5 Version history is mandatory

User edits, LLM extractions, rejections, corrections, and reversions must be recorded.

The prototype will use a simplified revision log instead of Git-based graph versioning.

---

## 2. Prototype Scope

### In scope for Prototype v0

- One series: Dexter
- One season: Season 1
- Three episodes: S01E01, S01E02, S01E03
- Neo4j graph database
- FastAPI backend
- React + TypeScript frontend
- Cytoscape.js graph visualization
- Episode progress selector
- Spoiler confirmation modal
- Filtered graph endpoint
- Series and episode metadata endpoints
- Manual seed graph data
- Source/evidence display
- Basic revision history model
- Basic user-created note support

### Out of scope for Prototype v0

- OpenSubtitles automation
- Script PDF parsing
- Podcast transcription
- Fandom/IMDb/news ingestion
- LLM extraction pipeline
- LLM chat
- Multi-user accounts
- Production authentication
- Deployment

These will be added after the core graph and spoiler model are proven.

---

## 3. Current Stack

```text
Frontend: React + TypeScript + Vite + Cytoscape.js
Backend:  FastAPI + Neo4j Python Driver + Pydantic
Database: Neo4j Community via Docker Compose
Package management: uv for Python, npm for frontend
IDE: PyCharm Professional or VS Code
```

---

## 4. Planned Folder Structure

```text
hdgrafcehennemi/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── domain/
│   │   ├── graph/
│   │   ├── spoiler/
│   │   └── revisions/
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── api/
│       ├── components/
│       ├── graph/
│       └── pages/
│
├── ontology/
│   ├── node_types.yaml
│   ├── relation_types.yaml
│   └── claim_types.yaml
│
├── data/
│   └── dexter/
│       ├── metadata/
│       ├── sources/
│       └── seed/
│
├── docs/
│   ├── architecture.md
│   ├── spoiler-model.md
│   └── ontology.md
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 5. Ontology v0.1

### Node types

```yaml
structural:
  - Series
  - Season
  - Episode
  - Scene

narrative:
  - Character
  - Location
  - Organization
  - Object
  - Event

knowledge:
  - Claim
  - Source
  - EvidenceFragment

user:
  - UserNote

system:
  - Revision
```

### Relationship types

```yaml
structural:
  - PART_OF
  - PRECEDES
  - OCCURRED_IN
  - LOCATED_IN

participation:
  - PARTICIPATED_IN
  - WITNESSED
  - CAUSED
  - AFFECTED
  - TARGETED
  - MENTIONED

character:
  - KNOWS
  - FAMILY_OF
  - WORKS_WITH
  - TRUSTS
  - DISTRUSTS
  - HELPS
  - OPPOSES
  - THREATENS
  - ATTACKS
  - KILLS

provenance:
  - SUPPORTED_BY
  - CONTRADICTED_BY
  - DERIVED_FROM
  - REFERS_TO

revision:
  - CORRECTS
  - SUPERSEDES
  - REVERTS_TO
```

### Claim types

```yaml
claim_types:
  - explicit_fact
  - observed_event
  - inferred_state
  - external_interpretation
  - user_authored

claim_statuses:
  - candidate
  - corroborated
  - canonical
  - disputed
  - rejected

confidence_levels:
  - low
  - medium
  - high
  - verified
```

---

## 6. Data Model: Atomic Claim

A claim should represent one atomic piece of knowledge.

Example:

```json
{
  "id": "claim_001",
  "subject_id": "character_dexter_morgan",
  "predicate": "KNOWS",
  "object_id": "character_debra_morgan",
  "claim_type": "explicit_fact",
  "status": "canonical",
  "visible_from_order": 1,
  "valid_from_order": 1,
  "valid_until_order": null,
  "confidence_level": "verified",
  "relationship_effect": 0.3,
  "created_by": "seed_data",
  "ontology_version": "0.1"
}
```

A claim should not be treated as final truth unless its status is `canonical` or `corroborated`.

---

## 7. Milestones

## Milestone 1 — Local infrastructure

Status: mostly complete.

Tasks:

- [x] Create GitHub repository
- [x] Start Neo4j with Docker Compose
- [x] Start FastAPI backend
- [x] Start Vite frontend
- [x] Create `.env.example`
- [x] Create ontology files
- [x] Create Dexter metadata files
- [ ] Add backend Neo4j connection health check
- [ ] Add seed script for series and episodes
- [ ] Add first API endpoints

Acceptance criteria:

- Neo4j Browser opens at `http://localhost:7474`
- FastAPI Swagger opens at `http://127.0.0.1:8000/docs`
- React frontend opens at `http://localhost:5173`
- `/health` returns database connection status

---

## Milestone 2 — Metadata graph

Tasks:

- [ ] Create Neo4j constraints for `Series` and `Episode`
- [ ] Seed Dexter series node
- [ ] Seed S01E01–S01E03 episode nodes
- [ ] Create `PART_OF` relationships
- [ ] Create `PRECEDES` relationships
- [ ] Add `GET /api/series`
- [ ] Add `GET /api/series/{series_id}/episodes`

Acceptance criteria:

Neo4j query:

```cypher
MATCH (series:Series)<-[:PART_OF]-(episode:Episode)
RETURN series, episode;
```

returns one series and three episodes.

---

## Milestone 3 — Spoiler-aware graph endpoint

Tasks:

- [ ] Define graph response model
- [ ] Add `visible_from_order` to all seeded nodes and claims
- [ ] Add `GET /api/graph?series_id=series_dexter&visible_until_order=1`
- [ ] Ensure backend filters all nodes and edges
- [ ] Add unit tests for spoiler boundaries

Acceptance criteria:

When `visible_until_order=1`, the API must not return S01E02 or S01E03 data.

---

## Milestone 4 — Manual seed graph

Tasks:

- [ ] Create character seed file
- [ ] Create source seed file
- [ ] Create evidence seed file
- [ ] Create claim seed file
- [ ] Seed basic Dexter S01E01 character network
- [ ] Add relationship claims with evidence links

Acceptance criteria:

The frontend can display a small graph containing:

- Dexter series
- S01E01–S01E03 episode nodes
- selected character nodes
- visible claims
- source/evidence references

---

## Milestone 5 — Frontend graph UI

Tasks:

- [ ] Replace Vite starter screen
- [ ] Create main layout
- [ ] Fetch series and episodes from backend
- [ ] Add watch-progress selector
- [ ] Add spoiler confirmation modal
- [ ] Render graph with Cytoscape.js
- [ ] Add node detail panel
- [ ] Add edge/claim detail panel
- [ ] Display evidence links

Acceptance criteria:

The user can select a watched episode and see only allowed graph elements.

---

## Milestone 6 — User notes and manual editing

Tasks:

- [ ] Add `UserNote` model
- [ ] Add endpoint for creating user notes
- [ ] Add endpoint for creating custom nodes
- [ ] Add endpoint for creating custom relationships
- [ ] Separate user-created content visually in frontend

Acceptance criteria:

The user can add a note to a character or claim and see it in the detail panel.

---

## Milestone 7 — Revision history

Tasks:

- [ ] Create `Revision` model
- [ ] Log claim creation
- [ ] Log claim update
- [ ] Log claim rejection
- [ ] Log user correction
- [ ] Add revision display panel
- [ ] Add simple revert operation

Acceptance criteria:

A user can edit a claim and inspect previous versions.

---

## Milestone 8 — Preparation for LLM extraction

Tasks:

- [ ] Define extraction output JSON schema
- [ ] Add `candidate` claim layer
- [ ] Add candidate review endpoint
- [ ] Add approve/reject/edit workflow
- [ ] Add source connector interface

Acceptance criteria:

The system can accept structured candidate claims from a future extractor without changing the core graph model.

---

## Milestone 9 — LLM chat, later phase

Tasks:

- [ ] Add spoiler-aware retrieval tools
- [ ] Add graph query tools for character relationships
- [ ] Add graph query tools for event timelines
- [ ] Add source-cited answer generation
- [ ] Add backend guardrail preventing LLM from querying beyond user progress

Acceptance criteria:

The LLM answers questions using only graph data visible to the user’s selected episode.

---

## 8. Prototype Demo Story

A good demo flow:

1. Open the app.
2. Select Dexter.
3. Set watch progress to S01E01.
4. Show that only S01E01-visible nodes and claims are displayed.
5. Open a character node.
6. Show source-backed claims.
7. Try to move to S01E02.
8. Show spoiler warning confirmation.
9. Confirm progress update.
10. Show newly unlocked graph elements.
11. Add a user note.
12. Edit a claim.
13. Show revision history.

---

## 9. Evaluation Plan

### Spoiler safety tests

- S01E01 users cannot see S01E02/S01E03 nodes.
- S01E01 users cannot search for future nodes.
- S01E01 API responses do not contain future labels, names, or counts.
- LLM retrieval tools cannot override user progress.

### Source tests

- Every automatic claim has at least one evidence fragment.
- Evidence contains an episode reference.
- Evidence contains a locator such as timestamp, page, or scene.

### Revision tests

- Every edit creates a revision.
- Old values can be inspected.
- Revert creates a new revision instead of deleting history.

### UX tests

- User can understand why a relationship exists.
- User can distinguish automatic and manual content.
- User can safely change episode progress.

---

## 10. Future Research/Academic Angle

This project can be framed as:

> A spoiler-aware, provenance-backed narrative knowledge graph with human-in-the-loop correction and future LLM integration.

Potential academic contributions:

- spoiler-aware graph retrieval,
- temporal visibility modeling for fictional narratives,
- evidence-backed claim graphs,
- provenance-aware graph-RAG,
- human-in-the-loop narrative knowledge editing,
- revision-controlled personal media knowledge bases.

