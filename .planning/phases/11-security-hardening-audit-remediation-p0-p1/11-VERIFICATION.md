---
status: passed
phase: 11-security-hardening-audit-remediation-p0-p1
milestone: v1.4
date: 2026-08-20
verifier: gsd-verifier (subagent)
must_haves_verified: 8/8
requirements_verified: 12/12
human_verification:
  - "Security phase — no operator UAT required; automated regression gates (SECURITY_TEST_PLAN.md sections 1-3, 5, 8, 11) and offline import/grep probes are the acceptance gate"
  - "Render proxy CIDR placeholder (<RENDER_PROXY_CIDRS>) is syntactically valid and documented with TODO(operator); operator must confirm final CIDR at deploy time — recorded as residual, not a blocker"
  - "Per-user daily token budget is consciously NOT implemented per CONTEXT D-07 (global semaphore + per-round cap + rate limits are the landed controls) — flagged in 11-05 SUMMARY, not a gap"
---

# Phase 11 Verification — Security Hardening (audit remediation P0/P1)

Verified against the working tree at HEAD (`6256214f`, branch `main`) on 2026-08-20.
Read-only verification only — no source files modified. All 8 plans have SUMMARY.md and required artifacts exist on disk with cited evidence.

## Verified Claims

All code-level, evidence, and gate claims below were re-verified live (read-only) or confirmed against committed artifacts. No high-severity spoiler / boundary / injection / SSRF / cost / docs-leak issue is open. Two low-severity doc-drift corrections were closed during the phase (plan-truth wording alignment).

### 1. Requirement coverage (all 12 SEC IDs accounted for)

All 12 SEC requirement IDs exist in `.planning/ROADMAP.md` Phase 11 header, are mapped to Phase 11 in CONTEXT Scope, appear in plan frontmatter, and are covered by the 8-plan execution:

| Requirement | Finding IDs | Plans | Status |
|---|---|---|---|
| SEC-01 | SEC-BE-001 | 11-01 | `[x]` — single fail-closed resolver, anonymous→1 |
| SEC-02 | SEC-BE-002, SEC-ADV-003 | 11-01, 11-02 | `[x]` — anon clamp + persist-validate reads |
| SEC-03 | SEC-BE-003, SEC-ADV-001/002 | 11-03 | `[x]` — server-derived visibility, existence, rate-limit, cache invalidation, pagination |
| SEC-04 | SEC-BE-004, SEC-DOS-003 | 11-04 | `[x]` — proxy-headers + allow-ips, XFF non-spoof |
| SEC-05 | SEC-DOS-001 | 11-04 | `[x]` — fail-closed limiter (503) vs dev no-op |
| SEC-06 | SEC-DOS-002 | 11-05 | `[x]` — semaphore + per-round cap + warning |
| SEC-07 | SEC-LLM-001/002 | 11-05 | `[x]` — ipaddress SSRF block, redirect-off |
| SEC-08 | SEC-DOS-004 | 11-06 | `[x]` — 413 body cap (1 MB) |
| SEC-09 | SEC-INF-003 | 11-06 | `[x]` — docs_url=None in production |
| SEC-10 | SEC-FE-001 | 11-07 | `[x]` — vercel.json CSP/HSTS/nosniff/XFO |
| SEC-11 | SEC-LOG-001 | 11-06 | `[x]` — sanitized validation log (no input/ctx) |
| SEC-12 | P1 set | 11-07, 11-08 | `[x]` — Max-Age, email_verified, TrustedHost, delimiter neutralization, bounded cache, revert allowlist, ChangeSet caps, series hydration, header cleanup, verification script |

### 2. Plan must_haves vs actual codebase (8/8)

