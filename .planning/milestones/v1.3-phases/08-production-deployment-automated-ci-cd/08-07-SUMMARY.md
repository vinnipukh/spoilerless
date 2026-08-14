---
phase: 08-production-deployment-automated-ci-cd
plan: 07
subsystem: infra
tags: [github-actions, ci, logging, middleware, uptime]

requires:
  - phase: 08-05
    provides: Redis rate-limiter foundations
provides:
  - GitHub Actions CI workflow (backend pytest + frontend build/lint on PR)
  - Structured exception logging in all error handlers (OPS-03)
  - Redacting request-logging middleware (method/path/status/duration, no BYOK/cookie leakage)
affects: [08-08]

tech-stack:
  added: []
  patterns:
    - "Request-logging middleware with explicit header allowlist (never logs Authorization/Cookie/X-LLM-*)"
    - "Exception handlers log with exc_info before sanitizing (Pattern 4 from 08-RESEARCH.md)"

key-files:
  created:
    - .github/workflows/ci.yml
    - backend/tests/test_error_handlers.py
  modified:
    - backend/app/core/errors.py
    - backend/app/main.py

key-decisions:
  - "CI uses pinned neo4j:2026.06.0-community (same as docker-compose.yml) for throwaway test DB"
  - "CI frontend node-version pinned to '24' to satisfy jsdom engines constraint"
  - "astral-sh/setup-uv pinned to commit SHA 08807647 (v8.1.0)"
  - "No deploy step — Render/Vercel native git-integration auto-deploy handles deployment (D-18)"
  - "Request-logging middleware uses allowlist approach (User-Agent, Content-Type, Accept only)"

patterns-established:
  - "Pattern: logger.error('<handler>_error', exc_info=exc) before building sanitized JSONResponse"
  - "Pattern: _request_logging_middleware with safe header allowlist, never logs denied headers"

requirements-completed: [OPS-01, OPS-03]

coverage:
  - id: D1
    description: "GitHub Actions CI workflow with backend pytest (Neo4j service container) + frontend build/lint triggered on pull_request"
    requirement: "OPS-01"
    verification:
      - kind: other
        ref: "python -c 'import yaml; yaml.safe_load(open(\".github/workflows/ci.yml\"))'"
        status: pass
    human_judgment: false

  - id: D2
    description: "All three exception handlers log ERROR with exc_info before sanitizing"
    requirement: "OPS-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_error_handlers.py::TestExceptionLogging"
        status: pass
    human_judgment: false

  - id: D3
    description: "Request-logging middleware logs method/path/status/duration without leaking BYOK headers or cookies"
    requirement: "OPS-03"
    verification:
      - kind: unit
        ref: "backend/tests/test_error_handlers.py::TestRequestLoggingMiddleware"
        status: pass
    human_judgment: false

  - id: D4
    description: "External uptime monitor on /health (UptimeRobot)"
    requirement: "OPS-02"
    verification: []
    human_judgment: true
    rationale: "UptimeRobot requires interactive account sign-up — no CLI/API path available without account creation"

duration: 10min
completed: 2026-08-04
status: checkpoint
---

# Phase 08-07: CI Gate, Exception Logging, and Uptime Monitor

**GitHub Actions CI gate (pytest + build/lint), structured exception logging with exc_info, and a redacting request-logging middleware — two of three tasks complete, uptime monitor requires human setup.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-08-04T14:00:00Z
- **Completed:** 2026-08-04T14:10:00Z
- **Tasks:** 2/3 complete (Task 3 at checkpoint)
- **Files modified:** 4

## Accomplishments
- GitHub Actions CI workflow (.github/workflows/ci.yml) — backend pytest with throwaway Neo4j service container + frontend build/lint, triggered on every pull_request
- Structured exception logging — all three handlers (constraint, database, validation) now log ERROR with exc_info before sanitising
- Redacting request-logging middleware — logs method/path/status/duration in ms, never leaks X-LLM-* headers, Cookie, or Authorization values

## Task Commits

1. **Task 1: GitHub Actions CI workflow** - `3516c2c` (feat(08-07): add GitHub Actions CI workflow)
2. **Task 2: Structured exception logging and middleware** - `25479f6` (test(08-07): RED) + `7eeebd6` (feat(08-07): GREEN)

**Plan metadata:** pending

## Files Created/Modified
- `.github/workflows/ci.yml` — CI workflow: backend pytest + frontend build/lint on PR
- `backend/app/core/errors.py` — Added logging.Logger, logger.error(exc_info=exc) in all three handlers
- `backend/app/main.py` — Added _request_logging_middleware with safe-header allowlist
- `backend/tests/test_error_handlers.py` — 10 tests: 4 exception logging + 6 middleware (redaction)

## Decisions Made
- CI Neo4j tag: `neo4j:2026.06.0-community` — matching docker-compose.yml, pinned patch (not floating)
- Node version: "24" — satisfies jsdom@30.0.1 engines constraint
- setup-uv: pinned to commit SHA `08807647e7069bb48b6ef5acd8ec9567f424441b` (v8.1.0)
- No deploy step — Render/Vercel native git-push auto-deploy covers deployment (D-18)
- Middleware allowlist: only User-Agent, Content-Type, Accept are logged

## Deviations from Plan

None — plan executed exactly as written. TDD for Task 2 followed RED (commit `25479f6`) → GREEN (commit `7eeebd6`).

## Issues Encountered

None.

## User Setup Required

**External uptime monitor** (Task 3) — see checkpoint below.

---

*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04 (Tasks 1-2), Task 3 at checkpoint*
