# Frontend Implementation

I built the frontend as a single-page application using React and TypeScript. The user interface lets viewers explore television story graphs, inspect character relationships, take notes, and ask questions through a chat assistant without seeing spoilers ahead of their watch progress.

The frontend code is in `frontend/src/`. The main entry file is `App.tsx`. To keep the code organized, I moved navigation logic into `useWorkspaceNavigation.ts` and scene management into `useWorkspaceScene.ts`. The interface has two main views: Overview Mode, which shows main characters and major episode events, and Full Mode, which provides tabs for Story events, Character networks, Evidence connections, and an Advanced view with user edits and revision history. View state like active filters, selected elements, and camera focus is managed through `useSceneState.ts`.

The graph is displayed on a canvas using Cytoscape.js in `GraphCanvas.tsx`. I separated layout calculations from the canvas component by writing `useCytoscapeLayout.ts`. This hook runs layout algorithms like `fcose` for clustered networks and left-to-right `dagre` (`rankDir: 'LR'`) for investigation trees. It applies layout settings and restores cached node positions while keeping user interactions responsive.

When graph data changes, updating the entire canvas would reset the camera and make the UI jump. To solve this, I wrote `cytoscapeReconciler.ts`. It compares current canvas elements with new backend data inside a `cy.batch()` call. It adds new nodes, updates compound episode boundaries, changes edges, and removes elements that are no longer visible. Node positions from previous views are stored in `positionCache.ts`, which lets the canvas restore node positions when returning to an earlier view.

When a user picks an episode in `EpisodeSelector.tsx`, `useWorkspaceScene.ts` calls `fetchVisualization` in `frontend/src/api/graph.ts`. The helper `apiFetch` in `client.ts` sends a GET request to `/api/series/{series_id}/graph/visualization` with the selected episode order and session cookie. The backend responds with a `VisualizationDTO`. Then, `sceneElements.ts` turns that data into Cytoscape elements using colors and sizes from `graphTokens.ts`, and `cytoscapeReconciler.ts` updates the canvas.

Clicking a node or edge opens `DetailPanel.tsx` in a side panel. The panel has tabs for overview information in `OverviewTab.tsx`, connected claims in `ClaimsTab.tsx`, source citations in `EvidenceTab.tsx`, and user notes in `NotesTab.tsx`. The chat assistant runs inside `ChatSheet.tsx` with a draggable sidebar built from `ResizableRail.tsx`. It uses a Bring-Your-Own-Key setup where provider settings and API keys stay in the browser localStorage under `spoilerless:byok-llm-settings`. When the user sends a message, `api/chat.ts` sends a POST request with `X-LLM-Provider` and `X-LLM-Api-Key` headers, reads the Server-Sent Events stream, and shows citation chips that highlight referenced nodes on the graph.

About four days before the presentation, I was worried that I would not finish the remaining frontend work and testing in time. I talked with my workplace mentor, who works as a DA & AI Lead, and got advice on how to organize the remaining tasks and use AI coding agents to help speed up development. I wrote a large part of the remaining code during the final night before the deadline. The next morning, I did not like how some of the panels looked, and when I asked some of my friends to try it, they found some interactions confusing too. I reworked the panel tabs, adjusted the graph layout transitions, and cleaned up the styling before leaving for work.

# Backend Implementation

I built the backend with Python 3.13 and FastAPI. It handles user authentication, watch boundary filtering, Neo4j database queries, Redis caching, and GraphRAG chat retrieval.

The backend source code is located in `spoilerless/app/`. When the server starts up in `main.py`, it connects to Neo4j using `Neo4jDatabase.open()` and initializes Redis. I added middleware to protect the server: `BodySizeLimitMiddleware` blocks request bodies larger than 1 MB with a 413 status, `TrustedHostMiddleware` checks incoming Host headers, and `CORSMiddleware` allows requests from the frontend origin. Authentication in `api/auth.py` verifies Google ID tokens using `ProductionGoogleVerifier` in `services/auth.py` and stores sessions as SHA-256 hashes in `repository/session.py`. When running with `ENVIRONMENT=production`, FastAPI turns off `/docs` and `/openapi.json` so API schemas are not publicly exposed.

To prevent spoilers, every request that reads story data passes through boundary resolution in `spoilerless/app/api/boundary.py` using `resolve_effective_boundary` and the `require_boundary` dependency. Anonymous users and users without saved progress are clamped to episode 1. For authenticated users with progress, it computes the effective boundary from the requested order, the saved view-as-of order, and the watched-through order. If a request asks for an episode number that does not exist in the database, the server returns a 422 error.

