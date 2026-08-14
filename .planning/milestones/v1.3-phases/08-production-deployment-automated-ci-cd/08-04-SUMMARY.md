---
phase: 08-production-deployment-automated-ci-cd
plan: 04
subsystem: security
tags: [csrf, cookie, samesite, auth]
status: complete
completed: 2026-08-04
---

# Phase 08 — Plan 08-04 Summary: Fail-closed CSRF + settings-driven SameSite

**`verify_origin` now fails closed on missing Origin/Referer (SEC-02,
docs/PROBLEMS.md #10), `POST /api/auth/logout` carries the same CSRF
dependency as `google_auth` (D-11), and the session cookie's `SameSite`
policy is settings-driven (`SESSION_COOKIE_SAMESITE`, default `lax` — correct
for the same-site custom-domain layout, D-10).**

## Accomplishments
- `verify_origin`: the final "no Origin/Referer → allow" branch now raises 403 `AUTH_ORIGIN_NOT_ALLOWED` instead of passing through (fail closed; browsers always send Origin on POSTs, so absence signals a non-browser client)
- `logout`: added `_csrf: Annotated[None, Depends(verify_origin)]` in the same position `google_auth` declares it — logout can no longer be CSRF-forged from a cross-site page
- `_make_cookie`/`_delete_cookie`: `samesite` now reads `get_settings().session_cookie_samesite` (default `"lax"`) instead of the hardcoded literal
- `config.py`: new `session_cookie_samesite: str = Field(default="lax", ...)` — per-environment policy (strict/none available deliberately)
- `FRONTEND_ORIGINS` unchanged — remains the single CSRF/CORS allowlist source of truth (D-12, regression-tested)

## Commits
1. `4c55a86` test(08-04): fail-closed verify_origin, logout CSRF, settings-driven SameSite (RED, executor — died on 429 after RED; GREEN completed inline by orchestrator)
2. `GREEN` feat(08-04): fail-closed verify_origin + logout CSRF + settings-driven SameSite (orchestrator-inline; SHA recorded in git log)
3. `docs(08-04)` SUMMARY + STATE/ROADMAP tracking

## Verification
- `pytest backend/tests/test_auth.py -q` → **42 passed** (15 new RED tests now green: no-Origin/Referer → 403; logout without matching origin → 403 instead of 204; logout with matching origin → 204 + session revoked; cookie samesite from settings, default lax)
- Deployed behavior unchanged for the live app: google_auth + logout still work with browser-supplied Origin

## Deviation
- Executor died on HTTP 429 after committing only the RED; the GREEN (3 small patches + config field) was implemented and verified inline by the orchestrator. No scope change.

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
