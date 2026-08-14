# S2 — Backend/API Security Audit Findings (Spoilerless)

**Auditor:** S2 (backend/API security subagent)
**Scope:** every HTTP endpoint in `spoilerless/app/api/` plus supporting services (`services/`, `repository/`, `graph/`, `spoiler/`, `cache/`, `llm/provider.py`, `core/`), `main.py`, and the Render launch config (`render.yaml`).
**Method:** hostile static analysis — "if I am an anonymous hostile internet user with curl, what can I make this app do?" No live DB touched, no network attacks, no secrets read.

---

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 0 |
| HIGH | 3 |
| MEDIUM | 4 |
| LOW | 3 |
| INFORMATIONAL | 2 |
| **Total** | **12** |

The app's auth/session primitives (48-byte tokens, SHA-256 hashed server-side, HttpOnly+Secure+SameSite cookie, per-route CSRF origin guard, parameterized Cypher everywhere except two closed-set f-strings) are genuinely strong. The vulnerabilities cluster around **spoiler-boundary enforcement inconsistencies** (the app's core security property), **anonymous read surfaces that ignore the boundary clamp**, and **proxy/rate-limit configuration**.

---

## Findings

### SEC-BE-001 | Spoiler-boundary bypass for authenticated users with no progress record on graph/episodes reads | HIGH | CONFIRMED
- **Component:** `spoilerless/app/api/graph.py:124-140` (`get_graph`), `spoilerless/app/api/series.py:87-97` (`list_episodes`)
- **Entry point:** `GET /api/series/{series_id}/graph?visible_until_order=N` and `GET /api/series/{series_id}/episodes?visible_until_order=N` with a valid session cookie for an account that has never set progress.
- **Data flow:** cookie → `require_current_user` → `visible_until_order` query param → `effective = requested` → no progress record found → effective stays client-chosen → `fetch_graph(series_id, effective, ...)` → full spoiler-safe-filtered-at-N graph.
- **Vulnerability:** `get_graph` sets `effective = requested` (line 133) and only clamps when `progress_service.get(...)` returns a record (lines 135-140). A fresh account has no `:UserSeriesProgress` row (nothing creates one at login; only `POST /progress` or chat auto-create). The sibling helper `_resolve_effective_boundary` (api/graph.py:425-437) *does* fail closed to order 1 for record-less users — the two paths disagree. Same defect in `api/series.py:87-97`.
- **Attack scenario:** attacker signs in with any Google account, never sets progress, then `curl -b session=<cookie> '/api/series/series:dexter/graph?visible_until_order=96'` → full graph including late-season characters, claims, evidence, sources.
- **Impact:** complete defeat of the app's core spoiler-boundary guarantee for every new account; spoiler data exfiltration at scale (scrape all episodes).
- **Reproduction (safe, read-only):** unit-level: instantiate `GraphService`/`ProgressService` against a throwaway in-memory/fake repo; assert `get_graph` with `visible_until_order=99` and no progress record yields `effective == 99` while `_resolve_effective_boundary(..., user=...)` yields 1. No live DB required.
- **Existing defenses:** `resolve_boundary` requires the order to be a persisted episode (limits to valid orders, doesn't limit the value); anonymous users are fixed at 1; visualization/expand/path/export use the correct fail-closed helper.
- **Recommended fix:** in both routes, treat a missing progress record exactly like `_resolve_effective_boundary` does: `effective = 1` (fail closed) when `record is None`.
- **Verification:** test asserting `effective == 1` for authenticated user without progress record on both routes; regression test comparing `get_graph` and `_resolve_effective_boundary` behavior for the same inputs.

---

### SEC-BE-002 | Anonymous spoiler-boundary bypass + cross-user content exposure on user-content and candidate read routes | HIGH | CONFIRMED
- **Component:** `spoilerless/app/api/user_content.py:51-77, 126-129, 177-180`; `spoilerless/app/repository/user_content.py:392-414, 536-545, 803-816`; `spoilerless/app/api/candidates.py:145-207`; `spoilerless/app/graph/candidates.py:252-330`
- **Entry point:** `GET /api/series/{series_id}/notes?visible_until_order=N`, `GET /api/series/{series_id}/notes/{note_id}?visible_until_order=N`, `GET .../custom-nodes/{node_id}?visible_until_order=N`, `GET .../custom-relationships/{relationship_id}?visible_until_order=N`, `GET /api/series/{series_id}/candidates?visible_until_order=N`, `GET .../candidates/{claim_id}?visible_until_order=N`
- **Data flow:** anonymous request → no user dependency at all (no `OptionalUserDependency`) → boundary validated only against persisted episode orders (`_require_persisted_boundary`, user_content.py:803-816; `_require_resolved_boundary`, api/candidates.py:42-67) → rows filtered `visible_from_order <= N`.
- **Vulnerability:** every graph-family read clamps anonymous readers to order 1 (PROB-04/#12), but these six read routes accept any persisted episode order from an unauthenticated client and never clamp. `N` = last episode order returns *every* note/custom-node/custom-relationship/candidate claim in the series, including content from other users (responses expose `user_id` of authors) and unreviewed `origin:'candidate'` extraction output.
- **Attack scenario:** `curl '/api/series/series:dexter/notes?visible_until_order=96'` with no cookie → all users' private-ish notes (theoretical content, spoilers) + author account ids; `curl '.../candidates?visible_until_order=96'` → full unreviewed candidate corpus (spoiler + unvetted content).
- **Impact:** spoiler disclosure at order 1-equivalent surface; privacy disclosure of user-generated content and author identifiers; candidate claims are also a graph-poisoning delivery channel (see SEC-BE-003).
- **Reproduction (safe):** code-level — assert these routes declare no auth dependency and that `list_notes(series, 999)` is reachable anonymously; unit test `_require_persisted_boundary` accepts the max episode order for an anonymous caller.
- **Existing defenses:** boundary must identify a persisted episode; notes/custom nodes/claims carry `visible_from_order` and are filtered; `extra="forbid"` models; generic 404s for hidden/missing.
- **Recommended fix:** add `OptionalUserDependency` and clamp `effective = 1` when `user is None` (mirror `_resolve_effective_boundary`); decide and document whether user content is public-by-design; if public, still clamp anonymous to 1.
- **Verification:** test: anonymous `visible_until_order=max` returns empty/order-1 set on all six routes; authenticated owner sees their content at their boundary.

---

### SEC-BE-003 | Any authenticated user can ingest spoiler content at client-chosen `visible_from_order=1`, visible to anonymous readers | HIGH | CONFIRMED
- **Component:** `spoilerless/app/api/candidates.py:121-142` (`POST /ingest` — `CurrentUserDependency` only, NOT admin); `spoilerless/app/graph/candidates.py:35-99` (`INGEST_CANDIDATE_QUERY`), `:101-156` (`_ingest_candidate_claims`); `spoilerless/app/domain/extraction.py:90-119` (`ExtractionClaim.visible_from_order`)
- **Entry point:** `POST /api/series/{series_id}/candidates/ingest` body `{"extractor_name": "...", "claims": [{"predicate": "...", "subject_id": "...", "object_id": "...", "visible_from_order": 1, "episode_id": "...", ...}]}`
- **Data flow:** authenticated user → `extractor_name`/`visible_from_order`/`predicate`/ids taken verbatim → `tx.run(INGEST_CANDIDATE_QUERY, parameters)` → `:Claim {origin:'candidate', visible_from_order: <client value>}` + `:Source` + `:EvidenceFragment` nodes → readable by anonymous clients at boundary 1 (SEC-BE-002).
- **Vulnerability:** (a) `visible_from_order` is client-controlled with no validation against the claimed `episode_id`'s real order or the ingester's own progress — the server-side visibility-derivation rule used everywhere else (CUSTOM_RELATIONSHIP_CREATE_QUERY, ChangeSet apply) is bypassed; (b) `subject_id`/`object_id`/`episode_id` are never checked to exist in the series; (c) ingest is gated only on *any* authenticated user (comment: "candidate claims are review-workflow artifacts" — but they are publicly readable, so un-reviewed attacker content is the public surface).
- **Attack scenario:** attacker logs in, `curl -X POST .../candidates/ingest -H 'Content-Type: application/json' -d '{"extractor_name":"x","claims":[{"predicate":"Dexter kills X in S08E10","subject_id":"character:dexter","object_id":"character:x","claim_type":"observed_event","visible_from_order":1,"evidence_text":"spoiler","evidence_locator":"S08E10:00:01","source_type":"transcript","source_locator":"s","episode_id":"episode:dexter:s08e10"}]}'` → any anonymous visitor at boundary 1 sees the spoiler claim in the candidates list.
- **Impact:** spoiler poisoning of the public read surface; graph-data integrity pollution (claims referencing nonexistent nodes); the canonical-graph protection (admin approve) is not the issue — *display before review* is.
- **Reproduction (safe):** unit test `_ingest_candidate_claims` with a fake tx asserting the persisted `visible_from_order` equals the client value for an episode whose real order is higher; assert no existence check on subject/object ids (query text contains no MATCH on `:Character {id: $subject_id}`).
- **Existing defenses:** `claim_type`/`confidence_level` ontology allowlists; deterministic content-derived ids (idempotent MERGE); claim list capped at 500; approve/reject/edit admin-only.
- **Recommended fix:** server-derive `visible_from_order` from the resolved episode's persisted order (min of subject/object/episode), require subject/object/episode to exist in-series, and clamp anonymous candidate reads to order 1 (SEC-BE-002) or gate ingest to admin.
- **Verification:** test asserting persisted `visible_from_order` equals the episode's real order regardless of the client-supplied value, and that unknown ids produce `INGEST_ERROR` (or 422).

---

### SEC-BE-004 | Per-IP rate limits collapse into one global bucket behind Render's proxy (uvicorn launched without `--proxy-headers`) | MEDIUM | CONFIRMED
- **Component:** `render.yaml:10` (`startCommand: uv run uvicorn spoilerless.app.main:app --host 0.0.0.0 --port $PORT`); `spoilerless/app/services/rate_limit.py:41-50` (`rate_limit_identifier` uses `request.client.host`)
- **Entry point:** `POST /api/auth/google` (login limiter 10/5min), plus any anonymous fallback keying.
- **Data flow:** client → Render edge proxy → uvicorn (proxy_headers defaults OFF) → `request.client.host` = the proxy's IP for every user → `ip:<proxy-ip>` bucket shared by the whole internet.
- **Vulnerability:** with proxy headers disabled, `client.host` is the direct peer (Render's proxy), so *all* anonymous requests share one rate-limit key. The login limiter (10 per 5 minutes) becomes a global bucket.
- **Attack scenario:** attacker opens a few parallel connections and deliberately fails 10 logins → **all** legitimate logins app-wide return 429 for 5 minutes; repeat → permanent login outage (no per-attacker attribution possible). Conversely, if an operator later adds `--proxy-headers` without `--forwarded-allow-ips`, X-Forwarded-For becomes attacker-spoofable and the limiter is trivially bypassed by rotating the header.
- **Impact:** availability (global login lockout); rate limiting is ineffective per-attacker either way in the current config.
- **Reproduction (safe):** read-only — confirm `render.yaml` startCommand has no `--proxy-headers`/`--forwarded-allow-ips` (done); unit test `rate_limit_identifier` returns the same key for two different spoofed `X-Forwarded-For` values when no proxy-headers middleware is installed.
- **Existing defenses:** Redis-backed atomic bucket (correct across workers); degrade-to-no-op on Redis outage (intended); authenticated routes key on user id so chat/content limits still work per-user.
- **Recommended fix:** launch with `--proxy-headers --forwarded-allow-ips <Render's proxy CIDRs>` (or a trusted proxy list), or key the login limiter on a `CF-Connecting-IP`/`X-Forwarded-For` value only after validating it against a trusted proxy; document the expected proxy topology.
- **Verification:** integration test behind a mocked proxy: two distinct XFF values produce distinct limiter keys; a 5-minute global bucket can no longer be exhausted by one client.

---

### SEC-BE-005 | BYOK `X-LLM-Base-URL` header enables authenticated SSRF into internal networks | MEDIUM | CONFIRMED (documented as accepted in code)
- **Component:** `spoilerless/app/services/chat.py:77-146` (`get_llm_provider`); `spoilerless/app/domain/settings.py:27-34, 62-81` (`_ALLOWED_LLM_URL_SCHEMES = ("http","https")`, comment explicitly acknowledges the residual risk)
- **Entry point:** `POST /api/series/{series_id}/chat/sessions/{session_id}/messages[/stream]` with headers `X-LLM-Api-Key: k`, `X-LLM-Base-URL: http://169.254.169.254` (or any internal host), `X-LLM-Model: m`
- **Data flow:** authenticated user header → scheme+host validation (http/https only, host required — no private/loopback/link-local blocking) → `httpx.AsyncClient(base_url=..., headers={"Authorization": "Bearer <user key>"})` → `POST {base_url}/chat/completions` with attacker-chosen model + question body.
- **Vulnerability:** any authenticated user can make the backend issue HTTP POSTs to arbitrary http(s) hosts: internal Render services, the app itself (self-SSRF), cloud metadata endpoints, Redis/Neo4j admin HTTP ports. Response bodies are only parsed as OpenAI-shaped SSE JSON (limited exfil), but HTTP status codes surface to the client (`LLM_PROVIDER_UNAVAILABLE: LLM provider returned HTTP 404`), giving a reachability/status oracle; timing + DNS rebinding add further probing power.
- **Attack scenario:** `curl -H 'X-LLM-Api-Key: x' -H 'X-LLM-Base-URL: http://<internal-render-service>:8080' -H 'X-LLM-Model: x' -d '{"question":"hi"}' .../messages` → internal port scan / endpoint probing / POST-based abuse of internal HTTP services, all attributed to the backend's egress IP.
- **Impact:** internal network reconnaissance and abuse; potential interaction with internal-only admin surfaces; per-request cost/abuse of the app's own egress.
- **Reproduction (safe):** unit test `get_llm_provider` with `httpx.MockTransport` asserting the request URL for `X-LLM-Base-URL: http://127.0.0.1:9999` is `http://127.0.0.1:9999/chat/completions` (no network egress).
- **Existing defenses:** scheme allowlist blocks `file://`, `gopher://` etc.; `X-LLM-*` headers excluded from logs; the key is the user's own (no shared-secret exfiltration); CORS allowlist covers the headers; validation reuses the stored-settings validator.
- **Recommended fix:** block loopback/link-local/private ranges (or require an explicit allowlist) for BYOK base URLs, or route BYOK egress through a fixed proxy; at minimum document the accepted risk with a config toggle (per the code's own 06-SECURITY.md note).
- **Verification:** test that `http://127.0.0.1`, `http://169.254.169.254`, `http://10.*`, `http://192.168.*` base URLs are rejected with 422 while public hosts pass.

---

### SEC-BE-006 | Neo4j driver exception messages returned verbatim to clients on candidate ingest | MEDIUM | CONFIRMED
- **Component:** `spoilerless/app/graph/candidates.py:147-151` (`errors.append({... "message": str(exc)})`), route `api/candidates.py:121-142`
- **Entry point:** `POST /api/series/{series_id}/candidates/ingest` with a payload that triggers a DB error (e.g., property value too large, constraint violation, syntax-adjacent failure).
- **Data flow:** per-claim `except Exception as exc` → `str(exc)` → HTTP 200 response `{"created": [...], "errors": [{"index": i, "claim_id": ..., "code": "INGEST_ERROR", "message": "<raw driver message>"}]}`.
- **Vulnerability:** raw `str(exc)` of any exception raised inside the transaction — including `neo4j.exceptions.Neo4jError` messages that can embed query fragments, parameter values, server version details, and the exact offending payload — is serialized into the client response. This contradicts the route's own documented intent ("raw str(exc) is never interpolated into the response", api/candidates.py:137-142).
- **Attack scenario:** attacker sends a claim with an oversized field (see SEC-BE-008) or a value that violates a constraint; the response leaks driver internals/query text that aid further attacks (e.g., reveals the exact Cypher and stored schema).
- **Impact:** information disclosure (DB internals, query text, schema hints); also turns server errors into 200-with-errors responses, complicating ops.
- **Reproduction (safe):** unit test `_ingest_candidate_claims` with a fake tx that raises `Neo4jError("Neo.ClientError.Statement...")`; assert the returned error message is sanitized (not the raw text).
- **Existing defenses:** global error handlers sanitize uncaught Neo4j errors; only the per-claim swallow path leaks.
- **Recommended fix:** map per-claim failures to a fixed `INGEST_ERROR` message with a stable error code, log the real exception server-side only.
- **Verification:** test asserting response errors contain no driver exception text.

---

### SEC-BE-007 | `ALLOWED_EMAILS` empty default is unenforced at startup; `email_verified` claim never checked | MEDIUM | NEEDS MANUAL VERIFICATION
- **Component:** `spoilerless/app/core/config.py:60-67` (default `""` disables allowlist, docstring: "never leave empty in production"); `render.yaml` defines no env (all env set out-of-band in the Render dashboard); `spoilerless/app/services/auth.py:159-177` (only `sub`/`email`/`name`/`picture` read; no `email_verified`, no `hd` check)
- **Entry point:** `POST /api/auth/google` (body `{"credential": "<Google ID token>"}`)
- **Data flow:** Google ID token → `verify_oauth2_token` (signature/aud/iss/exp OK) → `email = info.get("email","")` → `email.lower() not in allowed_emails` (empty set → pass) → role from `admin_emails` → user upsert + session.
- **Vulnerability:** (a) if `ALLOWED_EMAILS` was not set in the production dashboard, *any* Google account can sign in (config-dependent; cannot be verified from the repo — needs manual check); (b) Google's recommended `email_verified` check is absent — for Workspace-issued accounts Google does not guarantee email ownership without it, so the email-based allowlist/admin derivation (`role = "admin" if email in admin_emails`, auth.py:169) trusts an unverified claim in the worst case. Admin derivation is not affected for consumer accounts, but the check is cheap and recommended.
- **Attack scenario:** if allowlist unset: attacker signs in with any Google account → full app access (compounds SEC-BE-001/002). If allowlist set and a target email lives in a domain where the attacker can obtain an unverified Workspace account with that address (unusual but documented Google caveat): allowlist bypass.
- **Impact:** authentication boundary collapse (config-dependent) / weakened identity binding for role assignment.
- **Reproduction (safe):** (a) verify production env manually (needs operator); (b) unit test `AuthService.authenticate` with a fake verifier returning `{"sub":"s","email":"admin@example.com","email_verified":False}` and `admin_emails={"admin@example.com"}` → role is `admin` today; assert it should be rejected.
- **Existing defenses:** `verify_oauth2_token` enforces signature/audience/issuer/expiry; `verify_google_client_id_equality` startup check; avatar URL scheme sanitization; server-side role derivation.
- **Recommended fix:** fail startup (or refuse login) when `ALLOWED_EMAILS` is empty outside `ENV=dev`; require `email_verified is True` (or an `hd`-based policy) before using `email` for allowlist/admin decisions.
- **Verification:** test asserting login is refused for `email_verified=False` tokens and for allowlist-empty configs in non-dev env.

---

### SEC-BE-008 | Unbounded string fields on ingest, candidate edit, and path-finding routes (no body-size limit) | LOW | CONFIRMED
- **Component:** `spoilerless/app/domain/extraction.py:34-119` (`extractor_name`, `extractor_version`, `predicate`, `source_type`, `source_locator`, `evidence_locator` — no `max_length`); `spoilerless/app/api/candidates.py:70-89` (`EditCandidateRequest.label`, `evidence_text`, `source_locator` — no `max_length`); `spoilerless/app/api/graph.py:460-464` (`PathRequest.source_entity_id`/`target_entity_id` — plain `str`); uvicorn has no body-size cap and no app-level middleware enforces one.
- **Entry point:** `POST .../candidates/ingest`, `PATCH .../candidates/{claim_id}`, `POST .../graph/path`
- **Data flow:** attacker JSON string (e.g., 5 MB `extractor_name`) → Pydantic (passes — no length constraint) → Neo4j parameter → property-size error or memory/DB bloat; path ids flow into BFS maps.
- **Vulnerability:** oversized values are not rejected at the API boundary; Neo4j `Neo4jError` "Property value is too large" results leak via SEC-BE-006; multiple concurrent large payloads exhaust free-tier memory.
- **Attack scenario:** `curl -X POST .../candidates/ingest -d '{"extractor_name":"<5MB>", ...}'` → DB write failure + leak, or sustained parallel requests → memory pressure.
- **Impact:** DoS/resource abuse; secondary leak amplification.
- **Reproduction (safe):** unit test: `ExtractionClaim`/`EditCandidateRequest` accept a 10 MB string today (assert validation should reject > N chars).
- **Existing defenses:** `PlainText`/`Identifier`/`Label` caps on most fields; claims list capped at 500; `llm_max_*` caps bound the chat context path.
- **Recommended fix:** add `max_length` to all free-string fields; add an app-level body-size middleware (e.g., reject > 1 MB); cap `Content-Length` at the proxy.
- **Verification:** test asserting 422 for oversized fields on all three routes.

---

### SEC-BE-009 | Unauthenticated, uncached `/graph/expand` fires 7 parallel Neo4j queries per request — cheap CPU/connection exhaustion | LOW | CONFIRMED
- **Component:** `spoilerless/app/api/graph.py:304-386` (`get_expansion` — no auth dependency, no rate limit, deliberately no cache, T10-CACHE-06); `spoilerless/app/services/graph.py:75-89` (`asyncio.gather` of 7 queries)
- **Entry point:** `GET /api/series/{series_id}/graph/expand?node_id=<id>&expansion_key=<key>&episode_order=<n>&limit=<1..25>`
- **Data flow:** anonymous request → boundary resolve (2 Neo4j reads) + 7 parallel graph queries → projection (no caching) → response. Repeat.
- **Vulnerability:** the endpoint is anonymous, unthrottled, and never cached; each request costs ~9 DB round-trips on the free-tier Render service.
- **Attack scenario:** `for i in $(seq 1000); do curl '.../graph/expand?node_id=character:dexter&expansion_key=clues&episode_order=1' & done` → Neo4j connection pool exhaustion (pool max 50, graph/database.py:70), CPU saturation, 503s for all users.
- **Impact:** availability.
- **Reproduction (safe):** count DB calls per request in a unit test (fake database); assert 9+ executions per expand call.
- **Existing defenses:** `limit` capped at 25; `node_id` must be visible at boundary; Redis-backed cache exists for the sibling visualization route (not used here by design).
- **Recommended fix:** add anonymous rate limiting (per-IP with correct proxy handling — see SEC-BE-004) or a small cache for expansion deltas; at minimum bound `node_id` length.
- **Verification:** test asserting rate-limited 429 after N anonymous expand requests.

---

### SEC-BE-010 | Session cookie has no Max-Age; sessions accumulate without a per-user cap | LOW | HIGH CONFIDENCE
- **Component:** `spoilerless/app/api/auth.py:69-78` (`_make_cookie` — no `max_age`); `spoilerless/app/services/auth.py:179-181` (new session per login, old ones not revoked); `spoilerless/app/repository/session.py:197-224` (create), `:277-297` (hourly sweep)
- **Entry point:** `POST /api/auth/google` repeated logins
- **Data flow:** each login → new `:Session` node; cookie without Max-Age → browser-session cookie (lives until browser close, even though server TTL is 7 days); repeated logins accumulate live sessions per user until the hourly sweep.
- **Vulnerability:** (a) no `Max-Age` on the cookie — on shared machines the session token stays usable from the browser profile until closed, longer than the UX suggests; (b) no session cap per user — an attacker who obtains several session tokens (or a user who logs in on many devices) leaves many live sessions; there is no "revoke all other sessions" path.
- **Attack scenario:** session token theft from a shared browser profile remains valid server-side up to 7 days and until browser close; a stolen-token rotation (multiple logins) multiplies live sessions.
- **Impact:** session persistence/cleanup hygiene; modest blast-radius increase on token theft.
- **Reproduction (safe):** unit test `_make_cookie` response headers — assert `max-age` absent today.
- **Existing defenses:** 48-byte random tokens hashed at rest; no slide-on-read; hourly sweep; `revoked_at` on logout; HttpOnly/Secure/SameSite set.
- **Recommended fix:** set `max_age=session_ttl_seconds` on the cookie; add a per-user active-session cap (revoke oldest) or a "log out everywhere" endpoint.
- **Verification:** test asserting `Set-Cookie` carries `Max-Age=604800` and that session creation beyond cap revokes the oldest.

---

### SEC-BE-011 | Cypher assembled via f-string key/label interpolation (currently safe, closed sets only) | INFORMATIONAL | CONFIRMED
- **Component:** `spoilerless/app/graph/candidates.py:468-479` (`set_items = [f"claim.{key} = ${key}" for key in command["updates"]]`); `spoilerless/app/revisions/__init__.py:279-282` (`f"CREATE (r:{resource_type} $props) ..."`)
- **Entry point:** `PATCH /api/series/{series_id}/candidates/{claim_id}` (admin), `POST .../revisions/{revision_id}/revert` (authenticated)
- **Data flow:** today the interpolated identifiers come only from closed server-side sets: `EditCandidateRequest.model_dump()` keys (pydantic `extra="forbid"`), `RevisionAction`/`resource_type` values written by server code (enums + fixed literals `"Claim"`, `"UserNote"`, `"UserNote"`...). No request text reaches the f-string.
- **Vulnerability:** none exploitable today, but the pattern is one refactor away from Cypher injection (e.g., if a future field is added to `EditCandidateRequest` as a free-form key, or a revision's `resource_type` ever stores client input). Defense-in-depth gap only.
- **Reproduction (safe):** grep-based — confirm all `log_revision(resource_type=...)` call sites pass enum values/literals.
- **Existing defenses:** closed pydantic models; ontology enums; parametrized values.
- **Recommended fix:** replace with `SET claim += $updates` (map parameter) and validate `resource_type` against a label allowlist before interpolation.
- **Verification:** test asserting `SET claim += $updates` semantics (all fields updated, no interpolation).

---

### SEC-BE-012 | Share tokens travel in URLs (history/referrer exposure); `token_hash` returned to owners; wildcard `FRONTEND_ORIGINS` disables CSRF guard | INFORMATIONAL | POSSIBLE
- **Component:** `spoilerless/app/api/share.py:85-92` (`url=f"/share/{raw_token}"`), `:148-169` (list returns `token_hash`); `spoilerless/app/api/deps.py:167-169` (`if "*" in origins: return` — wildcard disables `verify_origin`)
- **Entry point:** `POST /api/share`, `GET /api/share`
- **Data flow:** raw 32-byte token embedded in a share URL returned to the creator; anyone with the URL can read the snapshot until TTL (30 days) or revocation; if an operator ever sets `FRONTEND_ORIGINS=*`, every state-changing route's CSRF origin check silently no-ops.
- **Vulnerability:** bearer-in-URL exposure via browser history, referrer headers (only partially mitigated by `Referrer-Policy: strict-origin-when-cross-origin`), and logging intermediaries; `*` origin misconfiguration would disable CSRF protection while CORS still allows credentialed cross-origin calls.
- **Attack scenario:** share URL pasted in chat/email/logs → snapshot readable by anyone; `FRONTEND_ORIGINS=*` + a crafted cross-origin POST with the victim's cookie (defense then rests on SameSite=Lax alone).
- **Impact:** snapshot confidentiality (by design of share links, but worth noting); CSRF protection collapse under misconfiguration.
- **Reproduction (safe):** static check of config parsing (deps.py) — wildcard branch returns before any origin comparison.
- **Existing defenses:** 32-byte entropy, hashed storage, TTL, revocation, SameSite=Lax, `Referrer-Policy` header, explicit CORS origin list.
- **Recommended fix:** document/share-link UX: consider short-lived tokens or a redemption flow; add a startup warning when `FRONTEND_ORIGINS` contains `*` with `allow_credentials=True`.
- **Verification:** test asserting startup/config validation rejects `*` origins in non-dev environments.

---

## Endpoint-by-Endpoint Request-Level Test Matrix

Legend: A=anonymous, U=authenticated user, UA=user or admin (owner-checked), AD=admin-only; ✓ protected, ✗ gap, ⚠ partial/conditional. "Boundary clamp" = client-chosen `visible_until_order` clamped to persisted progress (anon → 1).

| # | Method & Route | Auth | CSRF | Rate limit | Boundary clamp | IDOR/BOLA | Notes |
|---|---|---|---|---|---|---|---|
| 1 | GET/HEAD `/health` | A | – | – | – | – | OK; reveals service name/DB status (informational) |
| 2 | POST `/api/auth/google` | A | ✓ | ✓ IP* | – | – | *per-IP bucket collapses behind proxy (SEC-BE-004); email_verified not checked (SEC-BE-007) |
| 3 | GET `/api/auth/me` | U | – | – | – | – | OK |
| 4 | POST `/api/auth/logout` | A(cookie) | ✓ | – | – | – | OK; CSRF-protected, idempotent |
| 5 | GET `/api/series` | A | – | – | – | – | OK |
| 6 | GET `/api/series/{series_id}` | A | – | – | – | – | OK |
| 7 | GET `/api/series/{series_id}/episodes` | A/U | – | – | ⚠ U-no-record bypass | – | SEC-BE-001 |
| 8 | GET `/api/series/{series_id}/graph` | A/U | – | – | ⚠ U-no-record bypass | – | SEC-BE-001; anon fixed at 1 ✓ |
| 9 | GET `.../graph/visualization` | A/U | – | – | ✓ (shared helper) | – | focus_id ≤20, view allowlist ✓ |
| 10 | GET `.../graph/expand` | A | – | ✗ | ✓ | – | SEC-BE-009 (uncached, unthrottled) |
| 11 | POST `.../graph/path` | A | – | – | ✓ | – | ids unbounded (SEC-BE-008) |
| 12 | GET `.../export` | A/U | – | – | ✓ | – | filename slugified ✓ |
| 13 | POST `.../notes` | U | ✓ | ✓ | – | ✓ | content ≤4000 ✓ |
| 14 | GET `.../notes` | A | – | – | ✗ anon clamp | – | SEC-BE-002; exposes all users' notes + user_id |
| 15 | GET `.../notes/{note_id}` | A | – | – | ✗ anon clamp | – | SEC-BE-002 |
| 16 | PATCH/DELETE `.../notes/{note_id}` | U | ✓ | ✓ | – | ✓ owner/admin | OK |
| 17 | POST `.../custom-nodes` | U | ✓ | ✓ | – | ✓ | episode must exist in series ✓; label ≤200 ✓ |
| 18 | GET `.../custom-nodes/{node_id}` | A | – | – | ✗ anon clamp | – | SEC-BE-002 |
| 19 | PATCH/DELETE `.../custom-nodes/{node_id}` | U | ✓ | ✓ | – | ✓ owner/admin | OK |
| 20 | POST `.../custom-relationships` | U | ✓ | ✓ | – | ✓ | visibility server-derived ✓ (max of endpoints) |
| 21 | GET `.../custom-relationships/{id}` | A | – | – | ✗ anon clamp | – | SEC-BE-002 |
| 22 | PATCH/DELETE `.../custom-relationships/{id}` | U | ✓ | ✓ | – | ✓ owner/admin | OK |
| 23 | GET `/api/series/{id}/progress` | U | – | – | – | ✓ | OK; generic 404 |
| 24 | POST `/api/series/{id}/progress` | U | ✓ | – | ✓ server-validated | ✓ | D-06 persisted-order validation ✓; no CSRF bypass |
| 25 | POST `.../change-sets` | U | ✓ | – | ✓ progress-resolved | ✓ | ops validated server-side ✓ |
| 26 | POST `.../change-sets/{id}/confirm` | AD | ✓ | – | ✓ fresh re-check | ✓ | OK |
| 27 | POST `.../change-sets/{id}/reject` | U | ✓ | – | – | ✓ user-scoped MATCH | OK (404 for foreign) |
| 28 | POST `.../change-sets/{id}/revert` | U | ✓ | – | – | ✓ user-scoped | OK |
| 29 | POST `.../candidates/ingest` | U (any) | ✓ | – | ✗ client-controlled vfo | – | SEC-BE-003 (+006, +008) |
| 30 | GET `.../candidates` | A | – | – | ✗ anon clamp | – | SEC-BE-002; boundary required ✓ |
| 31 | GET `.../candidates/{claim_id}` | A | – | – | ✗ anon clamp | – | SEC-BE-002; 404 echoes claim_id (harmless) |
| 32 | POST `.../candidates/{claim_id}/approve` | AD | ✓ | – | – | ✓ | OK |
| 33 | POST `.../candidates/{claim_id}/reject` | AD | ✓ | – | – | ✓ | OK |
| 34 | PATCH `.../candidates/{claim_id}` | AD | ✓ | – | – | ✓ | f-string SET keys (SEC-BE-011); unbounded fields (008) |
| 35 | GET `.../revisions`, `.../revisions/{id}` | A | – | – | ✗ anon clamp | – | revisions expose before/after snapshots + user_id |
| 36 | POST `.../revisions/{id}/revert` | U | ✓ | – | ✓ visibility-gated | ✓ owner checks (snapshot/current) | CREATE revisions 422 ✓; canonical 409 ✓ |
| 37 | GET/PUT `/api/settings/llm` | AD | PUT ✓ | – | – | – | OK; masked key; blank-key guard ✓ |
| 38 | POST `/api/share` | U | ✓ | – | ✓ clamp (fail-closed 1) | ✓ | token 32B entropy, TTL 30d ✓; URL exposure (012) |
| 39 | GET `/api/share/{token}/graph` | A (bearer) | – | – | n/a (snapshot) | ✓ | token-gated; 404 uniform ✓ |
| 40 | GET `/api/share` | U | – | – | – | ✓ | returns token_hash only ✓ |
| 41 | DELETE `/api/share/{token}` | U | ✓ | – | – | ✓ owner/admin | OK |
| 42 | POST `.../chat/sessions` | U | ✓ | – | – | ✓ | title ≤200 ✓ |
| 43 | GET `.../chat/sessions` | U | – | – | – | ✓ | OK |
| 44 | GET `.../chat/sessions/{id}` | U | – | – | ✓ messages boundary-filtered | ✓ | OK |
| 45 | DELETE `.../chat/sessions/{id}` | U | ✓ | – | – | ✓ | OK |
| 46 | POST `.../chat/sessions/{id}/messages` | U | ✓ | ✓ per-user | ✓ | ✓ | question ≤4000 ✓; BYOK SSRF (005) |
| 47 | POST `.../chat/sessions/{id}/messages/stream` | U | ✓ | ✓ per-user | ✓ | ✓ | SSE; structured error events ✓; BYOK SSRF (005) |
| 48 | GET `/api/static/*` | A | – | – | – | – | Starlette StaticFiles (traversal-safe) ✓ |

**Cross-cutting checks (passed):** session tokens 48-byte urlsafe, SHA-256 hashed, no raw storage; cookie HttpOnly+Secure(prod default)+SameSite=Lax; no slide-on-read; login/chat/content-write limiters Redis-backed; CSRF origin guard on all 20+ state-changing routes (fails closed on missing Origin/Referer); CORS explicit origins + credentials; request logging excludes Cookie/Authorization/X-LLM-*; error envelopes sanitized globally (except SEC-BE-006); avatar URL scheme allowlist; no SQL/shell/template/CRLF injection found; `Content-Disposition` filename slugified; LLM keys never in responses/logs; graph cache keys include user+effective boundary with epoch invalidation; no wildcard Redis exposure.
