# Phase 12 CONTEXT — Post-Hardening Remediation, Frontend Modularity & Code Quality

Locked findings and decisions from the 2026-08-20 Thermo-Nuclear Dual Review (`thermo-nuclear-review-subagent`, `thermo-nuclear-code-quality-review-subagent`, and `scout` reconnaissance) conducted across the full-stack codebase.

---

## Scope & Finding Registry

### P0 / Blocker (Must land in Wave 1)

- **THERMO-P0-01 (Privacy Schema Mismatch)**: `_shape_note_response` pops `user_id` on non-owner and anonymous reads (D-02), but `NoteResponse`, `CustomNodeResponse`, and `CustomRelationshipResponse` in `spoilerless/app/domain/user_content.py` have mandatory non-nullable `user_id: Identifier` with no default, triggering a `pydantic.ValidationError` (500 Internal Server Error) on all public/non-owner reads.
- **THERMO-P0-02 (Monolithic `App.tsx` & Render-Phase State Churn)**: `frontend/src/App.tsx` (1,198 lines) exceeds the 1,000-line ceiling, orchestrating 25+ independent `useState` hooks, raw SVG icon trees, drag-resize rails, and DTO merges. It introduces anti-patterns by chaining synchronous `setState` calls during the render phase (`if (graphData && activeGraph !== graphData) setActiveGraph(graphData)` at lines 150-153, 530-542, 560-578), bypassing React 19's unidirectional flow and triggering cascaded re-renders.
- **THERMO-P0-03 (Imperative Cytoscape & React Lifecycle Tangling in `GraphCanvas.tsx`)**: `frontend/src/components/graph/GraphCanvas.tsx` (1,120 lines) uses 14 `useRef` handles and 8 separate `useEffect` hooks to imperatively manage Cytoscape topology reconciliation, layout triggers, focus animations, and pulse glows. It embeds modal dialogs (`CreateNodeDialog`) and relies on a global mutable module singleton (`autoZoomHold.ts`), causing state pollution.
- **THERMO-P0-04 (Mixed Concerns & Synthetic Async Hacks in `DetailPanel.tsx`)**: `frontend/src/components/detail/DetailPanel.tsx` (1,049 lines) embeds 6 tab bodies, `NoteEditor`, `NoteItem`, `CreateRelationshipDialog`, and `CharacterPortrait` in a single file, using an artificial `setTimeout(() => setResolved(true), 0)` hack for synchronous local lookups.

---

### P1 / High (Must land in Wave 1)

- **THERMO-P1-01 (Premature Un-Clamped Boundary Check)**: `user_content.py` (lines 94, 117, 183, 249) and `revisions.py` (lines 90, 125) execute `_require_persisted_boundary(series_id, visible_until_order)` on the raw user query parameter *before* passing it to `resolve_effective_boundary`. This causes anonymous `visible_until_order=999` to return `422` instead of clamping to `1` (returning `200` with boundary 1 data), violating invariant D-01 and generating redundant Cypher roundtrips.
- **THERMO-P1-02 (Frontend Production CSP Cross-Origin Block)**: `frontend/vercel.json` and `frontend/index.html` define `connect-src 'self' https://accounts.google.com;` which blocks cross-origin backend API communication (`https://api.spoilerless.net` or `https://*.onrender.com`) in production deployments.
- **THERMO-P1-03 (Unsupported Note Target Types in `DetailPanel.tsx`)**: `DetailPanel.tsx:518` sets `target_type: 'Character'` when creating notes on non-Character nodes (`Location`, `Event`, `Organization`, `Object`). The backend executes `MATCH (target:Character {id: $target_id})`, finding 0 rows and rejecting with 404/409 errors.
- **THERMO-P1-04 (Lexicographical Episode ID Comparison in `CreateRelationshipDialog`)**: `DetailPanel.tsx:294-297` executes `episodes.reduce((a, b) => a.id > b.id ? a : b)` when picking the default episode. Comparing string UUIDs performs alphabetical comparison instead of comparing numeric `episode_order`, leading to arbitrary episode assignments.
- **THERMO-P1-05 (DTO Drift Between Frontend TypeScript and Backend Pydantic Models)**:
  - `frontend/src/types/graph.ts`: `GraphClaim.relationship_effect` is typed as non-nullable `number`, whereas backend returns `str | float | None`.
  - `frontend/src/types/graph.ts`: `GraphResponse` omits `effective_view_order: number`.
  - `frontend/src/types/graph.ts`: `GraphEvidence.content_hash` is typed as non-nullable `string`, whereas backend allows `None`.
  - `frontend/src/types/chat.ts`: `ChatMessage` omits backend `status: MessageStatus` (`"pending" | "completed" | "failed"`).
  - `frontend/src/types/changeSet.ts`: `ChangeSet` omits `revert_revision_id: Identifier | None`.
