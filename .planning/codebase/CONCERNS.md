---
last_mapped: 2026-08-26
focus: concerns
last_mapped_commit: 0b74a325d0884faa06fda5e7f257fb91c4f6a523
---
<!-- refreshed: 2026-08-26 -->
# Codebase Concerns

**Analysis Date:** 2026-08-26

Severity follows repository impact: High means a security breach, data loss, crash, or deployment blocker; Medium means a plausible load, correctness, or maintenance failure; Low means contained debt or a non-blocking edge case. Documented future scope is identified separately from defects.

## Technical Debt

### 1.1 Monolithic God-Files in Frontend and Backend

**Files:** `frontend/src/App.tsx`, `frontend/src/components/graph/GraphCanvas.tsx`, `frontend/src/components/detail/DetailPanel.tsx`, `spoilerless/app/services/visualization.py`, `spoilerless/app/revisions/__init__.py`

**Problem (historical):** Monolithic files exceeding 700–1,100+ lines created cognitive overload, mixed concerns (e.g. layout lifecycle + render-phase state mutations), and made changes error-prone.

**Status:** RESOLVED in Phase 12 (THERMO-P0-02, THERMO-P0-03, THERMO-P0-04, THERMO-P3-02, THERMO-P3-05).
- `frontend/src/App.tsx` decomposed from ~900 lines to 291 lines; extracted `useWorkspaceScene.ts` (217 lines), `useWorkspaceNavigation.ts` (50 lines), `layout/AppIcons.tsx` (74 lines), and `layout/ResizableRail.tsx` (143 lines).
- `frontend/src/components/graph/GraphCanvas.tsx` decomposed from ~700 lines to 426 lines; extracted `useCytoscapeLayout.ts` (197 lines) and `dialogs/CreateCustomNodeDialog.tsx` (130 lines).
- `frontend/src/components/detail/DetailPanel.tsx` decomposed from ~750 lines to 180 lines; extracted `tabs/OverviewTab.tsx` (152 lines), `tabs/ClaimsTab.tsx` (49 lines), `tabs/EvidenceTab.tsx` (45 lines), `tabs/NotesTab.tsx` (235 lines), `CharacterPortrait.tsx` (78 lines), and `dialogs/CreateRelationshipDialog.tsx` (167 lines).
- Monolithic `spoilerless/app/services/visualization.py` (1,173 lines) decomposed into package `spoilerless/app/services/visualization/` (8 focused modules).
- Monolithic `spoilerless/app/revisions/__init__.py` (341 lines) split into `repository.py`, `service.py`, and clean facade `__init__.py`.

### 1.2 Response Schema Mismatch on Privacy-Scrubbed Reads

**Files:** `spoilerless/app/domain/user_content.py`, `spoilerless/app/api/user_content.py`, `spoilerless/tests/test_user_content_api.py`

**Problem (historical):** Non-owner and anonymous reads stripped `user_id` from user content responses (`NoteResponse`, `CustomNodeResponse`, `CustomRelationshipResponse`), but the Pydantic domain models declared `user_id: str` without `Optional`, causing 500 Pydantic `ValidationError` crashes on safe privacy-scrubbed reads.

**Status:** RESOLVED in Phase 12 (THERMO-P0-01). `user_id: Optional[str] = None` declared on all user content response models; verified green with regression tests in `test_user_content_api.py`.

### 1.3 Candidate Ingest Cypher Query Amplification

**Files:** `spoilerless/app/graph/candidates.py`, `spoilerless/app/api/candidates.py`

**Problem (historical):** Ingesting candidate claims issued separate sequential Cypher roundtrips per claim to verify node existence and episode boundaries, creating a 3x query amplification overhead.

**Status:** RESOLVED in Phase 12 (THERMO-P2-03). Consolidated into a single Cypher query per claim roundtrip that validates subject, object, and episode visibility in one atomic execution.

### 1.4 Integration Tests Share the Application's Live Neo4j State

**Files:** `spoilerless/tests/conftest.py`, `scripts/run_phase10_backend_tests.py`

**Evidence:** Default `NEO4J_URI=bolt://127.0.0.1:7687` targets the same DB as local app use; `bootstrap_scratch_series(SCRATCH, (1,2,3))` creates an isolated `Series` + `Episodes` that seed audit allows.

**Problem:** Test isolation depends on collision-resistant IDs and explicit teardown.

