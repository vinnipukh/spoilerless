# 08-15 API.md update — verified facts + drift traps (gsd-doc-writer)

Verified 2026-08-15 during the docs/API.md update (update mode, verify-then-
targeted-patch). The existing doc was ~95% accurate; five claims were stale.
Trust these over the task brief; the brief is a hint, never truth.

## Inventory gate (unchanged, re-verified)
- `spoilerless/tests/test_frontend_contract_doc.py` still asserts **52 ops /
  39 path templates** — matches the docs/API.md header. Never cite any count
  without reading the test's live asserts first.
- **CORRECTION (08-14 verification): `test_openapi_contract.py` is GREEN, not
  stale.** It locks the same 39-template surface (`assert
  len(schema["paths"]) == 39`, line 225; comment line 152: "current inventory
  instead of the stale 45-op/32-path set") with fully typed operations (every
  DELETE typed 204 or 200-with-body). The "remains STALE (32 paths)" claim in
  the earlier version of this file was inherited from 08-12 without re-grepping;
  Phase 10 10-03/10-06 inventory updates fixed the file. Both contract tests
  are green members of the zero-failure baseline.

## Drift traps found & fixed in docs/API.md
1. **Share-create boundary IS clamped** (commit 7dc6370, "fix(09): clamp
   share-create boundary to creator progress"): no progress row → fail closed
   to order 1; else `effective_view_order(min(requested, view_as_of_order),
   watched_through_order)`. Any doc text saying share-create "does not clamp
   to the creator's watch progress" is STALE.
2. **CSRF covers EVERY cookie-authenticated state-changing route** (commit
   69b7830): `CsrfGuardDependency` (alias of `verify_origin` in
   `spoilerless/app/api/deps.py`) is on auth google+logout, candidates
   ingest/edit/approve/reject, change_set propose/confirm/reject/revert, chat
   create/delete/messages/stream, progress POST, revisions revert, settings
   PUT, share POST+DELETE. Claims that "only sign-in/logout verify origin" or
   "state-changing routes do not perform CSRF validation" are STALE.
   Exception: `POST /api/series/{series_id}/graph/path` has only
   `OptionalUserDependency` — no origin check.
3. **Render service name is `spoilerless-api`** (render.yaml), NOT
   `spoilerless`. Build `uv sync --frozen`, start
   `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT` —
   verified verbatim.
4. **Deployed origin**: `https://api.spoilerless.net` exists only as a
   COMMENTED example in `frontend/.env.example` → phrase as "intended", carry
   `<!-- VERIFY: ... -->`; live DNS/deployment state is external to the repo.
5. **`/api/static` mount** in `spoilerless/app/main.py` serves self-hosted
   portraits `/api/static/characters/<id>.webp` (PROBLEMS #28 contract —
   images never external CDNs). NOT in the OpenAPI operation inventory; graph
   `image_url` values are origin-relative and pass CSP `img-src 'self'`.

## Verified-unchanged facts (accurate as of 08-15)
- Rate limits (`services/rate_limit.py`, module constants — NOT env-dependent;
  no VERIFY marker needed): login 10/300s per IP, chat-send 20/60s per user,
  content-write 30/60s per user-or-IP. Redis-backed (`RedisBucket` via
  pyrate-limiter, atomic across workers); no-op when `REDIS_URL` empty; Redis
  outage degrades to no-op, never 500 (PROB-23, SEVENTEENTH PASS).
- `ERROR_CODES` registry = **32 codes** (`core/errors.py`).
  `INVALID_EXTRACTION_PAYLOAD` is still raised by candidate EDIT only
  (`api/candidates.py` ~line 319, ValueError → 422); ingest/approve/reject no
  longer map to it (PROB-09/#71).
- Session cookie: name `session`, Secure default `true`, SameSite default
  `lax`, TTL 604800. **No slide-on-read** — `refresh` bumps `last_seen_at`
  only (PROB-03/#9); background sweep hourly (3600s), started only when DB
  reachable at startup.
- Tokens: `core/tokens.py` — `generate_token(nbytes=48)` +
  `hash_token()` (SHA-256 hex); sessions 48-byte, share tokens 32-byte.
- Candidate IDs: deterministic `extracted:{sha256(normalized)[:16]}` in
  `graph/candidates.py` (D-11).
- Share: TTL 2592000 (30 days); POST → 201; `DELETE /api/share/{token}` →
  **200 `{"status":"revoked"}`** (not 204); invalid/expired/revoked → 404
  TOKEN_NOT_FOUND; revoke limited to creator or admin.
- Expansion: `EXPANSION_DEFAULT_LIMIT=12`, `EXPANSION_MAX_LIMIT=25`,
  `PROJECTION_VERSION="1.0.0"` (`domain/visualization.py`); expand is NEVER
  cached (T10-CACHE-06); allowlist keys family|work|conflict|episode_events|
  clues|locations|evidence.
- `MAX_PATH_HOPS=4` (`retrieval/tools.py`); path route resolves boundary from
  persisted progress alone (PROB-09/#59).
- Visualization view enum: episode_overview|character_network|plot_threads|
  investigation|full|graphrag_focus; `focus_id` accepted only for
  graphrag_focus, cap 20 distinct.
- CORS: `FRONTEND_ORIGINS` default `http://localhost:5173`; explicit methods
  + explicit headers incl. BYOK `X-LLM-*` (no wildcard with credentials).
- Health: typed 200/503 + `HEAD /health` (include_in_schema=False).

## Workflow notes
- Present-tense behavior claims ("the route currently...", "does not...") are
  the drift-trap class. Re-check the route file before trusting; `git log` on
  the route file surfaces recent fixes (e.g. share clamp) that docs predate.
- Update mode on a mostly-accurate doc = targeted patches, not rewrite:
  docs/API.md stayed 563 lines with all accurate prose preserved.
- VERIFY marker count to report to the parent: 1 added (deployed origin).
