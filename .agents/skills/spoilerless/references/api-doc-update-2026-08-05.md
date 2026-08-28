# API.md update verification — refreshed 2026-08-10

Use this reference when refreshing `docs/API.md`. Re-read live code before reuse.

## Verified inventory snapshot

- **50** OpenAPI operations over **37** path templates.
- Per file: series 3, graph 3, user_content 13, auth 3, revisions 3, candidates 6, progress 2, chat 6, change_set 4, settings 2, share 4, plus schema-visible `GET /health`.
- `HEAD /health` exists but is `include_in_schema=False`.
- `ERROR_CODES` contains **32** registered codes.

## Exact route-table verification

Do not stop at counts. Parse each router prefix and route decorator, add schema-visible `/health`, and compare the resulting `(method, full_path)` set with the Endpoints Overview table. Assert set equality and count. Equal totals can hide one missing and one invented route.

## Auth matrix

- Session required: `/auth/me`, progress, all chat, all ChangeSets, candidate ingest, all user-content writes, revision revert, and share create/list/revoke.
- Admin required: candidate edit/approve/reject, ChangeSet confirm, and both LLM-settings routes.
- Anonymous: series/user-content/revision/candidate reads, health, Google sign-in/logout, and token-gated `GET /api/share/{token}/graph`.
- Share revoke is creator-or-admin; public share graph uses the token's captured boundary and does not resolve a session.
- Google sign-in/logout origin validation fails closed unless `*` is configured.

## Boundary and model traps

- Revision and direct user-content reads accept any positive boundary; graph, candidate reads, progress updates, and share creation validate persisted episode orders.
- Candidate list/get require `visible_until_order`; omission is 422, not an all-level read.
- Progress accepts mutually exclusive `watched_through_order` or legacy `visible_until_order`, optionally with `view_as_of_order`; view-only updates send `view_as_of_order` alone.
- Graph responses include `effective_view_order`; chat messages include `status`; user-content/revision responses expose owner/actor `user_id`.
- `POST .../graph/path` has no boundary input; since PROB-09/#59 (commit `29ffeeb`) the shared resolver is called with NO requested order — the effective boundary comes from persisted progress alone, never from the `MAX_PATH_HOPS` hop constant. Anonymous AND progress-less authenticated readers are fail-closed to order 1 (the same read surface an anonymous visitor gets); with a progress row it is `effective_view_order(view_as_of_order, watched_through_order)`. Document live behavior, not generic comments.

## Share API details

- `POST /api/share`: session, 201, `{series_id, visible_until_order}`; validates a persisted episode but does not clamp to creator progress.
- `GET /api/share`: session; returns active records with hashes, not raw tokens.
- `GET /api/share/{token}/graph`: anonymous valid-token snapshot.
- `DELETE /api/share/{token}`: creator/admin; raw token or hash; returns `{"status":"revoked"}`.
- Raw tokens use `secrets.token_urlsafe(32)`; only SHA-256 is stored; TTL is 2,592,000 seconds. The hourly sweep removes expired/revoked Session and ShareToken nodes.

## Error registry nuance

- `AUTH_SESSION_EXPIRED` and `AUTH_SESSION_INVALID` are registered but not raised.
- `INGEST_ERROR` is inside a 200 ingest body, not an HTTP error.
- `TOKEN_NOT_FOUND` is emitted by share failures.
- `LLM_STREAM_FAILED` is an SSE `event: error` code after HTTP 200 headers have opened; do not put it in an HTTP-status table as a 503 response. `LLM_PROVIDER_UNAVAILABLE` can be either a pre-stream HTTP 503 or an in-stream SSE error.

## Adversarial verification findings (2026-08-10)

Treat prose summaries as independently testable claims even when a later endpoint-specific section is correct:

- The generic statement “deletes return 204” has an exception: `DELETE /api/share/{token}` returns HTTP 200 with `{"status": "revoked"}`.
- Revision revert's comments/documentation claim ownerless legacy records are admin-only, but the live checks are conditional on `stored_owner is not None` / `snapshot_owner is not None`. Missing ownership therefore skips the 403 check for non-admins. Document current behavior until code is fixed; do not propagate the intended fail-closed rule as live fact.
- LLM settings accept four provider values: `gemini`, `openai_compatible`, `vllm`, and `ollama`; the latter two currently share `OpenAICompatibleProvider`.
- `SettingsService.update_llm` strips API keys. Blank/whitespace retains an existing stored key, but returns 422 when no key exists; whitespace is never persisted as a new key. `null` leaves the merged stored state unchanged.
- BYOK with a non-blank `X-LLM-Api-Key` bypasses stored/env keys for that request. Do not broaden this into “the backend holds no LLM secret”: persisted Neo4j and `LLM_API_KEY` fallback storage still exist.

## RE-VERIFICATION (2026-08-10, post-fix) — all 7 findings FIXED, doc = 247/247/0

Do NOT re-flag the findings above: the surgical doc fixes landed and every one was re-proven against live code this pass.

