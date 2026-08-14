# HD Graf Cehennemi (Spoilerless)

## What This Is

A spoiler-safe narrative knowledge graph for TV series with a grounded conversational agent, shipped as a live zero-cost hosted product. As of v1.3 (Spoilerless), the app covers Dexter Season 1 with an enriched episode-101 knowledge base, runs on Render + Vercel + Neo4j AuraDB Free + Upstash Redis, and lets an authenticated user explore source-backed narrative knowledge through four coordinated views (Story, Characters, Evidence, Advanced), control the visible episode boundary, add personal knowledge, inspect/revert revisions, ask questions answered only from graph data visible up to their watch progress (with clickable citations, graph highlighting, and a GraphRAG Answer Graph), export knowledge, and safely propose graph edits through a typed confirm-before-apply ChangeSet flow.

## Core Value

Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress, because filtering occurs in the backend before data reaches the frontend, the LLM, or any tool call. No raw Cypher ever reaches the model, and no graph write happens without explicit human confirmation. One shared fail-closed boundary resolver (`resolve_effective_boundary` = `min(requested_view_order, watched_progress)`) is the single enforcement seam across graph reads, projections, expansion, path/search, GraphRAG focus, and saved restoration.

## Current State (v1.3 shipped 2026-08-14)

- **Live deployment at $0:** Vercel (frontend) + Render free web service (backend, `spoilerless.app.main:app`) + Neo4j AuraDB Free (`03a8623b`) + Upstash Redis (`darling-rat-221809`), custom domain, `docs/DEPLOYMENT.md` with rollback procedure.
- **Access control:** Google OAuth with operator email allowlist (`ALLOWED_EMAILS`), no dev-auth backdoor, admin role derived server-side from `ADMIN_EMAILS` at every login gating candidate review / ChangeSet confirm / server LLM settings; BYOK LLM chat (browser-held key in `localStorage`, per-request `X-LLM-*` headers, never persisted server-side); Secure/SameSite cookies, fail-closed CSRF Origin/Referer, Redis-backed multi-worker rate limits (login/chat/writes → 429).
- **Spoiler-safe visualization:** library-neutral DTO + 6 projections (`episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`), cache keys carry series/order/view/projection_version/epoch/scope/focus-SHA; Episode Overview Variant A default (12–28 nodes / <35 edges bounds); server-allowlisted semantic expansion (7 keys, undo/collapse/reset); GraphRAG Answer Graph + Evidence Chain with scene restoration; benchmark harness (30/50 → 300/1000 node/edge datasets).
- **Audit-remediated core:** all 45+ `docs/PROBLEMS.md` findings resolved (ownership on every mutation, collision-proof sessions + sweep, deterministic suites via scratch-series isolation + drift-agnostic asserts + zombie sweep + CI DB-pollution gate, lint 0 errors, error-code convention, security headers, core-module direct tests), plus 10 new features (search/jump, timeline, reveal highlight, dashboard, export, path finder, full-text search, command palette, shareable snapshots, mobile) and FEAT-11 touches (backlinks, hover cards, ⌘K switcher, filters, node properties).
- **Rebranded:** package dirs, pyproject, docker-compose, services, `/health` `service` field, UI title, and docs renamed `hdgrafcehennemi` → `spoilerless` (git history intentionally untouched).
- ~23,300+ LOC across `backend/app` and `frontend/src`. Python 3.13 + FastAPI + Pydantic v2 + Neo4j async driver; React 19 + TypeScript + Vite + Cytoscape.js; `uv` for Python packaging. Backend 142+ offline tests green; frontend 400 tests; coverage audit 98/98 source ids.

## Next Milestone Goals (candidates, not yet scoped)

- Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement (OPS-01 remains a minimal PR gate)
- Full observability: centralized log aggregation, metrics dashboards, incident/rollback runbook automation (OPS-03 is structured app logging only)
- Person / ACTED_AS / APPEARS_IN actor model; reviews, ratings, trivia, recommendations; automated external ingestion
- Complete the 2026-08-04 Dexter S01E01 enrichment quick task's live steps (AuraDB seed + DB-backed tests + browser acceptance — blocked earlier by Aura auth failure)

## Previous Milestones

<details>
<summary>v1.2 Spoiler-Safety Hardening (shipped 2026-08-03) — Phase 7</summary>

**Goal:** Harden spoiler safety by separating watched progress from the temporary view boundary, centralizing the visibility policy, and closing indirect leak channels (metadata, search, counts, media, chat, graph edits) without changing the stack or rebuilding working features.

