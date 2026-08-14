# Phase 11 CONTEXT — Security Hardening (audit remediation)

Locked decisions from the 2026-08-15 adversarial audit (SECURITY_AUDIT.md). The audit IS the spec — do not revisit scope. Every finding ID below is authoritative; fix exactly what it names, nothing more.

## Scope

**P0 (must land):** SEC-BE-001, SEC-BE-002 (+SEC-ADV-003), SEC-BE-003 (+SEC-ADV-001/002), SEC-BE-004/SEC-DOS-003, SEC-DOS-001, SEC-DOS-002, SEC-LLM-001/002, SEC-DOS-004, SEC-INF-003, SEC-FE-001, SEC-LOG-001.
**P1 (include):** SEC-LLM-004 (output guard + delimiter neutralization), SEC-DOS-005 (cache-key redesign — bounded focus sets), SEC-BE-010 (session Max-Age), SEC-BE-007 (`email_verified` check), SEC-LOG-006 (TrustedHostMiddleware), SEC-ADV-001 (ingest rate limit + pagination), SEC-GR-014 (revert label allowlist), SEC-LLM-007 (propose_changeset ops cap).
**Out of scope (P2/P3):** least-privilege Neo4j user, key-at-rest encryption, SRI, retention policy, origin-lock behind Cloudflare, Actions SHA-pinning, /health trim.

## Locked design decisions

1. **Single boundary resolution path.** Extend the existing `_resolve_effective_boundary` helper (spoilerless/app/api/graph.py:426-437) — or a shared equivalent — to EVERY spoiler-sensitive read: graph, episodes, candidates list/get, notes list/get, custom-nodes get, custom-relationships get, revisions list/get, export, visualization, expand, path. Anonymous ⇒ order 1; authenticated without progress record ⇒ order 1 (fail closed); authenticated with record ⇒ min(requested, view_as_of, watched_through). Delete the divergent clamp at graph.py:124-140 / series.py:87-94.
2. **Revisions/candidates response shaping.** Non-owner (incl. anonymous) responses must NOT include `before`/`after` snapshots or `user_id`; owner/admin keep full detail. Persisted-episode validation for `visible_until_order` on notes/custom/revisions GET (like candidates already does) — invalid order ⇒ 422.
3. **Ingest hardening.** `visible_from_order` is derived server-side via the existing `derive_visible_from_order` rule (spoilerless/app/spoiler/visibility.py); subject/object/episode existence validated; ingest gets the content-write rate-limit bucket (or its own); `invalidate_series` called after ingest. Client-supplied visibility values are ignored (422 or dropped — pick one, be consistent).
4. **Trusted proxy.** render.yaml startCommand gains `--proxy-headers --forwarded-allow-ips` with the Render proxy CIDR range (documented placeholder; operator confirms final value) — OR a site-wide login circuit breaker if IPs are infeasible. Local docker dev must keep working (no proxy). XFF spoofing test: crafted X-Forwarded-For must NOT change the rate-limit key.
5. **Fail-closed rate limiting.** New env flag (e.g. `RATE_LIMIT_FAIL_OPEN=false` default in prod config; local dev keeps degrade behavior) — when Redis is unavailable, login + chat + content-write paths must NOT silently run unthrottled (503 or explicit throttle), while read caches may still degrade. Keep the existing per-request no-op for dev when `REDIS_URL` empty.
6. **SSRF hardening.** `LLMSettingsUpdate._validate_base_url` (spoilerless/app/domain/settings.py:62-81) gains: resolve hostname → reject loopback/private/link-local/metadata IPv4+IPv6 (use `ipaddress` module; also reject raw-IP literals, decimal/hex forms, trailing-dot hosts, `localhost`); both BYOK headers and stored settings paths share the check. Redirect handling: httpx client stays redirect-off (verify default; assert in tests).
7. **LLM cost controls.** Global asyncio.Semaphore (process-wide, configurable, default e.g. 4) around provider calls in addition to the per-user slot; per-round tool-call cap ≤8 in the pipeline loop (retrieval/pipeline.py:822 area); per-user daily token budget is OPTIONAL (skip if complex — flag as not-implemented in SUMMARY). `ALLOWED_EMAILS` prod requirement is operator-side; add a startup warning when empty in production mode (do not hard-fail — local dev needs empty).
8. **Body-size limit.** Starlette middleware rejecting bodies over a config cap (default e.g. 1 MB; Content-Length and chunked both handled) → 413. `ChangeSetCreateRequest.operations` gets a max (e.g. 50). `question` cap already exists (4000).
9. **Docs off in prod.** `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` when `ENVIRONMENT=production` (new setting; default dev keeps docs).
10. **CSP shell.** `vercel.json` `headers` block with the same CSP/HSTS/nosniff/XFO/Referrer-Policy as backend `_SECURITY_HEADERS` (main.py:47-59); `index.html` gets a CSP meta fallback (dev). Keep Google Identity Services allowed (script-src https://accounts.google.com).
11. **Log sanitization.** Validation-error handler (core/errors.py:234) logs `errors()` with `input`/`ctx` fields stripped (or a sanitized summary); never raw bodies. PII emails on denied sign-in stay (out of scope) or get truncated — pick one, note in SUMMARY.
12. **P1 details.** Session cookie Max-Age = session_ttl_seconds; `email_verified is not True` ⇒ reject in ProductionGoogleVerifier path (auth.py); TrustedHostMiddleware with hosts from FRONTEND_ORIGINS + api domain (config `allowed_hosts`); context formatters neutralize delimiter tags (`<claims>` etc. inside retrieved text — escape angle brackets) per SEC-LLM-004; viz cache key focus set bounded (canonicalize to ≤N distinct focus signatures per series, e.g. cap distinct keys); `propose_changeset` operations ≤20.

## Constraints (project rules)

- Minimal-scope literal fixes. No drive-by refactors. Match existing style (StrictModel pydantic, parameterized Cypher, error envelope codes lowercase `^[a-z][a-z0-9_]*$`).
- Tests: scratch-series + teardown, never pollute series_dexter; drift-agnostic asserts; live-DB tests only via existing patterns; never touch real dev user rows (ae8a41b7-...).
- Full backend suite ONLY via scripts/run_phase10_backend_tests.py (refuses while local docker spoilerless-neo4j is live — docker stop first, restart after).
- Do NOT run `npm audit --audit-level=high` gate fixes (SEC-DEP-007) in this phase.
- Docs: update SECURITY_ATTACK_SURFACE.md route table + SECURITY_TEST_PLAN.md checkboxes at phase end; PROBLEMS.md ledger entry (append numbered pass).
- Render dashboard Start Command must stay `uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT` — render.yaml is the source of truth for repo-side changes; do not touch the dashboard.

## Verification sources

- SECURITY_AUDIT.md (findings, chains, P0–P3 roadmap)
- SECURITY_TEST_PLAN.md (sections 1–3, 5, 8, 11 are the acceptance tests for this phase)
- Per-agent evidence: .planning/quick/20260814-security-audit/findings/S{1..10}-*.md
