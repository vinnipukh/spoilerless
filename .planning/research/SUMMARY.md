# Project Research Summary

**Project:** HD Graf Cehennemi — Spoiler-Safe Narrative Knowledge Graph
**Domain:** TV series narrative knowledge graph with spoiler gating
**Researched:** 2026-07-28
**Confidence:** HIGH

## Executive Summary

HD Graf Cehennemi is a spoiler-safe narrative knowledge graph for TV series — a local-first web application that lets users explore character relationships, claims, and evidence for a show (starting with Dexter S01E01-03) while a spoiler boundary at the data-access layer guarantees they never see content beyond their watch progress. Research was conducted across four areas: technology stack, feature landscape, system architecture, and common pitfalls.

**The recommended approach** is a proven three-tier architecture: Neo4j (graph database, already running in Docker Compose) → FastAPI (REST API with Pydantic validation, already scaffolded) → React + Cytoscape.js (interactive graph visualization, already scaffolded). The central architectural invariant — `visible_from_order` on every graph element, enforced in Cypher queries before data ever leaves the server — is what makes this product unique. No existing TV companion (Trakt, Serializd, TV Time, The StoryGraph) applies spoiler gating at the data layer; they rely on community-managed tags or simple UI toggles that can be bypassed.

**The single greatest risk** is spoiler leakage through incomplete filtering — particularly via relationship traversal (returning a relationship whose target node is hidden) or `OPTIONAL MATCH` semantics that leak hidden node IDs through serialized metadata. Every query and response model must be designed as a leak-proof contract from day one. A secondary risk is over-engineering the ontology before real data exists; the research strongly recommends starting with a minimal set of node types (Character, Claim, Episode, Source, EvidenceFragment) and expanding only when seed data proves a type is needed.

## Key Findings

### Recommended Stack

The technology choices are already validated by the existing scaffold — every core dependency is installed and verified compatible. The stack is industry-standard for graph-backed web applications and requires no risky or experimental technologies.

**Core technologies:**
- **Neo4j 2026-community** (Docker Compose) — graph database as single source of truth. The `visible_from_order` spoiler filtering is expressed natively in Cypher `WHERE` clauses rather than post-processed in Python, making it performant and auditable.
- **FastAPI 0.140.7** — Async-first REST framework with Pydantic v2 validation, auto-generated OpenAPI docs. Already configured with CORS, lifespan, and health endpoint (though the health check is currently hardcoded).
- **Neo4j Python Driver 6.2.0+** — Official driver with `execute_query` API and managed transaction lifecycle. Must use lazy initialization (not module-level singleton) to avoid breaking tests.
- **React 19 + TypeScript 6.x + Vite 8.x** — Frontend scaffold in place. TypeScript strict mode catches Cytoscape.js integration bugs at compile time.
- **Cytoscape.js 3.34.0** — Mature graph visualization library with force-directed layouts, compound nodes, edge bundling, and event handling. More suitable than D3.js (which would require building graph interaction primitives from scratch).
- **@tanstack/react-query** (to install) — Recommended server-state management. Eliminates manual fetch/useEffect boilerplate, provides cache keying by `(seriesId, visibleUntilOrder)` so progress-change invalidates stale graph data.
- **react-router-dom** (to install) — Client-side routing for graph view, notes view, revisions, and settings.

**Supporting libraries:** Pydantic (validation), pytest + httpx + pytest-asyncio (backend testing), Vitest + Testing Library (frontend testing), PyYAML (ontology file loading).

**What NOT to use:** Redux (overkill — React Query + useContext for spoiler boundary suffices), SQLAlchemy (Neo4j is not SQL), GraphQL (overengineering for 6–8 endpoints), cron-based polling (graph data is event-driven, not time-driven), f-string Cypher queries (injection risk + breaks query plan caching).

See [STACK.md](./STACK.md) for full rationale, version compatibility matrix, and alternative comparison.

### Expected Features

The feature landscape reveals a clear competitive niche: **no existing product combines spoiler-gated graph exploration with a character/claim knowledge graph for TV.**