**Delivered:**
- Watched progress (`watched_through_order`) separated from temporary view boundary (`view_as_of_order`); effective boundary = `min(view, watched)`, enforced server-side
- Central visibility-policy service — `visible_from_order` stays canonical, missing visibility fails closed (no `coalesce(..., 1)` defaults)
- Episode metadata gating (spoiler title → generic label, synopsis/runtime/image masked at the backend) with publication-order semantics across seasons
- Relationship-level + provenance-chain (Claim → EvidenceFragment → Source) visibility; user Notes hidden below their creation boundary
- Search/autocomplete/count leak protection: hidden entities behave like nonexistent, counts are "seen so far" only
- Spoiler-safe media handling: hidden images never returned, neutral fallback + safe alt text
- GraphRAG/chat-history/citations/graph-focus and ChangeSets operate on the effective boundary; boundary snapshot persisted per assistant response
- Documented spoiler-leak threat model and regression matrix
</details>

<details>
<summary>v1.1 MVP (shipped 2026-08-02, supersedes v1.0) — Phases 1–6</summary>

- Neo4j + FastAPI backend, Google OAuth authentication, real health checks, idempotent seed setup.
- React + TypeScript + Cytoscape frontend: series/episode selection, watch-progress confirmation gate, graph exploration, tabbed detail inspector, cinematic visual system.
- User notes and custom nodes/relationships, visually and structurally distinct from canonical/candidate content.
- Append-only revision history with inspect/revert.
- Candidate-claim extraction-preparation layer: structured JSON contract, review UI (approve/reject/edit), source-connector interface — accepts fixtures only, no live ingestion or LLM extraction.
- Full spoiler-safe GraphRAG chat agent: ten allowlisted retrieval tools, an LLM provider abstraction (OpenAI-compatible + Gemini + fake test double), a deterministic retrieval→context→answer→citation pipeline, a versioned system prompt treating all graph-sourced text as untrusted, and a typed two-stage ChangeSet propose/confirm/revert flow with auditable Revision logging.
</details>

## Requirements

### Validated

- ✓ Local Neo4j/FastAPI/React infrastructure with real health checks and idempotent setup — v1.0
- ✓ Dexter Series/Episode metadata graph and endpoints — v1.0
- ✓ Manually curated evidence-backed seed graph with spoiler visibility metadata — v1.0
- ✓ Backend-enforced spoiler-aware graph API (data-access-layer filtering) — v1.0
- ✓ React/Cytoscape graph experience with watch-progress confirmation — v1.0
- ✓ User notes and custom node/relationship creation, distinct from canonical content — v1.0
- ✓ Append-only revision history with revert — v1.0
- ✓ Extraction-preparation contracts, candidate review workflow, source-connector interface (no live ingestion) — v1.0
- ✓ Google OAuth authentication (single real-user model, no roles yet) — v1.0
- ✓ Spoiler-safe GraphRAG chat: allowlisted retrieval tools, LLM provider abstraction, citation-validated grounded answers — v1.1
- ✓ Typed ChangeSet propose/confirm/revert graph-editing flow with auditable Revision — v1.1
- ✓ Email allowlist sign-in; dev-auth backdoor removed; admin role on candidate review/ChangeSet confirm/LLM settings — v1.3 (AUTH-01..04)
- ✓ BYOK LLM chat (browser-held key, per-request headers, never persisted/logged server-side) — v1.3 (AI-01..03)
- ✓ Production cookie/CORS/CSRF hardening, Redis-backed multi-worker rate limiting (429s) — v1.3 (SEC-01..03)
- ✓ AuraDB Free + Upstash Redis cache with write invalidation + Render/Vercel deployment, secrets as platform env vars — v1.3 (INFRA-01..05)
- ✓ GitHub Actions CI gate, external `/health` uptime check, structured exception logging — v1.3 (OPS-01..03)
- ✓ All PROBLEMS.md audit findings (45 original + 12 second-pass) resolved; deterministic test suites; lint 0 errors — v1.3 (PROB-01..32)
- ✓ 10 new features + FEAT-11 second-brain touches; rebrand to Spoilerless — v1.3 (FEAT-01..11, REBRAND-01)
- ✓ Spoiler-safe narrative visualization: DTO, 6 projections, four-view hierarchy, semantic expansion, Answer Graph, benchmarks — v1.3 (VIZ-01..10)
- ✓ Green full regression gate + operator golden-path UAT + shipped-state docs — v1.3 (POLISH-01..03, DOCS-03/04)

### Active

- [ ] Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement
- [ ] Full observability: centralized log aggregation, metrics dashboards, tracing
- [ ] Person / ACTED_AS / APPEARS_IN actor model (carried from v1.1/v1.2)
- [ ] Reviews, ratings, trivia, recommendations (carried from v1.1/v1.2)
- [ ] Automated ingestion/extraction from external sources (OpenSubtitles, scripts, Fandom/IMDb/news)
- [ ] Dexter S01E01 enrichment live-completion: AuraDB seed + DB-backed tests + browser acceptance (data/code/offline tests already shipped 2026-08-04)

### Out of Scope

