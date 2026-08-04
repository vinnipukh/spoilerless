---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Production Deployment & Access Hardening
current_phase: 8
current_phase_name: production-deployment-automated-ci-cd
status: executing
stopped_at: Plan 08-02 (BYOK LLM chat) complete - frontend localStorage BYOK + X-LLM-* headers (AI-01/02/03)
last_updated: "2026-08-04T13:25:00.000Z"
last_activity: 2026-08-04
last_activity_desc: Plan 08-02 (BYOK LLM chat) completed - 1/8 plans done
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 8
  completed_plans: 1
  percent: 12
---

# HD Graf Cehennemi — Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Users can safely explore a TV-series knowledge graph — and chat about it — without ever seeing information beyond their selected watch progress; the backend filters before data reaches the frontend, the LLM, or any tool call.
**Current focus:** Phase 8 — production-deployment-automated-ci-cd

## Current Position

Phase: 8 (production-deployment-automated-ci-cd) — EXECUTING
Plan: 2 of 8
Status: Executing Phase 8
Last activity: 2026-08-04 — Plan 08-02 (BYOK LLM chat) completed

Progress: [█░░░░░░░░░] 12% (v1.3); 7 phases complete across v1.0–v1.2

## Performance Metrics

**Velocity:**

- Total plans completed (all milestones to date): 36 (v1.0/v1.1: 27, v1.2: 8, v1.3: 1)
- v1.3: 1 plan completed (08-02 BYOK), 7 planned (TBD per phase)

**By Phase:**

| Phase | Plans | Notes |
|-------|-------|-------|
| 1–6 (v1.0/v1.1) | 27 | See `.planning/milestones/v1.1-ROADMAP.md` for per-plan durations |
| 7 (v1.2 Spoiler-Safety Hardening) | 8 | See `.planning/milestones/v1.2-phases/07-spoiler-safety-hardening/` SUMMARY.md files |
| 8–10 (v1.3) | 1 | See Phase 8 SUMMARY.md files (08-02 BYOK complete) |

**Recent Trend:** v1.3 executing — Plan 08-02 (BYOK LLM chat) completed 2026-08-04.

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- [PROJECT.md]: Global (non-per-user) LLM Settings, built without a threat model — flagged as SSRF/cross-user-takeover surface; full fix deferred to v1.3 (Phase 8, AUTH-04/AI-01..03)
- [08-02]: LLM settings moved to browser-only BYOK — frontend keeps key/base_url/model in localStorage ('hdgraf:byok-llm-settings') and sends them per-request as X-LLM-* headers; frontend api/settings.ts (GET/PUT /api/settings/llm) removed. Backend endpoint stays for now; 08-03 gates it to admin or retires it.
- [v1.3 requirements]: Stack additions locked for this milestone only — Upstash Redis (caching) and a hosted target (Vercel/Render/AuraDB); no other new stack components (no second graph DB, no JWT auth, no frontend rewrite)
- [v1.3 roadmap]: AUTH-01 (email allowlist) and AUTH-02 (`/api/auth/dev` removal) landed ahead of formal planning; mapped to Phase 8 for traceability as verification/regression work, not new build work
- [v1.3 roadmap]: Phases sequenced access-control/security (8) → data+hosting infra migration (9) → CI/monitoring/docs (10), since exposing the app publicly (Phase 9) should follow session/CORS/rate-limit hardening (Phase 8), and monitoring/docs (Phase 10) need a real deployed target to point at

### Pending Todos

None yet.

### Blockers/Concerns

- Pre-existing test-pollution debt in `test_seed_idempotency.py` (untorn-down candidate-origin fixture from `test_candidate_ingest.py`) — not mapped to any v1.3 requirement, remains open technical debt
- Pre-existing frontend lint debt (28 errors, none newly introduced in v1.1) — not mapped to any v1.3 requirement, remains open technical debt

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

Last session: 2026-08-04 13:25
Stopped at: Plan 08-02 (BYOK LLM chat) complete — backend request-scoped BYOK provider (cf2f685) + frontend localStorage settings/X-LLM-* headers (7665168, 7e7e025); 1/8 Phase 8 plans done
Resume file: None

## Operator Next Steps

- Continue executing Phase 8 — next: plan 08-03 (admin role: candidate review, ChangeSet confirm, /api/settings/llm gated to admin)
