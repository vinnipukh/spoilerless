---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Production Deployment & Access Hardening
current_phase: 9
current_phase_name: Feature Expansion & Full Audit Remediation
status: executing
stopped_at: Phase 9 context gathered
last_updated: "2026-08-04T21:56:30.062Z"
last_activity: 2026-08-05
last_activity_desc: Phase 8 closed out (VERIFICATION.md passed, operator-UAT verified)
progress:
  total_phases: 3
  completed_phases: 1
  total_plans: 8
  completed_plans: 8
  percent: 33
---

# HD Graf Cehennemi — Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress; the backend filters before data reaches the frontend, the LLM, or any tool call.
**Current focus:** Phase 9 — feature-expansion-&-full-audit-remediation

## Current Position

Phase: 9 — Feature Expansion & Full Audit Remediation
Plan: Not started
Status: Phase 8 complete (8/8 plans verified); Phase 9 not started
Last activity: 2026-08-05 — Phase 8 closed out (VERIFICATION.md passed, operator-UAT verified)

Progress: [███░░░░░░░] 33% (v1.3, 1/3 phases); 7 phases complete across v1.0–v1.2

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
| 9–10 (v1.3) | TBD | Phase 9 pending planning — carries 8 Phase 8 carry-over plans (09-01..09-08) |

**Recent Trend:** v1.3 — Phase 8 (Production Deployment & Automated CI/CD) complete and verified 2026-08-05; Phase 9 planning next.

*Updated after each plan completion*

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

### Pending Todos

None yet.

### Blockers/Concerns

- Pre-existing test-pollution debt in `test_seed_idempotency.py` (untorn-down candidate-origin fixture from `test_candidate_ingest.py`; 8 candidate nodes currently in the shared live DB) — now mapped to Phase 9 carry-over **09-05** (PROB-06)
- Pre-existing frontend lint debt (28 errors, none newly introduced in v1.1) — now mapped to Phase 9 carry-over **09-06** (PROB-08; CI fix branch `ci-smoke-test` scoped 3 React-Compiler-era rules to warnings, 0 lint errors verified locally)
- Deploy-time: REDIS_URL (Upstash rediss:// from 08-01 user_setup) must be set on Render for rate limiting to activate; empty = rate limiting disabled (by design, 08-05) — mapped to Phase 9 carry-over **09-04**

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

Last session: 2026-08-04T21:56:30.048Z
Stopped at: Phase 9 context gathered
Resume file: .planning/phases/09-feature-expansion-full-audit-remediation/09-CONTEXT.md

## Operator Next Steps

- Phase 8 is CLOSED — no open Phase 8 action items. UptimeRobot monitor is live (UAT #11 pass; free-tier false-downs during Render sleep are a known free-tier cost, not a defect).
- Resume with Phase 9 planning (feature expansion + full audit remediation, per `.planning/REQUIREMENTS.md`). Phase 9 carries 8 Phase 8 carry-over plans (09-01..09-08) listed in ROADMAP.md — CI smoke re-run to main (09-02) and admin-role live check (09-03) are the two user-action-adjacent ones.
