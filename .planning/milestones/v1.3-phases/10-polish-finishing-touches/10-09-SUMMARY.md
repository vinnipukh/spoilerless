---
phase: 10-polish-finishing-touches
plan: 09
subsystem: testing
tags: [regression, docker, neo4j, ephemeral, test-runner, polish-01, gate]

# Dependency graph
requires:
  - phase: 10-polish-finishing-touches
    provides: 10-03/10-06 OpenAPI inventories (52/39), 10-05/10-07 frontend suites, 10-08 benchmark harness
provides:
  - Guarded ephemeral-container backend runner (only full-suite entrypoint; fail-closed target guards; proven teardown)
  - Chunk inventory gate (every test_*.py exactly once)
  - Seven-red baseline honestly retired (zero known failures)
  - POLISH-01 automated closeout gate evidence
affects: [10-10 UAT, 10-11 docs/coverage audit]

# Actuals (#2632) — pairs with the plan's `estimate` (30000 tokens) on the same scale (chars/4 over the realized diff).
actuals:
  tokens: 17600
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Ephemeral-target discipline: random password + loopback ports + no volume mounts; refuses ambient env overrides, dev containers, remote URIs, pre-existing names
    - Effective-Settings probe before testing (proves alias resolution + 0-node target)
    - finally-teardown with absence verification (docker rm -f -v + inspect)

key-files:
  created:
    - scripts/run_phase10_backend_tests.py
    - spoilerless/tests/test_phase10_test_runner.py
  modified:
    - scripts/run_backend_tests.py
    - docs/TESTING.md
    - docs/PROBLEMS.md

key-decisions:
  - "The seven-red baseline was retired by root-cause repair, not whitelisting: inventory reds were stale expectations fixed by 10-03/10-06; seed-image reds fixed by the 08-12 portrait restore; constraint-name reds are engine-tolerant on 2026.06.0."
  - "The guarded runner is the ONLY full-suite entrypoint — the developer container and any persistent/live target are refused at the guard layer (T10-LEAK-09)."
  - "Full suite on the ephemeral container: 11/11 chunks green in 90s wall (was ~43min on the shared live DB — per-test reseed eliminated)."

patterns-established:
  - "Pattern 1: fail-closed test infra — every ambient override, remote target, and pre-existing container is a hard refusal with a TargetRefusal error."
  - "Pattern 2: chunk inventory asserted at startup against the test directory — new test files can never silently fall out of CI."

requirements-completed: [POLISH-01]
coverage:
  - id: D1
    description: "Guarded ephemeral-container runner with fail-closed target guards and proven teardown (18 mock-driven guard tests, no daemon)"
    requirement: POLISH-01
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_phase10_test_runner.py"
        status: pass
      - kind: other
        ref: "run_phase10_backend_tests.py --files (8 files) → 179 passed; teardown verified: container + anonymous volumes removed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full backend suite on the ephemeral container — 11/11 chunks green (core, domain-models, series-api, graph, change-set, candidates, auth, user-content, chat-llm, contract-ops, phase10-viz)"
    requirement: POLISH-01
    verification:
      - kind: integration
        ref: "unset PYTHONPATH && uv run python scripts/run_phase10_backend_tests.py --all → All 11 chunk(s) passed in 90.0s wall; teardown verified"
        status: pass
    human_judgment: false
  - id: D3
    description: "Frontend full gate — vitest 388 passed, lint 0 errors, tsc/vite build clean, git diff --check clean"
    requirement: POLISH-01
    verification:
      - kind: unit
        ref: "NODE_ENV=test CI=1 npm --prefix frontend test -- --run → 42 files / 388 tests passed"
        status: pass
      - kind: other
        ref: "npm --prefix frontend run lint → 0 errors (12 warnings); npm run build → built in 598ms; git diff --check clean"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-08-13
status: complete
---

# Phase 10: Polish & Finishing Touches Summary

**Guarded ephemeral-container backend runner, honest seven-red retirement, and a fully green POLISH-01 automated closeout gate**

## Performance

- **Duration:** 35 min (executor built+verified Task 1; orchestrator committed and ran Task 2 inline)
- **Started:** 2026-08-13 20:39
- **Completed:** 2026-08-13 21:30
- **Tasks:** 2
- **Files modified:** 5 (2 created)

## Accomplishments
- `scripts/run_phase10_backend_tests.py`: uniquely-named `neo4j:2026.06.0-community` ephemeral container (random password, random loopback ports, no volume mounts); refuses ambient `NEO4J_*`/`aura_*` overrides, remote/Aura URIs, dev containers (`spoilerless-neo4j`, `hdgraf-neo4j`), pre-existing container/volume names; effective-Settings probe (0 nodes) before testing; always `docker rm -f -v` + absence verification
- 18 mock-driven guard tests (no daemon needed); chunk inventory asserted against the test directory at startup
- Seven-red baseline retired by root cause: 3 stale inventory expectations (fixed by 10-03/10-06), 2 seed-image reds (08-12 portrait restore), 2 engine-tolerant constraint names — no assertion weakened; PROBLEMS.md NINETEENTH PASS records it
- Full gate: backend 11/11 chunks in 90s wall on the ephemeral target (teardown verified); frontend 388 tests / lint 0 errors / build clean / diff check clean

## Task Commits

Each task was committed atomically:

1. **Task 1: guarded runner + chunk inventory gate** - `dec4058` (test)
2. **Task 1b: seven-red retirement ledger entry** - docs commit (docs)

**Plan metadata:** pending (SUMMARY + STATE.md + ROADMAP.md commit)

## Files Created/Modified
- `scripts/run_phase10_backend_tests.py` - guarded ephemeral-container runner (created)
- `spoilerless/tests/test_phase10_test_runner.py` - 18 fail-closed guard tests (created)
- `scripts/run_backend_tests.py` - 11th chunk (phase10-viz) + inventory assertion
- `docs/TESTING.md` - zero-known-failure baseline, runner as only entrypoint
- `docs/PROBLEMS.md` - NINETEENTH PASS (seven-red retirement)

## Decisions Made
- Full suite runs exclusively on the ephemeral target — the 43-minute live-DB profile was per-test reseed; the guarded runner finishes 11 chunks in 90s
- Retirement over whitelisting: every former red has a verified root-cause fix
- POLISH-01 stays unmarked until 10-11 (shared ID)

## Deviations from Plan
None - plan executed as written.

## Issues Encountered
- `docker container inspect` prints `[]` with rc=1 for missing containers — the executor's initial `_container_exists()` treated stdout as truth and produced a false REFUSED; fixed to trust the exit code.
- Executor hit its tool cap after Task 1 verification; orchestrator committed, appended the ledger entry, and ran the full Task 2 gate inline.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 10-10 UAT: all automated gates green — human golden-path testing on the deployed app is the remaining POLISH-02 evidence
- 10-11 docs/coverage audit: zero-failure baseline is the documented starting state

---
*Phase: 10-polish-finishing-touches*
*Completed: 2026-08-13*
