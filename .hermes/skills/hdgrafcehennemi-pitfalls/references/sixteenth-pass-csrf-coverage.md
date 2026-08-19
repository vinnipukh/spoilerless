# SIXTEENTH PASS — CSRF coverage beyond login/logout (2026-08-12)

Closed the second ARCHITECTURE.md "Normative follow-ups" gap: every
cookie-authenticated state-changing route must validate Origin/Referer,
not just `/api/auth/google` + logout.

## Fix shape (commit 69b7830)

- `verify_origin`, `_allowed_origins`, `AUTH_ORIGIN_NOT_ALLOWED` moved
  `api/auth.py` → `api/deps.py` (shared deps module; auth.py re-exports
  for backward compat). New `CsrfGuardDependency = Annotated[None,
  Depends(verify_origin)]`.
- Guard wired into ALL 26 cookie-auth write routes as `_csrf:
  CsrfGuardDependency` (underscore-ignored param, declared AFTER the auth
  dep so unauthenticated 401 fires before the 403): candidates
  (ingest/approve/reject/edit), change_set (propose/confirm/reject/revert),
  chat (create/delete session, post/stream message), progress update,
  revisions revert, settings llm update, share (create/revoke),
  user_content (notes + custom nodes/relationships CRUD).
- Exempt: POST `/graph/path` (`OptionalUserDependency`, read-only — no
  state change, CSRF not applicable).

## Pitfall 1 — manual route inventory misses routes; write a static scan

The hand-enumerated list omitted `POST /candidates/ingest`. A static
inventory test caught it:

```python
def test_every_cookie_authenticated_state_changing_route_has_csrf_guard():
    # for each api module's router.routes:
    #   methods & {POST,PUT,PATCH,DELETE} and "CurrentUserDependency" or
    #   "RequireAdminDependency" in str(inspect.signature(route.endpoint))
    #   => "CsrfGuardDependency" must be present, else violation
```

Import the api modules explicitly (`from spoilerless.app.api import auth,
candidates, ...`) — `dir(api_pkg)` has no `*_router` exports. Textual
signature scan mirrors the existing D-20 query-constant scan style. Any
future write route added without the guard fails this test.

## Pitfall 2 — adding an auth dep to many routes breaks the whole suite

TestClient sends NO Origin header; `verify_origin` fails closed (no
Origin/Referer → 403 AUTH_ORIGIN_NOT_ALLOWED). Every authenticated write
test in the suite 403'd the moment the guard went in.

Fix: conftest autouse fixture `_csrf_bypass_default` sets
`FRONTEND_ORIGINS=*` (monkeypatch + `get_settings.cache_clear()`) before
every test — MUST skip `test_config` (`"test_config" in
request.node.module.__name__`), whose production-safe-defaults assertion
requires the pristine unset-env default (`frontend_origins ==
"http://localhost:5173"`, not `*`). CSRF-specific tests pin a concrete
origin via monkeypatch.setenv + cache_clear and assert 403/200.

## Pitfall 3 — dependency order matters for 401-vs-403

Declare `user: CurrentUserDependency` (or `_admin`) BEFORE `_csrf` in the
signature: FastAPI resolves dependencies left-to-right, so
unauthenticated requests get the 401 (existing tests asserting 401 keep
passing) instead of a confusing 403.

## Behavioral test shape (test_progress_api.py)

`_restrict_csrf_origin(monkeypatch)` (setenv `FRONTEND_ORIGINS=...` +
cache_clear), authed user via in-memory session repo, then three
assertions on `POST /progress`: evil Origin → 403, missing Origin → 403
(fail closed), matching Origin → 200.
