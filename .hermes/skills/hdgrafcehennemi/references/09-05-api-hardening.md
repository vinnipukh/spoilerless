# 09-05 API hardening — execution + resume state (2026-08-05)

Plan 09-05 (PROB-09/17/19/29/30). Executor died at tool-iteration budget
mid-Task-1 verification: **build RED, ZERO commits landed**. Full resume
state + durable patterns below. Read before resuming Phase 9.

## Resume state — Task 1 (PROB-09/#20) 100% implemented, backend+frontend tests green, build RED

Uncommitted working tree (stage EXPLICIT paths only; never `.planning/config.json`;
**delete `scripts/sweep_error_codes_09_05.sh` before committing** — one-shot tool):

- `spoilerless/app/core/errors.py` — `ERROR_CODES` frozenset (33 codes) +
  pattern `^[A-Z][A-Z0-9_]*$` + `field_validator _code_must_be_registered`
  (validation references the registry; contract test references it too).
- Mechanical quoted-literal sweep across `spoilerless/app` + `spoilerless/tests`
  (32 files) + docs (`frontend-api-contract.md`, `API.md`, `CONFIGURATION.md`,
  `PROJECT-SPEC.md` — code references only).
- `spoilerless/tests/test_openapi_contract.py` — 2 new tests:
  `test_every_openapi_error_code_is_uppercase_and_registered` (walks every
  response example + ErrorDetail schema `code` examples),
  `test_registry_codes_all_match_uppercase_pattern`.
- `spoilerless/tests/test_frontend_contract_doc.py` + the doc it locks
  (backticked code list + JSON envelope string all uppercased).
- Frontend: `client.ts` (`INVALID_REQUEST` array-shape, `UNKNOWN_ERROR`
  fallback), `client.test.ts` (NEW, 10 tests), `AuthProvider.tsx` (legacy
  `'unauthenticated'` alias removed), `ChangeSetCard.tsx` (`CHANGESET_STALE`),
  `ChatPanel.tsx` (`TOO_MANY_REQUESTS`), `api/chat.test.ts` + `progress.test.ts`
  + `changeSet.test.ts` + `ChangeSetCard.test.tsx` swept.

VERIFIED GREEN: `uv run pytest spoilerless/tests/test_openapi_contract.py
spoilerless/tests/test_frontend_contract_doc.py spoilerless/tests/test_error_handlers.py
-x -q` → 22 passed; `NODE_ENV=test CI=1 npx vitest run` → 258/258.

**BLOCKER (one line):** `npm run build` →
`src/api/client.test.ts(16,33): error TS2353: Object literal may only specify
known properties, and 'loc' does not exist in type '{ msg?: string | undefined; }'`.
The `ApiError` constructor param is `Array<{ msg?: string }>`; the test payload
`{ loc, msg, type }` (the REAL FastAPI validation-error shape) is too wide.
Fix: widen the constructor param to `Array<{ loc?: unknown; msg?: string;
type?: string }>` (matches reality) OR drop loc/type from the test payload.
Then re-run build; commit
`feat(09-05): uppercase error-code registry + contract test + client normalization (PROB-09)`.

## Task 2/3 designs (context already gathered — do not re-derive)

