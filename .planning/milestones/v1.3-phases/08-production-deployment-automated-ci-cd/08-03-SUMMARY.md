---
phase: 08-production-deployment-automated-ci-cd
plan: 03
subsystem: auth
tags: [admin-role, authorization, authz, fastapi, neoj4, appuser, changeset, candidates, settings]

# Dependency graph
requires:
  - phase: 08-02
    provides: BYOK LLM chat (browser-held key/base_url/model per-request X-LLM-* headers); /api/settings/llm retained as admin-only server-fallback surface
  - phase: 08-01
    provides: secure cookie defaults (Secure=True), certifi TLS trust, production hosting skeleton the login flow runs on
provides:
  - role field ("admin" | "user") on AppUser, assigned server-side from ADMIN_EMAILS at every login (never client input)
  - require_admin FastAPI dependency + RequireAdminDependency alias layered on require_current_user
  - 403 admin gate on candidate approve/reject/edit, ChangeSet confirm, and GET/PUT /api/settings/llm
affects: [08-04 (cookie/CSRF), 09-01+ (revision-revert ownership — AUTH-03 explicitly excludes revert here), frontend candidate-review UI, docs/API.md route-auth table]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Admin role derived at login from a server env allowlist (ADMIN_EMAILS), persisted and re-synced on every login, enforced by a dependency-scoped FastAPI guard"
    - "Real-app integration auth helper: test AppUser + Session rows created via production repositories on a fresh driver/loop, cookie set on TestClient, rows deleted in teardown (never touches real user rows)"

key-files:
  created:
    - .planning/phases/08-production-deployment-automated-ci-cd/08-03-SUMMARY.md
  modified:
    - backend/app/core/config.py
    - backend/app/domain/auth.py
    - backend/app/repository/user.py
    - backend/app/services/auth.py
    - backend/app/api/auth.py
    - backend/app/api/deps.py
    - backend/app/api/candidates.py
    - backend/app/api/change_set.py
    - backend/app/api/settings.py
    - backend/tests/test_auth.py
    - backend/tests/test_candidate_review.py
    - backend/tests/test_change_set_confirmation.py
    - backend/tests/test_settings_api.py

key-decisions:
  - "Role is recomputed from ADMIN_EMAILS membership on EVERY login and re-synced via ON MATCH SET u.role = $role — removing an email demotes the user on next sign-in (nothing prevents demotion; plan-authorized discretion)"
  - "GET_USER_BY_ID_QUERY coalesces u.role to 'user' — pre-migration records behind live sessions never fail validation"
  - "require_admin 403 uses the existing lowercase 'forbidden' code from _ERROR_SPECS[403] (docs/PROBLEMS.md #20 casing — no new uppercase code)"
  - "Only ChangeSet confirm is gated; propose/reject/revert keep CurrentUserDependency-only gating (AUTH-03's 'ChangeSet approval endpoints' read as the confirm/apply action; revision-revert is Phase 9/PROB-01 scope)"
  - "GET/PUT /api/settings/llm survive as admin-only server-fallback configuration rather than retirement — BYOK covers the per-user path"
  - "candidates.py ingest/list/get stay anonymous exactly as today (auth/ownership on those is Phase 9/PROB-01 scope)"

patterns-established:
  - "Dependency alias per authz level: RequireAdminDependency = Annotated[dict[str, Any], Depends(require_admin)], layered on require_current_user"
  - "Real-app integration tests authenticate through real :AppUser + :Session rows on a fresh driver/loop with teardown deletion"

requirements-completed: [AUTH-03, AUTH-04]