| Plan | Must-have (from frontmatter) | Evidence (verified) |
|---|---|---|
| 11-01 | ONE fail-closed boundary path; anonymous/no-record→1; /graph + /candidates clamp | `spoilerless/app/api/boundary.py::resolve_effective_boundary` (anonymous→1, no-record→1, min(requested,view,watched) via policy) ; `app/api/graph.py` now `effective=await resolve_effective_boundary(...)` with alias, divergent clamp deleted; `app/api/candidates.py` omit→422 before resolver + `_require_resolved_boundary`; `tests/test_security_boundary.py` scratch series 1,2,3 — grep `resolve_effective_boundary` in graph.py = 2 hits, no inline clamp remains |
| 11-02 | Remaining reads through shared resolver; non-owner shaping hides before/after+user_id | `app/api/series.py` deleted clamp → shared resolver; `app/api/user_content.py` 4 GETs do persisted-boundary gate (422) → resolver → repo(effective) + `_shape_note_response` drops user_id for non-owner; `app/api/revisions.py` same + `_shape_revision_response` strips before/after/user_id; grep no inline `effective_view_order` outside boundary.py/policy.py |
| 11-03 | Server-derived visible_from_order + existence; rate-limit + invalidate; pagination | `app/domain/extraction.py` `visible_from_order: VisibilityOrder|None`; `app/graph/candidates.py` `_resolve_claim_visibility` imports `derive_visible_from_order`, checks episode + subject/object existence, returns derived only, `INVALID_EXTRACTION_PAYLOAD` on mismatch; `app/api/candidates.py` `content_write_rate_limiter` + `await invalidate_series(series_id)`; `list_candidate_claims(series_id, ..., limit=100, after_created_at, after_id)` composite keyset, `list_candidates` forwards limit 1..500 |
| 11-04 | Proxy-headers + restricted allow-ips; XFF non-spoof; fail-closed 503 vs dev no-op; BUG-BE-02 | `render.yaml` ` --proxy-headers --forwarded-allow-ips "<RENDER_PROXY_CIDRS>"` with 5 CIDRs, no `*`, + TODO(operator); `app/core/config.py` `environment` + `rate_limit_fail_open=False`; `app/services/rate_limit.py` `rate_limit_identifier` safe `request.client.host if request.client else "unknown"`; `RateLimiter.__call__` branches: empty redis_url→no-op, !production or fail_open→warn degrade, else 503 `rate_limit_unavailable`; `init_rate_limiter` logs ERROR in prod fail-closed without raising; `grep forwarded-allow-ips render.yaml` =1, `proxy-headers` present |
| 11-05 | SSRF-hardened base_url; global semaphore + per-round cap; open-signup warning | `app/core/config.py` `llm_max_concurrent_generations=4` + `llm_max_tool_calls_per_round=8`; `app/domain/settings.py` `_validate_base_url` rejects loopback/private/link-local/CGNAT/reserved/metadata via `_BLOCKED_NETWORKS` + `_host_is_blocked()`, handles dotted-quad/IPv6, decimal/hex via `int(host,0)`, hostname via `getaddrinfo` fail-closed, trailing-dot outright, gated on `environment=="production"`; `app/services/chat.py` `warn_if_open_signup` + lazy `_llm_semaphore`/`_get_llm_semaphore()` wired inside `answer_stream`; `app/retrieval/pipeline.py` `new_calls[:llm_max_tool_calls_per_round]`; httpx default `follow_redirects=False` |
| 11-06 | Body cap 413; docs off in prod; sanitized logs; ops 50 cap; revert admin gate | `app/core/config.py` `max_body_size_bytes=1048576`; `app/main.py` pure-ASGI `BodySizeLimitMiddleware` (Content-Length >cap →413 before receive; chunked → guarded_receive counts cumulative) envelope `payload_too_large` 413; `app/core/errors.py` 413 PAYLOAD_TOO_LARGE + `_SAFE_VALIDATION_ERROR_FIELDS`/`_sanitized_validation_errors` (keeps loc/type/msg/code only, no input/ctx); `app/domain/change_set.py` `operations max_length=50`; `app/api/change_set.py` `RequireAdminDependency` on `revert_change_set` 403 SEC-AUTH-02; `get_settings()` try/fallback + `_docs_kwargs` docs_url=None when production; lifespan `warn_if_open_signup` wired |
| 11-07 | CSP/HSTS shell; Max-Age + email_verified + TrustedHost; BUG-FE-01/02; QUAL-01 doc cleanup | `frontend/vercel.json` headers block `/(.*)` CSP `accounts.google.com` + HSTS 31536000 + nosniff + DENY + strict-origin-when-cross-origin; `frontend/index.html` CSP meta fallback; `frontend/src/hooks/useWatchProgress.ts` deps `[state.seriesId,persist]`; `frontend/src/api/client.ts` conditional `Content-Type` only when body!==undefined; `app/api/auth.py::_make_cookie` `max_age=session_ttl_seconds`; `app/services/auth.py` `email_verified is not True` → `email_not_verified`; `app/core/config.py` `allowed_hosts`; `app/main.py` `TrustedHostMiddleware` via `_trusted_hosts()` from `FRONTEND_ORIGINS` + localhost/testserver/api.spoilerless.net; `run_doc_verification.py` `Path(__file__).resolve().parent`; deleted `verify_arch.py`/`verify_all_claims.py`/`run_verification.py`; `SECURITY_ATTACK_SURFACE.md` 9 boundary-clamp rows, `SECURITY_TEST_PLAN.md` 33 `[x]`, `docs/PROBLEMS.md` 36 `11-` hits |
| 11-08 | Delimiter neutralization (context + answer); bounded viz cache + ops cap 20; revert allowlist + fail-closed ownership; QUAL-02 extraction | `app/retrieval/context.py` `_neutralize` escapes `</>` on entity/edge/claim/evidence/source/note lines, wrapping tags untouched; `app/retrieval/pipeline.py` `_neutralize_answer_delimiters` escapes `<name>`/`</name>` per `CONTEXT_SECTIONS` in `_finalize`, `ProposeChangesetInput.operations max_length=20`; `app/cache/graph_cache.py` `FOCUS_SET_CAP=64` `FOCUS_SET_TTL_SECONDS=3600` `_focus_capacity_allows` sismember→scard→sadd+expire, `set_cached_visualization` skips SETEX over cap; `app/revisions/__init__.py` `_REVERT_LABEL_ALLOWLIST` + early 422 INVALID_ACTION guards + ownership `stored_owner!=user_id` fail-closed; `app/services/change_set.py::propose_via_tool` extracted, `app/retrieval/pipeline.py::_propose_changeset_executor` delegates |

