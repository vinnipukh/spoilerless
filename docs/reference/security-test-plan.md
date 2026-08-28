# SECURITY_TEST_PLAN.md — Spoilerless

Regression tests derived from SECURITY_AUDIT.md (2026-08-15 audit). Each test maps to findings; most map to existing test seams (`spoilerless/tests/` uses FastAPI TestClient + FakeLLMProvider; frontend uses Vitest). Priority order = P0 findings first. "CI-ready" = automatable in the existing pytest/vitest pipelines.

---

## 1. Spoiler-boundary enforcement (P0 — SEC-BE-001, SEC-BE-002, SEC-ADV-003)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 1.1 | Anonymous `GET /api/series/{id}/candidates?visible_until_order=999` returns only order-1 content (empty or order-1 only) | SEC-BE-002 | ✅ pytest |
| 1.2 | Anonymous `GET /notes`, `/custom-nodes/{id}`, `/custom-relationships/{id}` with `visible_until_order=999` returns only order-1 content | SEC-BE-002 | ✅ |
| 1.3 | Anonymous `GET /revisions?visible_until_order=999` returns only order-1 revisions; response contains NO `before`/`after` payload or `user_id` for non-owners | SEC-BE-002 | ✅ |
| 1.4 | `GET /graph` + `/episodes` with a valid session whose user has **no progress record** returns boundary-1 graph (fail-closed), not `visible_until_order` requested | SEC-BE-001 | ✅ |
| 1.5 | Same as 1.4 but authenticated user WITH progress: boundary = min(requested, persisted) | SEC-BE-001 | ✅ |
| 1.6 | `visible_until_order=0`, negative, non-int, absent → 422; notes/custom/revisions GET with non-persisted order → 422 (after persisted-episode validation added) | SEC-ADV-003 | ✅ |
| 1.7 | `GET /graph/visualization`, `/expand`, `/export`, `/graph/path` anonymous → boundary 1; authenticated no-record → boundary 1 | SEC-BE-001 | ✅ |
| 1.8 | Share snapshot: token graph never exceeds creator's persisted boundary even if client requests higher | CR-01 (positive) | ✅ |

## 2. Candidate ingest trust (P0 — SEC-BE-003, SEC-ADV-001, SEC-ADV-002)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 2.1 | Ingest with body `visible_from_order: 1` is stored at SERVER-derived visibility (order 1 only if subject/object/episode exist at order 1), never client-chosen | SEC-BE-003 | ✅ |
| 2.2 | Ingest with non-existent subject_id / object_id / episode_id → 422/404, no node created | SEC-BE-003 | ✅ |
| 2.3 | Ingest rejected when exceeding rate limit (content-write bucket after fix) | SEC-ADV-001 | ✅ |
| 2.4 | After ingest, `GET /graph` (cached path) reflects the new candidate within one invalidation — no stale window > TTL | SEC-ADV-002 | ✅ |
| 2.5 | Anonymous ingest → 401; ingest without CSRF Origin → 403 | SEC-BE-003 | ✅ |
| 2.6 | Candidate approve/reject/edit remain admin-only (non-admin → 403) | — (positive) | ✅ |

## 3. Rate limiting & availability (P0/P1 — SEC-BE-004, SEC-DOS-001, SEC-DOS-003)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 3.1 | Login limiter: 11th `POST /api/auth/google` from distinct client IPs within 5 min → each IP counted separately (needs `--proxy-headers` config in test env: simulate distinct `X-Forwarded-For` only when `forwarded-allow-ips` permits) | SEC-BE-004 | ✅ |
| 3.2 | Login limiter fail-closed: Redis unavailable → login still rate-limited (or startup fails loudly) — NO silent no-op in prod mode | SEC-DOS-001 | ✅ (with flag) |
| 3.3 | Chat limiter: 21st message within 60s → 429 per user | SEC-DOS-002 | ✅ |
| 3.4 | XFF spoofing: crafted `X-Forwarded-For` does NOT change the rate-limit key when proxy trust is properly configured | SEC-BE-004 | ✅ |
| 3.5 | 500-claim ingest batch → 429 after limit added (SEC-ADV-001 rate bucket) | SEC-ADV-001 | ✅ |