# Coverage metadata
coverage:
  - id: D1
    description: "AppUser role field (admin | user), assigned and re-synced server-side from ADMIN_EMAILS membership at login only; no request body can set role"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/tests/test_auth.py#TestAdminRole::test_login_with_admin_email_grants_admin_role_on_first_login"
        status: pass
      - kind: integration
        ref: "backend/tests/test_auth.py#TestAdminRole::test_login_with_email_absent_from_admin_emails_grants_user_role"
        status: pass
      - kind: integration
        ref: "backend/tests/test_auth.py#TestAdminRole::test_admin_demoted_when_email_removed_from_admin_emails"
        status: pass
      - kind: integration
        ref: "backend/tests/test_auth.py#TestAdminRole::test_empty_admin_emails_means_no_implicit_admin"
        status: pass
      - kind: integration
        ref: "backend/tests/test_auth.py#TestAdminRole::test_google_auth_request_rejects_client_supplied_role"
        status: pass
    human_judgment: false
  - id: D2
    description: "Candidate approve/reject/edit return 403 forbidden for an authenticated non-admin and succeed for an admin"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/tests/test_candidate_review.py#TestCandidateApprove::test_approve_forbidden_for_non_admin"
        status: pass
      - kind: integration
        ref: "backend/tests/test_candidate_review.py#TestCandidateReject::test_reject_forbidden_for_non_admin"
        status: pass
      - kind: integration
        ref: "backend/tests/test_candidate_review.py#TestCandidateEdit::test_edit_forbidden_for_non_admin"
        status: pass
      - kind: integration
        ref: "backend/tests/test_candidate_review.py#TestCandidateApprove::test_approve_returns_200"
        status: pass
    human_judgment: false
  - id: D3
    description: "ChangeSet confirm returns 403 for a non-admin and proceeds normally for an admin; propose/reject/revert unchanged for any authenticated user"
    requirement: AUTH-03
    verification:
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_confirm_requires_admin_role_403_for_non_admin"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_confirm_succeeds_when_progress_is_unchanged_since_propose"
        status: pass
      - kind: integration
        ref: "backend/tests/test_change_set_confirmation.py#test_reject_makes_no_mutation_and_a_subsequent_confirm_fails"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET and PUT /api/settings/llm both require the admin role (403 for non-admin, succeed for admin); 403 uses lowercase 'forbidden' code"
    requirement: AUTH-04
    verification:
      - kind: integration
        ref: "backend/tests/test_settings_api.py#test_get_and_update_llm_settings_require_admin_role"
        status: pass
      - kind: integration
        ref: "backend/tests/test_settings_api.py#test_get_and_update_llm_settings_roundtrip"
        status: pass
    human_judgment: false

# Metrics
duration: 35min
completed: 2026-08-04
status: complete
---

# Plan 08-03: Admin role — candidate review, ChangeSet confirm, and /api/settings/llm gated to admin

