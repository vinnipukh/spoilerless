# HD Graf Cehennemi (Spoilerless)

## What This Is

A spoiler-safe narrative knowledge graph for TV series with a grounded conversational agent, shipped as a live zero-cost hosted product. The app covers Dexter Season 1 with an enriched episode-101 knowledge base, runs on Render + Vercel + Neo4j AuraDB Free + Upstash Redis, and lets an authenticated user explore source-backed narrative knowledge through four coordinated views (Story, Characters, Evidence, Advanced), control the visible episode boundary, add personal knowledge, inspect/revert revisions, ask questions answered only from graph data visible up to their watch progress (with clickable citations, graph highlighting, and a GraphRAG Answer Graph), export knowledge, and safely propose graph edits through a typed confirm-before-apply ChangeSet flow.

## Core Value

Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress, because filtering occurs in the backend before data reaches the frontend, the LLM, or any tool call. No raw Cypher ever reaches the model, and no graph write happens without explicit human confirmation. One shared fail-closed boundary resolver (`resolve_effective_boundary` / `require_boundary`) is the single enforcement seam across graph reads, projections, expansion, path/search, GraphRAG focus, and saved restoration.

## Current State (v1.5 Post-Hardening Remediation & Code Quality shipped 2026-08-26)

- **Live deployment at $0:** Vercel (frontend) + Render free web service (backend, `spoilerless.app.main:app`) + Neo4j AuraDB Free (`03a8623b`) + Upstash Redis (`darling-rat-221809`), custom domain, `docs/DEPLOYMENT.md` with rollback procedure.
- **Access control & privacy:** Google OAuth with operator email allowlist (`ALLOWED_EMAILS`), no dev-auth backdoor, admin role derived server-side from `ADMIN_EMAILS` at every login gating candidate review / ChangeSet confirm / server LLM settings; BYOK LLM chat (browser-held key in `localStorage`, per-request `X-LLM-*` headers, never persisted server-side); Secure/SameSite cookies, fail-closed CSRF Origin/Referer, Redis-backed multi-worker rate limits with lazy re-init (login/chat/writes → 429 / 503 `RATE_LIMIT_UNAVAILABLE`); privacy-scrubbed reads safely return `user_id: null` on `NoteResponse` / `CustomNodeResponse` / `CustomRelationshipResponse`.
- **Spoiler-safe visualization & modular architecture:** library-neutral DTO + 6 projections (`episode_overview`, `character_network`, `plot_threads`, `investigation`, `full`, `graphrag_focus`), cache keys carry series/order/view/projection_version/epoch/scope/focus-SHA; Episode Overview Variant A default; server-allowlisted semantic expansion (7 keys, undo/collapse/reset); GraphRAG Answer Graph + Evidence Chain with scene restoration; decomposed frontend architecture (`App.tsx` 291 lines, `GraphCanvas.tsx` 426 lines, `DetailPanel.tsx` 180 lines, `useWorkspaceScene`, `useCytoscapeLayout`, `sceneElements.ts`, `graphTokens.ts`, `ResizableRail`, `AppIcons`); decomposed backend package `spoilerless/app/services/visualization/` (8 modules) and `spoilerless/app/revisions/` (`service.py`, `repository.py`).
- **Audit-remediated core & security-hardened:** all 45+ `docs/PROBLEMS.md` findings resolved, plus 10 new features and FEAT-11 touches (backlinks, hover cards, ⌘K switcher, filters, node properties); single fail-closed `resolve_effective_boundary` (`spoilerless/app/api/boundary.py`) gating every spoiler-sensitive read (anonymous fixed at 1, no-record fail-closed, clamped `min(requested, view, watched)` + persisted-episode 422); candidate ingest server-derives `visible_from_order` with single-roundtrip Cypher checks, rate-limiting, and cache invalidation; trusted proxy + fail-closed rate limiting (`render.yaml --proxy-headers --forwarded-allow-ips` + `spoilerless/app/services/rate_limit.py`); SSRF-hardened `base_url` with 1.0s DNS timeout; LLM cost caps — process-wide `asyncio.Semaphore(4)` + per-round tool-call cap 8; `BodySizeLimitMiddleware` 413 `PAYLOAD_TOO_LARGE` (1 MiB) + docs-off in prod + `TrustedHostMiddleware` with Render wildcard support; CSP/security headers on API and Vercel shell (`https://api.spoilerless.net`, `https://*.onrender.com`); log sanitization; delimiter neutralization; bounded viz cache (`FOCUS_SET_CAP=64`); revert allowlist + ownership fail-closed.
- **Rebranded:** package dirs, pyproject, docker-compose, services, `/health` `service` field, UI title, and docs renamed `hdgrafcehennemi` → `spoilerless` (git history intentionally untouched).
- ~23,600+ LOC across `spoilerless/app` and `frontend/src`. Python 3.13 + FastAPI + Pydantic v2 + Neo4j async driver; React 19 + TypeScript + Vite + Cytoscape.js; `uv` for Python packaging. Backend 53 test modules (23,400+ lines); frontend 438+ tests across 29 test files.