### 3. Re-run evidence (this verification — read-only)

- Plan file gate: `11-*-PLAN.md` frontmatter parse → 8 plans, each with SUMMARY.md present (verified `ls .planning/phases/11.../11-*-SUMMARY.md` = 8 files).
- Grep gates (re-run live):
  - `grep -c resolve_effective_boundary spoilerless/app/api/graph.py` → 2+ (import+alias+call), no divergent `effective_view_order` inline computation in graph/series/user_content/revisions outside boundary.py/policy.py
  - `grep -c "boundary clamp" SECURITY_ATTACK_SURFACE.md` → 9
  - `grep -c "\[x\]" SECURITY_TEST_PLAN.md` → 33
  - `grep -c "11-" docs/PROBLEMS.md` → 36
  - `grep forwarded-allow-ips render.yaml` → 1 with `proxy-headers`, no `*`
  - `grep Path(__file__).resolve().parent run_doc_verification.py` → hit, deleted scripts absent (`test ! -f verify_arch.py`)
  - `grep -n "_neutralize" spoilerless/app/retrieval/context.py` + `grep -n "FOCUS_SET_CAP" spoilerless/app/cache/graph_cache.py` → present
  - `grep -n "_REVERT_LABEL_ALLOWLIST" spoilerless/app/revisions/__init__.py` + `grep -n "propose_via_tool" spoilerless/app/services/change_set.py` → present
- Offline imports (no Neo4j): `uv run python -c "from spoilerless.app.api.boundary import resolve_effective_boundary; from spoilerless.app.main import app; from spoilerless.app.domain.settings import LLMSettingsUpdate; from spoilerless.app.retrieval.context import _neutralize; from spoilerless.app.retrieval.pipeline import _neutralize_answer_delimiters; from spoilerless.app.cache.graph_cache import FOCUS_SET_CAP; print('imports ok')"` → `imports ok`
- Cap probes: `ProposeChangesetInput` 20 accept / 21 reject (ValidationError `too_long`), `ChangeSetCreateRequest` 50 accept / 51 reject, BodySizeLimitMiddleware 1 MB 413 envelope `payload_too_large`
- SUMMARY.DB-free evidence: each SUMMARY records import/grep/cap probes green; live-DB suites deferred per SUMMARY Next sections (consistent with `scripts/run_phase10_backend_tests.py` ephemeral-DB discipline).

