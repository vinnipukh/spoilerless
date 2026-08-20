---
last_mapped: 2026-08-20
focus: concerns
last_mapped_commit: 6256214f672d21e0c264a4910033fe02dc51da80
---
<!-- refreshed: 2026-08-20 -->
# Codebase Concerns

**Analysis Date:** 2026-08-20

Severity follows repository impact: High means a security breach, data loss, crash, or deployment blocker; Medium means a plausible load, correctness, or maintenance failure; Low means contained debt or a non-blocking edge case. Documented future scope is identified separately from defects.

## Technical Debt

### 1.1 Starter and roadmap residue obscures the executable product

**Files:** `spoilerless/app/main.py` (prior lines 1–16 PyCharm sample), `frontend/README.md` (deleted), `.planning/ROADMAP.md` (lines 104–116, 301–475), `spoilerless/app/repository/settings.py` (lines 1–7 docstring), `spoilerless/app/graph/seed.py` (lines 114–231)

**Evidence:**
- `main.py` historically was the PyCharm `print_hi` sample; `frontend/README.md` described the generic Vite template; `.planning/ROADMAP.md` carried unchecked implementeds.

**Problem:** Tracked entry-looking files and authoritative prose disagree with the live application.

**Risk:** Low (historical). New contributors can run the wrong entry point.

**Status:** RESOLVED (08-11/08-12) — `spoilerless/app/main.py` is the real FastAPI app (now with `TrustedHostMiddleware`, `BodySizeLimitMiddleware`, security-headers and request-logging middleware, docs-off in production), `frontend/README.md` deleted, settings docstring corrected. Phase 11 (`spoilerless/app/main.py: _docs_kwargs` docs-off when `ENVIRONMENT=production`) further reduces stale-build prose risk.

**Fix direction:** No action; keep production `ENVIRONMENT=production` set before import (Render dashboard) so `_docs_kwargs` disables `/docs`/`/openapi.json`.

### 1.2 Integration tests share the application’s live Neo4j state

**Files:** `spoilerless/tests/conftest.py` (lines 15–21, 122–255, now includes `bootstrap_scratch_series` / `teardown_scratch_series`), `spoilerless/tests/test_settings_api.py`, `spoilerless/tests/test_candidate_ingest.py` (now scratch-isolated in Phase 11), `spoilerless/tests/test_security_boundary.py` (scratch series `series_scratch_boundary`), `spoilerless/tests/test_session_repository.py`, `scripts/run_phase10_backend_tests.py`

**Evidence:** Default `NEO4J_URI=bolt://127.0.0.1:7687` targets the same DB as local app use; `bootstrap_scratch_series(SCRATCH, (1,2,3))` now creates an isolated `Series` + `Episodes` that the seed audit allows.

