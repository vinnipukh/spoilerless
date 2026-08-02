# HD Graf Cehennemi — Coding Agent Project Specification

## 1. Project Summary

**HD Graf Cehennemi** is a spoiler-aware, source-grounded television-series knowledge graph application. The system allows a user to explore characters, events, locations, organizations, objects, claims, and relationships through an interactive graph interface similar to Obsidian's graph view. In parallel, the application provides an LLM chat interface that answers questions using only the graph data visible at the user's current watch progress.

The first prototype is intentionally limited to:

- **Series:** Dexter
- **Season:** Season 1
- **Episodes:** S01E01, S01E02, S01E03
- **Database:** Neo4j Community Edition
- **Backend:** FastAPI
- **Frontend:** React + TypeScript + Vite
- **Graph visualization:** Cytoscape.js
- **Python dependency manager:** uv
- **Local orchestration:** Docker Compose
- **Development method:** GSD workflow through Hermes Agent

This is a one-week vertical prototype. The priority is not broad content ingestion, production deployment, or a complete multi-user product. The priority is to demonstrate the central architecture convincingly:

```text
Curated episode data
        ↓
Source-grounded claims
        ↓
Neo4j graph
        ↓
Backend spoiler filtering
        ↓
Interactive graph UI
        ↓
LLM answers grounded in the visible subgraph
```

The prototype must look polished and must demonstrate that spoiler restrictions are enforced by the backend, not merely hidden in the browser.


### 1.1 One-Week Delivery Boundary

The one-week build uses **manually curated seed data** for Dexter S01E01-S01E03. The coding agent must not interpret the existence of `Source`, `EvidenceFragment`, `Claim`, or `origin: candidate` fields as permission to build an automatic ingestion system during this sprint.

For this prototype:

```text
Manual curation
    ↓
Validated JSON/YAML seed records
    ↓
Idempotent Neo4j seed command
    ↓
Spoiler-filtered API
```

The following pipeline is part of the intended long-term architecture, but is explicitly postponed:

```text
Subtitle or script scene
    ↓
LLM entity and relation extraction
    ↓
Schema validation
    ↓
Entity resolution
    ↓
Claim and evidence generation
    ↓
Human review
    ↓
Canonical Neo4j graph
```

The one-week prototype should leave clean extension points for this future pipeline without implementing it. Do not add placeholder frameworks, background queues, model clients, vector stores, or ingestion services merely to appear extensible.

---

## 2. Core Product Idea

The application has two equally important sides.

### 2.1 Interactive Second-Brain Graph

The user can:

- Explore characters and their relationships.
- Inspect events, locations, episodes, and evidence.
- Click a node or relationship to inspect its source.
- Add personal notes.
- Add user-created nodes or relationships.
- Distinguish system-generated content from user-created content.
- Inspect revision history for modified claims.

### 2.2 Spoiler-Aware GraphRAG Chat

The user can ask questions such as:

```text
What is Dexter's relationship with Debra so far?
Why does Dexter distrust this character?
Which events connect Dexter and Rita up to S01E02?
```

The LLM must not receive the full graph. It must receive only the subgraph allowed by the user's watch progress. A user at S01E01 must not receive S01E02 or S01E03 facts, metadata, character names, relationship counts, or indirect hints.

The first prototype may use a constrained GraphRAG-lite design:

```text
User question
    ↓
Entity extraction or safe predefined query selection
    ↓
Parameterized Cypher query
    ↓
Spoiler-filtered graph context
    ↓
LLM answer with evidence references
```

The LLM should not be given unrestricted Cypher generation privileges in the first prototype.

---

## 3. Non-Negotiable Architecture Rules

These rules are project invariants. Do not violate them without explicit user approval.

### 3.1 Spoiler Filtering Happens on the Backend

Future data must never be sent to the frontend and then hidden with CSS. The current candidate-review API is a known exception to this invariant: its list boundary is optional, and its single-candidate read has no watch boundary.

Bad:

```python
all_nodes = repository.get_everything()
return {
    "nodes": all_nodes,
    "frontend_should_hide_future_nodes": True,
}
```

Correct:

```python
visible_nodes = repository.get_visible_nodes(
    series_id=series_id,
    max_visible_order=user_progress.episode_order,
)
return {"nodes": visible_nodes}
```

The same restriction applies to:

- Search results
- Autocomplete suggestions
- Node degree
- Relationship counts
- Hidden labels
- Episode metadata
- LLM retrieval context
- Graph layout metadata
- Character appearance counts
- API error messages

Do not reproduce IMDb-style spoiler leaks such as displaying how many episodes an actor or character appears in.

### 3.2 Use `episode_order` for Visibility

Do not compare strings such as `S01E2 < S01E10`.

Every spoiler-sensitive record must have:

```text
visible_from_order: integer
```

Example:

```json
{
  "id": "character_dexter_morgan",
  "type": "Character",
  "label": "Dexter Morgan",
  "visible_from_order": 1
}
```

Visibility rule:

```text
record.visible_from_order <= user_progress.episode_order
```

### 3.3 Every Automatic Claim Requires Evidence

An automatically created claim must reference at least one evidence fragment.

Bad:

```json
{
  "subject": "Dexter",
  "predicate": "DISTRUSTS",
  "object": "Character X"
}
```

Correct:

```json
{
  "id": "claim_dexter_distrusts_x_001",
  "subject_id": "character_dexter_morgan",
  "predicate": "DISTRUSTS",
  "object_id": "character_x",
  "claim_type": "inferred_state",
  "status": "candidate",
  "visible_from_order": 1,
  "evidence_ids": ["evidence_subtitle_s01e01_001"],
  "origin": "automatic"
}
```

### 3.4 Automatic and User-Created Content Must Remain Distinguishable

Use an explicit field such as:

```text
origin:
- candidate
- user
- canonical
```

A user correction must not silently overwrite the automatic source record.

### 3.5 Do Not Physically Destroy History

The first prototype does not need full event sourcing, but modifications should create revision records.

Example:

```json
{
  "revision_id": "revision_0004",
  "entity_id": "claim_dexter_distrusts_x_001",
  "operation": "UPDATE",
  "previous_revision_id": "revision_0003",
  "actor_type": "user",
  "reason": "Changed relation from DISLIKES to DISTRUSTS"
}
```

### 3.6 Ontology Is Versioned

Node and relationship types must come from the ontology files.

Suggested files:

```text
ontology/
├── node_types.yaml
├── relation_types.yaml
└── claim_types.yaml
```

The coding agent must not invent new relationship labels during implementation without documenting why.

---

## 4. Initial Ontology

### 4.1 Node Types

The first prototype may use the following node types:

```yaml
ontology_version: "0.1"

node_types:
  structural:
    - Series
    - Season
    - Episode
    - Scene

  narrative:
    - Character
    - Event
    - Location
    - Organization
    - Object

  knowledge:
    - Claim
    - Source
    - EvidenceFragment

  user:
    - UserNote

  system:
    - Revision
```

Not every type must be fully exposed in the UI during the first week, but the graph model should remain compatible with this structure.

### 4.2 Relationship Types

Suggested structural relationships:

```text
PART_OF
PRECEDES
OCCURRED_IN
LOCATED_IN
```

Suggested narrative relationships:

```text
PARTICIPATED_IN
WITNESSED
CAUSED
AFFECTED
TARGETED
MENTIONED
```

Suggested character relationships:

```text
KNOWS
FAMILY_OF
WORKS_WITH
TRUSTS
DISTRUSTS
HELPS
OPPOSES
THREATENS
ATTACKS
KILLS
```

Suggested provenance relationships:

```text
SUPPORTED_BY
CONTRADICTED_BY
DERIVED_FROM
REFERS_TO
```

Suggested revision relationships:

```text
CORRECTS
SUPERSEDES
REVERTS_TO
```

Use the correct spelling:

```text
OCCURRED_IN
```

not:

```text
OCCURED_IN
```

### 4.3 Claim Types

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

Do not over-engineer confidence scoring during the one-week prototype. Store a level and an explanation rather than pretending that arbitrary decimal precision is scientifically calibrated.

---

## 5. Temporal Model

A major requirement is that information is time-bound.

Each spoiler-sensitive entity or assertion should include:

```text
visible_from_order
```

Claims may additionally include:

```text
valid_from_order
valid_until_order
```

These fields have different meanings.

- `visible_from_order`: the earliest episode after which the viewer is allowed to know the information.
- `valid_from_order`: the episode from which the relationship or state is considered true in the story.
- `valid_until_order`: the episode after which that state is no longer valid.

Example:

```json
{
  "subject_id": "character_a",
  "predicate": "TRUSTS",
  "object_id": "character_b",
  "visible_from_order": 3,
  "valid_from_order": 2,
  "valid_until_order": null
}
```

The viewer may only discover the trust relationship in episode 3 even if the state began in episode 2.

For the first prototype, `visible_from_order` is mandatory. The other two fields are optional but recommended for claim records.

---

## 6. Provenance and Evidence

Every claim should be explainable.

### 6.1 Subtitle Evidence

```json
{
  "id": "evidence_subtitle_s01e01_001",
  "source_id": "source_opensubtitles_s01e01_en",
  "source_type": "subtitle",
  "episode_id": "dexter_s01e01",
  "start_time": "00:04:12",
  "end_time": "00:04:31",
  "speaker": "Dexter",
  "content_hash": "sha256:example",
  "visible_from_order": 1
}
```

### 6.2 Script PDF Evidence

```json
{
  "id": "evidence_script_s01e01_001",
  "source_id": "source_script_s01e01",
  "source_type": "script_pdf",
  "episode_id": "dexter_s01e01",
  "page_number": 5,
  "scene_number": 3,
  "paragraph_hash": "sha256:example",
  "visible_from_order": 1
}
```

The public UI currently displays source metadata and locators as plain text; it does not render navigable source links. It must not republish complete copyrighted scripts or subtitles.

The prototype can use manually curated source references. Automated downloading and parsing are future work unless all core prototype tasks are already complete.

---

## 7. Neo4j Data Requirements

### 7.1 Stable IDs

Every visible node and relationship must have a stable string ID.

Examples:

```text
series_dexter
dexter_s01e01
character_dexter_morgan
event_dexter_s01e01_opening
claim_dexter_family_debra_001
evidence_subtitle_s01e01_001
```

Do not rely on Neo4j internal element IDs as public API identifiers.

### 7.2 Constraints

At minimum:

```cypher
CREATE CONSTRAINT series_id_unique IF NOT EXISTS
FOR (n:Series)
REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT episode_id_unique IF NOT EXISTS
FOR (n:Episode)
REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT character_id_unique IF NOT EXISTS
FOR (n:Character)
REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT claim_id_unique IF NOT EXISTS
FOR (n:Claim)
REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT source_id_unique IF NOT EXISTS
FOR (n:Source)
REQUIRE n.id IS UNIQUE;

CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS
FOR (n:EvidenceFragment)
REQUIRE n.id IS UNIQUE;
```

### 7.3 Idempotent Seeding

The seed process must use `MERGE` or another deterministic method.

Running the seed command twice must not duplicate nodes or relationships.

Suggested command:

```powershell
uv run --project backend python -m backend.app.graph.setup
```

### 7.4 Parameterized Queries

Never concatenate user input into Cypher.

Bad:

{% raw %}
```python
query = f"MATCH (n:Series {{id: '{series_id}'}}) RETURN n"
```
{% endraw %}

Correct:

```python
query = """
MATCH (n:Series {id: $series_id})
RETURN n
"""

record = session.run(query, series_id=series_id)
```

---

## 8. Backend API Contract

The backend should remain small and direct. Avoid unnecessary enterprise abstractions.

Recommended initial endpoints:

```text
GET  /health
GET  /api/series
GET  /api/series/{series_id}/episodes
GET  /api/series/{series_id}/graph
POST /api/series/{series_id}/progress
GET  /api/series/{series_id}/claims/{claim_id}
POST /api/notes
POST /api/chat
```

Not all endpoints must be completed on day one.

### 8.1 Graph Response

Suggested response:

