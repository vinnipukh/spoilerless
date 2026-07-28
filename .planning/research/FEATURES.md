# Feature Research

**Domain:** Spoiler-Safe Narrative Knowledge Graph for TV Series
**Researched:** 2026-07-28
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features that any TV-series companion or knowledge-graph app ought to have. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Series/Episode browser | Users need to pick a show and see episode lists | LOW | Already scaffolded: `GET /api/series`, `GET /api/series/{id}/episodes` |
| Watch progress tracking | Users expect to mark which episode they're on | LOW | Already in ROADMARK as "Episode progress selector" with spoiler confirmation modal |
| Character nodes with metadata | Core narrative entity — name, image, description, aliases | LOW | Character model defined in ROADMAP.md ontology (narrative node type) |
| Relationship types between characters (KNOWS, FAMILY_OF, etc.) | Essential for any character relationship graph | LOW | 10+ character relation types defined in ontology v0.1 |
| Episode ordering (season + episode number) | Users navigate the timeline of a show | LOW | ORDER field on Episode nodes; PRECEDES relationship between episodes |
| Graph visualization (forces-directed layout) | Users expect to see an interactive graph of characters and connections | MEDIUM | Cytoscape.js already in stack; need layout config and stylesheet for character/claim/evidence distinction |
| Node detail panel | Clicking a node shows what it is, its attributes, and connected claims | MEDIUM | Already planned (UI-04 in PROJECT.md) — shows node info, claims, evidence links |
| Edge/relationship detail panel | Clicking an edge shows relationship type, strength, and evidence | MEDIUM | Planned (UI-05 in PROJECT.md) |
| Season/episode metadata (air date, title, synopsis) | Required for basic show context | LOW | Metadata loaded via Dexter seed files (series.json, episodes.json) |
| Source/evidence display for claims | Users expect to see "why does the system think this" | MEDIUM | EvidenceFragment model with source locator; core principle: every auto-claim must be source-backed |

### Differentiators (Competitive Advantage)