**Must have (table stakes):**
- Series/Episode browser — already scaffolded (`GET /api/series`, `GET /api/series/{id}/episodes`)
- Episode progress selector with spoiler confirmation modal — the core UX flow
- Character nodes with metadata (name, description, aliases)
- Relationship types between characters (KNOWS, FAMILY_OF, KILLS, etc.)
- Interactive force-directed graph visualization (Cytoscape.js)
- Node detail panel (character info, claims, evidence)
- Edge/relationship detail panel (type, strength, evidence)
- Source/evidence display for claims — every auto-claim is evidence-backed

**Should have (competitive advantages):**
- **Spoiler-gated graph at the data-access layer** — backend guarantees the frontend never receives data beyond the user's watch progress. This is THE core differentiator. No existing product does this architecturally.
- **Progressive graph disclosure** — as the user advances, new connections and claims unlock like a map revealing itself
- **Atomic claim model with temporal validity** — `valid_from_order` / `valid_until_order` handles reveals and rewrites cleanly
- **Two-dimensional knowledge model** — `relationship_effect × confidence_level` separates narrative strength from system certainty
- **User vs canonical content separation** — user notes and custom nodes visually distinct from curated data
- **Source-backed evidence chain** — every claim traces back to specific evidence (source type, locator, episode, timestamp)
- **Candidate claim workflow** — future LLM extractions produce "candidate" claims needing review before becoming canonical

**Defer (v2+):**
- Multi-user accounts & auth — single-user prototype only
- Real-time collaborative editing — revision history + export/import suffices
- Live LLM chat over the full graph — requires spoiler-guarded retrieval tools; Milestone 9
- Full automated scraping pipeline — high maintenance burden; manual seed for prototype
- Mobile app — responsive web is sufficient for local exploration
- Automatic graph layout — ship with Cose layout; add alternatives as power-user option

**MVP definition (v1):** The prototype launch requires: spoiler-gated graph endpoint (P1), `visible_from_order` on all seeded nodes (P1), character/source/evidence/claim seed data (P1), episode progress selector (P1), Cytoscape.js graph rendering (P1), node detail panel (P1), and a real Neo4j health check (P1).

See [FEATURES.md](./FEATURES.md) for the full prioritization matrix, dependency graph, and competitor analysis.

### Architecture Approach

The architecture follows a clean four-layer separation: **Presentation** (React SPA with Cytoscape.js graph viz and spoiler progress UI) → **API Gateway** (FastAPI with spoiler-aware query layer) → **Domain/Service Layer** (per-entity services for series, character, claim, user notes, revisions) → **Data Access** (Neo4j Python Driver singleton with parameterized Cypher queries). The spoiler-boundary logic is isolated in its own `backend/app/spoiler/` package, making it auditable and testable as the central architectural invariant.

**Major architectural patterns:**
1. **Parameterized Cypher Filtering** — Every graph query includes `WHERE n.visible_from_order <= $visible_until_order` injected at the Cypher level, not post-processed in Python. The `visible_until_order` parameter is mandatory (no default, 400 if absent).
2. **Atomic Claim + Evidence Fragments** — Knowledge as subject-predicate-object triples (Claims), each backed by EvidenceFragments pointing to Sources. Claims carry both `relationship_effect` (narrative strength) and `confidence_level` (system certainty) as orthogonal dimensions.
3. **Temporal Validity** — `visible_from_order` (when user sees it) is separate from `valid_from_order`/`valid_until_order` (narrative truth window). For v0, valid_from = visible_from and valid_until = null everywhere.
4. **Separated User and Canonical Content** — User nodes/notes have distinct labels (`UserNote`, custom user labels) and visual styling (dashed borders, different colors). Never merged.
5. **Revision Log as Event Stream** — Immutable `Revision` nodes linked to affected entities via `CORRECTS`, `SUPERSEDES`, `REVERTS_TO` edges. Revisions include `before`/`after` snapshots for diff rendering.