**Problem:** Isolation depends on collision-resistant IDs, narrow cleanup, and correct driver ownership. `test_candidate_ingest.py` historically used `SERIES_ID = "series_dexter"` (pollution source #46); Phase 11 migrates it to scratch.

**Risk:** Medium if scratch cleanup is skipped; an interrupted run leaks `series_scratch_boundary` nodes/claims that trip the DB-pollution gate (`ci.yml` asserts zero `series_scratch%` after seed) and the seed audit if the series leaks into `series_dexter`.

**Status:** RESOLVED for full-suite runs via `scripts/run_phase10_backend_tests.py` (ephemeral container, 0 nodes proven, always `docker rm -f -v`). Residual: plain `uv run pytest` still hits the resolved `Settings` DB (root `.env` AuraDB legacy default); ad-hoc runs must use scratch helpers and `teardown_scratch_series`.

**Fix direction:** Keep `scripts/run_phase10_backend_tests.py` as the only full-suite gate; migrate every graph-writing test to `bootstrap_scratch_series` (Phase 11 pattern); keep `assert_chunk_inventory_matches_disk()` green as the suite grows (now 52 files with `test_security_boundary.py`).

### 1.3 Schema evolution is bootstrap-driven rather than migration-driven

**Files:** `spoilerless/app/graph/seed.py` (create_constraints, seed_graph, audit_visibility_integrity), `spoilerless/app/graph/setup.py`, `spoilerless/app/graph/labels.py`, `spoilerless/tests/test_setup_schema_check.py`

**Evidence:** No tracked migration directory; `create_constraints` iterates `NODE_LABELS`.

**Problem:** No ordered transforms, rollback, or applied-version ledger.

**Risk:** Medium. Future property renames require manual intervention on local docker and AuraDB separately; seed-content drift fixes must be re-applied per database (the 01N52 null reveal-point fix pattern persists).

**Status:** OPEN (#19 deferred per PROBLEMS.md FOURTEENTH PASS; Phase 11 does not add migrations). Phase 11 adds new labels/predicates only via seed + repository, not via migration.

**Fix direction:** Add versioned forward-only Neo4j migrations with ledger + preflight/rollback; retain setup for fresh DBs.

### 1.4 Revision revert does not invalidate the series graph cache (now fixed for candidates; revert audit continues)

**Files:** `spoilerless/app/revisions/__init__.py` (`revert_revision_work`), `spoilerless/app/graph/candidates.py` (approve/reject/edit → `invalidate_series`), `spoilerless/app/api/candidates.py` (ingest/list/get now invalidate/clamp via `resolve_effective_boundary`), `spoilerless/app/api/revisions.py`

**Evidence:** 2026-08-14: `grep -n invalidate_series spoilerless/app/revisions` returned 0; 2026-08-20 candidate ingest now calls `await invalidate_series(series_id)` after `ingest_batch` (`spoilerless/app/api/candidates.py:152`), and approve/reject/edit paths invalidate; revert path remains the audit target.

**Problem:** Stale cache after revert could serve pre-revert content until otherwise invalidated.

**Risk:** Medium. Candidate-write staleness is fixed; revert staleness is now the Phase 11 audit item (11-08).

**Status:** PARTIALLY RESOLVED — candidate mutation cache invalidation landed in Phase 11 (ingest + approve/reject/edit); revert `invalidate_series` is tracked in Phase 11 plan 11-08 (shared boundary/revert label allowlist work). Verify via `grep -n invalidate_series spoilerless/app/revisions/__init__.py` on closeout.

**Fix direction:** Call `invalidate_series` inside `revert_revision_work` transaction boundary (mirror candidate pattern) and add revert-then-read cache test (Phase 11 11-08).

### 1.5 Uncommitted work in flight and machine-local files sit outside git

**Files (modified, 2026-08-20):** `.planning/ROADMAP.md`, `.planning/phases/11-security-hardening-audit-remediation-p0-p1/11-04-PLAN.md`, `11-06-PLAN.md`, `11-07-PLAN.md`, `11-08-PLAN.md`, `11-CONTEXT.md`, `.planning/codebase/{ARCHITECTURE,CONVENTIONS,INTEGRATIONS,STACK,STRUCTURE,TESTING,CONCERNS}.md` (this refresh; previously 2026-08-14 showed 13 modified + 7 untracked including `cytoscapeReconciler.ts`/`run_doc_verification.py`/`.hermes`).

**Evidence:** `git status --short` on 2026-08-20 shows 6 modified under `.planning/` (ROADMAP + four Phase 11 plan docs + CONTEXT); prior 2026-08-14 status showed `cytoscapeReconciler.ts` as untracked import target while `GraphCanvas.tsx` already imported it, plus four `verify_*.py` scripts and `.hermes/` at repo root.

**Problem:** Half-committed reconciler extraction and root-level verify scripts could be lost on `git reset --hard`; `.hermes/` risked accidental commit.

**Risk:** Low (transient). Phase 11 scope is now tracked plans, not half-committed code; prior `cytoscapeReconciler.ts` extraction has since been committed (verify `git ls-files frontend/src/components/graph/cytoscapeReconciler.ts`).

**Status:** LARGELY RESOLVED — reconciler + tests landed; verify scripts are cited as one-off audit tooling (not CI) and `.hermes/` is machine-local. Resume Phase 11: the 6 modified planning files are the in-flight GSD state; commit via `node .../gsd-tools.cjs query commit "docs: map existing codebase" --files .planning/codebase/*.md` (and separately stage planning docs per GSD closeout, never `git add .` when `.planning/config.json` is dirty).

**Fix direction:** Commit planning docs via the GSD commit helper (codebase docs only when unrelated dirty planning files exist); keep `.hermes/` in `.gitignore`.

## Security

### 2.1 Candidate administration — now authenticated, rate-limited, and boundary-clamped; pagination trust boundary remains under audit

**Files:** `spoilerless/app/api/candidates.py` (ingest `CurrentUserDependency` + `content_write_rate_limiter` + `CsrfGuardDependency` → `ingest_batch` → `invalidate_series`; list/get require `OptionalUserDependency` + `resolve_effective_boundary` + `_require_resolved_boundary`; pagination `limit/after_created_at/after_id`), `spoilerless/app/graph/candidates.py`, `spoilerless/app/api/boundary.py`, `spoilerless/tests/test_candidate_ingest.py`, `spoilerless/tests/test_candidate_review.py`, `spoilerless/tests/test_security_boundary.py`

**Evidence:** Ingest line 144 `user: CurrentUserDependency` and line 135 `_rate_limit: Annotated[None, Depends(content_write_rate_limiter)]`; list/get lines 170–193 resolve via `resolve_effective_boundary(graph_service, progress_service, series_id, user, visible_until_order)` then gate on `effective`. Unauthenticated read past order 999 is clamped to 1 in tests.

**Problem (historical):** Unauthenticated graph poisoning, review-state mutation, and caller-supplied `visible_from_order`.

**Risk:** High (historical).

**Status:** SUBSTANTIALLY RESOLVED (09-03 admin gates + 11-01 boundary + 11-03 ingest hardening). Candidate `list`/`get` now fail-closed via shared resolver (anonymous and no-record readers fixed at 1, authenticated clamped to `min(requested, view_as_of, watched_through)` via `spoilerless/app/spoiler/policy.py: effective_view_order`, then persisted-episode validation or 422). Ingest is authenticated, CSRF-guarded, rate-limited, and cache-invalidated. Remaining audit items (Phase 11 11-03/11-08/11-06): ingest batch-size cap (Max-Age test pending), candidate response model share (`dict` → ontology-backed Pydantic), and the `limit`/`after_*` cursor trust boundary (server-enforced `ge=1 le=500`, `datetime` parse, but no `after_id` ownership check yet — see 11-08).

**Fix direction:** Keep `resolve_effective_boundary` as the only read-boundary seam; enforce ingest batch-size upper bound and per-route payload caps (SEC-DOS-004 body size already lands at 1 MiB default); introduce shared response models; audit `after_id` cursor for IDOR.

### 2.2 Revision reads and reverts — revert now ownership-gated; read boundary trust remains open

**Files:** `spoilerless/app/api/revisions.py` (revert `CurrentUserDependency` + admin/ownership in transaction), `spoilerless/app/revisions/__init__.py` (`revert_revision_work`), `spoilerless/tests/test_revisions.py` (ownership matrix)

**Evidence:** `revert_revision` line 131 `user: CurrentUserDependency`, `actor_id` + tenure check inside `revert_revision_work`; `list_revisions`/`get_revision` still take `visible_until_order: Boundary` query with no auth.

**Problem (historical):** Caller-supplied future boundary could reveal spoilery snapshots; unauthenticated revert.

**Risk:** Medium. Revert mutation is gated; **reads remain enumerable at a caller-supplied boundary**.

**Status:** PARTIALLY RESOLVED (09-03 + 08-11 revert ownership; read path open, tracked as 2.5/SEC-BE-003 tail). Phase 11 11-08 plans fail-closed reversion ownership + `ChangeSet` revert admin gating + revision revert label allowlist.

**Fix direction:** Route revision list/get through `resolve_effective_boundary` (authenticated → clamped to progress, anonymous → 1), scope to owning `AppUser` or explicit share policy, and keep the in-transaction admin/ownership check; add direct security contract tests via no-record vs record reads (reuse `test_security_boundary.py` scratch pattern).

### 2.3 Every authenticated user can replace a shared provider target and credential — gated to admin, plaintext-at-rest tail remains

**Files:** `spoilerless/app/api/settings.py` (`RequireAdminDependency` on GET/PUT), `spoilerless/app/domain/settings.py` (payload `api_key`, `MERGE (s:AppSetting)`), `spoilerless/app/services/settings.py`, `spoilerless/app/llm/provider.py`, `spoilerless/tests/test_settings_api.py` (admin fake 403 matrix)

**Evidence:** `spoilerless/app/api/settings.py:36,50 RequireAdminDependency`; response masks key, node stores `json.dumps(payload)` plaintext.

**Problem (historical):** Authenticated non-admin could redirect provider to attacker loopback/internal/metadata IP and exfiltrate.

**Risk:** High (historical), now Medium tail.

**Status:** SUBSTANTIALLY RESOLVED for the settings-write vector (admin-only). Tail OPEN (#5, verified 08-12 THIRTEENTH PASS): single global `:AppSetting {key:'llm'}` node, `http(s)` scheme check only (no host allowlist), key plaintext at rest, no SSRF private/link-local/metadata block for `llm_base_url`. Phase 11 spec (SEC-LLM-001/002) plans an allowlist/private-range block and per-user vs global credential separation.

**Fix direction:** Host allowlist/private-range/metadata denial for `llm_base_url` (SEC-LLM-002), encrypted envelope or external secret-manager reference, rotation/clear semantics (Phase 11 11-07).

### 2.4 LLM API keys are plaintext application data at rest

**Files:** `spoilerless/app/domain/settings.py` (payload assembly), `spoilerless/app/repository/settings.py` (MERGE), backup/exports

**Evidence:** `payload["api_key"] = api_key; MERGE (s:AppSetting {key:$key}) SET s.value=$value`.

**Problem:** Database readers/backups can recover credential.

**Risk:** Medium. A Neo4j disclosure becomes an LLM credential disclosure.

**Status:** OPEN. Phase 11 does not encrypt at rest; it reduces blast radius by admin-gating + body-size + logging sanitization + host allowlist (so the key is harder to steal via SSRF). Tail tracked in SECURITY_AUDIT.md SEC-05.

**Fix direction:** Encrypted envelope/external secret manager, key outside Neo4j, backup-equivalent protection, rotation (Phase 11 11-07).

### 2.5 Read-boundary resolution — now unified; revision/user-content reads remain on legacy path

**Files:** `spoilerless/app/api/boundary.py` (canonical resolver, 66 lines), `spoilerless/app/api/candidates.py` (uses it), `spoilerless/app/api/graph.py` (graph GET previously cloned clamp, now deleted in 11-01 diff), `spoilerless/app/api/series.py` (series clamp deleted), `spoilerless/app/api/user_content.py` / `spoilerless/app/api/revisions.py` (still client-supplied boundary), `spoilerless/app/services/progress.py`, `spoilerless/app/spoiler/policy.py` (pure `effective_view_order` / `resolve_effective_boundary`), `spoilerless/tests/test_security_boundary.py` (anonym/ no-record / clamp / invalid matrix)

**Evidence:** `spoilerless/app/api/boundary.py: resolve_effective_boundary` header: "EVERY spoiler-sensitive read route resolves its effective boundary through this one function. Anonymous readers FIXED at 1; no-record readers FIXED at 1 (fail closed, SEC-BE-001); with record clamped to min(requested, view_as_of, watched_through) via policy.effective_view_order. `None` requested_order resolves from persisted progress alone (PROB-09/#59). Every return validated to a persisted episode or 422."

**Problem:** Legacy: candidate, user-content, revision, graph, export each had own rule; client-supplied integer could expose future content.

**Risk:** Medium (now contained for the migrated surfaces).

**Status:** SUBSTANTIALLY RESOLVED for the highest-value surfaces (candidates + graph/series) via the single resolver. Residual (Phase 11 11-02/11-08): `user_content` and `revisions` list/get still accept client-supplied boundary without auth/progress clamp; export/saved-restoration focus paths use the policy module but not yet the DB-reading `api/boundary.py` seam.

**Fix direction:** Roll `resolve_effective_boundary` onto every read surface (user-content, revision, export, search/autocomplete, saved restoration) with the same anonymous→1 / no-record→1 / clamped contract; keep anonymous reads clamped to earliest boundary. Closeout criterion: `grep -rn "visible_until_order" spoilerless/app/api --include="*.py"` shows no raw `Query(..., ge=1)` boundary without a `resolve_effective_boundary` call preceding it (except the single canonical definition).

### 2.6 Security headers, TrustedHost, body-size, docs-off, and log sanitization — landed in Phase 11 (P0)

**Files:** `spoilerless/app/main.py` (Boundaries: `BodySizeLimitMiddleware` ~60 lines, `TrustedHostMiddleware` + `_trusted_hosts()` derivation from `FRONTEND_ORIGINS`/`allowed_hosts`, `_security_headers_middleware` CSP/HSTS/X-Frame-Options, `_docs_kwargs` docs-off when `ENVIRONMENT=production`, `max_body_size_bytes=1048576`), `spoilerless/app/core/config.py` (`environment`, `rate_limit_fail_open`, `allowed_hosts`, `max_body_size_bytes`, `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round`), `spoilerless/app/core/errors.py` (`PAYLOAD_TOO_LARGE`, `_sanitized_validation_errors`, `_ERROR_SPECS[413]`), `spoilerless/app/services/rate_limit.py` (fail-closed vs fail-open matrix), `frontend/vercel.json` (CSP on shell, verified unchanged diff in drift)

**Evidence:**
- `spoilerless/app/main.py:120-180 BodySizeLimitMiddleware`: `Content-Length > max_size` rejected before body read; chunked bodies counted via `guarded_receive` and `BodyTooLarge`; 413 envelope uses `code: payload_too_large` (sanitized lowercase, registered uppercase in `ERROR_CODES`).
- `spoilerless/app/main.py:66-80 _security_headers_middleware`: `Content-Security-Policy` tuned for Google Identity Services script, `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`.
- `spoilerless/app/main.py:304-311 TrustedHostMiddleware`: `allowed_hosts=_trusted_hosts()` derives from `FRONTEND_ORIGINS` hosts + localhost + `allowed_hosts` setting; `frontend/vercel.json` carries the shell CSP.
- `spoilerless/app/core/errors.py: _sanitized_validation_errors`: `RequestValidationError` never logged as `str(exc)` (which embeds `input`/`ctx` with raw values); only `loc/type/msg/code` via `extra={"errors": ...}` (SEC-LOG-001).
- `spoilerless/app/core/config.py: environment="development"` default, `rate_limit_fail_open=False`, `allowed_hosts=""`, `max_body_size_bytes=1048576`, `llm_max_concurrent_generations=4`, `llm_max_tool_calls_per_round=8`.

**Problem (historical):** Open docs in production (SEC-INF-003), no CSP, no TrustedHost SSRF guard, no body-size cap (SEC-DOS-004), raw validation errors logged with submitted values (SEC-LOG-001), rate limiter silently degraded (SEC-DOS-001).

**Risk:** Medium–High (historical).

**Status:** RESOLVED for founding P0 items — middleware ordering in `spoilerless/app/main.py` is `TrustedHostMiddleware` (outermost) → `CORSMiddleware` → `BodySizeLimitMiddleware` → security-headers → request-logging; docs are `None` when `ENVIRONMENT=production` (must be set before import on Render); validation logs sanitized; rate limiting is environment-aware (local dev empty `REDIS_URL` stays no-op; production fail-closed returns 503, fail-open degrades with warning — see 6.3).

**Fix direction:** Keep `ENVIRONMENT=production` on Render (dashboard, not `render.yaml`); keep CSP tight to GIS/script needs; do not reintroduce `logger.error("validation_error", exc_info=exc)`.

## Performance

### 3.1 Graph reads and Cytoscape rendering return the whole visible graph

**Files:** `spoilerless/app/services/graph.py` (`asyncio.gather` over `SERIES_QUERY`, `NODES_QUERY`, `STRUCTURAL_EDGES_QUERY`, `VISIBLE_CLAIMS_QUERY`, `VISIBLE_USER_RELATIONSHIPS_QUERY`, `SOURCES_QUERY`, `EVIDENCE_QUERY`), `spoilerless/app/spoiler/filter.py`, `frontend/src/components/graph/GraphCanvas.tsx` (1,120 lines), `frontend/src/components/graph/graphElements.ts`, `frontend/src/components/graph/cytoscapeReconciler.ts` (batched `cy.batch` diff)

**Evidence:** Seven concurrent queries, no `LIMIT`/cursor at the graph boundary; frontend maps full `GraphResponse` → Cytoscape and lays out on data change. Phase 10 added typed DTOs, dagre for investigation, visualization cache; Phase 11 adds candidate pagination but not graph pagination.

**Problem:** Materializes every visible node/edge/claim/source/evidence in Neo4j + Python + JSON + browser; layout cost grows with visible frontier.

**Risk:** Medium at expanded-data scale; Low for three-episode Dexter prototype (bounded by `visible_from_order` ≤ effective boundary + Variant A caps).

**Status:** OPEN. Candidate list pagination (`limit 1..500` + cursors) in Phase 11 11-03 reduces one hot path; graph payload itself still unpaginated.

**Fix direction:** Paginate or subgraph-expand graph reads (summary + detail-on-demand), cap neighborhood expansion, measure `GraphResponse` byte size in CI, preserve stable positions via `cytoscapeReconciler.ts`.

### 3.2 Request-scoped LLM clients have no explicit close lifecycle

**Files:** `spoilerless/app/services/chat.py`, `spoilerless/app/llm/provider.py` (`httpx.AsyncClient` per request, no `aclose()`)

**Evidence:** `return OpenAICompatibleProvider(...)` / `self._client = client or httpx.AsyncClient(...)`.

**Problem:** Per-response close does not close the pool.

**Risk:** Medium (socket/FD pressure under chat load).

**Status:** OPEN. Phase 11 adds a process-wide `llm_max_concurrent_generations` semaphore (4) and `llm_max_tool_calls_per_round` (8) to cap amplification (SEC-DOS-002), but does not introduce a lifespan-owned `AsyncClient`.

**Fix direction:** Yield-ing async dependency or lifespan-scoped clients keyed by effective config; lifecycle test with instrumented client (Phase 11 11-07).

### 3.3 The chat concurrency ceiling is process-local

**Files:** `spoilerless/app/services/chat.py` (`_MAX_CONCURRENT_GENERATIONS_PER_USER = 1`, in-process `dict`)

**Evidence:** Per-user dict, zero-valued keys retained, not shared across workers.

**Problem:** Multi-worker Render bypasses ceiling.

**Risk:** Low locally, Medium on scaled deployment.

**Status:** OPEN but bounded tighter: Phase 11 adds a shared-cap semaphore (`llm_max_concurrent_generations=4` process-wide) in `spoilerless/app/services/chat.py` + per-tool-round cap (8) in `spoilerless/app/retrieval/pipeline.py` (+ `spoilerless/app/core/config.py` settings). Horizontal bypass still possible.

**Fix direction:** Shared store (Redis) lease with TTL/atomic acquire for strict multi-worker enforcement; remove zero-valued entries.

## Maintainability

### 4.1 Core production modules concentrate too many responsibilities

**Files:** `spoilerless/app/retrieval/pipeline.py` (1,089 lines post-Phase 11 caps), `spoilerless/app/llm/system_prompt.py` (827), `spoilerless/app/repository/change_set.py` (850), `spoilerless/app/retrieval/tools.py` (881), `spoilerless/app/repository/user_content.py` (856), `frontend/src/components/detail/DetailPanel.tsx` (1,049), `frontend/src/components/graph/GraphCanvas.tsx` (1,120), plus new `spoilerless/app/api/boundary.py` (66, intentionally small leaf), `spoilerless/app/core/config.py` (+40), `spoilerless/app/main.py` (middleware grown), `spoilerless/app/services/rate_limit.py` (fail-closed matrix)

**Evidence:** Largest modules mix orchestration/validation/persistence/UI; Phase 11 adds +320 committed lines to `spoilerless/app/services/rate_limit.py`, `config.py`, `errors.py`, `candidates.py`, `main.py` plus 66 new in `boundary.py` — god-file sizes in `pipeline.py`/`DetailPanel`/`GraphCanvas` are unchanged except caps/guard edits.

**Problem:** Mixed abstraction levels, large review surface.

**Risk:** Medium. Spoiler/cache/headers regressions during localized changes.

**Status:** OPEN (#79 god-file decomposition deferred). Positive: `boundary.py` is the anti-god-file pattern — one function, no router, pure import — and rate-limit `content_write_rate_limiter` is now injected as `Depends`, not inlined.

**Fix direction:** Extract query modules, split `DetailPanel` tabs/dialogs, continue reconciler extraction; protect `system_prompt.py` prose; keep new middleware as leaf modules.

### 4.2 The configured frontend lint gate — now green baseline with scoped warnings

**Files:** `frontend/eslint.config.js` (scoped `react-hooks/*` → `warn`, test `no-explicit-any` → `warn`), `frontend/src/components/detail/DetailPanel.tsx` (`react-hooks/refs` reads), `frontend/src/components/graph/GraphCanvas.tsx`

**Evidence:** Live `npm run lint` on 2026-08-14: **0 errors, 21 warnings** (`react-hooks/refs` — render-time ref reads including `useImperativeReconcileRef.current` on the `layout` prop). 2026-08-12 had 0 errors, 39 warnings.

**Problem (historical):** 28-error red baseline could not gate.

**Risk:** Low now; warnings hide new violations if baseline grows.

**Status:** RESOLVED (08-11 PROB-09 refactor, verified 08-12/08-13). Phase 11 does not worsen lint; `vercel.json` CSP is not linted. Keep `npm run lint = 0 errors` as the CI gate; do not grow `warn` count.

**Fix direction:** Triage `react-hooks/refs` findings behind actual graph refresh/focus semantics before touching tests; establish lint gating in CI (done).

### 4.3 Candidate review bypasses service/domain boundaries — narrowed, residual `dict` responses

**Files:** `spoilerless/app/api/candidates.py` (now `CandidateRepository` + `GraphService` + `ProgressService`, `content_write_rate_limiter`, `resolve_effective_boundary`), `spoilerless/app/graph/candidates.py` (`CandidateRepository` keyword-param methods), `spoilerless/app/domain/extraction.py`, `spoilerless/app/services/rate_limit.py`

**Evidence:** No `repo._db` access; `except Exception → 422 + str(exc)` catch-all removed (keeps `ValueError` only); three closures moved into repo; `ingest_batch` → `invalidate_series`; pagination `limit/after_*` added. Response models remain route-local `dict`.

**Problem (historical):** Transactions/validation in routes, leaked `str(exc)`.

**Risk:** Low–Medium residual (ontology/DTO drift across paths).

**Status:** SUBSTANTIALLY RESOLVED (08-11/08-12). Residual: shared Pydantic response models absent; no `CandidateService` layer — routes still own the paginated `list_candidate_claims(series_id, effective, limit, after_created_at, after_id)` shape directly.

**Fix direction:** Introduce `CandidateService`, shared strict request/response models (route + repo), centrally validate episode boundaries via `resolve_effective_boundary`.

### 4.4 Backend test files reproduce the god-file pattern

**Files:** `spoilerless/tests/test_visualization_projection.py` (1,711), `spoilerless/tests/test_graph_api.py` (1,685), `spoilerless/tests/test_retrieval_tools.py` (1,350), `spoilerless/tests/test_chat_api.py` (1,302), `spoilerless/tests/test_auth.py` (1,167), `spoilerless/tests/test_retrieval_pipeline.py` (770), `spoilerless/tests/test_security_boundary.py` (316, new, but small and focused), `spoilerless/tests/test_candidate_ingest.py` (361, +86), `spoilerless/tests/test_candidate_review.py` (361, +31)

**Evidence:** Five files >1,000 lines; `test_security_boundary.py` is intentionally small and module-scoped.

**Problem:** Navigation/parallelism/merge pressure.

**Risk:** Low–Medium maintainability; guarded runner still executes them green.

**Status:** OPEN. Positive trend: Phase 11 boundary suite is right-sized; chunk inventory gate (`assert_chunk_inventory_matches_disk`) keeps sharding correct as the suite grows to 52 files (total ~22.6k lines).

**Fix direction:** Split largest files by fixture group; cap new test files at ~400–500 lines.

## Compatibility

### 5.1 Runtime requirements are documented but incompletely enforced

**Files:** `pyproject.toml` (`requires-python = ">=3.13"`), `frontend/package.json` (no `engines` even though Vite 8 requires modern Node), `frontend/package-lock.json`, `README.md`

**Evidence:** Lower-bound/caret ranges; `uv.lock`/`package-lock.json` pin, but `engines` missing.

**Problem:** Wrong Node fails at install/build, wrong Python fails at install.

**Risk:** Low. Phase 11 does not change runtime floors; new `environment`/`max_body_size_bytes` settings are backwards-compatible defaults.

**Fix direction:** Add Node `engines`/package-manager metadata, CI pinned versions, frozen installs.

### 5.2 The Neo4j Compose definition is development-specific

**Files:** `docker-compose.yml` (now `neo4j:2026.06.0-community`, `127.0.0.1` bind, host bind mounts, `${NEO4J_PASSWORD:-change-me}` fallback coupled to `.env.example`), `.env.example`, `spoilerless/app/core/config.py` (dual-alias `neo4j_*`/`aura_*`, defaults `bolt://127.0.0.1:7687`/`neo4j`/`hdgraf-local-password`/`neo4j`)

**Evidence:** Guarded runner refuses live targets to protect both; engine divergence documented (AuraDB `NODE_PROPERTY_UNIQUENESS` vs local `UNIQUENESS`).

**Problem:** Portable production orchestration absent.

**Risk:** Low (documented as local). Phase 11 keeps `AUTH_DEV_CODE` legacy in root `.env` (gitignored, operator-touch) but `config.py` defaults now match `docker-compose.yml` + `scripts/env-local.sh`.

**Fix direction:** Keep Compose dev-only, pin digest, runtime secret injection, separate prod manifests.

## Missing Features

### 6.1 No coverage threshold or browser E2E suite

**Files:** `pyproject.toml` (no pytest-cov), `frontend/vite.config.ts` (no coverage block), `.github/workflows/ci.yml` (backend service-container Neo4j + DB-pollution gate, frontend `npm ci` + build + lint + audit; no coverage, no Playwright), `spoilerless/tests/` + `frontend/src/**/*.test.tsx`

**Evidence:** 52 ops/39 templates locked by `test_openapi_contract.py` + `test_frontend_contract_doc.py` (TWENTIETH PASS); `scripts/verify_phase10_coverage.py` PHASE10-COVERAGE table (98 ids) locked by `test_phase10_coverage_audit.py`; Phase 11 traces via `SECURITY_TEST_PLAN.md` (no E2E).

**Problem (historical):** No automated gate at all.

**Risk:** Medium. Broken contracts, cookies, SSE, responsive sheets, deployment-specific failures can merge without coverage/E2E.

**Status:** PARTIALLY RESOLVED (09-08 CI backend+frontend on every PR). Residual: no coverage threshold, no browser E2E. Phase 11 does not add either (out of SEC scope).

**Fix direction:** Coverage with evidence-based threshold, small Playwright smoke suite (login/session, graph boundary, chat SSE, mutation/revert, CSP headers) — product decision.

### 6.2 Production deployment exists but operations tooling is thin

**Files:** `docs/DEPLOYMENT.md`, `spoilerless/app/core/config.py` (`aura_*` alias wins), `spoilerless/app/main.py` (lifespan + session sweep + `_docs_kwargs` production-off), `docker-compose.yml`

**Evidence:** `https://spoilerless.onrender.com/health` → `200 {"status":"ok","database":"connected","service":"spoilerless-backend"}` (verified 2026-08-14). AuraDB via `aura_*` wins. `render.yaml` does NOT set `ENVIRONMENT=production` — must be Render dashboard. Open operator actions: `#29` (~40 commits ahead of `origin/main` per 08-14 — now fewer, but push + CI-green is still operator-touch per Phase 11 docs), `#36` least-privilege AuraDB user.

**Problem:** No metrics/tracing/alerting, no AuraDB backup/restore drill, no rollback automation, no local↔AuraDB sync. Stale-build dashboard override trap documented but still possible if `ENVIRONMENT` not set.

**Risk:** Medium (hardening gap, not hypothetical — prod is live, but incident response unrehearsed).

**Status:** PARTIALLY RESOLVED — deployment verified live; production-off docs, security headers, body-size, rate-limit middleware landed; sweep loop runs hourly under lifespan. Residual: no least-privilege AuraDB user, no backup drill, no adoption of managed logging/metrics.

**Fix direction:** Push `origin/main` + CI-green; least-privilege AuraDB user; AuraDB backup/restore rehearsal; structured logs/metrics/traces + alerts; migration-before-rollout + rollback automation; set `ENVIRONMENT=production` on Render before Phase 11 closeout.

### 6.3 No general HTTP abuse controls — narrow workers now rate-limited, body-sized, and LLM-capped; read-surface gap remains

**Files:** `spoilerless/app/services/rate_limit.py` (login 10/5m IP, chat-send 20/min user, content-write 30/min user-or-IP via `content_write_rate_limiter` + `rate_limit_identifier` with ASGI `request.client is None` guard), `spoilerless/app/api/candidates.py` (ingest gated, list/get not gated), `spoilerless/app/api/auth.py`, `spoilerless/app/api/chat.py`, `spoilerless/app/api/user_content.py`, `spoilerless/app/core/config.py` (`environment`, `rate_limit_fail_open`, `max_body_size_bytes`, `llm_max_concurrent_generations`, `llm_max_tool_calls_per_round`), `spoilerless/app/main.py` (`BodySizeLimitMiddleware` + `init_rate_limiter` fail-closed matrix)

**Evidence:** `services/rate_limit.py: RateLimiter.__call__` now branches: empty `redis_url` → no-op (local dev contract); `environment != "production" or rate_limit_fail_open` → warning + return (degrade); else → `503 rate_limit_unavailable` (SEC-DOS-001). `init_rate_limiter` mirrors: fail-closed production logs `ERROR` with "every limited route will 503". `main.py: BodySizeLimitMiddleware` samples `Content-Length` plus chunked `received > max_size` → 413. Candidate ingest carries `_rate_limit: Depends(content_write_rate_limiter)` (08-05) plus new `rate_limit_identifier` fix for test ASGI clients without `request.client`. LLM caps: `spoilerless/app/retrieval/pipeline.py: new_calls[: llm_max_tool_calls_per_round]` (8) and `spoilerless/app/services/chat.py: asyncio.Semaphore(llm_max_concurrent_generations=4)` (SEC-DOS-002).

**Problem (historical):** No per-IP/user budget on any route.

**Risk:** Medium for internet exposure; Low locally. The remaining un-throttled read surfaces are `GET /api/series/{id}/graph` (full visible graph, cache-poisonable), `GET /api/series/{id}/candidates` list/get, and export/search; flooding them is still possible on public deploy.

**Status:** SUBSTANTIALLY RESOLVED for the abuse-primary surfaces (login, chat-send, content-write/ingest) + new payload-cost cap (body 1 MiB default) + LLM amplification cap (tool-calls/round + concurrent generations). Residual: no general per-IP/user budget on graph reads, candidate reads, or other GETs; fail-closed production trades availability for DoS resistance during Redis outage (observably 503 instead of silent throttling bypass — the SEVENTEENTH PASS free-tier daily-reset class that was previously fail-open→silent, now fail-closed when configured).

**Fix direction:** Per-route/IP/user rate buckets for graph reads + candidate reads + export/search (keyed via `rate_limit_identifier`); consider `413` + `429` coverage in `test_openapi_contract.py`; monitor Upstash daily-reset window to tune `rate_limit_fail_open` per environment.

### 6.4 Expired and revoked sessions have no automated retention cleanup — resolved

**Files:** `spoilerless/app/repository/session.py`, `spoilerless/app/repository/share.py`, `spoilerless/app/services/auth.py`, `spoilerless/app/main.py` (`_session_sweep_loop` hourly), `spoilerless/app/graph/seed.py` (legacy zombie sweep)

**Evidence:** Lifespan hourly `sweep_expired()` for `:Session` + `ShareToken`; failed iteration logged, never fatal; sweep skipped when DB unreachable at startup (degraded `/health` path).

**Problem (historical):** Stale records accumulated.

**Risk:** Low.

**Status:** RESOLVED (09-04). Phase 11 adds no retention change; `sweep_expired` also clears `ShareToken` expiry.

### 6.5 Documented future extraction work is not a present defect

**Files:** `.planning/ROADMAP.md`, `spoilerless/app/api/candidates.py`, `spoilerless/app/domain/extraction.py`, `docs/ARCHITECTURE.md` (616–635)

**Evidence:** Candidate ingestion/review exists; subtitle/script/podcast connectors + automated extractor are future product scope (ROBUST).

**Problem:** Aspirational work misread as bug.

**Risk:** N/A.

**Status:** NOT A DEFECT. Phase 11 hardens the existing `EXTRACTION_BATCH` contract (batch envelope validation, pagination, auth) but does not ship an extractor.

### 6.6 Local docker Neo4j and AuraDB can silently diverge

**Files:** `docker-compose.yml`, `scripts/env-local.sh`, `spoilerless/app/core/config.py` (dual alias, defaults), `scripts/run_phase10_backend_tests.py` (guard refuses both), `spoilerless/app/graph/seed.py`

**Evidence:** Two live targets: local `spoilerless-neo4j`/`hdgraf-neo4j` vs AuraDB via `aura_*`. Engine divergence documented (AuraDB `NODE_PROPERTY_UNIQUENESS` vs local `UNIQUENESS`); `run_phase10_backend_tests.py` must refuse both; seed fixes must be applied per-database.

**Problem:** Local green ≠ prod green.

**Risk:** Medium operational. Phase 11's new constraints (e.g. no new constraint names yet, but `PAYLOAD_TOO_LARGE` / `max_body_size` are runtime gates, not DDL) keep drift low, but any future DDL via `create_constraints` still needs per-database application.

**Status:** OPEN.

**Fix direction:** Pre-deploy schema/seed drift check (constraint inventory + seed-content hash), documented reseed-to-AuraDB procedure, engine-tolerant assertions where engines legitimately differ.

### 6.7 Phase 11 security hardening is mid-flight — tracer 11-01 green, 11-02..11-08 in progress, uncommitted planning is the risk

**Files:** `.planning/ROADMAP.md` (Phase 11: Security Hardening — IN PROGRESS, 2026-08-15, SEC-01..SEC-12), `.planning/phases/11-security-hardening-audit-remediation-p0-p1/11-01-PLAN.md` (committed 6256214), `11-04-PLAN.md`/`11-06-PLAN.md`/`11-07-PLAN.md`/`11-08-PLAN.md`/`11-CONTEXT.md` (modified, not committed), `SECURITY_AUDIT.md` / `SECURITY_TEST_PLAN.md` / `SECURITY_ATTACK_SURFACE.md` (audit deliverables), `spoilerless/app/api/boundary.py`, `spoilerless/app/api/candidates.py`, `spoilerless/app/core/config.py`, `spoilerless/app/main.py`, `spoilerless/app/services/rate_limit.py`, `spoilerless/tests/test_security_boundary.py`, `.planning/codebase/*.md` (this map, 2026-08-20 anchor 6256214f)

**Evidence:** Drift `git diff --stat 5bd1641..HEAD` = 42 files / +1,660 lines (Phase 11 P0 hardening). Tracer slice 11-01 ships the unified `resolve_effective_boundary` + candidate ingest fix + scratch-series harness + boundary matrix tests and is verified green at HEAD 6256214. Uncommitted `git status` shows 5 planning files modified (`ROADMAP.md`, `11-04/11-06/11-07/11-08 PLAN.md`, `CONTEXT.md`) — these are plan refinements ahead of execution.

**Problem:** Planning is ahead of execution; the codebase at HEAD is tracer-only (candidates + graph/series fail-closed), while the remaining P0/P1 bound in `ROADMAP.md` Success Criteria (trusted proxy, fail-closed limiter, cost caps, SSRF, body-size, docs-off, CSP, log sanitization, plus P1 output guard/cache-key/Max-Age/email_verified/TrustedHost/ingest-pagination/revert-allowlist/reversion-ownership/ChangeSet admin/series-switch hydration/client-header hardening/verification portability) maps to plans 11-02..11-08 that are planned but not all executed at this map date. The prior map (2026-08-14) had zero Phase 11 commits; this map captures the tracer green and the remaining plan surface.

**Risk:** Medium. Feature work that touches candidate/rate-limit/main/config without consulting `SECURITY_TEST_PLAN.md` can bypass the tracer's fail-closed contract. Availability risk during fail-closed `REDIS_URL` outage in production (every limited route 503 until Redis returns — intentional per SEC-DOS-001). Docs-off in production requires `ENVIRONMENT=production` before import or docs remain reachable (SEC-INF-003).

**Status:** IN PROGRESS — do not mark P0 closed until `test_security_boundary.py` + remaining boundary/ingest/rate-limit/SSRF/body/CSP/log suites pass on the guarded runner, `SECURITY_AUDIT.md` P0 rows are struck, and the 5 modified planning docs are GSD-committed via `query commit` (not `git add .` when `.planning/config.json` sits dirty).

**Fix direction:** Execute 11-02..11-08 sequentially via `/.--` GSD runbook, keeping each plan's security-test-plan section reference literal; gate each on `scripts/run_phase10_backend_tests.py` + `NODE_ENV=test CI=1 npm run test` + `npm run lint`/`build` + `grep -E "payload_too_large|rate_limit_unavailable|PAYLOAD_TOO_LARGE" spoilerless/app/core/errors.py` code-registry checks; stage `.planning/ROADMAP.md`, `.planning/STATE.md`, and the phase `VERIFICATION.md` together per orchestrator closeout (house pattern `2bbd330`/`80b4646`/`7f4c52a`). Keep `ENVIRONMENT=production` + `REDIS_URL` + `FRONTEND_ORIGINS` + `GOOGLE_CLIENT_ID` consistent between Render and root `.env` (verify via `grep -n FRONTEND_ORIGINS .env` before deploy, never inline `export X="$(grep ...)"` in the hardline terminal).

---

*Concerns audit: 2026-08-20*