Task 2 (security headers + CORS, PROB-17/#38):
- `main.py`: `_security_headers_middleware` http-middleware registered after
  CORS, MUTATING call_next's response (streaming-safe), setting:
  CSP `default-src 'self'; script-src 'self' https://accounts.google.com;
  img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; font-src 'self';
  connect-src 'self' https://accounts.google.com; frame-src https://accounts.google.com;
  object-src 'none'; base-uri 'self'; form-action 'self'`
  (Google Identity Services loads `https://accounts.google.com/gsi/client` —
  `frontend/index.html:16`), HSTS `max-age=31536000; includeSubDomains`,
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`.
- CORS narrow (no wildcards with credentials): allow_methods
  GET/POST/PUT/PATCH/DELETE/OPTIONS; allow_headers `Content-Type`,
  `Authorization`, `X-LLM-Api-Key`, `X-LLM-Provider`, `X-LLM-Base-URL`,
  `X-LLM-Model` (BYOK names from `frontend/src/lib/byok.ts:76-83`).
- Tests in `test_graph_api.py` (`test_main_lifespan.py` DOES NOT EXIST — plan
  verify drift). Header assertions fit `test_app_starts_degraded_and_docs_remain_available`
  (no live DB needed — monkeypatched UnavailableDatabase); preflight test needs
  the `live_client` fixture (local Neo4j, ~95s).

Task 3 (trust nits + series MATCH + env, PROB-19/29/30):
- `repository/settings.py` docstring: seed.py has NO AppSetting constraint —
  remove the "uniqueness constraint created by the seed routine" claim.
- Whitespace-only `api_key` → 422: existing test `test_settings_api.py:235`
  sends `api_key: ""` to KEEP the stored key — a model-level validator that
  rejects empty would break it. Strip-then-reject in `SettingsService.update_llm`
  only when no stored key exists.
- `api/candidates.py`: add public `approve_claim`/`reject_claim`/`edit_claim`
  to `CandidateRepository` (wrap `self._db.execute_write`), delete the 3
  `repo._db` sites (`:252/:309/:363`); grep gate `rg -n "_db" api/candidates.py` = 0.
- `ontology.py`: `@functools.lru_cache` on `load_ontology` (import-time callers:
  `retrieval/tools.py:23`, `domain/extraction.py:15`, `api/graph.py:35`).
- `filter.py`: `SOURCES_QUERY` :154 + `EVIDENCE_QUERY` :183 gain
  `{series_id: $series_id}` on the `Source`/`EvidenceFragment` MATCHes; keep
  the six visibility clauses byte-identical. VERIFIED seeded rows carry
  `series_id` (`data/dexter/seed/sources.json` + `evidence_fragments.json`) —
  the predicate is safe, no seed drift.
- `DEVELOPMENT.md`: env-file steps :37-38 (`cp frontend/.env.example
  frontend/.env.local` is dead — root .env is the single source,
  `VITE_GOOGLE_CLIENT_ID` lives there) + :51 setup command → runbook-canonical
  `uv run --project spoilerless python -m spoilerless.app.graph.setup`
  (PROBLEMS.md:323 documents this exact drift).
- `vite.config.ts` `envDir: '..'`; equality check GOOGLE_CLIENT_ID vs
  VITE_GOOGLE_CLIENT_ID in config.py startup + ci.yml step — only fire when
  BOTH are set (root .env currently has GOOGLE_CLIENT_ID but no
  VITE_GOOGLE_CLIENT_ID; a hard fail would break local runs).
- Trust nits (Rule 2 beyond the plan): `services/auth.py` sanitize `avatar_url`
  (http/https only, else `''`); `EmailNotAllowedError` is already fail-closed
  (raised before repo upsert, `auth.py:145-146`) — add a regression test
  asserting no user row is created for a disallowed email.

## Durable patterns

1. **Code-convention sweeps: quoted-literal replace for Python, word-boundary
   for docs.** Python: replace ONLY quoted tokens (`"forbidden"`/`'forbidden'`)
   — bare identifiers in test names (`test_extra_fields_forbidden`) and
   parametrize labels (`("boundary", "forbidden", "present")`) are NOT codes.
   Docs: word-boundary is fine for snake_case codes, but `forbidden` /
   `unauthenticated` need surgical `403 forbidden`→`403 FORBIDDEN` handling —
   prose verbs ("is forbidden") must stay. Exclude `.planning/` +
   `docs/PROBLEMS.md` (audit trail). Frontend SSE payloads carry codes as
   `\"code\"` INSIDE single-quoted JS strings — the quoted-token perl pass
   misses them; replace separately.
2. **Frontend fallback/synthesized codes are in-scope for the sweep**:
   `client.ts`'s array-shape `invalid_request` and non-JSON `unknown_error`
   fallbacks, plus every `error.code === 'lowercase_code'` consumer
   (AuthProvider legacy `'unauthenticated'` alias, ChangeSetCard
   `changeset_stale`, ChatPanel `too_many_requests`). Alias removal is a
   required step, not optional.
3. **Registry design that avoids circular imports**: frozenset in errors.py +
   pydantic `field_validator` on ErrorDetail.code + contract test walking
   OpenAPI response examples AND ErrorDetail schema examples. `api/auth.py`
   imports `core/errors.py` — the registry holds string literals, never imports
   from api/ modules.
4. **FOURTH build-blind-spot instance — TS2353 excess-property on a narrow
   union param**: `new ApiError([{loc, msg, type}])` reds the build because
   the constructor param is `Array<{msg?: string}>`. Fix = widen the param type
   to match the real FastAPI validation shape, or narrow the test payload.
   Same class as TS18048 / TS18047 — only `npm run build` catches it.
5. `test_main_lifespan.py` does not exist (plan verify drift — same class as
   the 09-03 `test_revisions_api.py` phantom).
