# Pitfalls Research

**Domain:** Spoiler-safe narrative knowledge graph (Neo4j + FastAPI + React/Cytoscape.js)
**Researched:** 2026-07-28
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Spoiler Leak via Relationship Traversal

**What goes wrong:**
A user with progress `visible_until_order=1` sees a node visible at order 1, but its connected relationship reveals a character who shouldn't be known yet (e.g., a killer reveal from episode 4 appears because the node is connected via a KNOWS edge). Worse: the backend returns a relationship object whose `target_id` references a hidden node, and the frontend renders its label from the relationship payload.

**Why it happens:**
Filters focus on individual nodes and edges without checking whether the relationship itself crosses the spoiler boundary. A relationship may be valid (visible_from_order ≤ user progress) but its target node may not be. The frontend then renders a hidden node's name via the relationship's serialized data.

**How to avoid:**
- Graph endpoint must apply a **three-way filter**: source node visible, relationship visible, target node visible.
- Relationship models should never carry denormalized node data (e.g., `target_name`, `target_label`) that could leak info.
- Add an integration test: set progress to Episode 1, request graph, assert no returned object contains references to Episode 2+ content by name or ID.

**Warning signs:**
- Graph response includes relationship objects with `source`/`target` string IDs that don't appear in the nodes array.
- A Cypher `MATCH (a)-[r]-(b) WHERE a.visible_from_order <= $progress AND r.visible_from_order <= $progress` that forgets to check `b.visible_from_order`.
- Frontend toast/panel showing "Connected to [Hidden Character Name]" before user has unlocked that episode.

**Phase to address:**
Milestone 3 (Spoiler-aware graph endpoint) — the three-way filter must be part of the core graph query. Milestone 5 (Frontend Graph UI) must defensively never render data about non-included nodes.

---

### Pitfall 2: `visible_from_order` Drift — Inconsistent Field Population

**What goes wrong:**
Some nodes, relationships, or claims are seeded without a `visible_from_order` property. A Cypher query that filters by `n.visible_from_order <= $progress` silently drops these nodes (NULL comparison in Cypher yields false), making them vanish from the graph. Or worse, a query that doesn't filter on `visible_from_order` exposes them to all users.

**Why it happens:**
The project requires `visible_from_order` on every graph element, but there's no database-level enforcement. Neo4j doesn't support `NOT NULL` constraints on properties — only existence constraints on property *existence*. A MERGE can create a node missing the property, and it won't fail any constraint.

**How to avoid:**
- Create a Neo4j existence constraint: `CREATE CONSTRAINT FOR (c:Claim) REQUIRE c.visible_from_order IS NOT NULL` for every node label.
- In seed scripts, always include `visible_from_order` explicitly — never rely on defaults.
- Add a CI check that queries `MATCH (n) WHERE n.visible_from_order IS NULL RETURN count(n)` and asserts zero.
- Add a Pydantic validator on graph response models that rejects nodes without the field.

**Warning signs:**
- A character node disappears from the graph even though the user has progressed past that episode.
- Cypher queries inconsistently use `optionalMatch` vs `Match` for visibility — some paths leak through unfiltered branches.
- Seed JSON files for characters/claims missing the `visible_from_order` field.

**Phase to address:**
Milestone 2 (Metadata graph) — add existence constraints when creating the constraint set. Milestone 4 (Manual seed graph) — validate every seed file has the field.

---

### Pitfall 3: Over-Engineering the Ontology Before Understanding the Data

**What goes wrong:**
The ontology defines 20+ node types, 30+ relationship types, 5 claim statuses, and 4 confidence levels before any real data exists. When seed data is finally written, most relationship types go unused, the confidence taxonomy is too fine-grained for the available evidence, and the team spends time maintaining complex validation logic for edge cases that never occur.

**Why it happens:**
It's tempting to design the "perfect" ontology upfront because the domain (TV narratives) feels well-understood. But the practical needs of spoiler gating and evidence linking often reshape the model once real data is written.

