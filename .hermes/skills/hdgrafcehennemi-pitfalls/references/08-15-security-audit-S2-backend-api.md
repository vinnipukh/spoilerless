# S2 — Backend/API Security Audit Findings (2026-08-14, Spoilerless)

Condensed from `.planning/quick/20260814-security-audit/findings/S2-backend-api.md`
(subagent S2, hostile static audit of every `spoilerless/app/api` route). Use as a
knowledge bank for future backend work — do NOT re-derive. Full detail (data
flows, reproductions, 48-route test matrix) lives in the findings file.

## Verified security architecture facts (audit baseline)
- **Auth:** Google ID token via `google.oauth2.id_token.verify_oauth2_token` (signature/aud/iss/exp) + HttpOnly session cookie. Sessions = `:Session` nodes storing SHA-256 of a 48-byte `secrets.token_urlsafe` token (raw never stored); server TTL 7 days, no slide-on-read, hourly sweep. No silent verifier fallback (ProductionGoogleVerifier injected explicitly).
- **CSRF:** `verify_origin` dependency on every state-changing route (deps.py) — fails closed when both Origin and Referer absent; `"*"` in FRONTEND_ORIGINS silently disables it.
- **CORS:** explicit origins + `allow_credentials=True`, explicit method/header lists incl. `X-LLM-*` BYOK headers.
- **Error envelope:** `ErrorDetail.code` must match `^[A-Z][A-Z0-9_]*$` and be in the `ERROR_CODES` registry; global sanitized handlers for validation / Neo4j / LLM / repository sentinels (api/exceptions.py).
- **Cypher:** parametrized everywhere except two closed-set f-strings (candidates edit SET keys; revisions revert CREATE label) — safe today, fragile pattern.
- **Rate limits:** Redis pyrate-limiter buckets; login 10/5min/IP, chat 20/min/user, content-write 30/min; dependencies no-op when REDIS_URL empty or Redis down (documented).
- **LLM key:** persisted `:AppSetting {key:'llm'}`, masked (`••••last4`) in responses; BYOK `X-LLM-Api-Key/Provider/Base-URL/Model` headers override per request; headers excluded from logs.
- **Spoiler boundary:** anonymous readers fixed at order 1 on graph-family routes (PROB-04/#12); authenticated clamped via `effective_view_order = min(view_as_of, watched_through)`; boundary must be a persisted episode order.

## Open findings (12) — top 6
1. **SEC-BE-001 HIGH (CONFIRMED):** `get_graph` (api/graph.py:124-140) and `list_episodes` (api/series.py:87-97) do NOT clamp authenticated users **without a progress record** to order 1 — `effective = requested` stays client-chosen, while the shared `_resolve_effective_boundary` helper (graph.py:425-437) fails closed to 1. Fresh account + `?visible_until_order=96` = full spoiler dump. Fix: treat `record is None` as `effective = 1` in both routes.
2. **SEC-BE-002 HIGH (CONFIRMED):** anonymous reads on notes / custom-nodes / custom-relationships / candidates (`api/user_content.py:51-77,126-129,177-180`; `api/candidates.py:145-207`) accept any persisted-episode boundary with no anon clamp → all users' content (+ author `user_id`) and unreviewed candidates readable by anyone.
3. **SEC-BE-003 HIGH (CONFIRMED):** `POST .../candidates/ingest` (ANY authenticated user, not admin) persists client-chosen `visible_from_order` with no validation against the episode's real order, and never checks subject/object/episode exist in-series (graph/candidates.py:35-99,132) → spoiler poisoning visible to anonymous readers at boundary 1.
4. **SEC-BE-004 MED (CONFIRMED):** `render.yaml` startCommand runs uvicorn WITHOUT `--proxy-headers` → `request.client.host` is Render's proxy IP for everyone → per-IP limiter is one global bucket (login 10/5min = global login lockout). If flags are added later, must pin `--forwarded-allow-ips`.
5. **SEC-BE-005 MED (CONFIRMED, code-documented accepted):** BYOK `X-LLM-Base-URL` allows any authenticated user to point the backend at arbitrary http(s) hosts (loopback/private ranges NOT blocked; domain/settings.py:27-34) → internal SSRF + HTTP-status oracle. Fixed verb `POST /chat/completions`; response exfil limited to OpenAI-shaped JSON.
6. **SEC-BE-006 MED (CONFIRMED):** ingest per-claim `except Exception` returns `str(exc)` to the client (graph/candidates.py:147-151) — raw Neo4j driver messages leak despite sanitized global handlers.

Others: SEC-BE-007 (ALLOWED_EMAILS empty default unenforced at startup; `email_verified` never checked in services/auth.py:159-177 — config risk, NEEDS MANUAL VERIFICATION), SEC-BE-008 (unbounded strings on ingest/EditCandidateRequest/PathRequest; no body-size cap), SEC-BE-009 (`/graph/expand` anonymous + uncached ≈ 9 Neo4j queries/request → DoS), SEC-BE-010 (session cookie no Max-Age; no per-user session cap), SEC-BE-011 (f-string Cypher, closed sets, informational), SEC-BE-012 (share token in URL; `*` origins disable CSRF).

## Safe audit constraints that worked
- Static analysis + safe unit tests only; NEVER touch live Neo4j or send network requests; never read .env secret VALUES (check defaults + which vars render.yaml/Dockerfile define instead).
- Windows git-bash: `unset PYTHONPATH` before running python.
- `search_files` regex mangling (escapes double-processed; patterns with `(`, `{`, `"`, `|` fail) → fall back to `grep -rn` in terminal for complex patterns.