- Multi-region or high-availability hosting; paid tier / usage-based billing — this product targets $0 free-tier hosting
- Mobile native apps — FEAT-10 is responsive web, not a native app
- Migrating off Neo4j, FastAPI, or React/Vite — hosting changes only, no rewrite
- God-file decomposition (`retrieval/pipeline.py`, `retrieval/tools.py`, `llm/system_prompt.py`, `repository/change_set.py`, `repository/user_content.py`) — noted in `docs/PROBLEMS.md` #18 as maintainability risk, not required for safe public launch
- Versioned Neo4j schema migrations (`docs/PROBLEMS.md` #19) — seed-as-schema continues

## Constraints

- **Spoiler safety:** every exposed graph element carries `visible_from_order`; one fail-closed resolver (`resolve_effective_boundary`) gates the backend before data reaches the frontend, the LLM, or any tool call. Hidden names, labels, evidence, and aggregate counts must not leak through any channel (projections, expansion, search, cache, focus, restoration).
- **No raw Cypher to the LLM:** the model's only actions are typed, allowlisted retrieval tool calls and typed ChangeSet proposals — never a text-to-Cypher surface.
- **Writes require human confirmation:** the model may only *propose* a ChangeSet; a human must explicitly confirm before any transaction touches the graph.
- **Provenance:** automatic/candidate claims require EvidenceFragments with source, episode, locator, retrieval metadata, and content hash where possible. Manually curated seed claims are evidence-backed.
- **Separation:** canonical, candidate/automatic, and user-created content are represented and displayed distinctly; the assistant can never mutate canonical/candidate content directly.
- **History:** edits and reverts append revisions; history is not destroyed.
- **Stack:** Neo4j (AuraDB Free in prod, Docker for local), FastAPI/Pydantic, React 19 + TypeScript + Vite + Cytoscape.js; Python packaging through `uv`; Redis (Upstash) for cache + rate limits.
- **Zero-cost hosting:** free tiers only (Render, Vercel, AuraDB Free, Upstash) — deploy decisions must respect the $0 budget (e.g. Render cold starts, free-tier false-downs).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Root `ROADMAP.md` defined Prototype v0 scope | Prevent planning documents from narrowing the canonical demo | ✓ Good — v0 shipped in full |
| Neo4j as graph source of truth | Graph-native storage fits connected narrative data | ✓ Good |
| Backend/data-access spoiler filtering | Downstream clients (frontend, LLM) must never receive future data | ✓ Good — held through GraphRAG chat and the Phase-10 projection redesign with zero leakage |
| Evidence-backed atomic claims | Users can understand why knowledge exists | ✓ Good |
| Separate user/candidate/canonical content | Preserves provenance and supports correction | ✓ Good — extended cleanly to ChangeSet origin protection in v1.1 |
| Simplified append-only revision log | Meets history/revert needs without Git-like graph versioning | ✓ Good — extended cleanly to ChangeSet apply/revert |
| Ten allowlisted typed retrieval tools, no raw Cypher to LLM | Eliminates the entire text-to-Cypher injection class structurally | ✓ Good — confirmed by prompt-injection test suite and security audit |
| Two-stage ChangeSet propose/confirm, never auto-apply | A human must gate every graph write the assistant suggests | ✓ Good |
| LLM settings moved to browser-only BYOK (08-02) | Closes the global-settings SSRF/cross-user-takeover surface; key never leaves the browser | ✓ Good — `localStorage` key + per-request `X-LLM-*` headers; server endpoint admin-gated |
| Admin role from `ADMIN_EMAILS` at every login (08-03) | Server-derived, re-synced (removals demote next sign-in), dependency-scoped 403 guard | ✓ Good |
| Redis-backed rate limiting via pyrate-limiter (08-05) | Atomic RedisBucket Lua script works across Render workers; tests no-op the limiter | ✓ Good |
| Rebrand `hdgrafcehennemi` → `spoilerless` (REBRAND-01) | Real deployed product name; git history intentionally untouched | ✓ Good |
| Episode Overview default = Variant A, projection_version 1.0.0 (10-01) | Measured A/B evidence (13 nodes in 12–28 target, stability 1.0, procedural labels 0) | ✓ Good — recorded in `docs/decision-logs/phase-10-visualization.md` |
| Centralized `resolve_effective_boundary` (10-02) | One pure fail-closed resolver across graph/projection/expansion/path/search/focus/restoration | ✓ Good |
| Human edge classes replace raw Neo4j relation names (10-02) | Unmapped relationship types fail closed (D-14); raw names only in debug views | ✓ Good |
| Story/Advanced keep the legacy scene for user content (260814-viz) | Custom nodes/edges exist only there, never in projection DTOs; `undefined` prop = leave-projection | ✓ Good — GAP-1 closed, 400 frontend tests |
| Scratch-series + drift-agnostic seed asserts (09-08) | Full backend suite deterministic without touching the live DB | ✓ Good — 11/11 chunks green |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-14 after v1.3 Production Deployment & Access Hardening milestone*
