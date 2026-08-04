---
phase: 08-production-deployment-automated-ci-cd
plan: 08
subsystem: docs
tags: [deployment, docs, doc-03]
status: complete
completed: 2026-08-04
---

# Phase 08 — Plan 08-08 Summary: DEPLOYMENT.md rewrite

**`docs/DEPLOYMENT.md` now describes the real, shipped production stack
(Vercel + Render + Neo4j AuraDB Free + Upstash Redis, `spoilerless.net`
subdomains) with accurate CI, rollback, environment variables, and safety
sections — the "no production deployment target defined" framing is gone.**

## Performance
- Duration: ~20 min (single-file rewrite, no code changes)
- Tasks: 1 (the plan defines a single auto task)
- Files modified: 1

## Accomplishments
- Replaced "Detected Deployment Targets" / "no production deployment target
  defined" with a production hosting stack table (Vercel Hobby, Render free,
  Neo4j AuraDB Free, Upstash Redis, Cloudflare, Google OAuth)
- Documented platform config files (`render.yaml`, `vercel.json`,
  `.github/workflows/ci.yml`) with their purposes
- Documented AuraDB Free credential ceiling (single admin credential —
  `CREATE USER`/custom RBAC is paid-tier only)
- Documented Redis as gating rate limiting + graph cache (no-ops without
  `REDIS_URL`)
- Kept the existing "Local Deployment" Docker Compose section with a note
  that it is not part of any production deployment path
- Rewrote "Build Pipeline" to describe the committed GitHub Actions CI
  workflow (`.github/workflows/ci.yml`, two jobs, throwaway Neo4j service
  container, pinned patch tag)
- Rewrote "Environment Setup" to list every environment variable by name
  only, grouped by platform (Render, Vercel, Upstash) — no real values
- Replaced "Pre-production safety gaps" with "Production Safety": what this
  phase closed (secure cookie, admin role, CSRF, BYOK, rate limiting, cache,
  CI gate), known gaps deferred to Phase 9, and 08-07 items not yet shipped
  (structured logging, request middleware, external uptime monitor)
- Rewrote "Rollback" with real Render/Vercel dashboard procedures and an
  explicit statement that AuraDB Free has no automated backup/restore
- Rewrote "Monitoring" to describe `/health`, the planned UptimeRobot
  monitor (08-07 Task 3, human-provisioned — not yet configured), and
  platform-level monitoring

## Verification
- `! grep "no production deployment target defined" docs/DEPLOYMENT.md` ✓
- `grep "spoilerless.net" docs/DEPLOYMENT.md` ✓
- `! grep -E "NEO4J_PASSWORD\s*=\s*[A-Za-z0-9]" docs/DEPLOYMENT.md` ✓
  (no real credential leaked)

## Task Commits
1. `8bdf633` docs(08-08): rewrite DEPLOYMENT.md for the real production hosting stack

## Deviations from Plan
- None. The plan's single task was executed as specified.

## Notes
- 08-07 Tasks 2 (structured logging/middleware) and 3 (UptimeRobot)
  are not yet shipped — the doc explicitly notes these as "pending 08-07
  completion" in the Production Safety and Monitoring sections.
- 08-07 Task 1 (CI workflow) is committed and documented as the CI gate.

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
