# 09-05 Execution Pitfalls — headers/CORS, trust nits, env consolidation

Durable gotchas from executing plan 09-05 (security headers + narrowed CORS,
settings/candidates/ontology trust fixes, series-scoped read path, root-.env
consolidation).

## pytest: parametrize argname must match the function parameter (module-collection trap)

- `@pytest.mark.parametrize(("boundary", "FORBIDDEN", "present"), [...])` over
  `def test(..., boundary, forbidden, present)` raises at COLLECTION:
  `Failed: In <file>::<test>: function uses no argument 'FORBIDDEN'`.
- This aborts collection of the ENTIRE test module — zero tests in the file run.
  `--continue-on-collection-errors` does NOT rescue other tests in the same file
  (module-level abort), and `-k` filters cannot help because collection happens first.
- Fix: rename the parametrize argname to the actual function parameter
  (`FORBIDDEN` → `forbidden`). Discovered pre-existing in test_graph_api.py
  (introduced ~7bc8791); the whole graph suite was uncollectable until fixed.
  Symptom to watch for: `pytest <file> -k <anything>` prints `1 error in <1s`
  with no tests run.

## test_settings_api.py — live :AppSetting node backup/restore + cross-loop rule

- The suite runs against the SHARED live Neo4j. The `database` fixture backs up
  the real `:AppSetting {key:'llm'}` JSON value and restores it in teardown —
  deleting the node would silently wipe the user's stored LLM key/config.
- To test a deterministic "no stored key" state, clear the node inside the test
  with a FRESH `Neo4jDatabase()` opened inside `asyncio.run(...)` — never the
  fixture `database` instance (its driver is bound to TestClient's portal loop;
  cross-loop `execute_query` crashes with 'NoneType' has no attribute 'send').
- Admin auth for settings routes: `_authed(client, fake_user_repo, session_repo)`
  upserts an admin user + sets the session cookie (AUTH-04 admin-only).

## lru_cached get_settings() — equality-gate tests need a fresh Settings()

- `core/config.py` `get_settings()` is `@lru_cache`d. New startup gates that
  compare settings against env (e.g. `verify_google_client_id_equality` —
  GOOGLE_CLIENT_ID vs VITE_GOOGLE_CLIENT_ID, both-set-only) must be unit-tested
  with `Settings(google_client_id=...)` kwargs + `monkeypatch.setenv/delenv`,
  never through the cached accessor. Keep the gate's test independent of import
  order in the test module.

## test_auth.py patterns for fail-closed assertions

- Fixtures: `client` (TestClient over `auth_app` with AuthService overridden to
  FakeUserRepo / InMemorySessionRepository / FakeGoogleVerifier); override Google
  claims via `fake_verifier.set_claims(picture=..., email=...)`.
- "No user row created" assertion: `assert fake_user_repo._store == {}` proves
  EmailNotAllowedError raised BEFORE `user_repo.upsert` (fail-closed ordering).
- Avatar sanitization: only http/https picture schemes survive; javascript:/data:
  claims → empty string.

## Service-layer 422: raise http_error() from the service, not a validator

- `http_error(422, "INVALID_REQUEST", msg)` (core/errors) works inside services —
  FastAPI renders the envelope. Do NOT add a validator on the update model when
  the route must keep "blank = keep stored key" semantics (test_settings_api
  keep-blank contract); do the strip-then-check in the service, keyed on whether
  a stored key exists. Whitespace-only key with no stored key → 422; blank with
  stored key → keep (200).

## Candidate route ↔ repository layering (NO-REPO-PRIVATE-ACCESS)

- `api/candidates.py` had three `db = repo._db` sites (approve/reject/edit) each
  followed by `db.execute_write(callback, cmd)`. Fix: add thin public methods to
  `graph/candidates.py` (`approve_claim`/`reject_claim`/`edit_claim` taking the
  tx-callback + command, delegating to `self._db.execute_write`) and call
  `repo.approve_claim(_approve, {...})`. Grep gate: `rg -c "_db"
  spoilerless/app/api/candidates.py` == 0.

## filter.py series_id scoping

- SOURCES_QUERY/EVIDENCE_QUERY already matched `Claim {series_id: $series_id}`;
  09-05 added `{series_id: $series_id}` to the endpoint node patterns
  (`->(source:Source {series_id: $series_id})`, `->(evidence:EvidenceFragment
  {series_id: $series_id})`). The six visibility WHERE clauses must stay
  byte-identical — verify with `git diff | grep '^[+-]'` filtering out the
  expected MATCH lines before committing.

## Env consolidation (PROB-30)

- Root .env only: `frontend/vite.config.ts` gets `envDir: '..'`; VITE_-prefixed
  vars (VITE_GOOGLE_CLIENT_ID, VITE_API_BASE_URL) must exist in root .env.example
  too or the DEVELOPMENT.md "root-.env-only" instructions are a lie.
- `backend/.env` must not exist (`test ! -f backend/.env`).
- Setup command canonical form (README.md): `uv run --project spoilerless python
  -m spoilerless.app.graph.setup`.

## Verification state at 09-05 close

- test_graph_api.py: 29 passed (after FORBIDDEN parametrize fix).
- test_auth.py + test_settings_api.py: 56 passed.
- Known baselines to NOT chase: test_seed_idempotency (2 failures), retrieval-tools
  seed drift. test_main_lifespan.py does NOT exist — skip its verify step.