Features that set HD Graf Cehennemi apart from every existing TV companion and graph app.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Spoiler-gated graph at the data-access layer** | Backend guarantees the frontend never receives data beyond the user's watch progress — not just a UI toggle | MEDIUM | `visible_from_order` on every node, claim, and relationship; Cypher filtering in `GET /api/graph`. This is THE core differentiator. No existing product (Trakt, Serializd, TV Time, IMDb) does this. |
| **Progressive graph disclosure** | As the user advances their watch progress, new character connections, claims, and evidence unlock — like a map revealing itself | MEDIUM | Each unlock shows new nodes/edges. Even an empty graph for episode 0 is compelling. |
| **Atomic claim model with temporal validity** | Claims carry `valid_from_order` and `valid_until_order` — a character can later be revealed as someone else (spoiler: they are related, or one is actually another in disguise) and the graph handles it cleanly | MEDIUM | Claim temporal validity allows rewrites and reveals within the same graph without data corruption. |
| **Two-dimensional knowledge model: relationship_effect × confidence_level** | Separate axes for "how strong is this narrative relationship" vs "how sure are we of this fact" | MEDIUM | Unique in TV companion apps. Lets users see both clear canonical facts (confidence=verified, effect=strong) and speculative/fan claims (confidence=low, effect=weak). |
| **User vs canonical content separation** | Users can add corrections, notes, and custom nodes without corrupting curated data; visually distinct in the UI | MEDIUM | UserNote and user-created nodes marked with `created_by` field. Different visual style in Cytoscape.js (dashed borders, different color palette). |
| **Revision history with revert** | Every claim change is logged; users can inspect previous versions and revert | HIGH | Revision model with CORRECTS, SUPERSEDES, REVERTS_TO relationships. Not just an audit log — a walkable graph of changes. |
| **Source-backed evidence chain on every claim** | Every automated claim traces back to specific evidence: source type, locator, episode, timestamp | MEDIUM | EvidenceFragment nodes linked via SUPPORTED_BY/CONTRADICTED_BY. Different from TV Tropes (which is trope-level, not episode-level). |
| **Candidate claim workflow for LLM extraction** | Future LLM extractions produce "candidate" claims that need review/approval before becoming canonical | MEDIUM | Claim status workflow: candidate → reviewed → corroborated/canonical/disputed/rejected. Full review/approve/reject UI planned (Milestone 8). |
| **Obsidian-style "second brain" for a TV show** | Not just tracking — deep knowledge graph exploration of character relationships, source evidence, and narrative structure | HIGH | Combines graph database (Neo4j) with visual exploration (Cytoscape.js) and personal annotation (UserNote). No product does this for TV. |
| **Cytoscape.js with spoiler-aware styling** | Nodes/edges beyond the boundary don't just hide — their styling can encode "there's something hidden here" (hollow/ghost nodes for known-but-spoilered connections) | MEDIUM | Ghost nodes optionally shown at spoiler boundary to hint at known connections without revealing details. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for a single-user local prototype.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Multi-user accounts & auth | "What if I want to share with friends?" | Single-user prototype; adds auth tokens, password hashing, session management — all irrelevant for local use. Multi-user spoiler boundaries compound complexity exponentially (different users at different watch points). | Skip entirely for v0. Single-user local app only. Add multi-user only if product-market fit justifies it post-v0. |
| Real-time collaborative editing | "Like Google Docs for the graph" | Requires WebSocket sync, conflict resolution, OT/CRDT — enormous complexity for zero current need. Revision history is already planned and covers the offline-collaboration use case. | Revision history + export/import of graph data. |
| Live LLM chat over the full graph | "Let me ask questions about the show" | The LLM must be spoiler-gated at the retrieval layer. Without careful guardrails, the LLM WILL leak spoilers. Full LLM integration is Milestone 9 for a reason. | Start with graph-only exploration (no LLM). Add spoiler-gated retrieval tools in v2. |
| Full automated scraping pipeline (subtitles, scripts, Fandom, IMDb, podcasts) | "The data should populate itself" | Maintenance burden: website structure changes break scrapers. Legal ambiguity around scraping. Data quality varies wildly across sources. | Seed the graph manually for prototype scope. Design clean Source connector interface (Milestone 8) but don't build scrapers yet. |
| Mobile app / push notifications | "I want to use this on my phone" | Full React Native or separate mobile build. Graph visualization on small screens is a hard UX problem. Not needed for a prototype that runs on localhost. | Focus on responsive desktop web. Cytoscape.js works on mobile but mobile-first UX is a separate project. |
| Social features (comments, likes, sharing) | "Let people discuss the graph" | Content moderation, spam, spoiler leakage through comments, user management. None of these serve the core value proposition. | User notes are personal (not social). Add social after the graph itself is proven. |
| Public hosting / "make it a website" | "Let anyone access it" | Spoiler safety is undermined by public access (anyone can set their progress to "finished" and see everything). Also: hosting costs, security, domain management. | Keep local-only for prototype. Document containerization path for self-hosting if desired. |
| Auto-magic graph layout | "Users shouldn't have to arrange nodes" | No perfect auto-layout exists for narrative graphs. Force-directed (Cose) is the default but often produces visual clutter. Over-investing in layout before content is wasted effort. | Ship with Cose layout (Cytoscape.js default). Add layout switching (grid, concentric, breadthfirst, random) as a power-user option. |
| Spoiler tags on every individual element | "Let users manually mark spoilers" | Requires community consensus on what's a spoiler. Manual tagging doesn't scale. Undermines the systematic `visible_from_order` model by adding a subjective layer. | Systematic episode-boundary spoiler gating is superior. Individual spoiler tags create ambiguity and maintenance burden. |

## Feature Dependencies