**Data flow:** User sets progress in ProgressSelector → `visible_until_order` stored in React state → `GET /api/graph?series_id=dexter&visible_until_order=N` → Backend SpoilerGuard validates parameter → Graph Query Builder constructs filtered Cypher → Neo4j returns only visible data → Response Filter safety-checks → Pydantic models strip internal metadata → Frontend receives clean nodes+edges, renders via Cytoscape.js.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full component diagram, project structure, data flow details, and scaling considerations.

### Critical Pitfalls

1. **Spoiler leak via relationship traversal** — A three-way filter (source node, relationship, target node all checked) is essential. Relationship models must never carry denormalized node data (`target_name`, `target_label`). Address in Milestone 3.

2. **`visible_from_order` drift / inconsistent field population** — Nodes seeded without `visible_from_order` silently vanish (NULL comparison in Cypher yields false). Mitigate with Neo4j existence constraints per label, explicit field in every seed file, and a CI check (`MATCH (n) WHERE n.visible_from_order IS NULL RETURN count(n)` must be 0).

3. **Over-engineering the ontology before understanding the data** — Start with minimal types (Character, Claim, Episode, Source, EvidenceFragment). Write seed data first, then trim the ontology to match reality. Only build Cypher queries and Pydantic models for labels actively used.

4. **Cypher spoiler leaks via `OPTIONAL MATCH`** — `OPTIONAL MATCH` can return partial relationship metadata even when the target is NULL. Never use `OPTIONAL MATCH` for spoiler-boundary filtering; use explicit `WHERE` clauses and explicitly project only allowed fields in the RETURN clause.

5. **Frontend caches spoiled data after progress change** — Include `visible_until_order` in the React Query cache key (`queryKey: ['graph', seriesId, visibleUntilOrder]`). Never store graph elements in global state that survives param changes. Clear the Cytoscape instance completely before re-rendering.

6. **Import-time Neo4j driver initialization breaking tests** — Current codebase creates the driver singleton at module import time. Refactor to lazy initialization or FastAPI lifespan creation so tests can import modules without a running Neo4j instance.

7. **Underspecified graph API response (graph closure invariant)** — The response must guarantee every edge's `source` and `target` ID appears in the nodes array. Add a Pydantic validator as a backstop.

See [PITFALLS.md](./PITFALLS.md) for the complete 12-pitfall catalog, recovery strategies, performance traps, security mistakes, UX pitfalls, and the "Looks Done But Isn't" checklist.

## Implications for Roadmap

Based on research findings, dependencies, and risk mitigation priorities, the following phase structure is recommended:

### Phase 1: Stabilize Infrastructure
**Rationale:** The existing codebase has known issues (duplicate FastAPI app construction, hardcoded health check, import-time Neo4j driver) that block all subsequent development and testing. Fixing these first eliminates landmines that would otherwise derail every later milestone.
**Delivers:** Reliable Neo4j connection, real health check, lazy driver initialization, working `pytest` suite without a running Neo4j instance.
**Addresses:** INFRA-01 from PROJECT.md.
**Avoids:** Pitfall 7 (import-time driver breaks tests), Pitfall 10 (duplicate app construction).
**Research flag:** Low complexity — well-documented patterns for FastAPI lifespan, Pydantic settings, and pytest fixtures.

### Phase 2: Metadata Graph + Constraints
**Rationale:** Series, season, and episode nodes form the structural backbone of the graph. Creating these with Neo4j existence constraints on `visible_from_order` ensures the spoiler-filtering invariant is enforced at the database level before any narrative data is loaded.
**Delivers:** Episode graph with PART_OF/PRECEDES relationships, Neo4j constraints per node label, seed script that verifies post-seed state.
**Uses:** Neo4j Python Driver, PyYAML for ontology loading.
**Implements:** Data Access Layer (existing pattern, hardened).
**Avoids:** Pitfall 2 (`visible_from_order` drift via constraints).
**Research flag:** Standard Neo4j patterns — skip deep research.