- Ownerless revision revert: doc now documents the actual branch behavior — `api/revisions.py:189-190` (`stored_owner is not None and ...`) and `:227-228` (`snapshot_owner is not None and ...`); missing owner skips the 403, non-admin proceeds. Doc lines 83 + 276 say exactly this.
- Share revoke: `api/share.py:169-199` — `@router.delete` (default 200) returns `{"status": "revoked"}`; doc line 164/436.
- Server-side secrets: `services/settings.py:34` (`stored.get("api_key") or settings.llm_api_key`), `core/config.py:102` `llm_api_key`, `services/chat.py:77+` `get_llm_provider` BYOK bypass (non-blank `X-LLM-Api-Key` → provider built exclusively from headers). Doc line 372.
- Provider enum: `domain/settings.py:54` `Literal["gemini","openai_compatible","vllm","ollama"]`; vllm/ollama → `OpenAICompatibleProvider` (`llm/provider.py:114`). Doc line 455.
- api_key semantics: `services/settings.py:57-67` — blank/whitespace retains stored key; 422 `INVALID_REQUEST` when none stored; whitespace never persisted; `null` leaves merged state unchanged. Doc line 455.
- LLM_STREAM_FAILED: emitted ONLY as `event: error` inside the `StreamingResponse` generator (`api/chat.py:253-271`) after HTTP 200; the 503-capable code is `LLM_PROVIDER_UNAVAILABLE` (`llm/provider.py:477` handler). Doc lines 505/507.
- Endpoint table: fresh in-process OpenAPI = 50 ops / 37 templates; `(method, path)` set EQUAL to the Endpoints Overview table after stripping markdown backticks from table paths (naive comparison false-fails on backticks — see SKILL.md pitfall). Auth column matches `CurrentUserDependency` / `RequireAdminDependency` / `OptionalUserDependency` per-route.
- ERROR_CODES = 32 (`core/errors.py:28` frozenset); `AUTH_SESSION_EXPIRED`/`AUTH_SESSION_INVALID` are constants only (no raise sites); `INGEST_ERROR` body-level 200; `CONSTRAINT_VIOLATION`/`DATABASE_ERROR`/`DATABASE_UNAVAILABLE` emitted via `install_error_handlers` (`core/errors.py:209-242`).

Re-check recipe that worked: `git diff docs/API.md` first, then re-prove every rewritten claim with file:line evidence, recount via `uv run python` importing `spoilerless.app.main:app` `.openapi()`, compare sets with backticks stripped, overwrite the artifact with 247/247/0.

Verification artifact discipline: duplicate failures are acceptable when the same stale rule appears as two distinct claims on different lines, but each failure should identify the exact live branch that disproves that occurrence. Validate the final JSON with the standard artifact validator and, when fresh canonical evidence is required, a one-test temporary pytest file that checks schema/arithmetic only.

## Safe sequence

1. Preserve the GSD marker as line 1.
2. Re-read routers, dependencies, models, handlers, and SSE branches.
3. Recount routes/templates/codes.
4. Patch stale sections; preserve accurate prose.
5. Compare exact route sets, check Markdown diff hygiene, and report line count.

## RE-VERIFICATION (2026-08-12, doc-writer session) — counts hold; 3 new live facts

Re-proved via fresh `.openapi()` import of `spoilerless.app.main:app` (repo-root `.venv` python): still **50 ops / 37 templates** (49 router ops + schema-visible `GET /health`; `HEAD /health` `include_in_schema=False`), `ERROR_CODES` still **32**. Doc Endpoints Overview table = exact `(method, path)` set equality after stripping backticks (50/50, no missing/invented). Facts that changed since the 2026-08-10 pass:

- **PROB-09/#81 (commit `00fbcb6`):** `ClientError` removed from the 503-mask tuple — `core/errors.py` `_SAFE_ERRORS` is now `(ServiceUnavailable, AuthError, Neo4jError)` only. Invalid Cypher/parameters (a server bug, not infra) surfaces as the framework's plain 500 with NO envelope. API.md's error section and table must state this; never regenerate the old "everything Neo4j → 503 DATABASE_UNAVAILABLE" claim.
- **PROB-09/#71 (commit `3a3ae40`):** candidate ingest/approve/reject are bare awaits — no catch-all `422 INVALID_EXTRACTION_PAYLOAD` and no `str(exc)` interpolation. Only candidate EDIT keeps `except ValueError` → `422 INVALID_EXTRACTION_PAYLOAD` (`api/candidates.py:389`). The ingest route's 422 `INVALID_EXTRACTION_PAYLOAD` example in its `responses=` dict is schema-only, not live emission. Doc error-table row must say "candidate edit only".
- **Path-route boundary:** see the corrected "Boundary and model traps" bullet above — the "seeded with order 4 / 422 if no episode order 4" phrasing must NOT appear in API.md.

## Doc-writer tooling pitfalls (2026-08-12)

- **Parsing multi-line FastAPI decorators:** a naive `@router\.(get|post|put|patch|delete)\s*\((.*?)\)` regex FAILS — call args contain nested parens (`error_responses(404, 503)`, `Depends(get_database)`), so non-greedy `.*?` stops at the first `)`. Use a brace-matching extractor: walk paren depth from the opening `(` to the closing `)`, then take the FIRST quoted string inside the call as the path and the next `\n\s*def\s+(\w+)` after the decorator as the handler name. Prefix from `router = APIRouter(prefix="...")`.
- **Import/cwd for counting:** the package root is the REPO root (pyproject.toml at repo root; `spoilerless/` is a plain package dir holding `app/`). `cd spoilerless && uv run python -c "import spoilerless..."` raises `ModuleNotFoundError` — run from the repo root with `sys.path` including it (e.g. `.venv/Scripts/python.exe` on Windows, `uv run python` from repo root on POSIX), then `app.openapi()` and count operations/templates.
- **Route-set comparison:** `re.findall(r'^\|\s*(GET|POST|PUT|PATCH|DELETE|HEAD)\s*\|\s*`([^`]+)`\s*\|', doc, re.M)` on the doc table; normalize both sides by stripping trailing `/`; assert set equality both directions (doc-minus-live = invented routes, live-minus-doc = missing). Counts alone hide one-missing-one-invented.