```
 Spoiler-Gated Graph (GRAPH-01)
    └──requires──> visible_from_order on every Seeded Node (GRAPH-02)
                       └──requires──> Seed Script with Constraints (INFRA-02)
                                         └──requires──> Neo4j DB Running (INFRA-01)

 Character/Claim/Evidence Seed (MILESTONE 4)
    └──requires──> Ontology YAML Files (node_types, relation_types, claim_types)
                       └──requires──> Core Graph Data Model (ROADMAP §6)
    └──requires──> Dexter Metadata Files (series.json, episodes.json)

 Frontend Graph UI (MILESTONE 5)
    └──requires──> Spoiler-Gated Graph Endpoint (GRAPH-01)
    └──requires──> Cytoscape.js + react-cytoscapejs installed (done)
    └──requires──> Graph Response Model (Pydantic -> JSON)
                       └──requires──> Spoiler Boundary Query Parameter

 User Notes & Custom Nodes (MILESTONE 6)
    └──requires──> Frontend Graph UI (MILESTONE 5)
    └──requires──> UserNote Model in Neo4j
                       └──requires──> User vs Canonical Separation Pattern

 Revision History (MILESTONE 7)
    └──requires──> Revision Node Model
                       └──requires──> Claim Model with versioning fields
    └──requires──> Frontend Display Panel

 Candidate Claim Workflow (MILESTONE 8)
    └──requires──> Claim Status Model (candidate → reviewed → canonical)
    └──requires──> Review/Approve/Reject API Endpoints

 LLM Chat (MILESTONE 9)
    └──requires──> Spoiler-Gated Graph Endpoint (GRAPH-01)
    └──requires──> Spoiler-Aware Retrieval Tools
    └──requires──> LLM Provider Integration

 Source Connector Interface (MILESTONE 8)
    └──requires──> EvidenceFragment Model
    └──requires──> Source Type Ontology
```

### Dependency Notes

- **Spoiler-Gated Graph is the lynchpin:** Everything downstream (frontend graph UI, LLM chat, progressive disclosure) depends on it. It must be built and tested first among graph features.
- **Seeded data precedes visualization:** You cannot build a useful graph UI without data to display. Milestone 4 (seed) must meaningfully overlap with Milestone 5 (UI) — seed a small graph first, prove visualization works, then expand.
- **User notes depend on graph UI:** Notes are displayed in the node detail panel. Without the graph UI and node selection, notes have no context.
- **Revision history depends on claim creation:** Revisions log what changed. No claims flowing → no revisions to display. Revisions add value only when users are actively editing.
- **LLM chat requires everything:** It's the last milestone because it depends on the complete spoiler-gating infrastructure, the complete claim model, revision history, and the candidate workflow. Do not attempt before Milestone 5 is solid.

### Enhancement Relationships

| Enhancer Feature | Target Feature | How They Combine |
|-----------------|----------------|------------------|
| Ghost nodes at spoiler boundary | Spoiler-Gated Graph | Shows a translucent node at the boundary hinting "someone appears here next" without revealing identity |
| Edge bundling in Cytoscape.js | Frontend Graph UI | Reduces visual clutter when multiple relationships exist between the same two characters |
| Node search/filter | Frontend Graph UI | Lets users find specific characters in a complex graph |
| Graph layout switching (grid, concentric, hierarchical) | Frontend Graph UI | Different narrative patterns benefit from different layouts — concentric for relationships around a protagonist, hierarchical for organizational structures |
| Cypher-native spoiler queries | Spoiler-Gated Graph | Encodes visible_from_order filtering directly in Cypher `WHERE` clauses rather than post-filtering in Python — more performant and harder to accidentally bypass |

## MVP Definition

### Launch With (v1)

Minimum viable prototype — what validates the concept for Dexter Season 1, Episodes 1–3.

- [x] **INFRA-01: Neo4j database running via Docker Compose** — already working
- [x] **INFRA-02: Backend scaffold (FastAPI + CORS + health endpoint)** — already scaffolded (needs real health check)
- [x] **Frontend scaffold (Vite + React + TypeScript + Cytoscape.js)** — already scaffolded
- [ ] **GRAPH-01: Spoiler-gated graph endpoint** — essential: `GET /api/graph?series_id=...&visible_until_order=N`
- [ ] **GRAPH-02: visible_from_order on all seeded nodes** — required for GRAPH-01 to work
- [ ] **DATA-01: Character, source, evidence, and claim seed files** — needed for any graph visualization
- [ ] **DATA-02: Seed script for Dexter S01E01 character network** — one-click seed
- [ ] **UI-02: Episode progress selector with spoiler confirmation modal** — core UX flow
- [ ] **UI-03: Cytoscape.js graph rendering** — the primary interaction surface
- [ ] **UI-04: Node detail panel** — shows character info + claims + evidence

