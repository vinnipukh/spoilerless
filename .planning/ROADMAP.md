# HD Graf Cehennemi (Spoilerless) — Roadmap

## Milestones

- ✅ **v1.0 Prototype v0** — Phases 1–5 (+ 03.1, 05.1 inserted) (shipped 2026-07-30)
- ✅ **v1.1 MVP** — Phases 1–6 (+ 03.1, 05.1 inserted) (shipped 2026-08-02, supersedes v1.0 — adds Phase 6 GraphRAG chat)
- ✅ **v1.2 Spoiler-Safety Hardening** — Phase 7 (shipped 2026-08-03)
- ✅ **v1.3 Production Deployment & Access Hardening** — Phases 8–10 (shipped 2026-08-14)

## Phases

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