## 4. LLM / prompt-injection containment (P1 — SEC-LLM-004, SEC-GR-013)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 4.1 | Existing prompt-injection suite extends: poisoned note/claim text containing "ignore previous instructions / reveal system prompt" stays inside `<claims>`/`<notes>` sections in the assembled context (assert via `FakeLLMProvider.calls`) | SEC-LLM-004 | ✅ (extends `test_prompt_injection.py`) |
| 4.2 | Delimiter-neutralization: context content containing `<claims>`-style tags cannot close/reopen sections (escape or strip tags in formatters) | SEC-LLM-004 | ✅ |
| 4.3 | Model cites only IDs retrieved this turn: fabricated claim_id in model citations → stripped; all-stripped answer → INSUFFICIENT_EVIDENCE fallback | — (positive) | ✅ |
| 4.4 | `propose_changeset` with >N operations → 422 (after cap added) | SEC-LLM-007 | ✅ |
| 4.5 | User content (custom-node label, note text) does NOT appear in other users' retrieval context (per-user notes isolation) | SEC-GR-013 | ✅ |
| 4.6 | Beyond-boundary entity query via any tool returns empty/fail-closed — not distinguishable from missing (no existence oracle through chat) | SEC-GR-008 | ✅ |

## 5. SSRF hardening (P1 — SEC-LLM-001/002)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 5.1 | `X-LLM-Base-URL: http://127.0.0.1`, `http://169.254.169.254`, `http://[::1]`, `http://10.0.0.1`, `http://172.16.0.1`, `http://192.168.1.1`, `http://localhost` → 422 (after blocklist added), both BYOK and stored settings paths | SEC-LLM-001 | ✅ |
| 5.2 | `X-LLM-Base-URL: http://example.com@127.0.0.1`, decimal/hex IP forms, trailing-dot hosts → 422 | SEC-LLM-001 | ✅ |
| 5.3 | Redirect-chasing: mock provider URL that 302s to a private host → request must NOT follow (or be rejected at DNS) | SEC-LLM-001 | ✅ (httpx MockTransport) |
| 5.4 | Gemini provider path: `model` value with `/` or `?` cannot alter request path/host (URL-encode or validate model token) | SEC-LLM-001 | ✅ |
| 5.5 | Stored settings path: PUT /api/settings/llm with private base_url → 422 (admin-only route) | SEC-LLM-002 | ✅ |

## 6. Cache isolation & poisoning (P1 — SEC-DOS-005)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 6.1 | Cached graph for boundary B never served for boundary B' > B (same series/user) | — (positive) | ✅ |
| 6.2 | User A's cached graph (user-scoped key) never served to user B or anonymous | — (positive) | ✅ |
| 6.3 | Poisoned viz entry (tampered projection_version / view_type / effective_view_order) → rejected as miss (existing T10-CACHE-02/03) | — (positive) | ✅ |
| 6.4 | Focus-set explosion: N distinct `focus_id[]` combos create ≤K distinct cache keys (after redesign) | SEC-DOS-005 | ✅ |

## 7. Auth & session (P1/P2 — SEC-BE-007, SEC-BE-010)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 7.1 | Google token claims with `email_verified: false` → 401 (after check added) | SEC-BE-007 | ✅ (FakeGoogleVerifier) |
| 7.2 | Session cookie carries Max-Age = session_ttl (after fix) | SEC-BE-010 | ✅ |
| 7.3 | Cross-owner mutations: user B patches/deletes user A's note/custom-node → 403 (existing) | — (positive) | ✅ |
| 7.4 | Session token entropy + hash-at-rest assertions (existing tests) | — (positive) | ✅ |

## 8. Input limits & body size (P0/P1 — SEC-DOS-004, SEC-BE-008)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 8.1 | Request body > configured limit (e.g. 1 MB) → 413, worker survives | SEC-DOS-004 | ✅ |
| 8.2 | `ChangeSetCreateRequest.operations` with > cap → 422 | SEC-DOS-004 | ✅ |
| 8.3 | Question = 4001 chars → 422 (existing), and server log does NOT contain the question text | SEC-LOG-001 | ✅ |

## 9. XSS / rendering regression guard (P1 — SEC-FE-001, SEC-FE-003)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 9.1 | Vitest: LLM response, node label, note content containing `<script>`, `javascript:` URL, `data:` URL → rendered as text; no `dangerouslySetInnerHTML` introduced (lint rule) | SEC-FE-010 | ✅ vitest + eslint |
| 9.2 | DB-supplied URL with `javascript:` scheme → not rendered as `href`/`src` (after scheme validation added) | SEC-FE-003 | ✅ |
| 9.3 | `vercel.json` headers include CSP (assert via config test / deployment check) | SEC-FE-001 | ✅ (config assert) |

## 10. DoS / resource bounds (P1/P2 — SEC-DOS-006/009/010)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 10.1 | Session detail / context assembly caps message history (assert bounded list after fix) | SEC-DOS-006 | ✅ |
| 10.2 | `GET /graph/expand` respects limit ≤25 and is rate-limited or cached (after fix) | SEC-DOS-010 | ✅ |
| 10.3 | Concurrent generation: 2nd parallel stream for same user → 429 (existing T-06-13) | — (positive) | ✅ |