## Next Milestone Goals (candidates, not yet scoped)

- Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement (OPS-01 remains a minimal PR gate)
- Full observability: centralized log aggregation, metrics dashboards, incident/rollback runbook automation (OPS-03 is structured app logging only)
- Person / ACTED_AS / APPEARS_IN actor model; reviews, ratings, trivia, recommendations; automated external ingestion
- Complete the 2026-08-04 Dexter S01E01 enrichment live-completion (AuraDB seed + DB-backed tests + browser acceptance)

## Previous Milestones

<details>
<summary>v1.4 Security Hardening (shipped 2026-08-20) — Phase 11</summary>

**Goal:** Close all P0/P1 security findings from the 2026-08-15 adversarial audit.
**Delivered:** Single fail-closed boundary resolver (`boundary.py`), candidate ingest hardening, trusted proxy + fail-closed rate limiting, SSRF base_url blocking, LLM cost caps, body-size middleware (413), docs disabled in production, CSP on Vercel shell, log sanitization, delimiter neutralization, bounded focus cache, revert allowlist.
</details>

<details>
<summary>v1.3 Production Deployment & Access Hardening (shipped 2026-08-14) — Phases 8–10</summary>

**Goal:** Production deployment on Render/Vercel/AuraDB, full audit remediation, rebrand, deterministic test suites, narrative visualization redesign.
**Delivered:** Live zero-cost hosting, Google OAuth with email allowlist, admin role, BYOK chat, 10 new features, 6 visualization projections, Answer Graph, semantic expansion.
</details>

<details>
<summary>v1.2 Spoiler-Safety Hardening (shipped 2026-08-03) — Phase 7</summary>

**Goal:** Separate watched progress from temporary view boundary, centralize visibility policy, close indirect leak channels.
</details>

<details>
<summary>v1.1 MVP (shipped 2026-08-02, supersedes v1.0) — Phases 1–6</summary>

