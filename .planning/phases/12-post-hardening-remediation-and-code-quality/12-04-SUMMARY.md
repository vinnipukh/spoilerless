---
phase: 12-post-hardening-remediation-and-code-quality
plan: 04
subsystem: infra
tags: [csp, content-security-policy, trustedhostmiddleware, render, vercel, fastapi]

# Dependency graph
requires:
  - phase: e90a591 (pre-phase hotfix)
    provides: CSP connect-src/style-src expansion, ALLOWED_HOSTS env var in render.yaml
provides:
  - Verified production CSP connect-src permits backend API origins (https://api.spoilerless.net, https://*.onrender.com)
  - Verified TrustedHostMiddleware safe fallback includes localhost/127.0.0.1/api.spoilerless.net/*.onrender.com/testserver when ALLOWED_HOSTS unset
  - Verified render.yaml configures ALLOWED_HOSTS for the spoilerless-api service
affects: [production-deployment, uat]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 0        # chars/4 over realized diff — zero-diff plan: all targets already satisfied at HEAD
  tasks: 2         # both tasks verified complete
  commits: 1       # docs commit for this SUMMARY only

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created:
    - .planning/phases/12-post-hardening-remediation-and-code-quality/12-04-SUMMARY.md
  modified: []   # none — all four target files already carried the required changes at HEAD

key-decisions:
  - "Plan 12-04 found pre-satisfied by commit e90a591 (ancestor of HEAD): applied only what was missing, which was nothing"
  - "Kept _trusted_hosts() frontend_origins hostname derivation (superset of plan snippet) rather than stripping to byte-match — snippet declared a guide, not byte-law"

patterns-established: []

requirements-completed: [THERMO-P1-02, THERMO-P2-01]

coverage:
  - id: D1
    description: "CSP connect-src in frontend/vercel.json + frontend/index.html includes 'self', accounts.google.com, api.spoilerless.net, *.onrender.com (style-src keeps deliberate e90a591 expansion)"
    requirement: THERMO-P1-02
    verification:
      - kind: other
        ref: "read_file frontend/vercel.json + frontend/index.html at HEAD f835565 — connect-src string matches target exactly"
        status: pass
    human_judgment: false
  - id: D2
    description: "_trusted_hosts() in spoilerless/app/main.py falls back to [localhost, 127.0.0.1, api.spoilerless.net, *.onrender.com, testserver] when settings load fails or ALLOWED_HOSTS is empty/unset"
    requirement: THERMO-P2-01
    verification:
      - kind: other
        ref: "grep spoilerless/app/main.py lines 279-294 — both fallback paths contain all five required hosts; no '*' wildcard"
        status: pass
    human_judgment: false
  - id: D3
    description: "render.yaml spoilerless-api service envVars sets ALLOWED_HOSTS=spoilerless-api.onrender.com,api.spoilerless.net,localhost,127.0.0.1"
    requirement: THERMO-P2-01
    verification:
      - kind: other
        ref: "git show e90a591 -- render.yaml + read_file render.yaml lines 17-19 — envVars entry present verbatim"
        status: pass
      - kind: other
        ref: "unset PYTHONPATH && uv run python -c 'from spoilerless.app.main import app' → IMPORT-OK"
        status: pass
    human_judgment: false

# Metrics
duration: 4min
completed: 2026-08-26
status: complete
---

# Phase 12 Plan 04: Post-Hardening Deployment Config Summary

**Production deployment configs verified CSP-permissive for API origins and TrustedHost-safe for Render hosts — all four target files already satisfied at HEAD by e90a591; zero code diffs required**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-26T00:00:00Z (approx.)
- **Completed:** 2026-08-26
- **Tasks:** 2 of 2
- **Files modified:** 0 source files (SUMMARY only)

## Accomplishments

- Verified `frontend/vercel.json` and `frontend/index.html` carry the exact target `connect-src 'self' https://accounts.google.com https://api.spoilerless.net https://*.onrender.com` at HEAD (`f835565`)
- Confirmed `style-src` was NOT regressed to the plan snippet — it retains e90a591's deliberate expansion (`'self' 'unsafe-inline' https://accounts.google.com`), per delegation guidance
- Verified `_trusted_hosts()` in `spoilerless/app/main.py` returns all five required hosts (`localhost`, `127.0.0.1`, `api.spoilerless.net`, `*.onrender.com`, `testserver`) on BOTH fallback paths: settings-load exception (line 283) and empty/unset `ALLOWED_HOSTS` (line 293)
- Verified `render.yaml` service `spoilerless-api` has the exact required `ALLOWED_HOSTS` env var entry (lines 17-19, landed by e90a591)
- Confirmed e90a591 is an ancestor of HEAD (`git merge-base --is-ancestor` → OK) so the fixes cannot be lost
- App imports cleanly: `unset PYTHONPATH && uv run python -c "from spoilerless.app.main import app"` → `IMPORT-OK`

## Task Commits

Each task was committed atomically:

1. **Task 1: Update CSP connect-src in frontend configuration** — no new commit; zero diff. Already landed in `e90a591` (in HEAD ancestry)
2. **Task 2: Fix TrustedHost fallback in main.py and render.yaml** — no new commit; zero diff. Already landed in `e90a591` (in HEAD ancestry)

**Plan metadata:** this SUMMARY commit (`docs(12-04): complete 12-04 plan summary`)

_No `feat(12-04)` commits exist because `git status` showed no modifications to any of the four target files at execution time — staging them would have produced an empty commit. Working tree contained only unrelated `.planning/` edits, which were left untouched per protocol._

## Files Created/Modified

- `.planning/phases/12-post-hardening-remediation-and-code-quality/12-04-SUMMARY.md` - this summary (created)

Pre-existing files carrying the required content (unmodified this plan):
- `frontend/vercel.json` - CSP header with expanded connect-src (e90a591)
- `frontend/index.html` - matching CSP meta tag (e90a591)
- `spoilerless/app/main.py` - `_trusted_hosts()` with safe fallbacks (lines 279-294)
- `render.yaml` - `ALLOWED_HOSTS` env var for spoilerless-api service

## Decisions Made

- **Treated the plan as a verification pass instead of forcing redundant edits.** Every change 12-04 specifies is byte-present at HEAD. Re-applying identical content would create noise commits; re-running `git add` on unchanged files produces nothing. Documented evidence trail above instead.
- **Preserved `_trusted_hosts()` frontend_origins derivation.** The current implementation derives extra hostnames from `settings.frontend_origins` before appending the five required hosts — a strict superset of the plan's snippet. Stripping it to byte-match would remove working behavior the snippet never intended to forbid ("guide, not byte-law").

## Deviations from Plan

None - plan executed exactly as written. (The plan's work being pre-landed is a discovery about repository state, not a deviation in execution.)

---

**Total deviations:** 0 auto-fixed
**Impact on plan:** None. Both must-have truths hold at HEAD.

## Issues Encountered

- Initial content-search against `main.py` returned a transient rg IO error; resolved by direct `grep` in terminal (file exists, content confirmed).
- `uv run` emitted a benign VIRTUAL_ENV path-mismatch warning; import succeeded regardless.

## User Setup Required

None - no external service configuration required. (Operator TODO already tracked in render.yaml comments re: Render proxy CIDR confirmation — out of scope for this plan.)

## Next Phase Readiness

- Production CSP and trusted-host configuration confirmed consistent across vercel.json / index.html / main.py / render.yaml
- No blockers introduced; remaining phase-12 plans unaffected

---
*Phase: 12-post-hardening-remediation-and-code-quality*
*Completed: 2026-08-26*
