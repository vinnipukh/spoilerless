---
phase: 09-feature-expansion-full-audit-remediation
plan: 05
type: execute
status: complete
executed_by: gsd-executor (deleg_594300ef Task 1 partial, deleg_2e5f1e19 Tasks 2-3 partial) + orchestrator inline completion (type fix, avatar commit, verification, SUMMARY)
---

# Phase 09 — Plan 09-05 Summary: API hardening

## Objective

PROB-09/#20 (error-code convention), PROB-17/#38 (security headers + CORS),
PROB-19 (trust nits, series-scoped read path), PROB-29 (missing series
MATCH), PROB-30 (env consolidation). ZERO-COST.

## Commits

| Task | SHA | Message |
|------|-----|---------|
| 1 | `8c9dff4` | feat(09-05): canonical UPPERCASE error codes (PROB-09/#20) |
| 2 | `358ee28` | feat(09-05): security headers middleware + narrowed CORS (PROB-17/#38) |
| 3a | `0c63743` | feat(09-05): trust nits + series-scoped read-path MATCH + env consolidation (PROB-19/29/30) |
| 3b | `6d71335` | feat(09-05): avatar_url scheme sanitization (http/https only, PROB-19/#41) |

## What shipped

### Task 1 — UPPERCASE error codes (`8c9dff4`)
- `core/errors.py`: uppercase registry `ERROR_CODES` (33 codes) + pattern
  `^[A-Z][A-Z0-9_]*$` + field_validator rejecting unregistered codes
- Mechanical sweep of all raise sites + tests + docs to uppercase (32 files,
  quoted literals only; test names untouched)
- `test_openapi_contract.py`: 2 new contract tests (OpenAPI codes uppercase +
  registered; registry self-check)
- Frontend: `client.ts` INVALID_REQUEST/UNKNOWN_ERROR normalization,
  AuthProvider legacy branch dropped, ChangeSetCard CHANGESET_STALE,
  ChatPanel TOO_MANY_REQUESTS, fixtures swept, new `client.test.ts` (10 tests)
- Orchestrator fix: `ApiValidationErrorItem` type (loc/msg/type) so the
  FastAPI 422-array shape typechecks

### Task 2 — security headers + CORS (`358ee28`)
- `_security_headers_middleware` in main.py: exact CSP (GIS-compatible),
  HSTS `max-age=31536000; includeSubDomains`, X-Content-Type-Options
  nosniff, X-Frame-Options DENY, Referrer-Policy
  strict-origin-when-cross-origin — registered before logging middleware
- CORS narrowed: explicit methods (GET/POST/PUT/PATCH/DELETE/OPTIONS),
  explicit headers (Content-Type, Authorization, X-LLM-*) — no wildcard
  with credentials
- Tests: `test_security_headers_on_every_response`,
  `test_cors_preflight_is_explicit_no_wildcard_with_credentials` + extended
  degraded test. Auto-fixed a pre-existing parametrize argname bug
  (`FORBIDDEN`→`forbidden`) that blocked collection of the whole module

### Task 3 — trust nits + series MATCH + env (`0c63743` + `6d71335`)
- Settings: whitespace-only api_key → 422 INVALID_REQUEST only when no
  stored key (keep-blank semantics preserved — service-level check, not a
  model validator); settings repo docstring corrected
- `CandidateRepository.approve_claim/reject_claim/edit_claim` via
  `execute_write`; `repo._db` sites removed (grep gate = 0)
- `load_ontology` lru_cached
- `filter.py`: `Source`/`EvidenceFragment` MATCHes series_id-scoped —
  visibility clauses byte-identical (verified via diff)
- Env: `vite.config.ts` `envDir: '..'`; `.env.example` gains
  VITE_GOOGLE_CLIENT_ID + VITE_API_BASE_URL; DEVELOPMENT.md root-.env-only
  flow + `uv run --project spoilerless python -m spoilerless.app.graph.setup`
- `config.py`: `verify_google_client_id_equality` fires only when both set
- Auth: `_sanitize_avatar_url` (http/https only, `javascript:`/`data:` →
  empty); EmailNotAllowedError no-row-created test

## Verification (real runs)

- `test_auth.py` + `test_settings_api.py`: 56/56
- `test_graph_api.py` (full): 29/29
- OpenAPI contract + health/security/cors/equality subset: 12/12
- Frontend: vitest 258/258 (33 files), `npm run build` green, lint 0
- Gates: `rg -c "_db" api/candidates.py` = 0; `envDir` present;
  `backend/.env` absent

## Self-Check

✅ PASS — all 3 tasks complete; security headers + CORS narrowed; error
codes canonical; no `.planning/config.json` or `.env` touched; no real-user
rows deleted.

*Completed: 2026-08-05 (2 executors + orchestrator closeout)*
