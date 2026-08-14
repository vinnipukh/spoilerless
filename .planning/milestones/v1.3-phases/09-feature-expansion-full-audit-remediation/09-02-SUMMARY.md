---
phase: 09-feature-expansion-full-audit-remediation
plan: 02
subsystem: testing
tags: [pytest, vitest, google-auth, httpx-mocktransport, wire-shape, regression-net]

# Dependency graph
requires:
  - phase: 09-feature-expansion-full-audit-remediation
    provides: "09-01 REBRAND rename (spoilerless/ import root, tests at spoilerless/tests/, frontend api/ tree)"
provides:
  - "Behavioral ProductionGoogleVerifier regression net (garbage token + httpx.MockTransport, zero network)"
  - "Live #42 NameError fix: google bound in verify() function scope (the regression net caught the bug the 'already fixed' claim missed)"
  - "Transport-level progress payload wire-shape tests (3 shapes, no vi.mock of the API client)"
affects: [09-03, 09-04, 09-07, PROB-14, PROB-15, PROB-23, auth code paths, progress code paths]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "httpx.MockTransport shim swapping google.auth.transport.requests.Request for verifier behavioral tests"
    - "Transport-level FE wire-shape tests replacing globalThis.fetch (chat.test.ts pattern) — never vi.mock the API client"

key-files:
  created:
    - spoilerless/tests/test_google_verifier.py
    - frontend/src/api/progress.test.ts (extended)
  modified:
    - spoilerless/app/services/auth.py
    - spoilerless/tests/test_auth.py

key-decisions:
  - "Rule 1 auto-fix: the plan premise ('#42 already fixed') was factually wrong — the lazy `from google.auth.transport import requests as google_requests` binds only google_requests, not google, so `except google.auth.exceptions.TransportError` NameErrors on ANY exception in verify(). Fixed by `import google.auth.exceptions` in the lazy-import block (binds google, matches documented intent); committed as a dedicated fix(09-02) commit so history is honest."
  - "Happy-path verifier test documented + skipped: success requires Google's live JWKS + a token signed by one of its keys — not testable offline; FakeGoogleVerifier already covers success in test_auth.py."
  - "google-auth 2.56.2 fetches signing certs BEFORE token decode, so a non-200 cert response is a TransportError (GoogleTransportError), while a 200-but-unverifiable token is a verification error (GoogleVerificationError) — documented in the test module."

patterns-established:
  - "Verifier behavioral tests: patch google.auth.transport.requests.Request module attribute (lazy import happens inside verify()) with an httpx.MockTransport-backed shim that translates httpx.TransportError -> google.auth.exceptions.TransportError; get_settings() lru_cache pitfall avoided entirely."
  - "Wire-shape tests assert the JSON-parsed body of the captured fetch call plus explicit not.toHaveProperty absence checks; rg gate for vi.mock('@/api/progress') stays clean."

requirements-completed: [PROB-14, PROB-15, PROB-23]

# Coverage metadata (#1602)
coverage:
  - id: D1
    description: "ProductionGoogleVerifier behavioral regression net — garbage token / unverifiable signature -> GoogleVerificationError (never NameError), transport failure + non-200 cert response + google-auth import failure -> GoogleTransportError, over httpx.MockTransport with zero network"
    requirement: PROB-23
    verification:
      - kind: unit
        ref: "spoilerless/tests/test_google_verifier.py#test_garbage_token_raises_verification_error_not_name_error"
        status: pass
      - kind: unit
        ref: "spoilerless/tests/test_google_verifier.py#test_transport_failure_maps_to_google_transport_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "Frontend progress payload wire-shape contract tests — the three request-body shapes (forward confirm / view-only / plain legacy) asserted against the captured fetch call at transport level, no API-client mock"
    requirement: PROB-15
    verification:
      - kind: unit
        ref: "frontend/src/api/progress.test.ts#updateProgress wire shape — parsed request body (no client mock)"
        status: pass
    human_judgment: false