```json
{
  "series": {
    "id": "series_dexter",
    "title": "Dexter"
  },
  "visible_until_order": 1,
  "nodes": [
    {
      "id": "character_dexter_morgan",
      "type": "Character",
      "label": "Dexter Morgan",
      "visible_from_order": 1,
      "origin": "curated",
      "properties": {}
    }
  ],
  "edges": [
    {
      "id": "edge_dexter_family_debra_001",
      "source": "character_dexter_morgan",
      "target": "character_debra_morgan",
      "type": "FAMILY_OF",
      "visible_from_order": 1,
      "claim_id": "claim_dexter_family_debra_001",
      "origin": "curated"
    }
  ]
}
```

### 8.2 Visibility Query Example

```cypher
MATCH (n)
WHERE n.series_id = $series_id
  AND coalesce(n.visible_from_order, 1) <= $visible_until_order
WITH collect(n) AS visible_nodes

UNWIND visible_nodes AS source
MATCH (source)-[r]->(target)
WHERE target IN visible_nodes
  AND coalesce(r.visible_from_order, 1) <= $visible_until_order

RETURN visible_nodes, collect(r) AS visible_relationships
```

The final implementation may use multiple simpler queries instead of one complex query. Prefer readability and correctness.

### 8.3 Health Check

The health endpoint should verify Neo4j connectivity rather than returning a hard-coded `"database": "connected"` value.

---

## 9. Frontend Requirements

The graph appearance is a primary project requirement.

The frontend must not look like default Cytoscape output.

### 9.1 Visual Language

Recommended node styling:

- `Character`: circle
- `Event`: rounded rectangle
- `Episode`: hexagon or compact tag-like node
- `Location`: square or rounded square
- `Organization`: diamond
- `UserNote`: note-shaped or dashed-border node

Recommended origin styling:

- `curated`: solid border
- `automatic`: standard border with system indicator
- `user`: dashed border or user badge

Recommended interaction:

- Selected node becomes visually dominant.
- Immediate neighbors remain highlighted.
- Unrelated nodes fade.
- Edge labels appear on hover or selection.
- A left-side detail panel shows claims, evidence, plain-text source locators, and revision history.
- A top episode selector displays the active spoiler boundary.
- Moving to a later episode requires explicit confirmation.

Use a graph layout suitable for small narrative graphs. `cose-bilkent` is preferred if available and stable. Keep the visible graph intentionally small.

A target of approximately 8–15 visible nodes per episode is preferable to rendering 50 noisy nodes.

### 9.2 Cytoscape Element Mapping

Example:

```typescript
type GraphNode = {
  id: string;
  type: string;
  label: string;
  visible_from_order: number;
  origin: "curated" | "automatic" | "user";
};

type GraphEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
  visible_from_order: number;
  claim_id?: string;
  origin: "curated" | "automatic" | "user";
};

const elements = [
  ...response.nodes.map((node) => ({
    data: {
      id: node.id,
      label: node.label,
      nodeType: node.type,
      origin: node.origin,
    },
  })),
  ...response.edges.map((edge) => ({
    data: {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.type,
      claimId: edge.claim_id,
      origin: edge.origin,
    },
  })),
];
```

The frontend must never reintroduce spoiler filtering logic as the security boundary. It may filter already-visible nodes for presentation, but the backend remains authoritative.

---

## 10. GraphRAG-Lite Design

The first prototype must demonstrate a real graph-backed answer path without requiring a full advanced GraphRAG framework.

Suggested safe flow:

```python
def answer_question(
    user_id: str,
    series_id: str,
    question: str,
) -> ChatResponse:
    progress = progress_service.get_progress(
        user_id=user_id,
        series_id=series_id,
    )

    entities = entity_matcher.find_known_entities(
        question=question,
        series_id=series_id,
        visible_until_order=progress.episode_order,
    )

    context = graph_retriever.retrieve_relationship_context(
        series_id=series_id,
        entity_ids=entities,
        visible_until_order=progress.episode_order,
    )

    return llm_service.answer_with_sources(
        question=question,
        graph_context=context,
    )
```

The LLM prompt should state:

```text
Use only the provided graph context.
Do not infer facts beyond the evidence.
Do not mention future episodes.
Cite claim and evidence identifiers in the answer.
If the available graph does not support the answer, say so.
```

