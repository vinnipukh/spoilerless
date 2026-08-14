---
phase: 09
slug: feature-expansion-full-audit-remediation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-05
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x (asyncio_mode=auto, root pyproject) + vitest 4.x (jsdom) |
| **Config file** | `pyproject.toml` (testpaths=backend/tests) / `frontend/vite.config.ts` |
| **Quick run command** | `uv run pytest backend/tests/test_<target>.py -x` (repo root) |
| **Full suite command** | `uv run pytest -q` + `cd frontend && NODE_ENV=test CI=1 npm run test` |
| **Estimated runtime** | ~300s backend, ~90s frontend |

---

## Sampling Rate

- **After every task commit:** Run the plan's named test files (`uv run pytest backend/tests/test_X.py -x` / targeted vitest)
- **After every plan wave:** Run `uv run pytest -q` + `NODE_ENV=test CI=1 npm run test` (frontend only when wave touches FE)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner per task) | 09-NN | wave | PROB-xx / FEAT-xx | T-09-NN / — | fail-closed per spec | unit/integration | `uv run pytest ...` or vitest | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_seed_idempotency.py` — scratch-series + teardown isolation (PROB-22)
- [ ] `backend/tests/test_auth.py` — real `ProductionGoogleVerifier` behavioral test (PROB-23)
- [ ] `backend/tests/test_retrieval_pipeline.py` — notes accumulator bucket (PROB-24)
- [ ] `backend/tests/test_progress_api.py` — FE wire-shape contract tests without mocked client (PROB-23)

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI re-run green on main after 09-02 merge | PROB-08/09-02 | needs operator GitHub push + Actions tab | merge `ci-smoke-test` fixes (already on local main), push, confirm backend pytest + frontend build/lint green |
| Admin-role live check with `ADMIN_EMAILS` configured | AUTH-03/09-03 | operator env config | set `ADMIN_EMAILS` on Render, verify candidate approve/reject/edit + ChangeSet confirm gated, non-admin 403 |
| `REDIS_URL` set on Render, live 429 + cache invalidation | SEC-03/INFRA-02/09-04 | operator env config | set Upstash `rediss://`, verify 429 after N rapid logins, cache hit/invalidate live |
| Live reseed/sweep (zombie AppUser/Session) | PROB-22 | destructive on shared AuraDB, operator sign-off | run sweep script against Aura, verify counts drop, seed tests green after |
| UptimeRobot alert fires on outage | OPS-02 | third-party account | trigger test alert, confirm email |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
