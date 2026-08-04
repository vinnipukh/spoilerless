# HD Graf Cehennemi — Roadmap

## Milestones

- ✅ **v1.0 Prototype v0** — Phases 1–5 (+ 03.1, 05.1 inserted) (shipped 2026-07-30)
- ✅ **v1.1 MVP** — Phases 1–6 (+ 03.1, 05.1 inserted) (shipped 2026-08-02, supersedes v1.0 — adds Phase 6 GraphRAG chat)
- ✅ **v1.2 Spoiler-Safety Hardening** — Phase 7 (shipped 2026-08-03)
- 🔄 **v1.3 Production Deployment & Access Hardening** — Phases 8–10: deploy+CI (8), features+full audit remediation (9), polish (10) (roadmapped 2026-08-04)

## Phases

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

<details>
<summary>✅ v1.2 Spoiler-Safety Hardening (Phase 7) — SHIPPED 2026-08-03</summary>

- [x] Phase 7: Spoiler-Safety Hardening (8/8 plans) — completed 2026-08-03

#### Phase 7: Spoiler-Safety Hardening

**Goal:** Separate watched progress from the temporary view boundary, centralize the `visible_from_order` policy (fail-closed), and close indirect leak channels — episode metadata, search/autocomplete, counts, media, chat/GraphRAG, and graph edits — on the existing stack.
Requirements: PROG-01–04, VIS-01–05, META-01–03, SEARCH-01–02, MEDIA-01–02, CHAT-01–03, EDIT-01–02, DOCS-01–02
Success criteria:
1. User can view an earlier already-watched episode without lowering progress; graph and chat show only boundary-safe data; returning restores eligible content
2. Future episode titles, synopses, runtimes, and images never appear in any API response (backend-masked)
3. Hidden entities, aliases, counts, and relationships behave like nonexistent in search, autocomplete, aggregates, and graph layout
4. GraphRAG and ChangeSets operate on the effective boundary; stale later-boundary ChangeSets fail closed
5. Threat-model doc + regression matrix cover every direct/indirect leak class with enforcement layer and test coverage

Plans: 07-01 audit + threat model + domain design · 07-02 progress migration + boundary service + API · 07-03 metadata gating + frontend UX · 07-04 relationship/provenance/Cypher hardening · 07-05 search/aggregate leak protection · 07-06 media safety · 07-07 chat/GraphRAG/ChangeSet integration · 07-08 regression + browser acceptance + docs

</details>

### 🔄 v1.3 Production Deployment & Access Hardening (In Planning)

**Milestone Goal:** Move HD Graf Cehennemi from a local-only prototype to a real, zero-cost hosted deployment (Vercel + Render + Neo4j AuraDB Free + Upstash Redis) with automated CI/CD, every finding in `docs/PROBLEMS.md`'s 45-item audit resolved, 10 new features, and a final polish pass.

- [ ] Phase 8: Production Deployment & Automated CI/CD (TBD plans) — pending planning
- [ ] Phase 9: Feature Expansion & Full Audit Remediation (TBD plans) — pending planning
- [ ] Phase 10: Polish & Finishing Touches (TBD plans) — pending planning

#### Phase 8: Production Deployment & Automated CI/CD

**Goal**: The app is live on real, zero-cost hosting (Vercel + Render + Neo4j AuraDB Free + Upstash Redis) behind production-grade access control (allowlist, admin role, BYOK chat, hardened cookies/CORS/rate-limits), with an automated GitHub Actions CI gate — nothing here is a "someday" fix, it's the difference between deployable and not.
**Depends on**: Phase 7 (builds on the complete, spoiler-safety-hardened v1.2 app)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AI-01, AI-02, AI-03, SEC-01, SEC-02, SEC-03, INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, OPS-01, OPS-02, OPS-03, DOCS-03
**Scope note**: AUTH-01 (email allowlist) and AUTH-02 (`/api/auth/dev` removal) already landed ahead of formal planning — this phase's work on them is verification/regression coverage, not new build work. Also resolves `docs/PROBLEMS.md` #5, #6, #7, #8, #10, #27, #31, #36, #39 as a side effect of the AUTH/AI/SEC/INFRA/OPS work below (each cross-referenced in REQUIREMENTS.md).
**Success Criteria** (what must be TRUE):
  1. A verified Google account not on `ALLOWED_EMAILS` is rejected at sign-in with `403 AUTH_EMAIL_NOT_ALLOWED`, no code path can create a session without a verified Google credential, a non-admin user is rejected with 403 from candidate review/ChangeSet approval, and `/api/settings/llm` is admin-gated or retired in favor of BYOK
  2. A user can enter their own LLM provider key/base URL/model in the frontend, stored only in browser `localStorage` and sent per-request as a header — never persisted, logged, or written server-side; chat is unavailable with a clear message when no key and no server fallback exist
  3. In production, the session cookie is `Secure` (default `true`) with correct `SameSite` handling across the cross-origin deployment, `FRONTEND_ORIGINS` is the exact deployed origin, CSRF Origin/Referer checking covers logout and no longer auto-allows a missing Origin, and login/chat-send/content-write requests return `429` once a multi-worker-safe per-user/IP rate limit is exceeded
  4. Neo4j runs on AuraDB Free (no exposed local Compose recipe in the deploy path) through a least-privilege app DB role; Upstash Redis caches and invalidates graph query responses; the backend is live on Render and the frontend on Vercel, reaching each other through configured CORS; every secret is a platform environment variable, none in the repo
  5. A GitHub Actions workflow runs backend `pytest` + frontend build/lint on every PR; an external uptime check on `GET /health` can alert on failure; the backend logs exceptions instead of dropping them; `docs/DEPLOYMENT.md` documents the real hosted target and rollback procedure
