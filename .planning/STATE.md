---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Production Deployment & Access Hardening
current_phase: 10
current_phase_name: polish-finishing-touches
status: executing
stopped_at: Completed 10-06-PLAN.md
last_updated: "2026-08-13T19:50:00.000Z"
last_activity: 2026-08-13
last_activity_desc: Plan 10-04 complete — DTO adapters, scene reducer, dagre/fcose layout contracts
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 37
  completed_plans: 28
  percent: 67
---

# HD Graf Cehennemi — Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress; the backend filters before data reaches the frontend, the LLM, or any tool call.
**Current focus:** Phase 10 — polish-finishing-touches

## Current Position

Phase: 10 (polish-finishing-touches) — EXECUTING
Plan: 7 of 11
Status: Ready to execute
Last activity: 2026-08-13 — Plan 10-06 complete: semantic expansion endpoint + history-based recovery

Progress: [████████░░] 84% (v1.3, 1/3 phases); 7 phases complete across v1.0–v1.2

## Performance Metrics

**Velocity:**

- Total plans completed (all milestones to date): 43 (v1.0/v1.1: 27, v1.2: 8, v1.3: 8)
- v1.3: 8 plans completed (08-01..08-08) — phase verified by operator UAT (10/12 passed; CI re-run + admin live check carried to Phase 9 as 09-02/09-03)

**By Phase:**

| Phase | Plans | Notes |
|-------|-------|-------|
| 1–6 (v1.0/v1.1) | 27 | See `.planning/milestones/v1.1-ROADMAP.md` for per-plan durations |
| 7 (v1.2 Spoiler-Safety Hardening) | 8 | See `.planning/milestones/v1.2-phases/07-spoiler-safety-hardening/` SUMMARY.md files |
| 8 (v1.3 Production Deployment) | 8 | Phase complete — VERIFICATION.md passed 2026-08-05; 2 items carried to Phase 9 (09-02, 09-03) |
| 9–10 (v1.3) | 2/18 | Phase 9 in progress — 09-01 rename + 09-02 regression nets done |
| 09-02 (Phase 9) | 45min | Verifier + progress wire-shape regression nets; #42 fix (a36676a) |