When a user requests a character network projection, the request moves through the backend:
1. The frontend sends `GET /api/series/series_dexter/graph/visualization?view=character_network&episode_order=2`, which enters `get_visualization` in `spoilerless/app/api/graph.py`.
2. The `require_boundary` dependency checks the user progress and sets the effective episode order to 2.
3. `VisualizationProjectionService` builds a cache key from the series ID, view type, and episode order, and checks Redis using `get_cached_visualization` in `graph_cache.py`.
4. If the data is not in cache, the service calls `GraphService.read_visible_graph(series_id, effective_order)` in `spoilerless/app/services/graph.py`.
5. `GraphService` runs a parameterized query in Neo4j through `Neo4jDatabase.execute_query()`, passing `$series_id` and `$visible_until_order = 2`.
6. `views.py` processes the returned database records, calculates character connections, assigns group numbers, and builds a `VisualizationDTO`.
7. The service saves the DTO to Redis with a 300-second TTL and sends the JSON response back with status 200.

`GraphService` in `spoilerless/app/services/graph.py` acts as a central coordinator for graph reads. When candidate extractions, custom nodes, custom relationships, or revisions change, it calls `invalidate_series_cache()` to clear outdated cache entries in Redis. Rate limiting in `services/rate_limit.py` uses Redis buckets to limit requests (login to 10 per 5 minutes, chat to 20 per minute, and writes to 30 per minute) and returns 503 if Redis becomes unreachable in production.

For chat questions, `ChatService` in `spoilerless/app/services/chat.py` receives messages from `POST /api/series/{id}/chat/sessions/{session_id}/messages`. It limits concurrent requests using `llm_max_concurrent_generations` (default 4) and calls `RetrievalPipeline` in `spoilerless/app/retrieval/pipeline.py`. The pipeline runs allowlisted retrieval tools against Neo4j to find relevant characters and claims. It places this evidence into a 9-section context prompt, cleans out potential delimiter injection text in the generated answer with `_neutralize_answer_delimiters()`, sends the prompt to the selected LLM provider, and streams the answer back to the frontend using Server-Sent Events.

# Graph Database and Neo4j Implementation

Neo4j is the database used to store series metadata, story entities, claims, evidence, user notes, and revision history.

I modeled story entities as separate node labels: `:Character`, `:Event`, `:Location`, `:Organization`, and `:Object`. Show structure is stored in `:Series` and `:Episode` nodes. Provenance data uses `:Claim`, `:EvidenceFragment`, and `:Source` nodes. User-related data uses `:AppUser`, `:UserSeriesProgress`, `:UserNote`, and `:Revision` nodes.

Physical relationships in Neo4j connect these structures:
- `(:Episode)-[:PART_OF]->(:Series)` connects episodes to their series.
- `(:Episode)-[:PRECEDES]->(:Episode)` connects consecutive episodes in timeline order.
- `(:Claim)-[:SUPPORTED_BY]->(:EvidenceFragment)` links statements to supporting evidence.
- `(:Claim)-[:REFERS_TO]->(:Source)` links statements to their source document.
- `(:UserNote)-[:REFERS_TO]->(target)` links personal notes to characters or events.
- `(:AppUser)-[:HAS_PROGRESS]->(:UserSeriesProgress)` links users to their watch history.

A major implementation choice in this project is that relationships between characters (like family ties, work connections, or investigations) are not stored as direct edges between `:Character` nodes. Instead, every factual statement is stored as its own `:Claim` node.

A `:Claim` node holds `subject_id`, `predicate`, `object_id`, `claim_type`, `status`, `confidence_level`, `visible_from_order`, `valid_from_order`, and `valid_until_order`. This design solves three problems:
1. Independent visibility: A character might appear in episode 1, but their relationship with another character might only be revealed in episode 3. Making the relationship a `:Claim` node gives it its own `visible_from_order` value.
2. Evidence links: Because the claim is a node, it connects directly to evidence fragments with `-[:SUPPORTED_BY]->`, so every relationship points back to its source text.
3. Graph projection: The backend queries visible `:Claim` nodes and turns them into graph edges for the frontend based on the user watch progress.

Every story node and claim has a `visible_from_order` integer. When querying the database, the backend passes the user watch boundary as `$visible_until_order`. A shortened version of the main query in `spoilerless/app/spoiler/filter.py` is shown below:

```cypher
MATCH (claim:Claim {series_id: $series_id})
MATCH (subject {id: claim.subject_id})
MATCH (object {id: claim.object_id})
MATCH (claim)-[supported:SUPPORTED_BY]->(evidence:EvidenceFragment)
MATCH (claim)-[ref:REFERS_TO]->(source:Source {id: evidence.source_id})
WHERE claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND (claim.valid_from_order IS NULL OR claim.valid_from_order <= $visible_until_order)
  AND (claim.valid_until_order IS NULL OR claim.valid_until_order >= $visible_until_order)
  AND subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
  AND object.visible_from_order <= $visible_until_order
RETURN claim.id AS id,
       claim.subject_id AS subject_id,
       claim.predicate AS predicate,
       claim.object_id AS object_id,
       claim.claim_type AS claim_type,
       claim.status AS status,
       claim.confidence_level AS confidence_level,
       claim.visible_from_order AS visible_from_order,
       source.id AS source_id,
       collect(DISTINCT evidence.id) AS evidence_ids
ORDER BY claim.visible_from_order, id
```

This query checks that the claim itself is visible at or before `$visible_until_order`, and also checks that both the `subject` and `object` entities are visible. If a claim connects a known character to a character who has not appeared yet, the query ignores that claim. This prevents future character names from leaking out early.

For multi-hop graph search and pathfinding, the retrieval code expands outward from starting nodes using `CLAIMS_FOR_FRONTIER_QUERY` in `spoilerless/app/retrieval/tools.py`. A shortened version of the query is shown below:

```cypher
MATCH (claim:Claim {series_id: $series_id})
WHERE claim.visible_from_order IS NOT NULL
  AND claim.visible_from_order <= $visible_until_order
  AND claim.origin IN ['canonical', 'candidate']
  AND (claim.subject_id IN $frontier OR claim.object_id IN $frontier)
MATCH (subject {id: claim.subject_id, series_id: $series_id})
MATCH (object {id: claim.object_id, series_id: $series_id})
WHERE subject.visible_from_order IS NOT NULL
  AND subject.visible_from_order <= $visible_until_order
  AND object.visible_from_order IS NOT NULL
  AND object.visible_from_order <= $visible_until_order
RETURN claim.id AS id,
       claim.subject_id AS subject_id,
       claim.object_id AS object_id,
       claim.predicate AS predicate,
       claim.visible_from_order AS visible_from_order
ORDER BY claim.visible_from_order, claim.id
```

The algorithm takes a list of node IDs in `$frontier`. It finds visible claims connected to those nodes and checks that both endpoints are within `$visible_until_order`. The newly discovered node IDs become the next frontier. Because both endpoints are checked at each step, the search cannot traverse through hidden intermediate characters.

When candidate extraction scripts add new claims, `spoilerless/app/graph/candidates.py` verifies the entities in a single query:

```cypher
MATCH (ep:Episode {series_id: $series_id, episode_order: $episode_order})
OPTIONAL MATCH (subj {id: $subject_id, series_id: $series_id})
  WHERE (subj:Character OR subj:Event OR subj:Location OR subj:Organization OR subj:Object)
OPTIONAL MATCH (obj {id: $object_id, series_id: $series_id})
  WHERE (obj:Character OR obj:Event OR obj:Location OR obj:Organization OR obj:Object)
RETURN ep IS NOT NULL AS episode_valid,
       subj IS NOT NULL AS subject_valid,
       subj.visible_from_order AS subject_order,
       obj IS NOT NULL AS object_valid,
       obj.visible_from_order AS object_order
```

This query checks that the episode exists and that both subject and object exist in the database. The backend uses the returned visibility numbers to set the new candidate claim visibility to `max(episode_order, subject_order, object_order)`.

I wrote the database setup code in `spoilerless/app/graph/seed.py` and `setup.py`. It creates uniqueness constraints on all entity IDs before loading seed JSON data using parameterized `MERGE` queries. This makes the setup script safe to run multiple times without creating duplicate records. After seeding, `audit_visibility_integrity()` checks that every story node and claim has a valid `visible_from_order`.

When an authenticated user writes a private note on a character or event, `spoilerless/app/repository/user_content.py` creates a `:UserNote` node and connects it with `(:UserNote)-[:REFERS_TO]->(target)`. When users edit graph data or accept assistant changes through `ChangeSetService`, the backend saves the change in `spoilerless/app/revisions/repository.py` by creating a `:Revision` node with JSON snapshots of the before and after states. The revision log is append-only. When a user reverts an edit, the backend does not delete old revision records: it applies the reverse change to the graph and adds a new `:Revision` node with `action: 'reverted'`, keeping the complete change history intact.
