# Admin role gating — backend enforcement + test patterns (plan 08-03, AUTH-03/AUTH-04)

## The dependency (backend/app/api/deps.py)

```python
async def require_admin(user: CurrentUserDependency) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise http_error(403, "forbidden", "Admin role required for this action.")
    return user

RequireAdminDependency = Annotated[dict[str, Any], Depends(require_admin)]
```

- 403 code is the EXISTING lowercase `"forbidden"` from `_ERROR_SPECS[403]` — do not invent a new code
  (casing inconsistency already flagged as docs/PROBLEMS.md #20).
- Role is assigned only after Google verification succeeds, from `config.admin_emails`
  (comma-separated, lowercased; `_admin_emails()` helper in api/auth.py mirrors `_allowed_emails()`),
  passed as `admin_emails=` to `AuthService.authenticate` and persisted by
  `UserRepository.upsert(..., role=role)`. Re-synced on EVERY login via
  `ON MATCH SET u.role = $role` → email removed from ADMIN_EMAILS demotes on next sign-in.
  Empty ADMIN_EMAILS ⇒ everyone is "user" (no implicit admin).
- `GET_USER_BY_ID_QUERY` uses `coalesce(u.role, 'user')` so pre-migration records behind live sessions
  never fail.
- Wire as `_admin: RequireAdminDependency` route param. SCOPE DISCIPLINE (08-03 example): gate ONLY what
  the requirement names — candidate approve/reject/edit, ChangeSet confirm, settings GET/PUT. NOT gated:
  ChangeSet reject/revert, candidate ingest/list/get (Phase 9/PROB-01 scope).

## Real-app integration auth (test_candidate_review.py pattern)

Exercising admin-gated routes against the REAL app (`backend.app.main`) without touching real user rows:

```python
def _create_user_with_session(role: str) -> tuple[str, str]:
    async def _run() -> tuple[str, str]:
        db = Neo4jDatabase()
        db.open()
        try:
            google_sub = f"test-{role}-{uuid4()}"
            user = await UserRepository(db).upsert(
                google_sub=google_sub,
                email=f"{google_sub}@example.com",
                display_name="Review Test User",
                avatar_url="",
                role=role,
            )
            raw_token = await Neo4jSessionRepository(db).create(user["id"], ttl_seconds=3600)
            return google_sub, raw_token
        finally:
            await db.close()
    return asyncio.run(_run())
```

- FRESH driver/loop — never the app's portal-loop driver (cross-loop `'NoneType' send` rule).
- Cookie name = `settings.session_cookie_name` (default "session"); set via
  `client.cookies.set("session", raw_token)`.
- Teardown deletes only test-created rows (works even when the session node is missing):
  `MATCH (u:AppUser {google_sub: $sub}) OPTIONAL MATCH (u)-[:HAS_SESSION]->(s:Session) DETACH DELETE u, s`
  run via `asyncio.run(...)` on a fresh `Neo4jDatabase()`.

## THE pitfall: a new authz gate 403s every parallel test fake missing `role`

- Five independent `FakeUserRepo` classes + `_authed` helpers exist: test_auth.py (role-aware since
  Task 1), test_settings_api.py, test_change_set_confirmation.py, test_change_set_api.py,
  test_change_set_revision.py.
- `user.get("role") != "admin"` treats a MISSING role key as non-admin. After landing the gate, any suite
  exercising the gated route fails with 403 (observed on 08-03: 5 fails test_change_set_api + 8 fails
  test_change_set_revision in the full suite; the plan's own three named test files were reworked in the
  RED commit, the other two were collateral found by the full run).
- Before adding ANY new authz dependency: `rg -n "class FakeUserRepo|def _authed" backend/tests/` and
  give every fake a `role` field (upsert `role: str = "user"` param + `"role": role` in the record).
- Where a suite ONLY exercises admin actions (confirm; revert always confirms first), default its
  `_authed(...)` actor to `role="admin"` with a comment — role gating itself lives in the dedicated
  suite. Settings roundtrip suite: default admin; 403 tests pass `role="user"` explicitly.
- RED-phase note: new 403 tests fail BEFORE the gate exists with "expected 403, got 200" — a genuine RED;
  existing 200-tests keep passing pre-gate, so the RED signal is only the new tests.

## Full-suite evidence caveats

- `test_seed_idempotency.py` asserts EXACT seed counts (`{"nodes": 41, "relationships": 26}`) and fails
  once ANY candidate-origin rows linger in the shared live DB. It fails STANDALONE too — residue
  accumulates ACROSS sessions (e.g. test_candidate_review's `ingested_claim_id` fixture ingests claims
  without teardown; test_candidate_ingest leaves rows), not just within one run's ordering.
  Pre-existing, documented debt (STATE.md Blockers) — log to deferred-items.md, do not "fix" inside an
  unrelated plan.
- 08-03 final evidence: plan-named suites 63 passed; change_set collateral files 27 passed; full suite
  `pytest backend/tests/ -q` → 426 passed / 3 failed, all 3 = the seed_idempotency debt.