### Phase 3: Spoiler-Aware Graph Endpoint (Critical Path)
**Rationale:** This is the core architectural invariant — no feature makes sense without it. The `GET /api/graph?series_id=&visible_until_order=N` endpoint with three-way filtering, SpoilerGuard validation, and the graph closure invariant must be built, tested, and proven before any frontend graph work begins.
**Delivers:** Parameterized Cypher filtering, response filter safety net, Pydantic response models with graph closure validation, integration tests at multiple progress boundaries.
**Addresses:** GRAPH-01, GRAPH-02, GRAPH-03 from PROJECT.md.
**Uses:** FastAPI router + dependency injection, Neo4j parameterized queries, Pydantic validators.
**Avoids:** Pitfall 1 (relationship traversal leak), Pitfall 4 (OPTIONAL MATCH leak), Pitfall 9 (underspecified graph response).
**Implements:** Spoiler Guard/Filter from architecture diagram.
**Research flag:** CRITICAL — start writing tests alongside implementation.

### Phase 4: Seed Character/Claim/Evidence Data
**Rationale:** Seeded data must exist before visualization can be built or tested. The seed data must be designed as a compelling demo (not just schema-correct data) with multi-episode visibility to demonstrate spoiler-gating visually.
**Delivers:** Dexter S01E01-03 character network, 5+ characters per episode, 3+ claims with evidence links, at least one cross-episode claim, at least one claim with `visible_from_order=3` for spoiler testing.
**Addresses:** DATA-01, DATA-02 from PROJECT.md.
**Uses:** PyYAML for ontology, Neo4j MERGE operations, JSON seed files.
**Avoids:** Pitfall 3 (over-engineered ontology — implement only what seed data uses), Pitfall 8 (claim model collapsing fact with certainty), Pitfall 12 (insufficient seed data for demo).
**Implements:** Character Service, Claim Service from architecture.
**Research flag:** Seed data design should be validated by walking through the Demo Story (ROADMAP §8) before writing JSON.

### Phase 5: Frontend Graph UI
**Rationale:** Building the frontend before the backend API is ready leads to mock data, integration delays, and untestable assumptions. The frontend consumes the working graph endpoint from Phase 3 and the seed data from Phase 4.
**Delivers:** Product layout replacing Vite starter, ProgressSelector with spoiler modal, Cytoscape.js graph rendering, NodePanel, EdgePanel, wiring to all backend endpoints.
**Addresses:** UI-01, UI-02, UI-03, UI-04, UI-05 from PROJECT.md.
**Uses:** @tanstack/react-query (cache keyed by visibleUntilOrder), react-router-dom (view routing), react-cytoscapejs (graph rendering).
**Implements:** Presentation Layer from architecture diagram.
**Avoids:** Pitfall 5 (frontend caching spoiled data — RQ cache key strategy), Pitfall 6 (Cytoscape performance — test with expected seed size, use `fcose` layout).
**Research flag:** Performance testing at expected seed size (~50 nodes) before polishing UI. Ghost nodes (optional enhancement) may increase visual complexity.

### Phase 6: User Notes + Manual Editing
**Rationale:** Once users can explore the graph, the next natural capability is annotating characters and adding missing connections. User content must be visually distinct from canonical data from the start.
**Delivers:** UserNote CRUD endpoints, user-created nodes/relationships, separate visual styling in frontend.
**Addresses:** NOTE-01, NOTE-02 from PROJECT.md.
**Uses:** Neo4j driver for UserNote nodes, FastAPI routers, Pydantic models.
**Implements:** UserNote Service from architecture.
**Implements:** Pattern 4 (Separated User and Canonical Content).