**How to avoid:**
- Start with a minimal ontology: Character, Claim, Episode, Source, EvidenceFragment. Add Organization, Object, Location, Event only when seed data proves they're needed.
- Implement the full ontology structure in the YAML files (they're documentation) but only build Cypher queries and Pydantic models for labels actively used by seed data.
- Use a single `RELATES_TO` relationship type instead of 10+ character-specific types (KNOWS, FAMILY_OF, TRUSTS, etc.) until the data proves finer granularity matters for filtering or querying.

**Warning signs:**
- Repository has 1000+ lines of ontology/domain code but only 50 lines of actual seed data.
- Pydantic models for node types that have zero instances in the database.
- Cypher queries that try to MATCH on relationship types that don't exist in the data.

**Phase to address:**
Milestone 4 (Manual seed graph) — write seed data first, then trim the ontology to match reality. The ontology YAML can stay expansive (it's a reference), but backend code must only implement what's used.

---

### Pitfall 4: Cypher Spoiler Query Leaks via `OPTIONAL MATCH`

**What goes wrong:**
A developer writes a well-intentioned graph query:

```cypher
MATCH (c:Character) WHERE c.visible_from_order <= $progress
OPTIONAL MATCH (c)-[r:KNOWS]-(other:Character)
WHERE r.visible_from_order <= $progress
RETURN c, collect({relationship: r, target: other}) AS connections
```

The `OPTIONAL MATCH` returns `other` as NULL when the relationship is hidden — good. But the relationship `r` itself is returned as a node object (Neo4j native) containing `startNode(r)` and `endNode(r)` metadata, which the driver serializes and the backend Pydantic model may accidentally include. If the backend serializes the relationship's start/end node IDs, the frontend learns the hidden character's database ID exists, which is a spoiler indicator.

**Why it happens:**
Cypher `OPTIONAL MATCH` semantics are confusing — it returns NULL for non-matching *patterns*, but individual properties from a matched relationship may still be non-null. The developer assumes NULL means "completely absent" but the driver may still return partial data.

**How to avoid:**
- Never use `OPTIONAL MATCH` for spoiler-boundary filtering. Use explicit `WHERE` clauses on all elements, and explicitly check each element's `visible_from_order`.
- In the RETURN clause, explicitly project only the allowed fields: `RETURN c.id, c.name, c.label` rather than returning entire nodes.
- Add a middleware that strips any relationship endpoint/start/end metadata before serialization.
- Write unit tests that assert the graph response for progress=N contains exactly N known node IDs and no more.

**Warning signs:**
- A user at Episode 1 sees "character_unknown_01" appear in any serialized response (even as a null or empty object).
- Relationship models in Pydantic include optional `start_node_id` or `end_node_id` fields that aren't being filtered server-side.

**Phase to address:**
Milestone 3 (Spoiler-aware graph endpoint) — the Cypher query and response model must be designed together as a leak-proof contract.

---

### Pitfall 5: Frontend Caches Spoiled Data After Progress Change

**What goes wrong:**
The user sets progress to Episode 3 and explores the graph. The frontend caches the response in React state or a local store. The user then resets progress to Episode 1 to re-explore. The frontend serves the cached Episode 3 graph data because the endpoint URL hasn't changed (or the cache key doesn't include `visible_until_order`).

**Why it happens:**
Developers assume progress only increases, so caching forward is safe. But users may reset progress (starting a rewatch, sharing a device). React state, React Query cache keys, or in-memory Cytoscape.js element arrays don't automatically invalidate on param change.

**How to avoid:**
- Include `visible_until_order` in the `GET /api/graph` cache key (React Query: `queryKey: ['graph', seriesId, visibleUntilOrder]`).
- Never store graph elements in global state that survives param changes — derive from the current visibleUntilOrder.
- Before rendering Cytoscape elements, clear the cy instance completely (`cy.elements().remove()`) and re-add from fresh API data.
- Add a spoiler confirmation modal that explicitly clears the graph view before revealing new data (already planned — enforce it).

**Warning signs:**
- Cytoscape.js layout preserves node positions from a higher-episode exploration after the user goes back to Episode 1.
- A node detail panel shows claim data that wasn't returned by the current API call.
- Frontend uses `useState` for graph data instead of RQ/RTK with keyed cache.

**Phase to address:**
Milestone 5 (Frontend graph UI) — cache keys and state management strategy must be established before Cytoscape integration. Milestone 6 (User notes) is particularly risky because user-created content may cache differently.

---

### Pitfall 6: Cytoscape.js Performance Cliff with 200+ Nodes

**What goes wrong:**
The prototype works beautifully with 15 nodes and 30 edges. When the seed grows to 200+ nodes (characters, claims, episodes, sources across a full season), Cytoscape.js with default layout (`cose`) takes 10+ seconds to settle, and interaction becomes sluggish. The frontend feels broken even though nothing is wrong architecturally.

**Why it happens:**
Cytoscape.js `cose` and `cose-bilkent` layouts run force-directed physics on the entire graph synchronously in the browser thread. Layout computation grows O(n²·log n) or worse. Browsers start dropping frames at ~100 elements with animate:true.

**How to avoid:**
- Always call `cy.elements().remove()` before loading new data (prevent element accumulation across renders).
- Start with `animate: false` on layout runs and consider `cola` or `fcose` (faster convergence) instead of `cose-bilkent`.
- Layer big graphs: default view shows only `Character` and `Episode` nodes (50–100 nodes); users expand claims/evidence on click.
- Set `maxZoom` to prevent the user from zooming out to see the entire 200-node graph at once (which triggers full render).
- If performance becomes a bottleneck early, consider `cytoscape-dagre` for structured layout or `cytoscape-spread` for initial positioning.

**Warning signs:**
- Layout animation visibly stutters or takes >3 seconds on the demo data.
- `cy.fit()` or `cy.center()` hangs when called after layout.
- Frontend bundle size grows because of unused Cytoscape extensions being imported.

**Phase to address:**
Milestone 5 (Frontend graph UI) — test layout with the expected seed data size before polishing. Milestone 4 must define the expected node count.

---

### Pitfall 7: Import-Time Neo4j Driver Initialization Breaking Tests

**What goes wrong:**
A developer runs `pytest` to add a spoiler-boundary test. The test imports `app.graph.database`, which executes `neo4j_db = Neo4jDatabase()` at module level. This tries to connect to a Neo4j instance which isn't running in the CI environment. The entire test suite fails before any test runs — not with a helpful "Neo4j not available" message, but with a cryptic connection error traceback.

**Why it happens:**
`backend/app/graph/database.py` creates the singleton at module import time (`neo4j_db = Neo4jDatabase()`). Python's import system executes this eagerly on first import. There's no lazy initialization or environment-aware fallback.

**How to avoid:**
- Use lazy initialization: create the driver on first access (property or factory function) rather than at import time.
- Or move the singleton creation to FastAPI lifespan so it only runs during app startup, not on import.
- Add a `TESTING` flag that skips driver creation and uses a mock or in-memory substitute.
- For the current codebase, this is already flagged in CONCERNS.md — prioritize fixing before Milestone 3.

**Warning signs:**
- `pytest` crashes on `from app.graph.database import neo4j_db` without even reaching a test function.
- Module-level side effects in database.py — any `print()`, connection attempt, or file read at import time.
- CI pipeline fails on first import before any test logic runs.

**Phase to address:**
Milestone 1 (Local infrastructure) — fix startup fragility before writing any new tests. The import-time driver is a landmine that blocks all future test development.

---

### Pitfall 8: Claim Model Design — Collapsing Narrative Fact vs System Certainty

**What goes wrong:**
The `Claim` node stores a single `confidence_level` and a single `status`, implying there's one "truth" about a claim. But narrative facts are inherently multi-perspective: a rumor seen in Episode 1 might be corroborated in Episode 5 and refuted in Episode 10. The model has no way to express this evolution without duplicating Claim nodes for each version or updating the single node in place (losing history).

**Why it happens:**
The ontology defines claim as an atomic fact with a status and confidence. This works for static knowledge bases but breaks for narratives where the *same fact* evolves over the storyline. The pitfall is treating a narrative knowledge graph like a traditional fact database.

**How to avoid:**
- Separate **what is claimed** (the triples) from **when it is true** (valid_from_order/valid_until_order). A single claim statement can have validity windows that shift.
- Store confidence at the EvidenceFragment level, not the Claim level — let the evidence tell you how sure the system is, not the claim.
- Use the revision history to track claim status changes over time; don't mutate the claim's status in place without creating a revision.
- The existing model already has `valid_from_order` and `valid_until_order` — enforce that queries filter on these as well as `visible_from_order`.

**Warning signs:**
- A claim about a character's motivation appears with `status: canonical` even though later episodes contradict it.
- The only way to change a claim's status is to mutate the existing node.
- No evidence of multi-episode validity logic in Cypher queries (all queries filter only on `visible_from_order`, ignoring `valid_from_order`/`valid_until_order`).

**Phase to address:**
Milestone 4 (Manual seed graph) — ensure seed data includes at least one claim with a non-null `valid_until_order` to validate windowed validity. Milestone 7 (Revision history) must handle status transitions.

---

### Pitfall 9: Underspecifying the Graph API Response Model

**What goes wrong:**
The `GET /api/graph` endpoint returns a flat JSON list of nodes and edges. The frontend Cytoscape component maps edges by source/target ID. But some edges reference node IDs that aren't in the nodes array (because the target node is hidden). Cytoscape.js silently skips these edges, breaking the graph layout. Or worse, it renders a partial edge pointing to (undefined), creating a visual artifact.

**Why it happens:**
The backend and frontend don't have a shared contract about graph completeness. The backend assumes "return what matches," the frontend assumes "every edge's source and target is in the nodes array." Neither validates the assumption.

**How to avoid:**
- The graph response model must guarantee: every edge's `source` and `target` ID appears in the `nodes` array. This is the **graph closure invariant**.
- Add a Pydantic validator on the graph response that rejects invalid payloads before they reach the frontend.
- In the frontend, wrap `cy.add()` in a try-catch and log malformed elements with context.
- Write a test: for every `visible_until_order=N`, assert that the set of source/target IDs in returned edges is a subset of returned node IDs.

**Warning signs:**
- Browser console shows Cytoscape.js warnings: "Cannot add edge: source/target not found."
- The graph renders with floating edges that don't connect to any node.
- The node count seems lower than expected, but edges reference missing IDs.

**Phase to address:**
Milestone 3 (Spoiler-aware graph endpoint) — the graph closure invariant must be designed into the response model, not bolted on later. Milestone 5 should defensively handle missing targets.

---

### Pitfall 10: Duplicate FastAPI App Construction

**What goes wrong:**
`backend/app/main.py` calls `FastAPI(...)` twice with the same arguments, then attaches routes/middleware to the second instance. This is confusing and fragile — any code that imports `app` from this module might get the first instance (if imported before line 23) or the second. It's a latent bug in a critical module.

**Why it happens:**
Already present in the codebase (documented in CONCERNS.md). Likely a copy-paste or refactoring artifact. Harmless now but a maintenance trap.

**How to avoid:**
- Remove the first `app = FastAPI(...)` assignment entirely.
- Run a linter that flags duplicate variable assignments to the same name in a module.
- Add a comment explaining why only one instance exists.

**Warning signs:**
- Two `FastAPI` calls in the same file.
- Any other file does `from app.main import app` and gets the wrong instance.

**Phase to address:**
Milestone 1 (Local infrastructure) — trivial one-line fix, but it's a code hygiene prerequisite for all subsequent milestones.

---

### Pitfall 11: Revision Model That Can't Represent Partial Edits

**What goes wrong:**
The Revision model logs full snapshots of claims when they change. A user edits a claim's `confidence_level` from "low" to "high". The system records the entire claim as a revision. Later, when displaying history, the UI shows two identical claim bodies with only one field changed — the user can't tell what actually changed without diffing the raw JSON.

**Why it happens:**
It's simpler to snapshot the whole object than to compute and store a delta. But for narrative knowledge graphs, users need to see *what changed* at a glance — "confidence upgraded from low to high" is meaningful narrative context, while "claim snapshot from 2026-07-28" is noise.

**How to avoid:**
- Store both `before` and `after` snapshots in each Revision, plus a `changed_fields` array listing which properties were modified.
- Or store structured diffs rather than full snapshots for property-level edits (keep full snapshots for structural changes).
- The frontend revision panel must render diffs, not raw JSON — use a side-by-side or highlighted view.
- For user corrections specifically (user_vs_canonical), log the user's proposed value separately from the canonical value.

**Warning signs:**
- Revision history panel shows identical-looking claim cards with different timestamps.
- The only way to inspect what changed is to open the browser's network tab and compare raw responses.
- Revision model stores a single `snapshot` JSON field instead of `before`/`after` or diff representation.

**Phase to address:**
Milestone 7 (Revision history) — design the revision model with diff visibility in mind from day one.

---

### Pitfall 12: No Evidence of Seed Data Completeness

**What goes wrong:**
The seed script runs without errors. The graph endpoint returns data. But when the frontend renders the graph, it shows 3 characters, 2 claims, and 0 evidence fragments — a sparse, unconvincing demo. The seed data is technically correct but doesn't demonstrate the product's value because it lacks:
- enough nodes to make the graph visually interesting,
- claims with evidence links (the core provenance feature),
- multi-episode visibility to demonstrate spoiler-gating.

**Why it happens:**
Data modeling is treated as a checkbox task ("create seed files") rather than a demo-design task ("create a compelling demo experience"). The seed data meets the schema requirements but doesn't meet the user experience requirements.

**How to avoid:**
- Design the seed data to demonstrate the Demo Story (from ROADMAP.md §8) before writing a single JSON file.
- Minimum viable seed per episode: 5+ character nodes, 3+ claims with evidence links, 1+ cross-episode relationship.
- Include at least one claim that spans multiple episodes (valid_from_order=1, valid_until_order=3) to test windowed validity.
- One claim that appears in Episode 3 (visible_from_order=3) to test spoiler-gating.
- Before calling seed data "done", render it in the frontend and verify the demo flow works end-to-end.

**Warning signs:**
- Seed files contain only IDs and names but no meaningful relationships or evidence.
- The demo graph looks sparse after seeding (fewer than 10 nodes).
- No seed file creates a node with `visible_from_order > 1`, so spoiler-gating can't be verified visually.
- EvidenceFragment nodes exist but no SUPPORTED_BY relationships connect them to claims.

**Phase to address:**
Milestone 4 (Manual seed graph) — write seed data as a demo script, not just a data load. Milestone 5 must wire it into a working frontend before calling either milestone complete.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Import-time Neo4j driver singleton | Simple, always available | Breaks tests, brittle startup | Never — use lazy init or lifespan |
| `visible_from_order` as integer only | Simple filtering | Can't express sub-episode, conditional, or "revealed after" logic | Prototype v0 only; document as technical debt |
| Direct Neo4j session in route handlers | Fast to write | No transaction management, hard to mock/test, error handling duplicated per-route | Milestones 1–4; refactor to repository layer before Milestone 6 |
| Single `RELATES_TO` for all character relationships | Minimal ontology | Fine-grained queries (find enemies, find family) require filtering on claim subject/predicate, not relationship type | Acceptable if the ontology YAML documents the intended types even if backend uses a generic type |
| Snapshot-only revision model | Simple implementation | Users can't see what changed without manual diffing | Milestone 7 only; must be replaced with delta model before production |
| JSON seed files | Easy to write/edit | No type validation, no cross-file referential integrity, no auto-generation | Prototype only; add validation script before Milestone 4 |
| Cytoscape `preset` layout (hardcoded positions) | Fast render, predictable layout | Doesn't scale, can't handle dynamic data, positions must be maintained by hand | Only for demo mockups; use `cola` or `fcose` for real data |
| Hardcoded health endpoint "connected" | Quick setup | Hides database connectivity issues | Never — already tracked as INFRA-01, fix immediately |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Neo4j Docker Compose | Using `latest` tag instead of `2026-community` | Pin to `neo4j:2026-community` (already done) |
| Neo4j driver | Creating driver per-request instead of singleton | One driver instance per app lifetime (already done, but import timing is wrong) |
| Cypher via FastAPI | Formatting Cypher queries with f-strings (SQL injection equivalent) | Always use parameterized queries with `$param` syntax (already done correctly) |
| React Query + Cytoscape | Updating Cytoscape elements by mutating existing `cy` instance state | Always clear and rebuild: `cy.elements().remove()` → `cy.add(data)` → `cy.layout(...).run()` |
| Vite proxy for API | No proxy config, relying on CORS | Use `vite.config.ts` proxy for development; CORS middleware for production |
| Pydantic + Neo4j | Returning `record.data()` directly without validating against response model | Always project to Pydantic models — strip extra neo4j metadata (start/end node ids, internal element ids) |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Return full graph for every request | Latency spikes as seed data grows; frontend re-renders entire Cytoscape graph | Paginate graph responses; use "expand on click" for claims/evidence | ~500 total nodes/edges |
| `cose-bilkent` layout with animate:true | UI freezes for 5–15 seconds on each layout run | Use `animate: false`; add a loading spinner; use `fcose` or `cola` layout alternatives | ~100 nodes |
| No index on `visible_from_order` | Full label scans on every graph query — `MATCH (n:Claim)` without index forces scan | `CREATE INDEX claim_visible_idx FOR (n:Claim) ON (n.visible_from_order)` | ~10k+ Claim nodes |
| Serializing entire Neo4j node objects to JSON | Response payload includes internal `elementId`, `labels`, unused properties | Explicitly project in RETURN clause; validate with Pydantic | Any scale — unnecessary bytes on every request |
| Frontend `useEffect` calling `cy.layout()` on every render | Layout re-runs regardless of data changes | Only call layout when data actually changes (stable reference or deep comparison) | Moderate React re-renders |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Sending ALL graph data to frontend and filtering client-side | A user can inspect network responses or modify JS to see every hidden node/claim | **Never send hidden data to the client** — backend MUST filter before responding. This is the cardinal rule. |
| Exposing Neo4j Browser port (7474) in production | Anyone with network access can query the database directly | Block 7474 in production Docker config; use only the Bolt port (7687) for app connections |
| No read-only API key for graph endpoint | Unauthenticated users can probe the system at any scale | Add a simple API key header check (out of scope for v0, but document as risk) |
| Revision log accumulates PII (user notes, corrections) | User-authored notes may contain personal information that can't be easily purged | Add a `user_id` field (even for single-user prototype) so future deletion is possible |
| LLM endpoint (future) with unfiltered context | LLM receives ALL graph data regardless of user progress, then is prompted "don't spoil" — trivial to jailbreak | LLM retrieval must use the same progress-filtered graph endpoint, never raw database access |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No progress-change confirmation | User accidentally swipes to Episode 10 and spoils a major plot point | Spoiler confirmation modal (already planned) — must show episode title + warning, not just generic "Are you sure?" |
| Graph auto-centers on progress change without preserving context | User was examining a character node in Episode 1, updates to Episode 2, graph re-layouts and they lose their place | After progress change, try to preserve viewport center or highlight newly visible elements |
| No visual distinction between visible and "locked" elements | User doesn't understand why some areas of the graph are empty | Show a visual indicator (gray overlay, lock icon, fog effect) on regions that will become visible at higher progress |
| Evidence links shown as abstract nodes | User doesn't understand what "evidence" means — it's just another node in the graph | Render evidence as compact citation-style links in the node detail panel, not as separate graph nodes |
| User notes mixed with canonical data | User can't tell which content they authored vs what was seeded | Distinct styling: user nodes get a dashed border, user notes get a colored background with an "edited" badge |
| Cytoscape node labels clipped or overlapping | User can't read character names because the layout is too dense for the viewport | Set explicit label width/ellipsis; enable node hover to show full name; use `nodeDimensionsLabel` extension |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Spoiler graph endpoint:** The query returns nodes filtered by `visible_from_order`, but relationships don't enforce that BOTH source and target nodes are visible. Without this, a hidden character's existence can be inferred.
- [ ] **Seed script:** Runs and prints "tamamlandı", but doesn't verify post-seed state — no `MATCH (n) RETURN count(n)` assertion, no constraint validation, no rollback on partial failure.
- [ ] **Frontend graph UI:** Cytoscape.js renders nodes and edges, but the layout uses `preset` positions from a hardcoded JSON file. Adding one new node requires manually computing its x/y position.
- [ ] **Health endpoint:** Returns `{"status": "ok", "database": "connected"}` but never actually checks the database connection (hardcoded). Marked as INFRA-01 in the roadmap.
- [ ] **Docker Compose:** Starts Neo4j, but there's no `depends_on` or wait-for-it script for the backend — if the backend starts before Neo4j is ready, it crashes immediately.
- [ ] **Revision model:** Creates Revision nodes for claim changes, but there's no revert logic — the Revision nodes exist as history without a way to restore a previous state.
- [ ] **User note CRUD:** Creates, reads, updates, and deletes notes, but user-created notes and canonical data are stored in the same query path without isolation — a malformed user query could accidentally modify canonical data.
- [ ] **Cypher constraints:** `CREATE CONSTRAINT ... IF NOT EXISTS` runs at seed time but is never verified before queries — if constraints somehow didn't get created, duplicate nodes silently corrupt the graph.
- [ ] **Frontend error handling:** API calls use `.catch()` but errors display as an ugly browser console message or JSON blob — no user-facing error toast, no retry, no graceful degradation.

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Spoiler data leaked via response | HIGH — trust is broken | 1. Identify the leak via query audit. 2. Fix the query/response model. 3. Add a regression test that explicitly checks for the leaked field. 4. Document the incident. |
| Missing `visible_from_order` on nodes | MEDIUM | 1. `MATCH (n) WHERE n.visible_from_order IS NULL SET n.visible_from_order = 999999` (hide from everyone). 2. Add existence constraint. 3. Fix seed data. |
| Cytoscape performance issues with large layout | MEDIUM | 1. Switch to `fcose` layout. 2. Add layer-based expansion (default: only characters + episodes). 3. Add pagination. |
| Revision with full snapshot only (no diff) | LOW (if revisions exist) / HIGH (if not yet) | If revisions exist: add a migration that computes diffs and stores them. If not yet: update the model before any real data creation. |
| Neo4j driver singleton blocks tests | LOW | 1. Refactor to lazy initialization. 2. Add `TESTING` env var to use mock driver. 3. Update CI to start Neo4j service. |
| Duplicate FastAPI app construction (current codebase) | VERY LOW | Remove the first `app = FastAPI(...)` assignment. Run tests to confirm nothing breaks. |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| P1: Spoiler leak via relationship traversal | Milestone 3 | Integration test: graph response is closed under target/source for given progress |
| P2: `visible_from_order` drift | Milestone 2 (constraints) + Milestone 4 (seed validation) | CI check: `MATCH (n) WHERE n.visible_from_order IS NULL RETURN count(n)` = 0 |
| P3: Over-engineered ontology | Milestone 4 | Backend only implements node/types actively in seed data |
| P4: OPTIONAL MATCH spoiler leak | Milestone 3 | Unit test: none of the allowed progress values return hidden node IDs |
| P5: Frontend caching spoiled data | Milestone 5 | Test: set progress high, explore, set progress low, assert no hidden data in DOM |
| P6: Cytoscape performance cliff | Milestone 5 | Load test with projected seed data size; layout must settle <2s |
| P7: Import-time driver breaks tests | Milestone 1 | `pytest` passes without a running Neo4j instance |
| P8: Claim model collapses narrative fact with certainty | Milestone 4 + Milestone 7 | Seed data includes a claim with `valid_until_order`; revision history captures status transitions |
| P9: Underspecified graph API response | Milestone 3 | Pydantic validator enforces graph closure invariant |
| P10: Duplicate FastAPI app construction | Milestone 1 | Linter or code review catches duplicate `FastAPI()` call |
| P11: Revision model can't represent partial edits | Milestone 7 | Revision history panel displays readable diffs per property, not raw JSON |
| P12: Insufficient seed data for compelling demo | Milestone 4 | Manual walkthrough of Demo Story (ROADMAP §8) reveals no gaps |

---

## Sources

- Neo4j Cypher documentation on OPTIONAL MATCH semantics and NULL handling
- Cytoscape.js performance guidelines (github.com/cytoscape/cytoscape.js/wiki/Performance)
- Known issues from similar spoiler-safe graph projects (TV knowledge graphs)
- CONCERNS.md — codebase audit findings from `.planning/codebase/CONCERNS.md`
- ROADMAP.md — milestone definitions from `ROADMAP.md`
- Personal experience: narrative knowledge graph projects where the "perfect ontology" trap delayed working prototypes by weeks
- Neo4j existence constraint documentation (`CREATE CONSTRAINT ... REQUIRE prop IS NOT NULL`)

---
*Pitfalls research for: HD Graf Cehennemi — spoiler-safe narrative knowledge graph*
*Researched: 2026-07-28*