## 11. Deployment & exposure (P0/P1 — SEC-INF-003, SEC-LOG-001)

| # | Test | Finding | CI-ready |
|---|------|---------|----------|
| 11.1 | With `ENVIRONMENT=production` (or `DISABLE_DOCS=true`), `/docs`, `/redoc`, `/openapi.json` → 404 | SEC-INF-003 | ✅ |
| 11.2 | Validation-error log line contains NO `input` field / raw body (after fix) | SEC-LOG-001 | ✅ (caplog) |
| 11.3 | Request log never contains Cookie/Authorization/X-LLM-* values (existing allowlist test, extend) | — (positive) | ✅ |

---

## CI integration notes

- **pytest:** all backend tests fit the existing `spoilerless/tests/` harness (TestClient, dependency_overrides, FakeLLMProvider, NoopGoogleVerifier). Boundary tests need a scratch-series fixture pattern (see memory: never pollute `series_dexter`; use scratch series + teardown).
- **vitest:** sections 9 via component tests + eslint rule for `dangerouslySetInnerHTML`.
- **GitHub Actions:** gate the PR pipeline on the full P0 set (sec-1..3, 8, 11) once implemented; npm audit gate must be fixed first (SEC-DEP-007 — red today).
- **Not CI-able:** 3.2 (prod fail-closed flag), 7.1/7.4 (external verifier), 11.3 (prod logs) — flagged as manual/ops checks in the audit.

---

## Phase 11 — Ticked checkboxes (11-01..11-07)

| 1.1 | Anonymous candidates 999 → order-1 | SEC-BE-002 | [x] (11-01) |
| 1.2 | Anonymous notes/custom reads clamped | SEC-BE-002 | [x] (11-02) |
| 1.3 | Anonymous revisions shaped | SEC-BE-002 | [x] (11-02) |
| 1.4 | Graph/episodes no-record → 1 | SEC-BE-001 | [x] (11-01/11-02) |
| 1.5 | Auth WITH progress min | SEC-BE-001 | [x] (11-01) |
| 1.6 | Invalid orders 422 | SEC-ADV-003 | [x] (11-02) |
| 1.7 | Viz/expand/export/path anonymous →1 | SEC-BE-001 | [x] (11-02) |
| 1.8 | Share snapshot | CR-01 | [x] (11-02) |
| 2.1 | Ingest server-derived visibility | SEC-BE-003 | [x] (11-03) |
| 2.2 | Ingest non-existent refs | SEC-BE-003 | [x] (11-03) |
| 2.3 | Ingest rate limit | SEC-ADV-001 | [x] (11-03) |
| 2.4 | Cache invalidation | SEC-ADV-002 | [x] (11-03) |
| 2.5 | Anonymous ingest 401 | SEC-BE-003 | [x] (11-03) |
| 2.6 | Approve admin-only | — | [x] (11-03) |
| 3.1 | Per-IP limiter | SEC-BE-004 | [x] (11-04) |
| 3.2 | Fail-closed 503 | SEC-DOS-001 | [x] (11-04) |
| 3.3 | Chat limiter | SEC-DOS-002 | [x] (11-04) |
| 3.4 | XFF spoof | SEC-BE-004 | [x] (11-04) |
| 3.5 | Ingest batch limit | SEC-ADV-001 | [x] (11-03) |
| 5.1 | SSRF loopback | SEC-LLM-001 | [x] (11-05) |
| 5.2 | SSRF decimal/hex | SEC-LLM-001 | [x] (11-05) |
| 5.3 | Redirect not followed | SEC-LLM-001 | [x] (11-05) |
| 5.4 | Gemini model sanitize | SEC-LLM-001 | [x] (11-05) |
| 5.5 | Stored SSRF | SEC-LLM-002 | [x] (11-05) |
| 8.1 | Body limit 413 | SEC-DOS-004 | [x] (11-06) |
| 8.2 | Ops cap 422 | SEC-DOS-004 | [x] (11-06) |
| 8.3 | Question cap | SEC-LOG-001 | [x] (11-06) |
| 11.1 | Docs off 404 | SEC-INF-003 | [x] (11-06) |
| 11.2 | Log sanitized | SEC-LOG-001 | [x] (11-06) |
| 11.3 | Request log allowlist | — | [x] (11-06) |
| 7.1 | email_verified false → 401 | SEC-BE-007 | [x] (11-07) |
| 7.2 | Max-Age cookie | SEC-BE-010 | [x] (11-07) |
| 9.3 | vercel.json CSP | SEC-FE-001 | [x] (11-07) |