**Recent Trend:** v1.3 — Phase 8 (Production Deployment & Automated CI/CD) complete and verified 2026-08-05; Phase 9 planning next.

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 10 P02 | 43min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [PROJECT.md]: Global (non-per-user) LLM Settings, built without a threat model — flagged as SSRF/cross-user-takeover surface; full fix deferred to v1.3 (Phase 8, AUTH-04/AI-01..03)
- [08-02]: LLM settings moved to browser-only BYOK — frontend keeps key/base_url/model in localStorage ('hdgraf:byok-llm-settings') and sends them per-request as X-LLM-* headers; frontend api/settings.ts (GET/PUT /api/settings/llm) removed. Backend endpoint stays for now; 08-03 gates it to admin or retires it.
- [08-03]: Admin role derived server-side from ADMIN_EMAILS at every login and persisted on AppUser (re-synced on each login — removals demote on next sign-in); require_admin gates candidate approve/reject/edit, ChangeSet confirm, and GET/PUT /api/settings/llm (403 "forbidden"). /api/settings/llm survives as admin-only server fallback (BYOK covers per-user path). ChangeSet reject/revert and candidate ingest/list/get intentionally NOT gated (Phase 9/PROB-01 scope).
- [08-05]: Rate limiting is Redis-backed via pyrate-limiter's atomic RedisBucket (Lua script) shared across Render workers (D-14). fastapi-limiter 0.2.0 is the pyrate-limiter rewrite — no FastAPILimiter.init (RESEARCH A5 verified live); kept its identifier+callback dependency contract in services/rate_limit.py with per-window RateLimiter(times, seconds) instances (login 10/5min per IP; chat-send 20/min per user; content-write 30/min per user-or-IP), init_rate_limiter() bound at startup from main.py lifespan guarded on redis_url (empty ⇒ disabled). require_current_user now stamps request.state.user so identifiers key per-user. Tests never touch Redis: conftest autouse fixture no-ops RateLimiter.__call__.
- [v1.3 requirements]: Stack additions locked for this milestone only — Upstash Redis (caching) and a hosted target (Vercel/Render/AuraDB); no other new stack components (no second graph DB, no JWT auth, no frontend rewrite)
- [v1.3 roadmap]: AUTH-01 (email allowlist) and AUTH-02 (`/api/auth/dev` removal) landed ahead of formal planning; mapped to Phase 8 for traceability as verification/regression work, not new build work
- [v1.3 roadmap]: Phases sequenced access-control/security (8) → data+hosting infra migration (9) → CI/monitoring/docs (10), since exposing the app publicly (Phase 9) should follow session/CORS/rate-limit hardening (Phase 8), and monitoring/docs (Phase 10) need a real deployed target to point at
- [09-02]: #42 NameError was LIVE (plan premise wrong) — fixed in a36676a; verifier + progress regression nets red-capable
- [10-01]: Episode Overview production default = Variant A (characters + major Events) at projection_version 1.0.0, from measured fixed-data evidence (13 nodes inside 12–28 target on cumulative S01E02 vs B's 11; edges 4/7, crossings 0, stability 1.0, procedural labels 0 for both). Decision log: docs/decision-logs/phase-10-visualization.md. Full Graph stays Advanced (D-11).
- [10-02]: Episode Overview projection implements the recorded 10-01 Variant A decision (characters + major Events) at projection_version 1.0.0; display_tier derives from safe editorial event tier (major=1, supporting=2, micro=3; characters=1; containers=2) pending the 10-03 display_tier source audit.
- [10-02]: Boundary enforcement centralized in policy.resolve_effective_boundary: one pure D-05 resolver for graph/projection/expansion/path/search/focus/restoration inputs; missing progress fails closed to order 1; the projection service rejects hidden rows before projection (T10-LEAK-02/T10-BOUND-02).
- [10-02]: Neutral DTO carries projection_version + effective_view_order metadata as the T10-CACHE-02 cache contract; no cache introduced in 10-02.
- [10-02]: Human edge classes (family/work/knows/precedes/part_of/...) replace raw Neo4j relation names in normal DTOs; unmapped relationship types fail closed (D-14).

### Pending Todos

None yet.

### Blockers/Concerns

- Pre-existing test-pollution debt in `test_seed_idempotency.py` (untorn-down candidate-origin fixture from `test_candidate_ingest.py`; 8 candidate nodes currently in the shared live DB) — now mapped to Phase 9 carry-over **09-05** (PROB-06)
- Pre-existing frontend lint debt (28 errors, none newly introduced in v1.1) — now mapped to Phase 9 carry-over **09-06** (PROB-08; CI fix branch `ci-smoke-test` scoped 3 React-Compiler-era rules to warnings, 0 lint errors verified locally)
- Deploy-time: REDIS_URL (Upstash rediss:// from 08-01 user_setup) must be set on Render for rate limiting to activate; empty = rate limiting disabled (by design, 08-05) — mapped to Phase 9 carry-over **09-04**

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260805-te3 | Visitor (misafir) read-only login — browse the graph, no node/note writes (backend anon writes already 401; fixed DetailPanel TooltipProvider crash) | 2026-08-05 | 73b87a7 | [260805-te3-add-a-visitor-misafir-read-only-login-vi](./quick/260805-te3-add-a-visitor-misafir-read-only-login-vi/) |
| 260810-testtime | Backend test suite 75m -> ~40m serial: DRY conftest helpers (seed_live_database, module_cleanup_fixture, run_query/helper_db/run_async), per-test cleanup -> module-scoped, chat_persistence async'd, pytest-asyncio loop_scope=module, ghost-node fixed-id cleanup fix. Parallel chunks on AuraDB measured SLOWER (connection contention); <8m needs local docker Neo4j. Pre-existing reds: 3 doc-contract + 1 seed-image | 2026-08-10 | a56b52f | — |
| 260810-ep1box | Episode-band cluster box is a non-interactive dashed outline — transparent fill (dot-grid shows through), dashed border, events:no (cluster taps no longer open a bogus DetailPanel) | 2026-08-10 | c77874d | — |
| 260811-prob09 | PROBLEMS.md NINTH-PASS fixes: #58 pipeline ProgressService imports; #59 path-route boundary resolves from persisted progress (never MAX_PATH_HOPS); #75 BacklinksTab jump-to-node + fresh hover card; #76 onRefreshGraph to GraphCanvas (non-destructive custom-node refresh); #80 dead-code sweep (10 items; 3 of the finding's claims verified FALSE at HEAD) | 2026-08-11 | 3d6dc33 | — |
| 260812-gra | Refresh graph automatically on website open: run the same forced Cytoscape layout and fit used by Refresh graph when the live canvas instance is created | 2026-08-12 | f968788 | [260812-gra-refresh-graph-on-open](./quick/260812-gra-refresh-graph-on-open/) |
| 260813-ftl | Hide note-adding UI (Add Note / NoteEditor / NoteItem edit-delete) and revision History tab from visitor (misafir) mode; readOnly threaded into DetailPanel from App.tsx | 2026-08-13 | ed24814 | [260813-ftl-hide-note-adding-ui-buttons-and-revision](./quick/260813-ftl-hide-note-adding-ui-buttons-and-revision/) |
| 260813-gao | Fix broken node portrait images in production: apiUrl() helper prefixes relative image_url with VITE_API_BASE_URL at both consumption sites (Cytoscape imageUrl + DetailPanel img src); local vite-proxy behavior unchanged | 2026-08-13 | 73ed961 | [260813-gao-fix-broken-node-portrait-images-in-produ](./quick/260813-gao-fix-broken-node-portrait-images-in-produ/) |

## Deferred Items

Items acknowledged and carried forward, not in v1.3 scope:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| OPS | Full CI/CD: dependency scanning, artifact publication, staged promotion, branch-protection enforcement (OPS-01 is a minimal PR gate only) | Deferred | v1.3 requirements gathering |
| OPS | Full observability: centralized logs, metrics dashboards, incident/rollback runbook automation (OPS-02 is a single health-check ping only) | Deferred | v1.3 requirements gathering |
| Content | Person / ACTED_AS / APPEARS_IN actor model | Deferred | Carried from v1.1/v1.2 |
| Content | Reviews, ratings, trivia, recommendations | Deferred | Carried from v1.1/v1.2 |
| Ingestion | Automated ingestion/extraction from external sources (OpenSubtitles, scripts, Fandom/IMDb/news) | Deferred | Carried from v1.1/v1.2 |
| Hosting | Multi-region/HA hosting, paid tier / usage-based billing | Out of scope | v1.3 requirements gathering |

## Session Continuity

Last session: 2026-08-13T15:04:23.232Z
Stopped at: Completed 10-02-PLAN.md
Resume file: None

## Operator Next Steps

- Phase 8 is CLOSED — no open Phase 8 action items. UptimeRobot monitor is live (UAT #11 pass; free-tier false-downs during Render sleep are a known free-tier cost, not a defect).
- Resume with Phase 9 planning (feature expansion + full audit remediation, per `.planning/REQUIREMENTS.md`). Phase 9 carries 8 Phase 8 carry-over plans (09-01..09-08) listed in ROADMAP.md — CI smoke re-run to main (09-02) and admin-role live check (09-03) are the two user-action-adjacent ones.