- **THERMO-P1-06 (Unescaped Path Parameter in Export API Client)**: `frontend/src/api/export.ts:12` constructs URLs with raw `${seriesId}` without `encodeURIComponent`, risking broken routes if IDs contain special characters.

---

### P2 / Medium (Wave 2)

- **THERMO-P2-01 (TrustedHost Derivation Host Mismatch)**: `_trusted_hosts()` in `spoilerless/app/main.py` derives hostnames from `FRONTEND_ORIGINS` when `ALLOWED_HOSTS` is empty. Incoming HTTP requests carry the backend domain, causing `400 Invalid host header` on Render (`*.onrender.com`) unless `ALLOWED_HOSTS` is explicitly configured.
- **THERMO-P2-02 (Synchronous DNS Resolution Event Loop Stall)**: `_host_is_blocked` in `spoilerless/app/domain/settings.py` invokes `socket.getaddrinfo` synchronously inside a Pydantic field validator on the main thread during `PUT /api/settings/llm` and on every BYOK chat turn with `X-LLM-Base-Url`, risking asyncio event loop stalls on slow/hostile DNS.
- **THERMO-P2-03 (Candidate Ingest 3x Cypher Roundtrip Amplification)**: `_resolve_claim_visibility` in `spoilerless/app/graph/candidates.py` executes 3 separate queries per claim (one for episode, two for subject/object existence), causing 150+ network roundtrips for a batch of 50 claims.
- **THERMO-P2-04 (Rate Limiter Startup Blip Permanent 503 Latch)**: When Redis is temporarily down during FastAPI container startup with `rate_limit_fail_open=False`, `RateLimiter._limiter` remains `None`, and all subsequent requests immediately 503 without attempting lazy reconnect/retry.
- **THERMO-P2-05 (Duplicate Resizable Drag-Rail Implementations)**: `App.tsx:1079-1145` (`EventTimelineRail`) and `components/chat/ChatSheet.tsx:48-90` duplicate identical pointer drag, pointer capture (`setPointerCapture`), jsdom fallback guards, and keyboard arrow step logic.
- **THERMO-P2-06 (Design System Token Drift & Hardcoded Colors)**: `DetailPanel.tsx` hardcodes hex colors (`CLAIM_ACCENT_COLOR = '#D946EF'`, `EVIDENCE_ACCENT_COLOR = '#FB923C'`), `nodeTypes.ts` hardcodes entity colors, and `GraphCanvas.tsx` hardcodes glow/overlay hexes instead of utilizing CSS variables and unified tokens.
- **THERMO-P2-07 (In-Flight Expansion Race Condition)**: `App.tsx:349-405` appends resolved `fetchExpansion` records without verifying if `seriesId` or `confirmedOrder` still matches the current active scene after rapid user navigation.

---

### P3 / Low (Wave 2)