# Metrics
duration: 45min
completed: 2026-08-05
status: complete
---

# Phase 09 — Plan 09-02 Summary: verifier + progress-payload regression nets

**Behavioral ProductionGoogleVerifier regression net (garbage token + httpx.MockTransport, zero network) that CAUGHT the live #42 NameError and locked the fix, plus transport-level wire-shape contract tests for the three progress payload shapes that never mock the API client.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-08-05T04:30Z (approx)
- **Completed:** 2026-08-05T05:13Z
- **Tasks:** 2 (Task 1 split into fix + test commits due to the live-bug discovery)
- **Files modified:** 4

## Accomplishments

- **The regression net caught the #42 bug live.** The plan (and 09-RESEARCH/skill) claimed the NameError was already fixed; the first test run disproved it with a `auth.py:73 NameError` traceback (locals probe: only `google_requests` bound; `except google.auth.exceptions.TransportError` NameErrors on ANY exception in `verify()`'s try block — exactly the documented #42 class). Applied the minimal Rule-1 fix (`import google.auth.exceptions` in the lazy-import block binds `google` in function scope) as a dedicated `fix(09-02)` commit so git history is honest.
- **Verifier failure contract locked behaviorally** (`spoilerless/tests/test_google_verifier.py`, 5 passed / 1 documented skip): garbage token → `GoogleVerificationError` (explicitly NOT a NameError, and a ValueError so the route 401s `AUTH_INVALID_GOOGLE_CREDENTIAL`, never 503); unverifiable signature → `GoogleVerificationError`; MockTransport raising `httpx.TransportError` → `GoogleTransportError` (the except branch that #42 NameError'd); non-200 cert response (`400 {"error_description": "Invalid value for id_token"}`) → `GoogleTransportError`; google-auth import failure → `GoogleTransportError`. Happy path documented + skipped (needs Google's live JWKS). Zero network — all over MockTransport (T-09-02-01/03).
- **#47 closed:** `test_auth.py`'s import-only `ProductionGoogleVerifier` reference removed — the verifier is now exercised, not just imported.
- **Progress payload wire shapes locked at transport level** (`frontend/src/api/progress.test.ts`, 8 passed): forward confirm → `{watched_through_order, view_as_of_order}` with `visible_until_order` ABSENT; view-only → `{view_as_of_order}` ALONE (no legacy confirm alias, no watched field); plain legacy → `{visible_until_order}` alone. Assertions run against the JSON-parsed body of the captured `globalThis.fetch` call plus URL / `method: POST` / `credentials: 'include'`. No `vi.mock('@/api/progress')` anywhere (rg gate clean) — the pattern that enshrined the #43 shipping-green bugs. `progress.ts` needed no change (08-04 per-intent builder already correct).

## Task Commits

Each task was committed atomically:

1. **Task 1a (Rule-1 auto-fix):** `a36676a` (fix) — `fix(09-02): bind google in ProductionGoogleVerifier.verify scope — #42 NameError is LIVE`
2. **Task 1b:** `86bcb50` (test) — `test(09-02): behavioral ProductionGoogleVerifier test (garbage token + MockTransport)`
3. **Task 2:** `082cb79` (test) — `test(09-02): progress payload wire-shape contract tests (fetch-level, no client mock)`

## Files Created/Modified

- `spoilerless/tests/test_google_verifier.py` (NEW) — 6 tests: 5 behavioral failure-path tests + 1 documented skip; MockTransport shim for `google.auth.transport.requests.Request`
- `spoilerless/app/services/auth.py` (MODIFIED) — `import google.auth.exceptions` added to the lazy-import block (binds `google` for the except clause; the live #42 fix)
- `spoilerless/tests/test_auth.py` (MODIFIED) — import-only `ProductionGoogleVerifier` reference removed (#47)
- `frontend/src/api/progress.test.ts` (MODIFIED) — new parsed-body wire-shape describe (3 shapes + URL/credentials assertions)

## Decisions Made

- Fix-inline decision and its evidence trail are in the Deviations section; the two-commit split for Task 1 was deliberate so the production fix is identifiable in history (git blame on `auth.py:62` shows `fix(09-02)`, not a test commit).
- Wire-shape assertions use `JSON.parse` of the captured body (order-independent) PLUS explicit `not.toHaveProperty` absence checks, per the plan's acceptance criteria.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] #42 NameError is LIVE in the tree — fixed in `verify()`**
- **Found during:** Task 1 (first run of the new regression net)
- **Issue:** The plan premise ("the #42 NameError is already fixed") was factually wrong. `from google.auth.transport import requests as google_requests` binds only `google_requests`; `except google.auth.exceptions.TransportError` (auth.py:73) therefore NameErrors on ANY exception raised inside `verify()`'s try block — verified by locals probe (`locals: ['google_requests']`) and a `NameError: name 'google' is not defined` at auth.py:73 traceback. In production this replaces the real transport error with a NameError the route cannot map → 500 instead of the documented 503/401 contract.
- **Fix:** Added `import google.auth.exceptions  # noqa: F401` as the first line of the lazy-import block — binds `google` in function scope (matching the intent documented in 09-RESEARCH/skill) and guarantees the `exceptions` submodule is imported.
- **Files modified:** `spoilerless/app/services/auth.py`
- **Verification:** `uv run pytest spoilerless/tests/test_google_verifier.py -q` → 5 passed, 1 skipped; `uv run pytest spoilerless/tests/test_auth.py -q` → 42 passed. Also a manual sanity check that the ValueError path (garbage token) and transport path (MockTransport raise) each produce the documented exception type.
- **Committed in:** `a36676a` (dedicated `fix(09-02)` commit, separate from the test commit per deviation tracking)

**2. [Rule 1 - Bug] Test-harness nits (not production):** `httpx.URL` has no `startswith` (use `.host`), and google-auth 2.56.2 certs URL is `oauth2/v1/certs` — the URL assertion now checks `request.url.host == "www.googleapis.com"` (the real contract). Fixed in the test file before commit.

---

**Total deviations:** 2 auto-fixed (2 by Rule 1; 1 production bug + 1 test-harness)
**Impact on plan:** The production fix is REQUIRED for the plan's acceptance criteria (both pytest invocations must pass) and is the exact bug class this plan exists to lock. No scope creep; the other plan assumptions held (`progress.ts` builder already correct, 08-04 fix landed fully).

## Issues Encountered

- The "already fixed" premise being wrong was the plan's central risk and materialized; resolved via Rule 1 with evidence documented above. `docs/PROBLEMS.md` #42 entry could not be marked fixed before this commit — it now genuinely is.
- Pre-existing dirty files (`.planning/config.json`, `docs/PROBLEMS.md`, untracked `.hermes/`) left untouched; explicit-path staging only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Auth and progress code paths now have red-capable regression nets before 09-03/09-04/09-07 modify them (per plan objective).
- PROB-14 (fix verified by test, not inspection) and PROB-23 are now genuinely closed; PROB-15 wire-shape coverage green.
- Known pre-existing baseline failures (test_seed_idempotency PROB-22, test_retrieval_tools PROB-20/#44) were not chased — planned for 09-08/09-18.

## Self-Check: PASSED

- `[ -f spoilerless/tests/test_google_verifier.py ]` FOUND; `[ -f frontend/src/api/progress.test.ts ]` FOUND
- Commits `a36676a`, `86bcb50`, `082cb79` verified in `git log`
- Verification evidence on disk: verifier 5 passed/1 skipped, test_auth 42 passed, vitest progress.test.ts 8 passed, `npm run build` green, rg prohibition gate clean

---
*Phase: 09-feature-expansion-full-audit-remediation*
*Completed: 2026-08-05*