The GraphRAG endpoint should return both the answer and structured citations.

Example:

```json
{
  "answer": "Up to S01E01, Dexter and Debra are established as siblings...",
  "citations": [
    {
      "claim_id": "claim_dexter_family_debra_001",
      "evidence_id": "evidence_subtitle_s01e01_001"
    }
  ]
}
```

Do not implement unrestricted text-to-Cypher in the one-week prototype.

---

## 11. Testing Requirements

Spoiler tests are mandatory.

Example test:

```python
def test_s01e01_graph_excludes_future_nodes(client):
    response = client.get(
        "/api/series/series_dexter/graph",
        params={"visible_until_order": 1},
    )

    assert response.status_code == 200

    payload = response.json()

    assert all(
        node["visible_from_order"] <= 1
        for node in payload["nodes"]
    )

    assert all(
        edge["visible_from_order"] <= 1
        for edge in payload["edges"]
    )

    returned_ids = {node["id"] for node in payload["nodes"]}

    assert "character_future_s01e02" not in returned_ids
    assert "event_future_s01e03" not in returned_ids
```

Additional tests should cover:

- Idempotent seeding
- Missing series returns 404
- Invalid episode order returns 422 or 400
- Edges never reference hidden nodes
- Evidence is not returned when its visibility exceeds the user's progress
- Chat retrieval does not include future claims
- Cypher parameters are used correctly

---

## 12. Future Automated Knowledge-Graph Ingestion Architecture

This section documents a post-prototype direction so future coding agents understand how automatic graph creation should eventually fit the existing model. It is **architectural guidance only** and is not part of the one-week implementation scope.

### 12.1 Main Principle

An LLM may assist with extracting candidate structure from source text, but it is not the source of truth. The source material, ontology, validation rules, and human review process remain authoritative.

The future extraction flow should be:

```text
Scene-sized source fragment
        ↓
Constrained structured extraction
        ↓
Pydantic or JSON Schema validation
        ↓
Canonical entity linking
        ↓
Candidate Claim creation
        ↓
Evidence attachment
        ↓
Human approval or rejection
        ↓
Canonical graph publication
```

Do not write raw model output directly into the canonical graph.

### 12.2 Process Sources in Small Units

Whole episodes should not be sent to an LLM as a single unstructured prompt. Prefer scene-sized or subtitle-window-sized fragments.

Recommended hierarchy:

```text
Source fragment → scene candidate graph
Scene graphs → episode candidate graph
Episode graphs → season graph
```

Benefits:

- Evidence timestamps and page references remain precise.
- Failed extraction can be retried for one scene.
- Entity resolution is easier to inspect.
- Prompt size and cost remain controlled.
- Spoiler boundaries naturally inherit the episode order.

A future input object may look like:

```python
from pydantic import BaseModel


class SceneInput(BaseModel):
    series_id: str
    episode_id: str
    episode_order: int
    scene_id: str
    source_id: str
    text: str
    start_time: str | None = None
    end_time: str | None = None
    page_number: int | None = None
```

### 12.3 Extraction Must Be Ontology-Constrained

The model must choose node and relationship types from the versioned ontology. It must not invent labels dynamically.

Allowed node types may include:

```text
Character
Location
Organization
Object
Event
Scene
Episode
```

Allowed relationship types must come from `ontology/relation_types.yaml`.

Bad model output:

```text
HAS_A_WEIRD_VIBE_WITH
IS_EMOTIONALLY_DISTANT_FROM
```

Acceptable output:

```text
DISTRUSTS
OPPOSES
KNOWS
```

When no ontology relationship accurately represents the source, the extractor should return an unresolved candidate rather than inventing a new predicate.

### 12.4 Structured Output Only

Do not parse loosely formatted prose such as:

```text
Entities:
Dexter, Debra
Relations:
Dexter is related to Debra
```

Use a validated structured response instead:

```python
from enum import StrEnum
from pydantic import BaseModel, Field


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExtractedEntity(BaseModel):
    mention: str
    proposed_type: str
    canonical_id_hint: str | None = None


class ExtractedRelation(BaseModel):
    source_mention: str
    predicate: str
    target_mention: str
    explicitness: str
    confidence: ConfidenceLevel
    evidence_text: str = Field(min_length=1)


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity]
    relations: list[ExtractedRelation]
```

