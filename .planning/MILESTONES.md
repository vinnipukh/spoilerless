# Milestones

## v1.5 Post-Hardening Remediation & Code Quality (Shipped: 2026-08-26)

**Phases completed:** 1 phase (Phase 12), 15 plans, 26 tasks

**Key accomplishments:**

- Frontend god-component decomposition: `App.tsx` reduced from ~900 lines to 291 lines; `GraphCanvas.tsx` reduced from ~700 lines to 426 lines; `DetailPanel.tsx` reduced from ~750 lines to 180 lines. Extracted `useWorkspaceScene`, `useWorkspaceNavigation`, `useCytoscapeLayout`, `ResizableRail`, `AppIcons`, tabs (`OverviewTab`, `ClaimsTab`, `EvidenceTab`, `NotesTab`), and dialogs (`CreateCustomNodeDialog`, `CreateRelationshipDialog`).
- Backend modularity & decomposition: Monolithic `services/visualization.py` (1,173 lines) decomposed into 8-module package `spoilerless/app/services/visualization/`; `revisions/__init__.py` split into `repository.py`, `service.py`, and `__init__.py`; centralized `GraphService` facade for visible graph reads and cache invalidation.
- Response schema nullability alignment (THERMO-P0-01): `user_id: Optional[str] = None` on `NoteResponse`, `CustomNodeResponse`, `CustomRelationshipResponse` allowing privacy-scrubbed non-owner reads to return 200 without Pydantic validation errors.
- Boundary enforcement simplification: `require_boundary` dependency in `api/boundary.py`; anonymous requests with `visible_until_order=999` clamp to episode 1 across all routes without premature 422 errors.
- Candidate ingest Cypher consolidation: Single Cypher roundtrip per claim for subject/object/episode visibility checks, eliminating 3x query amplification.
- Resilience & Security: SSRF DNS resolution bounded with 1.0s timeout; `RateLimiter` lazy re-initialization on startup Redis outages with registered uppercase error codes (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`); production CSP and `TrustedHost` support for `https://api.spoilerless.net` and `https://*.onrender.com`.
- Design system & UI/UX harmonization: Centralized design tokens in `graphTokens.ts`, 44px touch targets, numeric episode ordering in relationship dialog, note attachment to all custom node types, distinct PathFinder clear icon, chat rate-limit error differentiation.

**Closeout type:** verified_closeout (15/15 plans executed and verified, all THERMO requirements checked)

---

## v1.4 Security Hardening (Shipped: 2026-08-20)

**Phases completed:** 1 phase (Phase 11), 8 plans, 14 tasks

**Key accomplishments:**

- Single fail-closed spoiler boundary resolver: `spoilerless/app/api/boundary.py::resolve_effective_boundary` gating every spoiler-sensitive read surface.
- Candidate ingest hardening: server-derived visibility, subject/object/episode existence verification, rate limiting, and series cache invalidation.
- Trusted proxy & fail-closed rate limiting: Render CIDR proxy header forwarding, fail-closed 503 on Redis outage in production.
- SSRF hardening: blocklist for loopback, private, link-local, and metadata addresses on both BYOK and stored provider URLs.
- LLM cost controls: process-wide semaphore (4 concurrent generations) + per-round tool-call cap (8) + changeset operation limits.
- Perimeter hardening: 1 MiB body size limit (413), docs disabled in production, security headers (CSP, HSTS) on Vercel shell, validation log sanitization, delimiter tag neutralization, and bounded visualization cache (`FOCUS_SET_CAP=64`).

**Closeout type:** verified_closeout (8/8 plans verified, all 12 SEC requirements checked)

---

## v1.3 Production Deployment & Access Hardening (Shipped: 2026-08-14)

**Phases completed:** 3 phases (Phases 8–10), 37 plans, 58 tasks

**Key accomplishments:**

- Live zero-cost production deployment (Phase 8): Render + Vercel + AuraDB Free + Upstash Redis, email allowlist, admin role, BYOK LLM chat (browser-held key), hardened cookie/CORS/CSRF/rate-limits (Redis multi-worker 429s), graph-cache invalidation, GitHub Actions CI, UptimeRobot monitoring
- Full audit remediation + rebrand (Phase 9): all 45+ PROBLEMS.md findings resolved, `hdgrafcehennemi` → `spoilerless` rename, 10 new features (search/jump, timeline, reveal highlight, dashboard, export, path finder, full-text search, command palette, shareable snapshots, mobile) + FEAT-11 backlinks/hover/⌘K/filters/properties
- Deterministic test infrastructure (Phase 9): scratch-series isolation + drift-agnostic seed asserts, zombie sweep + CI DB-pollution gate, lint 0 errors, core-module direct tests — suite green without touching the live DB
- Narrative visualization redesign (Phase 10): library-neutral spoiler-safe DTO, 6 projections, four-view hierarchy (Story/Characters/Evidence/Advanced), Episode Overview variants with hard bounds, server-allowlisted semantic expansion (undo/collapse), GraphRAG Answer Graph, benchmark harness (30/50→300/1000)
- GAP-1 wiring closure (`260814-viz`): frontend fetches `character_network`/`investigation`/`graphrag_focus` projections + Expand menu end-to-end — 400 frontend / 130 backend tests green
- Closeout gates: 98/98 coverage audit, 11/11 regression chunks, operator golden-path UAT (12/12 scenarios, 1 BYOK-chat row blocked by zero-cost policy)

**Closeout type:** verified_closeout (all 3 phases verified passed, 75/75 requirements checked)

---

## v1.1 MVP (Shipped: 2026-08-02)

**Phases completed:** 8 phases, 35 plans, 47 tasks (supersedes v1.0 — adds Phase 6: Spoiler-Safe GraphRAG Chat and Graph-Editing Agent)

**Key accomplishments:**

- Async Neo4j backend, ontology-validated deterministic Dexter evidence graph, and fail-closed spoiler-safe API proven across live episode boundaries.
- React/Vite frontend with AppShell, SeriesSelect, EpisodeSelector, ConfirmAdvanceModal, GraphCanvas, and DetailPanel.
- Cytoscape canvas polish, Overview/Claims/Evidence tabs, and StructuralEdgeCard.
- User notes and custom node/relationship creation, distinct from canonical content.
- Append-only revision history with inspect and revert.
- Extraction-preparation contracts, candidate review workflow, source-connector interface.
- Spoiler-safe GraphRAG chat: allowlisted retrieval tools, LLM provider abstraction, citation-validated grounded answers.
- Typed ChangeSet propose/confirm/revert graph-editing flow with auditable Revision logging.

---

## v1.0 Prototype v0 (Shipped: 2026-07-30)

**Phases completed:** 6 phases, 22 plans, 17 tasks

**Key accomplishments:**

- Lifespan-owned async Neo4j backend, ontology-validated deterministic Dexter evidence graph, and fail-closed spoiler-safe API.
- React/Vite frontend layout and Cytoscape graph rendering.
- User notes, revision history, and extraction-preparation contracts.

---