- **THERMO-P3-01 (Redundant Boundary Lookup in Candidates)**: `list_candidates` and `get_candidate` in `api/candidates.py` call `_require_resolved_boundary` right after `resolve_effective_boundary`, executing the identical Cypher boundary query twice.
- **THERMO-P3-02 (Circular Import Workaround in ChangeSetService)**: `ProposeChangesetInput` is defined in `retrieval/pipeline.py` and imported inside the `ChangeSetService.propose_via_tool` method body; it should be located in `domain/change_set.py`.
- **THERMO-P3-03 (Error Code Schema Registration)**: `services/rate_limit.py` emits lowercase `"rate_limit_unavailable"` and `main.py` emits lowercase `"payload_too_large"`. Both must be registered and uppercase (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`) per `core/errors.py`.
- **THERMO-P3-04 (Boundary Resolver Type Hygiene)**: `api/boundary.py` lacks type annotations on `service` and `progress_service` and uses a bespoke `_error` helper instead of `core/errors.py::http_error`.
- **THERMO-P3-05 (Revisions Module Hygiene & Cleanup)**: Duplicate `CustomNodeType` imports in `revisions/__init__.py` and redundant deserialization of `before_snapshot` in `revert_revision_work`.
- **THERMO-P3-06 (Auth Lifecycle Placement)**: `warn_if_open_signup` lives in `services/chat.py` and is imported in `main.py` with defensive try/except; it belongs in `services/auth.py`.
- **THERMO-P3-07 (Keyset Pagination Temporal Type Coercion in Candidates)**: `spoilerless/app/graph/candidates.py` stamps `created_at` as ISO string while Cypher queries bind `after_created_at` as Neo4j `DateTime`, causing potential comparison anomalies.
- **THERMO-P3-08 (Ambiguous Duplicate `X` Icon in PathFinder)**: `frontend/src/components/graph/PathFinder.tsx:162-185` renders two visually identical `X` buttons side-by-side (clear selection vs exit mode) without visual distinction.
- **THERMO-P3-09 (Chat Rate Limit vs Busy Message Conflation)**: `frontend/src/components/chat/ChatPanel.tsx:47` translates `TOO_MANY_REQUESTS` to `'busy'` ("assistant is still answering"), confusing rate limits with concurrency locks.
- **THERMO-P3-10 (Accessibility Focus & Scroll Overhauls)**: `SeriesDashboard.tsx` lacks `scrollIntoView` during keyboard navigation; `DetailPanel` and `RevisionHistoryPanel` lose focus to `document.body` after note/revision deletion.

---

## Action Matrix

| Priority | Identifier | Area | Description | Target File(s) | Impact |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **P0** | THERMO-P0-01 | Backend Domain | Make `user_id: Identifier \| None = None` on user content response models. | `domain/user_content.py` | Fixes 500 ValidationError on anonymous & public reads. |
| **P0** | THERMO-P0-02 | Frontend Arch | Decompose `App.tsx` into `useWorkspaceScene` and `useWorkspaceNavigation`. | `App.tsx`, `hooks/useWorkspaceScene.ts` | Eliminates 1,200-line god-module & render-phase state mutations. |
| **P0** | THERMO-P0-03 | Frontend Graph | Decompose `GraphCanvas.tsx` into Cytoscape hooks; extract `CreateNodeDialog`. | `GraphCanvas.tsx`, `useCytoscapeBridge.ts` | Reduces 1,120-line file to ~350 lines; isolates canvas DOM lifecycle. |
| **P0** | THERMO-P0-04 | Frontend Detail | Decompose `DetailPanel.tsx` into atomic tabs & dialog components. | `DetailPanel.tsx`, `tabs/*.tsx` | Reduces 1,049-line file to ~250 lines; deletes artificial timeout hacks. |
| **P1** | THERMO-P1-01 | Backend API | Remove raw `_require_persisted_boundary` checks before boundary clamping. | `api/user_content.py`, `api/revisions.py` | Ensures `visible_until_order=999` clamps to order 1 with 200 OK. |
| **P1** | THERMO-P1-02 | Infrastructure | Add backend domains to `connect-src` in production CSP headers. | `vercel.json`, `index.html` | Prevents browser CSP from blocking production API requests. |
| **P1** | THERMO-P1-03 | Frontend UX | Support multi-type note targets or constrain UI creation affordances. | `DetailPanel.tsx`, `user_content.py` | Eliminates 404 errors when attaching notes to Location/Event nodes. |
| **P1** | THERMO-P1-04 | Frontend UX | Compare `episode_order` numerically in `CreateRelationshipDialog`. | `DetailPanel.tsx`, `dialogs/*.tsx` | Ensures correct latest-episode selection on new relationships. |
| **P1** | THERMO-P1-05 | Contracts | Synchronize TypeScript interfaces with backend Pydantic models. | `types/graph.ts`, `types/chat.ts` | Eliminates runtime undefined/null type crashes in client logic. |
| **P1** | THERMO-P1-06 | Frontend API | URL-encode `seriesId` in `export.ts`. | `api/export.ts` | Prevents route resolution errors on custom series identifiers. |
| **P2** | THERMO-P2-01 | Backend Infra | Add `*.onrender.com` to `TrustedHostMiddleware` fallback allowlist. | `main.py` | Prevents 400 Invalid Host Header on Render deployments. |
| **P2** | THERMO-P2-02 | Backend Security | Bound SSRF DNS resolution to prevent event loop stalls. | `domain/settings.py` | Prevents slow/hostile DNS from blocking FastAPI event loop. |
| **P2** | THERMO-P2-03 | Backend Graph | Consolidate candidate visibility pre-pass query into a single roundtrip. | `graph/candidates.py` | Eliminates 3x Cypher query amplification on claim ingestion. |
| **P2** | THERMO-P2-04 | Backend Cache | Implement lazy reconnection in `RateLimiter`. | `services/rate_limit.py` | Prevents permanent 503 lockouts on startup Redis blips. |
| **P2** | THERMO-P2-05 | Frontend Layout | Extract unified `ResizableRail.tsx` primitive. | `components/layout/ResizableRail.tsx` | Eliminates duplicated pointer capture and drag resize logic. |
| **P2** | THERMO-P2-06 | Design System | Centralize design tokens in `graphTokens.ts` and CSS `@theme`. | `tokens/graphTokens.ts`, `index.css` | Eliminates hardcoded hex drift across themes. |
| **P2** | THERMO-P2-07 | Frontend State | Guard in-flight expansion responses against scene switches. | `useWorkspaceScene.ts` | Prevents cross-episode graph node contamination. |
| **P3** | THERMO-P3-01..10 | Polish & Cleanup | Clean up imports, error codes, pagination types, UI icons, and focus. | Multiple files | Enhances codebase hygiene, accessibility, and error clarity. |

---

## Plan Decomposition

- **Plan 12-01 (Wave 1)**: `12-01-PLAN.md` — Privacy & Response Schema Alignment (THERMO-P0-01).
- **Plan 12-02 (Wave 1)**: `12-02-PLAN.md` — Boundary Verification Simplification, Invariant Enforcement & Type Hygiene (THERMO-P1-01, THERMO-P3-01, THERMO-P3-04).
- **Plan 12-03 (Wave 2)**: `12-03-PLAN.md` — Candidate Ingest Cypher Query Consolidation & Pagination Temporal Coercion (THERMO-P2-03, THERMO-P3-07).
- **Plan 12-04 (Wave 1)**: `12-04-PLAN.md` — Production Infrastructure, CSP & TrustedHost Hardening (THERMO-P1-02, THERMO-P2-01).
- **Plan 12-05 (Wave 2)**: `12-05-PLAN.md` — Async Event Loop Protection, Rate Limiter Resilience & Error Code Alignment (THERMO-P2-02, THERMO-P2-04, THERMO-P3-03).
- **Plan 12-06 (Wave 2)**: `12-06-PLAN.md` — Domain & Architectural Layering Cleanup (THERMO-P3-02, THERMO-P3-05, THERMO-P3-06).
- **Plan 12-07 (Wave 1)**: `12-07-PLAN.md` — Frontend Bug Fixes, UI/UX Edge Cases & API Contract Alignment (THERMO-P1-03, THERMO-P1-04, THERMO-P1-05, THERMO-P1-06, THERMO-P3-08, THERMO-P3-09, THERMO-P3-10).
- **Plan 12-08 (Wave 2)**: `12-08-PLAN.md` — Frontend Architectural Decomposition & 1,000-Line Ceiling Elimination (THERMO-P0-02, THERMO-P0-03, THERMO-P0-04, THERMO-P2-05, THERMO-P2-07).
- **Plan 12-09 (Wave 2)**: `12-09-PLAN.md` — Design System Tokens, Theme Harmonization & UI/UX Polish (THERMO-P2-06).

---

## Constraints & Project Rules

- Minimal-scope literal fixes. Match existing architecture (FastAPI, StrictModel Pydantic, React 19 hooks, Cytoscape non-destructive reconciler).
- Tests: Use scratch series + teardown, never touch `series_dexter` or real dev user rows (`ae8a41b7-...`).
- Vitest tests: All 44 test suites (404+ tests) must remain green with zero regressions.
- No drive-by refactorings outside the scoped plans.