**Risk:** Low-to-Medium when running ad-hoc suites against shared instances.

**Status:** RESOLVED for full CI/local suite runs via `scripts/run_phase10_backend_tests.py` (provisions an ephemeral, uniquely-named Neo4j container and tears down on completion). Scratch-series helper pattern (`bootstrap_scratch_series`/`teardown_scratch_series`) protects ad-hoc runs.

### 1.5 Schema Evolution is Bootstrap-Driven Rather Than Migration-Driven

**Files:** `spoilerless/app/graph/seed.py`, `spoilerless/app/graph/setup.py`

**Evidence:** No ordered migration framework directory; `setup.py` and `seed.py` execute idempotent setup and schema constraint creation.

**Problem:** Schema updates and data migrations must be idempotent scripts rather than incremental versioned files.

**Risk:** Low (for current single-series architecture).

**Status:** ACKNOWLEDGED ARCHITECTURAL CHOICE. Setup scripts are strictly idempotent and verified via `test_seed_idempotency.py`.

## Security & Reliability

### 2.1 SSRF DNS Event Loop Blocking

**Files:** `spoilerless/app/domain/settings.py`

**Problem (historical):** `_validate_base_url` performed asynchronous DNS lookup for SSRF IP checks without a hard deadline. Slow or uncooperative DNS servers could stall the FastAPI asyncio event loop.

**Status:** RESOLVED in Phase 12 (THERMO-P2-02). DNS resolution is wrapped with `asyncio.wait_for(..., timeout=1.0)`.

### 2.2 Rate Limiter Startup Resilience

**Files:** `spoilerless/app/services/rate_limit.py`, `spoilerless/tests/test_rate_limit.py`

**Problem (historical):** If Redis was temporarily unavailable during FastAPI startup, `RateLimiter` remained permanently disabled or crashed the service, requiring a manual pod restart.

**Status:** RESOLVED in Phase 12 (THERMO-P2-04, THERMO-P3-03). Implemented lazy re-initialization on subsequent requests when Redis connectivity is restored; registered uppercase error code `RATE_LIMIT_UNAVAILABLE`.

### 2.3 CSP connect-src and TrustedHost for Production Render Origins

**Files:** `frontend/vercel.json`, `frontend/index.html`, `spoilerless/app/main.py`

**Problem (historical):** Production CSP policy lacked `https://api.spoilerless.net` and `https://*.onrender.com` in `connect-src`, causing browser connection rejections on direct backend communication. Render backend domains also risked 400 Bad Request from `TrustedHostMiddleware` in fallback mode.

**Status:** RESOLVED in Phase 12 (THERMO-P1-02, THERMO-P2-01). CSP updated in both `vercel.json` and `index.html`; `_trusted_hosts()` in `main.py` includes regex pattern for Render wildcard subdomains.

### 2.4 Premature Un-Clamped Boundary Checks

**Files:** `spoilerless/app/api/user_content.py`, `spoilerless/app/api/revisions.py`, `spoilerless/app/api/boundary.py`

**Problem (historical):** Routes executed raw persistence checks against un-clamped caller-supplied `visible_until_order` parameters before invoking `resolve_effective_boundary`, resulting in premature 422 errors instead of proper clamping.

**Status:** RESOLVED in Phase 12 (THERMO-P1-01). All spoiler-sensitive routes delegate boundary resolution directly to `resolve_effective_boundary` / `require_boundary`, clamping anonymous requests to episode 1.

## Map Delta (2026-08-26 vs 2026-08-20 / 5ad6867)

- **Resolved Frontend God-Components:** `App.tsx`, `GraphCanvas.tsx`, and `DetailPanel.tsx` decomposed into modular components, custom hooks, and layout primitives under 450 lines.
- **Resolved Backend God-Files:** `services/visualization.py` decomposed into 8-module package; `revisions/__init__.py` split into repository and service; `GraphService` facade added.
- **Resolved Privacy Response Mismatch:** Added `user_id: Optional[str] = None` across user content response DTOs.
- **Resolved SSRF DNS Timeout:** Added 1.0s timeout on DNS lookups.
- **Resolved RateLimiter Outage Recovery:** Added lazy re-initialization and uppercase error codes.
- **Resolved Ingestion Cypher Amplification:** Consolidated candidate ingest checks to single Cypher query per claim.

---

*Concerns audit: 2026-08-26*