**AppUser gains a server-derived role ("admin" | "user") from ADMIN_EMAILS at every login, and require_admin gates candidate approve/reject/edit, ChangeSet confirm, and GET/PUT /api/settings/llm with a clear 403 for non-admins — closing the anonymous graph-poisoning gap (docs/PROBLEMS.md #2, REQUIREMENTS.md AUTH-03/AUTH-04)**

## Performance

- **Duration:** 35 min
- **Started:** 2026-08-04
- **Completed:** 2026-08-04
- **Tasks:** 2 (both TDD)
- **Files modified:** 13

## Accomplishments

- Admin role field on AppUser, persisted and re-synced on every login solely from ADMIN_EMAILS membership (empty ADMIN_EMAILS ⇒ every user is "user" — no implicit admin); UserPublic exposes role with a "user" default
- No API surface accepts a client-supplied role: GoogleAuthRequest extra="forbid" rejects unknown fields, role is computed only after Google verification, and no route takes a role parameter (T-08-03-03 mitigated)
- `require_admin` dependency + `RequireAdminDependency` alias in deps.py, using the existing lowercase "forbidden" 403 code
- 403 admin gates on candidate approve/reject/edit (T-08-03-01), ChangeSet confirm only (T-08-03-02; propose/reject/revert intentionally unchanged), and GET/PUT /api/settings/llm (T-08-03-04)
- Real-app integration auth pattern in test_candidate_review.py: test AppUser + Session rows created via production repositories on a fresh driver/loop, cookie set on TestClient, rows deleted in teardown — no real user rows touched, no cross-loop driver crashes

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Role field — persistence, assignment, domain model** - `037d43c` (test) + `573462e` (feat)
2. **Task 2: Enforce admin role on candidate review, ChangeSet confirm, and LLM settings** - `11acd74` (test) + `abbb7e7` (feat)
3. **Collateral auto-fix: role-aware fakes in change_set_api/revision suites** - `82cdca5` (fix, after full-suite verification)

**Plan metadata:** plan file 08-03-PLAN.md (no separate plan commit — plan authored in place)

## Files Created/Modified

- `backend/app/core/config.py` - `admin_emails` setting (comma-separated allowlist, empty = no admin), same Field pattern as allowed_emails
- `backend/app/domain/auth.py` - `role: Literal["admin", "user"] = "user"` on UserPublic
- `backend/app/repository/user.py` - upsert gains `role` param, set on ON CREATE + ON MATCH; RETURN includes role; GET_USER_BY_ID_QUERY coalesces role to "user"
- `backend/app/services/auth.py` - `AuthService.authenticate(..., admin_emails=...)` computes role post-verification and passes to upsert
- `backend/app/api/auth.py` - `_admin_emails()` helper; google_auth passes admin_emails to authenticate (only edit to this file)
- `backend/app/api/deps.py` - `require_admin` + `RequireAdminDependency` layered on require_current_user
- `backend/app/api/candidates.py` - `_admin: RequireAdminDependency` on approve_candidate/reject_candidate/edit_candidate only
- `backend/app/api/change_set.py` - `_admin: RequireAdminDependency` on confirm_change_set only
- `backend/app/api/settings.py` - `_user: CurrentUserDependency` → `_admin: RequireAdminDependency` on get_llm_settings/update_llm_settings
- `backend/tests/test_auth.py` - Task 1 role tests (admin grant/persist/demote/empty-allowlist/UserPublic/forbid-role)
- `backend/tests/test_candidate_review.py` - real-app admin/user session fixtures; 403 tests for approve/reject/edit; existing 200/404 tests now admin-authenticated
- `backend/tests/test_change_set_confirmation.py` - FakeUserRepo + `_authed` role support; confirm-ing tests act as admin; new 403 non-admin confirm test proving zero mutation + reject still reachable
- `backend/tests/test_settings_api.py` - FakeUserRepo + `_authed` role support (default admin); new 403 non-admin GET/PUT test

## Decisions Made

- Role re-syncs on every login (ON MATCH SET) so ADMIN_EMAILS removals demote on next sign-in — plan-authorized discretion, nothing prevents demotion
- `GET_USER_BY_ID_QUERY` coalesces role to "user" defensively for pre-migration records behind live sessions
- 403 code is the existing lowercase "forbidden" (no new uppercase code — PROBLEMS.md #20)
- Only confirm is ChangeSet-gated (scoped AUTH-03 reading); revision-revert stays Phase 9/PROB-01
- /api/settings/llm survives as admin-only rather than retired (BYOK covers per-user path)
- candidates ingest/list/get remain anonymous (Phase 9 scope)

## Deviations from Plan

None beyond one auto-fixed collateral test break (below) — the plan itself
was executed exactly as written.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Full suite: change_set confirm/revert suites 403'd after the admin gate landed**
- **Found during:** final full-suite verification (after Task 2 GREEN)
- **Issue:** `test_change_set_api.py` and `test_change_set_revision.py` have
  their own `FakeUserRepo` (no `role` key) and `_authed` helpers; their
  confirm steps hit the new `require_admin` gate, and a missing role key
  resolved to non-admin → every confirm/revert test failed with 403.
- **Fix:** added the `role` field to both fakes' `upsert` records and defaulted
  their `_authed(...)` actors to `role="admin"` with an explanatory comment
  (both suites exercise admin-only actions — confirm, and revert which always
  confirms first; role gating itself is covered by
  test_change_set_confirmation.py).
- **Files modified:** backend/tests/test_change_set_api.py,
  backend/tests/test_change_set_revision.py
- **Verification:** `pytest backend/tests/test_change_set_api.py backend/tests/test_change_set_revision.py -q` → 27 passed
- **Committed in:** `82cdca5` (fix(08-03), directly after the Task 2 GREEN)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary consequence of the Task 2 gate; no scope creep.

## Issues Encountered

- Existing candidate-review tests called approve/reject/edit anonymously (200 expected); once the admin gate lands those become 401. Reworked them to authenticate as an admin via real AppUser+Session rows (fresh driver/loop pattern) — this is the plan's own "admin succeeds (200)" test requirement, not a deviation.
- Existing change_set/settings tests used FakeUserRepo records without a role key; require_admin treats a missing role as non-admin, which would have 403'd every existing test. Extended both fakes with a role field (mirroring test_auth.py's Task 1 fake).
- Full-suite run: 413 passed, 16 failed — 8 of the 16 were the change_set_api/
  change_set_revision collateral break (auto-fixed above; those files now pass
  27/27); the remaining 8 were `test_seed_idempotency.py` (3 tests) and
  `test_change_set_api.py` confirm tests pre-fix. `test_seed_idempotency.py`
  still fails standalone against the hardcoded `{"nodes": 41, "relationships":
  26}` count because the shared live DB carries leftover candidate-origin rows
  from ingestion tests — **pre-existing, documented debt** (STATE.md Blockers,
  logged to deferred-items.md), not introduced by 08-03.
- Live DB note: the shared `:AppSetting {key:'llm'}` node holds the user's real config; test_settings_api.py's backup/restore fixture (pre-existing) protects it. Neo4j emits pre-existing "property key does not exist" warnings for `synopsis_visible_from_order`/`image_visible_from_order` during seeding — unrelated schema drift, not introduced here.

## User Setup Required

None - no external service configuration required. Operators grant admin by adding emails to `ADMIN_EMAILS` (comma-separated; empty = no admin until set).

## Next Phase Readiness

- 08-04 (cookie/CORS/CSRF hardening) can proceed — deps.py/auth.py untouched by cookie logic beyond the one admin_emails helper
- Phase 9 PROB-01 (ownership on ingest/list/get + revision revert) now has the require_admin precedent to reuse
- docs/API.md's route-auth table will need the new 403 responses noted when next regenerated

---
*Phase: 08-production-deployment-automated-ci-cd*
*Completed: 2026-08-04*