**Goal:** Graph exploration, user notes/custom nodes, revisions with revert, candidate review UI, GraphRAG chat with ChangeSet editing.
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
- ✓ Extraction-preparation contracts, candidate review workflow, source-connector interface — v1.0
- ✓ Google OAuth authentication (single real-user model) — v1.0
- ✓ Spoiler-safe GraphRAG chat: allowlisted retrieval tools, LLM provider abstraction, citation-validated grounded answers — v1.1
- ✓ Typed ChangeSet propose/confirm/revert graph-editing flow with auditable Revision — v1.1
- ✓ Email allowlist sign-in; dev-auth backdoor removed; admin role on candidate review/ChangeSet confirm/LLM settings — v1.3 (AUTH-01..04)
- ✓ BYOK LLM chat (browser-held key, per-request headers, never persisted/logged server-side) — v1.3 (AI-01..03)
- ✓ Production cookie/CORS/CSRF hardening, Redis-backed multi-worker rate limiting (429s) — v1.3 (SEC-01..03)
- ✓ AuraDB Free + Upstash Redis cache with write invalidation + Render/Vercel deployment — v1.3 (INFRA-01..05)
- ✓ GitHub Actions CI gate, external `/health` uptime check, structured exception logging — v1.3 (OPS-01..03)
- ✓ All PROBLEMS.md audit findings resolved; deterministic test suites; lint 0 errors — v1.3 (PROB-01..32)
- ✓ 10 new features + FEAT-11 second-brain touches; rebrand to Spoilerless — v1.3 (FEAT-01..11, REBRAND-01)
- ✓ Spoiler-safe narrative visualization: DTO, 6 projections, four-view hierarchy, semantic expansion, Answer Graph, benchmarks — v1.3 (VIZ-01..10)
- ✓ Single fail-closed boundary resolver across all reads — Phase 11 (SEC-01..02)
- ✓ Candidate ingest hardening — server-derived visible_from_order + existence + rate-limit + invalidation + pagination — Phase 11 (SEC-03)
- ✓ Trusted proxy + per-IP limits + fail-closed rate limiting — Phase 11 (SEC-04..05)
- ✓ LLM cost controls + SSRF hardening — Phase 11 (SEC-06..07)
- ✓ Request body-size limit 413 + docs off in prod + CSP on Vercel + log sanitization — Phase 11 (SEC-08..11)
- ✓ P1 hardening: delimiter neutralization + bounded focus cache (64) + revert allowlist — Phase 11 (SEC-12)
- ✓ Response schema nullability alignment (`user_id: Optional[str] = None` on NoteResponse/CustomNodeResponse/CustomRelationshipResponse) — Phase 12 (THERMO-P0-01)
- ✓ Monolithic frontend decomposition below 450 lines (`App.tsx`, `GraphCanvas.tsx`, `DetailPanel.tsx`, `useWorkspaceScene`, `useCytoscapeLayout`, `ResizableRail`, `AppIcons`, tabs, dialogs) — Phase 12 (THERMO-P0-02..04, THERMO-P2-05, THERMO-P2-07)
- ✓ Frontend UI/UX fixes: numeric episode ordering, note attachments to all custom types, distinct PathFinder icon, chat error differentiation, accessibility scroll/focus — Phase 12 (THERMO-P1-03..06, THERMO-P3-08..10)
- ✓ Simplified boundary verification and anonymous clamp across all routes (`require_boundary`, clamp to 1) — Phase 12 (THERMO-P1-01, THERMO-P3-01)
- ✓ Candidate ingest Cypher consolidation into single roundtrip — Phase 12 (THERMO-P2-03, THERMO-P3-07)
- ✓ Production CSP connect-src and TrustedHost for Render domains — Phase 12 (THERMO-P1-02, THERMO-P2-01)
- ✓ SSRF DNS timeout (1.0s) + RateLimiter lazy re-initialization + uppercase error codes — Phase 12 (THERMO-P2-02, THERMO-P2-04, THERMO-P3-03)
- ✓ Design system token centralization (`graphTokens.ts`) and 44px touch targets — Phase 12 (THERMO-P2-06)
- ✓ Backend modularization: `visualization/` package decomposition, `revisions/` split, `GraphService` facade — Phase 12 (THERMO-P3-02, THERMO-P3-05, THERMO-P3-06)

### Active

- [ ] Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement
- [ ] Full observability: centralized log aggregation, metrics dashboards, tracing
- [ ] Person / ACTED_AS / APPEARS_IN actor model (carried from v1.1/v1.2)
- [ ] Reviews, ratings, trivia, recommendations (carried from v1.1/v1.2)
- [ ] Automated ingestion/extraction from external sources (OpenSubtitles, scripts, Fandom/IMDb/news)
- [ ] Dexter S01E01 enrichment live-completion: AuraDB seed + DB-backed tests + browser acceptance

### Out of Scope

- Multi-region or high-availability hosting; paid tier / usage-based billing — this product targets $0 free-tier hosting
- Mobile native apps — FEAT-10 is responsive web, not a native app
- Migrating off Neo4j, FastAPI, or React/Vite — hosting changes only, no rewrite
- Versioned Neo4j schema migrations — seed-as-schema continues

## Constraints

