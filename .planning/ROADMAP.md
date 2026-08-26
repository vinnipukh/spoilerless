# HD Graf Cehennemi (Spoilerless) — Roadmap

## Milestones

- ✅ **v1.0 Prototype v0** — Phases 1–5 (+ 03.1, 05.1 inserted) (shipped 2026-07-30)
- ✅ **v1.1 MVP** — Phases 1–6 (+ 03.1, 05.1 inserted) (shipped 2026-08-02, supersedes v1.0 — adds Phase 6 GraphRAG chat)
- ✅ **v1.2 Spoiler-Safety Hardening** — Phase 7 (shipped 2026-08-03)
- ✅ **v1.3 Production Deployment & Access Hardening** — Phases 8–10 (shipped 2026-08-14)
- ✅ **v1.4 Security Hardening** — Phase 11 (shipped 2026-08-20)
- 🟡 **v1.5 Post-Hardening Remediation & Code Quality** — Phase 12 (in progress)

## Phases

#### Phase 12: Post-Hardening Remediation & Code Quality

**Goal**: Resolve all findings from the 2026-08-20 Thermo-Nuclear Dual Review and reconnaissance: fix the P0 response schema mismatch on privacy-scrubbed reads (`NoteResponse` / `CustomNodeResponse` `user_id` nullability), decompose the monolithic frontend god-components exceeding the 1,000-line maintainability ceiling (`App.tsx`, `GraphCanvas.tsx`, `DetailPanel.tsx`), eliminate render-phase `setState` churn, encapsulate Cytoscape lifecycles, fix frontend UI/UX and API contract bugs (numeric episode ordering in relationship dialog, multi-type note attachments, DTO alignment, PathFinder icons, chat rate limit error differentiation, accessibility scroll/focus), remove premature un-clamped boundary checks in `user_content.py` and `revisions.py`, consolidate candidate ingestion Cypher queries (eliminating 3x query amplification), fix frontend CSP `connect-src` for production backend origins, fix `_trusted_hosts` fallback for Render deployments, bound SSRF DNS resolution to prevent event loop stalls, implement lazy rate limiter reconnect, register uppercase error codes (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`), unify design tokens (`graphTokens.ts`), and clean up domain/architectural layering.
**Depends on**: Phase 11 (shipped)
**Requirements**: THERMO-P0-01, THERMO-P0-02, THERMO-P0-03, THERMO-P0-04, THERMO-P1-01, THERMO-P1-02, THERMO-P1-03, THERMO-P1-04, THERMO-P1-05, THERMO-P1-06, THERMO-P2-01, THERMO-P2-02, THERMO-P2-03, THERMO-P2-04, THERMO-P2-05, THERMO-P2-06, THERMO-P2-07, THERMO-P3-01..10
**Success Criteria** (what must be TRUE):

  1. Anonymous and non-owner reads on `/notes`, `/custom-nodes`, `/custom-relationships` return 200 with `user_id: null` instead of raising 500 Pydantic `ValidationError`.
  2. Monolithic frontend files (`App.tsx`, `GraphCanvas.tsx`, `DetailPanel.tsx`) are decomposed below 350 lines with zero render-phase state mutations, isolated Cytoscape lifecycle hooks, and separate tab/dialog components.
  3. `CreateRelationshipDialog` selects the latest episode by numeric `episode_order`; note creation supports all `CustomNodeType` labels without 404/409 errors; TypeScript interfaces in `frontend/src/types` align 100% with backend Pydantic models.
  4. Anonymous requests passing `visible_until_order=999` across all read routes clamp to episode 1 and return 200 without throwing 422; no route executes un-clamped raw persistence checks before `resolve_effective_boundary`.
  5. Candidate claim visibility resolution runs in a single consolidated Cypher query per claim, eliminating secondary existence query roundtrips while preserving node existence validation.
  6. Frontend CSP `connect-src` in `vercel.json` and `index.html` allows connections to `https://api.spoilerless.net` and `https://*.onrender.com`; `_trusted_hosts()` in `main.py` permits Render backend domains (`*.onrender.com`) in fallback mode without 400 Bad Request.
  7. DNS resolution in SSRF validation is bounded with a timeout preventing asyncio event loop stalls; `RateLimiter` attempts lazy initialization on startup blips; all error codes are registered and uppercase (`RATE_LIMIT_UNAVAILABLE`, `PAYLOAD_TOO_LARGE`).
  8. Design tokens are centralized in `graphTokens.ts` and `index.css` `@theme`, eliminating hardcoded hex sprawl and standardizing 44px touch targets.
  9. `ProposeChangesetInput` lives in `domain/change_set.py` with top-level imports; `warn_if_open_signup` lives in `services/auth.py`; `revisions` module has clean imports and single-pass JSON deserialization.

**Plans**:

- [x] 12-01-PLAN.md — Privacy & Response Schema Alignment (THERMO-P0-01) [Wave 1]
- [x] 12-02-PLAN.md — Boundary Verification Simplification, Invariant Enforcement & Type Hygiene (THERMO-P1-01, THERMO-P3-01, THERMO-P3-04) [Wave 1]
- [x] 12-03-PLAN.md — Candidate Ingest Cypher Query Consolidation & Pagination Temporal Coercion (THERMO-P2-03, THERMO-P3-07) [Wave 2]
- [x] 12-04-PLAN.md — Production Infrastructure, CSP & TrustedHost Hardening (THERMO-P1-02, THERMO-P2-01) [Wave 1]
- [x] 12-05-PLAN.md — Async Event Loop Protection, Rate Limiter Resilience & Error Code Alignment (THERMO-P2-02, THERMO-P2-04, THERMO-P3-03) [Wave 2]
- [ ] 12-06-PLAN.md — Domain & Architectural Layering Cleanup (THERMO-P3-02, THERMO-P3-05, THERMO-P3-06) [Wave 2]
- [x] 12-07-PLAN.md — Frontend Bug Fixes, UI/UX Edge Cases & API Contract Alignment (THERMO-P1-03, THERMO-P1-04, THERMO-P1-05, THERMO-P1-06, THERMO-P3-08, THERMO-P3-09, THERMO-P3-10) [Wave 1]
- [ ] 12-08-PLAN.md — Frontend Architectural Decomposition & 1,000-Line Ceiling Elimination (THERMO-P0-02, THERMO-P0-03, THERMO-P0-04, THERMO-P2-05, THERMO-P2-07) [Wave 2]
- [ ] 12-09-PLAN.md — Design System Tokens, Theme Harmonization & UI/UX Polish (THERMO-P2-06) [Wave 2]

#### Phase 11: Security Hardening — audit remediation (P0/P1)

**Goal**: Close the P0 (and P1) security findings from the 2026-08-15 adversarial audit (SECURITY_AUDIT.md): make the spoiler boundary fail closed on every read surface, remove the one-request graph-poisoning write, restore per-IP rate limiting behind the Render proxy, make rate limiting fail closed in production, cap LLM cost amplification, block SSRF via LLM provider `base_url`, bound request bodies, hide API docs in production, ship CSP/security headers on the Vercel shell, and stop logging raw submitted values.
**Depends on**: Phase 10 (shipped); SECURITY_AUDIT.md / SECURITY_TEST_PLAN.md (2026-08-15 audit deliverables)
**Requirements**: SEC-01 (boundary fail-closed: SEC-BE-001), SEC-02 (anonymous clamp + auth/persist-validate reads: SEC-BE-002, SEC-ADV-003), SEC-03 (ingest hardening: SEC-BE-003, SEC-ADV-001, SEC-ADV-002), SEC-04 (trusted proxy + per-IP limits: SEC-BE-004/SEC-DOS-003), SEC-05 (fail-closed rate limiting: SEC-DOS-001), SEC-06 (LLM cost controls: SEC-DOS-002), SEC-07 (SSRF hardening: SEC-LLM-001/002), SEC-08 (body-size limit: SEC-DOS-004), SEC-09 (docs off in prod: SEC-INF-003), SEC-10 (CSP on Vercel shell: SEC-FE-001), SEC-11 (log sanitization: SEC-LOG-001), SEC-12 (P1: output guard, cache-key redesign, Max-Age, email_verified, TrustedHost, ingest pagination, revert label allowlist, fail-closed reversion ownership, ChangeSet revert admin gating, frontend series-switch hydration & client header hardening, verification script path portability)
**Success Criteria** (what must be TRUE):

  1. Every spoiler-sensitive read (graph, episodes, candidates, notes, custom-nodes/relationships, revisions, export, visualization, expand, path) resolves the boundary through ONE fail-closed path: anonymous and no-progress-record users get order 1; no client-chosen boundary bypasses it; revisions/candidates responses never expose `before`/`after` snapshots or `user_id` to non-owners.
  2. Candidate ingest derives `visible_from_order` server-side, validates subject/object/episode existence, is rate-limited, and invalidates the series cache; no client-supplied visibility value is persisted.
  3. Per-IP rate limits are per-IP again behind the Render proxy (or replaced by a site-wide login circuit breaker); XFF cannot spoof the key; rate limiting fails closed for auth/LLM paths when Redis is unavailable.
  4. LLM cost per account is bounded (global generation semaphore + per-round tool-call cap + per-user budget); SSRF-hardened `base_url` validation rejects loopback/private/link-local/metadata for both BYOK and stored paths.
  5. Request bodies are size-limited; `/docs`, `/redoc`, `/openapi.json` 404 in production; the Vercel SPA shell carries CSP + security headers; validation-error logs never contain raw submitted values.
  6. Regression tests from SECURITY_TEST_PLAN.md sections 1–3, 5, 8, 11 are implemented and green; backend pytest + frontend vitest/lint/build stay green; docs updated (SECURITY_ATTACK_SURFACE.md refreshed).

**Plans**: planned in `11-*.md` (see below).

<details>
<summary>✅ v1.4 Security Hardening (Phase 11) — SHIPPED 2026-08-20</summary>

- [x] Phase 11: Security Hardening — audit remediation (P0/P1) — completed 2026-08-20, verified (8/8 plans)

</details>

<details>
<summary>✅ v1.3 Production Deployment & Access Hardening (Phases 8–10) — SHIPPED 2026-08-14</summary>

- [x] Phase 8: Production Deployment & Automated CI/CD (8/8 plans) — completed 2026-08-05, verified
- [x] Phase 9: Feature Expansion & Full Audit Remediation (18/18 plans) — completed 2026-08-13, verified
- [x] Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign (11/11 plans) — completed 2026-08-14, verified

</details>

<details>
<summary>✅ v1.2 Spoiler-Safety Hardening (Phase 7) — SHIPPED 2026-08-03</summary>

- [x] Phase 7: Spoiler-Safety Hardening (8/8 plans) — completed 2026-08-03

</details>

<details>
<summary>✅ v1.1 MVP (Phases 1–6, + 03.1, 05.1) — SHIPPED 2026-08-02</summary>

- [x] Phase 1: Backend Graph Foundation (1/1 plan) — completed 2026-07-28
- [x] Phase 2: Polished Cytoscape Graph Experience (4/4 plans) — completed 2026-07-29
- [x] Phase 03.1: Frontend visual overhaul — cinematic graph exploration UI (4/4 plans, inserted) — completed 2026-07-29
- [x] Phase 3: User Notes and Manual Editing (4/4 plans, full-stack) — completed 2026-07-29
- [x] Phase 4: Revision History and Revert (5/5 plans) — completed 2026-07-30
- [x] Phase 5: Future-Extraction Preparation (4/4 plans) — completed 2026-07-30
- [x] Phase 05.1: Candidate review frontend UI — approve/reject/edit workflow (inserted) — completed 2026-07-30
- [x] Phase 6: Spoiler-safe GraphRAG chat and graph-editing agent (13/13 plans) — completed 2026-08-02

</details>

Full phase details archived at `.planning/milestones/v1.1-ROADMAP.md`, `.planning/milestones/v1.2-ROADMAP.md`, and `.planning/milestones/v1.3-ROADMAP.md` (with per-version phase directories under `.planning/milestones/v1.3-phases/`).

---
*Last updated: 2026-08-20 — v1.4 Security Hardening (Phase 11) SHIPPED. Phase 11 (8/8 plans) audit remediation complete; all P0/P1 findings closed; next milestone to be defined via `/gsd-new-milestone`.*
