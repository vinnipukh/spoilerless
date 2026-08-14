# S0 — Lead Engineer Independent Notes (pre-subagent synthesis)

Lead-level verification of highest-risk paths done before subagent results arrive. Used to challenge/validate subagent claims.

## Verified facts (file:line)

- **BYOK SSRF vector** — `spoilerless/app/services/chat.py:77-146` `get_llm_provider`: ANY authenticated user may send `X-LLM-Base-URL` + `X-LLM-Provider` + `X-LLM-Model` + `X-LLM-Api-Key` headers; provider POSTs `{base_url}/chat/completions` (or `/v1beta/models/{model}:streamGenerateContent?alt=sse`) with attacker-controlled JSON body. Validation = `LLMSettingsUpdate._validate_base_url` (http/https + host present only — need domain/settings.py exact rule). NO private-IP/loopback/link-local/metadata blocking, no DNS-rebinding protection. Response oracle: HTTP >=400 → 503; 200 non-SSE → empty done; SSE-shaped → content echoed to attacker. Blind-ish SSRF primitive (POST to arbitrary host, status/timing oracle, content only if SSE-shaped). httpx default follow_redirects=False (verify). Design doc says "user can only spend their own key to their own host" — the SSRF primitive against internal Render/Aura network is the residual risk. Note: AuraDB/Upstash are external SaaS; internal targets = Render service mesh, metadata (Render has no AWS-style metadata but IPv6/169.254.169.254 still probeable), localhost services.
- **Chat hardening** — `domain/chat.py:107` question max 4000 chars; pipeline: 12-tool allowlist (`retrieval/pipeline.py:441-500+`), all Neo4j tools with server-resolved `visible_until_order` (never model input), boundary gates inside every Cypher query (`retrieval/tools.py`), defense-in-depth `_visible_at` filter (pipeline.py:126-141), delimited context sections (assemble_context), citations validated against this-turn retrieved IDs only, `_MAX_TOOL_RESULT_CHARS=4000` replay cap, per-user concurrent-generation slot = 1 (in-process dict — single-worker assumption, `services/chat.py:46-74`), rate limiter chat-send 20/min/user (no-op when REDIS_URL empty or Redis down — degrade design).
- **No HTTP/scraper tools** exist in the LLM tool allowlist — the only external network call is the provider itself (BYOK or stored settings).
- **Settings API** admin-only + CSRF guard (`api/settings.py`); LLM key write-only masked; stored base_url also goes through `_validate_base_url`.
- **User notes/custom nodes**: writes auth-gated + owner-scoped + admin override; GET list/read are ANONYMOUS and return ALL users' notes/custom nodes/relationships at client-supplied `visible_until_order` — but PROBLEMS.md #4 documents notes as intentionally GLOBAL (all visitors see them; known trust-based spoiler risk, no moderation). Custom-node/relationship GETs — need to check if "global by design" applies (share module exists: api/share.py, domain/share.py).
- **Security headers** set in middleware (`main.py:47-73`): CSP, HSTS, nosniff, DENY frame, Referrer-Policy. CORS explicit origins + credentials, no wildcard (main.py:192-214).
- **/health** minimal: status/database/service (build marker) only (main.py:104-110, 222-249). No redis/version/env fields. Good.
- **Request logging** safe allowlist (main.py:76-101): method/path/status/duration + user-agent/content-type/accept only; cookie/authorization/x-llm-* denied.
- **/docs, /redoc, /openapi.json** EXPOSED in prod — `FastAPI(title=..., version=...)` at main.py:164-168 with default docs_url. Informational-to-low: full API schema incl. all routes/params public.
- **render.yaml** minimal: no env section (REDIS_URL set via dashboard), svc name spoilerless-api vs dashboard svc spoilerless (known drift, health probe = spoilerless.onrender.com). Single free web service — uvicorn single process (concurrency dict valid). No workers config.
- **Sweep task** deletes expired sessions/shares hourly (main.py:131-152).

## Open questions for subagents
1. Exact `_validate_base_url` rule (domain/settings.py) — does it reject userinfo/ports/IPs?
2. share.py semantics — do shared notes/links expose beyond boundary?
3. Auth service: session token entropy, timing-safe compare, sweep races (S2/S5).
4. Frontend LLM output rendering (XSS) (S3).
5. Rate limiter: X-Forwarded-For trust for IP key (S2/S8).
6. Dependencies: FastAPI/uvicorn/httpx/pydantic versions + known CVEs (S7).
7. Git history secret scan (S6).
8. Cache key isolation + viz cache validation (S5/S8).