If validation fails, do not write partial output to Neo4j.

### 12.5 No Prior-Knowledge Leakage

Television-series knowledge may already exist in a model's parameters. Extraction prompts must explicitly prohibit using prior knowledge.

Future extractor prompt rule:

```text
Use only the supplied source fragment.
Do not use prior knowledge of the television series.
Do not infer later events, hidden identities, motives, or relationships unless
supported by the supplied fragment.
Return only ontology-approved node and relationship types.
Every relation must include local evidence from the supplied fragment.
```

This requirement is separate from backend spoiler filtering. Both are necessary.

### 12.6 Canonical Entity Resolution

Different mentions must be resolved to stable canonical entities.

Example:

```json
{
  "canonical_id": "character_dexter_morgan",
  "canonical_name": "Dexter Morgan",
  "aliases": ["Dexter", "Dex", "Morgan"]
}
```

A future entity linker must not automatically accept the top candidate in every case. Ambiguous mentions such as `Morgan` may refer to multiple characters.

Suggested policy:

```python
def decide_entity_link(top_score: float) -> str:
    if top_score >= 0.90:
        return "auto_link"
    if top_score >= 0.70:
        return "manual_review"
    return "unresolved"
```

Thresholds are placeholders and must be validated on real project data before production use.

### 12.7 Candidate Claims, Not Immediate Canonical Edges

Automatic extraction should create candidate claims with evidence rather than silently publishing trusted graph facts.

Example candidate claim:

```json
{
  "id": "claim_candidate_0001",
  "subject_id": "character_dexter_morgan",
  "predicate": "WORKS_WITH",
  "object_id": "organization_miami_metro",
  "claim_type": "explicit_fact",
  "status": "candidate",
  "confidence": "high",
  "origin": "automatic",
  "visible_from_order": 1,
  "evidence_ids": ["evidence_subtitle_s01e01_001"]
}
```

A human reviewer may later approve, edit, dispute, or reject it. Canonical graph edges may be materialized only after approval, or derived at query time from approved claims.

### 12.8 Human-in-the-Loop Review

The future review UI should allow a user to:

- Compare the source fragment with extracted entities and relations.
- Link a mention to an existing entity.
- Create a new entity when necessary.
- Change an ontology predicate.
- Approve or reject a candidate claim.
- Record the reason for a correction.
- Preserve the original automatic extraction in revision history.

Automatic content must never become indistinguishable from curated or user-created content.

### 12.9 Suggested Future Service Boundary

A future ingestion package may eventually look like:

```text
backend/app/ingestion/
├── schemas.py
├── extractor.py
├── entity_linker.py
├── claim_builder.py
├── review_repository.py
└── pipeline.py
```

Conceptual orchestration:

```python
def process_scene(scene: SceneInput) -> ExtractionResult:
    raw_output = extractor.extract(
        text=scene.text,
        allowed_node_types=ontology.node_types,
        allowed_relation_types=ontology.relation_types,
    )

    validated = ExtractionResult.model_validate(raw_output)

    linked_entities = entity_linker.resolve(
        series_id=scene.series_id,
        entities=validated.entities,
    )

    candidate_claims = claim_builder.build_candidates(
        episode_order=scene.episode_order,
        source_id=scene.source_id,
        relations=validated.relations,
        linked_entities=linked_entities,
    )

    review_repository.save_candidates(
        entities=linked_entities,
        claims=candidate_claims,
    )

    return validated
```

This code is illustrative. Do not create these modules during the current sprint unless the user explicitly changes scope.

### 12.10 Deliberately Rejected Shortcuts

The future implementation should avoid:

- LLM output written directly to canonical Neo4j nodes.
- Free-form relationship labels.
- Blind acceptance of the highest similarity match.
- Whole-season prompts.
- NetworkX as a required production intermediary.
- Evidence-free inferred claims.
- Automatic overwrite of curated data.
- Model-generated facts unsupported by source text.

NetworkX may still be used for offline analysis or experiments, but Neo4j remains the canonical graph store.