**Plans**: TBD
**UI hint**: yes

#### Phase 9: Feature Expansion & Full Audit Remediation

**Goal**: Every one of `docs/PROBLEMS.md`'s 45 verified findings is resolved, and the product gains 10 new user-facing capabilities on top of the now-deployed app.
**Depends on**: Phase 8 (fixing ownership/audit/test-infra bugs and adding features on a still-local, unhardened app would need redoing against the real hosted environment)
**Requirements**: PROB-01..21, FEAT-01..10, DOCS-04
**Success Criteria** (what must be TRUE):
  1. Every mutation endpoint (notes, custom nodes/relationships, candidates, revision revert) requires an authenticated, correctly-scoped owner; user-content records carry owner `user_id`; session IDs are collision-proof and swept on expiry; anonymous/candidate reads can no longer request an arbitrary spoiler boundary
  2. Both test suites (backend `pytest` against a disposable DB, frontend `vitest`) are fully green and deterministic — no suite mutates the live application database; `npm run lint` is 0 errors; error codes use one consistent casing
  3. Committed boilerplate/junk is removed, a LICENSE exists, seed images are no longer hotlinked from a third party, the repo is pushed to a real accessible remote, revision/candidate-approval responses are internally consistent, chat mid-stream failures are logged not silently orphaned, the Google-verifier `NameError` and the progress-confirm 422 contract bug are fixed, `None`-valued visibility orders 422 instead of 500ing, baseline security headers are present, core modules (db driver, ontology loader, series service, config, lifespan) have direct tests, and a root error boundary + debug-log cleanup ship
  4. `docs/API.md`, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md` match live behavior — no stale route counts, no "known gaps" that already shipped, no claims contradicted by the running code
  5. All 10 new features are live and usable: node search/jump, timeline view, newly-revealed highlight on episode advance, series dashboard, note/claim export, shortest-path relationship finder, full-text note/claim search, command palette, shareable read-only snapshot link, and a mobile-usable graph/detail panel
**Plans**: TBD
**UI hint**: yes

#### Phase 10: Polish & Finishing Touches

**Goal**: Ship v1.3 in a demonstrably solid state — no known regressions, a verified golden path, and docs that describe the shipped product accurately. No new features or architectural changes in this phase.
**Depends on**: Phase 9 (polishing requires the features and fixes it's polishing to already exist)
**Requirements**: POLISH-01, POLISH-02, POLISH-03
**Success Criteria** (what must be TRUE):
  1. Backend `pytest`, frontend `vitest`, `npm run lint`, and `npm run build` are all green with zero known failures
  2. A conversational UAT pass covers the full golden path (login → series/episode select → graph explore → BYOK chat → notes → export → each new feature) with no unresolved regressions found
  3. `README.md` and root-level docs reflect the shipped v1.3 state — no stale "prototype only, no deployment" language remains
**Plans**: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|-----------------|--------|-----------|
| 1. Backend Graph Foundation | v1.0/v1.1 | 1/1 | Complete | 2026-07-28 |
| 2. Polished Cytoscape Graph Experience | v1.0/v1.1 | 4/4 | Complete | 2026-07-29 |
| 03.1 Frontend visual overhaul | v1.0/v1.1 | 4/4 | Complete | 2026-07-29 |
| 3. User Notes and Manual Editing | v1.0/v1.1 | 4/4 | Complete | 2026-07-29 |
| 4. Revision History and Revert | v1.0/v1.1 | 5/5 | Complete | 2026-07-30 |
| 5. Future-Extraction Preparation | v1.0/v1.1 | 4/4 | Complete | 2026-07-30 |
| 05.1 Candidate review frontend UI | v1.0/v1.1 | — | Complete | 2026-07-30 |
| 6. Spoiler-safe GraphRAG chat and graph-editing agent | v1.1 | 13/13 | Complete | 2026-08-02 |
| 7. Spoiler-Safety Hardening | v1.2 | 8/8 | Complete | 2026-08-03 |
| 8. Production Deployment & Automated CI/CD | v1.3 | 0/TBD | Not started | - |
| 9. Feature Expansion & Full Audit Remediation | v1.3 | 0/TBD | Not started | - |
| 10. Polish & Finishing Touches | v1.3 | 0/TBD | Not started | - |

Full phase details archived at `.planning/milestones/v1.1-ROADMAP.md` / `.planning/milestones/v1.1-phases/` and `.planning/milestones/v1.2-ROADMAP.md` / `.planning/milestones/v1.2-phases/` (v1.2 archive supersedes the earlier v1.1 archive, which predates Phase 7).

---
*Last updated: 2026-08-04 — v1.3 Production Deployment & Access Hardening roadmapped (Phases 8–10, restructured per user direction: deploy+CI / features+full audit remediation / polish; 21 PROB + 10 FEAT + 3 POLISH requirements added on top of the original 18)*