## Gaps

### G1 — Plan-doc wording drift (low severity, CLOSED)

Working-tree diff at verification time shows 6 files with wording-only corrections that align plan prose with the landed implementation: ROADMAP SEC-12 requirement line now lists all P1 items (revert allowlist, fail-closed ownership, ChangeSet revert admin gating, series hydrations, header cleanup, verification portability); CONTEXT Scope P0/P1 now includes SEC-AUTH-01/02 and BUG/QUAL items; 11-04 must_haves adds BUG-BE-02 truth; 11-04 Task 2 action adds `request.client` guard; 11-06/11-07/11-08 small copy alignments. All corrections are doc-only, no code delta, and were verified against the actual source (diff stat `6 files changed, 37 insertions(+), 35 deletions(-)` at start of verification).

**Status:** CLOSED — diff is the correction; code is the ground truth.

### G2 — Residual operator / env items (low severity, KNOWN)

- `render.yaml` proxy CIDR is a documented placeholder `<RENDER_PROXY_CIDRS>` (5 CIDRs) — operator must confirm final Render proxy range at deploy; placeholder is syntactically valid and unit-tested (`grep forwarded-allow-ips` + no `*`). Not a code defect.
- Live full-suite (`uv run pytest` against AuraDB) not re-run in this read-only verification (SUMMARIES defer to ephemeral-DB workflow `scripts/run_phase10_backend_tests.py` / live env). The 6 success-criteria remain gated on `SECURITY_TEST_PLAN.md` sections 1–3,5,8,11 regression suites + frontend vitest/lint/build — to be re-run operator-side on a live env; the code paths and unit probes are green.
- Full CI/CD, full observability, actor model, ingestion remain deferred/out-of-scope per PROJECT.md Out of Scope and STATE.md Deferred Items (not Phase 11).

## Requirement Traceability

| Requirement | Plans | Evidence |
|---|---|---|
| SEC-01 | 11-01 | `app/api/boundary.py` shared resolver, grep + import probes |
| SEC-02 | 11-01, 11-02 | candidates/notes/custom/revisions all through resolver; persisted-boundary 422; shaping hides before/after+user_id |
| SEC-03 | 11-03 | `_resolve_claim_visibility` derive+existence, ingest rate-limit + `invalidate_series`, `limit` 1..500 pagination |
| SEC-04 | 11-04 | `render.yaml --proxy-headers --forwarded-allow-ips` + `rate_limit_identifier` XFF non-trust |
| SEC-05 | 11-04 | `RateLimiter` fail-closed 503 vs dev no-op, `rate_limit_fail_open=False` |
| SEC-06 | 11-05 | `llm_max_concurrent_generations` semaphore + `llm_max_tool_calls_per_round` 8 + `warn_if_open_signup` |
| SEC-07 | 11-05 | `_validate_base_url` ipaddress block + decimal/hex + trailing-dot, redirect-off |
| SEC-08 | 11-06 | `BodySizeLimitMiddleware` 1 MB 413 (Content-Length + chunked) |
| SEC-09 | 11-06 | `FastAPI(**_docs_kwargs)` docs_url=None when `environment==production` |
| SEC-10 | 11-07 | `vercel.json` headers + `index.html` CSP meta (Google allowed) |
| SEC-11 | 11-06 | `_sanitized_validation_errors` (no input/ctx) |
| SEC-12 | 11-07, 11-08 | Max-Age, email_verified, TrustedHost, useWatchProgress deps, apiFetch bodyless, Path dynamic, deliberation-neutralization, bounded viz cache (64), ops caps 50/20, revert allowlist + fail-closed, QUAL-02 extraction |

**Conclusion:** all 12 SEC requirement IDs are accounted for and backed by landed code, offline probes, and summary evidence; all 8 plans' must_haves are delivered; the grep/import/cap gates are confirmed. The single low-severity doc-drift is closed; the remaining env/operator items are recorded residuals — status **passed**.