- **Spoiler safety:** every exposed graph element carries `visible_from_order`; one fail-closed resolver (`resolve_effective_boundary` / `require_boundary`) gates the backend before data reaches the frontend, the LLM, or any tool call.
- **No raw Cypher to the LLM:** the model's only actions are typed, allowlisted retrieval tool calls and typed ChangeSet proposals.
- **Writes require human confirmation:** the model may only *propose* a ChangeSet; a human must explicitly confirm before any transaction touches the graph.
- **Provenance:** automatic/candidate claims require EvidenceFragments with source, episode, locator, retrieval metadata, and content hash where possible.
- **Separation:** canonical, candidate/automatic, and user-created content are represented and displayed distinctly.
- **History:** edits and reverts append revisions; history is not destroyed.
- **Maintainability:** component files must remain under a 450-line ceiling; business and state transitions belong in custom hooks and focused services.
- **Stack:** Neo4j (AuraDB Free in prod, Docker for local), FastAPI/Pydantic, React 19 + TypeScript + Vite + Cytoscape.js; Python packaging through `uv`; Redis (Upstash) for cache + rate limits.
- **Zero-cost hosting:** free tiers only (Render, Vercel, AuraDB Free, Upstash).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Root `ROADMAP.md` defined Prototype v0 scope | Prevent planning documents from narrowing the canonical demo | ✓ Good — v0 shipped in full |
| Neo4j as graph source of truth | Graph-native storage fits connected narrative data | ✓ Good |
| Backend/data-access spoiler filtering | Downstream clients (frontend, LLM) must never receive future data | ✓ Good — zero leakage across all versions |
| Evidence-backed atomic claims | Users can understand why knowledge exists | ✓ Good |
| Separate user/candidate/canonical content | Preserves provenance and supports correction | ✓ Good |
| Simplified append-only revision log | Meets history/revert needs without Git-like graph versioning | ✓ Good |
| Ten allowlisted typed retrieval tools, no raw Cypher to LLM | Eliminates the entire text-to-Cypher injection class structurally | ✓ Good |
| Two-stage ChangeSet propose/confirm, never auto-apply | A human must gate every graph write the assistant suggests | ✓ Good |
| LLM settings moved to browser-only BYOK (08-02) | Closes global-settings SSRF/cross-user-takeover surface | ✓ Good |
| Admin role from `ADMIN_EMAILS` at every login (08-03) | Server-derived, re-synced, dependency-scoped 403 guard | ✓ Good |
| Redis-backed rate limiting via pyrate-limiter (08-05) | Atomic RedisBucket Lua script works across Render workers | ✓ Good |
| Rebrand `hdgrafcehennemi` → `spoilerless` (REBRAND-01) | Real deployed product name; git history untouched | ✓ Good |
| Centralized `resolve_effective_boundary` as single fail-closed seam (11-01/11-02) | Every spoiler-sensitive read must be server-clamped | ✓ Good |
| Fail-closed rate limiting + trusted proxy (11-04) | Site-global login bucket and fail-open outage are product-fatal | ✓ Good |
| SSRF-hardened `base_url` + LLM cost caps (11-05) | Shared stored `base_url` is an SSRF primitive; unbounded rounds farm wallet | ✓ Good |
| Body-size + docs-off + log sanitization + delimiter + bounded cache (11-06..11-08) | Bound attack surface at ASGI layer | ✓ Good |
| Privacy-scrubbed response nullability (12-01) | Stripping `user_id` on non-owner reads must not trigger 500 Pydantic validation error | ✓ Good — `user_id: Optional[str] = None` on Note/CustomNode/CustomRelationship |
| Require boundary dependency & anonymous clamp (12-02) | Prevent premature 422 persistence checks on un-clamped caller inputs | ✓ Good — `require_boundary` dependency; anonymous clamped to 1 |
| Single-query candidate ingest Cypher (12-03) | Eliminate 3x query amplification overhead per candidate claim | ✓ Good — consolidated existence & boundary check in single Cypher roundtrip |
| Production CSP & TrustedHost wildcard support (12-04) | Support Render preview and production domains without CSP connection blocks | ✓ Good — `https://api.spoilerless.net` and `https://*.onrender.com` in connect-src |
| SSRF 1.0s DNS timeout & RateLimiter lazy re-init (12-05) | Prevent event-loop stalls from DNS and enable recovery from startup Redis outages | ✓ Good — `asyncio.wait_for` 1.0s, lazy re-init in RateLimiter, uppercase error codes |
| Frontend god-component decomposition below 450 lines (12-08) | Eliminate cognitive debt, render-phase state mutations, and improve testability | ✓ Good — `App.tsx` 291 lines, `GraphCanvas.tsx` 426 lines, `DetailPanel.tsx` 180 lines |
| Centralized design tokens (12-09) | Eliminate hardcoded hex sprawl and standardize 44px touch targets | ✓ Good — `frontend/src/lib/tokens/graphTokens.ts` |
| Modular visualization service package (12-10..12-15) | Replace 1,173-line monolith with 8 focused modules | ✓ Good — `spoilerless/app/services/visualization/` package |

---
*Last updated: 2026-08-26 after v1.5 Post-Hardening Remediation & Code Quality (Phase 12) milestone — 15/15 plans complete and verified.*
