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

- [x] Phase 8: Production Deployment & Automated CI/CD (8 plans) — planned, ready to execute (completed 2026-08-04)
- [x] Phase 9: Feature Expansion & Full Audit Remediation (TBD plans) — pending planning (completed 2026-08-13)
- [ ] Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign (TBD plans) — pending planning

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

**Plans**: 8/8 plans executed and verified (08-01..08-08) — Phase 8 COMPLETE 2026-08-05 (VERIFICATION.md passed; 2 items carried to Phase 9: 09-02 CI re-run, 09-03 admin live check)

Plans:

- [x] 08-01-PLAN.md — Tracer: production deploy skeleton (Render + Vercel + AuraDB + spoilerless.net custom domain, one real Google login end-to-end)
- [x] 08-02-PLAN.md — BYOK LLM chat: browser-held key/base_url/model, per-request headers, backend passthrough (completed 2026-08-04: cf2f685, 7665168, 7e7e025)
- [x] 08-03-PLAN.md — Admin role: candidate review, ChangeSet confirm, and /api/settings/llm gated to admin (completed 2026-08-04: 037d43c, 573462e, 11acd74, abbb7e7)
- [x] 08-04-PLAN.md — Cookie/CORS/CSRF hardening: fail-closed verify_origin, logout CSRF coverage, settings-driven SameSite
- [x] 08-05-PLAN.md — Redis foundation + rate limiting: multi-worker-safe 429 on login/chat-send/content-write (completed 2026-08-04: a672d17, 1f8a3e9)
- [x] 08-06-PLAN.md — Graph query response cache: Redis cache-aside keyed by (series_id, boundary, user_id), invalidated on write (completed 2026-08-04: 913f211, 7fae2a4, 22bb957)
- [x] 08-07-PLAN.md — Ops: GitHub Actions CI gate, structured exception logging, external uptime check (completed 2026-08-04: 3516c2c, 7eeebd6; CI lint fixes on ci-smoke-test — re-run carried to 09-02; UptimeRobot monitor live, UAT #11 pass)
- [x] 08-08-PLAN.md — docs/DEPLOYMENT.md rewrite for the real hosted target and rollback procedure (completed 2026-08-04: 8bdf633)

**UI hint**: yes

#### Phase 9: Feature Expansion & Full Audit Remediation

**Goal**: Every one of `docs/PROBLEMS.md`'s 45 verified findings is resolved, and the product gains 10 new user-facing capabilities on top of the now-deployed app.
**Depends on**: Phase 8 (fixing ownership/audit/test-infra bugs and adding features on a still-local, unhardened app would need redoing against the real hosted environment)
**Requirements**: PROB-01..21, FEAT-01..10, DOCS-04, REBRAND-01, FEAT-11
**Success Criteria** (what must be TRUE):

  0. REBRAND-01: every user-visible and repo-level `hdgrafcehennemi` reference is renamed to `spoilerless` (package dirs, pyproject, docker-compose container name, service names, README, DEPLOYMENT.md, /health `service` field, UI title "HD Graf Cehennemi" → "Spoilerless") — git history intentionally untouched; runtime/deploy names updated

  1. Every mutation endpoint (notes, custom nodes/relationships, candidates, revision revert) requires an authenticated, correctly-scoped owner; user-content records carry owner `user_id`; session IDs are collision-proof and swept on expiry; anonymous/candidate reads can no longer request an arbitrary spoiler boundary
  2. Both test suites (backend `pytest` against a disposable DB, frontend `vitest`) are fully green and deterministic — no suite mutates the live application database; `npm run lint` is 0 errors; error codes use one consistent casing
  3. Committed boilerplate/junk is removed, a LICENSE exists, seed images are no longer hotlinked from a third party, the repo is pushed to a real accessible remote, revision/candidate-approval responses are internally consistent, chat mid-stream failures are logged not silently orphaned, the Google-verifier `NameError` and the progress-confirm 422 contract bug are fixed, `None`-valued visibility orders 422 instead of 500ing, baseline security headers are present, core modules (db driver, ontology loader, series service, config, lifespan) have direct tests, and a root error boundary + debug-log cleanup ship
  4. `docs/API.md`, `docs/ARCHITECTURE.md`, and `docs/ROADMAP.md` match live behavior — no stale route counts, no "known gaps" that already shipped, no claims contradicted by the running code
  5. All 10 new features are live and usable: node search/jump, timeline view, newly-revealed highlight on episode advance, series dashboard, note/claim export, shortest-path relationship finder, full-text note/claim search, command palette, shareable read-only snapshot link, and a mobile-usable graph/detail panel
  6. FEAT-11 (Obsidian-style second-brain touches, small scope): node backlinks panel (reverse relationships + mentions), hover preview card on graph nodes, quick-switcher jump (⌘K fuzzy search), graph filters by node type/edge type, per-node properties (aliases, created/updated, source), and version-history surfaced via the existing Revision system — spoiler boundary preserved throughout; no free-form canvas or personal-layer rewrite in this phase

**Plans**: 10/18 plans executed

- [x] 09-01-PLAN.md
- [x] 09-02-PLAN.md
- [x] 09-03-PLAN.md
- [x] 09-04-PLAN.md
- [x] 09-05-PLAN.md
- [x] 09-06-PLAN.md
- [x] 09-07-PLAN.md
- [x] 09-08-PLAN.md
- [x] 09-09-PLAN.md
- [x] 09-10-PLAN.md
- [x] 09-11-PLAN.md
- [x] 09-12-PLAN.md
- [x] 09-13-PLAN.md
- [x] 09-14-PLAN.md
- [x] 09-15-PLAN.md
- [x] 09-16-PLAN.md
- [x] 09-17-PLAN.md
- [x] 09-18-PLAN.md

**Phase 8 carry-over (blocked / undone — must land in Phase 9):**

- [x] **09-01**: External uptime monitor (08-07 Task 3, `checkpoint:human-action`) — UptimeRobot account + HTTPS monitor for `https://api.spoilerless.net/health` (5-min) + email alert contact; verify alert fires (OPS-02)
- [x] **09-02**: CI smoke fixes → main (08-07 UAT #4, `fixed-pending-ci-rerun`) — merge/re-verify `ci-smoke-test` branch (React-Compiler-era rules scoped to warnings, typed `catch(err)` handlers, seed-idempotency cleanup, graph-image D-14 curation); confirm GitHub Actions green on main (OPS-01)
- [x] **09-03**: Admin role live verification (08-UAT #6, skipped) — configure `ADMIN_EMAILS`; verify candidate approve/reject/edit + ChangeSet confirm admin-gated, non-admin 403 (AUTH-03)
- [x] **09-04**: `REDIS_URL` on Render (08-05/08-06 runtime gate) — set Upstash `rediss://`; verify live 429 rate-limit + graph-cache invalidation (SEC-03, INFRA-02)
- [x] **09-05**: Seed-test pollution debt (STATE.md blocker) — candidate-origin residue teardown between `test_candidate_ingest.py` and `test_seed_idempotency.py` (PROB-06)
- [x] **09-06**: Frontend lint 0-error cleanup — pre-existing 28 errors + `react-hooks/refs` stale-ref bugs in `useChatSessions.ts`/`useNotes.ts`/`useRevisions.ts` (PROB-08)
- [x] **09-07**: Full CI/CD (deferred OPS) — dependency scanning, artifact publication, staged promotion, branch-protection enforcement (OPS-01 is minimal PR gate only)
- [x] **09-08**: Full observability (deferred OPS) — centralized logs, metrics dashboards, incident/rollback runbook automation (OPS-02 is single health ping only)

**UI hint**: yes

#### Phase 10: Polish & Finishing Touches + Narrative Visualization Redesign

**Goal**: Ship v1.3 as a demonstrably solid, spoiler-safe interactive story map: reduced task-specific visual projections and coordinated Story, Characters, Evidence, and Advanced experiences over the complete Neo4j/GraphRAG data, followed by a green regression pass, verified golden-path UAT, and accurate shipped-state docs.
**Depends on**: Phase 9 (the redesign builds on the completed graph, timeline, GraphRAG, responsive, and audit-remediation foundations)
**Requirements**: VIZ-01, VIZ-02, VIZ-03, VIZ-04, VIZ-05, VIZ-06, VIZ-07, VIZ-08, VIZ-09, VIZ-10, POLISH-01, POLISH-02, POLISH-03
**Scope amendment (D-01)**: Phase 10 includes both the original `POLISH-01..03` closeout obligations and the narrative visualization redesign locked in `10-CONTEXT.md`. This explicitly supersedes the earlier “no new features or architectural changes” boundary. Keep Cytoscape.js; preserve complete Neo4j and spoiler-safe GraphRAG detail; filter before projection; do not redesign unrelated auth, settings, chat, Notes, ChangeSet, ingestion, renderer, or ontology systems.
**Success Criteria** (what must be TRUE):

  1. A library-neutral, spoiler-safe visualization DTO and task-specific endpoints produce bounded Episode Overview, Character Network, plot-thread, investigation, full, and GraphRAG-focus projections only after `effective_view_order = min(requested_view_order, watched_progress)` is enforced; cache keys cannot cross view, boundary, projection version, graph revision, or required user scope.
  2. The default desktop and mobile hierarchy is Story, Characters, Evidence, Advanced. Story coordinates Episode Overview with its timeline; mobile uses scrollable top tabs and a half/full-height Inspector sheet; raw Neo4j relation names and procedural edges stay out of non-debug views.
  3. Fixed S01E01 and cumulative S01E02 snapshots select and prove one of two Episode Overview variants, stay within the 12–28 target / 40-node hard bound and 35-edge preference / 60-edge hard bound, and demonstrate that future elements cannot affect counts, layout, hints, search, focus, or restored scenes.
  4. Semantic expansion is server-allowlisted, spoiler-safe, bounded, collapsible, undoable, and resettable; stable Cytoscape scene state preserves camera, selection, important positions, expansions, and timeline coordination without random global relayout. GraphRAG Answer Graph and Evidence Chain flows restore the prior scene when closed.
  5. Automated tests cover projection order/bounds/leaks, cache separation, GraphRAG independence/focus, adapter and scene behavior, timeline/Inspector/responsive coordination, Episode switching, Answer Graph, Evidence Chain, and benchmark datasets at 30/50, 75/150, 150/400, and 300/1000 node/edge scales.
  6. Backend `pytest`, frontend `vitest`, `npm run lint`, and `npm run build` are green; a real golden-path UAT includes the original flow plus Dexter-family, Doakes-distrust, episode events/clues/cases, Overview restoration, GraphRAG visualization, and Episode 2→1 spoiler disappearance; README and root docs match the shipped architecture and behavior.

**Plans**: 11 plans in 10 dependency waves (`10-01` baseline/A-B gate; `10-02` DTO/boundary; `10-03` projections/cache; `10-04` Cytoscape adapter/scene; `10-05` four-view responsive UI; `10-06` semantic expansion/recovery; `10-07` GraphRAG Answer Graph/evidence; `10-08` benchmarks/refinement; `10-09` isolated regression gate; `10-10` operator UAT; `10-11` docs/coverage closeout).

**UI hint**: yes

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
| 8. Production Deployment & Automated CI/CD | v1.3 | 8/8 | Complete    | 2026-08-04 |
| 9. Feature Expansion & Full Audit Remediation | v1.3 | 18/18 | Complete    | 2026-08-13 |
| 10. Polish & Finishing Touches + Narrative Visualization Redesign | v1.3 | 1/11 | In Progress | - |

Full phase details archived at `.planning/milestones/v1.1-ROADMAP.md` / `.planning/milestones/v1.1-phases/` and `.planning/milestones/v1.2-ROADMAP.md` / `.planning/milestones/v1.2-phases/` (v1.2 archive supersedes the earlier v1.1 archive, which predates Phase 7).

---
*Last updated: 2026-08-05 — Phase 8 (Production Deployment & Automated CI/CD) COMPLETE and verified (VERIFICATION.md passed, operator UAT 10/12; CI re-run + admin live check carried to Phase 9 as 09-02/09-03). Phase 9 now carries 8 Phase 8 carry-over plans (09-01..09-08) + PROB/FEAT/DOCS-04/REBRAND-01/FEAT-11 requirements.*
