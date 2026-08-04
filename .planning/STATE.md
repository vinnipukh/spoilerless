---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Production Deployment & Access Hardening
current_phase: 8
current_phase_name: production-deployment-automated-ci-cd
status: executing
stopped_at: "None — Plan 08-05 (Redis rate limiter) complete (a672d17, 1f8a3e9); next plan 08-06 (graph query response cache)."
last_updated: "2026-08-04T12:22:22.000Z"
last_activity: 2026-08-04
last_activity_desc: Plan 08-05 (Redis-backed rate limiter) completed — redis + fastapi-limiter installed, RateLimiter deps on login/chat-send/content-write, 429 in existing envelope, no live Redis needed for tests
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 8
  completed_plans: 5
  percent: 63
---

# HD Graf Cehennemi — Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress; the backend filters before data reaches the frontend, the LLM, or any tool call.
**Current focus:** Phase 8 — production-deployment-automated-ci-cd

## Current Position

Phase: 8 (production-deployment-automated-ci-cd) — EXECUTING
Plan: 6 of 8
Status: Executing Phase 8
Last activity: 2026-08-04 — Plan 08-05 (rate limiter) complete; 08-06 (graph query response cache) is next

Progress: [███░░░░░░░] 38% (v1.3); 7 phases complete across v1.0–v1.2

## Performance Metrics

**Velocity:**

- Total plans completed (all milestones to date): 40 (v1.0/v1.1: 27, v1.2: 8, v1.3: 5)
- v1.3: 5 plans completed (08-01 tracer, 08-02 BYOK, 08-03 admin role, 08-04 CSRF, 08-05 rate limiter), 3 planned (08-06..08-08)

**By Phase:**

| Phase | Plans | Notes |
|-------|-------|-------|
| 1–6 (v1.0/v1.1) | 27 | See `.planning/milestones/v1.1-ROADMAP.md` for per-plan durations |
| 7 (v1.2 Spoiler-Safety Hardening) | 8 | See `.planning/milestones/v1.2-phases/07-spoiler-safety-hardening/` SUMMARY.md files |
| 8–10 (v1.3) | 5 | See Phase 8 SUMMARY.md files (08-01..08-05 complete) |

**Recent Trend:** v1.3 executing — Plan 08-05 (Redis rate limiter) completed 2026-08-04.

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

- Pre-existing test-pollution debt in `test_seed_idempotency.py` (untorn-down candidate-origin fixture from `test_candidate_ingest.py`; 8 candidate nodes currently in the shared live DB) — not mapped to any v1.3 requirement, remains open technical debt (details: deferred-items.md, 08-03/08-04)
- Pre-existing frontend lint debt (28 errors, none newly introduced in v1.1) — not mapped to any v1.3 requirement, remains open technical debt
- Deploy-time: REDIS_URL (Upstash rediss:// from 08-01 user_setup) must be set on Render for rate limiting to activate; empty = rate limiting disabled (by design, 08-05)

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

Last session: 2026-08-04 12:22 UTC
Stopped at: Plan 08-05 (Redis rate limiter) complete — commits a672d17 (test RED) + 1f8a3e9 (feat GREEN) + docs commit (SUMMARY/STATE/ROADMAP); next: 08-06 (graph query response cache)
Resume file: None

## Operator Next Steps

- Set REDIS_URL (Upstash rediss:// connection string, collected in 08-01's user_setup) on the Render service to activate rate limiting in production; verify with the deploy smoke test that login/chat/content-write routes accept requests and that 11th login within 5 minutes returns 429 `too_many_requests`.
- Resume with plan 08-06 (graph query response cache), which reuses `backend/app/cache/redis_client.py::get_redis()` as its single Redis connection point.