### Phase 7: Revision History
**Rationale:** Revisions add value only when users are actively editing. Build after Phase 6 so there are edits to record.
**Delivers:** Revision model with `before`/`after` snapshots and `changed_fields`, display panel, revert operation.
**Addresses:** REV-01, REV-02 from PROJECT.md.
**Implements:** Pattern 5 (Revision Log as Event Stream).
**Avoids:** Pitfall 11 (revision model that can't represent partial edits — use `before`/`after` + `changed_fields`, not full snapshots).
**Implements:** Revision Service from architecture.

### Phase 8: Tests + CI
**Rationale:** Tests should be written alongside code from Phase 3 onward, but dedicating a phase to filling coverage gaps, adding CI, and hardening error handling ensures production quality.
**Delivers:** Backend unit tests (spoiler boundaries, all routes), frontend lint + build checks, GitHub Actions workflow, user-facing error handling.
**Addresses:** TEST-01, TEST-02, CI-01 from PROJECT.md.

### Phase 9: Candidate Claim Workflow (future)
**Delivers:** Claim status model (candidate → reviewed → canonical), review/approve/reject UI, source connector interface.
**Deferred:** Requires LLM integration; core graph must be proven first.

### Phase 10: LLM Chat Over Graph (future)
**Delivers:** Spoiler-gated retrieval tools, LLM provider integration, conversational interface.
**Deferred:** Milestone 9 — depends on complete spoiler-gating infrastructure, claim model, revision history, and candidate workflow.

### Phase Ordering Rationale

- **Infrastructure first** (Phase 1) — the existing landmines (duplicate FastAPI app, import-time driver, hardcoded health check) will silently break everything that follows if not fixed.
- **Spoiler endpoint before frontend** (Phase 3 → Phase 5) — the frontend depends on the spoiler-gated API. Building frontend with mock data creates integration delays and untestable assumptions.
- **Seed data before visualization** (Phase 4 overlaps Phase 5) — seed a minimal graph first, prove visualization works, then expand. The `visible_from_order=3` claim in seed data enables spoiler-gating validation in the UI.
- **User notes after graph UI** (Phase 6) — notes are displayed in the node detail panel; without the graph UI, notes have no visual context.
- **Revisions after user edits** (Phase 7) — no edits flowing means no revisions to display.
- **Tests alongside implementation** — start writing tests in Phase 3, not Phase 8. Phase 8 closes the gap.
- **LLM last** (Phase 10) — requires the complete spoiler infrastructure, claim model, revision history, and candidate workflow. Attempting earlier risks spooning data to the LLM.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3 (Spoiler endpoint):** Cypher query design for multi-type filtering (characters + claims + evidence with different `visible_from_order` values) needs careful planning. The three-way filter and graph closure invariant must be designed together as a leak-proof contract.
- **Phase 5 (Frontend UI):** Cytoscape.js performance characteristics with the projected seed data size (~50 nodes). `fcose` vs `cose-bilkent` layout choice should be validated with actual data.
- **Phase 7 (Revisions):** Revision model design — `before`/`after` snapshot vs structured diff pattern needs iterative refinement. Research how Neo4j handles high-frequency write+read on Revision node streams.
- **Phase 9–10 (LLM integration):** Spoiler-guarded retrieval tool design, LLM prompt injection guardrails. Full research needed before implementation.

Phases with standard patterns (skip deep research-phase):
- **Phase 1 (Infrastructure):** Well-documented patterns for FastAPI lifespan, singleton lifecycle, pytest fixtures.
- **Phase 2 (Metadata graph):** Standard Neo4j constraint and MERGE patterns.
- **Phase 4 (Seed data):** JSON → Neo4j data loading is straightforward. The design challenge is demo-story quality, not technical.
- **Phase 6 (User notes):** Standard CRUD with Neo4j, similar to existing series/episode endpoints.
- **Phase 8 (Tests/CI):** Standard GitHub Actions + pytest + Vitest patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Every technology is installed, version-compatible, verified against official docs. Alternatives considered and dismissed with clear rationale. |
| Features | HIGH | Competitive analysis vs 6 existing products shows clear niche. Feature prioritization backed by dependency analysis and user value scoring. |
| Architecture | HIGH | Patterns (parameterized Cypher, atomic claims, temporal validity, separated user content, revision stream) are well-documented and independently verifiable. |
| Pitfalls | HIGH | 12 documented pitfalls with specific prevention strategies, derived from similar projects' experience and codebase audit (CONCERNS.md). Recovery strategies provided. |

**Overall confidence:** HIGH

### Gaps to Address

- **Cytoscape.js layout performance with real-world graph sizes:** The projected seed data (~30–50 nodes) is well within Cytoscape.js's comfort zone, but the performance cliff at ~200 nodes should be validated during Phase 5 if the seed scope expands.
- **Temporal validity complexity:** The `valid_from_order`/`valid_until_order` model is theoretically sound but unproven with real narrative data. Phase 4 should include at least one claim with `valid_until_order` to validate the query pattern.
- **Revision model granularity:** The choice between `before`/`after` snapshots vs structured diffs affects both storage and UX. Prototype both approaches briefly during Phase 7 planning.
- **LLM spoiler guardrails (Phase 10):** The current architecture guarantees spoiler safety for direct graph queries, but LLM-based chat introduces a new attack surface (prompt injection, tool misuse). Deferred to Phase 10 research, but the graph endpoint infrastructure built in Phase 3 is the prerequisite.

## Sources

### Primary (HIGH confidence)
- [FastAPI official docs](https://fastapi.tiangolo.com/) — async patterns, lifespan, middleware, CORS config
- [Neo4j Python Driver v6 manual](https://neo4j.com/docs/python-manual/current/) — driver lifecycle, execute_query API, async patterns
- [Neo4j Cypher Manual](https://neo4j.com/docs/cypher-manual/current/) — constraint syntax, property type constraints, OPTIONAL MATCH semantics
- [Cytoscape.js v3 docs](https://js.cytoscape.org/) — element data format, layout algorithms, compound nodes, edge bundling
- [TanStack React Query v5 docs](https://tanstack.com/query/v5/docs/framework/react/overview) — query keys, cache invalidation, mutations
- [React Router v7 docs — Library Mode](https://reactrouter.com/start/library/installation) — declarative routing, nested layouts
- [Vitest v3 config reference](https://vitest.dev/config/) — vite.config.ts integration, jsdom environment
- [pytest-asyncio v0.25 docs](https://pytest-asyncio.readthedocs.io/) — asyncio_mode, async fixtures
- [react-cytoscapejs GitHub](https://github.com/plotly/react-cytoscapejs) — wrapper API, event handling, lifecycle

### Secondary (MEDIUM confidence)
- **Serializd** (https://serializd.com) — TV tracking + community, "Letterboxd for TV", confirms no graph features
- **Trakt** (https://trakt.tv) — TV/movie tracking, no spoiler gating
- **TV Time** (https://tvtime.com) — Social TV tracking, no data-layer spoiler protection
- **The StoryGraph** (https://thestorygraph.com) — Book tracking with community-managed spoiler tags (not systematic)
- **TV Tropes** (https://tvtropes.org) — Crowdsourced narrative tropes wiki, no graph API
- **Obsidian** (https://obsidian.md) — Local markdown knowledge graph with graph view, no TV-specific models
- **IMDb** (https://imdb.com) — TV episode guides, character data, no graph exploration
- **Cytoscape.js performance guidelines** (github.com/cytoscape/cytoscape.js/wiki/Performance) — layout performance cliff at ~100+ nodes
- **Neo4j GraphGists** — Reference graph data models for TV series and narrative
- **CONCERNS.md** — Codebase audit findings from `.planning/codebase/CONCERNS.md`
- **ROADMAP.md** — Existing project roadmap, ontology v0.1, Demo Story
- **PROJECT.md** — Project context, validated requirements, active requirements

### Tertiary (LOW confidence)
- Personal experience accounts from similar spoiler-safe graph projects (narrative knowledge graphs for TV) — informs pitfall catalog but not independently verifiable
- Neo4j community edition constraint behavior for `visible_from_order` null handling — verified during Phase 2 implementation

---

*Research completed: 2026-07-28*
*Ready for roadmap: yes*