### Add After Validation (v1.x)

Features to add once the core spoiler-gated graph is proven.

- [ ] **NOTE-01: UserNote model + CRUD endpoints** — triggered by: users wanting to annotate characters/claims
- [ ] **NOTE-02: User-created nodes and relationships** — triggered by: users wanting to add missing characters
- [ ] **REV-01: Revision history model** — triggered by: first accidental deletion or erroneous claim
- [ ] **REV-02: Revision display + revert** — triggered by: REV-01 existing but no way to inspect
- [ ] **UI-05: Edge/claim detail panel** — triggered by: users clicking relationships and wanting details
- [ ] **TEST-01/02: Backend + frontend tests** — triggered by: codebase growing beyond trivial size
- [ ] **Ghost nodes at spoiler boundary** — triggered by: users wanting to know "how much more is there?"

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **LLM-01: Candidate claim layer + review workflow** — defer because: requires LLM integration; core graph must be proven first
- [ ] **LLM chat over spoiler-gated graph** — defer because: introduces complex guardrail requirements; easy to leak spoilers
- [ ] **Full automated subtitle/script scraping** — defer because: high maintenance burden; manual seed is sufficient for prototype
- [ ] **Fandom/IMDb/news ingestion** — defer because: legal ambiguity, data quality variance
- [ ] **Podcast transcription extraction** — defer because: niche use case, hard to parse
- [ ] **Multi-series support beyond Dexter** — defer because: prove with one series first
- [ ] **Multi-user accounts** — defer because: single-user prototype; multi-user spoiler boundaries are exponentially complex
- [ ] **Mobile app** — defer because: not needed for local prototype; responsive web is sufficient for exploration

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Spoiler-gated graph endpoint (GRAPH-01) | HIGH | MEDIUM | P1 |
| visible_from_order on all seeded nodes (GRAPH-02) | HIGH | LOW | P1 |
| Seed character/source/evidence/claim data (DATA-01/02) | HIGH | MEDIUM | P1 |
| Episode progress selector with spoiler modal (UI-02) | HIGH | LOW | P1 |
| Cytoscape.js graph rendering (UI-03) | HIGH | MEDIUM | P1 |
| Node detail panel (UI-04) | HIGH | MEDIUM | P1 |
| Real Neo4j health check (INFRA-01 fix) | MEDIUM | LOW | P1 |
| Edge/claim detail panel (UI-05) | MEDIUM | MEDIUM | P2 |
| UserNote CRUD (NOTE-01) | MEDIUM | MEDIUM | P2 |
| User-created nodes/relationships (NOTE-02) | MEDIUM | HIGH | P2 |
| Revision history model + display (REV-01/02) | MEDIUM | HIGH | P2 |
| Ghost nodes at spoiler boundary | LOW | MEDIUM | P2 |
| Backend unit tests (TEST-01) | MEDIUM | MEDIUM | P2 |
| Frontend component tests (TEST-02) | MEDIUM | MEDIUM | P2 |
| CI pipeline (CI-01) | MEDIUM | LOW | P2 |
| Candidate claim workflow (LLM-01) | MEDIUM | HIGH | P3 |
| Graph layout switching | LOW | LOW | P3 |
| Node search/filter in graph | MEDIUM | MEDIUM | P3 |
| Source connector interface | MEDIUM | HIGH | P3 |
| LLM chat over graph | HIGH | VERY HIGH | P4 |
| Automated scraping pipeline | HIGH | VERY HIGH | P4 |
| Multi-user/auth | LOW (for prototype) | HIGH | P4 |

**Priority key:**
- P1: Must have for prototype launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration
- P4: Only if product-market fit is proven

## Competitor Feature Analysis