### 12.11 Future Definition of Done

The automatic ingestion phase should not be considered complete until:

1. Scene-sized source fragments can be processed deterministically.
2. Output is validated against a strict schema.
3. Entity and relation types are ontology-constrained.
4. Every candidate claim contains source evidence.
5. Ambiguous entity links enter manual review.
6. The model cannot directly publish canonical graph facts.
7. Human approval actions create revision records.
8. Spoiler visibility is inherited from the source episode.
9. Tests prove later-episode material cannot enter earlier retrieval contexts.
10. Reprocessing the same source does not create uncontrolled duplicates.

---

## 12. Scope Boundaries for the One-Week Prototype

Do not implement these unless the core vertical slice is already complete:

- Full OpenSubtitles automation
- LLM-based entity and relation extraction
- Automatic entity linking or alias resolution
- Candidate-claim review expansion beyond the implemented ingest, list/get, approve, reject, and edit workflow
- Full script PDF ingestion pipeline
- Podcast transcription
- IMDb scraping
- Fandom scraping
- News ingestion
- Authentication expansion beyond the implemented Google sign-in and session-cookie flow
- Multi-user authorization
- GraphQL
- Vector search
- Advanced hybrid retrieval
- Community detection
- Production deployment architecture
- Kubernetes
- Full event sourcing
- Automatic ontology evolution
- Large-scale confidence calibration
- Multi-series support
- Actor appearance counts
- Mobile application
- Social features

These are future-work items.

The one-week deliverable should optimize for:

```text
working
visible
testable
source-grounded
spoiler-safe
demo-ready
```

not for maximum feature breadth.

---

## 13. Recommended One-Week Execution Order

### Day 1
- Finalize ontology.
- Create deterministic Dexter S01E01–S01E03 seed data.
- Add Neo4j constraints and indexes.
- Build `/api/series`, `/episodes`, and spoiler-filtered `/graph`.

### Day 2
- Connect React to the real graph endpoint.
- Render Cytoscape graph.
- Add node selection and detail panel.

### Day 3
- Spend most of the day polishing graph appearance.
- Add node-type styles.
- Add neighbor highlighting.
- Add edge filtering.
- Add episode selector and confirmation modal.

### Day 4
- Add Claim, Source, and EvidenceFragment details.
- Show source links and evidence metadata in the side panel.

### Day 5
- Add GraphRAG-lite chat using the filtered graph.
- Support a few reliable demo questions.

### Day 6
- Add user notes.
- Add basic revision history.
- Improve empty states and loading/error UX.

### Day 7
- Run spoiler tests.
- Fix bugs.
- Prepare README, architecture diagram, screenshots, and demo script.

---

## 14. Coding Agent Operating Instructions

Before making changes:

1. Inspect the current repository.
2. Preserve existing working configuration.
3. Use `uv`, `pyproject.toml`, and `uv.lock`.
4. Do not replace the stack.
5. Do not create a second frontend or backend.
6. Do not migrate from Neo4j.
7. Do not add GraphQL.
8. Do not introduce a large framework unless required.
9. Keep modules small and readable.
10. Prefer explicit code over speculative abstractions.

When uncertain, prefer:

```text
a smaller working implementation
over
a larger incomplete architecture
```

Every task should be independently demonstrable.

Every spoiler-sensitive endpoint should have a test.

Every automated claim should be traceable to evidence.

Every frontend graph element should come from the backend response.

Every future-phase idea should be documented instead of silently implemented.

---

## 15. Definition of Done

The prototype is complete when a reviewer can perform this demo:

1. Open Dexter Season 1.
2. Set progress to S01E01.
3. View a polished graph containing only S01E01 information.
4. Click a character or relationship.
5. Inspect its claim and source evidence.
6. Attempt to move to S01E02.
7. See a spoiler confirmation modal.
8. Confirm and observe newly visible nodes and relationships.
9. Add a personal note.
10. Ask the LLM about a visible character relationship.
11. Receive an answer grounded in Neo4j claims and evidence.
12. Verify that the same question at S01E01 does not leak S01E02 or S01E03 information.

The prototype does not need to be a complete product. It must be a polished and technically honest proof that the architecture works.