| Feature | Serializd | Trakt | TV Time | The StoryGraph | IMDb | TV Tropes | Obsidian | Our Approach |
|---------|-----------|-------|---------|---------------|------|-----------|----------|-------------|
| Watch progress tracking | ✅ Per-episode | ✅ Per-episode | ✅ Per-episode | ✅ Per-book | ✅ Per-episode | ❌ | ❌ | ✅ Per-episode with spoiler boundary |
| Spoiler-gated content | ❌ No gating | ❌ Community spoiler tags only | ❌ Community spoiler tags only | ✅ "Spoiler-free" reading mode (community managed) | ❌ | ❌ | ❌ | ✅ Data-layer gating via visible_from_order — strongest approach |
| Graph visualization | ❌ | ❌ | ❌ | ✅ Book relationship graph (limited) | ❌ | ❌ | ✅ Local note graph (backlinks) | ✅ Cytoscape.js interactive graph with node/edge detail |
| Character relationship graph | ❌ | ❌ | ❌ | ❌ | ✅ Credits/cast (flat list) | ✅ Trope connections (wiki) | ❌ | ✅ Neo4j graph: KNOWS, KILLS, FAMILY_OF, etc. |
| Source-backed evidence | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Inline citations (wiki style) | ❌ | ✅ EvidenceFragment → Source model per claim |
| User notes/annotations | ❌ | ❌ | ❌ | ✅ Book notes/journal | ❌ | ❌ | ✅ Rich markdown notes | ✅ UserNote model with graph context |
| Revision history | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Wiki edit history | ✅ Git-based | ✅ Neo4j Revision nodes with revert |
| Temporal claim validity | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ valid_from_order / valid_until_order |
| relationship_effect × confidence_level | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Two orthogonal dimensions |
| LLM chat over data | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ AI chat (limited) | ✅ Future: spoiler-gated retrieval + answer generation |

### Competitive Insight

**No existing product combines spoiler-gated graph exploration with a character/claim knowledge graph for TV.** The closest analogs:

- **The StoryGraph** has the strongest spoiler-free philosophy, but it's for books (not TV) and uses community-managed spoiler tags (not systematic data-layer filtering).
- **TV Tropes** has the richest narrative graph of tropes connected to works, but it's wiki-based (no graph API, no spoiler gating, no character-level relationship model).
- **Obsidian** has the best local knowledge graph experience, but it's a general-purpose note-taking tool (no TV-specific models, no spoiler system, no narrative structure).
- **Serializd/Trakt/TV Time** have robust watch tracking but are social-log-focused — they track "what you watched" not "what happened in the story."

**HD Graf Cehennemi occupies a unique niche:** a structured, queryable narrative knowledge graph that genuinely prevents spoilers by architectural enforcement rather than community labeling.

## Sources

- **Serializd** (https://serializd.com) — TV tracking + community, "Letterboxd for TV"
- **Trakt** (https://trakt.tv) — TV/movie tracking with watchlists, no spoiler gating
- **TV Time** (https://tvtime.com) — Social TV tracking, episode reactions
- **The StoryGraph** (https://thestorygraph.com) — Book tracking with spoiler-free reading mode, relationship graphs
- **TV Tropes** (https://tvtropes.org) — Crowdsourced narrative tropes wiki
- **Obsidian** (https://obsidian.md) — Local markdown knowledge graph with graph view
- **IMDb** (https://imdb.com) — TV episode guides, cast/character data
- **Neo4j GraphGists** — Reference graph data models for TV series and narrative
- **Cytoscape.js** (https://js.cytoscape.org) — Graph visualization library for interactive network rendering
- **ROADMAP.md** — Existing project roadmap with 9 milestones and detailed ontology v0.1
- **STACK.md** — Technology stack research and rationale (.planning/research/STACK.md)
- **PROJECT.md** — Project context and validated/active requirements (.planning/PROJECT.md)
- **Cytoscape.js documentation** — Layout algorithms (cose, concentric, grid, breadthfirst), compound node support, edge bundling, event handling
- **Neo4j Cypher Manual** — Property constraints, temporal filtering, path queries applicable to visible_from_order gating

---

*Feature research for: HD Graf Cehennemi (spoiler-safe narrative knowledge graph)*
*Researched: 2026-07-28*
